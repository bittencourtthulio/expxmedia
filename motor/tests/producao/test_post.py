"""T-03.11: produção de post único a partir de slots e template, com peca.json, PNG e eventos."""
from __future__ import annotations

import json

import pytest
from PIL import Image

from expxmedia.nucleo import rastro, tempo
from expxmedia.peca import modelo
from expxmedia.producao import post
from fixtures.fontes_ficticias import semear_cache

TEMPLATE = "post_unico-numero-e-frase-86c9ac"


def _entrada(**extras):
    dados = {
        "template": TEMPLATE,
        "titulo": "Doze perguntas antes de fechar um pedido",
        "slides": [{
            "kind": "numero",
            "etiqueta": "Checklist",
            "numero": "12",
            "texto": "Perguntas para fazer antes de fechar qualquer pedido. Salve e use no próximo atendimento.",
        }],
        "legenda": "Doze perguntas que evitam retrabalho.\n\nSalve para usar depois.",
        "conteudo": {"gancho": "12 perguntas", "gancho_tipo": "numero", "cta": "Salve", "cta_forma": "salvar"},
    }
    dados.update(extras)
    return dados


def _eventos(raiz):
    eventos, corrompidas = rastro.ler(raiz, tempo.agora(raiz).strftime("%Y-%m"))
    assert corrompidas == 0
    return eventos


# ---------------------------------------------------------------- integração


def test_post_gera_png_em_pecas_e_fica_produzida_com_geracao_concluida(instalacao, tmp_path):
    r = post.produzir(instalacao, _entrada(), cache_fontes=semear_cache(tmp_path / "fontes"))

    peca = modelo.carregar(instalacao, r["peca_id"])
    pasta = modelo.pasta(instalacao, r["peca_id"])
    assert pasta.parent.parent == instalacao / "pecas"
    assert peca["status"] == "produzida" and r["status"] == "produzida"
    assert (peca["tipo"], peca["formatos"], peca["template"]) == ("post_unico", ["4:5"], TEMPLATE)
    assert peca["slides"] == [{"n": 1, "kind": "numero", "midia": "imagem", "arquivo": "slides/slide_01.png", "duracao_s": None}]
    with Image.open(pasta / "slides" / "slide_01.png") as img:
        assert img.size == (1080, 1350)
    assert {"caminho": "slides/slide_01.png", "papel": "slide", "formato": "4:5"} in peca["arquivos"]
    assert {"caminho": "texto/legenda.txt", "papel": "legenda", "formato": None} in peca["arquivos"]
    assert (pasta / "texto" / "legenda.txt").read_text(encoding="utf-8").startswith("Doze perguntas")
    assert peca["conteudo"]["legenda"] == "texto/legenda.txt" and peca["conteudo"]["gancho_tipo"] == "numero"
    assert peca["producao"]["capacidades"] == ["renderizar_html"]
    assert peca["producao"]["provedores"] == {"renderizar_html": "playwright"}

    eventos = [e for e in _eventos(instalacao) if e["peca_id"] == r["peca_id"]]
    assert [e["evento"] for e in eventos] == ["peca_criada", "geracao_concluida", "peca_status"]
    concluida = eventos[1]
    assert (concluida["capacidade"], concluida["provedor"], concluida["resultado"]) == ("renderizar_html", "playwright", "ok")
    assert concluida["template_id"] == TEMPLATE and concluida["segundos"] >= 0
    assert any(a.endswith("slides/slide_01.png") for a in concluida["arquivos"])
    assert [e["detalhe"] for e in eventos if e["evento"] == "peca_status"] == ["roteiro -> produzida"]


def test_post_com_logo_da_alma_e_kind_frase(instalacao, tmp_path):
    entrada = _entrada(slides=[{"kind": "frase", "abertura": "Pressa não é", "palavra": "Foco.",
                                "texto": "Diga o que é pronto e o que não pode faltar."}])
    entrada.pop("legenda")
    r = post.produzir(instalacao, entrada, cache_fontes=semear_cache(tmp_path / "fontes"))
    peca = modelo.carregar(instalacao, r["peca_id"])
    assert peca["slides"][0]["kind"] == "frase" and peca["conteudo"]["legenda"] is None
    assert not (modelo.pasta(instalacao, r["peca_id"]) / "texto").exists()


# ---------------------------------------------------------------- funcional


def test_slot_acima_do_max_e_erro_antes_do_render_sem_arquivo(instalacao, tmp_path):
    entrada = _entrada()
    entrada["slides"][0]["numero"] = "12345"  # max 4
    with pytest.raises(post.ErroSlots) as erro:
        post.produzir(instalacao, entrada, cache_fontes=semear_cache(tmp_path / "fontes"))
    assert "slot 'numero'" in str(erro.value) and "o template aguenta 4" in str(erro.value)
    assert erro.value.erros and all(isinstance(e, str) for e in erro.value.erros)
    # nada foi criado: nem peça, nem saida/, nem evento
    assert list((instalacao / "pecas").rglob("*")) == []
    assert _eventos(instalacao) == []


def test_post_unico_aceita_um_slide_so(instalacao, tmp_path):
    entrada = _entrada()
    entrada["slides"] = entrada["slides"] * 2
    with pytest.raises(post.ErroSlots, match="exatamente 1 slide"):
        post.produzir(instalacao, entrada)
    assert list((instalacao / "pecas").rglob("*")) == []


def test_template_de_outro_tipo_ou_inexistente_e_erro_de_entrada(instalacao):
    with pytest.raises(post.ErroEntradaProducao, match="carrossel-editorial-b74228.*carrossel"):
        post.produzir(instalacao, _entrada(template="carrossel-editorial-b74228"))
    with pytest.raises(post.ErroEntradaProducao, match=f"template 'nao-existe-000000'.*{TEMPLATE}"):
        post.produzir(instalacao, _entrada(template="nao-existe-000000"))


@pytest.mark.parametrize("campo, valor, trecho", [
    ("template", None, "template"),
    ("titulo", "", "titulo"),
    ("slides", "não é lista", "slides"),
    ("legenda", 12, "legenda"),
])
def test_entrada_invalida_cita_o_campo(instalacao, campo, valor, trecho):
    with pytest.raises(post.ErroEntradaProducao) as erro:
        post.produzir(instalacao, _entrada(**{campo: valor}))
    assert f"'{trecho}'" in str(erro.value)
    assert json.dumps(erro.value.campo) == json.dumps(campo)
