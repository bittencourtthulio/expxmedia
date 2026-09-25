"""Subcomandos de áudio, texto e reel de página do `expxmedia-motor` (D-11):

    narrar          --roteiro ARQ --porta-voz ID [--tipo reel|aula|...] --saida PASTA
    transcrever     --audio ARQ --saida ARQ.json [--modo varredura|alinhamento] [--modelo M] [--idioma X]
                    [--alinhamento ARQ.json]
    legendar reel   --alinhamento ARQ --roteiro ARQ --saida PASTA (--cta PALAVRA --card-final "..."... | --sem-cta)
                    [--offset S] [--porta-voz ID]
    legendar aula   --roteiro ARQ --transcricao ARQ --saida PASTA
    verificar       --perfil reel|reel_pagina|corte|sob_medida|aula VIDEO [--pasta PASTA] [--caps ARQ]
                    [--legendas ARQ] [--alinhamento ARQ] [--roteiro ARQ] [--srt ARQ] [--legenda-post ARQ]
    produzir reel-pagina --entrada reel.json

Arquivos de entrada (`--roteiro`, `--audio`, `--alinhamento` do legendar, VIDEO...) são relativos à
pasta atual; pastas e arquivos de saída (`--saida`) são relativos à raiz da instalação (M9). A copy do
card final e do selo vem de quem chama (peça, Alma), nunca daqui (M13).

Saídas: entrada inválida (arquivo ausente, CTA fora do roteiro, perfil desconhecido) sai com 2;
capacidade não habilitada, 3; verificação reprovada, 1 com o JSON completo (`aprovado: false` e os
achados); roteiro reprovado pelo gate ou reel reprovado na verificação, 1 com os achados.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from expxmedia import cli
from expxmedia.alma import carregar as alma_carregar
from expxmedia.legendar import aula as legenda_aula
from expxmedia.legendar import reel as legenda_reel
from expxmedia.legendar import srt
from expxmedia.narrar import base as narrar_base
from expxmedia.nucleo import arquivos
from expxmedia.nucleo.raiz import absoluto, relativo
from expxmedia.producao import reel_pagina
from expxmedia.transcrever import whisper
from expxmedia.video import verificar as _verificar

TIPOS_NARRAR = ("reel", "aula", "post_unico", "carrossel", "apresentacao")


def registrar(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("narrar", help="narra um roteiro na voz do porta-voz: mp3 + alinhamento por caractere")
    p.add_argument("--roteiro", required=True, help="arquivo de texto do roteiro (relativo à pasta atual)")
    p.add_argument("--porta-voz", dest="porta_voz", required=True)
    p.add_argument("--tipo", default="reel", choices=TIPOS_NARRAR, help="tipo de peça (escolhe os parâmetros de voz)")
    p.add_argument("--saida", required=True, help="pasta de saída, relativa à raiz")
    p.set_defaults(func=narrar)

    p = subparsers.add_parser("transcrever", help="transcreve áudio ou vídeo com tempo por palavra")
    p.add_argument("--audio", required=True, help="áudio ou vídeo (relativo à pasta atual)")
    p.add_argument("--saida", required=True, help="JSON da transcrição, relativo à raiz")
    p.add_argument("--modo", default="varredura", choices=list(whisper.MODOS))
    p.add_argument("--modelo", default=None)
    p.add_argument("--idioma", default=None, help="padrão: empresa.idioma da Alma")
    p.add_argument("--alinhamento", default=None, help="grava também o alinhamento por caractere aqui (relativo à raiz)")
    p.set_defaults(func=transcrever)

    legendar = cli.grupo(subparsers, "legendar", help="legendas em PNG (reel) ou SRT (aula)")
    p = legendar.add_parser("reel", help="legenda do reel: PNG por bloco, caps.txt, legendas.json, card do CTA e SRT")
    p.add_argument("--alinhamento", required=True, help="alinhamento por caractere no espaço do roteiro")
    p.add_argument("--roteiro", required=True)
    p.add_argument("--saida", required=True, help="pasta de saída, relativa à raiz")
    p.add_argument("--cta", default=None, help="palavra do CTA (tem de estar no roteiro)")
    p.add_argument("--sem-cta", dest="sem_cta", action="store_true", help="sem palavra destacada e sem card final")
    p.add_argument("--card-final", dest="card_final", action="append", default=[],
                   help="linha do card final, com {cta} onde entra a palavra (repita)")
    p.add_argument("--offset", type=float, default=legenda_reel.OFFSET_PADRAO,
                   help="atraso do áudio (0 em fala gravada)")
    p.add_argument("--porta-voz", dest="porta_voz", default=None, help="termos de várias palavras do léxico dele")
    p.set_defaults(func=legendar_reel)

    p = legendar.add_parser("aula", help="legenda de aula: texto do roteiro nos tempos da transcrição (42x2) e SRT")
    p.add_argument("--roteiro", required=True)
    p.add_argument("--transcricao", required=True, help="JSON da transcrição (palavras com tempo)")
    p.add_argument("--saida", required=True, help="pasta de saída, relativa à raiz")
    p.set_defaults(func=legendar_aula)

    p = subparsers.add_parser("verificar", help="verificação de entrega de um vídeo num perfil")
    p.add_argument("video", help="MP4 (relativo à pasta atual)")
    p.add_argument("--perfil", required=True, help=f"perfil: {', '.join(_verificar.PERFIS)}")
    p.add_argument("--pasta", default=None, help="pasta dos artefatos pelos nomes padrão (padrão: a do vídeo)")
    for nome, ajuda in (("caps", "caps.txt"), ("legendas", "legendas.json"), ("alinhamento", "alinhamento"),
                        ("roteiro", "roteiro"), ("srt", "SRT"), ("legenda-post", "texto do post")):
        p.add_argument(f"--{nome}", dest=nome.replace("-", "_"), default=None, help=f"{ajuda} (sobrepõe o da pasta)")
    p.set_defaults(func=verificar)

    produzir = cli.grupo(subparsers, "produzir", help="produção de peças")
    p = produzir.add_parser("reel-pagina", help="reel a partir de página: captura, gate, narração, legenda, montagem e verificação")
    p.add_argument("--entrada", required=True, help="JSON com url, titulo, roteiro, cta, impacto, card_final, selo...")
    p.set_defaults(func=produzir_reel_pagina)


# ---------------------------------------------------------------- apoio


def _arquivo(caminho: str, campo: str) -> Path:
    arq = Path(caminho).resolve()
    if not arq.is_file():
        raise cli.ErroEntrada(f"campo '{campo}': arquivo não encontrado: {caminho}")
    return arq


def _ler_texto(caminho: str, campo: str) -> str:
    try:
        return _arquivo(caminho, campo).read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise cli.ErroEntrada(f"campo '{campo}': o arquivo não é UTF-8") from None


def _ler_json(caminho: str, campo: str) -> Any:
    try:
        return json.loads(_ler_texto(caminho, campo))
    except json.JSONDecodeError as erro:
        raise cli.ErroEntrada(f"campo '{campo}': JSON inválido na linha {erro.lineno}: {erro.msg}") from None


def _alma(raiz: Path) -> alma_carregar.Alma:
    try:
        return alma_carregar.carregar(raiz)
    except alma_carregar.ErroAlmaAusente as erro:
        raise cli.ErroEntrada(str(erro)) from None


# ---------------------------------------------------------------- narrar e transcrever


def narrar(args: argparse.Namespace) -> dict[str, Any]:
    texto = _ler_texto(args.roteiro, "roteiro")
    try:
        r = narrar_base.narrar(args.raiz, texto, args.porta_voz, args.tipo, args.saida)
    except narrar_base.ErroNarrar as erro:
        dados = {"ok": False, "erro": erro.codigo, "mensagem": str(erro)}
        if erro.codigo in ("porta_voz_ausente", "texto_vazio", "alma_ilegivel"):
            raise cli.Falha(cli.ENTRADA_INVALIDA, dados) from None
        raise cli.Falha(cli.ERRO, dados) from None
    return {k: v for k, v in r.items() if k != "alinhamento"}


def transcrever(args: argparse.Namespace) -> dict[str, Any]:
    idioma = args.idioma or whisper.idioma_da_alma(_alma(args.raiz))
    try:
        t = whisper.transcrever(Path(args.audio).resolve(), idioma=idioma, modo=args.modo, modelo=args.modelo)
    except whisper.ErroTranscricao as erro:
        raise cli.ErroEntrada(str(erro)) from None
    destino = absoluto(args.raiz, args.saida)
    arquivos.gravar_json(destino, t)
    saida = {"transcricao": relativo(args.raiz, destino), "motor": t["motor"], "modelo": t["modelo"],
             "idioma": t["idioma"], "palavras": len(t["palavras"]), "alinhamento": None}
    if args.alinhamento:
        _, alinhamento = whisper.para_alinhamento(t["palavras"])
        arq = absoluto(args.raiz, args.alinhamento)
        arquivos.gravar_json(arq, alinhamento)
        saida["alinhamento"] = relativo(args.raiz, arq)
    return saida


# ---------------------------------------------------------------- legendar


def legendar_reel(args: argparse.Namespace) -> dict[str, Any]:
    alinhamento = _ler_json(args.alinhamento, "alinhamento")
    roteiro = _ler_texto(args.roteiro, "roteiro")
    if not args.sem_cta and not args.card_final:
        raise cli.ErroEntrada("campo 'card-final': informe as linhas do card final (com {cta}) ou use --sem-cta")
    alma = _alma(args.raiz)
    pronuncia = None
    if args.porta_voz:
        voz = narrar_base.porta_voz_da_alma(args.raiz, args.porta_voz).get("voz") or {}
        pronuncia = voz.get("pronuncia") if isinstance(voz, dict) else None
    destino = absoluto(args.raiz, args.saida)
    try:
        estilo, avisos = legenda_reel.estilo_da_alma(alma, raiz=args.raiz)
        r = legenda_reel.legendar_reel(alinhamento, roteiro, destino, estilo=estilo, cta=args.cta,
                                       sem_cta=args.sem_cta, termos_multi=legenda_reel.termos_multi(pronuncia),
                                       card_final=tuple(args.card_final) or ("{cta}",), offset=args.offset)
    except legenda_reel.ErroLegenda as erro:
        raise cli.ErroEntrada(str(erro)) from None
    arq_srt = srt.gravar_srt([{"start": ini, "end": fim, "lines": [txt]}
                              for (_, ini, fim), txt in zip(r["entradas"], r["textos"])], destino / "legendas.srt")
    return {
        "saida": relativo(args.raiz, destino),
        "caps": relativo(args.raiz, destino / "caps.txt"),
        "legendas": relativo(args.raiz, destino / "legendas.json"),
        "srt": relativo(args.raiz, arq_srt),
        **{k: r[k] for k in ("blocos", "cta", "duracao", "offset_audio", "ritmo_cadencia", "palavras_por_bloco",
                             "tamanho_card", "achados")},
        "avisos": avisos + r["avisos"],
    }


def legendar_aula(args: argparse.Namespace) -> dict[str, Any]:
    roteiro = _ler_texto(args.roteiro, "roteiro")
    transcricao = _ler_json(args.transcricao, "transcricao")
    destino = absoluto(args.raiz, args.saida)
    destino.mkdir(parents=True, exist_ok=True)
    try:
        r = legenda_aula.gerar(roteiro, transcricao, destino / "legendas.json", destino / "legendas.srt")
    except (ValueError, KeyError, TypeError) as erro:
        raise cli.ErroEntrada(f"legenda de aula: {erro}") from None
    return {"legendas": r["legendas"], "json": relativo(args.raiz, destino / r["json"]),
            "srt": relativo(args.raiz, destino / r["srt"])}


# ---------------------------------------------------------------- verificar


def verificar(args: argparse.Namespace) -> dict[str, Any]:
    if args.perfil not in _verificar.PERFIS:
        raise cli.ErroEntrada(f"perfil desconhecido: {args.perfil} (conhecidos: {', '.join(_verificar.PERFIS)})")
    video = Path(args.video).resolve()
    if not video.is_file():
        raise cli.ErroEntrada(f"campo 'video': arquivo não encontrado: {args.video}")
    pasta = Path(args.pasta).resolve() if args.pasta else video.parent
    art = _verificar.artefatos_da_pasta(pasta)
    for campo, atributo in (("caps", "caps_txt"), ("legendas", "legendas"), ("alinhamento", "alinhamento"),
                            ("roteiro", "roteiro"), ("srt", "srt"), ("legenda_post", "legenda_post")):
        valor = getattr(args, campo)
        if valor:
            setattr(art, atributo, _arquivo(valor, campo.replace("_", "-")))
    resultado = _verificar.verificar(video, args.perfil, art)
    if not resultado["aprovado"]:
        raise cli.Falha(cli.ERRO, {"ok": False, **resultado})
    return resultado


# ---------------------------------------------------------------- produzir


def produzir_reel_pagina(args: argparse.Namespace) -> dict[str, Any]:
    dados = _ler_json(args.entrada, "entrada")
    try:
        return reel_pagina.produzir(args.raiz, dados)
    except reel_pagina.ErroEntradaReel as erro:
        raise cli.ErroEntrada(str(erro)) from None
    except (reel_pagina.ErroRoteiroReprovado, reel_pagina.ErroVerificacaoReprovada) as erro:
        motivo = "roteiro_reprovado" if isinstance(erro, reel_pagina.ErroRoteiroReprovado) else "verificacao_reprovada"
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": motivo, "mensagem": str(erro), "peca_id": erro.peca_id,
                                   "achados": erro.achados}) from None
    except reel_pagina.ErroProducaoReel as erro:
        raise cli.ErroEntrada(str(erro)) from None
