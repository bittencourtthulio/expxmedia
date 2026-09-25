"""Fixtures dos testes do render HTML (T-03.01 a T-03.05).

- `alma_neutra(**cores)`: Alma mínima (dict) com os nove papéis de cor e fontes nulas, que caem na
  Inter embarcada do motor — nada de rede.
- `criar_template(kinds, css, fragmentos, **extras)`: escreve um template do núcleo numa pasta
  temporária (`template.json`, `template.css`, `slides/<kind>.html`).
- `g1`: o layout do golden G1 adaptado para template (adaptador_g1.py), a Alma golden e as fontes
  do golden servidas pelo stub HTTP local no papel do Google Fonts, renderizado UMA vez por sessão.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from stubs.servidor import ServidorStub


def _carregar(nome):
    caminho = Path(__file__).resolve().parent / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(f"_render_html_{nome}", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


adaptador_g1 = _carregar("adaptador_g1")

CORES_NEUTRAS = {
    "fundo": "#ffffff",
    "fundo_alt": "#101010",
    "texto": "#111111",
    "texto_inverso": "#ffffff",
    "apoio": "#555555",
    "destaque": "#1f4fd1",
    "destaque_2": "#6b2fb3",
    "positivo": "#1c7c3c",
    "negativo": "#b3261e",
}


def fazer_alma(**cores):
    return {
        "expxmedia_alma": 1,
        "empresa": {"nome": "Teste", "fuso": "America/Sao_Paulo", "idioma": "pt-BR"},
        "visual": {
            "cores": {**CORES_NEUTRAS, **cores},
            "fontes": {"titulo": {"familia": None, "origem": None}, "texto": {"familia": None, "origem": None}},
            "logo": {"principal": None, "negativo": None, "simbolo": None},
        },
    }


@pytest.fixture
def alma_neutra():
    return fazer_alma


def escrever_template(pasta: Path, kinds: dict, css: str, fragmentos: dict[str, str], **extras) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    manifesto = {
        "expxmedia_template": 1,
        "template_id": "carrossel-teste-render-abc123",
        "titulo": "Teste",
        "tipo": "carrossel",
        "motor": "html",
        "formato": "4:5",
        "canvas": {"w": 1080, "h": 1350},
        "status": "rascunho",
        "tokens": ["fundo", "texto"],
        "fontes": ["titulo", "texto"],
        "sequencia": list(kinds),
        "kinds": {
            nome: {"midia": "imagem", "duracao_s": None, "fit": None, "requisitos": [], **kind}
            for nome, kind in kinds.items()
        },
        **extras,
    }
    (pasta / "template.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8")
    (pasta / "template.css").write_text(css, encoding="utf-8")
    (pasta / "slides").mkdir(exist_ok=True)
    for kind, html in fragmentos.items():
        (pasta / "slides" / f"{kind}.html").write_text(html, encoding="utf-8")
    return pasta


@pytest.fixture
def criar_template(tmp_path):
    contador = {"n": 0}

    def criar(kinds, css, fragmentos, **extras):
        contador["n"] += 1
        return escrever_template(tmp_path / f"template{contador['n']}", kinds, css, fragmentos, **extras)

    return criar


@pytest.fixture(scope="session")
def stub_fontes_g1():
    """O stub HTTP local no papel do Google Fonts, servindo o CSS e o woff2 gravados no golden G1."""
    css, arquivos = adaptador_g1.fontes_golden()
    with ServidorStub() as stub:
        stub.rota("GET", "/css2", corpo=css.encode("utf-8"), cabecalhos={"Content-Type": "text/css"})
        for nome, dados in arquivos.items():
            stub.rota("GET", f"/{nome}", corpo=dados, cabecalhos={"Content-Type": "font/woff2"})
        yield stub


@pytest.fixture(scope="session")
def g1(tmp_path_factory, stub_fontes_g1):
    """O G1 renderizado pelo núcleo uma vez por sessão: {template, copy, alma, saida, resultado, golden}."""
    from expxmedia.render_html import renderizar

    base = tmp_path_factory.mktemp("g1")
    template, copy = adaptador_g1.montar_template(base / "template")
    alma = adaptador_g1.alma_golden()
    saida = base / "saida"
    resultado = renderizar.renderizar(template, copy, alma, saida, cache_fontes=base / "cache",
                                      url_fontes=stub_fontes_g1.url, salvar_html=True, exemplo=True)
    return {"template": template, "copy": copy, "alma": alma, "saida": saida, "resultado": resultado,
            "golden": adaptador_g1.render_golden(), "cache": base / "cache", "url_fontes": stub_fontes_g1.url}
