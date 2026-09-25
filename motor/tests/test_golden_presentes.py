"""T-01.07: goldens do sistema atual (D-16, D-37, D-47).

Os goldens em tests/golden/ são a saída de referência do código dos projetos de origem,
gerada por scripts/gerar_golden.py numa CÓPIA temporária. Aqui se confere:

- funcional: o manifesto lista G1 a G8 com sha256, comando de origem e entradas usadas, e
  a verificação acusa qualquer golden ou arquivo listado que falte (ou que tenha mudado);
- integração: o gerador roda o código de origem em cópia temporária, o sha256 de cada
  arquivo de origem lido é igual antes e depois, e a saída regerada é a mesma do golden.
"""
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest

MOTOR = Path(__file__).resolve().parents[1]
GOLDEN = MOTOR / "tests" / "golden"
MANIFESTO = GOLDEN / "manifesto.json"
SCRIPT = MOTOR / "scripts" / "gerar_golden.py"
PROJETOS = MOTOR.parents[1]
IDS = [f"G{n}" for n in range(1, 9)]
SHA = re.compile(r"^[0-9a-f]{64}$")
PAPEIS = ("fundo", "fundo_alt", "texto", "texto_inverso", "apoio", "destaque", "destaque_2", "positivo", "negativo")


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler(caminho):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def _relativo_seguro(caminho):
    p = Path(caminho)
    return bool(caminho) and not p.is_absolute() and ".." not in p.parts and not re.match(r"^[A-Za-z]:", caminho)


def problemas(manifesto, raiz):
    """O que falta ou diverge no manifesto e na pasta dos goldens. Lista vazia = tudo presente."""
    achados = []
    goldens = manifesto.get("goldens") or {}
    for gid in IDS:
        g = goldens.get(gid)
        if not g:
            achados.append(f"{gid}: ausente do manifesto")
            continue
        if g.get("id") != gid:
            achados.append(f"{gid}: id divergente ({g.get('id')})")
        for campo in ("descricao", "comando", "entradas", "arquivos"):
            if not g.get(campo):
                achados.append(f"{gid}: sem {campo}")
        if g.get("bloqueio"):
            achados.append(f"{gid}: bloqueado: {g['bloqueio']}")
        for e in g.get("entradas") or []:
            if not SHA.match(str(e.get("sha256", ""))):
                achados.append(f"{gid}: entrada {e.get('caminho')} sem sha256")
            if not _relativo_seguro(e.get("caminho", "")):
                achados.append(f"{gid}: entrada com caminho não relativo à pasta projects/: {e.get('caminho')}")
        for a in g.get("arquivos") or []:
            rel = a.get("caminho", "")
            if not _relativo_seguro(rel):
                achados.append(f"{gid}: arquivo com caminho não relativo: {rel}")
                continue
            arq = Path(raiz) / rel
            if not arq.is_file():
                achados.append(f"{gid}: falta {rel}")
            elif sha256(arq) != a.get("sha256"):
                achados.append(f"{gid}: sha256 divergente em {rel}")
    return achados


@pytest.fixture(scope="module")
def manifesto():
    assert MANIFESTO.is_file(), f"falta {MANIFESTO.relative_to(MOTOR)}"
    return ler(MANIFESTO)


def arquivos_de(manifesto, gid):
    return {a["caminho"] for a in manifesto["goldens"][gid]["arquivos"]}


# ------------------------------------------------------------------ funcional


def test_manifesto_lista_g1_a_g8_com_todos_os_arquivos(manifesto):
    assert problemas(manifesto, GOLDEN) == []


def test_verificacao_acusa_golden_ou_arquivo_faltando(manifesto, tmp_path):
    base = copy.deepcopy(manifesto)
    sem_g5 = copy.deepcopy(base)
    del sem_g5["goldens"]["G5"]
    assert "G5: ausente do manifesto" in problemas(sem_g5, GOLDEN)

    # um arquivo listado que some da pasta é acusado pelo nome
    raiz = tmp_path / "golden"
    shutil.copytree(GOLDEN, raiz)
    alvo = sorted(arquivos_de(base, "G3"))[0]
    (raiz / alvo).unlink()
    assert f"G3: falta {alvo}" in problemas(base, raiz)

    # um arquivo alterado é acusado pelo sha256
    outro = sorted(arquivos_de(base, "G6"))[0]
    (raiz / outro).write_bytes(b"{}")
    assert f"G6: sha256 divergente em {outro}" in problemas(base, raiz)

    # golden sem entrada ou sem comando reprova
    sem_cmd = copy.deepcopy(base)
    sem_cmd["goldens"]["G7"]["comando"] = []
    sem_cmd["goldens"]["G2"]["entradas"] = []
    achados = problemas(sem_cmd, GOLDEN)
    assert "G7: sem comando" in achados and "G2: sem entradas" in achados


def test_manifesto_sem_caminho_absoluto_e_com_origem_intacta(manifesto):
    def strings(x):
        if isinstance(x, dict):
            for v in x.values():
                yield from strings(v)
        elif isinstance(x, list):
            for v in x:
                yield from strings(v)
        elif isinstance(x, str):
            yield x

    absolutos = [s for s in strings(manifesto) if re.search(r"(^|[\s'\"=])(/Users/|/private/|/var/folders/|/tmp/|[A-Za-z]:\\)", s)]
    assert absolutos == []
    for gid in IDS:
        g = manifesto["goldens"][gid]
        assert g["origem_intacta"]["iguais"] is True, gid
        assert g["origem_intacta"]["arquivos"] >= len(g["entradas"]), gid
        for c in g["codigo"]:
            assert SHA.match(c["sha256"]) and _relativo_seguro(c["caminho"]), (gid, c)


def test_nada_proibido_na_pasta_dos_goldens():
    arquivos = [p for p in GOLDEN.rglob("*") if p.is_file()]
    nomes = [p.name.lower() for p in arquivos]
    assert not [n for n in nomes if n.startswith(".env")]
    # D-47: a fonte do sistema da origem não é copiada; vídeo de referência de terceiros também não
    assert not [n for n in nomes if n.endswith((".ttf", ".otf", ".mov", ".webm", ".m4a"))]
    assert not [p for p in arquivos if "referencia" in p.parts]
    assert not [n for n in nomes if n == "prancha.png"]  # a prancha recorta a arte de terceiros


def test_g1_render_alma_e_fontes(manifesto):
    from PIL import Image

    g1 = GOLDEN / "G1"
    render = ler(g1 / "render.json")
    assert render["ok"] is True and render["layout"] == "0001-pos-paineis-de-pagamento"
    assert [s["kind"] for s in render["slides"]] == ["interface", "numero", "frase", "manchete"]
    assert all(re.match(r"^(fixo|free=-?\d+ shrink=\d+ zoom=[\d.]+)$", s["encaixe"]) for s in render["slides"])
    assert not Path(render["saida"]).is_absolute()
    for n in range(1, 5):
        with Image.open(g1 / f"slide_{n}.png") as img:
            assert img.size == (1080, 1350)

    alma = ler(g1 / "alma-golden.json")
    assert alma["expxmedia_alma"] == 1 and alma["confirmada_em"]
    for secao in ("empresa", "publico", "ofertas", "voz", "visual", "cta", "canais", "porta_vozes", "restricoes", "origens", "pendencias"):
        assert secao in alma, secao
    cores = alma["visual"]["cores"]
    assert set(cores) == set(PAPEIS)
    # tema "referencia" de layout.css da origem nos papéis de cor
    assert cores["fundo"] == "#f1f1f1" and cores["fundo_alt"] == "#0b0b0d"
    assert cores["texto"] == "#121212" and cores["texto_inverso"] == "#f4f4f4"
    assert cores["apoio"] == "#77777c" and cores["destaque"] == "#5a5ef2"
    assert cores["destaque_2"] == "#8e5cf6" and cores["positivo"] == "#4ee08a"
    assert alma["visual"]["fontes"]["titulo"] == {"familia": "Inter Tight", "origem": "google"}

    fontes = sorted((g1 / "fontes").glob("*.woff2"))
    assert fontes, "nenhuma fonte baixada no golden do G1"
    for f in fontes:
        assert f.read_bytes()[:4] == b"wOF2", f.name
    css = (g1 / "fontes" / "fontes.css").read_text(encoding="utf-8")
    assert "Inter Tight" in css and "gstatic" not in css
    for nome in re.findall(r"url\(([^)]+)\)", css):
        assert (g1 / "fontes" / nome.strip("'\"")).is_file(), nome


def test_g2_timeline_e_trilha():
    tl = ler(GOLDEN / "G2" / "timeline.json")
    assert tl["fps"] == 30 and tl["totalFrames"] == 1275
    assert [c["id"] for c in tl["cenas"]][:3] == ["corrida", "loop", "milhao"] and len(tl["cenas"]) == 10
    assert [(c["inicio"], c["dur"]) for c in tl["cenas"]][:2] == [(0, 166), (166, 122)]
    assert len(tl["blocos"]) == 62
    with wave.open(str(GOLDEN / "G2" / "trilha.wav")) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (44100, 2, 2)
        assert abs(w.getnframes() / 44100 - (1275 / 30 + 0.5)) < 0.01


def test_g3_legendas_do_reel_de_pagina():
    g3 = GOLDEN / "G3"
    leg = ler(g3 / "legendas.json")
    assert leg["cta"] == "FIRECRAWL" and leg["offset_audio"] == 0.6
    blocos = sorted((g3 / "caps").glob("[0-9][0-9][0-9].png"))
    assert len(blocos) == leg["blocos"]
    assert (g3 / "caps" / "end.png").is_file() and (g3 / "caps" / "blank.png").is_file()
    citados = re.findall(r"^file '([^']+)'$", (g3 / "caps.txt").read_text(), re.M)
    assert citados and all((g3 / c).is_file() for c in citados)
    for nome in ("alignment.json", "roteiro.txt", "cta.txt"):
        assert (g3 / "entradas" / nome).is_file(), nome


def test_g4_montagem_e_alma_golden_reel():
    g4 = GOLDEN / "G4"
    probe = ler(g4 / "ffprobe.json")
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    assert (video["width"], video["height"], video["r_frame_rate"]) == (1080, 1920, "30/1")
    assert audio["sample_rate"] == "48000"
    leg = ler(GOLDEN / "G3" / "legendas.json")
    assert 0 < float(probe["format"]["duration"]) <= leg["duracao"] + 0.1
    assert (g4 / "firecrawl-firecrawl.mp4").stat().st_size > 100_000
    for nome in ("strip.png", "captura.json", "narracao.mp3", "impacto.txt"):
        assert (g4 / "entradas" / nome).is_file(), nome

    alma = ler(g4 / "alma-golden-reel.json")
    cores = alma["visual"]["cores"]
    assert set(cores) == set(PAPEIS)
    # cores de captions.py/compose.py: texto branco, CTA verde, caixa preta, cartão amarelo
    assert cores["texto_inverso"].upper() == "#FFFFFF" and cores["destaque"].upper() == "#3FB950"
    assert cores["fundo"] == "#000000" and cores["destaque_2"].upper() == "#FFD400"
    for papel in ("titulo", "texto"):
        f = alma["visual"]["fontes"][papel]
        # D-47: fonte local do sistema usada na origem, só nos testes, sem cópia no repositório
        assert f["origem"] == "local" and f["arquivo"].endswith("Arial Black.ttf")


def test_g5_legendas_de_aula():
    g5 = GOLDEN / "G5"
    legendas = ler(g5 / "legendas.json")
    assert legendas and all(1 <= len(c["lines"]) <= 2 and all(len(l) <= 42 for l in c["lines"]) for c in legendas)
    assert all(c["start"] < c["end"] for c in legendas)
    srt = (g5 / "radar-ia-09-jev-calibracao.srt").read_text(encoding="utf-8")
    assert len(re.findall(r"^\d\d:\d\d:\d\d,\d{3} --> \d\d:\d\d:\d\d,\d{3}$", srt, re.M)) == len(legendas)
    cues = ler(g5 / "cues.json")
    assert cues["duration"] > 0 and cues["cues"]
    assert (g5 / "entradas" / "roteiro.txt").is_file() and (g5 / "entradas" / "narracao.whisper.json").is_file()


def test_g6_g7_g8():
    deck = ler(GOLDEN / "G6" / "deck.json")
    assert deck

    g7 = GOLDEN / "G7"
    cand = ler(g7 / "candidatos.json")
    primeiro = cand["candidatos"][0]
    assert primeiro["inicio"] < primeiro["fim"] and primeiro["texto"]
    recasado = ler(g7 / "alignment.recasado.json")
    roteiro = (g7 / "roteiro.txt").read_text(encoding="utf-8").rstrip("\n")
    assert "".join(recasado["characters"]) == roteiro
    whisper = ler(g7 / "alignment.whisper.json")
    assert len(whisper["characters"]) == len(whisper["character_start_times_seconds"])
    assert ler(g7 / "transcricao_corte.json")["palavras"] and ler(g7 / "transcricao.json")["palavras"]

    al = ler(GOLDEN / "G8" / "alignment.json")
    assert len(al["characters"]) == len(al["character_end_times_seconds"]) > 100
    assert (GOLDEN / "G8" / "narracao.mp3").read_bytes()[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3")


# ------------------------------------------------------------------ integração


def _carregar_gerador():
    spec = importlib.util.spec_from_file_location("gerar_golden_t0107", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_copia_recusa_destino_na_origem_e_env(tmp_path):
    gg = _carregar_gerador()
    projetos = tmp_path / "projects"
    (projetos / "Proj").mkdir(parents=True)
    (projetos / "Proj" / "a.txt").write_text("x")
    (projetos / "Proj" / ".env").write_text("SEGREDO=1")
    with pytest.raises(gg.ErroGolden):
        gg.Origens(projetos, projetos / "Proj" / "copia")
    org = gg.Origens(projetos, tmp_path / "copia")
    org.copiar("Proj/a.txt")
    assert (tmp_path / "copia" / "Proj" / "a.txt").read_text() == "x"
    with pytest.raises(gg.ErroGolden):
        org.copiar("Proj/.env")
    assert org.conferir() == []
    (projetos / "Proj" / "a.txt").write_text("mudou")
    assert org.conferir() == ["Proj/a.txt"]


@pytest.mark.integracao_local
def test_gerador_roda_em_copia_e_nao_toca_a_origem(manifesto, tmp_path, requer_binario):
    requer_binario("ffprobe")
    alvo = ("G5", "G7")
    lidos = sorted({c["caminho"] for gid in alvo for c in manifesto["goldens"][gid]["codigo"] + manifesto["goldens"][gid]["entradas"]})
    faltando = [c for c in lidos if not (PROJETOS / c).is_file()]
    if faltando:
        pytest.skip(f"projetos de origem ausentes nesta máquina: {faltando[:3]}")
    # além dos arquivos lidos, toda pasta de origem onde o código roda: uma execução no lugar
    # (em vez da cópia) gravaria candidatos.json, alignment.json, src/ ou out/ ali dentro
    pastas = {(PROJETOS / c).parent for c in lidos}

    def retrato():
        estado = {}
        for pasta in pastas:
            for arq in pasta.rglob("*"):
                if arq.is_file() and not {"node_modules", "__pycache__"} & set(arq.relative_to(pasta).parts):
                    estado[str(arq.relative_to(PROJETOS))] = sha256(arq)
        return estado

    antes = retrato()
    assert set(lidos) <= set(antes)

    r = subprocess.run([sys.executable, str(SCRIPT), "--so", ",".join(alvo), "--saida", str(tmp_path / "golden")],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]

    assert retrato() == antes
    novo = ler(tmp_path / "golden" / "manifesto.json")
    for gid in alvo:
        assert novo["goldens"][gid]["origem_intacta"]["iguais"] is True
        assert set(novo["goldens"]) == set(alvo)
        # a mesma entrada no mesmo código dá a mesma saída do golden versionado
        gravado = {a["caminho"]: a["sha256"] for a in manifesto["goldens"][gid]["arquivos"]}
        for a in novo["goldens"][gid]["arquivos"]:
            assert gravado.get(a["caminho"]) == a["sha256"] == sha256(tmp_path / "golden" / a["caminho"]), a["caminho"]
