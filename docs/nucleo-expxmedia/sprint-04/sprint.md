---
expx_schema: 1
expx_tool: sprintx
kind: sprint
trabalho_id: nucleo-expxmedia
sprint_id: sprint-04
titulo: "Audio, texto e video basico"
status: nao_iniciado
criterio_saida: "cd motor && uv run pytest tests/video tests/narrar tests/transcrever tests/legendar tests/producao/test_reel_pagina.py tests/test_cli_audio_texto.py termina com 0 failed e 0 skipped nesta maquina"
fases: [F-04.1, F-04.2, F-04.3, F-04.4]
riscos: ["ffmpeg local sem libass; legendas queimadas por PNG (base/legendar.md)", "Alinhamento no espaco do roteiro aborta se a API normalizar o texto (base/narrar-elevenlabs.md)", "loudnorm precisa medir a mistura final, nao a narracao isolada (base/montagem-reel-ffmpeg.md)"]
atualizado_em: 2026-09-24
---

# Sprint 04 — Audio, texto e video basico

## Objetivo

Porta ffmpeg e a verificação de entrega, a narração com alinhamento, a transcrição e as legendas.

## Fases

| Fase | Título | Roda em paralelo com |
|---|---|---|
| F-04.1 | ffmpeg e verificacao | nenhuma |
| F-04.2 | Narracao | F-04.3 |
| F-04.3 | Transcricao e legenda | F-04.2 |
| F-04.4 | Reel de pagina capturada | nenhuma |

Detalhe de cada fase em `fases.md`; tasks em `tasks.md`.

## Critério de saída

`cd motor && uv run pytest tests/video tests/narrar tests/transcrever tests/legendar tests/producao/test_reel_pagina.py tests/test_cli_audio_texto.py` termina com 0 failed e 0 skipped nesta máquina

## Riscos conhecidos

- ffmpeg local sem libass; legendas queimadas por PNG (base/legendar.md)
- Alinhamento no espaco do roteiro aborta se a API normalizar o texto (base/narrar-elevenlabs.md)
- loudnorm precisa medir a mistura final, nao a narracao isolada (base/montagem-reel-ffmpeg.md)
