---
expx_schema: 1
expx_tool: sprintx
kind: sprint
trabalho_id: nucleo-expxmedia
sprint_id: sprint-01
titulo: "Capacidade de testar"
status: concluido
criterio_saida: "cd motor && uv run pytest termina com 0 failed e os goldens estao gravados com manifesto"
fases: [F-01.1, F-01.2]
riscos: ["Goldens dependem de rodar codigo dos projetos de origem em copia temporaria (D-37)", "Rede necessaria uma vez: uv sync, npm ci do kit, chrome-headless-shell do Remotion, playwright install chromium, Google Fonts do golden; sem rede vira bloqueio (D-42)"]
atualizado_em: 2026-09-24
---

# Sprint 01 — Capacidade de testar

## Objetivo

Entrega o projeto Python, o harness de teste com rede bloqueada, a Alma fictícia, o stub HTTP, o kit Remotion instalável, a varredura de marca e os goldens do sistema atual. Nenhuma funcionalidade de negócio.

## Fases

| Fase | Título | Roda em paralelo com |
|---|---|---|
| F-01.1 | Projeto Python e harness | nenhuma |
| F-01.2 | Ambiente, kit Remotion, varredura de marca e goldens | nenhuma |

Detalhe de cada fase em `fases.md`; tasks em `tasks.md`.

## Critério de saída

`cd motor && uv run pytest` termina com 0 failed e os goldens estão gravados com manifesto

## Riscos conhecidos

- Goldens dependem de rodar codigo dos projetos de origem em copia temporaria (D-37)
- Rede necessaria uma vez: uv sync, npm ci do kit, chrome-headless-shell do Remotion, playwright install chromium, Google Fonts do golden; sem rede vira bloqueio (D-42)
