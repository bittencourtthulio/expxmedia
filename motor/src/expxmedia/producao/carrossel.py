"""Produção de carrossel de imagem: N slides PNG, prancha e legenda.txt a partir de template e slots.

Mesma entrada e mesmo caminho do post único (`producao.post`), com três diferenças: o carrossel
aceita vários slides, na ordem da entrada; sai com a prancha (`previa/prancha.png`, papel
`previa`); e a legenda é obrigatória (`texto/legenda.txt`, papel `legenda`). Kind que não existe
no template é erro antes do render, citando o kind e os kinds disponíveis.

Uso:

    from expxmedia.producao import carrossel
    r = carrossel.produzir(raiz, entrada, base_imagens="pasta/das/imagens")
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from expxmedia.producao.post import (
    ErroEntradaProducao,
    ErroProducao,
    ErroRenderReprovado,
    ErroSlots,
    produzir_estatico,
)

__all__ = ["ErroProducao", "ErroEntradaProducao", "ErroSlots", "ErroRenderReprovado", "produzir"]


def produzir(raiz: Path | str, dados: Any, **opcoes: Any) -> dict[str, Any]:
    """Produz um carrossel de imagem (todo slide `midia: imagem`)."""
    return produzir_estatico(raiz, dados, tipo="carrossel", **opcoes)
