"""T-04.05: léxico de pronúncia do porta-voz na fala e alinhamento no espaço do roteiro (D-22).

Contra o stub HTTP local (D-15). O stub devolve o alinhamento sobre o texto que o motor mandou
(como a API faz), e o motor precisa devolvê-lo no texto do ROTEIRO.
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

_TESTS = str(Path(__file__).resolve().parents[1])
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from stubs.servidor import servidor_stub  # noqa: E402,F401  (fixture)

from expxmedia.narrar import base, pronuncia  # noqa: E402

pytestmark = pytest.mark.integracao_local

PORTA_VOZ = "porta-voz-teste"
CAMINHO = "/v1/text-to-speech/voz-ficticia-0001/with-timestamps"
ROTEIRO = "Hoje o Claude fez um petit gâteau e um gâteau simples. Comenta CLAUDE aqui."
LEXICO = [
    {"termo": "Claude", "fala": "Clód"},
    {"termo": "gâteau", "fala": "gatô"},
    {"termo": "petit gâteau", "fala": "petí gatô"},
]
FALA = "Hoje o Clód fez um petí gatô e um gatô simples. Comenta CLÓD aqui."


def _alinhamento(texto, passo=0.05):
    return {"characters": list(texto),
            "character_start_times_seconds": [i * passo for i in range(len(texto))],
            "character_end_times_seconds": [(i + 1) * passo for i in range(len(texto))]}


@pytest.fixture(scope="module")
def mp3_bytes(tmp_path_factory):
    destino = tmp_path_factory.mktemp("mp3") / "voz.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=44100:duration=3",
                    "-c:a", "libmp3lame", "-b:a", "128k", str(destino)], check=True, capture_output=True)
    return destino.read_bytes()


@pytest.fixture
def raiz(instalacao, monkeypatch, requer_binario):
    requer_binario("ffmpeg")
    requer_binario("ffprobe")
    monkeypatch.delenv("EXPXMEDIA_PROVEDORES_TESTE", raising=False)
    (instalacao / ".env").write_text("ELEVENLABS_API_KEY=chave-falsa\n", encoding="utf-8")
    caminho = instalacao / "alma" / "alma.json"
    alma = json.loads(caminho.read_text(encoding="utf-8"))
    alma["porta_vozes"][0]["voz"]["pronuncia"] = LEXICO
    caminho.write_text(json.dumps(alma, ensure_ascii=False), encoding="utf-8")
    return instalacao


def _responder(stub, texto_devolvido, mp3):
    stub.rota("POST", CAMINHO, json={"audio_base64": base64.b64encode(mp3).decode("ascii"),
                                     "alignment": _alinhamento(texto_devolvido),
                                     "normalized_alignment": _alinhamento(texto_devolvido)})


# ------------------------------------------------------------------ integração

def test_lexico_vai_na_fala_e_o_alinhamento_volta_no_roteiro(raiz, servidor_stub, mp3_bytes):
    _responder(servidor_stub, FALA, mp3_bytes)

    r = base.narrar(raiz, ROTEIRO, PORTA_VOZ, "aula", "pecas/p1/midia", url_base=servidor_stub.url)

    [req] = servidor_stub.requisicoes
    enviado = req.json["text"]
    assert enviado == FALA
    assert "Clód" in enviado and "CLÓD" in enviado          # caixa alta preservada: é ênfase
    assert "Claude" not in enviado and "CLAUDE" not in enviado

    al = json.loads((raiz / r["arquivo_alinhamento"]).read_text(encoding="utf-8"))
    assert "".join(al["characters"]) == ROTEIRO             # os caracteres de Claude, não de Clód
    assert len(al["character_start_times_seconds"]) == len(ROTEIRO)
    assert not (raiz / "pecas/p1/midia/alignment.raw.json").exists()

    # trecho literal copia o tempo exato do caractere falado
    i_rot = ROTEIRO.index("fez")
    i_fala = FALA.index("fez")
    assert al["character_start_times_seconds"][i_rot] == pytest.approx(i_fala * 0.05)
    # trecho substituído: o intervalo falado de "Clód" é repartido igualmente pelos 6 caracteres de "Claude"
    i_c, j_c = ROTEIRO.index("Claude"), FALA.index("Clód")
    t0, t1 = j_c * 0.05, (j_c + 4) * 0.05
    inis = al["character_start_times_seconds"][i_c:i_c + 6]
    fins = al["character_end_times_seconds"][i_c:i_c + 6]
    assert inis[0] == pytest.approx(t0)
    assert fins[-1] == pytest.approx(t1)
    assert inis == pytest.approx([t0 + (t1 - t0) / 6 * k for k in range(6)])


# ------------------------------------------------------------------ funcional

def test_texto_normalizado_pela_api_grava_raw_e_levanta_sem_nova_chamada(raiz, servidor_stub, mp3_bytes):
    normalizado = FALA.replace("Hoje", "Hoje, dia vinte e cinco,")
    _responder(servidor_stub, normalizado, mp3_bytes)

    with pytest.raises(base.ErroNarrar) as erro:
        base.narrar(raiz, ROTEIRO, PORTA_VOZ, "reel", "pecas/p1/midia", url_base=servidor_stub.url)

    assert erro.value.codigo == "texto_normalizado"
    assert "NÃO chame a API de novo" in str(erro.value)
    assert len(servidor_stub.requisicoes) == 1               # nenhuma nova chamada
    pasta = raiz / "pecas/p1/midia"
    bruto = json.loads((pasta / "alignment.raw.json").read_text(encoding="utf-8"))
    assert "".join(bruto["characters"]) == normalizado
    assert (pasta / "narracao.mp3").read_bytes() == mp3_bytes  # o crédito não se perdeu
    assert not (pasta / "alinhamento.json").exists()          # nada de alinhamento torto


def test_aplicar_casamento_do_lexico():
    fala, segmentos = pronuncia.aplicar(ROTEIRO, LEXICO)
    assert fala == FALA
    # segmentos cobrem os dois textos inteiros, sem buraco nem sobreposição
    assert segmentos[0][0] == 0 and segmentos[-1][1] == len(ROTEIRO)
    assert segmentos[0][2] == 0 and segmentos[-1][3] == len(FALA)
    for a, b in zip(segmentos, segmentos[1:]):
        assert a[1] == b[0] and a[3] == b[2]

    # fronteira de palavra nas duas pontas, sem diferenciar maiúsculas; caixa do roteiro preservada
    assert pronuncia.aplicar("Claudete e claude e Claude.", LEXICO)[0] == "Claudete e Clód e Clód."  # minúscula no roteiro: fala como no léxico (origem)
    # plural é termo próprio
    lex = [{"termo": "harness", "fala": "rárnes"}, {"termo": "harnesses", "fala": "rárneses"}]
    assert pronuncia.aplicar("harness e harnesses", lex)[0] == "rárnes e rárneses"
    # sem léxico, a fala é o roteiro
    assert pronuncia.aplicar(ROTEIRO, [])[0] == ROTEIRO
    # léxico também aceita o dicionário {termo: fala}
    assert pronuncia.aplicar("o Claude", {"Claude": "Clód"})[0] == "o Clód"


def test_remapear_recusa_o_que_nao_reconstroi_o_roteiro():
    fala, segmentos = pronuncia.aplicar(ROTEIRO, LEXICO)
    with pytest.raises(ValueError):
        pronuncia.remapear(_alinhamento(fala), ROTEIRO + "x", fala, segmentos)


def test_termos_multi_para_a_legenda_nao_rachar():
    assert pronuncia.termos_multi(LEXICO) == (("petit", "gâteau"),)
