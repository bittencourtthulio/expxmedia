"""T-09.08: skill publicar e agente publicador (D-07, D-08, D-15, D-29, D-30).

- integração: a skill e o agente citam só subcomandos que existem no CLI e passam na varredura de
  marca.
- funcional: a skill manda rodar o dry-run antes de publicar (todo `--confirmar` vem depois de um
  comando sem ele), proíbe retentar publicação que falhou sem nova ordem, escolhe o provedor pela
  verificação sem trocar em silêncio e explica o que muda entre o Expx Flow e a Graph API.
"""
from __future__ import annotations

import re
from pathlib import Path

from plugin.test_ancoras import normalizar
from plugin.test_estrutura import comandos_citados, comandos_inexistentes, frontmatter
from test_marca import varrer

TESTES = Path(__file__).resolve().parents[1]
REPO = TESTES.parents[1]
SKILL = REPO / "nucleo" / "skills" / "publicar" / "SKILL.md"
AGENTE = REPO / "nucleo" / "agents" / "publicador.md"

_RE_ENVIO = re.compile(r"expxmedia-motor[ \t]+(publicar|agendar)\b[^\n`]*")


def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def envios(texto: str) -> list[tuple[str, bool]]:
    """Cada `expxmedia-motor publicar|agendar ...` do texto, na ordem: (subcomando, tem --confirmar)."""
    return [(m.group(1), "--confirmar" in m.group(0)) for m in _RE_ENVIO.finditer(texto)]


def confirmar_antes_do_dry_run(texto: str) -> list[str]:
    """Subcomandos cujo `--confirmar` aparece sem um dry-run do mesmo subcomando antes."""
    vistos_sem: set[str] = set()
    fora = []
    for sub, confirma in envios(texto):
        if confirma and sub not in vistos_sem:
            fora.append(sub)
        if not confirma:
            vistos_sem.add(sub)
    return fora


# ---------------------------------------------------------------- integração


def test_arquivos_existem_com_frontmatter():
    for arquivo in (SKILL, AGENTE):
        assert arquivo.is_file(), arquivo
        dados = frontmatter(_ler(arquivo))
        assert len(dados.get("description", "")) >= 40, arquivo
    assert frontmatter(_ler(SKILL))["name"] == "publicar"
    assert frontmatter(_ler(AGENTE))["name"] == "publicador"


def test_so_cita_subcomandos_que_existem():
    citados = set()
    for arquivo in (SKILL, AGENTE):
        texto = _ler(arquivo)
        assert comandos_inexistentes(texto) == [], arquivo.name
        citados |= set(comandos_citados(texto))
    assert {("publicar",), ("agendar",), ("capacidades",), ("peca", "status"), ("agendador", "instalar"),
            ("agendador", "rodar")} <= citados


def test_sem_marca():
    achados = varrer([SKILL, AGENTE])
    assert not achados, achados


# ---------------------------------------------------------------- funcional


def test_dry_run_vem_antes_de_publicar_de_verdade():
    for arquivo in (SKILL, AGENTE):
        texto = _ler(arquivo)
        lista = envios(texto)
        assert any(c for _, c in lista), f"{arquivo.name}: nenhum envio com --confirmar"
        assert confirmar_antes_do_dry_run(texto) == [], arquivo.name
        assert "dry-run" in texto
    corpo = normalizar(_ler(SKILL))
    assert "dry-run e obrigatorio" in corpo
    assert "espere o sim" in corpo


def test_verificador_de_ordem_pega_confirmar_primeiro():
    ruim = "Rode `expxmedia-motor publicar --peca X --confirmar` e depois `expxmedia-motor publicar --peca X`."
    assert confirmar_antes_do_dry_run(ruim) == ["publicar"]
    bom = "Rode `expxmedia-motor agendar --peca X --para T`; com o sim, `expxmedia-motor agendar --peca X --para T --confirmar`."
    assert confirmar_antes_do_dry_run(bom) == []


def test_proibe_retentar_publicacao_que_falhou():
    for arquivo in (SKILL, AGENTE):
        corpo = normalizar(_ler(arquivo))
        assert "nunca retente" in corpo, arquivo.name
        assert "nova ordem" in corpo, arquivo.name
    corpo = normalizar(_ler(SKILL))
    # a trava de duplicata só se solta depois de conferir no provedor
    assert "--forcar" in corpo and "confira no provedor" in corpo
    assert "incerto" in corpo


def test_provedor_pela_verificacao_sem_troca_silenciosa():
    corpo = normalizar(_ler(SKILL))
    for trecho in ("expxmedia-motor capacidades --capacidade publicar", "provedor_publicar", "provedor_agendar",
                   "nunca troque de provedor"):
        assert normalizar(trecho) in corpo, trecho


def test_explica_expx_flow_contra_graph_api():
    corpo = normalizar(_ler(SKILL))
    for trecho in ("agenda no servidor", "agendador local", "maquina ligada", "15 minutos",
                   "dm so existe no expx flow", "2 a 20", "2 a 10", "4:5 a 1.91:1", "jpeg"):
        assert normalizar(trecho) in corpo, trecho
