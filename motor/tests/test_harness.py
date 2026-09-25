"""T-01.02: a suíte roda com a rede externa fechada e pula teste local quando o binário falta (D-14)."""
import os
import socket
import threading

import pytest


def test_host_externo_por_nome_recebe_connection_error():
    with pytest.raises(ConnectionError, match="example.com"):
        socket.create_connection(("example.com", 80), timeout=2)


def test_ip_externo_direto_recebe_connection_error():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(ConnectionError, match="93.184.216.34"):
            s.connect(("93.184.216.34", 80))
        with pytest.raises(ConnectionError):
            s.connect_ex(("93.184.216.34", 80))
    finally:
        s.close()


def test_requests_trata_o_bloqueio_como_erro_de_conexao():
    requests = pytest.importorskip("requests")
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get("http://example.com/", timeout=2)


def test_urllib_tambem_e_barrado():
    import urllib.error
    import urllib.request
    with pytest.raises((ConnectionError, urllib.error.URLError)):
        urllib.request.urlopen("http://example.com/", timeout=2)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_loopback_continua_permitido(host):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(1)
    porta = servidor.getsockname()[1]
    recebido = []

    def atender():
        conn, _ = servidor.accept()
        with conn:
            recebido.append(conn.recv(16))

    t = threading.Thread(target=atender, daemon=True)
    t.start()
    try:
        with socket.create_connection((host, porta), timeout=2) as c:
            c.sendall(b"ola")
        t.join(timeout=2)
    finally:
        servidor.close()
    assert recebido == [b"ola"]


def test_loopback_ipv6_permitido():
    if not socket.has_ipv6:
        pytest.skip("sem IPv6 nesta máquina")
    servidor = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        servidor.bind(("::1", 0))
    except OSError:
        servidor.close()
        pytest.skip("::1 indisponível nesta máquina")
    servidor.listen(1)
    porta = servidor.getsockname()[1]
    try:
        with socket.create_connection(("::1", porta), timeout=2):
            pass
    finally:
        servidor.close()


def test_hf_hub_offline_na_sessao():
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    constantes = pytest.importorskip("huggingface_hub.constants")
    assert constantes.HF_HUB_OFFLINE is True


def test_requer_binario_ausente_pula_com_o_nome_no_motivo(requer_binario):
    nome = "binario-que-nao-existe-expxmedia-7f3a"
    with pytest.raises(pytest.skip.Exception) as info:
        requer_binario(nome)
    assert nome in str(info.value)


def test_requer_binario_presente_devolve_o_caminho(requer_binario):
    caminho = requer_binario("sh")
    assert os.path.isabs(caminho) and os.access(caminho, os.X_OK)


def test_marcador_integracao_local_registrado(pytestconfig):
    assert any(linha.startswith("integracao_local") for linha in pytestconfig.getini("markers"))
