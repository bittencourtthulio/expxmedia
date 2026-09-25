---
expx_schema: 1
expx_tool: sprintx
kind: fases
trabalho_id: nucleo-expxmedia
sprint_id: sprint-01
atualizado_em: 2026-09-24
fases:
  - id: F-01.1
    titulo: "Projeto Python e harness"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/test_pacote.py tests/test_harness.py tests/test_instalacao.py tests/test_stub.py termina com 0 failed"
    paralelizavel: false
    paralela_com: []
    tasks: [T-01.01, T-01.02, T-01.03, T-01.04]
  - id: F-01.2
    titulo: "Ambiente, kit Remotion, varredura de marca e goldens"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/test_ambiente_local.py tests/test_kit_remotion.py tests/test_marca.py tests/test_golden_presentes.py termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-01.05, T-01.06, T-01.08, T-01.07]
---

# Fases — Sprint 01

> O paralelismo declarado aqui é definitivo: a execução nunca decide paralelismo sozinha.

---

## F-01.1 — Projeto Python e harness

**Objetivo:** Criar o pacote, o conftest, a fixture de instalação e o stub HTTP.

**Tasks que a compõem:** T-01.01, T-01.02, T-01.03, T-01.04

**Critério de saída:** `cd motor && uv run pytest tests/test_pacote.py tests/test_harness.py tests/test_instalacao.py tests/test_stub.py` termina com 0 failed

**Roda em paralelo com:** nenhuma

---

## F-01.2 — Ambiente, kit Remotion, varredura de marca e goldens

**Objetivo:** Preparar os binários e caches, instalar o kit com versões travadas, criar a varredura de marca e gravar os goldens.

**Tasks que a compõem:** T-01.05, T-01.06, T-01.08, T-01.07

**Critério de saída:** `cd motor && uv run pytest tests/test_ambiente_local.py tests/test_kit_remotion.py tests/test_marca.py tests/test_golden_presentes.py` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma
