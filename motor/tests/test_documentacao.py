"""T-10.04: a documentação do núcleo acompanha o código.

- Todo subcomando listado na referência do CLI em motor/README.md existe no --help real, e todo
  subcomando do CLI está documentado lá (as duas direções).
- O README da raiz marca o passo 2 (núcleo) como concluído e cita motor/ e nucleo/.
- nucleo/README.md cita toda skill, comando e agente do plugin.
- `claude plugin validate nucleo` termina com código 0.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import pytest

from expxmedia.cli import construir_parser


REPO = Path(__file__).resolve().parents[2]
MOTOR = REPO / "motor"
NUCLEO = REPO / "nucleo"
README_MOTOR = MOTOR / "README.md"
README_NUCLEO = NUCLEO / "README.md"
README_RAIZ = REPO / "README.md"

INICIO = "<!-- cli:inicio -->"
FIM = "<!-- cli:fim -->"


def _subparsers(parser):
    for acao in parser._actions:
        if isinstance(acao, argparse._SubParsersAction):
            return acao.choices
    return {}


def comandos_do_cli():
    """Caminho de cada subcomando folha do CLI real ("alma confirmar", "publicar"...)."""
    folhas = set()

    def descer(parser, caminho):
        filhos = _subparsers(parser)
        if not filhos and caminho:
            folhas.add(" ".join(caminho))
        for nome, sub in filhos.items():
            descer(sub, caminho + [nome])

    descer(construir_parser(), [])
    return folhas


def _secao_cli(texto):
    assert INICIO in texto and FIM in texto, "motor/README.md sem os marcadores da referência do CLI"
    return texto.split(INICIO, 1)[1].split(FIM, 1)[0]


def comandos_do_readme():
    """Subcomandos das linhas de uso (`expxmedia-motor <grupo> <sub> ...`) da referência do CLI."""
    documentados = set()
    for linha in _secao_cli(README_MOTOR.read_text(encoding="utf-8")).splitlines():
        if not linha.startswith("expxmedia-motor "):
            continue
        caminho = []
        for token in linha.split()[1:]:
            if not re.fullmatch(r"[a-z][a-z0-9-]*", token):
                break
            caminho.append(token)
        documentados.add(" ".join(caminho))
    return documentados


def cabecalhos_do_readme():
    """Subcomandos dos cabeçalhos #### da referência (um por subcomando de grupo)."""
    secao = _secao_cli(README_MOTOR.read_text(encoding="utf-8"))
    return set(re.findall(r"^####\s+`([a-z][a-z0-9 -]*)`\s*$", secao, flags=re.MULTILINE))


def _help_de(caminho, capsys):
    with pytest.raises(SystemExit) as saida:
        construir_parser().parse_args(caminho.split() + ["--help"])
    assert saida.value.code == 0, caminho
    return capsys.readouterr().out


# --- integração: README do motor x --help do CLI ---------------------------------------------


def test_referencia_do_cli_nao_esta_vazia():
    documentados = comandos_do_readme()
    assert len(documentados) >= 30
    assert "" not in documentados


def test_todo_subcomando_documentado_existe_no_help(capsys):
    documentados = comandos_do_readme()
    inexistentes = sorted(documentados - comandos_do_cli())
    assert not inexistentes, f"documentados no motor/README.md mas ausentes do CLI: {inexistentes}"
    for caminho in sorted(documentados):
        partes = caminho.split()
        if len(partes) == 2:
            # o subcomando aparece no --help real do grupo dele
            assert re.search(rf"^\s+{re.escape(partes[1])}\b", _help_de(partes[0], capsys), re.M), caminho
        _help_de(caminho, capsys)


def test_nenhum_subcomando_do_cli_fica_sem_documentacao():
    faltando = sorted(comandos_do_cli() - comandos_do_readme())
    assert not faltando, f"subcomandos do CLI sem documentação no motor/README.md: {faltando}"


def test_cabecalhos_batem_com_os_subcomandos_de_grupo():
    de_grupo = {c for c in comandos_do_cli() if " " in c}
    assert cabecalhos_do_readme() == de_grupo


def test_grupos_do_help_real_por_subprocesso():
    """O --help do executável instalado lista todos os grupos citados no README."""
    saida = subprocess.run(
        [sys.executable, "-m", "expxmedia.cli", "--help"],
        capture_output=True, text=True, cwd=MOTOR, timeout=60,
    )
    if saida.returncode != 0 or not saida.stdout.strip():
        saida = subprocess.run(
            ["uv", "run", "expxmedia-motor", "--help"],
            capture_output=True, text=True, cwd=MOTOR, timeout=120,
        )
    assert saida.returncode == 0, saida.stderr
    grupos = {c.split()[0] for c in comandos_do_readme()}
    for grupo in grupos:
        assert re.search(rf"^\s+{re.escape(grupo)}\b", saida.stdout, re.M), grupo


def test_readme_do_motor_cobre_o_que_a_task_pede():
    texto = README_MOTOR.read_text(encoding="utf-8")
    for trecho in [
        "Python 3.11", "uv", "Node 20", "ffmpeg 8", "Playwright", "chrome-headless-shell",
        "faster-whisper", "u2net", "say",
        "uv run python scripts/preparar_ambiente.py",
        "uv run pytest", "integracao_local", "tests/golden", "scripts/gerar_golden.py",
        "PENDENTE-01", "00-DECISOES.md",
    ]:
        assert trecho in texto, trecho
    pacotes = {
        p.name for p in (MOTOR / "src" / "expxmedia").iterdir()
        if p.is_dir() and (p / "__init__.py").exists()
    }
    for pacote in pacotes:
        assert f"`{pacote}`" in texto, f"pacote sem descrição na arquitetura: {pacote}"
    for codigo in ("| 0 |", "| 1 |", "| 2 |", "| 3 |"):
        assert codigo in texto, codigo


# --- funcional: README da raiz, README do plugin e validação do plugin -----------------------


def test_readme_raiz_marca_o_passo_2_e_cita_motor_e_nucleo():
    texto = README_RAIZ.read_text(encoding="utf-8")
    assert "## Ordem de construção" in texto
    ordem = texto.split("## Ordem de construção", 1)[1].split("\n## ", 1)[0]
    passo2 = re.search(r"^2\. .*$", ordem, re.M)
    assert passo2, "README da raiz sem o passo 2"
    assert "✅" in passo2.group(0), passo2.group(0)
    assert "motor/" in passo2.group(0) and "nucleo/" in passo2.group(0), passo2.group(0)
    assert "passo 0" not in texto.lower()
    assert "Como começar" in texto
    for trecho in ("preparar_ambiente.py", "--plugin-dir nucleo", "/expxmedia:alma"):
        assert trecho in texto, trecho


def test_readme_do_nucleo_cita_skills_comandos_agentes_e_hooks():
    texto = README_NUCLEO.read_text(encoding="utf-8")
    assert "claude --plugin-dir nucleo" in texto
    skills = [p.parent.name for p in (NUCLEO / "skills").glob("*/SKILL.md")]
    comandos = [p.stem for p in (NUCLEO / "commands").glob("*.md")]
    agentes = [p.stem for p in (NUCLEO / "agents").glob("*.md")]
    hooks = [p.name for p in (NUCLEO / "hooks").glob("*.sh")]
    assert skills and comandos and agentes and hooks
    for nome in skills + agentes + hooks:
        assert f"`{nome}`" in texto, nome
    for nome in comandos:
        assert f"/expxmedia:{nome}" in texto, nome


@pytest.mark.integracao_local
def test_claude_plugin_validate_nucleo(requer_binario):
    claude = requer_binario("claude")
    saida = subprocess.run(
        [claude, "plugin", "validate", "nucleo"],
        capture_output=True, text=True, cwd=REPO, timeout=120,
    )
    assert saida.returncode == 0, saida.stdout + saida.stderr
