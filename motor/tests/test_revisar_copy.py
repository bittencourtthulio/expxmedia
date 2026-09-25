"""T-09.10: revisão mecânica de copy (D-45), com os bloqueantes parametrizados pela Alma.

Os bloqueantes mecanizáveis da revisão editorial de origem (Instagram-Carrosseis/editorial/revisao.md:9-30):
travessão (quando a Alma proíbe), tratamento diferente de voz.tratamento, palavra proibida da Alma,
palavra do CTA diferente da publicação e primeira frase repetida em 14 dias contra as peças da instalação.
Cada ocorrência volta com a posição (arquivo, linha, coluna, índice).
"""
import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from expxmedia import cli
from expxmedia.nucleo import tempo
from expxmedia.peca import modelo
from expxmedia.revisar import copy as revisar_copy

MOTOR = Path(__file__).resolve().parents[1]


def _rodar(capsys, *argv):
    codigo = cli.main(list(argv))
    return codigo, json.loads(capsys.readouterr().out)


def _alma(raiz):
    return json.loads((raiz / "alma" / "alma.json").read_text(encoding="utf-8"))


def _gravar_alma(raiz, dados):
    (raiz / "alma" / "alma.json").write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def _peca(raiz, gancho, dias_atras, *, palavra=None, serie=None):
    peca = modelo.criar(raiz, tipo="carrossel", titulo=f"peça de {dias_atras} dias", formatos=["4:5"],
                        serie=serie, conteudo={"gancho": gancho})
    caminho = modelo.pasta(raiz, peca["peca_id"]) / "peca.json"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["criada_em"] = tempo.iso(tempo.agora(raiz) - timedelta(days=dias_atras))
    if palavra:
        dados["publicacoes"] = [{
            "canal": "instagram", "provedor": "expxflow", "estado": "agendada", "agendada_para": None,
            "publicada_em": None, "id_externo": None, "url": None,
            "automacao_dm": {"palavra": palavra, "id_externo": None}, "erro": None,
        }]
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return peca["peca_id"]


def _tipos(resultado):
    return [b["tipo"] for b in resultado["bloqueantes"]]


# ---------------------------------------------------------------- integração


def test_cli_acusa_abertura_repetida_contra_peca_de_5_dias(instalacao, tmp_path, capsys):
    recente = _peca(instalacao, "A fornada das 16h sai em dez minutos.", 5)
    _peca(instalacao, "Pão de ontem não precisa virar farinha.", 20)
    texto = tmp_path / "copy.txt"
    texto.write_text("A fornada das 16h sai em dez minutos!\nSepare o seu no balcão.\n", encoding="utf-8")

    codigo, dados = _rodar(capsys, "revisar", "copy", "--arquivo", str(texto), "--raiz", str(instalacao))

    assert codigo == cli.ERRO
    assert dados["ok"] is False and dados["aprovado"] is False
    assert _tipos(dados) == ["abertura_repetida"]
    b = dados["bloqueantes"][0]
    assert b["peca_id"] == recente
    assert (b["arquivo"], b["linha"], b["coluna"], b["indice"]) == ("copy.txt", 1, 1, 0)
    assert b["trecho"] == "A fornada das 16h sai em dez minutos!"


def test_abertura_de_20_dias_ou_da_propria_peca_nao_conta(instalacao, capsys, tmp_path):
    antiga = _peca(instalacao, "Pão de ontem não precisa virar farinha.", 20)
    propria = _peca(instalacao, "Três fornadas por dia, e a das 16h é a mais disputada.", 0)
    texto = tmp_path / "copy.txt"
    texto.write_text("Pão de ontem não precisa virar farinha. Vira torrada.\n", encoding="utf-8")
    assert revisar_copy.revisar(instalacao, {"copy.txt": texto.read_text(encoding="utf-8")})["aprovado"] is True
    texto.write_text("Três fornadas por dia, e a das 16h é a mais disputada.\n", encoding="utf-8")
    codigo, dados = _rodar(capsys, "revisar", "copy", "--arquivo", str(texto), "--peca", propria,
                           "--raiz", str(instalacao))
    assert codigo == cli.OK and dados["aprovado"] is True and dados["bloqueantes"] == []
    assert antiga  # a antiga existe e ficou fora da janela de 14 dias


def test_mesma_estrutura_de_abertura_pelas_tres_primeiras_palavras(instalacao):
    _peca(instalacao, "Você já reparou que o pão de fermentação dura mais?", 3)
    r = revisar_copy.revisar(instalacao, "Você já reparou como o croissant estala?\n")
    assert _tipos(r) == ["abertura_repetida"]
    r = revisar_copy.revisar(instalacao, "Você sabe a hora da fornada?\n")
    assert r["aprovado"] is True


def test_serie_restringe_a_comparacao(instalacao):
    _peca(instalacao, "A fornada das 16h sai em dez minutos.", 2, serie="fornadas")
    assert _tipos(revisar_copy.revisar(instalacao, "A fornada das 16h sai em dez minutos.", serie="outra")) == []
    assert _tipos(revisar_copy.revisar(instalacao, "A fornada das 16h sai em dez minutos.", serie="fornadas")) == [
        "abertura_repetida"]


def test_cli_em_subprocesso_aprova_texto_limpo(instalacao, tmp_path):
    texto = tmp_path / "limpo.txt"
    texto.write_text("A fornada das 16h sai fresquinha.\nComente PÃO e separe o seu.\n", encoding="utf-8")
    ambiente = {k: v for k, v in os.environ.items() if k != "EXPXMEDIA_PROVEDORES_TESTE"}
    feito = subprocess.run(
        ["uv", "run", "--project", str(MOTOR), "expxmedia-motor", "revisar", "copy", "--arquivo", str(texto),
         "--palavra-publicacao", "PÃO", "--raiz", str(instalacao)],
        capture_output=True, text=True, timeout=120, env=ambiente,
    )
    assert feito.returncode == 0, feito.stdout + feito.stderr
    dados = json.loads(feito.stdout)
    assert dados["aprovado"] is True
    assert {"tratamento", "palavra_proibida", "palavra_cta", "abertura_repetida"} <= set(dados["conferidos"])


# ---------------------------------------------------------------- funcional


def test_tu_numa_alma_de_voce_e_palavra_proibida_com_posicao(instalacao):
    texto = "Tu vais amar este pão.\nNada de pão gourmet por aqui, é tudo feito aqui.\n"
    r = revisar_copy.revisar(instalacao, {"legenda.txt": texto})
    assert r["aprovado"] is False
    assert _tipos(r) == ["tratamento", "palavra_proibida"]
    tratamento, proibida = r["bloqueantes"]
    assert (tratamento["arquivo"], tratamento["linha"], tratamento["coluna"], tratamento["indice"]) == ("legenda.txt", 1, 1, 0)
    assert tratamento["trecho"] == "Tu"
    assert (proibida["linha"], proibida["coluna"], proibida["indice"]) == (2, 13, texto.index("gourmet"))
    assert proibida["trecho"] == "gourmet"
    assert "voce" in tratamento["mensagem"] or "você" in tratamento["mensagem"]


def test_todas_as_formas_de_tu_e_palavra_proibida_com_varias_palavras(instalacao):
    texto = "Teu pão, tua mesa, teus filhos, tuas manhãs: contigo desde cedo. O melhor  do mundo? Tudo atual."
    r = revisar_copy.revisar(instalacao, texto)
    trechos = [(b["tipo"], b["trecho"]) for b in r["bloqueantes"]]
    assert trechos == [
        ("tratamento", "Teu"), ("tratamento", "tua"), ("tratamento", "teus"), ("tratamento", "tuas"),
        ("tratamento", "contigo"), ("palavra_proibida", "O melhor  do mundo"),
    ]


def test_alma_de_tu_acusa_voce(instalacao):
    alma = _alma(instalacao)
    alma["voz"]["tratamento"] = "tu"
    _gravar_alma(instalacao, alma)
    r = revisar_copy.revisar(instalacao, "Tu vais gostar. Voce e vocês também.")
    assert [(b["tipo"], b["trecho"]) for b in r["bloqueantes"]] == [("tratamento", "Voce"), ("tratamento", "vocês")]


def test_travessao_so_quando_a_regra_da_alma_proibe(instalacao):
    texto = "Pão quente — e sem fila. Das 7h – 9h."
    assert "travessao" not in _tipos(revisar_copy.revisar(instalacao, texto))
    alma = _alma(instalacao)
    alma["voz"]["regras"].append("Nunca use travessão")
    _gravar_alma(instalacao, alma)
    r = revisar_copy.revisar(instalacao, texto)
    assert [(b["tipo"], b["trecho"], b["indice"]) for b in r["bloqueantes"]] == [
        ("travessao", "—", texto.index("—")), ("travessao", "–", texto.index("–"))]


def test_palavra_do_cta_diferente_da_publicacao(instalacao):
    texto = "A fornada saiu.\nComente FORNO que a gente te avisa.\n"
    r = revisar_copy.revisar(instalacao, texto, palavra_publicacao="PÃO")
    assert _tipos(r) == ["palavra_cta"]
    b = r["bloqueantes"][0]
    assert (b["trecho"], b["linha"], b["coluna"]) == ("FORNO", 2, 9)
    assert "PÃO" in b["mensagem"]
    # a palavra da publicação vem da peça quando ela tem automação de DM
    peca = _peca(instalacao, None, 0, palavra="FORNO")
    assert revisar_copy.revisar(instalacao, texto, peca_id=peca)["aprovado"] is True
    outra = _peca(instalacao, None, 0, palavra="PÃO")
    assert _tipos(revisar_copy.revisar(instalacao, texto, peca_id=outra)) == ["palavra_cta"]


def test_sem_palavra_da_publicacao_o_cta_fica_nao_conferido(instalacao):
    r = revisar_copy.revisar(instalacao, "Comente FORNO.")
    assert r["aprovado"] is True
    assert "palavra_cta" in {n["tipo"] for n in r["nao_conferidos"]}


def test_alma_sem_tratamento_nao_inventa_regra(instalacao):
    alma = _alma(instalacao)
    alma["voz"]["tratamento"] = None
    _gravar_alma(instalacao, alma)
    r = revisar_copy.revisar(instalacao, "Tu vais amar.")
    assert r["aprovado"] is True
    assert "tratamento" in {n["tipo"] for n in r["nao_conferidos"]}
