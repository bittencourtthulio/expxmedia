"""Subcomandos de reel por referência, reel de corte e abertura do `expxmedia-motor` (D-11):

    referencia analisar  --video ARQ --pasta SLUG|PASTA [--sem-fala] [--modelo M] [--idioma X]
    referencia criar     SLUG [--titulo T] [--origem-url URL] [--pedido TEXTO]
    referencia montar    --pasta SLUG|PASTA
    referencia previa    --pasta SLUG|PASTA [--porta-voz ID] [--canal C]
    referencia render    --pasta SLUG|PASTA [--porta-voz ID] [--canal C]
    produzir reel-corte  --entrada corte.json
    produzir abertura    --pasta PASTA --prompt TEXTO [--tipo objeto|porta_voz] [--porta-voz ID] [--duracao S]
                         [--estilo TEXTO] [--sem-transformar] | --pasta PASTA --dispensar

A pasta do reel por referência é um slug (`referencias/<slug>`) ou um caminho dentro da raiz
(`referencia.sob_medida.pasta_do_reel`). O reel de corte tem muitos parâmetros e entra por arquivo JSON
(`--entrada`, o formato de `producao.reel_corte`). Como nos demais subcomandos, os arquivos de entrada
(`--video`, `--entrada`) são relativos à pasta atual e as pastas de trabalho (`--pasta`) são relativas à raiz
(M9); os caminhos devolvidos no JSON são relativos à raiz.

Saídas: entrada inválida sai com 2 citando o campo; `cenas.json` recusado sai com 2 (`cenas_recusado`,
com cada problema citando a cena) e código do reel recusado pelo validador, também 2 (`codigo_recusado`,
com os achados); capacidade não habilitada, 3; etapa que falta, análise, Remotion, verificação reprovada
ou abertura impossível, 1 com o JSON do motivo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from expxmedia import cli
from expxmedia.imagem import higgsfield
from expxmedia.motion import remotion
from expxmedia.nucleo.raiz import absoluto, relativo
from expxmedia.producao import abertura, reel_corte, reel_referencia
from expxmedia.referencia import analisar as referencia_analisar
from expxmedia.referencia import sob_medida
from expxmedia.transcrever import whisper


def registrar(subparsers: argparse._SubParsersAction) -> None:
    ref = cli.grupo(subparsers, "referencia", help="reel por referência sob medida: análise, pasta, montagem, prévia e render")

    p = ref.add_parser("analisar", help="quadros, folhas de contato, cortes e fala do vídeo de referência em analise/")
    p.add_argument("--video", required=True, help="vídeo de referência (relativo à pasta atual)")
    p.add_argument("--pasta", required=True, help="slug ou pasta do reel, relativa à raiz")
    p.add_argument("--sem-fala", dest="sem_fala", action="store_true", help="não transcreve a fala")
    p.add_argument("--modelo", default=referencia_analisar.MODELO_PADRAO, help="modelo do whisper")
    p.add_argument("--idioma", default=None, help="idioma da fala (padrão: detecta)")
    p.set_defaults(func=referencia_analisar_cmd)

    p = ref.add_parser("criar", help="cria referencias/<slug>/ com o cenas.json esqueleto e o Reel.tsx do kit")
    p.add_argument("slug", help="minúsculas, números e hífen")
    p.add_argument("--titulo", default=None)
    p.add_argument("--origem-url", dest="origem_url", default=None, help="URL da referência (só registro)")
    p.add_argument("--pedido", default=None, help="o pedido de quem encomendou o reel")
    p.set_defaults(func=referencia_criar)

    p = ref.add_parser("montar", help="linha do tempo pelas âncoras e trilha com os efeitos em midia/")
    p.add_argument("--pasta", required=True, help="slug ou pasta do reel, relativa à raiz")
    p.set_defaults(func=referencia_montar)

    for nome, ajuda, func in (
            ("previa", "um still a 60%% de cada cena com as guias e a folha em previa/NN/ (até 3 voltas)", referencia_previa),
            ("render", "render, normalização, verificação no perfil sob_medida e a peça produzida", referencia_render)):
        p = ref.add_parser(nome, help=ajuda)
        p.add_argument("--pasta", required=True, help="slug ou pasta do reel, relativa à raiz")
        p.add_argument("--porta-voz", dest="porta_voz", default=None, help="id do porta-voz da Alma (padrão: o da narração)")
        p.add_argument("--canal", default=None, help="canal do selo (padrão: o da Alma)")
        p.set_defaults(func=func)

    produzir = cli.grupo(subparsers, "produzir", help="produção de peças")
    p = produzir.add_parser("reel-corte", help="reel de corte: trecho de vídeo longo em 9:16 com a fala original")
    p.add_argument("--entrada", required=True, help="JSON com video, titulo, gancho, trecho|plano, broll... (ver producao.reel_corte)")
    p.set_defaults(func=produzir_reel_corte)

    p = produzir.add_parser("abertura", help="abertura gerada por IA que troca o fundo do começo do reel (video_ia)")
    p.add_argument("--pasta", required=True, help="pasta de montagem do reel, relativa à raiz")
    p.add_argument("--prompt", default=None, help="o que acontece no plano, em inglês")
    p.add_argument("--tipo", default="objeto", help=f"tipo de abertura: {', '.join(abertura.TIPOS)}")
    p.add_argument("--porta-voz", dest="porta_voz", default=None, help="id do porta-voz (tipo porta_voz)")
    p.add_argument("--duracao", type=float, default=abertura.DURACAO_NA_TELA, help="segundos na tela")
    p.add_argument("--estilo", default=None, help="a estética do plano (da Alma ou do template)")
    p.add_argument("--sem-transformar", dest="sem_transformar", action="store_true",
                   help="não transforma no primeiro quadro do conteúdo")
    p.add_argument("--dispensar", action="store_true", help="este reel vai sem abertura (remove clipe e marcador)")
    p.set_defaults(func=produzir_abertura)


# ---------------------------------------------------------------- apoio


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


def _falha(codigo: int, erro: str, mensagem: str, **extras: Any) -> cli.Falha:
    return cli.Falha(codigo, {"ok": False, "erro": erro, "mensagem": mensagem, **extras})


def _etapa_referencia(etapa, *args: Any, **kw: Any) -> Any:
    """Roda uma etapa do reel por referência traduzindo os erros dela nos códigos do CLI."""
    try:
        return etapa(*args, **kw)
    except sob_medida.ErroSobMedida as erro:
        raise _falha(cli.ENTRADA_INVALIDA, "cenas_recusado", str(erro), erros=erro.erros) from None
    except reel_referencia.ErroCodigoRecusado as erro:
        raise _falha(cli.ENTRADA_INVALIDA, "codigo_recusado", str(erro), achados=erro.achados) from None
    except reel_referencia.ErroVerificacaoReprovada as erro:
        raise _falha(cli.ERRO, "verificacao_reprovada", str(erro), peca_id=erro.peca_id, achados=erro.achados) from None
    except reel_referencia.ErroReferencia as erro:
        raise _falha(cli.ERRO, "referencia", str(erro)) from None
    except remotion.ErroRemotion as erro:
        raise _falha(cli.ERRO, "remotion", str(erro)) from None


# ---------------------------------------------------------------- referencia


def referencia_analisar_cmd(args: argparse.Namespace) -> dict[str, Any]:
    video = Path(args.video).resolve()
    if not video.is_file():
        raise cli.ErroEntrada(f"campo 'video': arquivo não encontrado: {args.video}")
    pasta = sob_medida.pasta_do_reel(args.raiz, args.pasta)
    try:
        formato = referencia_analisar.analisar(video, pasta, com_fala=not args.sem_fala, modelo=args.modelo,
                                               idioma=args.idioma)
    except (referencia_analisar.ErroAnalise, whisper.ErroTranscricao) as erro:
        raise _falha(cli.ERRO, "analise", str(erro)) from None
    analise = pasta / referencia_analisar.PASTA_ANALISE
    return {
        "pasta": relativo(args.raiz, pasta),
        "analise": relativo(args.raiz, analise),
        "formato": relativo(args.raiz, analise / "formato.json"),
        "leitura": relativo(args.raiz, analise / "leitura.md"),
        "duracao": formato["duracao"],
        "cenas": formato["cenas"],
        "cortes": formato["cortes"],
        "quadros": len(formato["quadros"]),
        "folhas": [relativo(args.raiz, analise / f["arquivo"]) for f in formato["folhas"]],
        "fala": bool(formato["fala"] and formato["fala"].get("palavras")),
        "leia": formato["leia"],
    }


def referencia_criar(args: argparse.Namespace) -> dict[str, Any]:
    try:
        return sob_medida.criar(args.raiz, args.slug, titulo=args.titulo, origem_url=args.origem_url,
                                pedido=args.pedido)
    except sob_medida.ErroSobMedida as erro:
        raise cli.ErroEntrada(str(erro)) from None


def referencia_montar(args: argparse.Namespace) -> dict[str, Any]:
    pasta = sob_medida.pasta_do_reel(args.raiz, args.pasta)
    timeline = _etapa_referencia(reel_referencia.montar, args.raiz, pasta)
    midia = pasta / sob_medida.MIDIA
    return {
        "pasta": relativo(args.raiz, pasta),
        "timeline": relativo(args.raiz, midia / "timeline.json"),
        "trilha": relativo(args.raiz, midia / "trilha.wav"),
        "cenas": len(timeline["cenas"]),
        "quadros": timeline["totalFrames"],
        "avisos": timeline.get("_avisos", []),
    }


def referencia_previa(args: argparse.Namespace) -> dict[str, Any]:
    pasta = sob_medida.pasta_do_reel(args.raiz, args.pasta)
    return _etapa_referencia(reel_referencia.previa, args.raiz, pasta, porta_voz=args.porta_voz, canal=args.canal)


def referencia_render(args: argparse.Namespace) -> dict[str, Any]:
    pasta = sob_medida.pasta_do_reel(args.raiz, args.pasta)
    return _etapa_referencia(reel_referencia.renderizar, args.raiz, pasta, porta_voz=args.porta_voz,
                             canal=args.canal, origem="skill")


# ---------------------------------------------------------------- produzir


def produzir_reel_corte(args: argparse.Namespace) -> dict[str, Any]:
    dados = _ler_json(args.entrada, "entrada")
    try:
        return reel_corte.produzir(args.raiz, dados, origem="skill")
    except reel_corte.ErroEntradaCorte as erro:
        raise cli.ErroEntrada(str(erro)) from None
    except reel_corte.ErroVerificacaoReprovada as erro:
        raise _falha(cli.ERRO, "verificacao_reprovada", str(erro), peca_id=erro.peca_id, achados=erro.achados) from None
    except reel_corte.ErroProducaoCorte as erro:
        raise _falha(cli.ERRO, "producao", str(erro)) from None


def produzir_abertura(args: argparse.Namespace) -> dict[str, Any]:
    pasta = absoluto(args.raiz, args.pasta)
    if not pasta.is_dir():
        raise cli.ErroEntrada(f"campo 'pasta': pasta de montagem não encontrada: {args.pasta}")
    if args.dispensar:
        abertura.dispensar(pasta)
        return {"pasta": relativo(args.raiz, pasta), "dispensada": True}
    if not (args.prompt or "").strip():
        raise cli.ErroEntrada("campo 'prompt': informe --prompt (o que acontece no plano, em inglês) ou --dispensar")
    try:
        r = abertura.gerar(args.raiz, pasta, prompt=args.prompt, tipo=args.tipo, porta_voz=args.porta_voz,
                           duracao=args.duracao, estilo=args.estilo,
                           transformar_no_conteudo=not args.sem_transformar, pedido_por="skill")
    except ValueError as erro:
        raise cli.ErroEntrada(str(erro)) from None
    except (abertura.ErroAbertura, higgsfield.ErroHiggsfield) as erro:
        raise _falha(cli.ERRO, "abertura", str(erro)) from None
    return {"pasta": relativo(args.raiz, pasta), "abertura": relativo(args.raiz, pasta / "abertura.mp4"),
            "marcador": relativo(args.raiz, pasta / "abertura.json"), **r}
