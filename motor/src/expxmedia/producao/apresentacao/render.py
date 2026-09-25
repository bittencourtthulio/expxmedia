"""Render da apresentação em vídeo: MP4 16:9 do deck inteiro e um PNG por slide.

Porte de `render` + `scripts/render.mjs` da origem (youtube-squad), sobre o runner do núcleo
(`expxmedia.motion.remotion`, D-17, D-46):

- a composição `Apresentacao` do kit desenha o deck inteiro, `FRAMES_POR_SLIDE` quadros por slide
  (240 = 8 s a 30 fps, como na origem); o MP4 sai h264 em 1920×1080;
- o PNG de cada slide é o **último quadro** do trecho dele (a origem gravava `renderStill` do último
  quadro de cada composição), tirado com um bundle só;
- imagem citada e ausente em `ativos/` vira `null` numa cópia do deck, com aviso: uma `<Img>` que
  falha derrubaria o render inteiro (origem: D-48 da apresentação);
- o que é da empresa (cores, fontes, nome, CTA) entra por props a partir da Alma (M13); as fontes e as
  imagens vão para um public dir temporário, com caminhos relativos a ele (M9).

A origem gravava um MP4 por slide para o palco; aqui o palco é HTML (`palco.py`) e o MP4 é o vídeo
da apresentação inteira, extra da peça (CONTRATO-peca, "Apresentação e aula").

Uso:

    from expxmedia.producao.apresentacao import render
    r = render.renderizar(deck, alma, "saida/", raiz=raiz, ativos="ativos/")
    # {"mp4": Path, "pngs": [Path, ...], "avisos": [...], "segundos": 41.2, "quadros": 2160}
"""
from __future__ import annotations

import re
import shutil
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Any
from urllib.request import url2pathname

from expxmedia.alma import fontes as _fontes
from expxmedia.motion import remotion
from expxmedia.producao.apresentacao import deck as _deck
from expxmedia.producao.apresentacao import palco as _palco

__all__ = [
    "COMPOSICAO",
    "FRAMES_POR_SLIDE",
    "LARGURA",
    "ALTURA",
    "NOME_MP4",
    "nome_png",
    "props_alma",
    "props",
    "quadros_dos_pngs",
    "renderizar",
]

COMPOSICAO = "Apresentacao"
# origem: youtube-squad/apresentacoes/motion/src/deck.ts:45 (240 quadros por slide)
FRAMES_POR_SLIDE = 240
# origem: youtube-squad/apresentacoes/motion/src/deck.ts:43-44
LARGURA = 1920
ALTURA = 1080
NOME_MP4 = "apresentacao.mp4"
_RE_BLOCO = re.compile(r"@font-face\s*\{[^}]*\}")
_RE_PESO = re.compile(r"font-weight:\s*(\d+)\s*;")
_RE_ESTILO = re.compile(r"font-style:\s*(\w+)\s*;")
_RE_URL = re.compile(r"url\(\s*['\"]?(file://[^'\")]+)['\"]?\s*\)")


def nome_png(n: int) -> str:
    """`slide_NN.png`, como os slides das outras peças (CONTRATO-peca)."""
    return f"slide_{n:02d}.png"


def quadros_dos_pngs(total: int, frames_por_slide: int = FRAMES_POR_SLIDE) -> list[int]:
    """O último quadro do trecho de cada slide. origem: youtube-squad/apresentacoes/motion/scripts/render.mjs:49-55"""
    return [(i + 1) * frames_por_slide - 1 for i in range(total)]


def _dados(alma: Any) -> dict[str, Any]:
    return (alma.dados if hasattr(alma, "dados") else alma) or {}


def _arquivos_da_fonte(resolvida: _fontes.FonteResolvida) -> list[tuple[Path, int | None, str | None]]:
    """(arquivo, peso, estilo) de cada @font-face da fonte resolvida; peso None = faixa (fonte variável)."""
    saida: list[tuple[Path, int | None, str | None]] = []
    vistos: set[Path] = set()
    for bloco in _RE_BLOCO.findall(resolvida.css):
        url = _RE_URL.search(bloco)
        if url is None:
            continue
        caminho = Path(url2pathname(urllib.parse.urlsplit(url.group(1)).path)).resolve()
        if caminho in vistos or not caminho.is_file():
            continue
        vistos.add(caminho)
        peso = _RE_PESO.search(bloco)
        estilo = _RE_ESTILO.search(bloco)
        saida.append((caminho, int(peso.group(1)) if peso else None, estilo.group(1) if estilo else None))
    if not saida:
        saida = [(p.resolve(), None, None) for p in resolvida.arquivos if p.is_file()]
    return saida


def props_alma(
    alma: Any,
    publico: Path,
    *,
    raiz: Path | str | None = None,
    cache_fontes: Path | str | None = None,
    url_fontes: str = _fontes.URL_GOOGLE_FONTS,
) -> tuple[dict[str, Any], list[str]]:
    """Props `alma` do kit (cores, fontes em arquivo no public dir, porta-voz e canal) e avisos de fonte."""
    dados = _dados(alma)
    cores = dict((dados.get("visual") or {}).get("cores") or {})
    fontes: dict[str, Any] = {}
    avisos: list[str] = []
    pasta_fontes = publico / "fontes"
    pasta_fontes.mkdir(parents=True, exist_ok=True)
    for papel in ("titulo", "texto"):
        r = _fontes.resolver_fonte(alma, papel, raiz=raiz, cache=cache_fontes, url_base=url_fontes)
        if r.aviso:
            avisos.append(r.aviso)
        arquivos = []
        for caminho, peso, estilo in _arquivos_da_fonte(r):
            destino = pasta_fontes / f"{papel}-{caminho.name}"
            shutil.copyfile(caminho, destino)
            arquivos.append({"caminho": destino.relative_to(publico).as_posix(), "peso": peso, "estilo": estilo})
        fontes[papel] = {"familia": r.familia, "arquivos": arquivos}
    return {"cores": cores, "fontes": fontes, "porta_voz": None, "canal": None}, avisos


def props(
    d: dict[str, Any],
    alma: Any,
    publico: Path,
    *,
    ativos: Path | str | None = None,
    raiz: Path | str | None = None,
    cache_fontes: Path | str | None = None,
    url_fontes: str = _fontes.URL_GOOGLE_FONTS,
    frames_por_slide: int = FRAMES_POR_SLIDE,
) -> tuple[dict[str, Any], list[str]]:
    """Props da composição `Apresentacao`: deck com o CTA da Alma e as imagens no public dir, e avisos."""
    completo, avisos = _deck.completar_cta(d, alma)
    resolvido, avisos_img = _palco.resolver_imagens(completo, ativos)
    avisos += avisos_img
    (publico / "ativos").mkdir(parents=True, exist_ok=True)

    def publicar(arq: Path | None) -> str | None:
        if arq is None:
            return None
        destino = publico / "ativos" / arq.name
        shutil.copyfile(arq, destino)
        return destino.relative_to(publico).as_posix()

    tema = resolvido.get("tema")
    if isinstance(tema, dict):
        tema = {"nome": tema.get("nome"), "cor": tema.get("cor"), "logo": publicar(tema.get("logo"))}
    slides = []
    for s in resolvido["slides"]:
        s = dict(s)
        if "imagem" in s:
            s["imagem"] = publicar(s["imagem"])
        slides.append(s)
    alma_props, avisos_fonte = props_alma(alma, publico, raiz=raiz, cache_fontes=cache_fontes, url_fontes=url_fontes)
    avisos += avisos_fonte
    idioma = (_dados(alma).get("empresa") or {}).get("idioma")
    return {
        "alma": alma_props,
        "deck": {"titulo": resolvido.get("titulo"), "tema": tema, "slides": slides},
        "rotulo": _palco.rotulo(completo, alma),
        "empresa": _palco._empresa(alma),
        "idioma": idioma if isinstance(idioma, str) and idioma.strip() else None,
        "framesPorSlide": frames_por_slide,
    }, avisos


def renderizar(
    d: dict[str, Any],
    alma: Any,
    pasta: Path | str,
    *,
    raiz: Path | str | None = None,
    ativos: Path | str | None = None,
    pasta_pngs: Path | str | None = None,
    cache_fontes: Path | str | None = None,
    url_fontes: str = _fontes.URL_GOOGLE_FONTS,
    frames_por_slide: int = FRAMES_POR_SLIDE,
    contar_slides: bool = True,
    opcoes_runner: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Renderiza `pasta/apresentacao.mp4` e `slide_NN.png` (em `pasta_pngs`, ou `pasta`).

    Deck inválido levanta `palco.ErroDeck` antes de qualquer render. `contar_slides=False` aceita um
    trecho do deck (prévia); a produção sempre valida o deck inteiro.
    """
    achados = _deck.validar(d, alma=alma, contar_slides=contar_slides)
    if achados:
        raise _palco.ErroDeck(achados)
    if not isinstance(frames_por_slide, int) or isinstance(frames_por_slide, bool) or frames_por_slide < 1:
        raise ValueError("frames_por_slide é um inteiro positivo")
    pasta = Path(pasta)
    pasta_pngs = Path(pasta_pngs) if pasta_pngs is not None else pasta
    pasta.mkdir(parents=True, exist_ok=True)
    pasta_pngs.mkdir(parents=True, exist_ok=True)
    inicio = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=".render-", dir=pasta) as tmp:
        publico = Path(tmp) / "publico"
        publico.mkdir()
        entrada, avisos = props(d, alma, publico, ativos=ativos, raiz=raiz, cache_fontes=cache_fontes,
                                url_fontes=url_fontes, frames_por_slide=frames_por_slide)
        opcoes = dict(opcoes_runner or {})
        mp4 = remotion.renderizar(COMPOSICAO, pasta / NOME_MP4, entrada, public_dir=publico, **opcoes)
        total = len(d["slides"])
        pngs = remotion.stills(COMPOSICAO, quadros_dos_pngs(total, frames_por_slide), pasta_pngs, entrada,
                               nomes=[nome_png(n) for n in range(1, total + 1)], public_dir=publico, **opcoes)
    return {
        "mp4": mp4,
        "pngs": pngs,
        "avisos": avisos,
        "segundos": round(time.monotonic() - inicio, 1),
        "quadros": total * frames_por_slide,
    }
