"""T-08.01: base de publicação — provedor pela verificação, intenção antes do envio,
idempotência por canal e horário, POST nunca retentado (D-07, D-29)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.ambiente.verificar import ErroProvedor  # noqa: E402
from expxmedia.nucleo import rastro, tempo  # noqa: E402
from expxmedia.peca import modelo  # noqa: E402
from expxmedia.publicar import base  # noqa: E402

CHAVE = "chave-falsa-expxflow"
CLIENTE = "00000000-0000-4000-8000-000000000001"


def _env(raiz, url, extra=""):
    (raiz / ".env").write_text(
        f"EXPXFLOW_API_KEY={CHAVE}\nEXPXFLOW_CLIENT_ID={CLIENTE}\nEXPXFLOW_BASE_URL={url}\n{extra}",
        encoding="utf-8",
    )


def _peca_aprovada(raiz):
    peca = modelo.criar(raiz, tipo="post_unico", titulo="Peça de publicação", formatos=["4:5"], status="roteiro")
    modelo.registrar_producao(raiz, peca["peca_id"], capacidades=["renderizar_html"],
                              provedores={"renderizar_html": "playwright"}, segundos=1)
    modelo.mudar_status(raiz, peca["peca_id"], "produzida")
    modelo.mudar_status(raiz, peca["peca_id"], "aprovada")
    return peca["peca_id"]


def _eventos(raiz):
    mes = tempo.agora(raiz).strftime("%Y-%m")
    return rastro.ler(raiz, mes)[0]


class AdaptadorHttp:
    """Adaptador mínimo que faz o POST pelo cliente único da base, contra o stub."""

    provedor = "expxflow"

    def __init__(self, url):
        self.url = url
        self.pedidos = []
        self.intencao_no_envio = None

    def validar(self, pedido):
        return []

    def enviar(self, pedido):
        self.pedidos.append(pedido)
        # a intenção já está gravada quando o envio começa
        self.intencao_no_envio = modelo.carregar(pedido.raiz, pedido.peca["peca_id"])["publicacoes"]
        corpo = base.post_json(self.url + "/post-api", {"caption": "x"}, cabecalhos={"X-API-Key": CHAVE})
        dados = corpo.get("data") or {}
        return base.Resultado(canais={
            canal: base.ResultadoCanal(estado="agendada", id_externo=dados.get("scheduled_post_id"))
            for canal in pedido.canais
        })


def _futuro(horas=24):
    return (datetime.now(timezone.utc) + timedelta(hours=horas)).replace(microsecond=0).isoformat()


# --- integração -------------------------------------------------------------------------

def test_mesmo_canal_e_horario_ja_enviado_recusa_sem_chamar_o_provedor(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    servidor_stub.rota("POST", "/post-api", status=201,
                       json={"success": True, "data": {"scheduled_post_id": "sched_1"}})
    peca_id = _peca_aprovada(instalacao)
    horario = _futuro()
    adaptador = AdaptadorHttp(servidor_stub.url)

    saida = base.publicar(instalacao, peca_id, agendada_para=horario, adaptador=adaptador)
    assert saida["provedor"] == "expxflow" and saida["capacidade"] == "agendar"
    # a intenção estava gravada antes do envio, marcada como resultado ainda desconhecido
    assert len(adaptador.intencao_no_envio) == 1
    intencao = adaptador.intencao_no_envio[0]
    assert intencao["canal"] == "instagram" and intencao["provedor"] == "expxflow"
    assert intencao["erro"].startswith(base.MARCA_INCERTO)
    peca = modelo.carregar(instalacao, peca_id)
    assert peca["status"] == "agendada"
    assert peca["publicacoes"][0]["estado"] == "agendada"
    assert peca["publicacoes"][0]["id_externo"] == "sched_1"
    assert len(servidor_stub.requisicoes) == 1

    # o mesmo horário escrito em outro fuso é o mesmo instante: recusa
    mesmo = datetime.fromisoformat(horario).astimezone(timezone(timedelta(hours=-3))).isoformat()
    with pytest.raises(base.ErroDuplicada) as erro:
        base.publicar(instalacao, peca_id, agendada_para=mesmo, adaptador=adaptador)
    assert erro.value.codigo == "ja_enviada"
    assert len(adaptador.pedidos) == 1
    assert len(servidor_stub.requisicoes) == 1
    assert modelo.carregar(instalacao, peca_id)["publicacoes"][0]["id_externo"] == "sched_1"
    eventos = [e["evento"] for e in _eventos(instalacao)]
    assert eventos.count("publicacao_agendada") == 1


def test_intencao_sem_resultado_bloqueia_novo_envio_ate_forcar(instalacao, servidor_stub):
    """Processo que caiu no meio do envio deixa a intenção: ninguém reenvia às cegas."""
    _env(instalacao, servidor_stub.url)
    servidor_stub.rota("POST", "/post-api", status=201, json={"success": True, "data": {"scheduled_post_id": "s2"}})
    peca_id = _peca_aprovada(instalacao)
    horario = _futuro()

    class Caiu(AdaptadorHttp):
        def enviar(self, pedido):
            raise KeyboardInterrupt  # simula a queda depois do POST

    with pytest.raises(KeyboardInterrupt):
        base.publicar(instalacao, peca_id, agendada_para=horario, adaptador=Caiu(servidor_stub.url))
    pub = modelo.carregar(instalacao, peca_id)["publicacoes"][0]
    assert pub["estado"] == "falhou" and pub["erro"].startswith(base.MARCA_INCERTO)

    adaptador = AdaptadorHttp(servidor_stub.url)
    with pytest.raises(base.ErroDuplicada):
        base.publicar(instalacao, peca_id, agendada_para=horario, adaptador=adaptador)
    assert adaptador.pedidos == []
    base.publicar(instalacao, peca_id, agendada_para=horario, adaptador=adaptador, forcar=True)
    assert len(adaptador.pedidos) == 1


def test_provedor_escolhido_nao_satisfeito_nao_troca_em_silencio(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url, "PROVEDOR_AGENDAR=meta_graph\n")
    peca_id = _peca_aprovada(instalacao)
    adaptador = AdaptadorHttp(servidor_stub.url)
    with pytest.raises(ErroProvedor) as erro:
        base.publicar(instalacao, peca_id, agendada_para=_futuro(), adaptador=adaptador)
    assert "não troca de provedor" in str(erro.value)
    assert adaptador.pedidos == [] and servidor_stub.requisicoes == []
    assert modelo.carregar(instalacao, peca_id)["publicacoes"] == []
    assert any(e["evento"] == "capacidade_ausente" for e in _eventos(instalacao))


def test_adaptador_de_outro_provedor_e_recusado(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    peca_id = _peca_aprovada(instalacao)
    adaptador = AdaptadorHttp(servidor_stub.url)
    adaptador.provedor = "meta_graph"
    with pytest.raises(ErroProvedor):
        base.publicar(instalacao, peca_id, agendada_para=_futuro(), adaptador=adaptador)
    assert adaptador.pedidos == []


# --- funcional --------------------------------------------------------------------------

def test_provedor_503_gera_publicacao_falhou_com_uma_unica_chamada(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    # se houvesse retentativa, a segunda chamada teria sucesso e o teste veria agendada
    servidor_stub.rota("POST", "/post-api", sequencia=[
        {"status": 503, "json": {"success": False, "error": "indisponível"}},
        {"status": 201, "json": {"success": True, "data": {"scheduled_post_id": "nao-devia"}}},
    ])
    peca_id = _peca_aprovada(instalacao)

    with pytest.raises(base.ErroEnvio) as erro:
        base.publicar(instalacao, peca_id, agendada_para=_futuro(), adaptador=AdaptadorHttp(servidor_stub.url))
    assert erro.value.status_http == 503 and erro.value.incerto
    assert len(servidor_stub.requisicoes_de("POST", "/post-api")) == 1
    assert CHAVE not in str(erro.value)

    peca = modelo.carregar(instalacao, peca_id)
    assert peca["status"] == "aprovada"
    pub = peca["publicacoes"][0]
    assert pub["estado"] == "falhou" and "503" in pub["erro"]
    falhas = [e for e in _eventos(instalacao) if e["evento"] == "publicacao_falhou"]
    assert len(falhas) == 1
    assert falhas[0]["resultado"] == "falha" and falhas[0]["provedor"] == "expxflow"
    assert falhas[0]["capacidade"] == "agendar" and falhas[0]["peca_id"] == peca_id


def test_erro_4xx_definitivo_permite_nova_tentativa_manual(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    servidor_stub.rota("POST", "/post-api", sequencia=[
        {"status": 400, "json": {"success": False, "error": "payload inválido"}},
        {"status": 201, "json": {"success": True, "data": {"scheduled_post_id": "s3"}}},
    ])
    peca_id = _peca_aprovada(instalacao)
    horario = _futuro()
    with pytest.raises(base.ErroEnvio) as erro:
        base.publicar(instalacao, peca_id, agendada_para=horario, adaptador=AdaptadorHttp(servidor_stub.url))
    assert not erro.value.incerto
    base.publicar(instalacao, peca_id, agendada_para=horario, adaptador=AdaptadorHttp(servidor_stub.url))
    assert modelo.carregar(instalacao, peca_id)["publicacoes"][0]["id_externo"] == "s3"


def test_timeout_depois_do_post_e_incerto_e_nao_retenta():
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    chamadas = []

    class Lento(BaseHTTPRequestHandler):
        def do_POST(self):
            chamadas.append(1)
            time.sleep(1.0)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Lento)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with pytest.raises(base.ErroEnvio) as erro:
            base.post_json(f"http://127.0.0.1:{srv.server_address[1]}/x", {}, timeout=0.3)
        assert erro.value.incerto and erro.value.codigo == "sem_resposta"
        time.sleep(0.2)
        assert len(chamadas) == 1
    finally:
        srv.shutdown()


def test_dry_run_nao_grava_nada_na_peca(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    peca_id = _peca_aprovada(instalacao)

    class Seco(AdaptadorHttp):
        def enviar(self, pedido):
            assert pedido.dry_run
            self.pedidos.append(pedido)
            return base.Resultado(canais={}, payload={"caption": "x"})

    antes = modelo.carregar(instalacao, peca_id)
    saida = base.publicar(instalacao, peca_id, agendada_para=_futuro(), adaptador=Seco(servidor_stub.url), dry_run=True)
    assert saida["dry_run"] is True and saida["payload"] == {"caption": "x"}
    depois = modelo.carregar(instalacao, peca_id)
    assert depois["publicacoes"] == [] and depois["atualizado_em"] == antes["atualizado_em"]
    assert servidor_stub.requisicoes == []


def test_achado_de_validacao_recusa_antes_de_gravar_intencao(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    peca_id = _peca_aprovada(instalacao)

    class Recusa(AdaptadorHttp):
        def validar(self, pedido):
            return [{"codigo": "proporcao", "mensagem": "9:16 não entra"}]

    adaptador = Recusa(servidor_stub.url)
    with pytest.raises(base.ErroValidacao) as erro:
        base.publicar(instalacao, peca_id, adaptador=adaptador)
    assert erro.value.achados[0]["codigo"] == "proporcao"
    assert adaptador.pedidos == []
    assert modelo.carregar(instalacao, peca_id)["publicacoes"] == []


def test_horario_sem_fuso_e_recusado(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    peca_id = _peca_aprovada(instalacao)
    with pytest.raises(base.ErroPublicacao):
        base.publicar(instalacao, peca_id, agendada_para="2030-01-01T10:00:00", adaptador=AdaptadorHttp(servidor_stub.url))


def test_peca_nao_aprovada_nao_publica(instalacao, servidor_stub):
    _env(instalacao, servidor_stub.url)
    peca = modelo.criar(instalacao, tipo="post_unico", titulo="Rascunho", formatos=["4:5"])
    adaptador = AdaptadorHttp(servidor_stub.url)
    with pytest.raises(base.ErroPublicacao) as erro:
        base.publicar(instalacao, peca["peca_id"], adaptador=adaptador)
    assert erro.value.codigo == "peca_nao_aprovada"
    assert adaptador.pedidos == []
