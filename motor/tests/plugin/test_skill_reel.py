"""T-09.05: skills criar-reel e reel-de-pagina, agentes roteirista e revisor-reel.

A inteligência de roteiro do reel da origem (6 partes, teste das dez primeiras palavras, veracidade dos
beats 2 a 6, palavra do CTA que sobrevive ao teclado) e o roteiro de auditoria do revisor viram skill e
agente do núcleo, com público, voz, CTA e porta-voz vindos da Alma (D-04, D-45, M13).

- integração: as skills e os agentes só citam subcomandos que existem no CLI (criar-reel cita os que
  produzem o reel) e passam na varredura de marca.
- funcional: skills + roteirista contêm todos os itens da fixture criar-reel (o roteirista sozinho
  também, porque é ele quem escreve); o revisor-reel contém todos os itens da fixture revisor-reel e
  declara só ferramentas de leitura; reel-de-pagina cita `produzir reel-pagina` e `produzir abertura`
  e põe a captura antes do roteiro, com o site.md como lastro.
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

CRIAR_REEL = NUCLEO / "skills" / "criar-reel" / "SKILL.md"
REEL_PAGINA = NUCLEO / "skills" / "reel-de-pagina" / "SKILL.md"
ROTEIRISTA = NUCLEO / "agents" / "roteirista.md"
REVISOR = NUCLEO / "agents" / "revisor-reel.md"
NOVOS = [CRIAR_REEL, REEL_PAGINA, ROTEIRISTA, REVISOR]

ESCRITA = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
LEITURA = {"Read", "Grep", "Glob", "Bash"}  # Bash só para verificar e extrair quadro, dito no agente

# Público e nicho das origens não entram (M13), além da lista de marca do núcleo.
MARCA_EXTRA = [re.compile(p, re.IGNORECASE) for p in (r"software\s*house", r"dono\s+de", r"@\w", r"\bexpx\b")]

# A abertura de toda skill de produção: (rótulo, título da seção, comando que a seção roda ou None).
ABERTURA_REEL = [
    ("portão", r"port[aã]o", ("alma", "validar")),
    ("leitura da Alma", r"\balma\b", None),
    ("busca na galeria", r"galeria", ("galeria", "buscar")),
    ("requisitos", r"requisitos", ("capacidades",)),
    ("registro da peça", r"registrar a pe[cç]a", ("produzir", "reel")),
]
ABERTURA_PAGINA = [
    ("portão", r"port[aã]o", ("alma", "validar")),
    ("leitura da Alma", r"\balma\b", None),
    ("galeria", r"galeria", None),
    ("requisitos", r"requisitos", ("capacidades",)),
    ("captura", r"captur", ("capturar", "pagina")),
    ("roteiro", r"roteiro", None),
    ("registro da peça", r"registrar a pe[cç]a", ("produzir", "reel-pagina")),
]


def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def _tools(caminho: Path) -> set[str]:
    return {t.strip() for t in frontmatter(_ler(caminho)).get("tools", "").split(",") if t.strip()}


def _secoes(texto: str) -> list[tuple[str, str]]:
    partes = re.split(r"^## +(.+)$", texto, flags=re.MULTILINE)
    return [(partes[i].strip(), partes[i + 1]) for i in range(1, len(partes) - 1, 2)]


def etapas_fora_de_ordem(texto: str, etapas) -> list[str]:
    """Rótulos das etapas ausentes ou fora de ordem; cada etapa é uma seção `## N. ...` depois da anterior.

    Quando a etapa declara um comando, a seção dela tem de rodá-lo.
    """
    secoes = _secoes(texto)
    problemas, inicio = [], 0
    for rotulo, padrao, comando in etapas:
        achou = next((i for i in range(inicio, len(secoes))
                      if re.match(r"^\d+\.", secoes[i][0]) and re.search(padrao, secoes[i][0], re.IGNORECASE)), None)
        if achou is None:
            problemas.append(rotulo)
            continue
        if comando is not None and comando not in comandos_citados(secoes[achou][1]):
            problemas.append(f"{rotulo}: a seção não roda expxmedia-motor {' '.join(comando)}")
        inicio = achou + 1
    return problemas


# ---------------------------------------------------------------- integração


def test_arquivos_existem_com_frontmatter_e_nome_da_pasta():
    for arquivo in NOVOS:
        assert arquivo.is_file(), arquivo
        dados = frontmatter(_ler(arquivo))
        assert len(dados.get("description", "")) >= 40, arquivo
        esperado = arquivo.parent.name if arquivo.name == "SKILL.md" else arquivo.stem
        assert dados.get("name") == esperado, arquivo


@pytest.mark.parametrize("arquivo", NOVOS, ids=lambda p: p.stem if p.name != "SKILL.md" else p.parent.name)
def test_so_cita_subcomandos_que_existem(arquivo):
    assert comandos_inexistentes(_ler(arquivo)) == []


def test_criar_reel_cita_os_comandos_do_caminho_narrado():
    citados = set(comandos_citados(_ler(CRIAR_REEL)))
    for comando in (("alma", "validar"), ("galeria", "buscar"), ("capacidades",), ("produzir", "reel"),
                    ("revisar", "copy"), ("peca", "status")):
        assert comando in citados, comando
    # o reel narrado em Remotion não é o reel de página nem o de corte
    assert ("produzir", "reel-pagina") not in citados and ("produzir", "reel-corte") not in citados


def test_arquivos_novos_sem_marca():
    assert varrer(NOVOS) == []
    achados = [(a.name, t.pattern) for a in NOVOS for t in MARCA_EXTRA if t.search(_ler(a))]
    assert achados == []


def test_revisor_declara_so_ferramentas_de_leitura():
    tools = _tools(REVISOR)
    assert tools and tools <= LEITURA and not tools & ESCRITA, tools
    texto = normalizar(_ler(REVISOR))
    # o Bash do revisor é só para verificar e olhar quadros: dito no agente
    assert "expxmedia-motor verificar" in texto
    assert "nunca corrige" in texto or "nunca corrija" in texto


def test_roteirista_escreve_e_nao_narra():
    tools = _tools(ROTEIRISTA)
    assert {"Write", "Read"} <= tools
    texto = _ler(ROTEIRISTA)
    # o roteirista não chama a narração: narrar custa crédito e é da produção
    assert not any(c[0] == "narrar" or c[:2] == ("produzir", "reel") for c in comandos_citados(texto))


# ---------------------------------------------------------------- funcional


def test_skills_e_roteirista_tem_todos_os_itens_de_criar_reel():
    fixture = carregar_fixture("criar-reel")
    assert itens_faltantes(fixture, [CRIAR_REEL, REEL_PAGINA, ROTEIRISTA]) == []
    # quem escreve o roteiro carrega a inteligência inteira sozinho
    assert itens_faltantes(fixture, ROTEIRISTA) == []


@pytest.mark.parametrize("skill", [CRIAR_REEL, REEL_PAGINA], ids=["criar-reel", "reel-de-pagina"])
def test_cada_skill_traz_as_6_partes_e_o_teste_das_dez_palavras(skill):
    fixture = carregar_fixture("criar-reel")
    itens = [i for i in fixture["itens"] if i["categoria"] in ("seis_partes", "dez_palavras")]
    assert itens_faltantes({"itens": itens}, skill) == []


def test_revisor_tem_todos_os_itens_de_revisor_reel():
    assert itens_faltantes(carregar_fixture("revisor-reel"), REVISOR) == []


def test_as_6_partes_estao_em_ordem_no_roteirista():
    texto = normalizar(_ler(ROTEIRISTA))
    posicoes = [texto.find(normalizar(a)) for a in ("1. Gancho", "2. O que é", "3. Prova", "4. Como usa",
                                                     "5. Para quem", "6. CTA")]
    assert -1 not in posicoes and posicoes == sorted(posicoes), posicoes


def test_criar_reel_abre_com_portao_alma_galeria_requisitos_e_registro():
    assert etapas_fora_de_ordem(_ler(CRIAR_REEL), ABERTURA_REEL) == []


def test_reel_de_pagina_captura_antes_do_roteiro_e_registra_depois():
    texto = _ler(REEL_PAGINA)
    assert etapas_fora_de_ordem(texto, ABERTURA_PAGINA) == []
    citados = comandos_citados(texto)
    assert ("produzir", "reel-pagina") in citados and ("produzir", "abertura") in citados
    corpo = normalizar(texto)
    assert "site.md" in corpo and "lastro" in corpo
    # a abertura é decisão de quem chama: a skill diz quando usar e quando dispensar
    assert "--dispensar" in texto and "quando usar" in corpo


def test_verificador_pega_skill_sem_o_teste_das_dez_palavras(tmp_path):
    """Revisor de testes: tirar o teste das dez palavras do roteirista faz a verificação falhar."""
    texto = _ler(ROTEIRISTA)
    capado = re.sub(r"dez(\*\*)?\s+primeiras\s+palavras", "primeiras frases", texto, flags=re.IGNORECASE)
    falso = tmp_path / "roteirista.md"
    falso.write_text(capado, encoding="utf-8")
    assert "dez-palavras" in itens_faltantes(carregar_fixture("criar-reel"), falso)


def test_ordem_pega_registro_antes_do_portao():
    embaralhada = "## 1. Registrar a peça\n\nexpxmedia-motor produzir reel --entrada x\n\n## 2. Portão\n\n" \
                  "expxmedia-motor alma validar\n"
    assert "portão" not in etapas_fora_de_ordem(embaralhada, ABERTURA_REEL[:1])
    assert "registro da peça" in etapas_fora_de_ordem(embaralhada, [ABERTURA_REEL[0], ABERTURA_REEL[4]])
