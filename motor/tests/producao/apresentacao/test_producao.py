"""T-05.11: template de apresentação embarcado e produção (HTML final; com mp4, MP4 e PNG por slide).

- Integração: produzir uma apresentação na fixture gera `saida/apresentacao.html` com papel `final`,
  a peça fica `produzida` com `geracao_concluida` no rastro, e o HTML traz o CSS do template.
- Funcional: com `mp4=True`, a peça lista também o MP4 com papel `final` e os PNGs com papel `slide`.
"""
from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from expxmedia.nucleo import rastro, tempo
from expxmedia.peca import modelo
from expxmedia.producao.apresentacao import deck as _deck
from expxmedia.producao.apresentacao import producao
from expxmedia.template import galeria_local, validar
from fixtures.fontes_ficticias import semear_cache

TEMPLATE = Path(__file__).resolve().parents[4] / "templates" / "apresentacao" / "padrao"
EXEMPLO = json.loads((TEMPLATE / "exemplo.json").read_text(encoding="utf-8"))


def _entrada(**extras):
    dados = {"deck": copy.deepcopy(EXEMPLO)}
    dados.update(extras)
    return dados


def _eventos(raiz):
    eventos, corrompidas = rastro.ler(raiz, tempo.agora(raiz).strftime("%Y-%m"))
    assert corrompidas == 0
    return eventos


# ---------------------------------------------------------------- integração


def test_apresentacao_gera_html_final_e_peca_produzida(instalacao, tmp_path):
    r = producao.produzir(instalacao, _entrada(), cache_fontes=semear_cache(tmp_path / "fontes"))

    peca = modelo.carregar(instalacao, r["peca_id"])
    pasta = modelo.pasta(instalacao, r["peca_id"])
    assert peca["status"] == "produzida" == r["status"]
    assert (peca["tipo"], peca["formatos"], peca["template"]) == ("apresentacao", ["16:9"], "apresentacao-padrao-4c7e2a")
    assert peca["arquivos"] == [
        {"caminho": "saida/apresentacao.html", "papel": "final", "formato": "16:9"},
        {"caminho": "texto/deck.json", "papel": "roteiro", "formato": None},
    ]
    html = (pasta / "saida" / "apresentacao.html").read_text(encoding="utf-8")
    assert html.count('<section class="slide ') == 9
    assert "/* Apresentação padrão: o palco do motor" in html  # o CSS do template entrou no palco
    assert json.loads((pasta / "texto" / "deck.json").read_text(encoding="utf-8")) == EXEMPLO
    # um slide por slide do deck, com o kind do tipo, apontando para o slide dentro do palco
    assert peca["slides"] == [
        {"n": n, "kind": s["tipo"], "midia": "imagem", "arquivo": f"saida/apresentacao.html#{n}", "duracao_s": None}
        for n, s in enumerate(EXEMPLO["slides"], 1)]
    # o CTA vem da Alma; o gancho sai do slide de título
    alma = json.loads((instalacao / "alma" / "alma.json").read_text(encoding="utf-8"))
    assert peca["conteudo"]["cta"] == alma["cta"]["padrao"] and peca["conteudo"]["cta_forma"] == "link"
    assert peca["conteudo"]["gancho"] == "A semana que não vira incêndio"
    assert peca["producao"]["capacidades"] == [] and peca["producao"]["provedores"] == {}
    eventos = [e for e in _eventos(instalacao) if e["peca_id"] == r["peca_id"]]
    assert [e["evento"] for e in eventos] == ["peca_criada", "geracao_concluida", "peca_status"]
    assert eventos[1]["template_id"] == "apresentacao-padrao-4c7e2a"
    assert "saida/apresentacao.html" in [a.split("/", 3)[-1] for a in eventos[1]["arquivos"]]
    assert r["pasta"].startswith("pecas/") and not Path(r["pasta"]).is_absolute()


def test_template_embarcado_valida_e_a_galeria_encontra(instalacao):
    assert validar.validar_template(TEMPLATE, modo="template") == []
    manifesto = json.loads((TEMPLATE / "template.json").read_text(encoding="utf-8"))
    assert list(manifesto)[0] == "expxmedia_template"
    assert (manifesto["tipo"], manifesto["formato"], manifesto["motor"]) == ("apresentacao", "16:9", "html")
    assert sorted(manifesto["kinds"]) == sorted(_deck.TIPOS) == sorted(manifesto["sequencia"])
    assert _deck.validar(EXEMPLO) == []
    assert not (TEMPLATE / "referencia").exists() and not (TEMPLATE / "previa").exists()
    ids = [a["template_id"] for a in galeria_local.buscar(instalacao, tipo="apresentacao", formato="16:9")]
    assert "apresentacao-padrao-4c7e2a" in ids


def test_deck_invalido_nao_cria_peca(instalacao):
    ruim = copy.deepcopy(EXEMPLO)
    ruim["slides"][2]["tipo"] = "grafico"
    with pytest.raises(producao.ErroDeckInvalido) as erro:
        producao.produzir(instalacao, {"deck": ruim})
    assert "tipos aceitos" in str(erro.value)
    assert list((instalacao / "pecas").rglob("peca.json")) == []


def test_entrada_fora_do_formato(instalacao):
    with pytest.raises(producao.ErroEntradaProducao) as erro:
        producao.produzir(instalacao, _entrada(cta_fixo="x"))
    assert erro.value.campo == "cta_fixo"
    with pytest.raises(producao.ErroEntradaProducao) as erro:
        producao.produzir(instalacao, _entrada(ativos="/tmp/fora"))
    assert erro.value.campo == "ativos"
    with pytest.raises(producao.ErroEntradaProducao) as erro:
        producao.produzir(instalacao, _entrada(template="carrossel-editorial-b74228"))
    assert erro.value.campo == "template"


def test_falha_no_render_registra_geracao_falhou_e_fica_em_roteiro(instalacao, tmp_path, monkeypatch):
    from expxmedia.producao.apresentacao import render

    def quebra(*a, **k):
        raise RuntimeError("render quebrou")

    monkeypatch.setattr(render, "renderizar", quebra)
    with pytest.raises(RuntimeError):
        producao.produzir(instalacao, _entrada(), mp4=True, cache_fontes=semear_cache(tmp_path / "fontes"))
    peca_json = next((instalacao / "pecas").rglob("peca.json"))
    peca = json.loads(peca_json.read_text(encoding="utf-8"))
    assert peca["status"] == "roteiro"
    falha = [e for e in _eventos(instalacao) if e["evento"] == "geracao_falhou"]
    assert len(falha) == 1 and falha[0]["capacidade"] == "renderizar_motion" and "render quebrou" in falha[0]["detalhe"]


# ---------------------------------------------------------------- funcional


@pytest.mark.integracao_local
def test_com_mp4_a_peca_lista_mp4_final_e_pngs_slide(instalacao, tmp_path, requer_binario):
    requer_binario("node")
    ffprobe = requer_binario("ffprobe")
    ativos = instalacao / "ativos"
    ativos.mkdir()
    Image.new("RGB", (1600, 900), (40, 90, 160)).save(ativos / "quadro.png")
    d = copy.deepcopy(EXEMPLO)
    d["slides"][7]["imagem"] = "quadro.png"
    # 30 quadros por slide: o render completo (240) é coberto em test_render; aqui importa o registro na peça
    r = producao.produzir(instalacao, {"deck": d, "ativos": "ativos"}, mp4=True, frames_por_slide=30,
                          cache_fontes=semear_cache(tmp_path / "fontes"))

    peca = modelo.carregar(instalacao, r["peca_id"])
    pasta = modelo.pasta(instalacao, r["peca_id"])
    finais = [a for a in peca["arquivos"] if a["papel"] == "final"]
    assert finais == [{"caminho": "saida/apresentacao.html", "papel": "final", "formato": "16:9"},
                      {"caminho": "saida/apresentacao.mp4", "papel": "final", "formato": "16:9"}]
    pngs = [a for a in peca["arquivos"] if a["papel"] == "slide"]
    assert pngs == [{"caminho": f"slides/slide_{n:02d}.png", "papel": "slide", "formato": "16:9"} for n in range(1, 10)]
    assert [s["arquivo"] for s in peca["slides"]] == [f"slides/slide_{n:02d}.png" for n in range(1, 10)]
    for a in pngs:
        with Image.open(pasta / a["caminho"]) as img:
            assert img.size == (1920, 1080)
    sonda = json.loads(subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,codec_name,nb_frames",
         "-of", "json", str(pasta / "saida" / "apresentacao.mp4")], capture_output=True, text=True, check=True).stdout)["streams"][0]
    assert (sonda["codec_name"], sonda["width"], sonda["height"], int(sonda["nb_frames"])) == ("h264", 1920, 1080, 9 * 30)
    assert peca["producao"]["capacidades"] == ["renderizar_motion"]
    assert peca["producao"]["provedores"] == {"renderizar_motion": "remotion"}
    assert peca["status"] == "produzida"
    assert not list((pasta / "saida").glob(".render-*"))
