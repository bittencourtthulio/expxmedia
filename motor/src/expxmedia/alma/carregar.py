"""Carga da Alma e o portão de primeiro uso (CONTRATO-alma).

O portão é fixo: sem `alma/alma.json`, ou com `confirmada_em` nulo, encaminha para
`/expxmedia:alma`; sem `.env` (que pode estar vazio), encaminha para `/expxmedia:ambiente`.

Uso:

    from expxmedia.alma import carregar
    carregar.portao(raiz)          # {"aberto": True, ..., "encaminhar": None, "motivo": None}
    alma = carregar.carregar(raiz) # alma.dados, alma.violacoes, alma.confirmada
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from expxmedia.alma.schema import ErroAlmaRejeitada, validar
from expxmedia.nucleo import arquivos

__all__ = ["Alma", "ErroAlmaAusente", "carregar", "portao", "caminho_alma"]

COMANDO_ALMA = "/expxmedia:alma"
COMANDO_AMBIENTE = "/expxmedia:ambiente"


class ErroAlmaAusente(FileNotFoundError):
    """A instalação não tem `alma/alma.json`."""


@dataclass
class Alma:
    """A Alma lida: os dados como estão no arquivo e as violações do contrato (M7)."""

    dados: dict[str, Any]
    violacoes: list[dict[str, str]] = field(default_factory=list)

    @property
    def confirmada(self) -> bool:
        return isinstance(self.dados.get("confirmada_em"), str) and bool(self.dados["confirmada_em"].strip())


def caminho_alma(raiz: Path | str) -> Path:
    return Path(raiz) / "alma" / "alma.json"


def carregar(raiz: Path | str) -> Alma:
    """Lê e valida `alma/alma.json`.

    Levanta ErroAlmaAusente se o arquivo não existe e ErroAlmaRejeitada se não dá para ler
    (JSON inválido, versão ausente ou maior, M2). Violação de contrato não levanta: vai em
    `violacoes`, e os dados voltam como estão, sem padrão preenchido em silêncio (M7).
    """
    caminho = caminho_alma(raiz)
    if not caminho.is_file():
        raise ErroAlmaAusente("a instalação não tem alma/alma.json")
    try:
        dados = arquivos.ler_json(caminho)
    except arquivos.ErroArquivo as erro:
        raise ErroAlmaRejeitada(str(erro)) from None
    return Alma(dados=dados, violacoes=validar(dados))


def portao(raiz: Path | str) -> dict[str, Any]:
    """Estado do portão de primeiro uso.

    Devolve `aberto`, `alma_existe`, `alma_confirmada`, `env_existe`, `encaminhar` (o comando
    para onde a skill deve mandar a pessoa, ou None) e `motivo` (texto, ou None quando aberto).
    A Alma é conferida antes do ambiente, na ordem do contrato.
    """
    raiz = Path(raiz)
    alma_existe = caminho_alma(raiz).is_file()
    env_existe = (raiz / ".env").is_file()
    alma_confirmada = False
    motivo: str | None = None

    if not alma_existe:
        motivo = "alma/alma.json não existe"
    else:
        try:
            alma_confirmada = carregar(raiz).confirmada
        except ErroAlmaRejeitada as erro:
            motivo = f"alma/alma.json não pode ser lida: {erro}"
        else:
            if not alma_confirmada:
                motivo = "a Alma ainda não foi confirmada (confirmada_em é null)"

    encaminhar: str | None = None
    if motivo is not None:
        encaminhar = COMANDO_ALMA
    elif not env_existe:
        encaminhar = COMANDO_AMBIENTE
        motivo = ".env não existe na raiz da instalação"

    return {
        "aberto": encaminhar is None,
        "alma_existe": alma_existe,
        "alma_confirmada": alma_confirmada,
        "env_existe": env_existe,
        "encaminhar": encaminhar,
        "motivo": motivo,
    }
