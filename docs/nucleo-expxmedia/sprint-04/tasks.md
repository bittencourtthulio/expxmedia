---
expx_schema: 1
expx_tool: sprintx
kind: tasks
trabalho_id: nucleo-expxmedia
sprint_id: sprint-04
atualizado_em: 2026-09-24
tasks:
  - id: T-04.01
    titulo: "Utilitarios ffmpeg"
    fase: F-04.1
    status: pendente
    objetivo: "Portar sondagem, loudnorm em duas passadas com passada extra se pico > -1 dBFS, PNG para JPEG e concatenacao."
    arquivos:
      cria: [motor/src/expxmedia/video/ffmpeg.py, motor/tests/video/test_ffmpeg.py]
      altera: []
    teste_integracao: "Normalizar a mistura de uma voz sintetica com uma trilha gerada pelo ffmpeg resulta em -14 LUFS com tolerancia de 1 e pico abaixo de -1 dBFS, medidos na mistura final."
    teste_funcional: "O comando da primeira passada contem loudnorm=I=-14:TP=-1.5 e print_format=json."
    criterio_aceite: "cd motor && uv run pytest tests/video/test_ffmpeg.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-01.02]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-04.02
    titulo: "Verificacao de entrega"
    fase: F-04.1
    status: pendente
    objetivo: "Portar as 11 checagens do verify.py (dimensao, fps, duracao, codecs, LUFS, pico, area segura, legibilidade ≤ 35% abaixo de 0,7 s, sincronia alinhamento × roteiro, cauda no card de CTA com diferenca de pixel ≤ 12/255, CTA presente) como perfis reel (30 a 70 s, reel narrado em Remotion), reel_pagina (50 a 70 s), corte (50 a 185 s com aviso acima de 75 s, cauda de no maximo 0,80 s depois da ultima legenda, sem CTA — checagem 10b), sob_medida e aula (1920x1080 e 1080x1920, 30 fps, h264/aac, -14 ±1 LUFS, pico ≤ -1 dBFS, SRT presente e sincronizado), sem marca (D-41, D-49)."
    arquivos:
      cria: [motor/src/expxmedia/video/verificar.py, motor/tests/video/test_verificar.py]
      altera: []
    teste_integracao: "Um MP4 1080x1920 30 fps normalizado gerado no teste passa no perfil reel."
    teste_funcional: "Um teste parametrizado com um artefato defeituoso por checagem recebe, para cada uma das 11 do perfil reel e das do perfil aula, o achado especifico com o limiar esperado, inclusive a cauda de 0,9 s no perfil corte (10b), e um corte de 78 s passa no perfil corte com aviso."
    criterio_aceite: "cd motor && uv run pytest tests/video/test_verificar.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-04.01]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-04.03
    titulo: "Interface de narracao e provedor de teste"
    fase: F-04.2
    status: pendente
    objetivo: "Definir a interface narrar com alinhamento por caractere e o provedor de teste que gera sinal audivel sintetico (um tom curto por palavra) a um ritmo configuravel, com alinhamento coerente (D-34, D-39)."
    arquivos:
      cria: [motor/src/expxmedia/narrar/base.py, motor/src/expxmedia/narrar/teste.py, motor/tests/narrar/test_teste.py]
      altera: []
    teste_integracao: "Com EXPXMEDIA_PROVEDORES_TESTE=1, verificar('narrar') fica habilitada pelo provedor teste."
    teste_funcional: "Narrar 20 palavras a 3,5 palavras por segundo pelo provedor teste devolve MP3 audivel de cerca de 5,7 s e alinhamento com um tempo por caractere do texto."
    criterio_aceite: "cd motor && uv run pytest tests/narrar/test_teste.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-02.07, T-04.01]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-04.04
    titulo: "ElevenLabs with-timestamps"
    fase: F-04.2
    status: pendente
    objetivo: "Portar a chamada with-timestamps com parametros do porta-voz por tipo de peca e padroes iguais aos atuais: reel 0.45/0.8/0.25/speed 1.2 e aula similarity 0.85, style 0.15, speed 0.94, timeout 300 s (D-22, D-40)."
    arquivos:
      cria: [motor/src/expxmedia/narrar/elevenlabs.py, motor/tests/narrar/test_elevenlabs.py]
      altera: []
    teste_integracao: "Contra o stub, a requisicao vai para /v1/text-to-speech/<voz_id>/with-timestamps com os voice_settings do porta-voz."
    teste_funcional: "Sem parametros no porta-voz, o corpo de um reel usa stability 0.45, similarity_boost 0.8, style 0.25 e speed 1.2, e o de uma aula usa similarity_boost 0.85, style 0.15 e speed 0.94."
    criterio_aceite: "cd motor && uv run pytest tests/narrar/test_elevenlabs.py termina com 0 failed"
    depende_de: [T-04.03, T-01.04]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-04.05
    titulo: "Pronuncia e alinhamento no espaco do roteiro"
    fase: F-04.2
    status: pendente
    objetivo: "Aplicar o lexico do porta-voz na fala e devolver o alinhamento no espaco do roteiro, abortando se a API normalizar o texto."
    arquivos:
      cria: [motor/src/expxmedia/narrar/pronuncia.py, motor/tests/narrar/test_pronuncia.py]
      altera: []
    teste_integracao: "Com lexico {'Claude': 'Clod'} o texto enviado ao stub contem Clod e o alinhamento devolvido tem os caracteres de Claude."
    teste_funcional: "Uma resposta do stub com texto diferente do enviado grava alignment.raw.json e levanta erro sem nova chamada."
    criterio_aceite: "cd motor && uv run pytest tests/narrar/test_pronuncia.py termina com 0 failed"
    depende_de: [T-04.04]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-04.06
    titulo: "Ritmo minimo com atempo"
    fase: F-04.2
    status: pendente
    objetivo: "Portar a correcao de ritmo que so acelera ate o minimo de palavras por segundo e reescala o alinhamento; aplicada so a reel, nunca a aula (D-40)."
    arquivos:
      cria: [motor/src/expxmedia/narrar/ritmo.py, motor/tests/narrar/test_ritmo.py]
      altera: []
    teste_integracao: "Um audio de 10 s com 30 palavras e minimo 3,47 pal/s e acelerado pelo ffmpeg para no maximo 8,65 s."
    teste_funcional: "Um audio ja acima do minimo, ou de uma peca do tipo aula, nao e alterado e o alinhamento sai identico."
    criterio_aceite: "cd motor && uv run pytest tests/narrar/test_ritmo.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-04.03]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-04.07
    titulo: "Transcricao com whisper"
    fase: F-04.3
    status: pendente
    objetivo: "Transcrever com faster-whisper offline (HF_HUB_OFFLINE=1, cache local), modelo_varredura small e modelo_alinhamento medium com beam 5 como na origem, e openai-whisper de reserva (simulado no teste), idioma da Alma, saida no formato de alinhamento (D-24)."
    arquivos:
      cria: [motor/src/expxmedia/transcrever/whisper.py, motor/tests/transcrever/test_whisper.py]
      altera: []
    teste_integracao: "Transcrever o audio falado do G8 com a rede bloqueada devolve palavras com tempos crescentes nesta maquina."
    teste_funcional: "Com faster-whisper tornado nao importavel e um modulo whisper simulado, o modulo usa a reserva e registra o motor usado; o modo alinhamento pede o modelo medium com beam_size 5."
    criterio_aceite: "cd motor && uv run pytest tests/transcrever/test_whisper.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-01.07, T-01.08]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-04.08
    titulo: "Legenda do reel em PNG com card final"
    fase: F-04.3
    status: pendente
    objetivo: "Portar captions.py: blocos por ritmo, PNGs com a escada 78→54 e base da caixa em 1499, palavra do CTA destacada, termos multi-palavra protegidos pelo lexico do porta-voz, card final end.png (escada 88→48, 2,2 s), legendas.json, caps.txt, e os erros de CTA ausente no roteiro e de CTA inferido por caixa alta; fonte e cores da Alma."
    arquivos:
      cria: [motor/src/expxmedia/legendar/reel.py, motor/tests/legendar/test_reel.py]
      altera: []
    teste_integracao: "Com as entradas do G3 e a alma-golden-reel, os blocos e o legendas.json gerados sao iguais aos do golden e cada PNG difere do golden em no maximo 1% dos pixels (tolerancia 8/255 por canal)."
    teste_funcional: "Um roteiro sem a palavra do CTA levanta o erro de CTA ausente, e um alinhamento com 50% dos cartoes abaixo de 0,7 s devolve achado de legibilidade."
    criterio_aceite: "cd motor && uv run pytest tests/legendar/test_reel.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-01.07, T-02.10]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-04.09
    titulo: "Legenda de aula 42x2 e SRT"
    fase: F-04.3
    status: pendente
    objetivo: "Portar o alinhamento texto do roteiro com tempos do whisper em 42 caracteres por 2 linhas equilibradas, sem palavra orfa, e o SRT (D-23)."
    arquivos:
      cria: [motor/src/expxmedia/legendar/aula.py, motor/src/expxmedia/legendar/srt.py, motor/tests/legendar/test_aula.py]
      altera: []
    teste_integracao: "As legendas geradas do roteiro e do whisper do G5 sao iguais ao legendas.json do G5."
    teste_funcional: "Nenhuma linha passa de 42 caracteres e o SRT gerado tem indices sequenciais e tempos no formato HH:MM:SS,mmm."
    criterio_aceite: "cd motor && uv run pytest tests/legendar/test_aula.py termina com 0 failed"
    depende_de: [T-01.07]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-04.10
    titulo: "Legenda queimada por PNG"
    fase: F-04.3
    status: pendente
    objetivo: "Queimar os PNGs de legenda em video por overlay temporizado, sem libass."
    arquivos:
      cria: [motor/src/expxmedia/legendar/queimar.py, motor/tests/legendar/test_queimar.py]
      altera: []
    teste_integracao: "Queimar dois blocos num video de 3 s gera MP4 em que o quadro em 1 s difere do original na faixa da legenda e o quadro em 2,9 s nao."
    teste_funcional: "O filtro montado para dois PNGs contem um overlay com enable=between(t,...) por bloco com os tempos dos blocos."
    criterio_aceite: "cd motor && uv run pytest tests/legendar/test_queimar.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-04.08]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-04.14
    titulo: "Recasamento da transcricao"
    fase: F-04.3
    status: pendente
    objetivo: "Portar o recasar: aplicar ao texto transcrito as grafias corrigidas por difflib com insercao de largura zero, preservando os tempos, sem descartar correcao em silencio."
    arquivos:
      cria: [motor/src/expxmedia/transcrever/recasar.py, motor/tests/transcrever/test_recasar.py]
      altera: []
    teste_integracao: "Recasar a transcricao do G7 com as grafias da origem gera a transcricao recasada igual ao golden."
    teste_funcional: "Uma correcao que insere palavra sem tempo recebe tempo de largura zero no ponto de insercao e aparece no resultado."
    criterio_aceite: "cd motor && uv run pytest tests/transcrever/test_recasar.py termina com 0 failed"
    depende_de: [T-04.07]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-04.11
    titulo: "Montagem do reel de pagina"
    fase: F-04.4
    status: pendente
    objetivo: "Portar compose.py e stitch.py: rolagem com fronteira de secao entre 90 e 230 px/s (ideal 160) e espera de 3,5 s, cartao de impacto (2,5 s, ate 3 linhas, escada 150→72, desvio do rosto com aviso), selo de CTA a partir de 5 s, duracao cortada no fim do ultimo cartao alinhada a grade de quadros, adelay com all=1, tira com teto de 16384 px, e visual.json e montado_em gravados depois do MP4; cores e fontes da Alma e geometria da interface como parametro do formato."
    arquivos:
      cria: [motor/src/expxmedia/video/montar_pagina.py, motor/tests/video/test_montar_pagina.py]
      altera: []
    teste_integracao: "Com as entradas do G4 e a alma-golden-reel, o MP4 montado tem a mesma duracao do golden e os quadros em 1, 5 e 10 s diferem do golden em no maximo 1% dos pixels (tolerancia 8/255)."
    teste_funcional: "Uma tira de 20000 px e recusada com o erro do teto e o visual.json so existe depois que o MP4 foi gravado."
    criterio_aceite: "cd motor && uv run pytest tests/video/test_montar_pagina.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-04.10, T-04.02, T-01.07]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-04.12
    titulo: "Producao do reel de pagina e gate do roteiro"
    fase: F-04.4
    status: pendente
    objetivo: "Produzir reel a partir de pagina: capturar, validar o roteiro pelo gate do roteirista (130 a 180 palavras, sem travessao, markdown ou numero decimal em algarismo, cta.txt contido no roteiro), narrar uma vez, legendar, montar, normalizar a mistura, verificar no perfil reel_pagina com as 11 checagens e registrar a peca."
    arquivos:
      cria: [motor/src/expxmedia/revisar/roteiro.py, motor/src/expxmedia/producao/reel_pagina.py, motor/tests/producao/test_reel_pagina.py]
      altera: []
    teste_integracao: "Produzir a partir de uma pagina servida pelo stub com o provedor de teste gera MP4 aprovado nas 11 checagens do perfil reel_pagina, inclusive area segura, cauda no card e CTA."
    teste_funcional: "Um roteiro com travessao ou sem o texto do cta.txt e recusado pelo gate antes de narrar, e a peca produzida lista arquivos com papel final, legenda e alinhamento."
    criterio_aceite: "cd motor && uv run pytest tests/producao/test_reel_pagina.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-04.11, T-04.05, T-04.06, T-03.09, T-02.11]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-04.13
    titulo: "CLI de audio, texto e reel de pagina"
    fase: F-04.4
    status: pendente
    objetivo: "Expor narrar, transcrever, legendar reel, legendar aula, verificar --perfil e produzir reel-pagina no CLI."
    arquivos:
      cria: [motor/src/expxmedia/cli_comandos/audio_texto.py, motor/tests/test_cli_audio_texto.py]
      altera: []
    teste_integracao: "Cada subcomando novo aparece no --help e verificar --perfil reel num MP4 do teste sai 0 em subprocesso."
    teste_funcional: "verificar --perfil aula num MP4 1080x1080 sai com codigo diferente de 0 e JSON com o achado dimensao."
    criterio_aceite: "cd motor && uv run pytest tests/test_cli_audio_texto.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-04.12, T-04.09, T-04.07, T-02.14]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
---

# Tasks — Sprint 04

> Comando de teste: `cd motor && uv run pytest tests/video tests/narrar tests/transcrever tests/legendar tests/producao/test_reel_pagina.py tests/test_cli_audio_texto.py`. Base de conhecimento em `docs/nucleo-expxmedia/base/`; decisões em `00-DECISOES.md`. Nenhuma task escreve nos projetos de origem (D-37).

---

### T-04.01 — Utilitarios ffmpeg

```yaml
id: T-04.01
titulo: Utilitarios ffmpeg
fase: F-04.1
objetivo: Portar sondagem, loudnorm em duas passadas com passada extra se pico > -1 dBFS, PNG para JPEG e concatenação.
arquivos:
  cria: [motor/src/expxmedia/video/ffmpeg.py, motor/tests/video/test_ffmpeg.py]
  altera: []
teste_integracao: Normalizar a mistura de uma voz sintética com uma trilha gerada pelo ffmpeg resulta em -14 LUFS com tolerância de 1 e pico abaixo de -1 dBFS, medidos na mistura final.
teste_funcional: O comando da primeira passada contém loudnorm=I=-14:TP=-1.5 e print_format=json.
criterio_aceite: `cd motor && uv run pytest tests/video/test_ffmpeg.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-01.02]
paralelizavel: true
status: pendente
```

---

### T-04.02 — Verificacao de entrega

```yaml
id: T-04.02
titulo: Verificacao de entrega
fase: F-04.1
objetivo: Portar as 11 checagens do verify.py (dimensão, fps, duração, codecs, LUFS, pico, área segura, legibilidade ≤ 35% abaixo de 0,7 s, sincronia alinhamento × roteiro, cauda no card de CTA com diferença de pixel ≤ 12/255, CTA presente) como perfis reel (30 a 70 s, reel narrado em Remotion), reel_pagina (50 a 70 s), corte (50 a 185 s com aviso acima de 75 s, cauda de no máximo 0,80 s depois da última legenda, sem CTA — checagem 10b), sob_medida e aula (1920x1080 e 1080x1920, 30 fps, h264/aac, -14 ±1 LUFS, pico ≤ -1 dBFS, SRT presente e sincronizado), sem marca (D-41, D-49).
arquivos:
  cria: [motor/src/expxmedia/video/verificar.py, motor/tests/video/test_verificar.py]
  altera: []
teste_integracao: Um MP4 1080x1920 30 fps normalizado gerado no teste passa no perfil reel.
teste_funcional: Um teste parametrizado com um artefato defeituoso por checagem recebe, para cada uma das 11 do perfil reel e das do perfil aula, o achado específico com o limiar esperado, inclusive a cauda de 0,9 s no perfil corte (10b), e um corte de 78 s passa no perfil corte com aviso.
criterio_aceite: `cd motor && uv run pytest tests/video/test_verificar.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-04.01]
paralelizavel: false
status: pendente
```

---

### T-04.03 — Interface de narracao e provedor de teste

```yaml
id: T-04.03
titulo: Interface de narracao e provedor de teste
fase: F-04.2
objetivo: Definir a interface narrar com alinhamento por caractere e o provedor de teste que gera sinal audível sintético (um tom curto por palavra) a um ritmo configurável, com alinhamento coerente (D-34, D-39).
arquivos:
  cria: [motor/src/expxmedia/narrar/base.py, motor/src/expxmedia/narrar/teste.py, motor/tests/narrar/test_teste.py]
  altera: []
teste_integracao: Com EXPXMEDIA_PROVEDORES_TESTE=1, verificar('narrar') fica habilitada pelo provedor teste.
teste_funcional: Narrar 20 palavras a 3,5 palavras por segundo pelo provedor teste devolve MP3 audível de cerca de 5,7 s e alinhamento com um tempo por caractere do texto.
criterio_aceite: `cd motor && uv run pytest tests/narrar/test_teste.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-02.07, T-04.01]
paralelizavel: false
status: pendente
```

---

### T-04.04 — ElevenLabs with-timestamps

```yaml
id: T-04.04
titulo: ElevenLabs with-timestamps
fase: F-04.2
objetivo: Portar a chamada with-timestamps com parâmetros do porta-voz por tipo de peça e padrões iguais aos atuais: reel 0.45/0.8/0.25/speed 1.2 e aula similarity 0.85, style 0.15, speed 0.94, timeout 300 s (D-22, D-40).
arquivos:
  cria: [motor/src/expxmedia/narrar/elevenlabs.py, motor/tests/narrar/test_elevenlabs.py]
  altera: []
teste_integracao: Contra o stub, a requisição vai para /v1/text-to-speech/<voz_id>/with-timestamps com os voice_settings do porta-voz.
teste_funcional: Sem parâmetros no porta-voz, o corpo de um reel usa stability 0.45, similarity_boost 0.8, style 0.25 e speed 1.2, e o de uma aula usa similarity_boost 0.85, style 0.15 e speed 0.94.
criterio_aceite: `cd motor && uv run pytest tests/narrar/test_elevenlabs.py` termina com 0 failed
depende_de: [T-04.03, T-01.04]
paralelizavel: true
status: pendente
```

---

### T-04.05 — Pronuncia e alinhamento no espaco do roteiro

```yaml
id: T-04.05
titulo: Pronuncia e alinhamento no espaco do roteiro
fase: F-04.2
objetivo: Aplicar o léxico do porta-voz na fala e devolver o alinhamento no espaço do roteiro, abortando se a API normalizar o texto.
arquivos:
  cria: [motor/src/expxmedia/narrar/pronuncia.py, motor/tests/narrar/test_pronuncia.py]
  altera: []
teste_integracao: Com léxico {'Claude': 'Clód'} o texto enviado ao stub contém Clód e o alinhamento devolvido tem os caracteres de Claude.
teste_funcional: Uma resposta do stub com texto diferente do enviado grava alignment.raw.json e levanta erro sem nova chamada.
criterio_aceite: `cd motor && uv run pytest tests/narrar/test_pronuncia.py` termina com 0 failed
depende_de: [T-04.04]
paralelizavel: false
status: pendente
```

---

### T-04.06 — Ritmo minimo com atempo

```yaml
id: T-04.06
titulo: Ritmo minimo com atempo
fase: F-04.2
objetivo: Portar a correção de ritmo que só acelera até o mínimo de palavras por segundo e reescala o alinhamento; aplicada só a reel, nunca a aula (D-40).
arquivos:
  cria: [motor/src/expxmedia/narrar/ritmo.py, motor/tests/narrar/test_ritmo.py]
  altera: []
teste_integracao: Um áudio de 10 s com 30 palavras e mínimo 3,47 pal/s é acelerado pelo ffmpeg para no máximo 8,65 s.
teste_funcional: Um áudio já acima do mínimo, ou de uma peça do tipo aula, não é alterado e o alinhamento sai idêntico.
criterio_aceite: `cd motor && uv run pytest tests/narrar/test_ritmo.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-04.03]
paralelizavel: true
status: pendente
```

---

### T-04.07 — Transcricao com whisper

```yaml
id: T-04.07
titulo: Transcricao com whisper
fase: F-04.3
objetivo: Transcrever com faster-whisper offline (HF_HUB_OFFLINE=1, cache local), modelo_varredura small e modelo_alinhamento medium com beam 5 como na origem, e openai-whisper de reserva (simulado no teste), idioma da Alma, saída no formato de alinhamento (D-24).
arquivos:
  cria: [motor/src/expxmedia/transcrever/whisper.py, motor/tests/transcrever/test_whisper.py]
  altera: []
teste_integracao: Transcrever o áudio falado do G8 com a rede bloqueada devolve palavras com tempos crescentes nesta máquina.
teste_funcional: Com faster-whisper tornado não importável e um módulo whisper simulado, o módulo usa a reserva e registra o motor usado; o modo alinhamento pede o modelo medium com beam_size 5.
criterio_aceite: `cd motor && uv run pytest tests/transcrever/test_whisper.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-01.07, T-01.08]
paralelizavel: true
status: pendente
```

---

### T-04.08 — Legenda do reel em PNG com card final

```yaml
id: T-04.08
titulo: Legenda do reel em PNG com card final
fase: F-04.3
objetivo: Portar captions.py: blocos por ritmo, PNGs com a escada 78→54 e base da caixa em 1499, palavra do CTA destacada, termos multi-palavra protegidos pelo léxico do porta-voz, card final end.png (escada 88→48, 2,2 s), legendas.json, caps.txt, e os erros de CTA ausente no roteiro e de CTA inferido por caixa alta; fonte e cores da Alma.
arquivos:
  cria: [motor/src/expxmedia/legendar/reel.py, motor/tests/legendar/test_reel.py]
  altera: []
teste_integracao: Com as entradas do G3 e a alma-golden-reel, os blocos e o legendas.json gerados são iguais aos do golden e cada PNG difere do golden em no máximo 1% dos pixels (tolerância 8/255 por canal).
teste_funcional: Um roteiro sem a palavra do CTA levanta o erro de CTA ausente, e um alinhamento com 50% dos cartões abaixo de 0,7 s devolve achado de legibilidade.
criterio_aceite: `cd motor && uv run pytest tests/legendar/test_reel.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-01.07, T-02.10]
paralelizavel: true
status: pendente
```

---

### T-04.09 — Legenda de aula 42x2 e SRT

```yaml
id: T-04.09
titulo: Legenda de aula 42x2 e SRT
fase: F-04.3
objetivo: Portar o alinhamento texto do roteiro com tempos do whisper em 42 caracteres por 2 linhas equilibradas, sem palavra órfã, e o SRT (D-23).
arquivos:
  cria: [motor/src/expxmedia/legendar/aula.py, motor/src/expxmedia/legendar/srt.py, motor/tests/legendar/test_aula.py]
  altera: []
teste_integracao: As legendas geradas do roteiro e do whisper do G5 são iguais ao legendas.json do G5.
teste_funcional: Nenhuma linha passa de 42 caracteres e o SRT gerado tem índices sequenciais e tempos no formato HH:MM:SS,mmm.
criterio_aceite: `cd motor && uv run pytest tests/legendar/test_aula.py` termina com 0 failed
depende_de: [T-01.07]
paralelizavel: true
status: pendente
```

---

### T-04.10 — Legenda queimada por PNG

```yaml
id: T-04.10
titulo: Legenda queimada por PNG
fase: F-04.3
objetivo: Queimar os PNGs de legenda em vídeo por overlay temporizado, sem libass.
arquivos:
  cria: [motor/src/expxmedia/legendar/queimar.py, motor/tests/legendar/test_queimar.py]
  altera: []
teste_integracao: Queimar dois blocos num vídeo de 3 s gera MP4 em que o quadro em 1 s difere do original na faixa da legenda e o quadro em 2,9 s não.
teste_funcional: O filtro montado para dois PNGs contém um overlay com enable=between(t,...) por bloco com os tempos dos blocos.
criterio_aceite: `cd motor && uv run pytest tests/legendar/test_queimar.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-04.08]
paralelizavel: false
status: pendente
```

---

### T-04.14 — Recasamento da transcricao

```yaml
id: T-04.14
titulo: Recasamento da transcricao
fase: F-04.3
objetivo: Portar o recasar: aplicar ao texto transcrito as grafias corrigidas por difflib com inserção de largura zero, preservando os tempos, sem descartar correção em silêncio.
arquivos:
  cria: [motor/src/expxmedia/transcrever/recasar.py, motor/tests/transcrever/test_recasar.py]
  altera: []
teste_integracao: Recasar a transcrição do G7 com as grafias da origem gera a transcrição recasada igual ao golden.
teste_funcional: Uma correção que insere palavra sem tempo recebe tempo de largura zero no ponto de inserção e aparece no resultado.
criterio_aceite: `cd motor && uv run pytest tests/transcrever/test_recasar.py` termina com 0 failed
depende_de: [T-04.07]
paralelizavel: false
status: pendente
```

---

### T-04.11 — Montagem do reel de pagina

```yaml
id: T-04.11
titulo: Montagem do reel de pagina
fase: F-04.4
objetivo: Portar compose.py e stitch.py: rolagem com fronteira de seção entre 90 e 230 px/s (ideal 160) e espera de 3,5 s, cartão de impacto (2,5 s, até 3 linhas, escada 150→72, desvio do rosto com aviso), selo de CTA a partir de 5 s, duração cortada no fim do último cartão alinhada à grade de quadros, adelay com all=1, tira com teto de 16384 px, e visual.json e montado_em gravados depois do MP4; cores e fontes da Alma e geometria da interface como parâmetro do formato.
arquivos:
  cria: [motor/src/expxmedia/video/montar_pagina.py, motor/tests/video/test_montar_pagina.py]
  altera: []
teste_integracao: Com as entradas do G4 e a alma-golden-reel, o MP4 montado tem a mesma duração do golden e os quadros em 1, 5 e 10 s diferem do golden em no máximo 1% dos pixels (tolerância 8/255).
teste_funcional: Uma tira de 20000 px é recusada com o erro do teto e o visual.json só existe depois que o MP4 foi gravado.
criterio_aceite: `cd motor && uv run pytest tests/video/test_montar_pagina.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-04.10, T-04.02, T-01.07]
paralelizavel: false
status: pendente
```

---

### T-04.12 — Producao do reel de pagina e gate do roteiro

```yaml
id: T-04.12
titulo: Producao do reel de pagina e gate do roteiro
fase: F-04.4
objetivo: Produzir reel a partir de página: capturar, validar o roteiro pelo gate do roteirista (130 a 180 palavras, sem travessão, markdown ou número decimal em algarismo, cta.txt contido no roteiro), narrar uma vez, legendar, montar, normalizar a mistura, verificar no perfil reel_pagina com as 11 checagens e registrar a peça.
arquivos:
  cria: [motor/src/expxmedia/revisar/roteiro.py, motor/src/expxmedia/producao/reel_pagina.py, motor/tests/producao/test_reel_pagina.py]
  altera: []
teste_integracao: Produzir a partir de uma página servida pelo stub com o provedor de teste gera MP4 aprovado nas 11 checagens do perfil reel_pagina, inclusive área segura, cauda no card e CTA.
teste_funcional: Um roteiro com travessão ou sem o texto do cta.txt é recusado pelo gate antes de narrar, e a peça produzida lista arquivos com papel final, legenda e alinhamento.
criterio_aceite: `cd motor && uv run pytest tests/producao/test_reel_pagina.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-04.11, T-04.05, T-04.06, T-03.09, T-02.11]
paralelizavel: false
status: pendente
```

---

### T-04.13 — CLI de audio, texto e reel de pagina

```yaml
id: T-04.13
titulo: CLI de audio, texto e reel de pagina
fase: F-04.4
objetivo: Expor narrar, transcrever, legendar reel, legendar aula, verificar --perfil e produzir reel-pagina no CLI.
arquivos:
  cria: [motor/src/expxmedia/cli_comandos/audio_texto.py, motor/tests/test_cli_audio_texto.py]
  altera: []
teste_integracao: Cada subcomando novo aparece no --help e verificar --perfil reel num MP4 do teste sai 0 em subprocesso.
teste_funcional: verificar --perfil aula num MP4 1080x1080 sai com código diferente de 0 e JSON com o achado dimensao.
criterio_aceite: `cd motor && uv run pytest tests/test_cli_audio_texto.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-04.12, T-04.09, T-04.07, T-02.14]
paralelizavel: false
status: pendente
```
