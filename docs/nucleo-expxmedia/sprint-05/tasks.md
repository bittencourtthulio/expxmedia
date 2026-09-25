---
expx_schema: 1
expx_tool: sprintx
kind: tasks
trabalho_id: nucleo-expxmedia
sprint_id: sprint-05
atualizado_em: 2026-09-25
tasks:
  - id: T-05.01
    titulo: "Kit base do Remotion"
    fase: F-05.1
    status: em_andamento
    objetivo: "Portar anim.ts, area segura e centralizacao, com FPS numa constante unica, useAlma por props e SeloPerfil a partir do porta-voz e do canal da Alma."
    arquivos:
      cria: [motor/kit-remotion/src/kit/constantes.ts, motor/kit-remotion/src/kit/anim.ts, motor/kit-remotion/src/kit/alma.tsx, motor/kit-remotion/src/kit/SeloPerfil.tsx, motor/kit-remotion/src/kit/fontes.ts, motor/kit-remotion/src/composicoes/TesteSelo/index.tsx, motor/tests/motion/test_kit.py]
      altera: []
    teste_integracao: "npx tsc --noEmit no kit termina sem erro e um still da composicao de teste do selo e gerado."
    teste_funcional: "A busca pelo literal 30 como fps nos arquivos do kit encontra so constantes.ts."
    criterio_aceite: "cd motor && uv run pytest tests/motion/test_kit.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-01.05]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-05.02
    titulo: "Montagem e trilha generalizadas"
    fase: F-05.1
    status: em_andamento
    objetivo: "Portar montar-reel.mjs e audio.mjs com caminhos por argumento, mesmo PRNG e semente, sem reescrever registro global (D-19)."
    arquivos:
      cria: [motor/kit-remotion/scripts/montar.mjs, motor/kit-remotion/scripts/audio.mjs, motor/tests/motion/test_montar.py]
      altera: []
    teste_integracao: "Montar o G2 a partir das mesmas entradas gera timeline.json igual ao golden e trilha.wav com o mesmo sha256."
    teste_funcional: "Uma ancora ausente da narracao faz a montagem sair com erro citando a cena e a ancora."
    criterio_aceite: "cd motor && uv run pytest tests/motion/test_montar.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.01, T-01.07]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-05.03
    titulo: "Runner Remotion multi-versao"
    fase: F-05.1
    status: em_andamento
    objetivo: "Renderizar com o kit na 4.0.528 e, para outras versoes, um projeto por versao em cache fora da instalacao; cada render faz bundle so da composicao pedida por um entry point proprio, com o browser compartilhado preparado na T-01.08, props JSON e timeout 1800 s; nenhum teste instala nada (D-17, D-46)."
    arquivos:
      cria: [motor/src/expxmedia/motion/remotion.py, motor/tests/motion/test_runner.py]
      altera: []
    teste_integracao: "Renderizar a composicao Vazio por 2 s com props JSON gera MP4 de 60 quadros nesta maquina."
    teste_funcional: "Pedir a versao 4.0.522 resolve um diretorio de cache diferente do da 4.0.528 sem instalar, e uma composicao quebrada em outra pasta de src/composicoes nao impede o render da composicao pedida."
    criterio_aceite: "cd motor && uv run pytest tests/motion/test_runner.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.01]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-05.04
    titulo: "Previa com guias"
    fase: F-05.1
    status: em_andamento
    objetivo: "Gerar still a 60% de cada cena com as guias 220 e 1500 px."
    arquivos:
      cria: [motor/src/expxmedia/motion/previa.py, motor/tests/motion/test_previa.py]
      altera: []
    teste_integracao: "Gerar previa de uma linha do tempo de 3 cenas produz 3 imagens e uma folha com as tres."
    teste_funcional: "Cada imagem de previa tem pixels da cor das guias nas linhas y=220 e y=1500."
    criterio_aceite: "cd motor && uv run pytest tests/motion/test_previa.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.03]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-05.05
    titulo: "Template de reel embarcado"
    fase: F-05.2
    status: pendente
    objetivo: "Criar um template de reel narrado em codigo Remotion sobre o kit, com cores e fontes da Alma (D-05, D-31)."
    arquivos:
      cria: [templates/reel/narrado-cartao/template.json, templates/reel/narrado-cartao/package.json, templates/reel/narrado-cartao/src/Composicao.tsx, templates/reel/narrado-cartao/src/cenas.tsx, templates/reel/narrado-cartao/cenas.json, templates/reel/narrado-cartao/exemplo.json, motor/tests/test_template_reel.py]
      altera: []
    teste_integracao: "O template renderiza com a Alma ficticia e o provedor de teste e passa no perfil reel da verificacao."
    teste_funcional: "O template passa em template.validar no modo template sem nenhum achado."
    criterio_aceite: "cd motor && uv run pytest tests/test_template_reel.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.02, T-05.03, T-02.12]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-05.06
    titulo: "Producao de reel narrado"
    fase: F-05.2
    status: pendente
    objetivo: "Produzir reel narrado em Remotion: gate de 130 a 180 palavras, narracao uma vez, montagem, render, normalizacao da mistura, verificacao no perfil reel (30 a 70 s) e peca.json (D-41)."
    arquivos:
      cria: [motor/src/expxmedia/producao/reel.py, motor/tests/producao/test_reel.py]
      altera: []
    teste_integracao: "Produzir um reel de 150 palavras com o provedor de teste a 3,5 palavras por segundo gera MP4 de 43 a 45 s aprovado no perfil reel e peca produzida."
    teste_funcional: "Um roteiro de 100 palavras e recusado antes de narrar e nenhuma chamada ao provedor acontece."
    criterio_aceite: "cd motor && uv run pytest tests/producao/test_reel.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.05, T-04.05, T-04.06, T-04.02]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-05.07
    titulo: "Slide de video no carrossel"
    fase: F-05.3
    status: pendente
    objetivo: "Permitir kind com midia video no carrossel, renderizado em Remotion no formato do carrossel a partir de uma composicao do kit, registrado na peca (D-06)."
    arquivos:
      cria: [motor/kit-remotion/src/composicoes/SlideVideo/index.tsx, motor/tests/producao/test_carrossel_misto.py]
      altera: [motor/src/expxmedia/producao/carrossel.py]
    teste_integracao: "Um carrossel com slide 1 de video e 2 de imagem gera slide_01.mp4 4:5 e dois PNGs."
    teste_funcional: "A peca registra slides[0].midia video com duracao_s preenchida e slides[1].midia imagem com duracao_s null."
    criterio_aceite: "cd motor && uv run pytest tests/producao/test_carrossel_misto.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.03, T-03.12]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-05.08
    titulo: "Deck da apresentacao"
    fase: F-05.4
    status: pendente
    objetivo: "Portar o schema do deck.json e sua validacao sem CTA fixo."
    arquivos:
      cria: [motor/src/expxmedia/producao/apresentacao/deck.py, motor/tests/producao/apresentacao/test_deck.py]
      altera: []
    teste_integracao: "O deck do G6 convertido para o schema do nucleo valida sem achado."
    teste_funcional: "Um slide com tipo desconhecido devolve achado citando os tipos aceitos."
    criterio_aceite: "cd motor && uv run pytest tests/producao/apresentacao/test_deck.py termina com 0 failed"
    depende_de: [T-01.07, T-02.11]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-05.09
    titulo: "Palco HTML navegavel"
    fase: F-05.4
    status: pendente
    objetivo: "Gerar apresentacao.html autocontida e navegavel por teclado, com tokens e fontes da Alma."
    arquivos:
      cria: [motor/src/expxmedia/producao/apresentacao/palco.py, motor/src/expxmedia/recursos/palco.html, motor/tests/producao/apresentacao/test_palco.py]
      altera: []
    teste_integracao: "Abrir o HTML gerado no Playwright e pressionar seta direita avanca do slide 1 para o 2."
    teste_funcional: "O HTML gerado nao referencia nenhuma URL externa e contem as variaveis --alma-*."
    criterio_aceite: "cd motor && uv run pytest tests/producao/apresentacao/test_palco.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.08, T-02.10]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-05.10
    titulo: "Cenas e render da apresentacao"
    fase: F-05.4
    status: pendente
    objetivo: "Portar as cenas da apresentacao para o kit e renderizar MP4 e PNG por slide."
    arquivos:
      cria: [motor/kit-remotion/src/composicoes/Apresentacao/index.tsx, motor/kit-remotion/src/composicoes/Apresentacao/cenas.tsx, motor/src/expxmedia/producao/apresentacao/render.py, motor/tests/producao/apresentacao/test_render.py]
      altera: []
    teste_integracao: "Renderizar um deck de 3 slides gera MP4 16:9 e 3 PNGs nesta maquina."
    teste_funcional: "Cada tipo de slide do schema tem componente registrado nas cenas do kit."
    criterio_aceite: "cd motor && uv run pytest tests/producao/apresentacao/test_render.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.08, T-05.03]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-05.11
    titulo: "Template e producao de apresentacao"
    fase: F-05.4
    status: pendente
    objetivo: "Criar o template de apresentacao embarcado e a producao que gera HTML, e opcionalmente MP4, com peca.json."
    arquivos:
      cria: [templates/apresentacao/padrao/template.json, templates/apresentacao/padrao/template.css, templates/apresentacao/padrao/exemplo.json, motor/src/expxmedia/producao/apresentacao/producao.py, motor/tests/producao/apresentacao/test_producao.py]
      altera: []
    teste_integracao: "Produzir uma apresentacao na fixture gera apresentacao.html com papel final e peca produzida."
    teste_funcional: "Com --mp4, a peca lista tambem o MP4 com papel final e os PNGs com papel slide."
    criterio_aceite: "cd motor && uv run pytest tests/producao/apresentacao/test_producao.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.09, T-05.10]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-05.12
    titulo: "CLI de motion"
    fase: F-05.5
    status: pendente
    objetivo: "Expor produzir reel, produzir apresentacao, motion previa e motion render no CLI."
    arquivos:
      cria: [motor/src/expxmedia/cli_comandos/motion.py, motor/tests/test_cli_motion.py]
      altera: []
    teste_integracao: "Cada subcomando novo aparece no --help e produzir apresentacao na fixture em subprocesso sai 0 com o peca_id."
    teste_funcional: "produzir reel com roteiro de 100 palavras sai com codigo diferente de 0 e JSON citando a faixa 130 a 180."
    criterio_aceite: "cd motor && uv run pytest tests/test_cli_motion.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.11, T-05.06, T-05.04]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
---

# Tasks — Sprint 05

> Comando de teste: `cd motor && uv run pytest tests/motion tests/producao/test_reel.py tests/producao/test_carrossel_misto.py tests/producao/apresentacao tests/test_template_reel.py tests/test_cli_motion.py`. Base de conhecimento em `docs/nucleo-expxmedia/base/`; decisões em `00-DECISOES.md`. Nenhuma task escreve nos projetos de origem (D-37).

---

### T-05.01 — Kit base do Remotion

```yaml
id: T-05.01
titulo: Kit base do Remotion
fase: F-05.1
objetivo: Portar anim.ts, área segura e centralização, com FPS numa constante única, useAlma por props e SeloPerfil a partir do porta-voz e do canal da Alma.
arquivos:
  cria: [motor/kit-remotion/src/kit/constantes.ts, motor/kit-remotion/src/kit/anim.ts, motor/kit-remotion/src/kit/alma.tsx, motor/kit-remotion/src/kit/SeloPerfil.tsx, motor/kit-remotion/src/kit/fontes.ts, motor/kit-remotion/src/composicoes/TesteSelo/index.tsx, motor/tests/motion/test_kit.py]
  altera: []
teste_integracao: npx tsc --noEmit no kit termina sem erro e um still da composição de teste do selo é gerado.
teste_funcional: A busca pelo literal 30 como fps nos arquivos do kit encontra só constantes.ts.
criterio_aceite: `cd motor && uv run pytest tests/motion/test_kit.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-01.05]
paralelizavel: false
status: em_andamento
```

---

### T-05.02 — Montagem e trilha generalizadas

```yaml
id: T-05.02
titulo: Montagem e trilha generalizadas
fase: F-05.1
objetivo: Portar montar-reel.mjs e audio.mjs com caminhos por argumento, mesmo PRNG e semente, sem reescrever registro global (D-19).
arquivos:
  cria: [motor/kit-remotion/scripts/montar.mjs, motor/kit-remotion/scripts/audio.mjs, motor/tests/motion/test_montar.py]
  altera: []
teste_integracao: Montar o G2 a partir das mesmas entradas gera timeline.json igual ao golden e trilha.wav com o mesmo sha256.
teste_funcional: Uma âncora ausente da narração faz a montagem sair com erro citando a cena e a âncora.
criterio_aceite: `cd motor && uv run pytest tests/motion/test_montar.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.01, T-01.07]
paralelizavel: false
status: em_andamento
```

---

### T-05.03 — Runner Remotion multi-versao

```yaml
id: T-05.03
titulo: Runner Remotion multi-versao
fase: F-05.1
objetivo: Renderizar com o kit na 4.0.528 e, para outras versões, um projeto por versão em cache fora da instalação; cada render faz bundle só da composição pedida por um entry point próprio, com o browser compartilhado preparado na T-01.08, props JSON e timeout 1800 s; nenhum teste instala nada (D-17, D-46).
arquivos:
  cria: [motor/src/expxmedia/motion/remotion.py, motor/tests/motion/test_runner.py]
  altera: []
teste_integracao: Renderizar a composição Vazio por 2 s com props JSON gera MP4 de 60 quadros nesta máquina.
teste_funcional: Pedir a versão 4.0.522 resolve um diretório de cache diferente do da 4.0.528 sem instalar, e uma composição quebrada em outra pasta de src/composicoes não impede o render da composição pedida.
criterio_aceite: `cd motor && uv run pytest tests/motion/test_runner.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.01]
paralelizavel: true
status: em_andamento
```

---

### T-05.04 — Previa com guias

```yaml
id: T-05.04
titulo: Previa com guias
fase: F-05.1
objetivo: Gerar still a 60% de cada cena com as guias 220 e 1500 px.
arquivos:
  cria: [motor/src/expxmedia/motion/previa.py, motor/tests/motion/test_previa.py]
  altera: []
teste_integracao: Gerar prévia de uma linha do tempo de 3 cenas produz 3 imagens e uma folha com as três.
teste_funcional: Cada imagem de prévia tem pixels da cor das guias nas linhas y=220 e y=1500.
criterio_aceite: `cd motor && uv run pytest tests/motion/test_previa.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.03]
paralelizavel: false
status: em_andamento
```

---

### T-05.05 — Template de reel embarcado

```yaml
id: T-05.05
titulo: Template de reel embarcado
fase: F-05.2
objetivo: Criar um template de reel narrado em código Remotion sobre o kit, com cores e fontes da Alma (D-05, D-31).
arquivos:
  cria: [templates/reel/narrado-cartao/template.json, templates/reel/narrado-cartao/package.json, templates/reel/narrado-cartao/src/Composicao.tsx, templates/reel/narrado-cartao/src/cenas.tsx, templates/reel/narrado-cartao/cenas.json, templates/reel/narrado-cartao/exemplo.json, motor/tests/test_template_reel.py]
  altera: []
teste_integracao: O template renderiza com a Alma fictícia e o provedor de teste e passa no perfil reel da verificação.
teste_funcional: O template passa em template.validar no modo template sem nenhum achado.
criterio_aceite: `cd motor && uv run pytest tests/test_template_reel.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.02, T-05.03, T-02.12]
paralelizavel: false
status: pendente
```

---

### T-05.06 — Producao de reel narrado

```yaml
id: T-05.06
titulo: Producao de reel narrado
fase: F-05.2
objetivo: Produzir reel narrado em Remotion: gate de 130 a 180 palavras, narração uma vez, montagem, render, normalização da mistura, verificação no perfil reel (30 a 70 s) e peca.json (D-41).
arquivos:
  cria: [motor/src/expxmedia/producao/reel.py, motor/tests/producao/test_reel.py]
  altera: []
teste_integracao: Produzir um reel de 150 palavras com o provedor de teste a 3,5 palavras por segundo gera MP4 de 43 a 45 s aprovado no perfil reel e peça produzida.
teste_funcional: Um roteiro de 100 palavras é recusado antes de narrar e nenhuma chamada ao provedor acontece.
criterio_aceite: `cd motor && uv run pytest tests/producao/test_reel.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.05, T-04.05, T-04.06, T-04.02]
paralelizavel: false
status: pendente
```

---

### T-05.07 — Slide de video no carrossel

```yaml
id: T-05.07
titulo: Slide de video no carrossel
fase: F-05.3
objetivo: Permitir kind com midia video no carrossel, renderizado em Remotion no formato do carrossel a partir de uma composição do kit, registrado na peça (D-06).
arquivos:
  cria: [motor/kit-remotion/src/composicoes/SlideVideo/index.tsx, motor/tests/producao/test_carrossel_misto.py]
  altera: [motor/src/expxmedia/producao/carrossel.py]
teste_integracao: Um carrossel com slide 1 de vídeo e 2 de imagem gera slide_01.mp4 4:5 e dois PNGs.
teste_funcional: A peça registra slides[0].midia video com duracao_s preenchida e slides[1].midia imagem com duracao_s null.
criterio_aceite: `cd motor && uv run pytest tests/producao/test_carrossel_misto.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.03, T-03.12]
paralelizavel: true
status: pendente
```

---

### T-05.08 — Deck da apresentacao

```yaml
id: T-05.08
titulo: Deck da apresentacao
fase: F-05.4
objetivo: Portar o schema do deck.json e sua validação sem CTA fixo.
arquivos:
  cria: [motor/src/expxmedia/producao/apresentacao/deck.py, motor/tests/producao/apresentacao/test_deck.py]
  altera: []
teste_integracao: O deck do G6 convertido para o schema do núcleo valida sem achado.
teste_funcional: Um slide com tipo desconhecido devolve achado citando os tipos aceitos.
criterio_aceite: `cd motor && uv run pytest tests/producao/apresentacao/test_deck.py` termina com 0 failed
depende_de: [T-01.07, T-02.11]
paralelizavel: true
status: pendente
```

---

### T-05.09 — Palco HTML navegavel

```yaml
id: T-05.09
titulo: Palco HTML navegavel
fase: F-05.4
objetivo: Gerar apresentacao.html autocontida e navegável por teclado, com tokens e fontes da Alma.
arquivos:
  cria: [motor/src/expxmedia/producao/apresentacao/palco.py, motor/src/expxmedia/recursos/palco.html, motor/tests/producao/apresentacao/test_palco.py]
  altera: []
teste_integracao: Abrir o HTML gerado no Playwright e pressionar seta direita avança do slide 1 para o 2.
teste_funcional: O HTML gerado não referencia nenhuma URL externa e contém as variáveis --alma-*.
criterio_aceite: `cd motor && uv run pytest tests/producao/apresentacao/test_palco.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.08, T-02.10]
paralelizavel: false
status: pendente
```

---

### T-05.10 — Cenas e render da apresentacao

```yaml
id: T-05.10
titulo: Cenas e render da apresentacao
fase: F-05.4
objetivo: Portar as cenas da apresentação para o kit e renderizar MP4 e PNG por slide.
arquivos:
  cria: [motor/kit-remotion/src/composicoes/Apresentacao/index.tsx, motor/kit-remotion/src/composicoes/Apresentacao/cenas.tsx, motor/src/expxmedia/producao/apresentacao/render.py, motor/tests/producao/apresentacao/test_render.py]
  altera: []
teste_integracao: Renderizar um deck de 3 slides gera MP4 16:9 e 3 PNGs nesta máquina.
teste_funcional: Cada tipo de slide do schema tem componente registrado nas cenas do kit.
criterio_aceite: `cd motor && uv run pytest tests/producao/apresentacao/test_render.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.08, T-05.03]
paralelizavel: false
status: pendente
```

---

### T-05.11 — Template e producao de apresentacao

```yaml
id: T-05.11
titulo: Template e producao de apresentacao
fase: F-05.4
objetivo: Criar o template de apresentação embarcado e a produção que gera HTML, e opcionalmente MP4, com peca.json.
arquivos:
  cria: [templates/apresentacao/padrao/template.json, templates/apresentacao/padrao/template.css, templates/apresentacao/padrao/exemplo.json, motor/src/expxmedia/producao/apresentacao/producao.py, motor/tests/producao/apresentacao/test_producao.py]
  altera: []
teste_integracao: Produzir uma apresentação na fixture gera apresentacao.html com papel final e peça produzida.
teste_funcional: Com --mp4, a peça lista também o MP4 com papel final e os PNGs com papel slide.
criterio_aceite: `cd motor && uv run pytest tests/producao/apresentacao/test_producao.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.09, T-05.10]
paralelizavel: false
status: pendente
```

---

### T-05.12 — CLI de motion

```yaml
id: T-05.12
titulo: CLI de motion
fase: F-05.5
objetivo: Expor produzir reel, produzir apresentacao, motion previa e motion render no CLI.
arquivos:
  cria: [motor/src/expxmedia/cli_comandos/motion.py, motor/tests/test_cli_motion.py]
  altera: []
teste_integracao: Cada subcomando novo aparece no --help e produzir apresentacao na fixture em subprocesso sai 0 com o peca_id.
teste_funcional: produzir reel com roteiro de 100 palavras sai com código diferente de 0 e JSON citando a faixa 130 a 180.
criterio_aceite: `cd motor && uv run pytest tests/test_cli_motion.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.11, T-05.06, T-05.04]
paralelizavel: false
status: pendente
```
