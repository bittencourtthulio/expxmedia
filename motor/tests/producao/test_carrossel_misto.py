"""T-05.07: carrossel misto — slide de vídeo renderizado em Remotion no formato do carrossel (D-06).

Integração: um carrossel com o slide 1 de vídeo (composição SlideVideo do kit) e os slides 2 e 3 de imagem
(template embarcado editorial) gera `slides/slide_01.mp4` em 4:5 (1080x1350) e dois PNGs, com a prancha.
Funcional: a peça registra `slides[0]` com `midia: video` e `duracao_s` preenchida (a do MP4) e os de
imagem com `duracao_s: null`; slot inválido do slide de vídeo é erro antes de qualquer render; carrossel
só de imagem segue pelo caminho estático.
"""
from __future__ import annotations

import pytest
from PIL import Image

from expxmedia.nucleo import rastro, tempo
from expxmedia.peca import modelo
from expxmedia.producao import carrossel
from expxmedia.video import ffmpeg
from fixtures.fontes_ficticias import semear_cache

TEMPLATE = "carrossel-editorial-b74228"
ROTULOS = ["Série", "Método", "Prática"]


def _entrada(video=None):
    return {
        "template": TEMPLATE,
        "titulo": "Sem atalho em movimento",
        "slides": [
            video or {"kind": "abertura", "midia": "video", "etiqueta": "Série", "titulo": "Sem atalho, com método",
                      "texto": "Três slides sobre fazer bem feito.", "duracao_s": 4},
            {"kind": "conteudo", "rotulos": ROTULOS, "palavra": "Tempo", "destaque": "Fermentação longa cria sabor.",
             "texto": "Doze horas de descanso fazem o que nenhum aditivo faz.", "rodape": "perfil da empresa"},
            {"kind": "cta", "rotulos": ROTULOS, "col_esq": "Fazer rápido não é fazer bem.",
             "col_dir": "Salve para a próxima vez.", "rodape": "perfil da empresa"},
        ],
        "legenda": "Sem atalho.\n\nUm vídeo e dois slides. Salve.",
    }


@pytest.fixture
def cache(tmp_path):
    return semear_cache(tmp_path / "fontes")


@pytest.mark.integracao_local
def test_slide_1_de_video_e_2_de_imagem(instalacao, cache, requer_binario):
    for b in ("node", "ffmpeg", "ffprobe"):
        requer_binario(b)
    r = carrossel.produzir(instalacao, _entrada(), cache_fontes=cache)
    assert r["status"] == "produzida"
    pasta = modelo.pasta(instalacao, r["peca_id"])
    video = pasta / "slides" / "slide_01.mp4"
    s = ffmpeg.sondar(video)
    assert (s["largura"], s["altura"]) == (1080, 1350)  # 4:5, o formato do carrossel
    assert "h264" in s["codecs"] and s["fps"] == "30/1"
    assert abs(s["duracao"] - 4) < 0.1
    pngs = sorted(p.name for p in (pasta / "slides").glob("*.png"))
    assert pngs == ["slide_02.png", "slide_03.png"]
    for nome in pngs:
        with Image.open(pasta / "slides" / nome) as img:
            assert img.size == (1080, 1350)
    assert not (pasta / "slides" / "slide_01.png").exists()
    with Image.open(pasta / "previa" / "prancha.png") as prancha:
        assert prancha.width > 3 * 432  # três miniaturas lado a lado, o vídeo por um quadro dele

    # funcional: a peça registra a mídia de cada slide
    peca = modelo.carregar(instalacao, r["peca_id"])
    s0, s1, s2 = peca["slides"]
    assert (s0["n"], s0["midia"], s0["arquivo"]) == (1, "video", "slides/slide_01.mp4")
    assert isinstance(s0["duracao_s"], float) and abs(s0["duracao_s"] - 4) < 0.1
    assert (s1["n"], s1["midia"], s1["duracao_s"], s1["arquivo"]) == (2, "imagem", None, "slides/slide_02.png")
    assert (s2["n"], s2["midia"], s2["duracao_s"]) == (3, "imagem", None)
    papeis = {a["caminho"]: (a["papel"], a["formato"]) for a in peca["arquivos"]}
    assert papeis["slides/slide_01.mp4"] == ("slide", "4:5") and papeis["slides/slide_02.png"] == ("slide", "4:5")
    assert papeis["texto/legenda.txt"][0] == "legenda" and papeis["previa/prancha.png"][0] == "previa"
    assert peca["producao"]["provedores"] == {"renderizar_html": "playwright", "renderizar_motion": "remotion"}
    assert not (pasta / ".render").exists()


def test_slot_invalido_do_slide_de_video_e_erro_antes_do_render(instalacao, cache):
    sem_titulo = {"kind": "abertura", "midia": "video", "etiqueta": "Série"}
    with pytest.raises(carrossel.ErroSlots, match="slide 1 \\(abertura\\), slot 'titulo': obrigatório"):
        carrossel.produzir(instalacao, _entrada(sem_titulo), cache_fontes=cache)
    longa = {"kind": "abertura", "midia": "video", "titulo": "curto", "duracao_s": 120}
    with pytest.raises(carrossel.ErroSlots, match="duracao_s de 3 a 60 s"):
        carrossel.produzir(instalacao, _entrada(longa), cache_fontes=cache)
    desconhecido = {"kind": "abertura", "midia": "video", "titulo": "curto", "cor": "azul"}
    with pytest.raises(carrossel.ErroSlots, match="slot 'cor' não existe"):
        carrossel.produzir(instalacao, _entrada(desconhecido), cache_fontes=cache)
    assert list((instalacao / "pecas").rglob("peca.json")) == []
    eventos, _ = rastro.ler(instalacao, tempo.agora(instalacao).strftime("%Y-%m"))
    assert eventos == []


def test_kind_de_video_do_template_vai_para_o_misto(monkeypatch, instalacao):
    chamado = {}
    monkeypatch.setattr(carrossel, "_produzir_misto", lambda raiz, dados, **o: chamado.setdefault("misto", True))
    monkeypatch.setattr(carrossel, "produzir_estatico", lambda raiz, dados, **o: chamado.setdefault("estatico", True))
    carrossel.produzir(instalacao, _entrada())
    assert chamado == {"misto": True}
    chamado.clear()
    so_imagem = _entrada()
    so_imagem["slides"] = so_imagem["slides"][1:]
    carrossel.produzir(instalacao, so_imagem)
    assert chamado == {"estatico": True}
