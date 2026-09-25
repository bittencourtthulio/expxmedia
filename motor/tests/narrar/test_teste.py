"""T-04.03: interface `narrar` e provedor de teste com sinal audível sintético (D-34, D-39).

O provedor de teste existe só com EXPXMEDIA_PROVEDORES_TESTE=1. Ele gera um tom curto por palavra,
com pausa entre palavras, ao ritmo pedido em palavras por segundo, e devolve o alinhamento por
caractere coerente com esse sinal. A medição de conferência (duração, loudness) é feita aqui com o
ffprobe/ffmpeg chamados pelo teste, não pelas funções do motor.
"""
import json
import re
import subprocess

import pytest

from expxmedia.ambiente import verificar
from expxmedia.ambiente.verificar import ErroCapacidade
from expxmedia.narrar import base, teste
from expxmedia.video import ffmpeg

pytestmark = pytest.mark.integracao_local

PORTA_VOZ = "porta-voz-teste"
# 20 palavras, com acento, pontuação e caixa alta (a interface não pode perder nada disso)
TEXTO = ("A fornada das quatro sai em dez minutos, quentinha. Comenta PÃO que a gente "
         "separa o seu e avisa hoje.")
PPS = 3.5


def _ligar_teste(raiz):
    (raiz / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")


def _duracao(caminho):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "default=nw=1:nk=1", str(caminho)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def _codec(caminho):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                        "stream=codec_name,sample_rate", "-of", "json", str(caminho)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)["streams"][0]


def _ebur128(caminho):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(caminho), "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    lufs = re.findall(r"I:\s*(-?\d+\.\d+)\s*LUFS", r.stderr)
    pico = re.findall(r"Peak:\s*(-?\d+\.\d+)\s*dBFS", r.stderr)
    return float(lufs[-1]), float(pico[-1])


@pytest.fixture(autouse=True)
def _binarios(requer_binario, monkeypatch):
    requer_binario("ffmpeg")
    requer_binario("ffprobe")
    # a flag só vale pelo .env de cada teste, nunca herdada do processo que roda a suíte
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)


# ------------------------------------------------------------------ integração

def test_flag_habilita_narrar_pelo_provedor_teste(instalacao):
    antes = verificar.verificar("narrar", instalacao, porta_voz=PORTA_VOZ)
    assert antes["habilitada"] is False
    assert "teste" not in [p["id"] for p in antes["provedores"]]

    _ligar_teste(instalacao)
    depois = verificar.verificar("narrar", instalacao, porta_voz=PORTA_VOZ)
    assert depois["habilitada"] is True
    assert depois["provedor"] == "teste"


def test_sem_flag_o_provedor_teste_recusa_e_nao_grava_nada(instalacao):
    with pytest.raises(ErroCapacidade):
        base.narrar(instalacao, TEXTO, PORTA_VOZ, "reel", "pecas/p1/midia", palavras_por_segundo=PPS)
    with pytest.raises(ErroCapacidade):
        teste.sintetizar(instalacao, TEXTO, {}, {}, instalacao / "pecas" / "x.mp3")
    assert not (instalacao / "pecas" / "p1").exists()
    assert not (instalacao / "pecas" / "x.mp3").exists()


# ------------------------------------------------------------------ funcional

def test_20_palavras_a_3_5_pps_dao_mp3_audivel_de_5_7_s_e_alinhamento_por_caractere(instalacao):
    assert len(TEXTO.split()) == 20
    _ligar_teste(instalacao)

    r = base.narrar(instalacao, TEXTO, PORTA_VOZ, "reel", "pecas/p1/midia", palavras_por_segundo=PPS)

    assert r["provedor"] == "teste"
    assert r["audio"] == "pecas/p1/midia/narracao.mp3"          # relativo à raiz (M9)
    assert r["arquivo_alinhamento"] == "pecas/p1/midia/alinhamento.json"
    mp3 = instalacao / r["audio"]
    assert _codec(mp3) == {"codec_name": "mp3", "sample_rate": "44100"}

    # ~5,7 s: 20 palavras / 3,5 pal/s = 5,714 s (+ o atraso do codificador mp3)
    duracao = _duracao(mp3)
    assert duracao == pytest.approx(20 / PPS, abs=0.12)
    assert r["palavras"] == 20

    # audível: o sinal tem energia de fala, não é silêncio (silêncio mede -70 LUFS ou nada)
    lufs, pico = _ebur128(mp3)
    assert lufs > -30.0
    assert pico < 0.0

    al = json.loads((instalacao / r["arquivo_alinhamento"]).read_text(encoding="utf-8"))
    assert al == r["alinhamento"]
    assert set(al) == {"characters", "character_start_times_seconds", "character_end_times_seconds"}
    # um tempo por caractere do texto, no texto exato
    assert len(al["characters"]) == len(TEXTO)
    assert "".join(al["characters"]) == TEXTO
    ini, fim = al["character_start_times_seconds"], al["character_end_times_seconds"]
    assert len(ini) == len(fim) == len(TEXTO)
    assert all(f >= i for i, f in zip(ini, fim))
    assert all(b >= a for a, b in zip(ini, ini[1:]))           # não volta no tempo
    assert fim[-1] <= duracao

    # coerência com o sinal: a palavra k começa em k / pps
    inicios = [m.start() for m in re.finditer(r"\S+", TEXTO)]
    for k, pos in enumerate(inicios):
        assert ini[pos] == pytest.approx(k / PPS, abs=1e-6)


def test_o_ritmo_e_configuravel(instalacao):
    _ligar_teste(instalacao)
    lento = base.narrar(instalacao, TEXTO, PORTA_VOZ, "aula", "pecas/lento", palavras_por_segundo=2.5)
    assert _duracao(instalacao / lento["audio"]) == pytest.approx(20 / 2.5, abs=0.12)

    # sem argumento, vale EXPXMEDIA_TESTE_NARRAR_PPS do .env
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\nEXPXMEDIA_TESTE_NARRAR_PPS=4\n", encoding="utf-8")
    rapido = base.narrar(instalacao, TEXTO, PORTA_VOZ, "aula", "pecas/rapido")
    assert _duracao(instalacao / rapido["audio"]) == pytest.approx(20 / 4, abs=0.12)


def test_o_sinal_sintetico_atinge_menos_14_lufs_depois_do_loudnorm_da_mistura(instalacao, tmp_path):
    """D-39: silêncio não chega a -14 LUFS; o sinal do provedor de teste chega."""
    _ligar_teste(instalacao)
    r = base.narrar(instalacao, TEXTO, PORTA_VOZ, "reel", "pecas/p1/midia", palavras_por_segundo=PPS)
    bruto = tmp_path / "bruto.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=320x240:r=30",
                    "-i", str(instalacao / r["audio"]), "-map", "0:v", "-map", "1:a", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(bruto)],
                   check=True, capture_output=True)

    resultado = ffmpeg.normalizar_audio(bruto, tmp_path / "final.mp4")

    assert resultado["dentro_do_alvo"] is True
    lufs, pico = _ebur128(tmp_path / "final.mp4")
    assert lufs == pytest.approx(-14.0, abs=1.0)
    assert pico <= -1.0


def test_interface_valida_o_alinhamento():
    bom = {"characters": list("ab"), "character_start_times_seconds": [0.0, 0.1],
           "character_end_times_seconds": [0.1, 0.2]}
    base.validar_alinhamento(bom, "ab")
    with pytest.raises(base.ErroNarrar):
        base.validar_alinhamento(bom, "abc")
    with pytest.raises(base.ErroNarrar):
        base.validar_alinhamento({**bom, "character_end_times_seconds": [0.1]}, "ab")
    with pytest.raises(base.ErroNarrar):
        base.validar_alinhamento({"characters": list("ab")}, "ab")


def test_bloco_de_parametros_por_tipo_de_peca():
    assert base.bloco_parametros("reel") == "reel"
    assert base.bloco_parametros("aula") == "aula"
    for tipo in ("post_unico", "carrossel", "apresentacao"):
        assert base.bloco_parametros(tipo) == "padrao"
    with pytest.raises(ValueError):
        base.bloco_parametros("podcast")
