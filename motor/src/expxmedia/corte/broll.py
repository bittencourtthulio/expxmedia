"""B-roll do corte pelo banco de imagens (capacidade `banco_imagens`, provedor `pexels`, D-28).

Porta de `Instragram-Videos/pipeline/broll.py`, sobre o módulo `imagem.pexels` (chave `PEXELS_API_KEY` do
`.env` da instalação; 429 sem nova tentativa). Quem escolhe o TERMO é quem leu o trecho: o termo é em
inglês e descreve a IMAGEM, não o conceito. Aqui se resolve o resto, validando antes de usar:

- **duração**: o clipe tem de durar ao menos a inserção + 1 s (sobra para tirar o miolo), senão é
  descartado (origem: broll.py:163);
- **relevância**: a página do Pexels descreve o vídeo no endereço (`/video/<descricao>-<id>/`); se ela
  descreve e nenhuma palavra do termo aparece, o resultado é outra coisa e é descartado. Página sem
  descrição não é julgada. É o mínimo mecânico: o julgamento de contexto continua com quem montou;
- busca em retrato e, sem nada válido, em paisagem (origem: broll.py:163-165); entre os válidos, o que
  tem arquivo vertical ganha, e depois a ordem do Pexels (a origem pegava o primeiro);
- **sem resultado válido devolve None, sem erro** (a origem abortava o plano inteiro; aqui quem chama
  decide seguir sem aquela inserção).

O arquivo baixado vai para `broll/NN_src.mp4` da pasta da peça e é normalizado em `broll/NN.mp4`: o
**miolo** do clipe (o primeiro segundo costuma ser a câmera entrando em regime), 1080x1920, 30 fps,
yuv420p, sem áudio, x264 medium crf 20 (origem: broll.py:175-185). A procedência (id, página, autor,
licença, termo) volta no registro, para `brolls.json`.

As regras de colocação (`validar_plano`) são do formato reel de corte, com os valores da origem como
padrão (`RegrasBroll`): cada inserção 2-4 s, 3 s livres no começo e 2 s no fim (o rosto abre e fecha),
4 s de respiro entre inserções e no máximo 40% do corte.

Uso:

    from expxmedia.corte import broll
    ins = broll.buscar_broll(raiz, "baker kneading dough", pasta_da_peca, duracao=3.0, indice=0)
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from expxmedia.imagem import pexels
from expxmedia.nucleo import raiz as instalacao
from expxmedia.video import ffmpeg

__all__ = ["ErroBroll", "RegrasBroll", "REGRAS_CORTE", "triar", "relevante", "buscar_broll", "validar_plano",
           "normalizar_clipe", "pexels"]

FOLGA_DURACAO_S = 1.0  # clipe ≥ inserção + 1 s; origem: Instragram-Videos/pipeline/broll.py:163
ORIENTACOES = ("portrait", "landscape")  # origem: Instragram-Videos/pipeline/broll.py:163-165
POR_PAGINA = 12  # origem: Instragram-Videos/pipeline/broll.py:46
LARGURA, ALTURA, FPS = 1080, 1920, 30  # origem: Instragram-Videos/pipeline/lib.py:9
CRF = "20"  # origem: Instragram-Videos/pipeline/broll.py:182
PRESET = "medium"  # origem: Instragram-Videos/pipeline/broll.py:182
CAUDA_ERRO = 600  # origem: Instragram-Videos/pipeline/broll.py:185
_PALAVRA_MIN = 3


@dataclass(frozen=True)
class RegrasBroll:
    dur_min: float
    dur_max: float
    inicio_livre: float
    fim_livre: float
    intervalo_min: float
    fracao_max: float


REGRAS_CORTE = RegrasBroll(
    dur_min=2.0,  # origem: Instragram-Videos/pipeline/lib.py:144
    dur_max=4.0,  # origem: Instragram-Videos/pipeline/lib.py:144
    inicio_livre=3.0,  # origem: Instragram-Videos/pipeline/lib.py:145
    fim_livre=2.0,  # origem: Instragram-Videos/pipeline/lib.py:146
    intervalo_min=4.0,  # origem: Instragram-Videos/pipeline/lib.py:147
    fracao_max=0.40,  # origem: Instragram-Videos/pipeline/lib.py:148
)


class ErroBroll(RuntimeError):
    """Falha ao normalizar o clipe baixado."""


def _palavras(texto: str) -> set[str]:
    saida = set()
    for w in re.findall(r"[a-zà-ÿ]+", texto.lower()):
        if len(w) >= _PALAVRA_MIN:
            saida.add(w[:-1] if w.endswith("s") and len(w) > _PALAVRA_MIN else w)
    return saida


def relevante(item: dict[str, Any], termo: str) -> bool | None:
    """True/False quando a página descreve o vídeo; None quando não há descrição para julgar."""
    caminho = urlsplit(item.get("pagina") or "").path.strip("/").split("/")
    slug = caminho[-1] if caminho and caminho[-1] else ""
    descricao = _palavras(re.sub(r"-?\d+$", "", slug).replace("-", " "))
    if not descricao:
        return None
    return bool(descricao & _palavras(termo))


def triar(itens: list[dict[str, Any]], termo: str, duracao: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(válidos na ordem de preferência, descartados com motivo) para uma inserção de `duracao` s."""
    validos, descartados = [], []
    minimo = duracao + FOLGA_DURACAO_S
    for it in itens:
        if not it.get("url"):
            descartados.append({"pexels_id": it.get("id"), "motivo": "sem arquivo para baixar"})
        elif (it.get("duracao") or 0) < minimo:
            descartados.append({"pexels_id": it.get("id"),
                                "motivo": f"duração {it.get('duracao') or 0}s abaixo do mínimo de {minimo:g}s"})
        elif relevante(it, termo) is False:
            descartados.append({"pexels_id": it.get("id"),
                                "motivo": f"relevância: a página descreve outra coisa que '{termo}'"})
        else:
            validos.append(it)
    # arquivo vertical primeiro; a ordem do Pexels desempata (sort é estável)
    validos.sort(key=lambda it: 0 if (it.get("altura") or 0) >= (it.get("largura") or 0) else 1)
    return validos, descartados


def normalizar_clipe(bruto: Path, destino: Path, duracao: float) -> None:
    """O miolo de `duracao` s do clipe, em 1080x1920, 30 fps, yuv420p, sem áudio.
    origem: Instragram-Videos/pipeline/broll.py:175-185"""
    info = ffmpeg.sondar(bruto)
    sobra = max(0.0, ((info["duracao"] or 0.0) - duracao) / 2)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{sobra:.2f}", "-i", str(bruto), "-t", f"{duracao:.2f}",
         "-vf", f"scale={LARGURA}:{ALTURA}:force_original_aspect_ratio=increase,crop={LARGURA}:{ALTURA},"
                f"fps={FPS},format=yuv420p",
         "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, str(destino)],
        capture_output=True, text=True)
    if r.returncode:
        raise ErroBroll(f"erro ao normalizar o clipe:\n{r.stderr[-CAUDA_ERRO:]}")


def buscar_broll(raiz: Path | str, termo: str, pasta: Path | str, *, duracao: float, indice: int = 0,
                 url_base: str = pexels.URL_BASE, normalizar: bool = True) -> dict[str, Any] | None:
    """Busca, valida, baixa e normaliza um b-roll para a pasta da peça. None quando nada serve.

    Devolve ``{arquivo, bruto, dur, termo, pexels_id, pagina, autor, autor_url, licenca, largura, altura,
    descartados}``, com os caminhos relativos à `pasta`.
    """
    raiz = Path(raiz)
    pasta = Path(pasta)
    if not (termo or "").strip():
        raise ValueError("termo de busca vazio")
    descartados: list[dict[str, Any]] = []
    escolhido = None
    for orientacao in ORIENTACOES:
        itens = pexels.buscar(raiz, termo, midia="video", orientacao=orientacao, por_pagina=POR_PAGINA,
                              url_base=url_base, altura_alvo=ALTURA)
        validos, fora = triar(itens, termo, duracao)
        descartados += fora
        if validos:
            escolhido = validos[0]
            break
    if escolhido is None:
        return None
    nome = f"{indice:02d}"
    bruto_rel = f"broll/{nome}_src.mp4"
    final_rel = f"broll/{nome}.mp4"
    pexels.baixar(raiz, escolhido, instalacao.relativo(raiz, pasta / bruto_rel))
    if normalizar:
        normalizar_clipe(pasta / bruto_rel, pasta / final_rel, duracao)
    return {
        "arquivo": final_rel if normalizar else bruto_rel,
        "bruto": bruto_rel,
        "dur": round(float(duracao), 2),
        "termo": termo,
        "pexels_id": escolhido["id"],
        "pagina": escolhido["pagina"],
        "autor": escolhido["autor"],
        "autor_url": escolhido["autor_url"],
        "licenca": escolhido["licenca"],
        "largura": escolhido["largura"],
        "altura": escolhido["altura"],
        "descartados": descartados,
    }


def validar_plano(plano: list[dict[str, Any]], duracao_corte: float, regras: RegrasBroll = REGRAS_CORTE) -> list[str]:
    """Problemas do plano `[{t, dur, termo, por_que}]` pelas regras de colocação; lista vazia = aprovado.
    origem: Instragram-Videos/pipeline/broll.py:136-155"""
    plano = sorted(plano, key=lambda p: float(p["t"]))
    problemas, total = [], 0.0
    for i, p in enumerate(plano):
        t, d = float(p["t"]), float(p["dur"])
        if not (regras.dur_min <= d <= regras.dur_max):
            problemas.append(f"#{i + 1} dura {d:g}s (faixa {regras.dur_min:g}-{regras.dur_max:g}s)")
        if t < regras.inicio_livre:
            problemas.append(f"#{i + 1} começa em {t:g}s — os {regras.inicio_livre:g}s iniciais são do rosto")
        if t + d > duracao_corte - regras.fim_livre:
            problemas.append(f"#{i + 1} termina em {t + d:.1f}s — o fecho ({duracao_corte - regras.fim_livre:.1f}s "
                             "em diante) é do rosto")
        if i and t - (float(plano[i - 1]["t"]) + float(plano[i - 1]["dur"])) < regras.intervalo_min:
            problemas.append(f"#{i + 1} cola no anterior (mínimo {regras.intervalo_min:g}s de respiro)")
        if not (p.get("termo") or "").strip():
            problemas.append(f"#{i + 1} sem termo de busca")
        total += d
    if duracao_corte > 0 and total > duracao_corte * regras.fracao_max:
        problemas.append(f"{total:.1f}s de b-roll em {duracao_corte:.1f}s de corte ({total / duracao_corte:.0%}) — "
                         f"teto {regras.fracao_max:.0%}")
    return problemas
