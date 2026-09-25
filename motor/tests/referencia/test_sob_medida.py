"""T-06.02: pasta do reel sob medida e validação do cenas.json (D-18, D-19, D-36).

Integração: criar um reel sob medida gera o `cenas.json` esqueleto e o `Reel.tsx` (com `cenas.tsx`) a partir
do kit, que compila com o kit no `tsc` e passa no validador de código no modo sob_medida, sem nada do visual
do exemplo aprovado.

Funcional: um `cenas.json` com a trilha igual à de outro reel da instalação (outro reel por referência ou
uma peça de reel) é recusado com a mensagem de trilha repetida; âncora fora de ordem, som que cita evento
inexistente, efeito e instrumento desconhecidos também são recusados, citando a cena.
"""
from __future__ import annotations

import json
import subprocess

import pytest

from expxmedia.motion import remotion
from expxmedia.nucleo import arquivos
from expxmedia.referencia import sob_medida
from expxmedia.template import validar

ROTEIRO = ("Todo mundo acha que precisa de mais tempo. Na verdade falta um jeito de decidir. "
           "Primeiro você lista o que importa. Depois corta o resto sem dó. Salve para lembrar amanhã.")

TRILHA = {"bpm": 112, "acordes": [[98, [392, 493.88, 587.33]], [110, [440, 523.25, 659.25]]],
          "instrumentos": {"kick": 0.3, "palma": 0.08, "chimbal": 0.03, "pluck": 0.02, "pad": 0.03, "baixo": 0.2},
          "arpejo": [0, 1, 2, 1], "ganho": 0.55, "semente": 11}


def _cenas(**muda):
    dados = {
        "trilha": json.loads(json.dumps(TRILHA)),
        "troca": [{"f": -3, "tipo": "whoosh", "desde": 1, "vol": 0.6}],
        "legenda": {"palavras_por_bloco": 3},
        "cauda_s": 1.4,
        "apresentador": False,
        "cenas": [
            {"id": "tempo", "ancora": "Todo mundo acha", "ev": {"relogio": 0.3}, "sons": [["relogio", "tick"]]},
            {"id": "decidir", "ancora": "Na verdade falta", "ev": {"balanca": 0.4, "pesa": 0.7},
             "sons": [["balanca", "pop"], ["balanca+pesa", "impacto", 0.2, 0.8]]},
            {"id": "lista", "ancora": "Primeiro você lista", "ev": {}, "sons": [["0", "digita", 0.5]]},
            {"id": "corta", "ancora": "Depois corta", "ev": {"tesoura": 0.5}, "sons": [["tesoura", "snip"]]},
            {"id": "fecho", "ancora": "Salve para lembrar", "ev": {"pede": 0.2}, "sons": []},
        ],
    }
    dados.update(muda)
    return dados


def _gravar(pasta, dados):
    arquivos.gravar_json(pasta / "reel" / "cenas.json", dados)


@pytest.fixture
def criado(instalacao):
    r = sob_medida.criar(instalacao, "decidir-rapido", titulo="Decidir rápido", origem_url="https://exemplo.invalid/r/1")
    pasta = instalacao / r["pasta"]
    (pasta / "roteiro.txt").write_text(ROTEIRO + "\n", encoding="utf-8")
    return instalacao, pasta


# ------------------------------------------------------------------ integração


@pytest.mark.integracao_local
def test_criar_gera_cenas_esqueleto_e_reel_que_compila_com_o_kit(instalacao, tmp_path, requer_binario):
    node = requer_binario("node")
    r = sob_medida.criar(instalacao, "decidir-rapido", titulo="Decidir rápido", origem_url="https://exemplo.invalid/r/1")
    assert r["pasta"] == "referencias/decidir-rapido"  # relativo à raiz (M9)
    pasta = instalacao / r["pasta"]
    reel_dir = pasta / "reel"
    for nome in ("cenas.json", "package.json", "src/Reel.tsx", "src/cenas.tsx"):
        assert (reel_dir / nome).is_file(), nome

    esqueleto = arquivos.ler_json(reel_dir / "cenas.json")
    assert set(esqueleto) == {"trilha", "troca", "legenda", "cauda_s", "apresentador", "cenas"}
    assert esqueleto["cenas"] == [] and esqueleto["trilha"]["bpm"] is None and esqueleto["trilha"]["acordes"] == []
    assert esqueleto["cauda_s"] == 1.4 and esqueleto["legenda"] == {"palavras_por_bloco": 3}
    # o esqueleto não passa na validação: a trilha e as cenas são do modelo, a partir da leitura
    erros = sob_medida.validar_cenas(instalacao, pasta)
    assert any("trilha.bpm" in e for e in erros) and any("cenas" in e for e in erros)

    marcador = arquivos.ler_json(pasta / "referencia.json")
    assert marcador["slug"] == "decidir-rapido" and marcador["origem_url"] == "https://exemplo.invalid/r/1"
    assert marcador["analise"] == "analise/formato.json" and marcador["peca_id"] is None
    pacote = arquivos.ler_json(reel_dir / "package.json")
    assert pacote["dependencies"]["remotion"] == remotion.VERSAO_KIT

    # no padrão estrutural do exemplo aprovado (Sequence por cena com sobreposição, ev da cena, legenda por
    # blocos, selo dentro do bloco centrado na área segura, trilha a 0.8), sem nada do visual dele
    codigo = (reel_dir / "src" / "Reel.tsx").read_text(encoding="utf-8") + (reel_dir / "src" / "cenas.tsx").read_text(encoding="utf-8")
    for estrutura in ("centralizarNaArea(", "<Sequence", "SeloPerfil", "ProvedorAlma", "TRANS = 12", "VOLUME_TRILHA = 0.8",
                      "export const CENAS", "export const FUNDOS", "ev: (nome: string) => number", "blocos"):
        assert estrutura in codigo, estrutura
    for do_exemplo in ("Mascote", "Progresso", "Etiqueta", "CARD", "ferrugem", "circle(", "Rockwell", "Georgia",
                       "#EFE8DA", "ia-decide", "staticFile("):
        assert do_exemplo not in codigo, do_exemplo
    assert validar.validar_template(reel_dir, modo="sob_medida") == []

    projeto = sob_medida.preparar_projeto(pasta, tmp_path / "projeto", "Reel-decidir-rapido")
    comp = projeto / "src" / "composicoes" / "Reel-decidir-rapido"
    assert '"./Reel"' in (comp / "index.tsx").read_text(encoding="utf-8")
    tsc = remotion.KIT / "node_modules" / "typescript" / "bin" / "tsc"
    r = subprocess.run([node, str(tsc), "-p", str(projeto / "tsconfig.json")], capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]

    # criar de novo não sobrescreve o código do modelo
    with pytest.raises(sob_medida.ErroSobMedida, match="já existe"):
        sob_medida.criar(instalacao, "decidir-rapido")


# ------------------------------------------------------------------ funcional


@pytest.mark.integracao_local
def test_trilha_igual_a_de_outro_reel_da_instalacao_e_recusada(criado, requer_binario):
    requer_binario("node")
    raiz, pasta = criado
    _gravar(pasta, _cenas())
    assert sob_medida.validar_cenas(raiz, pasta) == []

    # outro reel por referência da instalação, com a mesma trilha (volume, arpejo e semente não contam)
    outro = sob_medida.criar(raiz, "outro-reel")
    mesma = {**json.loads(json.dumps(TRILHA)), "semente": 3, "arpejo": [0, 2], "ganho": 0.4}
    mesma["instrumentos"] = {k: v * 2 for k, v in TRILHA["instrumentos"].items()}
    arquivos.gravar_json(raiz / outro["pasta"] / "reel" / "cenas.json", {**_cenas(), "trilha": mesma})
    erros = sob_medida.validar_cenas(raiz, pasta)
    assert erros == ["a trilha é a mesma do reel outro-reel (bpm, acordes e instrumentos). "
                     "Cada reel tem a sua: mude andamento, harmonia ou timbre."]
    with pytest.raises(sob_medida.ErroSobMedida, match="Cada reel tem a sua"):
        sob_medida.conferir_cenas(raiz, pasta)

    # mudar o andamento resolve; 112 e 112.0 são o mesmo número (a assinatura é a do montar.mjs)
    _gravar(pasta, _cenas(trilha={**TRILHA, "bpm": 118}))
    assert sob_medida.validar_cenas(raiz, pasta) == []
    _gravar(pasta, _cenas(trilha={**TRILHA, "bpm": 112.0}))
    assert "outro-reel" in sob_medida.validar_cenas(raiz, pasta)[0]

    # uma peça de reel da instalação (midia/cenas.json) também conta
    (raiz / outro["pasta"] / "reel" / "cenas.json").unlink()
    peca = raiz / "pecas" / "2026-09" / "P-20260925-ABCD-um-reel" / "midia"
    arquivos.gravar_json(peca / "cenas.json", {"trilha": TRILHA, "cenas": []})
    erros = sob_medida.validar_cenas(raiz, pasta)
    assert len(erros) == 1 and "P-20260925-ABCD-um-reel" in erros[0] and "Cada reel tem a sua" in erros[0]
    # a peça deste mesmo reel (a do marcador) não conta como outro reel
    marcador = arquivos.ler_json(pasta / "referencia.json")
    arquivos.gravar_json(pasta / "referencia.json", {**marcador, "peca_id": "P-20260925-ABCD"})
    assert sob_medida.validar_cenas(raiz, pasta) == []


@pytest.mark.integracao_local
def test_ancoras_eventos_efeitos_e_instrumentos(criado, requer_binario):
    requer_binario("node")
    raiz, pasta = criado
    efeitos = sob_medida.efeitos_disponiveis()
    assert len(efeitos) == 20 and {"whoosh", "pop", "tick", "snip", "impacto"} <= set(efeitos)

    fora_de_ordem = _cenas()
    fora_de_ordem["cenas"][1]["ancora"], fora_de_ordem["cenas"][2]["ancora"] = "Primeiro você lista", "Na verdade falta"
    _gravar(pasta, fora_de_ordem)
    erros = sob_medida.validar_cenas(raiz, pasta)
    assert erros == ['cena 3 (lista): âncora "Na verdade falta" não casou com o roteiro, em ordem']

    ausente = _cenas()
    ausente["cenas"][0]["ancora"] = "frase que não existe"
    _gravar(pasta, ausente)
    assert sob_medida.validar_cenas(raiz, pasta)[0].startswith('cena 1 (tempo): âncora "frase que não existe"')

    evento = _cenas()
    evento["cenas"][1]["sons"][1][0] = "balanca+sobe"
    evento["cenas"][4]["ev"] = {"pede": 1.4}
    _gravar(pasta, evento)
    assert sob_medida.validar_cenas(raiz, pasta) == [
        'cena 2 (decidir): som cita o evento "sobe", que não está em ev',
        'cena 5 (fecho): evento "pede" = 1.4 fora de 0 a 1 (fração da duração da cena)',
    ]

    efeito = _cenas()
    efeito["cenas"][3]["sons"][0][1] = "explosao"
    efeito["troca"][0]["tipo"] = "chiado"
    efeito["trilha"]["instrumentos"]["guitarra"] = 0.2
    efeito["cenas"].append({**efeito["cenas"][0]})
    _gravar(pasta, efeito)
    erros = sob_medida.validar_cenas(raiz, pasta)
    assert "trilha: instrumento desconhecido: guitarra (existem: kick, caixa, palma, chimbal, pluck, sino, pad, baixo)" in erros
    assert any(e.startswith("troca 1: efeito desconhecido: chiado") for e in erros)
    assert any(e.startswith("cena 4 (corta): efeito desconhecido: explosao") for e in erros)
    assert "ids de cena repetidos: tempo" in erros

    (pasta / "roteiro.txt").unlink()
    _gravar(pasta, _cenas())
    assert sob_medida.validar_cenas(raiz, pasta) == ["falta roteiro.txt: as âncoras são conferidas contra o roteiro"]


def test_numeros_do_esqueleto_e_da_assinatura():
    # origem: Instragram-Videos/remotion/scripts/montar-reel.mjs:94 (cauda 1.4), :106 (3 palavras por bloco),
    # :128 (troca padrão) e Instragram-Videos/remotion/scripts/audio.mjs:218,246-247 (arpejo, fade, ganho)
    e = sob_medida.esqueleto_cenas()
    assert e["cauda_s"] == 1.4 and e["legenda"]["palavras_por_bloco"] == 3
    assert e["troca"] == [{"f": -3, "tipo": "whoosh", "desde": 1}, {"f": 5, "tipo": "pop", "desde": 0}]
    assert e["trilha"]["arpejo"] == [0, 1, 2, 1, 2, 0, 1, 2] and e["trilha"]["ganho"] == 0.55
    assert e["trilha"]["fade_s"] == 1.6 and e["trilha"]["semente"] == 7
    a = sob_medida.assinatura({"bpm": 100, "acordes": [[110, [440]]], "instrumentos": {"pad": 1, "kick": 0.2}})
    b = sob_medida.assinatura({"bpm": 100.0, "acordes": [[110.0, [440.0]]], "instrumentos": {"kick": 0.9, "pad": 0}})
    assert a == b and a != sob_medida.assinatura({"bpm": 101, "acordes": [[110, [440]]], "instrumentos": {"pad": 1, "kick": 1}})
