"""T-10.01: os cinco tipos de peça produzidos pelo CLI, sem chave, numa instalação nova (D-35).

Como uma empresa usaria o núcleo: uma instalação nova montada pela fixture `instalacao` (Alma
fictícia), com `EXPXMEDIA_PROVEDORES_TESTE=1` no `.env` e nenhuma chave de provedor, e cada peça
produzida por `uv run expxmedia-motor produzir ...` em subprocesso, com os templates embarcados.

As sete produções: post único, carrossel, carrossel misto (slide de vídeo), apresentação (HTML e
`--mp4`), reel narrado, reel de página (página servida pelo stub local) e aula.

- Integração: cada produção sai 0, a peça termina `produzida` e todo arquivo listado existe.
- Funcional: todo `peca.json` gerado valida contra o CONTRATO-peca (o motor não tem schema JSON de
  peça; as chaves, os enums e as regras do contrato são conferidos aqui) e tem `producao.capacidades`
  preenchido.

Tudo é produzido uma vez por módulo (a produção com Remotion é lenta) e cada teste confere um tipo.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path, PurePosixPath

import pytest

from expxmedia.ambiente.catalogo import Catalogo
from fixtures.fontes_ficticias import semear_cache
from fixtures.instalacao import montar_instalacao
from stubs.servidor import ServidorStub

pytestmark = pytest.mark.integracao_local

MOTOR = Path(__file__).resolve().parents[2]
TEMPLATES = MOTOR.parent / "templates"
TIMEOUT = 1200  # s por produção; o reel e a aula renderizam em Remotion


def _exemplo(*partes: str) -> dict:
    return json.loads((TEMPLATES.joinpath(*partes) / "exemplo.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- entradas (templates embarcados)

EX_POST = _exemplo("post_unico", "numero-e-frase")
EX_CARROSSEL = _exemplo("carrossel", "editorial")
EX_REEL = _exemplo("reel", "narrado-cartao")
EX_DECK = _exemplo("apresentacao", "padrao")
EX_AULA = _exemplo("aula", "padrao")

POST = {"template": "post_unico-numero-e-frase-86c9ac", "titulo": "Doze perguntas antes do pedido",
        "slides": [copy.deepcopy(EX_POST["slides"][0])],
        "legenda": "Doze perguntas para fazer antes de fechar qualquer pedido. Salve."}
CARROSSEL = {"template": "carrossel-editorial-b74228", "titulo": "Sem atalho",
             "slides": copy.deepcopy(EX_CARROSSEL["slides"]),
             "legenda": "Sem atalho.\n\nFazer bem feito leva tempo. Salve para a próxima vez."}
CARROSSEL_MISTO = {**copy.deepcopy(CARROSSEL), "titulo": "Sem atalho em movimento",
                   "slides": [{"kind": "abertura", "midia": "video", "etiqueta": "Série",
                               "titulo": "Sem atalho, com método", "texto": "Três slides sobre fazer bem feito.",
                               "duracao_s": 4}] + copy.deepcopy(EX_CARROSSEL["slides"][1:])}

# reel de página: o roteiro passa no gate (130 a 180 palavras, CTA dentro, sem algarismo decimal)
CTA_PAGINA = "FORNADA"
FRASES_PAGINA = [
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
    f"Comenta {CTA_PAGINA} que a gente manda os horários.",
]
PARAGRAFO = ("Este parágrafo existe para dar corpo de texto à página de teste, com frases comuns e sem nenhuma "
             "marca, de modo que o texto renderizado passe com folga do piso de caracteres. ")


def _pagina_html() -> bytes:
    secoes = "".join(
        f"<section><h2>Seção número {n} do conteúdo</h2><p>{PARAGRAFO * 5}</p></section>" for n in range(1, 7))
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Página de teste</title><style>"
            "html,body{margin:0;padding:0;background:#ffffff;color:#111111;font:16px/1.4 sans-serif}"
            "section{height:900px;overflow:hidden}h1,h2{margin:0;height:60px}p{margin:0}</style></head><body>"
            f"<h1>Título principal da página de teste</h1>{secoes}</body></html>").encode("utf-8")


def _reel_pagina(url: str) -> dict:
    return {
        "url": url,
        "titulo": "Pão de fermentação natural",
        "roteiro": " ".join(FRASES_PAGINA),
        "cta": CTA_PAGINA,
        "impacto": ["PÃO QUENTE", "TODA MANHÃ"],
        "card_final": ["Comenta {cta}", "para saber o horário"],
        "selo": "Comenta {cta}",
        "legenda": f"Comenta {CTA_PAGINA} e receba os horários da semana.",
        "conteudo": {"gancho": FRASES_PAGINA[0], "gancho_tipo": "processo", "cta_forma": "comentario"},
    }


# ---------------------------------------------------------------- contrato da peça (CONTRATO-peca.md)

CHAVES_PECA = {
    "expxmedia_peca", "peca_id", "slug", "titulo", "tipo", "formatos", "status", "pack", "serie", "template",
    "porta_voz", "oferta", "vaga", "criada_em", "atualizado_em", "motivo_descarte", "conteudo", "slides",
    "compoe", "arquivos", "producao", "publicacoes", "metricas",
}
FORMATOS_POR_TIPO = {
    "post_unico": {"4:5", "1:1", "9:16"},
    "carrossel": {"4:5", "1:1"},
    "reel": {"9:16"},
    "apresentacao": {"16:9"},
    "aula": {"16:9", "9:16"},
}
STATUS = {"ideia", "roteiro", "produzida", "aprovada", "agendada", "publicada", "medida", "descartada"}
MIDIAS = {"imagem", "video"}
PAPEIS = {"final", "slide", "legenda", "roteiro", "audio", "alinhamento", "srt", "avatar", "tela", "previa", "fonte"}
FORMATOS = {"4:5", "1:1", "9:16", "16:9", None}
GANCHO_TIPOS = {"pergunta", "contraste", "numero", "lista", "historia", "processo", "polemica", "outro", None}
CTA_FORMAS = {"comentario", "salvar", "compartilhar", "link", "seguir", "dm", "nenhum", None}
CHAVES_CONTEUDO = {"gancho", "gancho_tipo", "cta", "cta_forma", "legenda", "roteiro"}
CHAVES_PRODUCAO = {"capacidades", "provedores", "segundos", "produzida_em"}
PECA_ID = re.compile(r"^P-\d{8}-[0-9A-F]{4}$")
MES = re.compile(r"^\d{4}-\d{2}$")


def _iso_com_fuso(valor) -> bool:
    if not isinstance(valor, str):
        return False
    try:
        return datetime.fromisoformat(valor).tzinfo is not None
    except ValueError:
        return False


def _relativo_seguro(caminho) -> bool:
    if not isinstance(caminho, str) or not caminho or "\\" in caminho:
        return False
    p = PurePosixPath(caminho)
    return not p.is_absolute() and ".." not in p.parts


def violacoes_do_contrato(peca: dict, pasta: Path) -> list[str]:
    """Tudo o que o `peca.json` descumpre do CONTRATO-peca; lista vazia quando cumpre."""
    v: list[str] = []
    faltam = CHAVES_PECA - set(peca)
    if faltam:
        v.append(f"chaves ausentes: {sorted(faltam)}")
    if peca.get("expxmedia_peca") != 1:
        v.append(f"expxmedia_peca = {peca.get('expxmedia_peca')!r}, esperado 1")
    peca_id = peca.get("peca_id")
    if not isinstance(peca_id, str) or not PECA_ID.fullmatch(peca_id):
        v.append(f"peca_id fora do padrão: {peca_id!r}")
    # pasta <AAAA-MM>/<peca_id>-<slug>/, com o mês de criação
    if pasta.name != f"{peca_id}-{peca.get('slug')}" or not MES.fullmatch(pasta.parent.name):
        v.append(f"pasta fora do padrão <AAAA-MM>/<peca_id>-<slug>: {pasta.parent.name}/{pasta.name}")
    elif _iso_com_fuso(peca.get("criada_em")) and peca["criada_em"][:7] != pasta.parent.name:
        v.append(f"mês da pasta {pasta.parent.name} difere de criada_em {peca['criada_em']}")
    if not isinstance(peca.get("titulo"), str) or not peca["titulo"].strip():
        v.append("titulo vazio")
    if not isinstance(peca.get("pack"), str) or not peca["pack"]:
        v.append("pack é obrigatório")
    tipo = peca.get("tipo")
    if tipo not in FORMATOS_POR_TIPO:
        v.append(f"tipo fora do enum: {tipo!r}")
    formatos = peca.get("formatos")
    if not isinstance(formatos, list) or not formatos:
        v.append("formatos precisa ser lista não vazia")
    elif tipo in FORMATOS_POR_TIPO and not set(formatos) <= FORMATOS_POR_TIPO[tipo]:
        v.append(f"formatos {formatos} não aceitos para {tipo}")
    elif tipo != "aula" and len(formatos) != 1:
        v.append(f"{tipo} tem um formato só, veio {formatos}")
    if peca.get("status") not in STATUS:
        v.append(f"status fora do enum: {peca.get('status')!r}")
    for campo in ("criada_em", "atualizado_em"):
        if not _iso_com_fuso(peca.get(campo)):
            v.append(f"{campo} não é ISO 8601 com fuso: {peca.get(campo)!r}")
    if peca.get("status") != "descartada" and peca.get("motivo_descarte") is not None:
        v.append("motivo_descarte preenchido sem a peça estar descartada")

    conteudo = peca.get("conteudo")
    if not isinstance(conteudo, dict):
        v.append("conteudo precisa ser objeto")
    else:
        if not CHAVES_CONTEUDO <= set(conteudo):
            v.append(f"conteudo sem as chaves {sorted(CHAVES_CONTEUDO - set(conteudo))}")
        if conteudo.get("gancho_tipo") not in GANCHO_TIPOS:
            v.append(f"conteudo.gancho_tipo fora do enum: {conteudo.get('gancho_tipo')!r}")
        if conteudo.get("cta_forma") not in CTA_FORMAS:
            v.append(f"conteudo.cta_forma fora do enum: {conteudo.get('cta_forma')!r}")

    slides = peca.get("slides")
    if not isinstance(slides, list):
        v.append("slides precisa ser lista")
    elif tipo in ("carrossel", "post_unico", "apresentacao"):
        if not slides:
            v.append(f"{tipo} exige slides")
        for i, s in enumerate(slides, 1):
            if s.get("n") != i:
                v.append(f"slide {i}: n = {s.get('n')!r}")
            if not isinstance(s.get("kind"), str) or not s["kind"]:
                v.append(f"slide {i}: kind vazio")
            if s.get("midia") not in MIDIAS:
                v.append(f"slide {i}: midia fora do enum: {s.get('midia')!r}")
            elif s["midia"] == "video":
                if not isinstance(s.get("duracao_s"), (int, float)) or s["duracao_s"] <= 0:
                    v.append(f"slide {i}: vídeo sem duracao_s")
            elif s.get("duracao_s") is not None:
                v.append(f"slide {i}: imagem com duracao_s {s.get('duracao_s')!r}")
            arquivo = s.get("arquivo")
            if tipo != "apresentacao" or arquivo is not None:
                if not _relativo_seguro(arquivo) or not (pasta / arquivo).is_file():
                    v.append(f"slide {i}: arquivo ausente ou fora da pasta: {arquivo!r}")
    elif slides != []:
        v.append(f"{tipo} tem slides: []")
    if not isinstance(peca.get("compoe"), list):
        v.append("compoe precisa ser lista")

    arquivos = peca.get("arquivos")
    if not isinstance(arquivos, list) or not arquivos:
        v.append("arquivos precisa ser lista não vazia")
    else:
        for a in arquivos:
            if set(a) != {"caminho", "papel", "formato"}:
                v.append(f"arquivo com chaves {sorted(a)}")
            if a.get("papel") not in PAPEIS:
                v.append(f"arquivo {a.get('caminho')!r}: papel fora do enum: {a.get('papel')!r}")
            if a.get("formato") not in FORMATOS:
                v.append(f"arquivo {a.get('caminho')!r}: formato fora do enum: {a.get('formato')!r}")
            if not _relativo_seguro(a.get("caminho")):
                v.append(f"arquivo com caminho não relativo (M9): {a.get('caminho')!r}")
            elif not (pasta / a["caminho"]).is_file() or (pasta / a["caminho"]).stat().st_size == 0:
                v.append(f"arquivo listado não existe ou está vazio: {a['caminho']}")

    producao = peca.get("producao")
    if peca.get("status") in ("produzida", "aprovada", "agendada", "publicada", "medida"):
        if not isinstance(producao, dict) or not CHAVES_PRODUCAO <= set(producao):
            v.append(f"producao incompleta: {producao!r}")
        else:
            conhecidas = {c.id for c in Catalogo().capacidades()}
            caps = producao["capacidades"]
            if not isinstance(caps, list) or not caps:
                v.append("producao.capacidades vazio")
            elif not set(caps) <= conhecidas:
                v.append(f"producao.capacidades fora do catálogo: {sorted(set(caps) - conhecidas)}")
            provs = producao["provedores"]
            if not isinstance(provs, dict) or not set(provs) <= set(caps or []):
                v.append(f"producao.provedores com capacidade não usada: {provs!r}")
            if not isinstance(producao["segundos"], (int, float)) or producao["segundos"] < 0:
                v.append(f"producao.segundos inválido: {producao['segundos']!r}")
            if not _iso_com_fuso(producao["produzida_em"]):
                v.append(f"producao.produzida_em não é ISO com fuso: {producao['produzida_em']!r}")
    if peca.get("publicacoes") != []:
        v.append("peça recém-produzida com publicacoes")
    if peca.get("metricas") is not None:
        v.append("peça recém-produzida com metricas")
    return v


# ---------------------------------------------------------------- produção pelo CLI

# nomes de chave que não podem vazar do ambiente de quem roda a suíte para o subprocesso
_PREFIXOS_CHAVE = ("ELEVENLABS_", "HEYGEN_", "OPENROUTER_", "PEXELS_", "EXPXFLOW_", "META_", "PROVEDOR_",
                   "YOUTUBE_", "HIGGSFIELD_", "EXPXMEDIA_")


def _ambiente_limpo(xdg: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(_PREFIXOS_CHAVE)}
    env["XDG_CACHE_HOME"] = str(xdg)
    env["HF_HUB_OFFLINE"] = "1"
    return env


def _produzir(raiz: Path, entradas: Path, env: dict, subcomando: str, nome: str, dados: dict,
              *extra: str) -> dict:
    arquivo = entradas / f"{nome}.json"
    arquivo.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    feito = subprocess.run(
        ["uv", "run", "--project", str(MOTOR), "expxmedia-motor", "produzir", subcomando,
         "--entrada", str(arquivo), *extra, "--raiz", str(raiz)],
        cwd=entradas, capture_output=True, text=True, timeout=TIMEOUT, env=env,
    )
    try:
        saida = json.loads(feito.stdout)
    except json.JSONDecodeError:
        saida = None
    return {"codigo": feito.returncode, "saida": saida, "bruto": (feito.stdout + feito.stderr)[-4000:]}


@pytest.fixture(scope="module")
def producoes(tmp_path_factory):
    for binario in ("uv", "node", "ffmpeg", "ffprobe"):
        if subprocess.run(["which", binario], capture_output=True).returncode != 0:
            pytest.fail(f"binário ausente: {binario}")
    base = tmp_path_factory.mktemp("cinco-tipos")
    raiz = montar_instalacao(base / "instalacao")
    # sem nenhuma chave: só o provedor de teste, pelo .env da instalação
    (raiz / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    xdg = base / "xdg"
    semear_cache(xdg / "expxmedia" / "fontes")
    entradas = base / "entradas"
    entradas.mkdir()
    env = _ambiente_limpo(xdg)

    r: dict[str, dict] = {}
    with ServidorStub() as stub:
        stub.rota("GET", "/pagina", corpo=_pagina_html(), cabecalhos={"Content-Type": "text/html; charset=utf-8"})
        r["post_unico"] = _produzir(raiz, entradas, env, "post", "post", POST)
        r["carrossel"] = _produzir(raiz, entradas, env, "carrossel", "carrossel", CARROSSEL)
        r["carrossel_misto"] = _produzir(raiz, entradas, env, "carrossel", "carrossel-misto", CARROSSEL_MISTO)
        r["apresentacao"] = _produzir(raiz, entradas, env, "apresentacao", "apresentacao", {"deck": EX_DECK}, "--mp4")
        r["reel"] = _produzir(raiz, entradas, env, "reel", "reel", EX_REEL)
        r["reel_pagina"] = _produzir(raiz, entradas, env, "reel-pagina", "reel-pagina",
                                     _reel_pagina(stub.url_de("/pagina")))
        r["aula"] = _produzir(raiz, entradas, env, "aula", "aula", EX_AULA)
        pedidos_pagina = len(stub.requisicoes_de("GET", "/pagina"))
    return {"raiz": raiz, "resultados": r, "pedidos_pagina": pedidos_pagina}


def _peca(producoes, nome: str) -> tuple[dict, dict, Path]:
    r = producoes["resultados"][nome]
    assert r["codigo"] == 0, r["bruto"]
    saida = r["saida"]
    assert saida is not None and saida["ok"] is True, r["bruto"]
    assert not Path(saida["pasta"]).is_absolute() and saida["pasta"].startswith("pecas/"), saida["pasta"]
    pasta = producoes["raiz"] / saida["pasta"]
    peca = json.loads((pasta / "peca.json").read_text(encoding="utf-8"))
    assert peca["peca_id"] == saida["peca_id"]
    return saida, peca, pasta


def _finais(peca: dict) -> dict:
    return {a["formato"]: a["caminho"] for a in peca["arquivos"] if a["papel"] == "final"}


# ---------------------------------------------------------------- integração


def test_sete_producoes_numa_instalacao_nova_terminam_produzidas(producoes):
    ids = set()
    for nome in producoes["resultados"]:
        _, peca, pasta = _peca(producoes, nome)
        assert peca["status"] == "produzida", (nome, peca["status"])
        assert (pasta / "peca.json").is_file()
        for a in peca["arquivos"]:
            assert (pasta / a["caminho"]).is_file() and (pasta / a["caminho"]).stat().st_size > 0, (nome, a)
        ids.add(peca["peca_id"])
    assert len(ids) == 7  # sete peças distintas na mesma instalação
    pecas = sorted((producoes["raiz"] / "pecas").rglob("peca.json"))
    assert len(pecas) == 7
    # nenhuma chave foi usada: o .env da instalação só tem a flag do provedor de teste
    assert (producoes["raiz"] / ".env").read_text(encoding="utf-8") == "EXPXMEDIA_PROVEDORES_TESTE=1\n"


def test_post_unico(producoes):
    _, peca, pasta = _peca(producoes, "post_unico")
    assert (peca["tipo"], peca["formatos"], peca["template"]) == ("post_unico", ["4:5"], POST["template"])
    assert [s["midia"] for s in peca["slides"]] == ["imagem"]
    assert (pasta / peca["slides"][0]["arquivo"]).suffix == ".png"


def test_carrossel(producoes):
    _, peca, pasta = _peca(producoes, "carrossel")
    assert (peca["tipo"], peca["formatos"]) == ("carrossel", ["4:5"])
    assert [s["kind"] for s in peca["slides"]] == [s["kind"] for s in CARROSSEL["slides"]]
    assert {s["midia"] for s in peca["slides"]} == {"imagem"}
    assert "renderizar_motion" not in peca["producao"]["capacidades"]
    assert (pasta / "texto" / "legenda.txt").read_text(encoding="utf-8").startswith("Sem atalho.")


def test_carrossel_misto_tem_slide_de_video(producoes):
    _, peca, pasta = _peca(producoes, "carrossel_misto")
    s0, *resto = peca["slides"]
    assert (s0["midia"], Path(s0["arquivo"]).suffix) == ("video", ".mp4")
    assert abs(s0["duracao_s"] - 4) < 0.2
    assert all(s["midia"] == "imagem" and s["duracao_s"] is None for s in resto)
    assert {"renderizar_html", "renderizar_motion"} <= set(peca["producao"]["capacidades"])


def test_apresentacao_html_e_mp4(producoes):
    saida, peca, pasta = _peca(producoes, "apresentacao")
    assert (peca["tipo"], peca["formatos"]) == ("apresentacao", ["16:9"])
    assert len(peca["slides"]) == len(EX_DECK["slides"])
    finais = [a["caminho"] for a in peca["arquivos"] if a["papel"] == "final"]
    assert "saida/apresentacao.html" in finais
    assert any(c.endswith(".mp4") for c in finais), finais  # --mp4
    assert "renderizar_motion" in peca["producao"]["capacidades"]


def test_reel_narrado_pelo_provedor_de_teste(producoes):
    saida, peca, pasta = _peca(producoes, "reel")
    assert (peca["tipo"], peca["formatos"], peca["slides"]) == ("reel", ["9:16"], [])
    assert _finais(peca) == {"9:16": "saida/final.mp4"}
    assert peca["producao"]["provedores"].get("narrar") == "teste"
    assert saida["verificacao"]["aprovado"] is True, saida["verificacao"]


def test_reel_de_pagina_servida_pelo_stub(producoes):
    saida, peca, pasta = _peca(producoes, "reel_pagina")
    assert producoes["pedidos_pagina"] >= 1  # a página veio do stub local
    assert (peca["tipo"], peca["formatos"], peca["slides"]) == ("reel", ["9:16"], [])
    assert "9:16" in _finais(peca)
    assert {"capturar_pagina", "narrar"} <= set(peca["producao"]["capacidades"])
    assert peca["producao"]["provedores"].get("narrar") == "teste"
    assert saida["verificacao"]["aprovado"] is True, saida["verificacao"]


def test_aula_nos_dois_formatos(producoes):
    saida, peca, pasta = _peca(producoes, "aula")
    assert (peca["tipo"], sorted(peca["formatos"]), peca["slides"]) == ("aula", ["16:9", "9:16"], [])
    finais = _finais(peca)
    assert set(finais) == {"16:9", "9:16"} and all(c.endswith(".mp4") for c in finais.values())
    assert {a["formato"] for a in peca["arquivos"] if a["papel"] == "srt"} == {"16:9", "9:16"}
    assert peca["producao"]["provedores"].get("narrar") == "teste"


# ---------------------------------------------------------------- funcional


def test_todo_peca_json_valida_contra_o_contrato_e_tem_capacidades(producoes):
    for nome in producoes["resultados"]:
        _, peca, pasta = _peca(producoes, nome)
        assert violacoes_do_contrato(peca, pasta) == [], nome
        assert peca["producao"]["capacidades"], nome


def test_o_validador_do_contrato_reprova_peca_fora_do_contrato(producoes):
    """O validador deste teste não é permissivo: cada desvio do contrato vira violação."""
    _, peca, pasta = _peca(producoes, "carrossel")
    desvios = {
        "sem capacidades": lambda p: p["producao"].update(capacidades=[]),
        "tipo fora do enum": lambda p: p.update(tipo="story"),
        "formato 16:9 em carrossel": lambda p: p.update(formatos=["16:9"]),
        "papel fora do enum": lambda p: p["arquivos"][0].update(papel="capa"),
        "caminho absoluto": lambda p: p["arquivos"][0].update(caminho=str(pasta / p["arquivos"][0]["caminho"])),
        "arquivo inexistente": lambda p: p["arquivos"].append({"caminho": "saida/nao.png", "papel": "final",
                                                                "formato": "4:5"}),
        "imagem com duração": lambda p: p["slides"][0].update(duracao_s=3),
        "gancho fora do enum": lambda p: p["conteudo"].update(gancho_tipo="susto"),
        "sem pack": lambda p: p.pop("pack"),
        "data sem fuso": lambda p: p.update(atualizado_em="2026-09-25T10:00:00"),
        "capacidade fora do catálogo": lambda p: p["producao"].update(capacidades=["teletransportar"]),
    }
    for nome, aplicar in desvios.items():
        copia = copy.deepcopy(peca)
        aplicar(copia)
        assert violacoes_do_contrato(copia, pasta), nome
