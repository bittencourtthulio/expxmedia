"""T-07.01: marcadores [[sN]] do roteiro -> cues.json a partir do alinhamento, com hash da narração.

origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:22-28 (marcadores) e :58-67 (cues).
A narração vem do provedor de teste (D-34, D-39): nenhum custo.
"""
import json
import re
from pathlib import Path

import pytest

from expxmedia.aula import cues
from expxmedia.narrar import base, teste

pytestmark = pytest.mark.integracao_local

PORTA_VOZ = "porta-voz-teste"
G5 = Path(__file__).resolve().parents[1] / "golden" / "G5"

# marcador no começo, marcador seguido de espaços e quebra de linha, subcue no meio da frase
ROTEIRO = (
    "[[s1]]A fornada sai cedo e o forno já está quente.\n\n"
    "[[s2]]   \n  Primeiro separe a farinha, depois o sal. [[s2_sal]] O sal entra por último.\n"
    "[[s3]] Por fim, descanse a massa por uma hora."
)


@pytest.fixture
def aula(instalacao, requer_binario, monkeypatch):
    requer_binario("ffmpeg")
    requer_binario("ffprobe")
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    (instalacao / ".env").write_text("EXPXMEDIA_PROVEDORES_TESTE=1\n", encoding="utf-8")
    return instalacao


def _narrar(raiz, pps):
    texto = cues.texto_falado(ROTEIRO)
    return base.narrar(raiz, texto, PORTA_VOZ, "aula", "midia", palavras_por_segundo=pps)


def _palavra_seguinte(texto_limpo, offset):
    """Índice (na lista de palavras) da primeira palavra que começa em ou depois do offset."""
    for k, m in enumerate(re.finditer(r"\S+", texto_limpo)):
        if m.start() >= offset:
            return k
    raise AssertionError("sem palavra depois do marcador")


# ---------------------------------------------------------------- integração

def test_cues_do_alinhamento_do_provedor_de_teste(aula):
    pps = 3.0
    r = _narrar(aula, pps)
    pasta = aula / "midia"
    saida = cues.gerar(aula, ROTEIRO, pasta)

    gravado = json.loads((pasta / "cues.json").read_text(encoding="utf-8"))
    assert saida == gravado
    # um início por marcador, na ordem do roteiro, em ordem crescente
    assert list(gravado["cues"]) == ["s1", "s2", "s2_sal", "s3"]
    tempos = list(gravado["cues"].values())
    assert tempos == sorted(tempos) and len(set(tempos)) == len(tempos)

    texto, offsets = cues.separar(ROTEIRO)
    assert texto == cues.texto_falado(ROTEIRO)
    janela = 1.0 / pps
    for nome, off in offsets.items():
        # o marcador aponta para a PRÓXIMA LETRA falada: o início da palavra seguinte no sinal
        k = _palavra_seguinte(texto, off)
        assert gravado["cues"][nome] == pytest.approx(round(k * janela, 3), abs=1e-6), nome

    # [[s2]] é seguido de espaços e quebra: o caractere no offset é espaço, cujo tempo é a pausa da
    # palavra anterior; o cue não pode cair nele
    off_s2 = offsets["s2"]
    assert texto[off_s2].isspace()
    t_espaco = r["alinhamento"]["character_start_times_seconds"][off_s2]
    assert gravado["cues"]["s2"] > t_espaco
    assert texto[off_s2:].lstrip().startswith("Primeiro")

    # duração = fim da fala + 1,5 s (origem: gerar_voz.py:65)
    fim = r["alinhamento"]["character_end_times_seconds"][-1]
    assert gravado["duration"] == pytest.approx(round(fim + 1.5, 3))
    # hash da narração e caminho relativo (M9)
    assert gravado["narracao"] == "narracao.mp3"
    assert gravado["narracao_sha256"] == cues.hash_arquivo(pasta / "narracao.mp3")
    assert gravado["desatualizados"] == []


def test_marcadores_do_golden_g5_viram_os_mesmos_cues(aula):
    """O roteiro real da origem produz exatamente as chaves do cues.json gravado pela origem."""
    roteiro = (G5 / "entradas" / "roteiro.txt").read_text(encoding="utf-8")
    origem = json.loads((G5 / "cues.json").read_text(encoding="utf-8"))
    texto = cues.texto_falado(roteiro)
    assert "[[" not in texto
    alinhamento = teste.alinhamento_sintetico(texto, 2.5)
    calculado = cues.calcular(roteiro, alinhamento)
    assert list(calculado["cues"]) == list(origem["cues"])
    assert calculado["cues"]["s1"] == origem["cues"]["s1"] == 0.0
    valores = list(calculado["cues"].values())
    assert valores == sorted(valores)


# ---------------------------------------------------------------- unidade do porte

def test_calcular_porta_a_regra_da_origem():
    # alinhamento à mão: cada caractere 0,1 s; espaço no offset do marcador
    roteiro = "[[a]]Oi.[[b]]   tudo [[c]]bem"
    texto, offsets = cues.separar(roteiro)
    assert texto == "Oi.   tudo bem"
    assert offsets == {"a": 0, "b": 3, "c": 11}
    ali = {
        "characters": list(texto),
        "character_start_times_seconds": [i * 0.1 for i in range(len(texto))],
        "character_end_times_seconds": [(i + 1) * 0.1 for i in range(len(texto))],
    }
    r = cues.calcular(roteiro, ali)
    # b pula os 3 espaços até o "t" (índice 6)
    assert r["cues"] == {"a": 0.0, "b": 0.6, "c": 1.1}
    assert r["duration"] == round(len(texto) * 0.1 + 1.5, 3)


def test_marcador_no_fim_usa_o_ultimo_caractere():
    roteiro = "fim [[z]]"
    ali = teste.alinhamento_sintetico(cues.texto_falado(roteiro), 2.0)
    r = cues.calcular(roteiro, ali)
    # origem: starts[min(index, len - 1)]
    assert r["cues"]["z"] == round(ali["character_start_times_seconds"][-1], 3)


def test_espaco_antes_do_primeiro_marcador_nao_desloca(aula):
    roteiro = "  [[s1]] Olá, tudo certo. [[s2]]Segunda parte."
    texto = cues.texto_falado(roteiro)
    assert texto == "Olá, tudo certo. Segunda parte."
    ali = teste.alinhamento_sintetico(texto, 2.0)
    r = cues.calcular(roteiro, ali)
    assert r["cues"] == {"s1": 0.0, "s2": 1.5}


def test_alinhamento_de_outro_texto_e_recusado():
    ali = teste.alinhamento_sintetico("outro texto qualquer", 2.0)
    with pytest.raises(cues.ErroCues) as e:
        cues.calcular("[[s1]]texto do roteiro", ali)
    assert e.value.codigo == "alinhamento_divergente"


def test_marcador_repetido_e_recusado():
    with pytest.raises(cues.ErroCues) as e:
        cues.separar("[[s1]]um [[s1]]dois")
    assert e.value.codigo == "marcador_repetido"


def test_roteiro_sem_marcador_e_recusado():
    with pytest.raises(cues.ErroCues) as e:
        cues.separar("sem marcador nenhum")
    assert e.value.codigo == "sem_marcador"


# ---------------------------------------------------------------- funcional

def test_mudar_a_narracao_marca_avatar_e_legendas_desatualizados(aula):
    pasta = aula / "midia"
    _narrar(aula, 3.0)
    primeiro = cues.gerar(aula, ROTEIRO, pasta)
    # dependentes produzidos a partir desta narração
    (pasta / "avatar.mp4").write_bytes(b"avatar")
    (pasta / "legendas.json").write_text("[]", encoding="utf-8")
    (pasta / "aula.srt").write_text("", encoding="utf-8")

    # regerar com a MESMA narração: hash igual, nada desatualizado
    mesmo = cues.gerar(aula, ROTEIRO, pasta)
    assert mesmo["narracao_sha256"] == primeiro["narracao_sha256"]
    assert mesmo["desatualizados"] == []
    assert cues.desatualizados(pasta) == []
    assert not cues.narracao_mudou(pasta)

    # narração regravada (outro ritmo): o mp3 muda antes do cues.json ser refeito
    _narrar(aula, 2.0)
    assert cues.narracao_mudou(pasta)
    novo = cues.gerar(aula, ROTEIRO, pasta)
    assert novo["narracao_sha256"] != primeiro["narracao_sha256"]
    assert novo["narracao_sha256"] == cues.hash_arquivo(pasta / "narracao.mp3")
    assert novo["cues"] != primeiro["cues"]
    assert novo["desatualizados"] == ["aula.srt", "avatar.mp4", "legendas.json"]
    assert cues.desatualizados(pasta) == ["aula.srt", "avatar.mp4", "legendas.json"]
    assert not cues.narracao_mudou(pasta)

    # gerar de novo sem regerar os dependentes não "esquece" que estão desatualizados
    assert cues.gerar(aula, ROTEIRO, pasta)["desatualizados"] == ["aula.srt", "avatar.mp4", "legendas.json"]

    # quem regera o avatar dá baixa; dependente apagado sai da lista
    (pasta / "aula.srt").unlink()
    assert cues.desatualizados(pasta) == ["avatar.mp4", "legendas.json"]
    assert cues.marcar_atualizado(aula, pasta, "avatar.mp4") == ["legendas.json"]
    assert cues.desatualizados(pasta) == ["legendas.json"]
    gravado = json.loads((pasta / "cues.json").read_text(encoding="utf-8"))
    assert gravado["desatualizados"] == ["legendas.json"]


def test_primeira_geracao_com_dependente_de_origem_desconhecida(aula):
    """Sem cues.json anterior não há como saber de que narração o avatar veio: fica desatualizado."""
    pasta = aula / "midia"
    _narrar(aula, 3.0)
    (pasta / "avatar.mp4").write_bytes(b"velho")
    assert cues.gerar(aula, ROTEIRO, pasta)["desatualizados"] == ["avatar.mp4"]


def test_marcar_atualizado_recusa_quem_nao_e_dependente(aula):
    pasta = aula / "midia"
    _narrar(aula, 3.0)
    cues.gerar(aula, ROTEIRO, pasta)
    with pytest.raises(cues.ErroCues):
        cues.marcar_atualizado(aula, pasta, "narracao.mp3")
