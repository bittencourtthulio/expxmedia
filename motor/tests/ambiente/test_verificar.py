"""T-02.07: verificação local de capacidades, como_habilitar e provedor padrão sem troca silenciosa (D-07)."""
import json
import os
import stat
import sys

import pytest

from expxmedia.ambiente import catalogo, verificar
from expxmedia.nucleo import arquivos

SEGREDO = "valor-secreto-nao-pode-vazar"
EXPXFLOW = (
    f"EXPXFLOW_API_KEY={SEGREDO}\nEXPXFLOW_CLIENT_ID={SEGREDO}-id\n"
    "EXPXFLOW_BASE_URL=http://127.0.0.1:9/api\n"
)
META = f"META_GRAPH_TOKEN={SEGREDO}-meta\nMETA_IG_USER_ID=123\n"
CHAVES_CONSULTA = {"capacidade", "habilitada", "provedor", "provedores", "como_habilitar"}


@pytest.fixture
def bin_falso(tmp_path, monkeypatch):
    """PATH só com executáveis falsos criados pelo teste; nenhum binário real é visto."""
    pasta = tmp_path / "bin"
    pasta.mkdir()
    monkeypatch.setenv("PATH", str(pasta))
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "navegadores"))
    monkeypatch.delenv(catalogo.FLAG_TESTE, raising=False)

    def criar(nome, script="exit 0"):
        arquivo = pasta / nome
        arquivo.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
        arquivo.chmod(arquivo.stat().st_mode | stat.S_IXUSR)
        return arquivo

    return criar


def _env(raiz, texto):
    (raiz / ".env").write_text(texto, encoding="utf-8")


def _sem_modulo(nome):
    return False


def _ver(raiz, **kw):
    kw.setdefault("modulo_python", _sem_modulo)
    return verificar.Verificador(raiz, **kw)


def _por_id(consulta):
    return {p["id"]: p for p in consulta["provedores"]}


# ---------- integração: PROVEDOR_PUBLICAR aponta para provedor não satisfeito ----------

def test_provedor_escolhido_sem_chave_e_erro_e_nao_troca_para_expxflow(instalacao, bin_falso):
    _env(instalacao, EXPXFLOW + "PROVEDOR_PUBLICAR=meta_graph\n")
    v = _ver(instalacao)
    consulta = v.verificar("publicar")
    assert consulta["habilitada"] is False
    assert consulta["provedor"] is None  # não escolhe expxflow em silêncio
    prov = _por_id(consulta)
    assert prov["expxflow"]["satisfeito"] is True
    assert prov["meta_graph"] == {
        "id": "meta_graph", "satisfeito": False, "falta": ["META_GRAPH_TOKEN", "META_IG_USER_ID"]
    }
    orientacao = consulta["como_habilitar"]
    assert "PROVEDOR_PUBLICAR" in orientacao and "meta_graph" in orientacao
    assert "META_GRAPH_TOKEN" in orientacao
    assert SEGREDO not in json.dumps(consulta)
    with pytest.raises(verificar.ErroProvedor) as info:
        v.escolher_provedor("publicar")
    assert "PROVEDOR_PUBLICAR" in str(info.value) and SEGREDO not in str(info.value)
    # com a chave da Meta presente, a escolha explícita vale mesmo com os dois satisfeitos
    _env(instalacao, EXPXFLOW + META + "PROVEDOR_PUBLICAR=meta_graph\n")
    v = _ver(instalacao)
    assert v.verificar("publicar")["provedor"] == "meta_graph"
    assert v.escolher_provedor("publicar") == "meta_graph"
    assert v.aviso("publicar") is None


def test_provedor_padrao_desconhecido_e_erro(instalacao, bin_falso):
    _env(instalacao, EXPXFLOW + "PROVEDOR_PUBLICAR=correio\n")
    consulta = _ver(instalacao).verificar("publicar")
    assert consulta["habilitada"] is False and consulta["provedor"] is None
    assert "correio" in consulta["como_habilitar"] and "expxflow" in consulta["como_habilitar"]


def test_regras_1_e_2_um_satisfeito_ou_ordem_da_tabela(instalacao, bin_falso):
    _env(instalacao, META)
    v = _ver(instalacao)
    assert v.verificar("publicar")["provedor"] == "meta_graph"  # regra 1
    assert v.aviso("publicar") is None
    _env(instalacao, EXPXFLOW + META)
    v = _ver(instalacao)
    consulta = v.verificar("publicar")
    assert consulta["habilitada"] and consulta["provedor"] == "expxflow"  # regra 2
    assert consulta["como_habilitar"] is None
    assert "PROVEDOR_PUBLICAR" in v.aviso("publicar")
    # PROVEDOR_* vazio é o mesmo que ausente
    _env(instalacao, EXPXFLOW + META + "PROVEDOR_PUBLICAR=\n")
    assert _ver(instalacao).verificar("publicar")["provedor"] == "expxflow"


def test_expxflow_exige_base_url(instalacao, bin_falso):
    _env(instalacao, f"EXPXFLOW_API_KEY={SEGREDO}\nEXPXFLOW_CLIENT_ID=x\n")
    consulta = _ver(instalacao).verificar("automacao_dm")
    assert consulta["habilitada"] is False
    assert _por_id(consulta)["expxflow"]["falta"] == ["EXPXFLOW_BASE_URL"]


# ---------- funcional: narrar sem chave ----------

def test_narrar_sem_chave(instalacao, bin_falso):
    consulta = verificar.verificar("narrar", instalacao)
    assert set(consulta) == CHAVES_CONSULTA
    assert consulta["habilitada"] is False
    assert consulta["provedor"] is None
    assert consulta["provedores"] == [
        {"id": "elevenlabs", "satisfeito": False, "falta": ["ELEVENLABS_API_KEY"]}
    ]
    assert consulta["como_habilitar"].startswith("Coloque ELEVENLABS_API_KEY no .env.")
    assert "Onde conseguir" in consulta["como_habilitar"]
    json.dumps(consulta)


def test_narrar_com_chave(instalacao, bin_falso):
    _env(instalacao, f"ELEVENLABS_API_KEY={SEGREDO}\n")
    consulta = verificar.verificar("narrar", instalacao, porta_voz="porta-voz-teste")
    assert consulta == {
        "capacidade": "narrar",
        "habilitada": True,
        "provedor": "elevenlabs",
        "provedores": [{"id": "elevenlabs", "satisfeito": True, "falta": []}],
        "como_habilitar": None,
    }


def test_raiz_padrao_e_a_da_pasta_atual(instalacao, bin_falso, monkeypatch):
    _env(instalacao, "ELEVENLABS_API_KEY=x\n")
    monkeypatch.chdir(instalacao / "pecas")
    assert verificar.verificar("narrar")["habilitada"] is True


# ---------- porta-voz ----------

def test_porta_voz_precisa_do_id_na_alma(instalacao, bin_falso):
    _env(instalacao, "ELEVENLABS_API_KEY=x\nHEYGEN_API_KEY=y\n")
    v = _ver(instalacao)
    avatar = v.verificar("avatar", porta_voz="porta-voz-teste")  # avatar_id é null na Alma fictícia
    assert avatar["habilitada"] is False
    assert _por_id(avatar)["heygen"]["falta"] == ["alma: porta-voz porta-voz-teste sem avatar.avatar_id"]
    assert "avatar.avatar_id" in avatar["como_habilitar"] and "alma/alma.json" in avatar["como_habilitar"]
    fantasma = v.verificar("narrar", porta_voz="nao-existe")
    assert fantasma["habilitada"] is False
    assert "nao-existe" in _por_id(fantasma)["elevenlabs"]["falta"][0]
    # sem porta-voz na consulta, vale só o provedor
    assert v.verificar("avatar")["habilitada"] is True
    # preencher o id na Alma habilita
    alma = arquivos.ler_json(instalacao / "alma" / "alma.json")
    alma["porta_vozes"][0]["avatar"]["avatar_id"] = "avatar-ficticio"
    arquivos.gravar_json(instalacao / "alma" / "alma.json", alma)
    assert _ver(instalacao).verificar("avatar", porta_voz="porta-voz-teste")["provedor"] == "heygen"


def test_rosto_ia_por_porta_voz_e_login(instalacao, bin_falso):
    bin_falso("higgsfield", 'if [ "$1 $2" = "account status" ]; then exit 0; fi; exit 9')
    v = _ver(instalacao)
    assert v.verificar("video_ia")["provedor"] == "higgsfield"
    rosto = v.verificar("rosto_ia", porta_voz="porta-voz-teste")  # rosto_ia.id é null
    assert _por_id(rosto)["higgsfield"]["falta"] == ["alma: porta-voz porta-voz-teste sem rosto_ia.id"]


# ---------- provedor de teste (D-34, D-39) ----------

def test_provedor_de_teste_so_com_a_flag(instalacao, bin_falso, monkeypatch):
    sem = _ver(instalacao).verificar("narrar")
    assert [p["id"] for p in sem["provedores"]] == ["elevenlabs"]
    monkeypatch.setenv(catalogo.FLAG_TESTE, "1")
    com = _ver(instalacao).verificar("narrar", porta_voz="porta-voz-teste")
    assert com["habilitada"] and com["provedor"] == "teste"
    # com a chave real, o real vem primeiro
    _env(instalacao, "ELEVENLABS_API_KEY=x\n")
    assert _ver(instalacao).verificar("narrar")["provedor"] == "elevenlabs"
    # a flag também vale pelo .env
    monkeypatch.delenv(catalogo.FLAG_TESTE)
    _env(instalacao, f"{catalogo.FLAG_TESTE}=1\n")
    assert _ver(instalacao).verificar("avatar")["provedor"] == "teste"
    _env(instalacao, f"{catalogo.FLAG_TESTE}=0\n")
    assert _ver(instalacao).verificar("avatar")["habilitada"] is False


# ---------- binários e CLI simulados no PATH ----------

def test_binarios_ffmpeg_e_node_com_versao(instalacao, bin_falso):
    v = _ver(instalacao)
    assert _por_id(v.verificar("editar_video"))["ffmpeg"]["falta"] == ["binário ffmpeg"]
    bin_falso("ffmpeg")
    bin_falso("node", "echo v18.19.0")
    v = _ver(instalacao)
    assert v.verificar("editar_video")["habilitada"] is True
    motion = v.verificar("renderizar_motion")
    assert _por_id(motion)["remotion"]["falta"] == ["binário node>=20"]
    bin_falso("node", "echo v20.11.1")
    assert _ver(instalacao).verificar("renderizar_motion")["provedor"] == "remotion"


def test_chromium_do_playwright(instalacao, bin_falso, tmp_path):
    v = _ver(instalacao)
    assert _por_id(v.verificar("renderizar_html"))["playwright"]["falta"] == ["Chromium do Playwright"]
    (tmp_path / "navegadores" / "chromium_headless_shell-1187").mkdir(parents=True)
    v = _ver(instalacao)
    assert v.verificar("renderizar_html")["habilitada"] is True
    assert v.verificar("capturar_pagina")["habilitada"] is True


def test_transcrever_whisper_ou_faster_whisper_e_legendar_derivada(instalacao, bin_falso):
    v = _ver(instalacao)
    transcrever = v.verificar("transcrever")
    assert _por_id(transcrever)["whisper_local"]["falta"] == ["binário whisper ou faster-whisper"]
    legendar = v.verificar("legendar")
    assert legendar["habilitada"] is False
    assert _por_id(legendar)["local"]["falta"] == ["narrar ou transcrever habilitada"]
    assert "ELEVENLABS_API_KEY" in legendar["como_habilitar"]
    # faster-whisper instalado como pacote Python
    v = _ver(instalacao, modulo_python=lambda nome: nome == "faster_whisper")
    assert v.verificar("transcrever")["habilitada"] and v.verificar("legendar")["provedor"] == "local"
    # executável whisper
    bin_falso("whisper")
    assert _ver(instalacao).verificar("legendar")["habilitada"] is True


def test_legendar_por_narrar(instalacao, bin_falso):
    _env(instalacao, "ELEVENLABS_API_KEY=x\n")
    assert _ver(instalacao).verificar("legendar")["habilitada"] is True


def test_login_do_cli_por_comando_de_status(instalacao, bin_falso):
    v = _ver(instalacao)
    assert _por_id(v.verificar("video_ia"))["higgsfield"]["falta"] == ["binário higgsfield"]
    bin_falso("higgsfield", "echo 'Not authenticated.' >&2; exit 1")
    assert _por_id(_ver(instalacao).verificar("video_ia"))["higgsfield"]["falta"] == [
        "login do higgsfield (higgsfield account status)"
    ]
    registro = instalacao / "chamadas.txt"
    bin_falso("higgsfield", f'echo "$@" >> "{registro}"; exit 0')
    v = _ver(instalacao)
    assert v.verificar("video_ia")["habilitada"]
    v.verificar("rosto_ia")
    assert registro.read_text().splitlines() == ["account status"]  # uma vez só por verificador


def test_cli_que_trava_nao_trava_a_consulta(instalacao, bin_falso):
    bin_falso("higgsfield", "sleep 5")
    v = _ver(instalacao, timeout=0.5)
    assert v.verificar("video_ia")["habilitada"] is False


def test_galeria_compartilhada_exige_gh_e_aceite(instalacao, bin_falso):
    bin_falso("gh", 'if [ "$1 $2" = "auth status" ]; then exit 0; fi; exit 1')
    v = _ver(instalacao)
    assert _por_id(v.verificar("galeria_compartilhada"))["github"]["falta"] == [
        "aceite da galeria compartilhada"
    ]
    arquivos.gravar_json(instalacao / ".expxmedia" / "galeria.json", {"expxmedia_galeria": 1, "aceite": True})
    assert _ver(instalacao).verificar("galeria_compartilhada")["provedor"] == "github"


def test_agendar_por_meta_graph_exige_agendador_local(instalacao, bin_falso):
    _env(instalacao, META)
    consulta = _ver(instalacao).verificar("agendar")
    assert consulta["habilitada"] is False
    assert _por_id(consulta)["meta_graph"]["falta"] == ["agendador local instalado"]
    assert _ver(instalacao).verificar("publicar")["provedor"] == "meta_graph"
    arquivos.gravar_json(instalacao / ".expxmedia" / "agendador.json", {"instalado": True})
    assert _ver(instalacao).verificar("agendar")["provedor"] == "meta_graph"


def test_youtube_exige_oauth(instalacao, bin_falso):
    _env(instalacao, "YOUTUBE_CLIENT_SECRET_FILE=segredos/client_secret.json\n")
    consulta = _ver(instalacao).verificar("publicar")
    assert _por_id(consulta)["youtube_api"]["falta"] == ["OAuth do YouTube com escopo de upload"]


# ---------- consulta geral, packs e sigilo ----------

def test_verificar_tudo_e_pack(instalacao, bin_falso):
    cat = catalogo.Catalogo()
    cat.registrar_pack("expx-instagram", [{
        "id": "metricas_instagram",
        "descricao": "métricas",
        "provedores": [{"id": "meta_graph", "env": ["META_GRAPH_TOKEN", "META_IG_USER_ID"], "cli": None, "binarios": []}],
        "como_habilitar": "Coloque META_GRAPH_TOKEN e META_IG_USER_ID no .env.",
    }])
    _env(instalacao, META)
    todas = _ver(instalacao, catalogo=cat).verificar_tudo()
    assert [c["capacidade"] for c in todas] == [c.id for c in cat.capacidades()]
    assert all(set(c) == CHAVES_CONSULTA for c in todas)
    metricas = todas[-1]
    assert metricas["capacidade"] == "metricas_instagram" and metricas["provedor"] == "meta_graph"
    assert SEGREDO not in json.dumps(todas)


def test_capacidade_desconhecida(instalacao, bin_falso):
    with pytest.raises(catalogo.ErroCatalogo):
        _ver(instalacao).verificar("metricas_instagram")


def test_escolher_provedor_desabilitada_orienta(instalacao, bin_falso):
    with pytest.raises(verificar.ErroCapacidade) as info:
        _ver(instalacao).escolher_provedor("banco_imagens")
    assert "PEXELS_API_KEY" in str(info.value)
