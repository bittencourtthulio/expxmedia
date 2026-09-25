"""Transcrição com tempo por palavra (capacidade `transcrever`, D-24).

Porta de `Instragram-Videos/pipeline/transcrever.py` (varredura e `--alinhar`). Duas passagens, de
propósito, porque são decisões de qualidade e não detalhe:

- ``varredura``: modelo rápido (`small`) com busca gulosa, para ESCOLHER trecho numa gravação longa;
  erro de grafia aqui não vai à tela;
- ``alinhamento``: modelo maior (`medium`) com beam 5, no trecho que vai QUEIMADO na tela.

Motores: `faster-whisper` (CTranslate2, 4 a 8x mais rápido em CPU) é o preferido; o `openai-whisper`
é a reserva quando o primeiro não está instalado — e o motor usado fica registrado na saída, porque a
reserva transforma minutos em meia hora e quem chama precisa saber disso.

O idioma vem de quem chama (a Alma, `empresa.idioma`), nunca fixo: extrair `pt` cravado faria uma
instalação não lusófona transcrever errado sem erro. Os modelos saem só do cache local quando
`HF_HUB_OFFLINE=1`.

Saída de `transcrever`: ``{fonte, modelo, motor, idioma, palavras: [{w, t0, t1}], segmentos: [{t0, t1, texto}]}``,
tempos a 3 casas. `para_alinhamento` converte as palavras no alinhamento por caractere do mesmo formato
que a narração devolve (`characters`, `character_start_times_seconds`, `character_end_times_seconds`),
o que torna a legenda agnóstica da origem da fala.

Uso:

    from expxmedia.transcrever import whisper
    t = whisper.transcrever("corte.mp4", idioma=whisper.idioma_da_alma(alma.dados), modo="alinhamento")
    texto, alinhamento = whisper.para_alinhamento(t["palavras"])
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

__all__ = [
    "ErroTranscricao",
    "MODELO_VARREDURA",
    "MODELO_ALINHAMENTO",
    "BEAM_VARREDURA",
    "BEAM_ALINHAMENTO",
    "MODOS",
    "idioma_da_alma",
    "transcrever",
    "para_alinhamento",
]

MODELO_VARREDURA = "small"  # origem: Instragram-Videos/pipeline/transcrever.py:41
MODELO_ALINHAMENTO = "medium"  # origem: Instragram-Videos/pipeline/transcrever.py:41
BEAM_VARREDURA = 1  # busca gulosa; origem: Instragram-Videos/pipeline/transcrever.py:134
BEAM_ALINHAMENTO = 5  # origem: Instragram-Videos/pipeline/transcrever.py:134
MODOS = ("varredura", "alinhamento")
PALAVRA_MIN_S = 0.02  # duração mínima de uma palavra no alinhamento; origem: Instragram-Videos/pipeline/transcrever.py:194
PROGRESSO_S = 60  # progresso a cada 60 s de áudio consumido; origem: Instragram-Videos/pipeline/transcrever.py:138


class ErroTranscricao(RuntimeError):
    """Transcrição impossível: sem motor, sem idioma, ou sem tempo por palavra."""


def idioma_da_alma(alma: Any) -> str | None:
    """Código de idioma do whisper a partir de `empresa.idioma` da Alma (`pt-BR` → `pt`)."""
    dados = alma.dados if hasattr(alma, "dados") else alma
    idioma = ((dados or {}).get("empresa") or {}).get("idioma")
    return _codigo(idioma)


def _codigo(idioma: str | None) -> str | None:
    if not isinstance(idioma, str) or not idioma.strip():
        return None
    return idioma.strip().replace("_", "-").split("-")[0].lower()


def _motor() -> tuple[str, Any]:
    """(nome, módulo) do motor disponível: faster-whisper, senão openai-whisper."""
    try:
        from faster_whisper import WhisperModel  # noqa: F401
        import faster_whisper
        return "faster-whisper", faster_whisper
    except ImportError:
        pass
    try:
        import whisper
        return "whisper", whisper
    except ImportError:
        raise ErroTranscricao(
            "nenhum motor de transcrição instalado: instale faster-whisper (preferido) "
            "ou openai-whisper (reserva, extra whisper-reserva)") from None


def transcrever(
    audio: str | Path,
    *,
    idioma: str | None,
    modo: str = "varredura",
    modelo: str | None = None,
    beam: int | None = None,
    progresso: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Transcreve `audio` com tempo por palavra.

    `idioma` é obrigatório (código ou tag, ex. `pt-BR`; use `idioma_da_alma`). `modo` escolhe o
    modelo e o beam padrão (`varredura`: small/1; `alinhamento`: medium/5); `modelo` e `beam`
    sobrescrevem. Levanta ErroTranscricao sem motor, sem idioma ou sem palavra com tempo.
    """
    if modo not in MODOS:
        raise ValueError(f"modo desconhecido: {modo!r} (válidos: {', '.join(MODOS)})")
    lingua = _codigo(idioma)
    if lingua is None:
        raise ErroTranscricao("idioma não informado: passe o idioma da Alma (empresa.idioma)")
    audio = Path(audio)
    if not audio.exists():
        raise ErroTranscricao(f"arquivo de áudio não existe: {audio.name}")
    alinhar = modo == "alinhamento"
    modelo = modelo or (MODELO_ALINHAMENTO if alinhar else MODELO_VARREDURA)
    beam = beam if beam is not None else (BEAM_ALINHAMENTO if alinhar else BEAM_VARREDURA)
    nome_motor, mod = _motor()
    avisar = progresso or (lambda _msg: None)

    palavras: list[dict[str, Any]] = []
    segmentos: list[dict[str, Any]] = []
    if nome_motor == "faster-whisper":
        # int8 no CPU: perda irrelevante para fala e o ganho de tempo torna a etapa usável.
        # origem: Instragram-Videos/pipeline/transcrever.py:125
        m = mod.WhisperModel(modelo, device="cpu", compute_type="int8")
        # vad_filter pula silêncio; condition_on_previous_text=False evita o laço de repetição em
        # áudio longo (medido: 15 min de CPU a 400% sem fechar).
        # origem: Instragram-Videos/pipeline/transcrever.py:126-134
        segs, _info = m.transcribe(str(audio), language=lingua, word_timestamps=True, vad_filter=True,
                                   condition_on_previous_text=False, beam_size=beam)
        t_ini, marca = time.time(), 0.0
        for sg in segs:
            if sg.end - marca >= PROGRESSO_S:
                marca = sg.end
                avisar(f"{sg.end / 60:.0f} min transcritos ({time.time() - t_ini:.0f} s decorridos)")
            segmentos.append({"t0": round(sg.start, 3), "t1": round(sg.end, 3), "texto": sg.text.strip()})
            for pw in (sg.words or []):
                txt = pw.word.strip()
                if txt:
                    palavras.append({"w": txt, "t0": round(pw.start, 3), "t1": round(pw.end, 3)})
    else:
        # Reserva: mesmos parâmetros do CLI da origem (--word_timestamps True --fp16 False), pela API
        # do módulo. origem: Instragram-Videos/pipeline/transcrever.py:150-165
        m = mod.load_model(modelo)
        w = m.transcribe(str(audio), language=lingua, word_timestamps=True, fp16=False, beam_size=beam)
        for sg in w.get("segments", []) or []:
            segmentos.append({"t0": round(sg["start"], 3), "t1": round(sg["end"], 3),
                              "texto": sg["text"].strip()})
            for pw in sg.get("words", []) or []:
                txt = pw["word"].strip()
                if txt:
                    palavras.append({"w": txt, "t0": round(pw["start"], 3), "t1": round(pw["end"], 3)})
    if not palavras:
        # origem: Instragram-Videos/pipeline/transcrever.py:167-169
        raise ErroTranscricao(f"o motor {nome_motor} não devolveu tempo por palavra "
                              "(word_timestamps exige versão recente do whisper)")
    return {"fonte": audio.name, "modelo": modelo, "motor": nome_motor, "idioma": lingua,
            "palavras": palavras, "segmentos": segmentos}


def para_alinhamento(palavras: list[dict[str, Any]]) -> tuple[str, dict[str, list]]:
    """(texto, alinhamento por caractere) a partir das palavras com tempo.

    Dentro de uma palavra o tempo é distribuído uniformemente (erro de dezenas de milissegundos);
    o separador entre palavras é `\\n` depois de `. ? ! :` e espaço nos demais casos, e ocupa o
    silêncio entre elas; cada palavra dura ao menos 0,02 s e nunca começa antes do fim da anterior.
    Tempos a 4 casas. origem: Instragram-Videos/pipeline/transcrever.py:180-213
    """
    chars: list[str] = []
    cs: list[float] = []
    ce: list[float] = []
    roteiro: list[str] = []
    anterior_fim = 0.0
    for i, p in enumerate(palavras):
        if i:
            sep = "\n" if palavras[i - 1]["w"].endswith((".", "?", "!", ":")) else " "
            chars.append(sep)
            cs.append(anterior_fim)
            ce.append(max(p["t0"], anterior_fim))
            roteiro.append(sep)
        t0, t1 = max(p["t0"], anterior_fim), max(p["t1"], p["t0"] + PALAVRA_MIN_S)
        passo = (t1 - t0) / len(p["w"])
        for k, c in enumerate(p["w"]):
            chars.append(c)
            cs.append(t0 + k * passo)
            ce.append(t0 + (k + 1) * passo)
        roteiro.append(p["w"])
        anterior_fim = t1

    texto = "".join(roteiro)
    if len(chars) != len(texto) or "".join(chars) != texto:
        raise ErroTranscricao("o alinhamento não reconstrói o texto")
    if any(y < x - 1e-6 for x, y in zip(cs, cs[1:])):
        raise ErroTranscricao("tempos não monotônicos no alinhamento")
    return texto, {
        "characters": chars,
        "character_start_times_seconds": [round(v, 4) for v in cs],
        "character_end_times_seconds": [round(v, 4) for v in ce],
    }
