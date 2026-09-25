"""T-07.06: template de aula embarcado e compilação de aulas em um episódio só (D-23, D-31).

Porta de cursos-ia/radar-ia-jev-completo (partes.json + gerar_srt.py): cada parte é um trecho [ini, fim) de
uma aula já produzida (fim null = até o fim), nada é regravado, e o SRT único repete a mesma regra de corte
em quadros: `from` acumulado, `trim = round(ini x FPS)`, `frames = round((fim - ini) x FPS)`.

- Integração: compilar duas aulas produzidas (uma pelo template embarcado) gera um MP4 com a soma das
  durações e um SRT com os tempos da segunda deslocados pela duração da primeira.
- Funcional: o template de aula passa em `template.validar` no modo template sem achado; a regra de corte
  do SRT é a da origem (legenda cortada na borda da parte, deslocamento pelo quadro acumulado).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from expxmedia.aula import compilar
from expxmedia.aula import cues as aula_cues
from expxmedia.nucleo import arquivos
from expxmedia.peca import modelo
from expxmedia.producao import aula
from expxmedia.template import galeria_local, validar
from expxmedia.video import ffmpeg
from fixtures.fontes_ficticias import semear_cache

TEMPLATES = Path(__file__).resolve().parents[3] / "templates"
PASTA = TEMPLATES / "aula" / "padrao"
MANIFESTO = json.loads((PASTA / "template.json").read_text(encoding="utf-8"))
EXEMPLO = json.loads((PASTA / "exemplo.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ funcional


def test_template_de_aula_passa_na_validacao_sem_achado():
    assert validar.validar_template(PASTA, modo="template") == []
    assert (MANIFESTO["tipo"], MANIFESTO["motor"], MANIFESTO["status"]) == ("aula", "remotion", "validado")
    assert MANIFESTO["template_id"].startswith("aula-padrao-")
    assert MANIFESTO["versoes"]["remotion"] == "4.0.528"
    # o exemplo é uma entrada completa da produção de aula, pelo template, e cada cena é um kind do template
    e = aula.ler_entrada(EXEMPLO)
    assert e["template"] == MANIFESTO["template_id"]
    assert {c["modo"] for c in e["cenas"]} <= set(MANIFESTO["kinds"])


def test_galeria_local_encontra_o_template_de_aula(instalacao):
    ids = [i["template_id"] for i in galeria_local.listar(instalacao) if (i["dados"] or {}).get("tipo") == "aula"]
    assert MANIFESTO["template_id"] in ids


def test_srt_compilado_segue_a_regra_de_corte_da_origem():
    # parte 1: [0, 4) de uma aula; parte 2: [2,47, fim=6) de outra
    leg1 = [{"start": 0.0, "end": 1.5, "lines": ["a"]}, {"start": 3.5, "end": 4.6, "lines": ["corta no fim"]},
            {"start": 4.7, "end": 5.5, "lines": ["fora"]}]
    leg2 = [{"start": 1.0, "end": 2.2, "lines": ["antes"]}, {"start": 2.3, "end": 3.0, "lines": ["corta no início"]},
            {"start": 3.1, "end": 5.0, "lines": ["b", "c"]}]
    caps, total = compilar.legendas_compiladas([
        {"ini": 0.0, "fim": 4.0, "legendas": leg1},
        {"ini": 2.47, "fim": 6.0, "legendas": leg2},
    ])
    # origem: cursos-ia/radar-ia-jev-completo/gerar_srt.py:16-19 — frames = round((fim - ini) x 30)
    assert total == 120 + round((6.0 - 2.47) * 30)
    off = 120 / 30 - 2.47
    assert [c["lines"] for c in caps] == [["a"], ["corta no fim"], ["corta no início"], ["b", "c"]]
    assert caps[1]["end"] == pytest.approx(4.0)
    assert caps[2]["start"] == pytest.approx(2.47 + off) and caps[2]["end"] == pytest.approx(3.0 + off)
    assert caps[3]["start"] == pytest.approx(3.1 + off) and caps[3]["end"] == pytest.approx(5.0 + off)


# ------------------------------------------------------------------ integração


def _com_avatar_id(raiz):
    alma = json.loads((raiz / "alma" / "alma.json").read_text(encoding="utf-8"))
    alma["porta_vozes"][0]["avatar"]["avatar_id"] = "avatar-ficticio-0001"
    (raiz / "alma" / "alma.json").write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")


@pytest.mark.integracao_local
def test_compilar_duas_aulas_soma_duracoes_e_desloca_o_srt(instalacao, tmp_path, monkeypatch, requer_binario):
    for b in ("node", "ffmpeg", "ffprobe"):
        requer_binario(b)
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    _com_avatar_id(instalacao)
    cache = semear_cache(tmp_path / "fontes")
    primeira = aula.produzir(instalacao, {**EXEMPLO, "formatos": ["16:9"]}, cache_fontes=cache)
    assert primeira["template"] == MANIFESTO["template_id"]
    assert modelo.carregar(instalacao, primeira["peca_id"])["template"] == MANIFESTO["template_id"]
    segunda = aula.produzir(instalacao, {
        "titulo": "Fermentação lenta", "formatos": ["16:9"], "avatar": False,
        "roteiro": "[[s1]] A fermentação lenta dá sabor ao pão. [[s2]] Deixe a massa na geladeira por uma noite.",
        "cenas": [{"cue": "s1", "titulo": "Fermentação lenta"}, {"cue": "s2", "titulo": "Uma noite na geladeira"}],
    }, cache_fontes=cache)

    r = compilar.compilar(instalacao, [{"peca_id": primeira["peca_id"], "ini": 0, "fim": None, "nome": "vitrine"},
                                       {"peca_id": segunda["peca_id"], "ini": 0, "fim": None, "nome": "fermentação"}],
                          titulo="Padaria completa", formato="16:9")
    d1 = aula_cues.ler(instalacao / primeira["pasta"] / "midia")["duration"]
    d2 = aula_cues.ler(instalacao / segunda["pasta"] / "midia")["duration"]
    video = instalacao / r["video"]
    info = ffmpeg.sondar(video)
    assert (info["largura"], info["altura"], info["fps"]) == (1920, 1080, "30/1")
    assert abs(info["duracao"] - (d1 + d2)) < 0.15, (info["duracao"], d1, d2)
    assert r["verificacao"]["aprovado"] is True, r["verificacao"]

    # o SRT: as legendas da primeira nos mesmos tempos, as da segunda deslocadas pela duração da primeira
    compilado = compilar.ler_srt(instalacao / r["srt"])
    leg1 = arquivos.ler_json(instalacao / primeira["pasta"] / "midia" / "legendas.json")
    leg2 = arquivos.ler_json(instalacao / segunda["pasta"] / "midia" / "legendas.json")
    assert len(compilado) == len(leg1) + len(leg2)
    desloc = round(d1 * 30) / 30
    assert compilado[0]["start"] == pytest.approx(leg1[0]["start"], abs=0.002)
    for c, original in zip(compilado[len(leg1):], leg2):
        assert c["lines"] == original["lines"]
        assert c["start"] == pytest.approx(original["start"] + desloc, abs=0.002)
    assert compilado[len(leg1)]["start"] > d1 - 0.05

    peca = modelo.carregar(instalacao, r["peca_id"])
    assert (peca["tipo"], peca["status"]) == ("aula", "produzida")
    assert peca["compoe"] == [primeira["peca_id"], segunda["peca_id"]]
    assert {(a["papel"], a["formato"]) for a in peca["arquivos"]} >= {("final", "16:9"), ("srt", "16:9")}
