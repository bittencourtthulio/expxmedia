---
expx_schema: 1
expx_tool: sprintx
kind: sprint
trabalho_id: nucleo-expxmedia
sprint_id: sprint-03
titulo: "Imagem estatica"
status: nao_iniciado
criterio_saida: "cd motor && uv run pytest termina com 0 failed e o teste de paridade HTML passa"
fases: [F-03.1, F-03.2, F-03.3]
riscos: ["Contraste precisa ser medido no PNG, nao no CSS (base/renderizar-html.md)", "color(srgb 0..1) nao e reescalado no codigo atual (base/00-LACUNAS.md)"]
atualizado_em: 2026-09-24
---

# Sprint 03 — Imagem estatica

## Objetivo

Porta o renderizador HTML com as heurísticas calibradas, os provedores de imagem e a captura de página, e produz post único e carrossel de imagem.

## Fases

| Fase | Título | Roda em paralelo com |
|---|---|---|
| F-03.1 | Renderizador HTML | F-03.2 |
| F-03.2 | Provedores de imagem | F-03.1 |
| F-03.3 | Captura e producao estatica | nenhuma |

Detalhe de cada fase em `fases.md`; tasks em `tasks.md`.

## Critério de saída

`cd motor && uv run pytest` termina com 0 failed e o teste de paridade HTML passa

## Riscos conhecidos

- Contraste precisa ser medido no PNG, nao no CSS (base/renderizar-html.md)
- color(srgb 0..1) nao e reescalado no codigo atual (base/00-LACUNAS.md)
