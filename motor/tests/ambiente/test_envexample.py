"""T-02.08: .env.example do núcleo, um bloco comentado por capacidade com onde conseguir cada chave."""
import os
import re

from expxmedia.ambiente import catalogo, env, envexample

SEGREDO = "chave-verdadeira-da-pessoa-123"


def _bloco_de(texto, variavel):
    """Linhas de comentário imediatamente acima da linha `variavel=`."""
    linhas = texto.splitlines()
    i = next(n for n, l in enumerate(linhas) if l.startswith(f"{variavel}="))
    acima = []
    for linha in reversed(linhas[:i]):
        if not linha.startswith("#"):
            if linha.strip() == "" and not acima:
                continue
            if "=" in linha and not linha.startswith("#"):
                continue  # outra variável do mesmo bloco
            break
        acima.insert(0, linha)
    return acima, linhas[i]


# ---------- integração: não toca no .env ----------

def test_gerar_exemplo_nao_altera_o_env(instalacao):
    conteudo = f"ELEVENLABS_API_KEY={SEGREDO}\nPROVEDOR_PUBLICAR=meta_graph\n".encode()
    (instalacao / ".env").write_bytes(conteudo)
    antes = os.stat(instalacao / ".env")
    caminho = envexample.escrever(instalacao)
    assert caminho == instalacao / ".env.example"
    assert (instalacao / ".env").read_bytes() == conteudo
    assert os.stat(instalacao / ".env").st_mtime_ns == antes.st_mtime_ns
    exemplo = caminho.read_text(encoding="utf-8")
    assert SEGREDO not in exemplo
    assert "PROVEDOR_PUBLICAR=\n" in exemplo  # a escolha da pessoa não vaza para o exemplo
    # regenerar sobrescreve só o exemplo, igual
    assert envexample.escrever(instalacao).read_text(encoding="utf-8") == exemplo
    assert not list(instalacao.glob(".env.example.*"))  # sem temporário esquecido


# ---------- funcional: bloco do narrar ----------

def test_elevenlabs_vazio_sob_comentario_de_narrar_com_onde_conseguir():
    texto = envexample.gerar()
    comentarios, linha = _bloco_de(texto, "ELEVENLABS_API_KEY")
    assert linha == "ELEVENLABS_API_KEY="
    assert any(re.match(r"^# narrar\b", c) for c in comentarios)
    assert any(c.startswith("# Onde conseguir: https://elevenlabs.io") for c in comentarios)


def test_todo_valor_vazio_e_o_arquivo_e_um_env_valido():
    texto = envexample.gerar()
    lido = env.interpretar(texto)
    assert lido and all(v == "" for v in lido.values())
    assert catalogo.FLAG_TESTE not in lido  # flag de teste não é para a pessoa


def test_todas_as_variaveis_do_catalogo_uma_vez_so():
    texto = envexample.gerar()
    nomes = [l.split("=", 1)[0] for l in texto.splitlines() if l and not l.startswith("#")]
    assert len(nomes) == len(set(nomes))
    esperadas = {
        "ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "OPENROUTER_API_KEY", "PEXELS_API_KEY",
        "EXPXFLOW_API_KEY", "EXPXFLOW_CLIENT_ID", "EXPXFLOW_BASE_URL",
        "META_GRAPH_TOKEN", "META_IG_USER_ID", "META_PAGE_ID", "YOUTUBE_CLIENT_SECRET_FILE",
        "PROVEDOR_PUBLICAR", "PROVEDOR_AGENDAR",
    }
    assert set(nomes) == esperadas


def test_blocos_de_expxflow_e_provedor_padrao():
    texto = envexample.gerar()
    comentarios, _ = _bloco_de(texto, "EXPXFLOW_API_KEY")
    assert any(c.startswith("# publicar, agendar, automacao_dm") for c in comentarios)
    assert any("Onde conseguir" in c for c in comentarios)
    bloco = texto.split("EXPXFLOW_API_KEY=", 1)[1].split("\n\n", 1)[0]
    assert "EXPXFLOW_BASE_URL=" in bloco  # obrigatória junto das chaves, sem padrão
    comentarios, _ = _bloco_de(texto, "PROVEDOR_PUBLICAR")
    assert any("expxflow | meta_graph | youtube_api" in c for c in comentarios)
    comentarios, _ = _bloco_de(texto, "PROVEDOR_AGENDAR")
    assert any("expxflow | meta_graph" in c and "youtube" not in c for c in comentarios)


def test_pack_acrescenta_suas_variaveis_sem_repetir():
    cat = catalogo.Catalogo()
    cat.registrar_pack("expx-meta", [{
        "id": "anuncios_meta",
        "descricao": "operar a conta de anúncios",
        "provedores": [{"id": "meta_graph", "env": ["META_GRAPH_TOKEN", "META_AD_ACCOUNT_ID"], "cli": None, "binarios": []}],
        "como_habilitar": "Coloque META_GRAPH_TOKEN e META_AD_ACCOUNT_ID no .env. Onde conseguir: gerenciador de anúncios.",
    }])
    texto = envexample.gerar(cat)
    nomes = [l.split("=", 1)[0] for l in texto.splitlines() if l and not l.startswith("#")]
    assert nomes.count("META_GRAPH_TOKEN") == 1 and "META_AD_ACCOUNT_ID" in nomes
    comentarios, _ = _bloco_de(texto, "META_AD_ACCOUNT_ID")
    assert any(c.startswith("# anuncios_meta") for c in comentarios)
    assert any("Onde conseguir: gerenciador de anúncios" in c for c in comentarios)
    assert "META_AD_ACCOUNT_ID" not in envexample.gerar()  # sem o pack, não polui
