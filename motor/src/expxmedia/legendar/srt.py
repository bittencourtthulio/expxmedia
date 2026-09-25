"""SRT a partir de legendas `[{start, end, lines}]` (D-23: o SRT é sempre gerado).

Formato da origem: índice a partir de 1, `HH:MM:SS,mmm --> HH:MM:SS,mmm`, as linhas da legenda,
uma linha em branco entre blocos e `\\n` no fim. O texto é o do roteiro, nunca o da transcrição.
(origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:134-142)

Diferença deliberada: a origem arredondava só a fração do segundo e podia escrever `,1000`
(ex. 3,9996 s); aqui o tempo é arredondado ao milissegundo antes de separar horas, minutos e segundos.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

__all__ = ["tempo_srt", "gerar_srt", "gravar_srt"]


def tempo_srt(t: float) -> str:
    """Segundos → `HH:MM:SS,mmm`."""
    ms = int(round(t * 1000))
    h, resto = divmod(ms, 3_600_000)
    m, resto = divmod(resto, 60_000)
    s, ms = divmod(resto, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def gerar_srt(legendas: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"{i + 1}\n{tempo_srt(c['start'])} --> {tempo_srt(c['end'])}\n" + "\n".join(c["lines"]) + "\n"
        for i, c in enumerate(legendas))


def gravar_srt(legendas: list[dict[str, Any]], destino: str | Path) -> Path:
    """Grava o SRT de forma atômica (M15), UTF-8 sem BOM."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=destino.parent, prefix=destino.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(gerar_srt(legendas))
        os.replace(tmp, destino)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return destino
