"""Provedor `teste` da capacidade `narrar`: sinal audível sintético, sem custo (D-34, D-39).

Existe só com `EXPXMEDIA_PROVEDORES_TESTE=1` (no processo ou no `.env` da instalação); sem a
flag, recusa com `ErroCapacidade` e não grava nada. Serve para validar o pipeline narrado
(legenda, montagem, loudnorm, verificação) sem gastar crédito de provedor.

O sinal: **um tom curto por palavra, com pausa entre palavras**, ao ritmo pedido em palavras por
segundo. A palavra k ocupa a janela [k/pps, (k+1)/pps): o tom toca na fração inicial
`FRACAO_TOM` da janela e o resto é pausa. A duração do áudio é exatamente palavras/pps. Não é
silêncio de propósito: silêncio não chega a -14 LUFS no loudnorm da mistura (D-39).

O alinhamento devolvido é coerente com o sinal: os caracteres da palavra k dividem o tom dela em
partes iguais; espaços e quebras entre palavras ocupam a pausa.

Ritmo: argumento `palavras_por_segundo`; senão `EXPXMEDIA_TESTE_NARRAR_PPS` do `.env`; senão
`PPS_PADRAO`.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

import numpy as np

from expxmedia.ambiente.catalogo import FLAG_TESTE
from expxmedia.ambiente.verificar import ErroCapacidade, Verificador

__all__ = ["PROVEDOR", "PPS_PADRAO", "PPS_ENV", "sintetizar", "alinhamento_sintetico"]

PROVEDOR = "teste"
PPS_ENV = "EXPXMEDIA_TESTE_NARRAR_PPS"
# Ritmo padrão do sinal de teste: acima do piso de ritmo do reel (3,47 pal/s), para o sinal não
# ser acelerado sem que o teste peça. Valor de teste, não calibrado.
PPS_PADRAO = 3.5
FRACAO_TOM = 0.7  # parte da janela de cada palavra com tom; o resto é pausa
TAXA = 44100  # mesma taxa do mp3_44100_128 do provedor real
AMPLITUDE = 0.5
RAMPA_S = 0.01  # entrada e saída de cada tom, sem clique
FREQUENCIAS = (196.0, 247.0, 294.0, 262.0, 330.0)  # alterna o tom entre palavras vizinhas
BITRATE = "128k"


def _ritmo(raiz: Path, palavras_por_segundo: float | None, verificador: Verificador) -> float:
    if palavras_por_segundo is None:
        bruto = verificador.env.get(PPS_ENV, "").strip()
        palavras_por_segundo = float(bruto) if bruto else PPS_PADRAO
    pps = float(palavras_por_segundo)
    if not pps > 0:
        raise ValueError("palavras_por_segundo precisa ser maior que zero")
    return pps


def alinhamento_sintetico(fala: str, pps: float) -> dict[str, list]:
    """Alinhamento por caractere de `fala` para o sinal de um tom por palavra a `pps`."""
    janela = 1.0 / pps
    tom = FRACAO_TOM * janela
    palavras = list(re.finditer(r"\S+", fala))
    ini = [0.0] * len(fala)
    fim = [0.0] * len(fala)
    for k, m in enumerate(palavras):
        t0 = k * janela
        passo = tom / (m.end() - m.start())
        for j, pos in enumerate(range(m.start(), m.end())):
            ini[pos] = t0 + passo * j
            fim[pos] = t0 + passo * (j + 1)
    # espaços: antes da 1ª palavra ficam em 0; entre palavras, na pausa; depois da última, no fim dela
    for k, m in enumerate(palavras):
        fim_espaco = palavras[k + 1].start() if k + 1 < len(palavras) else len(fala)
        t_ini = k * janela + tom
        t_fim = (k + 1) * janela if k + 1 < len(palavras) else t_ini
        for pos in range(m.end(), fim_espaco):
            ini[pos], fim[pos] = t_ini, t_fim
    return {
        "characters": list(fala),
        "character_start_times_seconds": ini,
        "character_end_times_seconds": fim,
    }


def _sinal(n_palavras: int, pps: float) -> np.ndarray:
    janela = 1.0 / pps
    total = int(round(n_palavras * janela * TAXA))
    sinal = np.zeros(total, dtype=np.float64)
    n_tom = int(round(FRACAO_TOM * janela * TAXA))
    rampa = max(1, min(int(RAMPA_S * TAXA), n_tom // 2))
    envelope = np.ones(n_tom)
    envelope[:rampa] = np.linspace(0.0, 1.0, rampa)
    envelope[-rampa:] = np.linspace(1.0, 0.0, rampa)
    t = np.arange(n_tom) / TAXA
    for k in range(n_palavras):
        f = FREQUENCIAS[k % len(FREQUENCIAS)]
        # fundamental + dois harmônicos: espectro mais próximo de voz do que um seno puro
        onda = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) + 0.25 * np.sin(6 * np.pi * f * t)
        onda = onda / 1.75 * AMPLITUDE * envelope
        a = int(round(k * janela * TAXA))
        b = min(total, a + n_tom)
        sinal[a:b] = onda[: b - a]
    return sinal


def sintetizar(
    raiz: Path | str,
    fala: str,
    voz: dict[str, Any] | None,
    parametros: dict[str, Any] | None,
    destino: Path | str,
    *,
    palavras_por_segundo: float | None = None,
    **_: Any,
) -> dict[str, list]:
    """Grava o mp3 sintético em `destino` e devolve o alinhamento no espaço de `fala`."""
    raiz, destino = Path(raiz), Path(destino)
    verificador = Verificador(raiz)
    if not verificador.teste:
        raise ErroCapacidade(f"o provedor de teste de narrar só existe com {FLAG_TESTE}=1.")
    pps = _ritmo(raiz, palavras_por_segundo, verificador)
    n = len(fala.split())
    if n == 0:
        raise ValueError("não há palavra para narrar")
    amostras = (np.clip(_sinal(n, pps), -1.0, 1.0) * 32767).astype("<i2")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "sinal.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(TAXA)
            w.writeframes(amostras.tobytes())
        parcial = destino.with_name(destino.name + ".parcial.mp3")
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-c:a", "libmp3lame",
                            "-b:a", BITRATE, "-ar", str(TAXA), str(parcial)], capture_output=True, text=True)
        if r.returncode:
            parcial.unlink(missing_ok=True)
            raise RuntimeError(f"ffmpeg não gerou o mp3 de teste: {r.stderr[-400:]}")
        parcial.replace(destino)
    return alinhamento_sintetico(fala, pps)
