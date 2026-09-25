"""Provedor `teste` da capacidade `avatar`: vídeo sintético com a duração do áudio, sem custo (D-34).

Existe só com `EXPXMEDIA_PROVEDORES_TESTE=1` (no processo ou no `.env` da instalação) e, como o
real, exige `avatar.avatar_id` do porta-voz na Alma e recusa áudio acima de 10 min (D-44): o
pipeline de aula passa pelos mesmos portões com ou sem crédito.

Forma igual à do que o HeyGen devolve no processo atual (base/avatar-heygen-processo-atual.md,
contrato de saída): H.264 1080x1350 + AAC 48 kHz, 25 fps (base/api-heygen.md, usage-limits), com
a duração do áudio e o próprio áudio na trilha (a composição usa o vídeo `muted`). A imagem é um
padrão de teste em movimento (`testsrc2` do ffmpeg), para o PiP mostrar que o vídeo anda.

Uso:

    from expxmedia.avatar import teste
    teste.gerar(raiz, "pecas/.../midia/narracao.mp3", "ana-souza", "pecas/.../midia/avatar.mp4")
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from expxmedia.ambiente.catalogo import FLAG_TESTE
from expxmedia.ambiente.verificar import ErroCapacidade, Verificador
from expxmedia.avatar.heygen import ErroAvatar, _caminhos, conferir_audio, exigir_provedor
from expxmedia.nucleo import raiz as instalacao

__all__ = ["PROVEDOR", "LARGURA", "ALTURA", "FPS", "gerar"]

PROVEDOR = "teste"
# origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:11-12 (AVATAR_SRC_W/H do twin 4:5)
LARGURA = 1080
ALTURA = 1350
FPS = 25  # base/api-heygen.md: 25 fps em vídeos com avatar
TAXA_AUDIO = 48000  # base/avatar-heygen-processo-atual.md: AAC 48 kHz


def gerar(
    raiz: Path | str,
    audio: Path | str,
    porta_voz: str,
    destino: Path | str,
    **_: Any,
) -> dict[str, Any]:
    """Grava em `destino` um mp4 sintético com a duração exata de `audio`."""
    raiz = Path(raiz)
    if not Verificador(raiz).teste:
        raise ErroCapacidade(f"o provedor de teste de avatar só existe com {FLAG_TESTE}=1.")
    exigir_provedor(raiz, PROVEDOR, porta_voz)
    mp3, saida = _caminhos(raiz, audio, destino)
    duracao = conferir_audio(mp3)
    saida.parent.mkdir(parents=True, exist_ok=True)
    parcial = saida.with_name(saida.name + ".parcial.mp4")
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=size={LARGURA}x{ALTURA}:rate={FPS}",
        "-i", str(mp3),
        "-map", "0:v", "-map", "1:a",
        "-t", f"{duracao:.3f}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", str(TAXA_AUDIO),
        str(parcial),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        parcial.unlink(missing_ok=True)
        raise ErroAvatar("ffmpeg", f"ffmpeg não gerou o avatar de teste: {r.stderr[-400:]}")
    parcial.replace(saida)
    from expxmedia.video import ffmpeg

    return {
        "provedor": PROVEDOR,
        "arquivo": instalacao.relativo(raiz, saida),
        "video_id": None,
        "duracao_s": ffmpeg.sondar(saida)["duracao"],
        "duracao_audio_s": duracao,
        "motor": None,
    }
