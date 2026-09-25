"""Adaptador de teste: o layout de origem do golden G1 vira um template do núcleo (D-16, D-20).

O golden G1 foi renderizado pelo `galeria.renderizar` de origem com o layout
`0001-pos-paineis-de-pagamento` e o `exemplo.json` dele. Para o núcleo renderizar as MESMAS
entradas, este adaptador:

- lê o layout direto da pasta de origem (somente leitura, D-37) e confere o sha256 de cada
  arquivo contra `golden/manifesto.json` — se a origem mudou, o teste para em vez de comparar
  entradas diferentes;
- troca o bloco `.slide.referencia { --x: #... }` do CSS pelo mapeamento de papéis gravado no
  manifesto do golden (`--claro` → `var(--alma-fundo)`, ...), e as famílias `--fonte-*` pelos
  tokens `--alma-fonte-*`. As variáveis sem papel ficam com a cor literal da origem: é código de
  teste, não template da galeria;
- copia os fragmentos `slides/*.html` como estão e converte `layout.json` em `template.json`
  (kinds, slots, fit e tipografia iguais);
- devolve a copy do `exemplo.json` (sem `layout` e `tema`, que o núcleo não usa).

Nada disto vive em `motor/src`: o núcleo não sabe que o layout de origem existe.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

TESTES = Path(__file__).resolve().parents[1]
GOLDEN = TESTES / "golden"
G1 = GOLDEN / "G1"
PROJETOS = TESTES.parents[2]  # a pasta que contém ExpxMedia e os projetos de origem
LAYOUT_ID = "0001-pos-paineis-de-pagamento"


def _manifesto_golden() -> dict:
    return json.loads((GOLDEN / "manifesto.json").read_text(encoding="utf-8"))["goldens"]["G1"]


def pasta_layout_origem() -> Path:
    return PROJETOS / "Instagram-Carrosseis" / "galeria" / "layouts" / LAYOUT_ID


def conferir_entradas() -> None:
    """Falha (AssertionError) se algum arquivo de entrada do G1 mudou ou sumiu na origem."""
    for entrada in _manifesto_golden()["entradas"]:
        caminho = PROJETOS / entrada["caminho"]
        assert caminho.is_file(), f"entrada do golden G1 ausente na origem: {entrada['caminho']}"
        sha = hashlib.sha256(caminho.read_bytes()).hexdigest()
        assert sha == entrada["sha256"], f"entrada do golden G1 mudou na origem: {entrada['caminho']} (regere o golden)"


def _css_com_tokens(css: str, papeis: dict[str, str]) -> str:
    por_variavel = {variavel: papel for papel, variavel in papeis.items()}
    bloco = re.search(r"\.slide\.referencia\s*\{([^}]*)\}", css)
    assert bloco, "o CSS do G1 não tem o bloco .slide.referencia"
    linhas = []
    for nome, valor in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", bloco.group(1)):
        if nome in por_variavel:
            valor = f"var(--alma-{por_variavel[nome]})"
        elif nome == "--fonte-titulo":
            valor = "var(--alma-fonte-titulo)"
        elif nome == "--fonte-texto":
            valor = "var(--alma-fonte-texto)"
        linhas.append(f"  {nome}: {valor.strip()};")
    novo = ".slide {\n" + "\n".join(linhas) + "\n}"
    return css[: bloco.start()] + novo + css[bloco.end():]


def montar_template(destino: Path) -> tuple[Path, dict]:
    """Escreve o template adaptado em `destino` e devolve (pasta do template, copy do exemplo)."""
    conferir_entradas()
    origem = pasta_layout_origem()
    layout = json.loads((origem / "layout.json").read_text(encoding="utf-8"))
    papeis = _manifesto_golden()["mapeamento_cores"]["papeis"]
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "template.css").write_text(_css_com_tokens((origem / "layout.css").read_text(encoding="utf-8"), papeis),
                                          encoding="utf-8")
    shutil.copytree(origem / "slides", destino / "slides", dirs_exist_ok=True)
    kinds = {}
    for nome, kind in layout["kinds"].items():
        kinds[nome] = {"midia": "imagem", "duracao_s": None, "fit": kind.get("fit"), "requisitos": [],
                       "slots": kind["slots"], **({"vazio_ok": True} if kind.get("vazio_ok") else {})}
    template = {
        "expxmedia_template": 1,
        "template_id": "post_unico-paridade-g1-000001",
        "titulo": "Paridade G1",
        "tipo": "post_unico",
        "motor": "html",
        "formato": "4:5",
        "canvas": layout["canvas"],
        "status": "rascunho",
        "estilos": [],
        "serve_para": [],
        "tokens": sorted(set(papeis)),
        "fontes": ["titulo", "texto"],
        "sequencia": [s["kind"] for s in layout["sequencia"]],
        "kinds": kinds,
        "fit": layout["fit"],
        "tipografia": layout["tipografia"],
    }
    (destino / "template.json").write_text(json.dumps(template, ensure_ascii=False, indent=1), encoding="utf-8")
    exemplo = json.loads((origem / "exemplo.json").read_text(encoding="utf-8"))
    copy = {"slides": exemplo["slides"]}
    return destino, copy


def alma_golden() -> dict:
    return json.loads((G1 / "alma-golden.json").read_text(encoding="utf-8"))


def render_golden() -> dict:
    return json.loads((G1 / "render.json").read_text(encoding="utf-8"))


def fontes_golden() -> tuple[str, dict[str, bytes]]:
    """(CSS do Google Fonts gravado no golden, {nome do woff2: bytes})."""
    pasta = G1 / "fontes"
    css = (pasta / "fontes.css").read_text(encoding="utf-8")
    return css, {p.name: p.read_bytes() for p in pasta.glob("*.woff2")}
