"""T-09.07: skills cortar-video, criar-apresentacao e criar-aula.

Cada skill carrega a ordem de dependências do pipeline dela, portada da origem sem marca (D-04, M13):

- cortar-video: as quatro perguntas de quem escolhe o trecho e as regras invioláveis da emenda
  (base/corte-e-reenquadramento.md, curadoria-corte da origem);
- criar-apresentacao: deck validado antes do render, de 6 a 10 slides, número só com fonte
  (base/apresentacao-deck.md; o score de pauta fica fora, D-48);
- criar-aula: grava a tela primeiro e escreve o roteiro depois, narração → tela → avatar → legenda →
  render, e o avatar SEMPRE do áudio da narração, nunca do texto (base/aula-pipeline.md, D-26).

- integração: as três skills só citam subcomandos que existem no CLI e passam na varredura de marca.
- funcional: cortar-video e criar-aula contêm todos os itens das fixtures de âncoras, inclusive o avatar
  a partir do áudio e nunca do texto; a ordem de cada pipeline aparece na ordem certa.
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

CORTE = NUCLEO / "skills" / "cortar-video" / "SKILL.md"
APRESENTACAO = NUCLEO / "skills" / "criar-apresentacao" / "SKILL.md"
AULA = NUCLEO / "skills" / "criar-aula" / "SKILL.md"
NOVOS = [CORTE, APRESENTACAO, AULA]

MARCA_EXTRA = [re.compile(p, re.IGNORECASE) for p in (r"software\s*house", r"dono\s+de", r"@\w", r"\bexpx\b")]

# (rótulo, título da seção `## N. ...`, comando que a seção roda ou None), na ordem exigida.
ABERTURA = {
    CORTE: [
        ("portão", r"port[aã]o", ("alma", "validar")),
        ("leitura da Alma", r"\balma\b", None),
        ("galeria", r"galeria", None),
        ("requisitos", r"requisitos", ("capacidades",)),
        ("transcrição da fonte", r"transcre", ("transcrever",)),
        ("escolha do trecho", r"trecho", None),
        ("registro da peça", r"registrar a pe[cç]a", ("produzir", "reel-corte")),
        ("verificação", r"verific|revis", ("verificar",)),
    ],
    APRESENTACAO: [
        ("portão", r"port[aã]o", ("alma", "validar")),
        ("leitura da Alma", r"\balma\b", None),
        ("busca na galeria", r"galeria", ("galeria", "buscar")),
        ("requisitos", r"requisitos", ("capacidades",)),
        ("deck", r"deck", None),
        ("registro da peça", r"registrar a pe[cç]a", ("produzir", "apresentacao")),
    ],
    AULA: [
        ("portão", r"port[aã]o", ("alma", "validar")),
        ("leitura da Alma", r"\balma\b", None),
        ("busca na galeria", r"galeria", ("galeria", "buscar")),
        ("requisitos", r"requisitos", ("capacidades",)),
        ("gravação de tela", r"tela", None),
        ("roteiro", r"roteiro", None),
        ("registro da peça", r"registrar a pe[cç]a", ("produzir", "aula")),
    ],
}


def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def _secoes(texto: str) -> list[tuple[str, str]]:
    partes = re.split(r"^## +(.+)$", texto, flags=re.MULTILINE)
    return [(partes[i].strip(), partes[i + 1]) for i in range(1, len(partes) - 1, 2)]


def etapas_fora_de_ordem(texto: str, etapas) -> list[str]:
    """Rótulos das etapas ausentes ou fora de ordem; cada etapa é uma seção `## N. ...` depois da anterior."""
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


def _ordem(texto: str, trechos: list[str]) -> list[int]:
    corpo = normalizar(texto)
    return [corpo.find(normalizar(t)) for t in trechos]


# ---------------------------------------------------------------- integração


@pytest.mark.parametrize("arquivo", NOVOS, ids=lambda p: p.parent.name)
def test_skill_existe_com_frontmatter(arquivo):
    assert arquivo.is_file(), arquivo
    dados = frontmatter(_ler(arquivo))
    assert dados.get("name") == arquivo.parent.name
    assert len(dados.get("description", "")) >= 40


@pytest.mark.parametrize("arquivo", NOVOS, ids=lambda p: p.parent.name)
def test_so_cita_subcomandos_que_existem(arquivo):
    texto = _ler(arquivo)
    assert comandos_citados(texto), "a skill não roda o motor"
    assert comandos_inexistentes(texto) == []


def test_arquivos_novos_sem_marca():
    assert varrer(NOVOS) == []
    achados = [(a.parent.name, t.pattern) for a in NOVOS for t in MARCA_EXTRA if t.search(_ler(a))]
    assert achados == []


# ---------------------------------------------------------------- funcional


def test_cortar_video_tem_todos_os_itens_da_fixture():
    assert itens_faltantes(carregar_fixture("cortar-video"), CORTE) == []


def test_criar_aula_tem_todos_os_itens_da_fixture():
    assert itens_faltantes(carregar_fixture("criar-aula"), AULA) == []


def test_criar_aula_gera_o_avatar_do_audio_e_nunca_do_texto():
    texto = _ler(AULA)
    fixture = carregar_fixture("criar-aula")
    avatar = {"itens": [i for i in fixture["itens"] if i["categoria"] == "avatar_audio"]}
    assert itens_faltantes(avatar, texto) == []
    assert ("avatar", "gerar") in comandos_citados(texto)
    # a seção que gera o avatar passa o mp3 da narração, não o roteiro
    linhas = [l for l in texto.splitlines() if "expxmedia-motor avatar gerar" in l]
    assert linhas and all("--audio" in l and "narracao.mp3" in l and "roteiro" not in l for l in linhas)


@pytest.mark.parametrize("arquivo", NOVOS, ids=lambda p: p.parent.name)
def test_skill_segue_a_ordem_de_dependencias(arquivo):
    assert etapas_fora_de_ordem(_ler(arquivo), ABERTURA[arquivo]) == []


def test_aula_grava_a_tela_antes_do_roteiro_e_narra_antes_do_avatar_e_da_legenda():
    posicoes = _ordem(_ler(AULA), ["grave a tela primeiro", "escreva o roteiro depois",
                                   "narração gera o áudio e os cues", "gravação de tela no tempo da fala",
                                   "avatar depois da narração", "legenda com o texto exato do roteiro",
                                   "render 16:9 e 9:16"])
    assert -1 not in posicoes and posicoes == sorted(posicoes), posicoes


def test_corte_escolhe_o_trecho_lendo_e_so_depois_corta():
    texto = _ler(CORTE)
    posicoes = _ordem(texto, ["o trecho se sustenta sem o que veio antes?", "fecha?",
                              "expxmedia-motor produzir reel-corte", "expxmedia-motor verificar"])
    assert -1 not in posicoes and posicoes == sorted(posicoes), posicoes
    corpo = normalizar(texto)
    assert "sem cta" in corpo and "--perfil corte" in corpo


def test_apresentacao_valida_o_deck_antes_do_render():
    texto = _ler(APRESENTACAO)
    corpo = normalizar(texto)
    for trecho in ("6 a 10 slides", "fonte", "travessão", "--mp4"):
        assert normalizar(trecho) in corpo, trecho
    posicoes = _ordem(texto, ["o primeiro slide é titulo", "o último é cta",
                              "expxmedia-motor produzir apresentacao"])
    assert -1 not in posicoes and posicoes == sorted(posicoes), posicoes


def test_verificador_pega_aula_que_gera_avatar_do_texto(tmp_path):
    """Revisor de testes: trocar 'nunca do texto' por uma instrução errada faz a verificação falhar."""
    capada = re.sub(r"nunca\s+do\s+texto", "também do texto", _ler(AULA), flags=re.IGNORECASE)
    falsa = tmp_path / "SKILL.md"
    falsa.write_text(capada, encoding="utf-8")
    assert "avatar-nunca-do-texto" in itens_faltantes(carregar_fixture("criar-aula"), falsa)
