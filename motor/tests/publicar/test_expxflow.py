"""T-08.02: adaptador Expx Flow contra o stub (D-06, D-50; base/publicar-expxflow.md)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from PIL import Image

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs.cloudflared_falso import cloudflared_no_path  # noqa: E402,F401  (fixture)
from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.ambiente.verificar import ErroCapacidade  # noqa: E402
from expxmedia.nucleo import rastro, tempo  # noqa: E402
from expxmedia.peca import modelo  # noqa: E402
from expxmedia.publicar import base, expxflow, tunel  # noqa: E402

CHAVE = "chave-falsa-expxflow"
CLIENTE = "00000000-0000-4000-8000-000000000001"
ROTAS_DE_CRIACAO = ("/media-upload-api", "/carousel-api", "/post-api", "/instagram-automation-api")
AUTOMACAO = {"keywords": ["CONTA"], "mensagem": "Oi {nome_usuario}, segue o material.",
             "link": "https://exemplo.invalid/material", "link_label": "Abrir material"}


def _env(raiz, url):
    (raiz / ".env").write_text(
        f"EXPXFLOW_API_KEY={CHAVE}\nEXPXFLOW_CLIENT_ID={CLIENTE}\nEXPXFLOW_BASE_URL={url}\n", encoding="utf-8")


def _futuro():
    return (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).isoformat()


def _png(caminho, tamanho=(1080, 1350)):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", tamanho, (40, 90, 160)).save(caminho)


def _aprovar(raiz, peca_id):
    modelo.registrar_producao(raiz, peca_id, capacidades=["renderizar_html"],
                              provedores={"renderizar_html": "playwright"}, segundos=1)
    modelo.mudar_status(raiz, peca_id, "produzida")
    modelo.mudar_status(raiz, peca_id, "aprovada")


def _carrossel_misto(raiz):
    peca = modelo.criar(raiz, tipo="carrossel", titulo="Carrossel misto", formatos=["4:5"], status="roteiro",
                        conteudo={"legenda": "texto/legenda.txt"})
    pasta = modelo.pasta(raiz, peca["peca_id"])
    (pasta / "texto").mkdir()
    (pasta / "texto" / "legenda.txt").write_text("Primeira linha da legenda.\n\n#tag1 #tag2\n", encoding="utf-8")
    (pasta / "slides").mkdir()
    (pasta / "slides" / "slide_01.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42video-falso")
    _png(pasta / "slides" / "slide_02.png")
    corpo = modelo.carregar(raiz, peca["peca_id"])
    corpo["slides"] = [
        {"n": 1, "kind": "capa", "midia": "video", "arquivo": "slides/slide_01.mp4", "duracao_s": 6},
        {"n": 2, "kind": "frase", "midia": "imagem", "arquivo": "slides/slide_02.png", "duracao_s": None},
    ]
    from expxmedia.nucleo import arquivos
    arquivos.gravar_json(pasta / "peca.json", corpo)
    _aprovar(raiz, peca["peca_id"])
    return peca["peca_id"]


def _reel(raiz):
    peca = modelo.criar(raiz, tipo="reel", titulo="Reel de teste", formatos=["9:16"], status="roteiro",
                        conteudo={"legenda": "Legenda curta do reel"})
    pasta = modelo.pasta(raiz, peca["peca_id"])
    (pasta / "saida").mkdir()
    (pasta / "saida" / "final.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42reel-falso")
    modelo.registrar_arquivo(raiz, peca["peca_id"], "saida/final.mp4", papel="final", formato="9:16")
    _aprovar(raiz, peca["peca_id"])
    return peca["peca_id"]


def _tunel_sem_confirmar(arquivos):
    return tunel.abrir(arquivos, confirmar=False)


def _adaptador(raiz):
    from expxmedia.ambiente import env
    return expxflow.ExpxFlow.da_instalacao(raiz, env.carregar(raiz), abrir_tunel=_tunel_sem_confirmar)


def _upload_ok(stub):
    stub.rota("POST", "/media-upload-api", status=201, json={
        "success": True, "data": {"image_url": stub.url + "/hospedado/slide_02.png", "content_type": "image/png",
                                  "size_bytes": 10}})


# --- integração -------------------------------------------------------------------------

def test_carrossel_misto_envia_um_filho_com_image_url_e_outro_com_video_url(
        instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao, servidor_stub.url)
    _upload_ok(servidor_stub)
    servidor_stub.rota("POST", "/carousel-api", status=201, json={"success": True, "data": {
        "project_id": "proj_1", "scheduled_post_id": "sched_8f2a", "slides_count": 2,
        "scheduled_at": "2026-12-01T21:00:00.000Z", "published_now": False, "trigger_id": "trg_19c"}})
    peca_id = _carrossel_misto(instalacao)
    horario = _futuro()

    saida = base.publicar(instalacao, peca_id, agendada_para=horario, automacao=AUTOMACAO,
                          adaptador=_adaptador(instalacao))

    uploads = servidor_stub.requisicoes_de("POST", "/media-upload-api")
    assert len(uploads) == 1  # só a imagem sobe; vídeo vai pelo túnel (upload recusa mp4)
    assert b'name="file"' in uploads[0].corpo and b"slide_02.png" in uploads[0].corpo
    [criacao] = servidor_stub.requisicoes_de("POST", "/carousel-api")
    assert criacao.cabecalhos["X-API-Key"] == CHAVE
    assert criacao.cabecalhos["Idempotency-Key"].startswith(peca_id)
    corpo = criacao.json
    video, imagem = corpo["slides"]
    assert set(video) == {"video_url"} and video["video_url"].startswith("https://tunel-falso-de-teste.trycloudflare.com/")
    assert video["video_url"].endswith(".mp4")
    assert imagem == {"image_url": servidor_stub.url + "/hospedado/slide_02.png"}
    assert corpo["scheduled_at"] == horario and "publish_now" not in corpo
    assert corpo["platforms"] == ["instagram"] and corpo["client_id"] == CLIENTE
    assert corpo["caption"] == "Primeira linha da legenda." and corpo["hashtags"] == "#tag1 #tag2"
    assert corpo["title"] == "Carrossel misto"
    assert corpo["automation"]["keywords"] == ["CONTA"]
    # o túnel já fechou
    from stubs import cloudflared_falso
    assert any(e["evento"] == "encerrado" for e in cloudflared_falso.eventos(cloudflared_no_path))

    peca = modelo.carregar(instalacao, peca_id)
    assert peca["status"] == "agendada"
    pub = peca["publicacoes"][0]
    assert pub["provedor"] == "expxflow" and pub["estado"] == "agendada"
    assert pub["id_externo"] == "sched_8f2a" and pub["agendada_para"] == horario
    assert pub["automacao_dm"] == {"palavra": "CONTA", "id_externo": "trg_19c"}
    assert pub["erro"] is None
    assert saida["canais"]["instagram"]["estado"] == "agendada"
    assert CHAVE not in str(saida)


def test_reel_vai_pelo_post_api_com_content_type_reel(instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao, servidor_stub.url)
    servidor_stub.rota("POST", "/post-api", status=201, json={"success": True, "data": {
        "scheduled_post_id": "sched_r1", "content_type": "reel", "published_now": False, "trigger_id": "trg_r",
        "automation_status": "falhou", "automation_error": "conta sem permissão de comentários"}})
    peca_id = _reel(instalacao)

    base.publicar(instalacao, peca_id, agendada_para=_futuro(), automacao=AUTOMACAO, adaptador=_adaptador(instalacao))

    assert servidor_stub.requisicoes_de("POST", "/media-upload-api") == []
    [post] = servidor_stub.requisicoes_de("POST", "/post-api")
    assert post.json["content_type"] == "reel"
    assert post.json["image_url"].startswith("https://tunel-falso-de-teste.trycloudflare.com/")
    assert post.json["caption"] == "Legenda curta do reel" and "title" not in post.json
    pub = modelo.carregar(instalacao, peca_id)["publicacoes"][0]
    # post agendado, automação falhou: não é sucesso limpo (Instragram-Videos/.claude/rules/publicacao.md:57-61)
    assert pub["estado"] == "agendada" and "automação" in pub["erro"]
    mes = tempo.agora(instalacao).strftime("%Y-%m")
    agendados = [e for e in rastro.ler(instalacao, mes)[0] if e["evento"] == "publicacao_agendada"]
    assert agendados[-1]["resultado"] == "aviso"


def test_publicar_agora_usa_publish_now(instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao, servidor_stub.url)
    _upload_ok(servidor_stub)
    servidor_stub.rota("POST", "/carousel-api", status=201, json={"success": True, "data": {
        "scheduled_post_id": "s_now", "published_now": True}})
    peca_id = _carrossel_misto(instalacao)
    base.publicar(instalacao, peca_id, adaptador=_adaptador(instalacao))
    corpo = servidor_stub.requisicoes_de("POST", "/carousel-api")[0].json
    assert corpo["publish_now"] is True and "scheduled_at" not in corpo
    peca = modelo.carregar(instalacao, peca_id)
    assert peca["status"] == "publicada" and peca["publicacoes"][0]["estado"] == "publicada"


def test_vincular_automacao_em_post_existente(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    servidor_stub.rota("POST", "/instagram-automation-api", json={"success": True, "data": {
        "trigger_id": "trg_v", "flow_id": "f1", "status": "aguardando_publicacao"}})
    trigger = _adaptador(instalacao).vincular_automacao("sched_x", AUTOMACAO)
    assert trigger == "trg_v"
    [req] = servidor_stub.requisicoes_de("POST", "/instagram-automation-api")
    assert req.json == {"acao": "vincular_automacao", "scheduled_post_id": "sched_x", "automacao": AUTOMACAO}


# --- funcional --------------------------------------------------------------------------

def test_207_grava_na_peca_o_estado_de_cada_plataforma(instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao, servidor_stub.url)
    _upload_ok(servidor_stub)
    servidor_stub.rota("POST", "/carousel-api", status=207, json={"success": True, "data": {
        "project_id": "proj_2", "scheduled_post_id": "sched_207", "published_now": False,
        "platforms": {"instagram": {"success": True}, "facebook": {"success": False, "error": "página desconectada"}}}})
    peca_id = _carrossel_misto(instalacao)

    saida = base.publicar(instalacao, peca_id, canais=["instagram", "facebook"], agendada_para=_futuro(),
                          adaptador=_adaptador(instalacao))

    assert servidor_stub.requisicoes_de("POST", "/carousel-api")[0].json["platforms"] == ["instagram", "facebook"]
    pubs = {p["canal"]: p for p in modelo.carregar(instalacao, peca_id)["publicacoes"]}
    assert pubs["instagram"]["estado"] == "agendada" and pubs["instagram"]["id_externo"] == "sched_207"
    assert pubs["facebook"]["estado"] == "falhou" and "página desconectada" in pubs["facebook"]["erro"]
    assert pubs["facebook"]["id_externo"] == "sched_207"
    assert saida["canais"]["facebook"]["estado"] == "falhou"
    assert modelo.carregar(instalacao, peca_id)["status"] == "agendada"
    mes = tempo.agora(instalacao).strftime("%Y-%m")
    eventos = [e["evento"] for e in rastro.ler(instalacao, mes)[0]]
    assert "publicacao_agendada" in eventos and "publicacao_falhou" in eventos
    # o post existe no provedor: reenviar o facebook no mesmo horário é recusado
    with pytest.raises(base.ErroDuplicada):
        base.publicar(instalacao, peca_id, canais=["facebook"],
                      agendada_para=pubs["facebook"]["agendada_para"], adaptador=_adaptador(instalacao))


def test_207_sem_detalhe_por_plataforma_marca_todas_como_falhou(instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao, servidor_stub.url)
    _upload_ok(servidor_stub)
    servidor_stub.rota("POST", "/carousel-api", status=207, json={"success": True, "data": {
        "scheduled_post_id": "sched_207b"}})
    peca_id = _carrossel_misto(instalacao)
    base.publicar(instalacao, peca_id, canais=["instagram", "facebook"], agendada_para=_futuro(),
                  adaptador=_adaptador(instalacao))
    pubs = modelo.carregar(instalacao, peca_id)["publicacoes"]
    assert [p["estado"] for p in pubs] == ["falhou", "falhou"]
    assert all("207" in p["erro"] and p["id_externo"] == "sched_207b" for p in pubs)


def test_dry_run_nao_chama_nenhuma_rota_de_criacao(instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao, servidor_stub.url)
    peca_id = _carrossel_misto(instalacao)
    saida = base.publicar(instalacao, peca_id, agendada_para=_futuro(), automacao=AUTOMACAO,
                          adaptador=_adaptador(instalacao), dry_run=True)
    assert servidor_stub.requisicoes == []
    for rota in ROTAS_DE_CRIACAO:
        assert servidor_stub.requisicoes_de("POST", rota) == []
    payload = saida["payload"]
    assert payload["rota"] == "/carousel-api"
    assert "video_url" in payload["corpo"]["slides"][0] and "image_url" in payload["corpo"]["slides"][1]
    assert CHAVE not in str(saida)
    # nem o túnel abre no dry-run
    from stubs import cloudflared_falso
    assert cloudflared_falso.eventos(cloudflared_no_path) == []
    assert modelo.carregar(instalacao, peca_id)["publicacoes"] == []


def test_sem_base_url_no_env_nao_ha_provedor(instalacao, servidor_stub):
    (instalacao / ".env").write_text(f"EXPXFLOW_API_KEY={CHAVE}\nEXPXFLOW_CLIENT_ID={CLIENTE}\n", encoding="utf-8")
    peca_id = _reel(instalacao)
    with pytest.raises(ErroCapacidade) as erro:
        base.publicar(instalacao, peca_id, agendada_para=_futuro())
    assert "EXPXFLOW_BASE_URL" in str(erro.value)
    assert not hasattr(expxflow, "URL_BASE")


def test_validacoes_de_payload_antes_de_qualquer_chamada(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    peca_id = _reel(instalacao)
    adaptador = _adaptador(instalacao)
    perto = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    with pytest.raises(base.ErroValidacao) as erro:
        base.publicar(instalacao, peca_id, agendada_para=perto, adaptador=adaptador)
    assert erro.value.achados[0]["codigo"] == "antecedencia"
    ruim = dict(AUTOMACAO, link_label="rótulo com mais de vinte caracteres")
    with pytest.raises(base.ErroValidacao) as erro:
        base.publicar(instalacao, peca_id, agendada_para=_futuro(), automacao=ruim, adaptador=adaptador)
    assert erro.value.achados[0]["codigo"] == "automacao"
    with pytest.raises(base.ErroValidacao) as erro:
        base.publicar(instalacao, peca_id, canais=["youtube"], agendada_para=_futuro(), adaptador=adaptador)
    assert erro.value.achados[0]["codigo"] == "canal"
    assert servidor_stub.requisicoes == []
