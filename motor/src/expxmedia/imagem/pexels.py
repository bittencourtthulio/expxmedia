"""Pexels: foto e vídeo de banco na capacidade `banco_imagens` (D-28, CONTRATO-capacidades).

Um módulo só para foto e vídeo, com a chave `PEXELS_API_KEY` lida do `.env` da instalação
(nunca do ambiente do processo, M12/M14). Antes de qualquer chamada, `ambiente.verificar`
confere a capacidade; desligada, levanta `ErroCapacidade` com o `como_habilitar` e nada sai
para a rede.

- Autenticação: cabeçalho `Authorization: <chave>`, **sem** `Bearer` (base/api-pexels.md).
- Fotos em `GET /v1/search`, vídeos em `GET /v1/videos/search`.
- 429 é `ErroPexels(codigo="limite_excedido")` **sem nova tentativa**: a cota da hora estourou e
  insistir na hora só gasta a próxima (origem: Instagram-Carrosseis/galeria/_galeria.py:485).
  Nenhum código é retentado.
- A resposta volta normalizada: `id, midia, url (arquivo), pagina, largura, altura, alt,
  duracao, autor, autor_url, fonte, licenca`. Autor e página são o crédito que a peça grava.
- **Mídia do Pexels nunca entra em template** (D-28): a licença não permite redistribuir o arquivo
  solto, então `baixar` recusa destino em `galeria/` ou em qualquer pasta `templates/`. Template
  guarda a consulta; o download acontece na instalação de quem usa, com a chave dela.

Uso:

    from expxmedia.imagem import pexels
    itens = pexels.buscar(raiz, "bread oven", midia="video", orientacao="portrait")
    pexels.baixar(raiz, itens[0], "pecas/2026-09/P-.../broll/01.mp4")
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

import requests

from expxmedia.ambiente.verificar import ErroCapacidade, Verificador
from expxmedia.nucleo import raiz as instalacao

__all__ = ["ErroPexels", "buscar", "baixar", "normalizar_foto", "normalizar_video", "URL_BASE"]

URL_BASE = "https://api.pexels.com"
CAMINHOS = {"foto": "/v1/search", "video": "/v1/videos/search"}
CHAVE_ENV = "PEXELS_API_KEY"
CAPACIDADE = "banco_imagens"
PROVEDOR = "pexels"
ORIENTACOES = ("portrait", "landscape", "square")  # origem: Instagram-Carrosseis/galeria/_galeria.py:452
POR_PAGINA_MAX = 80  # teto da API (base/api-pexels.md)
POR_PAGINA_PADRAO = 12  # origem: Instragram-Videos/pipeline/broll.py:46
TIMEOUT_BUSCA = 30  # s; origem: Instagram-Carrosseis/galeria/_galeria.py:480
TIMEOUT_DOWNLOAD = 180  # s; origem: Instragram-Videos/pipeline/broll.py:171
ALTURA_MINIMA_VIDEO = 720  # origem: Instragram-Videos/pipeline/broll.py:59
ALTURA_ALVO_VIDEO = 1920  # origem: Instragram-Videos/pipeline/lib.py (H do reel 1080x1920)
LICENCA = "Pexels License — uso comercial permitido, atribuição não exigida"  # origem: Instragram-Videos/pipeline/broll.py:191
_PASTAS_PROIBIDAS = ("galeria", "templates")


class ErroPexels(RuntimeError):
    """Falha do provedor, com `codigo` estável. A mensagem nunca traz a chave (M14)."""

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


def _chave(raiz: Path) -> str:
    verificador = Verificador(raiz)
    consulta = verificador.verificar(CAPACIDADE)
    if not consulta["habilitada"] or consulta["provedor"] != PROVEDOR:
        raise ErroCapacidade(
            f"{CAPACIDADE} não está habilitada pelo {PROVEDOR}. {consulta['como_habilitar'] or ''}".strip()
        )
    return verificador.env[CHAVE_ENV].strip()


def buscar(
    raiz: Path | str,
    termo: str,
    *,
    midia: str = "foto",
    orientacao: str | None = "portrait",
    por_pagina: int = POR_PAGINA_PADRAO,
    pagina: int = 1,
    url_base: str = URL_BASE,
    altura_alvo: int = ALTURA_ALVO_VIDEO,
    timeout: float = TIMEOUT_BUSCA,
) -> list[dict[str, Any]]:
    """Uma página de resultados do Pexels, normalizada. Termo em inglês descrevendo a imagem.

    `orientacao` None não filtra. `altura_alvo` escolhe o arquivo de vídeo (o mais próximo dela);
    vem do formato da peça, 1920 é o reel vertical.
    """
    if midia not in CAMINHOS:
        raise ValueError(f"midia é {' ou '.join(CAMINHOS)}, não {midia!r}")
    if orientacao is not None and orientacao not in ORIENTACOES:
        raise ValueError(f"orientacao é {', '.join(ORIENTACOES)}, não {orientacao!r}")
    if not 1 <= int(por_pagina) <= POR_PAGINA_MAX:
        raise ValueError(f"por_pagina vai de 1 a {POR_PAGINA_MAX}")
    if not (termo or "").strip():
        raise ValueError("termo de busca vazio")
    chave = _chave(Path(raiz))
    parametros: dict[str, Any] = {"query": termo.strip(), "per_page": int(por_pagina), "page": int(pagina)}
    if orientacao is not None:
        parametros["orientation"] = orientacao
    try:
        resposta = requests.get(
            url_base.rstrip("/") + CAMINHOS[midia],
            params=parametros,
            headers={"Authorization": chave},
            timeout=timeout,
        )
    except requests.RequestException as erro:
        raise ErroPexels("rede", f"Pexels inacessível: {type(erro).__name__}") from None
    _conferir_status(resposta.status_code)
    try:
        corpo = resposta.json()
    except ValueError:
        raise ErroPexels("resposta_invalida", "o Pexels não devolveu JSON") from None
    if midia == "foto":
        return [normalizar_foto(f) for f in corpo.get("photos") or [] if isinstance(f, dict)]
    return [normalizar_video(v, altura_alvo) for v in corpo.get("videos") or [] if isinstance(v, dict)]


def _conferir_status(status: int) -> None:
    if 200 <= status < 300:
        return
    if status == 429:
        raise ErroPexels(
            "limite_excedido",
            "o Pexels respondeu 429 (cota da hora estourada). Não insista agora: use o que já foi "
            "buscado ou tente mais tarde.",
        )
    if status == 401:
        raise ErroPexels("chave_recusada", f"o Pexels recusou {CHAVE_ENV} (HTTP 401); confira o .env. O valor não se imprime.")
    if status == 403:
        raise ErroPexels("bloqueado", "o Pexels respondeu 403 (bloqueio). Não insista agora.")
    raise ErroPexels(f"http_{status}", f"o Pexels respondeu HTTP {status}")


def normalizar_foto(foto: dict[str, Any]) -> dict[str, Any]:
    src = foto.get("src") or {}
    return {
        "id": foto.get("id"),
        "midia": "foto",
        "url": src.get("original") or src.get("large2x") or src.get("large") or "",
        "pagina": foto.get("url") or "",
        "largura": int(foto.get("width") or 0),
        "altura": int(foto.get("height") or 0),
        "alt": foto.get("alt") or "",
        "duracao": None,
        "autor": foto.get("photographer") or "",
        "autor_url": foto.get("photographer_url") or "",
        "fonte": PROVEDOR,
        "licenca": LICENCA,
    }


def melhor_arquivo(video: dict[str, Any], altura_alvo: int = ALTURA_ALVO_VIDEO) -> dict[str, Any]:
    """O arquivo mais alto que não seja absurdo de baixar; vertical ganha de horizontal.

    origem: Instragram-Videos/pipeline/broll.py:57-64 (altura >= 720, prefere altura >= largura,
    o mais próximo da altura do alvo).
    """
    arquivos = [f for f in video.get("video_files") or [] if isinstance(f, dict)]
    bons = [f for f in arquivos if f.get("link") and (f.get("height") or 0) >= ALTURA_MINIMA_VIDEO] or arquivos
    if not bons:
        return {}
    verticais = [f for f in bons if (f.get("height") or 0) >= (f.get("width") or 0)]
    return min(verticais or bons, key=lambda f: abs((f.get("height") or 0) - altura_alvo))


def normalizar_video(video: dict[str, Any], altura_alvo: int = ALTURA_ALVO_VIDEO) -> dict[str, Any]:
    arquivo = melhor_arquivo(video, altura_alvo)
    usuario = video.get("user") or {}
    return {
        "id": video.get("id"),
        "midia": "video",
        "url": arquivo.get("link") or "",
        "pagina": video.get("url") or "",
        "largura": int(arquivo.get("width") or video.get("width") or 0),
        "altura": int(arquivo.get("height") or video.get("height") or 0),
        "alt": "",
        "duracao": video.get("duration"),
        "autor": usuario.get("name") or "",
        "autor_url": usuario.get("url") or "",
        "fonte": PROVEDOR,
        "licenca": LICENCA,
    }


def _destino_permitido(raiz: Path, destino: str | Path) -> Path:
    relativo = instalacao.relativo(raiz, destino)  # M9: dentro da raiz, sem escapar
    partes = PurePosixPath(relativo).parts
    if partes[0] == "galeria" or "templates" in partes:
        raise ErroPexels(
            "destino_proibido",
            f"mídia do Pexels não entra em template nem na galeria ({relativo}): a licença não "
            "permite redistribuir o arquivo. Guarde a consulta no template e baixe na peça (D-28).",
        )
    return raiz / relativo


def baixar(raiz: Path | str, item: dict[str, Any], destino: str | Path, *, timeout: float = TIMEOUT_DOWNLOAD) -> str:
    """Baixa o arquivo de um item normalizado para `destino` (relativo à raiz) e devolve o caminho relativo.

    Recusa destino em `galeria/` ou em pasta `templates/` antes de qualquer download (D-28).
    """
    raiz = Path(raiz)
    alvo = _destino_permitido(raiz, destino)
    url = item.get("url") or ""
    if not url:
        raise ErroPexels("sem_arquivo", f"o item {item.get('id')} não tem arquivo para baixar")
    try:
        resposta = requests.get(url, timeout=timeout)
    except requests.RequestException as erro:
        raise ErroPexels("rede", f"download do Pexels falhou: {type(erro).__name__}") from None
    _conferir_status(resposta.status_code)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    temporario = alvo.with_name(alvo.name + ".parcial")
    temporario.write_bytes(resposta.content)
    temporario.replace(alvo)
    return instalacao.relativo(raiz, alvo)
