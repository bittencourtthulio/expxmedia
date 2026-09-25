"""T-01.01: o pacote expxmedia instala pelo uv e todas as dependências do plano são importáveis (D-42)."""
import importlib
import importlib.metadata
import tomllib
from pathlib import Path

import pytest

MOTOR = Path(__file__).resolve().parents[1]

# nome de distribuição -> módulo importável
DEPENDENCIAS = {
    "playwright": "playwright.sync_api",
    "pillow": "PIL.Image",
    "numpy": "numpy",
    "opencv-python-headless": "cv2",
    "filelock": "filelock",
    "jsonschema": "jsonschema",
    "requests": "requests",
    "faster-whisper": "faster_whisper",
    "rembg": "rembg",
    "onnxruntime": "onnxruntime",
}
DEV = {"pytest": "pytest", "scikit-image": "skimage"}

SUBPACOTES = [
    "nucleo", "ambiente", "alma", "peca", "template", "render_html", "imagem", "captura",
    "producao", "producao.apresentacao", "video", "narrar", "transcrever", "legendar", "motion",
    "referencia", "corte", "aula", "avatar", "publicar", "agendador", "revisar", "cli_comandos",
]


def _pyproject():
    return tomllib.loads((MOTOR / "pyproject.toml").read_text(encoding="utf-8"))


def _nomes(requisitos):
    import re
    return {re.split(r"[\s<>=!~\[;]", r, maxsplit=1)[0].lower() for r in requisitos}


def test_versao_do_pacote():
    import expxmedia
    assert expxmedia.__version__ == "0.1.0"
    assert importlib.metadata.version("expxmedia") == "0.1.0"


def test_pyproject_declara_tudo():
    dados = _pyproject()
    projeto = dados["project"]
    assert projeto["name"] == "expxmedia"
    assert projeto["requires-python"] == ">=3.11"
    assert projeto["scripts"]["expxmedia-motor"] == "expxmedia.cli:main"
    assert _nomes(projeto["dependencies"]) == set(DEPENDENCIAS)
    assert "openai-whisper" in _nomes(projeto["optional-dependencies"]["whisper-reserva"])
    assert set(DEV) <= _nomes(dados["dependency-groups"]["dev"])
    pytest_cfg = dados["tool"]["pytest"]["ini_options"]
    assert "--import-mode=importlib" in pytest_cfg["addopts"]
    assert any(m.startswith("integracao_local") for m in pytest_cfg["markers"])


@pytest.mark.parametrize("modulo", sorted({**DEPENDENCIAS, **DEV}.values()))
def test_dependencia_importavel(modulo):
    importlib.import_module(modulo)


@pytest.mark.parametrize("sub", SUBPACOTES)
def test_subpacote_importavel(sub):
    importlib.import_module(f"expxmedia.{sub}")
