"""T-05.02: montagem da linha do tempo e trilha generalizadas (D-19).

- Integração: montar o G2 a partir das mesmas entradas gera timeline.json igual ao golden (byte a
  byte) e trilha.wav com o mesmo sha256, sem escrever nada fora de --saida (nenhum registro global).
- Funcional: âncora ausente da narração faz a montagem sair com erro citando a cena e a âncora;
  trilha igual a uma assinatura da lista passada por argumento é recusada; evento e efeito
  desconhecidos falham com mensagem.
"""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

MOTOR = Path(__file__).resolve().parents[2]
KIT = MOTOR / "kit-remotion"
MONTAR = KIT / "scripts" / "montar.mjs"
G2 = MOTOR / "tests" / "golden" / "G2"

pytestmark = pytest.mark.integracao_local


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _sha_manifesto(nome):
    m = json.loads((MOTOR / "tests" / "golden" / "manifesto.json").read_text(encoding="utf-8"))
    return next(a["sha256"] for a in m["goldens"]["G2"]["arquivos"] if a["caminho"] == f"G2/{nome}")


@pytest.fixture
def node(requer_binario):
    return requer_binario("node")


@pytest.fixture
def entradas(tmp_path):
    reel = tmp_path / "reel"
    reel.mkdir()
    shutil.copy(G2 / "entradas" / "cenas.json", reel / "cenas.json")
    return {
        "reel": reel,
        "narracao": G2 / "entradas" / "narracao.mp3",
        "alinhamento": G2 / "entradas" / "alignment.json",
        "saida": tmp_path / "saida",
    }


def _montar(node, e, *extra, cwd=None):
    args = [node, str(MONTAR), "--reel", str(e["reel"]), "--narracao", str(e["narracao"]),
            "--alinhamento", str(e["alinhamento"]), "--saida", str(e["saida"]), *extra]
    return subprocess.run(args, cwd=cwd or e["reel"].parent, capture_output=True, text=True, timeout=300)


def _arvore(raiz):
    return sorted((str(p.relative_to(raiz)), p.stat().st_mtime_ns) for p in raiz.rglob("*")
                  if "node_modules" not in p.parts and p.name != "registro.generated.ts")


# ---------------------------------------------------------------- integração


def test_montar_g2_gera_timeline_e_trilha_iguais_ao_golden(node, entradas, tmp_path):
    antes = _arvore(KIT)
    r = _montar(node, entradas)
    assert r.returncode == 0, r.stderr
    saida = entradas["saida"]
    assert (saida / "timeline.json").read_bytes() == (G2 / "timeline.json").read_bytes()
    assert _sha(saida / "timeline.json") == _sha_manifesto("timeline.json")
    assert _sha(saida / "trilha.wav") == _sha_manifesto("trilha.wav") == _sha(G2 / "trilha.wav")
    assert _sha(saida / "narracao.mp3") == _sha(entradas["narracao"])
    # nada de registro global nem escrita no kit ou na pasta do reel
    assert sorted(p.name for p in saida.iterdir()) == ["narracao.mp3", "timeline.json", "trilha.wav"]
    assert sorted(p.name for p in entradas["reel"].iterdir()) == ["cenas.json"]
    assert _arvore(KIT) == antes
    # console no formato da origem: "<reel>: N cenas · F frames (Xs) · E efeitos"
    assert r.stdout.splitlines()[0] == "reel: 10 cenas · 1275 frames (42.5s) · 74 efeitos", r.stdout


def test_montar_com_lista_de_assinaturas_diferentes_passa(node, entradas, tmp_path):
    cenas = json.loads((entradas["reel"] / "cenas.json").read_text(encoding="utf-8"))
    outra = dict(cenas["trilha"], bpm=cenas["trilha"]["bpm"] + 4)
    lista = tmp_path / "assinaturas.json"
    lista.write_text(json.dumps([{"reel": "outro-reel", "trilha": outra}]), encoding="utf-8")
    r = _montar(node, entradas, "--assinaturas", str(lista))
    assert r.returncode == 0, r.stderr
    assert _sha(entradas["saida"] / "trilha.wav") == _sha(G2 / "trilha.wav")


def test_assinatura_impressa_casa_com_a_da_lista(node, entradas, tmp_path):
    r = subprocess.run([node, str(MONTAR), "--assinatura", "--reel", str(entradas["reel"])],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assinatura = json.loads(r.stdout)
    cenas = json.loads((entradas["reel"] / "cenas.json").read_text(encoding="utf-8"))
    # só bpm, acordes e o conjunto de nomes dos instrumentos (volumes, arpejo e semente não entram)
    assert json.loads(assinatura) == {"bpm": cenas["trilha"]["bpm"], "acordes": cenas["trilha"]["acordes"],
                                      "instrumentos": sorted(cenas["trilha"]["instrumentos"])}
    lista = tmp_path / "assinaturas.json"
    lista.write_text(json.dumps([{"reel": "reel-antigo", "assinatura": assinatura}]), encoding="utf-8")
    r = _montar(node, entradas, "--assinaturas", str(lista))
    assert r.returncode != 0
    assert "reel-antigo" in r.stderr and "Cada reel tem a sua" in r.stderr


# ---------------------------------------------------------------- funcional


def test_ancora_ausente_sai_com_erro_citando_cena_e_ancora(node, entradas):
    cenas = json.loads((entradas["reel"] / "cenas.json").read_text(encoding="utf-8"))
    alvo = cenas["cenas"][4]
    alvo["ancora"] = "palavra que ninguém disse"
    (entradas["reel"] / "cenas.json").write_text(json.dumps(cenas, ensure_ascii=False), encoding="utf-8")
    r = _montar(node, entradas)
    assert r.returncode != 0
    assert f"cena 5 ({alvo['id']})" in r.stderr
    assert "palavra que ninguém disse" in r.stderr
    assert not (entradas["saida"] / "timeline.json").exists()


def test_trilha_repetida_de_outro_reel_e_recusada(node, entradas, tmp_path):
    cenas = json.loads((entradas["reel"] / "cenas.json").read_text(encoding="utf-8"))
    # mesma assinatura com volumes diferentes continua sendo a mesma trilha
    igual = dict(cenas["trilha"], ganho=0.3, instrumentos={k: v * 2 for k, v in cenas["trilha"]["instrumentos"].items()})
    lista = tmp_path / "assinaturas.json"
    lista.write_text(json.dumps([{"reel": "reel-anterior", "trilha": igual}]), encoding="utf-8")
    r = _montar(node, entradas, "--assinaturas", str(lista))
    assert r.returncode != 0
    assert "reel-anterior" in r.stderr and "mude andamento, harmonia ou timbre" in r.stderr


def test_som_com_evento_inexistente_falha(node, entradas):
    cenas = json.loads((entradas["reel"] / "cenas.json").read_text(encoding="utf-8"))
    cenas["cenas"][2]["sons"] = [["nao_existe", "pop"]]
    (entradas["reel"] / "cenas.json").write_text(json.dumps(cenas, ensure_ascii=False), encoding="utf-8")
    r = _montar(node, entradas)
    assert r.returncode != 0
    assert '"nao_existe"' in r.stderr and cenas["cenas"][2]["id"] in r.stderr


def test_efeito_desconhecido_lista_os_vinte_existentes(node, entradas):
    cenas = json.loads((entradas["reel"] / "cenas.json").read_text(encoding="utf-8"))
    cenas["cenas"][1]["sons"] = [["0", "trombone"]]
    (entradas["reel"] / "cenas.json").write_text(json.dumps(cenas, ensure_ascii=False), encoding="utf-8")
    r = _montar(node, entradas)
    assert r.returncode != 0
    assert "efeito desconhecido: trombone" in r.stderr
    existentes = r.stderr.split("existem: ", 1)[1].split(")", 1)[0].split(", ")
    assert existentes == ["whoosh", "pop", "bolha", "check", "ding", "tick", "digita", "erro", "carimbo", "impacto",
                          "subida", "descida", "moeda", "snip", "clack", "plim", "hum", "chime", "passos", "pagina"]


def test_argumento_obrigatorio_ausente_sai_com_uso(node, entradas):
    r = subprocess.run([node, str(MONTAR), "--reel", str(entradas["reel"])], capture_output=True, text=True, timeout=60)
    assert r.returncode == 2
    assert "--narracao" in r.stderr and "--saida" in r.stderr


def test_semente_muda_a_trilha(node, entradas):
    cenas = json.loads((entradas["reel"] / "cenas.json").read_text(encoding="utf-8"))
    cenas["trilha"]["semente"] = 8
    (entradas["reel"] / "cenas.json").write_text(json.dumps(cenas, ensure_ascii=False), encoding="utf-8")
    assert _montar(node, entradas).returncode == 0
    assert _sha(entradas["saida"] / "trilha.wav") != _sha(G2 / "trilha.wav")
    # a linha do tempo não depende da semente
    assert (entradas["saida"] / "timeline.json").read_bytes() == (G2 / "timeline.json").read_bytes()


def test_montar_le_o_fps_da_constante_do_kit():
    fonte = MONTAR.read_text(encoding="utf-8")
    assert "constantes.ts" in fonte
    assert "FPS = 30" not in fonte
