---
expx_schema: 1
expx_tool: sprintx
kind: fases
trabalho_id: nucleo-expxmedia
sprint_id: sprint-05
atualizado_em: 2026-09-25
fases:
  - id: F-05.1
    titulo: "Kit e runner"
    status: concluido
    criterio_saida: "cd motor && uv run pytest tests/motion termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-05.01, T-05.02, T-05.03, T-05.04]
  - id: F-05.2
    titulo: "Reel narrado"
    status: concluido
    criterio_saida: "cd motor && uv run pytest tests/producao/test_reel.py termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: true
    paralela_com: [F-05.3, F-05.4]
    tasks: [T-05.05, T-05.06]
  - id: F-05.3
    titulo: "Carrossel misto"
    status: concluido
    criterio_saida: "cd motor && uv run pytest tests/producao/test_carrossel_misto.py termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: true
    paralela_com: [F-05.2, F-05.4]
    tasks: [T-05.07]
  - id: F-05.4
    titulo: "Apresentacao"
    status: concluido
    criterio_saida: "cd motor && uv run pytest tests/producao/apresentacao termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: true
    paralela_com: [F-05.2, F-05.3]
    tasks: [T-05.08, T-05.09, T-05.10, T-05.11]
  - id: F-05.5
    titulo: "CLI de motion"
    status: concluido
    criterio_saida: "cd motor && uv run pytest tests/test_cli_motion.py termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-05.12]
---

# Fases — Sprint 05

> O paralelismo declarado aqui é definitivo: a execução nunca decide paralelismo sozinha.

---

## F-05.1 — Kit e runner

**Objetivo:** Kit base, montagem e trilha generalizadas, runner multi-versão e prévia com guias.

**Tasks que a compõem:** T-05.01, T-05.02, T-05.03, T-05.04

**Critério de saída:** `cd motor && uv run pytest tests/motion` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma

---

## F-05.2 — Reel narrado

**Objetivo:** Template de reel e produção de reel narrado.

**Tasks que a compõem:** T-05.05, T-05.06

**Critério de saída:** `cd motor && uv run pytest tests/producao/test_reel.py` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** F-05.3, F-05.4

---

## F-05.3 — Carrossel misto

**Objetivo:** Slide de vídeo no carrossel.

**Tasks que a compõem:** T-05.07

**Critério de saída:** `cd motor && uv run pytest tests/producao/test_carrossel_misto.py` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** F-05.2, F-05.4

---

## F-05.4 — Apresentacao

**Objetivo:** Deck, palco HTML navegável, cenas e template.

**Tasks que a compõem:** T-05.08, T-05.09, T-05.10, T-05.11

**Critério de saída:** `cd motor && uv run pytest tests/producao/apresentacao` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** F-05.2, F-05.3

---

## F-05.5 — CLI de motion

**Objetivo:** Subcomandos de reel, apresentação, prévia e render.

**Tasks que a compõem:** T-05.12

**Critério de saída:** `cd motor && uv run pytest tests/test_cli_motion.py` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma
