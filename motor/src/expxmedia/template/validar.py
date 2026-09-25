"""Validação estática dos arquivos de um template (CONTRATO-template, D-36, M13).

Dois modos:

- `template`: o template da galeria. Cor literal fora de `:root` é achado (preto, branco e
  `transparent` são permitidos, porque não identificam marca): a cor de quem criou o template
  vazaria para todo mundo.
- `sob_medida`: o código de um reel por referência (D-36). Pode usar as cores literais da paleta
  da referência; todas as outras regras valem igual.

Em qualquer modo:

- URL externa em `url()`, `@import`, `src`, `href` de `<link>` ou string de código é achado,
  exceto o Google Fonts.
- Código (TSX/TS/JSX/JS): imports só de `react`, `remotion`, `@remotion/*`,
  `@expxmedia/template` e de arquivos do próprio template; outro pacote só se estiver em
  `dependencias` **e** na lista permitida da galeria. Proibidos: `fs`, `child_process`, `net`,
  `http`, `https`, `fetch`, `XMLHttpRequest`, `WebSocket`, `eval`, `new Function`, `process`,
  `require` dinâmico e `import()` dinâmico.

Cada achado é `{"tipo", "arquivo", "linha", "detalhe"}`, com `tipo` em `cor_literal`,
`url_externa`, `import_proibido`, `api_proibida`, `template_rejeitado`, `arquivo_ausente` ou
um tipo de violação do schema (`chave_omitida`, `tipo_invalido`, `valor_invalido`).

A análise é de texto: reduz o risco, não o zera. A segunda barreira é o render isolado.

Uso:

    from expxmedia.template import validar
    achados = validar.validar_template(pasta, modo="template")
"""
from __future__ import annotations

import bisect
import re
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from expxmedia.nucleo import arquivos as _arquivos
from expxmedia.template import schema as _schema

__all__ = [
    "MODOS",
    "HOSTS_PERMITIDOS",
    "MODULOS_PROIBIDOS",
    "APIS_PROIBIDAS",
    "validar_css",
    "validar_html",
    "validar_codigo",
    "validar_template",
]

MODOS = ("template", "sob_medida")
HOSTS_PERMITIDOS = frozenset({"fonts.googleapis.com", "fonts.gstatic.com"})
MODULOS_PROIBIDOS = frozenset({"fs", "child_process", "net", "http", "https"})
APIS_PROIBIDAS = ("fetch", "XMLHttpRequest", "WebSocket", "eval", "process")
_GLOBAIS = frozenset({"window", "globalThis", "self", "global"})
_EXT_CSS = {".css"}
_EXT_HTML = {".html", ".htm"}
_EXT_CODIGO = {".tsx", ".ts", ".jsx", ".js", ".mjs", ".cjs"}
_PASTAS_IGNORADAS = {"node_modules", "previa", "referencia", "compartilhada", ".git"}

# Cores nomeadas do CSS (CSS Color Module 4), exceto as permitidas: black, white, transparent.
_NOMEADAS = frozenset("""
aliceblue antiquewhite aqua aquamarine azure beige bisque blanchedalmond blue blueviolet brown burlywood
cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod
darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon
darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray
dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green
greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon
lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon
lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen
magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue
mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy
oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip
peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown
seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan teal
thistle tomato turquoise violet wheat whitesmoke yellow yellowgreen
""".split())
_RE_NOMEADA = re.compile(r"(?<![\w-])(" + "|".join(sorted(_NOMEADAS, key=len, reverse=True)) + r")(?![\w-])", re.I)
_RE_HEX = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z_-])")
_RE_FUNCAO_COR = re.compile(r"(?<![\w-])(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(([^()]*)\)", re.I)
_RE_URL_CSS = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I | re.S)
_RE_IMPORT_CSS = re.compile(r"@import\s+(['\"])(.*?)\1", re.I)
_RE_STRING_CSS = re.compile(r"(['\"])(?:\\.|(?!\1).)*\1", re.S)
_ATRIBUTOS_COR = {"fill", "stroke", "color", "bgcolor", "stop-color", "flood-color", "lighting-color"}
# Atributos que fazem a página carregar algo. `href` de `<a>` não carrega nada no render.
_ATRIBUTOS_URL = {"src", "srcset", "poster", "data", "action", "formaction", "background", "xlink:href"}
_TAGS_HREF = {"link", "image", "use", "feimage"}


def _carrega_url(tag: str, atributo: str) -> bool:
    return atributo in _ATRIBUTOS_URL or (atributo == "href" and tag in _TAGS_HREF)


def _exigir_modo(modo: str) -> None:
    if modo not in MODOS:
        raise ValueError(f"modo desconhecido: {modo!r} (válidos: {', '.join(MODOS)})")


def _achado(tipo: str, arquivo: str, linha: int | None, detalhe: str) -> dict[str, Any]:
    return {"tipo": tipo, "arquivo": arquivo, "linha": linha, "detalhe": detalhe}


class _Linhas:
    """Converte deslocamento no texto em número de linha (1-based)."""

    def __init__(self, texto: str, base: int = 1):
        self._quebras = [i for i, c in enumerate(texto) if c == "\n"]
        self._base = base

    def __call__(self, deslocamento: int) -> int:
        return bisect.bisect_left(self._quebras, deslocamento) + self._base


# ---------------------------------------------------------------- cores e URLs


def _hex_neutro(digitos: str) -> bool:
    if len(digitos) in (3, 4):
        digitos = "".join(c * 2 for c in digitos)
    return digitos[:6].lower() in ("000000", "ffffff")


def _funcao_neutra(nome: str, argumentos: str) -> bool:
    if nome.lower() not in ("rgb", "rgba"):
        return False
    canais = [c for c in re.split(r"[\s,/]+", argumentos.strip()) if c][:3]
    if len(canais) != 3:
        return False
    normalizados = {"0": "0", "0%": "0", "255": "1", "100%": "1"}
    valores = {normalizados.get(c.strip()) for c in canais}
    return valores in ({"0"}, {"1"})


def _cores_literais(valor: str, nomeadas: bool = True) -> list[str]:
    """Cores literais não neutras em `valor` (valor de declaração CSS ou texto de string)."""
    achadas = []
    for m in _RE_FUNCAO_COR.finditer(valor):
        if not _funcao_neutra(m.group(1), m.group(2)):
            achadas.append(m.group(0))
    sem_funcoes = _RE_FUNCAO_COR.sub(" ", valor)
    for m in _RE_HEX.finditer(sem_funcoes):
        if not _hex_neutro(m.group(1)):
            achadas.append(m.group(0))
    if nomeadas:
        achadas.extend(m.group(0) for m in _RE_NOMEADA.finditer(sem_funcoes))
    return achadas


def _url_externa(url: str) -> bool:
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    partes = urlsplit(url)
    if partes.scheme.lower() in ("", "data", "blob", "about"):
        return False
    if partes.scheme.lower() == "file":
        return True
    return (partes.hostname or "").lower() not in HOSTS_PERMITIDOS


def _mascarar(texto: str, inicio: int, fim: int) -> str:
    return texto[:inicio] + re.sub(r"[^\n]", " ", texto[inicio:fim]) + texto[fim:]


# ---------------------------------------------------------------- CSS


def validar_css(texto: str, *, arquivo: str, modo: str = "template", linha_base: int = 1) -> list[dict[str, Any]]:
    """Achados de um CSS: URL externa (sempre) e cor literal fora de `:root` (modo template)."""
    _exigir_modo(modo)
    linha = _Linhas(texto, linha_base)
    # comentários viram espaço, preservando as quebras de linha
    for m in reversed(list(re.finditer(r"/\*.*?\*/", texto, re.S))):
        texto = _mascarar(texto, m.start(), m.end())
    achados = []
    for m in list(_RE_URL_CSS.finditer(texto)) + list(_RE_IMPORT_CSS.finditer(texto)):
        if _url_externa(m.group(2)):
            achados.append(_achado("url_externa", arquivo, linha(m.start()), f"URL externa: {m.group(2).strip()}"))
    if modo == "template":
        achados.extend(_cores_css(texto, arquivo, linha))
    achados.sort(key=lambda a: (a["linha"] or 0, a["tipo"]))
    return achados


def _cores_css(texto: str, arquivo: str, linha: _Linhas) -> list[dict[str, Any]]:
    achados = []
    pilha: list[bool] = []  # para cada bloco aberto: está dentro de :root?
    inicio = 0
    i = 0
    while i < len(texto):
        c = texto[i]
        if c in "'\"":
            fecha = re.match(r"(['\"])(?:\\.|(?!\1).)*\1", texto[i:], re.S)
            i += fecha.end() if fecha else 1
            continue
        if c == "{":
            prelude = texto[inicio:i].strip()
            eh_root = bool(prelude) and all(s.strip() == ":root" for s in prelude.split(","))
            pilha.append(eh_root or (bool(pilha) and pilha[-1]))
            inicio = i + 1
        elif c in ";}":
            declaracao = texto[inicio:i]
            dentro_root = bool(pilha) and pilha[-1]
            if pilha and not dentro_root and ":" in declaracao:
                achados.extend(_cores_declaracao(declaracao, inicio, arquivo, linha))
            if c == "}" and pilha:
                pilha.pop()
            inicio = i + 1
        i += 1
    return achados


def _cores_declaracao(declaracao: str, deslocamento: int, arquivo: str, linha: _Linhas) -> list[dict[str, Any]]:
    propriedade, _, valor = declaracao.partition(":")
    valor = _RE_URL_CSS.sub(" ", valor)
    valor = _RE_STRING_CSS.sub(" ", valor)
    valor = re.sub(r"--[\w-]+", " ", valor)  # nomes de variáveis (var(--alma-texto)) não são cor
    cores = _cores_literais(valor)
    if not cores:
        return []
    comeco = deslocamento + (len(declaracao) - len(declaracao.lstrip()))
    return [_achado("cor_literal", arquivo, linha(comeco),
                    f"cor literal fora de :root em {propriedade.strip()}: {', '.join(cores)} (use var(--alma-*))")]


# ---------------------------------------------------------------- HTML


class _LeitorHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, list[tuple[str, str | None]], int]] = []
        self.estilos: list[tuple[str, int]] = []
        self._em_style: int | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, attrs, self.getpos()[0]))
        if tag == "style":
            self._em_style = self.getpos()[0]
            self._buffer = []

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag == "style" and self._em_style is not None:
            self.estilos.append(("".join(self._buffer), self._em_style))
            self._em_style = None

    def handle_data(self, data):
        if self._em_style is not None:
            self._buffer.append(data)


def validar_html(texto: str, *, arquivo: str, modo: str = "template") -> list[dict[str, Any]]:
    """Achados de um HTML de slide: `<style>`, atributo `style`, cores de SVG e URLs que carregam."""
    _exigir_modo(modo)
    leitor = _LeitorHtml()
    leitor.feed(texto)
    leitor.close()
    achados = []
    for css, linha_style in leitor.estilos:
        achados.extend(validar_css(css, arquivo=arquivo, modo=modo, linha_base=linha_style))
    for tag, atributos, linha in leitor.tags:
        for nome, valor in atributos:
            valor = valor or ""
            if nome == "style":
                achados.extend(validar_css(f"x{{{valor}}}", arquivo=arquivo, modo=modo, linha_base=linha))
            elif nome in _ATRIBUTOS_COR:
                cores = _cores_literais(valor) if modo == "template" else []
                if cores:
                    achados.append(_achado("cor_literal", arquivo, linha,
                                           f"cor literal no atributo {nome} de <{tag}>: {', '.join(cores)}"))
            elif _carrega_url(tag, nome):
                urls = [u.split()[0] for u in valor.split(",") if u.strip()] if nome == "srcset" else [valor]
                for url in urls:
                    if _url_externa(url):
                        achados.append(_achado("url_externa", arquivo, linha,
                                               f"URL externa em {nome} de <{tag}>: {url.strip()}"))
    achados.sort(key=lambda a: (a["linha"] or 0, a["tipo"]))
    return achados


# ---------------------------------------------------------------- código (TSX/TS/JSX/JS)


def _analisar_js(texto: str) -> tuple[str, dict[int, str]]:
    """(código com comentários e conteúdo de strings trocados por espaço, {início da string: conteúdo}).

    O código de dentro de `${...}` de template literal continua sendo código. Aspa simples ou
    dupla sem fechamento na mesma linha não abre string (apóstrofo em texto de JSX).
    """
    saida = list(texto)
    strings: dict[int, str] = {}
    n = len(texto)

    def apagar(a: int, b: int) -> None:
        for k in range(a, b):
            if saida[k] != "\n":
                saida[k] = " "

    def codigo(i: int, ate_chave: bool) -> int:
        profundidade = 0
        while i < n:
            c = texto[i]
            if texto.startswith("//", i):
                fim = texto.find("\n", i)
                fim = n if fim < 0 else fim
                apagar(i, fim)
                i = fim
                continue
            if texto.startswith("/*", i):
                fim = texto.find("*/", i + 2)
                fim = n if fim < 0 else fim + 2
                apagar(i, fim)
                i = fim
                continue
            if c in "'\"":
                j = i + 1
                while j < n and texto[j] not in (c, "\n"):
                    j += 2 if texto[j] == "\\" else 1
                if j < n and texto[j] == c:
                    strings[i] = texto[i + 1 : j]
                    apagar(i + 1, j)
                    i = j + 1
                else:
                    i += 1
                continue
            if c == "`":
                i = crase(i)
                continue
            if ate_chave:
                if c == "{":
                    profundidade += 1
                elif c == "}":
                    if profundidade == 0:
                        return i
                    profundidade -= 1
            i += 1
        return i

    def crase(i: int) -> int:
        inicio = i
        partes: list[str] = []
        j = i + 1
        trecho = j
        while j < n and texto[j] != "`":
            if texto[j] == "\\":
                j += 2
                continue
            if texto.startswith("${", j):
                partes.append(texto[trecho:j])
                apagar(trecho, j)
                fim = codigo(j + 2, ate_chave=True)
                partes.append(" ")
                j = fim + 1
                trecho = j
                continue
            j += 1
        fim = min(j, n)
        partes.append(texto[trecho:fim])
        apagar(trecho, fim)
        strings[inicio] = "".join(partes)
        return fim + 1

    codigo(0, ate_chave=False)
    return "".join(saida), strings


_RE_IMPORT = re.compile(
    r"(?<![\w$.])import\s+(?:type\s+)?(?:[\w$*{}\s,]+?\s+from\s+)?(?=['\"])"
    r"|(?<![\w$.])export\s+(?:type\s+)?(?:\*(?:\s+as\s+[\w$]+)?|\{[^}]*\})\s*from\s+(?=['\"])"
)
_RE_REQUIRE = re.compile(r"(?<![\w$.])require\s*\(\s*")
_RE_IMPORT_DINAMICO = re.compile(r"(?<![\w$.])import\s*\(")
_RE_FUNCTION = re.compile(r"(?<![\w$])new\s+Function\b|(?<![\w$.])Function\s*\(")
_RE_API = re.compile(r"(?<![\w$])(" + "|".join(APIS_PROIBIDAS) + r")(?![\w$])")
_RE_COLCHETE = re.compile(r"\[\s*(?=['\"`])")


def _modulo_base(modulo: str) -> str:
    partes = modulo.split("/")
    return "/".join(partes[:2]) if modulo.startswith("@") else partes[0]


def _modulo_permitido(modulo: str, permitidos: frozenset[str]) -> bool:
    base = _modulo_base(modulo)
    if base in ("react", "remotion", "@expxmedia/template"):
        return True
    if modulo.startswith("@remotion/") and len(modulo) > len("@remotion/"):
        return True
    return base in permitidos


def validar_codigo(
    texto: str,
    *,
    arquivo: str,
    modo: str = "template",
    permitidos: set[str] | frozenset[str] = frozenset(),
    pasta: Path | None = None,
) -> list[dict[str, Any]]:
    """Achados de um arquivo de código do template.

    `permitidos`: pacotes extras aceitos (já cruzados entre `dependencias` e a lista da galeria).
    `pasta`: a pasta do template; com ela, import relativo que sai da pasta é achado.
    """
    _exigir_modo(modo)
    permitidos = frozenset(permitidos)
    mascarado, strings = _analisar_js(texto)
    linha = _Linhas(texto)
    achados = []
    especificadores: set[int] = set()

    def modulo(inicio: int, especificador: str) -> None:
        especificadores.add(inicio)
        nome = especificador.strip()
        sem_prefixo = nome[5:] if nome.startswith("node:") else nome
        if nome.startswith(("./", "../")) or nome in (".", ".."):
            if pasta is not None:
                alvo = (pasta / PurePosixPath(arquivo).parent / nome).resolve()
                if alvo != pasta.resolve() and pasta.resolve() not in alvo.parents:
                    achados.append(_achado("import_proibido", arquivo, linha(inicio),
                                           f"import relativo sai da pasta do template: {nome}"))
            return
        if _modulo_base(sem_prefixo) in MODULOS_PROIBIDOS:
            achados.append(_achado("import_proibido", arquivo, linha(inicio), f"módulo proibido: {nome}"))
        elif nome.startswith("node:") or not _modulo_permitido(nome, permitidos):
            achados.append(_achado("import_proibido", arquivo, linha(inicio),
                                   f"import fora da lista permitida: {nome} (react, remotion, @remotion/*, "
                                   "@expxmedia/template, ou dependência aceita pela galeria)"))

    for m in _RE_IMPORT.finditer(mascarado):
        if m.end() in strings:
            modulo(m.end(), strings[m.end()])
    for m in _RE_REQUIRE.finditer(mascarado):
        pos = m.end()
        if pos < len(texto) and texto[pos] in "'\"" and pos in strings:
            modulo(pos, strings[pos])
        else:
            achados.append(_achado("api_proibida", arquivo, linha(m.start()), "require dinâmico"))
    for m in _RE_IMPORT_DINAMICO.finditer(mascarado):
        achados.append(_achado("api_proibida", arquivo, linha(m.start()), "import() dinâmico"))
    for m in _RE_FUNCTION.finditer(mascarado):
        achados.append(_achado("api_proibida", arquivo, linha(m.start()), "new Function"))
    for m in _RE_API.finditer(mascarado):
        antes = mascarado[: m.start()].rstrip()
        if antes.endswith("."):
            dono = re.search(r"([\w$]+)\s*(?:\?)?$", antes[:-1].rstrip())
            if not dono or dono.group(1) not in _GLOBAIS:
                continue  # propriedade de outro objeto (ex.: dados.process)
        achados.append(_achado("api_proibida", arquivo, linha(m.start()), f"API proibida: {m.group(1)}"))
    for m in _RE_COLCHETE.finditer(mascarado):
        conteudo = strings.get(m.end(), "")
        if conteudo.strip() in APIS_PROIBIDAS:
            especificadores.add(m.end())
            achados.append(_achado("api_proibida", arquivo, linha(m.start()), f"API proibida: {conteudo.strip()}"))

    for inicio, conteudo in strings.items():
        if inicio in especificadores:
            continue
        for url in re.findall(r"(?:[a-z][a-z0-9+.-]*:)?//[^\s'\"`)]+", conteudo, re.I):
            if _url_externa(url) and not url.lower().startswith(("data:", "blob:")):
                achados.append(_achado("url_externa", arquivo, linha(inicio), f"URL externa: {url}"))
                break
        if modo == "template":
            cores = _cores_literais(conteudo, nomeadas=False)
            if not cores and _RE_NOMEADA.fullmatch(conteudo.strip()):
                cores = [conteudo.strip()]
            if cores:
                achados.append(_achado("cor_literal", arquivo, linha(inicio),
                                       f"cor literal no código: {', '.join(cores)} (use useAlma())"))
    achados.sort(key=lambda a: (a["linha"] or 0, a["tipo"]))
    return achados


# ---------------------------------------------------------------- pasta do template


def validar_template(
    pasta: Path | str,
    *,
    modo: str = "template",
    permitidos_galeria: set[str] | frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Achados de todos os arquivos da pasta do template, inclusive o `template.json`.

    No modo `template`, `template.json` é obrigatório; no `sob_medida`, é conferido se existir.
    Pacote extra só é aceito se estiver em `dependencias` do template **e** em
    `permitidos_galeria`.
    """
    _exigir_modo(modo)
    pasta = Path(pasta)
    achados: list[dict[str, Any]] = []
    dependencias: dict[str, Any] = {}
    manifesto = pasta / "template.json"
    if manifesto.is_file():
        try:
            dados = _arquivos.ler_json(manifesto)
            violacoes = _schema.validar(dados)
        except (_arquivos.ErroArquivo, _schema.ErroTemplateRejeitado) as erro:
            achados.append(_achado("template_rejeitado", "template.json", None, str(erro)))
        else:
            achados.extend(_achado(v["tipo"], "template.json", None, v["mensagem"]) for v in violacoes)
            if isinstance(dados.get("dependencias"), dict):
                dependencias = dados["dependencias"]
    elif modo == "template":
        achados.append(_achado("arquivo_ausente", "template.json", None, "o template não tem template.json"))
    permitidos = frozenset(permitidos_galeria) & frozenset(dependencias)

    for caminho in sorted(pasta.rglob("*")):
        if not caminho.is_file():
            continue
        relativo = caminho.relative_to(pasta)
        if _PASTAS_IGNORADAS.intersection(relativo.parts[:-1]):
            continue
        nome = relativo.as_posix()
        sufixo = caminho.suffix.lower()
        if sufixo not in _EXT_CSS | _EXT_HTML | _EXT_CODIGO:
            continue
        texto = caminho.read_text(encoding="utf-8-sig", errors="replace")
        if sufixo in _EXT_CSS:
            achados.extend(validar_css(texto, arquivo=nome, modo=modo))
        elif sufixo in _EXT_HTML:
            achados.extend(validar_html(texto, arquivo=nome, modo=modo))
        else:
            achados.extend(validar_codigo(texto, arquivo=nome, modo=modo, permitidos=permitidos, pasta=pasta))
    achados.sort(key=lambda a: (a["arquivo"], a["linha"] or 0, a["tipo"]))
    return achados
