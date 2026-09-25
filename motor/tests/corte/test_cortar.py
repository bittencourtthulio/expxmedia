"""T-06.05: corte com reenquadramento 9:16 (porta de `Instragram-Videos/pipeline/cut.py`).

Vídeos sintéticos montados com a fixture de rosto de T-01.03 (D-43, domínio público):

- integração: um 16:9 de 20 s com o rosto deslocando-se para a direita vira 9:16 com o rosto dentro do
  quadro em todos os quadros amostrados, com no máximo 24 pontos de trajetória;
- funcional: sem rosto o corte usa fundo desfocado e registra o modo; ruído de 3 px (e deriva menor que
  a zona morta de 12% do crop) não muda a trajetória; num vídeo com divisão tela/painel na coluna 1280 a
  fronteira medida por gradiente fica a no máximo 8 px dela.
"""
from __future__ import annotations

import random
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw

from expxmedia.corte import cortar
from expxmedia.video import ffmpeg

ROSTO = Path(__file__).resolve().parents[1] / "fixtures" / "rosto" / "astronauta.png"
# caixa do rosto na fixture (Haar 1.15/6/24 em 512x512): x 176, y 65, 98x98
CAIXA_FIXTURE = (176, 65, 98, 98)


def _recorte_rosto(destino: Path, lado: int) -> Path:
    """O rosto da fixture com uma margem de meia face em volta, redimensionado para `lado` px."""
    x, y, w, h = CAIXA_FIXTURE
    m = w // 2
    img = Image.open(ROSTO).convert("RGB").crop((x - m, y - m, x + w + m, y + h + m))
    img.resize((lado, lado), Image.LANCZOS).save(destino)
    return destino


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True, capture_output=True)


def _video_rosto_andando(destino: Path, dur: float = 20.0) -> dict:
    """1920x1080, rosto de ~196 px (a face ocupa metade do recorte de 392) com o centro indo de x=640 a
    x=1280 (dentro de 0,30-0,70 da largura: é plano de fala, não screencast)."""
    rosto = _recorte_rosto(destino.parent / "rosto_andando.png", 392)
    x0, x1 = 640, 1280
    vel = (x1 - x0) / dur
    _ffmpeg("-f", "lavfi", "-i", f"color=c=0x707070:s=1920x1080:r=30:d={dur}",
            "-f", "lavfi", "-i", f"sine=f=220:d={dur}",
            "-loop", "1", "-i", str(rosto),
            "-filter_complex", f"[0:v][2:v]overlay=x='{x0}-196+{vel}*t':y=(H-h)/2:shortest=1,format=yuv420p[v]",
            "-map", "[v]", "-map", "1:a", "-t", str(dur),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-c:a", "aac", str(destino))
    return {"x0": x0, "vel": vel, "meia_face": 98}


def _faces(quadro_bgr: np.ndarray) -> list:
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    alt, larg = quadro_bgr.shape[:2]
    escala = 640.0 / larg
    g = cv2.cvtColor(cv2.resize(quadro_bgr, (640, int(alt * escala))), cv2.COLOR_BGR2GRAY)
    return [tuple(v / escala for v in f) for f in casc.detectMultiScale(g, 1.15, 6, minSize=(24, 24))]


def _quadros(video: Path, tempos: list[float]):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    for t in tempos:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ok, fr = cap.read()
        assert ok, f"sem quadro em {t} s"
        yield t, fr
    cap.release()


# ------------------------------------------------------------------ integração


@pytest.mark.integracao_local
def test_rosto_andando_fica_dentro_do_quadro_9x16(tmp_path, requer_binario):
    requer_binario("ffmpeg")
    fonte = tmp_path / "fala.mp4"
    _video_rosto_andando(fonte)
    saida = tmp_path / "corte.mp4"

    r = cortar.cortar(fonte, saida)

    s = ffmpeg.sondar(saida)
    assert (s["largura"], s["altura"], s["fps"]) == (1080, 1920, "30/1")
    assert abs(s["duracao"] - 20.0) < 0.2
    assert r["modo"] == "rosto" and r["enquadramento"] == "rosto"
    assert 2 <= len(r["caminho"]) <= cortar.MAX_PONTOS == 24
    # o crop andou para a direita junto com o rosto (640 px de deriva)
    assert r["caminho"][-1][1] - r["caminho"][0][1] > 400
    assert r["deslocamento_px"] > 400
    assert r["screencast"] == []

    # em todo quadro amostrado o rosto é achado inteiro dentro do 9:16
    for t, fr in _quadros(saida, [0.5 + 1.5 * k for k in range(13)]):
        faces = _faces(fr)
        assert faces, f"rosto fora do quadro em {t:.1f} s"
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        assert x >= 0 and x + w <= 1080 and y >= 0 and y + h <= 1920, f"rosto cortado em {t:.1f} s"


# ------------------------------------------------------------------ funcional


@pytest.mark.integracao_local
def test_sem_rosto_usa_fundo_desfocado_e_registra_o_modo(tmp_path, requer_binario):
    requer_binario("ffmpeg")
    fonte = tmp_path / "sem_rosto.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=4", "-f", "lavfi", "-i", "sine=f=330:d=4",
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(fonte))
    saida = tmp_path / "corte.mp4"

    r = cortar.cortar(fonte, saida)

    assert r["modo"] == "fundo_desfocado"
    assert r["enquadramento"] == "fundo desfocado"
    assert "rosto" in r["motivo"]
    assert r["rostos"]["com_rosto"] == 0 and r["rostos"]["amostrados"] >= 12
    s = ffmpeg.sondar(saida)
    assert (s["largura"], s["altura"]) == (1080, 1920)
    # o 16:9 inteiro no meio (1080x608) e o fundo borrado em cima: o topo quase não tem detalhe
    _, fr = next(_quadros(saida, [2.0]))
    topo = cv2.cvtColor(fr[:500], cv2.COLOR_BGR2GRAY)
    meio = cv2.cvtColor(fr[700:1200], cv2.COLOR_BGR2GRAY)
    assert cv2.Laplacian(topo, cv2.CV_64F).var() * 10 < cv2.Laplacian(meio, cv2.CV_64F).var()


def _achados_parados(x_de_t, n: int = 80) -> list[tuple[float, float, float, float]]:
    return [(k / cortar.AMOSTRAS_POR_S, x_de_t(k), 540.0, 250.0) for k in range(n)]


def test_ruido_de_3px_nao_muda_a_trajetoria():
    src_w, crop_w = 1920, 606
    rnd = random.Random(7)
    ruido = _achados_parados(lambda k: 960.0 + rnd.uniform(-3, 3))
    caminho, mov = cortar.caminho_do_rosto(ruido, src_w, crop_w, 20.0, [])
    assert mov == 0.0
    assert len({x for _, x in caminho}) == 1

    # deriva de 60 px: menor que a zona morta (0,12 × 606 ≈ 73 px), o crop não se move
    deriva = _achados_parados(lambda k: 960.0 + 60.0 * k / 79)
    _, mov = cortar.caminho_do_rosto(deriva, src_w, crop_w, 20.0, [])
    assert mov == 0.0
    # deriva de 150 px passa da zona morta e o crop acompanha
    grande = _achados_parados(lambda k: 960.0 + 150.0 * k / 79)
    _, mov = cortar.caminho_do_rosto(grande, src_w, crop_w, 20.0, [])
    assert mov > 40.0
    assert cortar.ZONA_MORTA_FRAC == 0.12 and cortar.EPS_PX == 14.0 and cortar.EMA == 0.25


def test_poucas_amostras_crop_central_e_teto_de_pontos():
    caminho, mov = cortar.caminho_do_rosto(_achados_parados(lambda k: 300.0, n=3), 1920, 606, 5.0, [])
    assert caminho == [(0.0, round((1920 - 606) / 2.0, 1))] and mov == 0.0
    # zigue-zague grande: muitos pontos de RDP, cortados no teto de 24
    zig = _achados_parados(lambda k: 500.0 if (k // 6) % 2 else 1400.0, n=400)
    caminho, _ = cortar.caminho_do_rosto(zig, 1920, 606, 100.0, [])
    assert len(caminho) == cortar.MAX_PONTOS
    expr = cortar.expr_de(caminho)
    assert expr.count("if(lt(t,") == cortar.MAX_PONTOS - 1


def _video_split(destino: Path, dur: float = 4.0) -> None:
    """Tela (documento claro com linhas de texto) de 0 a 1280 e painel escuro da webcam de 1280 a 1920,
    com o rosto pequeno (~0,13 da largura) no painel."""
    fundo = Image.new("RGB", (1920, 1080), (24, 26, 30))
    d = ImageDraw.Draw(fundo)
    d.rectangle([0, 0, 1279, 1079], fill=(245, 245, 240))
    rnd = random.Random(3)
    for y in range(90, 1000, 38):
        x = 80
        while x < 1180:
            w = rnd.randint(30, 140)
            d.rectangle([x, y, min(x + w, 1200), y + 14], fill=(40, 40, 40))
            x += w + rnd.randint(12, 26)
    rosto = Image.open(_recorte_rosto(destino.parent / "rosto_painel.png", 500))
    fundo.paste(rosto, (1600 - 250, 540 - 250))
    quadro = destino.parent / "split.png"
    fundo.save(quadro)
    _ffmpeg("-loop", "1", "-framerate", "30", "-i", str(quadro), "-f", "lavfi", "-i", f"sine=f=200:d={dur}",
            "-t", str(dur), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(destino))


@pytest.mark.integracao_local
def test_fronteira_tela_painel_medida_por_gradiente(tmp_path, requer_binario):
    requer_binario("ffmpeg")
    fonte = tmp_path / "split.mp4"
    _video_split(fonte)

    achados, n, src_w, src_h = cortar.amostrar_rostos(fonte)
    assert achados and src_w == 1920
    fx = float(np.median([a[1] for a in achados]))
    fw = float(np.median([a[3] for a in achados]))
    assert fw < cortar.ROSTO_PEQUENO_FRAC * src_w and fx > cortar.ROSTO_CENTRADO_MAX * src_w
    medida = cortar.fronteira_do_painel(fonte, 0.0, 4.0, fx, fw, src_w, direita=True)
    assert abs(medida - 1280) <= 8
    # a estimativa pelo rosto (fx − 0,70·fw) fica longe: é a medição que acerta
    assert abs((fx - 0.70 * fw) - 1280) > 8

    saida = tmp_path / "corte.mp4"
    r = cortar.cortar(fonte, saida)
    assert r["modo"] == "split" and r["enquadramento"] == "split screencast"
    [(t0, t1, lado, largura_tela, h_topo)] = r["screencast"]
    assert lado == "direita" and abs(largura_tela - 1280) <= 8
    assert 460 <= h_topo <= 1240
    assert ffmpeg.sondar(saida)["altura"] == 1920
