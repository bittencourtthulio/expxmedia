"""T-06.06: b-roll pelo módulo Pexels (porta de `Instragram-Videos/pipeline/broll.py`), contra o stub local.

- integração: pedir b-roll para um termo baixa o vídeo vertical escolhido para a pasta da peça e o
  normaliza (1080x1920, 30 fps, sem áudio, o miolo do clipe na duração pedida), com a procedência gravada;
- funcional: resultados abaixo da duração mínima (duração pedida + 1 s) são descartados, resultado cuja
  página descreve outra coisa é descartado por relevância, e sem resultado válido o módulo devolve vazio
  sem erro; as regras de colocação da origem (2-4 s, 3 s livres no começo, 2 s no fim, 4 s de respiro,
  40% do corte) recusam o plano antes de qualquer busca.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.corte import broll  # noqa: E402
from expxmedia.video import ffmpeg  # noqa: E402

CHAVE = "chave-falsa-do-env-da-instalacao"


def _video(id_, dur, pagina, arquivos):
    return {"id": id_, "width": 1080, "height": 1920, "duration": dur, "url": pagina,
            "user": {"name": f"Autora {id_}", "url": f"https://www.pexels.com/@autora{id_}"},
            "video_files": arquivos}


def _arq(link, w, h):
    return {"id": hash(link) % 1000, "quality": "hd", "file_type": "video/mp4", "width": w, "height": h, "link": link}


@pytest.fixture
def com_chave(instalacao):
    (instalacao / ".env").write_text(f"PEXELS_API_KEY={CHAVE}\n", encoding="utf-8")
    return instalacao


@pytest.fixture
def clipe_mp4(tmp_path):
    """Um clipe real de 8 s, 720x1280, com áudio (o b-roll sai sem)."""
    destino = tmp_path / "clipe.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=720x1280:r=25:d=8",
                    "-f", "lavfi", "-i", "sine=f=440:d=8", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", str(destino)], check=True, capture_output=True)
    return destino.read_bytes()


# ------------------------------------------------------------------ integração


@pytest.mark.integracao_local
def test_baixa_o_video_vertical_escolhido_para_a_pasta_da_peca(com_chave, servidor_stub, clipe_mp4, requer_binario):
    requer_binario("ffmpeg")
    s = servidor_stub
    s.rota("GET", "/vertical.mp4", corpo=clipe_mp4)
    s.rota("GET", "/horizontal.mp4", corpo=b"nao-deve-baixar")
    s.rota("GET", "/v1/videos/search", json={"videos": [
        # só horizontal: perde para o vertical
        _video(10, 20, "https://www.pexels.com/video/bread-dough-kneading-10/",
               [_arq(s.url_de("/horizontal.mp4"), 1920, 1080)]),
        _video(11, 12, "https://www.pexels.com/video/baker-kneading-bread-dough-11/",
               [_arq(s.url_de("/vertical.mp4"), 1080, 1920), _arq(s.url_de("/horizontal.mp4"), 1920, 1080)]),
    ]})
    pasta = com_chave / "pecas" / "2026-09" / "P-20260925-AB12-teste"

    r = broll.buscar_broll(com_chave, "bread dough kneading", pasta, duracao=3.0, indice=0, url_base=s.url)

    busca = [q for q in s.requisicoes if q.caminho == "/v1/videos/search"]
    assert busca[0].query["orientation"] == ["portrait"]
    assert busca[0].cabecalhos["Authorization"] == CHAVE
    assert [q.caminho for q in s.requisicoes if q.caminho.endswith(".mp4")] == ["/vertical.mp4"]
    assert r is not None
    assert r["pexels_id"] == 11
    assert r["arquivo"] == "broll/00.mp4" and r["bruto"] == "broll/00_src.mp4"
    assert r["autor"] == "Autora 11" and r["pagina"].endswith("-11/")
    assert "Pexels" in r["licenca"] and r["termo"] == "bread dough kneading"
    final = pasta / "broll" / "00.mp4"
    info = ffmpeg.sondar(final)
    assert (info["largura"], info["altura"], info["fps"]) == (1080, 1920, "30/1")
    assert abs(info["duracao"] - 3.0) < 0.1
    assert info["taxa_audio"] is None  # b-roll sem áudio


# ------------------------------------------------------------------ funcional


def test_curtos_e_irrelevantes_sao_descartados_e_sem_valido_devolve_vazio(com_chave, servidor_stub):
    s = servidor_stub
    s.rota("GET", "/v1/videos/search", json={"videos": [
        _video(1, 3, "https://www.pexels.com/video/bread-dough-1/", [_arq("http://x/1.mp4", 1080, 1920)]),
        _video(2, 30, "https://www.pexels.com/video/ocean-waves-at-sunset-2/", [_arq("http://x/2.mp4", 1080, 1920)]),
    ]})
    pasta = com_chave / "pecas" / "2026-09" / "P-20260925-AB12-teste"

    r = broll.buscar_broll(com_chave, "bread dough", pasta, duracao=3.0, url_base=s.url)

    assert r is None
    # tentou retrato e paisagem (a segunda busca da origem), e não baixou nada
    orientacoes = [q.query["orientation"][0] for q in s.requisicoes if q.caminho == "/v1/videos/search"]
    assert orientacoes == ["portrait", "landscape"]
    assert not any(q.caminho.endswith(".mp4") for q in s.requisicoes)
    assert not (pasta / "broll").exists()

    # a triagem sozinha, com os motivos
    itens = [broll.pexels.normalizar_video(v) for v in (
        _video(1, 3, "https://www.pexels.com/video/bread-dough-1/", [_arq("http://x/1.mp4", 1080, 1920)]),
        _video(2, 30, "https://www.pexels.com/video/ocean-waves-at-sunset-2/", [_arq("http://x/2.mp4", 1080, 1920)]),
        _video(3, 4, "https://www.pexels.com/video/fresh-bread-3/", [_arq("http://x/3.mp4", 1080, 1920)]),
        _video(4, 9, "https://www.pexels.com/video/4/", [_arq("http://x/4.mp4", 1080, 1920)]),
    )]
    validos, descartados = broll.triar(itens, "bread dough", 3.0)
    assert [v["id"] for v in validos] == [3, 4]  # 4 s = 3 + 1: no limite, fica; página sem descrição não é julgada
    motivos = {d["pexels_id"]: d["motivo"] for d in descartados}
    assert "duração" in motivos[1] and "relevância" in motivos[2]


def test_sem_resultado_nenhum_devolve_vazio_sem_erro(com_chave, servidor_stub):
    servidor_stub.rota("GET", "/v1/videos/search", json={"videos": []})
    pasta = com_chave / "pecas" / "2026-09" / "P-20260925-AB12-teste"
    assert broll.buscar_broll(com_chave, "bread", pasta, duracao=2.0, url_base=servidor_stub.url) is None


def test_regras_de_colocacao_da_origem():
    assert broll.validar_plano([{"t": 8.0, "dur": 3.0, "termo": "bread"}], 60.0) == []
    problemas = broll.validar_plano([
        {"t": 1.0, "dur": 3.0, "termo": "a"},     # antes dos 3 s livres
        {"t": 6.0, "dur": 5.0, "termo": "b"},     # acima de 4 s e colado no anterior
        {"t": 57.0, "dur": 2.5, "termo": ""},     # invade o fecho e sem termo
    ], 60.0)
    texto = " | ".join(problemas)
    assert "3s iniciais" in texto and "faixa 2-4s" in texto and "respiro" in texto
    assert "fecho" in texto and "sem termo" in texto
    # teto de 40% do corte: 2 inserções de 4 s em 18 s = 44%
    problemas = broll.validar_plano([{"t": 3.0, "dur": 4.0, "termo": "a"}, {"t": 11.0, "dur": 4.0, "termo": "b"}],
                                    18.0)
    assert any("teto 40%" in p for p in problemas)
