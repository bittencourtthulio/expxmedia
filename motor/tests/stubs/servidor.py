"""Stub HTTP local para testar provedores sem rede (D-14, D-15).

Sobe um http.server numa thread, em 127.0.0.1 e numa porta livre (porta 0), o que passa pelo
bloqueio de rede do conftest (loopback liberado). Permite registrar rotas por método + caminho,
com resposta fixa ou uma sequência de respostas (polling: cada chamada consome a próxima e a
última se repete), e grava cada requisição recebida (método, caminho, query, cabeçalhos, corpo
bruto e JSON quando houver).

Uso:
    with ServidorStub() as stub:
        stub.rota("POST", "/v1/itens", json={"id": 1}, status=201)
        requests.post(stub.url + "/v1/itens", json={"a": 1})
        stub.requisicoes[0].json  # {"a": 1}

Ou pela fixture `servidor_stub` (registre com `pytest_plugins = ["stubs.servidor"]`).
Rota não registrada responde 404 com JSON {"erro": "rota_nao_registrada", ...} e também é gravada.
"""
from __future__ import annotations

import json as _json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from requests.structures import CaseInsensitiveDict

HOST = "127.0.0.1"


@dataclass
class Resposta:
    status: int = 200
    corpo: bytes = b""
    cabecalhos: dict[str, str] = field(default_factory=dict)

    @classmethod
    def de(cls, status: int = 200, json: Any = None, corpo: bytes | str | None = None,
           cabecalhos: dict[str, str] | None = None) -> "Resposta":
        if json is not None and corpo is not None:
            raise ValueError("informe json ou corpo, não os dois")
        extras = dict(cabecalhos or {})
        if json is not None:
            dados = _json.dumps(json).encode("utf-8")
            extras.setdefault("Content-Type", "application/json")
        elif isinstance(corpo, str):
            dados = corpo.encode("utf-8")
            extras.setdefault("Content-Type", "text/plain; charset=utf-8")
        else:
            dados = corpo or b""
            if dados:
                extras.setdefault("Content-Type", "application/octet-stream")
        return cls(status=status, corpo=dados, cabecalhos=extras)


@dataclass
class Requisicao:
    metodo: str
    caminho: str
    query: dict[str, list[str]]
    cabecalhos: CaseInsensitiveDict
    corpo: bytes

    @property
    def json(self) -> Any:
        """Corpo decodificado como JSON, ou None quando vazio ou não é JSON."""
        if not self.corpo:
            return None
        try:
            return _json.loads(self.corpo.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None


class _Rota:
    def __init__(self, respostas: list[Resposta]):
        self._respostas = respostas
        self._indice = 0

    def proxima(self) -> Resposta:
        resposta = self._respostas[min(self._indice, len(self._respostas) - 1)]
        self._indice += 1
        return resposta


class ServidorStub:
    def __init__(self) -> None:
        self._rotas: dict[tuple[str, str], _Rota] = {}
        self._trava = threading.Lock()
        self.requisicoes: list[Requisicao] = []
        self._servidor: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.url = ""

    # ciclo de vida
    def iniciar(self) -> str:
        if self._servidor is not None:
            return self.url
        stub = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _tratar(self) -> None:
                stub._atender(self)

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _tratar

            def log_message(self, *args: Any) -> None:  # silencia o log no stderr
                pass

        self._servidor = ThreadingHTTPServer((HOST, 0), _Handler)
        self._servidor.daemon_threads = True
        porta = self._servidor.server_address[1]
        self.url = f"http://{HOST}:{porta}"
        self._thread = threading.Thread(target=self._servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self._thread.start()
        return self.url

    def parar(self) -> None:
        if self._servidor is None:
            return
        self._servidor.shutdown()
        self._servidor.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._servidor = None
        self._thread = None

    def __enter__(self) -> "ServidorStub":
        self.iniciar()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.parar()

    # registro
    def rota(self, metodo: str, caminho: str, *, status: int = 200, json: Any = None,
             corpo: bytes | str | None = None, cabecalhos: dict[str, str] | None = None,
             sequencia: list[Resposta | dict] | None = None) -> None:
        """Registra (ou substitui) a resposta de método + caminho (sem query).

        `sequencia`: lista de Resposta ou de dicts com as chaves de Resposta.de
        (status, json, corpo, cabecalhos); cada chamada consome a próxima e a última se repete.
        """
        if sequencia is not None:
            if not sequencia:
                raise ValueError("sequencia vazia")
            respostas = [r if isinstance(r, Resposta) else Resposta.de(**r) for r in sequencia]
        else:
            respostas = [Resposta.de(status=status, json=json, corpo=corpo, cabecalhos=cabecalhos)]
        with self._trava:
            self._rotas[(metodo.upper(), caminho)] = _Rota(respostas)

    def url_de(self, caminho: str) -> str:
        return self.url + caminho

    def requisicoes_de(self, metodo: str, caminho: str) -> list[Requisicao]:
        with self._trava:
            return [r for r in self.requisicoes if r.metodo == metodo.upper() and r.caminho == caminho]

    # atendimento (thread do servidor)
    def _atender(self, h: BaseHTTPRequestHandler) -> None:
        partes = urlsplit(h.path)
        tamanho = int(h.headers.get("Content-Length") or 0)
        corpo = h.rfile.read(tamanho) if tamanho > 0 else b""
        requisicao = Requisicao(
            metodo=h.command.upper(),
            caminho=partes.path,
            query=parse_qs(partes.query, keep_blank_values=True),
            cabecalhos=CaseInsensitiveDict(h.headers.items()),
            corpo=corpo,
        )
        with self._trava:
            self.requisicoes.append(requisicao)
            rota = self._rotas.get((requisicao.metodo, requisicao.caminho))
            resposta = rota.proxima() if rota is not None else Resposta.de(
                status=404,
                json={"erro": "rota_nao_registrada", "metodo": requisicao.metodo, "caminho": requisicao.caminho},
            )
        h.send_response(resposta.status)
        for nome, valor in resposta.cabecalhos.items():
            h.send_header(nome, valor)
        h.send_header("Content-Length", str(len(resposta.corpo)))
        h.end_headers()
        if requisicao.metodo != "HEAD" and resposta.corpo:
            h.wfile.write(resposta.corpo)


@pytest.fixture
def servidor_stub():
    """ServidorStub já iniciado; para ao fim do teste."""
    with ServidorStub() as stub:
        yield stub
