"""Subcomandos base do `expxmedia-motor`: capacidades, alma, peca e galeria (D-11).

    capacidades [--capacidade X] [--porta-voz ID]
    alma validar
    peca criar --tipo T --formato F [--formato F2] [--titulo "..."] [--serie S] [--pack P]
    peca status <peca_id> [--novo S] [--motivo "..."]
    galeria buscar --tipo T --formato F [--serve-para X]... [--estilo X]... [--kind K]...
                   [--porta-voz ID] [--embarcados PASTA]
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from expxmedia import cli
from expxmedia.alma import carregar as alma_carregar
from expxmedia.ambiente.verificar import Verificador
from expxmedia.nucleo.raiz import relativo
from expxmedia.peca import modelo
from expxmedia.template import galeria_local

TITULO_PADRAO = "sem título"


def registrar(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("capacidades", help="o que está habilitado nesta instalação e como habilitar o resto")
    p.add_argument("--capacidade", default=None, help="consulta só esta capacidade")
    p.add_argument("--porta-voz", dest="porta_voz", default=None, help="confere também o id do porta-voz na Alma")
    p.set_defaults(func=capacidades)

    alma = cli.grupo(subparsers, "alma", help="Alma da empresa")
    p = alma.add_parser("validar", help="valida alma/alma.json contra o contrato e mostra o portão")
    p.set_defaults(func=alma_validar)

    peca = cli.grupo(subparsers, "peca", help="peças (peca.json)")
    p = peca.add_parser("criar", help="cria a pasta e o peca.json de uma peça nova")
    p.add_argument("--tipo", required=True, choices=list(modelo.TIPOS))
    p.add_argument("--formato", required=True, action="append", help="repita para mais de um formato")
    p.add_argument("--titulo", default=TITULO_PADRAO)
    p.add_argument("--serie", default=None)
    p.add_argument("--pack", default="nucleo")
    p.set_defaults(func=peca_criar)

    p = peca.add_parser("status", help="mostra ou muda o status da peça pelo ciclo de vida")
    p.add_argument("peca_id")
    p.add_argument("--novo", default=None, choices=list(modelo.STATUS))
    p.add_argument("--motivo", default=None, help="obrigatório para descartada")
    p.set_defaults(func=peca_status)

    galeria = cli.grupo(subparsers, "galeria", help="galeria local de templates")
    p = galeria.add_parser("buscar", help="templates por tipo e formato, sem os que não dá para usar aqui")
    p.add_argument("--tipo", required=True, choices=list(modelo.TIPOS))
    p.add_argument("--formato", required=True, choices=sorted(modelo.FORMATOS))
    p.add_argument("--serve-para", dest="serve_para", action="append", default=[])
    p.add_argument("--estilo", dest="estilos", action="append", default=[])
    p.add_argument("--kind", dest="kinds", action="append", default=None,
                   help="kinds que serão usados (padrão: todos os do template)")
    p.add_argument("--porta-voz", dest="porta_voz", default=None)
    p.add_argument("--embarcados", default=None, help="pasta dos templates embarcados (padrão: templates/ do repositório)")
    p.set_defaults(func=galeria_buscar)


# ---------------------------------------------------------------- capacidades


def capacidades(args: argparse.Namespace) -> dict[str, Any]:
    verificador = Verificador(args.raiz)
    if args.capacidade:
        return _com_aviso(verificador, verificador.verificar(args.capacidade, args.porta_voz), args.porta_voz)
    return {"capacidades": [_com_aviso(verificador, c, args.porta_voz)
                            for c in verificador.verificar_tudo(args.porta_voz)]}


def _com_aviso(verificador: Verificador, consulta: dict[str, Any], porta_voz: str | None) -> dict[str, Any]:
    """Acrescenta `aviso` à consulta quando a escolha do provedor é implícita (regra 2 do contrato)."""
    aviso = verificador.aviso(consulta["capacidade"], porta_voz)
    return {**consulta, "aviso": aviso} if aviso else consulta


# ---------------------------------------------------------------- alma


def alma_validar(args: argparse.Namespace) -> dict[str, Any]:
    try:
        alma = alma_carregar.carregar(args.raiz)
    except alma_carregar.ErroAlmaAusente as erro:
        raise cli.ErroEntrada(str(erro)) from None
    dados = {
        "ok": not alma.violacoes,
        "valida": not alma.violacoes,
        "confirmada": alma.confirmada,
        "violacoes": alma.violacoes,
        "portao": alma_carregar.portao(args.raiz),
    }
    if alma.violacoes:
        raise cli.Falha(cli.ENTRADA_INVALIDA, dados)
    return dados


# ---------------------------------------------------------------- peça


def peca_criar(args: argparse.Namespace) -> dict[str, Any]:
    peca = modelo.criar(
        args.raiz, tipo=args.tipo, titulo=args.titulo, formatos=list(args.formato), pack=args.pack, serie=args.serie,
    )
    pasta = modelo.pasta(args.raiz, peca["peca_id"])
    return {
        "peca_id": peca["peca_id"],
        "caminho": relativo(args.raiz, pasta / modelo.NOME_ARQUIVO),
        "peca": peca,
    }


def peca_status(args: argparse.Namespace) -> dict[str, Any]:
    atual = modelo.carregar(args.raiz, args.peca_id)
    if args.novo is None:
        return {
            "peca_id": args.peca_id,
            "status": atual["status"],
            "permitidos": sorted(modelo.TRANSICOES.get(atual["status"], ())),
        }
    peca = modelo.mudar_status(args.raiz, args.peca_id, args.novo, motivo=args.motivo)
    return {
        "peca_id": args.peca_id,
        "anterior": atual["status"],
        "status": peca["status"],
        "permitidos": sorted(modelo.TRANSICOES.get(peca["status"], ())),
    }


# ---------------------------------------------------------------- galeria


def galeria_buscar(args: argparse.Namespace) -> dict[str, Any]:
    return galeria_local.buscar_detalhado(
        args.raiz,
        tipo=args.tipo,
        formato=args.formato,
        serve_para=args.serve_para,
        estilos=args.estilos,
        kinds=args.kinds,
        porta_voz=args.porta_voz,
        embarcados=Path(args.embarcados).resolve() if args.embarcados else None,
    )
