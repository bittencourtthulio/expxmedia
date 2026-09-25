"""T-04.07: transcrição com whisper (faster-whisper preferencial, openai-whisper de reserva, D-24).

- integração: o áudio falado do G8 transcrito offline (rede bloqueada pelo conftest, HF_HUB_OFFLINE=1)
  devolve palavras com tempos crescentes, e o texto é o da narração;
- funcional: sem faster-whisper importável, o módulo cai no openai-whisper (aqui um módulo simulado)
  e registra o motor usado; o modo alinhamento pede o modelo medium com beam_size 5 e a varredura
  pede small com busca gulosa, no idioma da Alma;
- paridade da conversão palavra → caractere com o `--alinhar` da origem (G7).
"""
import json
import re
import sys
import types
import unicodedata
from pathlib import Path

import pytest

from expxmedia.transcrever import whisper as tw

GOLDEN = Path(__file__).resolve().parents[1] / "golden"


def _norm(txt):
    txt = unicodedata.normalize("NFKD", txt.lower())
    return re.sub(r"[^a-z0-9 ]", "", txt).split()


# ------------------------------------------------------------------ integração

@pytest.mark.integracao_local
def test_transcreve_o_audio_do_g8_offline_com_tempos_crescentes(tmp_path):
    import os
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    audio = GOLDEN / "G8" / "narracao.mp3"
    r = tw.transcrever(audio, idioma="pt-BR", modo="varredura")

    assert r["motor"] == "faster-whisper"
    assert r["modelo"] == "small"
    assert r["idioma"] == "pt"
    palavras = r["palavras"]
    assert len(palavras) > 60
    for p in palavras:
        assert set(p) == {"w", "t0", "t1"} and p["w"].strip() == p["w"] and p["w"]
        assert p["t1"] >= p["t0"]
    inicios = [p["t0"] for p in palavras]
    assert all(b >= a for a, b in zip(inicios, inicios[1:])), "tempos de início não crescentes"
    assert inicios[-1] > 30.0  # a narração tem ~41 s: a transcrição cobre o áudio todo

    # o texto é o da narração: a maioria das palavras do roteiro aparece na transcrição
    roteiro = set(_norm((GOLDEN / "G8" / "roteiro.txt").read_text(encoding="utf-8")))
    ditas = _norm(" ".join(p["w"] for p in palavras))
    acertos = sum(1 for w in ditas if w in roteiro)
    assert acertos / len(ditas) > 0.8

    # e a saída vira alinhamento por caractere com as invariantes da origem
    texto, al = tw.para_alinhamento(palavras)
    assert "".join(al["characters"]) == texto
    cs = al["character_start_times_seconds"]
    assert all(b >= a - 1e-6 for a, b in zip(cs, cs[1:]))


# ------------------------------------------------------------------ funcional

class _Palavra:
    def __init__(self, word, start, end):
        self.word, self.start, self.end = word, start, end


class _Segmento:
    def __init__(self, start, end, text, words):
        self.start, self.end, self.text, self.words = start, end, text, words


def _faster_falso(chamadas):
    mod = types.ModuleType("faster_whisper")

    class WhisperModel:
        def __init__(self, modelo, **kw):
            chamadas.append(("modelo", modelo, kw))

        def transcribe(self, caminho, **kw):
            chamadas.append(("transcribe", caminho, kw))
            ws = [_Palavra(" Olá,", 0.0, 0.4), _Palavra(" mundo.", 0.5, 1.0), _Palavra(" Fim", 1.2, 1.5)]
            return iter([_Segmento(0.0, 1.5, " Olá, mundo. Fim", ws)]), None

    mod.WhisperModel = WhisperModel
    return mod


@pytest.fixture
def audio_falso(tmp_path):
    a = tmp_path / "fala.wav"
    a.write_bytes(b"RIFF")
    return a


def test_modo_alinhamento_pede_medium_com_beam_5_e_varredura_small_gulosa(monkeypatch, audio_falso):
    chamadas = []
    monkeypatch.setitem(sys.modules, "faster_whisper", _faster_falso(chamadas))

    r = tw.transcrever(audio_falso, idioma="es-MX", modo="alinhamento")
    (_, modelo, kw_mod), (_, _, kw) = chamadas
    assert modelo == "medium"
    assert kw_mod == {"device": "cpu", "compute_type": "int8"}
    assert kw["beam_size"] == 5
    assert kw["language"] == "es"  # idioma vem de quem chama (a Alma), nunca fixo em pt
    assert kw["word_timestamps"] is True and kw["vad_filter"] is True
    assert kw["condition_on_previous_text"] is False
    assert r["motor"] == "faster-whisper" and r["modelo"] == "medium"
    assert r["palavras"] == [{"w": "Olá,", "t0": 0.0, "t1": 0.4}, {"w": "mundo.", "t0": 0.5, "t1": 1.0},
                             {"w": "Fim", "t0": 1.2, "t1": 1.5}]
    assert r["segmentos"] == [{"t0": 0.0, "t1": 1.5, "texto": "Olá, mundo. Fim"}]

    chamadas.clear()
    tw.transcrever(audio_falso, idioma="pt-BR", modo="varredura")
    (_, modelo, _), (_, _, kw) = chamadas
    assert modelo == "small" and kw["beam_size"] == 1 and kw["language"] == "pt"

    assert (tw.MODELO_VARREDURA, tw.MODELO_ALINHAMENTO, tw.BEAM_ALINHAMENTO, tw.BEAM_VARREDURA) == \
        ("small", "medium", 5, 1)


def test_sem_faster_whisper_usa_a_reserva_e_registra_o_motor(monkeypatch, audio_falso):
    chamadas = []
    reserva = types.ModuleType("whisper")

    class _Modelo:
        def transcribe(self, caminho, **kw):
            chamadas.append(("transcribe", caminho, kw))
            return {"segments": [{"start": 0.0, "end": 1.0, "text": " Bom dia.",
                                  "words": [{"word": " Bom", "start": 0.0, "end": 0.3},
                                            {"word": " dia.", "start": 0.35, "end": 0.9}]}]}

    def load_model(nome, **kw):
        chamadas.append(("load_model", nome, kw))
        return _Modelo()

    reserva.load_model = load_model
    # faster-whisper tornado não importável: None em sys.modules faz o import levantar ImportError
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    monkeypatch.setitem(sys.modules, "whisper", reserva)

    r = tw.transcrever(audio_falso, idioma="pt-BR", modo="alinhamento")
    assert r["motor"] == "whisper"
    assert r["modelo"] == "medium"
    (_, nome, _), (_, _, kw) = chamadas
    assert nome == "medium"
    assert kw["language"] == "pt" and kw["word_timestamps"] is True and kw["fp16"] is False
    assert r["palavras"] == [{"w": "Bom", "t0": 0.0, "t1": 0.3}, {"w": "dia.", "t0": 0.35, "t1": 0.9}]


def test_sem_nenhum_motor_ou_sem_idioma_levanta_erro_claro(monkeypatch, audio_falso):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    monkeypatch.setitem(sys.modules, "whisper", None)
    with pytest.raises(tw.ErroTranscricao, match="faster-whisper"):
        tw.transcrever(audio_falso, idioma="pt-BR")
    with pytest.raises(tw.ErroTranscricao, match="idioma"):
        tw.transcrever(audio_falso, idioma=None)


def test_whisper_sem_palavras_com_tempo_levanta(monkeypatch, audio_falso):
    mod = types.ModuleType("faster_whisper")

    class WhisperModel:
        def __init__(self, *a, **k):
            pass

        def transcribe(self, *a, **k):
            return iter([_Segmento(0, 1, " x", [])]), None

    mod.WhisperModel = WhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", mod)
    with pytest.raises(tw.ErroTranscricao, match="tempo por palavra"):
        tw.transcrever(audio_falso, idioma="pt")


def test_idioma_da_alma():
    assert tw.idioma_da_alma({"empresa": {"idioma": "pt-BR"}}) == "pt"
    assert tw.idioma_da_alma({"empresa": {"idioma": "en"}}) == "en"
    assert tw.idioma_da_alma({"empresa": {"idioma": None}}) is None


# ------------------------------------------------------------------ paridade G7

def test_conversao_palavra_caractere_igual_ao_alinhar_da_origem():
    corte = json.loads((GOLDEN / "G7" / "transcricao_corte.json").read_text(encoding="utf-8"))
    texto, al = tw.para_alinhamento(corte["palavras"])
    assert texto + "\n" == (GOLDEN / "G7" / "roteiro.whisper.txt").read_text(encoding="utf-8")
    assert al == json.loads((GOLDEN / "G7" / "alignment.whisper.json").read_text(encoding="utf-8"))
