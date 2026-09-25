"""T-05.08: schema do deck da apresentação e validação, sem CTA fixo (base/apresentacao-deck.md).

- Integração: o deck real do G6 (sistema de origem), convertido para o schema do núcleo, valida sem
  achado; o CTA sem URL recebe a da Alma.
- Funcional: tipo desconhecido cita os tipos aceitos; cada teto calibrado (palavras, itens, slides,
  contraste 3:1) está no limite exato da origem.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from expxmedia.producao.apresentacao import deck

G6 = Path(__file__).resolve().parents[2] / "golden" / "G6" / "deck.json"
ALMA = Path(__file__).resolve().parents[2] / "fixtures" / "alma-ficticia" / "alma" / "alma.json"
TIPOS_DA_ORIGEM = ["titulo", "declaracao", "grade", "comparacao", "etapas", "estatisticas", "fluxo", "screenshot", "cta"]


@pytest.fixture
def g6():
    return deck.de_origem(json.loads(G6.read_text(encoding="utf-8")))


@pytest.fixture
def alma():
    return json.loads(ALMA.read_text(encoding="utf-8"))


def _campos(achados):
    return [a["campo"] for a in achados]


# ---------------------------------------------------------------- integração


def test_deck_do_g6_convertido_valida_sem_achado(g6):
    assert deck.validar(g6) == []
    assert set(g6) == {"titulo", "tema", "slides"}
    assert [s["tipo"] for s in g6["slides"]] == ["titulo", "declaracao", "comparacao", "grade", "etapas",
                                                  "estatisticas", "fluxo", "screenshot", "cta"]
    # o CTA fixo da origem saiu: a URL vem da Alma
    assert g6["slides"][-1]["url"] is None
    assert g6["tema"]["cor"] == "#D97757"


def test_o_g6_da_origem_sem_converter_nao_valida():
    """Controle: o deck cru da origem tem as chaves da fila de pautas e a marca fixa (D-48, M13)."""
    cru = json.loads(G6.read_text(encoding="utf-8"))
    campos = _campos(deck.validar(cru))
    assert {"slug", "pauta_id", "pauta", "marca", "criado_em", "gerado_por"} <= set(campos)


def test_cta_vazio_recebe_o_cta_da_alma(g6, alma):
    completo, avisos = deck.completar_cta(g6, alma)
    cta = completo["slides"][-1]
    assert cta["url"] == alma["cta"]["destino"]
    assert cta["titulo"] == g6["slides"][-1]["titulo"]  # o que o deck trouxe vale
    assert avisos == []
    assert g6["slides"][-1]["url"] is None  # o deck não muda
    sem_titulo = copy.deepcopy(g6)
    sem_titulo["slides"][-1]["titulo"] = None
    completo, _ = deck.completar_cta(sem_titulo, alma)
    assert completo["slides"][-1]["titulo"] == alma["cta"]["padrao"]
    assert deck.validar(completo) == []


def test_sem_cta_na_alma_o_campo_fica_null_com_aviso(g6, alma):
    alma["cta"] = {"padrao": None, "destino": None, "variacoes": []}
    completo, avisos = deck.completar_cta(g6, alma)
    assert completo["slides"][-1]["url"] is None
    assert any("url" in a and "cta.destino" in a for a in avisos)


# ---------------------------------------------------------------- funcional


def test_tipo_desconhecido_cita_os_tipos_aceitos(g6):
    g6["slides"][3] = {"tipo": "grafico", "titulo": "x"}
    achados = deck.validar(g6)
    assert len(achados) == 1
    assert achados[0]["campo"] == "slides[3].tipo"
    for tipo in TIPOS_DA_ORIGEM:
        assert tipo in achados[0]["detalhe"]
    assert "'grafico'" in achados[0]["detalhe"]


def test_os_tipos_e_tetos_sao_os_da_origem():
    assert list(deck.TIPOS) == TIPOS_DA_ORIGEM
    assert deck.TIPOS["titulo"] == {"kicker": 4, "titulo": 10, "subtitulo": 20}
    assert deck.TIPOS["declaracao"] == {"texto": 20, "autor": 4}
    assert deck.TIPOS["screenshot"] == {"titulo": 6, "legenda": 12}
    assert deck.TIPOS["cta"] == {"titulo": 10, "texto": 16}
    assert (deck.SLIDES_MIN, deck.SLIDES_MAX, deck.CONTRASTE_MINIMO) == (6, 10, 3.0)


def _palavras(n):
    return " ".join(f"p{i}" for i in range(n))


@pytest.mark.parametrize("indice, campo, teto", [
    (0, "titulo", 10), (0, "subtitulo", 20), (0, "kicker", 4), (1, "texto", 20), (1, "autor", 4),
    (2, "titulo", 8), (7, "titulo", 6), (7, "legenda", 12), (8, "titulo", 10), (8, "texto", 16),
])
def test_teto_de_palavras_no_limite_exato(g6, indice, campo, teto):
    g6["slides"][indice][campo] = _palavras(teto)
    assert deck.validar(g6) == []
    g6["slides"][indice][campo] = _palavras(teto + 1)
    achados = deck.validar(g6)
    assert _campos(achados) == [f"slides[{indice}].{campo}"]
    assert f"no máximo {teto} palavras (tem {teto + 1})" in achados[0]["detalhe"]


def test_b_nao_conta_como_palavra_e_so_vale_em_titulo_e_declaracao(g6):
    g6["slides"][0]["titulo"] = "<b>" + _palavras(10) + "</b>"
    assert deck.validar(g6) == []
    g6["slides"][2]["titulo"] = "Entrada <b>contra</b> trabalho"
    assert _campos(deck.validar(g6)) == ["slides[2].titulo"]


@pytest.mark.parametrize("indice, chave, minimo, maximo", [
    (3, "itens", 3, 6),   # grade
    (4, "itens", 3, 5),   # etapas
    (6, "nos", 3, 6),     # fluxo
    (5, "numeros", 1, 4),  # estatisticas
])
def test_quantidade_de_itens_no_limite_exato(g6, indice, chave, minimo, maximo):
    modelo = g6["slides"][indice][chave][0]
    for n in (minimo, maximo):
        g6["slides"][indice][chave] = [copy.deepcopy(modelo) for _ in range(n)]
        assert deck.validar(g6) == [], n
    for n in (minimo - 1, maximo + 1):
        g6["slides"][indice][chave] = [copy.deepcopy(modelo) for _ in range(n)]
        assert _campos(deck.validar(g6)) == [f"slides[{indice}].{chave}"], n


def test_comparacao_de_1_a_5_itens_por_lado(g6):
    g6["slides"][2]["direita"]["itens"] = ["um"] * 5
    assert deck.validar(g6) == []
    g6["slides"][2]["direita"]["itens"] = ["um"] * 6
    assert _campos(deck.validar(g6)) == ["slides[2].direita.itens"]
    g6["slides"][2]["direita"]["itens"] = []
    assert _campos(deck.validar(g6)) == ["slides[2].direita.itens"]


@pytest.mark.parametrize("n, ok", [(5, False), (6, True), (10, True), (11, False)])
def test_de_6_a_10_slides(g6, n, ok):
    meio = [copy.deepcopy(g6["slides"][1]) for _ in range(n - 2)]
    g6["slides"] = [g6["slides"][0], *meio, g6["slides"][-1]]
    achados = deck.validar(g6)
    assert (achados == []) is ok
    if not ok:
        assert _campos(achados) == ["slides"] and f"(tem {n})" in achados[0]["detalhe"]


def test_primeiro_e_titulo_e_ultimo_e_cta(g6):
    g6["slides"][0], g6["slides"][-1] = g6["slides"][-1], g6["slides"][0]
    detalhes = " ".join(a["detalhe"] for a in deck.validar(g6))
    assert "primeiro slide é do tipo titulo" in detalhes and "último slide é do tipo cta" in detalhes


def test_contar_slides_false_aceita_trecho_do_deck(g6):
    trecho = {"titulo": "x", "tema": None, "slides": g6["slides"][2:5]}
    assert deck.validar(trecho) != []
    assert deck.validar(trecho, contar_slides=False) == []


@pytest.mark.parametrize("campo, valor, trecho", [
    ("texto", "Hora que não paga — nunca", "travessão"),
    ("texto", "Hora que não paga – nunca", "meia-risca"),
    ("texto", "linha um\nlinha dois", "quebra de linha"),
])
def test_proibidos_em_qualquer_texto(g6, campo, valor, trecho):
    g6["slides"][1][campo] = valor
    achados = deck.validar(g6)
    assert _campos(achados) == [f"slides[1].{campo}"] and trecho in achados[0]["detalhe"]


def test_numero_sem_fonte_ou_sem_valor_numerico(g6):
    g6["slides"][5]["numeros"][0]["fonte"] = " "
    g6["slides"][5]["numeros"][1]["valor"] = "100"
    g6["slides"][5]["numeros"][2]["valor"] = True
    assert _campos(deck.validar(g6)) == ["slides[5].numeros[0].fonte", "slides[5].numeros[1].valor",
                                         "slides[5].numeros[2].valor"]


def test_imagem_so_nome_de_arquivo_em_ativos(g6):
    g6["slides"][7]["imagem"] = "../fora.png"
    g6["tema"]["logo"] = "https://exemplo.invalid/logo.png"
    assert _campos(deck.validar(g6)) == ["tema.logo", "slides[7].imagem"]
    g6["slides"][7]["imagem"] = None
    g6["tema"]["logo"] = None
    assert deck.validar(g6) == []


def test_cor_do_tema_hex_e_contraste_3_sobre_o_fundo_da_alma(g6, alma):
    g6["tema"]["cor"] = "rgb(1,2,3)"
    assert _campos(deck.validar(g6)) == ["tema.cor"]
    fundo = alma["visual"]["cores"]["fundo"]
    # 3:1 é o limite: 3,00 passa, 2,96 reprova
    g6["tema"]["cor"] = "#D57855"
    assert deck.contraste("#D57855", fundo) == 3.0
    assert deck.validar(g6, alma=alma) == []
    g6["tema"]["cor"] = "#D97757"
    assert deck.contraste("#D97757", fundo) < 3.0
    achados = deck.validar(g6, alma=alma)
    assert _campos(achados) == ["tema.cor"] and "mínimo 3.0:1" in achados[0]["detalhe"]
    assert deck.validar(g6) == []  # sem Alma não há fundo para medir


def test_contraste_wcag_como_na_origem():
    assert deck.contraste("#000000", "#FFFFFF") == 21.0
    assert deck.contraste("#FFFFFF", "#FFFFFF") == 1.0


def test_cta_url_opcional_mas_nunca_vazia(g6):
    g6["slides"][-1]["url"] = "exemplo.invalid/entrar"
    assert deck.validar(g6) == []
    g6["slides"][-1]["url"] = "  "
    assert _campos(deck.validar(g6)) == ["slides[8].url"]


def test_chave_desconhecida_na_raiz_e_no_tema(g6):
    g6["cta_fixo"] = "x"
    g6["tema"]["site"] = "x"
    assert _campos(deck.validar(g6)) == ["cta_fixo", "tema.site"]


def test_imagens_lista_logo_e_imagens_de_slide(g6):
    assert deck.imagens(g6) == [("tema.logo", "logo.png"), ("slides[7].imagem", "print.png"),
                                ("slides[8].imagem", "expxplay.png")]
