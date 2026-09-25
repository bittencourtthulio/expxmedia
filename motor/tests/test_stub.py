"""T-01.04: stub HTTP local que registra rotas e grava as requisições (D-14, D-15)."""
import socket
import sys
from pathlib import Path

import pytest
import requests

# Com --import-mode=importlib a pasta tests/ não entra no sys.path; o pacote stubs mora nela.
_TESTS = str(Path(__file__).resolve().parent)
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs.servidor import Resposta, ServidorStub, servidor_stub  # noqa: E402,F401  (fixture)


def test_sobe_em_loopback_numa_porta_livre_e_responde_apesar_do_bloqueio(servidor_stub):
    # o bloqueio do conftest está ativo: a rede externa continua fechada
    with pytest.raises(ConnectionError):
        socket.create_connection(("example.com", 80), timeout=2)

    host, porta = servidor_stub.url.removeprefix("http://").split(":")
    assert host == "127.0.0.1"
    assert int(porta) > 0

    servidor_stub.rota("GET", "/saude", json={"ok": True})
    r = requests.get(servidor_stub.url_de("/saude"), timeout=5)
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert r.headers["Content-Type"] == "application/json"


def test_dois_stubs_usam_portas_diferentes():
    with ServidorStub() as a, ServidorStub() as b:
        assert a.url != b.url


def test_post_json_devolve_o_json_e_grava_corpo_e_cabecalhos(servidor_stub):
    servidor_stub.rota("POST", "/v1/videos", status=201, json={"id": "abc", "estado": "fila"},
                       cabecalhos={"X-Limite": "7"})
    r = requests.post(
        servidor_stub.url_de("/v1/videos") + "?orientation=portrait&per_page=5",
        json={"prompt": "um gato", "n": 2},
        headers={"Authorization": "Bearer chave-falsa"},
        timeout=5,
    )
    assert r.status_code == 201
    assert r.json() == {"id": "abc", "estado": "fila"}
    assert r.headers["X-Limite"] == "7"

    assert len(servidor_stub.requisicoes) == 1
    req = servidor_stub.requisicoes[0]
    assert req.metodo == "POST"
    assert req.caminho == "/v1/videos"
    assert req.query == {"orientation": ["portrait"], "per_page": ["5"]}
    assert req.cabecalhos["authorization"] == "Bearer chave-falsa"
    assert req.cabecalhos["Content-Type"] == "application/json"
    assert req.json == {"prompt": "um gato", "n": 2}
    assert b'"prompt"' in req.corpo
    assert servidor_stub.requisicoes_de("POST", "/v1/videos") == [req]
    assert servidor_stub.requisicoes_de("GET", "/v1/videos") == []


def test_metodo_diferente_nao_casa_e_rota_ausente_da_404_gravado(servidor_stub):
    servidor_stub.rota("POST", "/v1/videos", json={"id": 1})
    r = requests.get(servidor_stub.url_de("/v1/videos"), timeout=5)
    assert r.status_code == 404
    assert r.json()["erro"] == "rota_nao_registrada"
    assert [q.metodo for q in servidor_stub.requisicoes] == ["GET"]


def test_resposta_em_bytes_e_corpo_nao_json(servidor_stub):
    png = b"\x89PNG\r\n\x1a\n" + bytes(range(256))
    servidor_stub.rota("GET", "/img.png", corpo=png, cabecalhos={"Content-Type": "image/png"})
    servidor_stub.rota("PUT", "/upload", status=204)
    r = requests.get(servidor_stub.url_de("/img.png"), timeout=5)
    assert r.content == png
    assert r.headers["Content-Type"] == "image/png"

    r = requests.put(servidor_stub.url_de("/upload"), data=png, timeout=5)
    assert r.status_code == 204
    req = servidor_stub.requisicoes[-1]
    assert req.corpo == png
    assert req.json is None


def test_sequencia_para_polling_consume_em_ordem_e_repete_a_ultima(servidor_stub):
    servidor_stub.rota("GET", "/status/1", sequencia=[
        {"json": {"status_code": "IN_PROGRESS"}},
        Resposta.de(status=503, json={"erro": "ocupado"}),
        {"json": {"status_code": "FINISHED"}},
    ])
    obtidos = []
    for _ in range(5):
        r = requests.get(servidor_stub.url_de("/status/1"), timeout=5)
        obtidos.append((r.status_code, r.json()))
    assert obtidos == [
        (200, {"status_code": "IN_PROGRESS"}),
        (503, {"erro": "ocupado"}),
        (200, {"status_code": "FINISHED"}),
        (200, {"status_code": "FINISHED"}),
        (200, {"status_code": "FINISHED"}),
    ]
    assert len(servidor_stub.requisicoes_de("GET", "/status/1")) == 5


def test_parar_libera_a_porta():
    stub = ServidorStub()
    url = stub.iniciar()
    stub.parar()
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get(url + "/x", timeout=2)
