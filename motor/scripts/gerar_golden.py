"""Goldens do sistema atual (T-01.07, D-16, D-37, D-47).

Roda o código dos projetos de origem numa CÓPIA temporária e grava a saída de referência
em tests/golden/<G>/, com tests/golden/manifesto.json. Nada é escrito nos projetos de
origem: cada arquivo copiado de lá tem o sha256 anotado antes da execução e conferido
depois; se algum mudou, o script para com erro. O `.env` dos projetos nunca é lido.

    cd motor && uv run python scripts/gerar_golden.py                 # G1 a G8
    cd motor && uv run python scripts/gerar_golden.py --so G5,G7      # só alguns
    cd motor && uv run python scripts/gerar_golden.py --saida /tmp/g  # outra pasta

Rede: só o G1, para o Google Fonts do render do layout. Nenhuma chamada paga (D-15).
Os projetos de origem são procurados na pasta que contém o repositório (a pasta projects/)
ou em --origens.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import date
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
REPO = MOTOR.parent
PROJETOS = REPO.parent
GOLDEN = MOTOR / "tests" / "golden"
IDS = [f"G{n}" for n in range(1, 9)]

CARROSSEIS = "Instagram-Carrosseis"
VIDEOS = "Instragram-Videos"
CURSOS = "cursos-ia"
YOUTUBE = "youtube-squad"

LAYOUT_G1 = "0001-pos-paineis-de-pagamento"
REEL_G2 = "recriado-ia-decide"
VIDEO_G3 = "firecrawl-firecrawl"
AULA_G5 = "radar-ia-09-jev-calibracao"
DECK_G6 = "2026-09-24-claude-code-ficou-caro-quanto-custa-de-verdade-e"
CORTE_G7 = "yt-04hAay1cjyU-t0239"
FONTE_G7 = "04hAay1cjyU"
HOSTS_DE_FONTE = ("fonts.googleapis.com", "fonts.gstatic.com")
# D-47: a fonte de sistema que captions.py:30 e compose.py:80 usam. Só referenciada, nunca copiada.
FONTE_SISTEMA_ORIGEM = "/System/Library/Fonts/Supplemental/Arial Black.ttf"


class ErroGolden(Exception):
    pass


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def gravar_json(caminho, dados):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, caminho)


def _dentro(filho, pai):
    try:
        Path(filho).resolve().relative_to(Path(pai).resolve())
        return True
    except ValueError:
        return False


class Origens:
    """Cópia somente-leitura dos projetos de origem para uma pasta temporária.

    `copiar("Projeto/caminho")` reproduz o arquivo (ou a árvore) em `<copia>/Projeto/caminho`
    e anota o sha256 de cada arquivo lido. `conferir()` recalcula e devolve os que mudaram.
    """

    def __init__(self, raiz, copia):
        self.raiz = Path(raiz).resolve()
        self.copia = Path(copia).resolve()
        if _dentro(self.copia, self.raiz):
            raise ErroGolden(f"a cópia não pode ficar dentro dos projetos de origem (D-37): {self.copia}")
        self.lidos = {}

    def _anotar(self, rel):
        if any(parte.startswith(".env") for parte in Path(rel).parts):
            raise ErroGolden(f"o .env dos projetos de origem nunca é lido: {rel}")
        origem = self.raiz / rel
        if not origem.is_file():
            raise ErroGolden(f"arquivo de origem ausente: {rel}")
        self.lidos[rel] = sha256(origem)
        return origem

    def copiar(self, rel, ignorar=()):
        """Copia arquivo ou pasta; devolve a lista de caminhos relativos lidos."""
        origem = self.raiz / rel
        if origem.is_dir():
            lidos = []
            for arq in sorted(origem.rglob("*")):
                if not arq.is_file() or arq.is_symlink():
                    continue
                sub = arq.relative_to(self.raiz).as_posix()
                partes = Path(sub).relative_to(rel).parts
                if any(p in ignorar or p.startswith(".env") or p in ("__pycache__", "node_modules", ".DS_Store") for p in partes):
                    continue
                lidos += self.copiar(sub)
            return lidos
        self._anotar(rel)
        destino = self.copia / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
        return [rel]

    def ler(self, rel):
        """Lê um arquivo de origem sem copiar (conferência de igualdade), anotando o sha256."""
        return self._anotar(rel).read_bytes()

    def conferir(self, caminhos=None):
        mudados = []
        for rel in sorted(caminhos if caminhos is not None else self.lidos):
            atual = self.raiz / rel
            if not atual.is_file() or sha256(atual) != self.lidos[rel]:
                mudados.append(rel)
        return mudados

    def item(self, rel):
        return {"caminho": rel, "sha256": self.lidos[rel]}


def rodar(args, cwd, env_extra=None, timeout=1800):
    env = dict(os.environ)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "PYTHONIOENCODING": "utf-8"})
    env.update(env_extra or {})
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
    if r.returncode:
        raise ErroGolden(f"falhou ({r.returncode}): {' '.join(map(str, args))}\n{r.stdout[-2000:]}\n{r.stderr[-3000:]}")
    return r.stdout


class Golden:
    """Monta a entrada do manifesto de um golden e copia os arquivos dele para a saída."""

    def __init__(self, gid, descricao, saida, origens):
        self.gid, self.saida, self.org = gid, Path(saida), origens
        self.pasta = self.saida / gid
        if self.pasta.exists():
            shutil.rmtree(self.pasta)
        self.pasta.mkdir(parents=True)
        self.dados = {"id": gid, "descricao": descricao, "comando": [], "codigo": [], "entradas": [],
                      "arquivos": [], "observacoes": [], "bloqueio": None}
        self._lidos = []

    def codigo(self, *rels):
        for rel in rels:
            self._lidos += self.org.copiar(rel)
            self.dados["codigo"].append(self.org.item(rel))

    def entrada(self, rel, guardar_como=None):
        """Copia a entrada para a cópia de trabalho; com `guardar_como`, guarda também no golden."""
        self._lidos += self.org.copiar(rel)
        self.dados["entradas"].append(self.org.item(rel))
        if guardar_como:
            self.guardar(self.org.copia / rel, guardar_como)

    def comparar_com_origem(self, rel, gerado, rotulo):
        """Anota se a saída regerada na cópia é igual ao arquivo que a origem já tinha gravado."""
        if not (self.org.raiz / rel).is_file():
            self.dados["observacoes"].append(f"{rotulo}: a origem não tem {rel} para comparar")
            return None
        velho, novo = self.org.ler(rel), Path(gerado).read_bytes()
        igual = velho == novo
        if not igual and rel.endswith(".json"):
            try:
                igual = "igual no conteúdo" if json.loads(velho) == json.loads(novo) else False
            except ValueError:
                pass
        self._lidos.append(rel)
        self.dados.setdefault("igual_a_origem", {})[rotulo] = igual
        return igual

    def comando(self, cwd_rel, args):
        self.dados["comando"].append({"cwd": cwd_rel, "args": [str(a) for a in args]})

    def guardar(self, origem, rel_golden):
        destino = self.pasta / rel_golden
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
        return destino

    def fechar(self):
        for rel in sorted(p.relative_to(self.saida).as_posix() for p in self.pasta.rglob("*") if p.is_file()):
            self.dados["arquivos"].append({"caminho": rel, "sha256": sha256(self.saida / rel)})
        mudados = self.org.conferir(set(self._lidos))
        self.dados["origem_intacta"] = {"arquivos": len(set(self._lidos)), "iguais": not mudados}
        if mudados:
            raise ErroGolden(f"{self.gid}: arquivos de origem mudaram durante a execução: {mudados}")
        return self.dados


def alma_base(nome, descricao, cores, fontes, estilo, origens_campos, pendencias):
    """Alma completa no formato do CONTRATO-alma, com identidade neutra de teste."""
    return {
        "expxmedia_alma": 1,
        "metodo": "entrevista",
        "fontes": [],
        "criada_em": f"{date.today().isoformat()}T00:00:00-03:00",
        "confirmada_em": f"{date.today().isoformat()}T00:00:00-03:00",
        "atualizado_em": f"{date.today().isoformat()}T00:00:00-03:00",
        "empresa": {"nome": nome, "nome_curto": nome, "descricao_curta": descricao, "segmento": "teste",
                    "site": None, "pais": "BR", "idioma": "pt-BR", "fuso": "America/Sao_Paulo"},
        "publico": {"principal": "suíte de testes de paridade do núcleo", "dores": ["regressão visual"],
                    "desejos": ["mesma saída do sistema atual"]},
        "ofertas": [{"id": "paridade", "nome": "Paridade", "tipo": "outro",
                     "descricao": "Alma de teste que reproduz a aparência do sistema atual.", "url": None, "principal": True}],
        "voz": {"tom": ["direto"], "tratamento": "voce", "formalidade": "media", "palavras_preferidas": [],
                "palavras_proibidas": [], "regras": [], "exemplos_bons": [], "exemplos_ruins": []},
        "visual": {"cores": cores, "fontes": fontes, "logo": {"principal": None, "negativo": None, "simbolo": None},
                   "estilo": estilo},
        "cta": {"padrao": "Salve para rever", "destino": None, "variacoes": []},
        "canais": [],
        "porta_vozes": [],
        "restricoes": {"temas_proibidos": [], "promessas_proibidas": [], "observacoes_legais": []},
        "origens": origens_campos,
        "pendencias": pendencias,
    }


# ------------------------------------------------------------------ G1


def _ler_tema_referencia(css):
    bloco = re.search(r"\.slide\.referencia\s*\{([^}]*)\}", css)
    if not bloco:
        raise ErroGolden("layout.css sem o bloco .slide.referencia")
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", bloco.group(1)))


def _capturar_fontes(htmls, pasta_fontes, canvas):
    """Abre os slides renderizados e guarda o que o navegador baixou do Google Fonts."""
    from playwright.sync_api import sync_playwright

    respostas = []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport=canvas, device_scale_factor=1, java_script_enabled=False)

        def porteiro(rota):
            url = urllib.parse.urlsplit(rota.request.url)
            if url.scheme in ("data", "about", "blob") or (url.scheme == "https" and url.hostname in HOSTS_DE_FONTE):
                return rota.continue_()
            rota.abort()

        pg.route("**/*", porteiro)
        pg.on("response", lambda r: respostas.append(r) if urllib.parse.urlsplit(r.url).hostname in HOSTS_DE_FONTE else None)
        for html in htmls:
            pg.set_content(Path(html).read_text(encoding="utf-8"), wait_until="networkidle")
            pg.evaluate("document.fonts.ready.then(()=>1)")
            pg.wait_for_timeout(150)
        corpos = {}
        for r in respostas:
            if r.ok and r.url not in corpos:
                corpos[r.url] = r.body()
        nav.close()

    pasta_fontes.mkdir(parents=True, exist_ok=True)
    baixadas, css_total = {}, []
    for url, corpo in corpos.items():
        host = urllib.parse.urlsplit(url).hostname
        if host == "fonts.gstatic.com":
            nome = Path(urllib.parse.urlsplit(url).path).name
            (pasta_fontes / nome).write_bytes(corpo)
            baixadas[url] = nome
        else:
            css_total.append(corpo.decode("utf-8"))
    if not baixadas:
        raise ErroGolden("o render não baixou nenhuma fonte do Google Fonts (sem rede?)")
    blocos = []
    for css in css_total:
        for comentario, bloco in re.findall(r"(/\*[^*]*\*/\s*)?(@font-face\s*\{[^}]*\})", css):
            url = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", bloco)
            if url and url.group(1) in baixadas:
                blocos.append((comentario or "") + bloco.replace(url.group(1), baixadas[url.group(1)]))
    (pasta_fontes / "fontes.css").write_text("\n".join(dict.fromkeys(blocos)) + "\n", encoding="utf-8")
    return sorted(set(baixadas.values())), [u for u in corpos if urllib.parse.urlsplit(u).hostname == "fonts.googleapis.com"]


def golden_g1(org, saida):
    g = Golden("G1", "Render HTML→PNG do layout 0001-pos-paineis-de-pagamento com o exemplo.json dele pelo "
               "galeria.renderizar de origem (prévia: 4 slides, render.json com as medidas do encaixe), a Alma "
               "golden com o tema 'referencia' nos papéis de cor e as fontes do Google Fonts baixadas no render.",
               saida, org)
    base = f"{CARROSSEIS}/galeria"
    g.codigo(f"{base}/__init__.py", f"{base}/_galeria.py", f"{base}/processar.py", f"{base}/tratamento.py",
             f"{base}/renomeados.json")
    layout = f"{base}/layouts/{LAYOUT_G1}"
    for rel in ("layout.json", "layout.css", "exemplo.json"):
        g.entrada(f"{layout}/{rel}")
    for rel in org.copiar(f"{layout}/slides"):
        g.dados["entradas"].append(org.item(rel))
        g._lidos.append(rel)
    # a referência (arte de terceiros) só vai para a cópia: a prancha precisa dela; o golden não guarda
    g._lidos += org.copiar(f"{layout}/referencia")
    raiz = org.copia / CARROSSEIS
    (raiz / layout.split("/", 1)[1] / "assets").mkdir(parents=True, exist_ok=True)
    rodador = org.copia / "_rodar_g1.py"
    rodador.write_text(
        "import json, sys\n"
        "sys.path.insert(0, '.')\n"
        "import galeria\n"
        f"r = galeria.renderizar('galeria/layouts/{LAYOUT_G1}', saida='saida', salvar_html=True)\n"
        "print(json.dumps(r, ensure_ascii=False))\n"
        "sys.exit(0 if r['ok'] else 1)\n", encoding="utf-8")
    g.comando(CARROSSEIS, ["python", "-c",
                           f"import galeria; galeria.renderizar('galeria/layouts/{LAYOUT_G1}', saida='saida', salvar_html=True)"])
    rodar([sys.executable, str(rodador)], cwd=raiz)
    render = json.loads((raiz / "saida" / "render.json").read_text(encoding="utf-8"))
    n = len(render["slides"])
    for i in range(1, n + 1):
        g.guardar(raiz / "saida" / f"slide_{i}.png", f"slide_{i}.png")
    g.guardar(raiz / "saida" / "render.json", "render.json")
    for i in range(1, n + 1):
        g.comparar_com_origem(f"{layout}/previa/slide_{i}.png", raiz / "saida" / f"slide_{i}.png", f"slide_{i}.png")

    manifesto_layout = json.loads((raiz / layout.split("/", 1)[1] / "layout.json").read_text(encoding="utf-8"))
    fontes, css_urls = _capturar_fontes([raiz / "saida" / f"slide_{i}.html" for i in range(1, n + 1)], g.pasta / "fontes",
                                        {"width": manifesto_layout["canvas"]["w"], "height": manifesto_layout["canvas"]["h"]})

    tema = _ler_tema_referencia((raiz / layout.split("/", 1)[1] / "layout.css").read_text(encoding="utf-8"))
    mapa = {"fundo": "--claro", "fundo_alt": "--escuro", "texto": "--tinta", "texto_inverso": "--tinta-inversa",
            "apoio": "--apoio", "destaque": "--destaque", "destaque_2": "--destaque-2", "positivo": "--positivo"}
    cores = {papel: tema[var].strip() for papel, var in mapa.items()}
    cores["negativo"] = "#e5484d"
    familia = manifesto_layout["fontes_google"][0].split(":")[0]
    alma = alma_base("Golden G1", "Alma de teste do golden G1: o tema 'referencia' do layout de posts de interface.",
                     cores, {"titulo": {"familia": familia, "origem": "google"}, "texto": {"familia": familia, "origem": "google"}},
                     ["tipografico", "tech-interface", "escuro"],
                     {"visual.cores": "humano", "visual.fontes": "humano"}, ["visual.logo.principal"])
    gravar_json(g.pasta / "alma-golden.json", alma)

    g.dados["mapeamento_cores"] = {
        "origem": f"{layout}/layout.css (bloco .slide.referencia)",
        "papeis": mapa,
        "sem_papel": {v: tema[v].strip() for v in tema if v not in mapa.values() and not v.startswith("--fonte")},
        "negativo": "o tema não tem cor de dado ruim; #e5484d preenche o papel e não aparece no layout",
    }
    g.dados["fontes"] = {"arquivos": [f"G1/fontes/{f}" for f in fontes], "css": "G1/fontes/fontes.css", "pedidas": css_urls}
    g.dados["observacoes"] += [
        "render.json e slide_N.png são a prévia do layout (copy = exemplo.json); a prancha não é guardada porque recorta a referência de terceiros",
        "a Alma golden tem identidade neutra de teste; só o visual reproduz a origem",
    ]
    return g.fechar()


# ------------------------------------------------------------------ G2 e G8


def golden_g2(org, saida):
    g = Golden("G2", "Linha do tempo e trilha do reel recriado sob medida recriado-ia-decide, pelo montar-reel.mjs "
               "de origem: timeline.json (cenas, eventos, blocos de legenda) e trilha.wav (música + efeitos).",
               saida, org)
    g.codigo(f"{VIDEOS}/remotion/scripts/montar-reel.mjs", f"{VIDEOS}/remotion/scripts/audio.mjs")
    # todos os cenas.json de src/reels entram: o montar-reel recusa trilha igual à de outro reel
    for rel in org.copiar(f"{VIDEOS}/remotion/src/reels", ignorar=("timeline.json",)):
        g._lidos.append(rel)
        if rel.endswith("cenas.json") or rel.endswith(f"{REEL_G2}/Reel.tsx"):
            g.dados["entradas"].append(org.item(rel))
    g.guardar(org.copia / f"{VIDEOS}/remotion/src/reels/{REEL_G2}/cenas.json", "entradas/cenas.json")
    video = f"{VIDEOS}/videos/{REEL_G2}"
    g.entrada(f"{video}/alignment.json", "entradas/alignment.json")
    g.entrada(f"{video}/narracao.mp3", "entradas/narracao.mp3")
    args = ["node", "scripts/montar-reel.mjs", REEL_G2]
    g.comando(f"{VIDEOS}/remotion", args)
    rodar(args, cwd=org.copia / VIDEOS / "remotion")
    timeline = g.guardar(org.copia / f"{VIDEOS}/remotion/src/reels/{REEL_G2}/timeline.json", "timeline.json")
    trilha = g.guardar(org.copia / f"{VIDEOS}/remotion/public/reels/{REEL_G2}/trilha.wav", "trilha.wav")
    g.comparar_com_origem(f"{VIDEOS}/remotion/src/reels/{REEL_G2}/timeline.json", timeline, "timeline.json")
    g.comparar_com_origem(f"{VIDEOS}/remotion/public/reels/{REEL_G2}/trilha.wav", trilha, "trilha.wav")
    g.dados["observacoes"].append("montar-reel.mjs só usa módulos node: e audio.mjs; node_modules não é necessário na cópia")
    return g.fechar()


def golden_g8(org, saida):
    g = Golden("G8", "Narração falada do reel recriado-ia-decide (mp3 da origem) e o alinhamento por caractere "
               "gravado pelo tts.py, para testar a transcrição offline.", saida, org)
    video = f"{VIDEOS}/videos/{REEL_G2}"
    g.entrada(f"{video}/narracao.mp3", "narracao.mp3")
    g.entrada(f"{video}/alignment.json", "alignment.json")
    g.entrada(f"{video}/roteiro.txt", "roteiro.txt")
    g.comando(VIDEOS, ["cp", f"videos/{REEL_G2}/narracao.mp3", f"videos/{REEL_G2}/alignment.json", f"videos/{REEL_G2}/roteiro.txt", "G8/"])
    g.dados["observacoes"].append("cópia de arquivos já gravados pela origem; a narração veio da ElevenLabs e não é regerada (D-15)")
    return g.fechar()


# ------------------------------------------------------------------ G3 e G4


def _ffprobe_resumo(mp4):
    bruto = json.loads(rodar(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(mp4)],
                             cwd=Path(mp4).parent))
    campos_s = ("index", "codec_type", "codec_name", "profile", "width", "height", "pix_fmt", "r_frame_rate",
                "avg_frame_rate", "nb_frames", "duration", "sample_rate", "channels", "channel_layout", "bit_rate")
    campos_f = ("format_name", "duration", "nb_streams")
    return {"streams": [{k: s[k] for k in campos_s if k in s} for s in bruto["streams"]],
            "format": {k: bruto["format"][k] for k in campos_f if k in bruto["format"]}}


def golden_g3_g4(org, saida, quais):
    video = f"{VIDEOS}/videos/{VIDEO_G3}"
    pipeline = [f"{VIDEOS}/pipeline/captions.py", f"{VIDEOS}/pipeline/lib.py", f"{VIDEOS}/pipeline/pronuncia.py"]
    resultado = {}
    g3 = Golden("G3", "Legendas do reel de página firecrawl-firecrawl pelo captions.py de origem: um PNG por bloco "
                "(caps/NNN.png, blank.png e o card final end.png), caps.txt (concat do ffmpeg) e legendas.json.",
                saida if "G3" in quais else org.copia / "_g3_so_para_o_g4", org)
    g3.codigo(*pipeline)
    for nome in ("alignment.json", "roteiro.txt", "cta.txt"):
        g3.entrada(f"{video}/{nome}", f"entradas/{nome}")
    args = ["python", "pipeline/captions.py", f"videos/{VIDEO_G3}"]
    g3.comando(VIDEOS, args)
    rodar([sys.executable, *args[1:]], cwd=org.copia / VIDEOS)
    feito = org.copia / video
    for png in sorted((feito / "caps").glob("*.png")):
        g3.guardar(png, f"caps/{png.name}")
    g3.guardar(feito / "caps.txt", "caps.txt")
    g3.guardar(feito / "legendas.json", "legendas.json")
    g3.comparar_com_origem(f"{video}/legendas.json", feito / "legendas.json", "legendas.json")
    g3.comparar_com_origem(f"{video}/caps.txt", feito / "caps.txt", "caps.txt")
    g3.comparar_com_origem(f"{video}/caps/end.png", feito / "caps" / "end.png", "caps/end.png")
    g3.dados["observacoes"] += [
        "a fonte é a do sistema na origem (captions.py:30); a alma-golden-reel do G4 aponta para ela (D-47)",
        "os PNGs gravados pela origem em 18/09 diferem dos regerados em poucos pixels de antisserrilhado (Pillow de "
        "hoje) e o end.png também no desenho; o golden segue o código atual rodado na cópia",
    ]
    if "G3" in quais:
        resultado["G3"] = g3.fechar()
    if "G4" not in quais:
        return resultado

    g4 = Golden("G4", "Montagem do reel de página firecrawl-firecrawl pelo compose.py de origem (rolagem, cartão de "
                "impacto, selo de CTA, legendas do G3, narração e loudnorm): o MP4 final, o resumo do ffprobe e a "
                "alma-golden-reel com as cores de captions.py/compose.py e a fonte local da origem (D-47).",
                saida, org)
    g4.codigo(f"{VIDEOS}/pipeline/compose.py", *pipeline)
    for nome in ("strip.png", "captura.json", "narracao.mp3"):
        g4.entrada(f"{video}/{nome}", f"entradas/{nome}")
    g4.entrada(f"{video}/repo.json")
    # O firecrawl foi montado em 18/09, antes do visual v2 (19/09); o compose.py de hoje exige impacto.txt
    # no vídeo de repositório. O golden cria um, curto, para exercitar o cartão de impacto e o selo.
    impacto = "SITE VIRA\nDADO DE IA\n"
    (feito / "impacto.txt").write_text(impacto, encoding="utf-8")
    g4.guardar(feito / "impacto.txt", "entradas/impacto.txt")
    args = ["python", "pipeline/compose.py", f"videos/{VIDEO_G3}"]
    g4.comando(VIDEOS, args)
    rodar([sys.executable, *args[1:]], cwd=org.copia / VIDEOS)
    mp4 = g4.guardar(feito / f"{VIDEO_G3}.mp4", f"{VIDEO_G3}.mp4")
    g4.guardar(feito / "visual.json", "visual.json")
    gravar_json(g4.pasta / "ffprobe.json", _ffprobe_resumo(mp4))

    cores = {
        "fundo": "#000000",          # caixa da legenda (0,0,0,205) captions.py:35 e selo (0,0,0,225) compose.py:243
        "fundo_alt": "#212830",      # fundo da tira (33,40,48) stitch.py:13
        "texto": "#000000",          # texto do cartão de impacto compose.py:212
        "texto_inverso": "#FFFFFF",  # texto da legenda e do selo captions.py:35, compose.py:244
        "apoio": "#8B949E",          # sem uso na origem
        "destaque": "#3FB950",       # palavra do CTA e contorno do selo (63,185,80) captions.py:35, compose.py:243
        "destaque_2": "#FFD400",     # cartão de impacto (255,212,0) compose.py:210
        "positivo": "#3FB950",       # mesma cor do CTA
        "negativo": "#F85149",       # sem uso na origem
    }
    fonte = {"familia": "Arial Black", "origem": "local", "arquivo": FONTE_SISTEMA_ORIGEM}
    alma = alma_base("Golden Reel", "Alma de teste dos goldens G3 e G4: cores e fonte do reel de página atual.",
                     cores, {"titulo": dict(fonte), "texto": dict(fonte)}, ["escuro", "legenda-em-caixa"],
                     {"visual.cores": "humano", "visual.fontes": "humano"}, ["visual.logo.principal"])
    gravar_json(g4.pasta / "alma-golden-reel.json", alma)
    g4.dados["mapeamento_cores"] = {
        "origem": [f"{VIDEOS}/pipeline/captions.py", f"{VIDEOS}/pipeline/compose.py", f"{VIDEOS}/pipeline/stitch.py"],
        "alfa": {"caixa_legenda": 205, "selo": 225, "veu_impacto": 120},
        "sem_uso_na_origem": ["apoio", "negativo"],
    }
    g4.dados["observacoes"] += [
        "impacto.txt não existe na origem (o vídeo é anterior ao visual v2); o gerador cria 'SITE VIRA / DADO DE IA' para exercitar o cartão",
        "a fonte da alma-golden-reel é a fonte do sistema usada na origem, só para os testes; o arquivo não é copiado (D-47)",
        "o G4 usa as legendas do G3 geradas na mesma cópia",
    ]
    resultado["G4"] = g4.fechar()
    return resultado


# ------------------------------------------------------------------ G5


def golden_g5(org, saida):
    g = Golden("G5", "Legendas de aula (42 caracteres × 2 linhas) e SRT do radar-ia-09-jev-calibracao pelo "
               "gerar_legendas.py de origem, com o texto do roteiro nos tempos do whisper, e o cues.json dos marcadores.",
               saida, org)
    aula = f"{CURSOS}/{AULA_G5}"
    g.codigo(f"{aula}/gerar_legendas.py", f"{aula}/gerar_voz.py")
    g.entrada(f"{aula}/roteiro.txt", "entradas/roteiro.txt")
    g.entrada(f"{aula}/raw/whisper/narracao.json", "entradas/narracao.whisper.json")
    # cues: gerar_voz.py calcula os cues a partir do alinhamento que a ElevenLabs devolve na mesma chamada
    # e não grava esse alinhamento. Sem ele, a função não roda sem rede e sem chamada paga (D-15).
    g.entrada(f"{aula}/src/cues.json", "cues.json")
    args = ["python", "gerar_legendas.py"]
    g.comando(aula, args)
    rodar([sys.executable, "gerar_legendas.py"], cwd=org.copia / aula)
    leg = g.guardar(org.copia / aula / "src" / "legendas.json", "legendas.json")
    srt = g.guardar(org.copia / aula / "out" / f"{AULA_G5}.srt", f"{AULA_G5}.srt")
    g.comparar_com_origem(f"{aula}/src/legendas.json", leg, "legendas.json")
    g.comparar_com_origem(f"{aula}/out/{AULA_G5}.srt", srt, f"{AULA_G5}.srt")
    g.dados["cues"] = {"regerado": False,
                       "motivo": "gerar_voz.py não salva o alinhamento da ElevenLabs; cues.json é o que a origem gravou"}
    g.dados["observacoes"].append("o gerar_voz.py entra só como código de referência dos cues; não é executado (lê .env e chama API paga)")
    return g.fechar()


# ------------------------------------------------------------------ G6


def golden_g6(org, saida):
    g = Golden("G6", "deck.json de uma apresentação do youtube-squad, para converter ao schema do núcleo.", saida, org)
    rel = f"{YOUTUBE}/apresentacoes/decks/{DECK_G6}/deck.json"
    g.entrada(rel, "deck.json")
    g.codigo(f"{YOUTUBE}/tests/decks.py")
    g.comando(YOUTUBE, ["cp", f"apresentacoes/decks/{DECK_G6}/deck.json", "G6/deck.json"])
    g.dados["observacoes"].append("cópia do deck.json; o schema da origem está em youtube-squad/tests/decks.py")
    return g.fechar()


# ------------------------------------------------------------------ G7

_WHISPER_FALSO = '''"""Reprodução da transcrição que a origem já gravou (transcricao_corte.json), sem rodar o modelo."""
import json
from pathlib import Path
from types import SimpleNamespace


class WhisperModel:
    def __init__(self, *a, **k):
        self.dados = json.loads(Path(__import__("os").environ["G7_TRANSCRICAO"]).read_text(encoding="utf-8"))

    def transcribe(self, *a, **k):
        palavras = [SimpleNamespace(word=p["w"], start=p["t0"], end=p["t1"]) for p in self.dados["palavras"]]
        segs = []
        for i, s in enumerate(self.dados["segmentos"]):
            segs.append(SimpleNamespace(start=s["t0"], end=s["t1"], text=s["texto"], words=palavras if i == 0 else []))
        return iter(segs), None
'''


def golden_g7(org, saida):
    g = Golden("G7", "Corte de YouTube yt-04hAay1cjyU-t0239: transcrição da aula (entrada do momentos.py), os "
               "candidatos que o momentos.py ranqueia (o trecho escolhido é o primeiro), a transcrição do corte, o "
               "alinhamento que o transcrever.py --alinhar deriva dela e o alinhamento recasado com as grafias "
               "corrigidas do roteiro.txt da origem.", saida, org)
    g.codigo(f"{VIDEOS}/pipeline/momentos.py", f"{VIDEOS}/pipeline/transcrever.py", f"{VIDEOS}/pipeline/lib.py")
    fonte = f"{VIDEOS}/fontes/{FONTE_G7}"
    g.entrada(f"{fonte}/transcricao.json", "transcricao.json")
    g.entrada(f"{fonte}/fonte.json", "entradas/fonte.json")
    args = ["python", "pipeline/momentos.py", f"fontes/{FONTE_G7}"]
    g.comando(VIDEOS, args)
    rodar([sys.executable, *args[1:]], cwd=org.copia / VIDEOS)
    cand = g.guardar(org.copia / fonte / "candidatos.json", "candidatos.json")
    g.comparar_com_origem(f"{fonte}/candidatos.json", cand, "candidatos.json")
    primeiro = json.loads(cand.read_text(encoding="utf-8"))["candidatos"][0]
    g.dados["trecho_escolhido"] = {"inicio": primeiro["inicio"], "fim": primeiro["fim"], "pontos": primeiro["pontos"]}

    corte = f"{VIDEOS}/videos/{CORTE_G7}"
    g.entrada(f"{corte}/transcricao_corte.json", "transcricao_corte.json")
    g.entrada(f"{corte}/corte9x16.mp4")  # só na cópia: o --alinhar mede a duração dele com ffprobe
    falso = org.copia / "_whisper_falso" / "faster_whisper"
    falso.mkdir(parents=True)
    (falso / "__init__.py").write_text(_WHISPER_FALSO, encoding="utf-8")
    trabalho = org.copia / corte
    reproducao = org.copia / "_transcricao_corte.json"
    shutil.copy2(trabalho / "transcricao_corte.json", reproducao)
    env = {"PYTHONPATH": str(falso.parent), "G7_TRANSCRICAO": str(reproducao)}
    args = ["python", "pipeline/transcrever.py", f"videos/{CORTE_G7}", "--alinhar"]
    g.comando(VIDEOS, args)
    rodar([sys.executable, *args[1:]], cwd=org.copia / VIDEOS, env_extra=env)
    g.guardar(trabalho / "alignment.json", "alignment.whisper.json")
    g.guardar(trabalho / "roteiro.txt", "roteiro.whisper.txt")
    if (trabalho / "transcricao_corte.json").read_bytes() != reproducao.read_bytes():
        g.dados["observacoes"].append("a transcricao_corte.json regravada pelo --alinhar difere da original só na formatação")

    g.entrada(f"{corte}/roteiro.txt", "roteiro.txt")  # o roteiro corrigido à mão sobrescreve o do whisper na cópia
    args = ["python", "pipeline/transcrever.py", f"videos/{CORTE_G7}", "--recasar"]
    g.comando(VIDEOS, args)
    rodar([sys.executable, *args[1:]], cwd=org.copia / VIDEOS)
    recasado = g.guardar(trabalho / "alignment.json", "alignment.recasado.json")
    g.comparar_com_origem(f"{corte}/alignment.json", recasado, "alignment.recasado.json")
    g.dados["observacoes"] += [
        "candidatos.json: a origem gravou 6 candidatos (rodada com --n menor); o padrão de hoje é 8 e os 6 primeiros são iguais aos da origem",
        "alignment.recasado.json: a origem foi recasada antes da correção da inserção de largura zero (transcrever.py:70-78); "
        "3 tempos de fim diferem em 0,02 s e o golden segue o código atual",
        "o whisper do --alinhar é substituído por um módulo que devolve a transcricao_corte.json gravada pela origem; "
        "o código de conversão palavra→caractere e o --recasar são os da origem",
        "o corte9x16.mp4 só entra na cópia (o --alinhar mede a duração); não é guardado no golden",
    ]
    return g.fechar()


# ------------------------------------------------------------------ principal


def versoes():
    def saida(args):
        try:
            return subprocess.run(args, capture_output=True, text=True).stdout.splitlines()[0].strip()
        except (OSError, IndexError):
            return None

    try:
        from importlib.metadata import version
        pw = version("playwright")
    except Exception:
        pw = None
    return {"python": sys.version.split()[0], "node": saida(["node", "--version"]),
            "ffmpeg": saida(["ffmpeg", "-version"]), "playwright": pw}


def gerar(quais, saida, origens):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    arq_manifesto = saida / "manifesto.json"
    manifesto = json.loads(arq_manifesto.read_text(encoding="utf-8")) if arq_manifesto.is_file() else {}
    manifesto.setdefault("goldens", {})
    feitos, impressos = {}, set()
    with tempfile.TemporaryDirectory(prefix="expxmedia-golden-") as tmp:
        for gid in quais:
            if gid in feitos:
                continue
            # uma cópia limpa por golden: nenhum golden enxerga saída de outro, a não ser G3→G4 (mesma cópia)
            org = Origens(origens, Path(tmp) / gid)
            print(f"{gid}...", flush=True)
            if gid in ("G3", "G4"):
                feitos.update(golden_g3_g4(org, saida, [q for q in quais if q in ("G3", "G4")]))
            else:
                feitos[gid] = {"G1": golden_g1, "G2": golden_g2, "G5": golden_g5, "G6": golden_g6,
                               "G7": golden_g7, "G8": golden_g8}[gid](org, saida)
            mudados = org.conferir()
            if mudados:
                raise ErroGolden(f"{gid}: a origem mudou durante a execução: {mudados}")
            for feito in [q for q in quais if q in feitos and q not in impressos]:
                impressos.add(feito)
                print(f"{feito}: {len(feitos[feito]['arquivos'])} arquivos, origem intacta ({len(org.lidos)} lidos)", flush=True)
    manifesto["goldens"].update(feitos)
    manifesto["goldens"] = dict(sorted(manifesto["goldens"].items()))
    manifesto.update({
        "expxmedia_golden": 1,
        "gerador": "motor/scripts/gerar_golden.py",
        "gerado_em": date.today().isoformat(),
        "ambiente": versoes(),
        "caminhos": {"entradas_e_codigo": "relativos à pasta projects/ que contém os projetos de origem",
                     "arquivos": "relativos a motor/tests/golden/"},
    })
    manifesto = {k: manifesto[k] for k in ("expxmedia_golden", "gerador", "gerado_em", "ambiente", "caminhos", "goldens")}
    gravar_json(arq_manifesto, manifesto)
    return manifesto


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--so", help="lista de goldens separados por vírgula (padrão: G1 a G8)")
    ap.add_argument("--saida", default=str(GOLDEN))
    ap.add_argument("--origens", default=str(PROJETOS), help="pasta que contém os projetos de origem")
    a = ap.parse_args(argv)
    quais = [q.strip().upper() for q in a.so.split(",")] if a.so else list(IDS)
    desconhecidos = [q for q in quais if q not in IDS]
    if desconhecidos:
        ap.error(f"golden desconhecido: {desconhecidos}")
    try:
        gerar([g for g in IDS if g in quais], a.saida, a.origens)
    except ErroGolden as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
