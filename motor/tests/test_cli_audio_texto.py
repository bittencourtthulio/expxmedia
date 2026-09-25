"""T-04.13: CLI de áudio, texto e reel de página — narrar, transcrever, legendar reel/aula, verificar e
produzir reel-pagina (D-11)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from expxmedia import cli
from expxmedia.video import ffmpeg

MOTOR = Path(__file__).resolve().parents[1]
W, H = 1080, 1920
ROTEIRO = "Um roteiro curto de teste. No fim ele pede: comenta QUERO que eu te mando."


def _roda(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def _subprocesso(*argv, cwd=MOTOR):
    return subprocess.run(["uv", "run", "--project", str(MOTOR), "expxmedia-motor", *map(str, argv)],
                          capture_output=True, text=True, cwd=cwd)


def _rodar(capsys, *argv):
    codigo = cli.main([str(a) for a in argv])
    return codigo, json.loads(capsys.readouterr().out)


def _cartao(caminho, caixa):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if caixa:
        d = ImageDraw.Draw(img)
        d.rectangle(caixa, fill=(250, 250, 250, 255))
        x0, y0, x1, y1 = caixa
        d.rectangle((x0 + 60, y0 + 60, x1 - 60, y1 - 60), fill=(20, 20, 20, 255))
    img.save(caminho)


def _reel_de_teste(pasta: Path, dur: int = 32, dims=(W, H)) -> Path:
    """MP4 sintético com o card do CTA no fim e os artefatos coerentes (legendas, alinhamento, roteiro)."""
    pasta.mkdir(parents=True)
    caps = pasta / "caps"
    caps.mkdir()
    _cartao(caps / "blank.png", None)
    _cartao(caps / "c1.png", (140, 1300, 940, 1480))
    _cartao(caps / "end.png", (90, 700, 990, 1200))
    tom = pasta / "tom.m4a"
    _roda(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={dur}",
           "-ac", "2", "-c:a", "aac", str(tom)])
    audio = pasta / "audio.m4a"
    assert ffmpeg.normalizar_audio(tom, audio)["dentro_do_alvo"]
    video = pasta / "reel.mp4"
    _roda(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x304050:s={dims[0]}x{dims[1]}:r=30",
           "-loop", "1", "-framerate", "30", "-i", str(caps / "end.png"), "-i", str(audio),
           "-filter_complex", "[0:v][1:v]overlay=0:0,format=yuv420p[v]", "-map", "[v]", "-map", "2:a",
           "-t", str(dur), "-c:v", "libx264", "-preset", "ultrafast", "-r", "30", "-c:a", "copy", str(video)])
    tom.unlink()
    audio.unlink()
    n = dur - 4
    linhas = ["file 'caps/blank.png'", "duration 0.5"] + ["file 'caps/c1.png'", "duration 1.0"] * n
    linhas += ["file 'caps/end.png'", f"duration {round(dur - 0.5 - n, 3)}"]
    (pasta / "caps.txt").write_text("\n".join(linhas) + "\n")
    (pasta / "legendas.json").write_text(json.dumps({"duracao": dur, "offset_audio": 0.5, "cta": "QUERO"}))
    (pasta / "roteiro.txt").write_text(ROTEIRO)
    fim, k = dur - 2.5, len(ROTEIRO)
    (pasta / "alignment.json").write_text(json.dumps({
        "characters": list(ROTEIRO),
        "character_start_times_seconds": [fim * i / k for i in range(k)],
        "character_end_times_seconds": [fim * (i + 1) / k for i in range(k)]}))
    (pasta / "aula.srt").write_text("1\n00:00:00,500 --> 00:00:02,000\nPrimeira linha.\n")
    return video


# ------------------------------------------------------------------ integração


def test_subcomandos_novos_aparecem_no_help():
    topo = _subprocesso("--help")
    assert topo.returncode == 0, topo.stderr
    for nome in ("narrar", "transcrever", "legendar", "verificar", "produzir"):
        assert nome in topo.stdout, nome
    legendar = _subprocesso("legendar", "--help")
    assert legendar.returncode == 0 and "reel" in legendar.stdout and "aula" in legendar.stdout
    produzir = _subprocesso("produzir", "--help")
    assert produzir.returncode == 0 and "reel-pagina" in produzir.stdout
    verificar = _subprocesso("verificar", "--help")
    assert verificar.returncode == 0 and "--perfil" in verificar.stdout and "reel_pagina" in verificar.stdout


@pytest.mark.integracao_local
def test_verificar_perfil_reel_sai_0_em_subprocesso(instalacao, tmp_path, requer_binario):
    requer_binario("ffmpeg")
    video = _reel_de_teste(tmp_path / "peca")
    feito = _subprocesso("--raiz", instalacao, "verificar", "--perfil", "reel", video)
    assert feito.returncode == 0, feito.stdout + feito.stderr
    saida = json.loads(feito.stdout)
    assert saida["ok"] is True and saida["aprovado"] is True and saida["perfil"] == "reel" and saida["achados"] == []


# ------------------------------------------------------------------ funcional


@pytest.mark.integracao_local
def test_verificar_perfil_aula_em_1080x1080_reprova_com_dimensao(instalacao, tmp_path, requer_binario, capsys):
    requer_binario("ffmpeg")
    video = _reel_de_teste(tmp_path / "quadrado", dur=6, dims=(1080, 1080))
    codigo, saida = _rodar(capsys, "--raiz", instalacao, "verificar", "--perfil", "aula", video)
    assert codigo != 0
    assert saida["ok"] is False and saida["aprovado"] is False
    dimensao = next(a for a in saida["achados"] if a["checagem"] == "dimensao")
    assert dimensao["obtido"] == "1080x1080" and "1920x1080" in dimensao["esperado"]


def test_verificar_perfil_desconhecido_e_entrada_invalida(instalacao, tmp_path, capsys):
    arq = tmp_path / "x.mp4"
    arq.write_bytes(b"")
    codigo, saida = _rodar(capsys, "--raiz", instalacao, "verificar", "--perfil", "inexistente", arq)
    assert codigo == cli.ENTRADA_INVALIDA and "perfil desconhecido" in saida["mensagem"]
    codigo, saida = _rodar(capsys, "--raiz", instalacao, "verificar", "--perfil", "reel", tmp_path / "nao.mp4")
    assert codigo == cli.ENTRADA_INVALIDA


@pytest.mark.integracao_local
def test_narrar_e_legendar_reel_pelo_cli(instalacao, tmp_path, capsys, requer_binario):
    requer_binario("ffmpeg")
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    roteiro = tmp_path / "roteiro.txt"
    texto = ("A fornada das quatro sai em dez minutos, quentinha. Comenta PÃO que a gente separa o seu "
             "e avisa hoje mesmo antes de fechar.")
    roteiro.write_text(texto, encoding="utf-8")
    codigo, saida = _rodar(capsys, "--raiz", instalacao, "narrar", "--roteiro", roteiro, "--porta-voz",
                           "porta-voz-teste", "--tipo", "reel", "--saida", "pecas/rascunho")
    assert codigo == 0, saida
    assert saida["provedor"] == "teste" and saida["audio"] == "pecas/rascunho/narracao.mp3"
    assert "alinhamento" not in saida  # o alinhamento fica no arquivo, não no stdout
    alinhamento = instalacao / saida["arquivo_alinhamento"]
    assert alinhamento.is_file()

    # legenda com a Inter embarcada (a Alma fictícia pede Google Fonts; sem rede, reserva com aviso)
    codigo, saida = _rodar(capsys, "--raiz", instalacao, "legendar", "reel", "--alinhamento", alinhamento,
                           "--roteiro", roteiro, "--saida", "pecas/rascunho", "--cta", "PÃO",
                           "--card-final", "Comenta {cta}", "--card-final", "para saber o horário")
    assert codigo == 0, saida
    assert saida["cta"] == "PÃO" and saida["blocos"] >= 3
    pasta = instalacao / "pecas" / "rascunho"
    assert (pasta / "caps.txt").is_file() and (pasta / "caps" / "end.png").is_file()
    assert (pasta / "legendas.json").is_file() and (pasta / "legendas.srt").is_file()

    # CTA fora do roteiro: entrada inválida
    codigo, saida = _rodar(capsys, "--raiz", instalacao, "legendar", "reel", "--alinhamento", alinhamento,
                           "--roteiro", roteiro, "--saida", "pecas/rascunho", "--cta", "BOLO",
                           "--card-final", "Comenta {cta}")
    assert codigo == cli.ENTRADA_INVALIDA and "BOLO" in saida["mensagem"]


def test_legendar_aula_pelo_cli(instalacao, tmp_path, capsys):
    roteiro = tmp_path / "roteiro.txt"
    roteiro.write_text("Hoje a gente fala de fermentação natural. É mais simples do que parece.", encoding="utf-8")
    palavras = roteiro.read_text(encoding="utf-8").split()
    transcricao = tmp_path / "transcricao.json"
    transcricao.write_text(json.dumps({"palavras": [{"w": p, "t0": 0.4 * i, "t1": 0.4 * i + 0.3}
                                                    for i, p in enumerate(palavras)]}), encoding="utf-8")
    codigo, saida = _rodar(capsys, "--raiz", instalacao, "legendar", "aula", "--roteiro", roteiro,
                           "--transcricao", transcricao, "--saida", "pecas/aula")
    assert codigo == 0, saida
    srt = (instalacao / "pecas" / "aula" / "legendas.srt").read_text(encoding="utf-8")
    assert srt.startswith("1\n00:00:00,000 --> ") and "fermentação natural." in srt
    assert saida["srt"] == "pecas/aula/legendas.srt" and saida["legendas"] >= 1


def test_transcrever_sem_idioma_e_audio_ausente(instalacao, tmp_path, capsys):
    codigo, saida = _rodar(capsys, "--raiz", instalacao, "transcrever", "--audio", tmp_path / "nao.mp3",
                           "--saida", "pecas/t/transcricao.json")
    assert codigo == cli.ENTRADA_INVALIDA and "nao.mp3" in saida["mensagem"]


def test_produzir_reel_pagina_com_entrada_invalida_sai_2(instalacao, tmp_path, capsys):
    entrada = tmp_path / "reel.json"
    entrada.write_text(json.dumps({"titulo": "x"}), encoding="utf-8")
    codigo, saida = _rodar(capsys, "--raiz", instalacao, "produzir", "reel-pagina", "--entrada", entrada)
    assert codigo == cli.ENTRADA_INVALIDA and "url" in saida["mensagem"]
