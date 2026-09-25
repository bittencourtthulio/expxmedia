"""T-02.02: escrita atômica de JSON e acréscimo de JSONL com trava entre processos (M15)."""
import json
import subprocess
import sys
import textwrap
import time

import pytest

from expxmedia.nucleo import arquivos

PROCESSOS = 8
LINHAS = 100
# Linha maior que o buffer de 8 KiB do Python: uma escrita sem trava que sai em vários
# write() (ex.: json.dump direto no arquivo) se intercala com a de outro processo; conferido
# com 78 de 800 linhas quebradas. Uma escrita sem trava num write() só pode escapar daqui
# pelo O_APPEND; por isso test_acrescimo_espera_a_trava verifica a trava diretamente.
TAMANHO = 40_000

ESCRITOR = textwrap.dedent(
    """
    import sys
    from expxmedia.nucleo import arquivos
    caminho, quem, linhas, tamanho = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    for i in range(linhas):
        arquivos.acrescentar_jsonl(caminho, {"quem": quem, "i": i, "carga": chr(65 + quem) * tamanho})
    """
)


# ---------- integração: oito processos no mesmo JSONL ----------

def test_oito_processos_acrescentam_800_linhas_validas(tmp_path):
    destino = tmp_path / "eventos" / "2026-09.jsonl"
    processos = [
        subprocess.Popen([sys.executable, "-c", ESCRITOR, str(destino), str(q), str(LINHAS), str(TAMANHO)])
        for q in range(PROCESSOS)
    ]
    for p in processos:
        assert p.wait(timeout=120) == 0

    brutas = destino.read_text(encoding="utf-8").splitlines()
    assert len(brutas) == PROCESSOS * LINHAS
    vistos = set()
    for bruta in brutas:
        obj = json.loads(bruta)  # cada linha é um JSON inteiro
        assert obj["carga"] == chr(65 + obj["quem"]) * TAMANHO
        vistos.add((obj["quem"], obj["i"]))
    assert len(vistos) == PROCESSOS * LINHAS

    eventos, corrompidas = arquivos.ler_jsonl(destino)
    assert (len(eventos), corrompidas) == (PROCESSOS * LINHAS, 0)
    # ordem preservada dentro de cada processo
    for q in range(PROCESSOS):
        assert [e["i"] for e in eventos if e["quem"] == q] == list(range(LINHAS))


def test_acrescimo_espera_a_trava(tmp_path):
    destino = tmp_path / "rastro.jsonl"
    with arquivos.trava(destino):
        filho = subprocess.Popen([sys.executable, "-c", ESCRITOR, str(destino), "0", "1", "10"])
        time.sleep(1.0)
        assert filho.poll() is None, "o acréscimo não respeitou a trava"
        assert not destino.exists() or destino.read_text(encoding="utf-8") == ""
    assert filho.wait(timeout=30) == 0
    assert arquivos.ler_jsonl(destino) == ([{"quem": 0, "i": 0, "carga": "A" * 10}], 0)


# ---------- funcional: gravar_json ----------

def test_gravar_json_nao_serializavel_levanta_e_preserva_anterior(tmp_path):
    destino = tmp_path / "peca.json"
    arquivos.gravar_json(destino, {"expxmedia_peca": 1, "titulo": "Pão de fermentação"})
    antes = destino.read_bytes()

    with pytest.raises(arquivos.ErroArquivo):
        arquivos.gravar_json(destino, {"expxmedia_peca": 1, "quando": object()})
    with pytest.raises(arquivos.ErroArquivo):
        arquivos.gravar_json(destino, {"expxmedia_peca": 1, "nota": float("nan")})

    assert destino.read_bytes() == antes
    assert [p.name for p in tmp_path.iterdir()] == ["peca.json"]  # nenhum temporário órfão


def test_gravar_json_formato_e_pasta_criada(tmp_path):
    destino = tmp_path / "pecas" / "2026-09" / "P-20260924-A3F9-x" / "peca.json"
    arquivos.gravar_json(destino, {"titulo": "Ação", "lista": []})
    bruto = destino.read_bytes()
    assert not bruto.startswith(b"\xef\xbb\xbf")  # UTF-8 sem BOM (M16)
    assert bruto.decode("utf-8") == '{\n  "titulo": "Ação",\n  "lista": []\n}\n'
    assert arquivos.ler_json(destino) == {"titulo": "Ação", "lista": []}


def test_ler_json_tolera_bom_e_nao_engole_json_quebrado(tmp_path):
    com_bom = tmp_path / "bom.json"
    com_bom.write_bytes(b"\xef\xbb\xbf" + json.dumps({"a": 1}).encode())
    assert arquivos.ler_json(com_bom) == {"a": 1}

    quebrado = tmp_path / "quebrado.json"
    quebrado.write_text('{"a": ', encoding="utf-8")
    with pytest.raises(arquivos.ErroArquivo, match="quebrado.json"):
        arquivos.ler_json(quebrado)

    ausente = tmp_path / "ausente.json"
    assert arquivos.ler_json(ausente, padrao=None) is None
    with pytest.raises(arquivos.ErroArquivo):
        arquivos.ler_json(ausente)


def test_ler_jsonl_pula_e_conta_linha_corrompida(tmp_path):
    destino = tmp_path / "x.jsonl"
    destino.write_bytes(b'\xef\xbb\xbf{"a":1}\n\n{quebrada\n[1,2]\n{"b":2}\n')
    assert arquivos.ler_jsonl(destino) == ([{"a": 1}, {"b": 2}], 2)
    assert arquivos.ler_jsonl(tmp_path / "nao-existe.jsonl") == ([], 0)


def test_acrescentar_jsonl_recusa_nao_objeto_e_nao_serializavel(tmp_path):
    destino = tmp_path / "x.jsonl"
    with pytest.raises(arquivos.ErroArquivo):
        arquivos.acrescentar_jsonl(destino, [1, 2])
    with pytest.raises(arquivos.ErroArquivo):
        arquivos.acrescentar_jsonl(destino, {"x": object()})
    assert not destino.exists() or destino.read_bytes() == b""
    arquivos.acrescentar_jsonl(destino, {"texto": "linha\ncom quebra"})
    assert destino.read_text(encoding="utf-8").count("\n") == 1
