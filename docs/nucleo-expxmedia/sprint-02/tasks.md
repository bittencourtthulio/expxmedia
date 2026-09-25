---
expx_schema: 1
expx_tool: sprintx
kind: tasks
trabalho_id: nucleo-expxmedia
sprint_id: sprint-02
atualizado_em: 2026-09-24
tasks:
  - id: T-02.01
    titulo: "Ids e tempo com fuso"
    fase: F-02.1
    status: pendente
    objetivo: "Gerar ids de peca e template, deduplicando contra as pecas existentes e os ids ja gerados no processo, e momentos ISO com o fuso da Alma (M5, M11)."
    arquivos:
      cria: [motor/src/expxmedia/nucleo/ids.py, motor/src/expxmedia/nucleo/tempo.py, motor/tests/nucleo/test_ids_tempo.py]
      altera: []
    teste_integracao: "Com a Alma ficticia em America/Sao_Paulo, agora() devolve momento com deslocamento -03:00."
    teste_funcional: "novo_peca_id para 2026-09-24 casa com ^P-20260924-[0-9A-F]{4}$ e 1000 chamadas nao repetem id."
    criterio_aceite: "cd motor && uv run pytest tests/nucleo/test_ids_tempo.py termina com 0 failed"
    depende_de: [T-01.03]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-02.02
    titulo: "Escrita atomica e JSONL com trava"
    fase: F-02.1
    status: pendente
    objetivo: "Portar a escrita atomica e o acrescimo com trava entre processos usando filelock (M15)."
    arquivos:
      cria: [motor/src/expxmedia/nucleo/arquivos.py, motor/tests/nucleo/test_arquivos.py]
      altera: []
    teste_integracao: "Oito processos acrescentando 100 linhas cada ao mesmo JSONL produzem 800 linhas JSON validas."
    teste_funcional: "gravar_json com objeto nao serializavel levanta erro e deixa o arquivo anterior intacto."
    criterio_aceite: "cd motor && uv run pytest tests/nucleo/test_arquivos.py termina com 0 failed"
    depende_de: [T-01.02]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-02.03
    titulo: "Rastro de eventos"
    fase: F-02.1
    status: pendente
    objetivo: "Gravar eventos com as doze chaves na ordem do CONTRATO-estado-eventos e extras declaradas depois."
    arquivos:
      cria: [motor/src/expxmedia/nucleo/rastro.py, motor/tests/nucleo/test_rastro.py]
      altera: []
    teste_integracao: "Um evento gravado em eventos/AAAA-MM.jsonl e relido com as doze chaves na ordem e ts com fuso."
    teste_funcional: "Registrar evento com chave extra nao declarada levanta erro e com extra declarada (segundos) grava a extra depois das doze."
    criterio_aceite: "cd motor && uv run pytest tests/nucleo/test_rastro.py termina com 0 failed"
    depende_de: [T-02.01, T-02.02]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-02.04
    titulo: "Raiz da instalacao e caminhos relativos"
    fase: F-02.1
    status: pendente
    objetivo: "Localizar a raiz da instalacao e converter caminhos para relativos (M9)."
    arquivos:
      cria: [motor/src/expxmedia/nucleo/raiz.py, motor/tests/nucleo/test_raiz.py]
      altera: []
    teste_integracao: "A partir de uma subpasta de pecas/ da fixture, encontrar_raiz devolve a pasta que contem alma/."
    teste_funcional: "relativo converte um caminho absoluto dentro da raiz em caminho relativo e recusa caminho fora da raiz."
    criterio_aceite: "cd motor && uv run pytest tests/nucleo/test_raiz.py termina com 0 failed"
    depende_de: [T-01.03]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-02.05
    titulo: "Leitor do .env"
    fase: F-02.2
    status: pendente
    objetivo: "Ler o .env da instalacao sem nunca expor valores em mensagens (M14)."
    arquivos:
      cria: [motor/src/expxmedia/ambiente/env.py, motor/tests/ambiente/test_env.py]
      altera: []
    teste_integracao: "Um erro provocado com chave presente mostra o nome da variavel e nao contem o valor em str nem repr."
    teste_funcional: "Um .env com comentario, aspas e linha vazia e lido como dicionario com os tres valores esperados."
    criterio_aceite: "cd motor && uv run pytest tests/ambiente/test_env.py termina com 0 failed"
    depende_de: [T-02.04]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-02.06
    titulo: "Catalogo de capacidades do nucleo"
    fase: F-02.2
    status: pendente
    objetivo: "Declarar as capacidades do nucleo, provedores e o que satisfaz cada um, incluindo derivadas e fornecidas por pack."
    arquivos:
      cria: [motor/src/expxmedia/ambiente/catalogo.py, motor/tests/ambiente/test_catalogo.py]
      altera: []
    teste_integracao: "Uma capacidade registrada como fornecida por pack aparece na consulta com os mesmos campos das do nucleo."
    teste_funcional: "O catalogo contem exatamente as capacidades do nucleo listadas em CONTRATO-capacidades.md, com legendar derivada de narrar ou transcrever."
    criterio_aceite: "cd motor && uv run pytest tests/ambiente/test_catalogo.py termina com 0 failed"
    depende_de: [T-02.05]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-02.07
    titulo: "Verificacao, como_habilitar e provedor padrao"
    fase: F-02.2
    status: pendente
    objetivo: "Responder se uma capacidade esta habilitada, por qual provedor e o que falta, respeitando PROVEDOR_* sem troca silenciosa (D-07)."
    arquivos:
      cria: [motor/src/expxmedia/ambiente/verificar.py, motor/tests/ambiente/test_verificar.py]
      altera: []
    teste_integracao: "Com PROVEDOR_PUBLICAR=meta_graph e so as chaves do Expx Flow, publicar devolve erro com orientacao e nao escolhe expxflow."
    teste_funcional: "Sem ELEVENLABS_API_KEY, verificar('narrar') devolve habilitada false e falta [ELEVENLABS_API_KEY]."
    criterio_aceite: "cd motor && uv run pytest tests/ambiente/test_verificar.py termina com 0 failed"
    depende_de: [T-02.06]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-02.08
    titulo: "Gerar .env.example do nucleo"
    fase: F-02.2
    status: pendente
    objetivo: "Gerar o .env.example com um bloco comentado por capacidade e onde conseguir cada chave."
    arquivos:
      cria: [motor/src/expxmedia/ambiente/envexample.py, motor/tests/ambiente/test_envexample.py]
      altera: []
    teste_integracao: "Gerar o exemplo numa instalacao com .env preenchido nao altera o .env."
    teste_funcional: "O exemplo gerado contem ELEVENLABS_API_KEY vazio sob um comentario que cita narrar e a linha Onde conseguir."
    criterio_aceite: "cd motor && uv run pytest tests/ambiente/test_envexample.py termina com 0 failed"
    depende_de: [T-02.06]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-02.09
    titulo: "Schema da Alma e ajuste do contrato"
    fase: F-02.3
    status: pendente
    objetivo: "Validar alma.json por JSON Schema e acrescentar ao contrato os parametros de voz por tipo de peca (reel e aula) e o lexico de pronuncia do porta-voz (D-22, D-40)."
    arquivos:
      cria: [motor/src/expxmedia/alma/schema.py, motor/src/expxmedia/alma/alma.schema.json, motor/tests/alma/test_schema.py]
      altera: [docs/contrato/CONTRATO-alma.md]
    teste_integracao: "A Alma ficticia valida contra o schema e o schema aceita porta_vozes[].voz.parametros.reel, parametros.aula e voz.pronuncia."
    teste_funcional: "Uma Alma sem visual.cores.destaque devolve violacao chave_omitida apontando o caminho do campo."
    criterio_aceite: "cd motor && uv run pytest tests/alma/test_schema.py termina com 0 failed"
    depende_de: [T-01.03]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-02.10
    titulo: "Carga da Alma, portao, tokens e fontes"
    fase: F-02.3
    status: pendente
    objetivo: "Carregar a Alma, dizer se o portao esta aberto, gerar os tokens CSS --alma-* e resolver fontes com cache local e Inter embarcada (D-21)."
    arquivos:
      cria: [motor/src/expxmedia/alma/carregar.py, motor/src/expxmedia/alma/tokens.py, motor/src/expxmedia/alma/fontes.py, motor/tests/alma/test_carregar.py]
      altera: []
    teste_integracao: "Com o stub de Google Fonts, resolver a fonte titulo grava o arquivo no cache e devolve @font-face apontando para ele."
    teste_funcional: "tokens_css da Alma ficticia devolve as nove variaveis --alma-<papel> com os valores do alma.json e portao devolve aberto false sem confirmada_em."
    criterio_aceite: "cd motor && uv run pytest tests/alma/test_carregar.py termina com 0 failed"
    depende_de: [T-02.09, T-01.04, T-01.08]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-02.11
    titulo: "Modelo de peca"
    fase: F-02.3
    status: pendente
    objetivo: "Criar e atualizar peca.json com todas as chaves, ciclo de vida valido e evento por transicao (CONTRATO-peca)."
    arquivos:
      cria: [motor/src/expxmedia/peca/modelo.py, motor/tests/peca/test_modelo.py]
      altera: []
    teste_integracao: "Mudar o status de roteiro para produzida grava peca.json atomico e acrescenta evento peca_status no rastro."
    teste_funcional: "Tentar mudar de publicada para roteiro levanta erro e criar peca sem tipo valido e recusado."
    criterio_aceite: "cd motor && uv run pytest tests/peca/test_modelo.py termina com 0 failed"
    depende_de: [T-02.03, T-02.04]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-02.12
    titulo: "Template: schema e validacao"
    fase: F-02.3
    status: pendente
    objetivo: "Validar template.json e os arquivos do template: cor literal fora de :root, URL externa, imports e APIs proibidas no TSX (CONTRATO-template, D-36)."
    arquivos:
      cria: [motor/src/expxmedia/template/schema.py, motor/src/expxmedia/template/template.schema.json, motor/src/expxmedia/template/validar.py, motor/tests/template/test_validar.py]
      altera: []
    teste_integracao: "Um TSX importando fs e um CSS com url(https://externo) geram um achado cada no modo template."
    teste_funcional: "Um CSS com #ff0000 fora de :root gera achado em modo template e nao gera em modo sob_medida."
    criterio_aceite: "cd motor && uv run pytest tests/template/test_validar.py termina com 0 failed"
    depende_de: [T-01.02]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-02.13
    titulo: "Galeria local"
    fase: F-02.4
    status: pendente
    objetivo: "Buscar templates por tipo e formato descartando os que tem requisito nao habilitado ou exigem porta-voz inexistente."
    arquivos:
      cria: [motor/src/expxmedia/template/galeria_local.py, motor/tests/template/test_galeria_local.py]
      altera: []
    teste_integracao: "Adicionar ELEVENLABS_API_KEY ao .env da fixture faz o template com requisito narrar voltar a aparecer na busca."
    teste_funcional: "Sem chave, buscar tipo reel formato 9:16 nao devolve o template que exige narrar."
    criterio_aceite: "cd motor && uv run pytest tests/template/test_galeria_local.py termina com 0 failed"
    depende_de: [T-02.07, T-02.12]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-02.14
    titulo: "CLI expxmedia-motor base com registro por modulo"
    fase: F-02.4
    status: pendente
    objetivo: "Criar o CLI que descobre subcomandos nos modulos de cli_comandos/ (cada modulo registra os seus, entao nenhuma task futura edita cli.py) e o modulo base com capacidades, alma validar, peca criar, peca status e galeria buscar, saida JSON (D-11)."
    arquivos:
      cria: [motor/src/expxmedia/cli.py, motor/src/expxmedia/cli_comandos/base.py, motor/tests/test_cli.py]
      altera: []
    teste_integracao: "uv run expxmedia-motor capacidades --raiz <fixture> em subprocesso sai com codigo 0 e JSON valido, e um modulo de teste colocado em cli_comandos/ aparece no --help sem editar cli.py."
    teste_funcional: "peca criar --tipo post_unico --formato 4:5 devolve JSON com peca_id no formato do contrato e cria peca.json."
    criterio_aceite: "cd motor && uv run pytest tests/test_cli.py termina com 0 failed"
    depende_de: [T-02.08, T-02.10, T-02.11, T-02.13]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
---

# Tasks — Sprint 02

> Comando de teste: `cd motor && uv run pytest`. Base de conhecimento em `docs/nucleo-expxmedia/base/`; decisões em `00-DECISOES.md`. Nenhuma task escreve nos projetos de origem (D-37).

---

### T-02.01 — Ids e tempo com fuso

```yaml
id: T-02.01
titulo: Ids e tempo com fuso
fase: F-02.1
objetivo: Gerar ids de peça e template, deduplicando contra as peças existentes e os ids já gerados no processo, e momentos ISO com o fuso da Alma (M5, M11).
arquivos:
  cria: [motor/src/expxmedia/nucleo/ids.py, motor/src/expxmedia/nucleo/tempo.py, motor/tests/nucleo/test_ids_tempo.py]
  altera: []
teste_integracao: Com a Alma fictícia em America/Sao_Paulo, agora() devolve momento com deslocamento -03:00.
teste_funcional: novo_peca_id para 2026-09-24 casa com ^P-20260924-[0-9A-F]{4}$ e 1000 chamadas não repetem id.
criterio_aceite: `cd motor && uv run pytest tests/nucleo/test_ids_tempo.py` termina com 0 failed
depende_de: [T-01.03]
paralelizavel: true
status: pendente
```

---

### T-02.02 — Escrita atomica e JSONL com trava

```yaml
id: T-02.02
titulo: Escrita atomica e JSONL com trava
fase: F-02.1
objetivo: Portar a escrita atômica e o acréscimo com trava entre processos usando filelock (M15).
arquivos:
  cria: [motor/src/expxmedia/nucleo/arquivos.py, motor/tests/nucleo/test_arquivos.py]
  altera: []
teste_integracao: Oito processos acrescentando 100 linhas cada ao mesmo JSONL produzem 800 linhas JSON válidas.
teste_funcional: gravar_json com objeto não serializável levanta erro e deixa o arquivo anterior intacto.
criterio_aceite: `cd motor && uv run pytest tests/nucleo/test_arquivos.py` termina com 0 failed
depende_de: [T-01.02]
paralelizavel: true
status: pendente
```

---

### T-02.03 — Rastro de eventos

```yaml
id: T-02.03
titulo: Rastro de eventos
fase: F-02.1
objetivo: Gravar eventos com as doze chaves na ordem do CONTRATO-estado-eventos e extras declaradas depois.
arquivos:
  cria: [motor/src/expxmedia/nucleo/rastro.py, motor/tests/nucleo/test_rastro.py]
  altera: []
teste_integracao: Um evento gravado em eventos/AAAA-MM.jsonl é relido com as doze chaves na ordem e ts com fuso.
teste_funcional: Registrar evento com chave extra não declarada levanta erro e com extra declarada (segundos) grava a extra depois das doze.
criterio_aceite: `cd motor && uv run pytest tests/nucleo/test_rastro.py` termina com 0 failed
depende_de: [T-02.01, T-02.02]
paralelizavel: false
status: pendente
```

---

### T-02.04 — Raiz da instalacao e caminhos relativos

```yaml
id: T-02.04
titulo: Raiz da instalacao e caminhos relativos
fase: F-02.1
objetivo: Localizar a raiz da instalação e converter caminhos para relativos (M9).
arquivos:
  cria: [motor/src/expxmedia/nucleo/raiz.py, motor/tests/nucleo/test_raiz.py]
  altera: []
teste_integracao: A partir de uma subpasta de pecas/ da fixture, encontrar_raiz devolve a pasta que contém alma/.
teste_funcional: relativo converte um caminho absoluto dentro da raiz em caminho relativo e recusa caminho fora da raiz.
criterio_aceite: `cd motor && uv run pytest tests/nucleo/test_raiz.py` termina com 0 failed
depende_de: [T-01.03]
paralelizavel: true
status: pendente
```

---

### T-02.05 — Leitor do .env

```yaml
id: T-02.05
titulo: Leitor do .env
fase: F-02.2
objetivo: Ler o .env da instalação sem nunca expor valores em mensagens (M14).
arquivos:
  cria: [motor/src/expxmedia/ambiente/env.py, motor/tests/ambiente/test_env.py]
  altera: []
teste_integracao: Um erro provocado com chave presente mostra o nome da variável e não contém o valor em str nem repr.
teste_funcional: Um .env com comentário, aspas e linha vazia é lido como dicionário com os três valores esperados.
criterio_aceite: `cd motor && uv run pytest tests/ambiente/test_env.py` termina com 0 failed
depende_de: [T-02.04]
paralelizavel: true
status: pendente
```

---

### T-02.06 — Catalogo de capacidades do nucleo

```yaml
id: T-02.06
titulo: Catalogo de capacidades do nucleo
fase: F-02.2
objetivo: Declarar as capacidades do núcleo, provedores e o que satisfaz cada um, incluindo derivadas e fornecidas por pack.
arquivos:
  cria: [motor/src/expxmedia/ambiente/catalogo.py, motor/tests/ambiente/test_catalogo.py]
  altera: []
teste_integracao: Uma capacidade registrada como fornecida por pack aparece na consulta com os mesmos campos das do núcleo.
teste_funcional: O catálogo contém exatamente as capacidades do núcleo listadas em CONTRATO-capacidades.md, com legendar derivada de narrar ou transcrever.
criterio_aceite: `cd motor && uv run pytest tests/ambiente/test_catalogo.py` termina com 0 failed
depende_de: [T-02.05]
paralelizavel: false
status: pendente
```

---

### T-02.07 — Verificacao, como_habilitar e provedor padrao

```yaml
id: T-02.07
titulo: Verificacao, como_habilitar e provedor padrao
fase: F-02.2
objetivo: Responder se uma capacidade está habilitada, por qual provedor e o que falta, respeitando PROVEDOR_* sem troca silenciosa (D-07).
arquivos:
  cria: [motor/src/expxmedia/ambiente/verificar.py, motor/tests/ambiente/test_verificar.py]
  altera: []
teste_integracao: Com PROVEDOR_PUBLICAR=meta_graph e só as chaves do Expx Flow, publicar devolve erro com orientação e não escolhe expxflow.
teste_funcional: Sem ELEVENLABS_API_KEY, verificar('narrar') devolve habilitada false e falta [ELEVENLABS_API_KEY].
criterio_aceite: `cd motor && uv run pytest tests/ambiente/test_verificar.py` termina com 0 failed
depende_de: [T-02.06]
paralelizavel: false
status: pendente
```

---

### T-02.08 — Gerar .env.example do nucleo

```yaml
id: T-02.08
titulo: Gerar .env.example do nucleo
fase: F-02.2
objetivo: Gerar o .env.example com um bloco comentado por capacidade e onde conseguir cada chave.
arquivos:
  cria: [motor/src/expxmedia/ambiente/envexample.py, motor/tests/ambiente/test_envexample.py]
  altera: []
teste_integracao: Gerar o exemplo numa instalação com .env preenchido não altera o .env.
teste_funcional: O exemplo gerado contém ELEVENLABS_API_KEY vazio sob um comentário que cita narrar e a linha Onde conseguir.
criterio_aceite: `cd motor && uv run pytest tests/ambiente/test_envexample.py` termina com 0 failed
depende_de: [T-02.06]
paralelizavel: true
status: pendente
```

---

### T-02.09 — Schema da Alma e ajuste do contrato

```yaml
id: T-02.09
titulo: Schema da Alma e ajuste do contrato
fase: F-02.3
objetivo: Validar alma.json por JSON Schema e acrescentar ao contrato os parâmetros de voz por tipo de peça (reel e aula) e o léxico de pronúncia do porta-voz (D-22, D-40).
arquivos:
  cria: [motor/src/expxmedia/alma/schema.py, motor/src/expxmedia/alma/alma.schema.json, motor/tests/alma/test_schema.py]
  altera: [docs/contrato/CONTRATO-alma.md]
teste_integracao: A Alma fictícia valida contra o schema e o schema aceita porta_vozes[].voz.parametros.reel, parametros.aula e voz.pronuncia.
teste_funcional: Uma Alma sem visual.cores.destaque devolve violação chave_omitida apontando o caminho do campo.
criterio_aceite: `cd motor && uv run pytest tests/alma/test_schema.py` termina com 0 failed
depende_de: [T-01.03]
paralelizavel: true
status: pendente
```

---

### T-02.10 — Carga da Alma, portao, tokens e fontes

```yaml
id: T-02.10
titulo: Carga da Alma, portao, tokens e fontes
fase: F-02.3
objetivo: Carregar a Alma, dizer se o portão está aberto, gerar os tokens CSS --alma-* e resolver fontes com cache local e Inter embarcada (D-21).
arquivos:
  cria: [motor/src/expxmedia/alma/carregar.py, motor/src/expxmedia/alma/tokens.py, motor/src/expxmedia/alma/fontes.py, motor/tests/alma/test_carregar.py]
  altera: []
teste_integracao: Com o stub de Google Fonts, resolver a fonte titulo grava o arquivo no cache e devolve @font-face apontando para ele.
teste_funcional: tokens_css da Alma fictícia devolve as nove variáveis --alma-<papel> com os valores do alma.json e portao devolve aberto false sem confirmada_em.
criterio_aceite: `cd motor && uv run pytest tests/alma/test_carregar.py` termina com 0 failed
depende_de: [T-02.09, T-01.04, T-01.08]
paralelizavel: false
status: pendente
```

---

### T-02.11 — Modelo de peca

```yaml
id: T-02.11
titulo: Modelo de peca
fase: F-02.3
objetivo: Criar e atualizar peca.json com todas as chaves, ciclo de vida válido e evento por transição (CONTRATO-peca).
arquivos:
  cria: [motor/src/expxmedia/peca/modelo.py, motor/tests/peca/test_modelo.py]
  altera: []
teste_integracao: Mudar o status de roteiro para produzida grava peca.json atômico e acrescenta evento peca_status no rastro.
teste_funcional: Tentar mudar de publicada para roteiro levanta erro e criar peça sem tipo válido é recusado.
criterio_aceite: `cd motor && uv run pytest tests/peca/test_modelo.py` termina com 0 failed
depende_de: [T-02.03, T-02.04]
paralelizavel: true
status: pendente
```

---

### T-02.12 — Template: schema e validacao

```yaml
id: T-02.12
titulo: Template: schema e validacao
fase: F-02.3
objetivo: Validar template.json e os arquivos do template: cor literal fora de :root, URL externa, imports e APIs proibidas no TSX (CONTRATO-template, D-36).
arquivos:
  cria: [motor/src/expxmedia/template/schema.py, motor/src/expxmedia/template/template.schema.json, motor/src/expxmedia/template/validar.py, motor/tests/template/test_validar.py]
  altera: []
teste_integracao: Um TSX importando fs e um CSS com url(https://externo) geram um achado cada no modo template.
teste_funcional: Um CSS com #ff0000 fora de :root gera achado em modo template e não gera em modo sob_medida.
criterio_aceite: `cd motor && uv run pytest tests/template/test_validar.py` termina com 0 failed
depende_de: [T-01.02]
paralelizavel: true
status: pendente
```

---

### T-02.13 — Galeria local

```yaml
id: T-02.13
titulo: Galeria local
fase: F-02.4
objetivo: Buscar templates por tipo e formato descartando os que têm requisito não habilitado ou exigem porta-voz inexistente.
arquivos:
  cria: [motor/src/expxmedia/template/galeria_local.py, motor/tests/template/test_galeria_local.py]
  altera: []
teste_integracao: Adicionar ELEVENLABS_API_KEY ao .env da fixture faz o template com requisito narrar voltar a aparecer na busca.
teste_funcional: Sem chave, buscar tipo reel formato 9:16 não devolve o template que exige narrar.
criterio_aceite: `cd motor && uv run pytest tests/template/test_galeria_local.py` termina com 0 failed
depende_de: [T-02.07, T-02.12]
paralelizavel: false
status: pendente
```

---

### T-02.14 — CLI expxmedia-motor base com registro por modulo

```yaml
id: T-02.14
titulo: CLI expxmedia-motor base com registro por modulo
fase: F-02.4
objetivo: Criar o CLI que descobre subcomandos nos módulos de cli_comandos/ (cada módulo registra os seus, então nenhuma task futura edita cli.py) e o módulo base com capacidades, alma validar, peca criar, peca status e galeria buscar, saída JSON (D-11).
arquivos:
  cria: [motor/src/expxmedia/cli.py, motor/src/expxmedia/cli_comandos/base.py, motor/tests/test_cli.py]
  altera: []
teste_integracao: uv run expxmedia-motor capacidades --raiz <fixture> em subprocesso sai com código 0 e JSON válido, e um módulo de teste colocado em cli_comandos/ aparece no --help sem editar cli.py.
teste_funcional: peca criar --tipo post_unico --formato 4:5 devolve JSON com peca_id no formato do contrato e cria peca.json.
criterio_aceite: `cd motor && uv run pytest tests/test_cli.py` termina com 0 failed
depende_de: [T-02.08, T-02.10, T-02.11, T-02.13]
paralelizavel: false
status: pendente
```
