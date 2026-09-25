---
expx_schema: 1
expx_tool: sprintx
kind: sprint
trabalho_id: nucleo-expxmedia
sprint_id: sprint-09
titulo: "Plugin do nucleo"
status: concluido
criterio_saida: "cd motor && uv run pytest (suite inteira) termina com 0 failed e 0 skipped nesta maquina e a varredura de marca passa sobre nucleo/"
fases: [F-09.1, F-09.2]
riscos: ["A inteligencia do recriado mora no processo do modelo; prompts precisam ser portados sem perda (base/inteligencia-reel-recriado.md)", "Revisor precisa conhecer o formato sob medida (base/inteligencia-reel-recriado.md risco 3)"]
atualizado_em: 2026-09-25
---

# Sprint 09 — Plugin do nucleo

## Objetivo

Plugin expxmedia do Claude Code com portão, segredo, Alma, ambiente, skills de produção, agentes e regras que carregam a inteligência dos projetos de origem sem marca.

## Fases

| Fase | Título | Roda em paralelo com |
|---|---|---|
| F-09.1 | Manifesto, hooks, Alma, ambiente e revisao de copy | nenhuma |
| F-09.2 | Skills de producao e agentes | nenhuma |

Detalhe de cada fase em `fases.md`; tasks em `tasks.md`.

## Critério de saída

`cd motor && uv run pytest` (suíte inteira) termina com 0 failed e 0 skipped nesta máquina e a varredura de marca passa sobre nucleo/

## Riscos conhecidos

- A inteligencia do recriado mora no processo do modelo; prompts precisam ser portados sem perda (base/inteligencia-reel-recriado.md)
- Revisor precisa conhecer o formato sob medida (base/inteligencia-reel-recriado.md risco 3)
