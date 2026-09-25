"""Abertura gerada: os primeiros segundos do reel viram um plano criado por IA (capacidade `video_ia`).

Porta de `Instragram-Videos/pipeline/abertura.py` (geração, janela pelo encaixe, faixa do rosto, marcador) e
da montagem por cima de `Instragram-Videos/pipeline/compose.py` (que o núcleo já tem em
`video.montar_pagina`). As regras que derrubam a qualidade se forem esquecidas:

- **a abertura não é colada na frente: ela troca o FUNDO da janela do cartão de impacto.** Narração,
  legenda e cartão correm desde o instante zero por cima dela — sem silêncio no começo e sem alongar o
  reel (colar na frente foi testado na origem e revertido);
- o clipe é gerado com **o primeiro quadro que o conteúdo mostra depois dela** como `end_image` (o topo da
  tira), para os elementos se transformarem nele e o corte não parecer corte. O cartão nunca vai ao
  modelo: gerador de vídeo devolve letra embaralhada;
- **a janela que vai ao ar termina no encaixe**, não no fim do arquivo: o modelo fecha a transformação
  antes do fim e segura a página parada. O encaixe é medido por pixel em miniatura (96x171, a cada 0,1 s):
  a diferença média para o destino cai e estaciona; o limiar é 15% do caminho entre o menor e o maior
  valor (relativo à própria curva); sem variação de 3 níveis ou com menos de 6 quadros não há encaixe e
  fica o fim do arquivo. A janela termina 0,1 s depois do encaixe e começa `duracao` antes;
- o clipe padronizado é **mudo** (1080x1920, 30 fps, yuv420p, x264 slow crf 18): clipe com áudio mexeria
  no loudness e no pico que o gate cobra;
- no tipo com gente (`porta_voz`), **a faixa do rosto é medida no clipe inteiro** já padronizado (Haar
  1.1/5/60x60, amostra a cada fps/4 quadros, maior rosto, união do topo mais alto e da base mais baixa) e
  vai para `abertura.json > rosto`; a montagem põe o cartão na faixa livre acima ou abaixo dele (posição
  fixa tapou os olhos em três alturas);
- `abertura.json` nasce com `montado_em: null` e **só a montagem o preenche, depois do MP4 final
  existir** (coorte que não mente quando a montagem falha);
- a URL assinada do resultado nunca vai a disco nem a log; do job fica só o id (em `imagem.higgsfield`).

Tipos: `objeto` (a coisa do gancho, sem gente) e `porta_voz` (o porta-voz da Alma na situação do reel:
o `rosto_ia` faz o quadro dele, que entra como `start_image`, porque nenhum modelo de vídeo aceita o id
de rosto direto). As **travas negativas** (sem texto, sem logo, sem interface, sem outras pessoas) e a
instrução de transformação ficam no núcleo; a estética do plano é da marca e vem por `estilo`.

Uso:

    from expxmedia.producao import abertura
    abertura.gerar(raiz, pasta_midia, prompt="a loaf of bread rising in a warm oven")
    abertura.montar(raiz, pasta_midia, estilo=estilo, impacto=["..."], saida=pasta_saida / "final.mp4")
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

from expxmedia.imagem import higgsfield
from expxmedia.nucleo import arquivos, tempo
from expxmedia.nucleo.raiz import relativo
from expxmedia.video import ffmpeg, montar_pagina

__all__ = [
    "ErroAbertura",
    "TIPOS",
    "DURACAO_NA_TELA",
    "TETO_CREDITOS_DIA",
    "quadro_destino",
    "instante_do_encaixe",
    "padronizar",
    "faixa_do_rosto",
    "creditos_gastos_hoje",
    "gerar",
    "dispensar",
    "montar",
]

DURACAO_NA_TELA = 2.5  # origem: Instragram-Videos/aberturas.json:12
DURACAO_MIN, DURACAO_MAX = 1.0, 5.0  # origem: Instragram-Videos/pipeline/abertura.py:418
TETO_CREDITOS_DIA = 80  # origem: Instragram-Videos/aberturas.json:16
ENCAIXE_PASSO_S = 0.1  # origem: Instragram-Videos/pipeline/abertura.py:235
MINIATURA = (96, 171)  # origem: Instragram-Videos/pipeline/abertura.py:253,255
ENCAIXE_QUADROS_MIN = 6  # origem: Instragram-Videos/pipeline/abertura.py:260
ENCAIXE_VARIACAO_MIN = 3.0  # origem: Instragram-Videos/pipeline/abertura.py:265
ENCAIXE_LIMIAR = 0.15  # origem: Instragram-Videos/pipeline/abertura.py:267
ENCAIXE_FOLGA_S = 0.1  # origem: Instragram-Videos/pipeline/abertura.py:292
LARGURA_ANALISE = 640  # origem: Instragram-Videos/pipeline/abertura.py:343
HAAR_ESCALA = 1.1  # origem: Instragram-Videos/pipeline/abertura.py:345
HAAR_VIZINHOS = 5  # origem: Instragram-Videos/pipeline/abertura.py:345
HAAR_MINIMO = (60, 60)  # origem: Instragram-Videos/pipeline/abertura.py:345
ROSTO_AMOSTRAS_POR_S = 4  # passo = fps/4; origem: Instragram-Videos/pipeline/abertura.py:334
CRF = "18"  # origem: Instragram-Videos/pipeline/abertura.py:304
PRESET = "slow"  # origem: Instragram-Videos/pipeline/abertura.py:304
CAUDA_ERRO = 800  # origem: Instragram-Videos/pipeline/abertura.py:307
MODO = "por-cima"  # único modo: troca o fundo, não alonga; origem: Instragram-Videos/aberturas.json:11
METODO = "abertura-gerada"  # origem: Instragram-Videos/pipeline/abertura.py:457

# Instrução de transformação e travas negativas: mecânica do formato, não estética de marca.
TRAVAS_OBJETO = ("No legible text, no letters, no numbers, no logos, no user interface, no people, no faces, "
                 "no hands.")  # origem: Instragram-Videos/aberturas.json:28
TRANSFORMACAO_OBJETO = (  # origem: Instragram-Videos/aberturas.json:29
    "This shot must END on the provided end frame. In the final moment, everything on screen breaks apart and "
    "reassembles, in one continuous and impactful move, into exactly that end frame, and then holds there "
    "perfectly still. Do not cut to the end frame: transform into it.")
TRAVAS_PORTA_VOZ = (  # origem: Instragram-Videos/aberturas.json:49
    "The camera HOLDS the framing on the person: no zoom, no push-in, no dolly — the person stays exactly the "
    "same size and in the same place in the frame, and only the environment around them moves. The person in "
    "the first frame is the subject and must stay recognizably the same person throughout. No legible text, no "
    "letters, no numbers, no logos, no user interface, no other people.")
TRANSFORMACAO_PORTA_VOZ = (  # origem: Instragram-Videos/aberturas.json:50
    "The shot starts on the provided start frame and must END on the provided end frame. The person stays fully "
    "visible, intact and recognizable, in the same framing, for most of the shot: only the environment around "
    "them moves and breaks apart. Then, in the final moment, the whole scene collapses and reassembles, in one "
    "continuous and impactful move, into exactly that end frame, and holds there perfectly still. Do not cut to "
    "the end frame: transform into it. Never replace the person with someone else and never change their "
    "clothing.")
ENQUADRAMENTO_RETRATO = (  # origem: Instragram-Videos/aberturas.json:46
    "vertical still, medium shot from the chest up, the head and face are in the TOP THIRD of the vertical "
    "frame and fully visible, nothing in front of the face, the person fills at least half the frame height, "
    "looking at camera.")

TIPOS: dict[str, dict[str, Any]] = {
    "objeto": {
        "modelo": "seedance_2_0",  # origem: Instragram-Videos/aberturas.json:20
        "parametros": {"mode": "std"},  # origem: Instragram-Videos/aberturas.json:21-23
        "duracao_gerada": 4,  # origem: Instragram-Videos/aberturas.json:24
        "aspecto": "9:16",  # origem: Instragram-Videos/aberturas.json:25
        "resolucao": "720p",  # origem: Instragram-Videos/aberturas.json:26
        "creditos_por_abertura": 19,  # estimativa, não cobrança; origem: Instragram-Videos/aberturas.json:27
        "travas": TRAVAS_OBJETO,
        "transformacao": TRANSFORMACAO_OBJETO,
        "retrato": False,
    },
    "porta_voz": {
        "modelo": "seedance_2_0",  # origem: Instragram-Videos/aberturas.json:33
        "parametros": {"mode": "std"},  # origem: Instragram-Videos/aberturas.json:34-36
        "duracao_gerada": 4,  # origem: Instragram-Videos/aberturas.json:37
        "aspecto": "9:16",  # origem: Instragram-Videos/aberturas.json:38
        "resolucao": "720p",  # origem: Instragram-Videos/aberturas.json:39
        "creditos_por_abertura": 19,  # origem: Instragram-Videos/aberturas.json:40
        "travas": TRAVAS_PORTA_VOZ,
        "transformacao": TRANSFORMACAO_PORTA_VOZ,
        "retrato": True,
    },
}


class ErroAbertura(RuntimeError):
    """Abertura impossível: teto de créditos, sem quadro de destino, clipe ilegível ou ffmpeg com erro."""


def _sh(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise ErroAbertura(f"binário não encontrado: {args[0]}") from e


# ------------------------------------------------------------------ quadro de destino e janela


def quadro_destino(pasta: Path, destino: Path, *, largura: int = 1080, altura: int = 1920) -> Path:
    """O primeiro quadro que o conteúdo mostra QUANDO A ABERTURA SAI: o topo da tira (a rolagem segura o topo
    parado até depois do cartão); sem tira, o primeiro quadro do vídeo do conteúdo.
    origem: Instragram-Videos/pipeline/abertura.py:80-102"""
    tira = pasta / "tira.png"
    if tira.exists():
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(tira) as img:
            img.convert("RGB").crop((0, 0, largura, altura)).save(destino)
        return destino
    fonte = next((p for p in (pasta / "scroll.mp4", pasta / "final.mp4") if p.exists()), None)
    if fonte is None:
        raise ErroAbertura(f"sem tira.png nem vídeo em {pasta.name}: não há quadro de destino para mirar")
    r = _sh(["ffmpeg", "-y", "-v", "error", "-i", str(fonte), "-frames:v", "1", str(destino)])
    if r.returncode:
        raise ErroAbertura(f"erro ao extrair o quadro de destino de {fonte.name}:\n{r.stderr[-400:]}")
    return destino


def instante_do_encaixe(bruto: Path, destino: Path, passo: float = ENCAIXE_PASSO_S) -> float | None:
    """Em que segundo do clipe ele já VIROU o quadro de destino; None quando a curva não estaciona.
    origem: Instragram-Videos/pipeline/abertura.py:235-271"""
    alvo = Image.open(destino).convert("L").resize(MINIATURA)
    w, h = MINIATURA
    with tempfile.TemporaryDirectory() as tmp:
        r = _sh(["ffmpeg", "-v", "error", "-i", str(bruto), "-vf", f"fps={1 / passo},scale={w}:{h}",
                 "-pix_fmt", "gray", f"{tmp}/q_%04d.png"])
        if r.returncode:
            return None
        quadros = sorted(Path(tmp).glob("q_*.png"))
        if len(quadros) < ENCAIXE_QUADROS_MIN:
            return None
        difs = [ImageStat.Stat(ImageChops.difference(Image.open(q).convert("L"), alvo)).mean[0] for q in quadros]
    piso, teto = min(difs), max(difs)
    if teto - piso < ENCAIXE_VARIACAO_MIN:
        return None
    limiar = piso + ENCAIXE_LIMIAR * (teto - piso)
    for n, d in enumerate(difs):
        if d <= limiar:
            return round(n * passo, 3)
    return None


def padronizar(bruto: Path, pronta: Path, dur: float, *, do_fim: bool, destino: Path | None = None,
               largura: int = 1080, altura: int = 1920, fps: int = 30) -> tuple[float, dict[str, Any]]:
    """(duração do clipe pronto, janela): 1080x1920, 30 fps, sem áudio. Com `do_fim`, a janela termina no
    encaixe (+0,1 s) e começa `dur` antes. origem: Instragram-Videos/pipeline/abertura.py:274-308"""
    corte, janela = ["-t", f"{dur}"], {}
    if do_fim:
        bruto_dur = ffmpeg.sondar(bruto)["duracao"] or 0.0
        encaixe = instante_do_encaixe(bruto, destino) if destino is not None and destino.exists() else None
        fim = min(bruto_dur, encaixe + ENCAIXE_FOLGA_S) if encaixe is not None else bruto_dur
        inicio = max(0.0, fim - dur)
        corte = ["-ss", f"{inicio:.3f}", "-t", f"{min(dur, fim - inicio):.3f}"]
        janela = {"clipe_s": round(bruto_dur, 3), "encaixe_s": encaixe, "de": round(inicio, 3), "ate": round(fim, 3)}
    r = _sh(["ffmpeg", "-y", "-v", "error", *corte, "-i", str(bruto),
             "-vf", f"scale={largura}:{altura}:flags=lanczos,fps={fps},format=yuv420p,setsar=1",
             "-an", "-t", f"{dur}", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
             "-movflags", "+faststart", str(pronta)])
    if r.returncode:
        raise ErroAbertura(f"erro ao padronizar o clipe:\n{r.stderr[-CAUDA_ERRO:]}")
    return ffmpeg.sondar(pronta)["duracao"] or 0.0, janela


def faixa_do_rosto(clipe: Path) -> dict[str, int] | None:
    """Faixa VERTICAL (px do quadro) que o rosto ocupa ao longo do clipe inteiro: {topo, base, quadros}.
    origem: Instragram-Videos/pipeline/abertura.py:311-357"""
    import cv2
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(clipe))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    passo, topo, base, achados, n = max(1, int(round(fps / ROSTO_AMOSTRAS_POR_S))), None, None, 0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        n += 1
        if (n - 1) % passo:
            continue
        alt, larg = frame.shape[:2]
        escala = LARGURA_ANALISE / larg
        cinza = cv2.cvtColor(cv2.resize(frame, (LARGURA_ANALISE, int(alt * escala))), cv2.COLOR_BGR2GRAY)
        caras = casc.detectMultiScale(cinza, HAAR_ESCALA, HAAR_VIZINHOS, minSize=HAAR_MINIMO)
        if len(caras) == 0:
            continue
        achados += 1
        x, y, w, h = max(caras, key=lambda c: c[2] * c[3])  # o maior rosto é ele
        y0, y1 = y / escala, (y + h) / escala
        topo = y0 if topo is None else min(topo, y0)
        base = y1 if base is None else max(base, y1)
    cap.release()
    if topo is None:
        return None
    return {"topo": round(topo), "base": round(base), "quadros": achados}


def creditos_gastos_hoje(raiz: Path) -> int:
    """Soma dos créditos das aberturas geradas hoje, lida dos próprios marcadores da instalação.
    origem: Instragram-Videos/pipeline/abertura.py:66-77"""
    hoje, total = tempo.hoje(raiz), 0
    for m in (Path(raiz) / "pecas").rglob("abertura.json"):
        try:
            d = json.loads(m.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if str(d.get("gerado_em") or "")[:10] == hoje:
            total += int(d.get("creditos") or 0)
    return total


# ------------------------------------------------------------------ geração


def gerar(
    raiz: Path | str,
    pasta: Path | str,
    *,
    prompt: str,
    tipo: str = "objeto",
    porta_voz: str | None = None,
    duracao: float = DURACAO_NA_TELA,
    estilo: str | None = None,
    transformar_no_conteudo: bool = True,
    teto_creditos_dia: int = TETO_CREDITOS_DIA,
    pedido_por: str = "quem chamou",
    cota: higgsfield.Cota | None = None,
) -> dict[str, Any]:
    """Gera, apara e padroniza a abertura na `pasta` de montagem e grava `abertura.json` (`montado_em` null).

    `prompt`: o que acontece no plano, em inglês, sem descrever a aparência de ninguém. `estilo`: a estética
    da marca (da Alma ou do template). Devolve o conteúdo do `abertura.json`.
    """
    raiz, pasta = Path(raiz), Path(pasta)
    if tipo not in TIPOS:
        raise ValueError(f"tipo de abertura desconhecido: {tipo!r} (válidos: {', '.join(TIPOS)})")
    if not (prompt or "").strip():
        raise ValueError("prompt vazio: o que acontece no plano, em inglês")
    if not DURACAO_MIN <= float(duracao) <= DURACAO_MAX:
        raise ValueError(f"{duracao}s de abertura está fora da faixa {DURACAO_MIN:g}-{DURACAO_MAX:g}s")
    cfg = TIPOS[tipo]
    if float(duracao) > cfg["duracao_gerada"]:
        raise ValueError(f"pedir {duracao}s na tela de um clipe de {cfg['duracao_gerada']}s não dá")
    if cfg["retrato"] and not porta_voz:
        raise ValueError("o tipo porta_voz pede o id do porta-voz da Alma")
    custo = int(cfg["creditos_por_abertura"])
    gasto = creditos_gastos_hoje(raiz)
    if teto_creditos_dia and gasto + custo > teto_creditos_dia:
        # origem: Instragram-Videos/pipeline/abertura.py:191-195
        raise ErroAbertura(f"o teto de {teto_creditos_dia} créditos/dia de abertura já foi gasto ({gasto} hoje): "
                           "monte sem abertura ou suba o teto")

    destino = quadro_destino(pasta, pasta / "abertura_destino.png") if transformar_no_conteudo else None
    retrato = None
    inicio_img = None
    if cfg["retrato"]:
        # nenhum modelo de vídeo aceita o id de rosto direto: o rosto_ia faz o quadro, que vira start_image
        texto_retrato = f"{ENQUADRAMENTO_RETRATO} {' '.join(prompt.split())}"
        r = higgsfield.gerar_rosto(raiz, porta_voz, texto_retrato, relativo(raiz, pasta / "abertura_retrato.png"),
                                   parametros={"aspect_ratio": cfg["aspecto"]}, cota=cota)
        retrato = {"porta_voz": porta_voz, "modelo": r["modelo"], "job": r["job"]}
        inicio_img = relativo(raiz, pasta / "abertura_retrato.png")

    texto = prompt.strip()
    for extra in ((estilo or "").strip(), cfg["travas"], cfg["transformacao"] if destino else ""):
        if extra:
            texto = f"{texto}\n\n{extra}"
    parametros = {**cfg["parametros"], "aspect_ratio": cfg["aspecto"], "duration": cfg["duracao_gerada"],
                  "resolution": cfg["resolucao"]}
    bruto = pasta / "abertura_bruta.mp4"
    video = higgsfield.gerar_video(raiz, texto, relativo(raiz, bruto), modelo=cfg["modelo"], parametros=parametros,
                                   start_image=inicio_img,
                                   end_image=relativo(raiz, destino) if destino else None, cota=cota)

    clipe = pasta / "abertura.mp4"
    dur_real, janela = padronizar(bruto, clipe, float(duracao), do_fim=destino is not None, destino=destino)
    # o rosto é medido DEPOIS de padronizar: é o clipe que vai ao ar
    rosto = faixa_do_rosto(clipe) if cfg["retrato"] else None
    avisos = []
    if cfg["retrato"] and rosto is None:
        avisos.append("não achei rosto na abertura e o tipo tem gente: o cartão vai para a posição de sempre — "
                      "confira o quadro antes de publicar")
    marcador = {
        "metodo": METODO, "modo": MODO, "tipo": tipo, "modelo": cfg["modelo"], "retrato": retrato,
        "duracao": round(dur_real, 3), "duracao_gerada": cfg["duracao_gerada"],
        "parametros": video["parametros"], "janela": janela or None, "rosto": rosto,
        "transformou_no_conteudo": destino is not None, "creditos": custo, "job": video["job"],
        "prompt": prompt.strip(), "gerado_em": tempo.agora_iso(raiz), "pedido_por": pedido_por,
        "montado_em": None,  # só a montagem preenche, com o MP4 final na mão
    }
    arquivos.gravar_json(pasta / "abertura.json", marcador)
    (pasta / "abertura.txt").write_text(prompt.strip() + "\n", encoding="utf-8")
    return {**marcador, "avisos": avisos}


def dispensar(pasta: Path | str) -> None:
    """Válvula: este reel vai sem abertura (remove clipe e marcador). origem: Instragram-Videos/pipeline/abertura.py:383-387"""
    pasta = Path(pasta)
    (pasta / "abertura.json").unlink(missing_ok=True)
    (pasta / "abertura.mp4").unlink(missing_ok=True)


def montar(raiz: Path | str, pasta: Path | str, *, estilo: montar_pagina.EstiloMontagem, **kw: Any) -> dict[str, Any]:
    """Monta o reel com a abertura por cima do começo (se houver `abertura.mp4` na pasta).

    A montagem é a de `video.montar_pagina`: overlay da abertura em `lt(t, duração)` com `eof_action=pass`,
    cartão sem véu por cima dela e desviando do rosto medido, legenda esperando o cartão sair quando há
    rosto, narração desde 0, e `abertura.json > montado_em` gravado só depois do MP4 final.
    """
    return montar_pagina.montar(pasta, estilo=estilo, raiz=raiz, **kw)
