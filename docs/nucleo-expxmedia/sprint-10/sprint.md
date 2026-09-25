---
expx_schema: 1
expx_tool: sprintx
kind: sprint
trabalho_id: nucleo-expxmedia
sprint_id: sprint-10
titulo: "Validacao ponta a ponta"
status: nao_iniciado
criterio_saida: "cd motor && uv run pytest termina com 0 failed e 0 skipped nesta maquina e os dois relatorios de validacao estao gravados"
fases: [F-10.1, F-10.2]
riscos: ["O reel por referencia depende de julgamento do modelo; o criterio e verificacao mecanica mais checklist gravado"]
atualizado_em: 2026-09-24
---

# Sprint 10 — Validacao ponta a ponta

## Objetivo

Prova de pronto: os cinco tipos produzidos sem chave com a Alma fictícia, publicação em dry-run, um reel por referência feito seguindo a skill, documentação e varredura final.

## Fases

| Fase | Título | Roda em paralelo com |
|---|---|---|
| F-10.1 | Ponta a ponta | nenhuma |
| F-10.2 | Documentacao e fechamento | nenhuma |

Detalhe de cada fase em `fases.md`; tasks em `tasks.md`.

## Critério de saída

`cd motor && uv run pytest` termina com 0 failed e 0 skipped nesta máquina e os dois relatórios de validação estão gravados

## Riscos conhecidos

- O reel por referencia depende de julgamento do modelo; o criterio e verificacao mecanica mais checklist gravado
