"""Produção do reel a partir de página capturada (D-38).

A entrada é um objeto JSON:

    {
      "url": "https://exemplo.example/docs",           (ou "captura": pasta de uma captura já feita)
      "titulo": "...",
      "roteiro": "texto que vai ser narrado (130 a 180 palavras)",
      "cta": "PALAVRA",                                 a palavra do CTA (o cta.txt da origem)
      "impacto": ["ATÉ TRÊS", "LINHAS CURTAS"],         cartão de impacto dos 2,5 s iniciais
      "card_final": ["<copy com {cta}>", "..."],        linhas do card final do CTA
      "selo": "<copy com {cta}>" | null,                selo do CTA acima da legenda (null: sem selo)
      "legenda": "texto do post" | null,
      "porta_voz": "id" | null,                         padrão: o principal da Alma
      "conteudo": {"gancho", "gancho_tipo", "cta_forma"} (opcional),
      "ocultar": ["seletor", ...] (opcional),           ajustes da captura
      "serie", "pack", "oferta", "slug"                 (opcionais)
    }

O caminho, na ordem (origem: Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md e os scripts de
`Instragram-Videos/pipeline/`):

1. confere a entrada (erro cita o campo; nada é criado) e cria a peça em `roteiro`;
2. **captura** a página (`captura.pagina`, Playwright) em `midia/`: tira, faixas, `site.md` (fonte) e
   `captura.json`. Com `captura` (pasta já capturada), copia de lá; se a pasta tiver a abertura que
   `produzir abertura` gerou (`abertura.mp4` + `abertura.json`), ela vem junto e a montagem a põe como
   FUNDO dos segundos iniciais (narração desde 0, duração inalterada; origem:
   Instragram-Videos/pipeline/compose.py:38-40), e a peça registra a capacidade `video_ia`;
3. **gate do roteirista** (`revisar.roteiro`): reprovado, nada é narrado — `geracao_falhou` no rastro e a
   peça fica em `roteiro`;
4. **narra uma vez** (`narrar`, o provedor que o `.env` escolher): `midia/narracao.mp3` e
   `midia/alinhamento.json`, no espaço do roteiro;
5. **legenda** (`legendar.reel`): `midia/caps/`, `caps.txt`, `legendas.json`, e o SRT dos blocos;
6. **monta** (`video.montar_pagina`): rolagem, cartão, selo, legenda, narração e a mistura normalizada
   em duas passadas, em `saida/final.mp4`;
7. **verifica** no perfil `reel_pagina` (as 11 checagens); reprovado, `geracao_falhou` e a peça fica em
   `roteiro`;
8. registra arquivos, produção e `geracao_concluida`, e passa a peça para `produzida`.

Uso:

    from expxmedia.producao import reel_pagina
    r = reel_pagina.produzir(raiz, entrada)   # {"peca_id", "status", "pasta", "arquivos", "verificacao", ...}
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from expxmedia.alma import carregar as alma_carregar
from expxmedia.ambiente.verificar import Verificador
from expxmedia.captura import pagina
from expxmedia.legendar import reel as legenda_reel
from expxmedia.legendar import srt
from expxmedia.narrar import base as narrar_base
from expxmedia.nucleo import arquivos, rastro
from expxmedia.nucleo.raiz import absoluto, relativo
from expxmedia.peca import modelo
from expxmedia.revisar import roteiro as gate_roteiro
from expxmedia.video import montar_pagina, verificar

__all__ = [
    "ErroProducaoReel",
    "ErroEntradaReel",
    "ErroRoteiroReprovado",
    "ErroVerificacaoReprovada",
    "CAMPOS",
    "PERFIL",
    "ler_entrada",
    "produzir",
]

TIPO, FORMATO, PERFIL = "reel", "9:16", "reel_pagina"
CAMPOS = ("url", "captura", "titulo", "roteiro", "cta", "impacto", "card_final", "selo", "legenda", "porta_voz",
          "conteudo", "ocultar", "serie", "pack", "oferta", "slug")
PROVEDOR_LEGENDA, PROVEDOR_VIDEO, PROVEDOR_CAPTURA = "local", "ffmpeg", "playwright"
PROVEDOR_ABERTURA = "higgsfield"
# o que `producao.abertura.gerar` deixa na pasta e a montagem usa (o clipe, o marcador e o prompt)
ARQUIVOS_ABERTURA = ("abertura.mp4", "abertura.json", "abertura.txt")


class ErroProducaoReel(RuntimeError):
    """A produção do reel não terminou."""


class ErroEntradaReel(ValueError):
    """Entrada fora do formato; `campo` diz qual. Nada foi criado."""

    def __init__(self, campo: str, mensagem: str) -> None:
        super().__init__(f"campo '{campo}': {mensagem}")
        self.campo = campo


class _ErroComPeca(ErroProducaoReel):
    def __init__(self, peca_id: str, mensagem: str, achados: list[dict[str, Any]]) -> None:
        super().__init__(f"{peca_id}: {mensagem}")
        self.peca_id = peca_id
        self.achados = achados


class ErroRoteiroReprovado(_ErroComPeca):
    """O gate do roteirista reprovou: nada foi narrado; a peça ficou em `roteiro`."""


class ErroVerificacaoReprovada(_ErroComPeca):
    """O MP4 saiu e reprovou na verificação de entrega; a peça ficou em `roteiro`."""


# ---------------------------------------------------------------- entrada


def _texto(entrada: dict[str, Any], campo: str, obrigatorio: bool = True) -> None:
    valor = entrada[campo]
    if valor is None and not obrigatorio:
        return
    if not isinstance(valor, str) or not valor.strip():
        raise ErroEntradaReel(campo, "texto obrigatório" if obrigatorio else "texto ou null")


def ler_entrada(dados: Any) -> dict[str, Any]:
    """Confere a forma da entrada e devolve as chaves do formato, ausente = None."""
    if not isinstance(dados, dict):
        raise ErroEntradaReel("entrada", "a entrada é um objeto JSON")
    extras = sorted(set(dados) - set(CAMPOS))
    if extras:
        raise ErroEntradaReel(extras[0], f"chave desconhecida (válidas: {', '.join(CAMPOS)})")
    e = {campo: dados.get(campo) for campo in CAMPOS}
    if (e["url"] is None) == (e["captura"] is None):
        raise ErroEntradaReel("url", "informe a url da página ou a pasta de uma captura já feita (captura), uma das duas")
    _texto(e, "url", obrigatorio=False)
    _texto(e, "captura", obrigatorio=False)
    for campo in ("titulo", "roteiro", "cta"):
        _texto(e, campo)
    if isinstance(e["impacto"], str):
        e["impacto"] = e["impacto"].strip().splitlines()
    if not isinstance(e["impacto"], list) or not all(isinstance(l, str) for l in e["impacto"]) \
            or not [l for l in e["impacto"] if l.strip()]:
        raise ErroEntradaReel("impacto", "lista de 1 a 3 linhas curtas do cartão de impacto")
    e["impacto"] = [l.strip() for l in e["impacto"] if l.strip()]
    if len(e["impacto"]) > montar_pagina.MAX_LINHAS_IMPACTO:
        raise ErroEntradaReel("impacto", f"{len(e['impacto'])} linhas; o teto é {montar_pagina.MAX_LINHAS_IMPACTO}")
    card = e["card_final"]
    if not isinstance(card, list) or not card or not all(isinstance(l, str) and l.strip() for l in card) \
            or not any("{cta}" in l for l in card):
        raise ErroEntradaReel("card_final", "lista de linhas do card final, uma delas com {cta}")
    if e["selo"] is not None and (not isinstance(e["selo"], str) or "{cta}" not in e["selo"]):
        raise ErroEntradaReel("selo", "texto com {cta} ou null")
    for campo in ("legenda", "porta_voz", "serie", "pack", "oferta", "slug"):
        _texto(e, campo, obrigatorio=False)
    if e["ocultar"] is not None and (not isinstance(e["ocultar"], list) or not all(isinstance(s, str) for s in e["ocultar"])):
        raise ErroEntradaReel("ocultar", "lista de seletores ou null")
    conteudo = e["conteudo"] or {}
    if not isinstance(conteudo, dict):
        raise ErroEntradaReel("conteudo", "objeto ou null")
    fora = sorted(set(conteudo) - {"gancho", "gancho_tipo", "cta_forma"})
    if fora:
        raise ErroEntradaReel("conteudo", f"chave '{fora[0]}' fora do contrato (gancho, gancho_tipo, cta_forma)")
    if conteudo.get("gancho_tipo") is not None and conteudo["gancho_tipo"] not in modelo.GANCHO_TIPOS:
        raise ErroEntradaReel("conteudo", f"gancho_tipo inválido: {conteudo['gancho_tipo']!r}")
    if conteudo.get("cta_forma") is not None and conteudo["cta_forma"] not in modelo.CTA_FORMAS:
        raise ErroEntradaReel("conteudo", f"cta_forma inválido: {conteudo['cta_forma']!r}")
    e["conteudo"] = conteudo
    e["roteiro"] = e["roteiro"].strip()
    e["cta"] = e["cta"].strip().upper()
    return e


def _porta_voz(alma: dict[str, Any], pedido: str | None) -> dict[str, Any]:
    vozes = [v for v in alma.get("porta_vozes") or [] if isinstance(v, dict)]
    if pedido:
        achado = next((v for v in vozes if v.get("id") == pedido), None)
        if achado is None:
            raise ErroEntradaReel("porta_voz", f"o porta-voz {pedido} não existe na Alma")
        return achado
    achado = next((v for v in vozes if v.get("principal")), vozes[0] if vozes else None)
    if achado is None:
        raise ErroEntradaReel("porta_voz", "a Alma não tem porta-voz para narrar")
    return achado


# ---------------------------------------------------------------- produção


def produzir(
    raiz: Path | str,
    dados: Any,
    *,
    cache_fontes: Path | str | None = None,
    origem: str = "skill",
    agente: str | None = None,
    opcoes_narrar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produz um reel de página a partir da entrada (ver o módulo)."""
    raiz = Path(raiz)
    e = ler_entrada(dados)
    try:
        alma = alma_carregar.carregar(raiz)
    except alma_carregar.ErroAlmaAusente as erro:
        raise ErroProducaoReel(str(erro)) from None
    voz_registro = _porta_voz(alma.dados, e["porta_voz"])
    captura_existente = None
    if e["captura"] is not None:
        captura_existente = absoluto(raiz, e["captura"])
        faltam = [n for n in ("tira.png", "captura.json", "site.md") if not (captura_existente / n).is_file()]
        if faltam:
            raise ErroEntradaReel("captura", f"a pasta da captura não tem {', '.join(faltam)}")

    conteudo = {"gancho": e["conteudo"].get("gancho"), "gancho_tipo": e["conteudo"].get("gancho_tipo"),
                "cta": e["cta"], "cta_forma": e["conteudo"].get("cta_forma")}
    peca = modelo.criar(raiz, tipo=TIPO, titulo=e["titulo"], formatos=[FORMATO], pack=e["pack"] or "nucleo",
                        slug=e["slug"], status="roteiro", serie=e["serie"], porta_voz=voz_registro.get("id"),
                        oferta=e["oferta"], conteudo=conteudo, origem=origem, agente=agente)
    peca_id, pack = peca["peca_id"], peca["pack"]
    pasta = modelo.pasta(raiz, peca_id)
    midia, texto, saida = pasta / "midia", pasta / "texto", pasta / "saida"
    for p in (midia, texto, saida):
        p.mkdir(exist_ok=True)
    inicio = time.monotonic()
    provedores: dict[str, str] = {}
    com_abertura = False
    etapa = ["captura"]

    def falhou(detalhe: str) -> None:
        rastro.registrar(raiz, origem=origem, evento="geracao_falhou", resultado="falha", pack=pack, peca_id=peca_id,
                         agente=agente, capacidade=None, provedor=None, detalhe=detalhe[:500],
                         segundos=round(time.monotonic() - inicio, 3))

    try:
        # 1. captura
        if captura_existente is None:
            Verificador(raiz).escolher_provedor("capturar_pagina")
            cap = pagina.capturar(e["url"], midia, ajustes=e["ocultar"] or None, raiz=raiz)
        else:
            for nome in ("tira.png", "captura.json", "site.md"):
                shutil.copyfile(captura_existente / nome, midia / nome)
            cap = arquivos.ler_json(midia / "captura.json")
            if (captura_existente / "abertura.mp4").is_file() and (captura_existente / "abertura.json").is_file():
                for nome in ARQUIVOS_ABERTURA:
                    if (captura_existente / nome).is_file():
                        shutil.copyfile(captura_existente / nome, midia / nome)
                com_abertura = True
        provedores["capturar_pagina"] = PROVEDOR_CAPTURA

        # 2. gate do roteirista, antes de narrar
        etapa[0] = "roteiro"
        arq_roteiro = texto / "roteiro.txt"
        arq_roteiro.write_text(e["roteiro"] + "\n", encoding="utf-8")
        gate = gate_roteiro.revisar_roteiro(e["roteiro"], e["cta"])
        if not gate["aprovado"]:
            raise ErroRoteiroReprovado(peca_id, "roteiro reprovado pelo gate: "
                                       + "; ".join(a["detalhe"] for a in gate["achados"]), gate["achados"])

        # 3. narração, uma vez
        etapa[0] = "narrar"
        narr = narrar_base.narrar(raiz, e["roteiro"], voz_registro["id"], TIPO, relativo(raiz, midia),
                                  **(opcoes_narrar or {}))
        provedores["narrar"] = narr["provedor"]

        # 4. legenda
        etapa[0] = "legendar"
        estilo_leg, avisos = legenda_reel.estilo_da_alma(alma, raiz=raiz, cache=cache_fontes)
        pronuncia = (voz_registro.get("voz") or {}).get("pronuncia") if isinstance(voz_registro.get("voz"), dict) else None
        leg = legenda_reel.legendar_reel(narr["alinhamento"], e["roteiro"], midia, estilo=estilo_leg, cta=e["cta"],
                                         termos_multi=legenda_reel.termos_multi(pronuncia),
                                         card_final=tuple(e["card_final"]))
        avisos += [a["detalhe"] for a in leg["achados"]]
        arq_srt = saida / "final.srt"
        blocos = [{"start": ini, "end": fim, "lines": [txt]}
                  for (_, ini, fim), txt in zip(leg["entradas"], leg["textos"])]
        srt.gravar_srt(blocos, arq_srt)
        provedores["legendar"] = PROVEDOR_LEGENDA

        # 5. montagem e mistura normalizada
        etapa[0] = "montar"
        estilo_mont, avisos_mont = montar_pagina.estilo_da_alma(alma, raiz=raiz, cache=cache_fontes)
        final = saida / "final.mp4"
        mont = montar_pagina.montar(midia, estilo=estilo_mont, saida=final, tira=midia / "tira.png",
                                    captura=midia / "captura.json", impacto=e["impacto"], selo=e["selo"],
                                    sem_selo=e["selo"] is None, raiz=raiz)
        avisos += [a for a in avisos_mont if a not in avisos] + mont["avisos"]
        if com_abertura and mont["abertura"] is None:
            raise ErroProducaoReel("a captura trouxe a abertura, mas a montagem não a pôs no vídeo")
        if com_abertura:
            provedores["video_ia"] = PROVEDOR_ABERTURA
        provedores["editar_video"] = PROVEDOR_VIDEO

        # 6. verificação de entrega
        etapa[0] = "verificar"
        art = verificar.Artefatos(caps_txt=midia / "caps.txt", legendas=midia / "legendas.json",
                                  alinhamento=midia / narrar_base.ARQUIVO_ALINHAMENTO, roteiro=arq_roteiro)
        resultado = verificar.verificar(final, PERFIL, art)
        if not resultado["aprovado"]:
            raise ErroVerificacaoReprovada(peca_id, "verificação reprovada no perfil reel_pagina: "
                                           + "; ".join(a["detalhe"] for a in resultado["achados"]),
                                           resultado["achados"])
    except _ErroComPeca as erro:
        falhou(str(erro))
        raise
    except Exception as erro:  # noqa: BLE001 — falha de produção vira evento, e sobe
        falhou(f"{etapa[0]}: {type(erro).__name__}: {erro}")
        raise

    segundos = round(time.monotonic() - inicio, 3)
    registrar = [
        (final, "final", FORMATO),
        (arq_srt, "srt", FORMATO),
        (midia / "legendas.json", "legenda", None),
        (midia / narrar_base.ARQUIVO_AUDIO, "audio", None),
        (midia / narrar_base.ARQUIVO_ALINHAMENTO, "alinhamento", None),
        (arq_roteiro, "roteiro", None),
        (midia / "site.md", "fonte", None),
    ]
    if com_abertura:
        # o contrato não tem papel próprio de abertura: é material-fonte da montagem, como o site.md
        registrar += [(midia / "abertura.mp4", "fonte", None), (midia / "abertura.json", "fonte", None)]
    legenda_post = None
    if e["legenda"]:
        legenda_post = texto / "legenda.txt"
        legenda_post.write_text(e["legenda"].strip() + "\n", encoding="utf-8")
        registrar.append((legenda_post, "legenda", None))
    for caminho, papel, formato in registrar:
        modelo.registrar_arquivo(raiz, peca_id, caminho, papel=papel, formato=formato)

    def aplicar(atual: dict[str, Any]) -> None:
        atual["conteudo"]["roteiro"] = relativo(pasta, arq_roteiro)
        if legenda_post is not None:
            atual["conteudo"]["legenda"] = relativo(pasta, legenda_post)

    modelo._atualizar(raiz, peca_id, aplicar)
    capacidades = list(provedores)
    modelo.registrar_producao(raiz, peca_id, capacidades=capacidades, provedores=provedores, segundos=segundos)
    rastro.registrar(raiz, origem=origem, evento="geracao_concluida", resultado="ok", pack=pack, peca_id=peca_id,
                     agente=agente, capacidade="editar_video", provedor=PROVEDOR_VIDEO,
                     detalhe=f"reel de página de {str(round(mont['duracao'], 1)).replace('.', ',')} s aprovado no perfil "
                             f"{PERFIL}", arquivos=[c for c, _, _ in registrar], segundos=segundos)
    final_peca = modelo.mudar_status(raiz, peca_id, "produzida", origem=origem, agente=agente)
    return {
        "peca_id": peca_id,
        "status": final_peca["status"],
        "tipo": TIPO,
        "pasta": relativo(raiz, pasta),
        "video": relativo(raiz, final),
        "duracao": mont["duracao"],
        "arquivos": final_peca["arquivos"],
        "captura": {"url": cap.get("url"), "secoes": len(cap.get("secoes") or []), "strip_h": cap.get("strip_h")},
        "narracao": {"provedor": narr["provedor"], "duracao_s": narr["duracao_s"], "palavras": narr["palavras"]},
        "legenda": {"blocos": leg["blocos"], "palavras_por_bloco": leg["palavras_por_bloco"], "cta": leg["cta"]},
        "montagem": {"rolagem": mont["rolagem"], "cartao": mont["cartao"], "selo": mont["selo"],
                     "abertura": mont["abertura"], "loudness": mont["loudness"]},
        "verificacao": resultado,
        "segundos": segundos,
        "avisos": avisos,
    }
