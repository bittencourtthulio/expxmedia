"""Harness da suíte do motor (D-14).

- Rede externa fechada no nível do socket (resolução de nome e connect), não só no urllib:
  qualquer biblioteca (requests, httpx, huggingface_hub) que escape de um falso bate aqui.
  Levanta ConnectionError, que as bibliotecas já tratam como falha de conexão.
  Padrão de origem: youtube-squad/tests/conftest.py:1-46 e Instragram-Videos/tests/conftest.py:17-26.
- Loopback (127.0.0.1, localhost, ::1) continua liberado para os stubs HTTP locais.
- HF_HUB_OFFLINE=1 na sessão inteira: modelos só do cache local.
- Fixture requer_binario: pula o teste com o nome do binário no motivo quando ele falta.
"""
import importlib.util
import os
import shutil
import socket
from pathlib import Path

import pytest


def _carregar_fixtures(nome):
    """Carrega tests/fixtures/<nome>.py pelo caminho (a suíte usa --import-mode=importlib, sem pacote tests)."""
    caminho = Path(__file__).resolve().parent / "fixtures" / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(f"_fixtures_{nome}", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# T-01.03: instalação temporária com a Alma fictícia
instalacao = _carregar_fixtures("instalacao").instalacao

LOCAIS = {"127.0.0.1", "localhost", "::1", "::ffff:127.0.0.1"}
# None e "" só aparecem ao abrir servidor (bind em qualquer interface), nunca para sair para fora.
SEM_HOST = {None, ""}


def pytest_configure(config):
    # antes de qualquer import do huggingface_hub, que lê a variável ao ser importado
    os.environ["HF_HUB_OFFLINE"] = "1"


def _host(endereco):
    if isinstance(endereco, tuple):
        return str(endereco[0])
    return str(endereco)


def _barrar(host):
    raise ConnectionError(f"teste tentou acessar a rede externa: {host}. Use um stub local ou um falso.")


@pytest.fixture(autouse=True, scope="session")
def sem_rede():
    resolver = socket.getaddrinfo
    conectar = socket.socket.connect
    conectar_ex = socket.socket.connect_ex

    def getaddrinfo(host, *args, **kwargs):
        nome = host.decode() if isinstance(host, bytes) else host
        if nome not in SEM_HOST and str(nome) not in LOCAIS:
            _barrar(nome)
        return resolver(host, *args, **kwargs)

    def checa(sock, endereco):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and _host(endereco) not in LOCAIS:
            _barrar(_host(endereco))

    def connect(sock, endereco):
        checa(sock, endereco)
        return conectar(sock, endereco)

    def connect_ex(sock, endereco):
        checa(sock, endereco)
        return conectar_ex(sock, endereco)

    mp = pytest.MonkeyPatch()
    mp.setattr(socket, "getaddrinfo", getaddrinfo)
    mp.setattr(socket.socket, "connect", connect)
    mp.setattr(socket.socket, "connect_ex", connect_ex)
    try:
        yield
    finally:
        mp.undo()


@pytest.fixture
def requer_binario():
    """Devolve requer(nome) -> caminho absoluto; pula o teste quando o binário não está no PATH."""

    def requer(nome):
        caminho = shutil.which(nome)
        if caminho is None:
            pytest.skip(f"binário ausente: {nome}")
        return caminho

    return requer
