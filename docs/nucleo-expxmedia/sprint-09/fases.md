---
expx_schema: 1
expx_tool: sprintx
kind: fases
trabalho_id: nucleo-expxmedia
sprint_id: sprint-09
atualizado_em: 2026-09-25
fases:
  - id: F-09.1
    titulo: "Manifesto, hooks, Alma, ambiente e revisao de copy"
    status: concluido
    criterio_saida: "cd motor && uv run pytest tests/plugin/test_hooks.py tests/alma/test_site.py tests/test_revisar_copy.py tests/plugin/test_ancoras.py tests/plugin/test_estrutura.py termina com 0 failed"
    paralelizavel: false
    paralela_com: []
    tasks: [T-09.01, T-09.10, T-09.11, T-09.02, T-09.03]
  - id: F-09.2
    titulo: "Skills de producao e agentes"
    status: concluido
    criterio_saida: "cd motor && uv run pytest tests/plugin termina com 0 failed"
    paralelizavel: false
    paralela_com: []
    tasks: [T-09.04, T-09.05, T-09.06, T-09.07, T-09.08]
---

# Fases — Sprint 09

> O paralelismo declarado aqui é definitivo: a execução nunca decide paralelismo sozinha.

---

## F-09.1 — Manifesto, hooks, Alma, ambiente e revisao de copy

**Objetivo:** Plugin validado, portão, segredo, extração de site, revisão mecânica de copy, âncoras de inteligência e skills de Alma e ambiente.

**Tasks que a compõem:** T-09.01, T-09.10, T-09.11, T-09.02, T-09.03

**Critério de saída:** `cd motor && uv run pytest tests/plugin/test_hooks.py tests/alma/test_site.py tests/test_revisar_copy.py tests/plugin/test_ancoras.py tests/plugin/test_estrutura.py` termina com 0 failed

**Roda em paralelo com:** nenhuma

---

## F-09.2 — Skills de producao e agentes

**Objetivo:** Skills e agentes de post, carrossel, reel, referência, corte, apresentação, aula e publicação.

**Tasks que a compõem:** T-09.04, T-09.05, T-09.06, T-09.07, T-09.08

**Critério de saída:** `cd motor && uv run pytest tests/plugin` termina com 0 failed

**Roda em paralelo com:** nenhuma
