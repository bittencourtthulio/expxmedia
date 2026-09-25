"""Produção de post único (e o motor comum da produção estática por template HTML).

A entrada é um objeto JSON com o template e os slots de cada slide:

    {
      "template": "post_unico-numero-e-frase-86c9ac",
      "titulo": "Doze perguntas antes de fechar um pedido",
      "slides": [{"kind": "numero", "numero": "12", "texto": "..."}],
      "legenda": "texto da legenda (opcional no post, obrigatória no carrossel)",
      "conteudo": {"gancho": ..., "gancho_tipo": ..., "cta": ..., "cta_forma": ...},   (opcional)
      "serie": null, "pack": "nucleo", "porta_voz": null, "oferta": null, "slug": null  (opcionais)
    }

O caminho, na ordem:

1. confere a entrada (erro cita o campo) e acha o template na galeria local ou nos embarcados;
2. confere os slots contra o template (`render_html.renderizar.validar_copy`): kind inexistente,
   slot desconhecido, obrigatório vazio e texto acima do `max` são erro **antes** do render —
   nenhuma peça, pasta ou evento é criado;
3. cria a peça em `roteiro` (`peca_criada`), renderiza os slides com a Alma, move os PNGs para
   `slides/slide_NN.png` (e a prancha para `previa/prancha.png` no carrossel), grava
   `texto/legenda.txt`, registra arquivos, slides e produção, o evento `geracao_concluida` e
   passa a peça para `produzida`;
4. render reprovado (contraste, encaixe, fonte...) registra `geracao_falhou`, a peça fica em
   `roteiro` (falha não é status, CONTRATO-peca) e levanta ErroRenderReprovado com os achados.

Uso:

    from expxmedia.producao import post
    r = post.produzir(raiz, entrada)   # {"peca_id", "status", "pasta", "slides", "arquivos", "avisos"}
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from expxmedia.alma import carregar as alma_carregar
from expxmedia.nucleo import rastro
from expxmedia.nucleo.raiz import relativo
from expxmedia.peca import modelo
from expxmedia.render_html import prancha as _prancha
from expxmedia.render_html import renderizar as _renderizar
from expxmedia.template import galeria_local

__all__ = [
    "ErroProducao",
    "ErroEntradaProducao",
    "ErroSlots",
    "ErroRenderReprovado",
    "CAPACIDADE",
    "PROVEDOR",
    "ler_entrada",
    "achar_template",
    "produzir_estatico",
    "produzir",
]

CAPACIDADE = "renderizar_html"
PROVEDOR = "playwright"
CAMPOS = ("template", "titulo", "slides", "legenda", "conteudo", "serie", "pack", "porta_voz", "oferta", "slug")
PASTA_RENDER = ".render"


class ErroProducao(ValueError):
    """A produção não pôde começar ou não terminou."""


class ErroEntradaProducao(ErroProducao):
    """Entrada fora do formato; `campo` diz qual."""

    def __init__(self, campo: str, mensagem: str) -> None:
        super().__init__(f"campo '{campo}': {mensagem}")
        self.campo = campo


class ErroSlots(ErroProducao):
    """Slots que não cabem no template; nada foi renderizado nem criado."""

    def __init__(self, erros: list[str]) -> None:
        super().__init__("slots inválidos para o template: " + "; ".join(erros))
        self.erros = list(erros)


class ErroRenderReprovado(ErroProducao):
    """O render rodou e reprovou (contraste, encaixe, fonte...); a peça ficou em `roteiro`."""

    def __init__(self, peca_id: str, relatorio: dict[str, Any]) -> None:
        problemas = [f"slide {s['slide']} ({s['kind']}): {p['detalhe']}"
                     for s in relatorio.get("slides") or [] for p in s.get("problemas") or []]
        problemas += list(relatorio.get("erros") or [])
        super().__init__(f"{peca_id}: render reprovado: " + "; ".join(problemas))
        self.peca_id = peca_id
        self.problemas = problemas
        self.relatorio = relatorio


# ---------------------------------------------------------------- entrada


def ler_entrada(dados: Any, tipo: str) -> dict[str, Any]:
    """Confere a forma da entrada e devolve as chaves do formato, ausente = None."""
    if not isinstance(dados, dict):
        raise ErroEntradaProducao("entrada", "a entrada é um objeto JSON")
    extras = sorted(set(dados) - set(CAMPOS))
    if extras:
        raise ErroEntradaProducao(extras[0], f"chave desconhecida (válidas: {', '.join(CAMPOS)})")
    entrada = {campo: dados.get(campo) for campo in CAMPOS}
    for campo in ("template", "titulo"):
        if not isinstance(entrada[campo], str) or not entrada[campo].strip():
            raise ErroEntradaProducao(campo, "texto obrigatório")
    if not isinstance(entrada["slides"], list) or not entrada["slides"]:
        raise ErroEntradaProducao("slides", "lista com pelo menos um slide ({\"kind\": ..., <slot>: ...})")
    for i, slide in enumerate(entrada["slides"], 1):
        if not isinstance(slide, dict) or not isinstance(slide.get("kind"), str):
            raise ErroEntradaProducao("slides", f"o slide {i} é um objeto com `kind` e os slots")
    if entrada["legenda"] is not None and not isinstance(entrada["legenda"], str):
        raise ErroEntradaProducao("legenda", "texto ou null")
    if tipo == "carrossel" and (not isinstance(entrada["legenda"], str) or not entrada["legenda"].strip()):
        raise ErroEntradaProducao("legenda", "o carrossel sai com a legenda: texto obrigatório")
    if entrada["conteudo"] is not None and not isinstance(entrada["conteudo"], dict):
        raise ErroEntradaProducao("conteudo", "objeto ou null")
    conteudo = entrada["conteudo"] or {}
    fora = sorted(set(conteudo) - (set(modelo.CHAVES_CONTEUDO) - {"legenda", "roteiro"}))
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


def achar_template(raiz: Path | str, template_id: str, tipo: str, embarcados: Path | str | None = None) -> Path:
    """Pasta do template `template_id` (galeria local antes da embarcada), conferindo o tipo."""
    base_emb = Path(embarcados) if embarcados is not None else galeria_local.pasta_embarcados()
    itens = galeria_local.listar(raiz, embarcados=base_emb)
    item = next((i for i in itens if i["template_id"] == template_id), None)
    if item is None:
        do_tipo = sorted(i["template_id"] for i in itens if isinstance(i["dados"], dict) and i["dados"].get("tipo") == tipo)
        raise ErroEntradaProducao("template", f"template '{template_id}' não encontrado (de {tipo}: {', '.join(do_tipo) or 'nenhum'})")
    if item["erro"] is not None:
        raise ErroEntradaProducao("template", f"template '{template_id}' fora do contrato: {item['erro']}")
    dados = item["dados"]
    if dados.get("tipo") != tipo:
        raise ErroEntradaProducao("template", f"template '{template_id}' é de {dados.get('tipo')}, não de {tipo}")
    if dados.get("motor") != "html":
        raise ErroEntradaProducao("template", f"template '{template_id}' usa o motor {dados.get('motor')}; a produção estática é html")
    if dados.get("status") in galeria_local.STATUS_FORA_DA_BUSCA:
        raise ErroEntradaProducao("template", f"template '{template_id}' está {dados['status']}")
    if item["galeria"] == "local":
        return Path(raiz) / item["caminho"]
    return base_emb.parent / item["caminho"]


# ---------------------------------------------------------------- produção


def _atualizar(raiz: Path, peca_id: str, aplicar) -> dict[str, Any]:
    # Slides e conteúdo não têm registro próprio no modelo; mesma gravação atômica sob trava (M15).
    return modelo._atualizar(raiz, peca_id, aplicar)[0]


def produzir_estatico(
    raiz: Path | str,
    dados: Any,
    *,
    tipo: str,
    base_imagens: Path | str | None = None,
    embarcados: Path | str | None = None,
    cache_fontes: Path | str | None = None,
    origem: str = "skill",
    agente: str | None = None,
) -> dict[str, Any]:
    """Produz uma peça `post_unico` ou `carrossel` de imagem a partir da entrada (ver o módulo)."""
    raiz = Path(raiz)
    entrada = ler_entrada(dados, tipo)
    pasta_template = achar_template(raiz, entrada["template"].strip(), tipo, embarcados)
    m = _renderizar.carregar_template(pasta_template)
    copy = {"slides": entrada["slides"]}
    erros = _renderizar.validar_copy(m, copy)
    kinds_video = [s["kind"] for s in entrada["slides"] if (m["kinds"].get(s["kind"]) or {}).get("midia") == "video"]
    if kinds_video:
        erros.append(f"kind de vídeo ({', '.join(kinds_video)}) não sai na produção estática: use o carrossel misto")
    if erros:
        raise ErroSlots(erros)
    try:
        alma = alma_carregar.carregar(raiz)
    except alma_carregar.ErroAlmaAusente as erro:
        raise ErroProducao(str(erro)) from None

    formato = m["formato"]
    conteudo = dict(entrada["conteudo"] or {})
    peca = modelo.criar(
        raiz, tipo=tipo, titulo=entrada["titulo"], formatos=[formato], pack=entrada["pack"] or "nucleo",
        slug=entrada["slug"], status="roteiro", serie=entrada["serie"], template=m["template_id"],
        porta_voz=entrada["porta_voz"], oferta=entrada["oferta"], conteudo=conteudo, origem=origem, agente=agente,
    )
    peca_id, pack = peca["peca_id"], peca["pack"]
    pasta = modelo.pasta(raiz, peca_id)
    temporaria = pasta / PASTA_RENDER
    inicio = time.monotonic()
    try:
        relatorio = _renderizar.renderizar(
            pasta_template, copy, alma, temporaria, raiz=raiz, base_copy=base_imagens, cache_fontes=cache_fontes,
            gerar_prancha=(tipo == "carrossel"),
        )
    except Exception as erro:  # noqa: BLE001 — falha de produção vira evento, e sobe
        shutil.rmtree(temporaria, ignore_errors=True)
        rastro.registrar(raiz, origem=origem, evento="geracao_falhou", resultado="falha", pack=pack, peca_id=peca_id,
                         agente=agente, capacidade=CAPACIDADE, provedor=PROVEDOR,
                         detalhe=f"{type(erro).__name__}: {erro}"[:500], segundos=round(time.monotonic() - inicio, 3),
                         template_id=m["template_id"])
        raise
    segundos = round(time.monotonic() - inicio, 3)
    if not relatorio.get("ok"):
        reprovado = ErroRenderReprovado(peca_id, relatorio)
        rastro.registrar(raiz, origem=origem, evento="geracao_falhou", resultado="falha", pack=pack, peca_id=peca_id,
                         agente=agente, capacidade=CAPACIDADE, provedor=PROVEDOR,
                         detalhe="; ".join(reprovado.problemas)[:500], segundos=segundos, template_id=m["template_id"])
        raise reprovado

    # mover para o lugar do contrato: slides/slide_NN.png, previa/prancha.png, previa/render.json
    (pasta / "slides").mkdir(exist_ok=True)
    slides, gerados = [], []
    for item in relatorio["slides"]:
        destino = pasta / "slides" / f"slide_{item['slide']:02d}.png"
        (temporaria / item["arquivo"]).replace(destino)
        gerados.append(destino)
        slides.append({"n": item["slide"], "kind": item["kind"], "midia": "imagem",
                       "arquivo": relativo(pasta, destino), "duracao_s": None})
    (pasta / "previa").mkdir(exist_ok=True)
    prancha = None
    if relatorio.get("prancha"):
        prancha = pasta / "previa" / "prancha.png"
        (temporaria / relatorio["prancha"]).replace(prancha)
    (temporaria / _prancha.NOME_RELATORIO).replace(pasta / "previa" / _prancha.NOME_RELATORIO)
    shutil.rmtree(temporaria, ignore_errors=True)

    for destino in gerados:
        modelo.registrar_arquivo(raiz, peca_id, destino, papel="slide", formato=formato)
    legenda = None
    if isinstance(entrada["legenda"], str) and entrada["legenda"].strip():
        legenda = pasta / "texto" / "legenda.txt"
        legenda.parent.mkdir(exist_ok=True)
        legenda.write_text(entrada["legenda"].strip() + "\n", encoding="utf-8")
        modelo.registrar_arquivo(raiz, peca_id, legenda, papel="legenda", formato=None)
    if prancha is not None:
        modelo.registrar_arquivo(raiz, peca_id, prancha, papel="previa", formato=None)

    def aplicar(atual: dict[str, Any]) -> None:
        atual["slides"] = slides
        if legenda is not None:
            atual["conteudo"]["legenda"] = relativo(pasta, legenda)

    _atualizar(raiz, peca_id, aplicar)
    modelo.registrar_producao(raiz, peca_id, capacidades=[CAPACIDADE], provedores={CAPACIDADE: PROVEDOR}, segundos=segundos)
    arquivos_evento = gerados + [p for p in (legenda, prancha) if p is not None]
    rastro.registrar(raiz, origem=origem, evento="geracao_concluida", resultado="ok", pack=pack, peca_id=peca_id,
                     agente=agente, capacidade=CAPACIDADE, provedor=PROVEDOR,
                     detalhe=f"{len(slides)} slide(s) de {m['template_id']} em {str(round(segundos, 1)).replace('.', ',')} s",
                     arquivos=arquivos_evento, segundos=segundos, template_id=m["template_id"])
    final = modelo.mudar_status(raiz, peca_id, "produzida", origem=origem, agente=agente)
    avisos = [f"slide {s['slide']} ({s['kind']}): {a['detalhe']}" for s in relatorio["slides"] for a in s.get("avisos") or []]
    avisos += [f"fonte {f['papel']}: {f['aviso']}" for f in relatorio.get("fontes") or [] if f.get("aviso")]
    return {
        "peca_id": peca_id,
        "status": final["status"],
        "tipo": tipo,
        "template": m["template_id"],
        "pasta": relativo(raiz, pasta),
        "slides": final["slides"],
        "arquivos": final["arquivos"],
        "segundos": segundos,
        "avisos": avisos,
    }


def produzir(raiz: Path | str, dados: Any, **opcoes: Any) -> dict[str, Any]:
    """Produz um post único: exatamente um slide, um PNG."""
    return produzir_estatico(raiz, dados, tipo="post_unico", **opcoes)
