"""Subcomandos de aula e avatar do `expxmedia-motor` (D-11, D-26, D-32):

    produzir aula     --entrada aula.json [--embarcados PASTA]
    aula compilar     --partes partes.json --titulo "..." [--formato 16:9|9:16] [--serie S]
    aula editar-tela  --cues pecas/.../midia/cues.json --janelas janelas.json --saida pecas/.../midia/demo.mp4
                      [--json pecas/.../midia/demo.json] [--marcas marks-rel.json] [--cue-final C] [--so-json]
    avatar gerar      --audio pecas/.../midia/narracao.mp3 --saida pecas/.../midia/avatar.mp4 [--porta-voz ID]

Arquivos de entrada (`--entrada`, `--partes`, `--janelas`, `--marcas`) são relativos à pasta atual; os
caminhos da instalação (`--cues`, `--saida`, `--json`, `--audio`) são relativos à raiz (M9), e os
caminhos devolvidos no JSON também.

`avatar gerar` usa o provedor que o ambiente escolher (`heygen` com HEYGEN_API_KEY, ou o de teste com
EXPXMEDIA_PROVEDORES_TESTE=1), sempre a partir do áudio (D-26). Sem nenhum dos dois, sai com 3 e o
`como_habilitar`, sem gastar nada.

Saídas: entrada inválida sai com 2 citando o campo; capacidade não habilitada, 3; verificação de entrega
reprovada, falha do Remotion, do avatar ou da produção, 1 com o JSON do motivo.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

from expxmedia import cli
from expxmedia.ambiente.verificar import Verificador
from expxmedia.aula import compilar as aula_compilar
from expxmedia.aula import editar_tela
from expxmedia.avatar.heygen import ErroAvatar
from expxmedia.motion import remotion
from expxmedia.nucleo.raiz import relativo
from expxmedia.producao import aula

PROVEDORES_AVATAR = {"heygen": "expxmedia.avatar.heygen", "teste": "expxmedia.avatar.teste"}


def registrar(subparsers: argparse._SubParsersAction) -> None:
    produzir = cli.grupo(subparsers, "produzir", help="produção de peças")
    p = produzir.add_parser("aula", help="aula narrada em 16:9 e/ou 9:16: cues, legenda 42x2, avatar e tela opcionais, SRT")
    p.add_argument("--entrada", required=True, help="JSON com titulo, roteiro com [[marcadores]], cenas... (o exemplo.json do template)")
    p.add_argument("--embarcados", default=None, help="pasta dos templates embarcados (padrão: templates/ do repositório)")
    p.set_defaults(func=produzir_aula)

    grupo = cli.grupo(subparsers, "aula", help="compilação de aulas e edição da gravação de tela")
    p = grupo.add_parser("compilar", help="trechos de aulas produzidas num MP4 só, com um SRT único deslocado")
    p.add_argument("--partes", required=True, help="JSON: lista de {peca_id, ini, fim (null = até o fim), nome}")
    p.add_argument("--titulo", required=True)
    p.add_argument("--formato", default="16:9", choices=["16:9", "9:16"])
    p.add_argument("--serie", default=None)
    p.set_defaults(func=compilar)

    p = grupo.add_parser("editar-tela", help="corta a gravação de tela por cues: acelera ou congela para caber na fala")
    p.add_argument("--cues", required=True, help="cues.json da aula, relativo à raiz")
    p.add_argument("--janelas", required=True, help="JSON: lista de janelas {cue, arquivo, inicio, fim, rotulo, camera, crop, crop9}")
    p.add_argument("--saida", required=True, help="demo.mp4 de saída, relativo à raiz")
    p.add_argument("--json", dest="destino_json", default=None, help="demo.json de saída (padrão: ao lado do mp4)")
    p.add_argument("--marcas", default=None, help="marks-rel.json da gravação ({t0, marks[{label, s}]})")
    p.add_argument("--cue-final", dest="cue_final", default=None, help="cue onde termina a fala da última janela")
    p.add_argument("--so-json", dest="so_json", action="store_true", help="regrava só o demo.json")
    p.set_defaults(func=editar)

    avatar = cli.grupo(subparsers, "avatar", help="vídeo do porta-voz falando a partir do áudio da narração")
    p = avatar.add_parser("gerar", help="gera o avatar do porta-voz a partir do ÁUDIO (nunca do texto)")
    p.add_argument("--audio", required=True, help="mp3 da narração, relativo à raiz")
    p.add_argument("--saida", required=True, help="mp4 de saída, relativo à raiz")
    p.add_argument("--porta-voz", dest="porta_voz", default=None, help="id do porta-voz (padrão: o principal da Alma)")
    p.set_defaults(func=gerar_avatar)


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


def _porta_voz(raiz: Path, pedido: str | None) -> str:
    try:
        alma = json.loads((raiz / "alma" / "alma.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as erro:
        raise cli.ErroEntrada(f"alma/alma.json ilegível: {erro}") from None
    vozes = [v for v in (alma.get("porta_vozes") or []) if isinstance(v, dict) and v.get("id")]
    if pedido:
        if not any(v["id"] == pedido for v in vozes):
            raise cli.ErroEntrada(f"campo 'porta-voz': o porta-voz {pedido} não existe na Alma")
        return pedido
    escolhido = next((v for v in vozes if v.get("principal")), vozes[0] if vozes else None)
    if escolhido is None:
        raise cli.ErroEntrada("campo 'porta-voz': a Alma não tem porta-voz")
    return escolhido["id"]


# ---------------------------------------------------------------- produzir aula


def produzir_aula(args: argparse.Namespace) -> dict[str, Any]:
    dados = _ler_json(args.entrada, "entrada")
    embarcados = _pasta(args.embarcados, "embarcados")
    try:
        return aula.produzir(args.raiz, dados, embarcados=embarcados, origem="skill")
    except aula.ErroEntradaAula as erro:
        raise cli.ErroEntrada(str(erro)) from None
    except aula.ErroVerificacaoReprovada as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "verificacao_reprovada", "mensagem": str(erro),
                                   "peca_id": erro.peca_id, "achados": erro.achados}) from None
    except remotion.ErroRemotion as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "remotion", "mensagem": str(erro)}) from None
    except ErroAvatar as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "avatar", "codigo": erro.codigo, "mensagem": str(erro)}) from None
    except (aula.ErroProducaoAula, editar_tela.ErroEditarTela) as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "producao", "mensagem": str(erro)}) from None


# ---------------------------------------------------------------- aula


def compilar(args: argparse.Namespace) -> dict[str, Any]:
    partes = _ler_json(args.partes, "partes")
    try:
        return aula_compilar.compilar(args.raiz, partes, titulo=args.titulo, formato=args.formato, serie=args.serie)
    except aula_compilar.ErroCompilar as erro:
        raise cli.ErroEntrada(str(erro)) from None


def editar(args: argparse.Namespace) -> dict[str, Any]:
    janelas = _ler_json(args.janelas, "janelas")
    if not isinstance(janelas, list) or not all(isinstance(j, dict) for j in janelas):
        raise cli.ErroEntrada("campo 'janelas': lista de objetos {cue, arquivo, inicio, fim, rotulo, camera, crop, crop9}")
    marcas = None
    if args.marcas is not None:
        arquivo = Path(args.marcas).resolve()
        if not arquivo.is_file():
            raise cli.ErroEntrada(f"campo 'marcas': arquivo não encontrado: {args.marcas}")
        marcas = editar_tela.ler_marcas(arquivo)
    try:
        demo = editar_tela.editar(args.raiz, args.cues, janelas, args.saida, args.destino_json, marcas=marcas,
                                  cue_final=args.cue_final, so_json=args.so_json)
    except editar_tela.ErroEditarTela as erro:
        raise cli.ErroEntrada(str(erro)) from None
    destino_json = args.destino_json or str(Path(args.saida).with_suffix(".json"))
    return {"video": None if args.so_json else relativo(args.raiz, args.raiz / args.saida),
            "json": relativo(args.raiz, args.raiz / destino_json), "demo": demo}


# ---------------------------------------------------------------- avatar


def gerar_avatar(args: argparse.Namespace) -> dict[str, Any]:
    porta_voz = _porta_voz(args.raiz, args.porta_voz)
    # ErroCapacidade sobe e sai com 3 e o como_habilitar (cli.executar), antes de qualquer custo
    provedor = Verificador(args.raiz).escolher_provedor("avatar", porta_voz)
    modulo = importlib.import_module(PROVEDORES_AVATAR[provedor])
    try:
        r = modulo.gerar(args.raiz, args.audio, porta_voz, args.saida)
    except ErroAvatar as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "avatar", "codigo": erro.codigo, "mensagem": str(erro)}) from None
    return {**r, "porta_voz": porta_voz}
