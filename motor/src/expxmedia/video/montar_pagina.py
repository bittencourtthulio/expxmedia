"""Montagem do reel de página capturada (capacidade `editar_video`, D-38).

Porta de `Instragram-Videos/pipeline/compose.py` (rolagem, cartão de impacto, selo de CTA, abertura de
fundo, legendas, narração e loudnorm) e da checagem de teto de `Instragram-Videos/pipeline/stitch.py`.
Os números são os da origem; o que é marca vem de fora do código (M13): fonte e cores da Alma
(`estilo_da_alma`), o texto do selo da peça, as linhas do cartão de impacto do roteiro. A geometria da
interface do canal (topo coberto pela UI, faixa da legenda, onde mora o selo) é parâmetro do formato
(`Geometria`), com o formato vertical da origem como padrão.

Entradas, na pasta de trabalho `pasta` (as do concat são relativas a ela, e o ffmpeg roda com `cwd` nela):

- a tira (`tira.png`, já na largura do vídeo) e o `captura.json` (`secoes[{t,y}]`, `px_por_css`);
- `caps.txt` + `caps/*.png` + `legendas.json` (`duracao`, `offset_audio`, `cta`), da legenda do reel;
- `narracao.mp3`;
- as linhas do cartão de impacto (até 3), por argumento ou em `impacto.txt`;
- opcional: `abertura.mp4` + `abertura.json` (com `rosto` medido), o clipe que troca o fundo da janela
  do cartão.

Três passadas de ffmpeg (8.x, sem libass: tudo é PNG por `overlay`):

1. **rolagem**: segura o topo por 3,5 s com cartão (2,0 s sem) e rola até a fronteira de seção cuja
   velocidade fica entre 90 e 230 px/s, a mais perto de 160 ("abaixo arrasta, acima borra"); nenhuma
   fronteira serve, rola a 160 px/s até onde der. `crop` sem `eval` (removido no ffmpeg 8);
2. **composição**: cartão de impacto (2,5 s, página desfocada e véu, ou por cima da abertura), selo do
   CTA de 5 s até 0,05 s antes do card final, legendas e a narração atrasada por `adelay ...:all=1`
   (silêncio real no grafo; nunca `-itsoffset`, que a plataforma perde no re-encode; `all=1` porque a
   narração é mono). O vídeo fecha junto com o card do CTA: a duração é o fim do último cartão cortado
   na grade de quadros (um quadro de folga), não a do áudio mais uma sobra;
3. **loudnorm em duas passadas sobre a mistura** (`ffmpeg.normalizar_audio`), vídeo copiado.

`visual.json` (o que foi ao ar) e `abertura.json.montado_em` são gravados **depois** do MP4 final:
gravar antes deixaria a coorte "mentindo" quando uma passada falha.
"""
from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from expxmedia.alma import fontes as _fontes
from expxmedia.nucleo import arquivos, tempo
from expxmedia.video import ffmpeg
from expxmedia.video.verificar import ultimo_cartao

__all__ = [
    "ErroMontagem",
    "ErroTiraAcimaDoTeto",
    "EstiloMontagem",
    "Geometria",
    "GEOMETRIA_VERTICAL",
    "LIMITE_TEXTURA",
    "IMPACTO_S",
    "SELO_INICIO_S",
    "VEL_IDEAL",
    "VEL_MIN",
    "VEL_MAX",
    "MAX_LINHAS_IMPACTO",
    "estilo_da_alma",
    "escolher_cartao",
    "escolher_rolagem",
    "duracao_final",
    "montar",
]

# ------------------------------------------------------------------ números da origem

LIMITE_TEXTURA = 16384  # altura máxima da tira (textura ffmpeg/PIL); origem: Instragram-Videos/pipeline/stitch.py:23
IMPACTO_S = 2.5  # janela do cartão de impacto; origem: Instragram-Videos/pipeline/compose.py:25
SELO_INICIO_S = 5.0  # o selo do CTA entra aqui; origem: Instragram-Videos/pipeline/compose.py:25
HOLD_EXTRA_S = 1.0  # topo parado depois do cartão; origem: Instragram-Videos/pipeline/compose.py:117
HOLD_SEM_IMPACTO_S = 2.0  # origem: Instragram-Videos/pipeline/compose.py:117
VEL_IDEAL, VEL_MIN, VEL_MAX = 160.0, 90.0, 230.0  # px/s; origem: Instragram-Videos/pipeline/compose.py:138
MAX_LINHAS_IMPACTO = 3  # origem: Instragram-Videos/pipeline/compose.py:194
CARTAO_TAM_MAX, CARTAO_TAM_MIN, CARTAO_TAM_PASSO = 150, 72, 2  # origem: Instragram-Videos/pipeline/compose.py:62,75
CARTAO_MARGEM = 200  # o cartão cabe em W - 200; origem: Instragram-Videos/pipeline/compose.py:73
CARTAO_ENTRELINHA = 1.18  # altura da linha = round(tam * 1.18); origem: Instragram-Videos/pipeline/compose.py:59,199
CARTAO_PAD_X = 110  # largura = maior linha + 110; origem: Instragram-Videos/pipeline/compose.py:200
CARTAO_PAD_Y = 70  # altura = linhas * alt_linha + 70; origem: Instragram-Videos/pipeline/compose.py:201
CARTAO_TOPO_TEXTO = 35  # origem: Instragram-Videos/pipeline/compose.py:215
CARTAO_RAIO = 34  # origem: Instragram-Videos/pipeline/compose.py:213
ALFA_VEU = 120  # véu sobre a página desfocada; origem: Instragram-Videos/pipeline/compose.py:218
DESFOQUE_SIGMA = 26  # origem: Instragram-Videos/pipeline/compose.py:226
DESFOQUE_ANTES_S = 0.15  # o desfoque sai antes do cartão; origem: Instragram-Videos/pipeline/compose.py:226
FADE_CARTAO_S = 0.3  # origem: Instragram-Videos/pipeline/compose.py:228
SELO_TAM = 44  # origem: Instragram-Videos/pipeline/compose.py:235
SELO_ALTURA = 84  # origem: Instragram-Videos/pipeline/compose.py:238
SELO_PAD_X = 64  # origem: Instragram-Videos/pipeline/compose.py:238
SELO_TEXTO_X = 32  # origem: Instragram-Videos/pipeline/compose.py:246
SELO_RAIO = 42  # origem: Instragram-Videos/pipeline/compose.py:244
SELO_CONTORNO = 4  # origem: Instragram-Videos/pipeline/compose.py:245
ALFA_SELO = 225  # origem: Instragram-Videos/pipeline/compose.py:244
SELO_ANTES_DO_CARD_S = 0.05  # o selo sai antes do card final (cauda comparada por pixel); origem: Instragram-Videos/pipeline/compose.py:252
CRF_ROLAGEM = "18"  # origem: Instragram-Videos/pipeline/compose.py:163
CRF_COMPOSICAO = "19"  # origem: Instragram-Videos/pipeline/compose.py:278
PRESET = "slow"  # origem: Instragram-Videos/pipeline/compose.py:163,278
AUDIO_BITRATE = "192k"  # origem: Instragram-Videos/pipeline/compose.py:279
AUDIO_TAXA = 48000  # origem: Instragram-Videos/pipeline/compose.py:276
CAUDA_ERRO = 800  # caracteres do stderr no erro; origem: Instragram-Videos/pipeline/compose.py:288


@dataclass(frozen=True)
class Geometria:
    """Geometria do formato e da interface do canal por cima do vídeo (parâmetro do formato)."""
    largura: int
    altura: int
    fps: int
    topo_ui: int  # acima disso a interface do canal cobre
    area_segura_inferior: int  # faixa inferior reservada à interface
    legenda_topo: int  # a legenda mais alta começa perto daqui
    cartao_centro_y: int  # centro do cartão sem rosto na abertura (centro óptico)
    selo_base_y: int  # base do selo do CTA, acima da legenda mais alta


GEOMETRIA_VERTICAL = Geometria(
    largura=1080,  # origem: Instragram-Videos/pipeline/lib.py:9
    altura=1920,  # origem: Instragram-Videos/pipeline/lib.py:9
    fps=30,  # origem: Instragram-Videos/pipeline/lib.py:9
    topo_ui=250,  # origem: Instragram-Videos/pipeline/compose.py:52
    area_segura_inferior=420,  # origem: Instragram-Videos/pipeline/lib.py:10
    legenda_topo=1260,  # origem: Instragram-Videos/pipeline/compose.py:53
    cartao_centro_y=780,  # origem: Instragram-Videos/pipeline/compose.py:76,100
    selo_base_y=1240,  # origem: Instragram-Videos/pipeline/compose.py:243
)


@dataclass(frozen=True)
class EstiloMontagem:
    fonte: Path
    cartao_fundo: tuple[int, int, int, int]
    cartao_texto: tuple[int, int, int, int]
    veu: tuple[int, int, int, int]
    selo_fundo: tuple[int, int, int, int]
    selo_contorno: tuple[int, int, int, int]
    selo_texto: tuple[int, int, int, int]
    selo_cta: tuple[int, int, int, int]


class ErroMontagem(RuntimeError):
    """A montagem não pôde começar ou uma passada do ffmpeg falhou."""


class ErroTiraAcimaDoTeto(ErroMontagem):
    """A tira passa do limite de textura (16384 px)."""


# ------------------------------------------------------------------ estilo


def _rgba(hexa: str, alfa: int = 255) -> tuple[int, int, int, int]:
    h = str(hexa).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ErroMontagem(f"cor inválida na Alma: {hexa!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alfa


def estilo_da_alma(alma: Any, *, raiz: Path | str | None = None, papel_fonte: str = "titulo",
                   cache: Path | str | None = None) -> tuple[EstiloMontagem, list[str]]:
    """(estilo, avisos) a partir da Alma.

    Papéis de cor: cartão em `destaque_2` com letra em `texto`; véu e fundo do selo em `texto`
    (escuro por baixo de letra clara, o mesmo par da caixa da legenda); selo com letra em
    `texto_inverso` e a palavra do CTA e o contorno em `destaque` (a cor do CTA na legenda). Fonte do
    `papel_fonte`; sem fonte resolvida, a Inter embarcada, com aviso.
    """
    dados = alma.dados if hasattr(alma, "dados") else alma
    cores = ((dados.get("visual") or {}).get("cores")) or {}
    faltam = [p for p in ("texto", "texto_inverso", "destaque", "destaque_2") if not isinstance(cores.get(p), str)]
    if faltam:
        raise ErroMontagem(f"a Alma não tem as cores {', '.join(faltam)} (visual.cores)")
    resolvida = _fontes.resolver_fonte(dados, papel_fonte, raiz=raiz, cache=cache)
    avisos = [resolvida.aviso] if resolvida.aviso else []
    arquivo = resolvida.arquivos[-1] if resolvida.origem == "embarcada" else resolvida.arquivos[0]
    return EstiloMontagem(
        fonte=Path(arquivo),
        cartao_fundo=_rgba(cores["destaque_2"]),
        cartao_texto=_rgba(cores["texto"]),
        veu=_rgba(cores["texto"], ALFA_VEU),
        selo_fundo=_rgba(cores["texto"], ALFA_SELO),
        selo_contorno=_rgba(cores["destaque"]),
        selo_texto=_rgba(cores["texto_inverso"]),
        selo_cta=_rgba(cores["destaque"]),
    ), avisos


# ------------------------------------------------------------------ decisões


def _medidas(fonte: Path, linhas: list[str], tam: int) -> tuple[int, float]:
    f = ImageFont.truetype(str(fonte), tam)
    return round(tam * CARTAO_ENTRELINHA) * len(linhas) + CARTAO_PAD_Y, max(f.getlength(l) for l in linhas)


def escolher_cartao(rosto: dict[str, int] | None, linhas: list[str], piso: int, *, fonte: Path,
                    geometria: Geometria = GEOMETRIA_VERTICAL) -> tuple[int, int, str, str | None]:
    """(centro y, tamanho, por quê, aviso) do cartão de impacto, desviando do rosto da abertura.

    Sem rosto medido: a maior fonte (150 → 72, passo 2) que caiba na largura, no centro óptico. Com
    rosto: as faixas abaixo (base do rosto → piso) e acima (topo da UI → topo do rosto), a maior
    primeiro, encolhendo até caber; não coube em nenhuma, fica na maior e **avisa** — nunca em silêncio.
    origem: Instragram-Videos/pipeline/compose.py:62-91
    """
    tamanhos = range(CARTAO_TAM_MAX, CARTAO_TAM_MIN - 1, -CARTAO_TAM_PASSO)

    def largura_ok(t: int) -> bool:
        return _medidas(fonte, linhas, t)[1] <= geometria.largura - CARTAO_MARGEM

    if not rosto:
        tam = next((t for t in tamanhos if largura_ok(t)), CARTAO_TAM_MIN)
        return geometria.cartao_centro_y, tam, "posição de sempre (sem rosto na abertura)", None
    faixas = [("abaixo do rosto", int(rosto["base"]), piso),
              ("acima do rosto", geometria.topo_ui, int(rosto["topo"]))]
    faixas.sort(key=lambda f: f[2] - f[1], reverse=True)
    for nome, a, b in faixas:
        for tam in tamanhos:
            alt, _ = _medidas(fonte, linhas, tam)
            if largura_ok(tam) and alt <= b - a:
                return (a + b) // 2, tam, f"{nome} (rosto em y {rosto['topo']}-{rosto['base']})", None
    nome, a, b = faixas[0]
    aviso = (f"o cartão não cabe nem acima nem abaixo do rosto (y {rosto['topo']}-{rosto['base']}) nem "
             f"encolhendo até {CARTAO_TAM_MIN}px. Fica na faixa maior, {nome}, e VAI encostar no rosto. "
             "Gere a abertura com o rosto mais alto, ou encurte o impacto.")
    tam = next((t for t in tamanhos if largura_ok(t)), CARTAO_TAM_MIN)
    alt, _ = _medidas(fonte, linhas, tam)
    y = max(geometria.topo_ui + alt // 2, min(b - alt // 2, (a + b) // 2))
    return y, tam, f"{nome} (apertado)", aviso


def duracao_final(legendas_duracao: float, fim_cartao: float, fps: int) -> float:
    """O vídeo fecha junto com o último cartão (o card do CTA), cortado na fronteira de quadro anterior.

    `-t` emite pts < t e o concat arredonda o fim do cartão para a grade de 1/FPS: cortar no valor
    cru deixa o último quadro cair no blank seguinte, justamente o que congela no loop.
    origem: Instragram-Videos/pipeline/compose.py:123-130
    """
    dur = legendas_duracao
    if fim_cartao > 0:
        dur = min(dur, math.floor(round(fim_cartao * fps, 6)) / fps)
    return dur


def escolher_rolagem(secoes: list[dict[str, Any]], px_por_css: float, strip_h: int, tempo_rolagem: float,
                     altura: int) -> tuple[int, float, str]:
    """(percurso px, velocidade px/s, por quê): termina numa fronteira de seção quando a velocidade
    fica legível (90 a 230 px/s, a mais perto de 160); senão 160 px/s até onde a tira der.
    origem: Instragram-Videos/pipeline/compose.py:136-157
    """
    percurso_max = strip_h - altura
    alvo, escolha = None, "página inteira"
    for s in sorted(secoes, key=lambda x: x["y"]):
        fim = min(s["y"] * px_por_css - altura, percurso_max)
        if fim <= 0:
            continue
        v = fim / tempo_rolagem
        if VEL_MIN <= v <= VEL_MAX and (alvo is None or abs(v - VEL_IDEAL) < abs(alvo[1] - VEL_IDEAL)):
            alvo, escolha = (fim, v), f"termina em '{s['t']}'"
    if alvo is None:
        fim = min(percurso_max, VEL_IDEAL * tempo_rolagem)
        alvo = (fim, fim / tempo_rolagem)
    return round(alvo[0]), round(alvo[1], 2), escolha


# ------------------------------------------------------------------ montagem


def _sh(args: list[str], **kw: Any) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, **kw)
    except FileNotFoundError as e:
        raise ErroMontagem(f"binário não encontrado: {args[0]}") from e


def _duracao_arquivo(caminho: Path) -> float:
    r = _sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(caminho)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise ErroMontagem(f"ffprobe não leu a duração de {caminho.name}") from None


def _conferir_tira(tira: Path, geometria: Geometria) -> tuple[int, int]:
    if not tira.is_file():
        raise ErroMontagem(f"tira ausente: {tira.name} (capture a página antes)")
    Image.MAX_IMAGE_PIXELS = None  # a tira é alta por natureza; o teto que vale é o de textura
    with Image.open(tira) as img:
        largura, altura = img.size
    if altura > LIMITE_TEXTURA:
        # origem: Instragram-Videos/pipeline/stitch.py:23-25
        raise ErroTiraAcimaDoTeto(
            f"tira de {altura}px passa do limite de textura ({LIMITE_TEXTURA}). Reduza o alcance da "
            "captura ou aumente a largura CSS da captura (nunca reduza a qualidade).")
    if largura != geometria.largura:
        raise ErroMontagem(f"tira com {largura}px de largura; o formato pede {geometria.largura}px")
    if altura < geometria.altura:
        raise ErroMontagem(f"tira com {altura}px de altura, menor que o quadro ({geometria.altura}px)")
    return largura, altura


def _linhas_impacto(pasta: Path, impacto: list[str] | str | None) -> list[str]:
    if impacto is None:
        arq = pasta / "impacto.txt"
        impacto = arq.read_text(encoding="utf-8") if arq.exists() else ""
    if isinstance(impacto, str):
        impacto = impacto.strip().splitlines()
    return [str(l).strip() for l in impacto if str(l).strip()]


def montar(
    pasta: str | Path,
    *,
    estilo: EstiloMontagem,
    saida: str | Path | None = None,
    tira: str | Path | None = None,
    captura: str | Path | None = None,
    impacto: list[str] | str | None = None,
    sem_impacto: bool = False,
    selo: str | None = None,
    sem_selo: bool = False,
    sem_abertura: bool = False,
    geometria: Geometria = GEOMETRIA_VERTICAL,
    raiz: str | Path | None = None,
) -> dict[str, Any]:
    """Monta o reel na `pasta` de trabalho e grava o MP4 em `saida` (padrão: `pasta/final.mp4`).

    `impacto`: linhas do cartão (lista ou texto); sem ele, `impacto.txt` da pasta; nenhum dos dois é
    erro, a menos que `sem_impacto=True` (a válvula da origem). `selo`: o texto do selo com `{cta}`
    onde entra a palavra (copy da peça ou da Alma, nunca do código); sem `selo`, ou com `sem_selo`, ou
    sem CTA na legenda, não há selo. `tira`/`captura`: padrão `tira.png` e `captura.json` da pasta.

    Devolve `{video, duracao, rolagem, cartao, selo, abertura, visual, loudness, avisos}`.
    """
    pasta = Path(pasta).resolve()
    tira = Path(tira) if tira is not None else pasta / "tira.png"
    captura = Path(captura) if captura is not None else pasta / "captura.json"
    saida = Path(saida) if saida is not None else pasta / "final.mp4"
    W, H, FPS = geometria.largura, geometria.altura, geometria.fps
    avisos: list[str] = []

    _, strip_h = _conferir_tira(tira, geometria)
    for nome in ("caps.txt", "legendas.json", "narracao.mp3"):
        if not (pasta / nome).is_file():
            raise ErroMontagem(f"artefato ausente na pasta de montagem: {nome}")
    if not captura.is_file():
        raise ErroMontagem(f"artefato ausente: {captura.name} (seções da captura)")
    cap = arquivos.ler_json(captura)
    leg = arquivos.ler_json(pasta / "legendas.json")

    linhas = [] if sem_impacto else _linhas_impacto(pasta, impacto)
    com_impacto = not sem_impacto
    if com_impacto and not linhas:
        # origem: Instragram-Videos/pipeline/compose.py:111-114
        raise ErroMontagem("cartão de impacto sem texto: o reel de página abre com até 3 linhas curtas em CAIXA "
                           "ALTA com a coisa concreta do gancho. Para montar sem ele de propósito: sem_impacto.")
    if len(linhas) > MAX_LINHAS_IMPACTO:
        # origem: Instragram-Videos/pipeline/compose.py:194-196
        raise ErroMontagem(f"o cartão de impacto tem {len(linhas)} linhas — o teto é {MAX_LINHAS_IMPACTO}. O "
                           f"cartão fica {IMPACTO_S:g}s na tela: mais que isso ninguém lê.")
    cta = leg.get("cta")
    com_selo = bool(selo) and not sem_selo and bool(cta)
    if selo and not sem_selo and not cta:
        avisos.append("selo de CTA pedido, mas a legenda não tem CTA: montado sem selo")

    # abertura gerada: troca o fundo da janela do cartão. origem: Instragram-Videos/pipeline/compose.py:38-40
    arq_abertura = pasta / "abertura.mp4"
    com_abertura = com_impacto and arq_abertura.exists() and not sem_abertura
    abert_s = round(_duracao_arquivo(arq_abertura), 3) if com_abertura else 0.0
    rosto = None
    if com_abertura and (pasta / "abertura.json").exists():
        rosto = arquivos.ler_json(pasta / "abertura.json").get("rosto")
    legenda_espera = bool(rosto)  # origem: Instragram-Videos/pipeline/compose.py:95-103

    cartao_y, cartao_tam, cartao_por_que = geometria.cartao_centro_y, None, "posição de sempre"
    if com_impacto:
        piso = (H - geometria.area_segura_inferior) if legenda_espera else geometria.legenda_topo
        cartao_y, cartao_tam, cartao_por_que, aviso = escolher_cartao(rosto, linhas, piso, fonte=estilo.fonte,
                                                                      geometria=geometria)
        if aviso:
            avisos.append(aviso)

    hold = IMPACTO_S + HOLD_EXTRA_S if com_impacto else HOLD_SEM_IMPACTO_S
    caps_txt = pasta / "caps.txt"
    _, ini_card, fim_cartao = ultimo_cartao(caps_txt)
    dur = duracao_final(leg["duracao"], fim_cartao, FPS)
    if dur < leg["duracao"]:
        avisos.append(f"cauda muda aparada: {leg['duracao'] - dur:.2f}s — o vídeo fecha em {dur}s, com o cartão")
    atraso_ms = round(leg["offset_audio"] * 1000)  # origem: Instragram-Videos/pipeline/compose.py:135
    tempo_rolagem = dur - hold
    if tempo_rolagem <= 0:
        raise ErroMontagem(f"vídeo de {dur}s não passa do topo parado ({hold}s)")
    percurso, vel, escolha = escolher_rolagem(cap.get("secoes") or [], float(cap["px_por_css"]), strip_h,
                                              tempo_rolagem, H)

    # 1/3 rolagem. origem: Instragram-Videos/pipeline/compose.py:160-166
    r = _sh(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(tira.resolve()),
             "-vf", f"crop=w={W}:h={H}:x=0:y='if(lt(t,{hold}),0,min((t-{hold})*{vel},{percurso}))',format=yuv420p",
             "-t", str(dur), "-c:v", "libx264", "-preset", PRESET, "-crf", CRF_ROLAGEM, "-r", str(FPS),
             str(pasta / "scroll.mp4")])
    if r.returncode:
        raise ErroMontagem(f"erro na rolagem:\n{r.stderr[-CAUDA_ERRO:]}")

    # PNGs e grafo. origem: Instragram-Videos/pipeline/compose.py:168-258
    extras: list[str] = []
    grafo_v: list[str] = []
    base = "0:v"
    n_entradas = [2]  # 0 = scroll.mp4, 1 = caps.txt, 2 = narracao.mp3

    def entrada(*args: str) -> int:
        extras.extend(args)
        n_entradas[0] += 1
        return n_entradas[0]

    if com_abertura:
        i = entrada("-i", "abertura.mp4")
        grafo_v.append(f"[{i}:v]setpts=PTS-STARTPTS,format=yuv420p[ab]")
        grafo_v.append(f"[{base}][ab]overlay=0:0:eof_action=pass:enable='lt(t,{abert_s})'[va]")
        base = "va"
    if com_impacto:
        tam = cartao_tam
        f = ImageFont.truetype(str(estilo.fonte), tam)
        alt_linha = round(tam * CARTAO_ENTRELINHA)
        cx_w = round(max(f.getlength(l) for l in linhas)) + CARTAO_PAD_X
        cx_h = alt_linha * len(linhas) + CARTAO_PAD_Y
        cartao = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(cartao)
        x0, y0 = (W - cx_w) // 2, cartao_y - cx_h // 2
        d.rounded_rectangle([x0, y0, x0 + cx_w, y0 + cx_h], radius=CARTAO_RAIO, fill=estilo.cartao_fundo)
        for n, l in enumerate(linhas):
            d.text((W / 2, y0 + CARTAO_TOPO_TEXTO + n * alt_linha + alt_linha / 2), l, font=f,
                   fill=estilo.cartao_texto, anchor="mm")
        cartao.save(pasta / "impacto_cartao.png")
        Image.alpha_composite(Image.new("RGBA", (W, H), estilo.veu), cartao).save(pasta / "impacto.png")
        i = entrada("-loop", "1", "-t", str(IMPACTO_S), "-i", "impacto_cartao.png" if com_abertura else "impacto.png")
        if not com_abertura:
            grafo_v.append(f"[{base}]gblur=sigma={DESFOQUE_SIGMA}:enable='lt(t,{IMPACTO_S - DESFOQUE_ANTES_S})'[bl]")
            base = "bl"
        grafo_v.append(f"[{i}:v]format=rgba,fade=t=out:st={IMPACTO_S - FADE_CARTAO_S}:d={FADE_CARTAO_S}:alpha=1[imp]")
        grafo_v.append(f"[{base}][imp]overlay=0:0:eof_action=pass[vi]")
        base = "vi"
    selo_info = None
    if com_selo:
        texto = selo.format(cta=cta)
        pos = texto.find(cta)
        a, b, c = (texto, "", "") if pos < 0 else (texto[:pos], cta, texto[pos + len(cta):])
        f = ImageFont.truetype(str(estilo.fonte), SELO_TAM)
        la, lb, lc = f.getlength(a), f.getlength(b), f.getlength(c)
        sw, sh_ = round(la + lb + lc) + SELO_PAD_X, SELO_ALTURA
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x0, y0 = (W - sw) // 2, geometria.selo_base_y - sh_
        d.rounded_rectangle([x0, y0, x0 + sw, y0 + sh_], radius=SELO_RAIO, fill=estilo.selo_fundo,
                            outline=estilo.selo_contorno, width=SELO_CONTORNO)
        for trecho, x, cor in ((a, x0 + SELO_TEXTO_X, estilo.selo_texto),
                               (b, x0 + SELO_TEXTO_X + la, estilo.selo_cta),
                               (c, x0 + SELO_TEXTO_X + la + lb, estilo.selo_texto)):
            if trecho:
                d.text((x, y0 + sh_ / 2), trecho, font=f, fill=cor, anchor="lm")
        img.save(pasta / "selo.png")
        selo_fim = round(ini_card - SELO_ANTES_DO_CARD_S, 3)
        i = entrada("-loop", "1", "-t", str(selo_fim), "-i", "selo.png")
        grafo_v.append(f"[{i}:v]format=rgba[selo]")
        grafo_v.append(f"[{base}][selo]overlay=0:0:eof_action=pass:enable='between(t,{SELO_INICIO_S},{selo_fim})'[vs]")
        base = "vs"
        selo_info = {"texto": texto, "inicio": SELO_INICIO_S, "fim": selo_fim}

    # 2/3 composição. origem: Instragram-Videos/pipeline/compose.py:266-281
    bruto = pasta / "bruto.mp4"
    r = _sh(["ffmpeg", "-y", "-v", "error", "-i", "scroll.mp4",
             "-f", "concat", "-safe", "0", "-i", "caps.txt",
             "-i", "narracao.mp3", *extras,
             "-filter_complex",
             "".join(g + ";" for g in grafo_v)
             + f"[1:v]format=rgba,fps={FPS},scale={W}:{H}[c];[{base}][c]overlay=0:0:shortest=0"
             + (f":enable='gte(t,{IMPACTO_S})'" if legenda_espera else "") + "[v];"
             + f"[2:a]aresample={AUDIO_TAXA},asetpts=PTS-STARTPTS,adelay=delays={atraso_ms}:all=1,apad[a]",
             "-map", "[v]", "-map", "[a]", "-t", str(dur),
             "-c:v", "libx264", "-preset", PRESET, "-crf", CRF_COMPOSICAO, "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-movflags", "+faststart", bruto.name], cwd=pasta)
    if r.returncode:
        raise ErroMontagem(f"erro na composição:\n{r.stderr[-CAUDA_ERRO:]}")

    # 3/3 loudnorm em duas passadas sobre a mistura (vídeo copiado)
    saida.parent.mkdir(parents=True, exist_ok=True)
    try:
        loud = ffmpeg.normalizar_audio(bruto, saida)
    except ffmpeg.ErroFfmpeg as erro:
        raise ErroMontagem(str(erro)) from None
    finally:
        bruto.unlink(missing_ok=True)
    if not loud["dentro_do_alvo"]:
        avisos.append(f"loudness fora do alvo depois do limitador: {loud['lufs']} LUFS, pico {loud['pico']} dBFS")

    # Marcadores só com o MP4 final na mão. origem: Instragram-Videos/pipeline/compose.py:259-264,301-309
    visual = {"metodo": "visual-v2", "impacto": linhas if com_impacto else None,
              "selo_cta": cta if com_selo else None, "abertura_gerada": abert_s if com_abertura else None}
    arquivos.gravar_json(pasta / "visual.json", visual)
    marca_abertura = pasta / "abertura.json"
    if marca_abertura.exists():
        dados = arquivos.ler_json(marca_abertura)
        agora = tempo.agora_iso(raiz) if raiz is not None else datetime.now().astimezone().isoformat(timespec="seconds")
        dados["montado_em"] = agora if com_abertura else None
        arquivos.gravar_json(marca_abertura, dados)

    return {
        "video": saida,
        "duracao": dur,
        "rolagem": {"hold": hold, "percurso": percurso, "velocidade": vel, "escolha": escolha},
        "cartao": ({"linhas": linhas, "tamanho": cartao_tam, "centro_y": cartao_y, "por_que": cartao_por_que}
                   if com_impacto else None),
        "selo": selo_info,
        "abertura": abert_s if com_abertura else None,
        "legenda_espera": legenda_espera,
        "visual": visual,
        "loudness": loud,
        "avisos": avisos,
    }
