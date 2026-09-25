"""T-07.07: CLI de aula e avatar (D-11, D-26, D-32).

    produzir aula       --entrada aula.json [--embarcados PASTA]
    aula compilar       --partes partes.json --titulo T [--formato F] [--serie S]
    aula editar-tela    --cues ... --janelas janelas.json --saida ... [--json ...] [--marcas ...] [--cue-final C]
    avatar gerar        --audio ... --saida ... [--porta-voz ID]

- Integração: cada subcomando novo aparece no --help e `produzir aula` com o provedor de teste, em
  subprocesso, sai 0 com o peca_id.
- Funcional: `avatar gerar` sem HEYGEN_API_KEY e sem provedor de teste sai com código 3 e a orientação de
  como_habilitar, sem gerar nada.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from expxmedia import cli
from expxmedia.nucleo import ids
from expxmedia.peca import modelo
from fixtures.fontes_ficticias import semear_cache

MOTOR = Path(__file__).resolve().parents[1]
ROTEIRO = "[[s1]] A massa descansa antes de ir ao forno. [[s2]] Assim o pão cresce por igual e fica leve."


def _rodar(capsys, *argv):
    codigo = cli.main([str(a) for a in argv])
    return codigo, json.loads(capsys.readouterr().out)


def _com_avatar_id(raiz):
    alma = json.loads((raiz / "alma" / "alma.json").read_text(encoding="utf-8"))
    alma["porta_vozes"][0]["avatar"]["avatar_id"] = "avatar-ficticio-0001"
    (raiz / "alma" / "alma.json").write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")


def _mp3(raiz, requer_binario, segundos=2):
    requer_binario("ffmpeg")
    destino = raiz / "pecas" / "audio" / "narracao.mp3"
    destino.parent.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=220:duration={segundos}",
                    "-c:a", "libmp3lame", "-b:a", "128k", str(destino)], check=True, capture_output=True)
    return "pecas/audio/narracao.mp3"


# ---------------------------------------------------------------- integração


def test_subcomandos_novos_aparecem_no_help(capsys):
    for argv, esperados in ((["produzir", "--help"], ("aula",)),
                            (["aula", "--help"], ("compilar", "editar-tela")),
                            (["avatar", "--help"], ("gerar",)),
                            (["produzir", "aula", "--help"], ("--entrada", "--embarcados")),
                            (["aula", "compilar", "--help"], ("--partes", "--titulo", "--formato")),
                            (["aula", "editar-tela", "--help"], ("--cues", "--janelas", "--saida", "--marcas")),
                            (["avatar", "gerar", "--help"], ("--audio", "--saida", "--porta-voz"))):
        codigo = cli.main(argv)
        saida = capsys.readouterr().out
        assert codigo == 0 and all(e in saida for e in esperados), (argv, saida)
    codigo = cli.main(["--help"])
    saida = capsys.readouterr().out
    assert codigo == 0 and "aula" in saida and "avatar" in saida


@pytest.mark.integracao_local
def test_produzir_aula_em_subprocesso_sai_0_com_o_peca_id(instalacao, tmp_path, requer_binario):
    for b in ("node", "ffmpeg", "ffprobe", "uv"):
        requer_binario(b)
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    xdg = tmp_path / "xdg"
    semear_cache(xdg / "expxmedia" / "fontes")
    entrada = tmp_path / "entrada" / "aula.json"
    entrada.parent.mkdir()
    entrada.write_text(json.dumps({
        "titulo": "Massa que descansa", "roteiro": ROTEIRO, "formatos": ["16:9"],
        "cenas": [{"cue": "s1", "titulo": "A massa descansa"}, {"cue": "s2", "titulo": "Pão leve", "itens": ["cresce por igual"]}],
    }, ensure_ascii=False), encoding="utf-8")
    ambiente = {k: v for k, v in os.environ.items() if k != "EXPXMEDIA_PROVEDORES_TESTE"}
    ambiente["XDG_CACHE_HOME"] = str(xdg)
    feito = subprocess.run(
        ["uv", "run", "--project", str(MOTOR), "expxmedia-motor", "produzir", "aula", "--entrada", str(entrada),
         "--raiz", str(instalacao)],
        cwd=MOTOR, capture_output=True, text=True, timeout=600, env=ambiente,
    )
    assert feito.returncode == 0, feito.stdout + feito.stderr
    dados = json.loads(feito.stdout)
    assert dados["ok"] is True and ids.peca_id_valido(dados["peca_id"])
    peca = modelo.carregar(instalacao, dados["peca_id"])
    assert (peca["tipo"], peca["status"]) == ("aula", "produzida")
    assert dados["videos"] == {"16:9": f"{dados['pasta']}/saida/aula-16x9.mp4"}
    assert not Path(dados["pasta"]).is_absolute() and dados["verificacao"]["16:9"]["aprovado"] is True
    # sem avatar_id no porta-voz o avatar não está habilitado: a aula sai sem ele, com aviso
    assert dados["avatar"] is None and any("avatar" in a for a in dados["avisos"])


@pytest.mark.integracao_local
def test_avatar_gerar_com_provedor_de_teste_sai_0(instalacao, capsys, requer_binario, monkeypatch):
    requer_binario("ffprobe")
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    _com_avatar_id(instalacao)
    audio = _mp3(instalacao, requer_binario)
    codigo, dados = _rodar(capsys, "avatar", "gerar", "--audio", audio, "--saida", "pecas/audio/avatar.mp4",
                           "--raiz", instalacao)
    assert codigo == 0, dados
    assert dados["provedor"] == "teste" and dados["arquivo"] == "pecas/audio/avatar.mp4"
    assert (instalacao / "pecas" / "audio" / "avatar.mp4").is_file()


def test_aula_compilar_com_uma_parte_sai_2(instalacao, capsys, tmp_path):
    partes = tmp_path / "partes.json"
    partes.write_text(json.dumps([{"peca_id": "P-20260925-AAAA", "ini": 0, "fim": None, "nome": "só uma"}]), encoding="utf-8")
    codigo, dados = _rodar(capsys, "aula", "compilar", "--partes", partes, "--titulo", "x", "--raiz", instalacao)
    assert codigo == 2 and dados["erro"] == "entrada_invalida" and "partes" in dados["mensagem"]


def test_produzir_aula_com_cena_sem_marcador_sai_2(instalacao, capsys, tmp_path):
    entrada = tmp_path / "aula.json"
    entrada.write_text(json.dumps({"titulo": "x", "roteiro": ROTEIRO, "cenas": [{"cue": "s7", "titulo": "?"}]}),
                       encoding="utf-8")
    codigo, dados = _rodar(capsys, "produzir", "aula", "--entrada", entrada, "--raiz", instalacao)
    assert codigo == 2 and "cenas" in dados["mensagem"] and "s7" in dados["mensagem"]
    assert list((instalacao / "pecas").rglob("peca.json")) == []


# ---------------------------------------------------------------- funcional


@pytest.mark.integracao_local
def test_avatar_gerar_sem_chave_e_sem_teste_sai_3_com_como_habilitar(instalacao, capsys, requer_binario, monkeypatch):
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    monkeypatch.delenv("HEYGEN_API_KEY", raising=False)
    (instalacao / ".env").write_text("", encoding="utf-8")
    _com_avatar_id(instalacao)
    audio = _mp3(instalacao, requer_binario)
    codigo, dados = _rodar(capsys, "avatar", "gerar", "--audio", audio, "--saida", "pecas/audio/avatar.mp4",
                           "--raiz", instalacao)
    assert codigo == cli.CAPACIDADE_NAO_HABILITADA == 3, dados
    assert dados["ok"] is False and dados["erro"] == "capacidade_nao_habilitada"
    assert "HEYGEN_API_KEY" in dados["como_habilitar"]
    assert not (instalacao / "pecas" / "audio" / "avatar.mp4").exists()
