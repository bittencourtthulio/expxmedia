"""T-02.01: ids de peça e template (M11) e momentos com o fuso da Alma (M5)."""
import json
import re
from datetime import date, datetime, timedelta

import pytest

from expxmedia.nucleo import ids, tempo

PECA_2026_09_24 = re.compile(r"^P-20260924-[0-9A-F]{4}$")
TEMPLATE = re.compile(r"^carrossel-editorial-azul-[0-9a-f]{6}$")


def _trocar_fuso(raiz, fuso):
    alma = raiz / "alma" / "alma.json"
    dados = json.loads(alma.read_text(encoding="utf-8"))
    dados["empresa"]["fuso"] = fuso
    alma.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


# ---------- tempo: integração com a Alma fictícia ----------

def test_agora_usa_fuso_da_alma_sao_paulo(instalacao):
    momento = tempo.agora(instalacao)
    assert momento.utcoffset() == timedelta(hours=-3)
    texto = tempo.agora_iso(instalacao)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-03:00", texto), texto


def test_agora_segue_a_alma_e_nao_a_maquina(instalacao):
    # Tóquio não tem horário de verão: +09:00 o ano todo. Se agora() usasse o fuso da
    # máquina ou um fuso fixo, este teste falharia.
    _trocar_fuso(instalacao, "Asia/Tokyo")
    assert tempo.agora_iso(instalacao).endswith("+09:00")
    assert tempo.fuso(instalacao).key == "Asia/Tokyo"


def test_hoje_e_iso_no_fuso_da_alma(instalacao):
    # 2026-09-24T02:00Z é ainda dia 23 em São Paulo.
    instante = datetime.fromisoformat("2026-09-24T02:00:00+00:00")
    assert tempo.hoje(instalacao, instante) == "2026-09-23"
    assert tempo.iso(instante, instalacao) == "2026-09-23T23:00:00-03:00"


def test_fuso_ausente_ou_invalido_levanta_erro(instalacao):
    _trocar_fuso(instalacao, None)
    with pytest.raises(tempo.ErroFuso, match="empresa.fuso"):
        tempo.agora(instalacao)
    _trocar_fuso(instalacao, "Marte/Olimpo")
    with pytest.raises(tempo.ErroFuso, match="Marte/Olimpo"):
        tempo.agora(instalacao)


def test_iso_recusa_momento_sem_fuso():
    with pytest.raises(tempo.ErroFuso):
        tempo.iso(datetime(2026, 9, 24, 7, 0))


# ---------- ids: funcional ----------

def test_novo_peca_id_formato_e_1000_sem_repeticao():
    gerados = [ids.novo_peca_id(date(2026, 9, 24)) for _ in range(1000)]
    for peca_id in gerados:
        assert PECA_2026_09_24.fullmatch(peca_id), peca_id
    # 1000 sorteios em 65536 valores repetiriam ~7 vezes sem deduplicação.
    assert len(set(gerados)) == 1000


def test_novo_peca_id_aceita_texto_e_datetime():
    assert ids.novo_peca_id("2026-09-24").startswith("P-20260924-")
    momento = datetime.fromisoformat("2026-09-24T23:30:00-03:00")
    assert ids.novo_peca_id(momento).startswith("P-20260924-")
    with pytest.raises(ids.ErroId):
        ids.novo_peca_id("24/09/2026")


def test_novo_peca_id_nao_repete_peca_existente(instalacao, monkeypatch):
    mes = instalacao / "pecas" / "2026-09"
    mes.mkdir()
    # data só deste teste, para não cruzar com os ids que outro teste já gerou no processo
    (mes / "P-20260925-00A1-gancho-forte").mkdir()
    sorteios = iter([0x00A1, 0x00A1, 0x0B2C])
    monkeypatch.setattr(ids, "_sortear", lambda bits: next(sorteios))
    assert ids.novo_peca_id("2026-09-25", raiz=instalacao) == "P-20260925-0B2C"
    # e o mesmo processo não devolve 0B2C de novo
    monkeypatch.setattr(ids, "_sortear", lambda bits, s=iter([0x0B2C, 0x0C3D]): next(s))
    assert ids.novo_peca_id("2026-09-25", raiz=instalacao) == "P-20260925-0C3D"


def test_peca_id_valido():
    assert ids.peca_id_valido("P-20260924-A3F9")
    assert not ids.peca_id_valido("P-20260924-a3f9")
    assert not ids.peca_id_valido("P-2026092-A3F9")


def test_novo_template_id_formato_slug_e_deduplicacao(instalacao, monkeypatch):
    tid = ids.novo_template_id("carrossel", "Editorial Azul")
    assert TEMPLATE.fullmatch(tid), tid
    assert ids.novo_template_id("post_unico", "Número Gigante!").startswith("post_unico-numero-gigante-")

    existente = instalacao / "galeria" / "templates" / "carrossel-editorial-azul-3fa2c1"
    existente.mkdir(parents=True)
    sorteios = iter([0x3FA2C1, 0x3FA2C1, 0x00BEEF])
    monkeypatch.setattr(ids, "_sortear", lambda bits: next(sorteios))
    assert ids.novo_template_id("carrossel", "editorial-azul", raiz=instalacao) == "carrossel-editorial-azul-00beef"


def test_novo_template_id_recusa_tipo_ou_slug_vazio():
    with pytest.raises(ids.ErroId):
        ids.novo_template_id("Carrossel", "x")
    with pytest.raises(ids.ErroId):
        ids.novo_template_id("carrossel", "!!!")


def test_slug():
    assert ids.slug("  Imposto mal-enquadrado: o caso  ") == "imposto-mal-enquadrado-o-caso"
    assert ids.slug("Ação & Reação") == "acao-reacao"
