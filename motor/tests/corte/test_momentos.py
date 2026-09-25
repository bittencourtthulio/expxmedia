"""T-06.04: escolha do trecho do vídeo longo (porta de `Instragram-Videos/pipeline/momentos.py`).

- integração: com a transcrição do G7 (varredura da origem) e o `fonte.json` dela, o ranqueamento devolve
  EXATAMENTE os candidatos que a origem gravou (mesma ordem, bordas, pontos, notas e texto), e o trecho
  escolhido é o primeiro deles;
- funcional: a janela escolhida tem no máximo 72 s e começa e termina em fronteira de palavra (começo de
  frase: depois de `. ? !` ou de pausa ≥ 0,6 s; fim: palavra que fecha frase);
- as listas de palavras e os pesos vêm da configuração por idioma (`recursos/momentos/pt.json`), escolhida
  pelo idioma da Alma; mudar um peso na configuração muda o ranqueamento.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from expxmedia.corte import momentos

G7 = Path(__file__).resolve().parents[1] / "golden" / "G7"


def _g7():
    tr = json.loads((G7 / "transcricao.json").read_text(encoding="utf-8"))
    fonte = json.loads((G7 / "entradas" / "fonte.json").read_text(encoding="utf-8"))
    esperado = json.loads((G7 / "candidatos.json").read_text(encoding="utf-8"))
    return tr, fonte, esperado


# ------------------------------------------------------------------ integração


def test_g7_mesmos_candidatos_e_mesmo_trecho_da_origem():
    tr, fonte, esperado = _g7()
    config = momentos.carregar_config("pt-BR")

    r = momentos.candidatos(tr, faixas_ja_usadas=fonte["faixas_ja_usadas"], config=config)

    assert r["gerados"] == esperado["gerados"] == 130
    assert r["candidatos"] == esperado["candidatos"]
    trecho = momentos.escolher(tr, faixas_ja_usadas=fonte["faixas_ja_usadas"], config=config)
    primeiro = esperado["candidatos"][0]
    assert (trecho["inicio"], trecho["fim"]) == (primeiro["inicio"], primeiro["fim"]) == (517.05, 587.27)


def test_config_vem_do_idioma_da_alma(instalacao):
    alma = json.loads((instalacao / "alma" / "alma.json").read_text(encoding="utf-8"))
    assert alma["empresa"]["idioma"] == "pt-BR"
    config = momentos.config_da_alma(alma)
    assert config == momentos.carregar_config("pt")
    # padrão = valores da origem (momentos.py:58, :81, :116-120 e lib.py:135)
    assert config["palavras_3s"] == 12
    assert config["pausa_frase_s"] == 0.6
    assert config["janela_min_s"] == 52.0 and config["janela_max_s"] == 72.0
    assert config["pesos"]["numero_abertura"] == 3.0 and config["pesos"]["anafora"] == -3.0

    with pytest.raises(momentos.ErroMomentos, match="xx"):
        momentos.carregar_config("xx-YY")


# ------------------------------------------------------------------ funcional


def test_janela_ate_72s_em_fronteira_de_palavra():
    tr, fonte, _ = _g7()
    config = momentos.carregar_config("pt")
    P = tr["palavras"]
    trecho = momentos.escolher(tr, faixas_ja_usadas=fonte["faixas_ja_usadas"], config=config)

    assert trecho["duracao"] <= 72.0
    assert trecho["fim"] - trecho["inicio"] <= 72.0 + 1e-9
    assert trecho["duracao"] >= 52.0
    # começa numa palavra que abre frase e termina numa que fecha frase
    i = next(k for k, p in enumerate(P) if round(p["t0"], 2) == trecho["inicio"])
    j = next(k for k, p in enumerate(P) if round(p["t1"], 2) == trecho["fim"] and k > i)
    assert i == 0 or P[i - 1]["w"].endswith((".", "?", "!")) or P[i]["t0"] - P[i - 1]["t1"] >= 0.6
    assert P[j]["w"].endswith((".", "?", "!"))
    assert trecho["palavras"] == j - i + 1
    assert trecho["texto"] == " ".join(p["w"] for p in P[i:j + 1])

    # todos os candidatos respeitam a janela e não se sobrepõem
    r = momentos.candidatos(tr, faixas_ja_usadas=fonte["faixas_ja_usadas"], config=config)
    cs = r["candidatos"]
    assert all(52.0 <= c["duracao"] <= 72.0 for c in cs)
    for a in cs:
        for b in cs:
            if a is not b:
                assert a["fim"] <= b["inicio"] or a["inicio"] >= b["fim"]


def test_janela_menor_encolhe_o_trecho():
    tr, _, _ = _g7()
    config = momentos.carregar_config("pt")
    r = momentos.candidatos(tr, config=config, maximo=60.0)
    assert r["candidatos"] and all(c["duracao"] <= 60.0 for c in r["candidatos"])


def test_peso_da_configuracao_muda_o_ranqueamento():
    tr, fonte, esperado = _g7()
    config = copy.deepcopy(momentos.carregar_config("pt"))
    config["pesos"]["numero_abertura"] = 0.0
    config["pesos"]["numero_trecho"] = 0.0
    r = momentos.candidatos(tr, faixas_ja_usadas=fonte["faixas_ja_usadas"], config=config)
    assert r["candidatos"] != esperado["candidatos"]


def test_faixa_ja_usada_derruba_o_trecho():
    tr, _, esperado = _g7()
    config = momentos.carregar_config("pt")
    primeiro = esperado["candidatos"][0]
    r = momentos.candidatos(tr, faixas_ja_usadas=[[primeiro["inicio"], primeiro["fim"]]], config=config)
    assert (r["candidatos"][0]["inicio"], r["candidatos"][0]["fim"]) != (primeiro["inicio"], primeiro["fim"])
    usado = next(c for c in r["candidatos"] if c["inicio"] == primeiro["inicio"])
    assert usado["ja_usado_frac"] == 1.0
    # −5 × fração já usada: 5,64 − 5,0 = 0,64 (momentos.py:181)
    assert usado["pontos"] == round(primeiro["pontos"] - 5.0, 2)
    assert any("já usado" in n for n in usado["notas"])


def test_sem_palavras_e_sem_fim_de_frase_sao_erro():
    config = momentos.carregar_config("pt")
    with pytest.raises(momentos.ErroMomentos, match="sem palavras"):
        momentos.candidatos({"palavras": []}, config=config)
    sem_pontuacao = {"palavras": [{"w": "fala", "t0": i * 0.5, "t1": i * 0.5 + 0.4} for i in range(300)]}
    with pytest.raises(momentos.ErroMomentos, match="fim de frase"):
        momentos.candidatos(sem_pontuacao, config=config)
