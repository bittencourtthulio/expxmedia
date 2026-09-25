"""T-06.08: abertura gerada (porta de `Instragram-Videos/pipeline/abertura.py` e da montagem por cima de
`compose.py`), com o Higgsfield falso (D-15, D-27) devolvendo um clipe sintético servido pelo stub local.

O clipe sintético (720x1280, 4 s) mostra a fixture de rosto (D-43) na metade de cima e, entre 2 s e 3 s,
se transforma no quadro de destino (o topo da tira), segurando-o até o fim — como o modelo faz quando
recebe o `end_image`.

- integração: o reel com abertura tem a mesma duração do reel sem abertura e a narração começa em t=0
  (a abertura troca o fundo do começo, nunca é emendada na frente); a janela que vai ao ar termina no
  encaixe do clipe no destino, não no fim do arquivo;
- funcional: um rosto na metade superior (Haar 1.1/5/60x60, amostra a cada fps/4) move o cartão de
  impacto para a metade inferior, e `abertura.json` só recebe `montado_em` depois do MP4 existir (falha na
  montagem deixa `null`).
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs import higgsfield_falso  # noqa: E402
from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.producao import abertura  # noqa: E402
from expxmedia.video import ffmpeg, montar_pagina  # noqa: E402

ROSTO = Path(__file__).resolve().parents[1] / "fixtures" / "rosto" / "astronauta.png"
CAIXA_FIXTURE = (176, 65, 98, 98)
IMPACTO = ["FORNADA NOVA", "ÀS 16H"]


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True, capture_output=True)


def _pasta_reel(destino: Path) -> Path:
    """Pasta de montagem do reel de página: tira, captura, 7 s de narração (desde t=0) e legenda com card."""
    destino.mkdir(parents=True)
    tira = Image.new("RGB", (1080, 6000), (236, 232, 222))
    d = ImageDraw.Draw(tira)
    for y in range(0, 6000, 400):
        d.rectangle([60, y + 80, 1020, y + 140], fill=(60, 60, 70))
    tira.save(destino / "tira.png")
    (destino / "captura.json").write_text(json.dumps(
        {"secoes": [{"t": "A", "y": 1500}, {"t": "B", "y": 2600}], "px_por_css": 1.5, "strip_h": 6000}))
    taxa, dur = 44100, 7.5
    t = np.arange(int(taxa * dur)) / taxa
    amostras = (0.3 * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    with wave.open(str(destino / "voz.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(amostras.tobytes())
    _ffmpeg("-i", str(destino / "voz.wav"), str(destino / "narracao.mp3"))
    (destino / "voz.wav").unlink()
    caps = destino / "caps"
    caps.mkdir()
    Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(caps / "blank.png")
    for nome in ("000", "end"):
        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        ImageDraw.Draw(img).rectangle([200, 1300, 880, 1450], fill=(0, 0, 0, 205))
        img.save(caps / f"{nome}.png")
    (destino / "caps.txt").write_text(
        "file 'caps/000.png'\nduration 5.4\nfile 'caps/blank.png'\nduration 0.15\n"
        "file 'caps/end.png'\nduration 2.2\nfile 'caps/blank.png'\nduration 0.4\nfile 'caps/blank.png'\n")
    (destino / "legendas.json").write_text(json.dumps({"blocos": 1, "cta": "PALAVRA", "duracao": 8.15,
                                                       "offset_audio": 0.0}))
    return destino


def _clipe_sintetico(pasta: Path) -> bytes:
    """720x1280, 4 s: rosto na metade de cima até 2 s, vira o destino entre 2 e 3 s, segura até 4 s."""
    x, y, w, h = CAIXA_FIXTURE
    m = w // 2
    quadro = Image.new("RGB", (720, 1280), (30, 60, 90))
    rosto = Image.open(ROSTO).convert("RGB").crop((x - m, y - m, x + w + m, y + h + m)).resize((260, 260))
    quadro.paste(rosto, (360 - 130, 330 - 130))
    quadro.save(pasta / "q_rosto.png")
    Image.open(pasta / "tira.png").convert("RGB").crop((0, 0, 1080, 1920)).resize((720, 1280)).save(pasta / "q_fim.png")
    saida = pasta.parent / "clipe_gerado.mp4"
    _ffmpeg("-loop", "1", "-framerate", "30", "-t", "3", "-i", str(pasta / "q_rosto.png"),
            "-loop", "1", "-framerate", "30", "-t", "2", "-i", str(pasta / "q_fim.png"),
            "-filter_complex", "[0:v][1:v]xfade=transition=fade:duration=1:offset=2,format=yuv420p[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "14", str(saida))
    for nome in ("q_rosto.png", "q_fim.png"):
        (pasta / nome).unlink()
    return saida.read_bytes()


@pytest.fixture
def cenario(instalacao, tmp_path, monkeypatch, servidor_stub, requer_binario):
    requer_binario("ffmpeg")
    bin_ = tmp_path / "bin"
    higgsfield_falso.instalar(bin_)
    log = tmp_path / "higgsfield.log"
    monkeypatch.setenv("PATH", str(bin_) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("HIGGSFIELD_FALSO_LOG", str(log))
    monkeypatch.setenv("HIGGSFIELD_FALSO_URL", servidor_stub.url)
    alma = json.loads((instalacao / "alma/alma.json").read_text(encoding="utf-8"))
    alma["porta_vozes"][0]["rosto_ia"]["id"] = "soul-ficticio-123"
    (instalacao / "alma/alma.json").write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")

    pasta = _pasta_reel(instalacao / "pecas" / "2026-09" / "P-20260925-AB12-teste" / "midia")
    servidor_stub.rota("GET", "/resultado.mp4", corpo=_clipe_sintetico(pasta))
    retrato = Image.new("RGB", (576, 1024), (200, 180, 160))
    buf = pasta.parent / "retrato.png"
    retrato.save(buf)
    servidor_stub.rota("GET", "/resultado.png", corpo=buf.read_bytes())
    buf.unlink()
    return instalacao, pasta, log


def _estilo() -> montar_pagina.EstiloMontagem:
    alma = {"visual": {"cores": {"texto": "#101010", "texto_inverso": "#FFFFFF", "destaque": "#3366FF",
                                 "destaque_2": "#FFCC00"}, "fontes": {}}}
    return montar_pagina.estilo_da_alma(alma)[0]


def _inicio_do_audio(video: Path) -> float:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                       capture_output=True, check=True)
    x = np.abs(np.frombuffer(r.stdout, dtype="<i2").astype(float))
    return float(np.argmax(x > 0.05 * x.max()) / 8000)


# ------------------------------------------------------------------ integração


@pytest.mark.integracao_local
def test_reel_com_abertura_tem_a_mesma_duracao_e_narracao_em_zero(cenario):
    raiz, pasta, log = cenario
    sem = pasta.parent / "sem_abertura"
    shutil.copytree(pasta, sem)
    r_sem = abertura.montar(raiz, sem, estilo=_estilo(), impacto=IMPACTO, saida=sem / "final.mp4")

    marcador = abertura.gerar(raiz, pasta, prompt="a bakery counter at dawn, flour in the air", tipo="porta_voz",
                              porta_voz="porta-voz-teste")

    # o clipe foi pedido com o quadro do conteúdo como end_image e o retrato como start_image, sem áudio
    create = [c for c in higgsfield_falso.chamadas(log) if c[:2] == ["generate", "create"]]
    video = next(c for c in create if c[2] == abertura.TIPOS["porta_voz"]["modelo"])
    assert "--end-image" in video and "--start-image" in video and "--generate-audio" in video
    assert video[video.index("--generate-audio") + 1] == "false"
    # janela pelo encaixe (o clipe vira o destino entre 2 e 3 s), não pelo fim do arquivo (4 s)
    j = marcador["janela"]
    # fade linear de 2 a 3 s: 15% do caminho restante é cruzado em ~2,85 s → amostra de 2,9 s
    assert 2.8 <= j["encaixe_s"] <= 2.95
    assert j["ate"] == round(min(j["clipe_s"], j["encaixe_s"] + 0.1), 3) < j["clipe_s"] - 0.5
    assert j["de"] == round(j["ate"] - 2.5, 3)
    clipe = ffmpeg.sondar(pasta / "abertura.mp4")
    assert (clipe["largura"], clipe["altura"], clipe["fps"]) == (1080, 1920, "30/1")
    assert clipe["taxa_audio"] is None and abs(clipe["duracao"] - 2.5) < 0.05
    assert marcador["montado_em"] is None

    r_com = abertura.montar(raiz, pasta, estilo=_estilo(), impacto=IMPACTO, saida=pasta / "final.mp4")

    d_com = ffmpeg.sondar(pasta / "final.mp4")["duracao"]
    d_sem = ffmpeg.sondar(sem / "final.mp4")["duracao"]
    assert r_com["duracao"] == r_sem["duracao"]
    assert abs(d_com - d_sem) < 1 / 30 + 1e-3
    assert r_com["abertura"] == pytest.approx(2.5, abs=0.05) and r_sem["abertura"] is None
    # a narração começa em 0 nos dois: a abertura não empurrou o áudio
    assert _inicio_do_audio(pasta / "final.mp4") < 0.05
    assert _inicio_do_audio(sem / "final.mp4") < 0.05


# ------------------------------------------------------------------ funcional


@pytest.mark.integracao_local
def test_rosto_em_cima_move_o_cartao_para_baixo_e_montado_em_so_depois_do_mp4(cenario, monkeypatch):
    raiz, pasta, _ = cenario
    marcador = abertura.gerar(raiz, pasta, prompt="a bakery counter at dawn", tipo="porta_voz",
                              porta_voz="porta-voz-teste")
    rosto = marcador["rosto"]
    assert rosto is not None and rosto["quadros"] >= 3
    assert rosto["base"] < 1920 / 2  # o rosto está na metade de cima
    salvo = json.loads((pasta / "abertura.json").read_text(encoding="utf-8"))
    assert salvo["montado_em"] is None and salvo["rosto"] == rosto
    assert salvo["tipo"] == "porta_voz" and salvo["modo"] == "por-cima"

    # a montagem falha: montado_em continua null
    def falhar(bruto, final):
        raise ffmpeg.ErroFfmpeg("falha simulada na normalização")

    monkeypatch.setattr(montar_pagina.ffmpeg, "normalizar_audio", falhar)
    with pytest.raises(montar_pagina.ErroMontagem):
        abertura.montar(raiz, pasta, estilo=_estilo(), impacto=IMPACTO, saida=pasta / "final.mp4")
    assert json.loads((pasta / "abertura.json").read_text(encoding="utf-8"))["montado_em"] is None
    assert not (pasta / "final.mp4").exists()
    monkeypatch.undo()

    r = abertura.montar(raiz, pasta, estilo=_estilo(), impacto=IMPACTO, saida=pasta / "final.mp4")
    assert r["cartao"]["centro_y"] > 1920 / 2 and r["cartao"]["por_que"].startswith("abaixo do rosto")
    assert r["legenda_espera"] is True
    final = pasta / "final.mp4"
    depois = json.loads((pasta / "abertura.json").read_text(encoding="utf-8"))
    assert depois["montado_em"] is not None
    assert (pasta / "abertura.json").stat().st_mtime_ns >= final.stat().st_mtime_ns


def test_sem_rosto_no_tipo_objeto_nao_mede_e_teto_de_creditos(cenario):
    raiz, pasta, log = cenario
    # outro reel de hoje já gastou o teto: nada é gerado e o CLI não é chamado
    outra = raiz / "pecas" / "2026-09" / "P-20260925-CD34-outra" / "midia"
    outra.mkdir(parents=True)
    from expxmedia.nucleo import tempo
    (outra / "abertura.json").write_text(json.dumps({"creditos": abertura.TETO_CREDITOS_DIA,
                                                     "gerado_em": tempo.agora_iso(raiz)}))
    with pytest.raises(abertura.ErroAbertura, match="teto"):
        abertura.gerar(raiz, pasta, prompt="a loaf of bread rising")
    assert not [c for c in higgsfield_falso.chamadas(log) if c[:2] == ["generate", "create"]]
    assert not (pasta / "abertura.json").exists()

    with pytest.raises(ValueError, match="1-5"):
        abertura.gerar(raiz, pasta, prompt="x", duracao=6.0)
    # dispensar remove clipe e marcador
    (pasta / "abertura.mp4").write_bytes(b"x")
    (pasta / "abertura.json").write_text("{}")
    abertura.dispensar(pasta)
    assert not (pasta / "abertura.mp4").exists() and not (pasta / "abertura.json").exists()
    assert math.isclose(abertura.DURACAO_NA_TELA, 2.5)
