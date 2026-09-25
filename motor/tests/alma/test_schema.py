"""T-02.09: schema da Alma (CONTRATO-alma, D-22, D-40, M2, M7)."""
import copy
import json
from pathlib import Path

import pytest

from expxmedia.alma import schema

ALMA_FICTICIA = Path(__file__).resolve().parents[1] / "fixtures" / "alma-ficticia" / "alma" / "alma.json"
GOLDEN = Path(__file__).resolve().parents[1] / "golden"


@pytest.fixture
def alma():
    return json.loads(ALMA_FICTICIA.read_text(encoding="utf-8"))


def _tipos_e_caminhos(violacoes):
    return {(v["tipo"], v["caminho"]) for v in violacoes}


# ---------------------------------------------------------------- integração


def test_alma_ficticia_valida_e_exercita_voz_por_tipo_e_pronuncia(alma):
    assert schema.validar(alma) == []
    voz = alma["porta_vozes"][0]["voz"]
    assert set(voz["parametros"]) == {"reel", "aula", "padrao"}
    assert voz["parametros"]["reel"]["ritmo_min_pps"] > 0
    assert voz["parametros"]["aula"]["timeout_s"] > 0
    # léxico com pelo menos um termo de várias palavras
    assert any(" " in item["termo"] for item in voz["pronuncia"])


def test_schema_aceita_parametros_reel_aula_e_pronuncia(alma):
    voz = alma["porta_vozes"][0]["voz"]
    voz["parametros"]["reel"] = dict(schema.PARAMETROS_VOZ_PADRAO["reel"])
    voz["parametros"]["aula"] = dict(schema.PARAMETROS_VOZ_PADRAO["aula"])
    voz["parametros"]["padrao"] = dict(schema.PARAMETROS_VOZ_PADRAO["padrao"])
    voz["pronuncia"] = [{"termo": "software house", "fala": "sóftwer ráuse"}, {"termo": "hooks", "fala": "rúks"}]
    assert schema.validar(alma) == []


def test_goldens_de_alma_validam():
    for arquivo in (GOLDEN / "G1" / "alma-golden.json", GOLDEN / "G4" / "alma-golden-reel.json"):
        assert schema.validar(json.loads(arquivo.read_text(encoding="utf-8"))) == [], arquivo.name


def test_padroes_de_voz_sao_os_da_origem():
    """Números calibrados da origem (D-22, D-40): trocar qualquer um tem de quebrar este teste."""
    reel = schema.PARAMETROS_VOZ_PADRAO["reel"]
    assert reel == {
        "stability": 0.45,
        "similarity_boost": 0.8,
        "style": 0.25,
        "use_speaker_boost": True,
        "speed": 1.2,
        "ritmo_min_pps": 3.47,
    }
    # piso derivado na origem: RITMO_APROVADO 3.18 * SPEED_PADRAO 1.2 / SPEED_APROVADO 1.1
    assert reel["ritmo_min_pps"] == round(3.18 * 1.2 / 1.1, 2)
    aula = schema.PARAMETROS_VOZ_PADRAO["aula"]
    assert aula == {
        "stability": 0.5,
        "similarity_boost": 0.85,
        "style": 0.15,
        "use_speaker_boost": True,
        "speed": 0.94,
        "timeout_s": 300,
    }
    assert "ritmo_min_pps" not in aula  # D-40: ritmo mínimo só no reel
    assert "ritmo_min_pps" not in schema.PARAMETROS_VOZ_PADRAO["padrao"]
    assert schema.MODELO_VOZ_PADRAO == "eleven_multilingual_v2"


def test_schema_json_e_o_arquivo_publicado():
    publicado = json.loads((Path(schema.__file__).parent / "alma.schema.json").read_text(encoding="utf-8"))
    assert schema.carregar_schema() == publicado


# ---------------------------------------------------------------- funcional


def test_sem_destaque_devolve_chave_omitida_com_caminho(alma):
    del alma["visual"]["cores"]["destaque"]
    violacoes = schema.validar(alma)
    assert ("chave_omitida", "visual.cores.destaque") in _tipos_e_caminhos(violacoes)
    assert len(violacoes) == 1


@pytest.mark.parametrize(
    "caminho",
    [
        ("porta_vozes", 0, "voz", "modelo"),
        ("porta_vozes", 0, "voz", "pronuncia"),
        ("porta_vozes", 0, "voz", "parametros", "aula"),
        ("porta_vozes", 0, "voz", "parametros", "reel", "ritmo_min_pps"),
        ("porta_vozes", 0, "voz", "parametros", "aula", "timeout_s"),
        ("confirmada_em",),
        ("empresa", "fuso"),
    ],
)
def test_chave_omitida_em_campos_aninhados(alma, caminho):
    alvo = alma
    for parte in caminho[:-1]:
        alvo = alvo[parte]
    del alvo[caminho[-1]]
    texto = "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in caminho).lstrip(".")
    assert _tipos_e_caminhos(schema.validar(alma)) == {("chave_omitida", texto)}


def test_valores_fora_do_contrato(alma):
    ruim = copy.deepcopy(alma)
    ruim["metodo"] = "Site"
    ruim["visual"]["cores"]["fundo"] = "bege"
    ruim["porta_vozes"][0]["voz"]["parametros"]["reel"]["speed"] = 1.3  # API recusa acima de 1.2
    ruim["porta_vozes"][0]["voz"]["pronuncia"] = [{"termo": "", "fala": "x"}]
    ruim["canais"][0]["canal"] = 3
    caminhos = _tipos_e_caminhos(schema.validar(ruim))
    assert ("valor_invalido", "metodo") in caminhos
    assert ("valor_invalido", "visual.cores.fundo") in caminhos
    assert ("valor_invalido", "porta_vozes[0].voz.parametros.reel.speed") in caminhos
    assert ("valor_invalido", "porta_vozes[0].voz.pronuncia[0].termo") in caminhos
    assert ("tipo_invalido", "canais[0].canal") in caminhos


def test_nulo_e_ausente_sao_diferentes(alma):
    alma["visual"]["cores"]["destaque"] = None  # campo sem evidência (regra 3): é null, não violação
    assert schema.validar(alma) == []


def test_versao_maior_ou_ausente_e_rejeitada(alma):
    alma["expxmedia_alma"] = 2
    with pytest.raises(schema.ErroAlmaRejeitada, match="versão 2"):
        schema.validar(alma)
    del alma["expxmedia_alma"]
    with pytest.raises(schema.ErroAlmaRejeitada, match="expxmedia_alma"):
        schema.validar(alma)
    with pytest.raises(schema.ErroAlmaRejeitada):
        schema.validar(["não", "é", "objeto"])


def test_exemplo_do_contrato_valida():
    contrato = Path(__file__).resolve().parents[3] / "docs" / "contrato" / "CONTRATO-alma.md"
    texto = contrato.read_text(encoding="utf-8")
    bloco = texto.split("```json", 1)[1].split("```", 1)[0]
    exemplo = json.loads(bloco)
    assert schema.validar(exemplo) == []
    assert exemplo["porta_vozes"][0]["voz"]["parametros"]["reel"] == schema.PARAMETROS_VOZ_PADRAO["reel"]
    assert exemplo["porta_vozes"][0]["voz"]["parametros"]["aula"] == schema.PARAMETROS_VOZ_PADRAO["aula"]
