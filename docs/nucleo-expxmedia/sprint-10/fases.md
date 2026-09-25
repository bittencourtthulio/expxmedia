---
expx_schema: 1
expx_tool: sprintx
kind: fases
trabalho_id: nucleo-expxmedia
sprint_id: sprint-10
atualizado_em: 2026-09-24
fases:
  - id: F-10.1
    titulo: "Ponta a ponta"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/e2e termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-10.01, T-10.02, T-10.03]
  - id: F-10.2
    titulo: "Documentacao e fechamento"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-10.04, T-10.05]
---

# Fases — Sprint 10

> O paralelismo declarado aqui é definitivo: a execução nunca decide paralelismo sozinha.

---

## F-10.1 — Ponta a ponta

**Objetivo:** Cinco tipos, publicação em dry-run e reel por referência guiado.

**Tasks que a compõem:** T-10.01, T-10.02, T-10.03

**Critério de saída:** `cd motor && uv run pytest tests/e2e` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma

---

## F-10.2 — Documentacao e fechamento

**Objetivo:** README do motor e do plugin, contrato atualizado e suíte completa.

**Tasks que a compõem:** T-10.04, T-10.05

**Critério de saída:** `cd motor && uv run pytest` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma
