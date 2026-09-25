"""T-08.07: CLI de publicação e do agendador — publicar, agendar, agendador rodar/instalar (D-07, D-11, D-29, D-30).

Provedores só contra o stub HTTP local (D-15): o `.env` da instalação aponta o Expx Flow para ele.
"""
from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from PIL import Image

_TESTS = str(Path(__file__).resolve().parent)
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia import cli  # noqa: E402
from expxmedia.agendador import instalar  # noqa: E402
from expxmedia.nucleo import rastro, tempo  # noqa: E402
from expxmedia.peca import modelo  # noqa: E402

MOTOR = Path(__file__).resolve().parents[1]
CHAVE = "chave-falsa-expxflow"
CLIENTE = "00000000-0000-4000-8000-000000000001"
EXE = "/opt/ferramentas/bin/expxmedia-motor"


def _env(raiz, url, extra=""):
    (raiz / ".env").write_text(
        f"EXPXFLOW_API_KEY={CHAVE}\nEXPXFLOW_CLIENT_ID={CLIENTE}\nEXPXFLOW_BASE_URL={url}\n{extra}", encoding="utf-8")


def _futuro():
    return (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).isoformat()


def _post(raiz, *, aprovar=True):
    """Post único com um PNG e legenda; `produzida` (ou `aprovada` com aprovar=True)."""
    peca = modelo.criar(raiz, tipo="post_unico", titulo="Post de teste", formatos=["4:5"], status="roteiro",
                        conteudo={"legenda": "Legenda do post.\n\n#tag1"})
    peca_id = peca["peca_id"]
    pasta = modelo.pasta(raiz, peca_id)
    (pasta / "saida").mkdir()
    Image.new("RGB", (1080, 1350), (40, 90, 160)).save(pasta / "saida" / "final.png")
    modelo.registrar_arquivo(raiz, peca_id, "saida/final.png", papel="final", formato="4:5")
    modelo.registrar_producao(raiz, peca_id, capacidades=["renderizar_html"],
                              provedores={"renderizar_html": "playwright"}, segundos=1)
    modelo.mudar_status(raiz, peca_id, "produzida")
    if aprovar:
        modelo.mudar_status(raiz, peca_id, "aprovada")
    return peca_id


def _rodar(capsys, *argv):
    codigo = cli.main([str(a) for a in argv])
    return codigo, json.loads(capsys.readouterr().out)


def _eventos_publicacao(raiz):
    eventos, _ = rastro.ler(raiz, tempo.agora(raiz).strftime("%Y-%m"))
    return [e for e in eventos if e["evento"].startswith("publicacao_")]


# --- integração -------------------------------------------------------------------------

def test_publicar_sem_confirmar_e_dry_run_pelo_executavel_e_sai_0(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    peca_id = _post(instalacao, aprovar=False)  # dry-run aceita peça só produzida
    antes = (modelo.pasta(instalacao, peca_id) / "peca.json").read_bytes()

    proc = subprocess.run(
        ["uv", "run", "--project", str(MOTOR), "expxmedia-motor", "publicar", "--peca", peca_id,
         "--raiz", str(instalacao)],
        capture_output=True, text=True, cwd=MOTOR,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    saida = json.loads(proc.stdout)
    assert saida["ok"] is True and saida["dry_run"] is True
    assert saida["capacidade"] == "publicar" and saida["provedor"] == "expxflow"
    corpo = saida["payload"]["corpo"]
    assert saida["payload"]["rota"] == "/post-api"
    assert corpo["publish_now"] is True and corpo["content_type"] == "image"
    assert corpo["caption"] == "Legenda do post." and corpo["hashtags"] == "#tag1"
    assert corpo["image_url"].startswith("https://dry-run.invalid/")
    assert CHAVE not in proc.stdout
    # nada enviado, nada gravado
    assert servidor_stub.requisicoes == []
    assert (modelo.pasta(instalacao, peca_id) / "peca.json").read_bytes() == antes
    assert _eventos_publicacao(instalacao) == []


def test_publicar_com_confirmar_envia_uma_vez_ao_stub_e_grava_publicada(instalacao, servidor_stub, capsys):
    _env(instalacao, servidor_stub.url)
    servidor_stub.rota("POST", "/media-upload-api", status=201, json={
        "success": True, "data": {"image_url": servidor_stub.url + "/hospedado/final.png"}})
    servidor_stub.rota("POST", "/post-api", status=201, json={"success": True, "data": {
        "scheduled_post_id": "s_1", "published_now": True}})
    peca_id = _post(instalacao)

    codigo, saida = _rodar(capsys, "publicar", "--peca", peca_id, "--confirmar", "--raiz", instalacao)

    assert codigo == 0, saida
    assert saida["dry_run"] is False and saida["canais"]["instagram"]["estado"] == "publicada"
    [post] = servidor_stub.requisicoes_de("POST", "/post-api")
    assert post.json["image_url"] == servidor_stub.url + "/hospedado/final.png"
    assert post.cabecalhos["X-API-Key"] == CHAVE
    peca = modelo.carregar(instalacao, peca_id)
    assert peca["status"] == "publicada" and peca["publicacoes"][0]["id_externo"] == "s_1"


def test_agendar_sem_confirmar_monta_o_agendamento_sem_enviar(instalacao, servidor_stub, capsys):
    _env(instalacao, servidor_stub.url)
    peca_id = _post(instalacao)
    horario = _futuro()

    codigo, saida = _rodar(capsys, "agendar", "--peca", peca_id, "--para", horario,
                           "--canal", "instagram", "--canal", "facebook", "--raiz", instalacao)

    assert codigo == 0, saida
    assert saida["capacidade"] == "agendar" and saida["dry_run"] is True
    corpo = saida["payload"]["corpo"]
    assert corpo["scheduled_at"] == horario and "publish_now" not in corpo
    assert corpo["platforms"] == ["instagram", "facebook"]
    assert servidor_stub.requisicoes == []
    assert modelo.carregar(instalacao, peca_id)["status"] == "aprovada"


# --- funcional --------------------------------------------------------------------------

def test_agendar_com_provedor_sem_chave_sai_3_com_como_habilitar_e_nao_troca(instalacao, servidor_stub, capsys):
    # Expx Flow está satisfeito, mas PROVEDOR_AGENDAR aponta para meta_graph, sem chave (D-07)
    _env(instalacao, servidor_stub.url, "PROVEDOR_AGENDAR=meta_graph\n")
    peca_id = _post(instalacao)
    antes = (modelo.pasta(instalacao, peca_id) / "peca.json").read_bytes()

    codigo, saida = _rodar(capsys, "agendar", "--peca", peca_id, "--para", _futuro(), "--confirmar",
                           "--raiz", instalacao)

    assert codigo == cli.CAPACIDADE_NAO_HABILITADA == 3
    assert saida["ok"] is False and saida["erro"] == "capacidade_nao_habilitada"
    assert saida["capacidade"] == "agendar"
    assert "META_GRAPH_TOKEN" in saida["como_habilitar"]
    assert "provedor" not in saida  # não caiu para o expxflow
    assert servidor_stub.requisicoes == []
    assert (modelo.pasta(instalacao, peca_id) / "peca.json").read_bytes() == antes


def test_publicar_sem_nenhum_provedor_sai_3(instalacao, capsys):
    peca_id = _post(instalacao)
    codigo, saida = _rodar(capsys, "publicar", "--peca", peca_id, "--raiz", instalacao)
    assert codigo == 3 and saida["como_habilitar"]
    assert "EXPXFLOW_API_KEY" in saida["como_habilitar"]


def test_confirmar_em_peca_nao_aprovada_sai_2_sem_chamar_o_provedor(instalacao, servidor_stub, capsys):
    _env(instalacao, servidor_stub.url)
    peca_id = _post(instalacao, aprovar=False)
    codigo, saida = _rodar(capsys, "publicar", "--peca", peca_id, "--confirmar", "--raiz", instalacao)
    assert codigo == 2 and saida["erro"] == "peca_nao_aprovada"
    assert servidor_stub.requisicoes == []


def test_agendar_sem_fuso_sai_2(instalacao, servidor_stub, capsys):
    _env(instalacao, servidor_stub.url)
    peca_id = _post(instalacao)
    codigo, saida = _rodar(capsys, "agendar", "--peca", peca_id, "--para", "2026-12-01T12:00:00",
                           "--confirmar", "--raiz", instalacao)
    assert codigo == 2 and saida["erro"] == "horario_invalido"
    assert servidor_stub.requisicoes == []


def test_segundo_envio_confirmado_e_recusado_como_duplicado(instalacao, servidor_stub, capsys):
    _env(instalacao, servidor_stub.url)
    servidor_stub.rota("POST", "/media-upload-api", status=201, json={
        "success": True, "data": {"image_url": servidor_stub.url + "/hospedado/final.png"}})
    servidor_stub.rota("POST", "/post-api", status=201, json={"success": True, "data": {"scheduled_post_id": "s_a"}})
    peca_id = _post(instalacao)
    horario = _futuro()
    assert _rodar(capsys, "agendar", "--peca", peca_id, "--para", horario, "--confirmar", "--raiz", instalacao)[0] == 0

    codigo, saida = _rodar(capsys, "agendar", "--peca", peca_id, "--para", horario, "--confirmar",
                           "--raiz", instalacao)

    assert codigo == 2 and saida["erro"] == "ja_enviada"
    assert len(servidor_stub.requisicoes_de("POST", "/post-api")) == 1


def test_provedor_503_sai_1_incerto_com_uma_unica_chamada(instalacao, servidor_stub, capsys):
    _env(instalacao, servidor_stub.url)
    servidor_stub.rota("POST", "/media-upload-api", status=201, json={
        "success": True, "data": {"image_url": servidor_stub.url + "/hospedado/final.png"}})
    servidor_stub.rota("POST", "/post-api", status=503, json={"error": "indisponível"})
    peca_id = _post(instalacao)

    codigo, saida = _rodar(capsys, "publicar", "--peca", peca_id, "--confirmar", "--raiz", instalacao)

    assert codigo == 1 and saida["ok"] is False
    assert saida["erro"] == "http_503" and saida["incerto"] is True
    assert len(servidor_stub.requisicoes_de("POST", "/post-api")) == 1
    assert modelo.carregar(instalacao, peca_id)["publicacoes"][0]["estado"] == "falhou"


DM = {"keywords": ["receita", "receitas"], "mensagem": "Aqui está a receita.", "link": "https://exemplo.invalid/r",
      "link_label": "Ver receita", "match_mode": "any"}


def _dm(tmp_path, dados=DM):
    arquivo = tmp_path / "dm.json"
    arquivo.write_text(dados if isinstance(dados, str) else json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return arquivo


def test_agendar_com_dm_leva_o_bloco_automation_ao_expxflow(instalacao, servidor_stub, capsys, tmp_path):
    _env(instalacao, servidor_stub.url)
    peca_id = _post(instalacao)

    codigo, saida = _rodar(capsys, "agendar", "--peca", peca_id, "--para", _futuro(), "--dm", _dm(tmp_path),
                           "--raiz", instalacao)

    assert codigo == 0, saida
    assert saida["payload"]["corpo"]["automation"] == DM
    assert servidor_stub.requisicoes == []


def test_publicar_com_dm_confirmado_grava_a_palavra_da_automacao(instalacao, servidor_stub, capsys, tmp_path):
    _env(instalacao, servidor_stub.url)
    servidor_stub.rota("POST", "/media-upload-api", status=201, json={
        "success": True, "data": {"image_url": servidor_stub.url + "/hospedado/final.png"}})
    servidor_stub.rota("POST", "/post-api", status=201, json={"success": True, "data": {
        "scheduled_post_id": "s_dm", "published_now": True, "trigger_id": "t_1"}})
    peca_id = _post(instalacao)

    codigo, saida = _rodar(capsys, "publicar", "--peca", peca_id, "--dm", _dm(tmp_path), "--confirmar",
                           "--raiz", instalacao)

    assert codigo == 0, saida
    [post] = servidor_stub.requisicoes_de("POST", "/post-api")
    assert post.json["automation"]["keywords"] == ["receita", "receitas"]
    pub = modelo.carregar(instalacao, peca_id)["publicacoes"][0]
    assert json.dumps(pub, ensure_ascii=False).count("t_1") == 1 and "receita" in json.dumps(pub, ensure_ascii=False)


def test_dm_com_provedor_meta_graph_sai_3_com_como_habilitar(instalacao, servidor_stub, capsys, tmp_path):
    # Expx Flow configurado, mas a publicação está fixada no meta_graph: a DM não tem quem a faça
    _env(instalacao, servidor_stub.url,
         "PROVEDOR_PUBLICAR=meta_graph\nMETA_GRAPH_TOKEN=token-falso\nMETA_IG_USER_ID=123\n")
    peca_id = _post(instalacao)

    codigo, saida = _rodar(capsys, "publicar", "--peca", peca_id, "--dm", _dm(tmp_path), "--raiz", instalacao)

    assert codigo == cli.CAPACIDADE_NAO_HABILITADA
    assert saida["erro"] == "automacao_indisponivel"
    assert "expxflow" in saida["como_habilitar"] and "meta_graph" in saida["como_habilitar"]
    assert servidor_stub.requisicoes == []


def test_dm_sem_expxflow_configurado_sai_3_citando_automacao_dm(instalacao, capsys, tmp_path):
    (instalacao / ".env").write_text("META_GRAPH_TOKEN=token-falso\nMETA_IG_USER_ID=123\n", encoding="utf-8")
    peca_id = _post(instalacao)

    codigo, saida = _rodar(capsys, "publicar", "--peca", peca_id, "--dm", _dm(tmp_path), "--raiz", instalacao)

    assert codigo == cli.CAPACIDADE_NAO_HABILITADA, saida
    assert saida["capacidade"] == "automacao_dm"
    assert "EXPXFLOW_API_KEY" in saida["como_habilitar"]


@pytest.mark.parametrize("conteudo, trecho", [
    ('{"keywords": [', "campo 'dm': JSON inválido"),
    ('["receita"]', "campo 'dm': o arquivo precisa ser um objeto"),
    (None, "campo 'dm': arquivo não encontrado"),
])
def test_dm_arquivo_invalido_sai_2(instalacao, servidor_stub, capsys, tmp_path, conteudo, trecho):
    _env(instalacao, servidor_stub.url)
    peca_id = _post(instalacao)
    arquivo = _dm(tmp_path, conteudo) if conteudo is not None else tmp_path / "nao.json"
    codigo, saida = _rodar(capsys, "publicar", "--peca", peca_id, "--dm", arquivo, "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and trecho in saida["mensagem"], saida
    assert servidor_stub.requisicoes == []


def test_dm_sem_palavra_sai_2_pela_validacao_do_adaptador(instalacao, servidor_stub, capsys, tmp_path):
    _env(instalacao, servidor_stub.url)
    peca_id = _post(instalacao)
    codigo, saida = _rodar(capsys, "publicar", "--peca", peca_id, "--dm", _dm(tmp_path, {"mensagem": "oi"}),
                           "--raiz", instalacao)
    assert codigo == cli.ENTRADA_INVALIDA and saida["erro"] == "validacao"
    assert any(a["codigo"] == "automacao" for a in saida["achados"])


def _agendada_meta(raiz, horario):
    peca_id = _post(raiz)
    modelo.registrar_publicacao(raiz, peca_id, {
        "canal": "instagram", "provedor": "meta_graph", "estado": "agendada",
        "agendada_para": horario.isoformat(timespec="seconds"),
    })
    modelo.mudar_status(raiz, peca_id, "agendada")
    return peca_id


def test_agendador_rodar_faz_uma_rodada_do_servico(instalacao, capsys):
    agora = tempo.agora(instalacao).replace(microsecond=0)
    futura = _agendada_meta(instalacao, agora + timedelta(hours=2))
    atrasada = _agendada_meta(instalacao, agora - timedelta(hours=2))

    codigo, saida = _rodar(capsys, "agendador", "rodar", "--raiz", instalacao)

    assert codigo == 0, saida
    assert saida["travado"] is False and saida["pendentes"] == 1
    assert [i["peca_id"] for i in saida["atrasadas"]] == [atrasada]
    assert saida["publicadas"] == []
    pub = modelo.carregar(instalacao, atrasada)["publicacoes"][0]
    assert pub["estado"] == "falhou" and pub["erro"].startswith("atraso")
    assert modelo.carregar(instalacao, futura)["publicacoes"][0]["estado"] == "agendada"


@pytest.fixture
def casa(tmp_path, monkeypatch):
    home = tmp_path / "casa"
    monkeypatch.setenv("HOME", str(home))
    return home


def test_agendador_instalar_sem_aplicar_so_mostra(instalacao, casa, capsys, monkeypatch):
    chamadas = []
    monkeypatch.setattr(instalar, "_executar", lambda argv: chamadas.append(argv) or 0)

    codigo, saida = _rodar(capsys, "agendador", "instalar", "--sistema", "macos", "--executavel", EXE,
                           "--raiz", instalacao)

    assert codigo == 0, saida
    assert saida["aplicado"] is False
    [arquivo] = saida["arquivos"]
    plist = plistlib.loads(arquivo["conteudo"].encode("utf-8"))
    assert plist["ProgramArguments"] == [EXE, "agendador", "rodar", "--raiz", str(instalacao.resolve())]
    assert chamadas == [] and not casa.exists()
    assert not (instalacao / ".expxmedia" / "agendador.json").exists()


def test_agendador_instalar_com_aplicar_instala_e_grava_o_marcador(instalacao, casa, capsys, monkeypatch):
    chamadas = []
    monkeypatch.setattr(instalar, "_executar", lambda argv: chamadas.append(argv) or 0)

    codigo, saida = _rodar(capsys, "agendador", "instalar", "--aplicar", "--sistema", "macos",
                           "--executavel", EXE, "--raiz", instalacao)

    assert codigo == 0, saida
    assert saida["aplicado"] is True
    assert Path(saida["arquivos"][0]["destino"]).is_file()
    assert str(casa) in saida["arquivos"][0]["destino"]
    assert any(c[:2] == ["launchctl", "bootstrap"] for c in chamadas)
    marcador = json.loads((instalacao / ".expxmedia" / "agendador.json").read_text(encoding="utf-8"))
    assert marcador["instalado"] is True and marcador["sistema"] == "macos"


def test_agendador_instalar_com_comando_que_falha_sai_1_sem_marcador(instalacao, casa, capsys, monkeypatch):
    monkeypatch.setattr(instalar, "_executar", lambda argv: 5)
    codigo, saida = _rodar(capsys, "agendador", "instalar", "--aplicar", "--sistema", "macos",
                           "--executavel", EXE, "--raiz", instalacao)
    assert codigo == 1 and saida["erro"] == "instalacao_agendador"
    assert not (instalacao / ".expxmedia" / "agendador.json").exists()
