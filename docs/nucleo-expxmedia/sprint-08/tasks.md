---
expx_schema: 1
expx_tool: sprintx
kind: tasks
trabalho_id: nucleo-expxmedia
sprint_id: sprint-08
atualizado_em: 2026-09-25
tasks:
  - id: T-08.01
    titulo: "Base de publicacao com idempotencia"
    fase: F-08.1
    status: concluida
    objetivo: "Escolher provedor pela verificacao, gravar a intencao na peca antes do envio e nunca retentar POST (D-29)."
    arquivos:
      cria: [motor/src/expxmedia/publicar/base.py, motor/tests/publicar/test_base.py]
      altera: []
    teste_integracao: "Publicar uma peca que ja tem publicacao enviada para o mesmo canal e horario recusa o segundo envio sem chamar o provedor."
    teste_funcional: "Um provedor que responde 503 gera publicacao_falhou com uma unica chamada registrada no stub."
    criterio_aceite: "cd motor && uv run pytest tests/publicar/test_base.py termina com 0 failed"
    depende_de: [T-02.07, T-02.11]
    paralelizavel: false
    concluida_em: 2026-09-25
    suite: verde
  - id: T-08.02
    titulo: "Adaptador Expx Flow"
    fase: F-08.1
    status: concluida
    objetivo: "Portar upload de midia, carousel-api com filhos imagem e video, post-api de reel, automacao de DM, 207 parcial e dry-run, com URL base configuravel (D-06)."
    arquivos:
      cria: [motor/src/expxmedia/publicar/expxflow.py, motor/tests/publicar/test_expxflow.py]
      altera: []
    teste_integracao: "Contra o stub, publicar um carrossel misto envia um filho com image_url e outro com video_url."
    teste_funcional: "Resposta 207 grava na peca o estado de cada plataforma e dry-run nao chama nenhuma rota de criacao."
    criterio_aceite: "cd motor && uv run pytest tests/publicar/test_expxflow.py termina com 0 failed"
    depende_de: [T-08.01, T-01.04]
    paralelizavel: true
    concluida_em: 2026-09-25
    suite: verde
  - id: T-08.03
    titulo: "Tunel de URL publica"
    fase: F-08.1
    status: concluida
    objetivo: "Portar o tunel cloudflared que expoe a midia por URL temporaria durante a publicacao."
    arquivos:
      cria: [motor/src/expxmedia/publicar/tunel.py, motor/tests/publicar/test_tunel.py, motor/tests/stubs/cloudflared_falso.py]
      altera: []
    teste_integracao: "Com um cloudflared falso no PATH, abrir o tunel devolve a URL impressa pelo processo e fechar encerra o processo."
    teste_funcional: "Se o processo nao imprime URL em 30 s, abrir levanta erro e encerra o processo."
    criterio_aceite: "cd motor && uv run pytest tests/publicar/test_tunel.py termina com 0 failed"
    depende_de: [T-01.02]
    paralelizavel: true
    concluida_em: 2026-09-25
    suite: verde
  - id: T-08.04
    titulo: "Adaptador Graph API"
    fase: F-08.1
    status: concluida
    objetivo: "Publicar pela Graph: conteiner, status, media_publish, PNG para JPEG, validacao de proporcao e de no maximo 10 itens, reel, e limite conservador de 50 publicacoes em 24 h consultado em content_publishing_limit antes de publicar (D-44)."
    arquivos:
      cria: [motor/src/expxmedia/publicar/meta_graph.py, motor/tests/publicar/test_meta_graph.py]
      altera: []
    teste_integracao: "Contra o stub, publicar um carrossel de 3 PNGs cria 3 conteineres filhos com JPEG, um conteiner pai e chama media_publish depois de FINISHED."
    teste_funcional: "Um post 9:16 e recusado antes de qualquer chamada com achado de proporcao, e com content_publishing_limit do stub em 50 a publicacao e recusada sem criar conteiner."
    criterio_aceite: "cd motor && uv run pytest tests/publicar/test_meta_graph.py termina com 0 failed"
    depende_de: [T-08.01, T-08.03, T-04.01]
    paralelizavel: false
    concluida_em: 2026-09-25
    suite: verde
  - id: T-08.05
    titulo: "Servico do agendador"
    fase: F-08.2
    status: concluida
    objetivo: "Varrer pecas agendadas via meta_graph a cada minuto, publicar ate 15 minutos depois do horario e marcar falhou depois disso, com trava (D-30)."
    arquivos:
      cria: [motor/src/expxmedia/agendador/servico.py, motor/tests/agendador/test_servico.py]
      altera: []
    teste_integracao: "Uma rodada com uma peca agendada para 5 minutos atras publica pelo adaptador falso e grava publicada."
    teste_funcional: "Uma peca agendada para 20 minutos atras vira falhou com motivo atraso sem chamar o adaptador."
    criterio_aceite: "cd motor && uv run pytest tests/agendador/test_servico.py termina com 0 failed"
    depende_de: [T-08.01, T-02.02]
    paralelizavel: true
    concluida_em: 2026-09-25
    suite: verde
  - id: T-08.06
    titulo: "Instalacao do agendador por SO"
    fase: F-08.2
    status: concluida
    objetivo: "Gerar LaunchAgent, tarefa do Agendador de Tarefas e unidade systemd de usuario; aplicar so com --aplicar."
    arquivos:
      cria: [motor/src/expxmedia/agendador/instalar.py, motor/tests/agendador/test_instalar.py]
      altera: []
    teste_integracao: "Sem --aplicar, instalar em macOS devolve o plist com ProgramArguments apontando para o servico e nao escreve em LaunchAgents."
    teste_funcional: "Para linux o texto gerado contem uma unidade [Service] e um [Timer] com OnCalendar de minuto e a instrucao de linger."
    criterio_aceite: "cd motor && uv run pytest tests/agendador/test_instalar.py termina com 0 failed"
    depende_de: [T-08.05]
    paralelizavel: true
    concluida_em: 2026-09-25
    suite: verde
  - id: T-08.07
    titulo: "CLI de publicacao e agendador"
    fase: F-08.3
    status: concluida
    objetivo: "Expor publicar, agendar, agendador rodar e agendador instalar no CLI, com dry-run como padrao para publicar."
    arquivos:
      cria: [motor/src/expxmedia/cli_comandos/publicar.py, motor/tests/test_cli_publicar.py]
      altera: []
    teste_integracao: "expxmedia-motor publicar --peca <id> sem --confirmar executa dry-run contra o stub e sai 0."
    teste_funcional: "agendar com PROVEDOR_AGENDAR apontando para provedor sem chave sai 3 com a orientacao de como_habilitar."
    criterio_aceite: "cd motor && uv run pytest tests/test_cli_publicar.py termina com 0 failed"
    depende_de: [T-08.02, T-08.04, T-08.06]
    paralelizavel: false
    concluida_em: 2026-09-25
    suite: verde
---

# Tasks — Sprint 08

> Comando de teste: `cd motor && uv run pytest tests/publicar tests/agendador tests/test_cli_publicar.py`. Base de conhecimento em `docs/nucleo-expxmedia/base/`; decisões em `00-DECISOES.md`. Nenhuma task escreve nos projetos de origem (D-37).

---

### T-08.01 — Base de publicacao com idempotencia

```yaml
id: T-08.01
titulo: Base de publicacao com idempotencia
fase: F-08.1
objetivo: Escolher provedor pela verificação, gravar a intenção na peça antes do envio e nunca retentar POST (D-29).
arquivos:
  cria: [motor/src/expxmedia/publicar/base.py, motor/tests/publicar/test_base.py]
  altera: []
teste_integracao: Publicar uma peça que já tem publicação enviada para o mesmo canal e horário recusa o segundo envio sem chamar o provedor.
teste_funcional: Um provedor que responde 503 gera publicacao_falhou com uma única chamada registrada no stub.
criterio_aceite: `cd motor && uv run pytest tests/publicar/test_base.py` termina com 0 failed
depende_de: [T-02.07, T-02.11]
paralelizavel: false
status: concluida
concluida: 2026-09-25 · suíte: tests/publicar 43 passed
```

---

### T-08.02 — Adaptador Expx Flow

```yaml
id: T-08.02
titulo: Adaptador Expx Flow
fase: F-08.1
objetivo: Portar upload de mídia, carousel-api com filhos imagem e vídeo, post-api de reel, automação de DM, 207 parcial e dry-run, com URL base configurável (D-06).
arquivos:
  cria: [motor/src/expxmedia/publicar/expxflow.py, motor/tests/publicar/test_expxflow.py]
  altera: []
teste_integracao: Contra o stub, publicar um carrossel misto envia um filho com image_url e outro com video_url.
teste_funcional: Resposta 207 grava na peça o estado de cada plataforma e dry-run não chama nenhuma rota de criação.
criterio_aceite: `cd motor && uv run pytest tests/publicar/test_expxflow.py` termina com 0 failed
depende_de: [T-08.01, T-01.04]
paralelizavel: true
status: concluida
concluida: 2026-09-25 · suíte: tests/publicar 43 passed
```

---

### T-08.03 — Tunel de URL publica

```yaml
id: T-08.03
titulo: Tunel de URL publica
fase: F-08.1
objetivo: Portar o túnel cloudflared que expõe a mídia por URL temporária durante a publicação.
arquivos:
  cria: [motor/src/expxmedia/publicar/tunel.py, motor/tests/publicar/test_tunel.py, motor/tests/stubs/cloudflared_falso.py]
  altera: []
teste_integracao: Com um cloudflared falso no PATH, abrir o túnel devolve a URL impressa pelo processo e fechar encerra o processo.
teste_funcional: Se o processo não imprime URL em 30 s, abrir levanta erro e encerra o processo.
criterio_aceite: `cd motor && uv run pytest tests/publicar/test_tunel.py` termina com 0 failed
depende_de: [T-01.02]
paralelizavel: true
status: concluida
concluida: 2026-09-25 · suíte: tests/publicar 43 passed
```

---

### T-08.04 — Adaptador Graph API

```yaml
id: T-08.04
titulo: Adaptador Graph API
fase: F-08.1
objetivo: Publicar pela Graph: contêiner, status, media_publish, PNG para JPEG, validação de proporção e de no máximo 10 itens, reel, e limite conservador de 50 publicações em 24 h consultado em content_publishing_limit antes de publicar (D-44).
arquivos:
  cria: [motor/src/expxmedia/publicar/meta_graph.py, motor/tests/publicar/test_meta_graph.py]
  altera: []
teste_integracao: Contra o stub, publicar um carrossel de 3 PNGs cria 3 contêineres filhos com JPEG, um contêiner pai e chama media_publish depois de FINISHED.
teste_funcional: Um post 9:16 é recusado antes de qualquer chamada com achado de proporção, e com content_publishing_limit do stub em 50 a publicação é recusada sem criar contêiner.
criterio_aceite: `cd motor && uv run pytest tests/publicar/test_meta_graph.py` termina com 0 failed
depende_de: [T-08.01, T-08.03, T-04.01]
paralelizavel: false
status: concluida
concluida: 2026-09-25 · suíte: tests/publicar 43 passed
```

---

### T-08.05 — Servico do agendador

```yaml
id: T-08.05
titulo: Servico do agendador
fase: F-08.2
objetivo: Varrer peças agendadas via meta_graph a cada minuto, publicar até 15 minutos depois do horário e marcar falhou depois disso, com trava (D-30).
arquivos:
  cria: [motor/src/expxmedia/agendador/servico.py, motor/tests/agendador/test_servico.py]
  altera: []
teste_integracao: Uma rodada com uma peça agendada para 5 minutos atrás publica pelo adaptador falso e grava publicada.
teste_funcional: Uma peça agendada para 20 minutos atrás vira falhou com motivo atraso sem chamar o adaptador.
criterio_aceite: `cd motor && uv run pytest tests/agendador/test_servico.py` termina com 0 failed
depende_de: [T-08.01, T-02.02]
paralelizavel: true
status: concluida
concluida: 2026-09-25 · suíte: 16 passed
```

---

### T-08.06 — Instalacao do agendador por SO

```yaml
id: T-08.06
titulo: Instalacao do agendador por SO
fase: F-08.2
objetivo: Gerar LaunchAgent, tarefa do Agendador de Tarefas e unidade systemd de usuário; aplicar só com --aplicar.
arquivos:
  cria: [motor/src/expxmedia/agendador/instalar.py, motor/tests/agendador/test_instalar.py]
  altera: []
teste_integracao: Sem --aplicar, instalar em macOS devolve o plist com ProgramArguments apontando para o serviço e não escreve em LaunchAgents.
teste_funcional: Para linux o texto gerado contém uma unidade [Service] e um [Timer] com OnCalendar de minuto e a instrução de linger.
criterio_aceite: `cd motor && uv run pytest tests/agendador/test_instalar.py` termina com 0 failed
depende_de: [T-08.05]
paralelizavel: true
status: concluida
concluida: 2026-09-25 · suíte: 10 passed
```

---

### T-08.07 — CLI de publicacao e agendador

```yaml
id: T-08.07
titulo: CLI de publicacao e agendador
fase: F-08.3
objetivo: Expor publicar, agendar, agendador rodar e agendador instalar no CLI, com dry-run como padrão para publicar.
arquivos:
  cria: [motor/src/expxmedia/cli_comandos/publicar.py, motor/tests/test_cli_publicar.py]
  altera: []
teste_integracao: expxmedia-motor publicar --peca <id> sem --confirmar executa dry-run contra o stub e sai 0.
teste_funcional: agendar com PROVEDOR_AGENDAR apontando para provedor sem chave sai 3 com a orientação de como_habilitar.
criterio_aceite: `cd motor && uv run pytest tests/test_cli_publicar.py` termina com 0 failed
depende_de: [T-08.02, T-08.04, T-08.06]
paralelizavel: false
status: concluida
concluida: 2026-09-25 · suíte: 13 passed (sprint 08: 82 passed)
```
