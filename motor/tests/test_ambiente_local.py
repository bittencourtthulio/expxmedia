"""T-01.08: ambiente local pronto para a suíte (D-42, D-21).

O teste NÃO instala nada: só confere a presença do que motor/scripts/preparar_ambiente.py
deixou na máquina (rodado uma vez, fora da suíte, com rede).

- Integração: binários no PATH, Chromium do Playwright na revisão pedida pela versão do
  playwright do venv, chrome-headless-shell do Remotion, caches do faster-whisper small e
  medium, u2net.onnx do rembg e os três arquivos da Inter embarcada.
- Funcional: com o PATH simulado sem um binário, a checagem falha citando o nome dele.
"""
import importlib.util
import os
import stat
from pathlib import Path

import pytest

MOTOR = Path(__file__).resolve().parents[1]
SCRIPT = MOTOR / "scripts" / "preparar_ambiente.py"
INTER = MOTOR / "src" / "expxmedia" / "recursos" / "fontes" / "Inter"

pytestmark = pytest.mark.integracao_local


def _carregar_script():
    spec = importlib.util.spec_from_file_location("_preparar_ambiente", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def prep():
    assert SCRIPT.is_file(), f"script de preparação ausente: {SCRIPT.relative_to(MOTOR)}"
    return _carregar_script()


# ---------------------------------------------------------------- integração


def test_lista_de_binarios_e_a_do_plano(prep):
    assert tuple(prep.BINARIOS) == ("ffmpeg", "say", "node", "npx", "claude", "uv")


def test_binarios_no_path(prep):
    ausentes = prep.binarios_ausentes()
    assert not ausentes, f"binários ausentes do PATH: {', '.join(ausentes)}"


def test_chromium_do_playwright_na_revisao_do_venv(prep):
    pastas = prep.pastas_chromium_playwright()
    assert pastas, "o playwright do venv não declara revisão de chromium"
    for pasta in pastas:
        assert (pasta / "INSTALLATION_COMPLETE").is_file(), f"Chromium do Playwright ausente: {pasta}"


def test_revisao_do_chromium_vem_do_playwright_instalado(prep):
    # a revisão não é fixa no teste: vem do browsers.json do pacote playwright do venv
    import json

    import playwright

    browsers = Path(playwright.__file__).parent / "driver" / "package" / "browsers.json"
    revisoes = {b["name"]: b["revision"] for b in json.loads(browsers.read_text())["browsers"]}
    nomes = {p.name for p in prep.pastas_chromium_playwright()}
    assert f"chromium-{revisoes['chromium']}" in nomes
    assert f"chromium_headless_shell-{revisoes['chromium-headless-shell']}" in nomes


def test_chrome_headless_shell_do_remotion(prep):
    binario = prep.chrome_headless_shell_remotion()
    assert binario is not None, "chrome-headless-shell do Remotion ausente em kit-remotion/node_modules/.remotion"
    assert binario.is_file() and os.access(binario, os.X_OK), binario


@pytest.mark.parametrize("modelo", ["small", "medium"])
def test_cache_do_faster_whisper(prep, modelo):
    pasta = prep.cache_faster_whisper(modelo)
    assert pasta.name == f"models--Systran--faster-whisper-{modelo}"
    snapshots = list((pasta / "snapshots").glob("*/model.bin"))
    assert snapshots, f"faster-whisper {modelo} ausente do cache: {pasta}"
    assert snapshots[0].stat().st_size > 1_000_000


def test_u2net_do_rembg(prep):
    u2net = prep.arquivo_u2net()
    assert u2net.name == "u2net.onnx"
    assert u2net.is_file(), f"u2net ausente: {u2net}"
    assert u2net.stat().st_size > 1_000_000


@pytest.mark.parametrize(
    "nome", ["inter-latin-400-normal.woff2", "inter-latin-700-normal.woff2", "OFL.txt"]
)
def test_inter_embarcada(nome):
    arquivo = INTER / nome
    assert arquivo.is_file(), f"arquivo da Inter ausente: {nome}"
    dados = arquivo.read_bytes()
    if nome.endswith(".woff2"):
        assert dados[:4] == b"wOF2", f"{nome} não é woff2"
    else:
        assert b"SIL Open Font License" in dados


def test_verificar_tudo_nao_aponta_nada(prep):
    assert prep.verificar() == []


# ---------------------------------------------------------------- funcional


def _bin_falso(pasta, nome):
    caminho = pasta / nome
    caminho.write_text("#!/bin/sh\nexit 0\n")
    caminho.chmod(caminho.stat().st_mode | stat.S_IXUSR)


@pytest.mark.parametrize("faltando", ["ffmpeg", "say", "node", "claude"])
def test_path_sem_um_binario_aponta_o_nome_dele(prep, tmp_path, monkeypatch, faltando):
    for nome in prep.BINARIOS:
        if nome != faltando:
            _bin_falso(tmp_path, nome)
    monkeypatch.setenv("PATH", str(tmp_path))

    assert prep.binarios_ausentes() == [faltando]
    problemas = prep.verificar()
    assert any(faltando in p for p in problemas), problemas
    outros = [n for n in prep.BINARIOS if n != faltando]
    assert not any(f"binário ausente: {n}" in p for p in problemas for n in outros), problemas


def test_path_completo_nao_aponta_binario(prep, tmp_path, monkeypatch):
    for nome in prep.BINARIOS:
        _bin_falso(tmp_path, nome)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert prep.binarios_ausentes() == []
