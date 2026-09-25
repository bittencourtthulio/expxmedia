"""T-03.13: CLI da produção estática — produzir post/carrossel, capturar pagina e imagem (D-11)."""
from __future__ import annotations

import base64
import io
import json
import os
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from expxmedia import cli
from expxmedia.imagem import openrouter, pexels
from expxmedia.nucleo import arquivos, ids
from expxmedia.peca import modelo
from fixtures.fontes_ficticias import semear_cache
from stubs import higgsfield_falso
from stubs.servidor import ServidorStub

MOTOR = Path(__file__).resolve().parents[1]
ROTULOS = ["Série", "Método", "Prática"]
CARROSSEL = {
    "template": "carrossel-editorial-b74228",
    "titulo": "Sem atalho",
    "slides": [
        {"kind": "capa", "rotulos": ROTULOS, "chapeu": "Feito com cuidado dura mais", "titulo": "SEM ATALHO",
         "rodape": "perfil da empresa"},
        {"kind": "cta", "rotulos": ROTULOS, "col_esq": "Fazer rápido não é fazer bem.",
         "col_dir": "Salve para a próxima vez.", "rodape": "perfil da empresa"},
    ],
    "legenda": "Sem atalho. Salve para a próxima vez.",
}
POST = {
    "template": "post_unico-numero-e-frase-86c9ac",
    "titulo": "Doze perguntas",
    "slides": [{"kind": "numero", "numero": "12", "texto": "Perguntas para fazer antes de fechar qualquer pedido."}],
}


@pytest.fixture
def cache_xdg(tmp_path, monkeypatch):
    """Cache de fontes semeado no XDG_CACHE_HOME: vale para o subprocesso e para o processo."""
    xdg = tmp_path / "xdg"
    semear_cache(xdg / "expxmedia" / "fontes")
    monkeypatch.setenv("XDG_CACHE_HOME", str(xdg))
    return xdg


def _escrever(pasta: Path, nome: str, dados) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / nome
    arquivo.write_text(dados if isinstance(dados, str) else json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return arquivo


def _rodar(capsys, *argv):
    codigo = cli.main([str(a) for a in argv])
    return codigo, json.loads(capsys.readouterr().out)


# ---------------------------------------------------------------- integração


def test_produzir_carrossel_em_subprocesso_sai_0_e_imprime_o_peca_id(instalacao, cache_xdg, tmp_path):
    entrada = _escrever(tmp_path / "entrada", "slots.json", CARROSSEL)
    ambiente = {k: v for k, v in os.environ.items() if k != "EXPXMEDIA_PROVEDORES_TESTE"}
    feito = subprocess.run(
        ["uv", "run", "--project", str(MOTOR), "expxmedia-motor", "produzir", "carrossel",
         "--entrada", str(entrada), "--raiz", str(instalacao)],
        cwd=MOTOR, capture_output=True, text=True, timeout=300, env=ambiente,
    )
    assert feito.returncode == 0, feito.stdout + feito.stderr
    dados = json.loads(feito.stdout)
    assert dados["ok"] is True and ids.peca_id_valido(dados["peca_id"])
    peca = modelo.carregar(instalacao, dados["peca_id"])
    assert peca["status"] == "produzida" and [s["kind"] for s in peca["slides"]] == ["capa", "cta"]
    assert dados["pasta"].startswith("pecas/") and not Path(dados["pasta"]).is_absolute()


def test_produzir_post_no_processo(instalacao, cache_xdg, tmp_path, capsys):
    entrada = _escrever(tmp_path / "entrada", "post.json", POST)
    codigo, dados = _rodar(capsys, "produzir", "post", "--entrada", entrada, "--raiz", instalacao)
    assert codigo == 0, dados
    assert modelo.carregar(instalacao, dados["peca_id"])["tipo"] == "post_unico"


def test_capturar_pagina_grava_na_saida_relativa(instalacao, tmp_path, capsys):
    texto = "Texto de corpo para a captura pelo CLI, sem marca nenhuma, repetido para passar do piso. " * 20
    html = ("<!doctype html><html><head><meta charset='utf-8'><title>Página</title></head><body style='margin:0'>"
            + "".join(f"<section style='height:1000px'><h2 style='margin:0'>Seção número {i}</h2><p>{texto}</p></section>" for i in range(2))
            + "</body></html>").encode()
    with ServidorStub() as stub:
        stub.rota("GET", "/p", corpo=html, cabecalhos={"Content-Type": "text/html; charset=utf-8"})
        codigo, dados = _rodar(capsys, "capturar", "pagina", "--url", stub.url_de("/p"), "--saida", "midia/captura",
                               "--raiz", instalacao)
    assert codigo == 0, dados
    assert dados["saida"] == "midia/captura"
    assert [s["y"] for s in dados["captura"]["secoes"]] == [0, 1000]
    assert (instalacao / "midia" / "captura" / "tira.png").is_file()
    assert (instalacao / "midia" / "captura" / "site.md").is_file()


def _png_data_url():
    buf = io.BytesIO()
    Image.new("RGB", (40, 50), (10, 120, 200)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_imagem_openrouter_passa_pela_cota(instalacao, capsys, monkeypatch):
    (instalacao / ".env").write_text("OPENROUTER_API_KEY=chave-falsa\n", encoding="utf-8")
    resposta = {"choices": [{"message": {"content": "ok", "images": [{"type": "image_url", "image_url": {"url": _png_data_url()}}]}}]}
    with ServidorStub() as stub:
        stub.rota("POST", "/api/v1/chat/completions", json=resposta)
        monkeypatch.setattr(openrouter, "URL_BASE", stub.url)
        codigo, dados = _rodar(capsys, "imagem", "openrouter", "--prompt", "a loaf of bread on a table",
                               "--saida", "pecas/x/img.png", "--proporcao", "4:5", "--raiz", instalacao)
    assert codigo == 0, dados
    assert dados["caminho"] == "pecas/x/img.png" and (instalacao / "pecas/x/img.png").is_file()
    cotas = arquivos.ler_json(instalacao / "estado" / "cotas.json")
    assert sum(dia.get("openrouter", 0) for dia in cotas["dias"].values()) == 1


def test_imagem_openrouter_com_cota_estourada_nao_chama_o_provedor(instalacao, capsys, monkeypatch):
    from expxmedia.imagem import cota

    (instalacao / ".env").write_text("OPENROUTER_API_KEY=chave-falsa\n", encoding="utf-8")
    monkeypatch.setattr(cota, "TETOS", {"openrouter": 0, "higgsfield": 0})
    with ServidorStub() as stub:
        monkeypatch.setattr(openrouter, "URL_BASE", stub.url)
        codigo, dados = _rodar(capsys, "imagem", "openrouter", "--prompt", "a loaf of bread", "--saida", "pecas/x/i.png",
                               "--raiz", instalacao)
        assert stub.requisicoes == []
    assert codigo == cli.ERRO and dados["ok"] is False and dados["provedor"] == "openrouter"


def test_imagem_rosto_higgsfield_passa_pela_cota(instalacao, capsys, monkeypatch, tmp_path):
    alma = arquivos.ler_json(instalacao / "alma" / "alma.json")
    alma["porta_vozes"][0]["rosto_ia"]["id"] = "soul-ficticio-123"
    arquivos.gravar_json(instalacao / "alma" / "alma.json", alma)
    buf = io.BytesIO()
    Image.new("RGB", (48, 64), (90, 60, 30)).save(buf, "PNG")
    with ServidorStub() as stub:
        stub.rota("GET", "/resultado.png", corpo=buf.getvalue())
        pasta = tmp_path / "bin"
        higgsfield_falso.instalar(pasta)
        monkeypatch.setenv("PATH", str(pasta) + os.pathsep + os.environ.get("PATH", ""))
        monkeypatch.setenv("HIGGSFIELD_FALSO_LOG", str(tmp_path / "h.log"))
        monkeypatch.setenv("HIGGSFIELD_FALSO_URL", stub.url)
        codigo, dados = _rodar(capsys, "imagem", "rosto", "--porta-voz", "porta-voz-teste",
                               "--prompt", "standing behind a counter", "--saida", "pecas/r/rosto.png", "--raiz", instalacao)
    assert codigo == 0, dados
    cotas = arquivos.ler_json(instalacao / "estado" / "cotas.json")
    assert sum(dia.get("higgsfield", 0) for dia in cotas["dias"].values()) == 1


def test_imagem_pexels_e_retrato(instalacao, capsys, monkeypatch):
    foto = {"id": 7, "width": 3000, "height": 4000, "url": "https://www.pexels.com/photo/7/", "photographer": "Autora",
            "photographer_url": "https://www.pexels.com/@a", "alt": "bread on a table",
            "src": {"original": "http://x/o.jpg", "large2x": "http://x/l.jpg", "portrait": "http://x/p.jpg"}}
    codigo, dados = _rodar(capsys, "imagem", "pexels", "--termo", "bread", "--raiz", instalacao)
    assert codigo == cli.CAPACIDADE_NAO_HABILITADA and "PEXELS_API_KEY" in dados["como_habilitar"]
    (instalacao / ".env").write_text("PEXELS_API_KEY=chave-falsa\n", encoding="utf-8")
    with ServidorStub() as stub:
        stub.rota("GET", "/v1/search", json={"photos": [foto]})
        monkeypatch.setattr(pexels, "URL_BASE", stub.url)
        codigo, dados = _rodar(capsys, "imagem", "pexels", "--termo", "bread", "--raiz", instalacao)
    assert codigo == 0, dados
    assert [i["id"] for i in dados["itens"]] == [7] and dados["baixado"] is None

    codigo, dados = _rodar(capsys, "imagem", "retrato", "--raiz", instalacao)
    assert codigo == 0 and dados["tipo"] == "retrato"
    assert dados["caminho"] == "alma/assets/retratos/porta-voz-teste/01.png"


# ---------------------------------------------------------------- funcional


@pytest.mark.parametrize("conteudo, trecho", [
    ('{"template": "carrossel-editorial-b74228", "titulo": "x", "slides": [', "campo 'entrada': JSON inválido na linha 1"),
    ({**CARROSSEL, "slides": "não é lista"}, "campo 'slides'"),
    ({k: v for k, v in CARROSSEL.items() if k != "template"}, "campo 'template'"),
    ({**CARROSSEL, "legenda": None}, "campo 'legenda'"),
    ({**CARROSSEL, "cor": "#ff0000"}, "campo 'cor'"),
])
def test_entrada_invalida_sai_2_citando_o_campo(instalacao, tmp_path, capsys, conteudo, trecho):
    entrada = _escrever(tmp_path / "entrada", "slots.json", conteudo)
    codigo, dados = _rodar(capsys, "produzir", "carrossel", "--entrada", entrada, "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA
    assert dados["ok"] is False and trecho in dados["mensagem"]
    assert list((instalacao / "pecas").rglob("*")) == []


def test_slots_acima_do_max_saem_2_com_a_lista_de_erros(instalacao, tmp_path, capsys):
    slots = json.loads(json.dumps(CARROSSEL))
    slots["slides"][0]["titulo"] = "X" * 23
    entrada = _escrever(tmp_path / "entrada", "slots.json", slots)
    codigo, dados = _rodar(capsys, "produzir", "carrossel", "--entrada", entrada, "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and dados["erro"] == "slots_invalidos"
    assert dados["erros"] == ["slide 1 (capa), slot 'titulo': 23 caracteres, o template aguenta 22"]


def test_entrada_inexistente_sai_2(instalacao, capsys, tmp_path):
    codigo, dados = _rodar(capsys, "produzir", "post", "--entrada", tmp_path / "nao.json", "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and "campo 'entrada'" in dados["mensagem"]


def test_subcomandos_aparecem_no_help(capsys):
    for grupo, subs in (("produzir", ("post", "carrossel")), ("capturar", ("pagina",)),
                        ("imagem", ("pexels", "openrouter", "retrato", "rosto"))):
        codigo = cli.main([grupo, "--help"])
        saida = capsys.readouterr().out
        assert codigo == 0 and all(s in saida for s in subs), (grupo, saida)
