"""T-03.09: captura de página com Playwright headless próprio (D-25), contra páginas do stub local.

As páginas de teste têm geometria fixa (seções de altura conhecida, corpo sem margem), para que
a posição de cada título e a altura da tira sejam números exatos, e não "mais ou menos".
"""
from __future__ import annotations

import json

import numpy as np
import pytest
from PIL import Image

from expxmedia.captura import pagina
from stubs.servidor import ServidorStub

PARAGRAFO = (
    "Este parágrafo existe para dar corpo de texto à página de teste, com frases comuns e sem "
    "nenhuma marca, de modo que o texto renderizado passe com folga do piso de caracteres. "
)
BASE_CSS = ("html,body{margin:0;padding:0;background:#ffffff;color:#111111;font:16px/1.4 sans-serif}"
            "section{height:1000px;overflow:hidden;margin:0;padding:0}"
            "h1,h2,h3{margin:0;padding:0;height:60px}p{margin:0}")


def _html(corpo: str, css: str = "") -> bytes:
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>Página de teste</title>"
            f"<style>{BASE_CSS}{css}</style></head><body>{corpo}</body></html>").encode("utf-8")


def _pagina_3000(banner: bool = True) -> bytes:
    cookie = ("<div id='cookie-consent' style='height:300px;background:#ff0000'>"
              "Aceitar cookies deste site</div>") if banner else ""
    chat = "<div id='chat-widget-x' style='position:fixed;right:0;bottom:0;width:200px;height:200px;background:#ff0000'>Fale conosco</div>"
    return _html(
        cookie
        + "<section><h1>Título principal da página</h1>" + f"<p>{PARAGRAFO * 4}</p></section>"
        + "<section><h2>Segunda seção do conteúdo</h2>" + f"<p>{PARAGRAFO * 4}</p></section>"
        # marcador verde entre 2500 e 2600 CSS px: prova que as faixas foram costuradas na ordem
        + "<section><h3>Terceira parte</h3>" + f"<p>{PARAGRAFO * 4}</p>"
        + "<div style='position:relative;top:340px;height:100px;background:#00c000'></div></section>"
        + chat
    )


@pytest.fixture
def servidor():
    with ServidorStub() as stub:
        yield stub


def _servir(stub: ServidorStub, caminho: str, html: bytes) -> str:
    stub.rota("GET", caminho, corpo=html, cabecalhos={"Content-Type": "text/html; charset=utf-8"})
    return stub.url_de(caminho)


def _vermelhos(caminho) -> int:
    with Image.open(caminho) as img:
        px = np.asarray(img.convert("RGB")).astype(int)
    return int(((px[..., 0] > 200) & (px[..., 1] < 60) & (px[..., 2] < 60)).sum())


# ---------------------------------------------------------------- integração


def test_captura_esconde_cookie_gera_site_md_e_secoes_com_y(servidor, tmp_path):
    url = _servir(servidor, "/pagina", _pagina_3000())
    saida = tmp_path / "captura"
    r = pagina.capturar(url, saida)

    # banner de cookie e widget de chat não aparecem na tira nem no texto
    assert (saida / "tira.png").is_file()
    assert _vermelhos(saida / "tira.png") == 0
    assert r["ocultos"]["consentimento"] >= 1 and r["ocultos"]["overlays"] >= 1
    site = (saida / "site.md").read_text(encoding="utf-8")
    assert "Aceitar cookies" not in site and "Fale conosco" not in site
    # o texto do corpo, renderizado do DOM
    assert site.startswith("# Página de teste\n")
    assert f"Fonte: {url}" in site
    assert "Segunda seção do conteúdo" in site and PARAGRAFO.strip()[:60] in site
    assert len(site) >= pagina.MIN_CHARS_SITE and r["site_chars"] > 1200

    # seções h1–h3 com o y de cada uma (o banner escondido não empurra nada para baixo)
    assert r["secoes"] == [
        {"t": "Título principal da página", "y": 0},
        {"t": "Segunda seção do conteúdo", "y": 1000},
        {"t": "Terceira parte", "y": 2000},
    ]
    # tira na largura do vídeo: 3000 CSS px × (1080 / 700)
    with Image.open(saida / "tira.png") as img:
        assert img.size == (1080, round(3000 * 1080 / 700))
    assert r["altura_css"] == 3000 and r["cortada"] is False
    with Image.open(saida / "chunks" / "000.png") as faixa:
        assert faixa.size == (700 * 2, 1100 * 2)  # faixa de 1100 CSS px na escala 2: texto nítido antes da redução
    assert r["chunks"] == 3 and sorted(p.name for p in (saida / "chunks").iterdir()) == ["000.png", "001.png", "002.png"]
    gravado = json.loads((saida / "captura.json").read_text(encoding="utf-8"))
    assert list(gravado)[0] == "expxmedia_captura"
    assert gravado["secoes"] == r["secoes"] and gravado["tira"] == "tira.png" and gravado["site_md"] == "site.md"
    assert gravado["strip_h"] == round(3000 * 1080 / 700) and gravado["px_por_css"] == pytest.approx(1080 / 700, rel=1e-3)


def test_sem_esconder_o_banner_ele_apareceria(servidor, tmp_path):
    """Controle do teste acima: o mesmo bloco vermelho sem id de consentimento aparece na tira."""
    html = _pagina_3000(banner=False).replace(b"<body>", b"<body><div style='height:300px;background:#ff0000'>faixa</div>")
    url = _servir(servidor, "/controle", html)
    pagina.capturar(url, tmp_path / "controle")
    assert _vermelhos(tmp_path / "controle" / "tira.png") > 100_000


# ---------------------------------------------------------------- funcional


def test_tira_de_pagina_de_3000_px_tem_3000_px_costurada_na_ordem(servidor, tmp_path):
    url = _servir(servidor, "/tres-mil", _pagina_3000(banner=False))
    saida = tmp_path / "um-para-um"
    r = pagina.capturar(url, saida, largura_css=1080, escala=1, largura_final=1080)
    with Image.open(saida / "tira.png") as img:
        assert img.size == (1080, 3000)
        px = np.asarray(img.convert("RGB")).astype(int)
    assert r["altura_css"] == 3000 and r["strip_h"] == 3000
    # o marcador verde (100 CSS px) mora na terceira seção, que começa em 2000 e cai na 2ª/3ª faixa
    verdes = np.where((px[:, 540, 1] > 150) & (px[:, 540, 0] < 60) & (px[:, 540, 2] < 60))[0]
    assert len(verdes) == 100
    assert 2000 < verdes[0] < 3000 and verdes[-1] - verdes[0] == 99  # contínuo: faixas sem buraco nem sobra


def test_pagina_com_menos_de_1200_caracteres_da_erro_de_conteudo_insuficiente(servidor, tmp_path):
    curta = _html("<section><h1>Pouco texto</h1><p>Só uma frase.</p></section>" * 2)
    url = _servir(servidor, "/rala", curta)
    with pytest.raises(pagina.ErroConteudoInsuficiente) as erro:
        pagina.capturar(url, tmp_path / "rala")
    assert "1200" in str(erro.value) and "caracteres" in str(erro.value)
    assert not (tmp_path / "rala" / "tira.png").exists()


def test_pagina_que_rola_menos_de_1600_px_e_recusada(servidor, tmp_path):
    url = _servir(servidor, "/curta", _html(f"<section><h1>Uma tela</h1><p>{PARAGRAFO * 12}</p></section>"))
    with pytest.raises(pagina.ErroPaginaCurta) as erro:
        pagina.capturar(url, tmp_path / "curta")
    assert "rola só 1200 CSS px" in str(erro.value) and "1600" in str(erro.value)
