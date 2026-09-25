---
expx_schema: 1
expx_tool: sprintx
kind: tasks
trabalho_id: nucleo-expxmedia
sprint_id: sprint-10
atualizado_em: 2026-09-25
tasks:
  - id: T-10.01
    titulo: "Cinco tipos sem chave"
    fase: F-10.1
    status: concluida
    objetivo: "Produzir post unico, carrossel, carrossel misto, apresentacao, reel e aula com a Alma ficticia, sem chave e com o provedor de teste."
    arquivos:
      cria: [motor/tests/e2e/test_cinco_tipos.py]
      altera: []
    teste_integracao: "Numa instalacao nova da fixture, as sete producoes (inclusive reel de pagina) terminam com peca produzida e arquivos existentes."
    teste_funcional: "Todo peca.json gerado valida contra o schema do contrato e tem producao.capacidades preenchido."
    criterio_aceite: "cd motor && uv run pytest tests/e2e/test_cinco_tipos.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-07.06, T-06.07, T-05.11, T-05.07, T-04.12]
    paralelizavel: false
    concluida_em: 2026-09-25
    suite: verde
  - id: T-10.02
    titulo: "Publicacao em dry-run nos dois provedores"
    fase: F-10.1
    status: concluida
    objetivo: "Publicar em dry-run um carrossel e um reel por Expx Flow e por Graph contra stubs."
    arquivos:
      cria: [motor/tests/e2e/test_publicacao.py]
      altera: []
    teste_integracao: "Com as chaves falsas dos dois provedores e PROVEDOR_PUBLICAR alternado, cada dry-run registra a intencao e o payload sem publicar."
    teste_funcional: "Com PROVEDOR_PUBLICAR ausente e os dois satisfeitos, o provedor usado e expxflow e o aviso de escolha implicita aparece."
    criterio_aceite: "cd motor && uv run pytest tests/e2e/test_publicacao.py termina com 0 failed"
    depende_de: [T-08.07]
    paralelizavel: true
    concluida_em: 2026-09-25
    suite: verde
  - id: T-10.03
    titulo: "Reel por referencia guiado pela skill"
    fase: F-10.1
    status: concluida
    objetivo: "Executar a skill reel-por-referencia sobre a referencia local ../Instagram-Carrosseis/series/recriacoes/pedidos/r20260924-221743/referencia/video.mp4 (so entrada, nunca copiada para o repositorio), com a Alma ficticia e o provedor de teste, numa instalacao persistente em docs/nucleo-expxmedia/validacao/reel-por-referencia/ (o MP4 fica fora do git e e registrado por sha256), gravando leitura, codigo, previas, MP4 e revisao, e um teste que confere mecanicamente o resultado lendo desse caminho."
    arquivos:
      cria: [docs/nucleo-expxmedia/validacao/reel-por-referencia.md, motor/tests/e2e/test_validacao_referencia.py]
      altera: [.gitignore]
    teste_integracao: "expxmedia-motor verificar --perfil sob_medida no MP4 gerado sai com codigo 0 e o validador de codigo no modo sob_medida nao devolve achado."
    teste_funcional: "O teste confere que leitura.md tem as 9 secoes nao vazias, que existem ao menos 1 e no maximo 3 previas gravadas e que cada item do checklist de parecenca no arquivo de validacao cita um caminho de quadro existente."
    criterio_aceite: "cd motor && uv run pytest tests/e2e/test_validacao_referencia.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-09.06]
    paralelizavel: true
    concluida_em: 2026-09-25
    suite: verde
  - id: T-10.04
    titulo: "Documentacao do nucleo"
    fase: F-10.2
    status: concluida
    objetivo: "Documentar o motor, o CLI e o uso do plugin com claude --plugin-dir nucleo, e atualizar o README do repositorio."
    arquivos:
      cria: [motor/README.md, nucleo/README.md, motor/tests/test_documentacao.py]
      altera: [README.md]
    teste_integracao: "Todo subcomando listado no motor/README.md existe no --help do CLI."
    teste_funcional: "O README do repositorio marca o passo 2 como concluido e cita motor/ e nucleo/, e claude plugin validate nucleo termina com codigo 0."
    criterio_aceite: "cd motor && uv run pytest tests/test_documentacao.py termina com 0 failed"
    depende_de: [T-10.02, T-10.03]
    paralelizavel: false
    concluida_em: 2026-09-25
    suite: verde
  - id: T-10.05
    titulo: "Suite completa e varredura final"
    fase: F-10.2
    status: concluida
    objetivo: "Rodar a suite inteira e a varredura de marca e registrar o resultado."
    arquivos:
      cria: [docs/nucleo-expxmedia/validacao/suite-final.md]
      altera: []
    teste_integracao: "A suite inteira roda nesta maquina sem falha e sem teste pulado."
    teste_funcional: "A varredura de marca sobre motor/src, motor/kit-remotion, nucleo e templates nao encontra termo proibido."
    criterio_aceite: "cd motor && uv run pytest termina com 0 failed e 0 skipped e suite-final.md registra o total de testes"
    depende_de: [T-10.04]
    paralelizavel: false
    concluida_em: 2026-09-25
    suite: verde
---

# Tasks — Sprint 10

> Comando de teste: `cd motor && uv run pytest`. Base de conhecimento em `docs/nucleo-expxmedia/base/`; decisões em `00-DECISOES.md`. Nenhuma task escreve nos projetos de origem (D-37).

---

### T-10.01 — Cinco tipos sem chave

```yaml
id: T-10.01
titulo: Cinco tipos sem chave
fase: F-10.1
objetivo: Produzir post único, carrossel, carrossel misto, apresentação, reel e aula com a Alma fictícia, sem chave e com o provedor de teste.
arquivos:
  cria: [motor/tests/e2e/test_cinco_tipos.py]
  altera: []
teste_integracao: Numa instalação nova da fixture, as sete produções (inclusive reel de página) terminam com peça produzida e arquivos existentes.
teste_funcional: Todo peca.json gerado valida contra o schema do contrato e tem producao.capacidades preenchido.
criterio_aceite: `cd motor && uv run pytest tests/e2e/test_cinco_tipos.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-07.06, T-06.07, T-05.11, T-05.07, T-04.12]
paralelizavel: false
status: concluida
concluida: 2026-09-25 · suíte: 10 passed, 0 skipped
```

---

### T-10.02 — Publicacao em dry-run nos dois provedores

```yaml
id: T-10.02
titulo: Publicacao em dry-run nos dois provedores
fase: F-10.1
objetivo: Publicar em dry-run um carrossel e um reel por Expx Flow e por Graph contra stubs.
arquivos:
  cria: [motor/tests/e2e/test_publicacao.py]
  altera: []
teste_integracao: Com as chaves falsas dos dois provedores e PROVEDOR_PUBLICAR alternado, cada dry-run registra a intenção e o payload sem publicar.
teste_funcional: Com PROVEDOR_PUBLICAR ausente e os dois satisfeitos, o provedor usado é expxflow e o aviso de escolha implícita aparece.
criterio_aceite: `cd motor && uv run pytest tests/e2e/test_publicacao.py` termina com 0 failed
depende_de: [T-08.07]
paralelizavel: true
status: concluida
concluida: 2026-09-25 · suíte: tests/e2e/test_publicacao.py 9 passed (após B-02)
```

---

### T-10.03 — Reel por referencia guiado pela skill

```yaml
id: T-10.03
titulo: Reel por referencia guiado pela skill
fase: F-10.1
objetivo: Executar a skill reel-por-referencia sobre a referência local ../Instagram-Carrosseis/series/recriacoes/pedidos/r20260924-221743/referencia/video.mp4 (só entrada, nunca copiada para o repositório), com a Alma fictícia e o provedor de teste, numa instalação persistente em docs/nucleo-expxmedia/validacao/reel-por-referencia/ (o MP4 fica fora do git e é registrado por sha256), gravando leitura, código, prévias, MP4 e revisão, e um teste que confere mecanicamente o resultado lendo desse caminho.
arquivos:
  cria: [docs/nucleo-expxmedia/validacao/reel-por-referencia.md, motor/tests/e2e/test_validacao_referencia.py]
  altera: [.gitignore]
teste_integracao: expxmedia-motor verificar --perfil sob_medida no MP4 gerado sai com código 0 e o validador de código no modo sob_medida não devolve achado.
teste_funcional: O teste confere que leitura.md tem as 9 seções não vazias, que existem ao menos 1 e no máximo 3 prévias gravadas e que cada item do checklist de parecença no arquivo de validação cita um caminho de quadro existente.
criterio_aceite: `cd motor && uv run pytest tests/e2e/test_validacao_referencia.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-09.06]
paralelizavel: true
status: concluida
concluida: 2026-09-25 · suíte: 5 passed, 0 skipped
```

---

### T-10.04 — Documentacao do nucleo

```yaml
id: T-10.04
titulo: Documentacao do nucleo
fase: F-10.2
objetivo: Documentar o motor, o CLI e o uso do plugin com claude --plugin-dir nucleo, e atualizar o README do repositório.
arquivos:
  cria: [motor/README.md, nucleo/README.md, motor/tests/test_documentacao.py]
  altera: [README.md]
teste_integracao: Todo subcomando listado no motor/README.md existe no --help do CLI.
teste_funcional: O README do repositório marca o passo 2 como concluído e cita motor/ e nucleo/, e claude plugin validate nucleo termina com código 0.
criterio_aceite: `cd motor && uv run pytest tests/test_documentacao.py` termina com 0 failed
depende_de: [T-10.02, T-10.03]
paralelizavel: false
status: concluida
concluida: 2026-09-25 · suíte: 9 passed
```

---

### T-10.05 — Suite completa e varredura final

```yaml
id: T-10.05
titulo: Suite completa e varredura final
fase: F-10.2
objetivo: Rodar a suíte inteira e a varredura de marca e registrar o resultado.
arquivos:
  cria: [docs/nucleo-expxmedia/validacao/suite-final.md]
  altera: []
teste_integracao: A suíte inteira roda nesta máquina sem falha e sem teste pulado.
teste_funcional: A varredura de marca sobre motor/src, motor/kit-remotion, nucleo e templates não encontra termo proibido.
criterio_aceite: `cd motor && uv run pytest` termina com 0 failed e 0 skipped e suite-final.md registra o total de testes
depende_de: [T-10.04]
paralelizavel: false
status: concluida
concluida: 2026-09-25 · suíte: 1131 passed, 0 skipped
```
