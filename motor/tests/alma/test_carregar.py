"""T-02.10: carga da Alma, portão, tokens CSS e fontes (CONTRATO-alma, CONTRATO-template, D-21)."""
import json
import re
from pathlib import Path

import pytest

from expxmedia.alma import carregar, fontes, tokens
from expxmedia.alma.schema import ErroAlmaRejeitada
from stubs.servidor import servidor_stub  # noqa: F401  (fixture)

PAPEIS = ("fundo", "fundo_alt", "texto", "texto_inverso", "apoio", "destaque", "destaque_2", "positivo", "negativo")
WOFF2_FALSO = b"wOF2" + bytes(range(60))


def _alma(raiz):
    return json.loads((raiz / "alma" / "alma.json").read_text(encoding="utf-8"))


def _gravar_alma(raiz, dados):
    (raiz / "alma" / "alma.json").write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def _css_google(url_base, familia, arquivo):
    return (
        "/* cyrillic */\n"
        "@font-face {\n"
        f"  font-family: '{familia}';\n  font-style: normal;\n  font-weight: 100 900;\n  font-display: swap;\n"
        f"  src: url({url_base}/s/cirilico.woff2) format('woff2');\n"
        "  unicode-range: U+0301, U+0400-045F;\n}\n"
        "/* latin */\n"
        "@font-face {\n"
        f"  font-family: '{familia}';\n  font-style: normal;\n  font-weight: 100 900;\n  font-display: swap;\n"
        f"  src: url({url_base}/s/{arquivo}) format('woff2');\n"
        "  unicode-range: U+0000-00FF, U+0131;\n}\n"
    )


# ---------------------------------------------------------------- integração


def test_fonte_titulo_do_google_vai_para_o_cache_e_o_font_face_aponta_para_ele(instalacao, servidor_stub, tmp_path):
    stub = servidor_stub
    stub.rota("GET", "/css2", corpo=_css_google(stub.url, "Fraunces", "fraunces-latin.woff2"),
              cabecalhos={"Content-Type": "text/css; charset=utf-8"})
    stub.rota("GET", "/s/fraunces-latin.woff2", corpo=WOFF2_FALSO)
    cache = tmp_path / "cache-fontes"

    fonte = fontes.resolver_fonte(_alma(instalacao), "titulo", raiz=instalacao, cache=cache, url_base=stub.url)

    assert fonte.familia == "Fraunces"
    assert fonte.origem == "google"
    assert fonte.aviso is None
    # só o subconjunto latino (pt-BR) foi baixado, para dentro do cache
    assert [a.name for a in fonte.arquivos] == ["fraunces-latin.woff2"]
    arquivo = fonte.arquivos[0]
    assert arquivo.is_file() and arquivo.read_bytes() == WOFF2_FALSO
    assert cache.resolve() in arquivo.resolve().parents
    # o @font-face aponta para o arquivo local, nunca para a rede
    assert "font-family: 'Fraunces'" in fonte.css
    assert f"url('{arquivo.resolve().as_uri()}')" in fonte.css
    assert stub.url not in fonte.css and "cirilico" not in fonte.css
    pedido = stub.requisicoes_de("GET", "/css2")[0]
    assert pedido.query["family"] == ["Fraunces:wght@100..900"]
    assert "Chrome" in pedido.cabecalhos["User-Agent"]  # sem UA moderno o Google não serve woff2

    # segunda resolução sai do cache, sem rede
    stub.parar()
    de_novo = fontes.resolver_fonte(_alma(instalacao), "titulo", raiz=instalacao, cache=cache, url_base=stub.url)
    assert de_novo.aviso is None and de_novo.arquivos == fonte.arquivos and de_novo.css == fonte.css


def test_familia_estatica_cai_para_pesos_fixos(instalacao, servidor_stub, tmp_path):
    stub = servidor_stub
    stub.rota("GET", "/css2", sequencia=[
        {"status": 400, "corpo": "Invalid selector"},
        {"corpo": _css_google(stub.url, "Nunito Sans", "nunito.woff2")},
    ])
    stub.rota("GET", "/s/nunito.woff2", corpo=WOFF2_FALSO)
    fonte = fontes.resolver_fonte(_alma(instalacao), "texto", raiz=instalacao, cache=tmp_path / "c", url_base=stub.url)
    assert fonte.aviso is None and fonte.familia == "Nunito Sans"
    familias = [r.query["family"][0] for r in stub.requisicoes_de("GET", "/css2")]
    assert familias == ["Nunito Sans:wght@100..900", "Nunito Sans:wght@400;700"]


def test_sem_google_fonts_usa_inter_embarcada_com_aviso(instalacao, servidor_stub, tmp_path):
    servidor_stub.rota("GET", "/css2", status=500, corpo="erro")
    fonte = fontes.resolver_fonte(_alma(instalacao), "titulo", raiz=instalacao, cache=tmp_path / "c",
                                  url_base=servidor_stub.url)
    assert fonte.origem == "embarcada"
    assert fonte.familia == "Inter"
    assert "Fraunces" in fonte.aviso
    assert fonte.pedida == "Fraunces"  # a família pedida viaja junto, para o aviso fonte_substituida
    assert {a.name for a in fonte.arquivos} == {"inter-latin-400-normal.woff2", "inter-latin-700-normal.woff2"}
    assert all(a.is_file() for a in fonte.arquivos)
    assert "font-family: 'Inter'" in fonte.css and "font-weight: 700" in fonte.css


def test_fonte_local_relativa_a_raiz(instalacao, tmp_path):
    alma = _alma(instalacao)
    (instalacao / "alma" / "assets" / "minha.ttf").write_bytes(b"\x00\x01\x00\x00fonte")
    alma["visual"]["fontes"]["texto"] = {"familia": "Minha Fonte", "origem": "local", "arquivo": "alma/assets/minha.ttf"}
    fonte = fontes.resolver_fonte(alma, "texto", raiz=instalacao, cache=tmp_path / "c")
    assert fonte.origem == "local" and fonte.aviso is None
    assert fonte.arquivos == [(instalacao / "alma" / "assets" / "minha.ttf").resolve()]
    assert "format('truetype')" in fonte.css and "font-family: 'Minha Fonte'" in fonte.css


def test_css_fontes_junta_titulo_texto_e_inter(instalacao, servidor_stub, tmp_path):
    stub = servidor_stub
    stub.rota("GET", "/css2", corpo=_css_google(stub.url, "Qualquer", "q.woff2"))
    stub.rota("GET", "/s/q.woff2", corpo=WOFF2_FALSO)
    css, resolvidas = fontes.css_fontes(_alma(instalacao), raiz=instalacao, cache=tmp_path / "c", url_base=stub.url)
    assert [r.papel for r in resolvidas] == ["titulo", "texto"]
    assert css.count("font-family: 'Inter'") == 2  # a reserva embarcada vai sempre junto


# ---------------------------------------------------------------- funcional


def test_tokens_css_da_alma_ficticia(instalacao):
    alma = _alma(instalacao)
    css = tokens.tokens_css(alma)
    valores = dict(re.findall(r"(--alma-[a-z0-9_-]+):\s*([^;]+);", css))
    cores = alma["visual"]["cores"]
    for papel in PAPEIS:
        assert valores[f"--alma-{papel}"] == cores[papel]  # --alma-<papel>, literal do contrato
    assert len([v for v in valores if not v.startswith("--alma-fonte")]) == 9
    assert valores["--alma-fonte-titulo"] == "'Fraunces', 'Inter', sans-serif"
    assert valores["--alma-fonte-texto"] == "'Nunito Sans', 'Inter', sans-serif"
    assert css.lstrip().startswith(":root {")
    # a família resolvida substitui a da Alma na pilha (fonte que caiu na reserva não é nomeada, D-21)
    trocado = dict(re.findall(r"(--alma-[a-z0-9_-]+):\s*([^;]+);", tokens.tokens_css(alma, familias={"titulo": "Inter"})))
    assert trocado["--alma-fonte-titulo"] == "'Inter', sans-serif"
    assert trocado["--alma-fonte-texto"] == "'Nunito Sans', 'Inter', sans-serif"


def test_tokens_css_recusa_papel_nulo(instalacao):
    alma = _alma(instalacao)
    alma["visual"]["cores"]["destaque"] = None
    with pytest.raises(tokens.ErroTokens, match="destaque"):
        tokens.tokens_css(alma)


def test_portao_aberto_com_alma_confirmada_e_env(instalacao):
    p = carregar.portao(instalacao)
    assert p == {"aberto": True, "alma_existe": True, "alma_confirmada": True, "env_existe": True,
                 "encaminhar": None, "motivo": None}


def test_portao_fechado_sem_confirmada_em(instalacao):
    alma = _alma(instalacao)
    alma["confirmada_em"] = None
    _gravar_alma(instalacao, alma)
    p = carregar.portao(instalacao)
    assert p["aberto"] is False
    assert p["alma_existe"] is True and p["alma_confirmada"] is False
    assert p["encaminhar"] == "/expxmedia:alma"


def test_portao_sem_alma_e_sem_env(instalacao):
    (instalacao / ".env").unlink()
    p = carregar.portao(instalacao)
    assert p["aberto"] is False and p["env_existe"] is False and p["encaminhar"] == "/expxmedia:ambiente"
    (instalacao / "alma" / "alma.json").unlink()
    p = carregar.portao(instalacao)
    assert p["alma_existe"] is False and p["encaminhar"] == "/expxmedia:alma"


def test_portao_alma_ilegivel_fica_fechado(instalacao):
    (instalacao / "alma" / "alma.json").write_text("{quebrado", encoding="utf-8")
    p = carregar.portao(instalacao)
    assert p["aberto"] is False and p["alma_confirmada"] is False and "JSON" in p["motivo"]


def test_carregar_devolve_dados_e_violacoes(instalacao):
    alma = carregar.carregar(instalacao)
    assert alma.dados["empresa"]["fuso"] == "America/Sao_Paulo"
    assert alma.violacoes == []
    assert alma.confirmada is True
    dados = _alma(instalacao)
    del dados["visual"]["cores"]["apoio"]
    _gravar_alma(instalacao, dados)
    assert [v["caminho"] for v in carregar.carregar(instalacao).violacoes] == ["visual.cores.apoio"]
    dados["expxmedia_alma"] = 9
    _gravar_alma(instalacao, dados)
    with pytest.raises(ErroAlmaRejeitada):
        carregar.carregar(instalacao)
