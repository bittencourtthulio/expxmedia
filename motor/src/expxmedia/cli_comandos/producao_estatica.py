"""Subcomandos da produção estática do `expxmedia-motor` (D-11):

    produzir post       --entrada slots.json [--embarcados PASTA]
    produzir carrossel  --entrada slots.json [--embarcados PASTA]
    capturar pagina     --url URL --saida PASTA [--largura-css N] [--esquema dark|light] [--ocultar SELETOR]...
    imagem pexels       --termo "..." [--midia foto|video] [--orientacao ...] [--quantos N] [--baixar DESTINO]
    imagem openrouter   --prompt "..." --saida ARQ.png [--proporcao 4:5] [--modelo M] [--base ARQ]
    imagem retrato      [--porta-voz ID] [--recortar-em ARQ.png] [--indice N]
    imagem rosto        --porta-voz ID --prompt "..." --saida ARQ.png

Caminhos de saída são relativos à raiz da instalação (M9); `--entrada` é relativo à pasta atual e
a pasta dele é a base dos caminhos de imagem dos slots. A geração paga (OpenRouter, Higgsfield)
passa pela cota diária da instalação (`imagem.cota.Cota(raiz).consumir`).

Saídas: entrada, slots ou JSON inválidos saem com 2 e a mensagem cita o campo; capacidade não
habilitada, 3; render reprovado, captura recusada, erro do provedor ou cota estourada, 1 com o
JSON do motivo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from expxmedia import cli
from expxmedia.captura import pagina
from expxmedia.imagem import cota as _cota
from expxmedia.imagem import higgsfield, openrouter, pexels, retratos
from expxmedia.nucleo.raiz import absoluto, relativo
from expxmedia.producao import carrossel, post


def registrar(subparsers: argparse._SubParsersAction) -> None:
    produzir = cli.grupo(subparsers, "produzir", help="produção de peças")
    for nome, ajuda in (("post", "post único a partir de template e slots"),
                        ("carrossel", "carrossel de imagem: slides, prancha e legenda")):
        p = produzir.add_parser(nome, help=ajuda)
        p.add_argument("--entrada", required=True, help="JSON com template, titulo, slides, legenda...")
        p.add_argument("--embarcados", default=None, help="pasta dos templates embarcados (padrão: templates/ do repositório)")
        p.set_defaults(func=produzir_post if nome == "post" else produzir_carrossel)

    capturar = cli.grupo(subparsers, "capturar", help="captura de conteúdo")
    p = capturar.add_parser("pagina", help="captura uma página web em tira, site.md e seções")
    p.add_argument("--url", required=True)
    p.add_argument("--saida", required=True, help="pasta de saída, relativa à raiz")
    p.add_argument("--largura-css", dest="largura_css", type=int, default=pagina.LARGURA_CSS)
    p.add_argument("--esquema", default=pagina.ESQUEMA, choices=["dark", "light", "no-preference"])
    p.add_argument("--ocultar", action="append", default=[], help="seletor extra a esconder (repita)")
    p.set_defaults(func=capturar_pagina)

    imagem = cli.grupo(subparsers, "imagem", help="imagens da peça: banco, geração, retrato")
    p = imagem.add_parser("pexels", help="busca foto ou vídeo no Pexels (banco_imagens)")
    p.add_argument("--termo", required=True, help="descrição em inglês")
    p.add_argument("--midia", default="foto", choices=["foto", "video"])
    p.add_argument("--orientacao", default="portrait", choices=["portrait", "landscape", "square"])
    p.add_argument("--quantos", type=int, default=pexels.POR_PAGINA_PADRAO)
    p.add_argument("--baixar", default=None, help="baixa o primeiro resultado neste caminho, relativo à raiz")
    p.set_defaults(func=imagem_pexels)

    p = imagem.add_parser("openrouter", help="gera imagem pelo OpenRouter (imagem_ia), dentro da cota")
    p.add_argument("--prompt", required=True)
    p.add_argument("--saida", required=True, help="PNG de saída, relativo à raiz")
    p.add_argument("--proporcao", default=None)
    p.add_argument("--modelo", default=None)
    p.add_argument("--base", default=None, help="imagem de base, relativa à raiz")
    p.set_defaults(func=imagem_openrouter)

    p = imagem.add_parser("retrato", help="retrato do porta-voz para o slot pessoa (ou o substituto desenhado)")
    p.add_argument("--porta-voz", dest="porta_voz", default=None, help="padrão: o principal da Alma")
    p.add_argument("--recortar-em", dest="recortar_em", default=None, help="recorta o fundo (u2net) e grava aqui")
    p.add_argument("--indice", type=int, default=0)
    p.set_defaults(func=imagem_retrato)

    p = imagem.add_parser("rosto", help="porta-voz em cena nova pelo Higgsfield (rosto_ia), dentro da cota")
    p.add_argument("--porta-voz", dest="porta_voz", required=True)
    p.add_argument("--prompt", required=True, help="a situação, curta e em inglês; nunca a aparência")
    p.add_argument("--saida", required=True, help="PNG de saída, relativo à raiz")
    p.set_defaults(func=imagem_rosto)


# ---------------------------------------------------------------- produzir


def _ler_entrada(caminho: str) -> tuple[Any, Path]:
    arquivo = Path(caminho).resolve()
    if not arquivo.is_file():
        raise cli.ErroEntrada(f"campo 'entrada': arquivo não encontrado: {caminho}")
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as erro:
        raise cli.ErroEntrada(f"campo 'entrada': JSON inválido na linha {erro.lineno}, coluna {erro.colno}: {erro.msg}") from None
    except UnicodeDecodeError:
        raise cli.ErroEntrada("campo 'entrada': o arquivo não é UTF-8") from None
    return dados, arquivo.parent


def _produzir(args: argparse.Namespace, modulo: Any) -> dict[str, Any]:
    dados, base = _ler_entrada(args.entrada)
    embarcados = Path(args.embarcados).resolve() if args.embarcados else None
    try:
        return modulo.produzir(args.raiz, dados, base_imagens=base, embarcados=embarcados)
    except post.ErroEntradaProducao as erro:
        raise cli.ErroEntrada(str(erro)) from None
    except post.ErroSlots as erro:
        raise cli.Falha(cli.ENTRADA_INVALIDA, {"ok": False, "erro": "slots_invalidos", "mensagem": str(erro),
                                               "erros": erro.erros}) from None
    except post.ErroRenderReprovado as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "render_reprovado", "mensagem": str(erro),
                                   "peca_id": erro.peca_id, "problemas": erro.problemas}) from None
    except post.ErroProducao as erro:
        raise cli.ErroEntrada(str(erro)) from None


def produzir_post(args: argparse.Namespace) -> dict[str, Any]:
    return _produzir(args, post)


def produzir_carrossel(args: argparse.Namespace) -> dict[str, Any]:
    return _produzir(args, carrossel)


# ---------------------------------------------------------------- capturar


def capturar_pagina(args: argparse.Namespace) -> dict[str, Any]:
    saida = absoluto(args.raiz, args.saida)
    try:
        r = pagina.capturar(args.url, saida, largura_css=args.largura_css, esquema=args.esquema,
                            ajustes=args.ocultar or None, raiz=args.raiz)
    except pagina.ErroCaptura as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "captura_recusada", "motivo": type(erro).__name__,
                                   "mensagem": str(erro)}) from None
    return {"saida": relativo(args.raiz, saida), "captura": r}


# ---------------------------------------------------------------- imagem


def _falha_provedor(provedor: str, erro: Exception) -> cli.Falha:
    return cli.Falha(cli.ERRO, {"ok": False, "erro": getattr(erro, "codigo", "provedor"), "provedor": provedor,
                                "mensagem": str(erro)})


def imagem_pexels(args: argparse.Namespace) -> dict[str, Any]:
    try:
        itens = pexels.buscar(args.raiz, args.termo, midia=args.midia, orientacao=args.orientacao,
                              por_pagina=args.quantos, url_base=pexels.URL_BASE)
        baixado = None
        if args.baixar:
            if not itens:
                raise cli.Falha(cli.ERRO, {"ok": False, "erro": "sem_resultado", "mensagem": f"nada no Pexels para {args.termo!r}"})
            baixado = pexels.baixar(args.raiz, itens[0], args.baixar)
    except ValueError as erro:
        raise cli.ErroEntrada(str(erro)) from None
    except pexels.ErroPexels as erro:
        raise _falha_provedor("pexels", erro) from None
    return {"itens": itens, "baixado": baixado}


def imagem_openrouter(args: argparse.Namespace) -> dict[str, Any]:
    try:
        return openrouter.gerar(args.raiz, args.prompt, args.saida, modelo=args.modelo, proporcao=args.proporcao,
                                base=args.base, url_base=openrouter.URL_BASE, cota=_cota.Cota(args.raiz).consumir)
    except ValueError as erro:
        raise cli.ErroEntrada(str(erro)) from None
    except (openrouter.ErroOpenRouter, _cota.ErroCota) as erro:
        raise _falha_provedor("openrouter", erro) from None


def imagem_retrato(args: argparse.Namespace) -> dict[str, Any]:
    try:
        if args.recortar_em:
            if not args.porta_voz:
                raise cli.ErroEntrada("campo 'porta-voz': obrigatório para recortar")
            return retratos.recortar_retrato(args.raiz, args.porta_voz, args.recortar_em, indice=args.indice)
        return retratos.resolver_slot_pessoa(args.raiz, args.porta_voz)
    except retratos.ErroRetrato as erro:
        raise cli.ErroEntrada(str(erro)) from None


def imagem_rosto(args: argparse.Namespace) -> dict[str, Any]:
    try:
        return higgsfield.gerar_rosto(args.raiz, args.porta_voz, args.prompt, args.saida,
                                      cota=_cota.Cota(args.raiz).consumir)
    except ValueError as erro:
        raise cli.ErroEntrada(str(erro)) from None
    except (higgsfield.ErroHiggsfield, _cota.ErroCota) as erro:
        raise _falha_provedor("higgsfield", erro) from None
