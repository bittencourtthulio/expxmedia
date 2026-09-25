"""OpenRouter: texto (e, opcionalmente, uma imagem de base) → imagem, na capacidade `imagem_ia`.

Caminho de chat completions com `modalities: ["image", "text"]`, o mesmo da origem
(origem: Instagram-Carrosseis/galeria/_galeria.py:767-797). A imagem volta como **data URL
base64** em `choices[0].message.images[].image_url.url`; o motor decodifica, confere que abre
como imagem e grava **PNG** no caminho de saída, qualquer que seja o formato que o provedor mandou.

- Chave `OPENROUTER_API_KEY` do `.env` da instalação (nunca do processo), em
  `Authorization: Bearer <chave>`. Capacidade conferida por `ambiente.verificar` antes.
- Modelo configurável: parâmetro `modelo`; senão `OPENROUTER_MODELO_IMAGEM` do `.env`; senão o
  padrão da origem. Slug de modelo muda no provedor, por isso não fica preso ao código.
- Proporção configurável: `proporcao` ("9:16", "4:5"...) vai em `image_config.aspect_ratio`.
  O provedor pode ajustar a proporção em silêncio: a resposta traz as dimensões gravadas.
- Nenhum código é retentado. 401/403, 402, 429 e demais viram `ErroOpenRouter` com `codigo`.
- `cota`: fábrica opcional de gerenciador de contexto por provedor (`cota.Cota(raiz).consumir`);
  confere o teto antes e anota depois, mesmo se a chamada falhar (o que saiu do cartão conta).

Uso:

    from expxmedia.imagem import openrouter
    openrouter.gerar(raiz, "a loaf of bread on a table...", "pecas/.../img.png", proporcao="4:5")
"""
from __future__ import annotations

import base64
import binascii
import contextlib
import io
import mimetypes
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

import requests
from PIL import Image, UnidentifiedImageError

from expxmedia.ambiente.verificar import ErroCapacidade, Verificador
from expxmedia.nucleo import raiz as instalacao

__all__ = ["ErroOpenRouter", "gerar", "MODELO_PADRAO", "URL_BASE"]

URL_BASE = "https://openrouter.ai"
CAMINHO = "/api/v1/chat/completions"
CHAVE_ENV = "OPENROUTER_API_KEY"
MODELO_ENV = "OPENROUTER_MODELO_IMAGEM"  # origem: Instagram-Carrosseis/galeria/_galeria.py:770
MODELO_PADRAO = "google/gemini-3-pro-image"  # origem: Instagram-Carrosseis/galeria/_galeria.py:702
CAPACIDADE = "imagem_ia"
PROVEDOR = "openrouter"
TIMEOUT_GERACAO = 300  # s; origem: Instagram-Carrosseis/galeria/_galeria.py:780

Cota = Callable[[str], AbstractContextManager[Any]]


class ErroOpenRouter(RuntimeError):
    """Falha do provedor, com `codigo` estável. A mensagem nunca traz a chave (M14)."""

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


def _ambiente(raiz: Path) -> tuple[str, str | None]:
    verificador = Verificador(raiz)
    consulta = verificador.verificar(CAPACIDADE)
    if not consulta["habilitada"] or consulta["provedor"] != PROVEDOR:
        raise ErroCapacidade(
            f"{CAPACIDADE} não está habilitada pelo {PROVEDOR}. {consulta['como_habilitar'] or ''}".strip()
        )
    modelo_env = verificador.env.get(MODELO_ENV, "").strip() or None
    return verificador.env[CHAVE_ENV].strip(), modelo_env


def _data_uri(arquivo: Path) -> str:
    mime = mimetypes.guess_type(arquivo.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(arquivo.read_bytes()).decode("ascii")


def gerar(
    raiz: Path | str,
    prompt: str,
    saida: str | Path,
    *,
    modelo: str | None = None,
    proporcao: str | None = None,
    base: str | Path | None = None,
    url_base: str = URL_BASE,
    timeout: float = TIMEOUT_GERACAO,
    cota: Cota | None = None,
) -> dict[str, Any]:
    """Gera uma imagem e grava PNG em `saida` (relativo à raiz). Devolve caminho relativo e metadados.

    `base`: imagem da instalação (caminho relativo) que vai junto, para variação imagem→imagem.
    """
    raiz = Path(raiz)
    if not (prompt or "").strip():
        raise ValueError("prompt vazio")
    destino = instalacao.absoluto(raiz, saida)
    chave, modelo_env = _ambiente(raiz)
    modelo = modelo or modelo_env or MODELO_PADRAO

    conteudo: list[dict[str, Any]] = [{"type": "text", "text": prompt.strip()}]
    if base is not None:
        conteudo.append({"type": "image_url", "image_url": {"url": _data_uri(instalacao.absoluto(raiz, base))}})
    corpo: dict[str, Any] = {
        "model": modelo,
        "modalities": ["image", "text"],
        "messages": [{"role": "user", "content": conteudo}],
    }
    if proporcao:
        corpo["image_config"] = {"aspect_ratio": proporcao}

    guarda = cota(PROVEDOR) if cota is not None else contextlib.nullcontext()
    with guarda:
        try:
            resposta = requests.post(
                url_base.rstrip("/") + CAMINHO,
                json=corpo,
                headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
                timeout=timeout,
            )
        except requests.RequestException as erro:
            raise ErroOpenRouter("rede", f"OpenRouter inacessível: {type(erro).__name__}") from None
        _conferir_status(resposta)
        try:
            dados = resposta.json()
        except ValueError:
            raise ErroOpenRouter("resposta_invalida", "o OpenRouter não devolveu JSON") from None

    mensagem = ((dados.get("choices") or [{}])[0] or {}).get("message") or {}
    bruto = _imagem_da_mensagem(mensagem)
    if bruto is None:
        texto = str(mensagem.get("content") or "")[:200]
        raise ErroOpenRouter("sem_imagem", f"o modelo {modelo} não devolveu imagem (respondeu: {texto or 'nada'})")
    try:
        with Image.open(io.BytesIO(bruto)) as img:
            img.load()
            convertida = img.convert("RGBA") if img.mode in ("RGBA", "LA", "P") else img.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise ErroOpenRouter("imagem_invalida", "o que o modelo devolveu não abriu como imagem") from None

    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".parcial")
    convertida.save(temporario, "PNG")
    temporario.replace(destino)
    return {
        "caminho": instalacao.relativo(raiz, destino),
        "provedor": PROVEDOR,
        "modelo": modelo,
        "proporcao": proporcao,
        "largura": convertida.width,
        "altura": convertida.height,
        "texto": str(mensagem.get("content") or "")[:200],
    }


def _imagem_da_mensagem(mensagem: dict[str, Any]) -> bytes | None:
    for item in mensagem.get("images") or []:
        url = ((item or {}).get("image_url") or {}).get("url") or ""
        if url.startswith("data:image/") and "," in url:
            try:
                return base64.b64decode(url.split(",", 1)[1], validate=False)
            except (binascii.Error, ValueError):
                return b""
    return None


def _conferir_status(resposta: requests.Response) -> None:
    status = resposta.status_code
    if 200 <= status < 300:
        return
    try:
        detalhe = str(((resposta.json() or {}).get("error") or {}).get("message") or "")[:200]
    except (ValueError, AttributeError):
        detalhe = ""
    if status in (401, 403):
        raise ErroOpenRouter("chave_recusada" if status == 401 else "recusado",
                             f"o OpenRouter recusou (HTTP {status}); confira {CHAVE_ENV} no .env. {detalhe}".strip())
    if status == 402:
        raise ErroOpenRouter("sem_credito", f"o OpenRouter respondeu 402 (créditos insuficientes). {detalhe}".strip())
    if status == 429:
        raise ErroOpenRouter("limite_excedido", f"o OpenRouter respondeu 429 (limite de ritmo). Não insista agora. {detalhe}".strip())
    raise ErroOpenRouter(f"http_{status}", f"o OpenRouter respondeu HTTP {status}. {detalhe}".strip())
