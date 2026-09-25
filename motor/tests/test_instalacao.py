"""T-01.03 — fixture de instalação com Alma fictícia e fixture de rosto (D-02, D-43)."""
import json
import re
from datetime import datetime
from pathlib import Path

import cv2
import pytest

TESTS = Path(__file__).resolve().parent
FIXTURE_ALMA = TESTS / "fixtures" / "alma-ficticia" / "alma"
ASTRONAUTA = TESTS / "fixtures" / "rosto" / "astronauta.png"
CONTRATO_ALMA = TESTS.parent.parent / "docs" / "contrato" / "CONTRATO-alma.md"

# Strings da varredura de marca: nada do dono dos projetos de origem pode aparecer na Alma fictícia.
MARCA_PROIBIDA = [
    "thulio",
    "bittencourt",
    "expx",
    "softwarehouse",
    "software house exponencial",
    "expxplay",
]

ENUMS = {
    "metodo": {"site", "entrevista", "misto"},
    "origens": {"site", "entrevista", "inferido", "humano"},
    "ofertas.tipo": {"produto", "servico", "curso", "evento", "assinatura", "outro"},
    "voz.tratamento": {"voce", "tu", "nos", "impessoal"},
    "voz.formalidade": {"baixa", "media", "alta"},
    "fontes.origem": {"google", "local"},
    "canais.canal": {"instagram", "facebook", "youtube", "tiktok", "linkedin", "x", "site", "outro"},
}

PAPEIS_COR = {
    "fundo", "fundo_alt", "texto", "texto_inverso", "apoio",
    "destaque", "destaque_2", "positivo", "negativo",
}


def _exemplo_do_contrato():
    """Lê o JSON de exemplo do CONTRATO-alma: é ele que define as seções exigidas."""
    texto = CONTRATO_ALMA.read_text(encoding="utf-8")
    blocos = re.findall(r"```json\n(.*?)```", texto, flags=re.S)
    exemplos = [json.loads(b) for b in blocos if '"expxmedia_alma"' in b]
    assert len(exemplos) == 1, "CONTRATO-alma.md deve ter exatamente um exemplo de alma.json"
    return exemplos[0]


def _faltas(exemplo, real, caminho=""):
    """Compara a forma do exemplo do contrato com a Alma real; devolve os caminhos que faltam."""
    faltas = []
    if isinstance(exemplo, dict):
        if not isinstance(real, dict):
            return [f"{caminho or '<raiz>'}: esperado objeto"]
        for chave, valor in exemplo.items():
            sub = f"{caminho}.{chave}" if caminho else chave
            if chave not in real:
                faltas.append(sub)
            elif caminho == "" and chave == "origens":
                continue  # mapa livre caminho -> origem, validado pelos enums
            else:
                faltas.extend(_faltas(valor, real[chave], sub))
    elif isinstance(exemplo, list):
        if not isinstance(real, list):
            return [f"{caminho}: esperado lista"]
        if exemplo and isinstance(exemplo[0], dict):
            if not real:
                faltas.append(f"{caminho}: lista vazia")
            for i, item in enumerate(real):
                faltas.extend(_faltas(exemplo[0], item, f"{caminho}[{i}]"))
    elif exemplo is None:
        pass  # campo opcional: null ou valor
    elif isinstance(exemplo, bool):
        if not isinstance(real, bool):
            faltas.append(f"{caminho}: esperado booleano")
    elif isinstance(exemplo, (int, float)):
        if not isinstance(real, (int, float)) or isinstance(real, bool):
            faltas.append(f"{caminho}: esperado número")
    elif isinstance(exemplo, str):
        # Regra 3 do contrato: campo sem evidência é null (e vai para pendencias).
        if real is not None and not (isinstance(real, str) and real.strip()):
            faltas.append(f"{caminho}: esperado texto não vazio ou null")
    return faltas


def _alma():
    return json.loads((FIXTURE_ALMA / "alma.json").read_text(encoding="utf-8"))


def _rostos(caminho):
    imagem = cv2.imread(str(caminho))
    assert imagem is not None, f"imagem ilegível: {caminho}"
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    classificador = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    assert not classificador.empty()
    return classificador.detectMultiScale(cinza, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))


# ---------------------------------------------------------------- integração


def test_instalacao_cria_estrutura_em_tmp_path(instalacao, tmp_path):
    assert isinstance(instalacao, Path)
    assert instalacao.is_dir()
    assert tmp_path in instalacao.parents or instalacao == tmp_path
    for pasta in ("alma", "pecas", "estado", "eventos"):
        assert (instalacao / pasta).is_dir(), pasta
    env = instalacao / ".env"
    assert env.is_file()
    assert env.read_bytes() == b""


def test_instalacao_e_copia_independente_da_fixture(instalacao):
    alma = instalacao / "alma"
    assert alma.resolve() != FIXTURE_ALMA.resolve()
    assert (alma / "alma.json").read_bytes() == (FIXTURE_ALMA / "alma.json").read_bytes()
    assert (alma / "voz.md").is_file()
    # os caminhos da Alma são relativos à raiz da instalação (M9)
    dados = json.loads((alma / "alma.json").read_text(encoding="utf-8"))
    assert (instalacao / dados["visual"]["logo"]["principal"]).is_file()
    for pv in dados["porta_vozes"]:
        for retrato in pv["retratos"]:
            assert not Path(retrato).is_absolute()
            assert (instalacao / retrato).is_file(), retrato
    # alterar a cópia não toca a fixture versionada
    (alma / "alma.json").write_text("{}", encoding="utf-8")
    assert _alma()["expxmedia_alma"] == 1


# ---------------------------------------------------------------- funcional


def test_alma_tem_todas_as_secoes_do_contrato():
    exemplo = _exemplo_do_contrato()
    alma = _alma()
    assert set(exemplo) <= set(alma), sorted(set(exemplo) - set(alma))
    assert _faltas(exemplo, alma) == []


def test_alma_confirmada_e_coerente_com_os_enums():
    alma = _alma()
    assert alma["expxmedia_alma"] == 1
    for campo in ("criada_em", "confirmada_em", "atualizado_em"):
        momento = datetime.fromisoformat(alma[campo])
        assert momento.tzinfo is not None, campo
    assert alma["empresa"]["fuso"] == "America/Sao_Paulo"
    assert alma["metodo"] in ENUMS["metodo"]
    assert set(alma["origens"].values()) <= ENUMS["origens"]
    assert {o["tipo"] for o in alma["ofertas"]} <= ENUMS["ofertas.tipo"]
    assert sum(1 for o in alma["ofertas"] if o["principal"]) == 1
    assert alma["voz"]["tratamento"] in ENUMS["voz.tratamento"]
    assert alma["voz"]["formalidade"] in ENUMS["voz.formalidade"]
    assert {f["origem"] for f in alma["visual"]["fontes"].values()} <= ENUMS["fontes.origem"]
    assert {c["canal"] for c in alma["canais"]} <= ENUMS["canais.canal"]
    assert set(alma["visual"]["cores"]) == PAPEIS_COR
    for papel, cor in alma["visual"]["cores"].items():
        assert re.fullmatch(r"#[0-9A-Fa-f]{6}", cor), papel


def test_porta_voz_teste_com_voz_elevenlabs():
    alma = _alma()
    porta_vozes = {pv["id"]: pv for pv in alma["porta_vozes"]}
    assert "porta-voz-teste" in porta_vozes
    pv = porta_vozes["porta-voz-teste"]
    assert pv["principal"] is True
    assert pv["voz"]["provedor"] == "elevenlabs"
    assert isinstance(pv["voz"]["voz_id"], str) and pv["voz"]["voz_id"]
    assert pv["retratos"] == ["alma/assets/retratos/porta-voz-teste/01.png"]


def test_pendencias_apontam_campos_nulos():
    alma = _alma()
    assert alma["visual"]["logo"]["negativo"] is None
    assert "visual.logo.negativo" in alma["pendencias"]


@pytest.mark.parametrize("arquivo", ["alma.json", "voz.md", "assets/logo.svg"])
def test_alma_sem_nenhuma_marca_real(arquivo):
    texto = (FIXTURE_ALMA / arquivo).read_text(encoding="utf-8").lower()
    # a chave de versão do esquema é o nome do produto exigido pelo CONTRATO-alma, não marca da empresa
    texto = texto.replace('"expxmedia_alma"', "")
    achados = [termo for termo in MARCA_PROIBIDA if termo in texto]
    assert achados == [], f"{arquivo} contém marca real: {achados}"


def test_logo_e_svg_valido():
    import xml.etree.ElementTree as ET

    raiz = ET.parse(FIXTURE_ALMA / "assets" / "logo.svg").getroot()
    assert raiz.tag.endswith("svg")
    assert raiz.get("viewBox")


def test_astronauta_tem_rosto_detectavel():
    assert len(_rostos(ASTRONAUTA)) >= 1


def test_retrato_do_porta_voz_tem_rosto_detectavel():
    retrato = FIXTURE_ALMA / "assets" / "retratos" / "porta-voz-teste" / "01.png"
    assert len(_rostos(retrato)) >= 1
