"""T-07.05: produção de aula (D-23, D-26, D-32, D-40, D-41).

Integração: uma aula curta narrada pelo provedor de teste, com avatar de teste gerado do ÁUDIO e uma
gravação de tela editada por cues, sai nos dois formatos com dois MP4 e dois SRT aprovados no perfil
`aula`, e a peça fica `produzida` com os arquivos do contrato (audio, alinhamento, avatar, tela, srt e um
final por formato).

Funcional: uma aula que usa uma apresentação registra o peca_id dela em `compoe` e mostra os slides dela;
a narração da aula vai com o bloco de parâmetros `aula` e não passa pela correção de ritmo mínimo (que é
só do reel): narrada a 2 palavras por segundo, abaixo do piso do reel, o áudio fica com a duração natural.
"""
from __future__ import annotations

import json
import re
import subprocess

import pytest
from PIL import Image

from expxmedia.aula import cues as aula_cues
from expxmedia.narrar import base as narrar_base
from expxmedia.nucleo import arquivos, rastro, tempo
from expxmedia.peca import modelo
from expxmedia.producao import aula
from expxmedia.video import ffmpeg
from fixtures.fontes_ficticias import semear_cache

pytestmark = pytest.mark.integracao_local

ROTEIRO = (
    "[[s1]] Hoje você aprende a organizar a vitrine da padaria em três passos simples. "
    "[[s2]] Primeiro, separe os pães por horário de saída do forno. "
    "[[s3]] Depois, coloque os mais pedidos na altura dos olhos. Pronto."
)
CENAS = [
    {"cue": "s1", "modo": "cena", "rotulo": "abertura", "titulo": "Vitrine em três passos", "texto": "organizar para vender",
     "itens": ["por horário", "na altura dos olhos"]},
    {"cue": "s2", "modo": "tela", "rotulo": "passo 1", "passo": "01 · horário", "fato": "pães por\nsaída do forno"},
    {"cue": "s3", "modo": "cena", "rotulo": "passo 2", "titulo": "Na altura dos olhos", "passo": "02 · altura",
     "fato": "os mais pedidos\nna frente"},
]


def _com_avatar_id(raiz):
    alma = json.loads((raiz / "alma" / "alma.json").read_text(encoding="utf-8"))
    alma["porta_vozes"][0]["avatar"]["avatar_id"] = "avatar-ficticio-0001"
    (raiz / "alma" / "alma.json").write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def ambiente(instalacao, tmp_path, monkeypatch, requer_binario):
    for b in ("node", "ffmpeg", "ffprobe"):
        requer_binario(b)
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    return instalacao, semear_cache(tmp_path / "fontes")


def _gravacao(raiz, segundos=6):
    destino = raiz / "gravacao" / "tela.mp4"
    destino.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30",
                    "-t", str(segundos), "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(destino)],
                   check=True, capture_output=True)
    return "gravacao/tela.mp4"


def _espiar_narrar(monkeypatch) -> list:
    chamadas = []
    original = narrar_base.narrar

    def espia(*a, **k):
        chamadas.append((a, k))
        return original(*a, **k)

    monkeypatch.setattr(aula.narrar_base, "narrar", espia)
    return chamadas


def _texto_srt(caminho) -> str:
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    return " ".join(l for l in linhas if l.strip() and not l.strip().isdigit() and "-->" not in l)


# ------------------------------------------------------------------ integração


def test_aula_curta_nos_dois_formatos_sai_com_dois_mp4_e_dois_srt_aprovados(ambiente, monkeypatch):
    raiz, cache = ambiente
    _com_avatar_id(raiz)
    arquivo = _gravacao(raiz)
    chamadas = _espiar_narrar(monkeypatch)
    entrada = {
        "titulo": "Vitrine em três passos",
        "roteiro": ROTEIRO,
        "cenas": json.loads(json.dumps(CENAS)),
        "formatos": ["16:9", "9:16"],
        "avatar": True,
        "tela": {"janelas": [{"cue": "s2", "arquivo": arquivo, "inicio": 0.0, "fim": 6.0, "rotulo": "planilha · horários",
                              "camera": [{"t": 0, "cx": 800}], "crop": None, "crop9": None}],
                 "marcas": None, "cue_final": None},
        "serie": "Padaria na prática",
    }
    r = aula.produzir(raiz, entrada, cache_fontes=cache)
    assert len(chamadas) == 1, "a narração é feita uma vez só"

    peca = modelo.carregar(raiz, r["peca_id"])
    assert (peca["tipo"], peca["status"], peca["formatos"]) == ("aula", "produzida", ["16:9", "9:16"])
    assert peca["slides"] == [] and peca["compoe"] == []
    pasta = raiz / r["pasta"]
    por_papel = {}
    for a in peca["arquivos"]:
        por_papel.setdefault(a["papel"], []).append(a)
        assert not a["caminho"].startswith("/") and (pasta / a["caminho"]).is_file(), a
    finais = {a["formato"]: a["caminho"] for a in por_papel["final"]}
    srts = {a["formato"]: a["caminho"] for a in por_papel["srt"]}
    assert set(finais) == set(srts) == {"16:9", "9:16"}
    for papel in ("audio", "alinhamento", "avatar", "tela", "roteiro", "legenda"):
        assert papel in por_papel, papel

    duracao = aula_cues.ler(pasta / "midia")["duration"]
    for formato, dimensao in (("16:9", (1920, 1080)), ("9:16", (1080, 1920))):
        info = ffmpeg.sondar(pasta / finais[formato])
        assert (info["largura"], info["altura"], info["fps"]) == (*dimensao, "30/1")
        assert abs(info["duracao"] - duracao) < 0.1
        v = r["verificacao"][formato]
        assert v["aprovado"] is True, v
        assert v["perfil"] == "aula" and v["achados"] == []

    # o SRT tem o texto do roteiro (sem os marcadores), nos tempos da narração (D-23)
    falado = aula_cues.texto_falado(ROTEIRO)
    assert _texto_srt(pasta / srts["16:9"]).split() == falado.split()
    assert (pasta / srts["16:9"]).read_text(encoding="utf-8") == (pasta / srts["9:16"]).read_text(encoding="utf-8")
    for bloco in arquivos.ler_json(pasta / "midia" / "legendas.json"):
        assert 1 <= len(bloco["lines"]) <= 2 and all(len(l) <= 42 for l in bloco["lines"])

    # avatar do ÁUDIO pelo provedor escolhido pelo ambiente, com a duração da narração
    assert peca["producao"]["provedores"]["avatar"] == "teste"
    assert peca["producao"]["provedores"]["narrar"] == "teste"
    assert abs(ffmpeg.sondar(pasta / "midia" / "avatar.mp4")["duracao"] - r["narracao"]["duracao_s"]) < 0.1
    # a tela cobre a fala do cue s2 até o cue seguinte
    demo = arquivos.ler_json(pasta / "midia" / "demo.json")
    c = aula_cues.ler(pasta / "midia")["cues"]
    assert abs(demo["duracao"] - (c["s3"] - c["s2"])) < 0.01
    assert aula_cues.desatualizados(pasta / "midia") == []

    eventos, _ = rastro.ler(raiz, tempo.agora(raiz).strftime("%Y-%m"))
    concluida = [e for e in eventos if e["evento"] == "geracao_concluida" and e["peca_id"] == r["peca_id"]]
    assert len(concluida) == 1 and "aula" in concluida[0]["detalhe"]


# ------------------------------------------------------------------ funcional


def _apresentacao_com_slides(raiz, n=2) -> str:
    peca = modelo.criar(raiz, tipo="apresentacao", titulo="Deck da vitrine", formatos=["16:9"], status="roteiro")
    pasta = modelo.pasta(raiz, peca["peca_id"])
    (pasta / "slides").mkdir()
    for i, cor in zip(range(1, n + 1), ((200, 40, 40), (40, 40, 200))):
        png = pasta / "slides" / f"slide_{i:02d}.png"
        Image.new("RGB", (1920, 1080), cor).save(png)
        modelo.registrar_arquivo(raiz, peca["peca_id"], png, papel="slide", formato="16:9")
    return peca["peca_id"]


def test_aula_com_apresentacao_registra_compoe_e_narracao_sem_ritmo(ambiente, monkeypatch):
    raiz, cache = ambiente
    deck = _apresentacao_com_slides(raiz)
    chamadas = _espiar_narrar(monkeypatch)
    cenas = [
        {"cue": "s1", "modo": "cena", "titulo": "Vitrine em três passos"},
        {"cue": "s2", "modo": "slide", "slide": 1, "rotulo": "deck · horários"},
        {"cue": "s3", "modo": "slide", "slide": 2, "rotulo": "deck · altura"},
    ]
    r = aula.produzir(raiz, {"titulo": "Vitrine com deck", "roteiro": ROTEIRO, "cenas": cenas, "formatos": ["16:9"],
                             "avatar": False, "apresentacao": deck},
                      cache_fontes=cache, opcoes_narrar={"palavras_por_segundo": 2.0})
    peca = modelo.carregar(raiz, r["peca_id"])
    assert peca["compoe"] == [deck]
    assert peca["formatos"] == ["16:9"] and [a["formato"] for a in peca["arquivos"] if a["papel"] == "final"] == ["16:9"]
    assert "avatar" not in {a["papel"] for a in peca["arquivos"]}
    assert r["verificacao"]["16:9"]["aprovado"] is True

    # narração com o tipo aula (bloco de parâmetros aula, D-40) e sem ritmo mínimo
    (args, _), = chamadas
    assert args[3] == "aula"
    palavras = len(aula_cues.texto_falado(ROTEIRO).split())
    assert r["narracao"]["fator_ritmo"] == 1.0
    assert abs(r["narracao"]["duracao_s"] - palavras / 2.0) < 0.1, "a narração da aula foi acelerada"

    # os slides da apresentação aparecem na janela da tela, na cena de cada um
    final = modelo.pasta(raiz, r["peca_id"]) / next(a["caminho"] for a in peca["arquivos"] if a["papel"] == "final")
    c = aula_cues.ler(modelo.pasta(raiz, r["peca_id"]) / "midia")["cues"]
    for cue, canal in (("s2", 0), ("s3", 2)):
        t = c[cue] + 1.0
        px = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(final), "-frames:v", "1",
                             "-vf", "crop=20:20:700:500,scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            capture_output=True, check=True).stdout
        assert px[canal] > 150 and max(px) == px[canal], (cue, list(px))


def test_entrada_invalida_nao_cria_peca(ambiente):
    raiz, cache = ambiente
    antes = sorted((raiz / "pecas").rglob("peca.json"))
    with pytest.raises(aula.ErroEntradaAula) as e:
        aula.produzir(raiz, {"titulo": "x", "roteiro": ROTEIRO, "cenas": [{"cue": "s9", "modo": "cena", "titulo": "?"}]})
    assert e.value.campo == "cenas" and "s9" in str(e.value)
    with pytest.raises(aula.ErroEntradaAula) as e:
        aula.produzir(raiz, {"titulo": "x", "roteiro": ROTEIRO, "cenas": CENAS})  # cena de tela sem gravação
    assert e.value.campo == "tela"
    outra = modelo.criar(raiz, tipo="reel", titulo="não é deck", formatos=["9:16"])
    with pytest.raises(aula.ErroEntradaAula) as e:
        aula.produzir(raiz, {"titulo": "x", "roteiro": ROTEIRO, "apresentacao": outra["peca_id"],
                             "cenas": [{"cue": "s1", "modo": "slide", "slide": 1}]})
    assert e.value.campo == "apresentacao"
    depois = sorted((raiz / "pecas").rglob("peca.json"))
    assert len(depois) == len(antes) + 1  # só o reel criado aqui pelo teste
    assert not re.search(r"narracao", " ".join(str(p) for p in (raiz / "pecas").rglob("*.mp3")))
