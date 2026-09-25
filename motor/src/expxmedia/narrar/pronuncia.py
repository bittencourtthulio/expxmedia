"""Camada falada: o léxico de pronúncia do porta-voz na fala e o alinhamento de volta ao roteiro (D-22).

Porta de `Instragram-Videos/pipeline/pronuncia.py`, com o léxico vindo da Alma
(`porta_vozes[].voz.pronuncia`, lista de `{termo, fala}`) em vez de uma tabela fixa.

POR QUE ISSO EXISTE — o modelo de fala lê o roteiro no idioma dele e abrasileira termos
estrangeiros. O mecanismo que funciona sem trocar de modelo (e de voz clonada) é o **alias**:
escrever o termo com a grafia que produz o som certo.

O TEXTO FALADO NÃO É O TEXTO ESCRITO — a legenda desenha os caracteres do alinhamento. Se ele
ficasse no espaço da fala, a legenda mostraria a grafia do alias. Por isso o alinhamento volta ao
espaço do roteiro antes de ser gravado; os `segmentos` de `aplicar()` são o mapa.

Regras do casamento (CONTRATO-alma, `pronuncia`):
- termo pode ter várias palavras; os mais longos casam primeiro ("petit gâteau" antes de "gâteau");
- ignora maiúsculas, com fronteira de palavra nas duas pontas; plural é termo próprio;
- a caixa do roteiro é preservada na fala (`RUNX` → `RUN ÉKS`): caixa alta é ênfase.

Se a API normalizar o texto (o alinhamento devolvido não reconstrói a fala enviada), remapear em
cima disso daria legenda torta em silêncio: `conferir_devolvido` grava `alignment.raw.json` e
levanta erro, e a API **não** é chamada de novo (origem: Instragram-Videos/pipeline/tts.py:128-139).
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from expxmedia.narrar.base import ARQUIVO_ALINHAMENTO_BRUTO, ErroNarrar
from expxmedia.nucleo import arquivos

__all__ = ["normalizar_lexico", "aplicar", "remapear", "conferir_devolvido", "termos_multi", "substituidos"]

Lexico = Iterable[Mapping[str, str]] | Mapping[str, str] | None
Segmento = tuple[int, int, int, int]
TRECHO_ERRO = 200  # caracteres de cada lado no erro; origem: Instragram-Videos/pipeline/tts.py:136-137


def normalizar_lexico(lexico: Lexico) -> dict[str, str]:
    """{termo em minúsculas: fala}. Aceita a lista da Alma ou um dicionário {termo: fala}."""
    if not lexico:
        return {}
    pares = lexico.items() if isinstance(lexico, Mapping) else (
        (e.get("termo"), e.get("fala")) for e in lexico if isinstance(e, Mapping)
    )
    saida: dict[str, str] = {}
    for termo, fala in pares:
        if isinstance(termo, str) and isinstance(fala, str) and termo.strip() and fala.strip():
            saida[termo.strip().lower()] = fala.strip()
    return saida


def _regex(termos: dict[str, str]) -> re.Pattern[str] | None:
    if not termos:
        return None
    # frases de várias palavras antes das de uma só: alternância por comprimento decrescente
    # origem: Instragram-Videos/pipeline/pronuncia.py:72-80
    chaves = sorted(termos, key=len, reverse=True)
    # fronteira de palavra nas duas pontas (o `\b` da origem, que também vale para termo que
    # começa ou termina fora de \w)
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(k) for k in chaves) + r")(?!\w)", re.IGNORECASE)


def _com_caixa(grafia: str, fala: str) -> str:
    """A fala com a CAIXA do roteiro. origem: Instragram-Videos/pipeline/pronuncia.py:87-101"""
    letras = [c for c in grafia if c.isalpha()]
    if letras and all(c.isupper() for c in letras):
        return fala.upper()
    if grafia[:1].isupper():
        return fala[:1].upper() + fala[1:]
    return fala


def aplicar(texto: str, lexico: Lexico) -> tuple[str, list[Segmento]]:
    """(fala, segmentos). `segmentos` = `(ini_orig, fim_orig, ini_fala, fim_fala)` cobrindo o texto
    inteiro, sem buraco nem sobreposição, alternando trechos literais e substituídos.

    origem: Instragram-Videos/pipeline/pronuncia.py:104-130
    """
    termos = normalizar_lexico(lexico)
    padrao = _regex(termos)
    partes: list[str] = []
    segmentos: list[Segmento] = []
    pos = nf = 0

    def _empurrar(ini_o: int, fim_o: int, trecho: str) -> None:
        nonlocal nf
        segmentos.append((ini_o, fim_o, nf, nf + len(trecho)))
        partes.append(trecho)
        nf += len(trecho)

    if padrao is not None:
        for m in padrao.finditer(texto):
            if m.start() > pos:
                _empurrar(pos, m.start(), texto[pos:m.start()])
            _empurrar(m.start(), m.end(), _com_caixa(m.group(0), termos[m.group(0).lower()]))
            pos = m.end()
    if pos < len(texto):
        _empurrar(pos, len(texto), texto[pos:])
    return "".join(partes), segmentos


def remapear(alinhamento: dict[str, Any], original: str, fala: str, segmentos: list[Segmento]) -> dict[str, list]:
    """Traz o alinhamento do espaço da FALA de volta ao do ORIGINAL.

    Trecho literal: tempos copiados caractere a caractere. Trecho substituído: o intervalo total
    (início do 1º caractere falado até o fim do último) é distribuído uniformemente sobre os
    caracteres originais — aproximação aceita na origem, não trocar sem teste.
    origem: Instragram-Videos/pipeline/pronuncia.py:133-164
    """
    cs = alinhamento["character_start_times_seconds"]
    ce = alinhamento["character_end_times_seconds"]
    chars: list[str] = []
    ini: list[float] = []
    fim: list[float] = []
    for io, fo, i_f, f_f in segmentos:
        trecho_o, trecho_f = original[io:fo], fala[i_f:f_f]
        if trecho_o == trecho_f:
            chars.extend(trecho_o)
            ini.extend(cs[i_f:f_f])
            fim.extend(ce[i_f:f_f])
            continue
        t0, t1 = cs[i_f], ce[f_f - 1]
        n = len(trecho_o)
        passo = (t1 - t0) / n if n else 0.0
        for k, c in enumerate(trecho_o):
            chars.append(c)
            ini.append(t0 + passo * k)
            fim.append(t0 + passo * (k + 1))
    if len(chars) != len(original) or "".join(chars) != original or len(ini) != len(chars):
        raise ValueError("remapeamento não reconstrói o roteiro original")
    return {"characters": chars, "character_start_times_seconds": ini, "character_end_times_seconds": fim}


def conferir_devolvido(alinhamento: dict[str, Any], fala: str, pasta: Path | str) -> None:
    """Para tudo se o texto do alinhamento não é a fala enviada (a API normalizou o texto).

    Grava o bruto em `alignment.raw.json` na `pasta` e levanta `ErroNarrar("texto_normalizado")`.
    O mp3 já foi gravado pelo provedor antes desta conferência.
    """
    devolvido = "".join(alinhamento.get("characters") or [])
    if devolvido == fala:
        return
    arquivos.gravar_json(Path(pasta) / ARQUIVO_ALINHAMENTO_BRUTO, alinhamento)
    raise ErroNarrar(
        "texto_normalizado",
        "o texto devolvido pelo alinhamento não bate com o texto enviado.\n"
        f"  enviado   ({len(fala)} chars): {fala[:TRECHO_ERRO]!r}\n"
        f"  devolvido ({len(devolvido)} chars): {devolvido[:TRECHO_ERRO]!r}\n"
        f"narracao.mp3 e {ARQUIVO_ALINHAMENTO_BRUTO} foram gravados (o crédito não se perdeu).\n"
        "Conserte o remapeamento a partir deles — NÃO chame a API de novo.",
    )


def termos_multi(lexico: Lexico) -> tuple[tuple[str, ...], ...]:
    """Termos de mais de uma palavra, em minúsculas, para a legenda não rachar o termo entre blocos.

    origem: Instragram-Videos/pipeline/pronuncia.py:82-84
    """
    termos = sorted(normalizar_lexico(lexico), key=len, reverse=True)
    return tuple(tuple(t.split()) for t in termos if len(t.split()) > 1)


def substituidos(original: str, fala: str, segmentos: list[Segmento]) -> int:
    """Quantos trechos saíram com pronúncia forçada. origem: Instragram-Videos/pipeline/tts.py:151"""
    return sum(1 for io, fo, i, f in segmentos if original[io:fo] != fala[i:f])
