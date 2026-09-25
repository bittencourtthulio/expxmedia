"""T-05.09: palco HTML da apresentação, autocontido e navegável por teclado.

- Integração: o HTML gerado, aberto no Chromium do Playwright, avança do slide 1 para o 2 com a seta
  direita (e volta com a esquerda, vai ao fim com End), sem pedir nada à rede e com as fontes da Alma
  carregadas.
- Funcional: o HTML não referencia nenhuma URL externa, traz as variáveis --alma-* da Alma e as fontes
  embutidas, e o CTA sai da Alma (nada de CTA fixo).
"""
from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path

import pytest

from expxmedia.alma import carregar as alma_carregar
from expxmedia.producao.apresentacao import deck as _deck
from expxmedia.producao.apresentacao import palco
from fixtures.fontes_ficticias import semear_cache

G6 = Path(__file__).resolve().parents[2] / "golden" / "G6" / "deck.json"
RE_URL_EXTERNA = re.compile(r"(?:https?:)?//[a-z0-9.-]+\.[a-z]{2,}", re.I)


def _png(caminho: Path, cor=(90, 120, 200), w=64, h=36) -> Path:
    linha = b"\x00" + bytes(cor) * w
    bruto = zlib.compress(linha * h)

    def bloco(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)

    caminho.write_bytes(b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                        + bloco(b"IDAT", bruto) + bloco(b"IEND", b""))
    return caminho


@pytest.fixture
def cenario(instalacao, tmp_path):
    alma = alma_carregar.carregar(instalacao)
    d = _deck.de_origem(json.loads(G6.read_text(encoding="utf-8")))
    d["tema"]["cor"] = None  # a cor do tema da origem não passa no contraste sobre o fundo claro da Alma fictícia
    ativos = tmp_path / "ativos"
    ativos.mkdir()
    _png(ativos / "logo.png")
    _png(ativos / "print.png")  # expxplay.png fica de fora: o CTA sai sem imagem, com aviso
    cache = semear_cache(tmp_path / "fontes")
    saida = tmp_path / "saida" / "apresentacao.html"
    r = palco.gerar(d, alma, saida, raiz=instalacao, ativos=ativos, cache_fontes=cache)
    return {"alma": alma, "deck": d, "r": r, "html": saida.read_text(encoding="utf-8"), "saida": saida, "tmp": tmp_path}


# ---------------------------------------------------------------- integração


@pytest.mark.integracao_local
def test_seta_direita_avanca_do_slide_1_para_o_2(cenario):
    from playwright.sync_api import sync_playwright

    pedidos: list[str] = []
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            pagina = navegador.new_page(viewport={"width": 1280, "height": 720})
            pagina.on("request", lambda req: pedidos.append(req.url))
            pagina.goto(cenario["saida"].resolve().as_uri())
            pagina.wait_for_function("document.fonts.status === 'loaded'")
            assert pagina.locator("#contador").inner_text() == "01 / 09"
            assert pagina.locator("#slide-1").is_visible() and not pagina.locator("#slide-2").is_visible()

            pagina.keyboard.press("ArrowRight")
            assert pagina.locator("#contador").inner_text() == "02 / 09"
            assert pagina.locator("#palco").get_attribute("data-atual") == "2"
            assert pagina.locator("#slide-2").is_visible() and not pagina.locator("#slide-1").is_visible()
            assert pagina.locator("#slide-2").get_attribute("data-tipo") == "declaracao"

            pagina.keyboard.press("ArrowLeft")
            assert pagina.locator("#contador").inner_text() == "01 / 09"
            pagina.keyboard.press("End")
            assert pagina.locator("#contador").inner_text() == "09 / 09"
            assert pagina.locator("#slide-9").get_attribute("data-tipo") == "cta"
            pagina.keyboard.press("ArrowRight")  # no último slide a seta não passa do fim
            assert pagina.locator("#contador").inner_text() == "09 / 09"
            assert pagina.url.endswith("#9")

            # as famílias da Alma estão carregadas (embutidas), não a genérica do sistema
            for familia in ("Fraunces", "Nunito Sans"):
                assert pagina.evaluate(f"document.fonts.check('40px \"{familia}\"')"), familia
            assert pagina.evaluate("[...document.fonts].filter(f => f.status === 'loaded').length") >= 2
        finally:
            navegador.close()
    externos = [u for u in pedidos if not u.startswith(("file:", "data:"))]
    assert externos == [], externos


@pytest.mark.integracao_local
def test_hash_abre_no_slide_pedido(cenario):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            pagina = navegador.new_page(viewport={"width": 960, "height": 540})
            pagina.goto(cenario["saida"].resolve().as_uri() + "#7")
            assert pagina.locator("#contador").inner_text() == "07 / 09"
            assert pagina.locator("#slide-7").get_attribute("data-tipo") == "fluxo"
            pagina.keyboard.press("Home")
            assert pagina.locator("#contador").inner_text() == "01 / 09"
            pagina.screenshot(path=str(cenario["tmp"] / "palco.png"))
        finally:
            navegador.close()


# ---------------------------------------------------------------- funcional


def test_html_sem_url_externa_e_com_tokens_da_alma(cenario):
    html = cenario["html"]
    assert RE_URL_EXTERNA.findall(html) == []
    assert not re.search(r"""(?:src|href)\s*=\s*["'](?!data:|#)""", html, re.I), "todo src/href é data URI"
    assert not re.search(r"url\(\s*(?!['\"]?(?:data:|%23))", html), "todo url() é data URI (ou referência interna do SVG)"
    assert "file:" not in html
    cores = cenario["alma"].dados["visual"]["cores"]
    for papel, valor in cores.items():
        assert f"--alma-{papel}: {valor};" in html, papel
    assert "--alma-fonte-titulo: 'Fraunces'" in html and "--alma-fonte-texto: 'Nunito Sans'" in html
    assert html.count("src: url('data:font/woff2;base64,") >= 2
    # nenhuma cor literal no desenho dos slides: só tokens (a da Alma entra pelas variáveis)
    estilo = html.split("</style>")[0].split("/* Palco da apresentação")[1]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", estilo)


def test_nove_slides_um_por_tipo_na_ordem_do_deck(cenario):
    html = cenario["html"]
    assert re.findall(r'<section class="slide t-(\w+)" id="slide-(\d+)"', html) == [
        (s["tipo"], str(i)) for i, s in enumerate(cenario["deck"]["slides"], 1)]
    assert "01 / 09" in html and cenario["r"]["slides"] == 9


def test_cta_vem_da_alma_e_imagem_ausente_vira_aviso(cenario):
    html, alma = cenario["html"], cenario["alma"].dados
    cta = html.split('id="slide-9"')[1]
    assert "trigodourado.example/encomenda" in cta  # cta.destino da Alma, sem esquema
    assert alma["empresa"]["nome_curto"] in cta  # cartaz sem imagem e cabeçalho com o nome da casa
    assert "<img" not in cta
    assert any("expxplay.png" in a for a in cenario["r"]["avisos"])
    # a imagem presente entra embutida
    assert '<img src="data:image/png;base64,' in html.split('id="slide-8"')[1].split("</section>")[0]


def test_palavras_em_b_viram_destaque_e_titulo_tem_teto(cenario):
    titulo = cenario["html"].split('id="slide-1"')[1].split("</section>")[0]
    # "Claude Code ficou <b>caro</b>?": 4ª palavra no quadro 8 + 3 x 3; o "?" fora do <b> é outra palavra (WordReveal)
    assert '<span class="p b" style="--d:17">caro</span><span class="p" style="--d:20">?</span>' in titulo
    assert 'data-teto="138"' in titulo


def test_cor_do_tema_troca_so_o_destaque(cenario, instalacao, tmp_path):
    d = dict(cenario["deck"], tema={**cenario["deck"]["tema"], "cor": "#D57855"})
    html, _, _ = palco.html_palco(d, cenario["alma"], raiz=instalacao, cache_fontes=semear_cache(tmp_path / "f"))
    assert ":root { --cor-destaque: #D57855;" in html
    assert "--cor-casa: var(--alma-destaque);" in html  # o CTA continua na cor da casa


def test_deck_invalido_nao_gera_palco(cenario, instalacao, tmp_path):
    d = dict(cenario["deck"], tema={**cenario["deck"]["tema"], "cor": "#D97757"})  # 2,96:1 sobre o fundo da Alma
    with pytest.raises(palco.ErroDeck) as erro:
        palco.gerar(d, cenario["alma"], tmp_path / "x.html", raiz=instalacao)
    assert [a["campo"] for a in erro.value.achados] == ["tema.cor"]
    assert not (tmp_path / "x.html").exists()


def test_geometria_do_fluxo_e_a_da_origem():
    caixas, altura = palco._caixas(5)  # 5 nós: duas linhas de 3 colunas
    assert [c["linha"] for c in caixas] == [0, 0, 0, 1, 1]
    assert caixas[0]["h"] == 200 and altura == 2 * 200 + 120
    assert caixas[1]["x"] == pytest.approx((1728 - 96 * 2) / 3 + 96)
    caixas4, altura4 = palco._caixas(4)
    assert {c["linha"] for c in caixas4} == {0} and altura4 == 230
