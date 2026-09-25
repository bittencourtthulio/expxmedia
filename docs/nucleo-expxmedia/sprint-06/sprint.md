---
expx_schema: 1
expx_tool: sprintx
kind: sprint
trabalho_id: nucleo-expxmedia
sprint_id: sprint-06
titulo: "Referencia e corte"
status: concluido
criterio_saida: "cd motor && uv run pytest tests/referencia tests/corte tests/producao/test_abertura.py tests/test_cli_referencia_corte.py termina com 0 failed e 0 skipped nesta maquina"
fases: [F-06.1, F-06.2, F-06.3, F-06.4]
riscos: ["A sequencia de cenas vem das folhas lidas pelo modelo, nao do scdet (base/inteligencia-reel-recriado.md)", "Documentacao do corte diverge do codigo; o codigo e a verdade (base/corte-e-reenquadramento.md)"]
atualizado_em: 2026-09-25
---

# Sprint 06 — Referencia e corte

## Objetivo

Análise de vídeo de referência e o reel sob medida, corte de vídeo longo em reel com reenquadramento e b-roll, e abertura gerada.

## Fases

| Fase | Título | Roda em paralelo com |
|---|---|---|
| F-06.1 | Reel por referencia | F-06.2, F-06.3 |
| F-06.2 | Corte de video longo | F-06.1, F-06.3 |
| F-06.3 | Abertura gerada | F-06.1, F-06.2 |
| F-06.4 | CLI de referencia e corte | nenhuma |

Detalhe de cada fase em `fases.md`; tasks em `tasks.md`.

## Critério de saída

`cd motor && uv run pytest tests/referencia tests/corte tests/producao/test_abertura.py tests/test_cli_referencia_corte.py` termina com 0 failed e 0 skipped nesta máquina

## Riscos conhecidos

- A sequencia de cenas vem das folhas lidas pelo modelo, nao do scdet (base/inteligencia-reel-recriado.md)
- Documentacao do corte diverge do codigo; o codigo e a verdade (base/corte-e-reenquadramento.md)
