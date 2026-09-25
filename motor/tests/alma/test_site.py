"""T-09.02: extração do site para a proposta de Alma (CONTRATO-alma, "Como a Alma é criada").

O site fictício de tests/fixtures/site-ficticio/ é servido pelo stub HTTP local. A extração é
determinística: o que não tem evidência no site sai null (ou lista vazia) e entra em `pendencias`;
o que tem entra com `origens[campo] = "site"`. Tom de voz nunca vem do site.
"""
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from expxmedia.alma import schema, site
from stubs.servidor import servidor_stub  # noqa: F401  (fixture)

SITE = Path(__file__).resolve().parents[1] / "fixtures" / "site-ficticio"
HTML = {"Content-Type": "text/html; charset=utf-8"}
CSS = {"Content-Type": "text/css; charset=utf-8"}


def _servir_ficticio(stub):
    for rota, arquivo in (("/", "index.html"), ("/sobre.html", "sobre.html"), ("/produtos.html", "produtos.html"),
                          ("/contato.html", "contato.html")):
        stub.rota("GET", rota, corpo=(SITE / arquivo).read_bytes(), cabecalhos=HTML)
    stub.rota("GET", "/estilo.css", corpo=(SITE / "estilo.css").read_bytes(), cabecalhos=CSS)
    stub.rota("GET", "/assets/logo.svg", corpo=(SITE / "assets" / "logo.svg").read_bytes(),
              cabecalhos={"Content-Type": "image/svg+xml"})


def _folhas(dados, prefixo=""):
    """(caminho, valor) de cada folha do JSON; lista vazia conta como folha."""
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            yield from _folhas(valor, f"{prefixo}.{chave}" if prefixo else chave)
    elif isinstance(dados, list) and dados and all(isinstance(i, dict) for i in dados):
        return  # listas de objetos (ofertas, canais) têm pendências próprias
    else:
        yield prefixo, dados


@pytest.fixture
def raiz(tmp_path):
    pasta = tmp_path / "instalacao"
    pasta.mkdir()
    return pasta


# ---------------------------------------------------------------- integração


def test_extrai_o_site_ficticio_baixa_o_logo_e_propoe_cores_nos_papeis(servidor_stub, raiz):
    _servir_ficticio(servidor_stub)
    r = site.extrair(servidor_stub.url + "/", raiz)
    p = r["proposta"]

    # logo baixado para alma/assets, byte a byte, com caminho relativo (M9)
    assert p["visual"]["logo"]["principal"] == "alma/assets/logo.svg"
    assert (raiz / "alma" / "assets" / "logo.svg").read_bytes() == (SITE / "assets" / "logo.svg").read_bytes()
    assert p["visual"]["logo"]["negativo"] is None and "visual.logo.negativo" in p["pendencias"]

    cores = p["visual"]["cores"]
    assert cores["destaque"] == "#2F7D4F"
    assert cores["destaque_2"] == "#D9467A"
    assert cores["fundo"] == "#FFFDF8"
    assert cores["texto"] == "#1F2A24"
    assert cores["texto_inverso"] == "#FFFFFF"
    for papel in ("fundo_alt", "apoio", "positivo", "negativo"):
        assert cores[papel] is None, papel
        assert f"visual.cores.{papel}" in p["pendencias"]
    for papel in ("destaque", "destaque_2", "fundo", "texto", "texto_inverso"):
        assert p["origens"][f"visual.cores.{papel}"] == "site"
    # cor em comentário de CSS e em <script> não é evidência
    vistas = {c["cor"] for c in r["evidencias"]["cores"]}
    assert "#ABCDEF" not in vistas and "#123456" not in vistas

    assert p["visual"]["fontes"]["titulo"] == {"familia": "Playfair Display", "origem": "google"}
    assert p["visual"]["fontes"]["texto"] == {"familia": "Work Sans", "origem": "google"}

    empresa = p["empresa"]
    assert empresa["nome"] == "Floricultura Jardim Aberto"
    assert empresa["descricao_curta"] == "Floricultura de bairro que monta buquês com flores do campo e entrega no mesmo dia."
    assert empresa["idioma"] == "pt-BR"
    assert empresa["site"] == servidor_stub.url
    assert p["origens"]["empresa.nome"] == "site"

    canais = {c["canal"]: c for c in p["canais"]}
    assert canais["instagram"] == {"canal": "instagram", "identificador": "@jardimaberto.flores",
                                   "url": "https://www.instagram.com/jardimaberto.flores/"}
    assert canais["youtube"]["identificador"] == "@jardimaberto"
    assert canais["facebook"]["identificador"] == "jardimaberto.flores"

    ofertas = {o["nome"]: o for o in p["ofertas"]}
    assert set(ofertas) == {"Buquê do dia", "Assinatura semanal de flores", "Oficina de arranjos"}
    assert ofertas["Assinatura semanal de flores"]["tipo"] == "assinatura"
    assert ofertas["Assinatura semanal de flores"]["url"] == "https://jardimaberto.example/assinatura"
    assert ofertas["Buquê do dia"]["tipo"] == "produto"
    assert ofertas["Buquê do dia"]["url"] == servidor_stub.url + "/produtos/buque-do-dia.html"
    assert ofertas["Buquê do dia"]["descricao"] == "Flores da estação escolhidas pela florista, montadas na hora."
    assert ofertas["Buquê do dia"]["id"] == "buque-do-dia"
    assert ofertas["Oficina de arranjos"]["url"] is None
    assert all(o["principal"] is False for o in p["ofertas"]) and "ofertas.principal" in p["pendencias"]

    papeis = {pg["papel"]: pg for pg in r["paginas"]}
    assert set(papeis) == {"inicio", "sobre", "produtos", "contato"}
    assert "duas irmãs" in papeis["sobre"]["texto"]
    assert p["fontes"] == [pg["url"] for pg in r["paginas"]]
    assert p["metodo"] == "site" and p["confirmada_em"] is None

    # só o próprio site foi lido: nada de Google Fonts, parceiro externo ou favicon
    caminhos = {req.caminho for req in servidor_stub.requisicoes}
    assert caminhos == {"/", "/sobre.html", "/produtos.html", "/contato.html", "/estilo.css", "/assets/logo.svg"}


def test_logo_raster_da_as_cores_dominantes_quando_o_css_nao_nomeia(servidor_stub, raiz):
    imagem = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
    for x in range(40):
        for y in range(20):
            if x < 28:
                imagem.putpixel((x, y), (0x1E, 0x5E, 0xFF, 255))  # maior área: destaque
            elif x < 36:
                imagem.putpixel((x, y), (0xF2, 0xB3, 0x3D, 255))  # segunda cor
    buffer = io.BytesIO()
    imagem.save(buffer, "PNG")
    servidor_stub.rota("GET", "/", cabecalhos=HTML, corpo=(
        "<html lang='en'><head><title>Oficina Norte - consertos</title>"
        "<style>body { background: #FFFFFF; color: #222222 }</style></head>"
        "<body><img id='site-logo' src='/img/marca.png' alt='Oficina Norte'></body></html>"))
    servidor_stub.rota("GET", "/img/marca.png", corpo=buffer.getvalue(), cabecalhos={"Content-Type": "image/png"})
    (raiz / "alma" / "assets").mkdir(parents=True)
    (raiz / "alma" / "assets" / "logo.png").write_bytes(b"logo ja confirmado")

    p = site.extrair(servidor_stub.url, raiz)["proposta"]

    assert p["visual"]["cores"]["destaque"] == "#1E5EFF"
    assert p["visual"]["cores"]["destaque_2"] == "#F2B33D"
    assert p["visual"]["cores"]["fundo"] == "#FFFFFF" and p["visual"]["cores"]["texto"] == "#222222"
    # logo existente nunca é sobrescrito
    assert (raiz / "alma" / "assets" / "logo.png").read_bytes() == b"logo ja confirmado"
    assert p["visual"]["logo"]["principal"] == "alma/assets/logo-site.png"
    assert (raiz / "alma" / "assets" / "logo-site.png").read_bytes() == buffer.getvalue()
    assert p["empresa"]["nome"] == "Oficina Norte" and p["empresa"]["idioma"] == "en"


# ---------------------------------------------------------------- funcional


def test_campos_sem_evidencia_saem_null_e_entram_em_pendencias(servidor_stub, raiz):
    servidor_stub.rota("GET", "/", cabecalhos=HTML, corpo="<html><head><title>Casa Azul</title></head><body><p>Olá.</p></body></html>")
    r = site.extrair(servidor_stub.url + "/", raiz)
    p = r["proposta"]

    assert p["empresa"]["nome"] == "Casa Azul"
    assert p["empresa"]["descricao_curta"] is None
    assert p["empresa"]["idioma"] is None
    assert all(v is None for v in p["visual"]["cores"].values())
    assert p["visual"]["logo"]["principal"] is None
    assert p["visual"]["fontes"]["titulo"] == {"familia": None, "origem": None}
    assert p["ofertas"] == [] and p["canais"] == [] and p["porta_vozes"] == []
    # nada inventado sobre voz: tom é sempre inferido pela conversa, nunca pelo extrator
    assert p["voz"]["tom"] == [] and p["voz"]["tratamento"] is None and p["voz"]["formalidade"] is None
    assert not (raiz / "alma" / "assets").exists() or not any((raiz / "alma" / "assets").iterdir())

    # toda folha null ou lista vazia está nas pendências; só o que veio do site está em origens
    for caminho, valor in _folhas(p):
        if caminho in {"confirmada_em", "pendencias"} or caminho.startswith("origens"):
            continue
        if valor is None or valor == []:
            assert caminho in p["pendencias"], caminho
            assert caminho not in p["origens"], caminho
    for caminho in ("ofertas", "canais", "porta_vozes", "empresa.fuso", "publico.principal", "voz.tom",
                    "visual.cores.destaque", "visual.logo.principal", "cta.padrao"):
        assert caminho in p["pendencias"], caminho
    assert p["origens"] == {"empresa.nome": "site", "empresa.site": "site"}


def test_proposta_cumpre_o_contrato_exceto_o_fuso(servidor_stub, raiz):
    _servir_ficticio(servidor_stub)
    p = site.extrair(servidor_stub.url, raiz)["proposta"]
    violacoes = schema.validar(p)
    # o site não diz o fuso da empresa: é a única chave que o contrato exige preenchida
    assert [v["caminho"] for v in violacoes] == ["empresa.fuso"]
    assert list(p)[0] == "expxmedia_alma"
    json.dumps(p)  # serializável


def test_site_fora_do_ar_levanta_erro_com_a_url(servidor_stub, raiz):
    with pytest.raises(site.ErroSite, match="404"):
        site.extrair(servidor_stub.url + "/", raiz)


def test_url_invalida_levanta_erro(raiz):
    with pytest.raises(site.ErroSite):
        site.extrair("ftp://nada.example", raiz)
