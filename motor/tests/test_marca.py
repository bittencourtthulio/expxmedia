"""T-01.06: varredura de marca (regra M13, D-02).

Nenhum código do núcleo carrega nome, cor, conta, fonte de sistema ou id de uma empresa
específica. Os termos proibidos (regex, case-insensitive) vivem em marca_proibida.txt,
um por linha, com a origem de cada um comentada. Esta pasta de testes não é varrida:
é aqui que os termos proibidos precisam aparecer.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LISTA = Path(__file__).resolve().parent / "marca_proibida.txt"

RAIZES = [
    REPO / "motor" / "src",
    REPO / "motor" / "kit-remotion" / "src",
    REPO / "motor" / "kit-remotion" / "scripts",
    REPO / "nucleo",
    REPO / "templates",
]

IGNORAR_PASTAS = {"node_modules", ".venv", "__pycache__", ".git"}
EXTENSOES_BINARIAS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tif", ".tiff",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".wav", ".m4a", ".mov", ".webm", ".ogg", ".aac",
    ".pdf", ".zip", ".gz", ".tar", ".onnx", ".bin", ".pyc", ".so", ".dylib",
}


def carregar_termos(caminho=LISTA):
    """Lê marca_proibida.txt: uma regex por linha; linhas vazias e iniciadas por '#' são comentário."""
    termos = []
    for bruta in caminho.read_text(encoding="utf-8").splitlines():
        linha = bruta.strip()
        if not linha or linha.startswith("#"):
            continue
        termos.append((linha, re.compile(linha, re.IGNORECASE)))
    return termos


def _texto(arquivo):
    """Conteúdo textual do arquivo, ou None se for binário."""
    if arquivo.suffix.lower() in EXTENSOES_BINARIAS:
        return None
    dados = arquivo.read_bytes()
    if b"\x00" in dados[:8192]:
        return None
    try:
        return dados.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _arquivos(raiz):
    for arquivo in sorted(raiz.rglob("*")):
        if not arquivo.is_file():
            continue
        if IGNORAR_PASTAS.intersection(arquivo.relative_to(raiz).parts):
            continue
        yield arquivo


_RE_ORIGEM = re.compile(r"origem:", re.IGNORECASE)


def varrer(raizes, termos=None):
    """Devolve [(arquivo, linha, termo)] de cada ocorrência de termo proibido nas raízes.

    Raízes inexistentes são ignoradas. `termo` é a regex da lista que casou.
    """
    termos = carregar_termos() if termos is None else termos
    achados = []
    for raiz in map(Path, raizes):
        if not raiz.exists():
            continue
        for arquivo in ([raiz] if raiz.is_file() else _arquivos(raiz)):
            texto = _texto(arquivo)
            if texto is None:
                continue
            for numero, conteudo in enumerate(texto.splitlines(), start=1):
                # Procedência exigida pelo método (D-50): o que vem depois de
                # "origem:" cita arquivo:linha dos projetos de origem e não é
                # marca embutida no comportamento.
                conteudo = _RE_ORIGEM.split(conteudo, maxsplit=1)[0]
                for termo, regex in termos:
                    if regex.search(conteudo):
                        achados.append((arquivo, numero, termo))
    return achados


def _formatar(achados):
    linhas = []
    for arquivo, numero, termo in achados:
        try:
            nome = arquivo.relative_to(REPO)
        except ValueError:
            nome = arquivo
        linhas.append(f"{nome}:{numero}:{termo}")
    return "\n".join(linhas)


# --- integração: o núcleo real está limpo ---------------------------------------------

def test_nucleo_sem_marca():
    achados = varrer(RAIZES)
    assert not achados, "termo de marca no núcleo (M13):\n" + _formatar(achados)


def test_lista_cobre_os_termos_minimos():
    """Cada amostra de marca real das origens é pega por algum termo da lista."""
    termos = carregar_termos()
    amostras = [
        "Thulio", "BITTENCOURT", "Software House Exponencial", "softwarehouse", "ExpxPlay",
        "Academia do Código", "academia do codigo", "Sala dos Mestres", "@expxinsta",
        "act_1234567",
        "ejwpfztkspbvmuwwiwmk", "#E4602A", "#22c55e", "#0B0B0F", "#F5F2EC", "#efe8da",
        "/System/Library/Fonts/Helvetica.ttc", "Arial Black", "Rockwell", "thulio.mov",
        "Radar IA",
    ]
    faltando = [a for a in amostras if not any(r.search(a) for _, r in termos)]
    assert not faltando, f"amostras não cobertas pela lista: {faltando}"


def test_lista_documenta_origem_de_cada_termo():
    """Todo termo é precedido por um comentário explicando a origem."""
    anterior = ""
    for bruta in LISTA.read_text(encoding="utf-8").splitlines():
        linha = bruta.strip()
        if linha and not linha.startswith("#"):
            assert anterior.startswith("#"), f"termo sem comentário de origem: {linha}"
        if linha:
            anterior = linha


# --- funcional -------------------------------------------------------------------------

def test_varrer_aponta_nome_do_dono(tmp_path):
    pasta = tmp_path / "src"
    (pasta / "sub").mkdir(parents=True)
    (pasta / "sub" / "limpo.py").write_text("x = 1\n", encoding="utf-8")
    (pasta / "sub" / "sujo.py").write_text(
        "a = 1\nautor = 'Thulio Bittencourt'\n", encoding="utf-8"
    )
    achados = varrer([pasta, tmp_path / "nao-existe"])
    assert {(a.name, n) for a, n, _ in achados} == {("sujo.py", 2)}
    termos = {t for _, _, t in achados}
    assert any(re.search(t, "thulio", re.IGNORECASE) for t in termos)
    assert any(re.search(t, "bittencourt", re.IGNORECASE) for t in termos)


def test_varrer_ignora_pastas_de_dependencia_e_binarios(tmp_path):
    for pasta in ("node_modules", ".venv", "__pycache__"):
        (tmp_path / pasta).mkdir()
        (tmp_path / pasta / "x.js").write_text("thulio\n", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\x00thulio")
    (tmp_path / "dado.bin2").write_bytes(b"\x00\x01thulio")
    assert varrer([tmp_path]) == []


def test_varrer_nao_aponta_produto_nem_provedor(tmp_path):
    (tmp_path / "ok.py").write_text(
        "PRODUTO = 'expxmedia'\n"
        "chave = os.environ['EXPXFLOW_API_KEY']\n"
        "provedor = 'Expx Flow'  # expxflow\n"
        "raiz = os.environ['EXPXMEDIA_RAIZ']\n",
        encoding="utf-8",
    )
    assert varrer([tmp_path]) == []


def test_procedencia_origem_nao_e_marca(tmp_path):
    arq = tmp_path / "modulo.py"
    arq.write_text("LIMIAR = 3  # origem: cursos-ia/radar-ia-09/gerar_voz.py:35\nNOME = 'Radar IA'\n", encoding="utf-8")
    achados = varrer([tmp_path])
    assert [n for _, n, _ in achados] == [2]
