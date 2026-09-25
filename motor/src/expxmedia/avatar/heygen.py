"""Provedor `heygen` da capacidade `avatar`: áudio da narração -> vídeo do porta-voz falando (D-26).

Sempre a partir do **áudio**, nunca do texto: com texto o HeyGen sintetiza outra locução, com outra
duração, e o PiP nunca sincroniza com a narração (base/avatar-heygen-processo-atual.md, origem:
cursos-ia/aula-skills-2/plano-gravacao.md:57-63). Só API v3; a v2 sai do ar em 2026-10-31
(base/api-heygen.md).

Fluxo (base/api-heygen.md):

1. `POST /v3/assets` multipart, campo `file`, com o mp3 -> `data.asset_id` (com fallback para
   `data.id`, divergência da doc);
2. `POST /v3/videos` com `type: avatar`, o `avatar_id` do porta-voz (`porta_vozes[].avatar.avatar_id`
   da Alma) e `audio_asset_id`; cabeçalho `Idempotency-Key` derivado do áudio e do pedido, para que
   uma repetição em 24 h não cobre de novo;
3. `GET /v3/videos/{video_id}` a cada `INTERVALO_POLLING_S` até `completed` ou `failed`; qualquer
   outro status (`waiting`, `pending`, `processing`...) é "em andamento". `failed` é terminal: erro com
   `failure_message`/`failure_code` do provedor e **nenhuma nova criação**;
4. download da `video_url` pré-assinada logo depois do `completed`, **sem** a chave no cabeçalho.

Estado retomável: o `video_id` fica em `<destino>.heygen.json` (com o sha256 do áudio e o pedido)
assim que o vídeo é criado. Se o polling estourar o tempo ou o processo cair, a próxima chamada com o
mesmo áudio e o mesmo pedido só consulta, não cria (nem paga) de novo. O arquivo some no `completed`
baixado e no `failed`.

Limites conferidos **antes** de qualquer chamada: áudio até 10 min (D-44, o menor dos dois limites
que a doc publica) e até 32 MB (upload simples de `/v3/assets`; o upload direto em 3 passos não é
usado).

- Chave `HEYGEN_API_KEY` do `.env` da instalação (nunca do processo, M12/M14), no cabeçalho
  `X-Api-Key`. Nenhuma mensagem de erro traz o valor dela.
- Erro HTTP vira `ErroAvatar(codigo="http_<status>")` com o `error.code` e o `error.message` do
  provedor. POST nunca é repetido automaticamente; no polling, 429/500/502/503/504 esperam
  (`Retry-After` quando vier) e tentam de novo dentro do tempo limite.
- `url_base` é configurável (stub nos testes).

Uso:

    from expxmedia.avatar import heygen
    r = heygen.gerar(raiz, "pecas/.../midia/narracao.mp3", "ana-souza", "pecas/.../midia/avatar.mp4")
    r["arquivo"], r["video_id"], r["duracao_s"]
"""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests

from expxmedia.ambiente.verificar import ErroCapacidade, Verificador
from expxmedia.nucleo import arquivos
from expxmedia.nucleo import raiz as instalacao

__all__ = [
    "PROVEDOR",
    "CAPACIDADE",
    "URL_BASE",
    "LIMITE_AUDIO_S",
    "LIMITE_UPLOAD_BYTES",
    "INTERVALO_POLLING_S",
    "TIMEOUT_POLLING_S",
    "PROPORCAO_PADRAO",
    "RESOLUCAO_PADRAO",
    "ErroAvatar",
    "exigir_provedor",
    "avatar_id_do_porta_voz",
    "conferir_audio",
    "gerar",
]

PROVEDOR = "heygen"
CAPACIDADE = "avatar"
CHAVE_ENV = "HEYGEN_API_KEY"
URL_BASE = "https://api.heygen.com"  # base/api-heygen.md (docs/api-key.md)
LIMITE_AUDIO_S = 600.0  # D-44: "Audio input: Maximum 10 minutes (600 seconds)" (base/api-heygen.md, usage-limits)
LIMITE_UPLOAD_BYTES = 32 * 1024 * 1024  # base/api-heygen.md (assets.md): POST /v3/assets aceita até 32 MB
# Intervalo de polling: a doc não informa; o exemplo dela usa 10 s (base/api-heygen.md, passo 3).
INTERVALO_POLLING_S = 10.0
# Teto do polling: a doc não informa tempo típico de render (base/api-heygen.md, risco 3). Valor do
# motor, não calibrado; a espera é retomável pelo estado gravado ao lado do destino.
TIMEOUT_POLLING_S = 3600.0
TIMEOUT_HTTP_S = 120.0  # por requisição; valor do motor
TIMEOUT_DOWNLOAD_S = 600.0  # valor do motor
# origem: cursos-ia/aula-skills-2/plano-gravacao.md:65 e cursos-ia/radar-ia-01-jev/README.md:13-14
# (twin em 4:5, 1080p). A composição de aula recorta a faixa 16:9 do canvas 1080x1350; outra
# proporção muda esse encaixe. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:11-13
PROPORCAO_PADRAO = "4:5"
RESOLUCAO_PADRAO = "1080p"
CAUDA_ERRO = 400  # caracteres do corpo quando o erro não vem no formato {"error": ...}
REPETIVEIS_POLLING = frozenset({429, 500, 502, 503, 504})  # base/api-heygen.md, tabela de erros
SUFIXO_ESTADO = ".heygen.json"


class ErroAvatar(RuntimeError):
    """Falha da capacidade `avatar`, com `codigo` estável. Nunca traz a chave (M14)."""

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


# ------------------------------------------------------------------ comum aos provedores

def exigir_provedor(raiz: Path | str, provedor: str, porta_voz: str) -> Verificador:
    """Confere, pelo `ambiente.verificar`, que `provedor` de avatar está satisfeito para o porta-voz.

    Falta de chave, de flag de teste ou de `avatar.avatar_id` na Alma vira `ErroCapacidade` com o
    que falta, antes de qualquer custo.
    """
    verificador = Verificador(raiz)
    consulta = verificador.verificar(CAPACIDADE, porta_voz)
    estado = next((p for p in consulta["provedores"] if p["id"] == provedor), None)
    if estado is None:
        raise ErroCapacidade(
            f"{CAPACIDADE} pelo provedor {provedor} não está disponível nesta instalação. "
            f"{consulta['como_habilitar'] or ''}".strip()
        )
    if estado["falta"]:
        orientacao = consulta["como_habilitar"] or ""
        raise ErroCapacidade(
            f"{CAPACIDADE} pelo {provedor} precisa de: {'; '.join(estado['falta'])}. {orientacao}".strip()
        )
    return verificador


def avatar_id_do_porta_voz(raiz: Path | str, porta_voz: str) -> str:
    alma = arquivos.ler_json(Path(raiz) / "alma" / "alma.json")
    for registro in (alma.get("porta_vozes") or []) if isinstance(alma, dict) else []:
        if isinstance(registro, dict) and registro.get("id") == porta_voz:
            avatar = registro.get("avatar") if isinstance(registro.get("avatar"), dict) else {}
            valor = avatar.get("avatar_id")
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
    raise ErroCapacidade(
        f"o porta-voz {porta_voz} não tem avatar.avatar_id preenchido em porta_vozes de alma/alma.json"
    )


def conferir_audio(caminho: Path) -> float:
    """Duração do áudio em segundos; recusa acima de `LIMITE_AUDIO_S` (D-44)."""
    from expxmedia.video import ffmpeg  # import tardio: só quem gera avatar precisa do ffprobe

    if not caminho.is_file():
        raise ErroAvatar("sem_audio", f"o áudio {caminho.name} não existe")
    try:
        duracao = ffmpeg.sondar(caminho)["duracao"]
    except ffmpeg.ErroFfmpeg as erro:
        raise ErroAvatar("audio_invalido", str(erro)) from None
    if duracao is None:
        raise ErroAvatar("audio_invalido", f"ffprobe não leu a duração de {caminho.name}")
    if duracao > LIMITE_AUDIO_S:
        raise ErroAvatar(
            "audio_longo",
            f"o áudio tem {duracao:.1f} s e o avatar aceita até {LIMITE_AUDIO_S:.0f} s (10 min, D-44); "
            "divida a narração em partes menores",
        )
    return float(duracao)


def _caminhos(raiz: Path, audio: Path | str, destino: Path | str) -> tuple[Path, Path]:
    return raiz / instalacao.relativo(raiz, audio), raiz / instalacao.relativo(raiz, destino)


# ------------------------------------------------------------------ HTTP

def _erro_http(resposta: requests.Response, chave: str, etapa: str) -> ErroAvatar:
    try:
        erro = (resposta.json() or {}).get("error") or {}
    except ValueError:
        erro = {}
    if isinstance(erro, dict) and (erro.get("code") or erro.get("message")):
        detalhe = f"{erro.get('code') or ''}: {erro.get('message') or ''}".strip(": ")
    else:
        detalhe = (resposta.text or "")[:CAUDA_ERRO]
    detalhe = detalhe.replace(chave, "***")
    return ErroAvatar(f"http_{resposta.status_code}", f"ERRO HeyGen {resposta.status_code} em {etapa}: {detalhe}")


def _dados(resposta: requests.Response, etapa: str) -> dict[str, Any]:
    try:
        dados = resposta.json().get("data")
    except (ValueError, AttributeError):
        dados = None
    if not isinstance(dados, dict):
        raise ErroAvatar("resposta_invalida", f"o HeyGen não devolveu data em {etapa}")
    return dados


def _subir_audio(url_base: str, chave: str, mp3: Path) -> str:
    try:
        with open(mp3, "rb") as f:
            resposta = requests.post(
                f"{url_base}/v3/assets",
                headers={"X-Api-Key": chave},
                files={"file": (mp3.name, f, "audio/mpeg")},
                timeout=TIMEOUT_HTTP_S,
            )
    except requests.RequestException as erro:
        raise ErroAvatar("rede", f"HeyGen inacessível no upload: {type(erro).__name__}") from None
    if not 200 <= resposta.status_code < 300:
        raise _erro_http(resposta, chave, "POST /v3/assets")
    dados = _dados(resposta, "POST /v3/assets")
    asset_id = dados.get("asset_id") or dados.get("id")  # base/api-heygen.md, risco 2
    if not isinstance(asset_id, str) or not asset_id:
        raise ErroAvatar("resposta_invalida", "o HeyGen não devolveu asset_id no upload do áudio")
    return asset_id


def _criar_video(url_base: str, chave: str, corpo: dict[str, Any], idempotencia: str) -> str:
    try:
        resposta = requests.post(
            f"{url_base}/v3/videos",
            headers={"X-Api-Key": chave, "Idempotency-Key": idempotencia},
            json=corpo,
            timeout=TIMEOUT_HTTP_S,
        )
    except requests.RequestException as erro:
        raise ErroAvatar("rede", f"HeyGen inacessível na criação do vídeo: {type(erro).__name__}") from None
    if not 200 <= resposta.status_code < 300:
        raise _erro_http(resposta, chave, "POST /v3/videos")
    video_id = _dados(resposta, "POST /v3/videos").get("video_id")
    if not isinstance(video_id, str) or not video_id:
        raise ErroAvatar("resposta_invalida", "o HeyGen não devolveu video_id na criação")
    return video_id


def _esperar(
    url_base: str, chave: str, video_id: str, intervalo_s: float, timeout_s: float,
    dormir: Callable[[float], Any], relogio: Callable[[], float],
) -> dict[str, Any]:
    limite = relogio() + timeout_s
    while True:
        espera = intervalo_s
        try:
            resposta = requests.get(f"{url_base}/v3/videos/{video_id}", headers={"X-Api-Key": chave},
                                    timeout=TIMEOUT_HTTP_S)
        except requests.RequestException:
            resposta = None  # rede instável no polling: tenta de novo dentro do limite
        if resposta is not None:
            if resposta.status_code in REPETIVEIS_POLLING:
                try:
                    espera = max(intervalo_s, float(resposta.headers.get("Retry-After") or 0))
                except ValueError:
                    pass
            elif not 200 <= resposta.status_code < 300:
                raise _erro_http(resposta, chave, f"GET /v3/videos/{video_id}")
            else:
                dados = _dados(resposta, f"GET /v3/videos/{video_id}")
                status = dados.get("status")
                if status == "completed":
                    return dados
                if status == "failed":
                    mensagem = dados.get("failure_message") or "sem mensagem do provedor"
                    codigo = dados.get("failure_code")
                    raise ErroAvatar(
                        "render_falhou",
                        f"o HeyGen falhou ao gerar o vídeo {video_id}: {mensagem}"
                        + (f" ({codigo})" if codigo else ""),
                    )
        if relogio() + espera > limite:
            raise ErroAvatar(
                "tempo_esgotado",
                f"o vídeo {video_id} não ficou pronto em {timeout_s:.0f} s; chame de novo para retomar "
                "a espera sem criar outro",
            )
        dormir(espera)


def _baixar(url: str, destino: Path) -> None:
    parcial = destino.with_name(destino.name + ".parcial")
    try:
        # URL pré-assinada: sem X-Api-Key, a chave não vai para o armazenamento de terceiros
        with requests.get(url, stream=True, timeout=TIMEOUT_DOWNLOAD_S) as resposta:
            if not 200 <= resposta.status_code < 300:
                raise ErroAvatar(f"http_{resposta.status_code}", f"download do avatar falhou ({resposta.status_code})")
            destino.parent.mkdir(parents=True, exist_ok=True)
            with open(parcial, "wb") as f:
                for bloco in resposta.iter_content(1 << 20):
                    f.write(bloco)
    except requests.RequestException as erro:
        parcial.unlink(missing_ok=True)
        raise ErroAvatar("rede", f"download do avatar falhou: {type(erro).__name__}") from None
    parcial.replace(destino)


# ------------------------------------------------------------------ fluxo

def _hash(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def gerar(
    raiz: Path | str,
    audio: Path | str,
    porta_voz: str,
    destino: Path | str,
    *,
    url_base: str | None = None,
    proporcao: str = PROPORCAO_PADRAO,
    resolucao: str = RESOLUCAO_PADRAO,
    motor: dict[str, Any] | None = None,
    intervalo_s: float = INTERVALO_POLLING_S,
    timeout_s: float = TIMEOUT_POLLING_S,
    dormir: Callable[[float], Any] = time.sleep,
    relogio: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Gera `destino` (mp4) do porta-voz falando o `audio` (mp3/wav da narração).

    `motor` é o `engine` da API (ex.: `{"type": "avatar_v"}`); None usa o padrão do provedor.
    Devolve `provedor`, `arquivo` (relativo à raiz, M9), `video_id`, `duracao_s`, `duracao_audio_s`
    e `motor` (o pedido, para `producao.provedores` da peça).
    """
    raiz = Path(raiz)
    mp3, saida = _caminhos(raiz, audio, destino)
    verificador = exigir_provedor(raiz, PROVEDOR, porta_voz)
    chave = verificador.env[CHAVE_ENV].strip()
    avatar_id = avatar_id_do_porta_voz(raiz, porta_voz)
    duracao_audio = conferir_audio(mp3)
    if mp3.stat().st_size > LIMITE_UPLOAD_BYTES:
        raise ErroAvatar(
            "audio_grande",
            f"o áudio tem {mp3.stat().st_size} bytes e o upload aceita até {LIMITE_UPLOAD_BYTES} (32 MB)",
        )
    base = (url_base or URL_BASE).rstrip("/")

    corpo: dict[str, Any] = {
        "type": "avatar",
        "avatar_id": avatar_id,
        "audio_asset_id": None,  # preenchido depois do upload
        "aspect_ratio": proporcao,
        "resolution": resolucao,
    }
    if motor:
        corpo["engine"] = motor
    sha = _hash(mp3)
    pedido = {k: v for k, v in corpo.items() if k != "audio_asset_id"}
    assinatura = hashlib.sha256(json.dumps({"audio": sha, **pedido}, sort_keys=True).encode()).hexdigest()

    estado_arq = saida.with_name(saida.name + SUFIXO_ESTADO)
    estado = arquivos.ler_json(estado_arq, padrao=None)
    if isinstance(estado, dict) and estado.get("assinatura") == assinatura and estado.get("video_id"):
        video_id = estado["video_id"]  # retomada: o vídeo já foi criado (e pago)
    else:
        corpo["audio_asset_id"] = _subir_audio(base, chave, mp3)
        video_id = _criar_video(base, chave, corpo, f"expxmedia-avatar-{assinatura[:48]}")
        arquivos.gravar_json(estado_arq, {"video_id": video_id, "assinatura": assinatura, "audio_sha256": sha})

    try:
        dados = _esperar(base, chave, video_id, intervalo_s, timeout_s, dormir, relogio)
    except ErroAvatar as erro:
        if erro.codigo == "render_falhou":
            estado_arq.unlink(missing_ok=True)  # terminal: não retomar um vídeo que falhou
        raise
    url = dados.get("video_url")
    if not isinstance(url, str) or not url:
        raise ErroAvatar("resposta_invalida", f"o vídeo {video_id} ficou pronto sem video_url")
    _baixar(url, saida)
    estado_arq.unlink(missing_ok=True)

    duracao = dados.get("duration")
    return {
        "provedor": PROVEDOR,
        "arquivo": instalacao.relativo(raiz, saida),
        "video_id": video_id,
        "duracao_s": float(duracao) if isinstance(duracao, (int, float)) else None,
        "duracao_audio_s": duracao_audio,
        "motor": motor,
    }
