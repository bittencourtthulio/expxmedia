"""T-05.01: kit base do Remotion (anim, área segura, FPS único, Alma por props, selo de perfil).

- Funcional: o literal 30 como fps só aparece em src/kit/constantes.ts; a mecânica de anim.ts
  (rampa, mola, área segura 220–1500, centralizar com folga 16 e escala ≤ 1) roda em Node com os
  mesmos números da origem, e a mola usa o FPS da constante (não um 30 próprio).
- Integração: `tsc --noEmit` no kit termina sem erro e um still da composição TesteSelo sai com o
  anel na cor `destaque` da Alma fictícia (e nenhum resto da cor de marca da origem).
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

MOTOR = Path(__file__).resolve().parents[2]
KIT = MOTOR / "kit-remotion"
KIT_SRC = KIT / "src" / "kit"
ALMA_FICTICIA = MOTOR / "tests" / "fixtures" / "alma-ficticia"
INTER = MOTOR / "src" / "expxmedia" / "recursos" / "fontes" / "Inter"

# fps escrito como número: `fps: 30`, `fps={30}`, `FPS = 30`, `fps = 30`
RE_FPS_30 = re.compile(r"\bfps\b\s*(?:[:=]\s*\{?\s*)30\b", re.IGNORECASE)
# A composição Vazio é da T-01.05 (fora desta task); ela ainda declara `fps: 30` e fica
# registrada no relatório para migrar para a constante.
FORA_DESTA_TASK: set = set()  # a Vazio já usa FPS (corrigida pelo orquestrador)


def _fontes_do_kit():
    for raiz in (KIT / "src", KIT / "scripts"):
        for arq in sorted(raiz.rglob("*")):
            if arq.suffix in {".ts", ".tsx", ".mjs", ".js"} and "node_modules" not in arq.parts:
                if arq.name == "registro.generated.ts":
                    continue
                yield arq


# ---------------------------------------------------------------- funcional


def test_literal_30_como_fps_so_em_constantes():
    achados = []
    for arq in _fontes_do_kit():
        rel = arq.relative_to(KIT)
        if rel in FORA_DESTA_TASK:
            continue
        for n, linha in enumerate(arq.read_text(encoding="utf-8").splitlines(), 1):
            if RE_FPS_30.search(linha):
                achados.append(f"{rel}:{n}")
    assert len(achados) == 1 and achados[0].startswith("src/kit/constantes.ts:"), achados


def test_detector_de_fps_pega_as_formas_da_origem():
    # as três formas em que o 30 aparecia na origem (Root.tsx:14, anim.ts:11, montar-reel.mjs:31)
    for linha in ("fps={30}", "spring({ frame: f - inicio, fps: 30, config })", "const FPS = 30;"):
        assert RE_FPS_30.search(linha), linha
    assert not RE_FPS_30.search("fps: FPS")


def test_anim_e_selo_nao_carregam_marca_nem_fps_proprio():
    anim = (KIT_SRC / "anim.ts").read_text(encoding="utf-8")
    assert re.search(r"import\s*\{[^}]*\bFPS\b[^}]*\}\s*from\s*\"\./constantes\"", anim), "anim.ts precisa usar o FPS de constantes.ts"
    selo = (KIT_SRC / "SeloPerfil.tsx").read_text(encoding="utf-8")
    assert "useAlma" in selo
    assert "staticFile(\"marca/" not in selo, "retrato do porta-voz vem da Alma, não de caminho fixo"
    assert not re.search(r"#[0-9a-fA-F]{6}", selo), "selo não traz cor literal: as cores vêm dos papéis da Alma"


def _rodar_node_com_kit(tmp_path, codigo):
    """Empacota um script que importa src/kit/*.ts com o esbuild do kit e roda em Node."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("binário ausente: node")
    saida = tmp_path / "sonda.cjs"
    # pela entrada padrão o esbuild resolve "remotion" a partir do cwd (o kit)
    r = subprocess.run(
        [str(KIT / "node_modules" / ".bin" / "esbuild"), "--bundle", "--platform=node", "--loader=ts",
         "--format=cjs", f"--outfile={saida}", "--log-level=error"],
        input=codigo.replace("@kit/", str(KIT_SRC) + "/"), cwd=KIT, capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, r.stderr
    r = subprocess.run([node, str(saida)], cwd=KIT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.integracao_local
def test_mecanica_de_anim_com_os_numeros_da_origem(tmp_path):
    res = _rodar_node_com_kit(tmp_path, """
import { spring } from "remotion";
import { FPS } from "@kit/constantes";
import { AREA_SEGURA, centralizarNaArea, mola, rampa, clamp } from "@kit/anim";
const molas = [0, 5, 10, 20, 40].map((f) => mola(f, 3, 11, 170));
const ref30 = [0, 5, 10, 20, 40].map((f) => spring({ frame: f - 3, fps: 30, config: { damping: 11, stiffness: 170 } }));
const ref60 = [0, 5, 10, 20, 40].map((f) => spring({ frame: f - 3, fps: 60, config: { damping: 11, stiffness: 170 } }));
const padrao = mola(10, 0);
const refPadrao = spring({ frame: 10, fps: 30, config: { damping: 12, stiffness: 140 } });
console.log(JSON.stringify({
  FPS, AREA_SEGURA, clamp,
  rampa: [rampa(-5, 0, 10), rampa(5, 0, 10), rampa(50, 0, 10), rampa(5, 0, 10, 100, 200)],
  molas, ref30, ref60, padrao, refPadrao,
  cabe: centralizarNaArea(400, 1000),
  grande: centralizarNaArea(124, 1482),
  folga0: centralizarNaArea(0, 1920, 0),
}));
""")
    assert res["FPS"] == 30
    assert res["AREA_SEGURA"] == {"topo": 220, "base": 1500}
    assert res["clamp"] == {"extrapolateLeft": "clamp", "extrapolateRight": "clamp"}
    assert res["rampa"] == [0, 0.5, 1, 150]
    assert res["molas"] == pytest.approx(res["ref30"])
    assert res["molas"] != pytest.approx(res["ref60"])  # prova que a mola usa o FPS 30
    assert res["padrao"] == pytest.approx(res["refPadrao"])  # damping 12, stiffness 140 por padrão
    # bloco de 600 px cabe: só desce até o centro da área (860), sem escala
    assert res["cabe"] == {"transformOrigin": "540px 700px", "transform": "translateY(160px) scale(1)"}
    # bloco do reel aprovado (124–1482): encolhe para caber em 1280 − 2×16 px
    k = (1500 - 220 - 2 * 16) / (1482 - 124)
    grande = res["grande"]
    assert grande["transformOrigin"] == "540px 803px"
    m = re.fullmatch(r"translateY\(57px\) scale\(([0-9.]+)\)", grande["transform"])
    assert m and float(m.group(1)) == pytest.approx(k)
    m = re.fullmatch(r"translateY\(-100px\) scale\(([0-9.]+)\)", res["folga0"]["transform"])
    assert m and float(m.group(1)) == pytest.approx(1280 / 1920)


# ---------------------------------------------------------------- integração


def _npx():
    npx = shutil.which("npx")
    node = shutil.which("node")
    if npx is None or node is None:
        pytest.skip("binário ausente: npx/node")
    return npx, node


@pytest.mark.integracao_local
def test_tsc_no_kit_termina_sem_erro():
    npx, node = _npx()
    r = subprocess.run([node, "scripts/registrar.mjs"], cwd=KIT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "TesteSelo" in (KIT / "src" / "composicoes" / "registro.generated.ts").read_text(encoding="utf-8")
    r = subprocess.run([npx, "--no-install", "tsc", "--noEmit"], cwd=KIT, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr


def _props_alma(publico):
    """Props da TesteSelo a partir da Alma fictícia: cores por papel, fontes em arquivo, porta-voz e canal."""
    alma = json.loads((ALMA_FICTICIA / "alma" / "alma.json").read_text(encoding="utf-8"))
    pv = next(p for p in alma["porta_vozes"] if p["principal"])
    canal = next(c for c in alma["canais"] if c["canal"] == "instagram")
    (publico / "retratos").mkdir(parents=True)
    shutil.copy(ALMA_FICTICIA / pv["retratos"][0], publico / "retratos" / "porta-voz.png")
    (publico / "fontes").mkdir()
    arquivos = []
    for peso in (400, 700):
        nome = f"inter-latin-{peso}-normal.woff2"
        shutil.copy(INTER / nome, publico / "fontes" / nome)
        arquivos.append({"caminho": f"fontes/{nome}", "peso": peso, "estilo": "normal"})
    fonte = {"familia": "Inter", "arquivos": arquivos}
    return {
        "alma": {
            "cores": alma["visual"]["cores"],
            "fontes": {"titulo": fonte, "texto": fonte},
            "porta_voz": {"id": pv["id"], "nome": pv["nome"], "retrato": "retratos/porta-voz.png"},
            "canal": {"canal": canal["canal"], "identificador": canal["identificador"]},
        }
    }, alma


def _conta_cor(img, hexa, tol=6):
    alvo = tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))
    return sum(1 for px in img.get_flattened_data() if all(abs(a - b) <= tol for a, b in zip(px[:3], alvo)))


@pytest.mark.integracao_local
def test_still_da_composicao_teste_selo(tmp_path):
    npx, node = _npx()
    assert subprocess.run([node, "scripts/registrar.mjs"], cwd=KIT, capture_output=True, timeout=60).returncode == 0
    publico = tmp_path / "publico"
    props, alma = _props_alma(publico)
    arq_props = tmp_path / "props.json"
    arq_props.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    png = tmp_path / "selo.png"
    r = subprocess.run(
        [npx, "--no-install", "remotion", "still", "src/index.ts", "TesteSelo", str(png), "--frame=45",
         f"--props={arq_props}", f"--public-dir={publico}", "--log=error"],
        cwd=KIT, capture_output=True, text=True, timeout=900,
    )
    assert r.returncode == 0 and png.is_file(), (r.stdout + r.stderr)[-2000:]
    img = Image.open(png).convert("RGB")
    assert img.size == (1080, 1920)
    destaque = alma["visual"]["cores"]["destaque"]
    assert _conta_cor(img, destaque) > 300, f"anel do selo sem a cor destaque {destaque}"
    assert _conta_cor(img, "#E4602A", tol=3) == 0, "cor de marca da origem vazou para o selo"
    # fundo da composição = fundo_alt da Alma
    fundo_alt = alma["visual"]["cores"]["fundo_alt"]
    assert _conta_cor(img, fundo_alt, tol=2) > 1080 * 1000
