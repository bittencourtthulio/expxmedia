---
expx_schema: 1
expx_tool: sprintx
kind: tasks
trabalho_id: nucleo-expxmedia
sprint_id: sprint-09
atualizado_em: 2026-09-25
tasks:
  - id: T-09.01
    titulo: "Manifesto do plugin e hooks de portao e segredo"
    fase: F-09.1
    status: em_andamento
    objetivo: "Criar o plugin expxmedia com hooks: portao no UserPromptSubmit que injeta a instrucao de Alma/ambiente e segredo que bloqueia .env e tokens (D-33)."
    arquivos:
      cria: [nucleo/.claude-plugin/plugin.json, nucleo/hooks/hooks.json, nucleo/hooks/expxmedia-portao.sh, nucleo/hooks/expxmedia-segredo.sh, motor/tests/plugin/test_hooks.py]
      altera: []
    teste_integracao: "claude plugin validate nucleo termina com codigo 0 e o hook de segredo recebendo payload de Read em .env sai com codigo 2 e motivo no stderr."
    teste_funcional: "O hook de portao numa instalacao sem alma.json imprime additionalContext citando /expxmedia:alma e sai 0."
    criterio_aceite: "cd motor && uv run pytest tests/plugin/test_hooks.py termina com 0 failed"
    depende_de: [T-02.10]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-09.10
    titulo: "Revisao mecanica de copy"
    fase: F-09.1
    status: em_andamento
    objetivo: "Criar o subcomando revisar copy com os bloqueantes mecanizaveis parametrizados pela Alma: travessao quando a regra da Alma proibe, tratamento diferente de voz.tratamento, palavras_proibidas, palavra-chave do CTA diferente da publicacao e abertura repetida em 14 dias contra as pecas da instalacao."
    arquivos:
      cria: [motor/src/expxmedia/revisar/copy.py, motor/src/expxmedia/cli_comandos/revisar.py, motor/tests/test_revisar_copy.py]
      altera: []
    teste_integracao: "expxmedia-motor revisar copy numa instalacao com uma peca de 5 dias atras com a mesma abertura devolve o bloqueante abertura_repetida."
    teste_funcional: "Um texto com tu numa Alma de tratamento voce e uma palavra proibida devolve os dois bloqueantes com a posicao de cada um."
    criterio_aceite: "cd motor && uv run pytest tests/test_revisar_copy.py termina com 0 failed"
    depende_de: [T-02.14, T-02.11]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-09.11
    titulo: "Ancoras de inteligencia"
    fase: F-09.1
    status: em_andamento
    objetivo: "Extrair das regras e skills de origem listas-ancora por skill (bloqueantes, duas passadas, 6 partes do roteiro, teste das dez palavras, 9 secoes da leitura, checklist de parecenca, red flags, perguntas do corte) em fixtures sem marca, com o teste que exige cada item na skill ou no agente correspondente."
    arquivos:
      cria: [motor/tests/fixtures/inteligencia/criar-carrossel.json, motor/tests/fixtures/inteligencia/criar-reel.json, motor/tests/fixtures/inteligencia/reel-por-referencia.json, motor/tests/fixtures/inteligencia/cortar-video.json, motor/tests/fixtures/inteligencia/criar-aula.json, motor/tests/fixtures/inteligencia/revisor-reel.json, motor/tests/plugin/test_ancoras.py]
      altera: []
    teste_integracao: "O teste valida so as fixtures e o verificador (a presenca nas skills e cobrada pelos test_skill_* da F-09.2); cada fixture cita, por item, o arquivo:linha de origem e atinge o minimo por categoria: reel-por-referencia com as 9 secoes da leitura, os itens do checklist de parecenca e as red flags de base/inteligencia-reel-recriado.md; criar-reel com as 6 partes do roteiro e o teste das dez palavras; criar-carrossel com as duas passadas e os bloqueantes de base/inteligencia-editorial-carrossel.md; cortar-video com as perguntas do corte; criar-aula com a ordem do pipeline e o avatar pelo audio; revisor-reel com a veracidade dos beats 2 a 6 com a linha da fonte, o frame da abertura como bloqueante (rosto, cartao fora do rosto, selo igual ao cta.txt) e o veredito PUBLICAR/SEGURAR."
    teste_funcional: "Com uma skill de teste que omite um item de ancora, o verificador aponta exatamente o item faltante."
    criterio_aceite: "cd motor && uv run pytest tests/plugin/test_ancoras.py termina com 0 failed"
    depende_de: [T-01.06]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-09.02
    titulo: "Extracao de site para a Alma"
    fase: F-09.1
    status: em_andamento
    objetivo: "Extrair do site nome, descricao, meta, cores do CSS e do logo, logo e textos das paginas de sobre e produtos, sem inventar campo."
    arquivos:
      cria: [motor/src/expxmedia/alma/site.py, motor/tests/alma/test_site.py, motor/tests/fixtures/site-ficticio/index.html]
      altera: []
    teste_integracao: "Contra o site ficticio servido pelo stub, a extracao baixa o logo para alma/assets e propoe cores nos papeis."
    teste_funcional: "Campos sem evidencia no site saem null e entram em pendencias da proposta."
    criterio_aceite: "cd motor && uv run pytest tests/alma/test_site.py termina com 0 failed"
    depende_de: [T-02.09, T-01.04]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-09.03
    titulo: "Skills de Alma e ambiente"
    fase: F-09.1
    status: em_andamento
    objetivo: "Escrever as skills e comandos /expxmedia:alma (site, entrevista, confirmo tudo) e /expxmedia:ambiente (orientacao por capacidade, chave no arquivo)."
    arquivos:
      cria: [nucleo/skills/alma/SKILL.md, nucleo/skills/ambiente/SKILL.md, nucleo/commands/alma.md, nucleo/commands/ambiente.md, motor/tests/plugin/test_estrutura.py]
      altera: []
    teste_integracao: "Todo comando expxmedia-motor citado nas skills existe no --help do CLI."
    teste_funcional: "Cada SKILL.md tem frontmatter com name e description e o nome bate com a pasta."
    criterio_aceite: "cd motor && uv run pytest tests/plugin/test_estrutura.py termina com 0 failed"
    depende_de: [T-09.01, T-09.02, T-02.14, T-09.10]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-09.04
    titulo: "Skills de post e carrossel com agentes"
    fase: F-09.2
    status: pendente
    objetivo: "Portar a inteligencia editorial de carrossel (duas passadas copy e revisao, bloqueantes mecanizaveis, validacao de imagem) como skills criar-post e criar-carrossel e agentes, lendo voz e regras da Alma."
    arquivos:
      cria: [nucleo/skills/criar-post/SKILL.md, nucleo/skills/criar-carrossel/SKILL.md, nucleo/agents/copywriter.md, nucleo/agents/revisor-editorial.md, nucleo/agents/validador-imagem.md, motor/tests/plugin/test_skill_estatica.py]
      altera: []
    teste_integracao: "Os agentes de revisao e validacao declaram tools so de leitura e a varredura de marca passa nos arquivos novos."
    teste_funcional: "A skill criar-carrossel cita o portao, a leitura da Alma, a busca na galeria, a verificacao de requisitos, revisar copy e o registro da peca, nessa ordem, e contem todos os itens da fixture de ancoras de criar-carrossel."
    criterio_aceite: "cd motor && uv run pytest tests/plugin/test_skill_estatica.py tests/plugin/test_ancoras.py tests/test_marca.py termina com 0 failed"
    depende_de: [T-09.03, T-03.13, T-09.11]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-09.05
    titulo: "Skills de reel narrado e de pagina com roteirista e revisor"
    fase: F-09.2
    status: pendente
    objetivo: "Portar roteiro em 6 partes, teste das dez palavras, veracidade e escolha da palavra do CTA como skill criar-reel (Remotion) e skill reel-de-pagina (captura antes do roteiro com site.md como lastro, quando usar abertura), o agente roteirista e o agente revisor-reel so leitura com o roteiro de auditoria da origem."
    arquivos:
      cria: [nucleo/skills/criar-reel/SKILL.md, nucleo/skills/reel-de-pagina/SKILL.md, nucleo/agents/roteirista.md, nucleo/agents/revisor-reel.md, motor/tests/plugin/test_skill_reel.py]
      altera: []
    teste_integracao: "A skill criar-reel referencia apenas subcomandos existentes do CLI e a varredura de marca passa."
    teste_funcional: "As skills e o roteirista contem todos os itens da fixture criar-reel, o revisor-reel contem todos os itens da fixture revisor-reel e declara tools so de leitura, e reel-de-pagina cita produzir reel-pagina e produzir abertura."
    criterio_aceite: "cd motor && uv run pytest tests/plugin/test_skill_reel.py tests/plugin/test_ancoras.py tests/test_marca.py termina com 0 failed"
    depende_de: [T-09.03, T-05.12, T-09.11, T-04.13, T-06.09]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-09.06
    titulo: "Skill de reel por referencia com revisor"
    fase: F-09.2
    status: pendente
    objetivo: "Portar a skill do recriado sob medida: 8 passos, tabela do que se imita, leitura das folhas em 9 secoes, 3 voltas de previa, checklist de parecenca e revisor que conhece o formato."
    arquivos:
      cria: [nucleo/skills/reel-por-referencia/SKILL.md, nucleo/skills/reel-por-referencia/regras.md, nucleo/agents/revisor-video.md, motor/tests/plugin/test_skill_referencia.py]
      altera: []
    teste_integracao: "O revisor-video declara tools so de leitura e cita o perfil sob_medida e o checklist de parecenca."
    teste_funcional: "A skill, as regras e o revisor juntos contem todos os itens da fixture de ancoras de reel-por-referencia, e a sequencia analisar, folhas, roteiro, narrar, codigo, previa, render, verificar, revisar aparece nessa ordem."
    criterio_aceite: "cd motor && uv run pytest tests/plugin/test_skill_referencia.py tests/plugin/test_ancoras.py tests/test_marca.py termina com 0 failed"
    depende_de: [T-09.03, T-06.09, T-09.11]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-09.07
    titulo: "Skills de corte, apresentacao e aula"
    fase: F-09.2
    status: pendente
    objetivo: "Escrever as skills cortar-video, criar-apresentacao e criar-aula com a ordem de dependencias de cada pipeline."
    arquivos:
      cria: [nucleo/skills/cortar-video/SKILL.md, nucleo/skills/criar-apresentacao/SKILL.md, nucleo/skills/criar-aula/SKILL.md, motor/tests/plugin/test_skill_corte_aula.py]
      altera: []
    teste_integracao: "As tres skills referenciam apenas subcomandos existentes do CLI e a varredura de marca passa."
    teste_funcional: "As skills cortar-video e criar-aula contem todos os itens das fixtures de ancoras correspondentes, inclusive gerar o avatar a partir do audio e nunca do texto."
    criterio_aceite: "cd motor && uv run pytest tests/plugin/test_skill_corte_aula.py tests/plugin/test_ancoras.py tests/test_marca.py termina com 0 failed"
    depende_de: [T-09.03, T-06.09, T-07.07, T-05.12, T-09.11]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-09.08
    titulo: "Skill de publicacao"
    fase: F-09.2
    status: pendente
    objetivo: "Escrever a skill publicar com dry-run obrigatorio antes, provedor pela verificacao e explicacao das diferencas entre Expx Flow e Graph."
    arquivos:
      cria: [nucleo/skills/publicar/SKILL.md, nucleo/agents/publicador.md, motor/tests/plugin/test_skill_publicar.py]
      altera: []
    teste_integracao: "A skill referencia apenas subcomandos existentes do CLI e a varredura de marca passa."
    teste_funcional: "A skill instrui rodar dry-run antes de publicar e proibe retentar publicacao que falhou sem nova ordem."
    criterio_aceite: "cd motor && uv run pytest tests/plugin/test_skill_publicar.py tests/test_marca.py termina com 0 failed"
    depende_de: [T-09.03, T-08.07]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
---

# Tasks — Sprint 09

> Comando de teste: `cd motor && uv run pytest`. Base de conhecimento em `docs/nucleo-expxmedia/base/`; decisões em `00-DECISOES.md`. Nenhuma task escreve nos projetos de origem (D-37).

---

### T-09.01 — Manifesto do plugin e hooks de portao e segredo

```yaml
id: T-09.01
titulo: Manifesto do plugin e hooks de portao e segredo
fase: F-09.1
objetivo: Criar o plugin expxmedia com hooks: portão no UserPromptSubmit que injeta a instrução de Alma/ambiente e segredo que bloqueia .env e tokens (D-33).
arquivos:
  cria: [nucleo/.claude-plugin/plugin.json, nucleo/hooks/hooks.json, nucleo/hooks/expxmedia-portao.sh, nucleo/hooks/expxmedia-segredo.sh, motor/tests/plugin/test_hooks.py]
  altera: []
teste_integracao: claude plugin validate nucleo termina com código 0 e o hook de segredo recebendo payload de Read em .env sai com código 2 e motivo no stderr.
teste_funcional: O hook de portão numa instalação sem alma.json imprime additionalContext citando /expxmedia:alma e sai 0.
criterio_aceite: `cd motor && uv run pytest tests/plugin/test_hooks.py` termina com 0 failed
depende_de: [T-02.10]
paralelizavel: false
status: em_andamento
```

---

### T-09.10 — Revisao mecanica de copy

```yaml
id: T-09.10
titulo: Revisao mecanica de copy
fase: F-09.1
objetivo: Criar o subcomando revisar copy com os bloqueantes mecanizáveis parametrizados pela Alma: travessão quando a regra da Alma proíbe, tratamento diferente de voz.tratamento, palavras_proibidas, palavra-chave do CTA diferente da publicação e abertura repetida em 14 dias contra as peças da instalação.
arquivos:
  cria: [motor/src/expxmedia/revisar/copy.py, motor/src/expxmedia/cli_comandos/revisar.py, motor/tests/test_revisar_copy.py]
  altera: []
teste_integracao: expxmedia-motor revisar copy numa instalação com uma peça de 5 dias atrás com a mesma abertura devolve o bloqueante abertura_repetida.
teste_funcional: Um texto com tu numa Alma de tratamento voce e uma palavra proibida devolve os dois bloqueantes com a posição de cada um.
criterio_aceite: `cd motor && uv run pytest tests/test_revisar_copy.py` termina com 0 failed
depende_de: [T-02.14, T-02.11]
paralelizavel: true
status: em_andamento
```

---

### T-09.11 — Ancoras de inteligencia

```yaml
id: T-09.11
titulo: Ancoras de inteligencia
fase: F-09.1
objetivo: Extrair das regras e skills de origem listas-âncora por skill (bloqueantes, duas passadas, 6 partes do roteiro, teste das dez palavras, 9 seções da leitura, checklist de parecença, red flags, perguntas do corte) em fixtures sem marca, com o teste que exige cada item na skill ou no agente correspondente.
arquivos:
  cria: [motor/tests/fixtures/inteligencia/criar-carrossel.json, motor/tests/fixtures/inteligencia/criar-reel.json, motor/tests/fixtures/inteligencia/reel-por-referencia.json, motor/tests/fixtures/inteligencia/cortar-video.json, motor/tests/fixtures/inteligencia/criar-aula.json, motor/tests/fixtures/inteligencia/revisor-reel.json, motor/tests/plugin/test_ancoras.py]
  altera: []
teste_integracao: O teste valida só as fixtures e o verificador (a presença nas skills é cobrada pelos test_skill_* da F-09.2); cada fixture cita, por item, o arquivo:linha de origem e atinge o mínimo por categoria: reel-por-referencia com as 9 seções da leitura, os itens do checklist de parecença e as red flags de base/inteligencia-reel-recriado.md; criar-reel com as 6 partes do roteiro e o teste das dez palavras; criar-carrossel com as duas passadas e os bloqueantes de base/inteligencia-editorial-carrossel.md; cortar-video com as perguntas do corte; criar-aula com a ordem do pipeline e o avatar pelo áudio; revisor-reel com a veracidade dos beats 2 a 6 com a linha da fonte, o frame da abertura como bloqueante (rosto, cartão fora do rosto, selo igual ao cta.txt) e o veredito PUBLICAR/SEGURAR.
teste_funcional: Com uma skill de teste que omite um item de âncora, o verificador aponta exatamente o item faltante.
criterio_aceite: `cd motor && uv run pytest tests/plugin/test_ancoras.py` termina com 0 failed
depende_de: [T-01.06]
paralelizavel: true
status: em_andamento
```

---

### T-09.02 — Extracao de site para a Alma

```yaml
id: T-09.02
titulo: Extracao de site para a Alma
fase: F-09.1
objetivo: Extrair do site nome, descrição, meta, cores do CSS e do logo, logo e textos das páginas de sobre e produtos, sem inventar campo.
arquivos:
  cria: [motor/src/expxmedia/alma/site.py, motor/tests/alma/test_site.py, motor/tests/fixtures/site-ficticio/index.html]
  altera: []
teste_integracao: Contra o site fictício servido pelo stub, a extração baixa o logo para alma/assets e propõe cores nos papéis.
teste_funcional: Campos sem evidência no site saem null e entram em pendencias da proposta.
criterio_aceite: `cd motor && uv run pytest tests/alma/test_site.py` termina com 0 failed
depende_de: [T-02.09, T-01.04]
paralelizavel: true
status: em_andamento
```

---

### T-09.03 — Skills de Alma e ambiente

```yaml
id: T-09.03
titulo: Skills de Alma e ambiente
fase: F-09.1
objetivo: Escrever as skills e comandos /expxmedia:alma (site, entrevista, confirmo tudo) e /expxmedia:ambiente (orientação por capacidade, chave no arquivo).
arquivos:
  cria: [nucleo/skills/alma/SKILL.md, nucleo/skills/ambiente/SKILL.md, nucleo/commands/alma.md, nucleo/commands/ambiente.md, motor/tests/plugin/test_estrutura.py]
  altera: []
teste_integracao: Todo comando expxmedia-motor citado nas skills existe no --help do CLI.
teste_funcional: Cada SKILL.md tem frontmatter com name e description e o nome bate com a pasta.
criterio_aceite: `cd motor && uv run pytest tests/plugin/test_estrutura.py` termina com 0 failed
depende_de: [T-09.01, T-09.02, T-02.14, T-09.10]
paralelizavel: false
status: em_andamento
```

---

### T-09.04 — Skills de post e carrossel com agentes

```yaml
id: T-09.04
titulo: Skills de post e carrossel com agentes
fase: F-09.2
objetivo: Portar a inteligência editorial de carrossel (duas passadas copy e revisão, bloqueantes mecanizáveis, validação de imagem) como skills criar-post e criar-carrossel e agentes, lendo voz e regras da Alma.
arquivos:
  cria: [nucleo/skills/criar-post/SKILL.md, nucleo/skills/criar-carrossel/SKILL.md, nucleo/agents/copywriter.md, nucleo/agents/revisor-editorial.md, nucleo/agents/validador-imagem.md, motor/tests/plugin/test_skill_estatica.py]
  altera: []
teste_integracao: Os agentes de revisão e validação declaram tools só de leitura e a varredura de marca passa nos arquivos novos.
teste_funcional: A skill criar-carrossel cita o portão, a leitura da Alma, a busca na galeria, a verificação de requisitos, revisar copy e o registro da peça, nessa ordem, e contém todos os itens da fixture de âncoras de criar-carrossel.
criterio_aceite: `cd motor && uv run pytest tests/plugin/test_skill_estatica.py tests/plugin/test_ancoras.py tests/test_marca.py` termina com 0 failed
depende_de: [T-09.03, T-03.13, T-09.11]
paralelizavel: true
status: pendente
```

---

### T-09.05 — Skills de reel narrado e de pagina com roteirista e revisor

```yaml
id: T-09.05
titulo: Skills de reel narrado e de pagina com roteirista e revisor
fase: F-09.2
objetivo: Portar roteiro em 6 partes, teste das dez palavras, veracidade e escolha da palavra do CTA como skill criar-reel (Remotion) e skill reel-de-pagina (captura antes do roteiro com site.md como lastro, quando usar abertura), o agente roteirista e o agente revisor-reel só leitura com o roteiro de auditoria da origem.
arquivos:
  cria: [nucleo/skills/criar-reel/SKILL.md, nucleo/skills/reel-de-pagina/SKILL.md, nucleo/agents/roteirista.md, nucleo/agents/revisor-reel.md, motor/tests/plugin/test_skill_reel.py]
  altera: []
teste_integracao: A skill criar-reel referencia apenas subcomandos existentes do CLI e a varredura de marca passa.
teste_funcional: As skills e o roteirista contêm todos os itens da fixture criar-reel, o revisor-reel contém todos os itens da fixture revisor-reel e declara tools só de leitura, e reel-de-pagina cita produzir reel-pagina e produzir abertura.
criterio_aceite: `cd motor && uv run pytest tests/plugin/test_skill_reel.py tests/plugin/test_ancoras.py tests/test_marca.py` termina com 0 failed
depende_de: [T-09.03, T-05.12, T-09.11, T-04.13, T-06.09]
paralelizavel: true
status: pendente
```

---

### T-09.06 — Skill de reel por referencia com revisor

```yaml
id: T-09.06
titulo: Skill de reel por referencia com revisor
fase: F-09.2
objetivo: Portar a skill do recriado sob medida: 8 passos, tabela do que se imita, leitura das folhas em 9 seções, 3 voltas de prévia, checklist de parecença e revisor que conhece o formato.
arquivos:
  cria: [nucleo/skills/reel-por-referencia/SKILL.md, nucleo/skills/reel-por-referencia/regras.md, nucleo/agents/revisor-video.md, motor/tests/plugin/test_skill_referencia.py]
  altera: []
teste_integracao: O revisor-video declara tools só de leitura e cita o perfil sob_medida e o checklist de parecença.
teste_funcional: A skill, as regras e o revisor juntos contêm todos os itens da fixture de âncoras de reel-por-referencia, e a sequência analisar, folhas, roteiro, narrar, código, prévia, render, verificar, revisar aparece nessa ordem.
criterio_aceite: `cd motor && uv run pytest tests/plugin/test_skill_referencia.py tests/plugin/test_ancoras.py tests/test_marca.py` termina com 0 failed
depende_de: [T-09.03, T-06.09, T-09.11]
paralelizavel: true
status: pendente
```

---

### T-09.07 — Skills de corte, apresentacao e aula

```yaml
id: T-09.07
titulo: Skills de corte, apresentacao e aula
fase: F-09.2
objetivo: Escrever as skills cortar-video, criar-apresentacao e criar-aula com a ordem de dependências de cada pipeline.
arquivos:
  cria: [nucleo/skills/cortar-video/SKILL.md, nucleo/skills/criar-apresentacao/SKILL.md, nucleo/skills/criar-aula/SKILL.md, motor/tests/plugin/test_skill_corte_aula.py]
  altera: []
teste_integracao: As três skills referenciam apenas subcomandos existentes do CLI e a varredura de marca passa.
teste_funcional: As skills cortar-video e criar-aula contêm todos os itens das fixtures de âncoras correspondentes, inclusive gerar o avatar a partir do áudio e nunca do texto.
criterio_aceite: `cd motor && uv run pytest tests/plugin/test_skill_corte_aula.py tests/plugin/test_ancoras.py tests/test_marca.py` termina com 0 failed
depende_de: [T-09.03, T-06.09, T-07.07, T-05.12, T-09.11]
paralelizavel: true
status: pendente
```

---

### T-09.08 — Skill de publicacao

```yaml
id: T-09.08
titulo: Skill de publicacao
fase: F-09.2
objetivo: Escrever a skill publicar com dry-run obrigatório antes, provedor pela verificação e explicação das diferenças entre Expx Flow e Graph.
arquivos:
  cria: [nucleo/skills/publicar/SKILL.md, nucleo/agents/publicador.md, motor/tests/plugin/test_skill_publicar.py]
  altera: []
teste_integracao: A skill referencia apenas subcomandos existentes do CLI e a varredura de marca passa.
teste_funcional: A skill instrui rodar dry-run antes de publicar e proíbe retentar publicação que falhou sem nova ordem.
criterio_aceite: `cd motor && uv run pytest tests/plugin/test_skill_publicar.py tests/test_marca.py` termina com 0 failed
depende_de: [T-09.03, T-08.07]
paralelizavel: true
status: pendente
```
