"""T-03.07: geração de imagem pelo OpenRouter (capacidade imagem_ia), contra o stub local."""
import base64
import io
import sys
from pathlib import Path

import pytest
from PIL import Image

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.ambiente.verificar import ErroCapacidade  # noqa: E402
from expxmedia.imagem import openrouter  # noqa: E402

CHAVE = "chave-falsa-openrouter-do-env"
CAMINHO = "/api/v1/chat/completions"


def _imagem(formato="PNG", tamanho=(64, 80), cor=(200, 120, 30)):
    buf = io.BytesIO()
    Image.new("RGB", tamanho, cor).save(buf, formato)
    return buf.getvalue()


def _resposta(dados: bytes, mime="image/png", texto="aqui está"):
    url = f"data:{mime};base64," + base64.b64encode(dados).decode()
    return {"choices": [{"message": {"content": texto, "images": [{"type": "image_url", "image_url": {"url": url}}]}}]}


@pytest.fixture
def com_chave(instalacao, monkeypatch):
    (instalacao / ".env").write_text(f"OPENROUTER_API_KEY={CHAVE}\n", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-do-processo-nao-pode-ir")
    return instalacao


# --- integração -------------------------------------------------------------------------

def test_requisicao_leva_modelo_configurado_e_proporcao(com_chave, servidor_stub):
    servidor_stub.rota("POST", CAMINHO, json=_resposta(_imagem()))

    openrouter.gerar(com_chave, "a loaf of sourdough bread on a wooden table, soft window light",
                     "pecas/x/imagem.png", modelo="provedor/modelo-configurado", proporcao="9:16",
                     url_base=servidor_stub.url)

    [req] = servidor_stub.requisicoes
    assert req.metodo == "POST" and req.caminho == CAMINHO
    assert req.cabecalhos["Authorization"] == f"Bearer {CHAVE}"
    corpo = req.json
    assert corpo["model"] == "provedor/modelo-configurado"
    assert corpo["image_config"]["aspect_ratio"] == "9:16"
    assert corpo["modalities"] == ["image", "text"]
    assert corpo["messages"][0]["content"][0]["text"].startswith("a loaf of sourdough")


def test_modelo_do_env_quando_nao_passado_e_padrao_sem_env(com_chave, servidor_stub):
    servidor_stub.rota("POST", CAMINHO, json=_resposta(_imagem()))
    openrouter.gerar(com_chave, "a loaf of sourdough bread on a wooden table", "pecas/a.png", url_base=servidor_stub.url)
    assert servidor_stub.requisicoes[-1].json["model"] == openrouter.MODELO_PADRAO
    assert "image_config" not in servidor_stub.requisicoes[-1].json  # sem proporção pedida, nada enviado

    (com_chave / ".env").write_text(
        f"OPENROUTER_API_KEY={CHAVE}\nOPENROUTER_MODELO_IMAGEM=outro/modelo-do-env\n", encoding="utf-8")
    openrouter.gerar(com_chave, "a loaf of sourdough bread on a wooden table", "pecas/b.png", url_base=servidor_stub.url)
    assert servidor_stub.requisicoes[-1].json["model"] == "outro/modelo-do-env"


# --- funcional --------------------------------------------------------------------------

def test_data_url_base64_vira_png_valido_no_caminho_de_saida(com_chave, servidor_stub):
    # o provedor manda JPEG: o arquivo gravado é PNG de verdade, com as mesmas dimensões
    servidor_stub.rota("POST", CAMINHO, json=_resposta(_imagem("JPEG", (90, 160)), mime="image/jpeg"))

    r = openrouter.gerar(com_chave, "a loaf of sourdough bread on a wooden table", "pecas/2026-09/P-1/img.png",
                         proporcao="9:16", url_base=servidor_stub.url)

    saida = com_chave / "pecas/2026-09/P-1/img.png"
    assert saida.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    with Image.open(saida) as img:
        img.verify()
    with Image.open(saida) as img:
        assert img.format == "PNG" and img.size == (90, 160)
    assert r["caminho"] == "pecas/2026-09/P-1/img.png"  # relativo (M9)
    assert (r["largura"], r["altura"]) == (90, 160)
    assert r["modelo"] == openrouter.MODELO_PADRAO


def test_resposta_sem_imagem_ou_invalida_nao_grava(com_chave, servidor_stub):
    servidor_stub.rota("POST", CAMINHO, json={"choices": [{"message": {"content": "não consigo"}}]})
    with pytest.raises(openrouter.ErroOpenRouter) as erro:
        openrouter.gerar(com_chave, "a loaf of sourdough bread on a wooden table", "pecas/c.png", url_base=servidor_stub.url)
    assert erro.value.codigo == "sem_imagem"

    servidor_stub.rota("POST", CAMINHO, json=_resposta(b"isto nao e imagem"))
    with pytest.raises(openrouter.ErroOpenRouter) as erro:
        openrouter.gerar(com_chave, "a loaf of sourdough bread on a wooden table", "pecas/c.png", url_base=servidor_stub.url)
    assert erro.value.codigo == "imagem_invalida"
    assert not (com_chave / "pecas/c.png").exists()


@pytest.mark.parametrize("status,codigo", [(401, "chave_recusada"), (402, "sem_credito"), (429, "limite_excedido")])
def test_erros_tipados_sem_nova_tentativa(com_chave, servidor_stub, status, codigo):
    servidor_stub.rota("POST", CAMINHO, status=status, json={"error": {"code": status, "message": "x"}})
    with pytest.raises(openrouter.ErroOpenRouter) as erro:
        openrouter.gerar(com_chave, "a loaf of sourdough bread on a wooden table", "pecas/d.png", url_base=servidor_stub.url)
    assert erro.value.codigo == codigo
    assert len(servidor_stub.requisicoes) == 1
    assert CHAVE not in str(erro.value)


def test_sem_chave_nao_chama(instalacao, servidor_stub):
    with pytest.raises(ErroCapacidade) as erro:
        openrouter.gerar(instalacao, "a loaf of sourdough bread on a wooden table", "pecas/e.png", url_base=servidor_stub.url)
    assert "OPENROUTER_API_KEY" in str(erro.value)
    assert servidor_stub.requisicoes == []


def test_base_vai_como_imagem_de_referencia(com_chave, servidor_stub):
    servidor_stub.rota("POST", CAMINHO, json=_resposta(_imagem()))
    openrouter.gerar(com_chave, "the same person, new studio portrait, 4:5", "pecas/f.png",
                     base="alma/assets/retratos/porta-voz-teste/01.png", url_base=servidor_stub.url)
    conteudo = servidor_stub.requisicoes[-1].json["messages"][0]["content"]
    assert conteudo[1]["type"] == "image_url"
    assert conteudo[1]["image_url"]["url"].startswith("data:image/png;base64,")
