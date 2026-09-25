"""T-03.03: contraste medido no PNG, com e sem a tinta do texto, no ponto pior do fundo (D-20).

O slide é fotografado duas vezes: com o texto e sem a tinta dele. O que muda entre as duas é a
tinta; o que não muda é o que está atrás. O contraste é cobrado entre a cor da tinta e os
percentis 5% e 95% de luminância do que está atrás. `data-sobre` e `decorativo` isentam.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw

from expxmedia.render_html import contraste, renderizar

CSS = """.slide{display:flex;flex-direction:column;padding:80px;background:var(--alma-fundo);color:var(--alma-texto);font-family:var(--alma-fonte-texto)}
h1{font-size:112px;font-weight:700;margin:0}"""
KINDS = {"k": {"vazio_ok": True, "fit": "fixo", "slots": {"a": {"tipo": "texto", "max": 60, "obrigatorio": True}}}}
COPY = {"slides": [{"kind": "k", "a": "Texto de teste"}]}


def _cinza_com_razao(razao, fundo=(255, 255, 255)):
    """O cinza mais próximo da razão pedida contra o fundo (o texto é mais escuro que o fundo)."""
    melhor = min(range(256), key=lambda v: abs(contraste.razao((v, v, v), fundo) - razao))
    return f"#{melhor:02x}{melhor:02x}{melhor:02x}", contraste.razao((melhor, melhor, melhor), fundo)


def _achados(r, tipo):
    return [p for s in r["slides"] for p in s["problemas"] if p["tipo"] == tipo]


def test_numeros_calibrados_da_origem():
    assert contraste.DISTANCIA_TINTA == 40
    assert contraste.TINTA_MINIMA == 0.02
    assert contraste.TRACO_DO_TEXTO == 0.15
    assert contraste.PERCENTIS == (0.05, 0.95)
    assert contraste.BALDE == 24


def test_g1_com_a_alma_golden_nao_tem_achado_de_contraste(g1):
    r = g1["resultado"]
    assert [p for s in r["slides"] for p in s["problemas"] if p["tipo"] in ("contraste_baixo", "texto_invisivel")] == []
    assert r["ok"], [s["problemas"] for s in r["slides"]]


@pytest.mark.parametrize("razao,reprova", [(2.8, True), (3.2, False)])
def test_par_texto_fundo_2_8_reprova_e_3_2_passa(criar_template, alma_neutra, tmp_path, razao, reprova):
    cor, real = _cinza_com_razao(razao)
    assert abs(real - razao) < 0.05
    r = renderizar.renderizar(criar_template(KINDS, CSS, {"k": "<h1>{{a}}</h1>"}), COPY,
                              alma_neutra(fundo="#ffffff", texto=cor), tmp_path / "s")
    achados = _achados(r, "contraste_baixo")
    assert bool(achados) is reprova, (cor, real, r["slides"][0]["problemas"])
    if reprova:
        assert achados[0]["detalhe"] == f"h1: contraste {real:.1f}:1 entre o texto e o fundo (o mínimo é 3:1)"


def test_ponto_pior_do_fundo_reprova_texto_sobre_divisa(criar_template, alma_neutra, tmp_path):
    # metade de baixo do título sobre uma faixa escura: a cor média passaria, o ponto pior não
    css = CSS + ".faixa{position:absolute;left:0;right:0;top:150px;height:200px;background:var(--alma-fundo_alt)}h1{position:relative}"
    frag = '<div class="faixa"></div><h1>{{a}}</h1>'
    r = renderizar.renderizar(criar_template(KINDS, css, {"k": frag}), COPY,
                              alma_neutra(fundo="#ffffff", texto="#111111", fundo_alt="#1a1a1a"), tmp_path / "s")
    achados = _achados(r, "contraste_baixo")
    assert achados and "o ponto pior do que está atrás" in achados[0]["detalhe"], r["slides"][0]["problemas"]


def test_data_sobre_e_decorativo_isentam(criar_template, alma_neutra, tmp_path):
    cor, _ = _cinza_com_razao(1.5)
    alma = alma_neutra(fundo="#ffffff", texto=cor)
    r = renderizar.renderizar(criar_template(KINDS, CSS, {"k": "<h1 data-sobre>{{a}}</h1>"}), COPY, alma, tmp_path / "s1")
    assert _achados(r, "contraste_baixo") == []
    r = renderizar.renderizar(criar_template(KINDS, CSS, {"k": '<h1 class="enfeite">{{a}}</h1>'}, tipografia={"decorativo": [".enfeite"]}),
                              COPY, alma, tmp_path / "s2")
    assert _achados(r, "contraste_baixo") == []
    r = renderizar.renderizar(criar_template(KINDS, CSS, {"k": "<h1>{{a}}</h1>"}), COPY, alma, tmp_path / "s3")
    assert _achados(r, "contraste_baixo")


def test_enfeite_por_cima_do_texto_e_texto_que_nao_aparece(criar_template, alma_neutra, tmp_path):
    css = CSS + ".tampa{position:absolute;top:0;left:0;width:1080px;height:400px;background:var(--alma-destaque)}"
    r = renderizar.renderizar(criar_template(KINDS, css, {"k": '<h1>{{a}}</h1><div class="tampa"></div>'}), COPY,
                              alma_neutra(), tmp_path / "s")
    assert _achados(r, "texto_invisivel"), r["slides"][0]["problemas"]


def test_cor_com_alfa_e_color_mix_sao_compostas_com_o_fundo():
    assert contraste.rgb_de("rgb(10, 20, 30)") == (10, 20, 30)
    assert contraste.rgb_de("rgba(0, 0, 0, 0.5)", (255, 255, 255)) == (128, 128, 128)
    # o Chromium serializa color-mix() como color(srgb 0..1 / alfa): escala para 0..255
    assert contraste.rgb_de("color(srgb 1 1 1 / 0.5)", (0, 0, 0)) == (128, 128, 128)
    assert contraste.rgb_de("color(srgb 0.2 0.4 0.6)") == (51, 102, 153)


def test_conferir_leitura_com_imagens_sinteticas():
    def png(desenho):
        img = Image.new("RGB", (400, 200), (255, 255, 255))
        desenho(ImageDraw.Draw(img))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    fundo = png(lambda d: None)
    com_texto = png(lambda d: d.rectangle((20, 20, 380, 180), fill=(200, 200, 200)))  # "tinta" clara no branco
    caixa = {"quem": "h1", "cor": "rgb(200, 200, 200)", "sobre": False, "pintura": False, "x1": 0, "y1": 0, "x2": 400, "y2": 200}
    cfg = {"contraste": 3.0}
    achados = contraste.conferir_leitura(com_texto, fundo, [caixa], cfg)
    assert [a["tipo"] for a in achados] == ["contraste_baixo"]
    assert contraste.conferir_leitura(fundo, fundo, [caixa], cfg)[0]["tipo"] == "texto_invisivel"
    assert contraste.conferir_leitura(com_texto, fundo, [{**caixa, "sobre": True}], cfg) == []


def test_dominante_por_baldes_e_empate_pela_primeira_cor():
    assert contraste.dominante([(0, 0, 0), (250, 250, 250), (251, 251, 251)]) == ((252, 252, 252), 2 / 3)
    assert contraste.dominante([(0, 0, 0), (250, 250, 250)]) == ((12, 12, 12), 0.5)
