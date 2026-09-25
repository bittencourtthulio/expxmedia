"""Ritmo mínimo da narração com `atempo`: só acelera, e só no reel (D-40).

Porta de `fixar_ritmo` e `reescalar` (Instragram-Videos/pipeline/tts.py:30-97) com o piso vindo do
porta-voz (`porta_vozes[].voz.parametros.reel.ritmo_min_pps`) em vez de uma constante do canal.

O `speed` do provedor NÃO garante ritmo: quatro chamadas iguais deram 3,18 / 2,79 / 3,26 / 3,42
pal/s. Quem garante o PISO é o `atempo`, só acelerando:

- mais lenta que o piso (fator > 1 + tolerância) → `atempo=<fator>` até o piso;
- mais rápida que o piso, ou dentro da tolerância → nada, sem re-encode. **Piso, nunca alvo**:
  frear uma leitura boa desfaz a melhoria e queima uma segunda geração de mp3;
- fator acima de `ATEMPO_MAX` → não aplica e avisa: algo mais está errado (roteiro, voz, speed).

`atempo` preserva o tom (`asetrate` desafinaria a voz clonada). O mp3 volta a 192k para
minimizar a perda da segunda geração. O alinhamento é reescalado pelo mesmo fator (t → t/fator),
então descreve o mp3 final. A aula tem calibragem própria e nunca passa por aqui; os demais tipos
também não (o ritmo mínimo só existe no bloco `reel`, CONTRATO-alma).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from expxmedia.narrar.base import ErroNarrar, bloco_parametros, duracao

__all__ = [
    "RITMO_APROVADO",
    "SPEED_APROVADO",
    "SPEED_PADRAO",
    "RITMO_MIN_PADRAO",
    "RITMO_TOL",
    "ATEMPO_MAX",
    "fator_para",
    "reescalar",
    "fixar_ritmo",
    "aplicar",
]

SPEED_APROVADO = 1.1  # origem: Instragram-Videos/pipeline/lib.py:23
SPEED_PADRAO = 1.2  # origem: Instragram-Videos/pipeline/lib.py:24
RITMO_APROVADO = 3.18  # pal/s; origem: Instragram-Videos/pipeline/lib.py:25
# ~3,47 pal/s: piso, nunca alvo. origem: Instragram-Videos/pipeline/lib.py:38
RITMO_MIN_PADRAO = RITMO_APROVADO * SPEED_PADRAO / SPEED_APROVADO
RITMO_TOL = 0.03  # desvio ignorado; origem: Instragram-Videos/pipeline/lib.py:39
ATEMPO_MAX = 1.35  # acima disso, avisa e não aplica; origem: Instragram-Videos/pipeline/lib.py:40
BITRATE_ATEMPO = "192k"  # origem: Instragram-Videos/pipeline/tts.py:92


def fator_para(duracao_s: float, palavras: int, ritmo_min: float) -> float:
    """duração atual / duração máxima tolerada. >1 veio lenta; <1 veio mais rápida que o piso.

    origem: Instragram-Videos/pipeline/tts.py:69-72
    """
    piso = palavras / ritmo_min
    return duracao_s / piso


def reescalar(alinhamento: dict[str, Any], fator: float) -> dict[str, Any]:
    """Divide os tempos pelo fator do `atempo` (t no original cai em t/fator no final).

    Linear, por isso pode rodar antes do remapeamento ao roteiro. origem: Instragram-Videos/pipeline/tts.py:30-42
    """
    if fator == 1.0:
        return alinhamento
    return {
        "characters": alinhamento["characters"],
        "character_start_times_seconds": [t / fator for t in alinhamento["character_start_times_seconds"]],
        "character_end_times_seconds": [t / fator for t in alinhamento["character_end_times_seconds"]],
    }


def fixar_ritmo(mp3: Path | str, palavras: int, ritmo_min: float = RITMO_MIN_PADRAO) -> dict[str, Any]:
    """Garante o PISO de ritmo no mp3 (no lugar). Devolve {fator, antes, depois, aplicado, aviso}.

    `fator` é o aplicado (1.0 quando nada mudou). origem: Instragram-Videos/pipeline/tts.py:45-97
    """
    mp3 = Path(mp3)
    if palavras <= 0 or not ritmo_min > 0:
        raise ValueError("palavras e ritmo mínimo precisam ser maiores que zero")
    antes = duracao(mp3)
    fator = fator_para(antes, palavras, ritmo_min)
    if fator <= 1.0 + RITMO_TOL:
        return {"fator": 1.0, "antes": antes, "depois": antes, "aplicado": False, "aviso": None}
    if fator > ATEMPO_MAX:
        aviso = (
            f"fator de aceleração {fator:.3f} acima do limite seguro {ATEMPO_MAX} "
            f"({antes:.2f}s para o piso de {palavras / ritmo_min:.2f}s). NADA foi aplicado: fator "
            "extremo significa que algo mais está errado (roteiro, voz ou speed). Investigue antes de montar."
        )
        return {"fator": 1.0, "antes": antes, "depois": antes, "aplicado": False, "aviso": aviso}

    tmp = mp3.with_name(mp3.stem + ".atempo.mp3")
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-filter:a", f"atempo={fator:.6f}",
         "-c:a", "libmp3lame", "-b:a", BITRATE_ATEMPO, str(tmp)],
        capture_output=True, text=True,
    )
    if r.returncode:
        tmp.unlink(missing_ok=True)
        raise ErroNarrar("atempo", f"ffmpeg falhou ao acelerar {mp3.name}: {r.stderr[-400:]}")
    tmp.replace(mp3)
    return {"fator": fator, "antes": antes, "depois": duracao(mp3), "aplicado": True, "aviso": None}


def aplicar(
    mp3: Path | str,
    alinhamento: dict[str, Any],
    palavras: int,
    tipo_peca: str,
    parametros: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Corrige o ritmo de um reel e devolve (alinhamento reescalado, info). Outros tipos: intactos."""
    if bloco_parametros(tipo_peca) != "reel":
        return alinhamento, {"fator": 1.0, "aplicado": False, "aviso": None}
    valor = (parametros or {}).get("ritmo_min_pps")
    ritmo_min = float(valor) if isinstance(valor, (int, float)) and valor > 0 else RITMO_MIN_PADRAO
    info = fixar_ritmo(mp3, palavras, ritmo_min)
    info["ritmo_min_pps"] = ritmo_min
    return reescalar(alinhamento, info["fator"]), info
