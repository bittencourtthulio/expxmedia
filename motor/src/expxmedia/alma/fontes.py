"""Fontes da Alma: Google Fonts em cache local, fonte local da instalação, Inter embarcada (D-21).

- `origem: google`: o CSS do Google Fonts é pedido uma vez, os arquivos woff2 do subconjunto
  latino (pt-BR) são baixados para o cache (`~/.cache/expxmedia/fontes`, ou `$XDG_CACHE_HOME`,
  ou o `cache` passado) e o `@font-face` devolvido aponta para o arquivo local. Da segunda vez
  em diante sai do cache, sem rede: o render continua funcionando offline.
- `origem: local`: `arquivo` relativo à raiz da instalação (M9).
- Sem fonte resolvida (família nula, rede fora, arquivo ausente): a Inter embarcada no motor,
  **com aviso** — o leitor não troca a fonte em silêncio (M7). Fonte de sistema nunca (D-21).

A URL base do Google Fonts é parâmetro (`url_base`), para os testes usarem o stub HTTP.

Uso:

    from expxmedia.alma import fontes
    fonte = fontes.resolver_fonte(alma, "titulo", raiz=raiz)   # fonte.css, fonte.arquivos, fonte.aviso
    css, resolvidas = fontes.css_fontes(alma, raiz=raiz)      # @font-face de título, texto e reserva
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests

from expxmedia.alma.tokens import FAMILIA_RESERVA, PAPEIS_FONTE
from expxmedia.nucleo import arquivos as _arquivos
from expxmedia.nucleo.ids import slug

__all__ = [
    "FonteResolvida",
    "URL_GOOGLE_FONTS",
    "PASTA_INTER",
    "cache_padrao",
    "resolver_fonte",
    "css_fontes",
    "css_inter_embarcada",
]

URL_GOOGLE_FONTS = "https://fonts.googleapis.com"
PASTA_INTER = Path(__file__).resolve().parents[1] / "recursos" / "fontes" / "Inter"
_INTER_PESOS = {400: "inter-latin-400-normal.woff2", 700: "inter-latin-700-normal.woff2"}

# Pedidos ao Google Fonts, em ordem: eixo variável inteiro; pesos fixos de título e texto;
# a família sem eixo. O Google responde 400 quando a família não tem o eixo ou o peso pedido.
_EIXOS = ("wght@100..900", "wght@400;700", None)
# Subconjuntos baixados: o que o português usa.
_SUBCONJUNTOS = {"latin", "latin-ext"}
# Sem um navegador moderno no User-Agent, o Google serve TTF em vez de woff2.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_FORMATOS = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}
_BLOCO = re.compile(r"(?:/\*\s*([\w-]+)\s*\*/\s*)?(@font-face\s*\{[^}]*\})")
_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)")


@dataclass
class FonteResolvida:
    papel: str
    familia: str
    origem: str  # google · local · embarcada
    arquivos: list[Path] = field(default_factory=list)
    css: str = ""
    aviso: str | None = None


class _Falha(Exception):
    pass


def cache_padrao() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "expxmedia" / "fontes"


def resolver_fonte(
    alma: Any,
    papel: str,
    *,
    raiz: Path | str | None = None,
    cache: Path | str | None = None,
    url_base: str = URL_GOOGLE_FONTS,
    timeout: float = 30,
) -> FonteResolvida:
    """Resolve a fonte do `papel` (`titulo` ou `texto`) da Alma para arquivos locais."""
    if papel not in PAPEIS_FONTE:
        raise ValueError(f"papel de fonte desconhecido: {papel!r} (válidos: {', '.join(PAPEIS_FONTE)})")
    dados = alma.dados if hasattr(alma, "dados") else alma
    fonte = (((dados.get("visual") or {}).get("fontes") or {}).get(papel)) or {}
    familia = fonte.get("familia")
    origem = fonte.get("origem")
    if not isinstance(familia, str) or not familia.strip():
        return _reserva(papel, f"visual.fontes.{papel} sem família: usando {FAMILIA_RESERVA} embarcada")
    familia = familia.strip()
    try:
        if origem == "google":
            caminhos, css = _google(familia, Path(cache) if cache is not None else cache_padrao(), url_base, timeout)
        elif origem == "local":
            caminhos, css = _local(familia, fonte.get("arquivo"), raiz)
        else:
            raise _Falha(f"origem {origem!r} desconhecida")
    except _Falha as falha:
        return _reserva(papel, f"fonte '{familia}' ({papel}) não resolvida: {falha}; usando {FAMILIA_RESERVA} embarcada")
    return FonteResolvida(papel=papel, familia=familia, origem=origem, arquivos=caminhos, css=css)


def css_fontes(
    alma: Any,
    *,
    raiz: Path | str | None = None,
    cache: Path | str | None = None,
    url_base: str = URL_GOOGLE_FONTS,
    timeout: float = 30,
) -> tuple[str, list[FonteResolvida]]:
    """(@font-face de título, texto e da Inter embarcada, resoluções por papel).

    A Inter embarcada vai sempre junto: é a reserva da pilha de `--alma-fonte-*`.
    """
    resolvidas = [
        resolver_fonte(alma, papel, raiz=raiz, cache=cache, url_base=url_base, timeout=timeout)
        for papel in PAPEIS_FONTE
    ]
    blocos = [r.css for r in resolvidas if r.origem != "embarcada"]
    blocos.append(css_inter_embarcada())
    return "\n".join(dict.fromkeys(blocos)), resolvidas


def css_inter_embarcada() -> str:
    return "".join(_font_face(FAMILIA_RESERVA, PASTA_INTER / nome, peso=peso) for peso, nome in _INTER_PESOS.items())


# ---------------------------------------------------------------- google


def _google(familia: str, cache: Path, url_base: str, timeout: float) -> tuple[list[Path], str]:
    pasta = cache / (slug(familia) or hashlib.sha1(familia.encode()).hexdigest()[:12])
    css_cache = pasta / "fontes.css"
    manifesto = pasta / "arquivos.json"
    em_cache = _ler_cache(pasta, css_cache, manifesto)
    if em_cache is not None:
        return em_cache

    css_remoto = _pedir_css(familia, url_base, timeout)
    blocos = []
    for subconjunto, bloco in _BLOCO.findall(css_remoto):
        if subconjunto and subconjunto not in _SUBCONJUNTOS:
            continue
        blocos.append(bloco)
    if not blocos:
        raise _Falha("o Google Fonts não devolveu @font-face do subconjunto latino")

    baixados: dict[str, Path] = {}
    saida = []
    for bloco in blocos:
        achado = _URL.search(bloco)
        if achado is None:
            continue
        url = urljoin(url_base.rstrip("/") + "/", achado.group(1))
        if url not in baixados:
            baixados[url] = _baixar(url, pasta, timeout)
        saida.append(_URL.sub(lambda _m, p=baixados[url]: f"url('{p.resolve().as_uri()}')", bloco, count=1))
    if not saida:
        raise _Falha("o CSS do Google Fonts não tem url() de arquivo")
    css = "\n".join(saida) + "\n"
    css_cache.parent.mkdir(parents=True, exist_ok=True)
    css_cache.write_text(css, encoding="utf-8")
    arquivos = list(dict.fromkeys(baixados.values()))
    _arquivos.gravar_json(manifesto, [p.name for p in arquivos])
    return arquivos, css


def _ler_cache(pasta: Path, css_cache: Path, manifesto: Path) -> tuple[list[Path], str] | None:
    try:
        nomes = _arquivos.ler_json(manifesto)
        css = css_cache.read_text(encoding="utf-8")
    except (OSError, _arquivos.ErroArquivo):
        return None
    caminhos = [pasta / n for n in nomes] if isinstance(nomes, list) else []
    if not caminhos or not all(p.is_file() and p.stat().st_size > 0 for p in caminhos):
        return None
    return caminhos, css


def _pedir_css(familia: str, url_base: str, timeout: float) -> str:
    ultimo = ""
    for eixo in _EIXOS:
        parametro = f"{familia}:{eixo}" if eixo else familia
        try:
            resposta = requests.get(
                url_base.rstrip("/") + "/css2",
                params={"family": parametro, "display": "swap"},
                headers={"User-Agent": _USER_AGENT},
                timeout=timeout,
            )
        except (requests.RequestException, ConnectionError) as erro:
            raise _Falha(f"Google Fonts inacessível ({type(erro).__name__})") from None
        if resposta.status_code == 200:
            return resposta.text
        ultimo = f"Google Fonts respondeu {resposta.status_code}"
        if resposta.status_code != 400:
            break
    raise _Falha(ultimo)


def _baixar(url: str, pasta: Path, timeout: float) -> Path:
    nome = Path(urlsplit(url).path).name
    if not nome or Path(nome).suffix.lower() not in _FORMATOS:
        nome = hashlib.sha1(url.encode()).hexdigest()[:16] + ".woff2"
    destino = pasta / nome
    if destino.is_file() and destino.stat().st_size > 0:
        return destino
    try:
        resposta = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=timeout)
    except (requests.RequestException, ConnectionError) as erro:
        raise _Falha(f"download da fonte falhou ({type(erro).__name__})") from None
    if resposta.status_code != 200 or not resposta.content:
        raise _Falha(f"download da fonte respondeu {resposta.status_code}")
    pasta.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".tmp")
    temporario.write_bytes(resposta.content)
    os.replace(temporario, destino)
    return destino


# ---------------------------------------------------------------- local e reserva


def _local(familia: str, arquivo: Any, raiz: Path | str | None) -> tuple[list[Path], str]:
    if not isinstance(arquivo, str) or not arquivo.strip():
        raise _Falha("origem local sem visual.fontes.*.arquivo")
    caminho = Path(arquivo)
    if not caminho.is_absolute():
        if raiz is None:
            raise _Falha("fonte local relativa sem a raiz da instalação")
        caminho = Path(raiz) / caminho
    caminho = caminho.resolve()
    if not caminho.is_file():
        raise _Falha(f"arquivo da fonte não encontrado: {Path(arquivo).name}")
    if caminho.suffix.lower() not in _FORMATOS:
        raise _Falha(f"formato de fonte não suportado: {caminho.suffix or '(sem extensão)'}")
    return [caminho], _font_face(familia, caminho, peso=None)


def _reserva(papel: str, aviso: str) -> FonteResolvida:
    return FonteResolvida(
        papel=papel,
        familia=FAMILIA_RESERVA,
        origem="embarcada",
        arquivos=[PASTA_INTER / nome for nome in _INTER_PESOS.values()],
        css=css_inter_embarcada(),
        aviso=aviso,
    )


def _font_face(familia: str, caminho: Path, peso: int | None) -> str:
    formato = _FORMATOS.get(caminho.suffix.lower(), "woff2")
    nome = familia.replace("\\", "\\\\").replace("'", "\\'")
    linha_peso = f"  font-weight: {peso};\n" if peso is not None else "  font-weight: 100 900;\n"
    return (
        "@font-face {\n"
        f"  font-family: '{nome}';\n"
        "  font-style: normal;\n"
        f"{linha_peso}"
        "  font-display: block;\n"
        f"  src: url('{caminho.resolve().as_uri()}') format('{formato}');\n"
        "}\n"
    )
