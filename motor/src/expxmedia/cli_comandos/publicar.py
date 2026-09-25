"""Subcomandos de publicação e do agendador local do `expxmedia-motor` (D-07, D-08, D-11, D-29, D-30).

    publicar --peca ID [--canal C]... [--confirmar] [--forcar]
    agendar --peca ID --para MOMENTO_ISO [--canal C]... [--confirmar] [--forcar]
    agendador rodar [--raiz RAIZ]
    agendador instalar [--aplicar] [--sistema S] [--executavel CAMINHO]

`publicar` e `agendar` são **dry-run por padrão**: sem `--confirmar`, o provedor escolhido valida e
monta o envio, e nada é enviado nem gravado na peça. Com `--confirmar`, envia uma vez só
(`publicar.base`: intenção antes do envio, POST nunca retentado).

O provedor sai de `ambiente.verificar`; `PROVEDOR_PUBLICAR`/`PROVEDOR_AGENDAR` apontando para
provedor não satisfeito sai com código 3 e o `como_habilitar`, sem trocar de provedor (D-07).

`agendador rodar` é uma rodada de `agendador.servico` — o que o LaunchAgent, a unidade systemd, a
tarefa do Windows ou o cron chamam a cada minuto. `agendador instalar` sem `--aplicar` só mostra o
que instalaria.

Códigos de saída além dos do `cli`: recusa da publicação (peça não aprovada, horário ou canal
inválido, duplicada, não cabe no provedor) sai 2; falha de envio sai 1, com `incerto` dizendo se o
provedor pode ter criado o post; falha ao instalar o agendador sai 1.
"""
from __future__ import annotations

import argparse
from typing import Any

from expxmedia import cli
from expxmedia.agendador import instalar as agendador_instalar
from expxmedia.agendador import servico as agendador_servico
from expxmedia.ambiente.verificar import ErroCapacidade
from expxmedia.peca import modelo
from expxmedia.publicar import base

CANAL_PADRAO = "instagram"
SISTEMAS = ("macos", "windows", "linux")
# recusas antes de qualquer envio: entrada da pessoa, não falha do provedor
_CODIGOS_ENTRADA = {"peca_nao_aprovada", "horario_invalido", "canal_invalido", "validacao", "ja_enviada",
                    "canal_ocupado", "midia_fora_da_peca"}
# a capacidade existe, mas não do jeito pedido (ex.: automação de DM fora do expxflow)
_CODIGOS_CAPACIDADE = {"automacao_indisponivel", "provedor_sem_adaptador", "sem_credenciais"}


def registrar(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("publicar", help="publica a peça agora (dry-run sem --confirmar)")
    _argumentos_envio(p)
    p.set_defaults(func=publicar, capacidade="publicar")

    p = subparsers.add_parser("agendar", help="agenda a peça para um horário (dry-run sem --confirmar)")
    _argumentos_envio(p)
    p.add_argument("--para", required=True, help="momento ISO 8601 com fuso, ex.: 2026-09-25T12:00:00-03:00")
    p.set_defaults(func=publicar, capacidade="agendar")

    agendador = cli.grupo(subparsers, "agendador", help="agendador local (publica no horário via meta_graph)")
    p = agendador.add_parser("rodar", help="uma rodada: publica o que chegou no horário (chamado pelo SO)")
    p.set_defaults(func=agendador_rodar)

    p = agendador.add_parser("instalar", help="instala o disparo de minuto em minuto no SO (sem --aplicar só mostra)")
    p.add_argument("--aplicar", action="store_true", help="escreve os arquivos e roda os comandos de instalação")
    p.add_argument("--sistema", default=None, choices=SISTEMAS, help="padrão: o sistema desta máquina")
    p.add_argument("--executavel", default=None, help="caminho do expxmedia-motor (padrão: o achado no PATH)")
    p.set_defaults(func=instalar_agendador)


def _argumentos_envio(p: argparse.ArgumentParser) -> None:
    p.add_argument("--peca", required=True, help="id da peça")
    p.add_argument("--canal", dest="canais", action="append", default=None, choices=sorted(modelo.CANAIS),
                   help=f"repita para mais de um canal (padrão: {CANAL_PADRAO})")
    p.add_argument("--confirmar", action="store_true", help="envia de verdade; sem ele é dry-run")
    p.add_argument("--forcar", action="store_true",
                   help="ignora a trava de envio duplicado (só depois de conferir no provedor)")


# ---------------------------------------------------------------- publicar / agendar


def publicar(args: argparse.Namespace) -> dict[str, Any]:
    capacidade = args.capacidade
    try:
        return base.publicar(
            args.raiz, args.peca,
            canais=args.canais or [CANAL_PADRAO],
            agendada_para=getattr(args, "para", None),
            dry_run=not args.confirmar,
            forcar=args.forcar,
        )
    except ErroCapacidade as erro:
        raise cli.CapacidadeNaoHabilitada(capacidade, str(erro)) from None
    except base.ErroEnvio as erro:
        raise cli.Falha(cli.ERRO, _falha(erro, capacidade, incerto=erro.incerto,
                                         status_http=erro.status_http)) from None
    except base.ErroValidacao as erro:
        raise cli.Falha(cli.ENTRADA_INVALIDA, _falha(erro, capacidade, achados=erro.achados)) from None
    except base.ErroPublicacao as erro:
        if erro.codigo in _CODIGOS_CAPACIDADE:
            raise cli.Falha(cli.CAPACIDADE_NAO_HABILITADA,
                            _falha(erro, capacidade, como_habilitar=str(erro))) from None
        codigo = cli.ENTRADA_INVALIDA if erro.codigo in _CODIGOS_ENTRADA else cli.ERRO
        raise cli.Falha(codigo, _falha(erro, capacidade)) from None


def _falha(erro: base.ErroPublicacao, capacidade: str, **extras: Any) -> dict[str, Any]:
    return {"ok": False, "erro": erro.codigo, "mensagem": str(erro), "capacidade": capacidade, **extras}


# ---------------------------------------------------------------- agendador


def agendador_rodar(args: argparse.Namespace) -> dict[str, Any]:
    return agendador_servico.rodar(args.raiz)


def instalar_agendador(args: argparse.Namespace) -> dict[str, Any]:
    try:
        return agendador_instalar.instalar(args.raiz, sistema=args.sistema, aplicar=args.aplicar,
                                           executavel=args.executavel)
    except agendador_instalar.ErroInstalacao as erro:
        raise cli.Falha(cli.ERRO, {"ok": False, "erro": "instalacao_agendador", "mensagem": str(erro),
                                   "aplicado": False}) from None
