"""Vitrine do README: peças reais produzidas pelo núcleo, sem mockup.

Monta uma instalação temporária com a Alma fictícia da suíte (tests/fixtures/alma-ficticia, uma
padaria de bairro), semeia o cache de fontes como `tests/fixtures/fontes_ficticias.py` faz (a
Inter embarcada declarada com o nome das famílias da Alma), liga só o provedor de teste
(`EXPXMEDIA_PROVEDORES_TESTE=1`) e produz cada peça pelo CLI, em subprocesso:

    uv run expxmedia-motor produzir <tipo> --entrada <arquivo> --raiz <instalação>

Depois converte as saídas em imagens leves para o GitHub em `.github/assets/vitrine/` (PNG
quantizado pelo Pillow, GIF pelo ffmpeg com palettegen/paletteuse) e grava `manifesto.json` com
o tipo de peça, o template, o comando, as dimensões e o tamanho de cada arquivo.

Nenhuma chamada paga e nenhuma rede além do local: a narração é o sinal sintético do provedor de
teste, as fontes vêm do cache semeado e o render é local (Playwright e Remotion).

    cd motor && uv run python scripts/gerar_vitrine.py
    cd motor && uv run python scripts/gerar_vitrine.py --trabalho /tmp/vitrine   # reaproveita produções
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

from expxmedia.alma.fontes import PASTA_INTER
from expxmedia.nucleo.ids import slug

MOTOR = Path(__file__).resolve().parents[1]
REPO = MOTOR.parent
ALMA_FICTICIA = MOTOR / "tests" / "fixtures" / "alma-ficticia" / "alma"
DESTINO = REPO / ".github" / "assets" / "vitrine"
REEL_REFERENCIA = (REPO / "docs" / "nucleo-expxmedia" / "validacao" / "reel-por-referencia" / "pecas" / "2026-09"
                   / "P-20260925-66DE-ref-validacao" / "saida" / "final.mp4")
TIMEOUT = 1500
LIMITE_GIF = 4 * 1024 * 1024
LIMITE_PNG = 600 * 1024

# ---------------------------------------------------------------- conteúdo de exemplo (padaria)

ASSINATURA = "@padariatrigodourado"
RODAPE = "Trigo Dourado"
ROTULOS = ["Fornada", "Bairro", "Receita"]

POST = {
    "template": "post_unico-numero-e-frase-86c9ac",
    "titulo": "Quarenta e oito horas de descanso",
    "slides": [{
        "kind": "numero",
        "etiqueta": "Fermentação natural",
        "numero": "48h",
        "texto": "de descanso antes do forno. É isso que deixa a casca fina e o miolo macio até o dia seguinte.",
        "itens": ["Farinha", "Água", "Sal", "Levain", "Tempo", "Forno", "Mãos", "Cuidado"],
        "assinatura": ASSINATURA,
    }],
    "legenda": "Quarenta e oito horas de descanso em cada pão. A fornada das 16h sai em breve. Quer que a gente separe o seu?",
}

SLIDES_CARROSSEL = [
    {
        "kind": "capa",
        "rotulos": ROTULOS,
        "chapeu": "Pão de verdade leva tempo",
        "titulo": "SEM PRESSA",
        "microcopy_esq": "Edição 01\nO que acontece\nantes das 6h",
        "microcopy_dir": "Parte 1 de 4\nLeia até o fim\ne salve.",
        "cursiva": "Levain",
        "rodape": RODAPE,
    },
    {
        "kind": "conteudo",
        "rotulos": ROTULOS,
        "palavra": "Descanso",
        "destaque": "A massa dorme 48 horas antes de ir ao forno.",
        "texto": "É esse tempo que deixa a casca crocante e o miolo úmido até o café do dia seguinte.",
        "rodape": RODAPE,
    },
    {
        "kind": "conteudo",
        "rotulos": ROTULOS,
        "palavra": "Fornada",
        "destaque": "Duas fornadas por dia: às 6h e às 16h.",
        "texto": "Quem chega na hora leva o pão ainda morno. Quem assina encontra o seu separado no balcão.",
        "rodape": RODAPE,
    },
    {
        "kind": "cta",
        "rotulos": ROTULOS,
        "col_esq": "Pão bom não se faz correndo.",
        "col_dir": "Separe o seu da fornada das 16h.",
        "rodape": RODAPE,
    },
]

CARROSSEL = {
    "template": "carrossel-editorial-b74228",
    "titulo": "Sem pressa",
    "slides": SLIDES_CARROSSEL,
    "legenda": ("Sem pressa.\n\nNa Trigo Dourado a massa descansa 48 horas antes do forno. "
                "A fornada das 16h sai todo dia. Salve para lembrar do horário."),
}

CARROSSEL_MISTO = {
    **CARROSSEL,
    "titulo": "Sem pressa em movimento",
    "slides": [{
        "kind": "abertura", "midia": "video", "etiqueta": "Fornada das 16h",
        "titulo": "Da bancada ao forno em 48 horas",
        "texto": "Farinha, água, sal e tempo. O resto é paciência de padeiro.",
        "duracao_s": 5,
    }] + SLIDES_CARROSSEL[1:],
}

CTA_REEL = "FORNADA"
ROTEIRO_REEL = (
    "Sabe aquele pão que endurece antes do jantar? Ele foi feito com pressa. "
    "Aqui na Trigo Dourado a massa descansa quarenta e oito horas antes de ir ao forno. "
    "É esse tempo que deixa a casca fina e o miolo úmido até o dia seguinte. "
    "O processo tem três etapas simples. Primeiro a gente alimenta o levain bem cedo. "
    "Depois mistura só farinha, água e sal. No fim a massa descansa na geladeira até a hora da fornada. "
    "Pão feito com pressa endurece no mesmo dia. Pão feito com tempo continua macio no café da manhã. "
    "Fermentação natural não é moda. É o jeito mais antigo de fazer um pão que dura. "
    "A fornada das dezesseis horas sai todo dia quentinha. Quer saber os horários da semana? "
    f"Comenta {CTA_REEL} aqui embaixo que a gente te manda. E passa aqui para levar o seu fresquinho."
)

REEL = {
    "template": "reel-narrado-cartao-870a5c",
    "titulo": "Por que o nosso pão não endurece",
    "roteiro": ROTEIRO_REEL,
    "cta": CTA_REEL,
    "cenas": [
        {"kind": "abertura", "ancora": "Sabe aquele pão", "etiqueta": ["O PÃO QUE", "ENDURECE"],
         "titulo": "O pão que endurece antes do jantar", "apoio": "Ele foi feito com pressa"},
        {"kind": "numero", "ancora": "Aqui na Trigo", "etiqueta": ["FERMENTAÇÃO", "NATURAL"],
         "valor": "48h", "texto": "de descanso antes de ir ao forno"},
        {"kind": "lista", "ancora": "O processo tem", "etiqueta": ["O PROCESSO", "TRÊS ETAPAS"],
         "titulo": "Três etapas simples",
         "itens": ["Alimente o levain cedo", "Farinha, água e sal", "Descanso até a fornada"]},
        {"kind": "contraste", "ancora": "Pão feito com pressa", "etiqueta": ["COM PRESSA", "OU COM TEMPO"],
         "rotulo_a": "Com pressa", "texto_a": "Endurece no mesmo dia",
         "rotulo_b": "Com tempo", "texto_b": "Macio no café da manhã"},
        {"kind": "frase", "ancora": "Fermentação natural não", "etiqueta": ["A IDEIA", "QUE FICA"],
         "texto": "Fermentação natural é o jeito mais antigo de fazer um pão que dura.",
         "marca": "um pão que dura"},
        {"kind": "cta", "ancora": "A fornada das", "etiqueta": ["A FORNADA", "DAS 16H"],
         "texto": f"Comenta {CTA_REEL}", "apoio": "e receba os horários da semana"},
    ],
    "legenda": f"Por que o nosso pão não endurece antes do jantar. Comenta {CTA_REEL} que a gente te manda os horários.",
    "conteudo": {"gancho": "Sabe aquele pão que endurece antes do jantar?", "gancho_tipo": "pergunta",
                 "cta_forma": "comentario"},
}

DECK = {
    "titulo": "Assinatura do pão da semana",
    "tema": None,
    "slides": [
        {"tipo": "titulo", "kicker": "Padaria Trigo Dourado",
         "titulo": "Pão fresco na mesa, <b>sem fila</b>",
         "subtitulo": "Como funciona a assinatura do pão da semana para famílias e escritórios do bairro"},
        {"tipo": "declaracao", "texto": "Pão bom não é o mais caro. É o que sai do forno <b>na hora certa</b>",
         "autor": "Rosa Farinha, padeira"},
        {"tipo": "comparacao", "titulo": "Pão de mercado contra pão da fornada",
         "esquerda": {"titulo": "Pão de mercado",
                      "itens": ["Endurece no mesmo dia", "Fila no horário de pico", "Conservante para durar"]},
         "direita": {"titulo": "Pão da fornada",
                     "itens": ["Macio até o café seguinte", "Separado com o seu nome", "Farinha, água, sal e tempo"]}},
        {"tipo": "etapas", "titulo": "A assinatura em quatro passos",
         "itens": [
             {"titulo": "Escolha", "texto": "O pão da semana e os dias"},
             {"titulo": "Reserve", "texto": "Pelo site ou no balcão"},
             {"titulo": "Assamos", "texto": "Na fornada das 6h ou das 16h"},
             {"titulo": "Retire", "texto": "Separado com o seu nome"},
         ]},
        {"tipo": "estatisticas", "titulo": "A fornada em números",
         "numeros": [
             {"valor": 48, "sufixo": " h", "rotulo": "de fermentação natural", "fonte": "receita da casa"},
             {"valor": 2, "sufixo": "", "rotulo": "fornadas por dia", "fonte": "às 6h e às 16h"},
         ]},
        {"tipo": "grade", "titulo": "O que vem na assinatura",
         "itens": [
             {"titulo": "Pão do dia", "texto": "Um pão de fermentação natural por dia útil"},
             {"titulo": "Sem fila", "texto": "Retirada no balcão lateral, sem esperar"},
             {"titulo": "Troca livre", "texto": "Mude o pão da semana até domingo à noite"},
             {"titulo": "Pausa fácil", "texto": "Viajou? Pause a semana pelo site"},
         ]},
        {"tipo": "cta", "titulo": None, "texto": "Separe seu pão da próxima fornada",
         "url": "trigodourado.example/assinatura", "imagem": None},
    ],
}

AULA = {
    "template": "aula-padrao-5b1e7d",
    "titulo": "Levain em casa em três passos",
    "roteiro": ("[[s1]] Fazer pão de fermentação natural em casa é mais simples do que parece. "
                "Hoje você aprende o levain em três passos. "
                "[[s2]] Primeiro, misture farinha e água em partes iguais num pote de vidro. "
                "[[s3]] Depois, alimente a mistura todo dia no mesmo horário, sempre com a mesma medida. "
                "[[s4]] Por fim, use o levain quando ele dobrar de tamanho em até seis horas. "
                "Resumindo: mistura, rotina e ponto."),
    "cenas": [
        {"cue": "s1", "modo": "cena", "rotulo": "abertura", "titulo": "Levain em casa",
         "texto": "Três passos para o seu primeiro fermento natural."},
        {"cue": "s2", "modo": "cena", "rotulo": "passo 1", "titulo": "Farinha e água",
         "passo": "01 · mistura", "fato": "partes iguais\nnum pote de vidro"},
        {"cue": "s3", "modo": "cena", "rotulo": "passo 2", "titulo": "Alimente todo dia",
         "passo": "02 · rotina", "fato": "mesmo horário\nmesma medida"},
        {"cue": "s4", "modo": "cena", "rotulo": "resumo", "titulo": "Resumindo.",
         "itens": ["mistura em partes iguais", "rotina de alimentação", "ponto: dobrou de tamanho"]},
    ],
    "formatos": ["16:9", "9:16"],
    "avatar": None,
    "tela": None,
    "apresentacao": None,
    "serie": "Oficina de fermentação natural",
    "porta_voz": None,
}

# (nome da produção, subcomando, entrada, argumentos extras)
PRODUCOES = [
    ("post", "post", POST, []),
    ("carrossel", "carrossel", CARROSSEL, []),
    ("carrossel-misto", "carrossel", CARROSSEL_MISTO, []),
    ("apresentacao", "apresentacao", {"deck": DECK}, ["--mp4"]),
    ("reel", "reel", REEL, []),
    ("aula", "aula", AULA, []),
]

# ---------------------------------------------------------------- instalação e produção


def montar_instalacao(raiz: Path) -> Path:
    if raiz.exists():
        return raiz
    raiz.mkdir(parents=True)
    shutil.copytree(ALMA_FICTICIA, raiz / "alma")
    for pasta in ("pecas", "estado", "eventos"):
        (raiz / pasta).mkdir()
    (raiz / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    return raiz


def semear_fontes(cache: Path, familias=("Fraunces", "Nunito Sans")) -> None:
    """Mesmo cache de tests/fixtures/fontes_ficticias.py: a Inter embarcada com o nome das famílias da Alma."""
    pesos = {400: "inter-latin-400-normal.woff2", 700: "inter-latin-700-normal.woff2"}
    for familia in familias:
        pasta = cache / slug(familia)
        pasta.mkdir(parents=True, exist_ok=True)
        blocos = []
        for peso, nome in pesos.items():
            destino = pasta / nome
            shutil.copyfile(PASTA_INTER / nome, destino)
            blocos.append("@font-face {\n"
                          f"  font-family: '{familia}';\n  font-style: normal;\n  font-weight: {peso};\n"
                          f"  src: url('{destino.resolve().as_uri()}') format('woff2');\n}}")
        (pasta / "fontes.css").write_text("\n".join(blocos) + "\n", encoding="utf-8")
        (pasta / "arquivos.json").write_text(json.dumps(list(pesos.values())), encoding="utf-8")


_PREFIXOS_CHAVE = ("ELEVENLABS_", "HEYGEN_", "OPENROUTER_", "PEXELS_", "EXPXFLOW_", "META_", "PROVEDOR_",
                   "YOUTUBE_", "HIGGSFIELD_", "EXPXMEDIA_")


def ambiente(xdg: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(_PREFIXOS_CHAVE)}
    env["XDG_CACHE_HOME"] = str(xdg)
    env["HF_HUB_OFFLINE"] = "1"
    return env


def comando_publico(subcomando: str, nome: str, extra: list[str]) -> str:
    return " ".join(["uv run expxmedia-motor produzir", subcomando, "--entrada", f"entradas/{nome}.json",
                     *extra, "--raiz", "<instalação>"])


def produzir(trabalho: Path, raiz: Path, env: dict, nome: str, subcomando: str, dados: dict,
             extra: list[str]) -> dict:
    entradas = trabalho / "entradas"
    entradas.mkdir(exist_ok=True)
    resultado = trabalho / "resultados" / f"{nome}.json"
    arquivo = entradas / f"{nome}.json"
    texto = json.dumps(dados, ensure_ascii=False, indent=2)
    if resultado.is_file() and arquivo.is_file() and arquivo.read_text(encoding="utf-8") == texto:
        print(f"[vitrine] {nome}: reaproveitado", flush=True)
        return json.loads(resultado.read_text(encoding="utf-8"))
    arquivo.write_text(texto, encoding="utf-8")
    print(f"[vitrine] produzindo {nome}...", flush=True)
    feito = subprocess.run(
        ["uv", "run", "--project", str(MOTOR), "expxmedia-motor", "produzir", subcomando,
         "--entrada", str(arquivo), *extra, "--raiz", str(raiz)],
        cwd=entradas, capture_output=True, text=True, timeout=TIMEOUT, env=env,
    )
    try:
        saida = json.loads(feito.stdout)
    except json.JSONDecodeError:
        saida = None
    if feito.returncode != 0 or not saida or not saida.get("ok"):
        sys.exit(f"[vitrine] {nome} falhou (código {feito.returncode}):\n{(feito.stdout + feito.stderr)[-4000:]}")
    resultado.parent.mkdir(exist_ok=True)
    resultado.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    return saida


def peca_de(raiz: Path, saida: dict) -> tuple[dict, Path]:
    pasta = raiz / saida["pasta"]
    return json.loads((pasta / "peca.json").read_text(encoding="utf-8")), pasta


# ---------------------------------------------------------------- conversão


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def _paleta(filtros: str, cores: int = 256) -> str:
    return (f"{filtros},split[a][b];[a]palettegen=max_colors={cores}:stats_mode=diff[p];"
            "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle")


def gif_de_video(video: Path, destino: Path, inicio: float, duracao: float, largura: int, fps: int) -> None:
    for cores in (256, 192, 128, 96):
        ff("-ss", f"{inicio}", "-t", f"{duracao}", "-i", str(video),
           "-filter_complex", _paleta(f"fps={fps},scale={largura}:-1:flags=lanczos", cores), "-loop", "0",
           str(destino))
        if destino.stat().st_size <= LIMITE_GIF:
            return
    sys.exit(f"[vitrine] {destino.name} passou de 4 MB")


def gif_de_imagens(imagens: list[Path], destino: Path, segundos: float, largura: int) -> None:
    lista = destino.with_suffix(".txt")
    linhas = []
    for img in imagens:
        linhas += [f"file '{img}'", f"duration {segundos}"]
    linhas.append(f"file '{imagens[-1]}'")  # o concat ignora a duração do último
    lista.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    try:
        for cores in (256, 192, 128):
            ff("-f", "concat", "-safe", "0", "-i", str(lista),
               "-filter_complex", _paleta(f"fps=10,scale={largura}:-1:flags=lanczos", cores), "-loop", "0",
               str(destino))
            if destino.stat().st_size <= LIMITE_GIF:
                return
    finally:
        lista.unlink(missing_ok=True)
    sys.exit(f"[vitrine] {destino.name} passou de 4 MB")


def png_otimizado(origem: Path | Image.Image, destino: Path, largura: int) -> None:
    img = origem if isinstance(origem, Image.Image) else Image.open(origem)
    img = img.convert("RGB")
    if img.width != largura:
        img = img.resize((largura, round(img.height * largura / img.width)), Image.LANCZOS)
    for cores in (256, 192, 128, 96, 64):
        img.quantize(colors=cores, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(
            destino, optimize=True)
        if destino.stat().st_size <= LIMITE_PNG:
            return
    sys.exit(f"[vitrine] {destino.name} passou de 600 KB")


def quadro(video: Path, segundo: float, destino: Path) -> Path:
    ff("-ss", f"{segundo}", "-i", str(video), "-frames:v", "1", str(destino))
    return destino


def duracao(video: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def screenshot_html(html: Path, destino: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 1280, "height": 720})
        pagina.route("**/*", lambda rota: rota.continue_() if rota.request.url.startswith("file:")
                     else rota.abort())  # nada de rede: só o arquivo local
        pagina.goto(html.resolve().as_uri())
        pagina.wait_for_timeout(1500)
        pagina.screenshot(path=str(destino))
        navegador.close()


def finais(peca: dict) -> dict:
    return {a["formato"]: a["caminho"] for a in peca["arquivos"] if a["papel"] == "final"}


# ---------------------------------------------------------------- principal


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--trabalho", help="pasta de trabalho (padrão: temporária, apagada no fim)")
    ap.add_argument("--destino", default=str(DESTINO))
    a = ap.parse_args()

    temporaria = a.trabalho is None
    trabalho = Path(a.trabalho or tempfile.mkdtemp(prefix="vitrine-")).resolve()
    trabalho.mkdir(parents=True, exist_ok=True)
    destino = Path(a.destino).resolve()
    destino.mkdir(parents=True, exist_ok=True)
    tmp = trabalho / "conversao"
    tmp.mkdir(exist_ok=True)

    raiz = montar_instalacao(trabalho / "instalacao")
    xdg = trabalho / "xdg"
    semear_fontes(xdg / "expxmedia" / "fontes")
    env = ambiente(xdg)

    s = {nome: produzir(trabalho, raiz, env, nome, sub, dados, extra) for nome, sub, dados, extra in PRODUCOES}
    cmd = {nome: comando_publico(sub, nome, extra) for nome, sub, _, extra in PRODUCOES}
    manifesto: list[dict] = []

    def registrar(arquivo: Path, tipo: str, template: str | None, comando: str, descricao: str) -> None:
        with Image.open(arquivo) as img:
            w, h = img.size
            quadros = getattr(img, "n_frames", 1)
        manifesto.append({"arquivo": arquivo.name, "tipo": tipo, "template": template, "comando": comando,
                          "descricao": descricao, "largura": w, "altura": h, "quadros": quadros,
                          "bytes": arquivo.stat().st_size})
        print(f"[vitrine] {arquivo.name}: {w}x{h}, {arquivo.stat().st_size} bytes", flush=True)

    # carrossel: prancha e slides
    peca, pasta = peca_de(raiz, s["carrossel"])
    prancha = next(pasta / x["caminho"] for x in peca["arquivos"] if x["papel"] == "previa")
    png_otimizado(prancha, destino / "carrossel-prancha.png", 1600)
    registrar(destino / "carrossel-prancha.png", "carrossel", peca["template"], cmd["carrossel"],
              "prancha de conferência com os slides do carrossel")
    slides = [pasta / x["arquivo"] for x in peca["slides"]]
    gif_de_imagens(slides, destino / "carrossel-slides.gif", 1.2, 540)
    registrar(destino / "carrossel-slides.gif", "carrossel", peca["template"], cmd["carrossel"],
              "os slides do carrossel em sequência, 1,2 s cada")

    # post único
    peca, pasta = peca_de(raiz, s["post"])
    png_otimizado(pasta / peca["slides"][0]["arquivo"], destino / "post-unico.png", 540)
    registrar(destino / "post-unico.png", "post_unico", peca["template"], cmd["post"], "post único")

    # carrossel misto: o slide de vídeo
    peca, pasta = peca_de(raiz, s["carrossel-misto"])
    video = pasta / next(x["arquivo"] for x in peca["slides"] if x["midia"] == "video")
    gif_de_video(video, destino / "carrossel-misto.gif", 0, duracao(video), 432, 12)
    registrar(destino / "carrossel-misto.gif", "carrossel", peca["template"], cmd["carrossel-misto"],
              "slide de vídeo do carrossel misto (Remotion)")

    # reel narrado: trecho com a legenda por blocos
    peca, pasta = peca_de(raiz, s["reel"])
    video = pasta / finais(peca)["9:16"]
    gif_de_video(video, destino / "reel.gif", 21.5, 10.0, 300, 12)
    registrar(destino / "reel.gif", "reel", peca["template"], cmd["reel"],
              "trecho de 10 s do reel narrado (contraste e frase) com a legenda por blocos")

    # apresentação: PNG por slide e o palco HTML
    peca, pasta = peca_de(raiz, s["apresentacao"])
    pngs = sorted(p for p in pasta.rglob("*.png") if "slide" in p.name.lower())
    escolhidos = [pngs[i] for i in (0, 1, 2, 6) if i < len(pngs)]
    gif_de_imagens(escolhidos, destino / "apresentacao.gif", 1.5, 720)
    registrar(destino / "apresentacao.gif", "apresentacao", peca["template"], cmd["apresentacao"],
              "quatro slides da apresentação, 1,5 s cada")
    html = pasta / "saida" / "apresentacao.html"
    screenshot_html(html, tmp / "palco.png")
    png_otimizado(tmp / "palco.png", destino / "apresentacao-palco.png", 720)
    registrar(destino / "apresentacao-palco.png", "apresentacao", peca["template"], cmd["apresentacao"],
              "apresentacao.html aberto no navegador (1280x720)")

    # aula: um quadro de cada formato
    peca, pasta = peca_de(raiz, s["aula"])
    for formato, nome, largura, fracao in (("16:9", "aula-16x9.png", 960, 0.42), ("9:16", "aula-9x16.png", 432, 0.9)):
        video = pasta / finais(peca)[formato]
        quadro(video, duracao(video) * fracao, tmp / nome)
        png_otimizado(tmp / nome, destino / nome, largura)
        registrar(destino / nome, "aula", peca["template"], cmd["aula"], f"um quadro da aula em {formato}")

    # reel por referência: render já produzido na validação do núcleo
    # Os 8,5 s iniciais: o gancho, sem o avatar do provedor de teste (padrão de barras), que
    # aparece nos trechos em que a referência tinha apresentador.
    gif_de_video(REEL_REFERENCIA, destino / "reel-referencia.gif", 0.0, 8.5, 300, 12)
    registrar(destino / "reel-referencia.gif", "reel", "sob medida (reel por referência)",
              "uv run expxmedia-motor referencia render --pasta <peça>",
              "gancho de 8,5 s do reel por referência da validação do núcleo, sem o avatar de teste")

    (destino / "manifesto.json").write_text(json.dumps({
        "gerado_por": "motor/scripts/gerar_vitrine.py",
        "empresa": "Padaria Trigo Dourado (Alma fictícia de motor/tests/fixtures/alma-ficticia)",
        "provedores": "EXPXMEDIA_PROVEDORES_TESTE=1, sem chave e sem rede",
        "arquivos": manifesto,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if temporaria:
        shutil.rmtree(trabalho, ignore_errors=True)
    print(f"[vitrine] pronto: {destino}")


if __name__ == "__main__":
    main()
