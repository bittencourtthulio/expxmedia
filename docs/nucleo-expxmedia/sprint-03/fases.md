---
expx_schema: 1
expx_tool: sprintx
kind: fases
trabalho_id: nucleo-expxmedia
sprint_id: sprint-03
atualizado_em: 2026-09-24
fases:
  - id: F-03.1
    titulo: "Renderizador HTML"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/render_html termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: true
    paralela_com: [F-03.2]
    tasks: [T-03.01, T-03.02, T-03.03, T-03.04, T-03.05]
  - id: F-03.2
    titulo: "Provedores de imagem"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/imagem termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: true
    paralela_com: [F-03.1]
    tasks: [T-03.06, T-03.07, T-03.08, T-03.14]
  - id: F-03.3
    titulo: "Captura e producao estatica"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/captura tests/producao/test_post.py tests/producao/test_carrossel.py tests/test_templates_embarcados.py tests/test_cli_producao_estatica.py termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-03.09, T-03.10, T-03.11, T-03.12, T-03.13]
---

# Fases — Sprint 03

> O paralelismo declarado aqui é definitivo: a execução nunca decide paralelismo sozinha.

---

## F-03.1 — Renderizador HTML

**Objetivo:** Render sem JS e sem rede, encaixe, contraste no PNG, prancha e paridade.

**Tasks que a compõem:** T-03.01, T-03.02, T-03.03, T-03.04, T-03.05

**Critério de saída:** `cd motor && uv run pytest tests/render_html` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** F-03.2

---

## F-03.2 — Provedores de imagem

**Objetivo:** Pexels, OpenRouter, Higgsfield, retratos e cota.

**Tasks que a compõem:** T-03.06, T-03.07, T-03.08, T-03.14

**Critério de saída:** `cd motor && uv run pytest tests/imagem` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** F-03.1

---

## F-03.3 — Captura e producao estatica

**Objetivo:** Captura de página, templates embarcados e produção de post único e carrossel de imagem.

**Tasks que a compõem:** T-03.09, T-03.10, T-03.11, T-03.12, T-03.13

**Critério de saída:** `cd motor && uv run pytest tests/captura tests/producao/test_post.py tests/producao/test_carrossel.py tests/test_templates_embarcados.py tests/test_cli_producao_estatica.py` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma
