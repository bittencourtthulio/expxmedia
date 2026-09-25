"""Raiz da instalação e caminhos relativos a ela (regra M9).

A raiz da instalação é a pasta que contém `alma/`. Todo caminho gravado em artefato (peça,
template, rastro, plano) é relativo a ela, com `/` como separador: caminho absoluto vaza o
usuário da máquina e quebra ao trocar de máquina.

Uso:

    from expxmedia.nucleo import raiz as instalacao
    r = instalacao.encontrar_raiz()                    # sobe a partir da pasta atual
    instalacao.relativo(r, r / "pecas/2026-09/x.png")  # "pecas/2026-09/x.png"
    instalacao.absoluto(r, "pecas/2026-09/x.png")      # Path absoluto, para abrir o arquivo
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath

__all__ = ["ErroRaiz", "ErroCaminho", "encontrar_raiz", "relativo", "absoluto"]

MARCA_DA_RAIZ = "alma"


class ErroRaiz(LookupError):
    """Nenhuma pasta acima do ponto de partida contém `alma/`."""


class ErroCaminho(ValueError):
    """Caminho fora da raiz da instalação, ou absoluto onde só relativo é aceito."""


def encontrar_raiz(inicio: Path | str | None = None) -> Path:
    """Primeira pasta, subindo a partir de `inicio` (padrão: a pasta atual), que contém `alma/`.

    `inicio` pode ser um arquivo; a busca começa na pasta dele. Devolve o caminho resolvido
    (sem links simbólicos). Levanta ErroRaiz se chegar à raiz do sistema sem achar.
    """
    ponto = Path(inicio if inicio is not None else Path.cwd()).resolve()
    if ponto.is_file():
        ponto = ponto.parent
    for pasta in (ponto, *ponto.parents):
        if (pasta / MARCA_DA_RAIZ).is_dir():
            return pasta
    raise ErroRaiz(
        f"nenhuma instalação do ExpxMedia encontrada a partir de {ponto.name or ponto}: "
        f"nenhuma pasta acima contém {MARCA_DA_RAIZ}/"
    )


def relativo(raiz: Path | str, caminho: Path | str) -> str:
    """`caminho` relativo à `raiz`, como texto com `/` (M9).

    Aceita caminho absoluto dentro da raiz ou caminho já relativo a ela (que é normalizado).
    Levanta ErroCaminho se o caminho, resolvido, cai fora da raiz ou é a própria raiz.
    """
    base = Path(raiz).resolve()
    alvo = Path(caminho)
    if not alvo.is_absolute():
        alvo = base / alvo
    alvo = alvo.resolve()
    try:
        partes = alvo.relative_to(base).parts
    except ValueError:
        raise ErroCaminho(f"caminho fora da raiz da instalação: {_mostrar(caminho)}") from None
    if not partes:
        raise ErroCaminho("o caminho aponta para a própria raiz da instalação, não para um arquivo dela")
    return PurePosixPath(*partes).as_posix()


def absoluto(raiz: Path | str, caminho_relativo: str | Path) -> Path:
    """Caminho absoluto de um caminho relativo gravado em artefato. Inverso de `relativo`.

    Recusa caminho absoluto (o artefato violaria M9) e caminho que escapa da raiz com `..`.
    """
    texto = str(caminho_relativo)
    if Path(texto).is_absolute() or PurePosixPath(texto).is_absolute():
        raise ErroCaminho(f"caminho absoluto onde só relativo é aceito (M9): {_mostrar(texto)}")
    base = Path(raiz).resolve()
    return base / relativo(base, texto)


def _mostrar(caminho: Path | str) -> str:
    """Só o nome final: mensagem de erro não vaza a árvore de pastas do usuário."""
    return Path(caminho).name or str(caminho)
