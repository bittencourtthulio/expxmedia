"""T-05.03: runner Remotion multi-versão (D-17, D-46).

- Integração: renderizar a composição Vazio por 2 s com props JSON gera MP4 de 60 quadros.
- Funcional: pedir a 4.0.522 resolve um diretório de cache diferente do da 4.0.528 sem instalar
  nada; uma composição quebrada em outra pasta de src/composicoes não impede o render da pedida
  (o bundle é feito por um entry point próprio que registra só ela).
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from expxmedia.motion import remotion

MOTOR = Path(__file__).resolve().parents[2]
KIT = MOTOR / "kit-remotion"


def _quadros(mp4):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
         "stream=nb_read_frames,width,height,r_frame_rate,codec_name", "-of", "json", str(mp4)],
        capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["streams"][0]


# ---------------------------------------------------------------- constantes e resolução


def test_numeros_da_origem():
    assert remotion.VERSAO_KIT == "4.0.528"
    assert remotion.TEMPO_RENDER_S == 1800
    assert remotion.KIT == KIT


def test_versao_do_kit_usa_o_proprio_kit(tmp_path):
    assert remotion.diretorio_projeto("4.0.528", cache=tmp_path) == KIT
    assert remotion.diretorio_projeto(cache=tmp_path) == KIT


def test_outra_versao_resolve_cache_por_versao_sem_instalar(tmp_path, monkeypatch):
    chamadas = []
    monkeypatch.setattr(remotion.subprocess, "run", lambda *a, **k: chamadas.append((a, k)))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    d522 = remotion.diretorio_projeto("4.0.522")
    assert d522 == tmp_path / "xdg" / "expxmedia" / "remotion" / "4.0.522"
    assert d522 != remotion.diretorio_projeto("4.0.528")
    assert remotion.diretorio_projeto("4.0.522", cache=tmp_path / "c") == tmp_path / "c" / "4.0.522"
    assert remotion.diretorio_projeto("4.0.500", cache=tmp_path / "c") != tmp_path / "c" / "4.0.522"
    monkeypatch.delenv("XDG_CACHE_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "casa"))
    assert remotion.diretorio_projeto("4.0.522") == tmp_path / "casa" / ".cache" / "expxmedia" / "remotion" / "4.0.522"
    # sem projeto preparado: erro claro, nenhum processo rodado, nada criado no cache
    with pytest.raises(remotion.ErroRemotion) as erro:
        remotion.renderizar("Vazio", tmp_path / "x.mp4", {"duracaoFrames": 60}, versao="4.0.522", cache=tmp_path / "c")
    assert "4.0.522" in str(erro.value) and "não está preparada" in str(erro.value)
    assert chamadas == []
    assert not (tmp_path / "c").exists()
    assert not remotion.projeto_pronto(d522)


def test_versao_invalida_e_recusada(tmp_path):
    for ruim in ("latest", "4.0", "../4.0.528", "^4.0.528"):
        with pytest.raises(ValueError):
            remotion.diretorio_projeto(ruim, cache=tmp_path)


def test_kit_esta_pronto_na_versao_travada():
    assert remotion.projeto_pronto(KIT)
    assert remotion.navegador_compartilhado() is not None


def test_composicao_inexistente_ou_nome_invalido(tmp_path):
    with pytest.raises(remotion.ErroRemotion, match="NaoExiste"):
        remotion.renderizar("NaoExiste", tmp_path / "x.mp4")
    with pytest.raises(ValueError):
        remotion.renderizar("../Vazio", tmp_path / "x.mp4")


def test_entry_registra_so_a_composicao_pedida(tmp_path):
    with remotion.entrada_temporaria(KIT, "Vazio") as entrada:
        texto = entrada.read_text(encoding="utf-8")
        assert entrada.is_relative_to(KIT / "out")
        assert "registerRoot" in texto and "composicoes/Vazio" in texto
        assert "registro.generated" not in texto and "TesteSelo" not in texto
    assert not entrada.parent.exists(), "entry temporário tem de ser apagado"


# ---------------------------------------------------------------- integração


@pytest.mark.integracao_local
def test_render_vazio_2s_com_props_gera_60_quadros(tmp_path, requer_binario):
    requer_binario("node")
    requer_binario("ffprobe")
    saida = remotion.renderizar("Vazio", tmp_path / "vazio.mp4", {"duracaoFrames": 60})
    assert saida == tmp_path / "vazio.mp4" and saida.stat().st_size > 0
    info = _quadros(saida)
    assert int(info["nb_read_frames"]) == 60
    assert (info["width"], info["height"], info["r_frame_rate"], info["codec_name"]) == (1080, 1920, "30/1", "h264")
    assert not list((KIT / "out" / "entradas").glob("*")) if (KIT / "out" / "entradas").exists() else True


@pytest.mark.integracao_local
def test_composicao_quebrada_em_outra_pasta_nao_impede_o_render(tmp_path, requer_binario):
    node = requer_binario("node")
    requer_binario("ffprobe")
    projeto = tmp_path / "kit"
    projeto.mkdir()
    for nome in ("package.json", "tsconfig.json"):
        shutil.copy(KIT / nome, projeto / nome)
    shutil.copytree(KIT / "scripts", projeto / "scripts")
    shutil.copytree(KIT / "src", projeto / "src", ignore=shutil.ignore_patterns("registro.generated.ts"))
    os.symlink(KIT / "node_modules", projeto / "node_modules")
    quebrada = projeto / "src" / "composicoes" / "Quebrada"
    quebrada.mkdir()
    (quebrada / "index.tsx").write_text(
        'import { naoExiste } from "pacote-que-nao-existe";\nexport const composicao = naoExiste(;\n', encoding="utf-8"
    )
    assert subprocess.run([node, "scripts/registrar.mjs"], cwd=projeto, capture_output=True, timeout=60).returncode == 0
    # prova de que a quebrada derruba o bundle de todas pelo index.ts do kit
    r = subprocess.run([node, "node_modules/@remotion/cli/remotion-cli.js", "compositions", "src/index.ts", "--log=error"],
                       cwd=projeto, capture_output=True, text=True, timeout=600)
    assert r.returncode != 0
    # o runner, com entry próprio, renderiza a pedida
    saida = remotion.renderizar("Vazio", tmp_path / "vazio.mp4", {"duracaoFrames": 30}, projeto=projeto)
    assert int(_quadros(saida)["nb_read_frames"]) == 30
    assert not any((projeto / "out" / "entradas").glob("*"))


@pytest.mark.integracao_local
def test_render_que_falha_devolve_o_fim_da_saida(tmp_path, requer_binario):
    requer_binario("node")
    # TesteSelo sem `alma` nas props: a composição lança erro e o runner cita o motivo
    with pytest.raises(remotion.ErroRemotion) as erro:
        remotion.renderizar("TesteSelo", tmp_path / "x.mp4", {"alma": None})
    assert "Alma inválida" in str(erro.value) or "alma" in str(erro.value).lower()
    assert len(str(erro.value)) <= 1500 + 200
