"""Extração do site da empresa para a proposta de Alma (CONTRATO-alma, "Como a Alma é criada").

Determinística: requests + parsing de HTML e CSS, sem modelo. Lê a página inicial e, quando
linkadas no mesmo site, as páginas de sobre, produtos/serviços, contato e blog; as folhas de estilo
do próprio site; e o logotipo, que é baixado para `alma/assets/`.

O que a extração nunca faz é inventar (regra 3 do contrato): campo sem evidência sai `null` (ou
lista vazia) e o caminho dele entra em `pendencias`; o que veio do site entra em `origens` como
`site`. Tom de voz, público e CTA nunca vêm daqui: a skill `/expxmedia:alma` os propõe a partir dos
textos devolvidos em `paginas` (como `inferido`) ou pergunta na entrevista.

Cores: os nove papéis do contrato são preenchidos só com evidência, nesta ordem de força:
1. variável CSS nomeada pelo papel (`--cor-primaria`, `--brand`, `--fundo`, `--success`...);
2. regras de `html`/`body` (fundo e texto);
3. texto sobre o destaque (`color` numa regra cujo fundo é a cor de destaque) para `texto_inverso`;
4. para `destaque` e `destaque_2` sem variável nomeada, as cores cromáticas dominantes do logotipo
   (e, sem logotipo, do CSS), por área ou contagem.

Uso:

    from expxmedia.alma import site
    r = site.extrair("https://www.exemplo.com.br", raiz)
    r["proposta"]     # alma.json proposto (confirmada_em null), com origens e pendencias
    r["paginas"]      # [{"papel", "url", "titulo", "texto"}] para a skill ler
    r["evidencias"]   # cores vistas, fontes vistas, logotipo
"""
from __future__ import annotations

import colorsys
import io
import re
import unicodedata
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests

from expxmedia.alma.schema import VERSAO
from expxmedia.nucleo import ids
from expxmedia.nucleo.raiz import relativo

__all__ = ["ErroSite", "extrair", "PAPEIS_COR", "TIMEOUT_S"]

TIMEOUT_S = 20
AGENTE = "expxmedia-alma/1 (extracao de site)"
# Teto do texto de cada página devolvido à skill: o bastante para inferir público e ofertas sem
# encher o contexto do modelo.
MAX_TEXTO_PAGINA = 6000

PAPEIS_COR = ("fundo", "fundo_alt", "texto", "texto_inverso", "apoio", "destaque", "destaque_2", "positivo", "negativo")

# Páginas que o contrato manda ler, pelo caminho do link ou pelo texto dele (sem acento, minúsculo).
PAGINAS = {
    "sobre": ("sobre", "quem-somos", "quem somos", "about", "nossa-historia", "nossa historia", "institucional"),
    "produtos": ("produtos", "produto", "servicos", "servico", "products", "services", "cardapio", "loja", "shop",
                 "catalogo", "cursos", "solucoes", "planos"),
    "contato": ("contato", "contact", "fale-conosco", "fale conosco"),
    "blog": ("blog", "artigos", "noticias"),
}

# Variável CSS -> papel. A ordem importa: o mais específico primeiro (fundo-alt antes de fundo,
# texto-inverso antes de texto).
VARIAVEIS_PAPEL = (
    ("texto_inverso", ("texto-inverso", "inverse", "on-primary", "on-brand", "on-accent")),
    ("fundo_alt", ("fundo-alt", "bg-alt", "background-alt", "surface", "fundo-2", "bg-2")),
    ("apoio", ("apoio", "muted", "subtle", "text-secondary", "texto-secundario")),
    ("destaque_2", ("secundaria", "secundario", "secondary", "destaque-2", "accent-2", "brand-2")),
    ("destaque", ("primaria", "primario", "primary", "brand", "marca", "destaque", "accent")),
    ("positivo", ("positivo", "sucesso", "success")),
    ("negativo", ("negativo", "perigo", "danger", "error", "erro")),
    ("fundo", ("fundo", "background", "bg")),
    ("texto", ("texto", "text", "foreground", "fg")),
)

# Cor "cromática" (candidata a destaque): saturação e luminosidade longe do cinza, do branco e do preto.
SATURACAO_MIN = 0.25
LUZ_MIN = 0.15
LUZ_MAX = 0.90
# destaque_2 precisa ser outra cor, não um tom vizinho do destaque.
DISTANCIA_MATIZ_MIN = 30.0

# Tipo de oferta pelo texto do cartão ou pelo caminho da página (sem acento).
TIPOS_OFERTA = (
    ("assinatura", ("assinatura", "subscription", "mensalidade")),
    ("curso", ("curso", "course", "treinamento", "workshop")),
    ("evento", ("evento", "event", "palestra", "encontro")),
    ("servico", ("servico", "service", "consultoria", "solucao")),
    ("produto", ("produto", "product", "loja", "shop", "catalogo", "cardapio")),
)
CLASSES_CARTAO = ("produto", "product", "servico", "service", "plano", "oferta", "offer", "card", "item", "curso")

REDES = (
    ("instagram", ("instagram.com",)),
    ("facebook", ("facebook.com", "fb.com")),
    ("youtube", ("youtube.com", "youtu.be")),
    ("tiktok", ("tiktok.com",)),
    ("linkedin", ("linkedin.com",)),
    ("x", ("x.com", "twitter.com")),
)

GENERICAS = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "inherit", "initial", "unset",
             "-apple-system", "ui-sans-serif", "ui-serif", "ui-monospace"}

VAZIOS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
IGNORAR_TEXTO = {"script", "style", "noscript", "template", "svg", "head"}
EXTENSOES_LOGO = {"image/svg+xml": ".svg", "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
                  "image/gif": ".gif"}


class ErroSite(RuntimeError):
    """O site não pôde ser lido (URL inválida, fora do ar, resposta que não é HTML)."""


# ---------------------------------------------------------------- HTML


class _No:
    __slots__ = ("tag", "attrs", "filhos", "pai")

    def __init__(self, tag: str, attrs: dict[str, str], pai: "_No | None") -> None:
        self.tag = tag
        self.attrs = attrs
        self.filhos: list["_No | str"] = []
        self.pai = pai

    def todos(self, *tags: str):
        for filho in self.filhos:
            if isinstance(filho, _No):
                if not tags or filho.tag in tags:
                    yield filho
                yield from filho.todos(*tags)

    def texto(self) -> str:
        partes: list[str] = []

        def andar(no: "_No") -> None:
            for filho in no.filhos:
                if isinstance(filho, str):
                    partes.append(filho)
                elif filho.tag not in IGNORAR_TEXTO:
                    andar(filho)
                    if filho.tag in {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
                                     "header", "footer", "tr"}:
                        partes.append("\n")

        andar(self)
        linhas = (" ".join(l.split()) for l in "".join(partes).splitlines())
        return "\n".join(l for l in linhas if l)

    def texto_bruto(self) -> str:
        return "".join(f if isinstance(f, str) else f.texto_bruto() for f in self.filhos)


class _Arvore(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.raiz = _No("#documento", {}, None)
        self.atual = self.raiz

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        no = _No(tag, {k.lower(): (v or "") for k, v in attrs}, self.atual)
        self.atual.filhos.append(no)
        if tag not in VAZIOS:
            self.atual = no

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.atual.filhos.append(_No(tag, {k.lower(): (v or "") for k, v in attrs}, self.atual))

    def handle_endtag(self, tag: str) -> None:
        no = self.atual
        while no is not None and no.tag != tag:
            no = no.pai
        if no is not None and no.pai is not None:
            self.atual = no.pai

    def handle_data(self, data: str) -> None:
        self.atual.filhos.append(data)


def _arvore(html: str) -> _No:
    parser = _Arvore()
    parser.feed(html)
    parser.close()
    return parser.raiz


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def _limpo(texto: str | None) -> str | None:
    if texto is None:
        return None
    texto = " ".join(texto.split())
    return texto or None


# ---------------------------------------------------------------- cores


_RE_HEX = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z_-])")
_RE_RGB = re.compile(r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})")
_RE_COMENTARIO = re.compile(r"/\*.*?\*/", re.DOTALL)
_RE_REGRA = re.compile(r"([^{}]+)\{([^{}]*)\}")


def _hex(texto: str) -> list[str]:
    """Cores de um valor CSS, em #RRGGBB maiúsculo (alfa descartado)."""
    cores: list[str] = []
    for m in _RE_HEX.finditer(texto):
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h[:3])
        cores.append("#" + h[:6].upper())
    for m in _RE_RGB.finditer(texto):
        partes = [min(255, int(x)) for x in m.groups()]
        cores.append("#" + "".join(f"{x:02X}" for x in partes))
    return cores


def _hls(cor: str) -> tuple[float, float, float]:
    r, g, b = (int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def _cromatica(cor: str) -> bool:
    _, luz, sat = _hls(cor)
    return sat >= SATURACAO_MIN and LUZ_MIN <= luz <= LUZ_MAX


def _distancia_matiz(a: str, b: str) -> float:
    d = abs(_hls(a)[0] - _hls(b)[0]) * 360
    return min(d, 360 - d)


def _regras(css: str) -> list[tuple[list[str], dict[str, str]]]:
    """[(seletores, declarações)] de uma folha, sem comentários; @media é achatado."""
    css = _RE_COMENTARIO.sub("", css)
    regras = []
    for m in _RE_REGRA.finditer(css):
        seletores = [s.strip().lower() for s in m.group(1).split(",") if s.strip()]
        seletores = [s for s in seletores if not s.startswith("@")]
        declaracoes: dict[str, str] = {}
        for parte in m.group(2).split(";"):
            if ":" in parte:
                chave, valor = parte.split(":", 1)
                declaracoes[chave.strip().lower()] = valor.strip()
        if seletores:
            regras.append((seletores, declaracoes))
    return regras


def _declaracoes_inline(estilo: str) -> dict[str, str]:
    declaracoes = {}
    for parte in estilo.split(";"):
        if ":" in parte:
            chave, valor = parte.split(":", 1)
            declaracoes[chave.strip().lower()] = valor.strip()
    return declaracoes


def _fundo(declaracoes: dict[str, str]) -> str | None:
    for chave in ("background-color", "background"):
        if chave in declaracoes:
            cores = _hex(declaracoes[chave])
            if cores:
                return cores[0]
    return None


def _cor_texto(declaracoes: dict[str, str]) -> str | None:
    cores = _hex(declaracoes.get("color", ""))
    return cores[0] if cores else None


def _cores_svg(dados: bytes) -> Counter:
    texto = dados.decode("utf-8", errors="replace")
    contagem: Counter = Counter()
    for m in re.finditer(r"(?:fill|stroke|stop-color)\s*[:=]\s*[\"']?\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))", texto):
        for cor in _hex(m.group(1)):
            contagem[cor] += 1
    return contagem


def _cores_raster(dados: bytes) -> Counter:
    from PIL import Image

    try:
        imagem = Image.open(io.BytesIO(dados)).convert("RGBA")
    except Exception:  # noqa: BLE001 — logotipo ilegível só não dá cor
        return Counter()
    imagem.thumbnail((128, 128))
    contagem: Counter = Counter()
    for r, g, b, a in (imagem.get_flattened_data() if hasattr(imagem, "get_flattened_data") else imagem.getdata()):
        if a >= 128:
            contagem[f"#{r:02X}{g:02X}{b:02X}"] += 1
    return contagem


# ---------------------------------------------------------------- rede


def _baixar(sessao: requests.Session, url: str) -> requests.Response:
    try:
        resposta = sessao.get(url, timeout=TIMEOUT_S, headers={"User-Agent": AGENTE})
    except requests.RequestException as erro:
        raise ErroSite(f"não foi possível ler {url}: {type(erro).__name__}") from None
    if resposta.status_code >= 400:
        raise ErroSite(f"{url} respondeu {resposta.status_code}")
    return resposta


def _texto_resposta(resposta: requests.Response) -> str:
    if resposta.encoding is None or resposta.encoding.lower() == "iso-8859-1":
        resposta.encoding = resposta.apparent_encoding or "utf-8"
    return resposta.text


def _mesmo_site(url: str, base: str) -> bool:
    return urlsplit(url).netloc.lower() == urlsplit(base).netloc.lower()


# ---------------------------------------------------------------- extração


def _meta(doc: _No, *nomes: str) -> str | None:
    for meta in doc.todos("meta"):
        chave = (meta.attrs.get("property") or meta.attrs.get("name") or "").lower()
        if chave in nomes and _limpo(meta.attrs.get("content")):
            return _limpo(meta.attrs["content"])
    return None


def _titulo(doc: _No) -> str | None:
    for no in doc.todos("title"):
        return _limpo(no.texto_bruto())
    return None


def _nome_empresa(doc: _No) -> str | None:
    nome = _meta(doc, "og:site_name", "application-name")
    if nome:
        return nome
    titulo = _titulo(doc)
    if not titulo:
        return None
    # "Nome | slogan", "Nome - slogan": a primeira parte é o nome.
    return _limpo(re.split(r"\s+[|\-–—·•:]\s+", titulo)[0])


def _papel_link(href: str, texto: str) -> str | None:
    caminho = _sem_acento(unquote(urlsplit(href).path)).strip("/")
    rotulo = _sem_acento(texto)
    for papel, chaves in PAGINAS.items():
        for chave in chaves:
            if re.search(rf"(^|[/_.\-]){re.escape(chave)}($|[/_.\-])", caminho) or re.search(rf"\b{re.escape(chave)}\b", rotulo):
                return papel
    return None


def _canal(url: str) -> dict[str, Any] | None:
    partes = urlsplit(url)
    host = partes.netloc.lower().removeprefix("www.").removeprefix("m.")
    for canal, dominios in REDES:
        if any(host == d or host.endswith("." + d) for d in dominios):
            segmentos = [s for s in partes.path.split("/") if s]
            if not segmentos:
                return {"canal": canal, "identificador": None, "url": url}
            primeiro = segmentos[0]
            if canal in {"youtube", "tiktok"} and primeiro.startswith("@"):
                ident = primeiro
            elif canal in {"instagram", "x"}:
                ident = "@" + primeiro.lstrip("@")
            elif canal == "linkedin" and len(segmentos) > 1:
                ident = segmentos[1]
            else:
                ident = primeiro
            return {"canal": canal, "identificador": ident, "url": url}
    return None


def _familias_google(doc: _No) -> list[str]:
    familias: list[str] = []
    for link in doc.todos("link"):
        href = link.attrs.get("href", "")
        partes = urlsplit(href)
        if partes.netloc.lower() != "fonts.googleapis.com":
            continue
        for valor in parse_qs(partes.query).get("family", []):
            for familia in valor.split("|"):
                nome = _limpo(familia.split(":")[0].replace("+", " "))
                if nome and nome not in familias:
                    familias.append(nome)
    return familias


def _primeira_familia(valor: str | None) -> str | None:
    if not valor:
        return None
    for parte in valor.split(","):
        nome = parte.strip().strip("'\"").strip()
        if nome and nome.lower() not in GENERICAS:
            return nome
    return None


def _logo(doc: _No, base: str) -> str | None:
    candidatos = []
    for img in doc.todos("img"):
        pistas = " ".join(img.attrs.get(a, "") for a in ("class", "id", "alt", "src")).lower()
        if "logo" in pistas and img.attrs.get("src"):
            dentro_do_cabecalho = False
            no = img.pai
            while no is not None:
                if no.tag == "header":
                    dentro_do_cabecalho = True
                    break
                no = no.pai
            candidatos.append((0 if dentro_do_cabecalho else 1, urljoin(base, img.attrs["src"])))
    return sorted(candidatos, key=lambda c: c[0])[0][1] if candidatos else None


def _tipo_oferta(*textos: str) -> str | None:
    for texto in textos:
        normal = _sem_acento(texto)
        for tipo, chaves in TIPOS_OFERTA:
            if any(re.search(rf"(^|[^a-z]){c}", normal) for c in chaves):
                return tipo
    return None


def _ofertas(doc: _No, url_pagina: str) -> tuple[list[dict[str, Any]], list[str]]:
    ofertas: list[dict[str, Any]] = []
    pendencias: list[str] = []
    vistos: set[str] = set()
    for no in doc.todos("article", "li", "div", "section"):
        classe = _sem_acento(no.attrs.get("class", "") + " " + no.attrs.get("id", ""))
        if not any(c in classe for c in CLASSES_CARTAO):
            continue
        titulo = next(no.todos("h2", "h3", "h4"), None)
        if titulo is None:
            continue
        # cartão que contém outros cartões é lista, não oferta
        if any(any(c in _sem_acento(f.attrs.get("class", "")) for c in CLASSES_CARTAO) and next(f.todos("h2", "h3", "h4"), None)
               for f in no.todos("article", "li", "div", "section")):
            continue
        nome = _limpo(titulo.texto())
        oid = ids.slug(nome or "")
        if not nome or not oid or oid in vistos:
            continue
        vistos.add(oid)
        paragrafo = next(no.todos("p"), None)
        link = next((a for a in no.todos("a") if a.attrs.get("href")), None)
        tipo = _tipo_oferta(nome, classe, urlsplit(url_pagina).path)
        if tipo is None:
            tipo = "outro"
            pendencias.append(f"ofertas.{oid}.tipo")
        oferta = {
            "id": oid,
            "nome": nome,
            "tipo": tipo,
            "descricao": _limpo(paragrafo.texto()) if paragrafo else None,
            "url": urljoin(url_pagina, link.attrs["href"]) if link else None,
            "principal": False,
        }
        for campo in ("descricao", "url"):
            if oferta[campo] is None:
                pendencias.append(f"ofertas.{oid}.{campo}")
        ofertas.append(oferta)
    return ofertas, pendencias


def _agora_iso() -> str:
    # A Alma ainda não existe, então não há empresa.fuso: vale o fuso da máquina, sempre explícito (M5).
    texto = datetime.now().astimezone().isoformat(timespec="seconds")
    return texto


def _proposta_vazia(agora: str) -> dict[str, Any]:
    return {
        "expxmedia_alma": VERSAO,
        "metodo": "site",
        "fontes": [],
        "criada_em": agora,
        "confirmada_em": None,
        "atualizado_em": agora,
        "empresa": {"nome": None, "nome_curto": None, "descricao_curta": None, "segmento": None, "site": None,
                    "pais": None, "idioma": None, "fuso": None},
        "publico": {"principal": None, "dores": [], "desejos": []},
        "ofertas": [],
        "voz": {"tom": [], "tratamento": None, "formalidade": None, "palavras_preferidas": [],
                "palavras_proibidas": [], "regras": [], "exemplos_bons": [], "exemplos_ruins": []},
        "visual": {
            "cores": {papel: None for papel in PAPEIS_COR},
            "fontes": {"titulo": {"familia": None, "origem": None}, "texto": {"familia": None, "origem": None}},
            "logo": {"principal": None, "negativo": None, "simbolo": None},
            "estilo": [],
        },
        "cta": {"padrao": None, "destino": None, "variacoes": []},
        "canais": [],
        "porta_vozes": [],
        "restricoes": {"temas_proibidos": [], "promessas_proibidas": [], "observacoes_legais": []},
        "origens": {},
        "pendencias": [],
    }


def _sem_evidencia(dados: Any, prefixo: str = "") -> list[str]:
    """Caminhos das folhas null e das listas vazias (a regra 3 do contrato, aplicada à proposta)."""
    if isinstance(dados, dict):
        caminhos: list[str] = []
        for chave, valor in dados.items():
            caminhos += _sem_evidencia(valor, f"{prefixo}.{chave}" if prefixo else chave)
        return caminhos
    if isinstance(dados, list):
        return [prefixo] if not dados else []
    return [prefixo] if dados is None else []


def extrair(url: str, raiz: Path | str, *, sessao: requests.Session | None = None) -> dict[str, Any]:
    """Lê o site em `url` e devolve {"proposta", "paginas", "evidencias", "avisos"}.

    Baixa o logotipo para `<raiz>/alma/assets/logo.<ext>` (ou `logo-site.<ext>`, se já houver um:
    logotipo existente nunca é sobrescrito). Não grava `alma/alma.json`: a proposta só vira Alma
    depois do "confirmo tudo" da pessoa. Levanta ErroSite se a página inicial não puder ser lida.
    """
    raiz = Path(raiz).resolve()
    partes = urlsplit(url.strip())
    if partes.scheme not in ("http", "https") or not partes.netloc:
        raise ErroSite(f"URL inválida (esperado http:// ou https://): {url!r}")
    inicio = url.strip()
    sessao = sessao or requests.Session()
    avisos: list[str] = []
    proposta = _proposta_vazia(_agora_iso())
    origens: dict[str, str] = {}
    pendencias_extra: list[str] = []

    resposta = _baixar(sessao, inicio)
    inicio = resposta.url or inicio
    doc = _arvore(_texto_resposta(resposta))
    base_site = f"{urlsplit(inicio).scheme}://{urlsplit(inicio).netloc}"

    # páginas
    paginas: list[dict[str, Any]] = [{"papel": "inicio", "url": inicio, "titulo": _titulo(doc), "texto": doc.texto()[:MAX_TEXTO_PAGINA]}]
    documentos = [doc]
    achadas: dict[str, str] = {}
    for a in doc.todos("a"):
        href = a.attrs.get("href", "")
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        alvo = urljoin(inicio, href).split("#")[0]
        if not _mesmo_site(alvo, inicio) or alvo.rstrip("/") == inicio.rstrip("/"):
            continue
        papel = _papel_link(alvo, a.texto())
        if papel and papel not in achadas:
            achadas[papel] = alvo
    ofertas: list[dict[str, Any]] = []
    for papel in PAGINAS:
        if papel not in achadas:
            continue
        try:
            r = _baixar(sessao, achadas[papel])
        except ErroSite as erro:
            avisos.append(str(erro))
            continue
        pagina = _arvore(_texto_resposta(r))
        documentos.append(pagina)
        paginas.append({"papel": papel, "url": r.url or achadas[papel], "titulo": _titulo(pagina),
                        "texto": pagina.texto()[:MAX_TEXTO_PAGINA]})
        if papel == "produtos":
            ofertas, pend = _ofertas(pagina, r.url or achadas[papel])
            pendencias_extra += pend
    proposta["fontes"] = [p["url"] for p in paginas]

    # empresa
    empresa = proposta["empresa"]
    empresa["nome"] = _nome_empresa(doc)
    empresa["descricao_curta"] = _meta(doc, "description", "og:description")
    empresa["site"] = base_site
    html = next(doc.todos("html"), None)
    empresa["idioma"] = _limpo(html.attrs.get("lang")) if html is not None else None
    for campo in ("nome", "descricao_curta", "site", "idioma"):
        if empresa[campo] is not None:
            origens[f"empresa.{campo}"] = "site"

    # ofertas
    proposta["ofertas"] = ofertas
    if ofertas:
        origens["ofertas"] = "site"
        pendencias_extra.append("ofertas.principal")

    # canais, de todas as páginas lidas
    canais: dict[str, dict[str, Any]] = {}
    for d in documentos:
        for a in d.todos("a"):
            canal = _canal(a.attrs.get("href", ""))
            if canal and canal["canal"] not in canais:
                canais[canal["canal"]] = canal
    proposta["canais"] = list(canais.values())
    if canais:
        origens["canais"] = "site"
        for c in proposta["canais"]:
            for campo in ("identificador", "url"):
                if c[campo] is None:
                    pendencias_extra.append(f"canais.{c['canal']}.{campo}")

    # CSS: <style> e folhas do próprio site (Google Fonts e CDN de terceiros não são a marca)
    regras: list[tuple[list[str], dict[str, str]]] = []
    for estilo in doc.todos("style"):
        regras += _regras(estilo.texto_bruto())
    for link in doc.todos("link"):
        rel = link.attrs.get("rel", "").lower().split()
        href = link.attrs.get("href")
        if "stylesheet" not in rel or not href:
            continue
        alvo = urljoin(inicio, href)
        if not _mesmo_site(alvo, inicio):
            continue
        try:
            regras += _regras(_texto_resposta(_baixar(sessao, alvo)))
        except ErroSite as erro:
            avisos.append(str(erro))
    inline = [_declaracoes_inline(no.attrs["style"]) for no in doc.todos() if no.attrs.get("style")]

    contagem_css: Counter = Counter()
    for _, declaracoes in regras:
        for chave, valor in declaracoes.items():
            for cor in _hex(valor):
                contagem_css[cor] += 1
    for declaracoes in inline:
        for valor in declaracoes.values():
            for cor in _hex(valor):
                contagem_css[cor] += 1

    cores = proposta["visual"]["cores"]
    # 1. variáveis nomeadas em :root, html ou body
    for seletores, declaracoes in regras:
        if not any(s in (":root", "html", "body") for s in seletores):
            continue
        for chave, valor in declaracoes.items():
            if not chave.startswith("--"):
                continue
            achadas_cor = _hex(valor)
            if not achadas_cor:
                continue
            nome = chave[2:].lower()
            for papel, chaves in VARIAVEIS_PAPEL:
                if any(re.search(rf"(^|-){re.escape(c)}($|-)", nome) for c in chaves):
                    if cores[papel] is None:
                        cores[papel] = achadas_cor[0]
                    break
    # 2. html/body
    for seletores, declaracoes in regras:
        if any(s in ("html", "body") for s in seletores):
            if cores["fundo"] is None and _fundo(declaracoes):
                cores["fundo"] = _fundo(declaracoes)
            if cores["texto"] is None and _cor_texto(declaracoes):
                cores["texto"] = _cor_texto(declaracoes)

    # logotipo: baixa e lê as cores dominantes
    contagem_logo: Counter = Counter()
    logo_url = _logo(doc, inicio)
    evid_logo: dict[str, Any] | None = None
    if logo_url:
        try:
            r = _baixar(sessao, logo_url)
        except ErroSite as erro:
            avisos.append(f"logotipo não baixado: {erro}")
        else:
            tipo = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            ext = EXTENSOES_LOGO.get(tipo) or Path(urlsplit(logo_url).path).suffix.lower()
            if ext not in EXTENSOES_LOGO.values():
                avisos.append(f"logotipo em formato não reconhecido: {tipo or ext or 'desconhecido'}")
            else:
                pasta = raiz / "alma" / "assets"
                pasta.mkdir(parents=True, exist_ok=True)
                destino = pasta / f"logo{ext}"
                if destino.exists():
                    destino = pasta / f"logo-site{ext}"
                    avisos.append(f"alma/assets/logo{ext} já existe e não foi tocado; o do site foi salvo em {destino.name}")
                destino.write_bytes(r.content)
                proposta["visual"]["logo"]["principal"] = relativo(raiz, destino)
                origens["visual.logo.principal"] = "site"
                contagem_logo = _cores_svg(r.content) if ext == ".svg" else _cores_raster(r.content)
                evid_logo = {"url": logo_url, "arquivo": relativo(raiz, destino),
                             "cores": [c for c, _ in contagem_logo.most_common(6)]}

    # 4. destaque e destaque_2 pelas cores cromáticas dominantes (logotipo antes do CSS)
    fonte_dominante = contagem_logo if any(_cromatica(c) for c in contagem_logo) else contagem_css
    cromaticas = [c for c, _ in fonte_dominante.most_common() if _cromatica(c)]
    if cores["destaque"] is None and cromaticas:
        cores["destaque"] = cromaticas[0]
    if cores["destaque_2"] is None and cores["destaque"] is not None:
        for c in cromaticas:
            if c != cores["destaque"] and _distancia_matiz(c, cores["destaque"]) >= DISTANCIA_MATIZ_MIN:
                cores["destaque_2"] = c
                break
    # 3. texto sobre o destaque
    if cores["texto_inverso"] is None and cores["destaque"] is not None:
        candidatos: Counter = Counter()
        for declaracoes in [d for _, d in regras] + inline:
            if _fundo(declaracoes) == cores["destaque"] and _cor_texto(declaracoes):
                candidatos[_cor_texto(declaracoes)] += 1
        if candidatos:
            cores["texto_inverso"] = candidatos.most_common(1)[0][0]
    for papel in PAPEIS_COR:
        if cores[papel] is not None:
            origens[f"visual.cores.{papel}"] = "site"

    # fontes: só as que o site carrega do Google Fonts, no papel que o CSS lhes dá
    google = _familias_google(doc)
    fam_titulo = fam_texto = None
    for seletores, declaracoes in regras:
        familia = _primeira_familia(declaracoes.get("font-family"))
        if not familia:
            continue
        if fam_titulo is None and any(s in ("h1", "h2") for s in seletores):
            fam_titulo = familia
        if fam_texto is None and any(s in ("html", "body") for s in seletores):
            fam_texto = familia
    for papel, familia in (("titulo", fam_titulo), ("texto", fam_texto)):
        if familia and familia in google:
            proposta["visual"]["fontes"][papel] = {"familia": familia, "origem": "google"}
            origens[f"visual.fontes.{papel}"] = "site"
        elif familia:
            avisos.append(f"fonte de {papel} {familia!r} não vem do Google Fonts: fica para a pessoa informar")

    proposta["origens"] = origens
    pendencias = _sem_evidencia({k: v for k, v in proposta.items() if k not in ("confirmada_em", "origens", "pendencias")})
    proposta["pendencias"] = pendencias + [p for p in pendencias_extra if p not in pendencias]

    return {
        "proposta": proposta,
        "paginas": paginas,
        "evidencias": {
            "cores": [{"cor": c, "contagem": n, "cromatica": _cromatica(c)} for c, n in contagem_css.most_common(12)],
            "fontes_google": google,
            "fontes_css": {"titulo": fam_titulo, "texto": fam_texto},
            "logo": evid_logo,
        },
        "avisos": avisos,
    }
