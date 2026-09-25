"""Subcomandos de motion do `expxmedia-motor` (D-11):

    produzir reel          --entrada reel.json [--embarcados PASTA]
    produzir apresentacao  --entrada apresentacao.json [--mp4] [--embarcados PASTA]
    motion previa          --composicao NOME --timeline timeline.json --saida PASTA [--props props.json]
                           [--public-dir PASTA] [--escala F] [--versao V]
    motion render          --composicao NOME --saida ARQ.mp4 [--props props.json] [--public-dir PASTA]
                           [--versao V] [--codec C]

A produção tem muitos parâmetros e entra por arquivo JSON (`--entrada`, o formato de
`producao.reel` e de `producao.apresentacao.producao`). Como nos demais subcomandos, os arquivos de
entrada (`--entrada`, `--timeline`, `--props`, `--public-dir`) são relativos à pasta atual e os
caminhos de saída (`--saida`) são relativos à raiz da instalação (M9); os caminhos devolvidos no JSON
são relativos à raiz.

Saídas: entrada inválida sai com 2 citando o campo; roteiro reprovado pelo gate do roteirista e deck
inválido também saem com 2, com os achados; capacidade não habilitada, 3; verificação de entrega
reprovada, falha do Remotion ou da produção, 1 com o JSON do motivo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from expxmedia import cli
from expxmedia.motion import previa, remotion
from expxmedia.nucleo.raiz import absoluto, relativo
from expxmedia.producao import reel
from expxmedia.producao.apresentacao import producao as apresentacao


def registrar(subparsers: argparse._SubParsersAction) -> None:
    produzir = cli.grupo(subparsers, "produzir", help="produção de peças")
    p = produzir.add_parser("reel", help="reel narrado em Remotion a partir de um template de reel")
    p.add_argument("--entrada", required=True, help="JSON com titulo, roteiro, cta, cenas... (o exemplo.json do template)")
    p.add_argument("--embarcados", default=None, help="pasta dos templates embarcados (padrão: templates/ do repositório)")
    p.set_defaults(func=produzir_reel)

    p = produzir.add_parser("apresentacao", help="apresentação em HTML navegável; com --mp4, também MP4 e PNG por slide")
    p.add_argument("--entrada", required=True, help="JSON com deck, template, ativos, conteudo...")
    p.add_argument("--mp4", action="store_true", help="renderiza também o MP4 e um PNG por slide (renderizar_motion)")
    p.add_argument("--embarcados", default=None, help="pasta dos templates embarcados (padrão: templates/ do repositório)")
    p.set_defaults(func=produzir_apresentacao)

    motion = cli.grupo(subparsers, "motion", help="render e prévia de composições do kit Remotion")
    p = motion.add_parser("previa", help="um still a 60%% de cada cena com as guias da área segura e a folha")
    p.add_argument("--composicao", required=True, help="pasta de src/composicoes do projeto Remotion")
    p.add_argument("--timeline", required=True, help="linha do tempo JSON com as cenas (inicio, dur, id)")
    p.add_argument("--saida", required=True, help="pasta da prévia, relativa à raiz")
    p.add_argument("--props", default=None, help="props JSON da composição")
    p.add_argument("--public-dir", dest="public_dir", default=None, help="pasta servida como public/ no render")
    p.add_argument("--escala", type=float, default=previa.ESCALA)
    p.add_argument("--versao", default=remotion.VERSAO_KIT, help="versão do Remotion (padrão: a do kit)")
    p.set_defaults(func=motion_previa)

    p = motion.add_parser("render", help="renderiza uma composição do kit Remotion em MP4")
    p.add_argument("--composicao", required=True, help="pasta de src/composicoes do projeto Remotion")
    p.add_argument("--saida", required=True, help="arquivo de vídeo de saída, relativo à raiz")
    p.add_argument("--props", default=None, help="props JSON da composição")
    p.add_argument("--public-dir", dest="public_dir", default=None, help="pasta servida como public/ no render")
    p.add_argument("--versao", default=remotion.VERSAO_KIT, help="versão do Remotion (padrão: a do kit)")
    p.add_argument("--codec", default="h264")
    p.set_defaults(func=motion_render)


# ---------------------------------------------------------------- entrada


def _ler_json(caminho: str, campo: str) -> Any:
    arquivo = Path(caminho).resolve()
    if not arquivo.is_file():
        raise cli.ErroEntrada(f"campo '{campo}': arquivo não encontrado: {caminho}")
    try:
        return json.loads(arquivo.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as erro:
        raise cli.ErroEntrada(f"campo '{campo}': JSON inválido na linha {erro.lineno}, coluna {erro.colno}: {erro.msg}") from None
    except UnicodeDecodeError:
        raise cli.ErroEntrada(f"campo '{campo}': o arquivo não é UTF-8") from None


def _pasta(caminho: str | None, campo: str) -> Path | None:
    if caminho is None:
        return None
    pasta = Path(caminho).resolve()
    if not pasta.is_dir():
        raise cli.ErroEntrada(f"campo '{campo}': pasta não encontrada: {caminho}")
    return pasta


def _props(caminho: str | None) -> dict[str, Any] | None:
    if caminho is None:
        return None
    props = _ler_json(caminho, "props")
    if not isinstance(props, dict):
        raise cli.ErroEntrada("campo 'props': as props da composição são um objeto JSON")
    return props


def _falha_remotion(erro: Exception) -> cli.Falha:
    return cli.Falha(cli.ERRO, {"ok": False, "erro": "remotion", "mensagem": str(erro)})


# ---------------------------------------------------------------- produzir


def produzir_reel(args: argparse.Namespace) -> dict[str, Any]:
    dados = _ler_json(args.entrada, "entrada")
    embarcados = _pasta(args.embarcados, "embarcados")
    try:
        return reel.produzir(args.raiz, dados, embarcados=embarcados, origem="skill")
    except reel.ErroEntradaReel as erro:
        raise cli.ErroEntrada(str(erro)) from None
    except reel.ErroRoteiroReprovado as erro:
        raise cli.Falha(cli.ENTRADA_INVALIDA, {"ok": False, "erro": "roteiro_reprovado", "mensagem": str(erro),
                                               "peca_id": erro.peca_id, "achados": erro.achados}) from None
    except reel.ErroVerificacaoReprovada as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "verificacao_reprovada", "mensagem": str(erro),
                                   "peca_id": erro.peca_id, "achados": erro.achados}) from None
    except remotion.ErroRemotion as erro:
        raise _falha_remotion(erro) from None
    except reel.ErroProducaoReel as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "producao", "mensagem": str(erro)}) from None


def produzir_apresentacao(args: argparse.Namespace) -> dict[str, Any]:
    dados = _ler_json(args.entrada, "entrada")
    embarcados = _pasta(args.embarcados, "embarcados")
    try:
        return apresentacao.produzir(args.raiz, dados, mp4=args.mp4, embarcados=embarcados)
    except apresentacao.ErroDeckInvalido as erro:
        raise cli.Falha(cli.ENTRADA_INVALIDA, {"ok": False, "erro": "deck_invalido", "mensagem": str(erro),
                                               "achados": erro.achados}) from None
    except remotion.ErroRemotion as erro:
        raise _falha_remotion(erro) from None
    except apresentacao.ErroProducao as erro:
        raise cli.ErroEntrada(str(erro)) from None


# ---------------------------------------------------------------- motion


def motion_previa(args: argparse.Namespace) -> dict[str, Any]:
    timeline = _ler_json(args.timeline, "timeline")
    cenas = timeline.get("cenas") if isinstance(timeline, dict) else None
    if not isinstance(cenas, list) or not cenas or not all(
            isinstance(c, dict) and all(isinstance(c.get(k), int) and not isinstance(c.get(k), bool) for k in ("inicio", "dur"))
            for c in cenas):
        raise cli.ErroEntrada("campo 'timeline': objeto JSON com cenas [{\"id\", \"inicio\", \"dur\"}] (quadros inteiros)")
    props = _props(args.props)
    public_dir = _pasta(args.public_dir, "public-dir")
    if not 0 < args.escala <= 1:
        raise cli.ErroEntrada("campo 'escala': número entre 0 (exclusivo) e 1")
    saida = absoluto(args.raiz, args.saida)
    try:
        r = previa.gerar_previa(args.composicao, timeline, saida, props, escala=args.escala, versao=args.versao,
                                public_dir=public_dir)
    except remotion.ErroRemotion as erro:
        raise _falha_remotion(erro) from None
    except ValueError as erro:
        raise cli.ErroEntrada(str(erro)) from None
    return {"imagens": [relativo(args.raiz, i) for i in r["imagens"]], "folha": relativo(args.raiz, r["folha"]),
            "quadros": r["quadros"]}


def motion_render(args: argparse.Namespace) -> dict[str, Any]:
    props = _props(args.props)
    public_dir = _pasta(args.public_dir, "public-dir")
    saida = absoluto(args.raiz, args.saida)
    try:
        video = remotion.renderizar(args.composicao, saida, props, versao=args.versao, public_dir=public_dir,
                                    codec=args.codec)
    except remotion.ErroRemotion as erro:
        raise _falha_remotion(erro) from None
    except ValueError as erro:
        raise cli.ErroEntrada(str(erro)) from None
    return {"video": relativo(args.raiz, video)}
