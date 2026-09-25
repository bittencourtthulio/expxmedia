"""T-07.02: avatar HeyGen API v3 sempre a partir do áudio (D-26) e provedor de teste (D-34).

Tudo contra o stub HTTP local (D-15): nenhuma chamada paga. Fluxo da v3 (base/api-heygen.md):
POST /v3/assets (multipart, campo file) -> POST /v3/videos com audio_asset_id -> GET
/v3/videos/{id} até completed/failed -> GET na video_url pré-assinada.
"""
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
from expxmedia.avatar import heygen, teste  # noqa: E402
from expxmedia.video import ffmpeg  # noqa: E402

pytestmark = pytest.mark.integracao_local

CHAVE = "chave-falsa-heygen-do-env"
PORTA_VOZ = "porta-voz-teste"
AVATAR_ID = "look-ficticio-0001"
VIDEO_ID = "vid-ficticio-123"
VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42-bytes-do-avatar-ficticio"


def _mp3(destino, segundos, taxa="8k"):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=220:sample_rate=22050:duration={segundos}",
                    "-c:a", "libmp3lame", "-b:a", taxa, str(destino)], check=True, capture_output=True)
    return destino


def _com_avatar_id(raiz, avatar_id=AVATAR_ID):
    caminho = raiz / "alma" / "alma.json"
    alma = json.loads(caminho.read_text(encoding="utf-8"))
    alma["porta_vozes"][0]["avatar"]["avatar_id"] = avatar_id
    caminho.write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def base_instalacao(instalacao, requer_binario, monkeypatch):
    requer_binario("ffmpeg")
    requer_binario("ffprobe")
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    monkeypatch.setenv("HEYGEN_API_KEY", "chave-do-processo-nao-pode-ir")
    (instalacao / "midia").mkdir()
    _mp3(instalacao / "midia" / "narracao.mp3", 3)
    return instalacao


@pytest.fixture
def com_chave(base_instalacao):
    (base_instalacao / ".env").write_text(f"HEYGEN_API_KEY={CHAVE}\n", encoding="utf-8")
    _com_avatar_id(base_instalacao)
    return base_instalacao


def _rotas(stub, status_polling):
    stub.rota("POST", "/v3/assets", json={"data": {"asset_id": "asset-001", "url": "x", "mime_type": "audio/mpeg"}})
    stub.rota("POST", "/v3/videos", json={"data": {"video_id": VIDEO_ID, "status": "waiting", "output_format": "mp4"}})
    stub.rota("GET", f"/v3/videos/{VIDEO_ID}", sequencia=[{"json": {"data": s}} for s in status_polling])
    stub.rota("GET", "/download/avatar.mp4", corpo=VIDEO_BYTES)


def _gerar(raiz, stub, **kw):
    esperas = []
    r = heygen.gerar(raiz, "midia/narracao.mp3", PORTA_VOZ, "midia/avatar.mp4",
                     url_base=stub.url, dormir=esperas.append, **kw)
    return r, esperas


# ---------------------------------------------------------------- integração

def test_fluxo_v3_upload_criacao_polling_download(com_chave, servidor_stub):
    stub = servidor_stub
    _rotas(stub, [
        {"id": VIDEO_ID, "status": "pending"},
        {"id": VIDEO_ID, "status": "processing"},
        {"id": VIDEO_ID, "status": "completed", "video_url": stub.url + "/download/avatar.mp4", "duration": 3.0},
    ])
    r, esperas = _gerar(com_chave, stub)

    # 1. upload do áudio como asset, multipart no campo file, com a chave do .env (nunca do processo)
    up = stub.requisicoes_de("POST", "/v3/assets")
    assert len(up) == 1
    assert up[0].cabecalhos["X-Api-Key"] == CHAVE
    assert b'name="file"' in up[0].corpo
    assert (com_chave / "midia" / "narracao.mp3").read_bytes() in up[0].corpo
    assert up[0].cabecalhos["Content-Type"].startswith("multipart/form-data")

    # 2. criação a partir do ÁUDIO (nunca de texto) com o avatar_id do porta-voz da Alma
    cria = stub.requisicoes_de("POST", "/v3/videos")
    assert len(cria) == 1
    corpo = cria[0].json
    assert corpo["type"] == "avatar"
    assert corpo["avatar_id"] == AVATAR_ID
    assert corpo["audio_asset_id"] == "asset-001"
    assert "script" not in corpo and "audio_url" not in corpo
    # origem: cursos-ia/aula-skills-2/plano-gravacao.md:65 (4:5, 1080p)
    assert corpo["aspect_ratio"] == "4:5" and corpo["resolution"] == "1080p"
    assert cria[0].cabecalhos["X-Api-Key"] == CHAVE
    assert cria[0].cabecalhos.get("Idempotency-Key")

    # 3. polling até completed, dormindo o intervalo entre as consultas
    assert len(stub.requisicoes_de("GET", f"/v3/videos/{VIDEO_ID}")) == 3
    assert esperas == [heygen.INTERVALO_POLLING_S] * 2

    # 4. download da URL pré-assinada, SEM a chave (ela não vai para terceiros)
    baixa = stub.requisicoes_de("GET", "/download/avatar.mp4")
    assert len(baixa) == 1 and "X-Api-Key" not in baixa[0].cabecalhos
    assert (com_chave / "midia" / "avatar.mp4").read_bytes() == VIDEO_BYTES
    assert r["provedor"] == "heygen"
    assert r["arquivo"] == "midia/avatar.mp4"
    assert r["video_id"] == VIDEO_ID
    # estado retomável apagado no fim
    assert not (com_chave / "midia" / "avatar.mp4.heygen.json").exists()


def test_asset_id_com_fallback_para_id(com_chave, servidor_stub):
    """A doc diverge (`asset_id` vs `id` no exemplo Python); o motor aceita os dois."""
    stub = servidor_stub
    _rotas(stub, [{"id": VIDEO_ID, "status": "completed", "video_url": stub.url + "/download/avatar.mp4"}])
    stub.rota("POST", "/v3/assets", json={"data": {"id": "asset-002"}})
    _gerar(com_chave, stub)
    assert stub.requisicoes_de("POST", "/v3/videos")[0].json["audio_asset_id"] == "asset-002"


def test_retoma_video_ja_criado_sem_nova_criacao(com_chave, servidor_stub):
    """Tempo esgotado guarda o video_id; a próxima chamada só consulta, não paga de novo."""
    stub = servidor_stub
    _rotas(stub, [{"id": VIDEO_ID, "status": "processing"}])
    with pytest.raises(heygen.ErroAvatar) as e:
        _gerar(com_chave, stub, timeout_s=0)
    assert e.value.codigo == "tempo_esgotado"
    assert VIDEO_ID in str(e.value)
    assert (com_chave / "midia" / "avatar.mp4.heygen.json").exists()

    _rotas(stub, [{"id": VIDEO_ID, "status": "completed", "video_url": stub.url + "/download/avatar.mp4"}])
    _gerar(com_chave, stub)
    assert len(stub.requisicoes_de("POST", "/v3/videos")) == 1
    assert len(stub.requisicoes_de("POST", "/v3/assets")) == 1
    assert (com_chave / "midia" / "avatar.mp4").read_bytes() == VIDEO_BYTES


def test_erro_http_traz_codigo_e_mensagem_sem_a_chave(com_chave, servidor_stub):
    stub = servidor_stub
    stub.rota("POST", "/v3/assets", json={"data": {"asset_id": "asset-001"}})
    stub.rota("POST", "/v3/videos", status=402, json={"error": {
        "code": "insufficient_credit", "message": f"saldo insuficiente {CHAVE}"}})
    with pytest.raises(heygen.ErroAvatar) as e:
        _gerar(com_chave, stub)
    assert e.value.codigo == "http_402"
    assert "insufficient_credit" in str(e.value) and "saldo insuficiente" in str(e.value)
    assert CHAVE not in str(e.value)
    assert len(stub.requisicoes_de("POST", "/v3/videos")) == 1  # nada é repetido
    assert not (com_chave / "midia" / "avatar.mp4").exists()


# ---------------------------------------------------------------- funcional

def test_status_failed_devolve_a_mensagem_do_provedor_sem_nova_criacao(com_chave, servidor_stub):
    stub = servidor_stub
    _rotas(stub, [
        {"id": VIDEO_ID, "status": "processing"},
        {"id": VIDEO_ID, "status": "failed", "failure_code": "avatar_not_usable",
         "failure_message": "O look pedido não pode ser usado com este plano."},
    ])
    with pytest.raises(heygen.ErroAvatar) as e:
        _gerar(com_chave, stub)
    assert e.value.codigo == "render_falhou"
    assert "O look pedido não pode ser usado com este plano." in str(e.value)
    assert "avatar_not_usable" in str(e.value)
    # uma criação só, e o polling parou no failed
    assert len(stub.requisicoes_de("POST", "/v3/videos")) == 1
    assert len(stub.requisicoes_de("POST", "/v3/assets")) == 1
    assert len(stub.requisicoes_de("GET", f"/v3/videos/{VIDEO_ID}")) == 2
    assert not stub.requisicoes_de("GET", "/download/avatar.mp4")
    assert not (com_chave / "midia" / "avatar.mp4").exists()
    # o failed é terminal: o estado de retomada não fica apontando para um vídeo que falhou
    assert not (com_chave / "midia" / "avatar.mp4.heygen.json").exists()


def test_audio_acima_de_10_minutos_e_recusado_antes_de_qualquer_chamada(com_chave, servidor_stub):
    _mp3(com_chave / "midia" / "narracao.mp3", 601)
    with pytest.raises(heygen.ErroAvatar) as e:
        _gerar(com_chave, servidor_stub)
    assert e.value.codigo == "audio_longo"
    assert heygen.LIMITE_AUDIO_S == 600
    assert servidor_stub.requisicoes == []


def test_sem_chave_recusa_sem_chamar(base_instalacao, servidor_stub):
    _com_avatar_id(base_instalacao)
    with pytest.raises(ErroCapacidade) as e:
        _gerar(base_instalacao, servidor_stub)
    assert "HEYGEN_API_KEY" in str(e.value)
    assert "chave-do-processo" not in str(e.value)
    assert servidor_stub.requisicoes == []


def test_sem_avatar_id_do_porta_voz_recusa_sem_chamar(base_instalacao, servidor_stub):
    (base_instalacao / ".env").write_text(f"HEYGEN_API_KEY={CHAVE}\n", encoding="utf-8")
    with pytest.raises(ErroCapacidade) as e:
        _gerar(base_instalacao, servidor_stub)
    assert "avatar.avatar_id" in str(e.value)
    assert servidor_stub.requisicoes == []


# ---------------------------------------------------------------- provedor de teste

def test_provedor_de_teste_gera_video_com_a_duracao_do_audio(base_instalacao):
    raiz = base_instalacao
    (raiz / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    _com_avatar_id(raiz)
    r = teste.gerar(raiz, "midia/narracao.mp3", PORTA_VOZ, "midia/avatar.mp4")
    assert r["provedor"] == "teste"
    assert r["arquivo"] == "midia/avatar.mp4"
    info = ffmpeg.sondar(raiz / "midia" / "avatar.mp4")
    audio = ffmpeg.sondar(raiz / "midia" / "narracao.mp3")["duracao"]
    # mesma forma do que o HeyGen devolve no processo atual: 1080x1350, H.264 + AAC, 25 fps
    assert (info["largura"], info["altura"]) == (1080, 1350)
    assert info["codecs"][:2] == ["h264", "aac"] or set(info["codecs"]) == {"h264", "aac"}
    assert info["fps_valor"] == 25
    assert abs(info["duracao"] - audio) < 0.05
    assert r["duracao_s"] == pytest.approx(info["duracao"], abs=0.01)


def test_provedor_de_teste_so_existe_com_a_flag(base_instalacao):
    _com_avatar_id(base_instalacao)
    with pytest.raises(ErroCapacidade):
        teste.gerar(base_instalacao, "midia/narracao.mp3", PORTA_VOZ, "midia/avatar.mp4")
    assert not (base_instalacao / "midia" / "avatar.mp4").exists()


def test_provedor_de_teste_exige_avatar_id_do_porta_voz(base_instalacao):
    (base_instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    with pytest.raises(ErroCapacidade) as e:
        teste.gerar(base_instalacao, "midia/narracao.mp3", PORTA_VOZ, "midia/avatar.mp4")
    assert "avatar.avatar_id" in str(e.value)


def test_provedor_de_teste_tambem_recusa_audio_longo(base_instalacao):
    (base_instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    _com_avatar_id(base_instalacao)
    _mp3(base_instalacao / "midia" / "narracao.mp3", 601)
    with pytest.raises(heygen.ErroAvatar) as e:
        teste.gerar(base_instalacao, "midia/narracao.mp3", PORTA_VOZ, "midia/avatar.mp4")
    assert e.value.codigo == "audio_longo"
