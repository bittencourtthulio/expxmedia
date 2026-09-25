"""T-03.14: retrato com rembg u2net, filtros de banco, slot pessoa e cota diária por provedor."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.imagem import cota, openrouter, retratos  # noqa: E402
from expxmedia.nucleo import tempo  # noqa: E402

RETRATO = "alma/assets/retratos/porta-voz-teste/01.png"


def _alma(raiz):
    return json.loads((raiz / "alma/alma.json").read_text(encoding="utf-8"))


def _gravar_alma(raiz, alma):
    (raiz / "alma/alma.json").write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")


# --- integração: rembg u2net de verdade, nesta máquina ------------------------------------

def test_recortar_retrato_do_porta_voz_gera_png_com_alfa_e_fundo_transparente(instalacao):
    r = retratos.recortar_retrato(instalacao, "porta-voz-teste", "pecas/x/retrato-sem-fundo.png")

    saida = instalacao / "pecas/x/retrato-sem-fundo.png"
    assert r["caminho"] == "pecas/x/retrato-sem-fundo.png"
    assert r["origem"] == RETRATO
    assert r["modelo"] == "u2net"
    with Image.open(saida) as img:
        assert img.format == "PNG" and img.mode == "RGBA"
        alfa = np.asarray(img.getchannel("A"))
    h, w = alfa.shape
    cantos = [alfa[:24, :24], alfa[:24, -24:]]  # cantos de cima: só fundo nesta foto
    assert all(c.max() < 16 for c in cantos), "o fundo não saiu transparente"
    assert alfa[h // 2 - 20:h // 2 + 20, w // 2 - 20:w // 2 + 20].min() > 240, "o rosto não ficou opaco"
    assert 0.2 < (alfa > 128).mean() < 0.9


# --- funcional ------------------------------------------------------------------------------

def test_modelo_registrado_e_u2net_nunca_u2netp(instalacao, monkeypatch):
    pedidos = []
    import rembg

    def sessao_falsa(nome, *a, **k):
        pedidos.append(nome)
        return object()

    def remover_falso(img, session=None, **k):
        return img.convert("RGBA")

    monkeypatch.setattr(rembg, "new_session", sessao_falsa)
    monkeypatch.setattr(rembg, "remove", remover_falso)
    monkeypatch.setattr(retratos, "_SESSOES", {})

    r = retratos.recortar(instalacao, RETRATO, "pecas/y.png")
    assert pedidos == ["u2net"]
    assert r["modelo"] == "u2net" == retratos.MODELO_RECORTE
    with pytest.raises(retratos.ErroRetrato):
        retratos.recortar(instalacao, RETRATO, "pecas/z.png", modelo="u2netp")
    assert pedidos == ["u2net"]


def test_slot_pessoa_numa_alma_sem_porta_voz_recebe_substituto_desenhado(instalacao):
    alma = _alma(instalacao)
    alma["porta_vozes"] = []
    _gravar_alma(instalacao, alma)

    r = retratos.resolver_slot_pessoa(instalacao)

    assert r["tipo"] == "substituto"
    assert r["caminho"] is None and r["porta_voz"] is None
    raiz_svg = ET.fromstring(r["svg"])
    assert raiz_svg.tag.endswith("svg")
    cores = alma["visual"]["cores"]
    assert cores["fundo_alt"] in r["svg"] and cores["apoio"] in r["svg"]  # cores da Alma, nada fixo
    assert "foto" in r["aviso"]


def test_slot_pessoa_com_porta_voz_usa_o_retrato_e_recusa_foto_de_banco(instalacao):
    r = retratos.resolver_slot_pessoa(instalacao)
    assert r == {"tipo": "retrato", "caminho": RETRATO, "porta_voz": "porta-voz-teste", "svg": None, "aviso": None}

    (instalacao / "pecas").mkdir(exist_ok=True)
    Image.new("RGB", (10, 10)).save(instalacao / "pecas/pexels-1.jpg")
    with pytest.raises(retratos.ErroRetrato):
        retratos.resolver_slot_pessoa(instalacao, valor="pecas/pexels-1.jpg")
    assert retratos.resolver_slot_pessoa(instalacao, valor=RETRATO)["caminho"] == RETRATO

    # porta-voz sem retrato no disco também cai no substituto
    (instalacao / RETRATO).unlink()
    assert retratos.resolver_slot_pessoa(instalacao, "porta-voz-teste")["tipo"] == "substituto"


def test_cada_filtro_de_banco_descarta_o_caso_dele():
    itens = [
        {"id": 1, "largura": 3000, "altura": 2000, "alt": "fresh bread on a wooden table"},
        {"id": 2, "largura": 1600, "altura": 1199, "alt": "oven"},  # lado curto abaixo de 1200
        {"id": 3, "largura": 3000, "altura": 2000, "alt": "a woman holding bread"},  # pessoa no alt
        {"id": 4, "largura": 3000, "altura": 2000, "alt": "flour"},  # já conhecida
        {"id": 1, "largura": 3000, "altura": 2000, "alt": "fresh bread on a wooden table"},  # repetida
        {"id": 5, "largura": 1200, "altura": 1800, "alt": "baguettes"},  # no limite: passa
    ]
    r = retratos.filtrar_banco(itens, conhecidos={4})
    assert [i["id"] for i in r["aprovados"]] == [1, 5]
    motivos = {(d["id"], d["motivo"]) for d in r["descartados"]}
    assert motivos == {(2, "tamanho"), (3, "pessoa_no_alt"), (4, "duplicata"), (1, "duplicata")}


def test_chamada_que_falha_incrementa_a_cota_do_dia(instalacao, servidor_stub):
    (instalacao / ".env").write_text("OPENROUTER_API_KEY=chave-falsa\n", encoding="utf-8")
    servidor_stub.rota("POST", "/api/v1/chat/completions", status=500, json={"error": {"message": "falhou"}})
    c = cota.Cota(instalacao)
    assert c.usadas("openrouter") == 0

    with pytest.raises(openrouter.ErroOpenRouter):
        openrouter.gerar(instalacao, "a loaf of bread on a wooden table", "pecas/a.png",
                         url_base=servidor_stub.url, cota=c.consumir)

    assert c.usadas("openrouter") == 1
    assert c.usadas("higgsfield") == 0  # cota por provedor
    dados = json.loads((instalacao / "estado/cotas.json").read_text(encoding="utf-8"))
    assert list(dados)[0] == "expxmedia_cotas"
    assert dados["dias"][tempo.hoje(instalacao)]["openrouter"] == 1


def test_teto_do_dia_barra_antes_de_chamar(instalacao, servidor_stub):
    (instalacao / ".env").write_text("OPENROUTER_API_KEY=chave-falsa\n", encoding="utf-8")
    servidor_stub.rota("POST", "/api/v1/chat/completions", status=500, json={})
    c = cota.Cota(instalacao)
    assert c.teto("openrouter") == 12  # origem: _galeria.py:703
    for _ in range(12):
        c.anotar("openrouter")
    with pytest.raises(cota.ErroCota):
        openrouter.gerar(instalacao, "a loaf of bread on a wooden table", "pecas/a.png",
                         url_base=servidor_stub.url, cota=c.consumir)
    assert servidor_stub.requisicoes == []
    assert c.usadas("openrouter") == 12


def test_cota_de_versao_maior_e_rejeitada(instalacao):
    (instalacao / "estado/cotas.json").write_text('{"expxmedia_cotas": 2, "dias": {}}', encoding="utf-8")
    with pytest.raises(cota.ErroCota):
        cota.Cota(instalacao).usadas("openrouter")
