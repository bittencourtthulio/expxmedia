"""T-03.10: templates embarcados de post único e carrossel, neutralizados com tokens --alma-* (D-31).

Cada template embarcado:
- passa em `template.validar` no modo `template` sem nenhum achado (sem cor literal fora do
  `:root`, sem URL externa, `template.json` no contrato);
- renderiza o próprio exemplo com a Alma fictícia sem achado de validação, contraste ou encaixe;
- troca de cara com a Alma: a mesma copy com outra Alma sai com outras cores (nada de cor fixa).
"""
from __future__ import annotations

import copy as _copy
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from expxmedia.alma import carregar as alma_carregar
from expxmedia.render_html import renderizar
from expxmedia.template import galeria_local, validar
from fixtures.fontes_ficticias import semear_cache

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
EMBARCADOS = {
    "post_unico/numero-e-frase": ("post_unico", "4:5", ["numero", "frase"]),
    "carrossel/editorial": ("carrossel", "4:5", ["capa", "conteudo", "cta"]),
}
REFERENCIA_PROIBIDA = ("referencia", "previa")


@pytest.fixture(scope="module")
def instalacao_modulo(tmp_path_factory):
    import importlib.util

    spec = importlib.util.spec_from_file_location("_fix_instalacao_embarcados", Path(__file__).parent / "fixtures" / "instalacao.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.montar_instalacao(tmp_path_factory.mktemp("embarcados") / "instalacao")


@pytest.fixture(scope="module")
def renders(instalacao_modulo, tmp_path_factory):
    """Cada template renderizado uma vez com o próprio exemplo e a Alma fictícia."""
    alma = alma_carregar.carregar(instalacao_modulo)
    assert not alma.violacoes
    saida = {}
    for nome in EMBARCADOS:
        pasta = TEMPLATES / nome
        destino = tmp_path_factory.mktemp(nome.replace("/", "-"))
        semear_cache(destino / "fontes")
        saida[nome] = renderizar.renderizar(pasta, pasta / "exemplo.json", alma, destino / "saida",
                                            raiz=instalacao_modulo, cache_fontes=destino / "fontes", exemplo=True)
        saida[nome]["_saida"] = destino / "saida"
    return saida


# ---------------------------------------------------------------- integração


@pytest.mark.parametrize("nome", sorted(EMBARCADOS))
def test_render_com_alma_ficticia_sem_achado(renders, nome):
    r = renders[nome]
    assert r["erros"] == [], r["erros"]
    tipo, _, kinds = EMBARCADOS[nome]
    assert [s["kind"] for s in r["slides"]] == kinds
    for slide in r["slides"]:
        assert slide["problemas"] == [], (nome, slide["kind"], slide["problemas"])
    assert r["ok"] is True
    for slide in r["slides"]:
        with Image.open(r["_saida"] / slide["arquivo"]) as img:
            assert img.size == (1080, 1350)
    assert (r["_saida"] / "_prancha.png").is_file()


@pytest.mark.parametrize("nome", sorted(EMBARCADOS))
def test_cor_vem_da_alma_e_nao_do_template(renders, instalacao_modulo, tmp_path, nome):
    """A mesma copy com outra paleta muda os pixels: nenhuma cor de marca fixa no template."""
    alma = _copy.deepcopy(alma_carregar.carregar(instalacao_modulo).dados)
    alma["visual"]["cores"].update({"fundo": "#EEF3FF", "destaque": "#1F3FBF", "texto": "#0E1330", "destaque_2": "#7A2E9E"})
    pasta = TEMPLATES / nome
    semear_cache(tmp_path / "fontes")
    outra = renderizar.renderizar(pasta, pasta / "exemplo.json", alma, tmp_path / "saida", raiz=instalacao_modulo,
                                  cache_fontes=tmp_path / "fontes", exemplo=True, gerar_prancha=False)
    assert outra["ok"], [s["problemas"] for s in outra["slides"]] or outra["erros"]
    original = renders[nome]
    for a, b in zip(original["slides"], outra["slides"]):
        with Image.open(original["_saida"] / a["arquivo"]) as x, Image.open(tmp_path / "saida" / b["arquivo"]) as y:
            diferentes = (np.abs(np.asarray(x.convert("RGB"), int) - np.asarray(y.convert("RGB"), int)).sum(axis=2) > 30).mean()
        assert diferentes > 0.3, (nome, a["kind"], diferentes)


@pytest.mark.parametrize("nome", sorted(EMBARCADOS))
def test_galeria_local_encontra_o_embarcado(instalacao_modulo, nome):
    tipo, formato, _ = EMBARCADOS[nome]
    achados = galeria_local.buscar(instalacao_modulo, tipo=tipo, formato=formato)
    manifesto = json.loads((TEMPLATES / nome / "template.json").read_text(encoding="utf-8"))
    assert manifesto["template_id"] in [a["template_id"] for a in achados]


# ---------------------------------------------------------------- funcional


@pytest.mark.parametrize("nome", sorted(EMBARCADOS))
def test_validar_modo_template_sem_achado(nome):
    pasta = TEMPLATES / nome
    tipo, formato, kinds = EMBARCADOS[nome]
    assert validar.validar_template(pasta, modo="template") == []
    manifesto = json.loads((pasta / "template.json").read_text(encoding="utf-8"))
    assert list(manifesto)[0] == "expxmedia_template"
    assert (manifesto["tipo"], manifesto["formato"], manifesto["motor"]) == (tipo, formato, "html")
    assert manifesto["sequencia"] == kinds and sorted(manifesto["kinds"]) == sorted(kinds)
    assert manifesto["origem"]["inspiracao"] is None and manifesto["origem"]["id_compartilhado"] is None
    for kind in kinds:
        assert (pasta / "slides" / f"{kind}.html").is_file()
    # referência de terceiros e prévia local nunca vêm embarcadas
    assert not any((pasta / p).exists() for p in REFERENCIA_PROIBIDA)
    # o exemplo usa todos os kinds na ordem da sequência e cabe nos slots
    exemplo = json.loads((pasta / "exemplo.json").read_text(encoding="utf-8"))
    assert renderizar.validar_copy(renderizar.carregar_template(pasta), exemplo, exemplo=True) == []


def test_validador_pega_cor_literal_num_template_embarcado(tmp_path):
    """Controle: o mesmo template com uma cor de marca fora do :root reprova."""
    import shutil

    copia = tmp_path / "editorial"
    shutil.copytree(TEMPLATES / "carrossel" / "editorial", copia)
    css = copia / "template.css"
    css.write_text(css.read_text(encoding="utf-8") + "\n.slide.cta { background: #E4602A; }\n", encoding="utf-8")
    achados = validar.validar_template(copia, modo="template")
    assert [a["tipo"] for a in achados] == ["cor_literal"]
