"""T-02.13: galeria local — busca por tipo e formato, requisito efetivo e porta-voz (CONTRATO-template, "A busca")."""
import copy
import json
from pathlib import Path

import pytest

from expxmedia.template import galeria_local

CONTRATO = Path(__file__).resolve().parents[3] / "docs" / "contrato" / "CONTRATO-template.md"


def _exemplo_contrato():
    texto = CONTRATO.read_text(encoding="utf-8")
    return json.loads(texto.split("```json", 1)[1].split("```", 1)[0])


def _template(template_id, tipo="reel", formato="9:16", requisitos=(), kinds_requisitos=None,
              exige_porta_voz=False, serve_para=("conceito",), estilos=("claro",), status="validado"):
    dados = copy.deepcopy(_exemplo_contrato())
    motor = "remotion" if tipo in ("reel", "aula") else "html"
    canvas = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}[formato]
    dados.update({
        "template_id": template_id, "tipo": tipo, "motor": motor, "formato": formato,
        "canvas": {"w": canvas[0], "h": canvas[1]}, "status": status,
        "requisitos": list(requisitos), "exige_porta_voz": exige_porta_voz,
        "serve_para": list(serve_para), "estilos": list(estilos),
    })
    if motor == "remotion":
        dados["versoes"]["remotion"] = "4.0.290"
    base_kind = dados["kinds"]["numero"]
    dados["kinds"] = {}
    for nome, reqs in (kinds_requisitos or {"numero": []}).items():
        kind = copy.deepcopy(base_kind)
        kind["requisitos"] = list(reqs)
        dados["kinds"][nome] = kind
    dados["sequencia"] = list(dados["kinds"])
    return dados


def _gravar(pasta, dados):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "template.json").write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return pasta


def _local(raiz, dados):
    return _gravar(raiz / "galeria" / "templates" / dados["template_id"], dados)


def _embarcado(pasta_templates, dados):
    return _gravar(pasta_templates / dados["tipo"] / dados["template_id"], dados)


def _ids(resultado):
    return [t["template_id"] for t in resultado]


def _com_chave(raiz, linha):
    env = raiz / ".env"
    env.write_text(env.read_text(encoding="utf-8") + linha + "\n", encoding="utf-8")


@pytest.fixture
def galeria(instalacao, tmp_path, monkeypatch):
    """Instalação com um reel que exige narrar (local), um reel sem requisito (local) e um embarcado."""
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    embarcados = tmp_path / "repo" / "templates"
    _local(instalacao, _template("reel-narrado-a1b2c3", requisitos=["narrar"], serve_para=["historia"]))
    _local(instalacao, _template("reel-mudo-d4e5f6", serve_para=["conceito"]))
    _embarcado(embarcados, _template("reel-embarcado-0a0b0c", serve_para=["numero-e-dado"], estilos=["escuro"]))
    return instalacao, embarcados


# ---------------------------------------------------------------- integração


def test_chave_elevenlabs_no_env_faz_o_template_narrado_voltar(galeria):
    raiz, embarcados = galeria
    antes = galeria_local.buscar(raiz, tipo="reel", formato="9:16", embarcados=embarcados)
    assert "reel-narrado-a1b2c3" not in _ids(antes)

    _com_chave(raiz, "ELEVENLABS_API_KEY=chave-falsa-de-teste")
    depois = galeria_local.buscar(raiz, tipo="reel", formato="9:16", embarcados=embarcados)
    assert "reel-narrado-a1b2c3" in _ids(depois)
    narrado = next(t for t in depois if t["template_id"] == "reel-narrado-a1b2c3")
    assert narrado["requisitos"] == ["narrar"]
    assert narrado["galeria"] == "local"
    assert narrado["caminho"] == "galeria/templates/reel-narrado-a1b2c3"
    # nenhum valor do .env sai no resultado (M14)
    assert "chave-falsa-de-teste" not in json.dumps(depois)


def test_embarcados_vem_do_repositorio_com_caminho_relativo(galeria):
    raiz, embarcados = galeria
    resultado = galeria_local.buscar(raiz, tipo="reel", formato="9:16", embarcados=embarcados)
    embarcado = next(t for t in resultado if t["template_id"] == "reel-embarcado-0a0b0c")
    assert embarcado["galeria"] == "embarcada"
    assert embarcado["caminho"] == "templates/reel/reel-embarcado-0a0b0c"
    assert not Path(embarcado["caminho"]).is_absolute()
    # a pasta padrão dos embarcados é templates/ na raiz do repositório
    assert galeria_local.pasta_embarcados() == Path(__file__).resolve().parents[3] / "templates"


# ---------------------------------------------------------------- funcional


def test_sem_chave_reel_9_16_nao_devolve_o_template_que_exige_narrar(galeria):
    raiz, embarcados = galeria
    detalhado = galeria_local.buscar_detalhado(raiz, tipo="reel", formato="9:16", embarcados=embarcados)
    assert "reel-narrado-a1b2c3" not in _ids(detalhado["templates"])
    assert set(_ids(detalhado["templates"])) == {"reel-mudo-d4e5f6", "reel-embarcado-0a0b0c"}
    descartado = next(d for d in detalhado["descartados"] if d["template_id"] == "reel-narrado-a1b2c3")
    assert descartado["motivo"] == "requisito_nao_habilitado"
    assert descartado["falta"] == ["narrar"]
    assert "ELEVENLABS_API_KEY" in descartado["como_habilitar"]["narrar"]


def test_filtra_por_tipo_e_formato(galeria):
    raiz, embarcados = galeria
    _local(raiz, _template("carrossel-editorial-111111", tipo="carrossel", formato="4:5"))
    _local(raiz, _template("carrossel-quadrado-222222", tipo="carrossel", formato="1:1"))
    assert _ids(galeria_local.buscar(raiz, tipo="carrossel", formato="4:5", embarcados=embarcados)) == [
        "carrossel-editorial-111111"
    ]
    assert galeria_local.buscar(raiz, tipo="aula", formato="16:9", embarcados=embarcados) == []


def test_requisito_efetivo_une_template_e_kinds_usados(galeria):
    raiz, embarcados = galeria
    _local(raiz, _template(
        "carrossel-misto-333333", tipo="carrossel", formato="4:5", requisitos=["renderizar_html"],
        kinds_requisitos={"capa": [], "video": ["narrar"]},
    ))
    todos = galeria_local.buscar_detalhado(raiz, tipo="carrossel", formato="4:5", embarcados=embarcados)
    descartado = next(d for d in todos["descartados"] if d["template_id"] == "carrossel-misto-333333")
    assert "narrar" in descartado["requisitos"] and "renderizar_html" in descartado["requisitos"]
    # sem o kind de vídeo, narrar não entra no requisito efetivo
    so_capa = galeria_local.buscar_detalhado(
        raiz, tipo="carrossel", formato="4:5", kinds=["capa"], embarcados=embarcados,
    )
    todos_ids = _ids(so_capa["templates"]) + [d["template_id"] for d in so_capa["descartados"]]
    assert "carrossel-misto-333333" in todos_ids
    item = next(d for d in so_capa["templates"] + so_capa["descartados"] if d["template_id"] == "carrossel-misto-333333")
    assert "narrar" not in item["requisitos"]


def test_exige_porta_voz_e_descartado_sem_porta_voz_na_alma(galeria):
    raiz, embarcados = galeria
    _local(raiz, _template("reel-rosto-444444", exige_porta_voz=True))
    com = galeria_local.buscar(raiz, tipo="reel", formato="9:16", embarcados=embarcados)
    assert "reel-rosto-444444" in _ids(com)

    alma_json = raiz / "alma" / "alma.json"
    alma = json.loads(alma_json.read_text(encoding="utf-8"))
    alma["porta_vozes"] = []
    alma_json.write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")
    sem = galeria_local.buscar_detalhado(raiz, tipo="reel", formato="9:16", embarcados=embarcados)
    assert "reel-rosto-444444" not in _ids(sem["templates"])
    motivo = next(d for d in sem["descartados"] if d["template_id"] == "reel-rosto-444444")["motivo"]
    assert motivo == "sem_porta_voz"


def test_ordena_por_aderencia_a_serve_para_e_estilos(galeria):
    raiz, embarcados = galeria
    _local(raiz, _template("reel-dado-escuro-555555", serve_para=["numero-e-dado"], estilos=["escuro"]))
    _local(raiz, _template("reel-dado-claro-666666", serve_para=["numero-e-dado", "conceito"], estilos=["claro"]))
    resultado = galeria_local.buscar(
        raiz, tipo="reel", formato="9:16", serve_para=["numero-e-dado"], estilos=["claro"], embarcados=embarcados,
    )
    ids = _ids(resultado)
    # serve_para + estilo > só serve_para (local antes do embarcado no empate) > nenhum
    assert ids[0] == "reel-dado-claro-666666"
    assert ids.index("reel-dado-escuro-555555") < ids.index("reel-embarcado-0a0b0c")
    assert ids.index("reel-embarcado-0a0b0c") < ids.index("reel-mudo-d4e5f6")
    assert resultado[0]["aderencia"] == {"serve_para": 1, "estilos": 1}


def test_local_prevalece_sobre_embarcado_de_mesmo_id_e_invalido_e_descartado(galeria):
    raiz, embarcados = galeria
    _local(raiz, _template("reel-embarcado-0a0b0c", serve_para=["historia"]))
    quebrado = _template("reel-quebrado-777777")
    del quebrado["kinds"]
    _local(raiz, quebrado)
    (raiz / "galeria" / "templates" / "sem-manifesto").mkdir()
    detalhado = galeria_local.buscar_detalhado(raiz, tipo="reel", formato="9:16", embarcados=embarcados)
    repetido = [t for t in detalhado["templates"] if t["template_id"] == "reel-embarcado-0a0b0c"]
    assert len(repetido) == 1 and repetido[0]["galeria"] == "local"
    invalido = next(d for d in detalhado["descartados"] if d["template_id"] == "reel-quebrado-777777")
    assert invalido["motivo"] == "invalido"


def test_status_reprovado_ou_fora_nao_e_cogitado(galeria):
    raiz, embarcados = galeria
    _local(raiz, _template("reel-reprovado-888888", status="reprovado"))
    _local(raiz, _template("reel-fora-999999", status="fora"))
    ids = _ids(galeria_local.buscar(raiz, tipo="reel", formato="9:16", embarcados=embarcados))
    assert "reel-reprovado-888888" not in ids and "reel-fora-999999" not in ids


def test_embarcados_ausentes_nao_quebram(instalacao, tmp_path):
    assert galeria_local.buscar(instalacao, tipo="reel", formato="9:16", embarcados=tmp_path / "nao-existe") == []
