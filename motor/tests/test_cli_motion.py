"""T-05.12: CLI de motion — produzir reel, produzir apresentacao, motion previa e motion render (D-11).

- Integração: cada subcomando novo aparece no --help, e `produzir apresentacao` na fixture, em subprocesso,
  sai 0 com o peca_id.
- Funcional: `produzir reel` com roteiro de 100 palavras sai com código diferente de 0 e JSON citando a faixa
  130 a 180, sem narrar.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from expxmedia import cli
from expxmedia.motion import remotion
from expxmedia.narrar import base as narrar_base
from expxmedia.nucleo import ids
from expxmedia.peca import modelo
from fixtures.fontes_ficticias import semear_cache

MOTOR = Path(__file__).resolve().parents[1]
TEMPLATES = MOTOR.parent / "templates"
EXEMPLO_REEL = json.loads((TEMPLATES / "reel" / "narrado-cartao" / "exemplo.json").read_text(encoding="utf-8"))
EXEMPLO_DECK = json.loads((TEMPLATES / "apresentacao" / "padrao" / "exemplo.json").read_text(encoding="utf-8"))
TIMELINE = {"fps": 30, "totalFrames": 90, "blocos": [],
            "cenas": [{"id": "abre", "inicio": 0, "dur": 30}, {"id": "meio", "inicio": 30, "dur": 25},
                      {"id": "fecha", "inicio": 55, "dur": 35}]}


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


def _reel_100_palavras() -> dict:
    """O exemplo do template sem 4 frases fora das âncoras: 143 - 43 = 100 palavras, âncoras e CTA intactos."""
    frases = re.split(r"(?<=[.?!])\s+", EXEMPLO_REEL["roteiro"])
    fora = {"Depois escolhe", "Com ele você", "É decidir antes", "E salva este"}
    roteiro = " ".join(f for f in frases if not any(f.startswith(x) for x in fora))
    return {**copy.deepcopy(EXEMPLO_REEL), "roteiro": roteiro}


# ---------------------------------------------------------------- integração


def test_subcomandos_novos_aparecem_no_help(capsys):
    for argv, esperados in ((["produzir", "--help"], ("reel", "apresentacao")),
                            (["motion", "--help"], ("previa", "render")),
                            (["produzir", "apresentacao", "--help"], ("--entrada", "--mp4")),
                            (["produzir", "reel", "--help"], ("--entrada",)),
                            (["motion", "previa", "--help"], ("--composicao", "--timeline", "--saida")),
                            (["motion", "render", "--help"], ("--composicao", "--saida", "--props"))):
        codigo = cli.main(argv)
        saida = capsys.readouterr().out
        assert codigo == 0 and all(e in saida for e in esperados), (argv, saida)
    codigo = cli.main(["--help"])
    assert codigo == 0 and "motion" in capsys.readouterr().out


def test_produzir_apresentacao_em_subprocesso_sai_0_com_o_peca_id(instalacao, cache_xdg, tmp_path):
    entrada = _escrever(tmp_path / "entrada", "apresentacao.json", {"deck": EXEMPLO_DECK})
    ambiente = {k: v for k, v in os.environ.items() if k != "EXPXMEDIA_PROVEDORES_TESTE"}
    feito = subprocess.run(
        ["uv", "run", "--project", str(MOTOR), "expxmedia-motor", "produzir", "apresentacao",
         "--entrada", str(entrada), "--raiz", str(instalacao)],
        cwd=MOTOR, capture_output=True, text=True, timeout=300, env=ambiente,
    )
    assert feito.returncode == 0, feito.stdout + feito.stderr
    dados = json.loads(feito.stdout)
    assert dados["ok"] is True and ids.peca_id_valido(dados["peca_id"])
    peca = modelo.carregar(instalacao, dados["peca_id"])
    assert (peca["status"], peca["tipo"]) == ("produzida", "apresentacao")
    assert {"caminho": "saida/apresentacao.html", "papel": "final", "formato": "16:9"} in peca["arquivos"]
    assert len(dados["slides"]) == len(EXEMPLO_DECK["slides"])
    assert dados["pasta"].startswith("pecas/") and not Path(dados["pasta"]).is_absolute()


def test_motion_previa_devolve_caminhos_relativos_a_raiz(instalacao, tmp_path, capsys, monkeypatch):
    pedidos = {}

    def still_falso(composicao, quadros, pasta, props=None, *, escala, nomes, **kw):
        pedidos.update(composicao=composicao, quadros=quadros, props=props, escala=escala, kw=kw)
        feitos = []
        for nome in nomes:
            p = Path(pasta) / nome
            Image.new("RGB", (round(1080 * escala), round(1920 * escala)), (20, 40, 200)).save(p)
            feitos.append(p)
        return feitos

    monkeypatch.setattr(remotion, "stills", still_falso)
    timeline = _escrever(tmp_path / "entrada", "timeline.json", TIMELINE)
    props = _escrever(tmp_path / "entrada", "props.json", {"duracaoFrames": 90})
    codigo, dados = _rodar(capsys, "motion", "previa", "--composicao", "Vazio", "--timeline", timeline,
                           "--props", props, "--saida", "pecas/x/previa", "--raiz", instalacao)
    assert codigo == 0, dados
    assert dados["quadros"] == [18, 45, 76]  # 60% de cada cena
    assert dados["folha"] == "pecas/x/previa/previa.jpg" and (instalacao / dados["folha"]).is_file()
    assert dados["imagens"] == ["pecas/x/previa/previa-01-abre.png", "pecas/x/previa/previa-02-meio.png",
                                "pecas/x/previa/previa-03-fecha.png"]
    assert pedidos["composicao"] == "Vazio" and pedidos["props"] == {"duracaoFrames": 90}
    assert pedidos["escala"] == 0.3 and pedidos["kw"]["versao"] == remotion.VERSAO_KIT


@pytest.mark.integracao_local
def test_motion_render_do_vazio(instalacao, tmp_path, capsys, requer_binario):
    requer_binario("node")
    props = _escrever(tmp_path / "entrada", "props.json", {"duracaoFrames": 30})
    codigo, dados = _rodar(capsys, "motion", "render", "--composicao", "Vazio", "--props", props,
                           "--saida", "midia/vazio.mp4", "--raiz", instalacao)
    assert codigo == 0, dados
    assert dados == {"ok": True, "video": "midia/vazio.mp4"}
    assert (instalacao / "midia" / "vazio.mp4").stat().st_size > 0


# ---------------------------------------------------------------- funcional


def test_produzir_reel_com_100_palavras_sai_nao_zero_citando_130_a_180(instalacao, tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    chamadas = []
    monkeypatch.setattr(narrar_base, "narrar", lambda *a, **k: chamadas.append(a))
    dados_reel = _reel_100_palavras()
    assert len(dados_reel["roteiro"].split()) == 100
    entrada = _escrever(tmp_path / "entrada", "reel.json", dados_reel)
    codigo, dados = _rodar(capsys, "produzir", "reel", "--entrada", entrada, "--raiz", instalacao)
    assert codigo != 0 and codigo == cli.ENTRADA_INVALIDA
    assert dados["ok"] is False and dados["erro"] == "roteiro_reprovado"
    assert "130 a 180" in json.dumps(dados, ensure_ascii=False)
    assert [(a["checagem"], a["obtido"]) for a in dados["achados"]] == [("palavras", 100)]
    assert chamadas == []  # reprovado antes de narrar
    assert modelo.carregar(instalacao, dados["peca_id"])["status"] == "roteiro"


def test_produzir_reel_entrada_invalida_sai_2_citando_o_campo(instalacao, tmp_path, capsys):
    semcenas = {k: v for k, v in EXEMPLO_REEL.items() if k != "cenas"}
    for conteudo, trecho in ((semcenas, "campo 'cenas'"), ({**EXEMPLO_REEL, "cor": "#ff0000"}, "campo 'cor'"),
                             ("{ruim", "campo 'entrada': JSON inválido")):
        entrada = _escrever(tmp_path / "entrada", "reel.json", conteudo)
        codigo, dados = _rodar(capsys, "produzir", "reel", "--entrada", entrada, "--raiz", instalacao)
        assert codigo == cli.ENTRADA_INVALIDA and trecho in dados["mensagem"], dados
    assert list((instalacao / "pecas").rglob("peca.json")) == []


def test_produzir_apresentacao_deck_invalido_sai_2_com_achados(instalacao, tmp_path, capsys):
    ruim = copy.deepcopy(EXEMPLO_DECK)
    ruim["slides"][2]["tipo"] = "grafico"
    entrada = _escrever(tmp_path / "entrada", "apresentacao.json", {"deck": ruim})
    codigo, dados = _rodar(capsys, "produzir", "apresentacao", "--entrada", entrada, "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and dados["erro"] == "deck_invalido" and dados["achados"]
    assert list((instalacao / "pecas").rglob("peca.json")) == []


def test_motion_erros_de_entrada_e_do_remotion(instalacao, tmp_path, capsys):
    ruim = _escrever(tmp_path / "entrada", "timeline.json", {"cenas": [{"id": "a", "inicio": "0", "dur": 30}]})
    codigo, dados = _rodar(capsys, "motion", "previa", "--composicao", "Vazio", "--timeline", ruim,
                           "--saida", "pecas/x/previa", "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and "campo 'timeline'" in dados["mensagem"]

    lista = _escrever(tmp_path / "entrada", "props.json", [1, 2])
    codigo, dados = _rodar(capsys, "motion", "render", "--composicao", "Vazio", "--props", lista,
                           "--saida", "midia/v.mp4", "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and "campo 'props'" in dados["mensagem"]

    codigo, dados = _rodar(capsys, "motion", "render", "--composicao", "Vazio", "--saida", str(tmp_path / "v.mp4"),
                           "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and "M9" in dados["mensagem"]

    codigo, dados = _rodar(capsys, "motion", "render", "--composicao", "../fora", "--saida", "midia/v.mp4",
                           "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and "nome de composição inválido" in dados["mensagem"]

    codigo, dados = _rodar(capsys, "motion", "render", "--composicao", "NaoExiste", "--saida", "midia/v.mp4",
                           "--raiz", instalacao)
    assert codigo == cli.ERRO and dados["erro"] == "remotion" and "NaoExiste" in dados["mensagem"]
    assert not (instalacao / "midia" / "v.mp4").exists()
