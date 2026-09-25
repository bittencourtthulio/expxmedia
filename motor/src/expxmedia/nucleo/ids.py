"""Ids de peça e de template (regra M11) e slug.

- Peça: `P-AAAAMMDD-XXXX`, XXXX = 4 hex maiúsculos aleatórios. Aleatório de propósito (M11):
  vários processos criam peças ao mesmo tempo sem contador compartilhado.
- Template: `<tipo>-<slug>-<hash6>`, hash6 = 6 hex minúsculos aleatórios.

Todo id novo é conferido contra os já gerados neste processo e, se `raiz` for dada, contra o
que já existe na instalação: pastas `pecas/<AAAA-MM>/<peca_id>-<slug>/` e
`galeria/templates/<template_id>/`. Isso não substitui trava entre processos; com 65536 ids
por dia, a chance de dois processos sortearem o mesmo id no mesmo instante é desprezível.

Uso:

    from expxmedia.nucleo import ids
    ids.novo_peca_id("2026-09-24", raiz=raiz)             # "P-20260924-A3F9"
    ids.novo_template_id("carrossel", "Editorial azul")    # "carrossel-editorial-azul-3fa2c1"
"""
from __future__ import annotations

import re
import secrets
import threading
import unicodedata
from datetime import date, datetime
from pathlib import Path

__all__ = [
    "ErroId",
    "PADRAO_PECA_ID",
    "PADRAO_TEMPLATE_ID",
    "novo_peca_id",
    "novo_template_id",
    "peca_id_valido",
    "slug",
]

PADRAO_PECA_ID = re.compile(r"^P-\d{8}-[0-9A-F]{4}$")
PADRAO_TEMPLATE_ID = re.compile(r"^[a-z0-9_]+-[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{6}$")
_PADRAO_TIPO = re.compile(r"^[a-z0-9_]+$")

_BITS_PECA = 16  # 4 hex
_BITS_TEMPLATE = 24  # 6 hex
_TENTATIVAS = 64  # sorteios antes de varrer o espaço inteiro atrás de um id livre

_gerados: set[str] = set()
_trava = threading.Lock()


class ErroId(ValueError):
    """Entrada inválida para gerar id, ou espaço de ids do dia esgotado."""


def _sortear(bits: int) -> int:
    """Inteiro aleatório com `bits` bits. Isolado para os testes forçarem colisões."""
    return secrets.randbits(bits)


def slug(texto: str) -> str:
    """Minúsculo, sem acento, só [a-z0-9] separados por hífen. Pode devolver "" se nada sobrar."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def peca_id_valido(valor: object) -> bool:
    """True se `valor` é um id de peça no formato M11."""
    return isinstance(valor, str) and PADRAO_PECA_ID.fullmatch(valor) is not None


def novo_peca_id(data: date | datetime | str, raiz: Path | str | None = None) -> str:
    """Id de peça novo para a `data` (date, datetime ou "AAAA-MM-DD").

    datetime é usado pela sua própria data: converta para o fuso da Alma antes (tempo.agora).
    """
    prefixo = f"P-{_data(data).strftime('%Y%m%d')}-"
    existentes = _pecas_existentes(Path(raiz), prefixo) if raiz is not None else set()
    return _novo(prefixo, _BITS_PECA, "{:04X}", existentes)


def novo_template_id(tipo: str, nome: str, raiz: Path | str | None = None) -> str:
    """Id de template novo: `<tipo>-<slug(nome)>-<hash6>`.

    `tipo` é o tipo de peça (`carrossel`, `post_unico`...), minúsculo sem acento (M4).
    """
    if not isinstance(tipo, str) or not _PADRAO_TIPO.fullmatch(tipo):
        raise ErroId(f"tipo de template inválido: {tipo!r} (use minúsculas, dígitos e _)")
    parte = slug(nome)
    if not parte:
        raise ErroId(f"o nome do template não gera slug: {nome!r}")
    prefixo = f"{tipo}-{parte}-"
    existentes = _templates_existentes(Path(raiz), prefixo) if raiz is not None else set()
    return _novo(prefixo, _BITS_TEMPLATE, "{:06x}", existentes)


def _novo(prefixo: str, bits: int, formato: str, existentes: set[str]) -> str:
    with _trava:
        ocupados = existentes | _gerados

        for _ in range(_TENTATIVAS):
            candidato = prefixo + formato.format(_sortear(bits))
            if candidato not in ocupados:
                _gerados.add(candidato)
                return candidato

        # Muitas colisões seguidas: o espaço está quase cheio. Escolhe entre os livres.
        livres = [n for n in range(2**bits) if prefixo + formato.format(n) not in ocupados]
        if not livres:
            raise ErroId(f"todos os ids com o prefixo {prefixo} já foram usados")
        candidato = prefixo + formato.format(livres[secrets.randbelow(len(livres))])
        _gerados.add(candidato)
        return candidato


def _data(valor: date | datetime | str) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
        try:
            return date.fromisoformat(valor)
        except ValueError:
            pass
    raise ErroId(f"data inválida para id de peça: {valor!r} (use AAAA-MM-DD)")


def _pecas_existentes(raiz: Path, prefixo: str) -> set[str]:
    """Ids de peça do dia já usados em pecas/<AAAA-MM>/<peca_id>-<slug>/."""
    pecas = raiz / "pecas"
    if not pecas.is_dir():
        return set()
    achados = set()
    for pasta in pecas.glob(f"*/{prefixo}*"):
        candidato = pasta.name[: len(prefixo) + 4]
        if PADRAO_PECA_ID.fullmatch(candidato):
            achados.add(candidato)
    return achados


def _templates_existentes(raiz: Path, prefixo: str) -> set[str]:
    """Ids de template já usados em galeria/templates/<template_id>/."""
    pasta = raiz / "galeria" / "templates"
    if not pasta.is_dir():
        return set()
    return {p.name for p in pasta.glob(f"{prefixo}*") if p.is_dir()}
