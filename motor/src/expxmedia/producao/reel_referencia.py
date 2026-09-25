"""Produção do reel por referência sob medida: montar, prévia, render e verificação (D-18, D-19, D-36).

Porta do caminho sob medida de `Instragram-Videos/pipeline/render_remotion.py` (`montar_sob_medida`,
`renderizar_sob_medida`, `previa`, `normalizar_audio`) e da verificação do modo recriado de
`Instragram-Videos/pipeline/verify.py`, sobre a pasta criada por `referencia.sob_medida`
(`referencias/<slug>/`, ver lá o que ela contém).

Cada etapa confere, ANTES de qualquer outra coisa, o código do reel com o validador no modo `sob_medida`
(`template.validar`, D-36): cores literais da paleta da referência passam; import e API proibidos
(`child_process`, `fs`, rede, `eval`...) recusam o reel antes de montar, narrar ou renderizar. Depois vem o
`cenas.json` (âncoras em ordem no roteiro, eventos existentes, trilha que não repete a de outro reel).

- `narrar`: narra `roteiro.txt` UMA vez, na voz do porta-voz, com o gate do roteiro (130 a 180 palavras,
  sem travessão, markdown nem decimal). Narração existente não é refeita: "não chame de novo por ajuste de
  cena" (origem: Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:82).
- `montar`: `scripts/montar.mjs` do kit (D-19) grava em `midia/` a linha do tempo pelas âncoras e a trilha
  com os efeitos; exige a leitura da referência escrita (`analise/leitura.md`) e recusa trilha repetida.
- `previa`: um still a 60% de cada cena com as guias da área segura (220 e 1500) e a folha
  `previa/NN/previa.jpg`; no máximo três voltas (origem: Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:146).
- `renderizar`: render da composição, normalização da mistura (-14 LUFS, pico ≤ -1 dBFS, com a passada do
  limitador quando o AAC estoura), verificação no perfil `sob_medida` e a peça `produzida`.
- `produzir`: o encadeamento inteiro, na ordem da skill: código → cenas → narração → montagem → prévia →
  render → verificação → peça.

Fontes, selo (porta-voz e canal) e o que é marca vêm da Alma por props (`producao.reel.props_alma`); a linha
do tempo e o áudio também chegam por props. O render roda num projeto temporário (os pacotes do kit por
link e o módulo `@expxmedia/template`), nunca escrevendo no kit.

Uso:

    from expxmedia.producao import reel_referencia
    r = reel_referencia.produzir(raiz, "referencias/meu-reel")   # {"peca_id", "status", "video", ...}
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from expxmedia.alma import carregar as alma_carregar
from expxmedia.ambiente.verificar import Verificador
from expxmedia.motion import previa as motion_previa
from expxmedia.motion import remotion
from expxmedia.narrar import base as narrar_base
from expxmedia.nucleo import arquivos, rastro, tempo
from expxmedia.nucleo.raiz import relativo
from expxmedia.peca import modelo
from expxmedia.producao import reel as producao_reel
from expxmedia.referencia import sob_medida
from expxmedia.revisar import roteiro as gate_roteiro
from expxmedia.template import validar
from expxmedia.video import ffmpeg, verificar

__all__ = [
    "ErroReferencia",
    "ErroCodigoRecusado",
    "ErroVerificacaoReprovada",
    "PERFIL",
    "LIMITE_PREVIAS",
    "validar_codigo",
    "conferir_codigo",
    "narrar",
    "montar",
    "previa",
    "renderizar",
    "produzir",
]

TIPO, FORMATO, PERFIL = "reel", "9:16", "sob_medida"
LIMITE_PREVIAS = 3  # "no máximo três voltas"; origem: Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:146
TEMPO_MONTAR_S = 600
FIM_DA_SAIDA = 1500  # origem: Instragram-Videos/pipeline/render_remotion.py:159 (últimos 1500 caracteres)
PROVEDOR_MOTION, PROVEDOR_VIDEO = "remotion", "ffmpeg"
LEITURA = "analise/leitura.md"


class ErroReferencia(RuntimeError):
    """O reel por referência não pôde seguir; a mensagem diz a etapa e o que falta."""


class ErroCodigoRecusado(ErroReferencia):
    """O validador de código (modo sob_medida) achou import ou API proibidos: nada foi montado nem renderizado."""

    def __init__(self, achados: list[dict[str, Any]]) -> None:
        resumo = "; ".join(f"{a['arquivo']}:{a['linha']} {a['detalhe']}" for a in achados[:10])
        super().__init__(f"código do reel recusado pelo validador (modo {PERFIL}): {resumo}")
        self.achados = achados


class ErroVerificacaoReprovada(ErroReferencia):
    """O MP4 saiu e reprovou no perfil sob_medida; a peça ficou em `roteiro`."""

    def __init__(self, peca_id: str, achados: list[dict[str, Any]]) -> None:
        super().__init__(f"{peca_id}: verificação reprovada no perfil {PERFIL}: "
                         + "; ".join(a["detalhe"] for a in achados))
        self.peca_id = peca_id
        self.achados = achados


# ---------------------------------------------------------------- código e cenas


def validar_codigo(pasta: Path | str) -> list[dict[str, Any]]:
    """Achados do validador de código no modo `sob_medida` (D-36) sobre `reel/` (lista vazia = aprovado)."""
    reel_dir = Path(pasta) / sob_medida.PASTA_REEL
    if not (reel_dir / "src" / "Reel.tsx").is_file():
        raise ErroReferencia(f"falta {sob_medida.PASTA_REEL}/src/Reel.tsx: crie o reel sob medida antes")
    return validar.validar_template(reel_dir, modo=PERFIL)


def conferir_codigo(pasta: Path | str) -> list[dict[str, Any]]:
    """`validar_codigo` que levanta ErroCodigoRecusado com os achados."""
    achados = validar_codigo(pasta)
    if achados:
        raise ErroCodigoRecusado(achados)
    return achados


def _antes(raiz: Path, pasta: Path | str) -> Path:
    """Código e cenas.json conferidos, nesta ordem, antes de qualquer etapa. Devolve a pasta do reel."""
    pasta = sob_medida.pasta_do_reel(raiz, pasta)
    if not (pasta / sob_medida.MARCADOR).is_file():
        raise ErroReferencia(f"{relativo(raiz, pasta)} não é um reel sob medida (falta {sob_medida.MARCADOR})")
    conferir_codigo(pasta)
    sob_medida.conferir_cenas(raiz, pasta)
    return pasta


def _marcador(pasta: Path) -> dict[str, Any]:
    return arquivos.ler_json(pasta / sob_medida.MARCADOR)


def _gravar_marcador(raiz: Path, pasta: Path, muda: dict[str, Any]) -> dict[str, Any]:
    dados = {**_marcador(pasta), **muda, "atualizado_em": tempo.agora_iso(raiz)}
    arquivos.gravar_json(pasta / sob_medida.MARCADOR, dados)
    return dados


def _porta_voz(alma: dict[str, Any], pedido: str | None) -> dict[str, Any]:
    vozes = [v for v in alma.get("porta_vozes") or [] if isinstance(v, dict)]
    if pedido:
        achado = next((v for v in vozes if v.get("id") == pedido), None)
        if achado is None:
            raise ErroReferencia(f"o porta-voz {pedido} não existe na Alma")
        return achado
    achado = next((v for v in vozes if v.get("principal")), vozes[0] if vozes else None)
    if achado is None:
        raise ErroReferencia("a Alma não tem porta-voz para narrar e assinar o selo")
    return achado


def _alma(raiz: Path):
    try:
        return alma_carregar.carregar(raiz)
    except alma_carregar.ErroAlmaAusente as erro:
        raise ErroReferencia(str(erro)) from None


# ---------------------------------------------------------------- narração


def _roteiro(pasta: Path) -> str:
    arq = pasta / sob_medida.ROTEIRO
    if not arq.is_file():
        raise ErroReferencia(f"falta {sob_medida.ROTEIRO}: escreva o roteiro a partir da leitura antes de narrar")
    return arq.read_text(encoding="utf-8").strip()


def narrar(raiz: Path | str, pasta: Path | str, *, porta_voz: str | None = None,
           opcoes_narrar: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Narra o roteiro uma vez em `midia/`; com a narração já feita, não chama o provedor e devolve None.

    O gate do roteiro vem antes: 130 a 180 palavras, sem travessão, markdown nem número decimal (o CTA do
    reel por referência é falado e não tem palavra-chave). origem: Instragram-Videos/pipeline/tts.py:103-106
    """
    raiz = Path(raiz)
    pasta = _antes(raiz, pasta)
    midia = pasta / sob_medida.MIDIA
    if (midia / narrar_base.ARQUIVO_AUDIO).is_file() and (midia / narrar_base.ARQUIVO_ALINHAMENTO).is_file():
        return None
    texto = _roteiro(pasta)
    gate = gate_roteiro.revisar_roteiro(texto, None)
    achados = [a for a in gate["achados"] if a["checagem"] != "cta"]
    if achados:
        raise ErroReferencia("roteiro reprovado antes de narrar: " + "; ".join(a["detalhe"] for a in achados))
    alma = _alma(raiz)
    voz = _porta_voz(alma.dados, porta_voz)
    narr = narrar_base.narrar(raiz, texto, voz["id"], TIPO, relativo(raiz, midia), **(opcoes_narrar or {}))
    _gravar_marcador(raiz, pasta, {"narracao": {"provedor": narr["provedor"], "porta_voz": voz["id"],
                                                "duracao_s": narr["duracao_s"], "palavras": narr["palavras"]}})
    return narr


# ---------------------------------------------------------------- montagem


def montar(raiz: Path | str, pasta: Path | str) -> dict[str, Any]:
    """Linha do tempo e trilha em `midia/` pelo `scripts/montar.mjs` do kit. Devolve a linha do tempo.

    origem: Instragram-Videos/pipeline/render_remotion.py:156-161 (montar_sob_medida)
    """
    raiz = Path(raiz)
    pasta = _antes(raiz, pasta)
    midia = pasta / sob_medida.MIDIA
    narracao, alinhamento = midia / narrar_base.ARQUIVO_AUDIO, midia / narrar_base.ARQUIVO_ALINHAMENTO
    if not (narracao.is_file() and alinhamento.is_file()):
        raise ErroReferencia(f"falta a narração em {relativo(raiz, midia)} (narracao.mp3 e alinhamento.json): "
                             "narre o roteiro antes de montar")
    node = shutil.which("node")
    if node is None:
        raise ErroReferencia("node não encontrado no PATH (a montagem da linha do tempo roda em Node)")
    with tempfile.TemporaryDirectory() as tmp:
        assinaturas = Path(tmp) / "assinaturas.json"
        assinaturas.write_text(json.dumps(sob_medida.trilhas_da_instalacao(raiz, fora=pasta), ensure_ascii=False),
                               encoding="utf-8")
        cmd = [node, str(producao_reel.MONTAR), "--reel", str(pasta / sob_medida.PASTA_REEL), "--narracao", str(narracao),
               "--alinhamento", str(alinhamento), "--saida", str(midia), "--assinaturas", str(assinaturas),
               "--leitura", str(pasta / LEITURA)]
        avatar = midia / "avatar.mp4"
        if avatar.is_file():
            cmd += ["--avatar", str(avatar)]
        try:
            r = subprocess.run(cmd, cwd=remotion.KIT, capture_output=True, text=True, timeout=TEMPO_MONTAR_S)
        except subprocess.TimeoutExpired as erro:
            raise ErroReferencia(f"a montagem passou do tempo limite de {TEMPO_MONTAR_S} s") from erro
    if r.returncode:
        raise ErroReferencia(f"a montagem falhou:\n{((r.stdout or '') + (r.stderr or ''))[-FIM_DA_SAIDA:]}")
    timeline = arquivos.ler_json(midia / "timeline.json")
    if int(timeline["fps"]) != verificar.FPS:
        raise ErroReferencia(f"a linha do tempo saiu a {timeline['fps']} fps; o perfil {PERFIL} pede {verificar.FPS}")
    timeline["_avisos"] = [l.strip() for l in ((r.stdout or "") + (r.stderr or "")).splitlines()
                           if l.strip().startswith("aviso:")]
    return timeline


# ---------------------------------------------------------------- render


def _composicao(pasta: Path) -> str:
    return "Reel-" + "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in pasta.name)


def _preparar_render(raiz: Path, pasta: Path, trabalho: Path, timeline: dict[str, Any], *,
                     porta_voz: str | None, canal: str | None,
                     cache_fontes: Path | str | None) -> tuple[str, Path, Path, dict[str, Any], list[str]]:
    """(composição, projeto, public dir, props, avisos) do render: a Alma, a linha do tempo e o áudio por props."""
    midia = pasta / sob_medida.MIDIA
    publico = trabalho / "publico"
    publico.mkdir(parents=True)
    audio: dict[str, str | None] = {"narracao": None, "trilha": None, "avatar": None}
    for chave, nome in (("narracao", narrar_base.ARQUIVO_AUDIO), ("trilha", "trilha.wav"), ("avatar", "avatar.mp4")):
        if (midia / nome).is_file():
            shutil.copyfile(midia / nome, publico / nome)
            audio[chave] = nome
    alma = _alma(raiz)
    marcador = _marcador(pasta)
    pedido = porta_voz or ((marcador.get("narracao") or {}).get("porta_voz"))
    voz = _porta_voz(alma.dados, pedido)
    alma_props, avisos = producao_reel.props_alma(alma, publico, raiz=raiz, cache_fontes=cache_fontes,
                                                  porta_voz=voz, canal=canal)
    composicao = _composicao(pasta)
    projeto = sob_medida.preparar_projeto(pasta, trabalho / "projeto", composicao)
    timeline = {k: v for k, v in timeline.items() if not k.startswith("_")}
    return composicao, projeto, publico, {"alma": alma_props, "timeline": timeline, "audio": audio}, avisos


def previa(raiz: Path | str, pasta: Path | str, *, porta_voz: str | None = None, canal: str | None = None,
           cache_fontes: Path | str | None = None) -> dict[str, Any]:
    """Monta e grava a prévia com as guias em `previa/NN/` (no máximo três voltas).

    origem: Instragram-Videos/pipeline/render_remotion.py:177-207 (previa)
    """
    raiz = Path(raiz)
    pasta = _antes(raiz, pasta)
    feitas = sorted(p for p in (pasta / "previa").glob("[0-9][0-9]") if p.is_dir())
    if len(feitas) >= LIMITE_PREVIAS:
        raise ErroReferencia(f"no máximo {LIMITE_PREVIAS} voltas de prévia: renderize, ou recomece o reel se "
                             "ainda não ficou parecido com a referência")
    timeline = montar(raiz, pasta)
    destino = pasta / "previa" / f"{len(feitas) + 1:02d}"
    with tempfile.TemporaryDirectory(prefix="referencia-previa-") as tmp:
        composicao, projeto, publico, props, avisos = _preparar_render(
            raiz, pasta, Path(tmp), timeline, porta_voz=porta_voz, canal=canal, cache_fontes=cache_fontes)
        props["audio"] = {"narracao": None, "trilha": None, "avatar": props["audio"]["avatar"]}
        feita = motion_previa.gerar_previa(composicao, props["timeline"], destino, props, projeto=projeto,
                                           public_dir=publico)
    return {"folha": relativo(raiz, feita["folha"]), "imagens": [relativo(raiz, p) for p in feita["imagens"]],
            "quadros": feita["quadros"], "volta": len(feitas) + 1, "avisos": timeline["_avisos"] + avisos}


def _peca(raiz: Path, pasta: Path, *, origem: str, agente: str | None, porta_voz: str | None) -> str:
    marcador = _marcador(pasta)
    peca_id = marcador.get("peca_id")
    if isinstance(peca_id, str) and peca_id:
        try:
            modelo.carregar(raiz, peca_id)
            return peca_id
        except modelo.ErroPeca:
            pass
    voz = porta_voz or (marcador.get("narracao") or {}).get("porta_voz")
    peca = modelo.criar(raiz, tipo=TIPO, titulo=marcador.get("titulo") or marcador["slug"], formatos=[FORMATO],
                        slug=marcador["slug"], status="roteiro", porta_voz=voz, origem=origem, agente=agente)
    _gravar_marcador(raiz, pasta, {"peca_id": peca["peca_id"]})
    return peca["peca_id"]


def renderizar(raiz: Path | str, pasta: Path | str, *, porta_voz: str | None = None, canal: str | None = None,
               cache_fontes: Path | str | None = None, origem: str = "skill",
               agente: str | None = None) -> dict[str, Any]:
    """Monta, renderiza, normaliza, verifica no perfil sob_medida e registra a peça.

    origem: Instragram-Videos/pipeline/render_remotion.py:164-174 (renderizar_sob_medida) e
    Instragram-Videos/pipeline/verify.py (modo recriado)
    """
    raiz = Path(raiz)
    pasta = _antes(raiz, pasta)
    inicio = time.monotonic()
    timeline = montar(raiz, pasta)
    for nome in (sob_medida.ROTEIRO, sob_medida.LEGENDA):
        if not (pasta / nome).is_file():
            raise ErroReferencia(f"falta {nome}: o perfil {PERFIL} confere roteiro e legenda do post")
    Verificador(raiz).escolher_provedor("renderizar_motion")
    peca_id = _peca(raiz, pasta, origem=origem, agente=agente, porta_voz=porta_voz)
    pack = modelo.carregar(raiz, peca_id)["pack"]
    base = modelo.pasta(raiz, peca_id)
    midia_peca, texto_peca, saida_peca = base / "midia", base / "texto", base / "saida"
    for p in (midia_peca, texto_peca, saida_peca):
        p.mkdir(exist_ok=True)
    midia = pasta / sob_medida.MIDIA
    etapa = ["renderizar"]

    def falhou(detalhe: str) -> None:
        rastro.registrar(raiz, origem=origem, evento="geracao_falhou", resultado="falha", pack=pack, peca_id=peca_id,
                         agente=agente, capacidade=None, provedor=None, detalhe=detalhe[:500],
                         segundos=round(time.monotonic() - inicio, 3))

    try:
        # os artefatos que o perfil confere, na peça
        copias = [(pasta / sob_medida.ROTEIRO, texto_peca / "roteiro.txt"),
                  (pasta / sob_medida.LEGENDA, texto_peca / "legenda.txt"),
                  (midia / narrar_base.ARQUIVO_AUDIO, midia_peca / narrar_base.ARQUIVO_AUDIO),
                  (midia / narrar_base.ARQUIVO_ALINHAMENTO, midia_peca / narrar_base.ARQUIVO_ALINHAMENTO),
                  (midia / "timeline.json", midia_peca / "timeline.json"),
                  (pasta / sob_medida.PASTA_REEL / "cenas.json", midia_peca / "cenas.json")]
        for de, para in copias:
            shutil.copyfile(de, para)
        with tempfile.TemporaryDirectory(prefix=f"{peca_id}-render-") as tmp:
            composicao, projeto, publico, props, avisos = _preparar_render(
                raiz, pasta, Path(tmp), timeline, porta_voz=porta_voz, canal=canal, cache_fontes=cache_fontes)
            bruto = remotion.renderizar(composicao, Path(tmp) / "bruto.mp4", props, projeto=projeto, public_dir=publico)
            # mistura normalizada: -14 LUFS, pico ≤ -1 dBFS (passada do limitador quando o AAC estoura)
            etapa[0] = "normalizar"
            final = saida_peca / "final.mp4"
            loud = ffmpeg.normalizar_audio(bruto, final)
        etapa[0] = "verificar"
        art = verificar.Artefatos(alinhamento=midia_peca / narrar_base.ARQUIVO_ALINHAMENTO,
                                  roteiro=texto_peca / "roteiro.txt", legenda_post=texto_peca / "legenda.txt")
        resultado = verificar.verificar(final, PERFIL, art)
        if not resultado["aprovado"]:
            raise ErroVerificacaoReprovada(peca_id, resultado["achados"])
    except ErroVerificacaoReprovada as erro:
        falhou(str(erro))
        raise
    except Exception as erro:  # noqa: BLE001 — falha de produção vira evento, e sobe
        falhou(f"{etapa[0]}: {type(erro).__name__}: {erro}")
        raise

    registrar = [(final, "final", FORMATO), (texto_peca / "roteiro.txt", "roteiro", None),
                 (texto_peca / "legenda.txt", "legenda", None),
                 (midia_peca / narrar_base.ARQUIVO_AUDIO, "audio", None),
                 (midia_peca / narrar_base.ARQUIVO_ALINHAMENTO, "alinhamento", None)]
    previas = sorted(p for p in (pasta / "previa").glob("[0-9][0-9]/previa.jpg"))
    if previas:
        (base / "previa").mkdir(exist_ok=True)
        shutil.copyfile(previas[-1], base / "previa" / "previa.jpg")
        registrar.append((base / "previa" / "previa.jpg", "previa", None))
    for caminho, papel, formato in registrar:
        modelo.registrar_arquivo(raiz, peca_id, caminho, papel=papel, formato=formato)

    def aplicar(atual: dict[str, Any]) -> None:
        atual["conteudo"]["roteiro"] = "texto/roteiro.txt"
        atual["conteudo"]["legenda"] = "texto/legenda.txt"

    modelo._atualizar(raiz, peca_id, aplicar)
    narracao = _marcador(pasta).get("narracao") or {}
    provedores = {**({"narrar": narracao["provedor"]} if narracao.get("provedor") else {}),
                  "renderizar_motion": PROVEDOR_MOTION, "editar_video": PROVEDOR_VIDEO}
    duracao = ffmpeg.sondar(final)["duracao"]
    segundos = round(time.monotonic() - inicio, 3)
    modelo.registrar_producao(raiz, peca_id, capacidades=list(provedores), provedores=provedores, segundos=segundos)
    rastro.registrar(raiz, origem=origem, evento="geracao_concluida", resultado="ok", pack=pack, peca_id=peca_id,
                     agente=agente, capacidade="renderizar_motion", provedor=PROVEDOR_MOTION,
                     detalhe=f"reel por referência de {str(round(duracao, 1)).replace('.', ',')} s aprovado no perfil {PERFIL}",
                     arquivos=[c for c, _, _ in registrar], segundos=segundos)
    peca = modelo.carregar(raiz, peca_id)
    if peca["status"] == "roteiro":
        peca = modelo.mudar_status(raiz, peca_id, "produzida", origem=origem, agente=agente)
    return {
        "peca_id": peca_id,
        "status": peca["status"],
        "tipo": TIPO,
        "pasta": relativo(raiz, base),
        "video": relativo(raiz, final),
        "duracao": duracao,
        "arquivos": peca["arquivos"],
        "montagem": {"cenas": len(timeline["cenas"]), "quadros": timeline["totalFrames"]},
        "loudness": loud,
        "verificacao": resultado,
        "segundos": segundos,
        "avisos": timeline["_avisos"] + avisos,
    }


def produzir(raiz: Path | str, pasta: Path | str, *, porta_voz: str | None = None, canal: str | None = None,
             cache_fontes: Path | str | None = None, opcoes_narrar: dict[str, Any] | None = None,
             origem: str = "skill", agente: str | None = None) -> dict[str, Any]:
    """O encadeamento: código e cenas conferidos → narração (uma vez) → montagem → prévia → render →
    normalização → verificação no perfil sob_medida → peça. origem: Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:176"""
    raiz = Path(raiz)
    pasta_reel = _antes(raiz, pasta)  # nada é narrado nem renderizado com código ou cenas recusados
    codigo = validar_codigo(pasta_reel)
    narrar(raiz, pasta_reel, porta_voz=porta_voz, opcoes_narrar=opcoes_narrar)
    feita = previa(raiz, pasta_reel, porta_voz=porta_voz, canal=canal, cache_fontes=cache_fontes)
    r = renderizar(raiz, pasta_reel, porta_voz=porta_voz, canal=canal, cache_fontes=cache_fontes, origem=origem,
                   agente=agente)
    return {**r, "previa": feita["folha"], "codigo": codigo}
