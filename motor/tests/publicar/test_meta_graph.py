"""T-08.04: adaptador Graph API contra o stub (D-29, D-44; base/publicar-meta-graph.md)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from PIL import Image

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs import cloudflared_falso  # noqa: E402
from stubs.cloudflared_falso import cloudflared_no_path  # noqa: E402,F401  (fixture)
from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.ambiente import env as leitor_env  # noqa: E402
from expxmedia.nucleo import arquivos, rastro, tempo  # noqa: E402
from expxmedia.peca import modelo  # noqa: E402
from expxmedia.publicar import base, meta_graph, tunel  # noqa: E402

TOKEN = "token-falso-da-graph"
IG = "17841400000000001"
TUNEL = "https://tunel-falso-de-teste.trycloudflare.com/"


def _env(raiz):
    (raiz / ".env").write_text(f"META_GRAPH_TOKEN={TOKEN}\nMETA_IG_USER_ID={IG}\n", encoding="utf-8")


def _aprovar(raiz, peca_id):
    modelo.registrar_producao(raiz, peca_id, capacidades=["renderizar_html"],
                              provedores={"renderizar_html": "playwright"}, segundos=1)
    modelo.mudar_status(raiz, peca_id, "produzida")
    modelo.mudar_status(raiz, peca_id, "aprovada")


def _peca_com_slides(raiz, tipo, formato, tamanhos, midias=None):
    peca = modelo.criar(raiz, tipo=tipo, titulo=f"{tipo} de teste", formatos=[formato], status="roteiro",
                        conteudo={"legenda": "Legenda da peça #tag"})
    pasta = modelo.pasta(raiz, peca["peca_id"])
    (pasta / "slides").mkdir()
    slides = []
    for n, tamanho in enumerate(tamanhos, start=1):
        midia = (midias or {}).get(n, "imagem")
        if midia == "imagem":
            nome = f"slides/slide_{n:02d}.png"
            Image.new("RGBA", tamanho, (30, 60, 200, 255)).save(pasta / nome)
        else:
            nome = f"slides/slide_{n:02d}.mp4"
            (pasta / nome).write_bytes(b"\x00\x00\x00\x18ftypmp42video-falso")
        slides.append({"n": n, "kind": "frase", "midia": midia, "arquivo": nome,
                       "duracao_s": 5 if midia == "video" else None})
    corpo = modelo.carregar(raiz, peca["peca_id"])
    corpo["slides"] = slides
    arquivos.gravar_json(pasta / "peca.json", corpo)
    _aprovar(raiz, peca["peca_id"])
    return peca["peca_id"]


class Espiao:
    """Abre o túnel de verdade (com o cloudflared falso) e guarda o que foi exposto."""

    def __init__(self):
        self.expostos = []
        self.aberto = None

    def __call__(self, caminhos):
        for c in caminhos:
            self.expostos.append((Path(c).suffix, Path(c).read_bytes()[:3]))
        self.aberto = tunel.abrir(caminhos, confirmar=False)
        return self.aberto


def _adaptador(raiz, stub, espiao=None):
    return meta_graph.MetaGraph.da_instalacao(
        raiz, leitor_env.carregar(raiz), url_base=stub.url, abrir_tunel=espiao or Espiao(),
        intervalo_status=0, pausar=lambda s: None)


def _limite(stub, uso):
    stub.rota("GET", f"/{IG}/content_publishing_limit",
              json={"data": [{"quota_usage": uso, "config": {"quota_total": 50, "quota_duration": 86400}}]})


# --- integração -------------------------------------------------------------------------

def test_carrossel_de_3_pngs_cria_3_filhos_jpeg_um_pai_e_publica_depois_de_finished(
        instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao)
    _limite(servidor_stub, 3)
    servidor_stub.rota("POST", f"/{IG}/media", sequencia=[
        {"json": {"id": "c1"}}, {"json": {"id": "c2"}}, {"json": {"id": "c3"}}, {"json": {"id": "pai"}}])
    for filho in ("c1", "c2", "c3"):
        servidor_stub.rota("GET", f"/{filho}", json={"status_code": "FINISHED", "id": filho})
    servidor_stub.rota("GET", "/pai", sequencia=[
        {"json": {"status_code": "IN_PROGRESS", "id": "pai"}}, {"json": {"status_code": "FINISHED", "id": "pai"}}])
    servidor_stub.rota("POST", f"/{IG}/media_publish", json={"id": "midia_9"})
    servidor_stub.rota("GET", "/midia_9", json={"permalink": "https://permalink.invalid/p/abc", "id": "midia_9"})
    peca_id = _peca_com_slides(instalacao, "carrossel", "4:5", [(1080, 1350)] * 3)
    espiao = Espiao()

    saida = base.publicar(instalacao, peca_id, adaptador=_adaptador(instalacao, servidor_stub, espiao))

    # PNG virou JPEG antes de ser exposto (a Graph só aceita JPEG)
    assert [s for s, _ in espiao.expostos] == [".jpg"] * 3
    assert all(magia == b"\xff\xd8\xff" for _, magia in espiao.expostos)
    criacoes = servidor_stub.requisicoes_de("POST", f"/{IG}/media")
    filhos, pai = criacoes[:3], criacoes[3]
    assert len(criacoes) == 4
    for req in filhos:
        assert req.json["is_carousel_item"] is True
        assert req.json["image_url"].startswith(TUNEL) and req.json["image_url"].endswith(".jpg")
        assert req.json["access_token"] == TOKEN
    assert pai.json["media_type"] == "CAROUSEL" and pai.json["children"] == "c1,c2,c3"
    assert pai.json["caption"] == "Legenda da peça #tag"
    # ordem: limite antes de tudo; media_publish depois do FINISHED do pai
    ordem = [(r.metodo, r.caminho) for r in servidor_stub.requisicoes]
    assert ordem[0] == ("GET", f"/{IG}/content_publishing_limit")
    consultas_pai = [i for i, o in enumerate(ordem) if o == ("GET", "/pai")]
    publicacao = ordem.index(("POST", f"/{IG}/media_publish"))
    assert len(consultas_pai) == 2 and consultas_pai[-1] < publicacao
    assert servidor_stub.requisicoes_de("POST", f"/{IG}/media_publish")[0].json["creation_id"] == "pai"
    assert len(servidor_stub.requisicoes_de("POST", f"/{IG}/media_publish")) == 1
    # o túnel ficou aberto até publicar e fechou depois
    assert espiao.aberto.processo.poll() is not None
    assert any(e["evento"] == "encerrado" for e in cloudflared_falso.eventos(cloudflared_no_path))

    peca = modelo.carregar(instalacao, peca_id)
    assert peca["status"] == "publicada"
    pub = peca["publicacoes"][0]
    assert pub["provedor"] == "meta_graph" and pub["estado"] == "publicada"
    assert pub["id_externo"] == "midia_9" and pub["url"] == "https://permalink.invalid/p/abc"
    assert pub["publicada_em"]
    assert saida["canais"]["instagram"]["estado"] == "publicada"
    assert TOKEN not in str(saida)


def test_reel_cria_conteiner_reels_com_video_url(instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao)
    _limite(servidor_stub, 0)
    peca = modelo.criar(instalacao, tipo="reel", titulo="Reel", formatos=["9:16"], status="roteiro",
                        conteudo={"legenda": "Legenda do reel"})
    pasta = modelo.pasta(instalacao, peca["peca_id"])
    (pasta / "saida").mkdir()
    (pasta / "saida" / "final.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42reel")
    modelo.registrar_arquivo(instalacao, peca["peca_id"], "saida/final.mp4", papel="final", formato="9:16")
    _aprovar(instalacao, peca["peca_id"])
    servidor_stub.rota("POST", f"/{IG}/media", json={"id": "r1"})
    servidor_stub.rota("GET", "/r1", json={"status_code": "FINISHED"})
    servidor_stub.rota("POST", f"/{IG}/media_publish", json={"id": "m_r"})
    servidor_stub.rota("GET", "/m_r", json={"permalink": "https://permalink.invalid/reel/r"})

    base.publicar(instalacao, peca["peca_id"], adaptador=_adaptador(instalacao, servidor_stub))

    [criacao] = servidor_stub.requisicoes_de("POST", f"/{IG}/media")
    assert criacao.json["media_type"] == "REELS" and criacao.json["video_url"].startswith(TUNEL)
    assert criacao.json["video_url"].endswith(".mp4") and criacao.json["share_to_feed"] is True
    assert modelo.carregar(instalacao, peca["peca_id"])["publicacoes"][0]["estado"] == "publicada"


def test_agendar_por_meta_graph_so_registra_para_o_agendador_local(instalacao, servidor_stub):
    _env(instalacao)
    (instalacao / ".expxmedia").mkdir()
    (instalacao / ".expxmedia" / "agendador.json").write_text('{"instalado": true}', encoding="utf-8")
    peca_id = _peca_com_slides(instalacao, "post_unico", "4:5", [(1080, 1350)])
    horario = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).isoformat()
    base.publicar(instalacao, peca_id, agendada_para=horario, adaptador=_adaptador(instalacao, servidor_stub))
    assert servidor_stub.requisicoes == []
    pub = modelo.carregar(instalacao, peca_id)["publicacoes"][0]
    assert pub["estado"] == "agendada" and pub["provedor"] == "meta_graph" and pub["id_externo"] is None
    assert modelo.carregar(instalacao, peca_id)["status"] == "agendada"


# --- funcional --------------------------------------------------------------------------

def test_post_9_16_e_recusado_antes_de_qualquer_chamada_com_achado_de_proporcao(
        instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao)
    _limite(servidor_stub, 0)
    peca_id = _peca_com_slides(instalacao, "post_unico", "9:16", [(1080, 1920)])
    with pytest.raises(base.ErroValidacao) as erro:
        base.publicar(instalacao, peca_id, adaptador=_adaptador(instalacao, servidor_stub))
    assert [a["codigo"] for a in erro.value.achados] == ["proporcao"]
    assert servidor_stub.requisicoes == []
    assert cloudflared_falso.eventos(cloudflared_no_path) == []
    assert modelo.carregar(instalacao, peca_id)["publicacoes"] == []


@pytest.mark.parametrize("tamanho,aceita", [((1080, 1350), True), ((1080, 1080), True), ((1910, 1000), True),
                                            ((1080, 1351), False), ((1920, 1000), False)])
def test_limites_de_proporcao_4_5_a_1_91(instalacao, servidor_stub, tamanho, aceita):
    _env(instalacao)
    peca_id = _peca_com_slides(instalacao, "post_unico", "4:5", [tamanho])
    adaptador = _adaptador(instalacao, servidor_stub)
    pedido = base.Pedido(raiz=instalacao, peca=modelo.carregar(instalacao, peca_id),
                         pasta=modelo.pasta(instalacao, peca_id), capacidade="publicar", canais=["instagram"],
                         agendada_para=None, dry_run=False, automacao=None, chave_idempotencia="x")
    achados = adaptador.validar(pedido)
    assert (achados == []) is aceita


def test_carrossel_com_11_itens_e_recusado(instalacao, servidor_stub):
    _env(instalacao)
    peca_id = _peca_com_slides(instalacao, "carrossel", "4:5", [(1080, 1350)] * 11)
    with pytest.raises(base.ErroValidacao) as erro:
        base.publicar(instalacao, peca_id, adaptador=_adaptador(instalacao, servidor_stub))
    assert "itens" in [a["codigo"] for a in erro.value.achados]
    assert servidor_stub.requisicoes == []


def test_limite_de_50_em_24h_recusa_sem_criar_conteiner(instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao)
    _limite(servidor_stub, 50)
    servidor_stub.rota("POST", f"/{IG}/media", json={"id": "nao-devia"})
    peca_id = _peca_com_slides(instalacao, "post_unico", "4:5", [(1080, 1350)])
    with pytest.raises(base.ErroEnvio) as erro:
        base.publicar(instalacao, peca_id, adaptador=_adaptador(instalacao, servidor_stub))
    assert erro.value.codigo == "limite_24h" and not erro.value.incerto
    assert servidor_stub.requisicoes_de("POST", f"/{IG}/media") == []
    assert servidor_stub.requisicoes_de("POST", f"/{IG}/media_publish") == []
    assert cloudflared_falso.eventos(cloudflared_no_path) == []
    pub = modelo.carregar(instalacao, peca_id)["publicacoes"][0]
    assert pub["estado"] == "falhou" and "50" in pub["erro"]
    mes = tempo.agora(instalacao).strftime("%Y-%m")
    assert [e["evento"] for e in rastro.ler(instalacao, mes)[0]].count("publicacao_falhou") == 1


def test_cota_do_provedor_menor_que_50_vale_a_menor(instalacao, servidor_stub):
    _env(instalacao)
    servidor_stub.rota("GET", f"/{IG}/content_publishing_limit",
                       json={"data": [{"quota_usage": 25, "config": {"quota_total": 25, "quota_duration": 86400}}]})
    peca_id = _peca_com_slides(instalacao, "post_unico", "4:5", [(1080, 1350)])
    with pytest.raises(base.ErroEnvio) as erro:
        base.publicar(instalacao, peca_id, adaptador=_adaptador(instalacao, servidor_stub))
    assert erro.value.codigo == "limite_24h"
    assert meta_graph.LIMITE_24H == 50


def test_conteiner_com_erro_nao_publica(instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao)
    _limite(servidor_stub, 0)
    servidor_stub.rota("POST", f"/{IG}/media", json={"id": "c_err"})
    servidor_stub.rota("GET", "/c_err", json={"status_code": "ERROR", "status": "Error: formato"})
    peca_id = _peca_com_slides(instalacao, "post_unico", "4:5", [(1080, 1350)])
    with pytest.raises(base.ErroEnvio) as erro:
        base.publicar(instalacao, peca_id, adaptador=_adaptador(instalacao, servidor_stub))
    assert erro.value.codigo == "conteiner_error" and not erro.value.incerto
    assert servidor_stub.requisicoes_de("POST", f"/{IG}/media_publish") == []


def test_media_publish_com_5xx_nao_e_retentado_e_fica_incerto(instalacao, servidor_stub, cloudflared_no_path):
    _env(instalacao)
    _limite(servidor_stub, 0)
    servidor_stub.rota("POST", f"/{IG}/media", json={"id": "c5"})
    servidor_stub.rota("GET", "/c5", json={"status_code": "FINISHED"})
    servidor_stub.rota("POST", f"/{IG}/media_publish", sequencia=[
        {"status": 500, "json": {"error": {"message": "erro interno", "code": -1, "error_subcode": 2207001}}},
        {"json": {"id": "nao-devia"}}])
    peca_id = _peca_com_slides(instalacao, "post_unico", "4:5", [(1080, 1350)])
    with pytest.raises(base.ErroEnvio) as erro:
        base.publicar(instalacao, peca_id, adaptador=_adaptador(instalacao, servidor_stub))
    assert erro.value.incerto
    assert len(servidor_stub.requisicoes_de("POST", f"/{IG}/media_publish")) == 1
    assert TOKEN not in str(erro.value)
    pub = modelo.carregar(instalacao, peca_id)["publicacoes"][0]
    assert pub["erro"].startswith(base.MARCA_INCERTO)


def test_token_recusado_cita_o_nome_da_variavel_sem_o_valor(instalacao, servidor_stub):
    _env(instalacao)
    servidor_stub.rota("GET", f"/{IG}/content_publishing_limit", status=400,
                       json={"error": {"message": "Invalid OAuth access token.", "type": "OAuthException", "code": 190}})
    peca_id = _peca_com_slides(instalacao, "post_unico", "4:5", [(1080, 1350)])
    with pytest.raises(base.ErroEnvio) as erro:
        base.publicar(instalacao, peca_id, adaptador=_adaptador(instalacao, servidor_stub))
    assert erro.value.codigo == "token" and "META_GRAPH_TOKEN" in str(erro.value)
    assert TOKEN not in str(erro.value)
    assert repr(_adaptador(instalacao, servidor_stub)).count(TOKEN) == 0
