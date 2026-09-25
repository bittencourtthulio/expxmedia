---
expx_schema: 1
expx_tool: sprintx
kind: tasks
trabalho_id: nucleo-expxmedia
sprint_id: sprint-07
atualizado_em: 2026-09-25
tasks:
  - id: T-07.01
    titulo: "Cues do roteiro de aula"
    fase: F-07.1
    status: concluida
    objetivo: "Portar marcadores [[sN]] para cues.json a partir do alinhamento, com hash da narracao para invalidar dependentes."
    arquivos:
      cria: [motor/src/expxmedia/aula/cues.py, motor/tests/aula/test_cues.py]
      altera: []
    teste_integracao: "Com o roteiro e o alinhamento do provedor de teste, cues.json tem um inicio por marcador em ordem crescente e um marcador seguido de espacos aponta para a proxima letra falada."
    teste_funcional: "Mudar a narracao muda o hash gravado e marca avatar e legendas existentes como desatualizados."
    criterio_aceite: "cd motor && uv run pytest tests/aula/test_cues.py termina com 0 failed"
    depende_de: [T-04.03]
    paralelizavel: true
    concluida_em: 2026-09-25
    suite: verde
  - id: T-07.02
    titulo: "Avatar HeyGen v3 e provedor de teste"
    fase: F-07.1
    status: concluida
    objetivo: "Gerar avatar a partir do audio pela API v3 (upload, audio_asset_id, polling, download) e provedor de teste (D-26, D-34)."
    arquivos:
      cria: [motor/src/expxmedia/avatar/heygen.py, motor/src/expxmedia/avatar/teste.py, motor/tests/avatar/test_heygen.py]
      altera: []
    teste_integracao: "Contra o stub, o fluxo faz upload do audio, cria o video com audio_asset_id e baixa apos status completed."
    teste_funcional: "Status failed no polling devolve erro com a mensagem do provedor e nenhuma nova criacao."
    criterio_aceite: "cd motor && uv run pytest tests/avatar/test_heygen.py termina com 0 failed"
    depende_de: [T-02.07, T-01.04]
    paralelizavel: true
    concluida_em: 2026-09-25
    suite: verde
  - id: T-07.03
    titulo: "Edicao da gravacao de tela por cues"
    fase: F-07.1
    status: concluida
    objetivo: "Portar editar_demo: cortar a gravacao por cue, acelerar ou congelar para caber na fala e enquadrar 9:16 (D-32)."
    arquivos:
      cria: [motor/src/expxmedia/aula/editar_tela.py, motor/tests/aula/test_editar_tela.py]
      altera: []
    teste_integracao: "Uma gravacao sintetica de 20 s e cues de 3 cenas gera demo.mp4 com a duracao total das cues."
    teste_funcional: "Um trecho mais curto que a fala congela o ultimo quadro ate completar a duracao da cue."
    criterio_aceite: "cd motor && uv run pytest tests/aula/test_editar_tela.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-04.01]
    paralelizavel: true
    concluida_em: 2026-09-25
    suite: verde
  - id: T-07.04
    titulo: "Composicao de aula L16 e L9"
    fase: F-07.2
    status: concluida
    objetivo: "Portar a composicao de aula com layouts 16:9 e 9:16, area segura, PiP do avatar e legenda, com marca da Alma."
    arquivos:
      cria: [motor/kit-remotion/src/composicoes/Aula/index.tsx, motor/kit-remotion/src/composicoes/Aula/layouts.ts, motor/tests/aula/test_composicao.py]
      altera: []
    teste_integracao: "Renderizar 2 s da composicao nos dois formatos gera MP4 1920x1080 e 1080x1920."
    teste_funcional: "O rotulo da janela do avatar vem do nome do porta-voz da Alma e as constantes de layout sao SAFE 168/280 e PiP 272x340 com topo em 1318 no 9:16."
    criterio_aceite: "cd motor && uv run pytest tests/aula/test_composicao.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.03, T-07.01]
    paralelizavel: false
    concluida_em: 2026-09-25
    suite: verde
  - id: T-07.05
    titulo: "Producao de aula"
    fase: F-07.2
    status: concluida
    objetivo: "Produzir aula: narrar com parametros de aula e sem ritmo minimo, cues, legendas 42x2, avatar opcional a partir do audio, tela opcional, render nos formatos pedidos, SRT e peca.json com compoe (D-40)."
    arquivos:
      cria: [motor/src/expxmedia/producao/aula.py, motor/tests/aula/test_producao.py]
      altera: []
    teste_integracao: "Produzir uma aula curta com provedor de teste nos dois formatos gera dois MP4 e dois SRT aprovados no perfil aula."
    teste_funcional: "Uma aula que usa uma apresentacao registra o peca_id dela em compoe e a narracao da aula nao passa pela correcao de ritmo."
    criterio_aceite: "cd motor && uv run pytest tests/aula/test_producao.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-07.04, T-07.02, T-07.03, T-04.09, T-05.11]
    paralelizavel: false
    concluida_em: 2026-09-25
    suite: verde
  - id: T-07.06
    titulo: "Template de aula e compilacao"
    fase: F-07.2
    status: concluida
    objetivo: "Criar o template de aula embarcado e a compilacao de episodios com SRT unico."
    arquivos:
      cria: [templates/aula/padrao/template.json, templates/aula/padrao/package.json, templates/aula/padrao/src/Composicao.tsx, templates/aula/padrao/exemplo.json, motor/src/expxmedia/aula/compilar.py, motor/tests/aula/test_compilar.py]
      altera: []
    teste_integracao: "Compilar duas aulas produzidas gera um MP4 com a soma das duracoes e um SRT com tempos deslocados."
    teste_funcional: "O template de aula passa em template.validar no modo template sem achado."
    criterio_aceite: "cd motor && uv run pytest tests/aula/test_compilar.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-07.05]
    paralelizavel: false
    concluida_em: 2026-09-25
    suite: verde
  - id: T-07.07
    titulo: "CLI de aula e avatar"
    fase: F-07.2
    status: concluida
    objetivo: "Expor produzir aula, aula compilar, aula editar-tela e avatar gerar no CLI."
    arquivos:
      cria: [motor/src/expxmedia/cli_comandos/aula.py, motor/tests/test_cli_aula.py]
      altera: []
    teste_integracao: "Cada subcomando novo aparece no --help e produzir aula com o provedor de teste em subprocesso sai 0 com o peca_id."
    teste_funcional: "avatar gerar sem HEYGEN_API_KEY e sem provedor de teste sai com codigo 3 e a orientacao de como_habilitar."
    criterio_aceite: "cd motor && uv run pytest tests/test_cli_aula.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-07.06]
    paralelizavel: false
    concluida_em: 2026-09-25
    suite: verde
---

# Tasks — Sprint 07

> Comando de teste: `cd motor && uv run pytest tests/aula tests/avatar tests/test_cli_aula.py`. Base de conhecimento em `docs/nucleo-expxmedia/base/`; decisões em `00-DECISOES.md`. Nenhuma task escreve nos projetos de origem (D-37).

---

### T-07.01 — Cues do roteiro de aula

```yaml
id: T-07.01
titulo: Cues do roteiro de aula
fase: F-07.1
objetivo: Portar marcadores [[sN]] para cues.json a partir do alinhamento, com hash da narração para invalidar dependentes.
arquivos:
  cria: [motor/src/expxmedia/aula/cues.py, motor/tests/aula/test_cues.py]
  altera: []
teste_integracao: Com o roteiro e o alinhamento do provedor de teste, cues.json tem um início por marcador em ordem crescente e um marcador seguido de espaços aponta para a próxima letra falada.
teste_funcional: Mudar a narração muda o hash gravado e marca avatar e legendas existentes como desatualizados.
criterio_aceite: `cd motor && uv run pytest tests/aula/test_cues.py` termina com 0 failed
depende_de: [T-04.03]
paralelizavel: true
status: concluida
concluida: 2026-09-25 · suíte: F-07.1 32 passed, 0 skipped
```

---

### T-07.02 — Avatar HeyGen v3 e provedor de teste

```yaml
id: T-07.02
titulo: Avatar HeyGen v3 e provedor de teste
fase: F-07.1
objetivo: Gerar avatar a partir do áudio pela API v3 (upload, audio_asset_id, polling, download) e provedor de teste (D-26, D-34).
arquivos:
  cria: [motor/src/expxmedia/avatar/heygen.py, motor/src/expxmedia/avatar/teste.py, motor/tests/avatar/test_heygen.py]
  altera: []
teste_integracao: Contra o stub, o fluxo faz upload do áudio, cria o vídeo com audio_asset_id e baixa após status completed.
teste_funcional: Status failed no polling devolve erro com a mensagem do provedor e nenhuma nova criação.
criterio_aceite: `cd motor && uv run pytest tests/avatar/test_heygen.py` termina com 0 failed
depende_de: [T-02.07, T-01.04]
paralelizavel: true
status: concluida
concluida: 2026-09-25 · suíte: F-07.1 32 passed, 0 skipped
```

---

### T-07.03 — Edicao da gravacao de tela por cues

```yaml
id: T-07.03
titulo: Edicao da gravacao de tela por cues
fase: F-07.1
objetivo: Portar editar_demo: cortar a gravação por cue, acelerar ou congelar para caber na fala e enquadrar 9:16 (D-32).
arquivos:
  cria: [motor/src/expxmedia/aula/editar_tela.py, motor/tests/aula/test_editar_tela.py]
  altera: []
teste_integracao: Uma gravação sintética de 20 s e cues de 3 cenas gera demo.mp4 com a duração total das cues.
teste_funcional: Um trecho mais curto que a fala congela o último quadro até completar a duração da cue.
criterio_aceite: `cd motor && uv run pytest tests/aula/test_editar_tela.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-04.01]
paralelizavel: true
status: concluida
concluida: 2026-09-25 · suíte: F-07.1 32 passed, 0 skipped
```

---

### T-07.04 — Composicao de aula L16 e L9

```yaml
id: T-07.04
titulo: Composicao de aula L16 e L9
fase: F-07.2
objetivo: Portar a composição de aula com layouts 16:9 e 9:16, área segura, PiP do avatar e legenda, com marca da Alma.
arquivos:
  cria: [motor/kit-remotion/src/composicoes/Aula/index.tsx, motor/kit-remotion/src/composicoes/Aula/layouts.ts, motor/tests/aula/test_composicao.py]
  altera: []
teste_integracao: Renderizar 2 s da composição nos dois formatos gera MP4 1920x1080 e 1080x1920.
teste_funcional: O rótulo da janela do avatar vem do nome do porta-voz da Alma e as constantes de layout são SAFE 168/280 e PiP 272x340 com topo em 1318 no 9:16.
criterio_aceite: `cd motor && uv run pytest tests/aula/test_composicao.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.03, T-07.01]
paralelizavel: false
status: concluida
concluida: 2026-09-25 · suíte: sprint 07: 50 passed, 0 skipped
```

---

### T-07.05 — Producao de aula

```yaml
id: T-07.05
titulo: Producao de aula
fase: F-07.2
objetivo: Produzir aula: narrar com parâmetros de aula e sem ritmo mínimo, cues, legendas 42x2, avatar opcional a partir do áudio, tela opcional, render nos formatos pedidos, SRT e peca.json com compoe (D-40).
arquivos:
  cria: [motor/src/expxmedia/producao/aula.py, motor/tests/aula/test_producao.py]
  altera: []
teste_integracao: Produzir uma aula curta com provedor de teste nos dois formatos gera dois MP4 e dois SRT aprovados no perfil aula.
teste_funcional: Uma aula que usa uma apresentação registra o peca_id dela em compoe e a narração da aula não passa pela correção de ritmo.
criterio_aceite: `cd motor && uv run pytest tests/aula/test_producao.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-07.04, T-07.02, T-07.03, T-04.09, T-05.11]
paralelizavel: false
status: concluida
concluida: 2026-09-25 · suíte: sprint 07: 50 passed, 0 skipped
```

---

### T-07.06 — Template de aula e compilacao

```yaml
id: T-07.06
titulo: Template de aula e compilacao
fase: F-07.2
objetivo: Criar o template de aula embarcado e a compilação de episódios com SRT único.
arquivos:
  cria: [templates/aula/padrao/template.json, templates/aula/padrao/package.json, templates/aula/padrao/src/Composicao.tsx, templates/aula/padrao/exemplo.json, motor/src/expxmedia/aula/compilar.py, motor/tests/aula/test_compilar.py]
  altera: []
teste_integracao: Compilar duas aulas produzidas gera um MP4 com a soma das durações e um SRT com tempos deslocados.
teste_funcional: O template de aula passa em template.validar no modo template sem achado.
criterio_aceite: `cd motor && uv run pytest tests/aula/test_compilar.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-07.05]
paralelizavel: false
status: concluida
concluida: 2026-09-25 · suíte: sprint 07: 50 passed, 0 skipped
```

---

### T-07.07 — CLI de aula e avatar

```yaml
id: T-07.07
titulo: CLI de aula e avatar
fase: F-07.2
objetivo: Expor produzir aula, aula compilar, aula editar-tela e avatar gerar no CLI.
arquivos:
  cria: [motor/src/expxmedia/cli_comandos/aula.py, motor/tests/test_cli_aula.py]
  altera: []
teste_integracao: Cada subcomando novo aparece no --help e produzir aula com o provedor de teste em subprocesso sai 0 com o peca_id.
teste_funcional: avatar gerar sem HEYGEN_API_KEY e sem provedor de teste sai com código 3 e a orientação de como_habilitar.
criterio_aceite: `cd motor && uv run pytest tests/test_cli_aula.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-07.06]
paralelizavel: false
status: concluida
concluida: 2026-09-25 · suíte: sprint 07: 50 passed, 0 skipped
```
