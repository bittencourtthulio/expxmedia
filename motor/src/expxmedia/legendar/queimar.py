"""Legenda queimada em vídeo por overlay temporizado dos PNGs, sem libass.

A build do ffmpeg da instalação não tem libass, então os filtros `subtitles`/`ass` não existem, e
`drawtext` depende de fonte do sistema. A legenda já sai desenhada em PNG (`legendar.reel`): aqui cada
PNG entra como uma entrada do ffmpeg e é sobreposto em 0:0 só no seu intervalo, com
`overlay=0:0:enable='between(t,início,fim)'` — o mesmo padrão da origem para inserções temporizadas
(`Instragram-Videos/pipeline/compose_cut.py:56`, `Instragram-Videos/pipeline/cut.py:379`).

O vídeo é re-encodado em h264/yuv420p com os parâmetros da montagem da origem; o áudio é copiado.

Uso:

    from expxmedia.legendar import queimar
    queimar.queimar("base.mp4", queimar.blocos_do_caps("caps.txt"), "legendado.mp4")
"""
from __future__ import annotations

import subprocess
from pathlib import Path

__all__ = ["ErroQueimar", "blocos_do_caps", "montar_filtro", "queimar"]

CRF = "19"  # origem: Instragram-Videos/pipeline/compose_cut.py:116
PRESET = "slow"  # origem: Instragram-Videos/pipeline/compose_cut.py:116
CAUDA_ERRO = 800  # caracteres do stderr no erro

Bloco = tuple[str | Path, float, float]


class ErroQueimar(RuntimeError):
    """Nada para queimar, PNG ausente ou ffmpeg com erro."""


def _num(x: float) -> str:
    return f"{float(x):.3f}".rstrip("0").rstrip(".") or "0"


def blocos_do_caps(caps_txt: str | Path) -> list[tuple[Path, float, float]]:
    """[(png, início, fim)] dos cartões visíveis de um `caps.txt` (concat demuxer), sem os `blank`.

    Os caminhos do `caps.txt` são relativos à pasta dele.
    """
    caps_txt = Path(caps_txt)
    blocos, t, nome = [], 0.0, None
    for linha in caps_txt.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha.startswith("file "):
            resto = linha.split(None, 1)[1]
            nome = resto.split("'")[1] if "'" in resto else resto
        elif linha.startswith("duration ") and nome:
            d = float(linha.split()[1])
            if Path(nome).stem != "blank":
                blocos.append((caps_txt.parent / nome, round(t, 3), round(t + d, 3)))
            t += d
    return blocos


def montar_filtro(blocos: list[Bloco]) -> str:
    """filter_complex com um overlay temporizado por bloco; a entrada 0 é o vídeo, a i+1 é o PNG i."""
    if not blocos:
        raise ErroQueimar("nenhum bloco de legenda para queimar")
    partes, atual = [], "0:v"
    for i, (_png, ini, fim) in enumerate(blocos, start=1):
        saida = "vout" if i == len(blocos) else f"v{i}"
        partes.append(f"[{atual}][{i}:v]overlay=0:0:enable='between(t,{_num(ini)},{_num(fim)})'[{saida}]")
        atual = saida
    return ";".join(partes)


def queimar(video: str | Path, blocos: list[Bloco], destino: str | Path) -> Path:
    """Grava `destino` com os PNGs sobrepostos nos seus intervalos. Levanta ErroQueimar em falha."""
    video, destino = Path(video), Path(destino)
    faltam = [Path(p).name for p, *_ in blocos if not Path(p).is_file()]
    if faltam:
        raise ErroQueimar(f"PNG de legenda ausente: {', '.join(faltam[:5])}")
    filtro = montar_filtro(blocos)
    if not video.is_file():
        raise ErroQueimar(f"vídeo não existe: {video.name}")
    entradas = ["-i", str(video)]
    for png, *_ in blocos:
        entradas += ["-i", str(png)]
    destino.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", *entradas, "-filter_complex", filtro,
           "-map", "[vout]", "-map", "0:a?", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
           "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(destino)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise ErroQueimar("binário não encontrado: ffmpeg") from e
    if r.returncode:
        raise ErroQueimar(f"ffmpeg falhou ao queimar a legenda:\n{r.stderr[-CAUDA_ERRO:]}")
    return destino
