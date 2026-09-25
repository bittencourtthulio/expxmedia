---
expx_schema: 1
expx_tool: sprintx
kind: fases
trabalho_id: nucleo-expxmedia
sprint_id: sprint-08
atualizado_em: 2026-09-24
fases:
  - id: F-08.1
    titulo: "Publicacao"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/publicar termina com 0 failed"
    paralelizavel: false
    paralela_com: []
    tasks: [T-08.01, T-08.02, T-08.03, T-08.04]
  - id: F-08.2
    titulo: "Agendador local"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/agendador termina com 0 failed"
    paralelizavel: false
    paralela_com: []
    tasks: [T-08.05, T-08.06]
  - id: F-08.3
    titulo: "CLI de publicacao"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/test_cli_publicar.py termina com 0 failed"
    paralelizavel: false
    paralela_com: []
    tasks: [T-08.07]
---

# Fases — Sprint 08

> O paralelismo declarado aqui é definitivo: a execução nunca decide paralelismo sozinha.

---

## F-08.1 — Publicacao

**Objetivo:** Base com idempotência, Expx Flow, túnel e Graph.

**Tasks que a compõem:** T-08.01, T-08.02, T-08.03, T-08.04

**Critério de saída:** `cd motor && uv run pytest tests/publicar` termina com 0 failed

**Roda em paralelo com:** nenhuma

---

## F-08.2 — Agendador local

**Objetivo:** Serviço e instalação por sistema operacional.

**Tasks que a compõem:** T-08.05, T-08.06

**Critério de saída:** `cd motor && uv run pytest tests/agendador` termina com 0 failed

**Roda em paralelo com:** nenhuma

---

## F-08.3 — CLI de publicacao

**Objetivo:** Publicar, agendar e agendador pelo CLI.

**Tasks que a compõem:** T-08.07

**Critério de saída:** `cd motor && uv run pytest tests/test_cli_publicar.py` termina com 0 failed

**Roda em paralelo com:** nenhuma
