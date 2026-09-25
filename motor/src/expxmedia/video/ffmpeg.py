"""Utilitários ffmpeg do motor: sondagem, loudness, normalização, PNG → JPEG e concatenação.

Porta de `Instragram-Videos/pipeline/render_remotion.py` (medir, normalizar_audio),
`Instragram-Videos/pipeline/compose.py` (loudnorm em duas passagens), `Instragram-Videos/pipeline/lib.py`
(alvos e ffprobe) e `Instragram-Videos/pipeline/cut.py` (concatenação por concat demuxer).

Normalização (a peça inteira sai daqui):

1. mede `loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json` **sobre a mistura final** (o arquivo
   bruto que já soma narração, trilha e efeitos). A origem media só a narração porque ela era o único
   áudio; com trilha somada, medir a voz sozinha deixaria a mistura fora do alvo;
2. aplica com os valores medidos (`linear=true`), vídeo em `-c:v copy`, áudio aac 192k 48 kHz;
3. mede o pico depois do encode (`ebur128=peak=true`); se passar de -1 dBFS (overshoot do AAC),
   refaz a aplicação com um limitador, tentando tetos cada vez mais baixos. O limitador só segura os
   picos: cortar o volume do arquivo inteiro derrubaria a loudness junto.

ffmpeg 8.x sem libass: nada aqui usa `drawtext` nem `subtitles`.
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageCms

__all__ = [
    "ErroFfmpeg",
    "ALVO_LUFS",
    "ALVO_TP",
    "LRA",
    "PICO_MAX",
    "TETOS_LIMITADOR_DB",
    "TOLERANCIA_LUFS",
    "sondar",
    "medir",
    "comando_medicao_loudnorm",
    "normalizar_audio",
    "png_para_jpeg",
    "concatenar",
]

ALVO_LUFS = -14.0  # origem: Instragram-Videos/pipeline/lib.py:11
ALVO_TP = -1.5  # origem: Instragram-Videos/pipeline/lib.py:12
LRA = 11  # origem: Instragram-Videos/pipeline/render_remotion.py:131
PICO_MAX = -1.0  # origem: Instragram-Videos/pipeline/render_remotion.py:120
TOLERANCIA_LUFS = 1.0  # origem: Instragram-Videos/pipeline/render_remotion.py:146
# Teto do limitador depois do loudnorm, tentado em ordem (None = sem limitador). O AAC passa do pico
# que o loudnorm entregou; cortar o volume inteiro levou um vídeo a -16,5 LUFS e reprovou o gate.
TETOS_LIMITADOR_DB = (None, -2.5, -3.5, -4.5)  # origem: Instragram-Videos/pipeline/render_remotion.py:127
LIMITADOR_ATAQUE_MS = 2  # origem: Instragram-Videos/pipeline/render_remotion.py:140
LIMITADOR_SOLTURA_MS = 40  # origem: Instragram-Videos/pipeline/render_remotion.py:140
AUDIO_BITRATE = "192k"  # origem: Instragram-Videos/pipeline/render_remotion.py:141
AUDIO_TAXA = 48000  # origem: Instragram-Videos/pipeline/render_remotion.py:142
CAUDA_ERRO = 800  # caracteres do stderr no erro; origem: Instragram-Videos/pipeline/render_remotion.py:134
JPEG_QUALIDADE = 95


class ErroFfmpeg(RuntimeError):
    """ffmpeg/ffprobe falhou; a mensagem traz a cauda do stderr."""


def _executar(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kw)
    except FileNotFoundError as e:  # binário ausente
        raise ErroFfmpeg(f"binário não encontrado: {cmd[0]}") from e


def _num(valor: float) -> str:
    """-14.0 → '-14'; -1.5 → '-1.5' (o filtro aceita os dois; o comando fica igual ao documentado)."""
    return f"{valor:g}"


# ------------------------------------------------------------------ sondagem

def _fracao(txt: str | None) -> float | None:
    if not txt or txt in ("0/0",):
        return None
    if "/" in txt:
        n, d = txt.split("/", 1)
        return float(n) / float(d) if float(d) else None
    return float(txt)


def sondar(caminho: str | Path) -> dict[str, Any]:
    """ffprobe do arquivo: largura, altura, fps (texto como o ffprobe dá, ex. '30/1'), duração em s,
    codecs de todas as trilhas em ordem, e a taxa de amostragem do primeiro áudio (ou None)."""
    caminho = Path(caminho)
    r = _executar(["ffprobe", "-v", "error", "-show_entries",
                   "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate",
                   "-of", "json", str(caminho)])
    if r.returncode:
        raise ErroFfmpeg(f"ffprobe falhou em {caminho.name}:\n{r.stderr[-CAUDA_ERRO:]}")
    dados = json.loads(r.stdout or "{}")
    trilhas = dados.get("streams") or []
    video = next((t for t in trilhas if t.get("codec_type") == "video"), None)
    audio = next((t for t in trilhas if t.get("codec_type") == "audio"), None)
    duracao = (dados.get("format") or {}).get("duration")
    return {
        "largura": int(video["width"]) if video and video.get("width") else None,
        "altura": int(video["height"]) if video and video.get("height") else None,
        "fps": video.get("r_frame_rate") if video else None,
        "fps_valor": _fracao(video.get("r_frame_rate")) if video else None,
        "duracao": float(duracao) if duracao not in (None, "N/A") else None,
        "codecs": [t.get("codec_name") for t in trilhas if t.get("codec_name")],
        "taxa_audio": int(audio["sample_rate"]) if audio and audio.get("sample_rate") else None,
    }


# ------------------------------------------------------------------ loudness

def medir(caminho: str | Path) -> tuple[float | None, float | None]:
    """(LUFS integrado, pico em dBFS) pela mesma medição do gate de entrega (ebur128=peak=true).

    origem: Instragram-Videos/pipeline/render_remotion.py:112-117 e Instragram-Videos/pipeline/verify.py:83-86
    """
    r = _executar(["ffmpeg", "-hide_banner", "-nostats", "-i", str(caminho), "-af", "ebur128=peak=true",
                   "-f", "null", "-"])
    lufs = re.findall(r"I:\s*(-?\d+\.\d+)\s*LUFS", r.stderr)
    pico = re.findall(r"Peak:\s*(-?\d+\.\d+)\s*dBFS", r.stderr)
    return (float(lufs[-1]) if lufs else None, float(pico[-1]) if pico else None)


def _filtro_loudnorm() -> str:
    return f"loudnorm=I={_num(ALVO_LUFS)}:TP={_num(ALVO_TP)}:LRA={LRA}"


def comando_medicao_loudnorm(entrada: str | Path) -> list[str]:
    """Primeira passada: mede a loudness da mistura e devolve o JSON do loudnorm no stderr."""
    return ["ffmpeg", "-hide_banner", "-nostats", "-i", str(entrada),
            "-af", f"{_filtro_loudnorm()}:print_format=json", "-f", "null", "-"]


def _comando_aplicacao(entrada: Path, saida: Path, filtro: str) -> list[str]:
    return ["ffmpeg", "-y", "-v", "error", "-i", str(entrada), "-c:v", "copy", "-af", filtro,
            "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", str(AUDIO_TAXA), "-movflags", "+faststart", str(saida)]


def normalizar_audio(bruto: str | Path, final: str | Path) -> dict[str, Any]:
    """Normaliza a mistura de `bruto` para -14 LUFS / pico ≤ -1 dBFS e grava `final`.

    Devolve {lufs, pico, passadas, dentro_do_alvo}. `passadas` conta a medição mais cada aplicação
    (2 no caso comum, 3+ quando o pico estourou e o limitador entrou). Fora do alvo depois do último
    teto: devolve `dentro_do_alvo = False` (quem reprova é o gate de entrega), como na origem.
    origem: Instragram-Videos/pipeline/render_remotion.py:130-149
    """
    bruto, final = Path(bruto), Path(final)
    m = _executar(comando_medicao_loudnorm(bruto))
    bloco = re.search(r"\{[^{}]*input_i[^{}]*\}", m.stderr, re.S)
    if not bloco:
        raise ErroFfmpeg(f"medição de loudness falhou em {bruto.name}:\n{m.stderr[-CAUDA_ERRO:]}")
    s = json.loads(bloco.group(0))
    base = (f"{_filtro_loudnorm()}:measured_I={s['input_i']}:measured_TP={s['input_tp']}:"
            f"measured_LRA={s['input_lra']}:measured_thresh={s['input_thresh']}:"
            f"offset={s['target_offset']}:linear=true")
    lufs = pico = None
    passadas = 1
    for teto in TETOS_LIMITADOR_DB:
        filtro = base if teto is None else (
            base + f",alimiter=limit={10 ** (teto / 20):.4f}:attack={LIMITADOR_ATAQUE_MS}"
                   f":release={LIMITADOR_SOLTURA_MS}:level=0")
        r = _executar(_comando_aplicacao(bruto, final, filtro))
        passadas += 1
        if r.returncode:
            raise ErroFfmpeg(f"erro na normalização de {bruto.name}:\n{r.stderr[-CAUDA_ERRO:]}")
        lufs, pico = medir(final)
        if _no_alvo(lufs, pico):
            return {"lufs": lufs, "pico": pico, "passadas": passadas, "dentro_do_alvo": True}
    return {"lufs": lufs, "pico": pico, "passadas": passadas, "dentro_do_alvo": False}


def _no_alvo(lufs: float | None, pico: float | None) -> bool:
    return (lufs is not None and pico is not None and pico <= PICO_MAX
            and abs(lufs - ALVO_LUFS) <= TOLERANCIA_LUFS)


# ------------------------------------------------------------------ imagem

def png_para_jpeg(png: str | Path, destino: str | Path, qualidade: int = JPEG_QUALIDADE,
                  fundo: tuple[int, int, int] = (255, 255, 255)) -> Path:
    """Converte PNG em JPEG sRGB (provedores de publicação que não aceitam PNG).

    A transparência é achatada sobre `fundo`; um perfil ICC embutido é convertido para sRGB.
    """
    png, destino = Path(png), Path(destino)
    with Image.open(png) as img:
        img.load()
        icc = img.info.get("icc_profile")
        if icc:
            try:
                origem_icc = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                modo = "RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB"
                img = ImageCms.profileToProfile(img.convert(modo), origem_icc, ImageCms.createProfile("sRGB"),
                                                outputMode=modo)
            except (ImageCms.PyCMSError, OSError):
                pass
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            plano = Image.new("RGB", rgba.size, fundo)
            plano.paste(rgba, mask=rgba.getchannel("A"))
        else:
            plano = img.convert("RGB")
    destino.parent.mkdir(parents=True, exist_ok=True)
    plano.save(destino, "JPEG", quality=qualidade)
    return destino


# ------------------------------------------------------------------ concatenação

def _linha_concat(caminho: Path) -> str:
    # concat demuxer: aspas simples dentro do nome viram '\''
    return "file '" + str(caminho.resolve()).replace("'", "'\\''") + "'\n"


def concatenar(partes: list[str | Path], destino: str | Path) -> Path:
    """Junta os trechos na ordem, sem re-encodar (concat demuxer + `-c copy`), com `+faststart`.

    Os trechos precisam ter os mesmos codecs e parâmetros. Um trecho só é copiado.
    origem: Instragram-Videos/pipeline/cut.py:481-490
    """
    partes = [Path(p) for p in partes]
    destino = Path(destino)
    if not partes:
        raise ErroFfmpeg("nenhum trecho para concatenar")
    faltam = [p.name for p in partes if not p.exists()]
    if faltam:
        raise ErroFfmpeg(f"trechos ausentes: {', '.join(faltam)}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        lista = Path(tmp) / "lista.txt"
        lista.write_text("".join(_linha_concat(p) for p in partes), encoding="utf-8")
        r = _executar(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                       "-c", "copy", "-movflags", "+faststart", str(destino)])
    if r.returncode:
        raise ErroFfmpeg(f"erro ao juntar os trechos:\n{r.stderr[-CAUDA_ERRO:]}")
    return destino
