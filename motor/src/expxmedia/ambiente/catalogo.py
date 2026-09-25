"""Catálogo de capacidades: o que o sistema sabe fazer e o que satisfaz cada provedor.

Fonte: `docs/contrato/CONTRATO-capacidades.md` (tabela "O catálogo do núcleo", provedores de
`publicar`/`agendar`, nomes canônicos do `.env`) e `CONTRATO-pack.md` (`capacidades.fornece`).

Cada provedor é satisfeito por uma combinação de:

- `env`: variáveis do `.env` que precisam estar preenchidas (`env_opcional` só documenta
  variáveis que ampliam o provedor, como `META_PAGE_ID` para o Facebook);
- `cli`: executável com login feito (a verificação roda um comando de status rápido);
- `binarios`: executáveis locais. Texto com `|` é alternativa (`whisper|faster-whisper`),
  `nome>=N` exige versão mínima, `chromium-playwright` é o navegador baixado pelo Playwright
  e `faster-whisper` é o pacote Python;
- `marcadores`: estado da instalação (`agendador_local` instalado, `aceite_galeria` dado,
  `oauth_youtube` feito); `ambiente.verificar` diz onde cada um é lido;
- `derivada_de` (na capacidade): basta uma das capacidades listadas estar habilitada.

Capacidade com `porta_voz` só vale para um porta-voz com aquele campo preenchido na Alma.

O provedor `teste` de `narrar` e `avatar` (D-34, D-39) só existe com
`EXPXMEDIA_PROVEDORES_TESTE=1`, e vem sempre depois do real: com os dois satisfeitos, a ordem
da tabela escolhe o real (regra 2).

Este módulo só descreve. Quem confere o ambiente é `ambiente.verificar`.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

__all__ = [
    "ErroCatalogo",
    "Provedor",
    "Capacidade",
    "Catalogo",
    "NUCLEO",
    "FLAG_TESTE",
    "MARCADORES",
]

FLAG_TESTE = "EXPXMEDIA_PROVEDORES_TESTE"

# Marcadores de estado da instalação e o que dizer quando faltam.
MARCADORES = {
    "agendador_local": "agendador local instalado",
    "aceite_galeria": "aceite da galeria compartilhada",
    "oauth_youtube": "OAuth do YouTube com escopo de upload",
}


class ErroCatalogo(ValueError):
    """Capacidade desconhecida, repetida ou declarada fora da forma do contrato."""


@dataclass(frozen=True)
class Provedor:
    id: str
    como_habilitar: str
    env: tuple[str, ...] = ()
    env_opcional: tuple[str, ...] = ()
    cli: str | None = None
    binarios: tuple[str, ...] = ()
    marcadores: tuple[str, ...] = ()
    somente_teste: bool = False

    def descrever(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "env": list(self.env),
            "env_opcional": list(self.env_opcional),
            "cli": self.cli,
            "binarios": list(self.binarios),
            "marcadores": list(self.marcadores),
            "somente_teste": self.somente_teste,
            "como_habilitar": self.como_habilitar,
        }


@dataclass(frozen=True)
class Capacidade:
    id: str
    descricao: str
    provedores: tuple[Provedor, ...]
    origem: str = "nucleo"
    derivada_de: tuple[str, ...] = ()
    porta_voz: str | None = None  # caminho do id no porta-voz da Alma, ex.: "voz.voz_id"

    def provedor(self, provedor_id: str) -> Provedor:
        for p in self.provedores:
            if p.id == provedor_id:
                return p
        raise ErroCatalogo(f"a capacidade {self.id} não tem o provedor {provedor_id}")

    def provedores_ativos(self, teste: bool) -> tuple[Provedor, ...]:
        """Provedores que existem neste ambiente: o de teste só com a flag ligada."""
        return tuple(p for p in self.provedores if teste or not p.somente_teste)

    def descrever(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "descricao": self.descricao,
            "origem": self.origem,
            "derivada_de": list(self.derivada_de),
            "porta_voz": self.porta_voz,
            "provedores": [p.descrever() for p in self.provedores],
        }


def _chave(nomes: str, onde: str) -> str:
    return f"Coloque {nomes} no .env. Onde conseguir: {onde}"


_PLAYWRIGHT = Provedor(
    "playwright",
    "Instale o Chromium do Playwright: cd motor && uv run playwright install chromium.",
    binarios=("chromium-playwright",),
)
_TESTE_NARRAR = Provedor(
    "teste",
    f"Provedor de teste (sinal sintético, sem custo): só com {FLAG_TESTE}=1.",
    somente_teste=True,
)
_TESTE_AVATAR = Provedor(
    "teste",
    f"Provedor de teste (vídeo sintético, sem custo): só com {FLAG_TESTE}=1.",
    somente_teste=True,
)
_EXPXFLOW = Provedor(
    "expxflow",
    _chave(
        "EXPXFLOW_API_KEY, EXPXFLOW_CLIENT_ID e EXPXFLOW_BASE_URL",
        "no painel do Expx Flow → Configurações → API Keys (a chave e o id do cliente); "
        "EXPXFLOW_BASE_URL é o endereço da API informado pelo Expx Flow.",
    ),
    env=("EXPXFLOW_API_KEY", "EXPXFLOW_CLIENT_ID", "EXPXFLOW_BASE_URL"),
)
_META_ONDE = (
    "developers.facebook.com → Graph API Explorer (token de longa duração com "
    "instagram_content_publish) e o id da conta profissional do Instagram."
)
_HIGGSFIELD = Provedor(
    "higgsfield",
    "Instale o CLI higgsfield e faça login: higgsfield auth login (abre o navegador).",
    cli="higgsfield",
)

NUCLEO: tuple[Capacidade, ...] = (
    Capacidade("renderizar_html", "HTML/CSS → PNG", (_PLAYWRIGHT,)),
    Capacidade(
        "renderizar_motion",
        "cenas → MP4",
        (
            Provedor(
                "remotion",
                "Instale Node 20 ou mais novo (https://nodejs.org) e o ffmpeg (https://ffmpeg.org).",
                binarios=("node>=20", "ffmpeg"),
            ),
        ),
    ),
    Capacidade(
        "editar_video",
        "cortar, juntar, reenquadrar, normalizar áudio",
        (Provedor("ffmpeg", "Instale o ffmpeg (https://ffmpeg.org).", binarios=("ffmpeg",)),),
    ),
    Capacidade(
        "narrar",
        "texto → voz, com tempo por caractere",
        (
            Provedor(
                "elevenlabs",
                _chave("ELEVENLABS_API_KEY", "https://elevenlabs.io → Profile → API Keys."),
                env=("ELEVENLABS_API_KEY",),
            ),
            _TESTE_NARRAR,
        ),
        porta_voz="voz.voz_id",
    ),
    Capacidade(
        "transcrever",
        "áudio/vídeo → texto com tempo por palavra",
        (
            Provedor(
                "whisper_local",
                "Instale o faster-whisper (cd motor && uv sync) ou o executável whisper.",
                binarios=("whisper|faster-whisper",),
            ),
        ),
    ),
    Capacidade(
        "legendar",
        "alinhamento → legenda queimada e SRT",
        (Provedor("local", "Habilite narrar ou transcrever: a legenda sai do alinhamento de uma delas."),),
        derivada_de=("narrar", "transcrever"),
    ),
    Capacidade(
        "avatar",
        "áudio → vídeo de porta-voz falando",
        (
            Provedor(
                "heygen",
                _chave("HEYGEN_API_KEY", "https://app.heygen.com → Settings → API."),
                env=("HEYGEN_API_KEY",),
            ),
            _TESTE_AVATAR,
        ),
        porta_voz="avatar.avatar_id",
    ),
    Capacidade(
        "imagem_ia",
        "texto → imagem",
        (
            Provedor(
                "openrouter",
                _chave("OPENROUTER_API_KEY", "https://openrouter.ai → Settings → Keys."),
                env=("OPENROUTER_API_KEY",),
            ),
        ),
    ),
    Capacidade("rosto_ia", "imagem do porta-voz em cena nova", (_HIGGSFIELD,), porta_voz="rosto_ia.id"),
    Capacidade("video_ia", "texto/imagem → vídeo curto", (_HIGGSFIELD,)),
    Capacidade(
        "banco_imagens",
        "busca de foto e vídeo de banco (b-roll)",
        (
            Provedor(
                "pexels",
                _chave("PEXELS_API_KEY", "https://www.pexels.com/api → Your API Key."),
                env=("PEXELS_API_KEY",),
            ),
        ),
    ),
    Capacidade("capturar_pagina", "screenshot e rolagem de página web", (_PLAYWRIGHT,)),
    Capacidade(
        "publicar",
        "publicar agora",
        (
            _EXPXFLOW,
            Provedor(
                "meta_graph",
                _chave("META_GRAPH_TOKEN e META_IG_USER_ID (e META_PAGE_ID para o Facebook)", _META_ONDE),
                env=("META_GRAPH_TOKEN", "META_IG_USER_ID"),
                env_opcional=("META_PAGE_ID",),
            ),
            Provedor(
                "youtube_api",
                _chave(
                    "YOUTUBE_CLIENT_SECRET_FILE (caminho do client_secret.json, relativo à raiz)",
                    "console.cloud.google.com → APIs e serviços → Credenciais → ID do cliente OAuth "
                    "(app para computador), com a YouTube Data API ativada; depois faça o OAuth "
                    "com escopo de upload.",
                ),
                env=("YOUTUBE_CLIENT_SECRET_FILE",),
                marcadores=("oauth_youtube",),
            ),
        ),
    ),
    Capacidade(
        "agendar",
        "publicar num horário futuro",
        (
            _EXPXFLOW,
            Provedor(
                "meta_graph",
                _chave("META_GRAPH_TOKEN e META_IG_USER_ID (e META_PAGE_ID para o Facebook)", _META_ONDE)
                + " E instale o agendador local (expxmedia doctor): a máquina precisa estar "
                "ligada no horário.",
                env=("META_GRAPH_TOKEN", "META_IG_USER_ID"),
                env_opcional=("META_PAGE_ID",),
                marcadores=("agendador_local",),
            ),
        ),
    ),
    Capacidade("automacao_dm", "comentário com palavra-chave → mensagem direta", (_EXPXFLOW,)),
    Capacidade(
        "galeria_compartilhada",
        "baixar e enviar templates da galeria pública",
        (
            Provedor(
                "github",
                "Instale o gh (https://cli.github.com), faça login com gh auth login e aceite o "
                "termo da galeria compartilhada ao instalar a camada galeria.",
                cli="gh",
                marcadores=("aceite_galeria",),
            ),
        ),
    ),
)


class Catalogo:
    """As capacidades do núcleo mais as fornecidas pelos packs registrados nesta instância."""

    def __init__(self, nucleo: Iterable[Capacidade] = NUCLEO) -> None:
        self._capacidades: dict[str, Capacidade] = {c.id: c for c in nucleo}

    def capacidades(self) -> list[Capacidade]:
        """Todas, na ordem: núcleo (ordem da tabela do contrato) e depois as de pack."""
        return list(self._capacidades.values())

    def obter(self, capacidade_id: str) -> Capacidade:
        try:
            return self._capacidades[capacidade_id]
        except KeyError:
            raise ErroCatalogo(f"capacidade desconhecida: {capacidade_id}") from None

    def descrever(self, capacidade_id: str) -> dict[str, Any]:
        """Forma JSON da capacidade, igual para as do núcleo e as de pack."""
        return self.obter(capacidade_id).descrever()

    def registrar_pack(self, pack_id: str, fornece: Iterable[Mapping[str, Any]]) -> list[Capacidade]:
        """Registra `capacidades.fornece` de um `pack.json` (CONTRATO-pack). Tudo ou nada."""
        novas = [_de_pack(pack_id, item) for item in fornece]
        vistos = set()
        for cap in novas:
            if cap.id in self._capacidades or cap.id in vistos:
                dono = self._capacidades[cap.id].origem if cap.id in self._capacidades else pack_id
                raise ErroCatalogo(f"o pack {pack_id} repete a capacidade {cap.id} (já fornecida por {dono})")
            vistos.add(cap.id)
        for cap in novas:
            self._capacidades[cap.id] = cap
        return novas


def _de_pack(pack_id: str, item: Mapping[str, Any]) -> Capacidade:
    if not isinstance(item, Mapping):
        raise ErroCatalogo(f"o pack {pack_id} declara capacidade fora da forma de objeto")
    cap_id = item.get("id")
    if not isinstance(cap_id, str) or not cap_id:
        raise ErroCatalogo(f"o pack {pack_id} declara capacidade sem id")
    como = item.get("como_habilitar")
    if not isinstance(como, str) or not como.strip():
        raise ErroCatalogo(f"a capacidade {cap_id} do pack {pack_id} não tem como_habilitar")
    brutos = item.get("provedores")
    if not isinstance(brutos, list) or not brutos:
        raise ErroCatalogo(f"a capacidade {cap_id} do pack {pack_id} não tem provedores")
    provedores = []
    for p in brutos:
        if not isinstance(p, Mapping) or not isinstance(p.get("id"), str):
            raise ErroCatalogo(f"a capacidade {cap_id} do pack {pack_id} tem provedor sem id")
        provedores.append(
            Provedor(
                id=p["id"],
                como_habilitar=como,
                env=tuple(p.get("env") or ()),
                env_opcional=tuple(p.get("env_opcional") or ()),
                cli=p.get("cli"),
                binarios=tuple(p.get("binarios") or ()),
                marcadores=tuple(p.get("marcadores") or ()),
            )
        )
    for m in (m for p in provedores for m in p.marcadores):
        if m not in MARCADORES:
            raise ErroCatalogo(f"a capacidade {cap_id} do pack {pack_id} usa marcador desconhecido: {m}")
    return Capacidade(
        id=cap_id,
        descricao=str(item.get("descricao") or ""),
        provedores=tuple(provedores),
        origem=pack_id,
        derivada_de=tuple(item.get("derivada_de") or ()),
        porta_voz=item.get("porta_voz"),
    )
