"""Rastro de eventos: `eventos/AAAA-MM.jsonl` (CONTRATO-estado-eventos).

Uma linha por evento, com as doze chaves obrigatórias **nesta ordem** e, depois delas, só as
extras declaradas no contrato. Nenhuma chave é omitida (M7): o que não se aplica é `null`, e
`arquivos` sem arquivo é `[]`. O `ts` sai no fuso da Alma (M5) e escolhe o arquivo do mês;
os caminhos de `arquivos` são gravados relativos à raiz (M9); a linha entra por acréscimo
com trava (M15).

Uso:

    from expxmedia.nucleo import rastro
    rastro.registrar(
        raiz, origem="skill", evento="geracao_concluida", resultado="ok",
        peca_id="P-20260924-A3F9", capacidade="renderizar_html", provedor="playwright",
        detalhe="3 slides em 57,5 s", arquivos=[caminho_do_png], segundos=57.5,
    )
    eventos, corrompidas = rastro.ler(raiz, "2026-09")

Nunca ponha valor de segredo em `detalhe` (M14): cite o nome da variável.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from expxmedia.nucleo import arquivos as _arquivos
from expxmedia.nucleo import ids, tempo
from expxmedia.nucleo.raiz import ErroCaminho, relativo

__all__ = [
    "ErroRastro",
    "VERSAO",
    "CHAVES",
    "EXTRAS",
    "ORIGENS",
    "RESULTADOS",
    "EVENTOS",
    "registrar",
    "ler",
    "arquivo_do_mes",
]

VERSAO = 1

# As doze chaves obrigatórias, na ordem do contrato.
CHAVES: tuple[str, ...] = (
    "ts",
    "expxmedia_eventos",
    "pack",
    "origem",
    "evento",
    "peca_id",
    "agente",
    "capacidade",
    "provedor",
    "resultado",
    "detalhe",
    "arquivos",
)

# Extras declaradas, na ordem da tabela do contrato; gravadas depois das doze, nesta ordem.
EXTRAS: tuple[str, ...] = ("hook", "segundos", "valores", "template_id", "vaga")

ORIGENS = frozenset({"skill", "agente", "hook", "rotina", "painel", "humano"})
RESULTADOS = frozenset({"ok", "falha", "aviso", "bloqueado"})
EVENTOS = frozenset(
    {
        "alma_criada",
        "alma_atualizada",
        "ambiente_configurado",
        "capacidade_ausente",
        "peca_criada",
        "peca_status",
        "geracao_concluida",
        "geracao_falhou",
        "publicacao_agendada",
        "publicacao_concluida",
        "publicacao_falhou",
        "metricas_coletadas",
        "template_criado",
        "template_validado",
        "template_enviado",
        "template_recusado",
        "template_baixado",
        "plano_gerado",
        "vaga_status",
        "hook_decidiu",
    }
)

_PADRAO_PACK = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_PADRAO_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ErroRastro(ValueError):
    """Evento fora do contrato: enum desconhecido, extra não declarada, caminho inválido."""


def arquivo_do_mes(raiz: Path | str, mes: str) -> Path:
    """Caminho de `eventos/AAAA-MM.jsonl` para o `mes` (`AAAA-MM`)."""
    if not isinstance(mes, str) or not _PADRAO_MES.fullmatch(mes):
        raise ErroRastro(f"mês inválido: {mes!r} (use AAAA-MM)")
    return Path(raiz) / "eventos" / f"{mes}.jsonl"


def registrar(
    raiz: Path | str,
    *,
    origem: str,
    evento: str,
    resultado: str,
    pack: str = "nucleo",
    peca_id: str | None = None,
    agente: str | None = None,
    capacidade: str | None = None,
    provedor: str | None = None,
    detalhe: str | None = None,
    arquivos: Iterable[Path | str] = (),
    **extras: Any,
) -> dict[str, Any]:
    """Valida, grava e devolve um evento do rastro.

    `origem`, `resultado` e `evento` seguem os enums e o vocabulário do contrato. `pack` é o
    nome do pack ou camada, ou `nucleo`. `arquivos` aceita caminhos absolutos dentro da raiz
    ou relativos a ela, e grava todos relativos. `extras` só aceita as chaves de EXTRAS.
    Qualquer violação levanta ErroRastro antes de tocar no disco.
    """
    desconhecidas = sorted(set(extras) - set(EXTRAS))
    if desconhecidas:
        raise ErroRastro(
            f"chave extra não declarada no contrato: {', '.join(desconhecidas)} "
            f"(declaradas: {', '.join(EXTRAS)})"
        )
    _exigir_no_conjunto("origem", origem, ORIGENS)
    _exigir_no_conjunto("resultado", resultado, RESULTADOS)
    _exigir_no_conjunto("evento", evento, EVENTOS)
    if not isinstance(pack, str) or not _PADRAO_PACK.fullmatch(pack):
        raise ErroRastro(f"pack inválido: {pack!r} (nome do pack, minúsculo, ou nucleo)")
    if peca_id is not None and not ids.peca_id_valido(peca_id):
        raise ErroRastro(f"peca_id fora do formato P-AAAAMMDD-XXXX: {peca_id!r}")
    for nome, valor in (("agente", agente), ("capacidade", capacidade), ("provedor", provedor), ("detalhe", detalhe)):
        if valor is not None and not isinstance(valor, str):
            raise ErroRastro(f"{nome} deve ser texto ou None, não {type(valor).__name__}")

    linha: dict[str, Any] = {
        "ts": None,
        "expxmedia_eventos": VERSAO,
        "pack": pack,
        "origem": origem,
        "evento": evento,
        "peca_id": peca_id,
        "agente": agente,
        "capacidade": capacidade,
        "provedor": provedor,
        "resultado": resultado,
        "detalhe": detalhe,
        "arquivos": _relativos(raiz, arquivos),
    }
    for chave in EXTRAS:
        if chave in extras:
            linha[chave] = extras[chave]

    momento = tempo.agora(raiz)
    linha["ts"] = tempo.iso(momento)
    try:
        _arquivos.acrescentar_jsonl(arquivo_do_mes(raiz, momento.strftime("%Y-%m")), linha)
    except _arquivos.ErroArquivo as erro:
        raise ErroRastro(str(erro)) from None
    return linha


def ler(raiz: Path | str, mes: str) -> tuple[list[dict[str, Any]], int]:
    """(eventos, corrompidas) do mês `AAAA-MM`. Mês sem arquivo devolve `([], 0)`."""
    return _arquivos.ler_jsonl(arquivo_do_mes(raiz, mes))


def _exigir_no_conjunto(nome: str, valor: object, validos: frozenset[str]) -> None:
    if valor not in validos:
        raise ErroRastro(f"{nome} fora do contrato: {valor!r} (válidos: {', '.join(sorted(validos))})")


def _relativos(raiz: Path | str, caminhos: Iterable[Path | str]) -> list[str]:
    if isinstance(caminhos, (str, bytes, Path)):
        raise ErroRastro("arquivos deve ser uma lista de caminhos, não um caminho só")
    try:
        return [relativo(raiz, c) for c in caminhos]
    except ErroCaminho as erro:
        raise ErroRastro(f"arquivos: {erro}") from None
