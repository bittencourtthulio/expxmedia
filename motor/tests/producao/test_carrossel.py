"""T-03.12: produção de carrossel de imagem com slides, prancha e legenda.txt a partir de template e slots."""
from __future__ import annotations

import copy as _copy

import numpy as np
import pytest
from PIL import Image

from expxmedia.alma import carregar as alma_carregar
from expxmedia.nucleo import arquivos, rastro, tempo
from expxmedia.peca import modelo
from expxmedia.producao import carrossel
from fixtures.fontes_ficticias import semear_cache

TEMPLATE = "carrossel-editorial-b74228"
ROTULOS = ["Série", "Método", "Prática"]


def _conteudo(palavra, destaque, texto, **extras):
    return {"kind": "conteudo", "rotulos": ROTULOS, "palavra": palavra, "destaque": destaque, "texto": texto,
            "rodape": "perfil da empresa", **extras}


def _entrada(**extras):
    dados = {
        "template": TEMPLATE,
        "titulo": "Sem atalho: o que faz um pão durar",
        "slides": [
            {"kind": "capa", "rotulos": ROTULOS, "chapeu": "Feito com cuidado dura mais", "titulo": "SEM ATALHO",
             "cursiva": "Processo", "rodape": "perfil da empresa"},
            _conteudo("Tempo", "Fermentação longa cria sabor.", "Doze horas de descanso fazem o que nenhum aditivo faz."),
            _conteudo("Forno", "Duas fornadas por dia.", "O pão sai quente de manhã e à tarde, sem estoque de ontem.",
                      foto="retrato.png"),
            _conteudo("Casca", "A casca protege o miolo.", "Casca firme segura a umidade e o pão dura mais tempo."),
            {"kind": "cta", "rotulos": ROTULOS, "col_esq": "Fazer rápido não é fazer bem.",
             "col_dir": "Salve para a próxima vez.", "rodape": "perfil da empresa"},
        ],
        "legenda": "Sem atalho.\n\nCinco slides sobre o que faz um pão durar. Salve.",
        "conteudo": {"gancho": "Sem atalho", "gancho_tipo": "contraste", "cta": "Salve", "cta_forma": "salvar"},
    }
    dados.update(extras)
    return dados


@pytest.fixture
def imagens(instalacao, tmp_path):
    """Pasta de imagens da entrada, com o retrato da Alma fictícia."""
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    origem = instalacao / "alma" / "assets" / "retratos" / "porta-voz-teste" / "01.png"
    (pasta / "retrato.png").write_bytes(origem.read_bytes())
    return pasta


def _eventos(raiz):
    eventos, corrompidas = rastro.ler(raiz, tempo.agora(raiz).strftime("%Y-%m"))
    assert corrompidas == 0
    return eventos


# ---------------------------------------------------------------- integração


def test_carrossel_de_5_slides_gera_5_pngs_prancha_e_peca_json_em_ordem(instalacao, imagens, tmp_path):
    r = carrossel.produzir(instalacao, _entrada(), base_imagens=imagens, cache_fontes=semear_cache(tmp_path / "fontes"))
    pasta = modelo.pasta(instalacao, r["peca_id"])
    peca = modelo.carregar(instalacao, r["peca_id"])

    assert peca["status"] == "produzida" and peca["tipo"] == "carrossel" and peca["template"] == TEMPLATE
    pngs = sorted(p.name for p in (pasta / "slides").glob("*.png"))
    assert pngs == [f"slide_{n:02d}.png" for n in range(1, 6)]
    for nome in pngs:
        with Image.open(pasta / "slides" / nome) as img:
            assert img.size == (1080, 1350)
    assert [s["n"] for s in peca["slides"]] == [1, 2, 3, 4, 5]
    assert [s["kind"] for s in peca["slides"]] == ["capa", "conteudo", "conteudo", "conteudo", "cta"]
    assert all(s["midia"] == "imagem" and s["duracao_s"] is None for s in peca["slides"])
    assert [s["arquivo"] for s in peca["slides"]] == [f"slides/{n}" for n in pngs]
    # prancha: os 5 slides lado a lado (célula 432 + folga 16)
    with Image.open(pasta / "previa" / "prancha.png") as img:
        assert img.size == (5 * 432 + 6 * 16, 540 + 2 * 16)
    papeis = {a["caminho"]: a["papel"] for a in peca["arquivos"]}
    assert papeis["previa/prancha.png"] == "previa" and papeis["texto/legenda.txt"] == "legenda"
    assert [c for c, p in papeis.items() if p == "slide"] == [f"slides/{n}" for n in pngs]
    assert (pasta / "texto" / "legenda.txt").read_text(encoding="utf-8").startswith("Sem atalho.")
    assert peca["conteudo"]["legenda"] == "texto/legenda.txt"
    # a foto entrou no slide 3 (figura em 80..1000 × 380..840): tons contínuos de foto, não chapados;
    # os slides sem foto têm só a palavra chapada e o fundo naquela área
    def tons(nome):
        with Image.open(pasta / "slides" / nome) as img:
            px = np.asarray(img.convert("RGB").crop((340, 420, 740, 820))).reshape(-1, 3)
            return len({tuple(c) for c in px})
    assert tons("slide_03.png") > 2000 and tons("slide_02.png") < 500
    assert not (pasta / ".render").exists()
    eventos = [e["evento"] for e in _eventos(instalacao) if e["peca_id"] == r["peca_id"]]
    assert eventos == ["peca_criada", "geracao_concluida", "peca_status"]


def test_render_reprovado_registra_geracao_falhou_e_peca_fica_em_roteiro(instalacao, tmp_path):
    """Alma com destaque cinza-claro sob o texto branco: o bloco de destaque perde contraste e o render reprova."""
    alma = arquivos.ler_json(instalacao / "alma" / "alma.json")
    alma["visual"]["cores"]["destaque"] = "#B8B8B8"
    arquivos.gravar_json(instalacao / "alma" / "alma.json", alma)
    assert not alma_carregar.carregar(instalacao).violacoes
    with pytest.raises(carrossel.ErroRenderReprovado) as erro:
        carrossel.produzir(instalacao, _entrada(slides=_entrada()["slides"][1:2]), cache_fontes=semear_cache(tmp_path / "fontes"))
    peca = modelo.carregar(instalacao, erro.value.peca_id)
    assert peca["status"] == "roteiro" and peca["producao"] is None and peca["slides"] == []
    assert any("contraste" in p for p in erro.value.problemas)
    eventos = [e for e in _eventos(instalacao) if e["peca_id"] == erro.value.peca_id]
    assert [e["evento"] for e in eventos] == ["peca_criada", "geracao_falhou"]
    assert eventos[1]["resultado"] == "falha" and eventos[1]["capacidade"] == "renderizar_html"


# ---------------------------------------------------------------- funcional


def test_kind_inexistente_cita_o_kind_e_os_disponiveis(instalacao):
    entrada = _entrada()
    entrada["slides"][1] = {"kind": "grafico", "rotulos": ROTULOS}
    with pytest.raises(carrossel.ErroSlots) as erro:
        carrossel.produzir(instalacao, entrada)
    mensagem = str(erro.value)
    assert "kind 'grafico' não existe no template" in mensagem
    assert "capa, conteudo, cta" in mensagem
    assert list((instalacao / "pecas").rglob("*")) == []


def test_slot_acima_do_max_no_carrossel_e_erro_antes_do_render(instalacao):
    entrada = _copy.deepcopy(_entrada())
    entrada["slides"][4]["col_dir"] = "x" * 51
    with pytest.raises(carrossel.ErroSlots, match="slide 5 \\(cta\\), slot 'col_dir': 51 caracteres, o template aguenta 50"):
        carrossel.produzir(instalacao, entrada)
    assert list((instalacao / "pecas").rglob("*")) == []


def test_carrossel_exige_legenda(instalacao):
    with pytest.raises(carrossel.ErroEntradaProducao) as erro:
        carrossel.produzir(instalacao, _entrada(legenda=None))
    assert erro.value.campo == "legenda"
