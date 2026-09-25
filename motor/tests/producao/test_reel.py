"""T-05.06: produção do reel narrado em Remotion (D-41, D-49).

Integração: um roteiro de 150 palavras narrado pelo provedor de teste a 3,5 palavras por segundo
(EXPXMEDIA_PROVEDORES_TESTE=1, sinal audível sintético) é montado, renderizado no template embarcado com a
Alma fictícia, normalizado e sai com MP4 de 43 a 45 s aprovado nas 11 checagens do perfil `reel`, e a peça
fica `produzida` — narrando uma vez só.

Funcional: um roteiro de 100 palavras é recusado pelo gate antes de narrar e nenhuma chamada ao provedor
acontece; âncora que não casa com o roteiro é erro de entrada antes de criar a peça; a trilha que repete a
de outra peça é transposta; som de item de lista sem o item sai; os cartões da legenda cobrem o vídeo.
"""
from __future__ import annotations

import json

import pytest

from expxmedia.narrar import base as narrar_base
from expxmedia.nucleo import arquivos, rastro, tempo
from expxmedia.peca import modelo
from expxmedia.producao import reel
from expxmedia.video import verificar
from fixtures.fontes_ficticias import semear_cache

CTA = "RESPOSTA"
FRASES = [
    "Toda loja pequena perde vendas no mesmo ponto da conversa.",
    "O cliente pergunta o preço e some sem dar resposta.",
    "Na maioria das vezes ele só ficou com uma dúvida.",
    "Quem responde em cinco minutos vende três vezes mais.",
    "O segredo está em três respostas prontas para perguntas comuns.",
    "A primeira explica o preço com o que está incluso.",
    "A segunda mostra o prazo de entrega sem rodeio nenhum.",
    "A terceira convida a pessoa para fechar o pedido hoje.",
    "Sem roteiro cada atendente inventa uma resposta diferente todo dia.",
    "Com roteiro a equipe inteira fala a mesma língua sempre.",
    "Resposta rápida não é pressa e sim respeito pelo cliente.",
    "Quem se sente atendido volta e ainda indica para os amigos.",
    "Você pode montar as suas três respostas ainda nesta semana.",
    "Eu preparei um modelo simples para você copiar e adaptar.",
    f"Comenta {CTA} aqui embaixo que eu te mando o modelo.",
]
ROTEIRO = " ".join(FRASES)
CENAS = [
    {"kind": "abertura", "ancora": "Toda loja pequena", "etiqueta": ["VENDA PERDIDA", "NO MESMO PONTO"],
     "titulo": "O cliente pergunta e some", "apoio": "Quase sempre ficou só uma dúvida"},
    {"kind": "numero", "ancora": "Quem responde em", "etiqueta": ["CINCO MINUTOS", "FAZEM DIFERENÇA"],
     "valor": "3x", "texto": "mais vendas para quem responde rápido"},
    {"kind": "lista", "ancora": "O segredo está", "etiqueta": ["TRÊS RESPOSTAS", "PRONTAS"],
     "titulo": "As três respostas", "itens": ["Preço e o que inclui", "Prazo sem rodeio", "Convite para fechar"]},
    {"kind": "contraste", "ancora": "Sem roteiro cada", "etiqueta": ["SEM ROTEIRO", "E COM ROTEIRO"],
     "rotulo_a": "Sem roteiro", "texto_a": "Cada um responde de um jeito",
     "rotulo_b": "Com roteiro", "texto_b": "A equipe fala a mesma língua"},
    {"kind": "frase", "ancora": "Resposta rápida não", "etiqueta": ["RESPOSTA RÁPIDA", "É RESPEITO"],
     "texto": "Resposta rápida não é pressa. É respeito pelo cliente.", "marca": "respeito pelo cliente"},
    {"kind": "cta", "ancora": "Eu preparei um", "etiqueta": ["O MODELO", "PARA COPIAR"],
     "texto": f"Comenta {CTA}", "apoio": "e receba o modelo das três respostas"},
]


def _entrada(**muda):
    dados = {
        "titulo": "Três respostas prontas que vendem",
        "roteiro": ROTEIRO,
        "cta": CTA,
        "cenas": json.loads(json.dumps(CENAS)),
        "legenda": f"Três respostas prontas mudam o atendimento. Comenta {CTA} e receba o modelo.",
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

    monkeypatch.setattr(reel.narrar_base, "narrar", contado)
    return chamadas


@pytest.fixture
def ambiente(instalacao, tmp_path, monkeypatch):
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    return instalacao, semear_cache(tmp_path / "fontes")


def _eventos(raiz):
    eventos, corrompidas = rastro.ler(raiz, tempo.agora(raiz).strftime("%Y-%m"))
    assert corrompidas == 0
    return eventos


# ------------------------------------------------------------------ integração


@pytest.mark.integracao_local
def test_reel_de_150_palavras_a_3_5_pps_sai_com_43_a_45_s_aprovado(ambiente, monkeypatch, requer_binario):
    for b in ("node", "ffmpeg", "ffprobe"):
        requer_binario(b)
    raiz, cache = ambiente
    assert len(ROTEIRO.split()) == 150
    chamadas = _contar_narrar(monkeypatch)
    r = reel.produzir(raiz, _entrada(), cache_fontes=cache, opcoes_narrar={"palavras_por_segundo": 3.5})

    assert len(chamadas) == 1  # narra uma vez
    assert r["status"] == "produzida"
    assert r["verificacao"] == {"aprovado": True, "perfil": "reel", "achados": [], "avisos": []}
    assert 43.0 <= r["duracao"] <= 45.0, r["duracao"]
    assert r["narracao"]["palavras"] == 150 and r["narracao"]["provedor"] == "teste"
    # 150 palavras a 3,5 por segundo: ceil(3,5 × 1,1) = 4 palavras por bloco (a regra da legenda do reel)
    assert r["legenda"]["palavras_por_bloco"] == 4 and r["legenda"]["cta"] == CTA

    pasta = modelo.pasta(raiz, r["peca_id"])
    midia, final = pasta / "midia", pasta / "saida" / "final.mp4"
    art = verificar.Artefatos(caps_txt=midia / "caps.txt", legendas=midia / "legendas.json",
                              alinhamento=midia / "alinhamento.json", roteiro=pasta / "texto" / "roteiro.txt")
    refeita = verificar.verificar(final, "reel", art)
    assert refeita["aprovado"], refeita["achados"]
    lufs, pico = verificar.ffmpeg.medir(final)
    assert abs(lufs + 14) <= 1 and pico <= -1.0

    timeline = arquivos.ler_json(midia / "timeline.json")
    assert [c["kind"] for c in timeline["cenas"]] == [c["kind"] for c in CENAS]
    assert abs(timeline["totalFrames"] / 30 - r["duracao"]) < 0.1
    # cauda de 1,4 s depois da última palavra; origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:94
    fim_fala = max(arquivos.ler_json(midia / "alinhamento.json")["character_end_times_seconds"])
    assert timeline["totalFrames"] == round((fim_fala + 1.4) * 30)
    assert len(list((midia / "caps").glob("[0-9][0-9][0-9].png"))) == len(timeline["blocos"])

    peca = modelo.carregar(raiz, r["peca_id"])
    assert peca["template"] == reel.TEMPLATE_PADRAO and peca["formatos"] == ["9:16"] and peca["slides"] == []
    assert peca["producao"]["provedores"] == {"narrar": "teste", "renderizar_motion": "remotion",
                                             "legendar": "local", "editar_video": "ffmpeg"}
    papeis = {a["caminho"]: a["papel"] for a in peca["arquivos"]}
    assert papeis["saida/final.mp4"] == "final" and papeis["saida/final.srt"] == "srt"
    assert papeis["midia/alinhamento.json"] == "alinhamento" and papeis["midia/narracao.mp3"] == "audio"
    assert peca["conteudo"]["roteiro"] == "texto/roteiro.txt" and peca["conteudo"]["legenda"] == "texto/legenda.txt"
    tipos = [ev["evento"] for ev in _eventos(raiz) if ev.get("peca_id") == r["peca_id"]]
    assert "geracao_concluida" in tipos and "geracao_falhou" not in tipos


# ------------------------------------------------------------------ funcional


def test_roteiro_de_100_palavras_recusado_antes_de_narrar(ambiente, monkeypatch):
    raiz, cache = ambiente
    chamadas = _contar_narrar(monkeypatch)
    curto = " ".join(ROTEIRO.split()[:90]) + f" Comenta {CTA} aqui embaixo que eu te mando o modelo."
    assert len(curto.split()) == 100
    cenas = CENAS[:4] + [{**CENAS[-1], "ancora": "Comenta"}]
    with pytest.raises(reel.ErroRoteiroReprovado) as erro:
        reel.produzir(raiz, _entrada(roteiro=curto, cenas=cenas), cache_fontes=cache)
    assert chamadas == []  # nenhuma chamada ao provedor
    assert "100 palavras" in str(erro.value) and "130-180" in str(erro.value)
    assert [a["checagem"] for a in erro.value.achados] == ["palavras"]
    pasta = modelo.pasta(raiz, erro.value.peca_id)
    assert not (pasta / "midia" / narrar_base.ARQUIVO_AUDIO).exists()
    assert modelo.carregar(raiz, erro.value.peca_id)["status"] == "roteiro"
    assert "geracao_falhou" in [ev["evento"] for ev in _eventos(raiz) if ev.get("peca_id") == erro.value.peca_id]


def test_ancora_fora_do_roteiro_e_kind_desconhecido_nao_criam_peca(ambiente, monkeypatch):
    raiz, cache = ambiente
    chamadas = _contar_narrar(monkeypatch)
    cenas = json.loads(json.dumps(CENAS))
    cenas[2]["ancora"] = "palavras que não existem"
    with pytest.raises(reel.ErroEntradaReel, match="cena 3 \\(lista\\).*não casou"):
        reel.produzir(raiz, _entrada(cenas=cenas), cache_fontes=cache)
    fora_de_ordem = json.loads(json.dumps(CENAS))
    fora_de_ordem[1]["ancora"], fora_de_ordem[2]["ancora"] = CENAS[2]["ancora"], CENAS[1]["ancora"]
    with pytest.raises(reel.ErroEntradaReel, match="não casou"):
        reel.produzir(raiz, _entrada(cenas=fora_de_ordem), cache_fontes=cache)
    with pytest.raises(reel.ErroEntradaReel, match="kind 'grafico' não existe"):
        reel.produzir(raiz, _entrada(cenas=[{**CENAS[0], "kind": "grafico"}]), cache_fontes=cache)
    longo = json.loads(json.dumps(CENAS))
    longo[1]["valor"] = "123456789"
    with pytest.raises(reel.ErroEntradaReel, match="9 caracteres, o template aguenta 8"):
        reel.produzir(raiz, _entrada(cenas=longo), cache_fontes=cache)
    assert chamadas == [] and list((raiz / "pecas").rglob("peca.json")) == []


def test_trilha_repetida_e_transposta_e_a_pedida_vai_como_veio():
    esqueleto = arquivos.ler_json(reel.achar_template(".", None)[0] / "cenas.json")
    base = esqueleto["trilha"]
    outras = [{"reel": "P-1", "trilha": base}]
    nova = reel._escolher_trilha(base, outras, explicita=False)
    assert nova["bpm"] == base["bpm"] and nova["acordes"] != base["acordes"]
    assert nova["acordes"][0][0] == round(base["acordes"][0][0] * 2 ** (1 / 12), 2)  # um semitom acima
    assert reel._escolher_trilha(base, outras + [{"reel": "P-2", "trilha": nova}], explicita=False)["acordes"] \
        == reel._transpor(base, 2)["acordes"]
    assert reel._escolher_trilha(base, [], explicita=False) is base
    assert reel._escolher_trilha(base, outras, explicita=True) is base


def test_cenas_da_peca_herdam_eventos_do_kind_e_som_de_item_ausente_sai():
    esqueleto = arquivos.ler_json(reel.achar_template(".", None)[0] / "cenas.json")
    cenas = reel.montar_cenas(esqueleto, CENAS, palavras_por_bloco=4, trilha=esqueleto["trilha"])
    assert cenas["legenda"] == {"palavras_por_bloco": 4} and cenas["cauda_s"] == 1.4
    lista = next(c for c in cenas["cenas"] if c["kind"] == "lista")
    assert lista["ev"] == esqueleto["kinds"]["lista"]["ev"]
    assert [s[0] for s in lista["sons"]] == ["i0", "i1", "i2"]  # 3 itens: o tique do i3 sai
    assert lista["itens"] == CENAS[2]["itens"] and lista["ancora"] == CENAS[2]["ancora"]
    assert [c["id"] for c in cenas["cenas"]][:2] == ["c01-abertura", "c02-numero"]


def test_cartoes_da_legenda_cobrem_o_video_ate_o_ultimo_quadro():
    timeline = {"fps": 30, "totalFrames": 200,
                "blocos": [[{"w": "a", "f0": 1, "f1": 5}], [{"w": "b", "f0": 40, "f1": 50}], [{"w": "c", "f0": 90, "f1": 99}]]}
    assert reel.cartoes_da_legenda(timeline) == [(0, 38), (38, 88), (88, 200)]
