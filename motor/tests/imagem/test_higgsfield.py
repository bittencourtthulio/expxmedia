"""T-03.08: Higgsfield pelo CLI para video_ia e rosto_ia, validando por `model get` antes (D-27)."""
import io
import json
import os
import sys
from pathlib import Path

import pytest
from PIL import Image

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs import higgsfield_falso  # noqa: E402
from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.ambiente.verificar import ErroCapacidade  # noqa: E402
from expxmedia.imagem import higgsfield  # noqa: E402


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (48, 64), (90, 60, 30)).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def falso(tmp_path, monkeypatch, servidor_stub):
    """higgsfield falso no começo do PATH, com o resultado servido pelo stub."""
    pasta = tmp_path / "bin"
    higgsfield_falso.instalar(pasta)
    log = tmp_path / "higgsfield.log"
    monkeypatch.setenv("PATH", str(pasta) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("HIGGSFIELD_FALSO_LOG", str(log))
    monkeypatch.setenv("HIGGSFIELD_FALSO_URL", servidor_stub.url)
    servidor_stub.rota("GET", "/resultado.mp4", corpo=b"mp4-falso")
    servidor_stub.rota("GET", "/resultado.png", corpo=_png())
    return log


def _subcomandos(log):
    return [" ".join(c[:2]) for c in higgsfield_falso.chamadas(log)]


# --- integração -------------------------------------------------------------------------

def test_video_ia_chama_model_get_antes_de_generate(instalacao, falso):
    r = higgsfield.gerar_video(instalacao, "a loaf of bread rising in a warm oven", "pecas/x/abertura.mp4")

    ordem = _subcomandos(falso)
    assert "model get" in ordem and "generate create" in ordem
    assert ordem.index("model get") < ordem.index("generate create")
    get = next(c for c in higgsfield_falso.chamadas(falso) if c[:2] == ["model", "get"])
    create = next(c for c in higgsfield_falso.chamadas(falso) if c[:2] == ["generate", "create"])
    assert get[2] == create[2] == higgsfield.MODELO_VIDEO
    assert "--json" in get and "--json" in create and "--wait" in create
    # padrões da origem que o esquema aceita, e sem áudio gerado
    texto = " ".join(create)
    assert "--aspect-ratio 9:16" in texto and "--duration 4" in texto and "--mode std" in texto
    assert "--generate-audio false" in texto

    assert (instalacao / "pecas/x/abertura.mp4").read_bytes() == b"mp4-falso"
    assert r["caminho"] == "pecas/x/abertura.mp4"
    assert r["job"] == "job-falso-0001"
    assert "http" not in json.dumps(r)  # a URL assinada não sai em lugar nenhum


# --- funcional --------------------------------------------------------------------------

def test_parametro_ausente_do_esquema_e_recusado_antes_de_gerar(instalacao, falso):
    with pytest.raises(higgsfield.ErroHiggsfield) as erro:
        higgsfield.gerar_video(instalacao, "a loaf of bread rising", "pecas/y.mp4",
                               parametros={"cfg_scale": 7})
    assert erro.value.codigo == "parametro_fora_do_esquema"
    assert "cfg_scale" in str(erro.value)
    assert "generate create" not in _subcomandos(falso)
    assert not (instalacao / "pecas/y.mp4").exists()


def test_valor_fora_do_enum_e_recusado_antes_de_gerar(instalacao, falso):
    with pytest.raises(higgsfield.ErroHiggsfield) as erro:
        higgsfield.gerar_video(instalacao, "a loaf of bread rising", "pecas/y.mp4",
                               parametros={"resolution": "8k"})
    assert erro.value.codigo == "valor_fora_do_esquema"
    assert "generate create" not in _subcomandos(falso)


def test_outro_modelo_descarta_padrao_que_o_esquema_nao_aceita(instalacao, falso):
    higgsfield.gerar_video(instalacao, "a loaf of bread rising", "pecas/z.mp4", modelo="seedance_2_5",
                           parametros={"mode": "t2v"})
    create = next(c for c in higgsfield_falso.chamadas(falso) if c[:2] == ["generate", "create"])
    assert create[2] == "seedance_2_5"
    assert "std" not in create and "t2v" in create


def test_rosto_ia_usa_o_id_do_porta_voz_da_alma(instalacao, falso):
    alma = json.loads((instalacao / "alma/alma.json").read_text(encoding="utf-8"))
    alma["porta_vozes"][0]["rosto_ia"]["id"] = "soul-ficticio-123"
    (instalacao / "alma/alma.json").write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")

    r = higgsfield.gerar_rosto(instalacao, "porta-voz-teste", "standing behind a bakery counter", "pecas/r/rosto.png")

    create = next(c for c in higgsfield_falso.chamadas(falso) if c[:2] == ["generate", "create"])
    assert create[2] == higgsfield.MODELO_ROSTO
    i = create.index("--custom-reference-id")
    assert create[i + 1] == "soul-ficticio-123"
    prompt = create[create.index("--prompt") + 1]
    assert prompt.startswith(higgsfield.PREAMBULO_ROSTO) and len(prompt) <= 900
    with Image.open(instalacao / "pecas/r/rosto.png") as img:
        assert img.format == "PNG"
    assert r["porta_voz"] == "porta-voz-teste"


def test_rosto_ia_sem_id_na_alma_nao_chama_o_cli(instalacao, falso):
    with pytest.raises(ErroCapacidade) as erro:
        higgsfield.gerar_rosto(instalacao, "porta-voz-teste", "standing behind a counter", "pecas/r.png")
    assert "rosto_ia" in str(erro.value)
    assert "generate create" not in _subcomandos(falso)


def test_sem_login_desliga_a_capacidade(instalacao, falso, monkeypatch):
    monkeypatch.setenv("HIGGSFIELD_FALSO_SEM_LOGIN", "1")
    with pytest.raises(ErroCapacidade) as erro:
        higgsfield.gerar_video(instalacao, "a loaf of bread rising", "pecas/y.mp4")
    assert "higgsfield auth login" in str(erro.value)
    assert _subcomandos(falso) == ["account status"]


def test_validar_parametros_direto():
    esquema = higgsfield_falso.ESQUEMAS["text2image_soul_v2"]
    assert higgsfield.validar_parametros(esquema, {"prompt": "x", "aspect-ratio": "3:4"}) == {
        "prompt": "x", "aspect_ratio": "3:4"}
    with pytest.raises(higgsfield.ErroHiggsfield) as erro:
        higgsfield.validar_parametros(esquema, {"aspect_ratio": "3:4"})
    assert erro.value.codigo == "parametro_obrigatorio"
