"""Gate do roteirista do reel narrado: o roteiro só vai para a narração se passar aqui.

Porta de `Instragram-Videos/.claude/hooks/roteirista/stop-gate.sh` (com a faixa de `Instragram-Videos/pipeline/lib.py:13`):

- 130 a 180 palavras (~60 s de fala);
- a palavra do CTA declarada (o `cta.txt` da origem) não vazia e contida no roteiro: senão a narração
  não pede o que a legenda e o card mostram;
- nada de travessão (– —), markdown (* # `) nem número decimal em algarismo: o TTS lê errado.

Como na origem, o gate pega só o número **decimal** em algarismo (`\\d+[.,]\\d`); inteiro passa. A regra
de voz pede números por extenso, mas mecanizar mais que a origem mudaria o que ela aprova.

Diferença deliberada: a origem para no primeiro problema; aqui todos os achados vêm juntos, no formato
dos demais gates (`{checagem, detalhe, esperado, obtido}`).

Uso:

    from expxmedia.revisar import roteiro
    r = roteiro.revisar_roteiro(texto, "PALAVRA")   # {"aprovado", "palavras", "cta", "achados"}
"""
from __future__ import annotations

import re
from typing import Any

__all__ = ["PALAVRAS_MIN", "PALAVRAS_MAX", "revisar_roteiro"]

PALAVRAS_MIN, PALAVRAS_MAX = 130, 180  # origem: Instragram-Videos/pipeline/lib.py:13 e .claude/hooks/roteirista/stop-gate.sh:12
# origem: Instragram-Videos/.claude/hooks/roteirista/stop-gate.sh:16 — r"[–—*#`]|\d+[.,]\d", separado por motivo
_TRAVESSAO = re.compile("[–—]")
_MARKDOWN = re.compile(r"[*#`]")
_DECIMAL = re.compile(r"\d+[.,]\d")


def _achado(checagem: str, detalhe: str, esperado: str, obtido: Any) -> dict[str, Any]:
    return {"checagem": checagem, "detalhe": detalhe, "esperado": esperado, "obtido": obtido}


def revisar_roteiro(roteiro: str, cta: str | None) -> dict[str, Any]:
    """Aplica o gate ao `roteiro` com a palavra do `cta`. Não levanta: devolve `aprovado` e os achados."""
    texto = roteiro or ""
    palavras = len(texto.split())
    cta = (cta or "").strip()
    achados = []
    if not PALAVRAS_MIN <= palavras <= PALAVRAS_MAX:
        achados.append(_achado("palavras", f"roteiro com {palavras} palavras, fora de {PALAVRAS_MIN}-{PALAVRAS_MAX}",
                               f"{PALAVRAS_MIN} a {PALAVRAS_MAX} palavras", palavras))
    if not cta:
        achados.append(_achado("cta", "palavra do CTA vazia ou ausente", "palavra do CTA declarada", None))
    elif cta not in texto:
        achados.append(_achado("cta", f"CTA '{cta}' não aparece no roteiro", "CTA contido no roteiro", cta))
    for checagem, padrao, detalhe in (
        ("travessao", _TRAVESSAO, "roteiro tem travessão — o TTS lê errado"),
        ("markdown", _MARKDOWN, "roteiro tem markdown — o TTS lê o símbolo"),
        ("numero_decimal", _DECIMAL, "roteiro tem número decimal em algarismo — escreva por extenso"),
    ):
        achou = padrao.findall(texto)
        if achou:
            achados.append(_achado(checagem, detalhe, "nenhuma ocorrência", achou[:5]))
    return {"aprovado": not achados, "palavras": palavras, "cta": cta or None, "achados": achados}
