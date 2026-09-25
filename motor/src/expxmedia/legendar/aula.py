"""Legenda de aula: o texto EXATO do roteiro nos tempos por palavra do whisper (D-23).

Porta do `gerar_legendas.py` das aulas, versão mais evoluída (idêntica nos episódios 01 a 09;
origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py). A transcrição direta erra nome próprio e escreve número em algarismo diferente da fala; por
isso a legenda usa só o TEMPO do whisper e o texto do roteiro.

Algoritmo:

1. palavras do roteiro (sem marcadores `[[cue]]`) contra as do whisper, ambas normalizadas (minúscula,
   NFKD, só `[a-z0-9]`), por `difflib.SequenceMatcher(autojunk=False)`: `equal` copia o tempo palavra a
   palavra; `replace` distribui o trecho do whisper proporcionalmente; palavra sem par é interpolada
   entre as vizinhas (sem vizinha à direita, anterior + 0,3 s);
2. frases terminam em `. : ? !`; frase terminada em `:` ou com até 3 palavras junta com a seguinte;
3. 42 caracteres por linha, 2 linhas; acima de 42 escolhe o corte em duas linhas que minimiza a linha
   mais longa (sem palavra órfã), senão quebra guloso;
4. frase que não cabe em 2 linhas vira k blocos equilibrados, com custo
   `|comprimento − alvo| + 20 × órfãs − 6 se o corte cai depois de vírgula` (órfã = linha < 18);
5. fim = `min(max(fim + 0,25, início + 1,0), próximo início − 0,05)`; a última usa `fim + 1,5`.

Entrada do whisper: o JSON do openai-whisper (`segments[].words[] {word, start, end}`) ou a saída de
`expxmedia.transcrever.whisper.transcrever` (`palavras[] {w, t0, t1}`).
Saída: `[{start, end, lines}]` (o `legendas.json` da composição) e o SRT (`legendar.srt`).
"""
from __future__ import annotations

import difflib
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

from expxmedia.legendar import srt
from expxmedia.nucleo import arquivos

__all__ = [
    "MAX_CARACTERES",
    "MAX_LINHAS",
    "palavras_do_whisper",
    "alinhar_palavras",
    "quebrar_linhas",
    "legendas_aula",
    "gerar",
]

MAX_CARACTERES = 42  # por linha; origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:14
MAX_LINHAS = 2  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:15
SEM_VIZINHA_S = 0.3  # palavra sem par e sem vizinha à direita; origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:46
ORFA_CARACTERES = 18  # linha menor que isto é órfã; origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:93
PESO_ORFA = 20  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:94
BONUS_VIRGULA = 6  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:94
FRASE_CURTA_PALAVRAS = 3  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:116
FOLGA_FIM_S = 0.25  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:129
DURACAO_MIN_S = 1.0  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:129
FOLGA_PROXIMA_S = 0.05  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:129
ULTIMA_FOLGA_S = 1.5  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:128

_MARCADOR = re.compile(r"\[\[\w+\]\]")  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:17
_FIM_FRASE = (".", ":", "?", "!")  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:107


def _norm(w: str) -> str:
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9]", "", w)


def palavras_do_whisper(whisper: dict[str, Any]) -> list[dict[str, Any]]:
    """[{word, start, end}] de qualquer um dos dois esquemas aceitos."""
    if "palavras" in whisper:
        return [{"word": p["w"], "start": p["t0"], "end": p["t1"]} for p in whisper["palavras"]]
    return [w for s in whisper.get("segments", []) for w in s.get("words", []) or []]


def alinhar_palavras(roteiro: str, whisper: dict[str, Any]) -> list[dict[str, Any]]:
    """[{w, s, e}] com as palavras do roteiro nos tempos do whisper (3 casas)."""
    script = _MARCADOR.sub("", roteiro).split()
    wwords = palavras_do_whisper(whisper)
    a = [_norm(w) for w in script]
    b = [_norm(w["word"]) for w in wwords]
    tempos: list[tuple[float, float] | None] = [None] * len(script)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                tempos[i1 + k] = (wwords[j1 + k]["start"], wwords[j1 + k]["end"])
        elif tag == "replace" and j2 > j1:
            t0, t1 = wwords[j1]["start"], wwords[j2 - 1]["end"]
            n = i2 - i1
            for k in range(n):
                tempos[i1 + k] = (t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n)
    for i, t in enumerate(tempos):
        if t is None:
            anterior = next((tempos[j][1] for j in range(i - 1, -1, -1) if tempos[j]), 0.0)
            proximo = next((tempos[j][0] for j in range(i + 1, len(tempos)) if tempos[j]),
                           anterior + SEM_VIZINHA_S)
            tempos[i] = (anterior, proximo)
    return [{"w": w, "s": round(s, 3), "e": round(e, 3)} for w, (s, e) in zip(script, tempos)]


def quebrar_linhas(texto: str) -> list[str]:
    """Linhas de até 42 caracteres; em duas linhas, o corte mais equilibrado (sem órfã)."""
    ws = texto.split()
    if len(texto) > MAX_CARACTERES:
        pares = [(" ".join(ws[:i]), " ".join(ws[i:])) for i in range(1, len(ws))]
        pares = [p for p in pares if max(map(len, p)) <= MAX_CARACTERES]
        if pares:
            return list(min(pares, key=lambda p: max(map(len, p))))
    linhas, atual = [], ""
    for w in ws:
        if len(atual) + len(w) + (1 if atual else 0) > MAX_CARACTERES and atual:
            linhas.append(atual)
            atual = w
        else:
            atual = f"{atual} {w}".strip()
    if atual:
        linhas.append(atual)
    return linhas


def _texto(ws: list[dict[str, Any]]) -> str:
    return " ".join(x["w"] for x in ws)


def _dividir_equilibrado(ws: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    k = math.ceil(len(quebrar_linhas(_texto(ws))) / MAX_LINHAS)
    if k <= 1:
        return [ws]
    total = len(_texto(ws))
    partes, resto = [], ws
    for _ in range(k - 1):
        alvo = total / k
        melhor, melhor_custo = None, None
        for i in range(1, len(resto)):
            esq, dir_ = quebrar_linhas(_texto(resto[:i])), quebrar_linhas(_texto(resto[i:]))
            if len(esq) > MAX_LINHAS:
                continue
            comprimento = len(_texto(resto[:i]))
            orfas = sum(1 for ln in esq if len(ln) < ORFA_CARACTERES) + (
                sum(1 for ln in dir_ if len(ln) < ORFA_CARACTERES) if k == 2 else 0)
            custo = abs(comprimento - alvo) + PESO_ORFA * orfas - (
                BONUS_VIRGULA if resto[i - 1]["w"].endswith(",") else 0)
            if melhor is None or custo < melhor_custo:
                melhor, melhor_custo = i, custo
        partes.append(resto[:melhor])
        resto = resto[melhor:]
        total = len(_texto(resto))
        k -= 1
    partes.append(resto)
    return partes


def legendas_aula(roteiro: str, whisper: dict[str, Any]) -> list[dict[str, Any]]:
    """[{start, end, lines}] da aula."""
    palavras = alinhar_palavras(roteiro, whisper)
    frases, atual = [], []
    for w in palavras:
        atual.append(w)
        if w["w"].endswith(_FIM_FRASE):
            frases.append(atual)
            atual = []
    if atual:
        frases.append(atual)

    juntas, i = [], 0
    while i < len(frases):
        frase = frases[i]
        if i + 1 < len(frases) and (frase[-1]["w"].endswith(":") or len(frase) <= FRASE_CURTA_PALAVRAS):
            juntas.append(frase + frases[i + 1])
            i += 2
            continue
        juntas.append(frase)
        i += 1

    blocos = [parte for frase in juntas for parte in _dividir_equilibrado(frase)]
    legendas = [{"start": b[0]["s"], "end": b[-1]["e"], "lines": quebrar_linhas(_texto(b))} for b in blocos]
    for i, c in enumerate(legendas):
        proximo = legendas[i + 1]["start"] if i + 1 < len(legendas) else c["end"] + ULTIMA_FOLGA_S
        c["end"] = round(min(max(c["end"] + FOLGA_FIM_S, c["start"] + DURACAO_MIN_S),
                             proximo - FOLGA_PROXIMA_S), 3)
    return legendas


def gerar(roteiro: str, whisper: dict[str, Any], destino_json: str | Path,
          destino_srt: str | Path) -> dict[str, Any]:
    """Grava o `legendas.json` da composição e o SRT (sempre, D-23). Devolve ``{legendas, json, srt}``."""
    legendas = legendas_aula(roteiro, whisper)
    arquivos.gravar_json(destino_json, legendas)
    srt.gravar_srt(legendas, destino_srt)
    return {"legendas": len(legendas), "json": Path(destino_json).name, "srt": Path(destino_srt).name}
