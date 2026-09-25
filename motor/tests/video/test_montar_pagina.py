"""T-04.11: montagem do reel de página (porta de `Instragram-Videos/pipeline/compose.py` e do teto de `stitch.py`).

Paridade com o G4 (D-16, D-47): com as entradas do golden (tira, captura, narração, impacto e as legendas
do G3 geradas na mesma cópia) e a `alma-golden-reel.json`, o MP4 montado tem a duração do golden e os
quadros em 1, 5 e 10 s diferem dele em no máximo 1% dos pixels (algum canal acima de 8/255).

O texto do selo ("Comenta <CTA>") é copy da origem e entra aqui como parâmetro do teste: no núcleo ele
nunca é fixo no código (M13).
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from expxmedia.alma.fontes import PASTA_INTER
from expxmedia.video import ffmpeg, montar_pagina

GOLDEN = Path(__file__).resolve().parents[1] / "golden"
G3, G4 = GOLDEN / "G3", GOLDEN / "G4"
ALMA_REEL = json.loads((G4 / "alma-golden-reel.json").read_text(encoding="utf-8"))
SELO_ORIGEM = "Comenta {cta}"  # copy da origem: compose.py:236


def _fonte_disponivel():
    return Path(ALMA_REEL["visual"]["fontes"]["titulo"]["arquivo"]).is_file()


def _pasta_g4(destino: Path) -> Path:
    destino.mkdir(parents=True)
    shutil.copyfile(G4 / "entradas" / "strip.png", destino / "tira.png")
    for nome in ("captura.json", "narracao.mp3", "impacto.txt"):
        shutil.copyfile(G4 / "entradas" / nome, destino / nome)
    shutil.copytree(G3 / "caps", destino / "caps")
    for nome in ("caps.txt", "legendas.json"):
        shutil.copyfile(G3 / nome, destino / nome)
    return destino


def _quadro(video: Path, t: float, destino: Path) -> Path:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(video), "-frames:v", "1", str(destino)],
                   check=True, capture_output=True)
    return destino


def _diferenca(a: Path, b: Path) -> float:
    x = np.asarray(Image.open(a).convert("RGB"), dtype=np.int16)
    y = np.asarray(Image.open(b).convert("RGB"), dtype=np.int16)
    assert x.shape == y.shape
    return float((np.abs(x - y).max(axis=2) > 8).mean())


def _video_stream(video: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=duration,nb_frames", "-of", "json", str(video)], check=True, capture_output=True,
                       text=True)
    return json.loads(r.stdout)["streams"][0]


# ------------------------------------------------------------------ integração


@pytest.mark.integracao_local
def test_paridade_com_o_g4(tmp_path, requer_binario):
    requer_binario("ffmpeg")
    if not _fonte_disponivel():
        pytest.skip("fonte local da alma-golden-reel ausente (só existe no macOS, D-47)")
    pasta = _pasta_g4(tmp_path / "g4")
    estilo, avisos = montar_pagina.estilo_da_alma(ALMA_REEL)
    assert avisos == []
    r = montar_pagina.montar(pasta, estilo=estilo, selo=SELO_ORIGEM, saida=pasta / "firecrawl-firecrawl.mp4")

    golden = json.loads((G4 / "ffprobe.json").read_text(encoding="utf-8"))
    video = r["video"]
    # mesma duração: o vídeo fecha no fim do card do CTA alinhado à grade de quadros
    v = _video_stream(video)
    gv = next(s for s in golden["streams"] if s["codec_type"] == "video")
    assert v["nb_frames"] == gv["nb_frames"]
    assert abs(float(v["duration"]) - float(gv["duration"])) < 1e-3
    s = ffmpeg.sondar(video)
    assert abs(s["duracao"] - float(golden["format"]["duration"])) < 0.05
    assert (s["largura"], s["altura"], s["fps"]) == (1080, 1920, "30/1")
    # fim do card em 51,952 s na grade de 1/30 (a legenda dura 52,35 s: a cauda muda sai)
    assert r["duracao"] == math.floor(round(51.952 * 30, 6)) / 30 == 1558 / 30

    # quadros 1 s (cartão sobre a página desfocada), 5 s (selo entrando) e 10 s (rolagem + legenda + selo)
    for t in (1, 5, 10):
        nosso = _quadro(video, t, tmp_path / f"nosso_{t}.png")
        dele = _quadro(G4 / "firecrawl-firecrawl.mp4", t, tmp_path / f"golden_{t}.png")
        frac = _diferenca(nosso, dele)
        assert frac <= 0.01, f"quadro em {t} s: {frac:.2%} dos pixels diferem"

    # o que foi ao ar
    assert json.loads((pasta / "visual.json").read_text(encoding="utf-8")) == \
        json.loads((G4 / "visual.json").read_text(encoding="utf-8"))
    # os números da rolagem e do cartão são os da origem
    assert r["rolagem"]["hold"] == 3.5
    assert montar_pagina.VEL_MIN <= r["rolagem"]["velocidade"] <= montar_pagina.VEL_MAX
    assert r["cartao"]["centro_y"] == 780
    assert r["selo"]["inicio"] == 5.0
    assert not (pasta / "bruto.mp4").exists()


# ------------------------------------------------------------------ funcional


def _pasta_sintetica(destino: Path, *, altura_tira: int = 6000) -> Path:
    """Pasta mínima: tira com seções, 3 s de tom, uma legenda e o card final."""
    destino.mkdir(parents=True)
    tira = Image.new("RGB", (1080, altura_tira), (40, 40, 40))
    d = ImageDraw.Draw(tira)
    for y in range(0, altura_tira, 400):
        d.rectangle([0, y, 1080, y + 40], fill=(200, 200, 200))
    tira.save(destino / "tira.png")
    (destino / "captura.json").write_text(json.dumps(
        {"secoes": [{"t": "A", "y": 1500}, {"t": "B", "y": 2600}], "px_por_css": 1.5, "strip_h": altura_tira}))
    taxa, dur = 44100, 3.0
    t = np.arange(int(taxa * dur)) / taxa
    amostras = (0.3 * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    with wave.open(str(destino / "voz.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(amostras.tobytes())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(destino / "voz.wav"), str(destino / "narracao.mp3")],
                   check=True)
    caps = destino / "caps"
    caps.mkdir()
    Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(caps / "blank.png")
    for nome in ("000", "end"):
        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        ImageDraw.Draw(img).rectangle([200, 1300, 880, 1450], fill=(0, 0, 0, 205))
        img.save(caps / f"{nome}.png")
    (destino / "caps.txt").write_text(
        "file 'caps/blank.png'\nduration 0.6\nfile 'caps/000.png'\nduration 5.0\n"
        "file 'caps/blank.png'\nduration 0.15\nfile 'caps/end.png'\nduration 2.2\n"
        "file 'caps/blank.png'\nduration 0.4\nfile 'caps/blank.png'\n")
    (destino / "legendas.json").write_text(json.dumps({"blocos": 1, "cta": "PALAVRA", "duracao": 8.35,
                                                       "offset_audio": 0.6}))
    return destino


def _estilo_embarcado() -> montar_pagina.EstiloMontagem:
    alma = {"visual": {"cores": {"texto": "#101010", "texto_inverso": "#FFFFFF", "destaque": "#3366FF",
                                 "destaque_2": "#FFCC00"}, "fontes": {}}}
    estilo, avisos = montar_pagina.estilo_da_alma(alma)
    assert estilo.fonte.parent == PASTA_INTER and avisos  # sem fonte: Inter embarcada, com aviso
    return estilo


def test_tira_acima_do_teto_e_recusada(tmp_path):
    pasta = _pasta_sintetica(tmp_path / "p", altura_tira=20000)
    with pytest.raises(montar_pagina.ErroTiraAcimaDoTeto, match="16384"):
        montar_pagina.montar(pasta, estilo=_estilo_embarcado(), impacto=["UMA LINHA"], selo="Peça {cta}")
    assert not list(pasta.glob("*.mp4")) and not (pasta / "visual.json").exists()


def test_teto_e_exatamente_16384(tmp_path):
    assert montar_pagina.LIMITE_TEXTURA == 16384
    pasta = _pasta_sintetica(tmp_path / "p", altura_tira=16385)
    with pytest.raises(montar_pagina.ErroTiraAcimaDoTeto):
        montar_pagina.montar(pasta, estilo=_estilo_embarcado(), impacto=["UMA LINHA"])


@pytest.mark.integracao_local
def test_visual_json_so_depois_do_mp4(tmp_path, monkeypatch, requer_binario):
    requer_binario("ffmpeg")
    pasta = _pasta_sintetica(tmp_path / "p")
    (pasta / "abertura.json").write_text(json.dumps({"rosto": None, "montado_em": None}))
    estilo = _estilo_embarcado()

    # a normalização falha: nem visual.json nem montado_em podem existir
    def falhar(bruto, final):
        raise ffmpeg.ErroFfmpeg("falha simulada na normalização")

    monkeypatch.setattr(montar_pagina.ffmpeg, "normalizar_audio", falhar)
    with pytest.raises(montar_pagina.ErroMontagem, match="simulada"):
        montar_pagina.montar(pasta, estilo=estilo, impacto=["UMA LINHA"], selo="Peça {cta}")
    assert not (pasta / "visual.json").exists()
    assert not (pasta / "final.mp4").exists()
    assert json.loads((pasta / "abertura.json").read_text())["montado_em"] is None
    monkeypatch.undo()

    r = montar_pagina.montar(pasta, estilo=estilo, impacto=["UMA LINHA"], selo="Peça {cta}")
    final = pasta / "final.mp4"
    assert r["video"] == final and final.is_file()
    assert (pasta / "visual.json").stat().st_mtime_ns >= final.stat().st_mtime_ns
    assert json.loads((pasta / "visual.json").read_text()) == {
        "metodo": "visual-v2", "impacto": ["UMA LINHA"], "selo_cta": "PALAVRA", "abertura_gerada": None}
    # duração: fim do card (0,6 + 5,0 + 0,15 + 2,2 = 7,95) na grade de 1/30, não a da legenda (8,35)
    assert r["duracao"] == math.floor(round(7.95 * 30, 6)) / 30
    assert abs(ffmpeg.sondar(final)["duracao"] - r["duracao"]) < 0.1
    # selo de 5 s até 0,05 s antes do card (5,75)
    assert r["selo"] == {"texto": "Peça PALAVRA", "inicio": 5.0, "fim": 5.7}
    lufs, pico = ffmpeg.medir(final)
    assert abs(lufs - ffmpeg.ALVO_LUFS) <= 1.0 and pico <= -1.0


def test_escolha_da_rolagem_e_do_cartao():
    # a fronteira mais perto de 160 px/s dentro de 90–230 ganha
    secoes = [{"t": "longe", "y": 3000}, {"t": "perto", "y": 2400}, {"t": "rapida", "y": 5000}]
    percurso, vel, escolha = montar_pagina.escolher_rolagem(secoes, 1.0, 20000, 10.0, 1920)
    assert (percurso, vel, escolha) == (1080, 108.0, "termina em 'longe'")
    percurso, vel, escolha = montar_pagina.escolher_rolagem([{"t": "x", "y": 3500}], 1.0, 20000, 10.0, 1920)
    assert (percurso, vel) == (1580, 158.0) and escolha == "termina em 'x'"
    # nenhuma fronteira legível: 160 px/s até onde der
    percurso, vel, escolha = montar_pagina.escolher_rolagem([{"t": "x", "y": 10000}], 1.0, 20000, 10.0, 1920)
    assert (percurso, vel, escolha) == (1600, 160.0, "página inteira")
    # velocidade abaixo de 90 não é fronteira
    _, vel, escolha = montar_pagina.escolher_rolagem([{"t": "x", "y": 2700}], 1.0, 20000, 10.0, 1920)
    assert escolha == "página inteira" and vel == 160.0

    fonte = PASTA_INTER / "inter-latin-700-normal.woff2"
    y, tam, _, aviso = montar_pagina.escolher_cartao(None, ["SITE VIRA", "DADO"], 1260, fonte=fonte)
    assert y == 780 and tam == 150 and aviso is None
    # rosto no meio: cabe abaixo dele, encolhendo
    y, tam, por_que, aviso = montar_pagina.escolher_cartao({"topo": 300, "base": 900}, ["SITE VIRA", "DADO"], 1260,
                                                           fonte=fonte)
    assert por_que.startswith("abaixo do rosto") and 900 < y < 1260 and aviso is None
    # rosto ocupando quase tudo: não cabe, AVISA
    _, _, _, aviso = montar_pagina.escolher_cartao({"topo": 260, "base": 1250}, ["A", "B", "C"], 1260, fonte=fonte)
    assert aviso and "rosto" in aviso


def test_cartao_com_mais_de_tres_linhas_e_recusado(tmp_path):
    pasta = _pasta_sintetica(tmp_path / "p")
    with pytest.raises(montar_pagina.ErroMontagem, match="teto é 3"):
        montar_pagina.montar(pasta, estilo=_estilo_embarcado(), impacto=["A", "B", "C", "D"])
    with pytest.raises(montar_pagina.ErroMontagem, match="sem_impacto"):
        montar_pagina.montar(pasta, estilo=_estilo_embarcado())
