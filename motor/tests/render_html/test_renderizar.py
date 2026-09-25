"""T-03.01: render HTML → PNG sem JavaScript da página e sem rede (D-20).

A página roda com JavaScript desligado; o encaixe e a medição rodam por `page.evaluate`, do lado
do Playwright, e continuam funcionando (o CDP avalia expressão mesmo com o script da página
desligado — é o que o `galeria.renderizar` de origem já fazia, `_galeria.py:1587-1589`).
Rede: só `data:`, `about:` e `blob:`. As fontes chegam como data URI a partir do cache local da
Alma (`alma.fontes`), então nem o Google Fonts é buscado pela página.
"""
from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from expxmedia.render_html import renderizar
from stubs.servidor import ServidorStub

CSS = """.slide{display:flex;flex-direction:column;padding:80px;background:var(--alma-fundo);color:var(--alma-texto);font-family:var(--alma-fonte-texto)}
h1{font-size:96px;margin:0;font-family:var(--alma-fonte-titulo)}p{font-size:40px;margin:40px 0 0}"""
CAPA = "<h1>{{titulo}}</h1><p>{{texto}}</p>"
KINDS = {"capa": {"vazio_ok": True, "fit": "fixo",
                  "slots": {"titulo": {"tipo": "texto", "max": 40, "obrigatorio": True},
                            "texto": {"tipo": "texto", "max": 80, "obrigatorio": False}}}}
COPY = {"slides": [{"kind": "capa", "titulo": "Texto original", "texto": "uma linha de apoio"}]}


def _png(caminho):
    with Image.open(caminho) as img:
        return np.asarray(img.convert("RGB")).astype(int)


def test_html_1080x1350_gera_png_com_essas_dimensoes(criar_template, alma_neutra, tmp_path):
    template = criar_template(KINDS, CSS, {"capa": CAPA})
    r = renderizar.renderizar(template, COPY, alma_neutra(), tmp_path / "saida")
    assert r["ok"], r
    with Image.open(tmp_path / "saida" / "slide_1.png") as img:
        assert img.size == (1080, 1350)
    assert r["slides"][0]["arquivo"] == "slide_1.png"


def test_canvas_vem_do_template(criar_template, alma_neutra, tmp_path):
    template = criar_template(KINDS, CSS, {"capa": CAPA}, canvas={"w": 1080, "h": 1080}, formato="1:1")
    r = renderizar.renderizar(template, COPY, alma_neutra(), tmp_path / "saida")
    assert r["ok"], r
    with Image.open(tmp_path / "saida" / "slide_1.png") as img:
        assert img.size == (1080, 1080)


def test_tokens_da_alma_pintam_o_slide(criar_template, alma_neutra, tmp_path):
    template = criar_template(KINDS, CSS, {"capa": CAPA})
    r = renderizar.renderizar(template, COPY, alma_neutra(fundo="#0b1020", texto="#ffffff"), tmp_path / "saida")
    assert r["ok"], r
    assert tuple(_png(tmp_path / "saida" / "slide_1.png")[5, 5]) == (11, 16, 32)


def test_script_da_pagina_nao_roda_e_imagem_remota_nao_e_buscada(criar_template, alma_neutra, tmp_path):
    vermelho = io.BytesIO()
    Image.new("RGB", (400, 400), (255, 0, 0)).save(vermelho, "PNG")
    limpo = renderizar.renderizar(criar_template(KINDS, CSS, {"capa": CAPA}), COPY, alma_neutra(), tmp_path / "limpo")
    assert limpo["ok"], limpo
    with ServidorStub() as stub:
        stub.rota("GET", "/foto.png", corpo=vermelho.getvalue(), cabecalhos={"Content-Type": "image/png"})
        fragmento = (CAPA
                     + "<script>document.querySelector('h1').textContent='TROCADO PELO SCRIPT DA PAGINA';"
                       "document.querySelector('.slide').style.background='#ff0000'</script>"
                     + f'<img src="{stub.url}/foto.png" alt="" style="position:absolute;left:0;top:0;width:400px;height:400px;visibility:hidden">'
                     + '<img src="https://example.com/pixel.png" alt="" style="position:absolute;left:500px;top:0;visibility:hidden">')
        r = renderizar.renderizar(criar_template(KINDS, CSS, {"capa": fragmento}), COPY, alma_neutra(), tmp_path / "sujo")
        assert stub.requisicoes == []  # a imagem remota nunca foi pedida
    tipos = [(p["tipo"], p["detalhe"]) for p in r["slides"][0]["problemas"]]
    assert ("rede_barrada", "rede barrada: o layout tentou buscar 127.0.0.1") in tipos
    assert ("rede_barrada", "rede barrada: o layout tentou buscar example.com") in tipos
    assert not r["ok"]
    # o PNG é o do texto original: igual, pixel a pixel, ao do template sem script e sem imagem
    assert np.array_equal(_png(tmp_path / "sujo" / "slide_1.png"), _png(tmp_path / "limpo" / "slide_1.png"))


def test_css_nao_busca_nem_o_google_fonts(criar_template, alma_neutra, tmp_path):
    css = CSS + ".slide{background-image:url('https://fonts.gstatic.com/s/roboto/v1/x.woff2')}"
    r = renderizar.renderizar(criar_template(KINDS, css, {"capa": CAPA}), COPY, alma_neutra(), tmp_path / "saida")
    assert "rede barrada: o layout tentou buscar fonts.gstatic.com" in [p["detalhe"] for p in r["slides"][0]["problemas"]]


def test_fonte_da_alma_vem_do_cache_local_e_carrega(criar_template, alma_neutra, tmp_path, stub_fontes_g1):
    alma = alma_neutra()
    alma["visual"]["fontes"] = {"titulo": {"familia": "Inter Tight", "origem": "google"},
                                "texto": {"familia": "Inter Tight", "origem": "google"}}
    template = criar_template(KINDS, CSS, {"capa": CAPA})
    r = renderizar.renderizar(template, COPY, alma, tmp_path / "saida", cache_fontes=tmp_path / "cache",
                              url_fontes=stub_fontes_g1.url)
    assert r["ok"], r
    assert [(f["papel"], f["familia"], f["origem"]) for f in r["fontes"]] == [("titulo", "Inter Tight", "google"),
                                                                             ("texto", "Inter Tight", "google")]
    assert r["slides"][0]["fontes_com_erro"] == []
    # a fonte baixada é outra que a reserva: o mesmo texto na Inter embarcada sai diferente
    reserva = renderizar.renderizar(template, COPY, alma_neutra(), tmp_path / "reserva")
    assert not np.array_equal(_png(tmp_path / "saida" / "slide_1.png"), _png(tmp_path / "reserva" / "slide_1.png"))


def test_fonte_fora_da_alma_reprova(criar_template, alma_neutra, tmp_path):
    css = CSS + "h1{font-family:'Fonte Qualquer', serif}"
    r = renderizar.renderizar(criar_template(KINDS, css, {"capa": CAPA}), COPY, alma_neutra(), tmp_path / "saida")
    assert [p for p in r["slides"][0]["problemas"] if p["tipo"] == "fonte_fora_da_alma"]


def test_copy_invalida_nao_abre_navegador_nem_grava(criar_template, alma_neutra, tmp_path):
    template = criar_template(KINDS, CSS, {"capa": CAPA})
    saida = tmp_path / "saida"
    r = renderizar.renderizar(template, {"slides": [{"kind": "capa", "titulo": "x" * 41, "extra": "?"}]}, alma_neutra(), saida)
    assert r["ok"] is False and r["slides"] == []
    assert any("41 caracteres, o template aguenta 40" in e for e in r["erros"])
    assert any("slot 'extra' não existe" in e for e in r["erros"])
    r = renderizar.renderizar(template, {"slides": [{"kind": "verso", "titulo": "x"}]}, alma_neutra(), saida)
    assert any("kind 'verso' não existe no template (capa)" in e for e in r["erros"])
    assert not saida.exists()


def test_modelo_ponto_em_secao_campo_ausente_e_secao_mal_fechada():
    assert renderizar.preencher("{{#sub}}<p>{{.}}</p>{{/sub}}", [{"sub": "texto"}]) == "<p>texto</p>"
    assert renderizar.preencher("{{#l}}{{@nn}}:{{.}} {{/l}}", [{"l": ["a", "b"]}]) == "01:a 02:b "
    assert renderizar.preencher("{{^x}}vazio{{/x}}", [{"x": ""}]) == "vazio"
    assert renderizar.texto_html("a *b* <c>\nd") == "a <em>b</em> &lt;c&gt;<br>d"
    with pytest.raises(ValueError):
        renderizar.conferir_modelo("{{#itens}}{{#x}}oi{{/itens}}")
    with pytest.raises(ValueError):
        renderizar.conferir_modelo("{{{cru}}}")


def test_item_de_lista_sem_campo_nao_herda_o_slot_do_slide(criar_template, alma_neutra, tmp_path):
    kinds = {"passo": {"vazio_ok": True, "slots": {
        "titulo": {"tipo": "texto", "max": 40, "obrigatorio": True},
        "itens": {"tipo": "lista", "n": [2, 3], "campos": ["nome", "titulo"], "max": 60, "obrigatorio": True}}}}
    template = criar_template(kinds, CSS, {"passo": "{{titulo}}|{{#itens}}[{{nome}}:{{titulo}}]{{/itens}}"})
    m = renderizar.carregar_template(template)
    html = renderizar.html_do_slide(m, {"slides": [{"kind": "passo", "titulo": "DO SLIDE", "itens": [{"nome": "a"}, {"nome": "b"}]}]},
                                    1, cabeca="")
    assert "DO SLIDE|[a:][b:]" in html


def test_slot_de_imagem_com_tratamento_pb(criar_template, alma_neutra, tmp_path):
    base = tmp_path / "copy"
    base.mkdir()
    Image.new("RGB", (300, 300), (200, 30, 30)).save(base / "foto.png")
    kinds = {"foto": {"vazio_ok": True, "fit": "fixo", "slots": {
        "imagem": {"tipo": "asset", "obrigatorio": True, "tratamento": {"pb": True}}}}}
    css = CSS + ".foto{position:absolute;left:0;top:0;width:300px;height:300px}"
    template = criar_template(kinds, css, {"foto": '<img class="foto" src="{{imagem}}">'})
    r = renderizar.renderizar(template, {"slides": [{"kind": "foto", "imagem": "foto.png"}]}, alma_neutra(), tmp_path / "saida",
                              base_copy=base, cache_tratadas=tmp_path / "tratadas")
    r_px = _png(tmp_path / "saida" / "slide_1.png")[150, 150]
    assert r_px[0] == r_px[1] == r_px[2]  # preto e branco
    assert list((tmp_path / "tratadas").glob("*.png"))
    # caminho que sai da pasta da copy não vira data URI
    r = renderizar.renderizar(template, {"slides": [{"kind": "foto", "imagem": "../fora.png"}]}, alma_neutra(), tmp_path / "s2",
                              base_copy=base)
    assert r["ok"] is False and any("relativo" in e for e in r["erros"])
    assert renderizar.erro_de_tratamento({"sepia": True}).startswith("`tratamento` não conhece sepia")
    assert renderizar.MODELO_RECORTE == "u2net"


def test_fonte_da_alma_que_nao_carrega_reprova(criar_template, alma_neutra, tmp_path):
    raiz = tmp_path / "instalacao"
    (raiz / "alma" / "fontes").mkdir(parents=True)
    (raiz / "alma" / "fontes" / "quebrada.woff2").write_bytes(b"isto nao e uma fonte")
    alma = alma_neutra()
    alma["visual"]["fontes"]["titulo"] = {"familia": "Quebrada", "origem": "local", "arquivo": "alma/fontes/quebrada.woff2"}
    r = renderizar.renderizar(criar_template(KINDS, CSS, {"capa": CAPA}), COPY, alma, tmp_path / "saida", raiz=raiz)
    assert "fonte 'Quebrada' não carregou" in [p["detalhe"] for p in r["slides"][0]["problemas"]]
    assert not r["ok"]


def test_sem_rede_e_sem_cache_a_fonte_google_cai_na_inter_de_ponta_a_ponta(instalacao, tmp_path):
    """Correção de T-03.01 (D-21): instalação da fixture, rede fechada, cache de fontes vazio.

    A Alma fictícia pede Fraunces e Nunito Sans do Google. Sem rede e sem cache, o render usa a
    Inter embarcada em tudo (pilha CSS, @font-face, checagem de fonte carregada), avisa
    `fonte_substituida` com a família pedida e a usada, e não reprova a peça.
    """
    from pathlib import Path

    from expxmedia.alma import carregar as alma_carregar

    alma = alma_carregar.carregar(instalacao)
    assert not alma.violacoes
    pedidas = {p: alma.dados["visual"]["fontes"][p]["familia"] for p in ("titulo", "texto")}
    assert all(alma.dados["visual"]["fontes"][p]["origem"] == "google" for p in pedidas)
    cache = tmp_path / "cache-vazio"
    cache.mkdir()
    template = Path(__file__).resolve().parents[3] / "templates" / "carrossel" / "editorial"
    r = renderizar.renderizar(template, template / "exemplo.json", alma, tmp_path / "saida", raiz=instalacao,
                              cache_fontes=cache, exemplo=True, salvar_html=True)
    problemas = [p for s in r["slides"] for p in s["problemas"]]
    assert not [p for p in problemas if p["tipo"] in ("fonte_fora_da_alma", "fonte_nao_carregou")], problemas
    assert r["ok"], problemas
    assert [(f["papel"], f["familia"], f["origem"]) for f in r["fontes"]] == [("titulo", "Inter", "embarcada"),
                                                                             ("texto", "Inter", "embarcada")]
    # aviso explícito, nunca em silêncio: família pedida e usada, por papel
    substituidas = [a for a in r["avisos"] if a["tipo"] == "fonte_substituida"]
    assert [(a["papel"], a["pedida"], a["usada"]) for a in substituidas] == [
        ("titulo", pedidas["titulo"], "Inter"), ("texto", pedidas["texto"], "Inter")]
    assert all(pedidas[a["papel"]] in a["detalhe"] and "Inter" in a["detalhe"] for a in substituidas)
    # a pilha do CSS não nomeia mais a família que não carregou
    html = (tmp_path / "saida" / "slide_1.html").read_text(encoding="utf-8")
    assert "--alma-fonte-titulo: 'Inter', sans-serif;" in html
    assert "--alma-fonte-texto: 'Inter', sans-serif;" in html
    assert all(f"'{familia}'" not in html for familia in pedidas.values())
    # nada foi gravado no cache vazio (não houve download)
    assert list(cache.iterdir()) == []
