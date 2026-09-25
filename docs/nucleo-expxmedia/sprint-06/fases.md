---
expx_schema: 1
expx_tool: sprintx
kind: fases
trabalho_id: nucleo-expxmedia
sprint_id: sprint-06
atualizado_em: 2026-09-24
fases:
  - id: F-06.1
    titulo: "Reel por referencia"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/referencia termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: true
    paralela_com: [F-06.2, F-06.3]
    tasks: [T-06.01, T-06.02, T-06.03]
  - id: F-06.2
    titulo: "Corte de video longo"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/corte termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: true
    paralela_com: [F-06.1, F-06.3]
    tasks: [T-06.04, T-06.05, T-06.06, T-06.07]
  - id: F-06.3
    titulo: "Abertura gerada"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/producao/test_abertura.py termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: true
    paralela_com: [F-06.1, F-06.2]
    tasks: [T-06.08]
  - id: F-06.4
    titulo: "CLI de referencia e corte"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/test_cli_referencia_corte.py termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-06.09]
---

# Fases — Sprint 06

> O paralelismo declarado aqui é definitivo: a execução nunca decide paralelismo sozinha.

---

## F-06.1 — Reel por referencia

**Objetivo:** Análise, pasta sob medida, montagem, prévia, render e verificação.

**Tasks que a compõem:** T-06.01, T-06.02, T-06.03

**Critério de saída:** `cd motor && uv run pytest tests/referencia` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** F-06.2, F-06.3

---

## F-06.2 — Corte de video longo

**Objetivo:** Momentos, corte com reenquadramento, b-roll e produção.

**Tasks que a compõem:** T-06.04, T-06.05, T-06.06, T-06.07

**Critério de saída:** `cd motor && uv run pytest tests/corte` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** F-06.1, F-06.3

---

## F-06.3 — Abertura gerada

**Objetivo:** Abertura com video_ia.

**Tasks que a compõem:** T-06.08

**Critério de saída:** `cd motor && uv run pytest tests/producao/test_abertura.py` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** F-06.1, F-06.2

---

## F-06.4 — CLI de referencia e corte

**Objetivo:** Subcomandos de referência, corte e abertura.

**Tasks que a compõem:** T-06.09

**Critério de saída:** `cd motor && uv run pytest tests/test_cli_referencia_corte.py` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma
