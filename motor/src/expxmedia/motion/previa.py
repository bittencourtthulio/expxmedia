"""Prévia de uma peça de motion: um quadro de cada cena com as guias da área segura e uma folha com todos.

Porta de `Instragram-Videos/pipeline/render_remotion.py:177-207` (`previa`): o quadro de cada cena é o de 60%
da duração, o still sai em escala 0,3, as guias vermelhas marcam y=220 e y=1500 do quadro 1080x1920 (a área
segura, ver `kit-remotion/src/kit/anim.ts`), cada imagem leva o número e o id da cena, e a folha junta tudo em
5 colunas, em JPEG qualidade 85. É o que se abre ao lado da referência para cobrar enquadramento, composição e
ordem de cena antes do render inteiro.

Diferença da origem: todos os stills saem de um bundle só (`remotion.stills`), e cada imagem fica gravada ao
lado da folha (`previa-NN-<id>.png`), não só a folha.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from expxmedia.motion import remotion

__all__ = ["ESCALA", "POSICAO", "GUIAS", "COR_GUIA", "COLUNAS", "QUALIDADE", "quadro_da_cena", "gerar_previa"]

ESCALA = 0.3  # origem: Instragram-Videos/pipeline/render_remotion.py:184
POSICAO = 0.6  # origem: Instragram-Videos/pipeline/render_remotion.py:189 (60% da cena)
GUIAS = (220, 1500)  # origem: Instragram-Videos/pipeline/render_remotion.py:196 e kit/anim.ts:16 (área segura)
COR_GUIA = (255, 0, 0)  # origem: Instragram-Videos/pipeline/render_remotion.py:197
LARGURA_GUIA = 2  # origem: Instragram-Videos/pipeline/render_remotion.py:197
COLUNAS = 5  # origem: Instragram-Videos/pipeline/render_remotion.py:200
QUALIDADE = 85  # origem: Instragram-Videos/pipeline/render_remotion.py:206


def quadro_da_cena(cena: dict[str, Any], posicao: float = POSICAO) -> int:
    """Quadro absoluto a `posicao` da cena. origem: Instragram-Videos/pipeline/render_remotion.py:189"""
    return int(cena["inicio"]) + int(int(cena["dur"]) * posicao)


def _cenas(timeline: dict[str, Any] | Path | str) -> list[dict[str, Any]]:
    if not isinstance(timeline, dict):
        timeline = json.loads(Path(timeline).read_text(encoding="utf-8"))
    cenas = timeline.get("cenas") or []
    if not cenas:
        raise ValueError("linha do tempo sem cenas: nada para prever")
    return cenas


def _nome(n: int, cena_id: str) -> str:
    seguro = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(cena_id)) or "cena"
    return f"previa-{n + 1:02d}-{seguro}.png"


def _marcar(png: Path, n: int, cena_id: str, escala: float) -> Image.Image:
    im = Image.open(png).convert("RGB")
    d = ImageDraw.Draw(im)
    for y in GUIAS:
        d.line([(0, y * escala), (im.width, y * escala)], fill=COR_GUIA, width=LARGURA_GUIA)
    d.text((6, 4), f"{n + 1} {cena_id}", fill=COR_GUIA)
    im.save(png)
    return im


def gerar_previa(
    composicao: str,
    timeline: dict[str, Any] | Path | str,
    pasta: Path | str,
    props: dict[str, Any] | None = None,
    *,
    escala: float = ESCALA,
    **opcoes_render: Any,
) -> dict[str, Any]:
    """Stills a 60% de cada cena com as guias 220/1500 e a folha `previa.jpg` em `pasta`.

    `opcoes_render` vai para `remotion.stills` (versao, projeto, public_dir...). Devolve
    `{"imagens": [png, ...], "folha": jpg, "quadros": [n, ...]}`.
    """
    cenas = _cenas(timeline)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    quadros = [quadro_da_cena(c) for c in cenas]
    nomes = [_nome(n, c.get("id", "")) for n, c in enumerate(cenas)]
    try:
        pngs = remotion.stills(composicao, quadros, pasta, props, escala=escala, nomes=nomes, **opcoes_render)
    except remotion.ErroRemotion as erro:
        raise remotion.ErroRemotion(f"prévia de {composicao}: {erro}") from erro
    fotos = [_marcar(png, n, c.get("id", ""), escala) for n, (png, c) in enumerate(zip(pngs, cenas))]

    w, h = fotos[0].size
    colunas = min(COLUNAS, len(fotos))
    linhas = (len(fotos) + COLUNAS - 1) // COLUNAS
    folha = Image.new("RGB", (w * colunas, h * linhas), "white")
    for i, im in enumerate(fotos):
        folha.paste(im, ((i % COLUNAS) * w, (i // COLUNAS) * h))
    destino = pasta / "previa.jpg"
    folha.save(destino, quality=QUALIDADE)
    return {"imagens": list(pngs), "folha": destino, "quadros": quadros}
