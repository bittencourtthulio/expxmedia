"""Corte com reenquadramento 9:16 de um vídeo longo (capacidade `editar_video`, provedor `ffmpeg`).

Porta de `Instragram-Videos/pipeline/cut.py`, com os mesmos números. Três coisas acontecem aqui, cada uma
por um defeito real observado na origem:

1. **Fora do screencast, o crop segue o rosto.** Crop central fixo decapita quem não fica no meio. O
   caminho é suavizado em cinco camadas que só funcionam juntas: amostras a 4 quadros/s, mediana móvel de
   7 amostras (1,5 s), média exponencial com fator 0,25, **zona morta** de 12% da largura do crop (o rosto
   passeia nela sem mover a câmera), simplificação Ramer-Douglas-Peucker com tolerância de 14 px e teto de
   24 pontos (mais que isso estoura a expressão do ffmpeg). Um "siga o rosto" ingênuo produz tremor.
2. **Screencast vira tela em cima, rosto embaixo.** A passagem é reconhecida por posição **e** tamanho
   do rosto, medidos (centro fora de 0,30-0,70 da largura e largura < 0,26); só o tamanho, com limiar de
   estimativa, não pegou nenhuma passagem real. A **fronteira tela/painel é medida** pelo gradiente
   horizontal (Sobel) em 5 quadros, com pico aceito se ≥ 2× a mediana numa janela de ±8% em volta da
   estimativa — derivar do rosto errou 400 px. A faixa útil vertical tira a tarja preta (0,35 × p95 do
   brilho por linha; tema escuro devolve a altura inteira). Buraco < 2 s entre passagens é fundido e
   cobertura ≥ 80% estende a passagem à peça inteira (sem piscar entre dois splits).
3. **Sem rosto, fundo desfocado**: o 16:9 inteiro centrado sobre ele mesmo ampliado e borrado
   (`gblur` sigma 40). É o enquadramento dominante na origem (10 de 16 cortes), onde era escolhido à
   mão; aqui o modo automático o escolhe quando não há rosto suficiente (menos de 4 amostras) nem
   screencast, e o relato registra o modo e o motivo.

Modos (`modo=`): `auto` (padrão, acima), `rosto` (como a origem sem válvula: poucas amostras → crop
central fixo), `central` (a válvula `--sem-rosto`) e `fundo_desfocado` (a válvula `--fundo-desfocado`).
`sem_split=True` é a válvula `--sem-split`.

A fonte é um **vídeo local** (entrada genérica); o download por `yt-dlp` da origem é um provedor de fonte
que fica fora deste módulo. `extrair_trecho` recorta um trecho do vídeo longo e `cortar_trechos` faz o
plano de vários trechos com as validações da origem (soma na janela, trecho ≥ 4 s, sem sobreposição,
faixa já usada ≤ 20%) e junta as peças por concat sem re-encode.

Uso:

    from expxmedia.corte import cortar
    relato = cortar.cortar("trecho.mp4", "corte9x16.mp4")      # {modo, enquadramento, caminho, ...}
"""
from __future__ import annotations

import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from expxmedia.video import ffmpeg

__all__ = [
    "ErroCorte",
    "Formato",
    "FORMATO_VERTICAL",
    "MODOS",
    "AMOSTRAS_POR_S",
    "ZONA_MORTA_FRAC",
    "EPS_PX",
    "MAX_PONTOS",
    "SUAVE_S",
    "EMA",
    "ROSTO_CENTRADO_MIN",
    "ROSTO_CENTRADO_MAX",
    "ROSTO_PEQUENO_FRAC",
    "amostrar_rostos",
    "passagens_screencast",
    "fronteira_do_painel",
    "faixa_util_vertical",
    "geometria_split",
    "caminho_do_rosto",
    "expr_de",
    "renderizar",
    "cortar",
    "extrair_trecho",
    "validar_trechos",
    "cortar_trechos",
]

# ------------------------------------------------------------------ números da origem

AMOSTRAS_POR_S = 4.0  # quadros analisados por segundo; origem: Instragram-Videos/pipeline/cut.py:33
ZONA_MORTA_FRAC = 0.12  # fração da largura do crop; origem: Instragram-Videos/pipeline/cut.py:34
EPS_PX = 14.0  # tolerância da simplificação RDP; origem: Instragram-Videos/pipeline/cut.py:35
MAX_PONTOS = 24  # teto de segmentos da expressão do ffmpeg; origem: Instragram-Videos/pipeline/cut.py:36
SUAVE_S = 1.5  # janela da mediana móvel; origem: Instragram-Videos/pipeline/cut.py:37
EMA = 0.25  # fator da suavização exponencial; origem: Instragram-Videos/pipeline/cut.py:312
AMOSTRAS_MIN = 4  # abaixo disso não há caminho; origem: Instragram-Videos/pipeline/cut.py:300
LARGURA_ANALISE = 640  # quadro reduzido para a detecção; origem: Instragram-Videos/pipeline/cut.py:104
HAAR_ESCALA = 1.15  # origem: Instragram-Videos/pipeline/cut.py:113
HAAR_VIZINHOS = 6  # origem: Instragram-Videos/pipeline/cut.py:113
HAAR_MINIMO = (24, 24)  # origem: Instragram-Videos/pipeline/cut.py:113
ROSTO_CENTRADO_MIN, ROSTO_CENTRADO_MAX = 0.30, 0.70  # origem: Instragram-Videos/pipeline/cut.py:54
ROSTO_PEQUENO_FRAC = 0.26  # origem: Instragram-Videos/pipeline/cut.py:55
SCREENCAST_MIN_S = 1.5  # passagem mais curta é ruído; origem: Instragram-Videos/pipeline/cut.py:56
SCREENCAST_PAD_S = 0.3  # folga nas bordas; origem: Instragram-Videos/pipeline/cut.py:57
BURACO_AMOSTRAS = 3  # buraco maior que 3 amostras separa passagens; origem: Instragram-Videos/pipeline/cut.py:130
FUSAO_S = 2.0  # buraco menor que isso entre passagens é fundido; origem: Instragram-Videos/pipeline/cut.py:161
COBERTURA_TOTAL = 0.8  # a peça inteira vira screencast; origem: Instragram-Videos/pipeline/cut.py:171
COBERTURA_SPLIT = 0.9  # rótulo "split screencast"; origem: Instragram-Videos/pipeline/cut.py:475
FRONTEIRA_QUADROS = 5  # origem: Instragram-Videos/pipeline/cut.py:195
FRONTEIRA_ESTIMATIVA = 0.70  # fx ∓ 0,70·fw; origem: Instragram-Videos/pipeline/cut.py:203
FRONTEIRA_JANELA = 0.08  # ± fração da largura; origem: Instragram-Videos/pipeline/cut.py:207-208
FRONTEIRA_PICO = 2.0  # pico ≥ 2× a mediana; origem: Instragram-Videos/pipeline/cut.py:213
FAIXA_LIMIAR = 0.35  # × percentil 95 do brilho; origem: Instragram-Videos/pipeline/cut.py:242
FAIXA_PERCENTIL = 95  # origem: Instragram-Videos/pipeline/cut.py:242
FAIXA_MIN_FRAC = 0.4  # faixa menor devolve a altura inteira; origem: Instragram-Videos/pipeline/cut.py:253
FAIXA_FOLGA = 8  # px; origem: Instragram-Videos/pipeline/cut.py:255
CORTE_X_DIREITA_MIN = 0.45  # origem: Instragram-Videos/pipeline/cut.py:265
CORTE_X_ESQUERDA_MAX = 0.55  # origem: Instragram-Videos/pipeline/cut.py:269
PAINEL_FOLGA = 1.05  # × largura do rosto; origem: Instragram-Videos/pipeline/cut.py:265,269
H_TOPO_MIN, H_TOPO_MAX = 460, 1240  # origem: Instragram-Videos/pipeline/cut.py:276
ROSTO_NO_PAINEL = 0.35  # rosto a 35% do topo do painel de baixo; origem: Instragram-Videos/pipeline/cut.py:289
DESFOQUE_SIGMA = 40  # origem: Instragram-Videos/pipeline/cut.py:362
FADE_AUDIO_S = 0.012  # emenda sem estalo; origem: Instragram-Videos/pipeline/cut.py:387
CRF = "18"  # origem: Instragram-Videos/pipeline/cut.py:388
PRESET = "slow"  # origem: Instragram-Videos/pipeline/cut.py:388
AUDIO_BITRATE = "192k"  # origem: Instragram-Videos/pipeline/cut.py:389
AUDIO_TAXA = "48000"  # origem: Instragram-Videos/pipeline/cut.py:389
ROSTO_AVISO_FRAC = 0.15  # rosto em menos disso dos quadros: só aviso; origem: Instragram-Videos/pipeline/cut.py:467
TRECHO_MIN_S = 4.0  # abaixo disso não é fala, é estilhaço; origem: Instragram-Videos/pipeline/cut.py:426
JANELA_FOLGA_S = 0.51  # folga da soma dos trechos; origem: Instragram-Videos/pipeline/cut.py:422
CORTE_MIN_S = 52.0  # origem: Instragram-Videos/pipeline/lib.py:135
CORTE_ALVO_S = 60.0  # origem: Instragram-Videos/pipeline/lib.py:136
CORTE_MAX_S = 180.0  # origem: Instragram-Videos/pipeline/lib.py:137
CORTE_AVISO_FATOR = 1.25  # aviso acima de alvo × 1,25; origem: Instragram-Videos/pipeline/cut.py:438
SOBREPOSICAO_MAX = 0.20  # fração do trecho que pode repetir um corte já feito; origem: Instragram-Videos/pipeline/lib.py:140
CAUDA_ERRO = 1200  # caracteres do stderr no erro; origem: Instragram-Videos/pipeline/cut.py:391

MODOS = ("auto", "rosto", "central", "fundo_desfocado")
ROTULOS = {"fundo_desfocado": "fundo desfocado", "split": "split screencast", "misto": "misto (fala + screencast)",
           "rosto": "rosto", "central": "central fixo"}  # origem: Instragram-Videos/pipeline/cut.py:474-477


@dataclass(frozen=True)
class Formato:
    largura: int
    altura: int
    fps: int


FORMATO_VERTICAL = Formato(1080, 1920, 30)  # origem: Instragram-Videos/pipeline/lib.py:9


class ErroCorte(RuntimeError):
    """Plano de trechos fora das regras, vídeo ilegível ou ffmpeg com erro."""


def _par(n: float) -> int:
    return int(n) // 2 * 2


def _cv2():
    import cv2
    return cv2


# ------------------------------------------------------------------ detecção


def amostrar_rostos(video: str | Path) -> tuple[list[tuple[float, float, float, float]], int, int, int]:
    """([(t, fx, fy, fw)] dos quadros amostrados com rosto, quantos foram olhados, largura, altura).

    Haar frontal, quadro reduzido a 640 px de largura, cinza, `detectMultiScale(1.15, 6, 24x24)`, fica o
    maior rosto. origem: Instragram-Videos/pipeline/cut.py:97-120
    """
    cv2 = _cv2()
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ErroCorte(f"não foi possível abrir {Path(video).name}")
    fps_src = cap.get(cv2.CAP_PROP_FPS) or 30.0
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    passo = max(1, int(round(fps_src / AMOSTRAS_POR_S)))
    escala = LARGURA_ANALISE / src_w
    achados, n, idx = [], 0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % passo == 0:
            n += 1
            g = cv2.cvtColor(cv2.resize(frame, (LARGURA_ANALISE, int(src_h * escala))), cv2.COLOR_BGR2GRAY)
            faces = casc.detectMultiScale(g, HAAR_ESCALA, HAAR_VIZINHOS, minSize=HAAR_MINIMO)
            if len(faces):
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                achados.append((idx / fps_src, (x + w / 2) / escala, (y + h / 2) / escala, w / escala))
        idx += 1
    cap.release()
    return achados, n, src_w, src_h


def _perfis(video: Path, t0: float, t1: float, medir) -> list:
    cv2 = _cv2()
    import numpy as np
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    perfis = []
    for k in range(FRONTEIRA_QUADROS):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int((t0 + (t1 - t0) * (k + 0.5) / FRONTEIRA_QUADROS) * fps))
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        perfis.append(medir(g))
    cap.release()
    return perfis


def fronteira_do_painel(video: str | Path, t0: float, t1: float, fx: float, fw: float, src_w: int,
                        direita: bool) -> float:
    """A coluna em que a tela acaba e o painel da webcam começa — MEDIDA na imagem.

    Gradiente horizontal médio por coluna (Sobel ksize 3) em 5 quadros da passagem; pico dentro de ±8% da
    largura em volta da estimativa `fx ∓ 0,70·fw`, aceito se ≥ 2× a mediana do perfil; senão fica a
    estimativa. origem: Instragram-Videos/pipeline/cut.py:177-213
    """
    cv2 = _cv2()
    import numpy as np
    perfis = _perfis(Path(video), t0, t1, lambda g: np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)).mean(axis=0))
    est = fx - fw * FRONTEIRA_ESTIMATIVA if direita else fx + fw * FRONTEIRA_ESTIMATIVA
    if not perfis:
        return est
    perfil = np.mean(perfis, axis=0)
    j0 = int(max(0, est - FRONTEIRA_JANELA * src_w))
    j1 = int(min(src_w - 1, est + FRONTEIRA_JANELA * src_w))
    if j1 - j0 < 10:
        return est
    janela = perfil[j0:j1]
    pico = int(np.argmax(janela))
    return float(j0 + pico) if janela[pico] >= FRONTEIRA_PICO * float(np.median(perfil)) else est


def faixa_util_vertical(video: str | Path, t0: float, t1: float, x0: float, largura: float,
                        src_h: int) -> tuple[int, int]:
    """(y, altura) da parte da tela com conteúdo, sem as tarjas pretas.
    origem: Instragram-Videos/pipeline/cut.py:216-256"""
    import numpy as np
    perfis = _perfis(Path(video), t0, t1, lambda g: g[:, int(x0):int(x0 + largura)].mean(axis=1))
    if not perfis:
        return 0, src_h
    perfil = np.mean(perfis, axis=0)
    limiar = FAIXA_LIMIAR * float(np.percentile(perfil, FAIXA_PERCENTIL))
    claras = perfil > limiar
    melhor, atual_ini = (0, src_h), None
    for i, c in enumerate(list(claras) + [False]):
        if c and atual_ini is None:
            atual_ini = i
        elif not c and atual_ini is not None:
            if i - atual_ini > melhor[1] - melhor[0] or melhor == (0, src_h):
                melhor = (atual_ini, i)
            atual_ini = None
    y0, y1 = melhor
    if y1 - y0 < FAIXA_MIN_FRAC * src_h:
        return 0, src_h  # tema escuro: melhor moldura do que cortar o conteúdo
    y0 = max(0, y0 - FAIXA_FOLGA)
    y1 = min(src_h, y1 + FAIXA_FOLGA)
    return _par(y0), _par(y1 - y0)


def geometria_split(fx: float, fy: float, fw: float, src_w: int, src_h: int, corte_medido: float | None = None,
                    faixa: tuple[int, int] | None = None, formato: Formato = FORMATO_VERTICAL) -> dict[str, Any]:
    """Onde termina a tela e onde começa a webcam, e como os dois painéis ocupam o 9:16.
    origem: Instragram-Videos/pipeline/cut.py:259-293"""
    W, H = formato.largura, formato.altura
    direita = fx > src_w / 2
    base = corte_medido if corte_medido is not None else (
        fx - fw * FRONTEIRA_ESTIMATIVA if direita else fx + fw * FRONTEIRA_ESTIMATIVA)
    if direita:
        corte_x = _par(min(max(base, src_w * CORTE_X_DIREITA_MIN), src_w - fw * PAINEL_FOLGA))
        tela = (0, corte_x)
        painel = (corte_x, src_w - corte_x)
    else:
        corte_x = _par(min(max(base, fw * PAINEL_FOLGA), src_w * CORTE_X_ESQUERDA_MAX))
        tela = (corte_x, src_w - corte_x)
        painel = (0, corte_x)
    tela_x, tela_w = tela
    tela_y, tela_h = faixa if faixa else (0, src_h)
    h_topo = _par(min(max(round(W * tela_h / tela_w), H_TOPO_MIN), H_TOPO_MAX))
    h_baixo = H - h_topo
    painel_x, painel_w = painel
    pane_h = round(painel_w * h_baixo / W)
    if pane_h > src_h:  # painel estreito demais para a altura pedida
        painel_w = _par(round(src_h * W / h_baixo))
        painel_x = _par(min(max(fx - painel_w / 2, 0), src_w - painel_w))
        pane_h = src_h
    pane_h = _par(pane_h)
    pane_y = _par(min(max(fy - ROSTO_NO_PAINEL * pane_h, 0), src_h - pane_h))
    return {"tela": [tela_x, tela_y, _par(tela_w), _par(tela_h)],
            "painel": [painel_x, pane_y, _par(painel_w), pane_h],
            "h_topo": h_topo, "h_baixo": h_baixo,
            "lado_webcam": "direita" if direita else "esquerda",
            "corte_x": corte_x}


def passagens_screencast(video: str | Path, achados: list[tuple[float, float, float, float]], src_w: int,
                         src_h: int, dur: float, formato: Formato = FORMATO_VERTICAL) -> list[tuple[float, float, dict]]:
    """[(t0, t1, geometria)] das passagens em que o quadro é composição, não plano de fala.
    origem: Instragram-Videos/pipeline/cut.py:123-174"""
    peq = [a for a in achados
           if a[3] < src_w * ROSTO_PEQUENO_FRAC
           and not (src_w * ROSTO_CENTRADO_MIN <= a[1] <= src_w * ROSTO_CENTRADO_MAX)]
    if not peq:
        return []
    janela = 1.0 / AMOSTRAS_POR_S * BURACO_AMOSTRAS
    grupos, atual = [], [peq[0]]
    for a in peq[1:]:
        if a[0] - atual[-1][0] > janela:
            grupos.append(atual)
            atual = []
        atual.append(a)
    grupos.append(atual)

    saida = []
    for g in grupos:
        t0, t1 = max(0.0, g[0][0] - SCREENCAST_PAD_S), min(dur, g[-1][0] + SCREENCAST_PAD_S)
        if t1 - t0 < SCREENCAST_MIN_S:
            continue
        fx = statistics.median(a[1] for a in g)
        fy = statistics.median(a[2] for a in g)
        fw = statistics.median(a[3] for a in g)
        direita = fx > src_w / 2
        corte_medido = fronteira_do_painel(video, t0, t1, fx, fw, src_w, direita)
        tx0 = 0 if direita else corte_medido
        tw = corte_medido if direita else src_w - corte_medido
        faixa = faixa_util_vertical(video, t0, t1, tx0, tw, src_h)
        geo = geometria_split(fx, fy, fw, src_w, src_h, corte_medido, faixa, formato)
        geo["fronteira_medida"] = round(corte_medido, 1)
        saida.append((round(t0, 2), round(t1, 2), geo))

    # buraco curto entre passagens é falha de detecção, não mudança de cena
    juntadas: list[tuple[float, float, dict]] = []
    for p in saida:
        if juntadas and p[0] - juntadas[-1][1] < FUSAO_S:
            anterior = juntadas.pop()
            maior = anterior if anterior[1] - anterior[0] >= p[1] - p[0] else p
            juntadas.append((anterior[0], p[1], maior[2]))
        else:
            juntadas.append(p)
    cobertura = sum(b - a for a, b, _ in juntadas) / dur if dur else 0
    if cobertura >= COBERTURA_TOTAL and juntadas:
        maior = max(juntadas, key=lambda q: q[1] - q[0])
        juntadas = [(0.0, round(dur, 2), maior[2])]
    return juntadas


# ------------------------------------------------------------------ caminho do rosto


def caminho_do_rosto(achados: list[tuple[float, float, float, float]], src_w: int, crop_w: int, dur: float,
                     ignorar: Iterable[tuple[float, float, Any]]) -> tuple[list[tuple[float, float]], float]:
    """([(t, x do crop)], deslocamento total em px): mediana 7, EMA 0,25, zona morta 12%, RDP 14 px, teto 24.
    origem: Instragram-Videos/pipeline/cut.py:297-343"""
    ignorar = list(ignorar)
    grandes = [a for a in achados if not any(t0 <= a[0] <= t1 for t0, t1, _ in ignorar)]
    if len(grandes) < AMOSTRAS_MIN:
        return [(0.0, round((src_w - crop_w) / 2.0, 1))], 0.0

    ts = [a[0] for a in grandes]
    xs = [a[1] for a in grandes]
    jan = max(3, int(AMOSTRAS_POR_S * SUAVE_S) | 1)
    med = []
    for i in range(len(xs)):
        j = sorted(xs[max(0, i - jan // 2):i + jan // 2 + 1])
        med.append(j[len(j) // 2])
    suav, acc = [], med[0]
    for v in med:
        acc += (v - acc) * EMA
        suav.append(acc)

    alvo, atual, banda = [], suav[0], crop_w * ZONA_MORTA_FRAC
    for v in suav:
        if abs(v - atual) > banda:
            atual = v - banda if v > atual else v + banda
        alvo.append(atual)
    xs_crop = [min(max(v - crop_w / 2.0, 0.0), src_w - crop_w) for v in alvo]

    def dp(i: int, j: int, marcados: set[int]) -> None:
        if j - i < 2:
            return
        t0, x0, t1, x1 = ts[i], xs_crop[i], ts[j], xs_crop[j]
        pior, k = 0.0, None
        for m in range(i + 1, j):
            prev = x0 + (x1 - x0) * ((ts[m] - t0) / (t1 - t0)) if t1 > t0 else x0
            d = abs(xs_crop[m] - prev)
            if d > pior:
                pior, k = d, m
        if pior > EPS_PX and k is not None:
            marcados.add(k)
            dp(i, k, marcados)
            dp(k, j, marcados)

    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))
    marc = {0, len(ts) - 1}
    dp(0, len(ts) - 1, marc)
    chave = sorted(marc)
    if len(chave) > MAX_PONTOS:
        passo = (len(chave) - 1) / (MAX_PONTOS - 1)
        chave = sorted({chave[min(len(chave) - 1, int(round(k * passo)))] for k in range(MAX_PONTOS)})
    caminho = [(round(ts[i], 3), round(xs_crop[i], 1)) for i in chave]
    return caminho, max(x for _, x in caminho) - min(x for _, x in caminho)


def expr_de(caminho: list[tuple[float, float]]) -> str:
    """Expressão por partes `if(lt(t,..),..)` para o `x` do filtro crop. origem: Instragram-Videos/pipeline/cut.py:346-353"""
    if len(caminho) == 1:
        return f"{caminho[0][1]}"
    expr = f"{caminho[-1][1]}"
    for (t0, x0), (t1, x1) in reversed(list(zip(caminho, caminho[1:]))):
        seg = f"{x0}+({x1 - x0})*(t-{t0})/{max(t1 - t0, 0.001):.3f}" if x1 != x0 else f"{x0}"
        expr = f"if(lt(t,{t1}),{seg},{expr})"
    return expr


# ------------------------------------------------------------------ render


def _sh(args: list[str], **kw: Any) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, **kw)
    except FileNotFoundError as e:
        raise ErroCorte(f"binário não encontrado: {args[0]}") from e


def renderizar(entrada: str | Path, saida: str | Path, src_w: int, src_h: int, expr: str, crop_w: int,
               crop_h: int, screencasts: list[tuple[float, float, dict]], fundo_desfocado: bool,
               formato: Formato = FORMATO_VERTICAL, tem_audio: bool = True) -> None:
    """Uma passada de ffmpeg: crop que segue o rosto (ou fundo desfocado) e os splits de screencast.
    origem: Instragram-Videos/pipeline/cut.py:357-391"""
    W, H, FPS = formato.largura, formato.altura, formato.fps
    partes, n_split = [], 1 + 2 * len(screencasts)
    if fundo_desfocado:
        partes.append(f"[0:v]split={n_split + 1}[bg][fg]"
                      + "".join(f"[s{i}t][s{i}b]" for i in range(len(screencasts))) + ";")
        partes.append(f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                      f"gblur=sigma={DESFOQUE_SIGMA}[bgb];")
        partes.append(f"[fg]scale={W}:-2:flags=lanczos[fgs];")
        partes.append("[bgb][fgs]overlay=0:(H-h)/2[base];")
    else:
        partes.append(f"[0:v]split={n_split}[b]" + "".join(f"[s{i}t][s{i}b]" for i in range(len(screencasts))) + ";")
        partes.append(f"[b]crop=w={crop_w}:h={crop_h}:x='{expr}':y=(ih-{crop_h})/2,"
                      f"scale={W}:{H}:flags=lanczos[base];")
    atual = "base"
    for i, (t0, t1, g) in enumerate(screencasts):
        tx, ty, tw, th = g["tela"]
        px, py, pw, ph = g["painel"]
        partes.append(f"[s{i}t]crop=w={tw}:h={th}:x={tx}:y={ty},scale={W}:{g['h_topo']}:flags=lanczos[t{i}];")
        partes.append(f"[s{i}b]crop=w={pw}:h={ph}:x={px}:y={py},scale={W}:{g['h_baixo']}:flags=lanczos[p{i}];")
        partes.append(f"[{atual}][t{i}]overlay=0:0:enable='between(t,{t0},{t1})'[a{i}];")
        partes.append(f"[a{i}][p{i}]overlay=0:{g['h_topo']}:enable='between(t,{t0},{t1})'[c{i}];")
        atual = f"c{i}"
    partes.append(f"[{atual}]fps={FPS},format=yuv420p[v]")
    audio = (["-map", "0:a",
              "-af", f"afade=t=in:st=0:d={FADE_AUDIO_S},areverse,afade=t=in:st=0:d={FADE_AUDIO_S},areverse",
              "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", AUDIO_TAXA] if tem_audio else ["-an"])
    r = _sh(["ffmpeg", "-y", "-v", "error", "-i", str(entrada), "-filter_complex", "".join(partes),
             "-map", "[v]", *audio, "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, str(saida)])
    if r.returncode:
        raise ErroCorte(f"erro no reenquadramento:\n{r.stderr[-CAUDA_ERRO:]}")


def cortar(entrada: str | Path, saida: str | Path, *, modo: str = "auto", sem_split: bool = False,
           formato: Formato = FORMATO_VERTICAL) -> dict[str, Any]:
    """Reenquadra `entrada` (16:9) em 9:16 e grava `saida`. Devolve o relato da peça.

    Relato: ``{modo, enquadramento, motivo, screencast: [[t0, t1, lado, largura_tela, h_topo]],
    fronteiras, caminho: [[t, x]], deslocamento_px, rostos: {com_rosto, amostrados}, duracao, avisos}``.
    """
    if modo not in MODOS:
        raise ValueError(f"modo desconhecido: {modo!r} (válidos: {', '.join(MODOS)})")
    entrada, saida = Path(entrada), Path(saida)
    s = ffmpeg.sondar(entrada)
    src_w, src_h, dur = s["largura"], s["altura"], s["duracao"] or 0.0
    if not src_w or not src_h:
        raise ErroCorte(f"{entrada.name} não tem trilha de vídeo")
    tem_audio = s["taxa_audio"] is not None
    W, H = formato.largura, formato.altura
    crop_w = _par(min(src_w, round(src_h * W / H)))  # origem: Instragram-Videos/pipeline/cut.py:456-457
    crop_h = _par(min(src_h, round(crop_w * H / W)))
    avisos: list[str] = []

    achados, n = ([], 0)
    if modo in ("auto", "rosto"):
        achados, n, _, _ = amostrar_rostos(entrada)
    scr = [] if (sem_split or modo not in ("auto", "rosto")) else passagens_screencast(
        entrada, achados, src_w, src_h, dur, formato)
    cobertura = sum(t1 - t0 for t0, t1, _ in scr) / dur if dur else 0.0
    fora_scr = [a for a in achados if not any(t0 <= a[0] <= t1 for t0, t1, _ in scr)]

    motivo = None
    if modo == "fundo_desfocado":
        chave, motivo = "fundo_desfocado", "pedido por quem chamou"
    elif modo == "auto" and not scr and len(fora_scr) < AMOSTRAS_MIN:
        chave = "fundo_desfocado"
        motivo = (f"sem rosto: {len(achados)} de {n} quadros amostrados com rosto e nenhum screencast — o "
                  "16:9 inteiro vai no meio, sobre ele mesmo desfocado")
    else:
        chave = None
    fundo = chave == "fundo_desfocado"

    if fundo or modo == "central" or not achados:
        caminho, movimento = [(0.0, round((src_w - crop_w) / 2.0, 1))], 0.0
    else:
        caminho, movimento = caminho_do_rosto(achados, src_w, crop_w, dur, scr)
    if chave is None:
        chave = ("split" if cobertura > COBERTURA_SPLIT else "misto" if scr else
                 "rosto" if movimento > 1 else "central")
        motivo = {"split": "a peça é screencast: tela em cima, rosto embaixo",
                  "misto": "fala com passagens de screencast",
                  "rosto": "o crop segue o rosto",
                  "central": "rosto parado no meio, poucas amostras ou crop central pedido"}[chave]
    if achados and not scr and len(achados) < max(AMOSTRAS_MIN, ROSTO_AVISO_FRAC * n):
        # origem: Instragram-Videos/pipeline/cut.py:467-469 — só aviso
        avisos.append("poucos quadros com rosto e nenhum screencast: confira o enquadramento")

    saida.parent.mkdir(parents=True, exist_ok=True)
    renderizar(entrada, saida, src_w, src_h, expr_de(caminho), crop_w, crop_h, [] if fundo else scr, fundo,
               formato, tem_audio)
    return {
        "modo": chave,
        "enquadramento": ROTULOS[chave],
        "motivo": motivo,
        "screencast": [[t0, t1, g["lado_webcam"], g["tela"][2], g["h_topo"]] for t0, t1, g in ([] if fundo else scr)],
        "fronteiras": [g.get("fronteira_medida") for _, _, g in ([] if fundo else scr)],
        "caminho": [[t, x] for t, x in caminho],
        "deslocamento_px": round(movimento, 1),
        "rostos": {"com_rosto": len(achados), "amostrados": n},
        "duracao": round(dur, 2),
        "avisos": avisos,
    }


# ------------------------------------------------------------------ trechos


def extrair_trecho(video: str | Path, inicio: float, fim: float, destino: str | Path) -> Path:
    """Recorta [inicio, fim] do vídeo longo local num arquivo intermediário quase sem perda.

    Faz o papel do download por `--download-sections` da origem, sobre um arquivo local: busca exata e
    re-encode (x264 crf 12, aac 192k 48 kHz) para o corte começar e terminar no instante pedido.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    r = _sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{inicio:.3f}", "-i", str(video), "-t", f"{fim - inicio:.3f}",
             "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", AUDIO_TAXA, str(destino)])
    if r.returncode or not destino.exists():
        raise ErroCorte(f"erro ao extrair o trecho {inicio:.1f}-{fim:.1f}s:\n{r.stderr[-CAUDA_ERRO:]}")
    return destino


def validar_trechos(trechos: list[dict[str, Any]], *, faixas_ja_usadas: Iterable[Iterable[float]] = (),
                    minimo: float = CORTE_MIN_S, maximo: float = CORTE_MAX_S,
                    alvo: float = CORTE_ALVO_S) -> tuple[list[dict[str, Any]], list[str]]:
    """(trechos ordenados, avisos). Levanta ErroCorte antes de qualquer render se o plano quebra a regra.
    origem: Instragram-Videos/pipeline/cut.py:417-440"""
    if not trechos:
        raise ErroCorte("plano sem trechos")
    lista = []
    for t in trechos:
        d = dict(t)
        d["inicio"], d["fim"] = float(d["inicio"]), float(d["fim"])
        lista.append(d)
    lista.sort(key=lambda t: t["inicio"])
    total = sum(t["fim"] - t["inicio"] for t in lista)
    if not (minimo - JANELA_FOLGA_S <= total <= maximo + JANELA_FOLGA_S):
        raise ErroCorte(f"{len(lista)} trecho(s) somam {total:.1f}s, fora da janela {minimo:.0f}-{maximo:.0f}s")
    for i, t in enumerate(lista):
        if t["fim"] - t["inicio"] < TRECHO_MIN_S:
            raise ErroCorte(f"trecho #{i + 1} tem {t['fim'] - t['inicio']:.1f}s — abaixo de "
                            f"{TRECHO_MIN_S:.0f}s não é fala, é estilhaço")
        if i and t["inicio"] < lista[i - 1]["fim"]:
            raise ErroCorte(f"trecho #{i + 1} se sobrepõe ao anterior")
    usadas = [tuple(f) for f in faixas_ja_usadas]
    for t in lista:
        d = t["fim"] - t["inicio"]
        for ini_u, fim_u in usadas:
            if max(0.0, min(t["fim"], fim_u) - max(t["inicio"], ini_u)) / d > SOBREPOSICAO_MAX:
                raise ErroCorte(f"o trecho {t['inicio']:.0f}-{t['fim']:.0f}s já virou vídeo ({ini_u:.0f}-{fim_u:.0f}s)")
    avisos = []
    if total > alvo * CORTE_AVISO_FATOR:
        avisos.append(f"{total:.0f}s no total; o alvo é {alvo:.0f}s: passar disso só se paga se a ideia não couber")
    return lista, avisos


def cortar_trechos(video: str | Path, trechos: list[dict[str, Any]], pasta: str | Path, *, modo: str = "auto",
                   sem_split: bool = False, faixas_ja_usadas: Iterable[Iterable[float]] = (),
                   minimo: float = CORTE_MIN_S, maximo: float = CORTE_MAX_S,
                   formato: Formato = FORMATO_VERTICAL, nome: str = "corte9x16.mp4") -> dict[str, Any]:
    """Extrai, reenquadra e junta os trechos em `pasta/<nome>`. Devolve o relato do corte
    (`trechos` com o relato de cada peça, `inicio`, `fim`, `duracao`, `montagem`, `video`, `avisos`).
    origem: Instragram-Videos/pipeline/cut.py:449-500"""
    lista, avisos = validar_trechos(trechos, faixas_ja_usadas=faixas_ja_usadas, minimo=minimo, maximo=maximo)
    pasta = Path(pasta)
    pecas_dir = pasta / "pecas"
    pecas_dir.mkdir(parents=True, exist_ok=True)
    pecas, relato = [], []
    for i, t in enumerate(lista):
        bruto = extrair_trecho(video, t["inicio"], t["fim"], pecas_dir / f"{i:02d}_src.mp4")
        peca = pecas_dir / f"{i:02d}.mp4"
        r = cortar(bruto, peca, modo=modo, sem_split=sem_split, formato=formato)
        avisos += [f"trecho #{i + 1}: {a}" for a in r["avisos"]]
        pecas.append(peca)
        relato.append({**t, "duracao": r["duracao"], "modo": r["modo"], "enquadramento": r["enquadramento"],
                       "motivo": r["motivo"], "screencast": r["screencast"], "deslocamento_px": r["deslocamento_px"],
                       "caminho": r["caminho"]})
    final = pasta / nome
    if len(pecas) == 1:
        pecas[0].replace(final)
    else:
        try:
            ffmpeg.concatenar(pecas, final)
        except ffmpeg.ErroFfmpeg as erro:
            raise ErroCorte(str(erro)) from None
    dur_final = ffmpeg.sondar(final)["duracao"] or 0.0
    return {"trechos": relato, "inicio": lista[0]["inicio"], "fim": lista[-1]["fim"], "duracao": round(dur_final, 2),
            "montagem": "trecho único" if len(lista) == 1 else f"{len(lista)} trechos juntados",
            "video": final, "avisos": avisos}
