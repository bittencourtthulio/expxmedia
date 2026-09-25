"""Contraste medido no PNG, com e sem a tinta do texto (D-20).

A medição do DOM não vê o que o PNG vê: texto atrás de um enfeite, texto sobre foto, forma ou
divisa de cor. Por isso o slide é fotografado duas vezes — com o texto e sem a tinta dele — e,
em cada caixa de texto:

1. a **tinta** é o que só existe com o texto ligado (distância RGB > 40 entre as duas fotos);
   tinta em menos de 2% da caixa é texto que não aparece (coberto ou da cor do fundo);
2. o que está **atrás** é o resto; traço da cor do próprio texto (sublinhado, ícone) sai da
   conta enquanto for menos de 15% da caixa;
3. o contraste WCAG é cobrado entre a cor da tinta (composta com o fundo, se tiver alfa) e o
   **ponto pior** do que está atrás: os percentis 5% e 95% de luminância. Degradê suave passa;
   metade de faixa, foto e forma atravessando a palavra não passam.

`data-sobre` (palavra que é desenho, atravessada de propósito) e texto pintado pelo fundo
(`background-clip: text`) saem da comparação por pixel; `decorativo` nem entra nas caixas.

Uso:

    from expxmedia.render_html import contraste
    fundo = contraste.foto_sem_tinta(pagina, recorte)
    achados = contraste.conferir_leitura(png, fundo, caixas, {"contraste": 3.0})
"""
from __future__ import annotations

import io
import re
from typing import Any, Iterable, Sequence

import numpy as np

__all__ = [
    "DISTANCIA_TINTA",
    "TINTA_MINIMA",
    "TRACO_DO_TEXTO",
    "PERCENTIS",
    "BALDE",
    "SEM_TINTA_JS",
    "VOLTA_TINTA_JS",
    "rgb_de",
    "luminancia",
    "razao",
    "distancia_cor",
    "dominante",
    "conferir_leitura",
    "foto_sem_tinta",
]

DISTANCIA_TINTA = 40      # origem: Instagram-Carrosseis/galeria/_galeria.py:1417 (soma |ΔR|+|ΔG|+|ΔB| que separa tinta de fundo)
TINTA_MINIMA = 0.02       # origem: Instagram-Carrosseis/galeria/_galeria.py:1425 (abaixo disto o texto não aparece no PNG)
TRACO_DO_TEXTO = 0.15     # origem: Instagram-Carrosseis/galeria/_galeria.py:1437 (traço da cor do texto que ainda não é fundo)
PERCENTIS = (0.05, 0.95)  # origem: Instagram-Carrosseis/galeria/_galeria.py:1440 (ponto pior do fundo: escuro e claro)
BALDE = 24                # origem: Instagram-Carrosseis/galeria/_galeria.py:1393 (cor dominante por baldes)
MARGEM_CAIXA = (2, 1)     # origem: Instagram-Carrosseis/galeria/_galeria.py:1413 (a caixa encolhe 2 px no início e 1 px no fim)
CAIXA_MINIMA = 8          # origem: Instagram-Carrosseis/galeria/_galeria.py:1414 (caixa menor que isto não se mede)
FUNDO_UNIFORME = 0.05     # origem: Instagram-Carrosseis/galeria/_galeria.py:1444 (diferença de luminância que ainda é "o fundo")

SEM_TINTA_JS = """
() => {
  // origem: Instagram-Carrosseis/galeria/_galeria.py:1345-1360
  // apaga só a tinta do texto, e só de quem tem texto direto: enfeite em currentColor continua pintado,
  // então o PNG que sobra é exatamente o que está ATRÁS do texto.
  const marcados = [];
  for (const e of document.querySelectorAll('.slide, .slide *')) {
    if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    marcados.push(e);
    e.style.setProperty('color', 'transparent', 'important');
    e.style.setProperty('text-shadow', 'none', 'important');
    if (e instanceof SVGElement) e.style.setProperty('fill', 'transparent', 'important');
  }
  window.__semTinta = marcados;
  return marcados.length;
}
"""

VOLTA_TINTA_JS = """
() => { for (const e of window.__semTinta || []) { e.style.removeProperty('color'); e.style.removeProperty('text-shadow'); e.style.removeProperty('fill'); } }
"""

_COR_SRGB = re.compile(
    r"^\s*color\(\s*srgb\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s*(?:/\s*([-+\d.eE]+%?)\s*)?\)\s*$", re.I
)


def rgb_de(css: str | None, fundo: Sequence[int] = (255, 255, 255)) -> tuple[int, int, int]:
    """A cor do texto como ela aparece: `rgba(...)` e `color-mix(...)` chegam com alfa, e o que se
    lê é a composição dela com o que está atrás. Sem isso, texto translúcido mede contraste que
    ninguém vê. Origem: Instagram-Carrosseis/galeria/_galeria.py:1365-1372.

    Correção sobre a origem: o Chromium serializa `color-mix()` como `color(srgb r g b / a)` com
    canais de 0 a 1; a origem lia esses números como 0–255 (base/renderizar-html.md, risco
    anotado). Aqui eles são escalados para 0–255 antes da composição.
    """
    srgb = _COR_SRGB.match(css or "")
    if srgb:
        canais = [min(1.0, max(0.0, float(v))) * 255 for v in srgb.groups()[:3]]
        alfa_txt = srgb.group(4)
        alfa = 1.0 if alfa_txt is None else (float(alfa_txt[:-1]) / 100 if alfa_txt.endswith("%") else float(alfa_txt))
        return tuple(int(round(c * alfa + f * (1 - alfa))) for c, f in zip(canais, fundo))  # type: ignore[return-value]
    achado = [float(v) for v in re.findall(r"[\d.]+", css or "")]
    if len(achado) < 3:
        return (0, 0, 0)
    cor, alfa = tuple(int(v) for v in achado[:3]), (achado[3] if len(achado) > 3 else 1.0)
    return tuple(int(round(c * alfa + f * (1 - alfa))) for c, f in zip(cor, fundo))  # type: ignore[return-value]


def _canal(v: float) -> float:
    # origem: Instagram-Carrosseis/galeria/_galeria.py:1376-1380 (luminância relativa WCAG)
    v /= 255
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


_LUT = np.array([_canal(v) for v in range(256)], dtype=np.float64)


def luminancia(cor: Sequence[int]) -> float:
    r, g, b = (_canal(c) for c in cor)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _luminancias(pixels: np.ndarray) -> np.ndarray:
    """A mesma conta de `luminancia`, na mesma ordem de operações, para um vetor de pixels."""
    return 0.2126 * _LUT[pixels[:, 0]] + 0.7152 * _LUT[pixels[:, 1]] + 0.0722 * _LUT[pixels[:, 2]]


def razao(a: Sequence[int], b: Sequence[int]) -> float:
    """Razão WCAG entre duas cores: 1 é invisível, 21 é preto no branco. Abaixo de 3 não se lê texto grande."""
    la, lb = luminancia(a), luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def distancia_cor(a: Sequence[int], b: Sequence[int]) -> int:
    return sum(abs(x - y) for x, y in zip(a, b))


def _como_matriz(pixels: Iterable[Sequence[int]] | np.ndarray) -> np.ndarray:
    matriz = np.asarray(pixels if isinstance(pixels, np.ndarray) else list(pixels), dtype=np.int64)
    return matriz.reshape(-1, 3) if matriz.size else np.zeros((0, 3), dtype=np.int64)


def dominante(pixels: Iterable[Sequence[int]] | np.ndarray, balde: int = BALDE) -> tuple[tuple[int, int, int], float]:
    """A cor mais comum, em baldes: o antialias e o ruído de JPEG não contam como cor nova.

    Empate: vence o balde que apareceu primeiro na varredura, como no `max` sobre o dicionário
    de contagem da origem (Instagram-Carrosseis/galeria/_galeria.py:1393-1402).
    """
    matriz = _como_matriz(pixels)
    if not len(matriz):
        return (255, 255, 255), 1.0
    chaves = matriz // balde
    codigo = (chaves[:, 0] * 1024 + chaves[:, 1]) * 1024 + chaves[:, 2]
    unicos, primeiro, contagem = np.unique(codigo, return_index=True, return_counts=True)
    maior = contagem.max()
    vencedor = int(np.argmin(np.where(contagem == maior, primeiro, np.iinfo(np.int64).max)))
    escolhido = chaves[primeiro[vencedor]]
    return tuple(int(c) * balde + balde // 2 for c in escolhido), int(contagem[vencedor]) / len(matriz)  # type: ignore[return-value]


def _achado(tipo: str, detalhe: str) -> dict[str, str]:
    return {"tipo": tipo, "detalhe": detalhe}


def _abrir(png: bytes) -> np.ndarray:
    from PIL import Image

    with Image.open(io.BytesIO(png)) as img:
        return np.asarray(img.convert("RGB"), dtype=np.int64)


def conferir_leitura(png: bytes, fundo_png: bytes, caixas: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, str]]:
    """Compara o slide com o mesmo slide sem a tinta do texto. O que sobra é o que está atrás de
    cada palavra: o texto aparece? tem contraste no ponto pior do que está atrás?

    Origem: Instagram-Carrosseis/galeria/_galeria.py:1405-1446, com os mesmos limiares.
    Achados: `texto_invisivel` e `contraste_baixo`.
    """
    arte, fundo = _abrir(png), _abrir(fundo_png)
    altura, largura = arte.shape[:2]
    achados: list[dict[str, str]] = []
    for c in caixas:
        x0 = max(0, int(c["x1"]) + MARGEM_CAIXA[0])
        y0 = max(0, int(c["y1"]) + MARGEM_CAIXA[0])
        x1 = min(largura, int(c["x2"]) - MARGEM_CAIXA[1])
        y1 = min(altura, int(c["y2"]) - MARGEM_CAIXA[1])
        if x1 - x0 < CAIXA_MINIMA or y1 - y0 < CAIXA_MINIMA:
            continue
        pa = arte[y0:y1, x0:x1].reshape(-1, 3)
        pb = fundo[y0:y1, x0:x1].reshape(-1, 3)
        total = len(pa)
        distancia = np.abs(pa - pb).sum(axis=1)
        tinta = distancia > DISTANCIA_TINTA              # o que só existe com o texto ligado
        atras = pb[~tinta]
        cor_fundo, _ = dominante(atras if len(atras) else pb)
        if c.get("pintura") or c.get("sobre"):
            # `pintura`: texto pintado pelo próprio fundo (background-clip: text) — a tinta não é a cor computada.
            # `sobre` (data-sobre): palavra que é desenho, não leitura, atravessada de propósito por foto ou forma.
            continue
        if int(tinta.sum()) < TINTA_MINIMA * total:
            achados.append(_achado("texto_invisivel", f"{c['quem']}: o texto não aparece no PNG "
                                                      "(coberto por outro elemento, ou da mesma cor do que está atrás)"))
            continue
        cor_tinta = rgb_de(c.get("cor"), cor_fundo)
        if not len(atras):
            atras = pb
        do_texto = np.abs(atras - np.asarray(cor_tinta)).sum(axis=1) <= DISTANCIA_TINTA
        if 0 < int(do_texto.sum()) < TRACO_DO_TEXTO * total:
            atras = atras[~do_texto]
        lumes = np.sort(_luminancias(atras if len(atras) else pb))
        n = len(lumes) - 1
        claro, escuro = float(lumes[int(PERCENTIS[1] * n)]), float(lumes[int(PERCENTIS[0] * n)])
        tom = luminancia(cor_tinta)
        pior = min((max(tom, x) + 0.05) / (min(tom, x) + 0.05) for x in (claro, escuro))
        if pior < cfg["contraste"]:
            onde = "o fundo" if abs(claro - escuro) < FUNDO_UNIFORME else "o ponto pior do que está atrás (foto, forma ou divisa de cor)"
            achados.append(_achado("contraste_baixo", f"{c['quem']}: contraste {pior:.1f}:1 entre o texto e {onde} "
                                                      f"(o mínimo é {cfg['contraste']:.0f}:1)"))
    return achados


def foto_sem_tinta(pagina: Any, recorte: dict[str, int]) -> bytes:
    """Fotografa o slide sem a tinta do texto e devolve a tinta. É o que está atrás de cada palavra."""
    pagina.evaluate(SEM_TINTA_JS)
    try:
        return pagina.screenshot(clip=recorte)
    finally:
        pagina.evaluate(VOLTA_TINTA_JS)
