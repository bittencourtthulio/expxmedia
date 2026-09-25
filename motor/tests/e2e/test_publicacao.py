"""T-10.02: publicação em dry-run de um carrossel e de um reel pelos dois provedores, contra stubs (D-07, D-15).

Tudo pelo CLI, em subprocesso, numa instalação nova montada pela fixture `instalacao` (Alma fictícia):
o carrossel e o reel são produzidos por `produzir carrossel` e `produzir reel` com os templates
embarcados e o provedor de teste, e publicados por `publicar --peca ID` (sem `--confirmar`, o
dry-run). As chaves são falsas:

- Expx Flow: `EXPXFLOW_*`, com `EXPXFLOW_BASE_URL` apontando para o stub HTTP local;
- Graph: `META_*`. O adaptador não lê a URL da Graph do `.env`; no subprocesso, `HTTP(S)_PROXY`
  aponta para o stub, então qualquer chamada para fora bateria nele (e falharia o comando). O
  túnel é o `cloudflared` falso no começo do PATH, com log de cada início.

- Integração: com `PROVEDOR_PUBLICAR` alternado entre `expxflow` e `meta_graph`, cada dry-run sai 0
  com a intenção (peça, capacidade, provedor escolhido) e o payload montado, sem publicar: nenhuma
  requisição ao stub, nenhum túnel aberto, `peca.json` e rastro intactos, nenhum segredo na saída.
- Funcional: com `PROVEDOR_PUBLICAR` ausente e os dois provedores satisfeitos, o provedor usado é o
  `expxflow` (o primeiro do catálogo) e o aviso de escolha implícita aparece.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from fixtures.fontes_ficticias import semear_cache
from fixtures.instalacao import montar_instalacao
from stubs import cloudflared_falso
from stubs.servidor import ServidorStub

pytestmark = pytest.mark.integracao_local

MOTOR = Path(__file__).resolve().parents[2]
TEMPLATES = MOTOR.parent / "templates"
TIMEOUT_PRODUCAO = 1200  # s; o reel renderiza em Remotion
TIMEOUT_PUBLICAR = 180

CHAVE_EXPXFLOW = "chave-falsa-expxflow-e2e"
CLIENTE_EXPXFLOW = "00000000-0000-4000-8000-0000000000e2"
TOKEN_META = "token-falso-meta-e2e"
IG_META = "17800000000000e2"

EX_CARROSSEL = json.loads((TEMPLATES / "carrossel" / "editorial" / "exemplo.json").read_text(encoding="utf-8"))
EX_REEL = json.loads((TEMPLATES / "reel" / "narrado-cartao" / "exemplo.json").read_text(encoding="utf-8"))
LEGENDA_CARROSSEL = "Sem atalho.\n\nFazer bem feito leva tempo. Salve para a próxima vez.\n\n#metodo #pratica"
CARROSSEL = {"template": "carrossel-editorial-b74228", "titulo": "Sem atalho",
             "slides": copy.deepcopy(EX_CARROSSEL["slides"]), "legenda": LEGENDA_CARROSSEL}

_PREFIXOS_CHAVE = ("ELEVENLABS_", "HEYGEN_", "OPENROUTER_", "PEXELS_", "EXPXFLOW_", "META_", "PROVEDOR_",
                   "YOUTUBE_", "HIGGSFIELD_", "EXPXMEDIA_", "CLOUDFLARED_FALSO_")
_PROXIES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
            "NO_PROXY", "no_proxy")


def _motor(raiz: Path, env: dict, *argv: str, timeout: int = TIMEOUT_PUBLICAR, cwd: Path | None = None):
    feito = subprocess.run(["uv", "run", "--project", str(MOTOR), "expxmedia-motor", *argv, "--raiz", str(raiz)],
                           cwd=cwd or MOTOR, capture_output=True, text=True, timeout=timeout, env=env)
    try:
        saida = json.loads(feito.stdout)
    except json.JSONDecodeError:
        saida = None
    return feito.returncode, saida, feito.stdout + feito.stderr


@pytest.fixture(scope="module")
def cenario(tmp_path_factory):
    """Instalação nova com um carrossel e um reel produzidos pelo CLI, stub e cloudflared falso prontos."""
    base = tmp_path_factory.mktemp("publicacao")
    raiz = montar_instalacao(base / "instalacao")
    xdg = base / "xdg"
    semear_cache(xdg / "expxmedia" / "fontes")
    bin_ = base / "bin"
    cloudflared_falso.instalar(bin_)
    log_tunel = base / "cloudflared.log"
    env_base = {k: v for k, v in os.environ.items() if not k.startswith(_PREFIXOS_CHAVE) and k not in _PROXIES}
    env_base.update(XDG_CACHE_HOME=str(xdg), HF_HUB_OFFLINE="1", CLOUDFLARED_FALSO_LOG=str(log_tunel),
                    PATH=f"{bin_}{os.pathsep}{os.environ.get('PATH', '')}")

    # produção: só o provedor de teste, nenhuma chave
    (raiz / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    entradas = base / "entradas"
    entradas.mkdir()
    pecas = {}
    for nome, subcomando, dados in (("carrossel", "carrossel", CARROSSEL), ("reel", "reel", EX_REEL)):
        arquivo = entradas / f"{nome}.json"
        arquivo.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        codigo, saida, bruto = _motor(raiz, env_base, "produzir", subcomando, "--entrada", str(arquivo),
                                      timeout=TIMEOUT_PRODUCAO, cwd=entradas)
        assert codigo == 0 and saida and saida["ok"], bruto[-4000:]
        pecas[nome] = {"peca_id": saida["peca_id"], "pasta": raiz / saida["pasta"]}

    with ServidorStub() as stub:
        env = dict(env_base)
        for nome in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            env[nome] = stub.url  # qualquer saída para fora (Graph, hospedagem) cairia no stub
        env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost"
        yield {"raiz": raiz, "env": env, "stub": stub, "log_tunel": log_tunel, "pecas": pecas}


def _env_publicacao(raiz: Path, url_stub: str, provedor: str | None) -> None:
    linhas = [
        f"EXPXFLOW_API_KEY={CHAVE_EXPXFLOW}",
        f"EXPXFLOW_CLIENT_ID={CLIENTE_EXPXFLOW}",
        f"EXPXFLOW_BASE_URL={url_stub}",
        f"META_GRAPH_TOKEN={TOKEN_META}",
        f"META_IG_USER_ID={IG_META}",
    ]
    if provedor is not None:
        linhas.append(f"PROVEDOR_PUBLICAR={provedor}")
    (raiz / ".env").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def _foto(cenario, peca: str) -> dict:
    """Bytes do peca.json e a lista de arquivos do rastro (eventos/), para provar que nada foi gravado."""
    raiz = cenario["raiz"]
    eventos = {p.relative_to(raiz).as_posix(): p.read_bytes() for p in sorted((raiz / "eventos").rglob("*")) if p.is_file()}
    return {"peca": (cenario["pecas"][peca]["pasta"] / "peca.json").read_bytes(), "eventos": eventos}


def _publicar_dry_run(cenario, peca: str, provedor: str | None):
    _env_publicacao(cenario["raiz"], cenario["stub"].url, provedor)
    antes = _foto(cenario, peca)
    requisicoes_antes = len(cenario["stub"].requisicoes)
    codigo, saida, bruto = _motor(cenario["raiz"], cenario["env"], "publicar", "--peca",
                                  cenario["pecas"][peca]["peca_id"])
    # sem publicar: nada chegou ao stub, nenhum túnel, peça e rastro intactos, nenhum segredo na saída
    assert cenario["stub"].requisicoes[requisicoes_antes:] == [], [r.caminho for r in cenario["stub"].requisicoes]
    assert cloudflared_falso.eventos(cenario["log_tunel"]) == []
    assert _foto(cenario, peca) == antes
    for segredo in (CHAVE_EXPXFLOW, TOKEN_META):
        assert segredo not in bruto
    return codigo, saida, bruto


# ---------------------------------------------------------------- integração


def test_pecas_produzidas_pelo_cli_para_publicar(cenario):
    for nome, tipo in (("carrossel", "carrossel"), ("reel", "reel")):
        peca = json.loads((cenario["pecas"][nome]["pasta"] / "peca.json").read_text(encoding="utf-8"))
        assert (peca["tipo"], peca["status"], peca["publicacoes"]) == (tipo, "produzida", [])


def test_carrossel_dry_run_pelo_expxflow(cenario):
    codigo, saida, bruto = _publicar_dry_run(cenario, "carrossel", "expxflow")
    assert codigo == 0, bruto
    assert saida["ok"] is True and saida["dry_run"] is True and saida["canais"] == {}
    assert (saida["peca_id"], saida["capacidade"], saida["provedor"]) == (
        cenario["pecas"]["carrossel"]["peca_id"], "publicar", "expxflow")
    payload = saida["payload"]
    assert payload["rota"] == "/carousel-api", payload
    corpo = payload["corpo"]
    assert len(corpo["slides"]) == len(CARROSSEL["slides"])
    assert all(s["image_url"].startswith("https://dry-run.invalid/") for s in corpo["slides"])
    assert corpo["title"] == CARROSSEL["titulo"] and corpo["platforms"] == ["instagram"]
    assert corpo["caption"].startswith("Sem atalho.") and corpo["hashtags"] == "#metodo #pratica"
    assert corpo["publish_now"] is True and corpo["client_id"] == CLIENTE_EXPXFLOW
    assert payload["idempotency_key"].startswith(cenario["pecas"]["carrossel"]["peca_id"])


def test_reel_dry_run_pelo_expxflow(cenario):
    codigo, saida, bruto = _publicar_dry_run(cenario, "reel", "expxflow")
    assert codigo == 0, bruto
    assert (saida["dry_run"], saida["capacidade"], saida["provedor"]) == (True, "publicar", "expxflow")
    corpo = saida["payload"]["corpo"]
    assert saida["payload"]["rota"] == "/post-api"
    assert corpo["content_type"] == "reel"
    assert corpo["image_url"] == "https://dry-run.invalid/final.mp4"  # o post-api chama o vídeo de image_url
    assert corpo["publish_now"] is True and corpo["caption"]


def test_carrossel_dry_run_pela_graph(cenario):
    codigo, saida, bruto = _publicar_dry_run(cenario, "carrossel", "meta_graph")
    assert codigo == 0, bruto
    assert (saida["dry_run"], saida["capacidade"], saida["provedor"]) == (True, "publicar", "meta_graph")
    plano = saida["payload"]
    assert plano["provedor"] == "meta_graph" and plano["tipo"] == "carrossel"
    assert len(plano["itens"]) == len(CARROSSEL["slides"])
    assert plano["legenda"] == LEGENDA_CARROSSEL


def test_reel_dry_run_pela_graph(cenario):
    codigo, saida, bruto = _publicar_dry_run(cenario, "reel", "meta_graph")
    assert codigo == 0, bruto
    assert (saida["dry_run"], saida["provedor"]) == (True, "meta_graph")
    plano = saida["payload"]
    assert plano["tipo"] == "reel" and plano["itens"] == ["final.mp4"]


def test_provedor_alternado_troca_o_adaptador_na_mesma_peca(cenario):
    """PROVEDOR_PUBLICAR decide: a mesma peça sai pelo expxflow e pela Graph, sem troca silenciosa."""
    usados = []
    for provedor in ("meta_graph", "expxflow", "meta_graph"):
        codigo, saida, bruto = _publicar_dry_run(cenario, "carrossel", provedor)
        assert codigo == 0, bruto
        usados.append(saida["provedor"])
    assert usados == ["meta_graph", "expxflow", "meta_graph"]


# ---------------------------------------------------------------- funcional


def test_sem_provedor_publicar_e_os_dois_satisfeitos_usa_expxflow(cenario):
    codigo, saida, bruto = _publicar_dry_run(cenario, "carrossel", None)
    assert codigo == 0, bruto
    assert saida["provedor"] == "expxflow" and saida["dry_run"] is True
    assert "rota" in saida["payload"]  # payload do expxflow, não o plano da Graph


def _textos(valor) -> list[str]:
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, dict):
        return [t for v in valor.values() for t in _textos(v)]
    if isinstance(valor, list):
        return [t for v in valor for t in _textos(v)]
    return []


def test_sem_provedor_publicar_o_aviso_de_escolha_implicita_aparece(cenario):
    codigo, saida, bruto = _publicar_dry_run(cenario, "reel", None)
    assert codigo == 0, bruto
    assert saida["provedor"] == "expxflow"
    avisos = _textos(saida.get("avisos")) + _textos(saida.get("aviso"))
    # o aviso de Verificador.aviso: cita os dois satisfeitos, a variável ausente e o escolhido
    assert any("PROVEDOR_PUBLICAR" in a and "meta_graph" in a and "expxflow" in a for a in avisos), (
        f"a saída do publicar não traz o aviso de escolha implícita: {saida}")


def test_com_provedor_publicar_explicito_nao_ha_aviso(cenario):
    codigo, saida, bruto = _publicar_dry_run(cenario, "reel", "expxflow")
    assert codigo == 0, bruto
    avisos = _textos(saida.get("avisos")) + _textos(saida.get("aviso"))
    assert not any("PROVEDOR_PUBLICAR" in a for a in avisos)
