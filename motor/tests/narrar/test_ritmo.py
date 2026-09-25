"""T-04.06: ritmo mínimo com atempo — só acelera, reescala o alinhamento, só no reel (D-40).

A duração de conferência é medida aqui com o ffprobe chamado pelo teste.
"""
import hashlib
import subprocess

import pytest

from expxmedia.narrar import base, ritmo

pytestmark = pytest.mark.integracao_local

PORTA_VOZ = "porta-voz-teste"


def _duracao(caminho):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "default=nw=1:nk=1", str(caminho)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def _mp3(destino, segundos):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=220:sample_rate=44100:duration={segundos}",
                    "-c:a", "libmp3lame", "-b:a", "128k", str(destino)], check=True, capture_output=True)
    return destino


def _hash(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _alinhamento(n, duracao):
    passo = duracao / n
    return {"characters": ["a"] * n,
            "character_start_times_seconds": [i * passo for i in range(n)],
            "character_end_times_seconds": [(i + 1) * passo for i in range(n)]}


@pytest.fixture(autouse=True)
def _binarios(requer_binario, monkeypatch):
    requer_binario("ffmpeg")
    requer_binario("ffprobe")
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)


# ------------------------------------------------------------------ integração

def test_10_s_com_30_palavras_e_acelerado_para_no_maximo_8_65_s(tmp_path):
    mp3 = _mp3(tmp_path / "narracao.mp3", 10)
    antes = _duracao(mp3)
    al = _alinhamento(40, antes)

    novo, info = ritmo.aplicar(mp3, al, 30, "reel", {"ritmo_min_pps": 3.47})

    depois = _duracao(mp3)
    assert depois <= 8.65
    assert depois == pytest.approx(30 / 3.47, abs=0.06)
    assert info["fator"] == pytest.approx(antes / (30 / 3.47), rel=1e-6)
    assert info["aplicado"] is True
    # alinhamento reescalado pelo mesmo fator: descreve o mp3 final
    assert novo["characters"] == al["characters"]
    assert novo["character_end_times_seconds"][-1] == pytest.approx(antes / info["fator"])
    assert novo["character_start_times_seconds"] == pytest.approx(
        [t / info["fator"] for t in al["character_start_times_seconds"]])


def test_narrar_reel_lento_pelo_provedor_teste_sai_no_piso_do_porta_voz(instalacao):
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    texto = " ".join(["palavra"] * 30)
    # 2,8 pal/s: abaixo do piso 3,2 da Alma fictícia (fator 1,143, dentro do limite 1,35)
    r = base.narrar(instalacao, texto, PORTA_VOZ, "reel", "pecas/p/midia", palavras_por_segundo=2.8)
    assert _duracao(instalacao / r["audio"]) == pytest.approx(30 / 3.2, abs=0.06)
    assert r["fator_ritmo"] == pytest.approx((30 / 2.8) / (30 / 3.2), rel=0.01)
    assert r["alinhamento"]["character_end_times_seconds"][-8] <= 30 / 3.2

    # a mesma leitura lenta numa aula não é tocada
    a = base.narrar(instalacao, texto, PORTA_VOZ, "aula", "pecas/a/midia", palavras_por_segundo=2.8)
    assert _duracao(instalacao / a["audio"]) == pytest.approx(30 / 2.8, abs=0.06)
    assert a["fator_ritmo"] == 1.0


# ------------------------------------------------------------------ funcional

@pytest.mark.parametrize("segundos, palavras, tipo", [
    (8, 30, "reel"),        # 3,75 pal/s: já acima do piso
    (10, 30, "aula"),       # abaixo do piso, mas aula nunca é acelerada
    (10, 30, "carrossel"),  # ritmo mínimo só existe no reel
])
def test_acima_do_minimo_ou_aula_nao_altera_nada(tmp_path, segundos, palavras, tipo):
    mp3 = _mp3(tmp_path / "narracao.mp3", segundos)
    hash_antes = _hash(mp3)
    al = _alinhamento(40, segundos)

    novo, info = ritmo.aplicar(mp3, al, palavras, tipo, {"ritmo_min_pps": 3.47})

    assert _hash(mp3) == hash_antes             # sem re-encode
    assert novo == al                           # alinhamento idêntico
    assert info["fator"] == 1.0 and info["aplicado"] is False
    assert not list(tmp_path.glob("*.atempo*"))


def test_caminhos_da_origem_e_limite_de_seguranca(tmp_path):
    # tabela da origem (base/narrar-elevenlabs.md): 3,04 pal/s acelera; 3,49 / 3,73 / 5,00 não
    assert ritmo.fator_para(30 / 3.04, 30, ritmo.RITMO_MIN_PADRAO) == pytest.approx(1.141, abs=0.001)
    for pps in (3.49, 3.73, 5.00):
        assert ritmo.fator_para(30 / pps, 30, ritmo.RITMO_MIN_PADRAO) <= 1.0 + ritmo.RITMO_TOL

    # números calibrados da origem
    assert ritmo.RITMO_MIN_PADRAO == pytest.approx(3.47, abs=0.005)
    assert ritmo.RITMO_TOL == 0.03
    assert ritmo.ATEMPO_MAX == 1.35

    # dentro da tolerância de 3%: nada
    mp3 = _mp3(tmp_path / "tol.mp3", 8.8)          # 30/8,8 = 3,41 pal/s: fator 1,017
    h = _hash(mp3)
    _, info = ritmo.aplicar(mp3, _alinhamento(4, 8.8), 30, "reel", {"ritmo_min_pps": 3.47})
    assert info["aplicado"] is False and _hash(mp3) == h

    # fator acima de 1,35: não aplica e avisa
    mp3 = _mp3(tmp_path / "lento.mp3", 12)         # 2,5 pal/s: fator 1,388
    h = _hash(mp3)
    _, info = ritmo.aplicar(mp3, _alinhamento(4, 12), 30, "reel", {"ritmo_min_pps": 3.47})
    assert info["aplicado"] is False and _hash(mp3) == h
    assert "1.35" in info["aviso"]

    # sem ritmo_min_pps no porta-voz, vale o padrão da origem (3,47)
    mp3 = _mp3(tmp_path / "padrao.mp3", 10)
    _, info = ritmo.aplicar(mp3, _alinhamento(4, 10), 30, "reel", {})
    assert _duracao(mp3) == pytest.approx(30 / ritmo.RITMO_MIN_PADRAO, abs=0.06)
