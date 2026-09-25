"""T-08.03: túnel cloudflared que expõe a mídia por URL temporária (base/tunel-url-publica.md)."""
import inspect
import os
import sys
import time
from pathlib import Path

import pytest
import requests

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs import cloudflared_falso  # noqa: E402
from stubs.cloudflared_falso import cloudflared_no_path  # noqa: E402,F401  (fixture)

from expxmedia.publicar import tunel  # noqa: E402


def _midia(tmp_path, nome="video.mp4", dados=b"conteudo-da-midia"):
    arquivo = tmp_path / nome
    arquivo.write_bytes(dados)
    return arquivo


# --- integração -------------------------------------------------------------------------

def test_abrir_devolve_a_url_impressa_e_fechar_encerra_o_processo(tmp_path, cloudflared_no_path):
    video = _midia(tmp_path)
    t = tunel.abrir([video], confirmar=False)
    try:
        assert t.base == "https://tunel-falso-de-teste.trycloudflare.com"
        url = t.url_de(video)
        assert url.startswith(t.base + "/") and url.endswith(".mp4")
        assert video.stem not in url  # nome aleatório, não o nome do arquivo
        # o servidor local serve só a cópia, sob o nome aleatório
        local = t.url_local + "/" + url.rsplit("/", 1)[1]
        assert requests.get(local, timeout=5).content == b"conteudo-da-midia"
        eventos = cloudflared_falso.eventos(cloudflared_no_path)
        inicio = eventos[0]
        assert inicio["argv"][:3] == ["tunnel", "--no-autoupdate", "--url"]
        assert inicio["argv"][3] == t.url_local
        pid = inicio["pid"]
        assert t.processo.poll() is None
    finally:
        t.fechar()
    assert t.processo.poll() is not None
    assert any(e["evento"] == "encerrado" and e["pid"] == pid for e in cloudflared_falso.eventos(cloudflared_no_path))
    with pytest.raises(requests.ConnectionError):
        requests.get(local, timeout=2)
    assert not t.pasta.exists()


def test_varios_arquivos_num_tunel_so_e_gerenciador_de_contexto(tmp_path, cloudflared_no_path):
    a = _midia(tmp_path, "slide_01.jpg", b"a")
    b = _midia(tmp_path, "slide_02.mp4", b"b")
    with tunel.abrir([a, b], confirmar=False) as t:
        urls = [t.url_de(a), t.url_de(b)]
        assert len(set(urls)) == 2 and urls[0].endswith(".jpg") and urls[1].endswith(".mp4")
        processo = t.processo
    assert processo.poll() is not None
    assert len([e for e in cloudflared_falso.eventos(cloudflared_no_path) if e["evento"] == "inicio"]) == 1


def test_url_publica_temporaria_de_um_arquivo(tmp_path, cloudflared_no_path):
    video = _midia(tmp_path)
    with tunel.url_publica_temporaria(video, confirmar=False) as url:
        assert url.startswith("https://tunel-falso-de-teste.trycloudflare.com/")


# --- funcional --------------------------------------------------------------------------

def test_sem_url_no_tempo_limite_levanta_erro_e_encerra_o_processo(tmp_path, cloudflared_no_path, monkeypatch):
    monkeypatch.setenv("CLOUDFLARED_FALSO_MODO", "mudo")
    video = _midia(tmp_path)
    inicio = time.monotonic()
    with pytest.raises(tunel.ErroTunel) as erro:
        tunel.abrir([video], confirmar=False, tempo_limite=1.0)
    assert time.monotonic() - inicio < 10
    assert "não subiu" in str(erro.value)
    eventos = cloudflared_falso.eventos(cloudflared_no_path)
    pid = eventos[0]["pid"]
    assert any(e["evento"] == "encerrado" and e["pid"] == pid for e in eventos)


def test_o_tempo_limite_padrao_e_30_segundos():
    assert tunel.TEMPO_LIMITE == 30
    assert inspect.signature(tunel.abrir).parameters["tempo_limite"].default == tunel.TEMPO_LIMITE


def test_processo_que_morre_sem_url_levanta_erro_sem_esperar_o_limite(tmp_path, cloudflared_no_path, monkeypatch):
    monkeypatch.setenv("CLOUDFLARED_FALSO_MODO", "morre")
    inicio = time.monotonic()
    with pytest.raises(tunel.ErroTunel):
        tunel.abrir([_midia(tmp_path)], confirmar=False)
    assert time.monotonic() - inicio < 10


def test_sem_cloudflared_no_path_orienta_a_instalar(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "vazio"))
    with pytest.raises(tunel.ErroTunel) as erro:
        tunel.abrir([_midia(tmp_path)], confirmar=False)
    assert erro.value.codigo == "sem_cloudflared" and "cloudflared" in str(erro.value)


def test_confirmacao_externa_que_falha_vira_aviso(tmp_path, cloudflared_no_path):
    """A URL do falso não é alcançável (rede bloqueada): a confirmação avisa e segue (tunel.py:95-97)."""
    avisos = []
    with tunel.abrir([_midia(tmp_path)], confirmar=True, tentativas_confirmacao=2, pausa_confirmacao=0,
                     avisar=avisos.append) as t:
        assert t.base
    assert avisos and "não confirmei" in avisos[0]
