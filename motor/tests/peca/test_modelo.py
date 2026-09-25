"""T-02.11: modelo de peça (CONTRATO-peca, CONTRATO-estado-eventos, M7, M9, M10, M15)."""
import json
import re
from pathlib import Path

import pytest

from expxmedia.nucleo import rastro, tempo
from expxmedia.peca import modelo

CHAVES = [
    "expxmedia_peca", "peca_id", "slug", "titulo", "tipo", "formatos", "status", "pack", "serie", "template",
    "porta_voz", "oferta", "vaga", "criada_em", "atualizado_em", "motivo_descarte", "conteudo", "slides",
    "compoe", "arquivos", "producao", "publicacoes", "metricas",
]


def _eventos(raiz):
    mes = tempo.agora(raiz).strftime("%Y-%m")
    eventos, corrompidas = rastro.ler(raiz, mes)
    assert corrompidas == 0
    return eventos


def _nova(raiz, **kw):
    kw.setdefault("tipo", "reel")
    kw.setdefault("titulo", "Fornada das 16h: o pão que sai quente")
    kw.setdefault("formatos", ["9:16"])
    return modelo.criar(raiz, **kw)


# ---------------------------------------------------------------- integração


def test_criar_grava_peca_json_completo_na_pasta_do_mes(instalacao):
    peca = _nova(instalacao, pack="expx-teste", status="roteiro")
    assert re.fullmatch(r"P-\d{8}-[0-9A-F]{4}", peca["peca_id"])
    assert list(peca) == CHAVES  # todas as chaves, na ordem do contrato (M7)
    mes = peca["criada_em"][:7]
    pasta = instalacao / "pecas" / mes / f"{peca['peca_id']}-fornada-das-16h-o-pao-que-sai-quente"
    assert modelo.pasta(instalacao, peca["peca_id"]) == pasta
    assert json.loads((pasta / "peca.json").read_text(encoding="utf-8")) == peca
    assert peca["status"] == "roteiro"
    assert peca["slides"] == [] and peca["compoe"] == [] and peca["arquivos"] == [] and peca["publicacoes"] == []
    assert peca["producao"] is None and peca["metricas"] is None and peca["motivo_descarte"] is None
    assert list(peca["conteudo"]) == ["gancho", "gancho_tipo", "cta", "cta_forma", "legenda", "roteiro"]
    assert peca["criada_em"].endswith("-03:00")  # fuso da Alma (M5)
    (evento,) = _eventos(instalacao)
    assert evento["evento"] == "peca_criada" and evento["peca_id"] == peca["peca_id"] and evento["pack"] == "expx-teste"
    assert evento["arquivos"] == [f"pecas/{mes}/{pasta.name}/peca.json"]  # relativo à raiz (M9)


def test_roteiro_para_produzida_grava_atomico_e_registra_evento(instalacao, monkeypatch):
    peca = _nova(instalacao, status="roteiro")
    pid = peca["peca_id"]
    (modelo.pasta(instalacao, pid) / "saida").mkdir()
    (modelo.pasta(instalacao, pid) / "saida" / "final.mp4").write_bytes(b"mp4")
    modelo.registrar_arquivo(instalacao, pid, "saida/final.mp4", papel="final", formato="9:16")
    modelo.registrar_producao(instalacao, pid, capacidades=["narrar", "renderizar_motion"],
                              provedores={"narrar": "elevenlabs", "renderizar_motion": "remotion"}, segundos=42.5)

    gravacoes = []
    original = modelo._arquivos.gravar_json
    monkeypatch.setattr(modelo._arquivos, "gravar_json", lambda c, d: (gravacoes.append(Path(c)), original(c, d)))

    antes = modelo.carregar(instalacao, pid)
    depois = modelo.mudar_status(instalacao, pid, "produzida")
    assert depois["status"] == "produzida"
    assert gravacoes == [modelo.pasta(instalacao, pid) / "peca.json"]  # pela escrita atômica (M15)
    assert modelo.carregar(instalacao, pid) == depois
    assert depois["atualizado_em"] >= antes["atualizado_em"]  # M10
    assert depois["arquivos"] == [{"caminho": "saida/final.mp4", "papel": "final", "formato": "9:16"}]
    assert depois["producao"]["capacidades"] == ["narrar", "renderizar_motion"]
    assert depois["producao"]["segundos"] == 42.5 and depois["producao"]["produzida_em"].endswith("-03:00")
    status = [e for e in _eventos(instalacao) if e["evento"] == "peca_status"]
    assert len(status) == 1
    assert status[0]["detalhe"] == "roteiro -> produzida" and status[0]["peca_id"] == pid
    assert list(modelo.pasta(instalacao, pid).glob("*.tmp")) == []


def test_ciclo_completo_ate_medida_e_publicacao(instalacao):
    pid = _nova(instalacao)["peca_id"]
    modelo.mudar_status(instalacao, pid, "roteiro")
    modelo.registrar_producao(instalacao, pid, capacidades=["renderizar_html"],
                              provedores={"renderizar_html": "playwright"}, segundos=3)
    for novo in ("produzida", "aprovada"):
        modelo.mudar_status(instalacao, pid, novo)
    pub = {"canal": "instagram", "provedor": "expxflow", "estado": "agendada",
           "agendada_para": "2026-09-25T12:00:00-03:00", "id_externo": "sched_1"}
    modelo.registrar_publicacao(instalacao, pid, pub)
    modelo.mudar_status(instalacao, pid, "agendada")
    modelo.registrar_publicacao(instalacao, pid, {**pub, "estado": "publicada", "publicada_em": "2026-09-25T12:00:05-03:00"})
    modelo.mudar_status(instalacao, pid, "publicada")
    final = modelo.mudar_status(instalacao, pid, "medida")
    assert final["status"] == "medida"
    # uma entrada por canal, completa (M7)
    assert len(final["publicacoes"]) == 1
    assert list(final["publicacoes"][0]) == ["canal", "provedor", "estado", "agendada_para", "publicada_em",
                                             "id_externo", "url", "automacao_dm", "erro"]
    assert final["publicacoes"][0]["estado"] == "publicada" and final["publicacoes"][0]["url"] is None
    detalhes = [e["detalhe"] for e in _eventos(instalacao) if e["evento"] == "peca_status"]
    assert detalhes == ["ideia -> roteiro", "roteiro -> produzida", "produzida -> aprovada", "aprovada -> agendada",
                        "agendada -> publicada", "publicada -> medida"]


def test_descartar_exige_motivo(instalacao):
    pid = _nova(instalacao)["peca_id"]
    with pytest.raises(modelo.ErroPeca, match="motivo"):
        modelo.mudar_status(instalacao, pid, "descartada")
    peca = modelo.mudar_status(instalacao, pid, "descartada", motivo="pauta repetida")
    assert peca["status"] == "descartada" and peca["motivo_descarte"] == "pauta repetida"
    with pytest.raises(modelo.ErroPeca):
        modelo.mudar_status(instalacao, pid, "roteiro")


# ---------------------------------------------------------------- funcional


def test_publicada_para_roteiro_e_recusado(instalacao):
    pid = _nova(instalacao, status="roteiro")["peca_id"]
    modelo.registrar_producao(instalacao, pid, capacidades=[], provedores={}, segundos=1)
    for novo in ("produzida", "aprovada", "publicada"):
        modelo.mudar_status(instalacao, pid, novo)
    eventos_antes = len(_eventos(instalacao))
    with pytest.raises(modelo.ErroTransicao, match="publicada -> roteiro"):
        modelo.mudar_status(instalacao, pid, "roteiro")
    with pytest.raises(modelo.ErroTransicao):
        modelo.mudar_status(instalacao, pid, "descartada", motivo="tarde demais")  # só antes de publicada
    assert modelo.carregar(instalacao, pid)["status"] == "publicada"
    assert len(_eventos(instalacao)) == eventos_antes


@pytest.mark.parametrize("de,para", [("ideia", "produzida"), ("roteiro", "aprovada"), ("ideia", "ideia"),
                                     ("roteiro", "ideia"), ("ideia", "inexistente")])
def test_transicoes_invalidas(instalacao, de, para):
    pid = _nova(instalacao, status=de)["peca_id"]
    with pytest.raises(modelo.ErroPeca):
        modelo.mudar_status(instalacao, pid, para)
    assert modelo.carregar(instalacao, pid)["status"] == de


def test_produzida_sem_producao_registrada_e_recusada(instalacao):
    pid = _nova(instalacao, status="roteiro")["peca_id"]
    with pytest.raises(modelo.ErroPeca, match="producao"):
        modelo.mudar_status(instalacao, pid, "produzida")


@pytest.mark.parametrize("kw", [
    {"tipo": "story"},
    {"tipo": None},
    {"tipo": "Reel"},
    {"tipo": "carrossel", "formatos": ["9:16"]},
    {"tipo": "reel", "formatos": []},
    {"tipo": "reel", "formatos": "9:16"},
    {"status": "produzida"},
    {"titulo": "!!!"},
])
def test_criar_recusa_entrada_fora_do_contrato(instalacao, kw):
    with pytest.raises(modelo.ErroPeca):
        _nova(instalacao, **kw)
    assert list((instalacao / "pecas").rglob("peca.json")) == []
    assert _eventos(instalacao) == []


def test_arquivo_e_publicacao_fora_do_contrato(instalacao, tmp_path):
    pid = _nova(instalacao)["peca_id"]
    with pytest.raises(modelo.ErroPeca):
        modelo.registrar_arquivo(instalacao, pid, "saida/x.mp4", papel="video")
    with pytest.raises(modelo.ErroPeca):
        modelo.registrar_arquivo(instalacao, pid, tmp_path / "fora.mp4", papel="final")  # fora da pasta da peça
    with pytest.raises(modelo.ErroPeca):
        modelo.registrar_publicacao(instalacao, pid, {"canal": "orkut", "provedor": "manual", "estado": "agendada"})
    # caminho absoluto dentro da pasta é gravado relativo (M9) e o registro é idempotente
    absoluto = modelo.pasta(instalacao, pid) / "texto" / "legenda.txt"
    modelo.registrar_arquivo(instalacao, pid, absoluto, papel="legenda")
    peca = modelo.registrar_arquivo(instalacao, pid, "texto/legenda.txt", papel="legenda")
    assert peca["arquivos"] == [{"caminho": "texto/legenda.txt", "papel": "legenda", "formato": None}]


def test_carregar_rejeita_versao_maior(instalacao):
    pid = _nova(instalacao)["peca_id"]
    caminho = modelo.pasta(instalacao, pid) / "peca.json"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["expxmedia_peca"] = 2
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    with pytest.raises(modelo.ErroPeca, match="versão"):
        modelo.carregar(instalacao, pid)
    with pytest.raises(modelo.ErroPeca):
        modelo.carregar(instalacao, "P-20000101-0000")
