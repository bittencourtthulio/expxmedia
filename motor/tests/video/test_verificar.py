"""T-04.02: verificação de entrega por perfil (reel, reel_pagina, corte, sob_medida, aula).

Os vídeos são sintéticos, gerados pelo ffmpeg (lavfi) na sessão e guardados em cache por parâmetro;
nada grande fica versionado. Cada artefato defeituoso quebra UMA checagem e o teste confere que o
achado é exatamente aquele, com o limiar esperado. O áudio "bom" passa pela normalização da T-04.01.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from expxmedia.video import ffmpeg, verificar

pytestmark = pytest.mark.integracao_local

W, H = 1080, 1920
ROTEIRO = "Um roteiro curto de teste. No fim ele pede: comenta QUERO que eu te mando."
SRT_BOM = "1\n00:00:00,500 --> 00:00:02,000\nPrimeira linha da aula.\n\n2\n00:00:02,100 --> 00:00:04,500\nSegunda linha.\n"


def _roda(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def _cartao(caminho, caixa, cor=(255, 255, 255, 255)):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if caixa:
        d = ImageDraw.Draw(img)
        d.rectangle(caixa, fill=cor)
        x0, y0, x1, y1 = caixa
        d.rectangle((x0 + 60, y0 + 60, x1 - 60, y1 - 60), fill=(20, 20, 20, 255))
    img.save(caminho)


class Fabrica:
    """Gera (e guarda) vídeos sintéticos e os PNGs de legenda da sessão."""

    def __init__(self, base: Path):
        self.base = base
        self.cache = {}
        self.caps = base / "caps"
        self.caps.mkdir()
        _cartao(self.caps / "blank.png", None)
        _cartao(self.caps / "c1.png", (140, 1300, 940, 1480))
        _cartao(self.caps / "end.png", (90, 700, 990, 1200), cor=(250, 250, 250, 255))
        _cartao(self.caps / "baixo.png", (140, 1560, 940, 1760))  # invade os 420 px de baixo
        # áudio de 90 s normalizado pela T-04.01 (a mistura inteira), cortado por cópia em cada vídeo
        tom = base / "tom.m4a"
        _roda(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
               "sine=frequency=440:sample_rate=48000:duration=90", "-ac", "2", "-c:a", "aac", str(tom)])
        self.audio_bom = base / "audio_bom.m4a"
        r = ffmpeg.normalizar_audio(tom, self.audio_bom)
        assert r["dentro_do_alvo"], r
        self.audio_baixo = base / "audio_baixo.m4a"
        _roda(["ffmpeg", "-y", "-v", "error", "-i", str(self.audio_bom), "-af", "volume=-8dB",
               "-c:a", "aac", "-b:a", "192k", str(self.audio_baixo)])
        # loudness no alvo, mas com estalos que passam de -1 dBFS
        self.audio_pico = base / "audio_pico.m4a"
        _roda(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
               "aevalsrc='0.21*sin(2*PI*440*t)+if(lt(mod(t\\,1)\\,0.002)\\,0.97\\,0)':s=48000:d=90:c=stereo",
               "-c:a", "aac", "-b:a", "192k", str(self.audio_pico)])

    def video(self, dur, dims=(W, H), fps=30, vcodec="libx264", audio="bom", card_ate=None):
        chave = (dur, dims, fps, vcodec, audio, card_ate)
        if chave in self.cache:
            return self.cache[chave]
        destino = self.base / f"v{len(self.cache):03d}.mp4"
        enable = f":enable='lt(t,{card_ate})'" if card_ate is not None else ""
        fonte = {"bom": self.audio_bom, "baixo": self.audio_baixo, "pico": self.audio_pico}[audio]
        cod = ["-c:v", "libx264", "-preset", "ultrafast"] if vcodec == "libx264" else ["-c:v", vcodec, "-q:v", "5"]
        _roda(["ffmpeg", "-y", "-v", "error",
               "-f", "lavfi", "-i", f"color=c=0x304050:s={dims[0]}x{dims[1]}:r={fps}",
               "-loop", "1", "-framerate", str(fps), "-i", str(self.caps / "end.png"),
               "-i", str(fonte),
               "-filter_complex", f"[0:v][1:v]overlay=0:0{enable},format=yuv420p[v]",
               "-map", "[v]", "-map", "2:a", "-t", str(dur), *cod, "-r", str(fps), "-c:a", "copy", str(destino)])
        self.cache[chave] = destino
        return destino


@pytest.fixture(scope="session")
def fabrica(tmp_path_factory):
    for b in ("ffmpeg", "ffprobe"):
        if shutil.which(b) is None:
            pytest.skip(f"binário ausente: {b}")
    return Fabrica(tmp_path_factory.mktemp("verificar"))


def _pasta(tmp_path, fabrica, dur, *, cartoes=None, cta="QUERO", fim_fala=None, roteiro=ROTEIRO,
           chars=None, offset=0.5, sem=(), srt=SRT_BOM, legenda_post="Legenda do post."):
    """Monta a pasta de artefatos coerente com um vídeo de `dur` segundos; os parâmetros quebram uma coisa."""
    p = tmp_path / "peca"
    p.mkdir()
    shutil.copytree(fabrica.caps, p / "caps")
    if cartoes is None:  # reel: legendas de 1 s e o card do CTA fechando junto com o vídeo
        n = int(dur - 4)
        cartoes = [("blank", 0.5)] + [("c1", 1.0)] * n + [("end", round(dur - 0.5 - n, 3))]
    linhas = []
    for nome, d in cartoes:
        linhas += [f"file 'caps/{nome}.png'", f"duration {d}"]
    (p / "caps.txt").write_text("\n".join(linhas) + "\n")
    (p / "legendas.json").write_text(json.dumps({"duracao": dur, "offset_audio": offset, "cta": cta}))
    (p / "roteiro.txt").write_text(roteiro)
    texto = chars if chars is not None else roteiro
    fim = (dur - 2.0 - offset) if fim_fala is None else fim_fala
    n = len(texto)
    (p / "alignment.json").write_text(json.dumps({
        "characters": list(texto),
        "character_start_times_seconds": [fim * i / n for i in range(n)],
        "character_end_times_seconds": [fim * (i + 1) / n for i in range(n)]}))
    (p / "legenda.txt").write_text(legenda_post)
    (p / "aula.srt").write_text(srt)
    for nome in sem:
        (p / nome).unlink()
    return verificar.artefatos_da_pasta(p)


def _checagens(r):
    return {a["checagem"] for a in r["achados"]}


def _achado(r, checagem):
    return next(a for a in r["achados"] if a["checagem"] == checagem)


# ------------------------------------------------------------------ teste de integração

def test_mp4_1080x1920_30fps_normalizado_passa_no_perfil_reel(fabrica, tmp_path):
    video = fabrica.video(32)
    r = verificar.verificar(video, "reel", _pasta(tmp_path, fabrica, 32))
    assert r == {"aprovado": True, "perfil": "reel", "achados": [], "avisos": []}
    json.dumps(r)  # saída estruturada serializável


# ------------------------------------------------------------------ teste funcional: um defeito por checagem

# (id, perfil, parâmetros do vídeo, parâmetros da pasta, checagens esperadas, checagem conferida, esperado)
CASOS = [
    # as 11 do perfil reel
    ("reel-1-dimensao", "reel", dict(dur=32, dims=(1080, 1080)), {}, {"dimensao", "cauda"}, "dimensao", "1080x1920"),
    ("reel-2-fps", "reel", dict(dur=32, fps=25), {}, {"fps"}, "fps", "30/1"),
    ("reel-3-duracao", "reel", dict(dur=25), {}, {"duracao"}, "duracao", "30-70 s"),
    ("reel-4-codecs", "reel", dict(dur=32, vcodec="mpeg4"), {}, {"codecs"}, "codecs", "h264 + aac"),
    ("reel-5-loudness", "reel", dict(dur=32, audio="baixo"), {}, {"loudness"}, "loudness", "-14 ±1 LUFS"),
    ("reel-6-pico", "reel", dict(dur=32, audio="pico"), {}, {"pico"}, "pico", "≤ -1.0 dBFS"),
    ("reel-7-area-segura", "reel", dict(dur=32),
     dict(cartoes=[("blank", 0.5), ("baixo", 1.0)] + [("c1", 1.0)] * 27 + [("end", 3.5)]),
     {"area_segura"}, "area_segura", "nenhum pixel visível nos 420 px inferiores"),
    ("reel-8-legibilidade", "reel", dict(dur=32),
     dict(cartoes=[("blank", 0.5)] + [("c1", 0.5)] * 30 + [("c1", 1.0)] * 10 + [("end", 6.5)]),
     {"legibilidade"}, "legibilidade", "≤ 35% dos cartões abaixo de 0.7 s"),
    ("reel-9-sincronia-tempo", "reel", dict(dur=32), dict(fim_fala=32.0), {"sincronia"}, "sincronia",
     "fim da narração ≤ duração + 0.05 s e alinhamento igual ao roteiro"),
    ("reel-9-sincronia-texto", "reel", dict(dur=32), dict(chars=ROTEIRO.replace("curto", "longo")), {"sincronia"},
     "sincronia", "fim da narração ≤ duração + 0.05 s e alinhamento igual ao roteiro"),
    ("reel-10-cauda-card", "reel", dict(dur=32, card_ate=29), {}, {"cauda"}, "cauda", "erro médio ≤ 12/255"),
    ("reel-11-cta", "reel", dict(dur=32), dict(cta="OUTRA"), {"cta"}, "cta", "CTA de legendas.json presente no roteiro"),
    ("reel-artefato-ausente", "reel", dict(dur=32), dict(sem=("caps.txt",)),
     {"area_segura", "legibilidade", "cauda"}, "legibilidade", "caps.txt presente"),
    # reel_pagina e corte: a faixa de duração de cada formato (D-49)
    ("reel_pagina-duracao-40", "reel_pagina", dict(dur=40), {}, {"duracao"}, "duracao", "50-70 s"),
    ("corte-duracao-40", "corte", dict(dur=40), dict(cta=None, cartoes=[("blank", 0.5)] + [("c1", 1.0)] * 39),
     {"duracao"}, "duracao", "50-185 s"),
    # corte: cauda muda de 0,9 s depois da última legenda (10b) e CTA proibido
    ("corte-10b-cauda", "corte", dict(dur=60), dict(cta=None, cartoes=[("blank", 0.5)] + [("c1", 1.0)] * 58
                                                   + [("c1", 0.6), ("blank", 0.9)]),
     {"cauda"}, "cauda", "≤ 0.80 s depois da última legenda"),
    ("corte-11-cta", "corte", dict(dur=60), dict(cartoes=[("blank", 0.5)] + [("c1", 1.0)] * 59), {"cta"}, "cta",
     "sem CTA (cta null em legendas.json)"),
    # sob_medida (modo recriado da origem)
    ("sob_medida-duracao", "sob_medida", dict(dur=25), {}, {"duracao"}, "duracao", "30-70 s"),
    ("sob_medida-arquivos", "sob_medida", dict(dur=32), dict(sem=("legenda.txt",)), {"arquivos"}, "arquivos",
     "alinhamento, roteiro e legenda do post presentes"),
    ("sob_medida-alinhamento", "sob_medida", dict(dur=32), dict(chars=ROTEIRO + " extra"), {"sincronia"}, "sincronia",
     "fim da narração ≤ duração + 0.05 s e alinhamento igual ao roteiro"),
    # aula
    ("aula-dimensao", "aula", dict(dur=6, dims=(1080, 1080)), {}, {"dimensao"}, "dimensao", "1920x1080 ou 1080x1920"),
    ("aula-fps", "aula", dict(dur=32, fps=25), {}, {"fps"}, "fps", "30/1"),
    ("aula-codecs", "aula", dict(dur=32, vcodec="mpeg4"), {}, {"codecs"}, "codecs", "h264 + aac"),
    ("aula-loudness", "aula", dict(dur=32, audio="baixo"), {}, {"loudness"}, "loudness", "-14 ±1 LUFS"),
    ("aula-pico", "aula", dict(dur=32, audio="pico"), {}, {"pico"}, "pico", "≤ -1.0 dBFS"),
    ("aula-srt-ausente", "aula", dict(dur=6, dims=(1920, 1080)), dict(sem=("aula.srt",)), {"srt"}, "srt",
     "SRT presente, em ordem e dentro da duração do vídeo"),
    ("aula-srt-fora", "aula", dict(dur=6, dims=(1920, 1080)),
     dict(srt=SRT_BOM + "\n3\n00:00:05,000 --> 00:00:09,000\nDepois do fim.\n"), {"srt"}, "srt",
     "SRT presente, em ordem e dentro da duração do vídeo"),
    ("aula-srt-fora-de-ordem", "aula", dict(dur=6, dims=(1920, 1080)),
     dict(srt="1\n00:00:03,000 --> 00:00:04,000\nB\n\n2\n00:00:01,000 --> 00:00:02,000\nA\n"), {"srt"}, "srt",
     "SRT presente, em ordem e dentro da duração do vídeo"),
]


@pytest.mark.parametrize("caso,perfil,pv,pp,esperadas,checagem,esperado", CASOS, ids=[c[0] for c in CASOS])
def test_defeito_recebe_o_achado_especifico_com_o_limiar(fabrica, tmp_path, caso, perfil, pv, pp, esperadas,
                                                         checagem, esperado):
    video = fabrica.video(**pv)
    r = verificar.verificar(video, perfil, _pasta(tmp_path, fabrica, pv["dur"], **pp))
    assert r["aprovado"] is False and r["perfil"] == perfil
    assert _checagens(r) == esperadas, r["achados"]
    a = _achado(r, checagem)
    assert set(a) == {"checagem", "detalhe", "esperado", "obtido"}
    assert a["esperado"] == esperado
    assert a["detalhe"]
    json.dumps(r)


def test_obtido_traz_o_valor_medido(fabrica, tmp_path):
    r = verificar.verificar(fabrica.video(32, fps=25, audio="baixo"), "reel", _pasta(tmp_path, fabrica, 32))
    assert _achado(r, "fps")["obtido"] == "25/1"
    assert _achado(r, "loudness")["obtido"] == pytest.approx(-22.0, abs=1.0)
    (tmp_path / "b").mkdir()
    r = verificar.verificar(fabrica.video(32), "reel", _pasta(tmp_path / "b", fabrica, 32, cartoes=[
        ("blank", 0.5)] + [("c1", 0.5)] * 30 + [("c1", 1.0)] * 10 + [("end", 6.5)]))
    assert _achado(r, "legibilidade")["obtido"] == pytest.approx(30 / 40, abs=0.001)


# ------------------------------------------------------------------ aprovados por perfil (achado BAIXA da auditoria)

def test_mp4_de_40s_passa_no_reel_e_reprova_na_duracao_de_reel_pagina_e_corte(fabrica, tmp_path):
    video = fabrica.video(40)
    art = _pasta(tmp_path, fabrica, 40)
    assert verificar.verificar(video, "reel", art)["aprovado"] is True
    rp = verificar.verificar(video, "reel_pagina", art)
    assert _checagens(rp) == {"duracao"} and _achado(rp, "duracao")["esperado"] == "50-70 s"
    assert _achado(rp, "duracao")["obtido"] == pytest.approx(40.0, abs=0.1)
    rc = verificar.verificar(video, "corte", art)
    assert "duracao" in _checagens(rc) and _achado(rc, "duracao")["esperado"] == "50-185 s"


def test_corte_de_78s_passa_com_aviso(fabrica, tmp_path):
    video = fabrica.video(78)
    r = verificar.verificar(video, "corte", _pasta(tmp_path, fabrica, 78, cta=None,
                                                    cartoes=[("blank", 0.5)] + [("c1", 1.0)] * 77 + [("blank", 0.3)]))
    assert r["aprovado"] is True and r["achados"] == []
    assert [a["checagem"] for a in r["avisos"]] == ["duracao"]
    assert "75" in r["avisos"][0]["detalhe"]


def test_corte_de_60s_passa_sem_aviso(fabrica, tmp_path):
    r = verificar.verificar(fabrica.video(60), "corte", _pasta(tmp_path, fabrica, 60, cta=None,
                                                               cartoes=[("blank", 0.5)] + [("c1", 1.0)] * 59))
    assert r == {"aprovado": True, "perfil": "corte", "achados": [], "avisos": []}


def test_reel_pagina_de_60s_passa(fabrica, tmp_path):
    r = verificar.verificar(fabrica.video(60), "reel_pagina", _pasta(tmp_path, fabrica, 60))
    assert r["aprovado"] is True, r


def test_sob_medida_passa_sem_caps(fabrica, tmp_path):
    art = _pasta(tmp_path, fabrica, 32, sem=("caps.txt", "legendas.json"), offset=0.0)
    r = verificar.verificar(fabrica.video(32), "sob_medida", art)
    assert r == {"aprovado": True, "perfil": "sob_medida", "achados": [], "avisos": []}


@pytest.mark.parametrize("dims", [(1920, 1080), (1080, 1920)])
def test_aula_nos_dois_formatos_passa(fabrica, tmp_path, dims):
    r = verificar.verificar(fabrica.video(6, dims=dims), "aula", _pasta(tmp_path, fabrica, 6))
    assert r == {"aprovado": True, "perfil": "aula", "achados": [], "avisos": []}


def test_perfil_desconhecido_e_video_ausente(tmp_path):
    with pytest.raises(ValueError, match="perfil"):
        verificar.verificar(tmp_path / "x.mp4", "story")
    with pytest.raises(FileNotFoundError):
        verificar.verificar(tmp_path / "x.mp4", "reel")


def test_limiares_calibrados_da_origem():
    p = verificar.PERFIS
    assert (p["reel"].duracao_min, p["reel"].duracao_max) == (30.0, 70.0)
    assert (p["reel_pagina"].duracao_min, p["reel_pagina"].duracao_max) == (50.0, 70.0)
    assert (p["corte"].duracao_min, p["corte"].duracao_max, p["corte"].duracao_aviso) == (50.0, 185.0, 75.0)
    assert (p["sob_medida"].duracao_min, p["sob_medida"].duracao_max) == (30.0, 70.0)
    assert p["aula"].duracao_min is None and set(p["aula"].dimensoes) == {(1920, 1080), (1080, 1920)}
    assert verificar.SAFE_BOTTOM == 420
    assert verificar.CAP_BLOCO_MIN_S == 0.7 and verificar.CAP_CURTOS_MAX_FRAC == 0.35
    assert verificar.CAUDA_ERRO_MAX == 12 and verificar.CAUDA_SEM_CTA_MAX_S == 0.8
    assert verificar.SINCRONIA_FOLGA_S == 0.05
    assert len(p["reel"].checagens) == 11 and p["reel"].checagens == p["reel_pagina"].checagens
