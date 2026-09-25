---
expx_schema: 1
expx_tool: sprintx
kind: tasks
trabalho_id: nucleo-expxmedia
sprint_id: sprint-06
atualizado_em: 2026-09-24
tasks:
  - id: T-06.01
    titulo: "Analise do video de referencia"
    fase: F-06.1
    status: pendente
    objetivo: "Portar analisar_reel: scdet 10, quadros a cada 2 s ate 24, folhas 6x2 a 1 quadro/s, whisper e formato.json."
    arquivos:
      cria: [motor/src/expxmedia/referencia/analisar.py, motor/tests/referencia/test_analisar.py]
      altera: []
    teste_integracao: "Analisar um video sintetico de 12 s com 4 cores gera folhas com 12 quadros em ordem e formato.json com duracao 12."
    teste_funcional: "O formato.json traz largura, altura, fps e duracao, e a pasta analise/ contem o esqueleto de leitura.md com as 9 secoes."
    criterio_aceite: "cd motor && uv run pytest tests/referencia/test_analisar.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-04.07, T-04.01]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-06.02
    titulo: "Pasta do reel sob medida e validacao do cenas.json"
    fase: F-06.1
    status: pendente
    objetivo: "Criar a pasta do reel sob medida a partir do kit e validar cenas.json: ancoras em ordem, eventos existentes e trilha diferente das anteriores."
    arquivos:
      cria: [motor/src/expxmedia/referencia/sob_medida.py, motor/tests/referencia/test_sob_medida.py]
      altera: []
    teste_integracao: "Criar um reel sob medida gera cenas.json esqueleto e Reel.tsx que compila com o kit."
    teste_funcional: "Um cenas.json com trilha igual a de outro reel da instalacao e recusado com a mensagem de trilha repetida."
    criterio_aceite: "cd motor && uv run pytest tests/referencia/test_sob_medida.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-05.02, T-02.12]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-06.03
    titulo: "Montar, previa, render e verificacao do sob medida"
    fase: F-06.1
    status: pendente
    objetivo: "Encadear montagem, previa com guias, render, normalizacao e verificacao no perfil sob_medida, com o validador de codigo no modo sob_medida (D-36)."
    arquivos:
      cria: [motor/src/expxmedia/producao/reel_referencia.py, motor/tests/referencia/test_reel_referencia.py]
      altera: []
    teste_integracao: "Com um reel sob medida de exemplo e o provedor de teste, o encadeamento gera MP4 aprovado no perfil sob_medida."
    teste_funcional: "Um Reel.tsx que importa child_process e recusado antes do render com achado do validador."
    criterio_aceite: "cd motor && uv run pytest tests/referencia/test_reel_referencia.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-06.02, T-05.04, T-05.06]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-06.04
    titulo: "Momentos do video longo"
    fase: F-06.2
    status: pendente
    objetivo: "Portar a escolha de trecho com listas de palavras e pesos em configuracao por idioma, padrao igual ao atual."
    arquivos:
      cria: [motor/src/expxmedia/corte/momentos.py, motor/src/expxmedia/recursos/momentos/pt.json, motor/tests/corte/test_momentos.py]
      altera: []
    teste_integracao: "Com a transcricao do G7, a escolha devolve o mesmo trecho que o sistema atual escolheu."
    teste_funcional: "A janela escolhida tem no maximo 72 s e comeca e termina em fronteira de palavra."
    criterio_aceite: "cd motor && uv run pytest tests/corte/test_momentos.py termina com 0 failed"
    depende_de: [T-04.07]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-06.05
    titulo: "Corte com reenquadramento"
    fase: F-06.2
    status: pendente
    objetivo: "Portar o recorte 9:16 que segue o rosto (Haar 1.15, 6, 24x24; mediana 7, EMA 0,25, zona morta 12%, RDP 14 px, teto de 24 pontos), a deteccao de screencast (0,26 mais posicao) com fronteira tela/painel por gradiente e o fundo desfocado, usando a fixture de rosto de T-01.03 (D-43)."
    arquivos:
      cria: [motor/src/expxmedia/corte/cortar.py, motor/tests/corte/test_cortar.py]
      altera: []
    teste_integracao: "Cortar um video 16:9 de 20 s montado com a fixture de rosto deslocando-se para a direita gera 9:16 com o rosto dentro do quadro em todos os quadros amostrados e no maximo 24 pontos de trajetoria."
    teste_funcional: "Sem rosto o corte usa fundo desfocado e registra o modo; ruido de 3 px nao muda a trajetoria (zona morta); num video com divisao tela/painel na coluna 1280 a fronteira detectada fica a no maximo 8 px dela."
    criterio_aceite: "cd motor && uv run pytest tests/corte/test_cortar.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-04.01]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-06.06
    titulo: "B-roll"
    fase: F-06.2
    status: pendente
    objetivo: "Buscar b-roll pelo modulo Pexels com validacao de relevancia e duracao antes de usar."
    arquivos:
      cria: [motor/src/expxmedia/corte/broll.py, motor/tests/corte/test_broll.py]
      altera: []
    teste_integracao: "Contra o stub do Pexels, pedir b-roll para um termo baixa o video vertical escolhido para a pasta da peca."
    teste_funcional: "Resultados abaixo da duracao minima sao descartados e sem resultado valido o modulo devolve vazio sem erro."
    criterio_aceite: "cd motor && uv run pytest tests/corte/test_broll.py termina com 0 failed"
    depende_de: [T-03.06]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-06.07
    titulo: "Producao de reel de corte"
    fase: F-06.2
    status: pendente
    objetivo: "Produzir reel a partir de video longo: transcrever, escolher trecho, cortar, gancho textual do compose_cut, legendar, normalizar, verificar e peca.json; video de teste de 90 s com fala sintetizada pelo say do macOS sobre a fixture de rosto (D-43)."
    arquivos:
      cria: [motor/src/expxmedia/producao/reel_corte.py, motor/tests/corte/test_reel_corte.py]
      altera: []
    teste_integracao: "Produzir a partir do video de teste de 90 s falado pelo say gera MP4 9:16 aprovado no perfil corte com o gancho nos 3 primeiros segundos."
    teste_funcional: "A peca registra arquivos com papel final, srt e fonte, e o evento geracao_concluida com segundos."
    criterio_aceite: "cd motor && uv run pytest tests/corte/test_reel_corte.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-06.04, T-06.05, T-06.06, T-04.10, T-04.02]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
  - id: T-06.08
    titulo: "Abertura gerada"
    fase: F-06.3
    status: pendente
    objetivo: "Portar a abertura com video_ia como fundo sobreposto ao inicio do reel (nunca emendada na frente): janela ate o instante em que o clipe vira a pagina, cartao desviando do rosto detectado com Haar 1.1, 5, 60x60 amostrado a cada fps/4 (abertura.py:311-357), narracao comecando em 0 e montado_em gravado depois do MP4; usa a fixture de rosto de T-01.03."
    arquivos:
      cria: [motor/src/expxmedia/producao/abertura.py, motor/tests/producao/test_abertura.py]
      altera: []
    teste_integracao: "Com o Higgsfield falso devolvendo um clipe sintetico, o reel com abertura tem a mesma duracao do reel sem abertura e a narracao comeca em t=0."
    teste_funcional: "Um rosto detectado na metade superior move o cartao para a metade inferior e abertura.json so recebe montado_em depois do MP4 existir."
    criterio_aceite: "cd motor && uv run pytest tests/producao/test_abertura.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-03.08, T-04.11]
    paralelizavel: true
    concluida_em: null
    suite: nao_executada
  - id: T-06.09
    titulo: "CLI de referencia e corte"
    fase: F-06.4
    status: pendente
    objetivo: "Expor referencia analisar, referencia criar, referencia montar, referencia previa, referencia render, produzir reel-corte e produzir abertura no CLI."
    arquivos:
      cria: [motor/src/expxmedia/cli_comandos/referencia_corte.py, motor/tests/test_cli_referencia_corte.py]
      altera: []
    teste_integracao: "Cada subcomando novo aparece no --help e referencia analisar num video sintetico em subprocesso sai 0 e grava analise/."
    teste_funcional: "referencia montar com um cenas.json de ancora ausente sai com codigo diferente de 0 citando a cena."
    criterio_aceite: "cd motor && uv run pytest tests/test_cli_referencia_corte.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-06.03, T-06.07, T-06.08]
    paralelizavel: false
    concluida_em: null
    suite: nao_executada
---

# Tasks — Sprint 06

> Comando de teste: `cd motor && uv run pytest tests/referencia tests/corte tests/producao/test_abertura.py tests/test_cli_referencia_corte.py`. Base de conhecimento em `docs/nucleo-expxmedia/base/`; decisões em `00-DECISOES.md`. Nenhuma task escreve nos projetos de origem (D-37).

---

### T-06.01 — Analise do video de referencia

```yaml
id: T-06.01
titulo: Analise do video de referencia
fase: F-06.1
objetivo: Portar analisar_reel: scdet 10, quadros a cada 2 s até 24, folhas 6x2 a 1 quadro/s, whisper e formato.json.
arquivos:
  cria: [motor/src/expxmedia/referencia/analisar.py, motor/tests/referencia/test_analisar.py]
  altera: []
teste_integracao: Analisar um vídeo sintético de 12 s com 4 cores gera folhas com 12 quadros em ordem e formato.json com duração 12.
teste_funcional: O formato.json traz largura, altura, fps e duração, e a pasta analise/ contém o esqueleto de leitura.md com as 9 seções.
criterio_aceite: `cd motor && uv run pytest tests/referencia/test_analisar.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-04.07, T-04.01]
paralelizavel: false
status: pendente
```

---

### T-06.02 — Pasta do reel sob medida e validacao do cenas.json

```yaml
id: T-06.02
titulo: Pasta do reel sob medida e validacao do cenas.json
fase: F-06.1
objetivo: Criar a pasta do reel sob medida a partir do kit e validar cenas.json: âncoras em ordem, eventos existentes e trilha diferente das anteriores.
arquivos:
  cria: [motor/src/expxmedia/referencia/sob_medida.py, motor/tests/referencia/test_sob_medida.py]
  altera: []
teste_integracao: Criar um reel sob medida gera cenas.json esqueleto e Reel.tsx que compila com o kit.
teste_funcional: Um cenas.json com trilha igual à de outro reel da instalação é recusado com a mensagem de trilha repetida.
criterio_aceite: `cd motor && uv run pytest tests/referencia/test_sob_medida.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-05.02, T-02.12]
paralelizavel: false
status: pendente
```

---

### T-06.03 — Montar, previa, render e verificacao do sob medida

```yaml
id: T-06.03
titulo: Montar, previa, render e verificacao do sob medida
fase: F-06.1
objetivo: Encadear montagem, prévia com guias, render, normalização e verificação no perfil sob_medida, com o validador de código no modo sob_medida (D-36).
arquivos:
  cria: [motor/src/expxmedia/producao/reel_referencia.py, motor/tests/referencia/test_reel_referencia.py]
  altera: []
teste_integracao: Com um reel sob medida de exemplo e o provedor de teste, o encadeamento gera MP4 aprovado no perfil sob_medida.
teste_funcional: Um Reel.tsx que importa child_process é recusado antes do render com achado do validador.
criterio_aceite: `cd motor && uv run pytest tests/referencia/test_reel_referencia.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-06.02, T-05.04, T-05.06]
paralelizavel: false
status: pendente
```

---

### T-06.04 — Momentos do video longo

```yaml
id: T-06.04
titulo: Momentos do video longo
fase: F-06.2
objetivo: Portar a escolha de trecho com listas de palavras e pesos em configuração por idioma, padrão igual ao atual.
arquivos:
  cria: [motor/src/expxmedia/corte/momentos.py, motor/src/expxmedia/recursos/momentos/pt.json, motor/tests/corte/test_momentos.py]
  altera: []
teste_integracao: Com a transcrição do G7, a escolha devolve o mesmo trecho que o sistema atual escolheu.
teste_funcional: A janela escolhida tem no máximo 72 s e começa e termina em fronteira de palavra.
criterio_aceite: `cd motor && uv run pytest tests/corte/test_momentos.py` termina com 0 failed
depende_de: [T-04.07]
paralelizavel: true
status: pendente
```

---

### T-06.05 — Corte com reenquadramento

```yaml
id: T-06.05
titulo: Corte com reenquadramento
fase: F-06.2
objetivo: Portar o recorte 9:16 que segue o rosto (Haar 1.15, 6, 24x24; mediana 7, EMA 0,25, zona morta 12%, RDP 14 px, teto de 24 pontos), a detecção de screencast (0,26 mais posição) com fronteira tela/painel por gradiente e o fundo desfocado, usando a fixture de rosto de T-01.03 (D-43).
arquivos:
  cria: [motor/src/expxmedia/corte/cortar.py, motor/tests/corte/test_cortar.py]
  altera: []
teste_integracao: Cortar um vídeo 16:9 de 20 s montado com a fixture de rosto deslocando-se para a direita gera 9:16 com o rosto dentro do quadro em todos os quadros amostrados e no máximo 24 pontos de trajetória.
teste_funcional: Sem rosto o corte usa fundo desfocado e registra o modo; ruído de 3 px não muda a trajetória (zona morta); num vídeo com divisão tela/painel na coluna 1280 a fronteira detectada fica a no máximo 8 px dela.
criterio_aceite: `cd motor && uv run pytest tests/corte/test_cortar.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-04.01]
paralelizavel: true
status: pendente
```

---

### T-06.06 — B-roll

```yaml
id: T-06.06
titulo: B-roll
fase: F-06.2
objetivo: Buscar b-roll pelo módulo Pexels com validação de relevância e duração antes de usar.
arquivos:
  cria: [motor/src/expxmedia/corte/broll.py, motor/tests/corte/test_broll.py]
  altera: []
teste_integracao: Contra o stub do Pexels, pedir b-roll para um termo baixa o vídeo vertical escolhido para a pasta da peça.
teste_funcional: Resultados abaixo da duração mínima são descartados e sem resultado válido o módulo devolve vazio sem erro.
criterio_aceite: `cd motor && uv run pytest tests/corte/test_broll.py` termina com 0 failed
depende_de: [T-03.06]
paralelizavel: true
status: pendente
```

---

### T-06.07 — Producao de reel de corte

```yaml
id: T-06.07
titulo: Producao de reel de corte
fase: F-06.2
objetivo: Produzir reel a partir de vídeo longo: transcrever, escolher trecho, cortar, gancho textual do compose_cut, legendar, normalizar, verificar e peca.json; vídeo de teste de 90 s com fala sintetizada pelo say do macOS sobre a fixture de rosto (D-43).
arquivos:
  cria: [motor/src/expxmedia/producao/reel_corte.py, motor/tests/corte/test_reel_corte.py]
  altera: []
teste_integracao: Produzir a partir do vídeo de teste de 90 s falado pelo say gera MP4 9:16 aprovado no perfil corte com o gancho nos 3 primeiros segundos.
teste_funcional: A peça registra arquivos com papel final, srt e fonte, e o evento geracao_concluida com segundos.
criterio_aceite: `cd motor && uv run pytest tests/corte/test_reel_corte.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-06.04, T-06.05, T-06.06, T-04.10, T-04.02]
paralelizavel: false
status: pendente
```

---

### T-06.08 — Abertura gerada

```yaml
id: T-06.08
titulo: Abertura gerada
fase: F-06.3
objetivo: Portar a abertura com video_ia como fundo sobreposto ao início do reel (nunca emendada na frente): janela até o instante em que o clipe vira a página, cartão desviando do rosto detectado com Haar 1.1, 5, 60x60 amostrado a cada fps/4 (abertura.py:311-357), narração começando em 0 e montado_em gravado depois do MP4; usa a fixture de rosto de T-01.03.
arquivos:
  cria: [motor/src/expxmedia/producao/abertura.py, motor/tests/producao/test_abertura.py]
  altera: []
teste_integracao: Com o Higgsfield falso devolvendo um clipe sintético, o reel com abertura tem a mesma duração do reel sem abertura e a narração começa em t=0.
teste_funcional: Um rosto detectado na metade superior move o cartão para a metade inferior e abertura.json só recebe montado_em depois do MP4 existir.
criterio_aceite: `cd motor && uv run pytest tests/producao/test_abertura.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-03.08, T-04.11]
paralelizavel: true
status: pendente
```

---

### T-06.09 — CLI de referencia e corte

```yaml
id: T-06.09
titulo: CLI de referencia e corte
fase: F-06.4
objetivo: Expor referencia analisar, referencia criar, referencia montar, referencia previa, referencia render, produzir reel-corte e produzir abertura no CLI.
arquivos:
  cria: [motor/src/expxmedia/cli_comandos/referencia_corte.py, motor/tests/test_cli_referencia_corte.py]
  altera: []
teste_integracao: Cada subcomando novo aparece no --help e referencia analisar num vídeo sintético em subprocesso sai 0 e grava analise/.
teste_funcional: referencia montar com um cenas.json de âncora ausente sai com código diferente de 0 citando a cena.
criterio_aceite: `cd motor && uv run pytest tests/test_cli_referencia_corte.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-06.03, T-06.07, T-06.08]
paralelizavel: false
status: pendente
```
