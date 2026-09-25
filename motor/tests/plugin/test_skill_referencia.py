"""T-09.06: a skill de reel por referência, as regras do formato e o revisor-video (D-04, D-18, D-45).

Integração: o revisor-video declara tools só de leitura, conhece o perfil `sob_medida` e o checklist de
parecença e dá veredito binário; skill, regras e revisor citam só subcomandos existentes do CLI e passam
na varredura de marca.

Funcional: skill, regras e revisor juntos contêm todos os itens da fixture de âncoras
`reel-por-referencia`, e a sequência analisar → folhas → roteiro → narrar → código → prévia → render →
verificar → revisar aparece nessa ordem (na linha da sequência e nos passos da skill).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from plugin.test_ancoras import MARCA_EXTRA, carregar_fixture, itens_faltantes, normalizar
from plugin.test_estrutura import comandos_citados, comandos_inexistentes, frontmatter
from test_marca import varrer

TESTES = Path(__file__).resolve().parents[1]
REPO = TESTES.parents[1]
NUCLEO = REPO / "nucleo"
SKILL = NUCLEO / "skills" / "reel-por-referencia" / "SKILL.md"
REGRAS = NUCLEO / "skills" / "reel-por-referencia" / "regras.md"
REVISOR = NUCLEO / "agents" / "revisor-video.md"
ARQUIVOS = (SKILL, REGRAS, REVISOR)

# As etapas, na ordem, e o que as identifica na linha da sequência (texto já normalizado).
ETAPAS: tuple[tuple[str, str], ...] = (
    ("analisar", r"\banalisar\b"),
    ("folhas", r"\bfolhas\b"),
    ("roteiro", r"\broteiro\b"),
    ("narrar", r"\bnarrar\b"),
    ("codigo", r"\bcodigo\b"),
    ("previa", r"\bprevia\b"),
    ("render", r"\brender\b"),
    ("verificar", r"\bverificar\b"),
    ("revisar", r"\brevis(?:ar|ao)\b"),
)
FERRAMENTAS_DE_LEITURA = {"Read", "Grep", "Glob"}


def _texto(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def ordem_das_etapas(trecho: str) -> list[str]:
    """As etapas de ETAPAS na ordem em que aparecem no trecho (cada uma pela 1ª ocorrência depois da anterior).

    Devolve só as etapas achadas em sequência; a lista inteira quando a ordem é a esperada.
    """
    corpo = normalizar(trecho)
    achadas: list[str] = []
    cursor = 0
    for nome, padrao in ETAPAS:
        m = re.compile(padrao).search(corpo, cursor)
        if not m:
            break
        achadas.append(nome)
        cursor = m.end()
    return achadas


def linha_da_sequencia(texto: str) -> str:
    """A linha `Sequência: a → b → ...` da skill (a primeira linha que começa com 'Sequência' e tem setas)."""
    for linha in texto.splitlines():
        limpa = linha.strip().lstrip("-*> ").strip("*")
        if normalizar(limpa).startswith("sequencia") and limpa.count("→") >= len(ETAPAS) - 1:
            return limpa
    return ""


def passos_da_skill(texto: str) -> list[str]:
    """Os títulos `## N. ...` da skill, em ordem."""
    return re.findall(r"^## \d+[a-z]?\. (.+)$", texto, re.MULTILINE)


def secao(texto: str, titulo: str) -> str:
    """O corpo da seção `## <titulo>` até o próximo `## `."""
    m = re.search(rf"^## {re.escape(titulo)}\s*$(.*?)(?=^## |\Z)", texto, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- integração


def test_arquivos_existem_e_skill_tem_frontmatter():
    for arquivo in ARQUIVOS:
        assert arquivo.is_file(), arquivo
    dados = frontmatter(_texto(SKILL))
    assert dados.get("name") == "reel-por-referencia"
    assert len(dados.get("description", "")) >= 40


def test_revisor_declara_tools_so_de_leitura():
    dados = frontmatter(_texto(REVISOR))
    assert dados.get("name") == "revisor-video"
    assert dados.get("description")
    tools = {t.strip() for t in dados.get("tools", "").split(",") if t.strip()}
    assert tools, "o revisor precisa declarar tools"
    assert tools <= FERRAMENTAS_DE_LEITURA, f"tools que não são só de leitura: {sorted(tools - FERRAMENTAS_DE_LEITURA)}"


def test_revisor_conhece_o_perfil_sob_medida_e_o_checklist_de_parecenca():
    texto = _texto(REVISOR)
    corpo = normalizar(texto)
    assert "--perfil sob_medida" in texto
    assert "checklist de parecenca" in corpo
    faltam = itens_faltantes(carregar_fixture("reel-por-referencia"), texto)
    checklist = [i["id"] for i in carregar_fixture("reel-por-referencia")["itens"]
                 if i["categoria"] == "checklist_parecenca"]
    assert not set(checklist) & set(faltam), f"itens do checklist ausentes do revisor: {sorted(set(checklist) & set(faltam))}"


def test_revisor_da_veredito_binario_e_nunca_corrige():
    texto = _texto(REVISOR)
    vereditos = set(re.findall(r"\*\*(APROVADO|REPROVADO)\*\*", texto))
    assert vereditos == {"APROVADO", "REPROVADO"}
    corpo = normalizar(texto)
    assert "veredito binario" in corpo
    assert "nunca corrija" in corpo or "nunca corrige" in corpo


def test_so_subcomandos_existentes_do_cli():
    for arquivo in ARQUIVOS:
        assert comandos_inexistentes(_texto(arquivo)) == [], arquivo.name
    citados = set(comandos_citados(_texto(SKILL)))
    esperados = {("alma", "validar"), ("capacidades",), ("referencia", "analisar"), ("referencia", "criar"),
                 ("revisar", "copy"), ("narrar",), ("referencia", "montar"), ("referencia", "previa"),
                 ("referencia", "render"), ("verificar",)}
    assert esperados <= citados, f"a skill não usa: {sorted(esperados - citados)}"


def test_sem_marca():
    assert varrer(list(ARQUIVOS)) == []
    for arquivo in ARQUIVOS:
        texto = _texto(arquivo)
        achados = [r.pattern for r in MARCA_EXTRA if r.search(texto)]
        assert not achados, f"{arquivo.name}: {achados}"


# ---------------------------------------------------------------- funcional


def test_todos_os_itens_da_fixture_aparecem():
    assert itens_faltantes(carregar_fixture("reel-por-referencia"), list(ARQUIVOS)) == []


def test_skill_sozinha_tem_as_9_secoes_da_leitura_e_as_red_flags():
    fixture = carregar_fixture("reel-por-referencia")
    faltam = set(itens_faltantes(fixture, _texto(SKILL)))
    for categoria in ("leitura_9_secoes", "red_flags", "limites"):
        ids = {i["id"] for i in fixture["itens"] if i["categoria"] == categoria}
        assert not ids & faltam, f"{categoria}: {sorted(ids & faltam)}"
    flags = [l for l in secao(_texto(SKILL), "Red flags").splitlines() if l.startswith("- ")]
    assert len(flags) >= 9, f"red flags: {len(flags)}"


def test_regras_tem_a_tabela_do_que_se_imita_e_do_que_nunca_entra():
    texto = _texto(REGRAS)
    assert re.search(r"^\| imita .*\| não entra nunca \|$", texto, re.MULTILINE)
    linhas = [l for l in texto.splitlines() if l.startswith("| ") and "---" not in l]
    assert len(linhas) >= 8  # cabeçalho + 7 linhas da origem


def test_sequencia_na_ordem():
    linha = linha_da_sequencia(_texto(SKILL))
    assert linha, "falta a linha 'Sequência: ... → ...' na skill"
    assert ordem_das_etapas(linha) == [n for n, _ in ETAPAS]
    passos = passos_da_skill(_texto(SKILL))
    assert ordem_das_etapas("\n".join(passos)) == [n for n, _ in ETAPAS], passos


def test_verificador_de_ordem_pega_etapa_trocada():
    certa = "Sequência: analisar → folhas → roteiro → narrar → código → prévia → render → verificar → revisar"
    assert ordem_das_etapas(certa) == [n for n, _ in ETAPAS]
    trocada = "Sequência: analisar → folhas → roteiro → código → narrar → prévia → render → verificar → revisar"
    assert ordem_das_etapas(trocada) != [n for n, _ in ETAPAS]
    sem_folhas = "Sequência: analisar → roteiro → narrar → código → prévia → render → verificar → revisar"
    assert ordem_das_etapas(sem_folhas) == ["analisar"]


def test_narracao_uma_vez_na_pasta_do_reel():
    texto = _texto(SKILL)
    chamadas = re.findall(r"^expxmedia-motor narrar .*$", texto, re.MULTILINE)
    assert len(chamadas) == 1, chamadas
    assert re.search(r"--saida referencias/<slug>/midia\b", chamadas[0]), chamadas[0]


@pytest.mark.parametrize("trecho", [
    # o portão e a Alma
    "alma validar", "/expxmedia:alma", "/expxmedia:ambiente",
    # a verificação de requisitos
    "capacidades --capacidade narrar", "capacidades --capacidade renderizar_motion",
    "capacidades --capacidade transcrever",
    # a verificação no perfil do formato e a revisão
    "verificar --perfil sob_medida", "revisor-video",
])
def test_skill_cobre_portao_requisitos_e_revisao(trecho):
    assert trecho in _texto(SKILL)


@pytest.mark.parametrize("licao", [
    "scdet", "220", "1500", "centrad", "selo", "whoosh", "narracao e obrigatoria", "veracidade",
])
def test_regras_trazem_as_licoes_medidas(licao):
    assert licao in normalizar(_texto(REGRAS)), licao


def test_marca_vem_da_alma():
    corpo = normalizar(_texto(SKILL) + _texto(REGRAS))
    for campo in ("publico", "voz", "cta", "porta-voz", "selo"):
        assert campo in corpo, campo
    for campo in ("publico.principal", "voz.tratamento", "cta.padrao", "porta_vozes", "canais"):
        assert campo in _texto(SKILL) + _texto(REGRAS), campo
