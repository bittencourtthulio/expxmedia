"""T-04.12: produção do reel de página e gate do roteirista.

Integração: uma página servida pelo stub local é capturada, o roteiro passa no gate, a narração sai do
provedor de teste (EXPXMEDIA_PROVEDORES_TESTE=1, sinal audível sintético), a legenda e a montagem usam a
Alma fictícia, a mistura é normalizada e o MP4 passa nas 11 checagens do perfil `reel_pagina`.

Funcional: o gate do roteirista (130 a 180 palavras, sem travessão, markdown ou número decimal em
algarismo, CTA contido no roteiro) recusa antes de narrar; a peça produzida lista os arquivos com papel
final, legenda e alinhamento.

O texto do selo e do card final é copy da peça (parâmetro do teste), nunca do código (M13).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from expxmedia.narrar import base as narrar_base
from expxmedia.nucleo import rastro, tempo
from expxmedia.peca import modelo
from expxmedia.producao import abertura, reel_pagina
from expxmedia.revisar import roteiro as gate
from expxmedia.video import ffmpeg, verificar
from fixtures.fontes_ficticias import semear_cache
from stubs import higgsfield_falso
from stubs.servidor import ServidorStub

PARAGRAFO = ("Este parágrafo existe para dar corpo de texto à página de teste, com frases comuns e sem nenhuma "
             "marca, de modo que o texto renderizado passe com folga do piso de caracteres. ")
CTA = "FORNADA"
# 8 palavras por frase: a 3,5 palavras por segundo os blocos de legenda ficam cheios (4 palavras)
FRASES = [
    "A massa descansa a noite inteira na bancada.",
    "De manhã cedo o forno já está quente.",
    "O pão sai com casca fina e crocante.",
    "O miolo fica aberto macio e bem úmido.",
    "Quem prova uma vez volta no dia seguinte.",
    "A fila anda rápido porque tudo está pronto.",
    "Você escolhe o pão e leva para casa.",
    "O café da manhã fica pronto em minutos.",
    "Nada de pão duro no fim da tarde.",
    "A receita usa só farinha água e sal.",
    "O tempo faz o resto do trabalho todo.",
    "Cada fornada tem hora marcada para sair quentinha.",
    "Você pode reservar o seu antes de chegar.",
    "A gente separa e deixa no balcão pronto.",
    "Assim ninguém fica sem o pão da semana.",
    "O cheiro chega na esquina antes da porta.",
    "As crianças pedem a casquinha no caminho todo.",
    "Os vizinhos já sabem a hora de passar.",
    "Quem trabalha cedo leva o pão ainda morno.",
    "No fim de semana a fornada sai dobrada.",
    f"Comenta {CTA} que a gente manda os horários.",
]
ROTEIRO = " ".join(FRASES)
CARD_FINAL = ["Comenta {cta}", "para saber o horário"]
SELO = "Comenta {cta}"


def _html() -> bytes:
    secoes = "".join(
        f"<section><h2>Seção número {n} do conteúdo</h2><p>{PARAGRAFO * 5}</p></section>" for n in range(1, 7))
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Página de teste</title><style>"
            "html,body{margin:0;padding:0;background:#ffffff;color:#111111;font:16px/1.4 sans-serif}"
            "section{height:900px;overflow:hidden}h1,h2{margin:0;height:60px}p{margin:0}</style></head><body>"
            f"<h1>Título principal da página de teste</h1>{secoes}</body></html>").encode("utf-8")


@pytest.fixture
def ambiente(instalacao, tmp_path, monkeypatch, requer_binario):
    requer_binario("ffmpeg")
    requer_binario("ffprobe")
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    cache = semear_cache(tmp_path / "fontes")
    with ServidorStub() as stub:
        stub.rota("GET", "/pagina", corpo=_html(), cabecalhos={"Content-Type": "text/html; charset=utf-8"})
        yield instalacao, stub.url_de("/pagina"), cache


@pytest.fixture
def ambiente_abertura(ambiente, tmp_path, monkeypatch):
    """O `ambiente` com o Higgsfield falso no PATH, servindo o clipe gerado por um segundo stub local."""
    raiz, url, cache = ambiente
    bin_ = tmp_path / "bin"
    higgsfield_falso.instalar(bin_)
    log = tmp_path / "higgsfield.log"
    monkeypatch.setenv("PATH", str(bin_) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("HIGGSFIELD_FALSO_LOG", str(log))
    with ServidorStub() as stub:
        monkeypatch.setenv("HIGGSFIELD_FALSO_URL", stub.url)
        yield raiz, url, cache, stub, log


def _clipe_que_vira_a_tira(tira, tmp) -> bytes:
    """720x1280, 4 s: um plano liso até 2 s, vira o topo da tira entre 2 e 3 s e segura até 4 s."""
    Image.new("RGB", (720, 1280), (30, 60, 90)).save(tmp / "q_ini.png")
    Image.open(tira).convert("RGB").crop((0, 0, 1080, 1920)).resize((720, 1280)).save(tmp / "q_fim.png")
    saida = tmp / "clipe_gerado.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-t", "3",
                    "-i", str(tmp / "q_ini.png"), "-loop", "1", "-framerate", "30", "-t", "2",
                    "-i", str(tmp / "q_fim.png"), "-filter_complex",
                    "[0:v][1:v]xfade=transition=fade:duration=1:offset=2,format=yuv420p[v]",
                    "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "14", str(saida)],
                   check=True, capture_output=True)
    return saida.read_bytes()


def _inicio_do_audio(video) -> float:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                       capture_output=True, check=True)
    x = np.abs(np.frombuffer(r.stdout, dtype="<i2").astype(float))
    return float(np.argmax(x > 0.05 * x.max()) / 8000)


def _entrada(url: str, **muda) -> dict:
    dados = {
        "url": url,
        "titulo": "Pão de fermentação natural",
        "roteiro": ROTEIRO,
        "cta": CTA,
        "impacto": ["PÃO QUENTE", "TODA MANHÃ"],
        "card_final": CARD_FINAL,
        "selo": SELO,
        "legenda": "Comenta FORNADA e receba os horários da semana.",
        "conteudo": {"gancho": FRASES[0], "gancho_tipo": "processo", "cta_forma": "comentario"},
    }
    dados.update(muda)
    return dados


def _contar_narrar(monkeypatch) -> list:
    chamadas = []
    original = narrar_base.narrar

    def contado(*a, **k):
        chamadas.append(a)
        return original(*a, **k)

    monkeypatch.setattr(reel_pagina.narrar_base, "narrar", contado)
    return chamadas


# ------------------------------------------------------------------ integração


@pytest.mark.integracao_local
def test_produz_reel_de_pagina_aprovado_nas_11_checagens(ambiente, monkeypatch):
    raiz, url, cache = ambiente
    chamadas = _contar_narrar(monkeypatch)
    r = reel_pagina.produzir(raiz, _entrada(url), cache_fontes=cache)

    assert len(chamadas) == 1  # narra uma vez
    assert r["status"] == "produzida"
    ver = r["verificacao"]
    assert ver["aprovado"] is True and ver["perfil"] == "reel_pagina" and ver["achados"] == []

    pasta = modelo.pasta(raiz, r["peca_id"])
    final = pasta / "saida" / "final.mp4"
    assert final.is_file()
    # a verificação refeita de fora dá o mesmo: as 11 checagens, inclusive área segura, cauda e CTA
    midia = pasta / "midia"
    art = verificar.Artefatos(caps_txt=midia / "caps.txt", legendas=midia / "legendas.json",
                              alinhamento=midia / "alinhamento.json", roteiro=pasta / "texto" / "roteiro.txt")
    refeita = verificar.verificar(final, "reel_pagina", art)
    assert refeita["aprovado"], refeita["achados"]
    assert set(verificar.PERFIS["reel_pagina"].checagens) == set(verificar.ONZE) and len(verificar.ONZE) == 11
    assert 50 <= r["duracao"] <= 70

    peca = modelo.carregar(raiz, r["peca_id"])
    assert peca["producao"]["provedores"] == {"capturar_pagina": "playwright", "narrar": "teste",
                                             "legendar": "local", "editar_video": "ffmpeg"}
    assert peca["conteudo"]["roteiro"] == "texto/roteiro.txt" and peca["conteudo"]["cta"] == CTA
    assert json.loads((midia / "visual.json").read_text(encoding="utf-8"))["selo_cta"] == CTA
    eventos, _ = rastro.ler(raiz, tempo.agora(raiz).strftime("%Y-%m"))
    assert any(e["evento"] == "geracao_concluida" and e["peca_id"] == r["peca_id"] for e in eventos)


@pytest.mark.integracao_local
def test_abertura_produzida_na_captura_vai_ao_reel_sem_mudar_a_duracao(ambiente_abertura, tmp_path):
    raiz, url, cache, stub, log = ambiente_abertura
    r_sem = reel_pagina.produzir(raiz, _entrada(url), cache_fontes=cache)
    midia_sem = modelo.pasta(raiz, r_sem["peca_id"]) / "midia"

    # a skill: captura em rascunhos, `produzir abertura` na pasta da captura, depois `produzir reel-pagina`
    captura = raiz / "rascunhos" / "pao" / "captura"
    captura.mkdir(parents=True)
    for nome in ("tira.png", "captura.json", "site.md"):
        shutil.copyfile(midia_sem / nome, captura / nome)
    stub.rota("GET", "/resultado.mp4", corpo=_clipe_que_vira_a_tira(captura / "tira.png", tmp_path))
    marcador = abertura.gerar(raiz, captura, prompt="a loaf of bread rising in a warm oven", tipo="objeto")
    assert marcador["montado_em"] is None and marcador["janela"]["encaixe_s"] is not None
    assert [c for c in higgsfield_falso.chamadas(log) if c[:2] == ["generate", "create"]]
    custo = abertura.TIPOS["objeto"]["creditos_por_abertura"]
    assert abertura.creditos_gastos_hoje(raiz) == custo  # a abertura em rascunhos já conta para o teto do dia

    entrada = _entrada(url)
    entrada.pop("url")
    r_com = reel_pagina.produzir(raiz, {**entrada, "captura": "rascunhos/pao/captura"}, cache_fontes=cache)
    assert r_com["status"] == "produzida" and r_com["verificacao"]["aprovado"], r_com["verificacao"]["achados"]
    pasta = modelo.pasta(raiz, r_com["peca_id"])
    midia, final = pasta / "midia", pasta / "saida" / "final.mp4"

    # a abertura chegou à montagem: troca o fundo do começo, não é emendada na frente
    assert (midia / "abertura.mp4").is_file()
    assert r_com["montagem"]["abertura"] == pytest.approx(abertura.DURACAO_NA_TELA, abs=0.05)
    assert r_sem["montagem"]["abertura"] is None
    visual = json.loads((midia / "visual.json").read_text(encoding="utf-8"))
    assert visual["abertura_gerada"] == pytest.approx(abertura.DURACAO_NA_TELA, abs=0.05)
    # mesma duração do reel sem abertura, narração desde t=0
    assert r_com["duracao"] == r_sem["duracao"]
    d_com = ffmpeg.sondar(final)["duracao"]
    d_sem = ffmpeg.sondar(modelo.pasta(raiz, r_sem["peca_id"]) / "saida" / "final.mp4")["duracao"]
    assert abs(d_com - d_sem) < 1 / 30 + 1e-3
    # a narração entra no mesmo instante do reel sem abertura e do próprio áudio narrado (o que o provedor
    # de teste tem de silêncio inicial é dele): a abertura não empurrou o áudio
    final_sem = modelo.pasta(raiz, r_sem["peca_id"]) / "saida" / "final.mp4"
    offset = json.loads((midia / "legendas.json").read_text(encoding="utf-8"))["offset_audio"]
    inicio_narracao = _inicio_do_audio(midia / "narracao.mp3") + offset
    assert abs(_inicio_do_audio(final) - _inicio_do_audio(final_sem)) < 0.05
    assert abs(_inicio_do_audio(final) - inicio_narracao) < 0.05
    # montado_em só na cópia que foi ao ar, gravado depois do MP4
    marca = json.loads((midia / "abertura.json").read_text(encoding="utf-8"))
    assert marca["montado_em"] is not None and marca["job"] == marcador["job"]
    assert (midia / "abertura.json").stat().st_mtime_ns >= final.stat().st_mtime_ns

    # a peça registra a abertura e a capacidade video_ia
    peca = modelo.carregar(raiz, r_com["peca_id"])
    assert "video_ia" in peca["producao"]["capacidades"]
    assert peca["producao"]["provedores"]["video_ia"] == "higgsfield"
    assert "video_ia" not in modelo.carregar(raiz, r_sem["peca_id"])["producao"]["capacidades"]
    papeis = {a["caminho"]: a["papel"] for a in peca["arquivos"]}
    assert papeis["midia/abertura.mp4"] == "fonte" and papeis["midia/abertura.json"] == "fonte"
    # a cópia na peça não conta os créditos de novo: é o mesmo job
    assert abertura.creditos_gastos_hoje(raiz) == custo


# ------------------------------------------------------------------ funcional


@pytest.mark.parametrize("roteiro,checagem", [
    (ROTEIRO.replace("A massa descansa", "A massa — descansa", 1), "travessao"),
    (ROTEIRO.replace(f"Comenta {CTA}", "Comenta PÃO"), "cta"),
])
@pytest.mark.integracao_local
def test_gate_recusa_antes_de_narrar(ambiente, monkeypatch, roteiro, checagem):
    raiz, url, cache = ambiente
    chamadas = _contar_narrar(monkeypatch)
    with pytest.raises(reel_pagina.ErroRoteiroReprovado) as erro:
        reel_pagina.produzir(raiz, _entrada(url, roteiro=roteiro), cache_fontes=cache)
    assert checagem in [a["checagem"] for a in erro.value.achados]
    assert chamadas == []
    pasta = modelo.pasta(raiz, erro.value.peca_id)
    assert not (pasta / "midia" / "narracao.mp3").exists()
    assert modelo.carregar(raiz, erro.value.peca_id)["status"] == "roteiro"
    eventos, _ = rastro.ler(raiz, tempo.agora(raiz).strftime("%Y-%m"))
    assert any(e["evento"] == "geracao_falhou" and e["peca_id"] == erro.value.peca_id for e in eventos)


@pytest.mark.integracao_local
def test_peca_lista_arquivos_final_legenda_e_alinhamento(ambiente):
    raiz, url, cache = ambiente
    r = reel_pagina.produzir(raiz, _entrada(url), cache_fontes=cache)
    papeis = {a["papel"]: a for a in r["arquivos"]}
    assert {"final", "legenda", "alinhamento", "audio", "roteiro", "srt", "fonte"} <= set(papeis)
    assert papeis["final"] == {"caminho": "saida/final.mp4", "papel": "final", "formato": "9:16"}
    assert papeis["alinhamento"]["caminho"] == "midia/alinhamento.json"
    pasta = modelo.pasta(raiz, r["peca_id"])
    for a in r["arquivos"]:
        assert (pasta / a["caminho"]).is_file(), a


def test_gate_do_roteirista():
    assert gate.revisar_roteiro(ROTEIRO, CTA)["aprovado"] is True
    assert gate.revisar_roteiro(ROTEIRO, CTA)["palavras"] == 168
    casos = {
        "palavras": " ".join(ROTEIRO.split()[:128]) + f" {CTA}",
        "travessao": ROTEIRO.replace("A massa", "A massa – ", 1),
        "markdown": ROTEIRO.replace("A massa", "**A massa**", 1),
        "numero_decimal": ROTEIRO.replace("A massa", "Em 2,5 horas a massa", 1),
    }
    for checagem, texto in casos.items():
        r = gate.revisar_roteiro(texto, CTA)
        assert r["aprovado"] is False and checagem in [a["checagem"] for a in r["achados"]], checagem
    # os limites são inclusivos: 130 e 180 passam, 129 e 181 não
    palavras = ROTEIRO.split()
    assert gate.revisar_roteiro(" ".join(palavras[:129] + [CTA]), CTA)["aprovado"] is True
    assert gate.revisar_roteiro(" ".join(palavras[:128] + [CTA]), CTA)["aprovado"] is False
    longo = " ".join((palavras * 2)[:180])
    assert gate.revisar_roteiro(longo, CTA)["aprovado"] is True
    assert gate.revisar_roteiro(longo + " mais", CTA)["aprovado"] is False
    # inteiro em algarismo passa (o gate da origem só pega decimal); CTA vazio reprova
    assert gate.revisar_roteiro(ROTEIRO.replace("A massa", "Em 4 horas a massa", 1), CTA)["aprovado"] is True
    assert "cta" in [a["checagem"] for a in gate.revisar_roteiro(ROTEIRO, "")["achados"]]
    assert (gate.PALAVRAS_MIN, gate.PALAVRAS_MAX) == (130, 180)


def test_entrada_invalida_nao_cria_peca(instalacao):
    with pytest.raises(reel_pagina.ErroEntradaReel, match="card_final"):
        reel_pagina.produzir(instalacao, _entrada("http://127.0.0.1:1/x", card_final=[]))
    with pytest.raises(reel_pagina.ErroEntradaReel, match="url"):
        reel_pagina.produzir(instalacao, _entrada(None))
    assert not list((instalacao / "pecas").rglob("peca.json"))
