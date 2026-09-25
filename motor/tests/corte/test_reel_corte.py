"""T-06.07: produção de reel de corte a partir de vídeo longo (D-43).

O vídeo de teste tem 90 s: a fixture de rosto (domínio público) num quadro 16:9, com a fala sintetizada
pelo `say` do macOS numa voz pt_BR. A produção roda uma vez por módulo (transcrição, momentos, corte,
alinhamento, legenda, gancho, normalização e verificação levam alguns minutos) e os dois testes leem o
resultado.

- integração: gera MP4 9:16 aprovado no perfil corte (sem CTA), com o gancho textual no topo nos 3
  primeiros segundos;
- funcional: a peça registra arquivos com papel final, srt e fonte, e o evento geracao_concluida com
  segundos.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from expxmedia.corte import momentos
from expxmedia.nucleo import rastro
from expxmedia.producao import reel_corte
from expxmedia.video import ffmpeg

ROSTO = Path(__file__).resolve().parents[1] / "fixtures" / "rosto" / "astronauta.png"
CAIXA_FIXTURE = (176, 65, 98, 98)
FALA = (
    "Hoje eu quero contar como a gente organizou a fornada da manhã. Durante muito tempo, o pão saía às sete "
    "horas e acabava antes das oito. Então nós mudamos a rotina da cozinha. A primeira massa agora descansa a "
    "noite inteira na geladeira, e isso deixa o sabor mais profundo. Às cinco da manhã, a equipe modela "
    "trezentos pães em menos de uma hora. O forno aquece enquanto a massa cresce, e nada fica parado "
    "esperando. Você sabia que três graus de diferença na água mudam o tempo de fermentação em quase meia "
    "hora? Por isso a gente mede tudo com termômetro, todos os dias. Quando o cliente chega, encontra pão "
    "quente na prateleira até as dez horas. A fila diminuiu, o desperdício caiu pela metade, e a equipe "
    "trabalha com mais calma. O segredo não foi comprar máquina nova. Foi olhar para cada etapa e cortar a "
    "espera que ninguém via. Se você tem um negócio pequeno, experimente anotar quanto tempo cada tarefa "
    "leva de verdade. Em uma semana, os números mostram onde está o gargalo. Depois disso, a decisão fica "
    "fácil. Cada detalhe conta quando a margem é pequena. E quem trabalha no balcão percebe a diferença "
    "antes de todo mundo. Amanhã a gente testa uma fornada extra no meio da tarde. Se der certo, conto aqui "
    "o resultado."
)
GANCHO = ["O PÃO ACABAVA", "ANTES DAS OITO"]
DURACAO_FONTE = 90.0


def _voz_pt_br() -> str:
    import re
    r = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    vozes = [m.group(1).strip() for m in (re.match(r"^(.+?)\s+pt_BR\s+#", l) for l in r.stdout.splitlines()) if m]
    if not vozes:
        pytest.skip("nenhuma voz pt_BR no say desta máquina")
    return "Luciana" if "Luciana" in vozes else vozes[0]


def _video_de_teste(pasta: Path) -> Path:
    """90 s, 1920x1080 a 30 fps: o rosto no meio, andando devagar, e a fala do `say`."""
    pasta.mkdir(parents=True, exist_ok=True)
    aiff = pasta / "fala.aiff"
    subprocess.run(["say", "-v", _voz_pt_br(), "-o", str(aiff), FALA], check=True, capture_output=True)
    x, y, w, h = CAIXA_FIXTURE
    m = w // 2
    rosto = pasta / "rosto.png"
    Image.open(ROSTO).convert("RGB").crop((x - m, y - m, x + w + m, y + h + m)).resize((420, 420)).save(rosto)
    video = pasta / "aula.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    "-f", "lavfi", "-i", f"color=c=0x5a6470:s=1920x1080:r=30:d={DURACAO_FONTE}",
                    "-loop", "1", "-i", str(rosto), "-i", str(aiff),
                    "-filter_complex",
                    f"[0:v][1:v]overlay=x='750-210+4*t':y=(H-h)/2:shortest=1,format=yuv420p[v];"
                    f"[2:a]apad,atrim=0:{DURACAO_FONTE}[a]",
                    "-map", "[v]", "-map", "[a]", "-t", str(DURACAO_FONTE),
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-c:a", "aac", "-ar", "48000",
                    str(video)], check=True, capture_output=True)
    return video


@pytest.fixture(scope="module")
def producao(tmp_path_factory):
    for binario in ("ffmpeg", "say"):
        if shutil.which(binario) is None:
            pytest.skip(f"binário ausente: {binario}")
    base = tmp_path_factory.mktemp("reel_corte")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_fix_inst", Path(__file__).resolve().parents[1] / "fixtures" / "instalacao.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    raiz = mod.montar_instalacao(base / "instalacao")
    video = _video_de_teste(raiz / "fontes")
    entrada = {"video": "fontes/aula.mp4", "titulo": "Fornada da manhã", "gancho": GANCHO}
    r = reel_corte.produzir(raiz, entrada)
    return raiz, video, r


# ------------------------------------------------------------------ integração


@pytest.mark.integracao_local
def test_mp4_9x16_aprovado_no_perfil_corte_com_gancho_nos_3_primeiros_segundos(producao):
    raiz, _, r = producao
    final = raiz / r["video"]
    assert final.is_file() and r["video"].endswith("saida/final.mp4")

    s = ffmpeg.sondar(final)
    assert (s["largura"], s["altura"], s["fps"]) == (1080, 1920, "30/1")
    assert "h264" in s["codecs"] and "aac" in s["codecs"]
    assert 50.0 <= s["duracao"] <= 72.0
    v = r["verificacao"]
    assert v["aprovado"] is True and v["perfil"] == "corte", v["achados"]
    # sem CTA: o perfil corte recusa CTA e a legenda saiu sem card final
    legendas = json.loads((raiz / r["pasta"] / "midia" / "legendas.json").read_text(encoding="utf-8"))
    assert legendas["cta"] is None and legendas["offset_audio"] == 0.0

    # o trecho foi o que os momentos escolheram, dentro da janela
    t = r["trecho"]
    assert 52.0 <= t["fim"] - t["inicio"] <= 72.0
    candidatos = json.loads((raiz / r["pasta"] / "midia" / "candidatos.json").read_text(encoding="utf-8"))
    assert (candidatos["candidatos"][0]["inicio"], candidatos["candidatos"][0]["fim"]) == (t["inicio"], t["fim"])

    # gancho: caixa na cor da Alma no topo, visível em 0,5 s, 1,5 s e 2,5 s
    g = r["gancho"]
    assert g["linhas"] == GANCHO and 250 <= g["y0"] < g["y1"] <= 640
    alma = json.loads((raiz / "alma" / "alma.json").read_text(encoding="utf-8"))
    cor = alma["visual"]["cores"]["destaque_2"].lstrip("#")
    alvo_bgr = np.array([int(cor[4:6], 16), int(cor[2:4], 16), int(cor[0:2], 16)], dtype=float)
    cap = cv2.VideoCapture(str(final))
    for tempo in (0.5, 1.5, 2.5):
        cap.set(cv2.CAP_PROP_POS_MSEC, tempo * 1000)
        ok, quadro = cap.read()
        assert ok
        # uma faixa da caixa à esquerda do texto (entre a borda e a primeira letra)
        faixa = quadro[g["y0"] + 20:g["y1"] - 20, g["x0"] + 8:g["x0"] + 30].reshape(-1, 3).astype(float)
        assert np.abs(faixa.mean(axis=0) - alvo_bgr).max() < 20, f"gancho ausente em {tempo} s"
    cap.release()


# ------------------------------------------------------------------ funcional


@pytest.mark.integracao_local
def test_peca_registra_final_srt_fonte_e_evento_com_segundos(producao):
    raiz, _, r = producao
    peca = json.loads((raiz / r["pasta"] / "peca.json").read_text(encoding="utf-8"))
    assert peca["tipo"] == "reel" and peca["status"] == "produzida"
    papeis = {a["papel"]: a for a in peca["arquivos"]}
    assert {"final", "srt", "fonte"} <= set(papeis)
    assert papeis["final"]["formato"] == "9:16"
    for a in peca["arquivos"]:
        assert not Path(a["caminho"]).is_absolute()
        assert (raiz / r["pasta"] / a["caminho"]).is_file(), a["caminho"]
    assert papeis["srt"]["caminho"].endswith(".srt")
    srt = (raiz / r["pasta"] / papeis["srt"]["caminho"]).read_text(encoding="utf-8")
    assert "-->" in srt
    fonte = json.loads((raiz / r["pasta"] / papeis["fonte"]["caminho"]).read_text(encoding="utf-8"))
    assert fonte["video"] == "fontes/aula.mp4" and fonte["cta"] is None
    assert fonte["trechos"][0]["modo"] in ("rosto", "central", "fundo_desfocado")
    assert peca["conteudo"]["cta"] is None
    assert set(peca["producao"]["capacidades"]) >= {"transcrever", "editar_video", "legendar"}

    mes = peca["criada_em"][:7]
    eventos, _ = rastro.ler(raiz, mes)
    concl = [e for e in eventos if e["evento"] == "geracao_concluida" and e["peca_id"] == r["peca_id"]]
    assert len(concl) == 1
    assert isinstance(concl[0]["segundos"], (int, float)) and concl[0]["segundos"] > 0
    assert concl[0]["resultado"] == "ok"
    assert not [e for e in eventos if e["evento"] == "geracao_falhou"]


def test_entrada_invalida_nao_cria_peca(instalacao):
    (instalacao / "fontes").mkdir()
    (instalacao / "fontes" / "x.mp4").write_bytes(b"")
    with pytest.raises(reel_corte.ErroEntradaCorte) as erro:
        reel_corte.produzir(instalacao, {"video": "fontes/x.mp4", "titulo": "x",
                                         "gancho": ["UM", "DOIS", "TRES", "QUATRO"]})
    assert erro.value.campo == "gancho"
    with pytest.raises(reel_corte.ErroEntradaCorte) as erro:
        reel_corte.produzir(instalacao, {"video": "fontes/nao-existe.mp4", "titulo": "x", "gancho": ["UM"]})
    assert erro.value.campo == "video"
    assert list((instalacao / "pecas").rglob("peca.json")) == []
    assert momentos.carregar_config("pt")["janela_max_s"] == 72.0
