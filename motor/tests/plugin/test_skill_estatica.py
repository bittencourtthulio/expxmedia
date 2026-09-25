"""T-09.04: skills criar-post e criar-carrossel e os agentes copywriter, revisor-editorial e validador-imagem.

A inteligência editorial de carrossel da origem (duas passadas, bloqueantes, validação de imagem com
dois validadores) vira skill e agente do núcleo, com a marca trocada pela Alma (D-04, D-45, M13).

- integração: os agentes de revisão e de validação declaram só ferramentas de leitura; os arquivos
  novos passam na varredura de marca e só citam subcomandos que existem no CLI.
- funcional: criar-carrossel segue a ordem portão → Alma → galeria → requisitos → revisar copy →
  registro da peça, e skill + agentes contêm todos os itens da fixture de âncoras de criar-carrossel.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from plugin.test_ancoras import carregar_fixture, itens_faltantes, normalizar
from plugin.test_estrutura import comandos_citados, comandos_inexistentes, frontmatter
from test_marca import varrer

TESTES = Path(__file__).resolve().parents[1]
REPO = TESTES.parents[1]
NUCLEO = REPO / "nucleo"

SKILL_CARROSSEL = NUCLEO / "skills" / "criar-carrossel" / "SKILL.md"
SKILL_POST = NUCLEO / "skills" / "criar-post" / "SKILL.md"
COPYWRITER = NUCLEO / "agents" / "copywriter.md"
REVISOR = NUCLEO / "agents" / "revisor-editorial.md"
VALIDADOR = NUCLEO / "agents" / "validador-imagem.md"
NOVOS = [SKILL_CARROSSEL, SKILL_POST, COPYWRITER, REVISOR, VALIDADOR]

ESCRITA = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
LEITURA_COM_MOTOR = {"Read", "Grep", "Glob", "Bash"}  # Bash só para o motor e grep, dito no agente
LEITURA_PURA = {"Read", "Grep", "Glob"}

# Além da lista de marca do núcleo: público e nicho das origens não entram (M13).
MARCA_EXTRA = [re.compile(p, re.IGNORECASE) for p in (r"software\s*house", r"dono\s+de", r"@\w")]

# A ordem que a task exige em criar-carrossel: (rótulo, título da seção, comando que a seção roda).
ORDEM_CARROSSEL = [
    ("portão", r"port[aã]o", ("alma", "validar")),
    ("leitura da Alma", r"\balma\b", None),
    ("busca na galeria", r"galeria", ("galeria", "buscar")),
    ("verificação de requisitos", r"requisitos", ("capacidades",)),
    ("revisar copy", r"revisar a copy", ("revisar", "copy")),
    ("registro da peça", r"registrar a pe[cç]a", ("produzir", "carrossel")),
]


def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def _tools(caminho: Path) -> set[str]:
    valor = frontmatter(_ler(caminho)).get("tools", "")
    return {t.strip() for t in valor.split(",") if t.strip()}


def _secoes(texto: str) -> list[tuple[str, str]]:
    """[(título, corpo)] das seções `## ` do Markdown, na ordem."""
    partes = re.split(r"^## +(.+)$", texto, flags=re.MULTILINE)
    return [(partes[i].strip(), partes[i + 1]) for i in range(1, len(partes) - 1, 2)]


def ordem_das_etapas(texto: str, etapas=ORDEM_CARROSSEL) -> list[str]:
    """Rótulos das etapas fora de ordem ou ausentes (vazio quando a skill segue a ordem).

    Cada etapa é a primeira seção `## N. ...`, depois da etapa anterior, cujo título casa o padrão;
    quando a etapa declara um comando, a seção tem de citá-lo.
    """
    secoes = _secoes(texto)
    problemas = []
    inicio = 0
    for rotulo, padrao, comando in etapas:
        achou = None
        for i in range(inicio, len(secoes)):
            titulo, corpo = secoes[i]
            if re.match(r"^\d+\.", titulo) and re.search(padrao, titulo, re.IGNORECASE):
                achou = i
                break
        if achou is None:
            problemas.append(rotulo)
            continue
        if comando is not None and comando not in comandos_citados(secoes[achou][1]):
            problemas.append(f"{rotulo}: a seção não roda expxmedia-motor {' '.join(comando)}")
        inicio = achou + 1
    return problemas


# ---------------------------------------------------------------- integração


def test_arquivos_existem_com_frontmatter():
    for arquivo in NOVOS:
        assert arquivo.is_file(), arquivo
        dados = frontmatter(_ler(arquivo))
        assert dados.get("name"), arquivo
        assert len(dados.get("description", "")) >= 40, arquivo
    for agente in (COPYWRITER, REVISOR, VALIDADOR):
        assert frontmatter(_ler(agente))["name"] == agente.stem


def test_revisor_e_validador_so_leem():
    revisor, validador = _tools(REVISOR), _tools(VALIDADOR)
    assert revisor and revisor <= LEITURA_COM_MOTOR and not revisor & ESCRITA, revisor
    assert validador and validador <= LEITURA_PURA, validador
    assert "Read" in validador  # o validador abre a imagem: é o validador com visão
    # quem escreve a copy é o copywriter, e só ele entre os três
    assert _tools(COPYWRITER) & {"Write", "Edit"}


def test_revisor_declara_que_nao_edita():
    texto = normalizar(_ler(REVISOR))
    assert "voce nao edita nada" in texto
    assert "expxmedia-motor revisar copy" in texto


def test_arquivos_novos_sem_marca():
    achados = varrer(NOVOS)
    assert not achados, achados
    extras = [(a.name, p.pattern) for a in NOVOS for p in MARCA_EXTRA if p.search(_ler(a))]
    assert not extras, extras


def test_so_citam_subcomandos_que_existem():
    citados = set()
    for arquivo in NOVOS:
        texto = _ler(arquivo)
        assert comandos_inexistentes(texto) == [], arquivo.name
        citados |= set(comandos_citados(texto))
    esperados = {("alma", "validar"), ("galeria", "buscar"), ("capacidades",), ("revisar", "copy"),
                 ("produzir", "carrossel"), ("produzir", "post"), ("peca", "status"), ("imagem", "pexels"),
                 ("imagem", "retrato")}
    assert esperados <= citados, esperados - citados


# ---------------------------------------------------------------- funcional


def test_criar_carrossel_segue_a_ordem():
    assert ordem_das_etapas(_ler(SKILL_CARROSSEL)) == []


def test_criar_post_segue_a_mesma_ordem():
    etapas = [(r, p, ("produzir", "post") if c == ("produzir", "carrossel") else c) for r, p, c in ORDEM_CARROSSEL]
    assert ordem_das_etapas(_ler(SKILL_POST), etapas) == []


def test_verificador_de_ordem_pega_troca_e_comando_ausente():
    certo = ("## 1. Portão\nexpxmedia-motor alma validar\n## 2. Ler a Alma\nx\n"
             "## 3. Buscar na galeria\nexpxmedia-motor galeria buscar --tipo carrossel --formato 4:5\n"
             "## 4. Verificar os requisitos\nexpxmedia-motor capacidades\n"
             "## 5. Revisar a copy\nexpxmedia-motor revisar copy\n"
             "## 6. Produzir e registrar a peça\nexpxmedia-motor produzir carrossel --entrada e.json\n")
    assert ordem_das_etapas(certo) == []
    trocado = certo.replace("## 3. Buscar na galeria", "## 3. Tmp").replace("## 4. Verificar os requisitos",
                                                                             "## 3b. Buscar na galeria")
    trocado = trocado.replace("## 3. Tmp", "## 4. Verificar os requisitos")
    assert ordem_das_etapas(trocado) != []
    sem_comando = certo.replace("expxmedia-motor revisar copy", "revise a copy")
    assert ordem_das_etapas(sem_comando) == ["revisar copy: a seção não roda expxmedia-motor revisar copy"]


def test_skill_e_agentes_contem_as_ancoras_de_criar_carrossel():
    fixture = carregar_fixture("criar-carrossel")
    alvos = [REPO / a for a in fixture["alvos"]]
    assert sorted(alvos) == sorted([SKILL_CARROSSEL, COPYWRITER, REVISOR])
    assert itens_faltantes(fixture, alvos) == []


def test_revisor_sozinho_carrega_os_bloqueantes():
    """Os bloqueantes são o checklist do revisor: não basta estarem espalhados na skill."""
    fixture = carregar_fixture("criar-carrossel")
    bloqueantes = {"itens": [i for i in fixture["itens"] if i["categoria"] in ("bloqueantes", "duas_passadas")]}
    assert itens_faltantes(bloqueantes, [REVISOR]) == []


def test_carrossel_misto_e_imagem_com_dois_validadores():
    skill = normalizar(_ler(SKILL_CARROSSEL))
    assert "carrossel misto" in skill and '"midia": "video"' in skill
    assert "validador-imagem" in skill
    validador = normalizar(_ler(VALIDADOR))
    for trecho in ("o que o slide afirma", "na duvida, recusa", "e a mesma pessoa", "nunca aprove sem abrir"):
        assert normalizar(trecho) in validador, trecho
    # números calibrados do primeiro validador (o script), com o mesmo valor da origem
    for trecho in ("1200 px", "uma por peca"):
        assert normalizar(trecho) in skill, trecho


@pytest.mark.parametrize("arquivo", [SKILL_CARROSSEL, SKILL_POST, COPYWRITER])
def test_voz_publico_e_cta_vem_da_alma(arquivo):
    texto = normalizar(_ler(arquivo))
    for trecho in ("voz.tratamento", "voz.palavras_proibidas", "publico", "cta"):
        assert normalizar(trecho) in texto, (arquivo.name, trecho)
