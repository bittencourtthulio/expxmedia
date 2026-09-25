---
expx_schema: 1
expx_tool: sprintx
kind: fases
trabalho_id: nucleo-expxmedia
sprint_id: sprint-07
atualizado_em: 2026-09-24
fases:
  - id: F-07.1
    titulo: "Cues, avatar e tela"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/aula/test_cues.py tests/avatar tests/aula/test_editar_tela.py termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-07.01, T-07.02, T-07.03]
  - id: F-07.2
    titulo: "Composicao e producao"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/aula tests/test_cli_aula.py termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-07.04, T-07.05, T-07.06, T-07.07]
---

# Fases — Sprint 07

> O paralelismo declarado aqui é definitivo: a execução nunca decide paralelismo sozinha.

---

## F-07.1 — Cues, avatar e tela

**Objetivo:** Cues do roteiro, avatar e edição da gravação de tela.

**Tasks que a compõem:** T-07.01, T-07.02, T-07.03

**Critério de saída:** `cd motor && uv run pytest tests/aula/test_cues.py tests/avatar tests/aula/test_editar_tela.py` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma

---

## F-07.2 — Composicao e producao

**Objetivo:** Composição L16 e L9, produção, template, compilação e CLI.

**Tasks que a compõem:** T-07.04, T-07.05, T-07.06, T-07.07

**Critério de saída:** `cd motor && uv run pytest tests/aula tests/test_cli_aula.py` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma
