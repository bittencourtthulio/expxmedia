---
expx_schema: 1
expx_tool: sprintx
kind: sprint
trabalho_id: nucleo-expxmedia
sprint_id: sprint-08
titulo: "Publicacao e agendador"
status: concluido
criterio_saida: "cd motor && uv run pytest tests/publicar tests/agendador tests/test_cli_publicar.py termina com 0 failed"
fases: [F-08.1, F-08.2, F-08.3]
riscos: ["Expx Flow documenta so imagem no carrossel (PENDENTE-02)", "Graph so aceita JPEG e 4:5 a 1.91:1 (base/publicar-meta-graph.md)"]
atualizado_em: 2026-09-25
---

# Sprint 08 — Publicacao e agendador

## Objetivo

Publicação por Expx Flow e Graph API com idempotência, túnel, agendador local e instalação por sistema operacional.

## Fases

| Fase | Título | Roda em paralelo com |
|---|---|---|
| F-08.1 | Publicacao | nenhuma |
| F-08.2 | Agendador local | nenhuma |
| F-08.3 | CLI de publicacao | nenhuma |

Detalhe de cada fase em `fases.md`; tasks em `tasks.md`.

## Critério de saída

`cd motor && uv run pytest tests/publicar tests/agendador tests/test_cli_publicar.py` termina com 0 failed

## Riscos conhecidos

- Expx Flow documenta so imagem no carrossel (PENDENTE-02)
- Graph so aceita JPEG e 4:5 a 1.91:1 (base/publicar-meta-graph.md)
