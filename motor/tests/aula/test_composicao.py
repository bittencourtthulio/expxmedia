"""T-07.04: composição de aula `Aula` do kit, layouts L16 e L9 (D-23, D-32, M13).

Porta de cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx com o conteúdo da aula vindo por props
(cenas, cues, legendas, tela, avatar) e a marca vindo da Alma (cores, fontes e o nome do porta-voz
no rótulo da janela do avatar).

- Integração: 2 s da composição renderizados nos dois formatos saem em MP4 1920x1080 e 1080x1920.
- Funcional: as constantes de layout são as calibradas da origem (SAFE 168/280, PiP 272x340 com topo
  em 1318 no 9:16), o PiP aparece de fato nessa posição no quadro renderizado, e o rótulo da janela
  do avatar muda com o nome do porta-voz da Alma (nada fixo no código).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from expxmedia.motion import remotion
from expxmedia.video import ffmpeg

pytestmark = pytest.mark.integracao_local

KIT = remotion.KIT
AULA = KIT / "src" / "composicoes" / "Aula"
CORES = {
    "fundo": "#F2EEE4", "fundo_alt": "#FAFAF7", "texto": "#1B2A3A", "texto_inverso": "#FFFFFF",
    "apoio": "#5A6B7C", "destaque": "#D9822B", "destaque_2": "#3C7A5A", "positivo": "#2E9E5B",
    "negativo": "#C0392B",
}
INTER = Path(__file__).resolve().parents[2] / "src" / "expxmedia" / "recursos" / "fontes" / "Inter"


def _hex(cor: str) -> tuple[int, int, int]:
    return tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))


def _perto(px, cor: str, tol: int = 12) -> bool:
    return all(abs(int(a) - b) <= tol for a, b in zip(px[:3], _hex(cor)))


def _sondar_layouts(tmp_path: Path) -> dict:
    """Empacota layouts.ts com o esbuild do kit e imprime as constantes em JSON."""
    node = shutil.which("node")
    assert node, "node ausente"
    codigo = (f'import * as L from "{(AULA / "layouts.ts").as_posix()}";\n'
              "console.log(JSON.stringify({SAFE: L.SAFE, L16: L.L16, L9: L.L9, PIP_BAR: L.PIP_BAR,"
              " TELA_BAR: L.TELA_BAR, AVATAR: L.AVATAR, FOLGA_FINAL_S: L.FOLGA_FINAL_S,"
              " FADE_PIP_QUADROS: L.FADE_PIP_QUADROS, LAYOUTS: Object.keys(L.LAYOUTS)}));\n")
    saida = tmp_path / "sonda.cjs"
    r = subprocess.run([str(KIT / "node_modules" / ".bin" / "esbuild"), "--bundle", "--platform=node", "--loader=ts",
                        "--format=cjs", f"--outfile={saida}", "--log-level=error"],
                       input=codigo, cwd=KIT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    r = subprocess.run([node, str(saida)], cwd=KIT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _publico(tmp_path: Path, *, avatar: bool = True, tela: bool = True) -> Path:
    publico = tmp_path / "publico"
    (publico / "fontes").mkdir(parents=True)
    shutil.copyfile(INTER / "inter-latin-400-normal.woff2", publico / "fontes" / "texto.woff2")
    shutil.copyfile(INTER / "inter-latin-700-normal.woff2", publico / "fontes" / "titulo.woff2")
    if avatar:  # o avatar tem a forma do que o HeyGen devolve: 1080x1350
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1080x1350:rate=25",
                        "-t", "3", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        str(publico / "avatar.mp4")], check=True, capture_output=True)
    if tela:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30",
                        "-t", "2", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        str(publico / "demo.mp4")], check=True, capture_output=True)
    return publico


def _props(formato: str, *, nome: str | None = "Rosa Farinha", avatar: bool = True, tela: bool = True,
           duracao: float = 2.0) -> dict:
    alma = {
        "cores": dict(CORES),
        "fontes": {"titulo": {"familia": "Titulo Teste", "arquivos": [{"caminho": "fontes/titulo.woff2", "peso": 700, "estilo": "normal"}]},
                   "texto": {"familia": "Texto Teste", "arquivos": [{"caminho": "fontes/texto.woff2", "peso": 400, "estilo": "normal"}]}},
        "porta_voz": {"id": "porta-voz-teste", "nome": nome, "retrato": None} if nome is not None else None,
        "canal": None,
    }
    demo = {"inicio": 1.0, "duracao": 1.0, "segmentos": [
        {"cue": "s2", "de": 0.0, "ate": 1.0, "rate": 2.0, "janela": "editor · projeto",
         "camera": [{"t": 0.0, "cx": 700}], "crop": {"x": 0, "y": 0, "w": 1920, "h": 1080},
         "crop9": {"x": 0, "y": 0, "w": 1920, "h": 1080}}],
        "camera": [{"t": 0.0, "cx": 700}]}
    return {
        "alma": alma,
        "formato": formato,
        "serie": "Série de teste",
        "titulo": "Aula de teste",
        "cues": {"duration": duracao, "cues": {"s1": 0.0, "s2": 1.0}},
        "cenas": [
            {"cue": "s1", "modo": "cena", "rotulo": "abertura", "titulo": "Uma aula curta", "texto": "com dois passos",
             "itens": ["primeiro", "segundo"], "passo": None, "fato": None, "imagem": None},
            {"cue": "s2", "modo": "tela" if tela else "cena", "rotulo": "passo 1", "titulo": "Na tela", "texto": None,
             "itens": [], "passo": "01 · projeto", "fato": "abrir a pasta\nrodar o comando", "imagem": None},
        ],
        "legendas": [{"start": 0.0, "end": 0.9, "lines": ["Uma aula curta,", "com dois passos."]},
                     {"start": 1.0, "end": 1.95, "lines": ["Agora na tela."]}],
        "narracao": None,
        "avatar": "avatar.mp4" if avatar else None,
        "tela": {"video": "demo.mp4", "demo": demo} if tela else None,
    }


# ---------------------------------------------------------------- integração


@pytest.mark.parametrize("formato,dimensao", [("16:9", (1920, 1080)), ("9:16", (1080, 1920))])
def test_render_de_2_s_nos_dois_formatos(tmp_path, requer_binario, formato, dimensao):
    for b in ("node", "ffmpeg", "ffprobe"):
        requer_binario(b)
    publico = _publico(tmp_path)
    mp4 = remotion.renderizar("Aula", tmp_path / f"aula-{formato.replace(':', 'x')}.mp4", _props(formato),
                              public_dir=publico)
    info = ffmpeg.sondar(mp4)
    assert (info["largura"], info["altura"]) == dimensao
    assert info["fps"] == "30/1"
    assert abs(info["duracao"] - 2.0) < 0.1, info


# ---------------------------------------------------------------- funcional


def test_constantes_de_layout_sao_as_calibradas_da_origem(tmp_path, requer_binario):
    requer_binario("node")
    c = _sondar_layouts(tmp_path)
    # origem: cursos-ia/aula-skills/src/Aula9x16.tsx:37
    assert c["SAFE"] == {"top": 168, "right": 56, "bottom": 280, "left": 56}
    l9, l16 = c["L9"], c["L16"]
    assert (l9["largura"], l9["altura"], l16["largura"], l16["altura"]) == (1080, 1920, 1920, 1080)
    # PiP 272x340, centrado, topo em 1318 no 9:16; 380x440 na coluna direita do 16:9
    assert l9["pip"] == {"left": 404, "top": 1318, "w": 272, "h": 340}
    assert l16["pip"] == {"left": 1484, "top": 500, "w": 380, "h": 440}
    # a área das cenas do 9:16 começa na faixa segura e termina 760 px acima da base
    assert l9["pad"] == "168px 56px 760px 56px" and l16["pad"] == "120px 440px 170px 110px"
    assert l9["tela"] == {"left": 56, "top": 168 + 34, "w": 968, "h": 962}
    assert l16["tela"] == {"left": 48, "top": 96 + 34, "w": 1392, "h": 783}
    assert l9["legenda"] == {"left": 56, "width": 968, "top": 1198} and l9["legendaFonte"] == 32
    assert l16["legenda"] == {"left": 48, "width": 1392, "bottom": 44} and l16["legendaFonte"] == 28
    assert l16["cartao"] == {"left": 1484, "top": 130, "w": 380} and l9["cartao"] is None
    assert (c["PIP_BAR"], c["TELA_BAR"], c["FOLGA_FINAL_S"], c["FADE_PIP_QUADROS"]) == (30, 34, 1.5, 15)
    assert c["AVATAR"] == {"largura": 1080, "altura": 1350, "conteudo_h": 607.5}
    assert sorted(c["LAYOUTS"]) == ["16:9", "9:16"]


def test_pip_no_topo_1318_e_rotulo_do_porta_voz_da_alma(tmp_path, requer_binario):
    for b in ("node", "ffmpeg", "ffprobe"):
        requer_binario(b)
    publico = _publico(tmp_path, tela=False)
    quadro = 15  # s1; o PiP vai até duração - 1,5 s (= quadro 75); a legenda do 9:16 fica em 1198, acima dele
    feitos = {}
    for nome in ("Rosa Farinha", "Joaquim Alvarenga Pereira"):
        pasta = tmp_path / nome.split()[0]
        png, = remotion.stills("Aula", [quadro], pasta, _props("9:16", nome=nome, tela=False, duracao=4.0), public_dir=publico)
        feitos[nome] = np.asarray(Image.open(png).convert("RGB")).astype(int)
    img = feitos["Rosa Farinha"]
    assert img.shape == (1920, 1080, 3)
    texto, fundo = CORES["texto"], CORES["fundo"]
    # barra de título do PiP (cor texto da Alma) começa em y=1318, x=404, e acaba em x=404+272
    assert _perto(img[1318 + 3, 404 + 3], texto), img[1321, 407]
    assert _perto(img[1318 + 3, 404 + 272 - 4], texto), img[1321, 672]
    assert not _perto(img[1318 - 6, 540], texto), "algo da cor da barra acima do topo 1318"
    assert _perto(img[1318 - 6, 540], fundo), img[1312, 540]
    assert _perto(img[1330, 404 - 8], fundo), "o PiP começa antes de x=404"
    # abaixo da barra de 30 px está o vídeo do avatar (não a cor da barra)
    assert not _perto(img[1318 + 30 + 150, 540], texto)
    # o rótulo muda com o nome do porta-voz; fora da barra do PiP o quadro é o mesmo
    outro = feitos["Joaquim Alvarenga Pereira"]
    barra = (slice(1318, 1318 + 30), slice(404, 404 + 272))
    assert np.abs(img[barra] - outro[barra]).sum() > 1000, "o rótulo do PiP não mudou com o nome do porta-voz"
    fora = np.abs(img - outro)
    fora[barra] = 0
    assert fora[:1318].max() <= 3, "a troca do porta-voz mexeu em algo além do rótulo do PiP"


def test_codigo_da_composicao_nao_carrega_marca_nem_cor():
    import re

    for arq in (AULA / "index.tsx", AULA / "layouts.ts"):
        texto = arq.read_text(encoding="utf-8")
        # só cinza neutro (r = g = b) no exemplo do Studio; cor de verdade vem da Alma
        cores = re.findall(r"#([0-9a-fA-F]{6})\b", texto)
        assert not re.search(r"#[0-9a-fA-F]{3}\b|#[0-9a-fA-F]{8}\b", texto)
        assert all(c[0:2] == c[2:4] == c[4:6] for c in cores), f"{arq.name} traz cor literal: as cores vêm da Alma"
        assert ".mov" not in texto, f"{arq.name} traz rótulo de janela fixo"
    index = (AULA / "index.tsx").read_text(encoding="utf-8")
    assert "porta_voz" in index and "useAlma" in index
