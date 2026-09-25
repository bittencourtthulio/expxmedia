"""T-02.05: leitor do .env da instalação sem nunca expor valores (M12, M14)."""
import pytest

from expxmedia.ambiente import env

SEGREDO = "sk-valor-secreto-9f8e7d"


def _gravar(raiz, texto):
    (raiz / ".env").write_text(texto, encoding="utf-8")


# ---------- integração: erro com chave presente cita o nome, nunca o valor ----------

def test_erro_de_aspas_sem_fechar_cita_nome_e_nao_o_valor(instalacao):
    _gravar(instalacao, f'ELEVENLABS_API_KEY="{SEGREDO}\n')
    with pytest.raises(env.ErroEnv) as info:
        env.carregar(instalacao)
    erro = info.value
    assert "ELEVENLABS_API_KEY" in str(erro)
    assert SEGREDO not in str(erro)
    assert SEGREDO not in repr(erro)
    assert SEGREDO[:8] not in str(erro)


def test_erro_de_valor_invalido_com_chave_presente_nao_vaza_o_valor(instalacao):
    _gravar(instalacao, f"PORTA_TUNEL={SEGREDO}\nELEVENLABS_API_KEY={SEGREDO}\n")
    ambiente = env.carregar(instalacao)
    with pytest.raises(env.ErroEnv) as info:
        ambiente.inteiro("PORTA_TUNEL")
    assert "PORTA_TUNEL" in str(info.value)
    assert SEGREDO not in str(info.value) and SEGREDO not in repr(info.value)
    # a exceção também não carrega o ValueError original (que traz o valor) na causa/contexto
    assert info.value.__cause__ is None
    assert info.value.__context__ is None or info.value.__suppress_context__


def test_exigir_lista_os_nomes_que_faltam_sem_valores(instalacao):
    _gravar(instalacao, f"ELEVENLABS_API_KEY={SEGREDO}\nHEYGEN_API_KEY=\n")
    ambiente = env.carregar(instalacao)
    with pytest.raises(env.ErroEnv) as info:
        ambiente.exigir("ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "PEXELS_API_KEY")
    mensagem = str(info.value)
    assert "HEYGEN_API_KEY" in mensagem and "PEXELS_API_KEY" in mensagem
    assert "ELEVENLABS_API_KEY" not in mensagem  # presente não é citado como falta
    assert SEGREDO not in mensagem
    assert ambiente.exigir("ELEVENLABS_API_KEY") == {"ELEVENLABS_API_KEY": SEGREDO}


def test_repr_e_str_do_ambiente_mascaram_valores(instalacao):
    _gravar(instalacao, f"ELEVENLABS_API_KEY={SEGREDO}\n")
    ambiente = env.carregar(instalacao)
    for texto in (repr(ambiente), str(ambiente), f"{ambiente}"):
        assert "ELEVENLABS_API_KEY" in texto
        assert SEGREDO not in texto


def test_linha_sem_igual_cita_so_o_numero_da_linha(instalacao):
    _gravar(instalacao, f"# comentário\n{SEGREDO}\n")
    with pytest.raises(env.ErroEnv) as info:
        env.carregar(instalacao)
    assert "linha 2" in str(info.value)
    assert SEGREDO not in str(info.value) and SEGREDO not in repr(info.value)


# ---------- funcional: comentário, aspas e linha vazia ----------

def test_env_com_comentario_aspas_e_linha_vazia(instalacao):
    _gravar(
        instalacao,
        "# narrar\n"
        "ELEVENLABS_API_KEY=abc123\n"
        "\n"
        '   HEYGEN_API_KEY = "com espaco e # cerquilha"  \n'
        "# comentário no meio\n"
        "export PEXELS_API_KEY='simples'\n",
    )
    assert dict(env.carregar(instalacao)) == {
        "ELEVENLABS_API_KEY": "abc123",
        "HEYGEN_API_KEY": "com espaco e # cerquilha",
        "PEXELS_API_KEY": "simples",
    }


def test_detalhes_do_formato():
    lido = env.interpretar(
        "﻿A=1 # comentário de fim de linha\n"
        "B=\n"
        "C=valor=com=igual\n"
        'D="linha\\nquebrada"\n'
        "A=2\n"
    )
    assert lido == {"A": "2", "B": "", "C": "valor=com=igual", "D": "linha\nquebrada"}


def test_preenchida_distingue_vazia_de_ausente(instalacao):
    _gravar(instalacao, "ELEVENLABS_API_KEY=abc\nHEYGEN_API_KEY=\nPEXELS_API_KEY=   \n")
    ambiente = env.carregar(instalacao)
    assert ambiente.preenchida("ELEVENLABS_API_KEY")
    assert not ambiente.preenchida("HEYGEN_API_KEY")
    assert not ambiente.preenchida("PEXELS_API_KEY")
    assert not ambiente.preenchida("OPENROUTER_API_KEY")
    assert "HEYGEN_API_KEY" in ambiente and "OPENROUTER_API_KEY" not in ambiente


def test_env_ausente_e_ambiente_vazio(tmp_path):
    assert dict(env.carregar(tmp_path)) == {}


def test_nome_de_variavel_invalido_e_recusado():
    with pytest.raises(env.ErroEnv, match="linha 1"):
        env.interpretar("1CHAVE=x\n")
