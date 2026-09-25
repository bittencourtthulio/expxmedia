"""T-03.06: Pexels foto e vídeo na capacidade banco_imagens (D-28), contra o stub local."""
import sys
from pathlib import Path

import pytest

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.ambiente.verificar import ErroCapacidade  # noqa: E402
from expxmedia.imagem import pexels  # noqa: E402

CHAVE = "chave-falsa-do-env-da-instalacao"

VIDEO = {
    "id": 3195394,
    "width": 1080,
    "height": 1920,
    "url": "https://www.pexels.com/video/3195394/",
    "duration": 14,
    "user": {"name": "Autora Falsa", "url": "https://www.pexels.com/@autora"},
    "video_files": [
        {"id": 1, "quality": "sd", "file_type": "video/mp4", "width": 540, "height": 960, "link": "http://x/sd.mp4"},
        {"id": 2, "quality": "hd", "file_type": "video/mp4", "width": 1080, "height": 1920, "link": "http://x/hd.mp4"},
        {"id": 3, "quality": "uhd", "file_type": "video/mp4", "width": 2160, "height": 3840, "link": "http://x/uhd.mp4"},
        {"id": 4, "quality": "hd", "file_type": "video/mp4", "width": 1920, "height": 1080, "link": "http://x/h.mp4"},
    ],
}

FOTO = {
    "id": 2014422,
    "width": 3024,
    "height": 4032,
    "url": "https://www.pexels.com/photo/2014422/",
    "photographer": "Fotógrafo Falso",
    "photographer_url": "https://www.pexels.com/@fotografo",
    "alt": "servidores num data center",
    "src": {"original": "http://x/original.jpeg", "large2x": "http://x/large2x.jpeg"},
}


@pytest.fixture
def com_chave(instalacao, monkeypatch):
    (instalacao / ".env").write_text(f"PEXELS_API_KEY={CHAVE}\n", encoding="utf-8")
    # a chave do processo nunca vale: só a do .env da instalação
    monkeypatch.setenv("PEXELS_API_KEY", "chave-do-processo-nao-pode-ir")
    return instalacao


# --- integração -------------------------------------------------------------------------

def test_video_vertical_envia_portrait_e_authorization_com_a_chave(com_chave, servidor_stub):
    servidor_stub.rota("GET", "/v1/videos/search", json={"page": 1, "per_page": 12, "videos": [VIDEO]})

    itens = pexels.buscar(com_chave, "bread oven", midia="video", orientacao="portrait",
                          url_base=servidor_stub.url)

    [req] = servidor_stub.requisicoes
    assert req.caminho == "/v1/videos/search"
    assert req.query["orientation"] == ["portrait"]
    assert req.query["query"] == ["bread oven"]
    # sem prefixo Bearer (base/api-pexels.md) e com a chave do .env, não a do processo
    assert req.cabecalhos["Authorization"] == CHAVE
    assert len(itens) == 1


def test_foto_usa_o_endpoint_de_foto(com_chave, servidor_stub):
    servidor_stub.rota("GET", "/v1/search", json={"photos": [FOTO]})
    itens = pexels.buscar(com_chave, "servers", midia="foto", orientacao="landscape", url_base=servidor_stub.url)
    [req] = servidor_stub.requisicoes
    assert req.caminho == "/v1/search"
    assert req.query["orientation"] == ["landscape"]
    assert itens[0]["midia"] == "foto"


# --- funcional --------------------------------------------------------------------------

def test_429_vira_limite_excedido_sem_nova_tentativa(com_chave, servidor_stub):
    servidor_stub.rota("GET", "/v1/videos/search", status=429, json={"error": "rate limit"})

    with pytest.raises(pexels.ErroPexels) as erro:
        pexels.buscar(com_chave, "bread", midia="video", url_base=servidor_stub.url)

    assert erro.value.codigo == "limite_excedido"
    assert len(servidor_stub.requisicoes) == 1  # nenhuma nova tentativa
    assert CHAVE not in str(erro.value)


def test_200_devolve_lista_normalizada(com_chave, servidor_stub):
    servidor_stub.rota("GET", "/v1/videos/search", json={"videos": [VIDEO]})
    servidor_stub.rota("GET", "/v1/search", json={"photos": [FOTO]})

    [video] = pexels.buscar(com_chave, "bread", midia="video", url_base=servidor_stub.url)
    # o arquivo escolhido: vertical, altura >= 720 e a mais próxima de 1920
    assert video["id"] == 3195394
    assert video["url"] == "http://x/hd.mp4"
    assert (video["largura"], video["altura"]) == (1080, 1920)
    assert video["duracao"] == 14
    assert video["autor"] == "Autora Falsa"
    assert video["pagina"] == "https://www.pexels.com/video/3195394/"
    assert video["fonte"] == "pexels"

    [foto] = pexels.buscar(com_chave, "servers", midia="foto", url_base=servidor_stub.url)
    assert foto["id"] == 2014422
    assert foto["url"] == "http://x/original.jpeg"
    assert (foto["largura"], foto["altura"]) == (3024, 4032)
    assert foto["alt"] == "servidores num data center"
    assert foto["autor"] == "Fotógrafo Falso"


def test_sem_chave_nao_chama_e_diz_como_habilitar(instalacao, servidor_stub, monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "so-no-processo")
    with pytest.raises(ErroCapacidade) as erro:
        pexels.buscar(instalacao, "bread", url_base=servidor_stub.url)
    assert "PEXELS_API_KEY" in str(erro.value)
    assert servidor_stub.requisicoes == []


def test_401_e_outros_codigos_tipados(com_chave, servidor_stub):
    servidor_stub.rota("GET", "/v1/search", status=401, json={})
    with pytest.raises(pexels.ErroPexels) as erro:
        pexels.buscar(com_chave, "x", url_base=servidor_stub.url)
    assert erro.value.codigo == "chave_recusada"


def test_parametros_invalidos_recusados_antes_de_chamar(com_chave, servidor_stub):
    with pytest.raises(ValueError):
        pexels.buscar(com_chave, "x", orientacao="diagonal", url_base=servidor_stub.url)
    with pytest.raises(ValueError):
        pexels.buscar(com_chave, "x", midia="audio", url_base=servidor_stub.url)
    with pytest.raises(ValueError):
        pexels.buscar(com_chave, "x", por_pagina=81, url_base=servidor_stub.url)
    assert servidor_stub.requisicoes == []


def test_midia_do_pexels_nunca_entra_em_template(com_chave, servidor_stub):
    servidor_stub.rota("GET", "/arquivo.mp4", corpo=b"video-falso")
    item = {"id": 1, "url": servidor_stub.url_de("/arquivo.mp4"), "midia": "video"}

    for proibido in ("galeria/templates/meu/assets/b.mp4", "templates/reel/x/assets/b.mp4"):
        with pytest.raises(pexels.ErroPexels) as erro:
            pexels.baixar(com_chave, item, proibido)
        assert erro.value.codigo == "destino_proibido"
    assert servidor_stub.requisicoes == []

    rel = pexels.baixar(com_chave, item, "pecas/2026-09/P-1/broll/01.mp4")
    assert rel == "pecas/2026-09/P-1/broll/01.mp4"
    assert (com_chave / rel).read_bytes() == b"video-falso"
