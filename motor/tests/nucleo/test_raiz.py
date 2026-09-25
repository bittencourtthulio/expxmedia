"""T-02.04: raiz da instalação e caminhos relativos (M9)."""
from pathlib import Path

import pytest

from expxmedia.nucleo import raiz


# ---------- integração: a partir de uma subpasta de pecas/ ----------

def test_encontrar_raiz_a_partir_de_subpasta_de_pecas(instalacao):
    funda = instalacao / "pecas" / "2026-09" / "P-20260924-A3F9-gancho" / "slides"
    funda.mkdir(parents=True)
    assert raiz.encontrar_raiz(funda) == instalacao.resolve()
    # também a partir de um arquivo, e da própria raiz
    arquivo = funda / "slide_01.png"
    arquivo.write_bytes(b"")
    assert raiz.encontrar_raiz(arquivo) == instalacao.resolve()
    assert raiz.encontrar_raiz(instalacao) == instalacao.resolve()


def test_encontrar_raiz_usa_pasta_atual_por_padrao(instalacao, monkeypatch):
    monkeypatch.chdir(instalacao / "estado")
    assert raiz.encontrar_raiz() == instalacao.resolve()


def test_encontrar_raiz_exige_pasta_alma(tmp_path):
    (tmp_path / "pecas" / "x").mkdir(parents=True)
    (tmp_path / "alma").write_text("não é pasta", encoding="utf-8")
    with pytest.raises(raiz.ErroRaiz, match="alma/"):
        raiz.encontrar_raiz(tmp_path / "pecas" / "x")


# ---------- funcional: relativo e absoluto ----------

def test_relativo_converte_absoluto_dentro_da_raiz(instalacao):
    alvo = instalacao / "pecas" / "2026-09" / "P-20260924-A3F9-gancho" / "saida" / "final.mp4"
    assert raiz.relativo(instalacao, alvo) == "pecas/2026-09/P-20260924-A3F9-gancho/saida/final.mp4"
    # caminho que já é relativo à raiz volta normalizado, com barra normal
    assert raiz.relativo(instalacao, "pecas/./2026-09/../2026-09/a.png") == "pecas/2026-09/a.png"
    assert raiz.relativo(instalacao, Path("eventos") / "2026-09.jsonl") == "eventos/2026-09.jsonl"


def test_relativo_recusa_caminho_fora_da_raiz(instalacao, tmp_path):
    fora = tmp_path / "outra" / "segredo.txt"
    with pytest.raises(raiz.ErroCaminho):
        raiz.relativo(instalacao, fora)
    with pytest.raises(raiz.ErroCaminho):
        raiz.relativo(instalacao, "../fora.txt")
    with pytest.raises(raiz.ErroCaminho):
        raiz.relativo(instalacao, instalacao)  # a própria raiz não é um caminho de artefato
    # vizinho com prefixo igual no nome não conta como dentro
    with pytest.raises(raiz.ErroCaminho):
        raiz.relativo(instalacao, Path(str(instalacao) + "-copia") / "a.txt")


def test_relativo_resolve_link_simbolico_da_raiz(instalacao, tmp_path):
    atalho = tmp_path / "atalho"
    atalho.symlink_to(instalacao, target_is_directory=True)
    alvo = instalacao / "pecas" / "a.png"
    assert raiz.relativo(atalho, alvo) == "pecas/a.png"


def test_absoluto_e_o_inverso_e_recusa_fuga(instalacao):
    assert raiz.absoluto(instalacao, "pecas/2026-09/a.png") == instalacao.resolve() / "pecas" / "2026-09" / "a.png"
    with pytest.raises(raiz.ErroCaminho):
        raiz.absoluto(instalacao, "../../etc/passwd")
    with pytest.raises(raiz.ErroCaminho):
        raiz.absoluto(instalacao, str(instalacao / "pecas"))  # M9: o artefato guarda relativo
