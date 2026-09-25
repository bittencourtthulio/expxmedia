"""T-04.14: recasamento da transcrição (grafias corrigidas sobre os tempos do whisper).

Referência: o `--recasar` ATUAL de `Instragram-Videos/pipeline/transcrever.py:52-92`. O golden
`G7/alignment.recasado.json` foi gerado por esse código atual numa cópia temporária. A origem guardava
um alinhamento recasado ANTES da correção da inserção de largura zero (`transcrever.py:70-78`): naquela
versão a inserção pura esticava 0,02 s por caractere e invadia o caractere seguinte; por isso o arquivo
antigo da origem difere do golden em 3 tempos de fim por 0,02 s (manifesto, `observacoes` do G7). O teste
segue o código atual, que é o comportamento correto (a monotonicidade não quebra).
"""
import json
from pathlib import Path

import pytest

from expxmedia.transcrever import recasar as rc
from expxmedia.transcrever.whisper import para_alinhamento

G7 = Path(__file__).resolve().parents[1] / "golden" / "G7"


def _ler(nome):
    return json.loads((G7 / nome).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ integração

def test_recasar_a_transcricao_do_g7_igual_ao_golden():
    al = _ler("alignment.whisper.json")
    corrigido = (G7 / "roteiro.txt").read_text(encoding="utf-8")
    novo, mudados = rc.recasar(al, corrigido)
    assert novo == _ler("alignment.recasado.json")
    assert "".join(novo["characters"]) == corrigido.rstrip("\n")
    assert mudados > 0


def test_recasar_arquivos_grava_o_alinhamento_e_e_idempotente(tmp_path):
    (tmp_path / "alignment.json").write_text((G7 / "alignment.whisper.json").read_text(encoding="utf-8"),
                                              encoding="utf-8")
    (tmp_path / "roteiro.txt").write_text((G7 / "roteiro.txt").read_text(encoding="utf-8"), encoding="utf-8")
    r = rc.recasar_arquivos(tmp_path / "alignment.json", tmp_path / "roteiro.txt")
    assert r["recasado"] is True and r["trechos"] > 0
    assert json.loads((tmp_path / "alignment.json").read_text(encoding="utf-8")) == _ler("alignment.recasado.json")
    # texto já igual ao alinhamento: nada a fazer, arquivo intocado
    antes = (tmp_path / "alignment.json").stat().st_mtime_ns
    r2 = rc.recasar_arquivos(tmp_path / "alignment.json", tmp_path / "roteiro.txt")
    assert r2 == {"recasado": False, "trechos": 0, "caracteres": len(_ler("alignment.recasado.json")["characters"])}
    assert (tmp_path / "alignment.json").stat().st_mtime_ns == antes


# ------------------------------------------------------------------ funcional

def _al():
    # "esse request" — o caso real da origem: inserir "pull " no meio
    _, al = para_alinhamento([{"w": "esse", "t0": 78.0, "t1": 78.9}, {"w": "request", "t0": 79.06, "t1": 79.6}])
    return al


def test_insercao_pura_no_meio_tem_largura_zero_e_aparece_no_resultado():
    al = _al()
    novo, mudados = rc.recasar(al, "esse pull request")
    assert mudados == 1
    assert "".join(novo["characters"]) == "esse pull request"
    cs_n, ce_n = novo["character_start_times_seconds"], novo["character_end_times_seconds"]
    # os 5 caracteres inseridos (difflib escolhe " pull" antes do espaço velho) têm largura zero,
    # contíguos, exatamente no início do caractere seguinte — que conserva o tempo velho
    zero = [k for k in range(len(cs_n)) if cs_n[k] == ce_n[k]]
    assert len(zero) == len("pull ") and zero == list(range(zero[0], zero[0] + 5))
    seguinte = zero[-1] + 1
    assert all(cs_n[k] == cs_n[seguinte] for k in zero)
    assert cs_n[seguinte] in al["character_start_times_seconds"]
    # os tempos dos trechos iguais são copiados exatos
    assert cs_n[:zero[0]] + cs_n[seguinte:] == al["character_start_times_seconds"]
    assert ce_n[:zero[0]] + ce_n[seguinte:] == al["character_end_times_seconds"]
    cs = novo["character_start_times_seconds"]
    assert all(b >= a - 1e-6 for a, b in zip(cs, cs[1:]))


def test_insercao_no_fim_estica_0_02_s_por_caractere():
    al = _al()
    novo, _ = rc.recasar(al, "esse request!!")
    fim = al["character_end_times_seconds"][-1]
    assert novo["character_start_times_seconds"][-2:] == [round(fim, 4), round(fim + 0.02, 4)]
    assert novo["character_end_times_seconds"][-1] == round(fim + 0.04, 4)


def test_troca_distribui_o_intervalo_uniformemente():
    al = _al()
    novo, _ = rc.recasar(al, "essa request")  # 'e' → 'a' na 4ª letra
    cs, ce = al["character_start_times_seconds"], al["character_end_times_seconds"]
    assert novo["character_start_times_seconds"][3] == cs[3]
    assert novo["character_end_times_seconds"][3] == ce[3]


def test_texto_identico_nao_muda_nada():
    al = _al()
    novo, mudados = rc.recasar(al, "esse request\n")
    assert mudados == 0 and novo == al


def test_alinhamento_invalido_levanta():
    al = _al()
    al["character_start_times_seconds"] = al["character_start_times_seconds"][:-1]
    with pytest.raises(rc.ErroRecasar):
        rc.recasar(al, "esse pull request")
