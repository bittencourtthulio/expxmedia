"""T-03.05: paridade do render HTML do núcleo com o sistema atual (D-16).

O layout de origem do golden G1, adaptado para template com tokens (adaptador_g1.py), é
renderizado pelo núcleo com a Alma golden e as fontes do golden, e cada slide é comparado com o
PNG que o `galeria.renderizar` de origem gravou: no máximo 1% dos pixels pode diferir, e só conta
como diferente o pixel com algum canal mais de 8/255 longe do golden.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

G1 = Path(__file__).resolve().parents[1] / "golden" / "G1"

LIMIAR_CANAL = 8        # de 255: diferença de canal que conta como pixel diferente
LIMITE_PIXELS = 0.01    # fração máxima de pixels diferentes por slide


def fracao_diferente(a: np.ndarray, b: np.ndarray, limiar: int = LIMIAR_CANAL) -> float:
    """Fração dos pixels em que algum canal RGB difere mais que `limiar`. Tamanhos diferentes = 1.0."""
    if a.shape != b.shape:
        return 1.0
    diferenca = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    return float((diferenca > limiar).mean())


def _rgb(caminho) -> np.ndarray:
    with Image.open(caminho) as img:
        return np.asarray(img.convert("RGB"))


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_cada_slide_do_g1_bate_com_o_golden(g1, n):
    nosso = _rgb(g1["saida"] / f"slide_{n}.png")
    golden = _rgb(G1 / f"slide_{n}.png")
    assert nosso.shape == golden.shape == (1350, 1080, 3)
    fracao = fracao_diferente(nosso, golden)
    assert fracao <= LIMITE_PIXELS, f"slide_{n}: {fracao:.2%} dos pixels diferem do golden (limite {LIMITE_PIXELS:.0%})"


def test_o_render_do_g1_passa_na_validacao_como_na_origem(g1):
    assert g1["resultado"]["ok"] is True and g1["golden"]["ok"] is True


def test_png_deslocado_10_px_acusa_diferenca_acima_do_limite():
    golden = _rgb(G1 / "slide_1.png")
    deslocado = np.array(golden)
    deslocado[:, 10:] = golden[:, :-10]
    deslocado[:, :10] = golden[:, :1]
    assert fracao_diferente(golden, golden) == 0.0
    assert fracao_diferente(golden, deslocado) > LIMITE_PIXELS


def test_o_limiar_de_canal_e_estrito():
    a = np.zeros((10, 10, 3), dtype=np.uint8)
    b = a.copy()
    b[0, :, 1] = 8           # 10% dos pixels a 8/255: dentro do limiar
    assert fracao_diferente(a, b) == 0.0
    b[0, :, 1] = 9           # a 9/255: contam
    assert fracao_diferente(a, b) == pytest.approx(0.1)
