"""T-02.03: rastro de eventos (CONTRATO-estado-eventos, M5, M7, M9, M15)."""
import json
import re
from datetime import datetime

import pytest

from expxmedia.nucleo import rastro, tempo

DOZE = [
    "ts", "expxmedia_eventos", "pack", "origem", "evento", "peca_id",
    "agente", "capacidade", "provedor", "resultado", "detalhe", "arquivos",
]


def _registrar_geracao(raiz, **extras):
    return rastro.registrar(
        raiz,
        origem="skill",
        evento="geracao_concluida",
        resultado="ok",
        peca_id="P-20260924-A3F9",
        agente="geradores",
        capacidade="renderizar_html",
        provedor="playwright",
        detalhe="3 slides em 57,5 s",
        arquivos=[raiz / "pecas" / "2026-09" / "P-20260924-A3F9-gancho" / "slides" / "slide_02.png"],
        **extras,
    )


# ---------- integração: grava em eventos/AAAA-MM.jsonl e relê ----------

def test_evento_gravado_no_mes_e_relido_com_as_doze_na_ordem(instalacao):
    gravado = _registrar_geracao(instalacao)

    mes = tempo.hoje(instalacao)[:7]
    arquivo = instalacao / "eventos" / f"{mes}.jsonl"
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 1
    relido = json.loads(linhas[0])  # json preserva a ordem das chaves da linha

    assert list(relido) == DOZE
    assert relido == gravado
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-03:00", relido["ts"]), relido["ts"]
    assert relido["ts"][:7] == mes
    assert relido["expxmedia_eventos"] == 1
    assert relido["pack"] == "nucleo"
    # M9: caminho relativo à raiz, com barra normal
    assert relido["arquivos"] == ["pecas/2026-09/P-20260924-A3F9-gancho/slides/slide_02.png"]

    assert rastro.ler(instalacao, mes) == ([relido], 0)


def test_chaves_ausentes_viram_null_e_lista_vazia(instalacao):
    gravado = rastro.registrar(instalacao, origem="humano", evento="alma_atualizada", resultado="ok")
    assert list(gravado) == DOZE
    for chave in ("peca_id", "agente", "capacidade", "provedor", "detalhe"):
        assert gravado[chave] is None
    assert gravado["arquivos"] == []


def test_arquivo_do_mes_segue_o_fuso_da_alma(instalacao, monkeypatch):
    # 2026-10-01T01:30Z ainda é setembro em São Paulo.
    instante = datetime.fromisoformat("2026-10-01T01:30:00+00:00")
    monkeypatch.setattr(rastro.tempo, "agora", lambda raiz: instante.astimezone(tempo.fuso(raiz)))
    gravado = rastro.registrar(instalacao, origem="rotina", evento="plano_gerado", resultado="ok")
    assert gravado["ts"] == "2026-09-30T22:30:00-03:00"
    assert (instalacao / "eventos" / "2026-09.jsonl").exists()
    assert not (instalacao / "eventos" / "2026-10.jsonl").exists()


# ---------- funcional: extras ----------

def test_extra_nao_declarada_levanta_e_nada_e_gravado(instalacao):
    with pytest.raises(rastro.ErroRastro, match="duracao"):
        _registrar_geracao(instalacao, duracao=12.5)
    assert list((instalacao / "eventos").iterdir()) == []


def test_extra_declarada_segundos_vem_depois_das_doze(instalacao):
    gravado = _registrar_geracao(instalacao, segundos=57.5)
    linha = (instalacao / "eventos").glob("*.jsonl").__next__().read_text(encoding="utf-8")
    relido = json.loads(linha)
    assert list(relido) == DOZE + ["segundos"]
    assert relido["segundos"] == 57.5
    assert relido == gravado


def test_extras_na_ordem_da_tabela(instalacao):
    gravado = rastro.registrar(
        instalacao, origem="rotina", evento="vaga_status", resultado="ok",
        vaga={"data": "2026-09-24", "id": "v3"}, hook="portao",
    )
    assert list(gravado)[12:] == ["hook", "vaga"]


# ---------- validação dos enums e formatos ----------

@pytest.mark.parametrize(
    "campos",
    [
        {"origem": "script"},
        {"resultado": "sucesso"},
        {"evento": "coisa_nova"},
        {"pack": "Expx Instagram"},
        {"peca_id": "P-2026-XYZ"},
        {"arquivos": ["/etc/passwd"]},
        {"arquivos": "pecas/a.png"},
        {"detalhe": 3},
    ],
)
def test_valores_fora_do_contrato_levantam(instalacao, campos):
    base = {"origem": "skill", "evento": "peca_criada", "resultado": "ok"}
    base.update(campos)
    with pytest.raises(rastro.ErroRastro):
        rastro.registrar(instalacao, **base)
    assert list((instalacao / "eventos").iterdir()) == []


def test_ler_mes_ausente_e_linha_corrompida(instalacao):
    assert rastro.ler(instalacao, "2020-01") == ([], 0)
    arquivo = instalacao / "eventos" / "2026-09.jsonl"
    arquivo.write_text('{quebrada\n{"ts":"x"}\n', encoding="utf-8")
    assert rastro.ler(instalacao, "2026-09") == ([{"ts": "x"}], 1)
    with pytest.raises(rastro.ErroRastro):
        rastro.ler(instalacao, "setembro")
