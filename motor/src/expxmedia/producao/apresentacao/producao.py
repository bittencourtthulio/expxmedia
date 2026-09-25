"""Produção de apresentação: HTML navegável (o `final`) e, com `mp4=True`, o MP4 e um PNG por slide.

A entrada é um objeto JSON:

    {
      "template": "apresentacao-padrao-4c7e2a",       (opcional: sem ele, o embarcado padrão)
      "deck": {"titulo": ..., "tema": ..., "slides": [...]},   (schema em deck.py)
      "ativos": "caminho/relativo/a/raiz" | null,     (pasta com as imagens citadas pelo deck)
      "conteudo": {"gancho", "gancho_tipo", "cta", "cta_forma"} | null,
      "serie": null, "pack": "nucleo", "porta_voz": null, "oferta": null, "slug": null
    }

O caminho, na ordem:

1. confere a entrada e acha o template (galeria local antes da embarcada); o deck é validado com a
   Alma (tetos da origem, contraste da cor do tema sobre o fundo da Alma) **antes** de criar a
   peça: deck inválido não cria pasta nem evento;
2. cria a peça em `roteiro`, grava o deck em `texto/deck.json` (`roteiro`) e gera
   `saida/apresentacao.html` (`final`, 16:9) com o CSS do template;
3. com `mp4`, renderiza `saida/apresentacao.mp4` (`final`, 16:9) e `slides/slide_NN.png`
   (`slide`, 16:9) pelo kit Remotion;
4. registra slides, produção e `geracao_concluida` e passa a peça para `produzida`. Falha no
   caminho registra `geracao_falhou` e a peça fica em `roteiro` (falha não é status).

`slides[].arquivo` aponta para o PNG do slide quando há render, e para o slide dentro do palco
(`saida/apresentacao.html#N`) quando a apresentação é só HTML.

O score de pauta da origem não é portado (D-48): é curadoria do pack.

Uso:

    from expxmedia.producao.apresentacao import producao
    r = producao.produzir(raiz, entrada)            # só o HTML
    r = producao.produzir(raiz, entrada, mp4=True)  # HTML + MP4 + PNG por slide
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from expxmedia.alma import carregar as alma_carregar
from expxmedia.alma import fontes as _fontes
from expxmedia.nucleo import arquivos as _arquivos
from expxmedia.nucleo import rastro
from expxmedia.nucleo.raiz import relativo
from expxmedia.peca import modelo
from expxmedia.producao import post as _post
from expxmedia.producao.apresentacao import deck as _deck
from expxmedia.producao.apresentacao import palco as _palco
from expxmedia.producao.apresentacao import render as _render

__all__ = [
    "TIPO",
    "FORMATO",
    "TEMPLATE_PADRAO",
    "CAMPOS",
    "ErroProducao",
    "ErroEntradaProducao",
    "ErroDeckInvalido",
    "ler_entrada",
    "produzir",
]

TIPO = "apresentacao"
FORMATO = "16:9"
TEMPLATE_PADRAO = "apresentacao-padrao-4c7e2a"
CAMPOS = ("template", "deck", "ativos", "conteudo", "serie", "pack", "porta_voz", "oferta", "slug")
NOME_HTML = "apresentacao.html"
CAPACIDADE_MOTION = "renderizar_motion"
PROVEDOR_MOTION = "remotion"

ErroProducao = _post.ErroProducao
ErroEntradaProducao = _post.ErroEntradaProducao


class ErroDeckInvalido(ErroProducao):
    """O deck não cumpre o schema; nada foi criado. `achados` traz todos de uma vez."""

    def __init__(self, achados: list[dict[str, str]]) -> None:
        super().__init__("deck inválido: " + "; ".join(f"{a['campo']}: {a['detalhe']}" for a in achados))
        self.achados = list(achados)


def ler_entrada(dados: Any) -> dict[str, Any]:
    """Confere a forma da entrada e devolve as chaves do formato, ausente = None."""
    if not isinstance(dados, dict):
        raise ErroEntradaProducao("entrada", "a entrada é um objeto JSON")
    extras = sorted(set(dados) - set(CAMPOS))
    if extras:
        raise ErroEntradaProducao(extras[0], f"chave desconhecida (válidas: {', '.join(CAMPOS)})")
    entrada = {campo: dados.get(campo) for campo in CAMPOS}
    if not isinstance(entrada["deck"], dict):
        raise ErroEntradaProducao("deck", "objeto com titulo, tema e slides")
    if entrada["template"] is not None and (not isinstance(entrada["template"], str) or not entrada["template"].strip()):
        raise ErroEntradaProducao("template", "texto ou null (null usa o template embarcado padrão)")
    if entrada["ativos"] is not None and (not isinstance(entrada["ativos"], str) or not entrada["ativos"].strip()
                                          or Path(entrada["ativos"]).is_absolute()):
        raise ErroEntradaProducao("ativos", "caminho relativo à raiz da instalação, ou null (M9)")
    if entrada["conteudo"] is not None and not isinstance(entrada["conteudo"], dict):
        raise ErroEntradaProducao("conteudo", "objeto ou null")
    conteudo = entrada["conteudo"] or {}
    fora = sorted(set(conteudo) - {"gancho", "gancho_tipo", "cta", "cta_forma"})
    if fora:
        raise ErroEntradaProducao("conteudo", f"chave '{fora[0]}' fora do contrato (gancho, gancho_tipo, cta, cta_forma)")
    if conteudo.get("gancho_tipo") is not None and conteudo["gancho_tipo"] not in modelo.GANCHO_TIPOS:
        raise ErroEntradaProducao("conteudo", f"gancho_tipo inválido: {conteudo['gancho_tipo']!r}")
    if conteudo.get("cta_forma") is not None and conteudo["cta_forma"] not in modelo.CTA_FORMAS:
        raise ErroEntradaProducao("conteudo", f"cta_forma inválido: {conteudo['cta_forma']!r}")
    for campo in ("serie", "pack", "porta_voz", "oferta", "slug"):
        if entrada[campo] is not None and (not isinstance(entrada[campo], str) or not entrada[campo].strip()):
            raise ErroEntradaProducao(campo, "texto ou null")
    return entrada


def _sem_b(texto: Any) -> str | None:
    return re.sub(r"</?b>", "", texto).strip() if isinstance(texto, str) and texto.strip() else None


def _conteudo(entrada: dict[str, Any], completo: dict[str, Any]) -> dict[str, Any]:
    """O essencial do texto para a análise: o que a entrada trouxe; o que faltar sai do próprio deck."""
    conteudo = dict(entrada["conteudo"] or {})
    slides = completo["slides"]
    if conteudo.get("gancho") is None:
        conteudo["gancho"] = _sem_b(slides[0].get("titulo"))
    cta = slides[-1]
    if conteudo.get("cta") is None:
        conteudo["cta"] = _sem_b(cta.get("titulo"))
    if conteudo.get("cta_forma") is None and conteudo["cta"] is not None:
        conteudo["cta_forma"] = "link" if cta.get("url") else "nenhum"
    return conteudo


def produzir(
    raiz: Path | str,
    dados: Any,
    *,
    mp4: bool = False,
    embarcados: Path | str | None = None,
    cache_fontes: Path | str | None = None,
    url_fontes: str = _fontes.URL_GOOGLE_FONTS,
    frames_por_slide: int = _render.FRAMES_POR_SLIDE,
    opcoes_runner: dict[str, Any] | None = None,
    origem: str = "skill",
    agente: str | None = None,
) -> dict[str, Any]:
    """Produz a apresentação (ver o módulo). Devolve {peca_id, status, pasta, slides, arquivos, avisos...}."""
    raiz = Path(raiz)
    entrada = ler_entrada(dados)
    template_id = (entrada["template"] or TEMPLATE_PADRAO).strip()
    pasta_template = _post.achar_template(raiz, template_id, TIPO, embarcados)
    css_template = (pasta_template / "template.css").read_text(encoding="utf-8") if (pasta_template / "template.css").is_file() else ""
    try:
        alma = alma_carregar.carregar(raiz)
    except alma_carregar.ErroAlmaAusente as erro:
        raise ErroProducao(str(erro)) from None
    d = entrada["deck"]
    achados = _deck.validar(d, alma=alma)
    if achados:
        raise ErroDeckInvalido(achados)
    ativos = (raiz / entrada["ativos"]).resolve() if entrada["ativos"] else None
    if ativos is not None and raiz.resolve() not in ativos.parents:
        raise ErroEntradaProducao("ativos", "a pasta de ativos fica dentro da instalação")
    completo, _ = _deck.completar_cta(d, alma)

    peca = modelo.criar(
        raiz, tipo=TIPO, titulo=d["titulo"], formatos=[FORMATO], pack=entrada["pack"] or "nucleo", slug=entrada["slug"],
        status="roteiro", serie=entrada["serie"], template=template_id, porta_voz=entrada["porta_voz"],
        oferta=entrada["oferta"], conteudo=_conteudo(entrada, completo), origem=origem, agente=agente,
    )
    peca_id, pack = peca["peca_id"], peca["pack"]
    pasta = modelo.pasta(raiz, peca_id)
    capacidades: list[str] = []
    provedores: dict[str, str] = {}
    inicio = time.monotonic()
    try:
        arq_deck = pasta / "texto" / "deck.json"
        _arquivos.gravar_json(arq_deck, d)
        palco = _palco.gerar(d, alma, pasta / "saida" / NOME_HTML, raiz=raiz, ativos=ativos, cache_fontes=cache_fontes,
                             url_fontes=url_fontes, css_template=css_template)
        avisos = list(palco["avisos"])
        video = None
        if mp4:
            capacidades.append(CAPACIDADE_MOTION)
            provedores[CAPACIDADE_MOTION] = PROVEDOR_MOTION
            video = _render.renderizar(d, alma, pasta / "saida", raiz=raiz, ativos=ativos, pasta_pngs=pasta / "slides",
                                       cache_fontes=cache_fontes, url_fontes=url_fontes, frames_por_slide=frames_por_slide,
                                       opcoes_runner=opcoes_runner)
            avisos += [a for a in video["avisos"] if a not in avisos]
    except Exception as erro:  # noqa: BLE001 — falha de produção vira evento, e sobe
        rastro.registrar(raiz, origem=origem, evento="geracao_falhou", resultado="falha", pack=pack, peca_id=peca_id,
                         agente=agente, capacidade=capacidades[-1] if capacidades else None,
                         provedor=provedores.get(capacidades[-1]) if capacidades else None,
                         detalhe=f"{type(erro).__name__}: {erro}"[:500], segundos=round(time.monotonic() - inicio, 3),
                         template_id=template_id)
        raise
    segundos = round(time.monotonic() - inicio, 3)

    modelo.registrar_arquivo(raiz, peca_id, palco["arquivo"], papel="final", formato=FORMATO)
    modelo.registrar_arquivo(raiz, peca_id, arq_deck, papel="roteiro", formato=None)
    gerados = [palco["arquivo"], arq_deck]
    html_rel = relativo(pasta, palco["arquivo"])
    slides = []
    for n, s in enumerate(d["slides"], 1):
        arquivo = f"{html_rel}#{n}"
        if video is not None:
            arquivo = relativo(pasta, video["pngs"][n - 1])
        slides.append({"n": n, "kind": s["tipo"], "midia": "imagem", "arquivo": arquivo, "duracao_s": None})
    if video is not None:
        modelo.registrar_arquivo(raiz, peca_id, video["mp4"], papel="final", formato=FORMATO)
        gerados.append(video["mp4"])
        for png in video["pngs"]:
            modelo.registrar_arquivo(raiz, peca_id, png, papel="slide", formato=FORMATO)
            gerados.append(png)

    def aplicar(atual: dict[str, Any]) -> None:
        atual["slides"] = slides

    modelo._atualizar(raiz, peca_id, aplicar)
    modelo.registrar_producao(raiz, peca_id, capacidades=capacidades, provedores=provedores, segundos=segundos)
    feito = "HTML" + (", MP4 e PNG por slide" if video is not None else "")
    rastro.registrar(raiz, origem=origem, evento="geracao_concluida", resultado="ok", pack=pack, peca_id=peca_id,
                     agente=agente, capacidade=capacidades[-1] if capacidades else None,
                     provedor=provedores.get(capacidades[-1]) if capacidades else None,
                     detalhe=f"{len(slides)} slide(s) de {template_id}: {feito} em {str(round(segundos, 1)).replace('.', ',')} s",
                     arquivos=gerados, segundos=segundos, template_id=template_id)
    final = modelo.mudar_status(raiz, peca_id, "produzida", origem=origem, agente=agente)
    return {
        "peca_id": peca_id,
        "status": final["status"],
        "tipo": TIPO,
        "template": template_id,
        "pasta": relativo(raiz, pasta),
        "slides": final["slides"],
        "arquivos": final["arquivos"],
        "segundos": segundos,
        "avisos": avisos,
    }
