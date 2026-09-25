"""Subcomandos de revisão do `expxmedia-motor` (D-11, D-45):

    revisar copy --arquivo ARQ [--arquivo ARQ2]... [--texto "..."] [--peca ID]
                 [--palavra-publicacao P] [--serie S]

`--arquivo` é relativo à pasta atual (a copy da arte, a legenda); a primeira frase do primeiro
texto é a abertura comparada com as peças dos últimos 14 dias. Aprovado sai 0; com bloqueante,
sai 1 com o JSON dos bloqueantes e a posição de cada um; peça ou texto inválido, 2.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from expxmedia import cli
from expxmedia.alma import carregar as alma_carregar
from expxmedia.revisar import copy as revisar_copy


def registrar(subparsers: argparse._SubParsersAction) -> None:
    revisar = cli.grupo(subparsers, "revisar", help="revisões mecânicas antes de renderizar ou publicar")
    p = revisar.add_parser("copy", help="bloqueantes mecânicos da copy pela Alma: travessão, tratamento, "
                                        "palavras proibidas, palavra do CTA e abertura repetida em 14 dias")
    p.add_argument("--arquivo", action="append", default=[], help="texto a revisar (repita: copy, legenda...)")
    p.add_argument("--texto", default=None, help="texto direto, em vez de arquivo")
    p.add_argument("--peca", default=None, help="peça revisada: sai da comparação e dá a palavra da publicação")
    p.add_argument("--palavra-publicacao", dest="palavra_publicacao", default=None,
                   help="palavra do CTA da publicação (padrão: a da automação de DM da peça)")
    p.add_argument("--serie", default=None, help="compara a abertura só com peças desta série")
    p.set_defaults(func=revisar_copy_cmd)


def _textos(args: argparse.Namespace) -> dict[str, str]:
    textos: dict[str, str] = {}
    for caminho in args.arquivo:
        arquivo = Path(caminho).resolve()
        if not arquivo.is_file():
            raise cli.ErroEntrada(f"campo 'arquivo': arquivo não encontrado: {caminho}")
        try:
            textos[arquivo.name] = arquivo.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            raise cli.ErroEntrada(f"campo 'arquivo': {caminho} não é UTF-8") from None
    if args.texto is not None:
        textos["texto"] = args.texto
    if not textos:
        raise cli.ErroEntrada("informe --arquivo ou --texto")
    return textos


def revisar_copy_cmd(args: argparse.Namespace) -> dict[str, Any]:
    try:
        resultado = revisar_copy.revisar(args.raiz, _textos(args), peca_id=args.peca,
                                         palavra_publicacao=args.palavra_publicacao, serie=args.serie)
    except (revisar_copy.ErroRevisao, alma_carregar.ErroAlmaAusente) as erro:
        raise cli.ErroEntrada(str(erro)) from None
    if not resultado["aprovado"]:
        raise cli.Falha(cli.ERRO, {"ok": False, **resultado})
    return resultado
