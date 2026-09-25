"""T-03.02: encaixe de texto e medição do DOM, com os números da origem (D-20).

0,96 por rodada (até 40), zoom de 0,02 entre 0,8 e 1,3 enquanto sobrar mais de 40 px, fonte
mínima 28 px, piso 18 px para o miúdo, faixa vazia de 22% no topo ou no rodapé.
"""
from __future__ import annotations

import re

from expxmedia.render_html import encaixe, renderizar

BASE = """.slide{display:flex;flex-direction:column;padding:80px;background:var(--alma-fundo);color:var(--alma-texto);font-family:var(--alma-fonte-texto)}
h1{font-size:96px;margin:0}.vis{flex:1;min-height:0}"""


def _problemas(r, tipo=None):
    return [p for s in r["slides"] for p in s["problemas"] if tipo is None or p["tipo"] == tipo]


def test_numeros_calibrados_da_origem():
    assert encaixe.FATOR_ENCOLHER == 0.96
    assert encaixe.RODADAS_ENCOLHER == 40
    assert encaixe.PASSO_ZOOM == 0.02
    assert encaixe.FOLGA_CRESCER_PX == 40
    assert (encaixe.FIT_PADRAO["zoom_min"], encaixe.FIT_PADRAO["zoom_max"]) == (0.8, 1.3)
    assert encaixe.TIPOGRAFIA_PADRAO["minimo"] == 28 and encaixe.TIPOGRAFIA_PADRAO["piso"] == 18
    assert encaixe.TIPOGRAFIA_PADRAO["vazio_max"] == 0.22 and encaixe.TIPOGRAFIA_PADRAO["contraste"] == 3.0


def test_encaixe_do_g1_bate_com_o_render_json_do_golden(g1):
    nosso, golden = g1["resultado"], g1["golden"]
    assert [s["kind"] for s in nosso["slides"]] == [s["kind"] for s in golden["slides"]]
    for meu, dele in zip(nosso["slides"], golden["slides"]):
        assert meu["encaixe"] == dele["encaixe"], (meu["kind"], meu["encaixe"], dele["encaixe"])
        assert [a["detalhe"] for a in meu["avisos"]] == dele["avisos"], meu["kind"]
        assert [p["detalhe"] for p in meu["problemas"]] == dele["problemas"], meu["kind"]
    assert [s["encaixe"] for s in nosso["slides"]] == ["free=19 shrink=0 zoom=1", "fixo", "fixo", "free=27 shrink=0 zoom=1"]


def test_texto_tres_vezes_maior_que_o_espaco_encolhe_e_acusa_fonte_abaixo_do_minimo(criar_template, alma_neutra, tmp_path):
    css = BASE + ".vis{flex:none;height:360px}.texto{font-size:32px;line-height:1.25;margin:0;width:900px}"
    kinds = {"k": {"vazio_ok": True, "slots": {"texto": {"tipo": "texto", "max": 2000, "obrigatorio": True}}}}
    fit = {"container": ".vis", "encolher": [".texto"], "zoom_min": 0.8, "zoom_max": 1.3, "margem": 0}
    template = criar_template(kinds, css, {"k": '<div class="vis"><div><p class="texto">{{texto}}</p></div></div>'}, fit=fit)
    # 32 px x 1.25 = 40 px por linha; 9 linhas cabem em 360 px. 27 linhas = três vezes o espaço.
    texto = " ".join(["palavra"] * 27 * 9)
    r = renderizar.renderizar(template, {"slides": [{"kind": "k", "texto": texto}]}, alma_neutra(), tmp_path / "saida")
    enc = r["slides"][0]["encaixe"]
    shrink = int(re.search(r"shrink=(\d+)", enc).group(1))
    assert shrink > 0 and int(re.search(r"free=(-?\d+)", enc).group(1)) >= 0, enc
    abaixo = _problemas(r, "fonte_abaixo_do_minimo")
    assert abaixo, r["slides"][0]["problemas"]
    px = int(re.search(r"texto de (\d+)px \(o mínimo é 28px\)", abaixo[0]["detalhe"]).group(1))
    # cada rodada multiplica a fonte por 0,96: o tamanho final prova o fator e o número de rodadas
    assert px == round(32 * 0.96 ** shrink) and px < 28
    assert not r["ok"]


def test_minimo_28_e_piso_18_do_miudo(criar_template, alma_neutra, tmp_path):
    kinds = {"k": {"vazio_ok": True, "fit": "fixo", "slots": {"a": {"tipo": "texto", "max": 30, "obrigatorio": True}}}}
    frag = '<h1>{{a}}</h1><p class="t28">vinte e oito</p><p class="t27">vinte e sete</p><p class="m18">miúdo</p><p class="m17">miúdo menor</p>'
    css = BASE + "p{margin:10px 0}.t28{font-size:28px}.t27{font-size:27px}.m18{font-size:18px}.m17{font-size:17px}"
    tip = {"miudo": [".m18", ".m17"]}
    r = renderizar.renderizar(criar_template(kinds, css, {"k": frag}, tipografia=tip), {"slides": [{"kind": "k", "a": "Título"}]},
                              alma_neutra(), tmp_path / "s")
    detalhes = [p["detalhe"] for p in _problemas(r, "fonte_abaixo_do_minimo")]
    assert detalhes == ["p.t27: texto de 27px (o mínimo é 28px)", "p.m17: texto de 17px (o mínimo de texto miúdo é 18px)"]


def test_template_nao_baixa_o_minimo_do_contrato(criar_template, alma_neutra, tmp_path):
    kinds = {"k": {"vazio_ok": True, "fit": "fixo", "slots": {"a": {"tipo": "texto", "max": 30, "obrigatorio": True}}}}
    css = BASE + ".t20{font-size:20px}"
    template = criar_template(kinds, css, {"k": '<h1>{{a}}</h1><p class="t20">vinte</p>'},
                              tipografia={"minimo": 12, "piso": 8, "contraste": 1.5, "vazio_max": 0.9})
    _fit, tip = encaixe.configuracao(renderizar.carregar_template(template))
    assert (tip["minimo"], tip["piso"], tip["contraste"], tip["vazio_max"]) == (28, 18, 3.0, 0.22)
    r = renderizar.renderizar(template, {"slides": [{"kind": "k", "a": "Título"}]}, alma_neutra(), tmp_path / "s")
    assert _problemas(r, "fonte_abaixo_do_minimo")


def test_zoom_cresce_ate_1_3_e_recua_ate_0_8(criar_template, alma_neutra, tmp_path):
    kinds = {"k": {"vazio_ok": True, "slots": {"a": {"tipo": "texto", "max": 200, "obrigatorio": True}}}}
    fit = {"container": ".vis", "encolher": ["p"], "zoom_min": 0.8, "zoom_max": 1.3, "margem": 0}
    css = BASE + "p{font-size:40px;margin:0}.largo{white-space:nowrap;width:300px}"
    frag = '<div class="vis"><div><p>{{a}}</p></div></div>'
    r = renderizar.renderizar(criar_template(kinds, css, {"k": frag}, fit=fit), {"slides": [{"kind": "k", "a": "curto"}]},
                              alma_neutra(), tmp_path / "s1")
    assert r["slides"][0]["encaixe"].endswith("shrink=0 zoom=1.3"), r["slides"][0]["encaixe"]
    frag = '<div class="vis"><div><p class="largo">{{a}}</p></div></div>'
    r = renderizar.renderizar(criar_template(kinds, css, {"k": frag}, fit=fit),
                              {"slides": [{"kind": "k", "a": "uma linha que nunca cabe em trezentos pixels"}]}, alma_neutra(), tmp_path / "s2")
    assert r["slides"][0]["encaixe"].endswith("zoom=0.8"), r["slides"][0]["encaixe"]
    assert [a for a in r["slides"][0]["avisos"] if a["tipo"] == "zoom_estoura_largura"]


def test_kind_fixo_nao_encaixa(criar_template, alma_neutra, tmp_path):
    kinds = {"k": {"vazio_ok": True, "fit": "fixo", "slots": {"a": {"tipo": "texto", "max": 30, "obrigatorio": True}}}}
    r = renderizar.renderizar(criar_template(kinds, BASE, {"k": '<div class="vis"><div><h1>{{a}}</h1></div></div>'}),
                              {"slides": [{"kind": "k", "a": "Título"}]}, alma_neutra(), tmp_path / "s")
    assert r["slides"][0]["encaixe"] == "fixo"


def test_faixa_vazia_de_22_por_cento(criar_template, alma_neutra, tmp_path):
    kinds = {"k": {"slots": {"a": {"tipo": "texto", "max": 30, "obrigatorio": True}}}}
    frag = '<h1>{{a}}</h1><div class="bloco"></div>'

    def rodape_vazio(fracao, **extra):
        altura = round(1350 * (1 - fracao))
        css = BASE + f".bloco{{position:absolute;left:0;top:0;width:300px;height:{altura}px;background:var(--alma-destaque)}}"
        k = {"k": {**kinds["k"], **extra}}
        r = renderizar.renderizar(criar_template(k, css, {"k": frag}), {"slides": [{"kind": "k", "a": "Título"}]},
                                  alma_neutra(), tmp_path / f"s{fracao}{bool(extra)}")
        return [p["detalhe"] for p in _problemas(r, "faixa_vazia")]

    vazios = rodape_vazio(0.25)
    assert vazios and vazios[0].startswith("faixa vazia no rodapé: 25% da altura sem nada (o limite é 22%")
    assert rodape_vazio(0.20) == []
    assert rodape_vazio(0.25, vazio_ok=True) == []


def test_texto_sobre_texto_fora_da_area_e_entrelinha_apertada(criar_template, alma_neutra, tmp_path):
    kinds = {"k": {"vazio_ok": True, "fit": "fixo", "slots": {"a": {"tipo": "texto", "max": 60, "obrigatorio": True}}}}
    frag = '<h1>{{a}}</h1><span class="pag">01/08</span>'
    css = BASE + "h1{line-height:.8}.pag{font-size:28px}"
    r = renderizar.renderizar(criar_template(kinds, css, {"k": frag}), {"slides": [{"kind": "k", "a": "Título com entrelinha"}]},
                              alma_neutra(), tmp_path / "s1")
    assert r["ok"], r["slides"][0]["problemas"]  # entrelinha 0,8 não é corte
    css2 = css + ".pag{position:absolute;left:80px;top:90px;font-size:60px}"
    r = renderizar.renderizar(criar_template(kinds, css2, {"k": frag}), {"slides": [{"kind": "k", "a": "Título com entrelinha"}]},
                              alma_neutra(), tmp_path / "s2")
    assert "texto sobre texto: h1 × span.pag" in [p["detalhe"] for p in _problemas(r, "texto_sobre_texto")]
    css3 = BASE + "h1{white-space:nowrap;font-size:200px}"
    r = renderizar.renderizar(criar_template(kinds, css3, {"k": "<h1>{{a}}</h1>"}), {"slides": [{"kind": "k", "a": "Título que não cabe"}]},
                              alma_neutra(), tmp_path / "s3")
    assert "h1: texto fora da área do slide" in [p["detalhe"] for p in _problemas(r, "texto_fora_da_area")]
