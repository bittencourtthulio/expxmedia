"""Subcomandos do `expxmedia-motor` para as skills /expxmedia:alma e /expxmedia:ambiente (D-11):

    alma extrair-site   --url URL [--saida alma/proposta.json]
    alma confirmar      [--proposta alma/proposta.json]
    ambiente exemplo
    ambiente criar-env
    ambiente gravar-chave --nome NOME        (o valor vem pelo stdin, nunca por argumento)

`alma extrair-site` lê o site (expxmedia.alma.site), baixa o logotipo para alma/assets e grava a
PROPOSTA; nunca grava alma/alma.json. `alma confirmar` é o "confirmo tudo": valida a proposta
contra o contrato, grava `confirmada_em` e `atualizado_em` no fuso da empresa (M5, M10) e a troca
por alma/alma.json de forma atômica (M15). Com violação, nada é gravado (sai 2 com as violações).

`ambiente exemplo` gera o .env.example pelo catálogo; `ambiente criar-env` cria o .env a partir
dele, só se não existir, e garante o .env no .gitignore (M14); `ambiente gravar-chave` grava uma
variável do catálogo no .env com o valor lido do stdin, para o caso de a pessoa colar a chave na
conversa: a saída nunca traz o valor e sempre avisa para girar a chave.

Caminhos são relativos à raiz da instalação (M9). Numa pasta nova, sem alma/, passe `--raiz .`.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from expxmedia import cli
from expxmedia.alma import carregar as alma_carregar
from expxmedia.alma import schema, site
from expxmedia.ambiente import envexample
from expxmedia.ambiente.catalogo import Catalogo
from expxmedia.nucleo import arquivos
from expxmedia.nucleo.raiz import absoluto, relativo

PROPOSTA_PADRAO = "alma/proposta.json"
_RE_VALOR_CRU = re.compile(r"^[A-Za-z0-9_\-.:/+=@,]+$")
_RE_PROVEDOR = re.compile(r"^PROVEDOR_[A-Z][A-Z0-9_]*$")


def registrar(subparsers: argparse._SubParsersAction) -> None:
    alma = cli.grupo(subparsers, "alma", help="Alma da empresa")
    p = alma.add_parser("extrair-site", help="lê o site da empresa e grava a proposta de Alma (nunca a Alma)")
    p.add_argument("--url", required=True, help="endereço do site (http:// ou https://)")
    p.add_argument("--saida", default=PROPOSTA_PADRAO, help=f"proposta, relativa à raiz (padrão: {PROPOSTA_PADRAO})")
    p.set_defaults(func=alma_extrair_site)

    p = alma.add_parser("confirmar", help="o \"confirmo tudo\": valida a proposta e a grava como alma/alma.json")
    p.add_argument("--proposta", default=PROPOSTA_PADRAO, help=f"relativa à raiz (padrão: {PROPOSTA_PADRAO})")
    p.set_defaults(func=alma_confirmar)

    ambiente = cli.grupo(subparsers, "ambiente", help="o .env da instalação, sem nunca mostrar valor de chave")
    p = ambiente.add_parser("exemplo", help="gera o .env.example: o que cada chave libera e onde conseguir")
    p.set_defaults(func=ambiente_exemplo)
    p = ambiente.add_parser("criar-env", help="cria o .env a partir do .env.example, só se ainda não existir")
    p.set_defaults(func=ambiente_criar_env)
    p = ambiente.add_parser("gravar-chave", help="grava no .env uma variável do catálogo com o valor lido do stdin")
    p.add_argument("--nome", required=True, help="nome canônico da variável (ex.: ELEVENLABS_API_KEY)")
    p.set_defaults(func=ambiente_gravar_chave)


# ---------------------------------------------------------------- alma


def alma_extrair_site(args: argparse.Namespace) -> dict[str, Any]:
    try:
        r = site.extrair(args.url, args.raiz)
    except site.ErroSite as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "site_indisponivel", "mensagem": str(erro)}) from None
    destino = absoluto(args.raiz, args.saida)
    arquivos.gravar_json(destino, r["proposta"])
    return {
        "proposta": relativo(args.raiz, destino),
        "pendencias": r["proposta"]["pendencias"],
        "origens": r["proposta"]["origens"],
        "paginas": r["paginas"],
        "evidencias": r["evidencias"],
        "avisos": r["avisos"],
    }


def alma_confirmar(args: argparse.Namespace) -> dict[str, Any]:
    caminho = absoluto(args.raiz, args.proposta)
    if not caminho.is_file():
        raise cli.ErroEntrada(f"campo 'proposta': {args.proposta} não existe; rode alma extrair-site ou monte a proposta")
    try:
        proposta = arquivos.ler_json(caminho)
    except arquivos.ErroArquivo as erro:
        raise cli.ErroEntrada(f"campo 'proposta': {erro}") from None
    violacoes = schema.validar(proposta)
    if violacoes:
        raise cli.Falha(cli.ENTRADA_INVALIDA, {
            "ok": False, "erro": "proposta_fora_do_contrato", "violacoes": violacoes,
            "mensagem": "a proposta não cumpre o contrato da Alma; nada foi gravado",
        })
    try:
        fuso = ZoneInfo(proposta["empresa"]["fuso"])
    except (ZoneInfoNotFoundError, ValueError):
        raise cli.ErroEntrada(f"empresa.fuso não é um fuso IANA conhecido: {proposta['empresa']['fuso']!r}") from None
    agora = datetime.now(fuso).isoformat(timespec="seconds")
    proposta["confirmada_em"] = agora
    proposta["atualizado_em"] = agora
    destino = alma_carregar.caminho_alma(args.raiz)
    arquivos.gravar_json(destino, proposta)
    if caminho.resolve() != destino.resolve():
        caminho.unlink()
    return {"alma": relativo(args.raiz, destino), "confirmada_em": agora,
            "pendencias": proposta["pendencias"], "portao": alma_carregar.portao(args.raiz)}


# ---------------------------------------------------------------- ambiente


def _gravar_texto(destino: Path, texto: str, modo: int | None = None) -> None:
    fd, temporario = tempfile.mkstemp(dir=destino.parent, prefix=destino.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        if modo is not None:
            os.chmod(temporario, modo)
        os.replace(temporario, destino)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise


def ambiente_exemplo(args: argparse.Namespace) -> dict[str, Any]:
    destino = envexample.escrever(args.raiz)
    return {"arquivo": relativo(args.raiz, destino)}


def _garantir_gitignore(raiz: Path) -> bool:
    gitignore = raiz / ".gitignore"
    linhas = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.is_file() else []
    if ".env" in (l.strip() for l in linhas):
        return False
    texto = "\n".join(linhas + [".env"]) + "\n"
    _gravar_texto(gitignore, texto)
    return True


def ambiente_criar_env(args: argparse.Namespace) -> dict[str, Any]:
    raiz = Path(args.raiz)
    env = raiz / ".env"
    exemplo = raiz / envexample.NOME_ARQUIVO
    if not exemplo.is_file():
        envexample.escrever(raiz)
    gitignore = _garantir_gitignore(raiz)
    if env.exists():
        return {"criado": False, "arquivo": ".env", "gitignore_atualizado": gitignore,
                "mensagem": "o .env já existe e não foi tocado"}
    _gravar_texto(env, exemplo.read_text(encoding="utf-8"), modo=0o600)
    return {"criado": True, "arquivo": ".env", "gitignore_atualizado": gitignore,
            "mensagem": "cole cada chave no .env, na linha dela; nunca na conversa"}


def _nomes_do_catalogo() -> set[str]:
    nomes: set[str] = set()
    for cap in Catalogo().capacidades():
        for provedor in cap.provedores:
            if not provedor.somente_teste:
                nomes.update(provedor.env)
                nomes.update(provedor.env_opcional)
    return nomes


def ambiente_gravar_chave(args: argparse.Namespace) -> dict[str, Any]:
    nome = args.nome.strip()
    if nome not in _nomes_do_catalogo() and not _RE_PROVEDOR.match(nome):
        raise cli.ErroEntrada(f"campo 'nome': {nome} não está no catálogo de variáveis do ExpxMedia (M12)")
    valor = sys.stdin.read().strip()
    if not valor:
        raise cli.ErroEntrada(f"nenhum valor recebido no stdin para {nome}")
    if "\n" in valor:
        raise cli.ErroEntrada(f"o valor de {nome} tem mais de uma linha")
    if _RE_VALOR_CRU.match(valor):
        linha_nova = f"{nome}={valor}"
    elif "'" not in valor:
        linha_nova = f"{nome}='{valor}'"
    else:
        raise cli.ErroEntrada(f"o valor de {nome} tem caracteres que o .env não guarda sem ambiguidade; cole-o no arquivo")
    env = Path(args.raiz) / ".env"
    linhas = env.read_text(encoding="utf-8-sig").splitlines() if env.is_file() else []
    padrao = re.compile(rf"^\s*(export\s+)?{re.escape(nome)}\s*=")
    novas, trocou = [], False
    for linha in linhas:
        if padrao.match(linha):
            if not trocou:
                novas.append(linha_nova)
                trocou = True
            continue
        novas.append(linha)
    if not trocou:
        novas.append(linha_nova)
    _gravar_texto(env, "\n".join(novas) + "\n", modo=0o600)
    return {
        "nome": nome,
        "gravada": True,
        "arquivo": ".env",
        "aviso": (f"{nome} foi gravada no .env. Como o valor passou pela conversa, ele ficou no histórico do "
                  "assistente: é bom girar a chave no provedor e colar a nova direto no arquivo."),
    }
