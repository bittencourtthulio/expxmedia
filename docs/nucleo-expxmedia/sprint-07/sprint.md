---
expx_schema: 1
expx_tool: sprintx
kind: sprint
trabalho_id: nucleo-expxmedia
sprint_id: sprint-07
titulo: "Aula e avatar"
status: nao_iniciado
criterio_saida: "cd motor && uv run pytest tests/aula tests/avatar tests/test_cli_aula.py termina com 0 failed e 0 skipped nesta maquina"
fases: [F-07.1, F-07.2]
riscos: ["Regerar a narracao invalida cues, avatar e legenda (base/aula-pipeline.md)", "Documentacao do HeyGen se contradiz em limites (base/api-heygen.md)"]
atualizado_em: 2026-09-24
---

# Sprint 07 — Aula e avatar

## Objetivo

Pipeline de aula com cues, avatar HeyGen v3, edição de gravação de tela por cues, composição 16:9 e 9:16 e compilação.

## Fases

| Fase | Título | Roda em paralelo com |
|---|---|---|
| F-07.1 | Cues, avatar e tela | nenhuma |
| F-07.2 | Composicao e producao | nenhuma |

Detalhe de cada fase em `fases.md`; tasks em `tasks.md`.

## Critério de saída

`cd motor && uv run pytest tests/aula tests/avatar tests/test_cli_aula.py` termina com 0 failed e 0 skipped nesta máquina

## Riscos conhecidos

- Regerar a narracao invalida cues, avatar e legenda (base/aula-pipeline.md)
- Documentacao do HeyGen se contradiz em limites (base/api-heygen.md)
