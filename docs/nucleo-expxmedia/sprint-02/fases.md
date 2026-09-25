---
expx_schema: 1
expx_tool: sprintx
kind: fases
trabalho_id: nucleo-expxmedia
sprint_id: sprint-02
atualizado_em: 2026-09-24
fases:
  - id: F-02.1
    titulo: "Arquivos, ids e rastro"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/nucleo termina com 0 failed"
    paralelizavel: false
    paralela_com: []
    tasks: [T-02.01, T-02.02, T-02.03, T-02.04]
  - id: F-02.2
    titulo: "Ambiente e capacidades"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/ambiente termina com 0 failed"
    paralelizavel: true
    paralela_com: [F-02.3]
    tasks: [T-02.05, T-02.06, T-02.07, T-02.08]
  - id: F-02.3
    titulo: "Alma, peca e template"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/alma tests/peca tests/template/test_validar.py termina com 0 failed"
    paralelizavel: true
    paralela_com: [F-02.2]
    tasks: [T-02.09, T-02.10, T-02.11, T-02.12]
  - id: F-02.4
    titulo: "Galeria local e CLI base"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/template/test_galeria_local.py tests/test_cli.py termina com 0 failed"
    paralelizavel: false
    paralela_com: []
    tasks: [T-02.13, T-02.14]
---

# Fases — Sprint 02

> O paralelismo declarado aqui é definitivo: a execução nunca decide paralelismo sozinha.

---

## F-02.1 — Arquivos, ids e rastro

**Objetivo:** Ids, tempo com fuso, escrita atômica, JSONL com trava, rastro e raiz da instalação.

**Tasks que a compõem:** T-02.01, T-02.02, T-02.03, T-02.04

**Critério de saída:** `cd motor && uv run pytest tests/nucleo` termina com 0 failed

**Roda em paralelo com:** nenhuma

---

## F-02.2 — Ambiente e capacidades

**Objetivo:** Leitor do .env, catálogo, verificação com como_habilitar e .env.example.

**Tasks que a compõem:** T-02.05, T-02.06, T-02.07, T-02.08

**Critério de saída:** `cd motor && uv run pytest tests/ambiente` termina com 0 failed

**Roda em paralelo com:** F-02.3

---

## F-02.3 — Alma, peca e template

**Objetivo:** Schema e carga da Alma, tokens e fontes, modelo de peça e validação de template.

**Tasks que a compõem:** T-02.09, T-02.10, T-02.11, T-02.12

**Critério de saída:** `cd motor && uv run pytest tests/alma tests/peca tests/template/test_validar.py` termina com 0 failed

**Roda em paralelo com:** F-02.2

---

## F-02.4 — Galeria local e CLI base

**Objetivo:** Busca na galeria local por requisitos e o CLI expxmedia-motor com saída JSON.

**Tasks que a compõem:** T-02.13, T-02.14

**Critério de saída:** `cd motor && uv run pytest tests/template/test_galeria_local.py tests/test_cli.py` termina com 0 failed

**Roda em paralelo com:** nenhuma
