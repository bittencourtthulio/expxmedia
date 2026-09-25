"""Recasamento: grafias corrigidas à mão aplicadas sobre os tempos da transcrição.

O whisper erra nome próprio e jargão, e o texto do alinhamento é o que vai QUEIMADO na tela. Corrigir
só o texto do roteiro não basta: a legenda é montada a partir de `characters` do alinhamento, então sem
recasar a correção seria ignorada em silêncio. Aqui ela nunca é descartada: todo trecho diferente entra.

Porta de `Instragram-Videos/pipeline/transcrever.py:52-92` (`--recasar`, versão atual):

- `difflib.SequenceMatcher(autojunk=False)` caractere a caractere entre o texto do alinhamento e o novo;
- trecho igual copia os tempos EXATOS;
- trecho trocado distribui o intervalo do trecho velho uniformemente sobre o texto novo;
- inserção pura no meio do texto tem LARGURA ZERO no ponto de inserção (a correção de grafia não ocupa
  tempo de fala); só no fim do texto, onde não existe caractere seguinte, estica 0,02 s por caractere.
  Esticar no meio invadia o caractere seguinte e quebrava a monotonicidade (caso real: inserir "pull "
  em "esse request").

Uso:

    from expxmedia.transcrever import recasar
    novo, trechos = recasar.recasar(alinhamento, texto_corrigido)
    recasar.recasar_arquivos("alignment.json", "roteiro.txt")   # grava no lugar (M15)
"""
from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from expxmedia.nucleo import arquivos

__all__ = ["ErroRecasar", "recasar", "recasar_arquivos"]

ESTICA_FIM_S = 0.02  # por caractere inserido no fim do texto; origem: Instragram-Videos/pipeline/transcrever.py:78
TOLERANCIA_MONOTONIA = 1e-6  # origem: Instragram-Videos/pipeline/transcrever.py:84
CASAS = 4  # origem: Instragram-Videos/pipeline/transcrever.py:87-88


class ErroRecasar(ValueError):
    """Alinhamento inconsistente ou recasamento que quebraria as invariantes."""


def recasar(alinhamento: dict[str, list], texto: str) -> tuple[dict[str, list], int]:
    """(alinhamento recasado sobre `texto`, número de trechos diferentes).

    `texto` perde só as quebras de linha finais. Texto igual devolve o alinhamento sem mudança e 0.
    """
    try:
        velho_chars = alinhamento["characters"]
        vs = alinhamento["character_start_times_seconds"]
        ve = alinhamento["character_end_times_seconds"]
    except (KeyError, TypeError):
        raise ErroRecasar("alinhamento sem characters e tempos por caractere") from None
    if not (len(velho_chars) == len(vs) == len(ve)):
        raise ErroRecasar("alinhamento com listas de tamanhos diferentes")
    velho = "".join(velho_chars)
    novo = texto.rstrip("\n")
    if velho == novo:
        return alinhamento, 0

    chars: list[str] = []
    cs: list[float] = []
    ce: list[float] = []
    sm = difflib.SequenceMatcher(None, velho, novo, autojunk=False)
    opcodes = sm.get_opcodes()
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            chars += list(novo[j1:j2])
            cs += vs[i1:i2]
            ce += ve[i1:i2]
        elif j2 > j1:
            t0 = vs[i1] if i1 < len(vs) else (ve[-1] if ve else 0.0)
            t1 = ve[i2 - 1] if i2 - 1 < len(ve) and i2 > i1 else t0
            if t1 <= t0:
                # inserção pura: largura zero no meio, 0,02 s por caractere só no fim do texto
                t1 = t0 + ESTICA_FIM_S * (j2 - j1) if i1 >= len(vs) else t0
            passo = (t1 - t0) / (j2 - j1)
            for k, c in enumerate(novo[j1:j2]):
                chars.append(c)
                cs.append(t0 + k * passo)
                ce.append(t0 + (k + 1) * passo)
        # tag "delete": os caracteres velhos somem com os seus tempos

    if "".join(chars) != novo or len(chars) != len(novo):
        raise ErroRecasar("o recasamento não reconstrói o texto corrigido")
    if any(y < x - TOLERANCIA_MONOTONIA for x, y in zip(cs, cs[1:])):
        raise ErroRecasar("tempos não monotônicos depois do recasamento")
    mudados = sum(1 for t, *_ in opcodes if t != "equal")
    return {
        "characters": chars,
        "character_start_times_seconds": [round(v, CASAS) for v in cs],
        "character_end_times_seconds": [round(v, CASAS) for v in ce],
    }, mudados


def recasar_arquivos(alinhamento: str | Path, texto: str | Path) -> dict[str, Any]:
    """Recasa o arquivo de alinhamento com o texto corrigido e grava no lugar (escrita atômica).

    Devolve ``{recasado, trechos, caracteres}``; com o texto já igual, não escreve nada.
    """
    alinhamento = Path(alinhamento)
    al = arquivos.ler_json(alinhamento)
    novo, trechos = recasar(al, Path(texto).read_text(encoding="utf-8"))
    if trechos:
        arquivos.gravar_json(alinhamento, novo)
    return {"recasado": bool(trechos), "trechos": trechos, "caracteres": len(novo["characters"])}
