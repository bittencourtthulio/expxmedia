"""T-09.11: âncoras de inteligência (D-04, D-45).

Cada fixture de tests/fixtures/inteligencia/ lista, para uma skill (ou agente) do núcleo, os itens de
inteligência da origem que ela tem de carregar: bloqueantes, as duas passadas, as 6 partes do
roteiro, o teste das dez palavras, as 9 seções da leitura, o checklist de parecença, as red flags,
as perguntas do corte, a ordem da aula, o roteiro do revisor. Cada item tem um texto-âncora curto,
sem marca, e a origem `arquivo:linha` (com a `sonda`, o trecho literal da origem naquela linha).

Este módulo valida só as fixtures e o verificador. A presença das âncoras nas skills é cobrada
pelos test_skill_* da F-09.2, que importam daqui:

    from plugin.test_ancoras import carregar_fixture, itens_faltantes
    faltam = itens_faltantes(carregar_fixture("criar-reel"), [skill, roteirista])
    assert faltam == []
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

import pytest

from test_marca import carregar_termos

TESTES = Path(__file__).resolve().parents[1]
FIXTURES = TESTES / "fixtures" / "inteligencia"
REPO = TESTES.parents[1]
PROJETOS = REPO.parent  # os projetos de origem são irmãos do ExpxMedia (D-37: só leitura)
ORIGENS = ("Instagram-Carrosseis", "Instragram-Videos", "cursos-ia", "youtube-squad", "ExpxMeta")

# O mínimo por categoria que cada fixture tem de atingir (T-09.11). Mora aqui, e não na fixture,
# para uma fixture não conseguir baixar o próprio piso.
MINIMOS: dict[str, dict[str, int]] = {
    "reel-por-referencia": {"leitura_9_secoes": 9, "checklist_parecenca": 9, "red_flags": 9},
    "criar-reel": {"seis_partes": 6, "dez_palavras": 3},
    "criar-carrossel": {"duas_passadas": 2, "bloqueantes": 13},
    "cortar-video": {"perguntas_corte": 4},
    "criar-aula": {"ordem_pipeline": 6, "avatar_audio": 1},
    "revisor-reel": {"veracidade": 2, "frame_abertura": 4, "veredito": 2},
}

# Itens que a task nomeia um a um: não podem sumir da fixture.
OBRIGATORIOS: dict[str, set[str]] = {
    "criar-reel": {"beat-gancho", "beat-o-que-e", "beat-prova", "beat-como-usa", "beat-para-quem", "beat-cta",
                   "dez-palavras", "olho-fechado"},
    "criar-carrossel": {"passada-copy", "passada-arte", "travessao", "palavra-cta-publicacao", "abertura-14-dias",
                        "tratamento", "acento"},
    "cortar-video": {"sustenta-sozinho", "promete-3-segundos", "fecha", "rende-sem-apoio"},
    "criar-aula": {"avatar-do-audio", "avatar-nunca-do-texto", "roteiro-com-cues", "render-dois-formatos"},
    "revisor-reel": {"veracidade-beats", "linha-da-fonte", "rosto-porta-voz", "cartao-fora-do-rosto", "selo-igual-cta",
                     "veredito-publicar", "veredito-segurar"},
    "reel-por-referencia": {"parecenca", "rf-tipos-fixos", "rf-avatar-texto", "leitura-o-que-nao-vai"},
}

# Além da lista de marca do núcleo: o público e o nicho das origens não entram (M13).
MARCA_EXTRA = [re.compile(p, re.IGNORECASE) for p in (r"software\s*house", r"dono\s+de", r"\bexpx\b", r"@\w")]

_RE_ORIGEM = re.compile(r"^(?P<arquivo>(?:%s)/[^:]+):(?P<linha>\d+)(?:-(?P<fim>\d+))?$" % "|".join(map(re.escape, ORIGENS)))
_RE_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_TRACOS = str.maketrans({"–": "-", "—": "-", "‐": "-", "‑": "-"})


# ---------------------------------------------------------------- verificador (usado pela F-09.2)


def normalizar(texto: str) -> str:
    """Minúsculo, sem acento, sem ênfase de Markdown (* _ `), traços unificados e espaços colapsados."""
    texto = unicodedata.normalize("NFD", texto.casefold())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[*_`]", "", texto.translate(_TRACOS))
    return " ".join(texto.split())


def carregar_fixture(nome: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{nome}.json").read_text(encoding="utf-8"))


def itens_faltantes(fixture: dict[str, Any] | str, textos: str | Path | Iterable[str | Path]) -> list[str]:
    """Ids dos itens da fixture cuja âncora (ou alguma alternativa) não aparece em nenhum dos textos.

    `fixture`: o dict da fixture ou o nome dela. `textos`: texto, caminho de arquivo ou lista deles
    (a skill, as regras, o agente). A comparação ignora caixa, acento, ênfase de Markdown e espaços.
    """
    if isinstance(fixture, str):
        fixture = carregar_fixture(fixture)
    if isinstance(textos, (str, Path)):
        textos = [textos]
    partes = []
    for t in textos:
        partes.append(t.read_text(encoding="utf-8") if isinstance(t, Path) else t)
    corpo = normalizar("\n".join(partes))
    faltam = []
    for item in fixture["itens"]:
        ancoras = [item["ancora"], *item.get("alternativas", [])]
        if not any(normalizar(a) in corpo for a in ancoras):
            faltam.append(item["id"])
    return faltam


# ---------------------------------------------------------------- integração: as fixtures


def _fixtures():
    return sorted(p.stem for p in FIXTURES.glob("*.json"))


def test_existe_uma_fixture_por_skill():
    assert _fixtures() == sorted(MINIMOS)


@pytest.mark.parametrize("nome", sorted(MINIMOS))
def test_fixture_bem_formada(nome):
    f = carregar_fixture(nome)
    assert list(f)[0] == "expxmedia_ancoras" and f["expxmedia_ancoras"] == 1
    assert f["skill"] == nome
    assert f["descricao"].strip()
    assert f["alvos"] and all(a.startswith("nucleo/") and a.endswith(".md") for a in f["alvos"])
    ids = [i["id"] for i in f["itens"]]
    assert len(ids) == len(set(ids)), "id repetido"
    for item in f["itens"]:
        assert _RE_ID.match(item["id"]), item["id"]
        assert set(item) <= {"id", "categoria", "ancora", "alternativas", "origem", "sonda"}, item
        assert _RE_ID.match(item["categoria"].replace("_", "-")), item["categoria"]
        assert 0 < len(item["ancora"].strip()) <= 60, f"âncora vazia ou longa demais: {item['id']}"
        assert _RE_ORIGEM.match(item["origem"]), f"origem fora do formato Projeto/arquivo:linha: {item['origem']}"


@pytest.mark.parametrize("nome", sorted(MINIMOS))
def test_fixture_atinge_o_minimo_por_categoria(nome):
    f = carregar_fixture(nome)
    contagem: dict[str, int] = {}
    for item in f["itens"]:
        contagem[item["categoria"]] = contagem.get(item["categoria"], 0) + 1
    for categoria, minimo in MINIMOS[nome].items():
        assert contagem.get(categoria, 0) >= minimo, f"{nome}: {categoria} tem {contagem.get(categoria, 0)}, mínimo {minimo}"
    ids = {i["id"] for i in f["itens"]}
    assert OBRIGATORIOS[nome] <= ids, f"{nome}: faltam {sorted(OBRIGATORIOS[nome] - ids)}"


@pytest.mark.parametrize("nome", sorted(MINIMOS))
def test_ancoras_nao_se_cobrem_umas_as_outras(nome):
    """Âncora contida em outra da mesma fixture nunca faltaria sozinha: o verificador ficaria cego a ela."""
    itens = carregar_fixture(nome)["itens"]
    for a in itens:
        for b in itens:
            if a is not b:
                assert normalizar(a["ancora"]) not in normalizar(b["ancora"]), (a["id"], b["id"])


@pytest.mark.parametrize("nome", sorted(MINIMOS))
def test_fixture_sem_marca(nome):
    termos = [r for _, r in carregar_termos()] + MARCA_EXTRA
    f = carregar_fixture(nome)
    textos = [("descricao", f["descricao"])]
    for item in f["itens"]:
        textos += [(item["id"], item["ancora"]), (item["id"], item.get("sonda", ""))]
        textos += [(item["id"], a) for a in item.get("alternativas", [])]
    achados = [(onde, t.pattern) for onde, texto in textos for t in termos if t.search(texto)]
    assert not achados, f"marca na fixture {nome}: {achados}"


@pytest.mark.parametrize("nome", sorted(MINIMOS))
def test_origem_aponta_linha_real_com_a_sonda(nome):
    """A origem existe, a linha existe e a sonda está nela (projetos de origem só lidos, D-37).

    Sem os projetos de origem na máquina, confere só o formato (já feito acima), sem pular.
    """
    for item in carregar_fixture(nome)["itens"]:
        m = _RE_ORIGEM.match(item["origem"])
        arquivo = PROJETOS / m["arquivo"]
        projeto = PROJETOS / m["arquivo"].split("/")[0]
        if not projeto.is_dir():
            continue
        assert arquivo.is_file(), f"{item['id']}: origem inexistente {item['origem']}"
        linhas = arquivo.read_text(encoding="utf-8").splitlines()
        inicio = int(m["linha"])
        fim = int(m["fim"] or inicio)
        assert 1 <= inicio <= fim <= len(linhas), f"{item['id']}: linha fora do arquivo {item['origem']}"
        if item.get("sonda"):
            trecho = "\n".join(linhas[inicio - 1:fim])
            assert item["sonda"] in trecho, f"{item['id']}: a sonda não está em {item['origem']}"


# ---------------------------------------------------------------- funcional: o verificador


@pytest.mark.parametrize("nome", sorted(MINIMOS))
def test_verificador_aponta_exatamente_o_item_omitido(nome, tmp_path):
    f = carregar_fixture(nome)
    completa = "# Skill de teste\n\n" + "\n".join(f"- **{i['ancora']}**: explicado aqui." for i in f["itens"])
    assert itens_faltantes(f, completa) == []
    for omitido in f["itens"]:
        linhas = [f"- {i['ancora']}" for i in f["itens"] if i is not omitido]
        skill = tmp_path / "SKILL.md"
        skill.write_text("\n".join(linhas), encoding="utf-8")
        assert itens_faltantes(f, [skill]) == [omitido["id"]], omitido["id"]


def test_verificador_ignora_caixa_acento_markdown_e_traco():
    fixture = {"itens": [
        {"id": "a", "categoria": "c", "ancora": "Até 8 letras", "origem": "x"},
        {"id": "b", "categoria": "c", "ancora": "130-180 palavras", "origem": "x"},
        {"id": "c", "categoria": "c", "ancora": "passada 2", "alternativas": ["segunda passada"], "origem": "x"},
    ]}
    texto = "A palavra tem **ATE 8   LETRAS**; o roteiro fica em 130–180 palavras; na `segunda passada` a arte."
    assert itens_faltantes(fixture, texto) == []
    assert itens_faltantes(fixture, "nada disso") == ["a", "b", "c"]


def test_verificador_aceita_nome_da_fixture_e_varios_textos():
    f = carregar_fixture("revisor-reel")
    metade = len(f["itens"]) // 2
    texto_1 = "\n".join(i["ancora"] for i in f["itens"][:metade])
    texto_2 = "\n".join(i["ancora"] for i in f["itens"][metade:])
    assert itens_faltantes("revisor-reel", [texto_1, texto_2]) == []
    assert itens_faltantes("revisor-reel", texto_1) == [i["id"] for i in f["itens"][metade:]]
