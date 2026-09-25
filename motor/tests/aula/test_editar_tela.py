"""T-07.03: edição da gravação de tela por cues (D-32).

Porta de cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py sem nada da máquina de origem: a
entrada é a gravação (qualquer mp4) e as janelas por cue. Regra só-acelera/congela: trecho mais
longo que a fala acelera; mais curto roda em 1x e congela o último quadro.
"""
import json
import subprocess

import numpy as np
import pytest

from expxmedia.aula import editar_tela
from expxmedia.video import ffmpeg

pytestmark = pytest.mark.integracao_local

# cues de uma aula: s1 abertura, s2..s4 com tela, s5 fechamento
CUES = {"duration": 20.0, "cues": {"s1": 0.0, "s2": 2.0, "s3": 8.0, "s4": 11.0, "s5": 15.0}}
TELA_CHEIA = {"x": 0, "y": 0, "w": 1920, "h": 1080}
EDITOR = {"x": 213, "y": 86, "w": 1707, "h": 960}
QUADRADO = {"x": 430, "y": 110, "w": 800, "h": 800}


@pytest.fixture
def gravacao(instalacao, requer_binario):
    requer_binario("ffmpeg")
    requer_binario("ffprobe")
    destino = instalacao / "gravacao" / "tela.mp4"
    destino.parent.mkdir()
    # 20 s de gravação sintética em movimento (testsrc2 muda a cada quadro), 1280x720, sem áudio
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30",
                    "-t", "20", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(destino)],
                   check=True, capture_output=True)
    (instalacao / "midia").mkdir()
    return instalacao


def _janelas():
    marcas = {"abrir": 1.0, "arquivo": 12.0, "resultado": 14.0}
    return marcas, [
        # s2: 12 s gravados para 6 s de fala -> 2x
        {"cue": "s2", "arquivo": "gravacao/tela.mp4", "inicio": {"marca": "abrir", "desloc": -1.0},
         "fim": {"marca": "arquivo"}, "rotulo": "editor · projeto", "camera": [{"t": 0, "cx": 700}],
         "crop": TELA_CHEIA, "crop9": None},
        # s3: 2 s gravados para 3 s de fala -> 1x e congela 1 s
        {"cue": "s3", "arquivo": "gravacao/tela.mp4", "inicio": {"marca": "arquivo"}, "fim": {"marca": "resultado"},
         "rotulo": "editor · dados.json", "camera": [{"t": 0, "cx": 900}], "crop": EDITOR, "crop9": None},
        # s4: 6 s gravados para 4 s de fala -> 1,5x; câmera anda no meio do trecho
        {"cue": "s4", "arquivo": "gravacao/tela.mp4", "inicio": 14.0, "fim": 20.0,
         "rotulo": "terminal · resultado", "camera": [{"t": 0, "cx": 830}, {"t": 16.0, "cx": 1100}],
         "crop": EDITOR, "crop9": QUADRADO},
    ]


def _quadro(video, t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=320:180,format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.uint8).astype(np.float64)


def _diferenca(a, b):
    return float(np.mean(np.abs(a - b)))


# ---------------------------------------------------------------- integração

def test_gravacao_de_20s_e_3_cenas_gera_demo_com_a_duracao_das_cues(gravacao):
    marcas, janelas = _janelas()
    demo = editar_tela.editar(gravacao, CUES, janelas, "midia/demo.mp4", "midia/demo.json",
                              marcas=marcas, cue_final="s5")
    mp4 = gravacao / "midia" / "demo.mp4"
    info = ffmpeg.sondar(mp4)
    total = CUES["cues"]["s5"] - CUES["cues"]["s2"]  # 13 s: soma exata das falas
    assert info["duracao"] == pytest.approx(total, abs=0.1)
    assert (info["largura"], info["altura"]) == (1920, 1080)
    assert info["fps_valor"] == 30
    assert info["codecs"] == ["h264"]  # sem áudio: o som vem da narração

    gravado = json.loads((gravacao / "midia" / "demo.json").read_text(encoding="utf-8"))
    assert gravado == demo
    assert gravado["inicio"] == 2.0
    segs = gravado["segmentos"]
    assert [s["cue"] for s in segs] == ["s2", "s3", "s4"]
    assert [s["rate"] for s in segs] == [2.0, 1.0, 1.5]
    assert [(s["de"], s["ate"]) for s in segs] == [(0.0, 6.0), (6.0, 9.0), (9.0, 13.0)]
    assert [s["janela"] for s in segs] == ["editor · projeto", "editor · dados.json", "terminal · resultado"]
    # crop9 ausente cai no crop (origem: editar_demo.py:63)
    assert segs[0]["crop9"] == TELA_CHEIA and segs[2]["crop9"] == QUADRADO
    # câmera convertida do tempo da gravação para o tempo do demo: 9 + (16 - 14) / 1,5
    assert segs[2]["camera"] == [{"t": 9.0, "cx": 830}, {"t": 10.333, "cx": 1100}]
    assert gravado["camera"] == [k for s in segs for k in s["camera"]]
    assert gravado["duracao"] == pytest.approx(13.0)


def test_so_json_nao_renderiza(gravacao):
    marcas, janelas = _janelas()
    editar_tela.editar(gravacao, CUES, janelas, "midia/demo.mp4", "midia/demo.json",
                       marcas=marcas, cue_final="s5", so_json=True)
    assert (gravacao / "midia" / "demo.json").exists()
    assert not (gravacao / "midia" / "demo.mp4").exists()


def test_ultima_janela_sem_cue_final_vai_ate_o_proximo_cue(gravacao):
    marcas, janelas = _janelas()
    demo = editar_tela.editar(gravacao, CUES, janelas, "midia/demo.mp4", "midia/demo.json",
                              marcas=marcas, so_json=True)
    assert demo["segmentos"][-1]["ate"] == 13.0  # s5, o cue seguinte a s4


def test_trecho_alem_do_fim_da_gravacao_usa_o_que_existe(gravacao):
    """Fim depois do fim do arquivo: o tempo gravado é o real (senão o trecho sai curto)."""
    _, janelas = _janelas()
    janelas = [dict(janelas[2], cue="s2", inicio=16.0, fim=30.0)]
    demo = editar_tela.editar(gravacao, CUES, janelas, "midia/demo.mp4", "midia/demo.json", cue_final="s3")
    # 4 s reais para 6 s de fala: 1x e congela
    assert demo["segmentos"][0]["rate"] == 1.0
    assert ffmpeg.sondar(gravacao / "midia" / "demo.mp4")["duracao"] == pytest.approx(6.0, abs=0.1)


def test_janela_com_cue_inexistente_ou_fora_de_ordem_e_recusada(gravacao):
    _, janelas = _janelas()
    with pytest.raises(editar_tela.ErroEditarTela):
        editar_tela.editar(gravacao, CUES, [dict(janelas[0], cue="s9")], "midia/demo.mp4", cue_final="s5")
    with pytest.raises(editar_tela.ErroEditarTela):
        editar_tela.editar(gravacao, CUES, [janelas[2] | {"cue": "s4"}, janelas[0] | {"cue": "s2",
                           "inicio": 0.0, "fim": 5.0}], "midia/demo.mp4", cue_final="s5")


# ---------------------------------------------------------------- funcional

def test_trecho_mais_curto_que_a_fala_congela_o_ultimo_quadro(gravacao):
    marcas, janelas = _janelas()
    editar_tela.editar(gravacao, CUES, janelas, "midia/demo.mp4", "midia/demo.json",
                       marcas=marcas, cue_final="s5")
    mp4 = gravacao / "midia" / "demo.mp4"
    # s3 ocupa 6..9 s do demo: 2 s de gravação em 1x (6..8) e o último quadro congelado (8..9)
    movendo = _diferenca(_quadro(mp4, 6.3), _quadro(mp4, 7.6))
    congelado_1 = _quadro(mp4, 8.2)
    congelado_2 = _quadro(mp4, 8.9)
    assert movendo > 3.0  # a gravação anda
    assert _diferenca(congelado_1, congelado_2) < 1.0  # o quadro fica parado até o fim da cue
    # o quadro congelado é o último do trecho gravado (t = 14 s da gravação), não um preto
    assert _diferenca(congelado_1, _quadro(gravacao / "gravacao" / "tela.mp4", 13.97)) < 6.0
    assert congelado_1.mean() > 20
    # e s4 começa com a gravação andando de novo
    assert _diferenca(_quadro(mp4, 9.2), _quadro(mp4, 10.2)) > 3.0


def test_nunca_desacelera():
    assert editar_tela.velocidade(gravado_s=2.0, fala_s=3.0) == (1.0, 1.0)
    assert editar_tela.velocidade(gravado_s=12.0, fala_s=6.0) == (2.0, 0.0)
    rate, hold = editar_tela.velocidade(gravado_s=3.0, fala_s=3.0)
    assert (rate, hold) == (1.0, 0.0)


# ---------------------------------------------------------------- marcas e enquadramento 9:16

def test_marcas_relativas_e_ponto_por_caracteres(tmp_path):
    rel = tmp_path / "marks-rel.json"
    rel.write_text(json.dumps({"t0": 1000.0, "marks": [{"label": "abrir", "s": 5.952}]}), encoding="utf-8")
    assert editar_tela.ler_marcas(rel) == {"abrir": 5.952}
    jsonl = tmp_path / "marks.jsonl"
    jsonl.write_text('{"label": "inicio", "t": 1003.5}\n{"label": "fim", "t": 1010.25}\n', encoding="utf-8")
    assert editar_tela.ler_marcas(jsonl, t0=1000.0) == {"inicio": 3.5, "fim": 10.25}
    with pytest.raises(editar_tela.ErroEditarTela):
        editar_tela.ler_marcas(jsonl)  # epoch sem t0 não vira segundo da gravação
    # origem: editar_demo.py:18-21 — o instante em que um trecho começa a ser digitado
    texto = "const A = 1;\nconst FAIXAS = [];\n"
    t = editar_tela.ponto_por_caracteres(10.0, 30.0, texto, "const FAIXAS")
    assert t == pytest.approx(10.0 + 20.0 * 13 / len(texto.rstrip("\n")))


def test_camera_do_9x16_interpola_e_respeita_o_recorte():
    camera = [{"t": 0.0, "cx": 700}, {"t": 10.0, "cx": 1100}]
    # transição de ±0,3 s em torno de cada ponto (origem: Aula.tsx:78-86)
    assert editar_tela.camera_x(camera, 5.0) == 700
    assert editar_tela.camera_x(camera, 9.7) == 700
    assert editar_tela.camera_x(camera, 10.0) == pytest.approx(900)
    assert editar_tela.camera_x(camera, 10.3) == 1100
    seg = {"crop": EDITOR, "crop9": QUADRADO}
    # área da tela no 9:16 (L9: 968x962): escala pela altura do crop9, câmera presa dentro dele
    r = editar_tela.recorte(seg, 1100, 968, 962, vertical=True)
    escala = 962 / 800
    assert r["escala"] == pytest.approx(escala)
    meia = 968 / escala / 2
    assert r["left"] == pytest.approx(968 / 2 - (430 + 800 - meia) * escala)
    assert r["top"] == pytest.approx(-110 * escala)
    assert (r["largura"], r["altura"]) == (pytest.approx(1920 * escala), pytest.approx(1080 * escala))
    # 16:9: escala pela largura do crop, sem câmera
    r16 = editar_tela.recorte(seg, 1100, 1392, 783, vertical=False)
    assert r16["escala"] == pytest.approx(1392 / 1707)
    assert r16["left"] == pytest.approx(-213 * 1392 / 1707)
