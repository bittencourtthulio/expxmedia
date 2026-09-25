"""Tokens CSS da Alma: `--alma-<papel>` e `--alma-fonte-titulo`/`--alma-fonte-texto`.

O template nunca pede "o azul", pede `destaque` (CONTRATO-alma, CONTRATO-template). O motor
injeta estes tokens no `:root` de toda página que renderiza; o CSS do template só referencia
`var(--alma-*)`.

A pilha de fonte termina na Inter embarcada no motor e na genérica `sans-serif` do CSS; nunca
numa fonte de sistema nomeada (D-21).

Uso:

    from expxmedia.alma import tokens
    tokens.tokens_css(alma)   # ":root {\\n  --alma-fundo: #FFF8EE;\\n ... }\\n"
"""
from __future__ import annotations

from typing import Any

__all__ = ["ErroTokens", "PAPEIS_COR", "PAPEIS_FONTE", "FAMILIA_RESERVA", "tokens", "tokens_css", "pilha_fonte"]

# Os nove papéis de cor, na ordem do contrato.
PAPEIS_COR: tuple[str, ...] = (
    "fundo",
    "fundo_alt",
    "texto",
    "texto_inverso",
    "apoio",
    "destaque",
    "destaque_2",
    "positivo",
    "negativo",
)
PAPEIS_FONTE: tuple[str, ...] = ("titulo", "texto")
# A fonte embarcada no motor (recursos/fontes/Inter), reserva de toda pilha (D-21).
FAMILIA_RESERVA = "Inter"


class ErroTokens(ValueError):
    """A Alma não traz um papel de cor exigido pelos tokens."""


def _dados(alma: Any) -> dict[str, Any]:
    return alma.dados if hasattr(alma, "dados") else alma


def pilha_fonte(familia: str | None) -> str:
    """`'Família', 'Inter', sans-serif` (sem repetir a Inter quando ela é a família)."""
    nomes = [f for f in (familia, FAMILIA_RESERVA) if f]
    unicos = list(dict.fromkeys(nomes))
    return ", ".join(f"'{_escapar(n)}'" for n in unicos) + ", sans-serif"


def tokens(alma: Any) -> dict[str, str]:
    """Mapa `--alma-*` → valor, a partir da Alma (dict ou Alma carregada).

    Levanta ErroTokens listando os papéis de cor ausentes ou nulos: o motor não inventa cor.
    Família de fonte nula cai na Inter embarcada (D-21), que já é a reserva de toda pilha.
    """
    visual = _dados(alma).get("visual") or {}
    cores = visual.get("cores") or {}
    faltam = [p for p in PAPEIS_COR if not isinstance(cores.get(p), str) or not cores[p].strip()]
    if faltam:
        raise ErroTokens(f"a Alma não define os papéis de cor: {', '.join(faltam)} (visual.cores)")
    saida = {f"--alma-{papel}": cores[papel].strip() for papel in PAPEIS_COR}
    fontes = visual.get("fontes") or {}
    for papel in PAPEIS_FONTE:
        familia = (fontes.get(papel) or {}).get("familia")
        saida[f"--alma-fonte-{papel}"] = pilha_fonte(familia if isinstance(familia, str) and familia.strip() else None)
    return saida


def tokens_css(alma: Any, seletor: str = ":root") -> str:
    """Bloco CSS com os tokens da Alma dentro de `seletor` (padrão `:root`)."""
    linhas = [f"  {nome}: {valor};" for nome, valor in tokens(alma).items()]
    return f"{seletor} {{\n" + "\n".join(linhas) + "\n}\n"


def _escapar(nome: str) -> str:
    return nome.strip().replace("\\", "\\\\").replace("'", "\\'")
