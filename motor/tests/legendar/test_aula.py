"""T-04.09: legenda de aula (texto do roteiro nos tempos do whisper, 42 caracteres × 2 linhas) e SRT.

Paridade com o G5: as mesmas entradas (roteiro com marcadores [[cue]] e o JSON do whisper) geram o
mesmo `legendas.json` e o mesmo SRT que o `gerar_legendas.py` de origem gravou.
"""
import json
import re
from pathlib import Path

from expxmedia.legendar import aula, srt

G5 = Path(__file__).resolve().parents[1] / "golden" / "G5"


def _entradas():
    roteiro = (G5 / "entradas" / "roteiro.txt").read_text(encoding="utf-8")
    whisper = json.loads((G5 / "entradas" / "narracao.whisper.json").read_text(encoding="utf-8"))
    return roteiro, whisper


# ------------------------------------------------------------------ integração

def test_legendas_do_g5_iguais_ao_golden(tmp_path):
    roteiro, whisper = _entradas()
    legendas = aula.legendas_aula(roteiro, whisper)
    assert legendas == json.loads((G5 / "legendas.json").read_text(encoding="utf-8"))

    r = aula.gerar(roteiro, whisper, tmp_path / "legendas.json", tmp_path / "aula.srt")
    assert json.loads((tmp_path / "legendas.json").read_text(encoding="utf-8")) == legendas
    assert (tmp_path / "aula.srt").read_text(encoding="utf-8") == \
        (G5 / "radar-ia-09-jev-calibracao.srt").read_text(encoding="utf-8")
    assert r["legendas"] == len(legendas)


def test_aceita_as_palavras_da_transcricao_do_nucleo():
    """A saída de `transcrever` ({palavras: [{w, t0, t1}]}) dá o mesmo resultado que o JSON do whisper."""
    roteiro, whisper = _entradas()
    palavras = [{"w": w["word"].strip(), "t0": w["start"], "t1": w["end"]}
                for s in whisper["segments"] for w in s["words"]]
    assert aula.legendas_aula(roteiro, {"palavras": palavras}) == aula.legendas_aula(roteiro, whisper)


# ------------------------------------------------------------------ funcional

def test_nenhuma_linha_passa_de_42_e_no_maximo_2_linhas():
    roteiro, whisper = _entradas()
    legendas = aula.legendas_aula(roteiro, whisper)
    assert (aula.MAX_CARACTERES, aula.MAX_LINHAS) == (42, 2)
    for c in legendas:
        assert 1 <= len(c["lines"]) <= 2
        assert all(len(ln) <= 42 for ln in c["lines"]), c
        assert c["end"] > c["start"]
    for a, b in zip(legendas, legendas[1:]):
        assert a["end"] <= b["start"] - 0.05 + 1e-9  # folga de 0,05 s para a próxima


def test_srt_tem_indices_sequenciais_e_tempos_hh_mm_ss_mmm():
    roteiro, whisper = _entradas()
    texto = srt.gerar_srt(aula.legendas_aula(roteiro, whisper))
    blocos = texto.strip("\n").split("\n\n")
    padrao = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$")
    for n, bloco in enumerate(blocos, start=1):
        linhas = bloco.split("\n")
        assert linhas[0] == str(n)
        assert padrao.match(linhas[1]), linhas[1]
        assert 1 <= len(linhas[2:]) <= 2


def test_tempo_srt_nunca_gera_1000_milissegundos():
    assert srt.tempo_srt(3.9996) == "00:00:04,000"
    assert srt.tempo_srt(3723.25) == "01:02:03,250"


def test_sem_palavra_orfa_e_texto_do_roteiro_nao_do_whisper():
    # 47 caracteres: o guloso faria "Hoje vamos medir a confiança do modelo em" + "casa." (órfã)
    roteiro = "[[s1]]Hoje vamos medir a confiança do modelo em casa."
    whisper = {"palavras": [{"w": w, "t0": i * 0.4, "t1": i * 0.4 + 0.3} for i, w in enumerate(
        "hoje vamos medir a confianca do modelo em casa".split())]}
    (c,) = aula.legendas_aula(roteiro, whisper)
    assert " ".join(c["lines"]) == "Hoje vamos medir a confiança do modelo em casa."
    assert c["lines"] == ["Hoje vamos medir a", "confiança do modelo em casa."]
    assert c["start"] == 0.0


def test_palavra_sem_par_no_whisper_e_interpolada():
    roteiro = "Um dois tres quatro."
    whisper = {"palavras": [{"w": "um", "t0": 0.0, "t1": 0.5}, {"w": "dois", "t0": 0.6, "t1": 1.0},
                            {"w": "quatro", "t0": 2.0, "t1": 2.5}]}
    pal = aula.alinhar_palavras(roteiro, whisper)
    assert [p["w"] for p in pal] == ["Um", "dois", "tres", "quatro."]
    assert (pal[2]["s"], pal[2]["e"]) == (1.0, 2.0)
