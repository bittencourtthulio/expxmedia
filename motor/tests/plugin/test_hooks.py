"""T-09.01: manifesto do plugin e os hooks de portão e de segredo (D-33, CONTRATO-alma, CONTRATO-pack).

- `expxmedia-portao.sh` (UserPromptSubmit): falha aberta, sempre sai 0. Sem Alma confirmada injeta a
  instrução de rodar /expxmedia:alma; com Alma e sem .env, /expxmedia:ambiente; portão aberto, nada.
- `expxmedia-segredo.sh` (PreToolUse): falha fechada. Leitura, escrita ou comando sobre .env, tokens
  e client_secret sai 2 com o motivo no stderr; o resto sai 0.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from expxmedia.alma import carregar

REPO = Path(__file__).resolve().parents[3]
NUCLEO = REPO / "nucleo"
HOOKS = NUCLEO / "hooks"
PORTAO = HOOKS / "expxmedia-portao.sh"
SEGREDO = HOOKS / "expxmedia-segredo.sh"


def _rodar(script, payload, *, projeto=None, cwd=None, bruto=None):
    ambiente = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if projeto is not None:
        ambiente["CLAUDE_PROJECT_DIR"] = str(projeto)
    entrada = bruto if bruto is not None else json.dumps(payload)
    return subprocess.run(
        ["bash", str(script)], input=entrada, capture_output=True, text=True, timeout=30,
        env=ambiente, cwd=str(cwd) if cwd else None,
    )


def _prompt(raiz, texto="quero um carrossel sobre a fornada de amanhã"):
    return {"hook_event_name": "UserPromptSubmit", "prompt": texto, "cwd": str(raiz), "session_id": "s1"}


def _contexto(feito):
    if not feito.stdout.strip():
        return None
    return json.loads(feito.stdout)["hookSpecificOutput"]["additionalContext"]


def _ferramenta(nome, **entrada):
    return {"hook_event_name": "PreToolUse", "tool_name": nome, "tool_input": entrada, "cwd": "/tmp", "session_id": "s1"}


# ---------------------------------------------------------------- integração


@pytest.mark.integracao_local
def test_plugin_valida_no_claude(requer_binario):
    claude = requer_binario("claude")
    feito = subprocess.run([claude, "plugin", "validate", "nucleo"], cwd=REPO, capture_output=True, text=True, timeout=120)
    assert feito.returncode == 0, feito.stdout + feito.stderr
    # sem aviso também: o runtime tolera, mas aviso de hook vira falha em caminho com espaço
    estrito = subprocess.run([claude, "plugin", "validate", "--strict", "nucleo"], cwd=REPO, capture_output=True,
                             text=True, timeout=120)
    assert estrito.returncode == 0, estrito.stdout + estrito.stderr


def test_manifesto_e_hooks_registrados():
    manifesto = json.loads((NUCLEO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifesto["name"] == "expxmedia"
    registro = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    portao = [h["command"] for g in registro["UserPromptSubmit"] for h in g["hooks"]]
    assert portao == ['"${CLAUDE_PLUGIN_ROOT}/hooks/expxmedia-portao.sh"']
    segredo = registro["PreToolUse"]
    assert [h["command"] for g in segredo for h in g["hooks"]] == ['"${CLAUDE_PLUGIN_ROOT}/hooks/expxmedia-segredo.sh"']
    casador = segredo[0]["matcher"].split("|")
    assert {"Read", "Edit", "Write", "Bash"} <= set(casador)
    for script in (PORTAO, SEGREDO):
        assert os.access(script, os.X_OK), f"{script.name} sem permissão de execução"


def test_segredo_bloqueia_read_de_env_com_codigo_2_e_motivo():
    feito = _rodar(SEGREDO, _ferramenta("Read", file_path="/instalacao/.env"))
    assert feito.returncode == 2
    assert ".env" in feito.stderr and "/expxmedia:ambiente" in feito.stderr
    assert feito.stdout == ""


@pytest.mark.parametrize("nome,entrada", [
    ("Read", {"file_path": "/x/.env.local"}),
    ("Edit", {"file_path": "/x/.env", "old_string": "A=", "new_string": "A=1"}),
    ("Write", {"file_path": "/x/.env", "content": "ELEVENLABS_API_KEY=abc"}),
    ("MultiEdit", {"file_path": "/x/.env", "edits": []}),
    ("Read", {"file_path": "/x/credenciais/client_secret_123.json"}),
    ("Read", {"file_path": "/x/token.json"}),
    ("Read", {"file_path": "/x/.expxmedia/youtube_tokens.pickle"}),
    ("Grep", {"pattern": "KEY", "path": "/x/.env"}),
    ("Bash", {"command": "cat .env"}),
    ("Bash", {"command": "grep API_KEY /x/.env | head"}),
    ("Bash", {"command": "source ./.env && run"}),
    ("Bash", {"command": "cp .env.example .env"}),
    ("Bash", {"command": "cat credenciais/client_secret.json"}),
    ("Bash", {"command": "cat token.json"}),
    ("Bash", {"command": "echo $ELEVENLABS_API_KEY"}),
    ("Bash", {"command": "echo ${META_GRAPH_TOKEN}"}),
    ("Bash", {"command": "printenv"}),
])
def test_segredo_bloqueia_env_tokens_e_client_secret(nome, entrada):
    feito = _rodar(SEGREDO, _ferramenta(nome, **entrada))
    assert feito.returncode == 2, (nome, entrada, feito.stderr)
    assert "expxmedia-segredo" in feito.stderr


@pytest.mark.parametrize("nome,entrada", [
    ("Read", {"file_path": "/x/.env.example"}),
    ("Read", {"file_path": "/x/alma/alma.json"}),
    ("Read", {"file_path": "/x/docs/tokens-de-cor.md"}),
    ("Write", {"file_path": "/x/nucleo/skills/ambiente/SKILL.md", "content": "Cole a chave no .env, nunca na conversa."}),
    ("Edit", {"file_path": "/x/motor/src/modulo.py", "old_string": "os.environ", "new_string": "process.env.X"}),
    ("Bash", {"command": "cat .env.example"}),
    ("Bash", {"command": "expxmedia-motor capacidades"}),
    ("Bash", {"command": "node -e 'console.log(process.env.HOME)'"}),
    ("Bash", {"command": "ls .envrc && uv run pytest"}),
    ("Bash", {"command": "env FOO=1 uv run pytest"}),
    ("Glob", {"pattern": "**/*.md"}),
])
def test_segredo_libera_o_resto(nome, entrada):
    feito = _rodar(SEGREDO, _ferramenta(nome, **entrada))
    assert feito.returncode == 0, (nome, entrada, feito.stderr)


@pytest.mark.parametrize("bruto", ["", "isto não é json", "[1, 2]", '{"tool_name": "Read", "tool_input": "x"}'])
def test_segredo_falha_fechado_com_payload_ilegivel(bruto):
    feito = _rodar(SEGREDO, None, bruto=bruto)
    assert feito.returncode == 2
    assert "expxmedia-segredo" in feito.stderr


# ---------------------------------------------------------------- funcional


def test_portao_sem_alma_manda_para_alma_e_sai_0(tmp_path):
    raiz = tmp_path / "vazia"
    raiz.mkdir()
    feito = _rodar(PORTAO, _prompt(raiz), projeto=raiz)
    assert feito.returncode == 0, feito.stderr
    contexto = _contexto(feito)
    assert "/expxmedia:alma" in contexto
    assert "/expxmedia:ambiente" not in contexto
    assert json.loads(feito.stdout)["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


def test_portao_alma_nao_confirmada_manda_para_alma(instalacao):
    caminho = instalacao / "alma" / "alma.json"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["confirmada_em"] = None
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    feito = _rodar(PORTAO, _prompt(instalacao), projeto=instalacao)
    assert feito.returncode == 0
    assert "/expxmedia:alma" in _contexto(feito)


def test_portao_alma_ilegivel_manda_para_alma(instalacao):
    (instalacao / "alma" / "alma.json").write_text("{ quebrado", encoding="utf-8")
    feito = _rodar(PORTAO, _prompt(instalacao), projeto=instalacao)
    assert feito.returncode == 0
    assert "/expxmedia:alma" in _contexto(feito)


def test_portao_sem_env_manda_para_ambiente(instalacao):
    (instalacao / ".env").unlink()
    feito = _rodar(PORTAO, _prompt(instalacao), projeto=instalacao)
    assert feito.returncode == 0
    contexto = _contexto(feito)
    assert "/expxmedia:ambiente" in contexto and "/expxmedia:alma" not in contexto


def test_portao_aberto_nao_injeta_nada(instalacao):
    feito = _rodar(PORTAO, _prompt(instalacao), projeto=instalacao)
    assert feito.returncode == 0
    assert feito.stdout.strip() == ""


def test_portao_usa_cwd_do_payload_e_sobe_ate_a_raiz(instalacao):
    (instalacao / ".env").unlink()
    sub = instalacao / "pecas" / "2026-09"
    sub.mkdir(parents=True)
    feito = _rodar(PORTAO, _prompt(sub), cwd=sub)
    assert feito.returncode == 0
    assert "/expxmedia:ambiente" in _contexto(feito)


def test_portao_concorda_com_o_motor(instalacao, tmp_path):
    """O hook e `alma.carregar.portao` encaminham para o mesmo lugar em cada estado."""
    vazia = tmp_path / "vazia"
    vazia.mkdir()
    sem_env = tmp_path / "sem-env"
    shutil.copytree(instalacao, sem_env)
    (sem_env / ".env").unlink()
    for raiz in (vazia, sem_env, instalacao):
        esperado = carregar.portao(raiz)["encaminhar"]
        contexto = _contexto(_rodar(PORTAO, _prompt(raiz), projeto=raiz))
        if esperado is None:
            assert contexto is None
        else:
            assert esperado in contexto


@pytest.mark.parametrize("bruto", ["", "nada de json", "[]"])
def test_portao_falha_aberto(tmp_path, bruto):
    feito = _rodar(PORTAO, None, projeto=tmp_path, bruto=bruto)
    assert feito.returncode == 0
