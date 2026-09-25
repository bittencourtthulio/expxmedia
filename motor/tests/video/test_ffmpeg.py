"""T-04.01: utilitários ffmpeg (sondagem, loudnorm em duas passadas + passada extra, PNG → JPEG, concatenação).

A medição de conferência deste arquivo é feita aqui mesmo, com o ebur128 do ffmpeg chamado pelo
teste, e não pela função `medir` do módulo: o teste não pode depender da função que ele confere.
"""
import re
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from expxmedia.video import ffmpeg

pytestmark = pytest.mark.integracao_local


def _ebur128(caminho):
    """(LUFS integrado, pico dBFS) medidos direto pelo ffmpeg, independente do módulo testado."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(caminho), "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    lufs = re.findall(r"I:\s*(-?\d+\.\d+)\s*LUFS", r.stderr)
    pico = re.findall(r"Peak:\s*(-?\d+\.\d+)\s*dBFS", r.stderr)
    return float(lufs[-1]), float(pico[-1])


def _roda(cmd, **kw):
    subprocess.run(cmd, check=True, capture_output=True, **kw)


@pytest.fixture
def mistura_bruta(tmp_path, requer_binario):
    """bruto.mp4 com a MISTURA de uma voz sintética (say) com uma trilha forte gerada pelo ffmpeg.

    A trilha é alta de propósito: a loudness da mistura fica longe da loudness da voz sozinha, então
    normalizar medindo só a voz (o que a origem fazia, compose.py) deixaria a mistura fora do alvo.
    """
    requer_binario("ffmpeg")
    requer_binario("say")
    voz = tmp_path / "voz.aiff"
    _roda(["say", "-o", str(voz), "Esta é uma narração sintética de teste para medir a mistura final do áudio, "
                                  "com voz e trilha somadas antes da normalização em duas passadas."])
    bruto = tmp_path / "bruto.mp4"
    _roda(["ffmpeg", "-y", "-v", "error",
           "-f", "lavfi", "-i", "color=c=gray:s=320x240:r=30",
           "-i", str(voz),
           "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000",
           "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.6:sample_rate=48000",
           "-filter_complex",
           "[1:a]aresample=48000,aformat=channel_layouts=stereo[v];"
           "[2:a]volume=0.5,aformat=channel_layouts=stereo[s];"
           "[3:a]aformat=channel_layouts=stereo[n];"
           "[v][s][n]amix=inputs=3:duration=first:normalize=0[a]",
           "-map", "0:v", "-map", "[a]", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", str(bruto)])
    return voz, bruto


# ------------------------------------------------------------------ teste funcional

def test_primeira_passada_mede_com_loudnorm_i14_tp15_em_json():
    cmd = ffmpeg.comando_medicao_loudnorm(Path("bruto.mp4"))
    linha = " ".join(cmd)
    assert "loudnorm=I=-14:TP=-1.5" in linha
    assert "print_format=json" in linha
    assert "LRA=11" in linha
    assert cmd[0] == "ffmpeg" and "-f" in cmd and "null" in cmd


def test_alvos_calibrados_da_origem():
    assert ffmpeg.ALVO_LUFS == -14.0
    assert ffmpeg.ALVO_TP == -1.5
    assert ffmpeg.PICO_MAX == -1.0
    assert ffmpeg.TETOS_LIMITADOR_DB == (None, -2.5, -3.5, -4.5)


# ------------------------------------------------------------------ teste de integração

def test_normalizar_a_mistura_final_chega_a_14_lufs_e_pico_abaixo_de_1(mistura_bruta, tmp_path):
    voz, bruto = mistura_bruta
    lufs_voz, _ = _ebur128(voz)
    lufs_bruto, _ = _ebur128(bruto)
    # a mistura parte fora do alvo e com loudness diferente da voz sozinha
    assert abs(lufs_bruto - (-14.0)) > 1.5
    assert abs(lufs_bruto - lufs_voz) > 1.0

    final = tmp_path / "final.mp4"
    r = ffmpeg.normalizar_audio(bruto, final)
    lufs, pico = _ebur128(final)
    assert abs(lufs - (-14.0)) <= 1.0, (lufs, pico)
    assert pico < -1.0, (lufs, pico)
    assert r["dentro_do_alvo"] is True
    assert r["lufs"] == pytest.approx(lufs, abs=0.05) and r["pico"] == pytest.approx(pico, abs=0.05)
    # vídeo copiado, não re-encodado; áudio aac 48 kHz
    s = ffmpeg.sondar(final)
    assert "h264" in s["codecs"] and "aac" in s["codecs"]
    assert s["taxa_audio"] == 48000


def test_passada_extra_com_limitador_quando_o_pico_passa_de_menos_1(mistura_bruta, tmp_path, monkeypatch):
    """Se o pico medido depois do encode passa de -1 dBFS, refaz com o limitador (-2,5 dB primeiro)."""
    _, bruto = mistura_bruta
    medidas = iter([(-14.1, -0.6), (-14.2, -1.8)])
    monkeypatch.setattr(ffmpeg, "medir", lambda caminho: next(medidas))
    comandos = []
    original = ffmpeg._executar

    def espiao(cmd, **kw):
        comandos.append(cmd)
        return original(cmd, **kw)

    monkeypatch.setattr(ffmpeg, "_executar", espiao)
    r = ffmpeg.normalizar_audio(bruto, tmp_path / "final.mp4")
    aplicacoes = [" ".join(c) for c in comandos if "linear=true" in " ".join(c)]
    assert len(aplicacoes) == 2
    assert "alimiter" not in aplicacoes[0]
    assert "alimiter=limit=0.7499" in aplicacoes[1]  # 10 ** (-2.5 / 20)
    assert r["passadas"] == 3 and r["pico"] == -1.8 and r["dentro_do_alvo"] is True


def test_sem_bloco_json_na_medicao_levanta_erro(tmp_path, requer_binario):
    requer_binario("ffmpeg")
    lixo = tmp_path / "nao_e_midia.mp4"
    lixo.write_text("isto não é um vídeo")
    with pytest.raises(ffmpeg.ErroFfmpeg, match="medição de loudness"):
        ffmpeg.normalizar_audio(lixo, tmp_path / "final.mp4")


def test_sondar_devolve_dimensao_fps_duracao_e_codecs(tmp_path, requer_binario):
    requer_binario("ffmpeg")
    v = tmp_path / "v.mp4"
    _roda(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "2", "-i", "testsrc2=s=1080x1920:r=30",
           "-f", "lavfi", "-t", "2", "-i", "sine=frequency=440:sample_rate=48000",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(v)])
    s = ffmpeg.sondar(v)
    assert (s["largura"], s["altura"]) == (1080, 1920)
    assert s["fps"] == "30/1"
    assert s["duracao"] == pytest.approx(2.0, abs=0.1)
    assert s["codecs"][:2] == ["h264", "aac"]


def test_sondar_arquivo_inexistente_levanta_erro(tmp_path):
    with pytest.raises(ffmpeg.ErroFfmpeg):
        ffmpeg.sondar(tmp_path / "nao_existe.mp4")


def test_png_para_jpeg_achata_a_transparencia_em_srgb(tmp_path):
    png = tmp_path / "slide.png"
    img = Image.new("RGBA", (40, 50), (0, 0, 0, 0))
    for x in range(20):
        for y in range(50):
            img.putpixel((x, y), (200, 30, 30, 255))
    img.save(png)
    jpg = ffmpeg.png_para_jpeg(png, tmp_path / "slide.jpg")
    with Image.open(jpg) as j:
        assert j.format == "JPEG" and j.mode == "RGB" and j.size == (40, 50)
        assert all(abs(a - b) <= 6 for a, b in zip(j.getpixel((35, 25)), (255, 255, 255)))
        assert all(abs(a - b) <= 12 for a, b in zip(j.getpixel((5, 25)), (200, 30, 30)))


def test_concatenar_junta_os_trechos_na_ordem(tmp_path, requer_binario):
    requer_binario("ffmpeg")
    partes = []
    for i, (seg, cor) in enumerate(((1, "red"), (2, "blue"))):
        p = tmp_path / f"parte '{i}.mp4"  # aspas no nome: a lista do concat precisa escapar
        _roda(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", str(seg), "-i", f"color=c={cor}:s=320x240:r=30",
               "-f", "lavfi", "-t", str(seg), "-i", "sine=frequency=440:sample_rate=48000",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(p)])
        partes.append(p)
    destino = ffmpeg.concatenar(partes, tmp_path / "junto.mp4")
    assert ffmpeg.sondar(destino)["duracao"] == pytest.approx(3.0, abs=0.15)
    quadro = tmp_path / "q.png"
    _roda(["ffmpeg", "-y", "-v", "error", "-ss", "2.5", "-i", str(destino), "-frames:v", "1", str(quadro)])
    r, g, b = Image.open(quadro).convert("RGB").getpixel((160, 120))
    assert b > 150 and r < 80  # depois de 1 s já é o trecho azul
    assert not list(tmp_path.glob("*.txt"))  # a lista temporária não fica para trás
