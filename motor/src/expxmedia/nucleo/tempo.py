"""Momentos e datas no fuso da empresa (regra M5).

"Publicar às 07:00" é 07:00 no fuso da empresa, não em UTC nem no fuso da máquina. Por isso
todo momento gravado pelo núcleo sai daqui, com o deslocamento de fuso explícito:
`2026-09-24T21:22:46-03:00`. O fuso vem de `empresa.fuso` da Alma (`alma/alma.json`), lido a
cada chamada: editar a Alma vale na hora, sem reiniciar nada.

Uso:

    from expxmedia.nucleo import tempo
    tempo.agora_iso(raiz)          # "2026-09-24T21:22:46-03:00"
    tempo.hoje(raiz)               # "2026-09-24"
    tempo.iso(momento, raiz)       # converte um datetime com fuso para o fuso da Alma

Padrão de origem: youtube-squad/comum.py:92-105 (agora, agora_iso, hoje_sp), que tinha o
fuso fixo; aqui ele é da instalação.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = ["ErroFuso", "fuso", "agora", "agora_iso", "hoje", "iso"]


class ErroFuso(ValueError):
    """A Alma não diz um fuso válido, ou o momento recebido não tem fuso."""


def fuso(raiz: Path | str) -> ZoneInfo:
    """Fuso IANA de `empresa.fuso` na Alma da instalação em `raiz`.

    Levanta ErroFuso se a Alma não existe, não é JSON, não traz `empresa.fuso` ou traz um nome
    que o banco de fusos não conhece. Nunca cai para o fuso da máquina em silêncio (M7).
    """
    caminho = Path(raiz) / "alma" / "alma.json"
    try:
        # utf-8-sig: leitor tolera BOM na entrada (M16)
        alma = json.loads(caminho.read_text(encoding="utf-8-sig"))
    except OSError as erro:
        raise ErroFuso(f"não foi possível ler alma/alma.json: {erro.strerror}") from None
    except ValueError:
        raise ErroFuso("alma/alma.json não é JSON válido") from None
    empresa = alma.get("empresa") if isinstance(alma, dict) else None
    nome = empresa.get("fuso") if isinstance(empresa, dict) else None
    if not isinstance(nome, str) or not nome.strip():
        raise ErroFuso("a Alma não define empresa.fuso (ex.: \"America/Sao_Paulo\")")
    try:
        return ZoneInfo(nome)
    except (ZoneInfoNotFoundError, ValueError):
        raise ErroFuso(f"empresa.fuso da Alma não é um fuso IANA conhecido: {nome!r}") from None


def agora(raiz: Path | str) -> datetime:
    """O momento atual no fuso da Alma (datetime com fuso)."""
    return datetime.now(timezone.utc).astimezone(fuso(raiz))


def agora_iso(raiz: Path | str) -> str:
    """O momento atual como texto ISO 8601 com deslocamento, em segundos (M5)."""
    return agora(raiz).isoformat(timespec="seconds")


def hoje(raiz: Path | str, instante: datetime | None = None) -> str:
    """A data `AAAA-MM-DD` no fuso da Alma, agora ou no `instante` dado (que precisa ter fuso)."""
    if instante is None:
        return agora(raiz).date().isoformat()
    _exigir_fuso(instante)
    return instante.astimezone(fuso(raiz)).date().isoformat()


def iso(momento: datetime, raiz: Path | str | None = None) -> str:
    """Texto ISO 8601 com deslocamento, em segundos.

    Com `raiz`, converte o momento para o fuso da Alma antes; sem `raiz`, mantém o fuso que o
    momento já tem. Momento sem fuso é ambíguo e levanta ErroFuso.
    """
    _exigir_fuso(momento)
    if raiz is not None:
        momento = momento.astimezone(fuso(raiz))
    return momento.isoformat(timespec="seconds")


def _exigir_fuso(momento: datetime) -> None:
    if momento.tzinfo is None or momento.utcoffset() is None:
        raise ErroFuso("momento sem fuso é ambíguo (M5); use um datetime com tzinfo")
