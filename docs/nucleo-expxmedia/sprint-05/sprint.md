---
expx_schema: 1
expx_tool: sprintx
kind: sprint
trabalho_id: nucleo-expxmedia
sprint_id: sprint-05
titulo: "Motion"
status: nao_iniciado
criterio_saida: "cd motor && uv run pytest tests/motion tests/producao/test_reel.py tests/producao/test_carrossel_misto.py tests/producao/apresentacao tests/test_template_reel.py tests/test_cli_motion.py termina com 0 failed e 0 skipped nesta maquina"
fases: [F-05.1, F-05.2, F-05.3, F-05.4, F-05.5]
riscos: ["fps 30 duplicado em cinco lugares no sistema atual (base/reel-recriado-roteiro-e-cenas.md)", "Render Remotion pode levar minutos; testes usam composicoes curtas", "Licenca do Remotion para clientes (PENDENTE-01)"]
atualizado_em: 2026-09-24
---

# Sprint 05 — Motion

## Objetivo

Kit Remotion genérico, runner multi-versão, montagem de linha do tempo e trilha, reel narrado, slide de vídeo no carrossel e apresentação.

## Fases

| Fase | Título | Roda em paralelo com |
|---|---|---|
| F-05.1 | Kit e runner | nenhuma |
| F-05.2 | Reel narrado | F-05.3, F-05.4 |
| F-05.3 | Carrossel misto | F-05.2, F-05.4 |
| F-05.4 | Apresentacao | F-05.2, F-05.3 |
| F-05.5 | CLI de motion | nenhuma |

Detalhe de cada fase em `fases.md`; tasks em `tasks.md`.

## Critério de saída

`cd motor && uv run pytest tests/motion tests/producao/test_reel.py tests/producao/test_carrossel_misto.py tests/producao/apresentacao tests/test_template_reel.py tests/test_cli_motion.py` termina com 0 failed e 0 skipped nesta máquina

## Riscos conhecidos

- fps 30 duplicado em cinco lugares no sistema atual (base/reel-recriado-roteiro-e-cenas.md)
- Render Remotion pode levar minutos; testes usam composicoes curtas
- Licenca do Remotion para clientes (PENDENTE-01)
