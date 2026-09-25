"""Provedor `elevenlabs` da capacidade `narrar`: with-timestamps, alinhamento por caractere (D-22, D-40).

    POST <url_base>/v1/text-to-speech/<voz_id>/with-timestamps?output_format=mp3_44100_128

Sempre `/with-timestamps`: o alinhamento por caractere vem junto, e transcrever de volta é pior
e mais lento (base/narrar-elevenlabs.md). Uma chamada por narração, sem retry: crédito é dinheiro.

- Chave `ELEVENLABS_API_KEY` do `.env` da instalação (nunca do processo, M12/M14), no cabeçalho
  `xi-api-key`. Sem ela, `ErroCapacidade` antes de qualquer chamada.
- `voz_id` e `modelo` vêm de `porta_vozes[].voz` da Alma; `voice_settings` e tempo limite do bloco
  do tipo de peça (`reel`, `aula`, `padrao`). O que o porta-voz não tiver vem dos padrões abaixo,
  iguais aos da origem.
- O mp3 é gravado **assim que a resposta chega**, antes de qualquer validação: o áudio já foi
  pago (origem: Instragram-Videos/pipeline/tts.py:125-126).
- Devolve o `alignment` (sobre o texto enviado), não o `normalized_alignment`: a legenda é fiel ao
  texto escrito (base/api-elevenlabs.md, risco 8).
- Erro HTTP vira `ErroElevenLabs(codigo="http_<status>")` com o começo do corpo (a origem mostra
  400 caracteres: Instragram-Videos/pipeline/tts.py:123); 401 pode ser cota estourada, então a
  mensagem não afirma "chave inválida". Nenhum código é retentado.

`url_base` é configurável (stub nos testes).
"""
from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Any

import requests

from expxmedia.ambiente.verificar import ErroCapacidade, Verificador
from expxmedia.narrar.base import ErroNarrar, bloco_parametros

__all__ = [
    "PROVEDOR",
    "URL_BASE",
    "FORMATO",
    "MODELO_PADRAO",
    "PADROES",
    "TIMEOUT_PADRAO_S",
    "ErroElevenLabs",
    "voice_settings",
    "timeout_de",
    "sintetizar",
]

PROVEDOR = "elevenlabs"
CAPACIDADE = "narrar"
CHAVE_ENV = "ELEVENLABS_API_KEY"
URL_BASE = "https://api.elevenlabs.io"
CAMINHO = "/v1/text-to-speech/{voz_id}/with-timestamps"
FORMATO = "mp3_44100_128"  # origem: Instragram-Videos/pipeline/tts.py:118
MODELO_PADRAO = "eleven_multilingual_v2"  # origem: Instragram-Videos/pipeline/tts.py:16
CAUDA_ERRO = 400  # caracteres do corpo no erro; origem: Instragram-Videos/pipeline/tts.py:123

# Chaves de `voice_settings` aceitas pela API; o resto do bloco (ritmo_min_pps, timeout_s) é do motor.
CHAVES_VOZ = ("stability", "similarity_boost", "style", "use_speaker_boost", "speed")

PADROES: dict[str, dict[str, Any]] = {
    # origem: Instragram-Videos/pipeline/tts.py:113-114 (0.45/0.8/0.25/boost) e
    # Instragram-Videos/pipeline/lib.py:24 (SPEED_PADRAO = 1.2, teto da API)
    "reel": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": True, "speed": 1.2},
    # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:37-41
    "aula": {"stability": 0.5, "similarity_boost": 0.85, "style": 0.15, "use_speaker_boost": True, "speed": 0.94},
    # demais tipos: mesma calibragem do reel (CONTRATO-alma, tabela de parâmetros)
    "padrao": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": True, "speed": 1.2},
}
# Tempo limite da chamada, o da aula. O reel da origem chamava sem timeout (Instragram-Videos/pipeline/tts.py:121);
# sem tempo limite um travamento de rede prende o motor para sempre, então todos os tipos usam o valor da aula.
TIMEOUT_PADRAO_S = 300  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:47


class ErroElevenLabs(ErroNarrar):
    """Falha do provedor ElevenLabs, com `codigo` estável. Nunca traz a chave (M14)."""


def voice_settings(parametros: dict[str, Any] | None, tipo_peca: str) -> dict[str, Any]:
    """`voice_settings` do corpo: o bloco do porta-voz, completado com o padrão do tipo de peça."""
    padrao = PADROES[bloco_parametros(tipo_peca)]
    parametros = parametros or {}
    return {chave: parametros.get(chave, padrao[chave]) for chave in CHAVES_VOZ}


def timeout_de(parametros: dict[str, Any] | None) -> float:
    valor = (parametros or {}).get("timeout_s")
    return float(valor) if isinstance(valor, (int, float)) and valor > 0 else TIMEOUT_PADRAO_S


def _chave(raiz: Path) -> str:
    env = Verificador(raiz).env
    if not env.get(CHAVE_ENV, "").strip():
        raise ErroCapacidade(
            f"{CAPACIDADE} pelo {PROVEDOR} precisa de {CHAVE_ENV} no .env da instalação. "
            "Onde conseguir: https://elevenlabs.io → Profile → API Keys."
        )
    return env[CHAVE_ENV].strip()


def sintetizar(
    raiz: Path | str,
    fala: str,
    voz: dict[str, Any] | None,
    parametros: dict[str, Any] | None,
    destino: Path | str,
    *,
    tipo_peca: str,
    url_base: str | None = None,
    **_: Any,
) -> dict[str, list]:
    """Uma chamada with-timestamps: grava o mp3 em `destino` e devolve o alinhamento de `fala`."""
    raiz, destino = Path(raiz), Path(destino)
    voz = voz or {}
    voz_id = voz.get("voz_id")
    corpo = {
        "text": fala,
        "model_id": voz.get("modelo") or MODELO_PADRAO,
        "voice_settings": voice_settings(parametros, tipo_peca),
    }
    chave = _chave(raiz)
    if not (isinstance(voz_id, str) and voz_id.strip()):
        raise ErroElevenLabs("sem_voz_id", "o porta-voz não tem voz.voz_id preenchido em alma/alma.json")
    url = (url_base or URL_BASE).rstrip("/") + CAMINHO.format(voz_id=voz_id.strip())
    try:
        resposta = requests.post(
            url,
            params={"output_format": FORMATO},
            json=corpo,
            headers={"xi-api-key": chave, "Content-Type": "application/json"},
            timeout=timeout_de(parametros),
        )
    except requests.RequestException as erro:
        raise ErroElevenLabs("rede", f"ElevenLabs inacessível: {type(erro).__name__}") from None
    if not 200 <= resposta.status_code < 300:
        trecho = (resposta.text or "")[:CAUDA_ERRO].replace(chave, "***")
        raise ErroElevenLabs(f"http_{resposta.status_code}", f"ERRO ElevenLabs {resposta.status_code}: {trecho}")
    try:
        dados = resposta.json()
        audio = base64.b64decode(dados["audio_base64"], validate=True)
        alinhamento = dados["alignment"]
    except (ValueError, KeyError, TypeError, binascii.Error):
        raise ErroElevenLabs("resposta_invalida", "a ElevenLabs não devolveu audio_base64 e alignment") from None

    # O áudio já foi pago: grave antes de qualquer validação.
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(destino.name + ".parcial")
    parcial.write_bytes(audio)
    parcial.replace(destino)

    if not isinstance(alinhamento, dict):
        raise ErroElevenLabs("resposta_invalida", "alignment da ElevenLabs não é um objeto")
    return {
        "characters": list(alinhamento.get("characters") or []),
        "character_start_times_seconds": list(alinhamento.get("character_start_times_seconds") or []),
        "character_end_times_seconds": list(alinhamento.get("character_end_times_seconds") or []),
    }
