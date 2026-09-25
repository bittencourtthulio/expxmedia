"""T-10.03: o reel por referência produzido seguindo a skill, conferido mecanicamente (D-04, D-18, D-36).

A produção foi feita uma vez, pela skill `reel-por-referencia`, numa instalação persistente em
docs/nucleo-expxmedia/validacao/reel-por-referencia/ (Alma fictícia, provedores de teste). O MP4, os
intermediários e os quadros e folhas extraídos da referência (de terceiro) ficam fora do git: este teste lê
do disco local desta máquina e FALHA (não pula) se a produção não estiver lá.

Integração: `expxmedia-motor verificar --perfil sob_medida` no MP4 sai com 0 e aprovado, e o validador de
código no modo sob_medida não devolve achado sobre o reel sob medida.

Funcional: leitura.md tem as 9 seções não vazias; há de 1 a 3 prévias gravadas; cada item (1 a 11) do
checklist de parecença em reel-por-referencia.md cita um caminho de quadro que existe; o sha256 registrado é o
do MP4.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from expxmedia.producao import reel_referencia
from expxmedia.template import validar

MOTOR = Path(__file__).resolve().parents[2]
VALIDACAO = MOTOR.parent / "docs" / "nucleo-expxmedia" / "validacao"
RAIZ = VALIDACAO / "reel-por-referencia"
REGISTRO = VALIDACAO / "reel-por-referencia.md"
REEL = RAIZ / "referencias" / "ref-validacao"

SECOES = ("Ideia em uma frase", "Tela fixa", "Legenda", "Personagem ou elemento-guia", "Cena a cena", "Ritmo", "Som",
          "Fecho", "O que não vai")
ITENS_CHECKLIST = 11


def _mp4() -> Path:
    peca_id = json.loads((REEL / "referencia.json").read_text(encoding="utf-8"))["peca_id"]
    assert peca_id, "o reel não tem peça registrada: rode a skill até o render"
    achados = list((RAIZ / "pecas").glob(f"*/{peca_id}-*/saida/final.mp4"))
    assert len(achados) == 1, f"MP4 da peça {peca_id} não encontrado em {RAIZ / 'pecas'}"
    return achados[0]


def _secao(texto: str, titulo: str) -> str:
    m = re.search(rf"^## {re.escape(titulo)}\s*$(.*?)(?=^## |\Z)", texto, flags=re.M | re.S)
    assert m, f"falta a seção '{titulo}'"
    return m.group(1)


# ------------------------------------------------------------------ integração


@pytest.mark.integracao_local
def test_verificar_sob_medida_sai_0_e_codigo_sem_achado(requer_binario):
    for b in ("ffmpeg", "ffprobe", "uv"):
        requer_binario(b)
    mp4 = _mp4()
    pasta = mp4.parent.parent
    r = subprocess.run(
        ["uv", "run", "--project", str(MOTOR), "expxmedia-motor", "verificar", "--perfil", "sob_medida", str(mp4),
         "--alinhamento", str(pasta / "midia" / "alinhamento.json"), "--roteiro", str(pasta / "texto" / "roteiro.txt"),
         "--legenda-post", str(pasta / "texto" / "legenda.txt"), "--raiz", str(RAIZ)],
        capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    saida = json.loads(r.stdout)
    assert saida["perfil"] == "sob_medida" and saida["aprovado"] is True and saida["achados"] == []

    # a saída gravada para o revisor é a mesma verificação
    gravada = json.loads((REEL / "revisao" / "verificacao.json").read_text(encoding="utf-8"))
    assert gravada["perfil"] == "sob_medida" and gravada["aprovado"] is True

    # validador de código, modo sob_medida, sem achado (e o reel é código próprio, não o esqueleto do kit)
    assert validar.validar_template(REEL / "reel", modo="sob_medida") == []
    assert reel_referencia.validar_codigo(REEL) == []
    cenas_tsx = (REEL / "reel" / "src" / "cenas.tsx").read_text(encoding="utf-8")
    assert "Rascunho" not in cenas_tsx
    cenas = json.loads((REEL / "reel" / "cenas.json").read_text(encoding="utf-8"))
    assert cenas["apresentador"] is True and set(c["id"] for c in cenas["cenas"]) <= set(re.findall(r"^  (\w+): \w+,$", cenas_tsx, re.M))


# ------------------------------------------------------------------ funcional


def test_leitura_tem_as_9_secoes_nao_vazias():
    texto = (REEL / "analise" / "leitura.md").read_text(encoding="utf-8")
    for n, titulo in enumerate(SECOES, 1):
        corpo = re.sub(r"<!--.*?-->", "", _secao(texto, f"{n}. {titulo}"), flags=re.S).strip()
        assert len(corpo) >= 40, f"seção {n} ({titulo}) vazia ou só com o lembrete do esqueleto"


def test_previas_gravadas_entre_1_e_3():
    voltas = sorted(p for p in (REEL / "previa").glob("[0-9][0-9]") if p.is_dir())
    assert 1 <= len(voltas) <= 3, [p.name for p in voltas]
    assert [p.name for p in voltas] == [f"{i:02d}" for i in range(1, len(voltas) + 1)]
    for volta in voltas:
        assert (volta / "previa.jpg").is_file(), volta
    # o registro conta as mesmas voltas
    registro = REGISTRO.read_text(encoding="utf-8")
    for volta in voltas:
        assert f"previa/{volta.name}/previa.jpg" in registro


def test_checklist_cita_quadro_existente_em_cada_item():
    registro = REGISTRO.read_text(encoding="utf-8")
    checklist = _secao(registro, "Checklist de parecença")
    itens = {int(m.group(1)): m.group(2) for m in re.finditer(r"^(\d+)\. (.+)$", checklist, flags=re.M)}
    assert sorted(itens) == list(range(1, ITENS_CHECKLIST + 1)), sorted(itens)
    for n, linha in itens.items():
        caminhos = re.findall(r"`([^`]+\.(?:jpg|png))`", linha)
        assert caminhos, f"item {n} do checklist não cita caminho de quadro"
        for c in caminhos:
            assert not Path(c).is_absolute() and ".." not in Path(c).parts, f"item {n}: caminho não relativo: {c}"
            assert (RAIZ / c).is_file(), f"item {n}: quadro citado não existe: {c}"
    veredito = _secao(registro, "Veredito")
    assert "APROVADO" in veredito and "REPROVADO" not in veredito


def test_sha256_registrado_e_o_do_mp4():
    registro = REGISTRO.read_text(encoding="utf-8")
    m = re.search(r"sha256[^`]*`([0-9a-f]{64})`", registro)
    assert m, "o registro não traz o sha256 do MP4"
    assert hashlib.sha256(_mp4().read_bytes()).hexdigest() == m.group(1)
