---
expx_schema: 1
expx_tool: sprintx
kind: tasks
trabalho_id: nucleo-expxmedia
sprint_id: sprint-03
atualizado_em: 2026-09-24
tasks:
  - id: T-03.01
    titulo: "Render HTML sem JS e sem rede"
    fase: F-03.1
    status: pendente
    objetivo: "Portar a base do galeria.renderizar: Playwright com JavaScript desligado, rede bloqueada exceto fontes do cache, canvas do template (D-20)."
    arquivos:
      cria: [motor/src/expxmedia/render_html/renderizar.py, motor/tests/render_html/test_renderizar.py]
      altera: []
    teste_integracao: "Renderizar um HTML de 1080x1350 gera PNG com essas dimensoes nesta maquina."
    teste_funcional: "Um HTML com script que troca o texto e uma imagem remota sai com o texto original e sem a imagem remota."
    criterio_aceite: "cd motor && uv run pytest tests/render_html/test_renderizar.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-02.10]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-03.02
    titulo: "Encaixe de texto"
    fase: F-03.1
    status: pendente
    objetivo: "Portar o encaixe com os mesmos numeros: 0,96 por rodada, zoom 0,8 a 1,3, fonte minima 28 px e piso 18 px para miudo, faixa vazia de 22%."
    arquivos:
      cria: [motor/src/expxmedia/render_html/encaixe.py, motor/tests/render_html/test_encaixe.py]
      altera: []
    teste_integracao: "O encaixe aplicado ao layout do G1 produz as mesmas medidas finais gravadas no render.json do golden."
    teste_funcional: "Um slot com texto tres vezes maior que o espaco encolhe ate o piso e devolve achado fonte_abaixo_do_minimo."
    criterio_aceite: "cd motor && uv run pytest tests/render_html/test_encaixe.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-03.01, T-01.07]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-03.03
    titulo: "Contraste medido no PNG"
    fase: F-03.1
    status: pendente
    objetivo: "Portar a medicao de contraste no PNG, com e sem a tinta do texto, no pior ponto do fundo, com as excecoes data-sobre e decorativo."
    arquivos:
      cria: [motor/src/expxmedia/render_html/contraste.py, motor/tests/render_html/test_contraste.py]
      altera: []
    teste_integracao: "O layout do G1 renderizado com a alma-golden nao gera achado de contraste."
    teste_funcional: "Um par texto/fundo de razao 2,8:1 devolve achado e um par de razao 3,2:1 nao devolve."
    criterio_aceite: "cd motor && uv run pytest tests/render_html/test_contraste.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-03.01]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-03.04
    titulo: "Prancha e render.json"
    fase: F-03.1
    status: pendente
    objetivo: "Portar a prancha de slides e o render.json com impressao digital da renderizacao."
    arquivos:
      cria: [motor/src/expxmedia/render_html/prancha.py, motor/tests/render_html/test_prancha.py]
      altera: []
    teste_integracao: "Renderizar tres slides gera _prancha.png com os tres lado a lado e render.json com um registro por slide."
    teste_funcional: "Renderizar duas vezes as mesmas entradas gera a mesma impressao digital no render.json."
    criterio_aceite: "cd motor && uv run pytest tests/render_html/test_prancha.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-03.01]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-03.05
    titulo: "Paridade HTML com o sistema atual"
    fase: F-03.1
    status: pendente
    objetivo: "Comparar o render do nucleo com o golden do sistema atual para as mesmas entradas (D-16)."
    arquivos:
      cria: [motor/tests/render_html/test_paridade.py]
      altera: []
    teste_integracao: "Cada slide do G1 renderizado pelo nucleo com a alma-golden e as fontes do golden difere do PNG golden em no maximo 1% dos pixels, contando como diferente so o pixel com algum canal acima de 8/255."
    teste_funcional: "A comparacao de um PNG com ele mesmo deslocado 10 px acusa diferenca acima do limite."
    criterio_aceite: "cd motor && uv run pytest tests/render_html/test_paridade.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-03.02, T-03.03, T-03.04]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-03.06
    titulo: "Pexels foto e video"
    fase: F-03.2
    status: pendente
    objetivo: "Unificar foto e video do Pexels na capacidade banco_imagens com PEXELS_API_KEY (D-28)."
    arquivos:
      cria: [motor/src/expxmedia/imagem/pexels.py, motor/tests/imagem/test_pexels.py]
      altera: []
    teste_integracao: "Contra o stub, buscar video vertical envia orientation=portrait e o cabecalho Authorization com a chave."
    teste_funcional: "Resposta 429 do stub devolve erro limite_excedido sem nova tentativa e resposta 200 devolve lista normalizada com id, url e dimensoes."
    criterio_aceite: "cd motor && uv run pytest tests/imagem/test_pexels.py termina com 0 failed"
    depende_de: [T-02.07, T-01.04]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-03.07
    titulo: "OpenRouter imagem"
    fase: F-03.2
    status: pendente
    objetivo: "Gerar imagem pelo OpenRouter com modelo e proporcao configuraveis."
    arquivos:
      cria: [motor/src/expxmedia/imagem/openrouter.py, motor/tests/imagem/test_openrouter.py]
      altera: []
    teste_integracao: "Contra o stub, a requisicao leva o modelo configurado e a proporcao pedida."
    teste_funcional: "Uma resposta com imagem em data URL base64 e gravada como PNG valido no caminho de saida."
    criterio_aceite: "cd motor && uv run pytest tests/imagem/test_openrouter.py termina com 0 failed"
    depende_de: [T-02.07, T-01.04]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-03.08
    titulo: "Higgsfield por CLI"
    fase: F-03.2
    status: pendente
    objetivo: "Chamar o CLI higgsfield para rosto_ia e video_ia validando parametros por model get antes (D-27)."
    arquivos:
      cria: [motor/src/expxmedia/imagem/higgsfield.py, motor/tests/imagem/test_higgsfield.py, motor/tests/stubs/higgsfield_falso.py]
      altera: []
    teste_integracao: "Com um executavel falso no PATH, gerar video_ia chama model get antes de generate."
    teste_funcional: "Um parametro ausente do esquema devolvido por model get e recusado antes de gerar."
    criterio_aceite: "cd motor && uv run pytest tests/imagem/test_higgsfield.py termina com 0 failed"
    depende_de: [T-02.07]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-03.09
    titulo: "Captura de pagina"
    fase: F-03.3
    status: pendente
    objetivo: "Capturar pagina com Playwright headless proprio: ocultar consentimento, cookies e overlays, secoes h1–h3 com posicao, site.md com o texto renderizado do DOM (minimo 1200 caracteres), rolagem e costura (D-25)."
    arquivos:
      cria: [motor/src/expxmedia/captura/pagina.py, motor/tests/captura/test_pagina.py]
      altera: []
    teste_integracao: "Capturar uma pagina do stub com banner de cookies gera tira sem o banner, site.md com o texto do corpo e a lista de secoes h1–h3 com y de cada uma."
    teste_funcional: "A tira costurada de uma pagina de 3000 px tem 3000 px de altura e uma pagina com menos de 1200 caracteres de texto devolve o erro de conteudo insuficiente."
    criterio_aceite: "cd motor && uv run pytest tests/captura/test_pagina.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-01.04, T-03.01]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-03.14
    titulo: "Retratos, filtros de banco e cota"
    fase: F-03.2
    status: pendente
    objetivo: "Portar o tratamento de retrato com rembg u2net (nunca u2netp), os filtros de banco (tamanho, pessoa no alt, duplicata), a regra de que o slot pessoa so aceita retrato do porta-voz com substituto desenhado, e a cota diaria por provedor que anota mesmo se falhar."
    arquivos:
      cria: [motor/src/expxmedia/imagem/retratos.py, motor/src/expxmedia/imagem/cota.py, motor/tests/imagem/test_retratos.py]
      altera: []
    teste_integracao: "Recortar o retrato do porta-voz da Alma ficticia com rembg u2net gera PNG com canal alfa e fundo transparente nesta maquina."
    teste_funcional: "Um slot pessoa numa Alma sem porta-voz recebe o substituto desenhado; uma chamada que falha incrementa a cota do dia; o modelo registrado e u2net; e cada filtro (tamanho minimo, pessoa no alt, duplicata) descarta o caso de teste dele."
    criterio_aceite: "cd motor && uv run pytest tests/imagem/test_retratos.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-03.06, T-02.10, T-01.08]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-03.10
    titulo: "Templates embarcados de post e carrossel"
    fase: F-03.3
    status: pendente
    objetivo: "Neutralizar ao menos um layout de post e um de carrossel dos atuais em templates com tokens --alma-* (D-31)."
    arquivos:
      cria: [templates/post_unico/numero-e-frase/template.json, templates/post_unico/numero-e-frase/template.css, templates/post_unico/numero-e-frase/slides/numero.html, templates/post_unico/numero-e-frase/exemplo.json, templates/carrossel/editorial/template.json, templates/carrossel/editorial/template.css, templates/carrossel/editorial/slides/capa.html, templates/carrossel/editorial/slides/conteudo.html, templates/carrossel/editorial/slides/cta.html, templates/carrossel/editorial/exemplo.json, motor/tests/test_templates_embarcados.py]
      altera: []
    teste_integracao: "Cada template embarcado renderizado com a Alma ficticia nao gera achado de validacao, de contraste nem de encaixe."
    teste_funcional: "Cada template embarcado passa em template.validar no modo template sem nenhum achado."
    criterio_aceite: "cd motor && uv run pytest tests/test_templates_embarcados.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-03.05, T-02.12]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-03.11
    titulo: "Producao de post unico"
    fase: F-03.3
    status: pendente
    objetivo: "Produzir post unico a partir de slots e template, com peca.json, PNG e eventos."
    arquivos:
      cria: [motor/src/expxmedia/producao/post.py, motor/tests/producao/test_post.py]
      altera: []
    teste_integracao: "Produzir um post na fixture gera o PNG em pecas/ e deixa a peca em status produzida com o evento geracao_concluida."
    teste_funcional: "Slots acima do max do template geram erro antes do render e nenhum arquivo em saida/."
    criterio_aceite: "cd motor && uv run pytest tests/producao/test_post.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-03.10, T-02.11]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-03.12
    titulo: "Producao de carrossel de imagem"
    fase: F-03.3
    status: pendente
    objetivo: "Produzir carrossel com slides, prancha e legenda.txt a partir de template e slots."
    arquivos:
      cria: [motor/src/expxmedia/producao/carrossel.py, motor/tests/producao/test_carrossel.py]
      altera: []
    teste_integracao: "Produzir um carrossel de 5 slides gera 5 PNGs, a prancha e peca.json com slides midia imagem na ordem."
    teste_funcional: "Um kind inexistente no template gera erro citando o kind e os kinds disponiveis."
    criterio_aceite: "cd motor && uv run pytest tests/producao/test_carrossel.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-03.10, T-02.11]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-03.13
    titulo: "CLI de producao estatica"
    fase: F-03.3
    status: pendente
    objetivo: "Expor produzir post, produzir carrossel, capturar pagina e imagem (pexels, openrouter, retrato) no CLI."
    arquivos:
      cria: [motor/src/expxmedia/cli_comandos/producao_estatica.py, motor/tests/test_cli_producao_estatica.py]
      altera: []
    teste_integracao: "expxmedia-motor produzir carrossel --entrada slots.json em subprocesso sai 0 e imprime o peca_id."
    teste_funcional: "Entrada JSON invalida sai com codigo 2 e mensagem que cita o campo."
    criterio_aceite: "cd motor && uv run pytest tests/test_cli_producao_estatica.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-03.11, T-03.12, T-02.14, T-03.09, T-03.14]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
---

# Tasks — Sprint 03

> Comando de teste: `cd motor && uv run pytest`. Base de conhecimento em `docs/nucleo-expxmedia/base/`; decisões em `00-DECISOES.md`. Nenhuma task escreve nos projetos de origem (D-37).

---

### T-03.01 — Render HTML sem JS e sem rede

```yaml
id: T-03.01
titulo: Render HTML sem JS e sem rede
fase: F-03.1
objetivo: Portar a base do galeria.renderizar: Playwright com JavaScript desligado, rede bloqueada exceto fontes do cache, canvas do template (D-20).
arquivos:
  cria: [motor/src/expxmedia/render_html/renderizar.py, motor/tests/render_html/test_renderizar.py]
  altera: []
teste_integracao: Renderizar um HTML de 1080x1350 gera PNG com essas dimensões nesta máquina.
teste_funcional: Um HTML com script que troca o texto e uma imagem remota sai com o texto original e sem a imagem remota.
criterio_aceite: `cd motor && uv run pytest tests/render_html/test_renderizar.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-02.10]
paralelizavel: false
status: pendente
```

---

### T-03.02 — Encaixe de texto

```yaml
id: T-03.02
titulo: Encaixe de texto
fase: F-03.1
objetivo: Portar o encaixe com os mesmos números: 0,96 por rodada, zoom 0,8 a 1,3, fonte mínima 28 px e piso 18 px para miúdo, faixa vazia de 22%.
arquivos:
  cria: [motor/src/expxmedia/render_html/encaixe.py, motor/tests/render_html/test_encaixe.py]
  altera: []
teste_integracao: O encaixe aplicado ao layout do G1 produz as mesmas medidas finais gravadas no render.json do golden.
teste_funcional: Um slot com texto três vezes maior que o espaço encolhe até o piso e devolve achado fonte_abaixo_do_minimo.
criterio_aceite: `cd motor && uv run pytest tests/render_html/test_encaixe.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-03.01, T-01.07]
paralelizavel: false
status: pendente
```

---

### T-03.03 — Contraste medido no PNG

```yaml
id: T-03.03
titulo: Contraste medido no PNG
fase: F-03.1
objetivo: Portar a medição de contraste no PNG, com e sem a tinta do texto, no pior ponto do fundo, com as exceções data-sobre e decorativo.
arquivos:
  cria: [motor/src/expxmedia/render_html/contraste.py, motor/tests/render_html/test_contraste.py]
  altera: []
teste_integracao: O layout do G1 renderizado com a alma-golden não gera achado de contraste.
teste_funcional: Um par texto/fundo de razão 2,8:1 devolve achado e um par de razão 3,2:1 não devolve.
criterio_aceite: `cd motor && uv run pytest tests/render_html/test_contraste.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-03.01]
paralelizavel: true
status: pendente
```

---

### T-03.04 — Prancha e render.json

```yaml
id: T-03.04
titulo: Prancha e render.json
fase: F-03.1
objetivo: Portar a prancha de slides e o render.json com impressão digital da renderização.
arquivos:
  cria: [motor/src/expxmedia/render_html/prancha.py, motor/tests/render_html/test_prancha.py]
  altera: []
teste_integracao: Renderizar três slides gera _prancha.png com os três lado a lado e render.json com um registro por slide.
teste_funcional: Renderizar duas vezes as mesmas entradas gera a mesma impressão digital no render.json.
criterio_aceite: `cd motor && uv run pytest tests/render_html/test_prancha.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-03.01]
paralelizavel: true
status: pendente
```

---

### T-03.05 — Paridade HTML com o sistema atual

```yaml
id: T-03.05
titulo: Paridade HTML com o sistema atual
fase: F-03.1
objetivo: Comparar o render do núcleo com o golden do sistema atual para as mesmas entradas (D-16).
arquivos:
  cria: [motor/tests/render_html/test_paridade.py]
  altera: []
teste_integracao: Cada slide do G1 renderizado pelo núcleo com a alma-golden e as fontes do golden difere do PNG golden em no máximo 1% dos pixels, contando como diferente só o pixel com algum canal acima de 8/255.
teste_funcional: A comparação de um PNG com ele mesmo deslocado 10 px acusa diferença acima do limite.
criterio_aceite: `cd motor && uv run pytest tests/render_html/test_paridade.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-03.02, T-03.03, T-03.04]
paralelizavel: false
status: pendente
```

---

### T-03.06 — Pexels foto e video

```yaml
id: T-03.06
titulo: Pexels foto e video
fase: F-03.2
objetivo: Unificar foto e vídeo do Pexels na capacidade banco_imagens com PEXELS_API_KEY (D-28).
arquivos:
  cria: [motor/src/expxmedia/imagem/pexels.py, motor/tests/imagem/test_pexels.py]
  altera: []
teste_integracao: Contra o stub, buscar vídeo vertical envia orientation=portrait e o cabeçalho Authorization com a chave.
teste_funcional: Resposta 429 do stub devolve erro limite_excedido sem nova tentativa e resposta 200 devolve lista normalizada com id, url e dimensões.
criterio_aceite: `cd motor && uv run pytest tests/imagem/test_pexels.py` termina com 0 failed
depende_de: [T-02.07, T-01.04]
paralelizavel: true
status: pendente
```

---

### T-03.07 — OpenRouter imagem

```yaml
id: T-03.07
titulo: OpenRouter imagem
fase: F-03.2
objetivo: Gerar imagem pelo OpenRouter com modelo e proporção configuráveis.
arquivos:
  cria: [motor/src/expxmedia/imagem/openrouter.py, motor/tests/imagem/test_openrouter.py]
  altera: []
teste_integracao: Contra o stub, a requisição leva o modelo configurado e a proporção pedida.
teste_funcional: Uma resposta com imagem em data URL base64 é gravada como PNG válido no caminho de saída.
criterio_aceite: `cd motor && uv run pytest tests/imagem/test_openrouter.py` termina com 0 failed
depende_de: [T-02.07, T-01.04]
paralelizavel: true
status: pendente
```

---

### T-03.08 — Higgsfield por CLI

```yaml
id: T-03.08
titulo: Higgsfield por CLI
fase: F-03.2
objetivo: Chamar o CLI higgsfield para rosto_ia e video_ia validando parâmetros por model get antes (D-27).
arquivos:
  cria: [motor/src/expxmedia/imagem/higgsfield.py, motor/tests/imagem/test_higgsfield.py, motor/tests/stubs/higgsfield_falso.py]
  altera: []
teste_integracao: Com um executável falso no PATH, gerar video_ia chama model get antes de generate.
teste_funcional: Um parâmetro ausente do esquema devolvido por model get é recusado antes de gerar.
criterio_aceite: `cd motor && uv run pytest tests/imagem/test_higgsfield.py` termina com 0 failed
depende_de: [T-02.07]
paralelizavel: true
status: pendente
```

---

### T-03.09 — Captura de pagina

```yaml
id: T-03.09
titulo: Captura de pagina
fase: F-03.3
objetivo: Capturar página com Playwright headless próprio: ocultar consentimento, cookies e overlays, seções h1–h3 com posição, site.md com o texto renderizado do DOM (mínimo 1200 caracteres), rolagem e costura (D-25).
arquivos:
  cria: [motor/src/expxmedia/captura/pagina.py, motor/tests/captura/test_pagina.py]
  altera: []
teste_integracao: Capturar uma página do stub com banner de cookies gera tira sem o banner, site.md com o texto do corpo e a lista de seções h1–h3 com y de cada uma.
teste_funcional: A tira costurada de uma página de 3000 px tem 3000 px de altura e uma página com menos de 1200 caracteres de texto devolve o erro de conteúdo insuficiente.
criterio_aceite: `cd motor && uv run pytest tests/captura/test_pagina.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-01.04, T-03.01]
paralelizavel: true
status: pendente
```

---

### T-03.14 — Retratos, filtros de banco e cota

```yaml
id: T-03.14
titulo: Retratos, filtros de banco e cota
fase: F-03.2
objetivo: Portar o tratamento de retrato com rembg u2net (nunca u2netp), os filtros de banco (tamanho, pessoa no alt, duplicata), a regra de que o slot pessoa só aceita retrato do porta-voz com substituto desenhado, e a cota diária por provedor que anota mesmo se falhar.
arquivos:
  cria: [motor/src/expxmedia/imagem/retratos.py, motor/src/expxmedia/imagem/cota.py, motor/tests/imagem/test_retratos.py]
  altera: []
teste_integracao: Recortar o retrato do porta-voz da Alma fictícia com rembg u2net gera PNG com canal alfa e fundo transparente nesta máquina.
teste_funcional: Um slot pessoa numa Alma sem porta-voz recebe o substituto desenhado; uma chamada que falha incrementa a cota do dia; o modelo registrado é u2net; e cada filtro (tamanho mínimo, pessoa no alt, duplicata) descarta o caso de teste dele.
criterio_aceite: `cd motor && uv run pytest tests/imagem/test_retratos.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-03.06, T-02.10, T-01.08]
paralelizavel: false
status: pendente
```

---

### T-03.10 — Templates embarcados de post e carrossel

```yaml
id: T-03.10
titulo: Templates embarcados de post e carrossel
fase: F-03.3
objetivo: Neutralizar ao menos um layout de post e um de carrossel dos atuais em templates com tokens --alma-* (D-31).
arquivos:
  cria: [templates/post_unico/numero-e-frase/template.json, templates/post_unico/numero-e-frase/template.css, templates/post_unico/numero-e-frase/slides/numero.html, templates/post_unico/numero-e-frase/exemplo.json, templates/carrossel/editorial/template.json, templates/carrossel/editorial/template.css, templates/carrossel/editorial/slides/capa.html, templates/carrossel/editorial/slides/conteudo.html, templates/carrossel/editorial/slides/cta.html, templates/carrossel/editorial/exemplo.json, motor/tests/test_templates_embarcados.py]
  altera: []
teste_integracao: Cada template embarcado renderizado com a Alma fictícia não gera achado de validação, de contraste nem de encaixe.
teste_funcional: Cada template embarcado passa em template.validar no modo template sem nenhum achado.
criterio_aceite: `cd motor && uv run pytest tests/test_templates_embarcados.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-03.05, T-02.12]
paralelizavel: false
status: pendente
```

---

### T-03.11 — Producao de post unico

```yaml
id: T-03.11
titulo: Producao de post unico
fase: F-03.3
objetivo: Produzir post único a partir de slots e template, com peca.json, PNG e eventos.
arquivos:
  cria: [motor/src/expxmedia/producao/post.py, motor/tests/producao/test_post.py]
  altera: []
teste_integracao: Produzir um post na fixture gera o PNG em pecas/ e deixa a peça em status produzida com o evento geracao_concluida.
teste_funcional: Slots acima do max do template geram erro antes do render e nenhum arquivo em saida/.
criterio_aceite: `cd motor && uv run pytest tests/producao/test_post.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-03.10, T-02.11]
paralelizavel: true
status: pendente
```

---

### T-03.12 — Producao de carrossel de imagem

```yaml
id: T-03.12
titulo: Producao de carrossel de imagem
fase: F-03.3
objetivo: Produzir carrossel com slides, prancha e legenda.txt a partir de template e slots.
arquivos:
  cria: [motor/src/expxmedia/producao/carrossel.py, motor/tests/producao/test_carrossel.py]
  altera: []
teste_integracao: Produzir um carrossel de 5 slides gera 5 PNGs, a prancha e peca.json com slides midia imagem na ordem.
teste_funcional: Um kind inexistente no template gera erro citando o kind e os kinds disponíveis.
criterio_aceite: `cd motor && uv run pytest tests/producao/test_carrossel.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-03.10, T-02.11]
paralelizavel: true
status: pendente
```

---

### T-03.13 — CLI de producao estatica

```yaml
id: T-03.13
titulo: CLI de producao estatica
fase: F-03.3
objetivo: Expor produzir post, produzir carrossel, capturar pagina e imagem (pexels, openrouter, retrato) no CLI.
arquivos:
  cria: [motor/src/expxmedia/cli_comandos/producao_estatica.py, motor/tests/test_cli_producao_estatica.py]
  altera: []
teste_integracao: expxmedia-motor produzir carrossel --entrada slots.json em subprocesso sai 0 e imprime o peca_id.
teste_funcional: Entrada JSON inválida sai com código 2 e mensagem que cita o campo.
criterio_aceite: `cd motor && uv run pytest tests/test_cli_producao_estatica.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-03.11, T-03.12, T-02.14, T-03.09, T-03.14]
paralelizavel: false
status: pendente
```
