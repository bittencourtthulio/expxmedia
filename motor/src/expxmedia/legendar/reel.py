"""Legenda do reel em PNG por bloco, com card final do CTA (capacidade `legendar`, D-23).

Porta de `Instragram-Videos/pipeline/captions.py`, com as constantes de `Instragram-Videos/pipeline/lib.py`.
A legenda é um PNG RGBA transparente por bloco + `caps.txt` (concat demuxer do ffmpeg), queimada por
overlay — nunca pelo filtro `subtitles` (build sem libass).

Entrada: o alinhamento por caractere NO ESPAÇO DO ROTEIRO (da narração ou da transcrição, mesmo formato)
e o roteiro. O que é marca vem de fora do código (M13): fonte e cores da Alma (`estilo_da_alma`), a
palavra do CTA e a copy do card final da peça, os termos de várias palavras do léxico do porta-voz.

Inteligência preservada (os números são os da origem):

- a cadência é medida no próprio alinhamento pela MEDIANA do intervalo início→início (a média seria
  mascarada pelas pausas) e dela sai quantas palavras cabem por bloco (3 a 6, mirando 1,1 s na tela);
- o bloco fecha ao encher, no fim de frase (`. : ? !`) ou depois de 1,6 s;
- termo de várias palavras do léxico não é rachado nem entre blocos nem entre linhas;
- escada de fonte 78 → 54 px, uma ou duas linhas de até 940 px; caixa arredondada cuja base para em
  1499, uma linha antes da área segura inferior;
- card final com a escada 88 → 48 px (CTA longo não estoura a largura), 0,15 s depois da última
  palavra, por 2,2 s;
- a palavra do CTA é DECLARADA: inferir "o primeiro token em caixa alta" pinta sigla (PDF, API) com a
  cor do CTA — já aconteceu; e o CTA tem de estar no roteiro, senão a narração não pede o que a legenda
  mostra.

Saída na pasta `destino`: `caps/NNN.png`, `caps/blank.png`, `caps/end.png` (com CTA), `caps.txt` e
`legendas.json` (`{blocos, cta, duracao, offset_audio, ritmo_cadencia, palavras_por_bloco}`). A função
devolve também o achado de legibilidade (mais de 35% dos cartões abaixo de 0,7 s), o mesmo gate da
verificação de entrega.
"""
from __future__ import annotations

import math
import shutil
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont

from expxmedia.alma import fontes as _fontes
from expxmedia.nucleo import arquivos
from expxmedia.video.verificar import CAP_BLOCO_MIN_S, CAP_CURTOS_MAX_FRAC, duracoes_cartoes

__all__ = [
    "ErroLegenda",
    "ErroCtaAusente",
    "ErroCtaNaoDeclarado",
    "EstiloLegenda",
    "estilo_da_alma",
    "termos_multi",
    "palavras_por_bloco",
    "legendar_reel",
    "LARGURA",
    "ALTURA",
    "AREA_SEGURA_INFERIOR",
    "CAIXA_BASE",
    "ESCADA_LEGENDA",
    "ESCADA_CARD",
    "SEGURA_CTA",
    "OFFSET_PADRAO",
]

LARGURA, ALTURA = 1080, 1920  # origem: Instragram-Videos/pipeline/lib.py:9
AREA_SEGURA_INFERIOR = 420  # faixa inferior reservada à interface; origem: Instragram-Videos/pipeline/lib.py:10
MARGEM_LATERAL = 140  # LARG_MAX = W - 140; origem: Instragram-Videos/pipeline/captions.py:32
# A primeira linha da área segura é H - SAFE_BOTTOM; a caixa para UMA linha antes.
CAIXA_BASE = ALTURA - AREA_SEGURA_INFERIOR - 1  # origem: Instragram-Videos/pipeline/captions.py:34
ALFA_CAIXA = 205  # caixa a ~80%; origem: Instragram-Videos/pipeline/captions.py:35
RAIO_CAIXA = 26  # origem: Instragram-Videos/pipeline/captions.py:131
PAD_CAIXA_X = 72  # origem: Instragram-Videos/pipeline/captions.py:127
PAD_CAIXA_Y = 40  # origem: Instragram-Videos/pipeline/captions.py:127
TOPO_TEXTO = 20  # origem: Instragram-Videos/pipeline/captions.py:132
ENTRELINHA_LEGENDA = 18  # altura de linha = tamanho + 18; origem: Instragram-Videos/pipeline/captions.py:125
ENTRELINHA_CARD = 20  # origem: Instragram-Videos/pipeline/captions.py:168
ESCADA_LEGENDA = (78, 72, 66, 60, 54)  # origem: Instragram-Videos/pipeline/captions.py:109
ESCADA_CARD = (88, 80, 72, 66, 60, 54, 48)  # origem: Instragram-Videos/pipeline/captions.py:162
SEGURA_CTA = 2.2  # card final na tela; origem: Instragram-Videos/pipeline/captions.py:36
CARD_ATRASO_S = 0.15  # card começa depois da última palavra; origem: Instragram-Videos/pipeline/captions.py:181
OFFSET_PADRAO = 0.6  # beat antes da narração; 0 em fala gravada; origem: Instragram-Videos/pipeline/captions.py:25
JANELA_BLOCO_S = 1.6  # bloco fecha depois disto; origem: Instragram-Videos/pipeline/captions.py:100
BLANK_MIN_S = 0.02  # intervalo maior que isto vira blank; origem: Instragram-Videos/pipeline/captions.py:187
SOBRA_FINAL_S = 0.4  # sobra de blank no fim do caps.txt; origem: Instragram-Videos/pipeline/captions.py:183
CAP_BLOCO_ALVO_S = 1.1  # tempo em tela que o bloco mira; origem: Instragram-Videos/pipeline/lib.py:59
CAP_PALAVRAS_BLOCO = 3  # piso; origem: Instragram-Videos/pipeline/lib.py:71
CAP_PALAVRAS_BLOCO_MAX = 6  # teto (2 linhas a 54 px); origem: Instragram-Videos/pipeline/lib.py:67
QUEBRA = tuple(".:?!")  # origem: Instragram-Videos/pipeline/captions.py:94
_PONT = ".,:;!?…()[]\"'«»"  # origem: Instragram-Videos/pipeline/captions.py:74
_PONT_CTA = ".,:;!?"  # origem: Instragram-Videos/pipeline/captions.py:136


class ErroLegenda(ValueError):
    """Entrada que não dá para legendar."""


class ErroCtaAusente(ErroLegenda):
    """A palavra do CTA não aparece no roteiro."""


class ErroCtaNaoDeclarado(ErroLegenda):
    """Legenda com CTA sem a palavra declarada."""


@dataclass(frozen=True)
class EstiloLegenda:
    fonte: Path
    cor_texto: tuple[int, int, int, int]
    cor_cta: tuple[int, int, int, int]
    cor_caixa: tuple[int, int, int, int]


def _rgba(hexa: str, alfa: int = 255) -> tuple[int, int, int, int]:
    h = hexa.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ErroLegenda(f"cor inválida na Alma: {hexa!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alfa


def estilo_da_alma(alma: Any, *, raiz: Path | str | None = None, papel_fonte: str = "titulo",
                   cache: Path | str | None = None) -> tuple[EstiloLegenda, list[str]]:
    """(estilo, avisos) a partir da Alma.

    Cores pelos papéis do contrato: letra em `texto_inverso`, caixa em `texto` a ~80% de opacidade
    (texto escuro por baixo de letra clara, o par que o contrato garante legível em qualquer marca),
    palavra do CTA em `destaque`. Fonte do `papel_fonte`; sem fonte resolvida, a Inter embarcada, com
    aviso (nunca em silêncio).
    """
    dados = alma.dados if hasattr(alma, "dados") else alma
    cores = ((dados.get("visual") or {}).get("cores")) or {}
    faltam = [p for p in ("texto", "texto_inverso", "destaque") if not isinstance(cores.get(p), str)]
    if faltam:
        raise ErroLegenda(f"a Alma não tem as cores {', '.join(faltam)} (visual.cores)")
    resolvida = _fontes.resolver_fonte(dados, papel_fonte, raiz=raiz, cache=cache)
    avisos = [resolvida.aviso] if resolvida.aviso else []
    # na reserva embarcada, o peso mais forte (a legenda é texto de impacto)
    arquivo = resolvida.arquivos[-1] if resolvida.origem == "embarcada" else resolvida.arquivos[0]
    return EstiloLegenda(
        fonte=Path(arquivo),
        cor_texto=_rgba(cores["texto_inverso"]),
        cor_cta=_rgba(cores["destaque"]),
        cor_caixa=_rgba(cores["texto"], ALFA_CAIXA),
    ), avisos


def termos_multi(pronuncia: Iterable[dict[str, Any]] | None) -> tuple[tuple[str, ...], ...]:
    """Termos de várias palavras do léxico do porta-voz (`voz.pronuncia`), em minúsculas, do mais longo."""
    termos = [str(t.get("termo") or "") for t in (pronuncia or [])]
    termos = sorted((t for t in termos if " " in t.strip()), key=len, reverse=True)
    return tuple(tuple(t.lower().split()) for t in termos)


def palavras_por_bloco(ritmo: float) -> int:
    """ceil(ritmo × 1,1 s) preso entre 3 e 6. origem: Instragram-Videos/pipeline/lib.py:246-256"""
    n = math.ceil(ritmo * CAP_BLOCO_ALVO_S)
    return max(CAP_PALAVRAS_BLOCO, min(CAP_PALAVRAS_BLOCO_MAX, n))


def _palavras(al: dict[str, list]) -> list[tuple[str, float, float]]:
    try:
        chars = al["characters"]
        cs, ce = al["character_start_times_seconds"], al["character_end_times_seconds"]
    except (KeyError, TypeError):
        raise ErroLegenda("alinhamento sem characters e tempos por caractere") from None
    palavras, atual, ini, fim = [], "", None, 0.0
    for c, s, e in zip(chars, cs, ce):
        if c.isspace():
            if atual:
                palavras.append((atual, ini, fim))
                atual, ini = "", None
        else:
            if not atual:
                ini = s
            atual += c
            fim = e
    if atual:
        palavras.append((atual, ini, fim))
    return palavras


def _resolver_cta(cta: str | None, sem_cta: bool, roteiro: str) -> str | None:
    if sem_cta:
        return None
    if not cta or not str(cta).strip():
        # origem: Instragram-Videos/pipeline/captions.py:41-42 — inferir pega sigla e pinta a palavra errada
        raise ErroCtaNaoDeclarado(
            "CTA não declarado: informe a palavra do CTA da peça (ou legende sem CTA de propósito); "
            "inferir o CTA pelo primeiro token em caixa alta é proibido — pega siglas do texto")
    cta = str(cta).strip().upper()
    if cta not in roteiro:
        # origem: Instragram-Videos/pipeline/captions.py:55-57
        raise ErroCtaAusente(f"a palavra do CTA ('{cta}') não aparece no roteiro — a narração não vai "
                             f"pedir o que a legenda mostra")
    return cta


def legendar_reel(
    alinhamento: dict[str, list],
    roteiro: str,
    destino: str | Path,
    *,
    estilo: EstiloLegenda,
    cta: str | None,
    sem_cta: bool = False,
    termos_multi: tuple[tuple[str, ...], ...] = (),
    card_final: tuple[str, ...] | list[str] = ("{cta}",),
    offset: float = OFFSET_PADRAO,
) -> dict[str, Any]:
    """Gera os PNGs, o `caps.txt` e o `legendas.json` em `destino`.

    `cta`: a palavra declarada (vira maiúscula); `sem_cta=True` legenda sem palavra destacada e sem card
    final (fala gravada, corte). `card_final`: as linhas do card, com `{cta}` onde entra a palavra (copy
    da peça ou da Alma, nunca do código). `offset`: atraso do áudio em relação ao vídeo (0 em fala gravada).

    Devolve o conteúdo do `legendas.json` mais `entradas` [(png, início, fim)], `textos` (texto de cada
    bloco), `tamanho_card`, `achados` (legibilidade) e `avisos`.
    """
    destino = Path(destino)
    cta = _resolver_cta(cta, sem_cta, roteiro)
    palavras = _palavras(alinhamento)
    if len(palavras) < 2:
        raise ErroLegenda("o alinhamento precisa de ao menos duas palavras para medir a cadência")

    # termo de várias palavras não racha: ligado[i] proíbe o corte entre a palavra i e a seguinte
    chaves = [p.strip(_PONT).lower() for p, *_ in palavras]
    ligado = [False] * len(palavras)
    for i in range(len(palavras)):
        for termo in termos_multi:
            if tuple(chaves[i:i + len(termo)]) == termo:
                for k in range(i, i + len(termo) - 1):
                    ligado[k] = True
    tokens = [(p, s, e, lig) for (p, s, e), lig in zip(palavras, ligado)]

    # cadência: inverso da MEDIANA do intervalo início→início. origem: Instragram-Videos/pipeline/captions.py:84-92
    inicios = [s for _, s, _, _ in tokens]
    gaps = sorted(b - a for a, b in zip(inicios, inicios[1:]))
    mediana = gaps[len(gaps) // 2]
    if mediana <= 0:
        raise ErroLegenda("alinhamento sem intervalo entre palavras: não dá para medir a cadência")
    ritmo = 1.0 / mediana
    por_bloco = palavras_por_bloco(ritmo)

    blocos, buf = [], []
    for p, s, e, lig in tokens:
        buf.append((p, s, e, lig))
        if lig:
            continue
        if len(buf) >= por_bloco or p.endswith(QUEBRA) or (e - buf[0][1]) > JANELA_BLOCO_S:
            blocos.append(buf)
            buf = []
    if buf:
        blocos.append(buf)

    medidor = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    larg_max = LARGURA - MARGEM_LATERAL

    def fonte(tam: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(estilo.fonte), tam)

    def encaixar(bloco):
        # origem: Instragram-Videos/pipeline/captions.py:108-120
        for tam in ESCADA_LEGENDA:
            f = fonte(tam)
            if medidor.textlength(" ".join(t[0] for t in bloco), font=f) <= larg_max:
                return f, [bloco]
            for corte in range(1, len(bloco)):
                if bloco[corte - 1][3]:
                    continue  # nem a quebra de linha racha um termo do léxico
                a, b = bloco[:corte], bloco[corte:]
                if (medidor.textlength(" ".join(t[0] for t in a), font=f) <= larg_max
                        and medidor.textlength(" ".join(t[0] for t in b), font=f) <= larg_max):
                    return f, [a, b]
        return fonte(ESCADA_LEGENDA[-1]), [bloco]

    def desenhar(linhas, f, entrelinha, destaca):
        # origem: Instragram-Videos/pipeline/captions.py:123-140 e 167-180
        alt_linha = f.size + entrelinha
        larguras = [medidor.textlength(" ".join(t[0] for t in ln), font=f) for ln in linhas]
        cx_w, cx_h = max(larguras) + PAD_CAIXA_X, alt_linha * len(linhas) + PAD_CAIXA_Y
        img = Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x0, y0 = (LARGURA - cx_w) / 2, CAIXA_BASE - cx_h
        d.rounded_rectangle([x0, y0, x0 + cx_w, y0 + cx_h], radius=RAIO_CAIXA, fill=estilo.cor_caixa)
        y = y0 + TOPO_TEXTO
        for ln, lw in zip(linhas, larguras):
            x = (LARGURA - lw) / 2
            for t in ln:
                tok = t[0]
                d.text((x, y), tok, font=f, fill=estilo.cor_cta if destaca(tok) else estilo.cor_texto)
                x += medidor.textlength(tok + " ", font=f)
            y += alt_linha
        return img

    caps = destino / "caps"
    shutil.rmtree(caps, ignore_errors=True)
    caps.mkdir(parents=True)
    Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0)).save(caps / "blank.png")

    entradas: list[tuple[str, float, float]] = []
    for i, bloco in enumerate(blocos):
        f, linhas = encaixar(bloco)
        img = desenhar(linhas, f, ENTRELINHA_LEGENDA, lambda tok: bool(cta) and tok.strip(_PONT_CTA) == cta)
        img.save(caps / f"{i:03d}.png")
        entradas.append((f"caps/{i:03d}.png", bloco[0][1] + offset, bloco[-1][2] + offset))

    tamanho_card = None
    if cta:
        linhas_card = [[(tok,) for tok in linha.format(cta=cta).split()] for linha in card_final]
        linhas_card = [ln for ln in linhas_card if ln]
        if not linhas_card:
            raise ErroLegenda("card final sem texto")
        fim_narr = entradas[-1][2]
        # escada até todas as linhas caberem. origem: Instragram-Videos/pipeline/captions.py:158-166
        for tam in ESCADA_CARD:
            fcta = fonte(tam)
            if max(medidor.textlength(" ".join(t[0] for t in ln), font=fcta) for ln in linhas_card) <= larg_max:
                break
        tamanho_card = fcta.size
        desenhar(linhas_card, fcta, ENTRELINHA_CARD, lambda tok: tok == cta).save(caps / "end.png")
        entradas.append(("caps/end.png", fim_narr + CARD_ATRASO_S, fim_narr + CARD_ATRASO_S + SEGURA_CTA))

    # concat demuxer. origem: Instragram-Videos/pipeline/captions.py:183-191
    duracao = round(entradas[-1][2] + SOBRA_FINAL_S, 2)
    linhas_txt, t = [], 0.0
    for png, s, e in entradas:
        if s - t > BLANK_MIN_S:
            linhas_txt.append(f"file 'caps/blank.png'\nduration {round(s - t, 3)}\n")
        linhas_txt.append(f"file '{png}'\nduration {round(e - s, 3)}\n")
        t = e
    linhas_txt.append(f"file 'caps/blank.png'\nduration {round(duracao - t, 3)}\nfile 'caps/blank.png'\n")
    caps_txt = destino / "caps.txt"
    caps_txt.write_text("".join(linhas_txt), encoding="utf-8")

    legendas = {"blocos": len(blocos), "cta": cta, "duracao": duracao, "offset_audio": offset,
                "ritmo_cadencia": round(ritmo, 3), "palavras_por_bloco": por_bloco}
    arquivos.gravar_json(destino / "legendas.json", legendas)

    # gate de legibilidade sobre o caps.txt que vai ao vídeo. origem: Instragram-Videos/pipeline/lib.py:259-277
    achados = []
    durs = duracoes_cartoes(caps_txt)
    curtos = [d for d in durs if d < CAP_BLOCO_MIN_S]
    frac = len(curtos) / len(durs) if durs else 1.0
    if frac > CAP_CURTOS_MAX_FRAC:
        achados.append({
            "checagem": "legibilidade",
            "detalhe": (f"legibilidade da legenda: {len(curtos)} de {len(durs)} cartões ({frac:.0%}) abaixo de "
                        f"{CAP_BLOCO_MIN_S:g} s na tela (mediana {statistics.median(durs):.2f} s, "
                        f"mínimo {min(durs):.2f} s)") if durs else "nenhum cartão de legenda",
            "esperado": f"≤ {CAP_CURTOS_MAX_FRAC:.0%} dos cartões abaixo de {CAP_BLOCO_MIN_S:g} s",
            "obtido": round(frac, 4),
        })

    return {**legendas, "entradas": entradas, "textos": [" ".join(t[0] for t in b) for b in blocos],
            "tamanho_card": tamanho_card, "achados": achados, "avisos": []}
