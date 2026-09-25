"""T-04.04: ElevenLabs with-timestamps com os parâmetros do porta-voz por tipo de peça (D-22, D-40).

Tudo contra o stub HTTP local (D-15): nenhuma chamada paga.
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.ambiente.verificar import ErroCapacidade  # noqa: E402
from expxmedia.narrar import base, elevenlabs  # noqa: E402

pytestmark = pytest.mark.integracao_local

CHAVE = "chave-falsa-elevenlabs-do-env"
PORTA_VOZ = "porta-voz-teste"
VOZ_ID = "voz-ficticia-0001"  # da Alma fictícia
CAMINHO = f"/v1/text-to-speech/{VOZ_ID}/with-timestamps"
TEXTO = "O pão sai quentinho às quatro da tarde, venha buscar o seu."


def _alinhamento(texto, pps=4.0):
    """Alinhamento plausível: cada caractere com 1/15 s, sem sobreposição."""
    passo = len(texto.split()) / pps / len(texto)
    return {"characters": list(texto),
            "character_start_times_seconds": [i * passo for i in range(len(texto))],
            "character_end_times_seconds": [(i + 1) * passo for i in range(len(texto))]}


@pytest.fixture(scope="module")
def mp3_bytes(tmp_path_factory):
    """mp3 44,1 kHz de verdade, de 3 s (12 palavras a 4 pal/s: acima de qualquer piso de ritmo)."""
    destino = tmp_path_factory.mktemp("mp3") / "voz.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=44100:duration=3",
                    "-c:a", "libmp3lame", "-b:a", "128k", str(destino)], check=True, capture_output=True)
    return destino.read_bytes()


@pytest.fixture
def com_chave(instalacao, monkeypatch, requer_binario):
    requer_binario("ffmpeg")
    requer_binario("ffprobe")
    (instalacao / ".env").write_text(f"ELEVENLABS_API_KEY={CHAVE}\n", encoding="utf-8")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "chave-do-processo-nao-pode-ir")
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    return instalacao


def _responder(stub, texto, mp3):
    stub.rota("POST", CAMINHO, json={
        "audio_base64": base64.b64encode(mp3).decode("ascii"),
        "alignment": _alinhamento(texto),
        "normalized_alignment": _alinhamento(texto),
    })


def _sem_parametros(raiz):
    caminho = raiz / "alma" / "alma.json"
    alma = json.loads(caminho.read_text(encoding="utf-8"))
    del alma["porta_vozes"][0]["voz"]["parametros"]
    caminho.write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ integração

def test_requisicao_with_timestamps_com_os_voice_settings_do_porta_voz(com_chave, servidor_stub, mp3_bytes):
    _responder(servidor_stub, TEXTO, mp3_bytes)

    r = base.narrar(com_chave, TEXTO, PORTA_VOZ, "reel", "pecas/p1/midia", url_base=servidor_stub.url)

    [req] = servidor_stub.requisicoes
    assert req.metodo == "POST"
    assert req.caminho == CAMINHO
    assert req.query["output_format"] == ["mp3_44100_128"]
    assert req.cabecalhos["xi-api-key"] == CHAVE              # do .env da instalação, não do processo
    corpo = req.json
    assert corpo["text"] == TEXTO
    assert corpo["model_id"] == "eleven_multilingual_v2"
    # o bloco reel da Alma fictícia, sem o ritmo mínimo (não é parâmetro da API)
    assert corpo["voice_settings"] == {"stability": 0.4, "similarity_boost": 0.75, "style": 0.3,
                                       "use_speaker_boost": True, "speed": 1.15}

    assert r["provedor"] == "elevenlabs"
    assert (com_chave / r["audio"]).read_bytes() == mp3_bytes  # gravado como veio
    assert "".join(r["alinhamento"]["characters"]) == TEXTO


def test_aula_usa_o_bloco_aula_e_o_timeout_dele(com_chave, servidor_stub, mp3_bytes, monkeypatch):
    _responder(servidor_stub, TEXTO, mp3_bytes)
    vistos = []
    post = elevenlabs.requests.post

    def espiao(*a, **kw):
        vistos.append(kw.get("timeout"))
        return post(*a, **kw)

    monkeypatch.setattr(elevenlabs.requests, "post", espiao)
    base.narrar(com_chave, TEXTO, PORTA_VOZ, "aula", "pecas/aula/midia", url_base=servidor_stub.url)

    assert servidor_stub.requisicoes[0].json["voice_settings"] == {
        "stability": 0.55, "similarity_boost": 0.9, "style": 0.1, "use_speaker_boost": True, "speed": 0.95}
    assert vistos == [240]


# ------------------------------------------------------------------ funcional

def test_sem_parametros_no_porta_voz_valem_os_padroes_da_origem(com_chave, servidor_stub, mp3_bytes, monkeypatch):
    _sem_parametros(com_chave)
    _responder(servidor_stub, TEXTO, mp3_bytes)
    vistos = []
    post = elevenlabs.requests.post

    def espiao(*a, **kw):
        vistos.append(kw.get("timeout"))
        return post(*a, **kw)

    monkeypatch.setattr(elevenlabs.requests, "post", espiao)

    base.narrar(com_chave, TEXTO, PORTA_VOZ, "reel", "pecas/r/midia", url_base=servidor_stub.url)
    base.narrar(com_chave, TEXTO, PORTA_VOZ, "aula", "pecas/a/midia", url_base=servidor_stub.url)
    base.narrar(com_chave, TEXTO, PORTA_VOZ, "carrossel", "pecas/c/midia", url_base=servidor_stub.url)

    reel, aula, outro = (q.json["voice_settings"] for q in servidor_stub.requisicoes)
    assert reel == {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": True, "speed": 1.2}
    assert aula == {"stability": 0.5, "similarity_boost": 0.85, "style": 0.15, "use_speaker_boost": True, "speed": 0.94}
    assert outro == reel
    assert vistos[1] == 300


def test_erro_http_vira_erro_tipado_sem_nova_tentativa_e_sem_a_chave(com_chave, servidor_stub):
    servidor_stub.rota("POST", CAMINHO, status=402, json={"detail": {"status": "payment_required"}})
    with pytest.raises(elevenlabs.ErroElevenLabs) as erro:
        base.narrar(com_chave, TEXTO, PORTA_VOZ, "reel", "pecas/p1/midia", url_base=servidor_stub.url)
    assert erro.value.codigo == "http_402"
    assert "payment_required" in str(erro.value)
    assert CHAVE not in str(erro.value)
    assert len(servidor_stub.requisicoes) == 1
    assert not (com_chave / "pecas/p1/midia/narracao.mp3").exists()


def test_sem_chave_nao_chama_e_diz_como_habilitar(instalacao, servidor_stub, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "so-no-processo")
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    with pytest.raises(ErroCapacidade) as erro:
        base.narrar(instalacao, TEXTO, PORTA_VOZ, "reel", "pecas/p1/midia", url_base=servidor_stub.url)
    assert "ELEVENLABS_API_KEY" in str(erro.value)
    with pytest.raises(ErroCapacidade):
        elevenlabs.sintetizar(instalacao, TEXTO, {"voz_id": VOZ_ID}, {}, instalacao / "x.mp3",
                              tipo_peca="reel", url_base=servidor_stub.url)
    assert servidor_stub.requisicoes == []


def test_voice_settings_puros():
    assert elevenlabs.voice_settings({}, "reel") == {
        "stability": 0.45, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": True, "speed": 1.2}
    # parâmetro parcial: o que falta vem do padrão do tipo; chaves que não são da API ficam fora
    assert elevenlabs.voice_settings({"speed": 1.0, "ritmo_min_pps": 3.0, "timeout_s": 10}, "aula") == {
        "stability": 0.5, "similarity_boost": 0.85, "style": 0.15, "use_speaker_boost": True, "speed": 1.0}
