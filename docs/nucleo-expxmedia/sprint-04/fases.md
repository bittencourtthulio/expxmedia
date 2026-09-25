---
expx_schema: 1
expx_tool: sprintx
kind: fases
trabalho_id: nucleo-expxmedia
sprint_id: sprint-04
atualizado_em: 2026-09-24
fases:
  - id: F-04.1
    titulo: "ffmpeg e verificacao"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/video termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-04.01, T-04.02]
  - id: F-04.2
    titulo: "Narracao"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/narrar termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: true
    paralela_com: [F-04.3]
    tasks: [T-04.03, T-04.04, T-04.05, T-04.06]
  - id: F-04.3
    titulo: "Transcricao e legenda"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/transcrever tests/legendar termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: true
    paralela_com: [F-04.2]
    tasks: [T-04.07, T-04.08, T-04.09, T-04.10, T-04.14]
  - id: F-04.4
    titulo: "Reel de pagina capturada"
    status: nao_iniciado
    criterio_saida: "cd motor && uv run pytest tests/video/test_montar_pagina.py tests/producao/test_reel_pagina.py tests/test_cli_audio_texto.py termina com 0 failed e 0 skipped nesta maquina"
    paralelizavel: false
    paralela_com: []
    tasks: [T-04.11, T-04.12, T-04.13]
---

# Fases — Sprint 04

> O paralelismo declarado aqui é definitivo: a execução nunca decide paralelismo sozinha.

---

## F-04.1 — ffmpeg e verificacao

**Objetivo:** Utilitários de ffmpeg e as checagens de entrega com os perfis reel, sob_medida e aula.

**Tasks que a compõem:** T-04.01, T-04.02

**Critério de saída:** `cd motor && uv run pytest tests/video` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma

---

## F-04.2 — Narracao

**Objetivo:** Interface, provedor de teste audível, ElevenLabs, pronúncia e ritmo.

**Tasks que a compõem:** T-04.03, T-04.04, T-04.05, T-04.06

**Critério de saída:** `cd motor && uv run pytest tests/narrar` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** F-04.3

---

## F-04.3 — Transcricao e legenda

**Objetivo:** Whisper offline, legenda do reel em PNG com card final, 42x2, SRT e queima por PNG.

**Tasks que a compõem:** T-04.07, T-04.08, T-04.09, T-04.10, T-04.14

**Critério de saída:** `cd motor && uv run pytest tests/transcrever tests/legendar` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** F-04.2

---

## F-04.4 — Reel de pagina capturada

**Objetivo:** Montagem com rolagem, cartão de impacto e selo de CTA, e a produção do reel de página.

**Tasks que a compõem:** T-04.11, T-04.12, T-04.13

**Critério de saída:** `cd motor && uv run pytest tests/video/test_montar_pagina.py tests/producao/test_reel_pagina.py tests/test_cli_audio_texto.py` termina com 0 failed e 0 skipped nesta maquina

**Roda em paralelo com:** nenhuma
