"""Produção de aula: MP4 + SRT por formato (16:9 e/ou 9:16) a partir de um roteiro com marcadores (D-23, D-26,
D-32, D-40, D-41).

Porta do pipeline das aulas (base/aula-pipeline.md, versão mais evoluída), na ordem da origem
(origem: cursos-ia/radar-ia-07-jev-codigo/README.md:53-56): narrar → (editar a tela) → avatar →
legendas → render nos dois formatos. A entrada é um objeto JSON (o `exemplo.json` do template de aula é
uma entrada completa):

    {
      "titulo": "...",
      "roteiro": "[[s1]] texto falado ... [[s2]] ...",     marcadores [[nome]] antes de cada trecho
      "cenas": [{"cue": "s1", "modo": "cena" | "tela" | "slide", "rotulo", "titulo", "texto", "itens",
                 "passo", "fato", "slide"}, ...],           uma por cue, na ordem da fala
      "formatos": ["16:9", "9:16"] | null,                 padrão: os dois
      "avatar": true | false | null,                       null: usa se a capacidade estiver habilitada
      "tela": {"janelas": [...], "marcas": {...} | "caminho/marks-rel.json" | null, "cue_final": null} | null,
      "apresentacao": "P-..." | null,                      peça de apresentação cujos slides a aula mostra
      "template": "aula-padrao-..." | null,                padrão: a composição Aula do kit
      "serie", "porta_voz", "pack", "slug", "oferta", "conteudo"   (opcionais)
    }

O caminho:

1. confere a entrada **antes** de criar a peça: cada cena aponta para um marcador do roteiro, na ordem;
   cena de tela exige gravação; cena de slide exige a apresentação com os PNG dos slides;
2. cria a peça em `roteiro` e **narra uma vez** com o tipo `aula`: o bloco de parâmetros de aula do
   porta-voz (D-40) e **sem** a correção de ritmo mínimo, que é só do reel;
3. `cues.json` dos marcadores (aula.cues), com o hash da narração;
4. legendas 42x2 com o texto do roteiro nos tempos da narração (D-23) e o SRT de cada formato;
5. avatar, opcional, **sempre do áudio** (D-26), pelo provedor que o ambiente escolher (`heygen` ou o de
   teste); a duração do avatar precisa bater com a da narração (base/avatar-heygen-processo-atual.md, risco 4);
6. tela, opcional: a gravação editada por cues (aula.editar_tela, D-32);
7. render da composição `Aula` em cada formato pedido, normalização (-14 LUFS, pico ≤ -1 dBFS) e
   verificação no perfil `aula` (D-41); reprovado, `geracao_falhou` e a peça fica em `roteiro`;
8. registra arquivos, `compoe` (a apresentação usada), produção e `geracao_concluida`; peça `produzida`.

Uso:

    from expxmedia.producao import aula
    r = aula.produzir(raiz, entrada)   # {"peca_id", "status", "pasta", "videos", "srts", "verificacao", ...}
"""
from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from expxmedia.alma import carregar as alma_carregar
from expxmedia.ambiente.verificar import ErroCapacidade, Verificador
from expxmedia.aula import cues as aula_cues
from expxmedia.aula import editar_tela
from expxmedia.legendar import aula as legenda_aula
from expxmedia.legendar import srt
from expxmedia.motion import remotion
from expxmedia.narrar import base as narrar_base
from expxmedia.nucleo import arquivos, rastro
from expxmedia.nucleo import raiz as instalacao
from expxmedia.nucleo.raiz import relativo
from expxmedia.peca import modelo
from expxmedia.producao import reel as _reel
from expxmedia.template import galeria_local
from expxmedia.video import ffmpeg, verificar

__all__ = [
    "ErroProducaoAula",
    "ErroEntradaAula",
    "ErroVerificacaoReprovada",
    "TIPO",
    "PERFIL",
    "COMPOSICAO",
    "CAMPOS",
    "MODOS",
    "TOLERANCIA_AVATAR_S",
    "ler_entrada",
    "palavras_do_alinhamento",
    "nome_saida",
    "produzir",
]

TIPO, PERFIL, COMPOSICAO = "aula", "aula", "Aula"
FORMATOS = ("16:9", "9:16")
CAMPOS = ("titulo", "roteiro", "cenas", "formatos", "avatar", "tela", "apresentacao", "template", "serie",
          "porta_voz", "pack", "slug", "oferta", "conteudo")
CAMPOS_CENA = ("cue", "modo", "rotulo", "titulo", "texto", "itens", "passo", "fato", "slide")
MODOS = ("cena", "tela", "slide")
# Avatar e narração saem do mesmo mp3; na origem a diferença medida foi de ~12 ms (294,696 contra 294,708 s).
# origem: cursos-ia/radar-ia-09-jev-calibracao/public/avatar.mp4 (ffprobe, base/avatar-heygen-processo-atual.md)
TOLERANCIA_AVATAR_S = 0.1
PROVEDOR_MOTION, PROVEDOR_VIDEO, PROVEDOR_LEGENDA = "remotion", "ffmpeg", "local"
AVATARES = {"heygen": "expxmedia.avatar.heygen", "teste": "expxmedia.avatar.teste"}
ARQ_AVATAR, ARQ_DEMO, ARQ_DEMO_JSON, ARQ_LEGENDAS = "avatar.mp4", "demo.mp4", "demo.json", "legendas.json"


class ErroProducaoAula(RuntimeError):
    """A produção da aula não terminou."""


class ErroEntradaAula(ValueError):
    """Entrada fora do formato; `campo` diz qual. Nada foi criado."""

    def __init__(self, campo: str, mensagem: str) -> None:
        super().__init__(f"campo '{campo}': {mensagem}")
        self.campo = campo


class ErroVerificacaoReprovada(ErroProducaoAula):
    """Um MP4 saiu e reprovou no perfil `aula`; a peça ficou em `roteiro`."""

    def __init__(self, peca_id: str, mensagem: str, achados: list[dict[str, Any]]) -> None:
        super().__init__(f"{peca_id}: {mensagem}")
        self.peca_id = peca_id
        self.achados = achados


def nome_saida(formato: str, extensao: str) -> str:
    """`aula-16x9.mp4`, `aula-9x16.srt` (CONTRATO-peca: saida/aula-16x9.srt)."""
    return f"aula-{formato.replace(':', 'x')}.{extensao}"


# ---------------------------------------------------------------- entrada


def _texto_ou_none(valor: Any, campo: str) -> str | None:
    if valor is None:
        return None
    if not isinstance(valor, str) or not valor.strip():
        raise ErroEntradaAula(campo, "texto ou null")
    return valor.strip()


def _cena(c: Any, n: int) -> dict[str, Any]:
    if not isinstance(c, dict):
        raise ErroEntradaAula("cenas", f"a cena {n} não é um objeto")
    fora = sorted(set(c) - set(CAMPOS_CENA))
    if fora:
        raise ErroEntradaAula("cenas", f"a cena {n} tem a chave desconhecida '{fora[0]}' (válidas: {', '.join(CAMPOS_CENA)})")
    if not isinstance(c.get("cue"), str) or not c["cue"].strip():
        raise ErroEntradaAula("cenas", f"a cena {n} não tem cue (o nome do marcador [[nome]] do roteiro)")
    modo = c.get("modo") or "cena"
    if modo not in MODOS:
        raise ErroEntradaAula("cenas", f"a cena {n} tem modo {modo!r} (válidos: {', '.join(MODOS)})")
    itens = c.get("itens") or []
    if not isinstance(itens, list) or not all(isinstance(i, str) and i.strip() for i in itens):
        raise ErroEntradaAula("cenas", f"a cena {n}: itens é uma lista de textos")
    cena = {"cue": c["cue"].strip(), "modo": modo, "itens": [i.strip() for i in itens]}
    for chave in ("rotulo", "titulo", "texto", "passo", "fato"):
        cena[chave] = _texto_ou_none(c.get(chave), "cenas")
    slide = c.get("slide")
    if modo == "slide":
        if isinstance(slide, bool) or not isinstance(slide, int) or slide < 1:
            raise ErroEntradaAula("cenas", f"a cena {n} ({cena['cue']}) é de slide e precisa de slide (número a partir de 1)")
    elif slide is not None:
        raise ErroEntradaAula("cenas", f"a cena {n} ({cena['cue']}) tem slide mas não é de modo slide")
    cena["slide"] = slide
    return cena


def ler_entrada(dados: Any) -> dict[str, Any]:
    """Confere a forma da entrada e devolve as chaves do formato, ausente = None (M7)."""
    if not isinstance(dados, dict):
        raise ErroEntradaAula("entrada", "a entrada é um objeto JSON")
    fora = sorted(set(dados) - set(CAMPOS))
    if fora:
        raise ErroEntradaAula(fora[0], f"chave desconhecida (válidas: {', '.join(CAMPOS)})")
    e = {campo: dados.get(campo) for campo in CAMPOS}
    for campo in ("titulo", "roteiro"):
        if not isinstance(e[campo], str) or not e[campo].strip():
            raise ErroEntradaAula(campo, "texto obrigatório")
    e["titulo"] = e["titulo"].strip()
    for campo in ("template", "serie", "porta_voz", "pack", "slug", "oferta", "apresentacao"):
        e[campo] = _texto_ou_none(e[campo], campo)
    try:
        texto, offsets = aula_cues.separar(e["roteiro"])
    except aula_cues.ErroCues as erro:
        raise ErroEntradaAula("roteiro", str(erro)) from None
    if not isinstance(e["cenas"], list) or not e["cenas"]:
        raise ErroEntradaAula("cenas", "lista de cenas, uma por marcador do roteiro ({\"cue\", \"modo\", ...})")
    cenas = [_cena(c, n) for n, c in enumerate(e["cenas"], 1)]
    ordem = sorted(offsets, key=lambda k: offsets[k])
    for c in cenas:
        if c["cue"] not in offsets:
            raise ErroEntradaAula("cenas", f"a cena {c['cue']} não tem marcador [[{c['cue']}]] no roteiro "
                                           f"(marcadores: {', '.join(ordem)})")
    usados = [c["cue"] for c in cenas]
    if len(set(usados)) != len(usados):
        raise ErroEntradaAula("cenas", "duas cenas com o mesmo cue")
    if usados != [k for k in ordem if k in usados]:
        raise ErroEntradaAula("cenas", "as cenas precisam seguir a ordem dos marcadores no roteiro")
    e["cenas"] = cenas
    formatos = e["formatos"] if e["formatos"] is not None else list(FORMATOS)
    if (not isinstance(formatos, list) or not formatos or len(set(formatos)) != len(formatos)
            or any(f not in FORMATOS for f in formatos)):
        raise ErroEntradaAula("formatos", "lista com 16:9 e/ou 9:16, sem repetir")
    e["formatos"] = [f for f in FORMATOS if f in formatos]
    if e["avatar"] is not None and not isinstance(e["avatar"], bool):
        raise ErroEntradaAula("avatar", "true, false ou null")
    tela = e["tela"]
    if tela is not None:
        if not isinstance(tela, dict) or not isinstance(tela.get("janelas"), list) or not tela["janelas"]:
            raise ErroEntradaAula("tela", "objeto com janelas (uma por cue com tela), ou null")
        fora = sorted(set(tela) - {"janelas", "marcas", "cue_final"})
        if fora:
            raise ErroEntradaAula("tela", f"chave desconhecida '{fora[0]}' (válidas: janelas, marcas, cue_final)")
        e["tela"] = {"janelas": tela["janelas"], "marcas": tela.get("marcas"), "cue_final": tela.get("cue_final")}
    de_tela = [c["cue"] for c in cenas if c["modo"] == "tela"]
    if de_tela and e["tela"] is None:
        raise ErroEntradaAula("tela", f"as cenas {', '.join(de_tela)} são de tela e a entrada não traz a gravação")
    if e["tela"] is not None:
        janelas = [j.get("cue") if isinstance(j, dict) else None for j in e["tela"]["janelas"]]
        faltam = [c for c in de_tela if c not in janelas]
        if faltam:
            raise ErroEntradaAula("tela", f"as cenas {', '.join(faltam)} são de tela e não têm janela da gravação")
    if any(c["modo"] == "slide" for c in cenas) and e["apresentacao"] is None:
        raise ErroEntradaAula("apresentacao", "há cena de slide e a entrada não aponta a apresentação")
    conteudo = e["conteudo"] or {}
    if not isinstance(conteudo, dict):
        raise ErroEntradaAula("conteudo", "objeto ou null")
    e["conteudo"] = conteudo
    e["roteiro"] = e["roteiro"].strip()
    e["texto_falado"] = texto
    return e


def _slides_da_apresentacao(raiz: Path, peca_id: str, cenas: list[dict[str, Any]]) -> dict[int, Path]:
    """{número do slide: PNG} dos slides usados pelas cenas, conferidos antes de criar a aula."""
    try:
        deck = modelo.carregar(raiz, peca_id)
    except modelo.ErroPeca as erro:
        raise ErroEntradaAula("apresentacao", str(erro)) from None
    if deck.get("tipo") != "apresentacao":
        raise ErroEntradaAula("apresentacao", f"a peça {peca_id} é {deck.get('tipo')}, não apresentacao")
    pasta = modelo.pasta(raiz, peca_id)
    pngs = [pasta / a["caminho"] for a in deck.get("arquivos") or []
            if a.get("papel") == "slide" and str(a.get("caminho", "")).lower().endswith(".png")]
    usados = {}
    for c in cenas:
        if c["modo"] != "slide":
            continue
        n = c["slide"]
        if n > len(pngs) or not pngs[n - 1].is_file():
            raise ErroEntradaAula("apresentacao", f"a cena {c['cue']} pede o slide {n} e a apresentação {peca_id} "
                                                  f"tem {len(pngs)} PNG de slide (produza a apresentação com --mp4)")
        usados[n] = pngs[n - 1]
    return usados


def _porta_voz(alma: dict[str, Any], pedido: str | None) -> dict[str, Any]:
    vozes = [v for v in alma.get("porta_vozes") or [] if isinstance(v, dict)]
    if pedido:
        achado = next((v for v in vozes if v.get("id") == pedido), None)
        if achado is None:
            raise ErroEntradaAula("porta_voz", f"o porta-voz {pedido} não existe na Alma")
        return achado
    achado = next((v for v in vozes if v.get("principal")), vozes[0] if vozes else None)
    if achado is None:
        raise ErroEntradaAula("porta_voz", "a Alma não tem porta-voz para narrar")
    return achado


# ---------------------------------------------------------------- etapas


def palavras_do_alinhamento(alinhamento: dict[str, list]) -> dict[str, Any]:
    """`{"palavras": [{w, t0, t1}]}` do alinhamento por caractere da narração (tempos do TTS, D-23).

    É a entrada que `legendar.aula` aceita no lugar do whisper: o texto continua sendo o do roteiro.
    """
    palavras, atual, t0, t1 = [], "", 0.0, 0.0
    for ch, ini, fim in zip(alinhamento["characters"], alinhamento["character_start_times_seconds"],
                            alinhamento["character_end_times_seconds"]):
        if ch.isspace():
            if atual:
                palavras.append({"w": atual, "t0": t0, "t1": t1})
                atual = ""
            continue
        if not atual:
            t0 = ini
        atual += ch
        t1 = fim
    if atual:
        palavras.append({"w": atual, "t0": t0, "t1": t1})
    return {"palavras": palavras}


def _gerar_avatar(raiz: Path, porta_voz: str, pedido: bool | None, mp3: Path, destino: Path,
                  opcoes: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """(resultado do provedor, aviso). O provedor sai do ambiente (heygen ou teste), nunca da entrada."""
    if pedido is False:
        return None, None
    try:
        provedor = Verificador(raiz).escolher_provedor("avatar", porta_voz)
    except ErroCapacidade as erro:
        if pedido is True:
            raise
        return None, f"aula sem avatar: {erro}"
    import importlib

    modulo = importlib.import_module(AVATARES[provedor])
    r = modulo.gerar(raiz, relativo(raiz, mp3), porta_voz, relativo(raiz, destino), **opcoes)
    return r, None


def _marcas(raiz: Path, marcas: Any) -> dict[str, float]:
    if marcas is None:
        return {}
    if isinstance(marcas, str):
        return editar_tela.ler_marcas(raiz / instalacao.relativo(raiz, marcas))
    if isinstance(marcas, dict) and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in marcas.values()):
        return {str(k): float(v) for k, v in marcas.items()}
    raise ErroEntradaAula("tela", "marcas é {rótulo: segundos}, o caminho de um marks-rel.json, ou null")


def props_aula(*, alma_props: dict[str, Any], formato: str, serie: str | None, titulo: str,
               cues: dict[str, Any], cenas: list[dict[str, Any]], legendas: list[dict[str, Any]],
               narracao: str | None, avatar: str | None, tela: dict[str, Any] | None,
               imagens: dict[int, str]) -> dict[str, Any]:
    """Props da composição `Aula` (kit-remotion/src/composicoes/Aula): caminhos relativos ao public dir."""
    return {
        "alma": alma_props,
        "formato": formato,
        "serie": serie,
        "titulo": titulo,
        "cues": {"duration": cues["duration"], "cues": cues["cues"]},
        "cenas": [{"cue": c["cue"], "modo": c["modo"], "rotulo": c["rotulo"], "titulo": c["titulo"], "texto": c["texto"],
                   "itens": c["itens"], "passo": c["passo"], "fato": c["fato"],
                   "imagem": imagens.get(c["slide"]) if c["modo"] == "slide" else None} for c in cenas],
        "legendas": legendas,
        "narracao": narracao,
        "avatar": avatar,
        "tela": tela,
    }


# ---------------------------------------------------------------- produção


def produzir(
    raiz: Path | str,
    dados: Any,
    *,
    cache_fontes: Path | str | None = None,
    embarcados: Path | str | None = None,
    origem: str = "skill",
    agente: str | None = None,
    opcoes_narrar: dict[str, Any] | None = None,
    opcoes_avatar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produz uma aula a partir da entrada (ver o módulo)."""
    raiz = Path(raiz)
    e = ler_entrada(dados)
    slides = _slides_da_apresentacao(raiz, e["apresentacao"], e["cenas"]) if e["apresentacao"] else {}
    template = _template(raiz, e["template"], embarcados) if e["template"] else None
    try:
        alma = alma_carregar.carregar(raiz)
    except alma_carregar.ErroAlmaAusente as erro:
        raise ErroProducaoAula(str(erro)) from None
    voz = _porta_voz(alma.dados, e["porta_voz"])
    marcas = _marcas(raiz, e["tela"]["marcas"]) if e["tela"] else {}

    conteudo = {k: e["conteudo"].get(k) for k in ("gancho", "gancho_tipo", "cta", "cta_forma")}
    peca = modelo.criar(raiz, tipo=TIPO, titulo=e["titulo"], formatos=list(e["formatos"]), pack=e["pack"] or "nucleo",
                        slug=e["slug"], status="roteiro", serie=e["serie"],
                        template=template["template_id"] if template else None, porta_voz=voz.get("id"),
                        oferta=e["oferta"], conteudo=conteudo, origem=origem, agente=agente)
    peca_id, pack = peca["peca_id"], peca["pack"]
    pasta = modelo.pasta(raiz, peca_id)
    midia, texto, saida = pasta / "midia", pasta / "texto", pasta / "saida"
    for p in (midia, texto, saida):
        p.mkdir(exist_ok=True)
    trabalho = Path(tempfile.mkdtemp(prefix=f"{peca_id}-aula-"))
    inicio = time.monotonic()
    provedores: dict[str, str] = {}
    avisos: list[str] = []
    etapa = ["roteiro"]
    template_id = template["template_id"] if template else None

    def falhou(detalhe: str) -> None:
        rastro.registrar(raiz, origem=origem, evento="geracao_falhou", resultado="falha", pack=pack, peca_id=peca_id,
                         agente=agente, capacidade=None, provedor=None, detalhe=detalhe[:500],
                         segundos=round(time.monotonic() - inicio, 3), **({"template_id": template_id} if template_id else {}))

    videos: dict[str, Path] = {}
    srts: dict[str, Path] = {}
    resultados: dict[str, Any] = {}
    avatar_r = demo = None
    try:
        arq_roteiro = texto / "roteiro.txt"
        arq_roteiro.write_text(e["roteiro"] + "\n", encoding="utf-8")
        Verificador(raiz).escolher_provedor("renderizar_motion")  # sem render possível, não gasta narração

        # 1. narração, uma vez, com os parâmetros de aula e sem ritmo mínimo (D-40)
        etapa[0] = "narrar"
        narr = narrar_base.narrar(raiz, e["texto_falado"], voz["id"], TIPO, relativo(raiz, midia), **(opcoes_narrar or {}))
        provedores["narrar"] = narr["provedor"]

        # 2. cues dos marcadores, com o hash da narração
        etapa[0] = "cues"
        cues = aula_cues.gerar(raiz, e["roteiro"], relativo(raiz, midia), alinhamento=narr["alinhamento"])

        # 3. legendas 42x2: texto do roteiro nos tempos da narração (D-23)
        etapa[0] = "legendar"
        legendas = legenda_aula.legendas_aula(e["roteiro"], palavras_do_alinhamento(narr["alinhamento"]))
        arquivos.gravar_json(midia / ARQ_LEGENDAS, legendas)
        for formato in e["formatos"]:
            srts[formato] = srt.gravar_srt(legendas, saida / nome_saida(formato, "srt"))
        provedores["legendar"] = PROVEDOR_LEGENDA

        # 4. avatar, do ÁUDIO (D-26)
        etapa[0] = "avatar"
        mp3 = midia / narrar_base.ARQUIVO_AUDIO
        avatar_r, aviso = _gerar_avatar(raiz, voz["id"], e["avatar"], mp3, midia / ARQ_AVATAR, opcoes_avatar or {})
        if aviso:
            avisos.append(aviso)
        if avatar_r is not None:
            provedores["avatar"] = avatar_r["provedor"]
            dur_avatar = ffmpeg.sondar(midia / ARQ_AVATAR)["duracao"] or 0.0
            if abs(dur_avatar - narr["duracao_s"]) > TOLERANCIA_AVATAR_S:
                raise ErroProducaoAula(f"o avatar tem {dur_avatar:.3f} s e a narração {narr['duracao_s']:.3f} s: "
                                       "o PiP não sincroniza; gere o avatar de novo a partir desta narração")

        # 5. tela editada por cues (D-32)
        if e["tela"]:
            etapa[0] = "tela"
            demo = editar_tela.editar(raiz, cues, e["tela"]["janelas"], relativo(raiz, midia / ARQ_DEMO),
                                      relativo(raiz, midia / ARQ_DEMO_JSON), marcas=marcas,
                                      cue_final=e["tela"]["cue_final"])
            provedores["editar_video"] = PROVEDOR_VIDEO

        # 6. render, normalização e verificação por formato
        etapa[0] = "renderizar"
        publico = trabalho / "publico"
        publico.mkdir()
        alma_props, avisos_alma = _reel.props_alma(alma, publico, raiz=raiz, cache_fontes=cache_fontes, porta_voz=voz)
        avisos += avisos_alma
        shutil.copyfile(mp3, publico / narrar_base.ARQUIVO_AUDIO)
        if avatar_r is not None:
            shutil.copyfile(midia / ARQ_AVATAR, publico / ARQ_AVATAR)
        if demo is not None:
            shutil.copyfile(midia / ARQ_DEMO, publico / ARQ_DEMO)
        imagens = {}
        for n, png in slides.items():
            destino = publico / "slides" / f"slide_{n:02d}{png.suffix.lower()}"
            destino.parent.mkdir(exist_ok=True)
            shutil.copyfile(png, destino)
            imagens[n] = relativo(publico, destino)
        projeto, composicao = _projeto_render(template, trabalho)
        for formato in e["formatos"]:
            props = props_aula(alma_props=alma_props, formato=formato, serie=e["serie"], titulo=e["titulo"], cues=cues,
                               cenas=e["cenas"], legendas=legendas, narracao=narrar_base.ARQUIVO_AUDIO,
                               avatar=ARQ_AVATAR if avatar_r is not None else None,
                               tela={"video": ARQ_DEMO, "demo": demo} if demo is not None else None, imagens=imagens)
            etapa[0] = f"renderizar {formato}"
            bruto = remotion.renderizar(composicao, trabalho / nome_saida(formato, "mp4"), props, projeto=projeto,
                                        public_dir=publico)
            etapa[0] = f"normalizar {formato}"
            final = saida / nome_saida(formato, "mp4")
            ffmpeg.normalizar_audio(bruto, final)
            etapa[0] = f"verificar {formato}"
            resultado = verificar.verificar(final, PERFIL, verificar.Artefatos(srt=srts[formato]))
            resultados[formato] = resultado
            videos[formato] = final
            if not resultado["aprovado"]:
                raise ErroVerificacaoReprovada(peca_id, f"verificação reprovada no perfil {PERFIL} ({formato}): "
                                               + "; ".join(a["detalhe"] for a in resultado["achados"]),
                                               resultado["achados"])
        provedores["renderizar_motion"] = PROVEDOR_MOTION
        provedores.setdefault("editar_video", PROVEDOR_VIDEO)
    except ErroVerificacaoReprovada as erro:
        falhou(str(erro))
        raise
    except Exception as erro:  # noqa: BLE001 — falha de produção vira evento, e sobe
        falhou(f"{etapa[0]}: {type(erro).__name__}: {erro}")
        raise
    finally:
        shutil.rmtree(trabalho, ignore_errors=True)

    segundos = round(time.monotonic() - inicio, 3)
    registrar: list[tuple[Path, str, str | None]] = []
    for formato in e["formatos"]:
        registrar += [(videos[formato], "final", formato), (srts[formato], "srt", formato)]
    registrar += [
        (midia / narrar_base.ARQUIVO_AUDIO, "audio", None),
        (midia / narrar_base.ARQUIVO_ALINHAMENTO, "alinhamento", None),
        (midia / aula_cues.ARQUIVO_CUES, "alinhamento", None),
        (midia / ARQ_LEGENDAS, "legenda", None),
        (arq_roteiro, "roteiro", None),
    ]
    if avatar_r is not None:
        registrar.append((midia / ARQ_AVATAR, "avatar", None))
    if demo is not None:
        registrar += [(midia / ARQ_DEMO, "tela", None), (midia / ARQ_DEMO_JSON, "tela", None)]
    for caminho, papel, formato in registrar:
        modelo.registrar_arquivo(raiz, peca_id, caminho, papel=papel, formato=formato)

    def aplicar(atual: dict[str, Any]) -> None:
        atual["conteudo"]["roteiro"] = relativo(pasta, arq_roteiro)
        atual["compoe"] = [e["apresentacao"]] if e["apresentacao"] else []

    modelo._atualizar(raiz, peca_id, aplicar)
    modelo.registrar_producao(raiz, peca_id, capacidades=list(provedores), provedores=provedores, segundos=segundos)
    duracao = round(float(cues["duration"]), 3)
    extras = {"template_id": template_id} if template_id else {}
    rastro.registrar(raiz, origem=origem, evento="geracao_concluida", resultado="ok", pack=pack, peca_id=peca_id,
                     agente=agente, capacidade="renderizar_motion", provedor=PROVEDOR_MOTION,
                     detalhe=f"aula de {str(round(duracao, 1)).replace('.', ',')} s em {', '.join(e['formatos'])} "
                             f"aprovada no perfil {PERFIL}",
                     arquivos=[c for c, _, _ in registrar], segundos=segundos, **extras)
    final_peca = modelo.mudar_status(raiz, peca_id, "produzida", origem=origem, agente=agente)
    return {
        "peca_id": peca_id,
        "status": final_peca["status"],
        "tipo": TIPO,
        "template": template_id,
        "pasta": relativo(raiz, pasta),
        "videos": {f: relativo(raiz, v) for f, v in videos.items()},
        "srts": {f: relativo(raiz, s) for f, s in srts.items()},
        "duracao": duracao,
        "cues": cues["cues"],
        "compoe": final_peca["compoe"],
        "arquivos": final_peca["arquivos"],
        "narracao": {"provedor": narr["provedor"], "duracao_s": narr["duracao_s"], "palavras": narr["palavras"],
                     "fator_ritmo": narr["fator_ritmo"]},
        "avatar": {"provedor": avatar_r["provedor"], "duracao_s": avatar_r["duracao_s"]} if avatar_r else None,
        "tela": {"segmentos": len(demo["segmentos"]), "duracao": demo["duracao"]} if demo else None,
        "legendas": len(legendas),
        "verificacao": resultados,
        "segundos": segundos,
        "avisos": avisos,
    }


# ---------------------------------------------------------------- template


def _template(raiz: Path, template_id: str, embarcados: Path | str | None) -> dict[str, Any]:
    """Manifesto e pasta do template de aula (galeria local antes da embarcada), conferidos antes da peça."""
    base_emb = Path(embarcados) if embarcados is not None else galeria_local.pasta_embarcados()
    itens = galeria_local.listar(raiz, embarcados=base_emb)
    item = next((i for i in itens if i["template_id"] == template_id), None)
    if item is None:
        de_aula = sorted(i["template_id"] for i in itens if isinstance(i["dados"], dict) and i["dados"].get("tipo") == TIPO)
        raise ErroEntradaAula("template", f"template '{template_id}' não encontrado (de aula: {', '.join(de_aula) or 'nenhum'})")
    if item["erro"] is not None:
        raise ErroEntradaAula("template", f"template '{template_id}' fora do contrato: {item['erro']}")
    dados = item["dados"]
    if dados.get("tipo") != TIPO or dados.get("motor") != "remotion":
        raise ErroEntradaAula("template", f"template '{template_id}' é {dados.get('tipo')}/{dados.get('motor')}, não aula/remotion")
    if dados.get("status") in galeria_local.STATUS_FORA_DA_BUSCA:
        raise ErroEntradaAula("template", f"template '{template_id}' está {dados['status']}")
    versao = (dados.get("versoes") or {}).get("remotion") or remotion.VERSAO_KIT
    if versao != remotion.VERSAO_KIT:
        raise ErroEntradaAula("template", f"o template pede o Remotion {versao}; o render de template roda sobre o kit "
                                          f"({remotion.VERSAO_KIT})")
    pasta = Path(raiz) / item["caminho"] if item["galeria"] == "local" else base_emb.parent / item["caminho"]
    for nome in ("package.json", "src/Composicao.tsx"):
        if not (pasta / nome).is_file():
            raise ErroEntradaAula("template", f"template '{template_id}' sem {nome}")
    return {**dados, "_pasta": pasta}


# O que o template de aula recebe de @expxmedia/template além dos módulos do kit: a composição Aula (layouts
# calibrados, tela, avatar, legenda) e as peças de desenho dela.
_EXPORTS_AULA = (
    'export * from {layouts};\n'
    'export {{ Aula, CenaPadrao, Pop, Rise, Janela, Etiqueta, cameraX, quadrosDaAula, EXEMPLO_AULA, '
    'composicao as composicaoAula }} from {indice};\n'
    'export type {{ PropsAula, Cena as CenaAula, DesenharCena, Cues, Legenda, Demo, Segmento }} from {indice};\n'
)


def _projeto_render(template: dict[str, Any] | None, trabalho: Path) -> tuple[Path | None, str]:
    """(projeto Remotion, composição): sem template, a composição `Aula` do próprio kit.

    Com template, o projeto temporário do reel (`producao.reel.preparar_projeto`: pacotes do kit por link e o
    `src/` do template como composição), com `@expxmedia/template` exportando também a composição Aula.
    """
    if template is None:
        return None, COMPOSICAO
    composicao = _reel._id_composicao(template["template_id"])
    projeto = _reel.preparar_projeto(template["_pasta"], trabalho / "projeto", composicao)
    aula_kit = remotion.KIT / "src" / "composicoes" / COMPOSICAO
    indice = projeto / "node_modules" / "@expxmedia" / "template" / "index.ts"
    with open(indice, "a", encoding="utf-8") as f:
        f.write(_EXPORTS_AULA.format(layouts=json.dumps((aula_kit / "layouts").as_posix()),
                                     indice=json.dumps((aula_kit / "index").as_posix())))
    return projeto, composicao
