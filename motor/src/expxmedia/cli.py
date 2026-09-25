"""CLI `expxmedia-motor`: o contrato entre as skills e o motor (D-11).

Os subcomandos não moram aqui. Cada módulo de `expxmedia/cli_comandos/` expõe
`registrar(subparsers)` e registra os seus; este arquivo só descobre os módulos (em ordem
alfabética, pulando os que começam com `_`), monta o parser e traduz o resultado. Nenhuma task
nova edita este arquivo: ela cria o seu módulo em `cli_comandos/`.

Contrato de cada subcomando:

- `parser.set_defaults(func=funcao)`; `funcao(args)` recebe `args.raiz` já resolvida (Path) e
  devolve um objeto JSON-serializável, impresso em stdout. Um `dict` sem `ok` ganha `"ok": true`.
- Vários módulos podem pendurar subcomandos no mesmo grupo (`produzir carrossel`,
  `produzir reel`...) com `cli.grupo(subparsers, "produzir", help=...)`, que cria o grupo uma vez
  e devolve o mesmo nas chamadas seguintes.
- `--raiz` é global e aceito em qualquer nível (`expxmedia-motor capacidades --raiz X`); sem ele,
  a raiz é encontrada subindo a partir da pasta atual (`nucleo.raiz.encontrar_raiz`).

Códigos de saída (a saída é sempre JSON em stdout, inclusive nos erros):

- 0 ok;
- 2 entrada inválida (`ErroEntrada`, erro de argumento, peça/Alma/capacidade fora do contrato,
  instalação não encontrada);
- 3 capacidade não habilitada (`ErroCapacidade` do ambiente, ou `CapacidadeNaoHabilitada`),
  com `como_habilitar`;
- 1 erro genérico;
- `Falha(codigo, dados)` sai com o código e o JSON que o subcomando escolher.
"""
from __future__ import annotations

import argparse
import importlib
import json
import pkgutil
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from expxmedia.alma.schema import ErroAlmaRejeitada
from expxmedia.ambiente.catalogo import ErroCatalogo
from expxmedia.ambiente.env import ErroEnv
from expxmedia.ambiente.verificar import ErroCapacidade
from expxmedia.nucleo.raiz import ErroCaminho, ErroRaiz, encontrar_raiz
from expxmedia.peca.modelo import ErroPeca

__all__ = [
    "OK",
    "ERRO",
    "ENTRADA_INVALIDA",
    "CAPACIDADE_NAO_HABILITADA",
    "ErroEntrada",
    "CapacidadeNaoHabilitada",
    "Falha",
    "grupo",
    "descobrir_modulos",
    "construir_parser",
    "executar",
    "main",
]

OK = 0
ERRO = 1
ENTRADA_INVALIDA = 2
CAPACIDADE_NAO_HABILITADA = 3

PACOTE_COMANDOS = "expxmedia.cli_comandos"
PROG = "expxmedia-motor"


class ErroEntrada(ValueError):
    """Entrada inválida: sai com código 2."""


class CapacidadeNaoHabilitada(RuntimeError):
    """Capacidade não habilitada: sai com código 3 e o `como_habilitar`."""

    def __init__(self, capacidade: str | None, como_habilitar: str | None) -> None:
        super().__init__(como_habilitar or f"{capacidade} não está habilitada")
        self.capacidade = capacidade
        self.como_habilitar = como_habilitar


class Falha(Exception):
    """Saída não zero com JSON escolhido pelo subcomando (ex.: verificação reprovada)."""

    def __init__(self, codigo: int, dados: Any) -> None:
        super().__init__(f"saída {codigo}")
        self.codigo = codigo
        self.dados = dados


# Erros de entrada que vêm das bibliotecas do motor.
_ERROS_ENTRADA = (ErroEntrada, ErroPeca, ErroCatalogo, ErroAlmaRejeitada, ErroRaiz, ErroCaminho, ErroEnv)


# ---------------------------------------------------------------- parser


class _Subcomandos(argparse._SubParsersAction):
    """Todo subparser criado ganha `--raiz` (sem padrão, para não apagar o valor global)."""

    def add_parser(self, name: str, **kwargs: Any) -> argparse.ArgumentParser:
        parser = super().add_parser(name, **kwargs)
        parser.add_argument("--raiz", default=argparse.SUPPRESS,
                            help="raiz da instalação (padrão: procurada a partir da pasta atual)")
        return parser


class _Parser(argparse.ArgumentParser):
    """Erro de argumento vira ErroEntrada (código 2, JSON), em vez de texto no stderr."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.register("action", "parsers", _Subcomandos)

    def error(self, message: str) -> None:  # type: ignore[override]
        raise ErroEntrada(f"{self.prog}: {message}")


def grupo(subparsers: argparse._SubParsersAction, nome: str, help: str | None = None) -> argparse._SubParsersAction:
    """Subcomandos do grupo `nome` (`produzir`, `peca`...), criado na primeira chamada e reusado depois."""
    existente = subparsers.choices.get(nome)
    if existente is not None:
        acao = getattr(existente, "_expxmedia_grupo", None)
        if acao is None:
            raise ValueError(f"o subcomando {nome} já existe e não é um grupo")
        return acao
    parser = subparsers.add_parser(nome, help=help, description=help)
    acao = parser.add_subparsers(dest=f"_{nome}", metavar="<subcomando>", parser_class=_Parser)
    acao.required = True
    parser._expxmedia_grupo = acao  # type: ignore[attr-defined]
    return acao


def descobrir_modulos(pacote: str = PACOTE_COMANDOS) -> list[ModuleType]:
    """Módulos de `cli_comandos/` com `registrar`, em ordem alfabética."""
    base = importlib.import_module(pacote)
    modulos = []
    for info in sorted(pkgutil.iter_modules(base.__path__), key=lambda m: m.name):
        if info.name.startswith("_"):
            continue
        modulo = importlib.import_module(f"{pacote}.{info.name}")
        if callable(getattr(modulo, "registrar", None)):
            modulos.append(modulo)
    return modulos


def construir_parser(pacote: str = PACOTE_COMANDOS) -> argparse.ArgumentParser:
    parser = _Parser(prog=PROG, description="Motor do núcleo do ExpxMedia. Toda saída é JSON em stdout.")
    parser.add_argument("--raiz", default=None,
                        help="raiz da instalação (padrão: procurada a partir da pasta atual)")
    subparsers = parser.add_subparsers(dest="_comando", metavar="<comando>", parser_class=_Parser)
    subparsers.required = True
    for modulo in descobrir_modulos(pacote):
        modulo.registrar(subparsers)
    return parser


# ---------------------------------------------------------------- execução


def _imprimir(dados: Any) -> None:
    sys.stdout.write(json.dumps(dados, ensure_ascii=False, indent=2) + "\n")
    sys.stdout.flush()


def _erro(tipo: str, mensagem: str, **extras: Any) -> dict[str, Any]:
    return {"ok": False, "erro": tipo, "mensagem": mensagem, **extras}


def executar(parser: argparse.ArgumentParser, argv: Sequence[str]) -> int:
    """Interpreta `argv`, roda o subcomando, imprime o JSON e devolve o código de saída."""
    try:
        args = parser.parse_args(list(argv))
        funcao = getattr(args, "func", None)
        if funcao is None:
            raise ErroEntrada("informe um subcomando (veja --help)")
        args.raiz = Path(args.raiz).resolve() if args.raiz else encontrar_raiz()
        resultado = funcao(args)
    except Falha as falha:
        _imprimir(falha.dados)
        return falha.codigo
    except CapacidadeNaoHabilitada as erro:
        _imprimir(_erro("capacidade_nao_habilitada", str(erro), capacidade=erro.capacidade,
                        como_habilitar=erro.como_habilitar))
        return CAPACIDADE_NAO_HABILITADA
    except ErroCapacidade as erro:
        _imprimir(_erro("capacidade_nao_habilitada", str(erro), como_habilitar=str(erro)))
        return CAPACIDADE_NAO_HABILITADA
    except _ERROS_ENTRADA as erro:
        _imprimir(_erro("entrada_invalida", str(erro)))
        return ENTRADA_INVALIDA
    except Exception as erro:  # noqa: BLE001 — todo erro sai em JSON, com código 1
        _imprimir(_erro("erro", f"{type(erro).__name__}: {erro}"))
        return ERRO
    if isinstance(resultado, dict) and "ok" not in resultado:
        resultado = {"ok": True, **resultado}
    _imprimir(resultado)
    return OK


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point `expxmedia-motor`. `--help` imprime o texto de ajuda e sai 0."""
    argv = sys.argv[1:] if argv is None else argv
    try:
        parser = construir_parser()
    except Exception as erro:  # noqa: BLE001 — módulo de comando quebrado não pode sair em texto
        _imprimir(_erro("erro", f"falha ao carregar os comandos: {type(erro).__name__}: {erro}"))
        return ERRO
    try:
        return executar(parser, argv)
    except SystemExit as saida:  # --help
        return saida.code if isinstance(saida.code, int) else OK


if __name__ == "__main__":
    sys.exit(main())
