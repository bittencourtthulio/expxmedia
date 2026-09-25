"""T-04.10: legenda queimada por PNG com overlay temporizado (ffmpeg sem libass)."""
import re
import subprocess

import numpy as np
import pytest
from PIL import Image, ImageDraw

from expxmedia.legendar import queimar


def _png_legenda(caminho, cor):
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([140, 1300, 940, 1499], radius=26, fill=cor)
    img.save(caminho)
    return caminho


def _quadro(video, t, destino):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(video), "-frames:v", "1", str(destino)],
                   check=True)
    return np.asarray(Image.open(destino).convert("RGB"), dtype=np.int16)


# ------------------------------------------------------------------ funcional

def test_filtro_tem_um_overlay_enable_between_por_bloco():
    blocos = [("caps/000.png", 0.6, 1.8), ("caps/001.png", 1.85, 2.4)]
    filtro = queimar.montar_filtro(blocos)
    overlays = re.findall(r"overlay=[^;\[]*", filtro)
    assert len(overlays) == 2
    assert "enable='between(t,0.6,1.8)'" in overlays[0]
    assert "enable='between(t,1.85,2.4)'" in overlays[1]
    assert "subtitles" not in filtro and "drawtext" not in filtro
    # o primeiro overlay parte do vídeo e o último sai no rótulo final
    assert filtro.startswith("[0:v][1:v]overlay") and filtro.endswith("[vout]")


def test_blocos_do_caps_txt_ignoram_blank_e_somam_os_tempos(tmp_path):
    (tmp_path / "caps.txt").write_text(
        "file 'caps/blank.png'\nduration 0.6\nfile 'caps/000.png'\nduration 1.2\n"
        "file 'caps/blank.png'\nduration 0.05\nfile 'caps/end.png'\nduration 2.2\n"
        "file 'caps/blank.png'\nduration 0.4\nfile 'caps/blank.png'\n", encoding="utf-8")
    assert queimar.blocos_do_caps(tmp_path / "caps.txt") == [
        (tmp_path / "caps/000.png", 0.6, 1.8), (tmp_path / "caps/end.png", 1.85, 4.05)]


def test_sem_blocos_ou_png_ausente_levanta(tmp_path):
    with pytest.raises(queimar.ErroQueimar):
        queimar.montar_filtro([])
    with pytest.raises(queimar.ErroQueimar, match="nao_existe.png"):
        queimar.queimar(tmp_path / "v.mp4", [(tmp_path / "nao_existe.png", 0, 1)], tmp_path / "s.mp4")


# ------------------------------------------------------------------ integração

@pytest.mark.integracao_local
def test_queimar_dois_blocos_num_video_de_3_s(tmp_path, requer_binario):
    requer_binario("ffmpeg")
    video = tmp_path / "base.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x3060a0:s=1080x1920:r=30:d=3",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(video)], check=True)
    a = _png_legenda(tmp_path / "000.png", (255, 255, 255, 230))
    b = _png_legenda(tmp_path / "001.png", (255, 200, 0, 230))
    saida = queimar.queimar(video, [(a, 0.5, 1.5), (b, 1.6, 2.5)], tmp_path / "final.mp4")

    s = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height",
                        "-of", "csv=p=0", str(saida)], capture_output=True, text=True, check=True).stdout
    assert "1080,1920" in s and "aac" in s
    faixa = (slice(1310, 1490), slice(160, 920))  # a faixa da legenda
    orig_1 = _quadro(video, 1.0, tmp_path / "o1.png")
    fim_1 = _quadro(saida, 1.0, tmp_path / "f1.png")
    orig_29 = _quadro(video, 2.9, tmp_path / "o29.png")
    fim_29 = _quadro(saida, 2.9, tmp_path / "f29.png")
    assert np.abs(fim_1[faixa] - orig_1[faixa]).mean() > 60  # legenda visível em 1 s
    assert np.abs(fim_29 - orig_29).max() <= 8  # nada em 2,9 s: depois do último bloco
    # fora da faixa o quadro de 1 s continua o original
    assert np.abs(fim_1[:1200] - orig_1[:1200]).max() <= 8
