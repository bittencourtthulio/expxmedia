---
expx_schema: 1
expx_tool: sprintx
kind: tasks
trabalho_id: nucleo-expxmedia
sprint_id: sprint-01
atualizado_em: 2026-09-24
tasks:
  - id: T-01.01
    titulo: "Pacote Python e pyproject com todas as dependencias"
    fase: F-01.1
    status: concluida
    objetivo: "Criar o pacote expxmedia com uv, src layout, Python 3.11+, pytest, o script expxmedia-motor e TODAS as dependencias do plano declaradas de uma vez: playwright, pillow, numpy, opencv-python-headless, filelock, jsonschema, requests, faster-whisper, rembg, onnxruntime, scikit-image (dev) e openai-whisper como extra opcional, o esqueleto de subpacotes com __init__.py e addopts --import-mode=importlib (D-14, D-42)."
    arquivos:
      cria: [motor/pyproject.toml, motor/uv.lock, motor/src/expxmedia/__init__.py, motor/src/expxmedia/nucleo/__init__.py, motor/src/expxmedia/ambiente/__init__.py, motor/src/expxmedia/alma/__init__.py, motor/src/expxmedia/peca/__init__.py, motor/src/expxmedia/template/__init__.py, motor/src/expxmedia/render_html/__init__.py, motor/src/expxmedia/imagem/__init__.py, motor/src/expxmedia/captura/__init__.py, motor/src/expxmedia/producao/__init__.py, motor/src/expxmedia/producao/apresentacao/__init__.py, motor/src/expxmedia/video/__init__.py, motor/src/expxmedia/narrar/__init__.py, motor/src/expxmedia/transcrever/__init__.py, motor/src/expxmedia/legendar/__init__.py, motor/src/expxmedia/motion/__init__.py, motor/src/expxmedia/referencia/__init__.py, motor/src/expxmedia/corte/__init__.py, motor/src/expxmedia/aula/__init__.py, motor/src/expxmedia/avatar/__init__.py, motor/src/expxmedia/publicar/__init__.py, motor/src/expxmedia/agendador/__init__.py, motor/src/expxmedia/revisar/__init__.py, motor/src/expxmedia/cli_comandos/__init__.py, motor/tests/stubs/__init__.py, motor/tests/test_pacote.py]
      altera: [.gitignore]
    teste_integracao: "O pytest descobre e roda o teste de import do pacote pelo uv."
    teste_funcional: "Importar expxmedia devolve __version__ igual a 0.1.0 e cada dependencia declarada e importavel no ambiente do uv."
    criterio_aceite: "cd motor && uv run pytest tests/test_pacote.py termina com 0 failed"
    depende_de: []
    paralelizavel: false
    concluida_em: 2026-09-24
    suite: verde
  - id: T-01.02
    titulo: "Conftest com rede bloqueada e marcador integracao_local"
    fase: F-01.1
    status: concluida
    objetivo: "Bloquear rede externa na suite e pular testes locais quando o binario faltar (D-14)."
    arquivos:
      cria: [motor/tests/conftest.py, motor/tests/test_harness.py]
      altera: []
    teste_integracao: "Um teste que abre socket para host externo recebe ConnectionError enquanto 127.0.0.1 continua permitido, e HF_HUB_OFFLINE=1 esta definido na sessao."
    teste_funcional: "A fixture requer_binario com um nome inexistente marca o teste como pulado com o nome no motivo."
    criterio_aceite: "cd motor && uv run pytest tests/test_harness.py termina com 0 failed"
    depende_de: [T-01.01]
    paralelizavel: false
    concluida_em: 2026-09-24
    suite: verde
  - id: T-01.03
    titulo: "Fixture de instalacao com Alma ficticia"
    fase: F-01.1
    status: concluida
    objetivo: "Criar uma empresa ficticia completa, a fixture que monta uma instalacao em pasta temporaria e a fixture de rosto gerada de skimage.data.astronaut (dominio publico) (D-02, D-43)."
    arquivos:
      cria: [motor/tests/fixtures/alma-ficticia/alma/alma.json, motor/tests/fixtures/alma-ficticia/alma/voz.md, motor/tests/fixtures/alma-ficticia/alma/assets/logo.svg, motor/tests/fixtures/alma-ficticia/alma/assets/retratos/porta-voz-teste/01.png, motor/tests/fixtures/rosto/astronauta.png, motor/tests/fixtures/instalacao.py, motor/tests/test_instalacao.py]
      altera: [motor/tests/conftest.py]
    teste_integracao: "A fixture instalacao cria em tmp_path as pastas alma/, pecas/, estado/, eventos/ e um .env vazio."
    teste_funcional: "O alma.json ficticio contem todas as secoes do CONTRATO-alma e nenhuma string da varredura de marca."
    criterio_aceite: "cd motor && uv run pytest tests/test_instalacao.py termina com 0 failed"
    depende_de: [T-01.02]
    paralelizavel: true
    concluida_em: 2026-09-24
    suite: verde
  - id: T-01.04
    titulo: "Stub HTTP local"
    fase: F-01.1
    status: concluida
    objetivo: "Criar um servidor HTTP local que registra rotas e grava as requisicoes, para testar provedores sem rede."
    arquivos:
      cria: [motor/tests/stubs/servidor.py, motor/tests/test_stub.py]
      altera: []
    teste_integracao: "O stub sobe em 127.0.0.1 numa porta livre e responde a rota registrada apesar do bloqueio de rede."
    teste_funcional: "Uma rota POST registrada com resposta JSON devolve esse JSON e guarda corpo e cabecalhos recebidos."
    criterio_aceite: "cd motor && uv run pytest tests/test_stub.py termina com 0 failed"
    depende_de: [T-01.02]
    paralelizavel: true
    concluida_em: 2026-09-24
    suite: verde
  - id: T-01.05
    titulo: "Kit Remotion com versoes travadas e registro gerado"
    fase: F-01.2
    status: concluida
    objetivo: "Criar o kit TypeScript com versoes exatas de remotion, @remotion/bundler, @remotion/renderer, @remotion/cli, @remotion/fonts, @remotion/captions e @remotion/layout-utils em 4.0.528, react e react-dom 19.3.0, typescript 5.8.3, @types/react e @fontsource/inter, gerando o package-lock.json com npm install (rede, uma vez), uma composicao de teste e o Root que importa um registro gerado atomicamente a partir das pastas src/composicoes/*, para que nenhuma task futura edite o Root (D-17, D-46)."
    arquivos:
      cria: [motor/kit-remotion/package.json, motor/kit-remotion/package-lock.json, motor/kit-remotion/tsconfig.json, motor/kit-remotion/src/index.ts, motor/kit-remotion/src/Root.tsx, motor/kit-remotion/scripts/registrar.mjs, motor/kit-remotion/src/composicoes/Vazio/index.tsx, motor/tests/test_kit_remotion.py]
      altera: [.gitignore]
    teste_integracao: "Com o kit instalado, rodar scripts/registrar.mjs e npx remotion compositions lista a composicao Vazio vinda de src/composicoes/Vazio."
    teste_funcional: "O package.json declara os pacotes listados sem ^ nem ~ e cada um deles existe em node_modules na versao declarada."
    criterio_aceite: "cd motor && uv run pytest tests/test_kit_remotion.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-01.02]
    paralelizavel: false
    concluida_em: 2026-09-24
    suite: verde
  - id: T-01.06
    titulo: "Varredura de marca"
    fase: F-01.2
    status: concluida
    objetivo: "Garantir por teste que nenhum codigo do nucleo carrega marca (M13, D-02)."
    arquivos:
      cria: [motor/tests/test_marca.py, motor/tests/marca_proibida.txt]
      altera: []
    teste_integracao: "A varredura percorre motor/src, motor/kit-remotion/src, motor/kit-remotion/scripts, nucleo/ e templates/ e falha com arquivo e linha quando acha termo proibido."
    teste_funcional: "Um arquivo temporario contendo o nome do dono dos projetos de origem e apontado pela funcao de varredura."
    criterio_aceite: "cd motor && uv run pytest tests/test_marca.py termina com 0 failed"
    depende_de: [T-01.02]
    paralelizavel: true
    concluida_em: 2026-09-24
    suite: verde
  - id: T-01.08
    titulo: "Preparacao do ambiente local"
    fase: F-01.2
    status: concluida
    objetivo: "Criar o script de preparacao, rodado uma vez pela task (fora da suite): uv sync, playwright install chromium, npm ci do kit, npx remotion browser ensure com o browser compartilhado pelo runner, copia da Inter (OFL) de @fontsource/inter para recursos/fontes/Inter, download de faster-whisper small e medium e do u2net se ausentes; o teste so confere presenca de binarios, caches (faster-whisper small e medium, u2net, chrome-headless-shell, Chromium) e arquivos (D-42)."
    arquivos:
      cria: [motor/scripts/preparar_ambiente.py, motor/src/expxmedia/recursos/fontes/Inter/OFL.txt, motor/src/expxmedia/recursos/fontes/Inter/inter-latin-400-normal.woff2, motor/src/expxmedia/recursos/fontes/Inter/inter-latin-700-normal.woff2, motor/tests/test_ambiente_local.py]
      altera: []
    teste_integracao: "Depois da execucao unica do script, o teste encontra Chromium do Playwright, chrome-headless-shell do Remotion, faster-whisper small e medium, u2net e os woff2 da Inter, sem executar instalacao nenhuma."
    teste_funcional: "O teste de ambiente falha citando o nome do item quando um binario da lista (ffmpeg, say, node, claude) nao esta no PATH."
    criterio_aceite: "cd motor && uv run pytest tests/test_ambiente_local.py termina com 0 failed e 0 skipped nesta maquina"
    depende_de: [T-01.05]
    paralelizavel: false
    concluida_em: 2026-09-24
    suite: verde
  - id: T-01.07
    titulo: "Goldens do sistema atual"
    fase: F-01.2
    status: concluida
    objetivo: "Gravar em copia temporaria as saidas de referencia: G1 render e render.json do layout Instagram-Carrosseis/galeria/layouts/0001-pos-paineis-de-pagamento com seu exemplo.json, a alma-golden.json com as cores do tema e as fontes baixadas; G2 timeline.json e trilha.wav de Instragram-Videos/remotion/src/reels/recriado-ia-decide com videos/recriado-ia-decide; G3 caps, end.png e legendas.json de Instragram-Videos/videos/firecrawl-firecrawl; G4 MP4 e resumo ffprobe do compose do mesmo video, com uma alma-golden-reel.json que reproduz as cores de captions.py/compose.py e aponta a fonte local do sistema usada na origem so para os testes (D-47); G5 legendas.json, SRT e cues.json de cursos-ia/radar-ia-09-jev-calibracao; G6 deck.json de youtube-squad/apresentacoes/decks/2026-09-24-claude-code-ficou-caro-quanto-custa-de-verdade-e; G7 transcricao, transcricao recasada e trecho escolhido por momentos.py em Instragram-Videos/videos/yt-04hAay1cjyU-t0239; G8 a narracao falada de videos/recriado-ia-decide (D-16, D-37)."
    arquivos:
      cria: [motor/scripts/gerar_golden.py, motor/tests/golden/manifesto.json, motor/tests/golden/README.md, motor/tests/test_golden_presentes.py]
      altera: []
    teste_integracao: "O script executa o codigo dos projetos de origem numa copia temporaria e o sha256 de cada arquivo de origem lido e igual antes e depois da execucao."
    teste_funcional: "O manifesto lista G1 a G8 com sha256, comando de origem e entrada usada, e o teste falha se qualquer um dos oito ou um arquivo listado faltar."
    criterio_aceite: "cd motor && uv run pytest tests/test_golden_presentes.py termina com 0 failed"
    depende_de: [T-01.03, T-01.08]
    paralelizavel: false
    concluida_em: 2026-09-24
    suite: verde
---

# Tasks — Sprint 01

> Comando de teste: `cd motor && uv run pytest`. Base de conhecimento em `docs/nucleo-expxmedia/base/`; decisões em `00-DECISOES.md`. Nenhuma task escreve nos projetos de origem (D-37).

---

### T-01.01 — Pacote Python e pyproject com todas as dependencias

```yaml
id: T-01.01
titulo: Pacote Python e pyproject com todas as dependencias
fase: F-01.1
objetivo: Criar o pacote expxmedia com uv, src layout, Python 3.11+, pytest, o script expxmedia-motor e TODAS as dependências do plano declaradas de uma vez: playwright, pillow, numpy, opencv-python-headless, filelock, jsonschema, requests, faster-whisper, rembg, onnxruntime, scikit-image (dev) e openai-whisper como extra opcional, o esqueleto de subpacotes com __init__.py e addopts --import-mode=importlib (D-14, D-42).
arquivos:
  cria: [motor/pyproject.toml, motor/uv.lock, motor/src/expxmedia/__init__.py, motor/src/expxmedia/nucleo/__init__.py, motor/src/expxmedia/ambiente/__init__.py, motor/src/expxmedia/alma/__init__.py, motor/src/expxmedia/peca/__init__.py, motor/src/expxmedia/template/__init__.py, motor/src/expxmedia/render_html/__init__.py, motor/src/expxmedia/imagem/__init__.py, motor/src/expxmedia/captura/__init__.py, motor/src/expxmedia/producao/__init__.py, motor/src/expxmedia/producao/apresentacao/__init__.py, motor/src/expxmedia/video/__init__.py, motor/src/expxmedia/narrar/__init__.py, motor/src/expxmedia/transcrever/__init__.py, motor/src/expxmedia/legendar/__init__.py, motor/src/expxmedia/motion/__init__.py, motor/src/expxmedia/referencia/__init__.py, motor/src/expxmedia/corte/__init__.py, motor/src/expxmedia/aula/__init__.py, motor/src/expxmedia/avatar/__init__.py, motor/src/expxmedia/publicar/__init__.py, motor/src/expxmedia/agendador/__init__.py, motor/src/expxmedia/revisar/__init__.py, motor/src/expxmedia/cli_comandos/__init__.py, motor/tests/stubs/__init__.py, motor/tests/test_pacote.py]
  altera: [.gitignore]
teste_integracao: O pytest descobre e roda o teste de import do pacote pelo uv.
teste_funcional: Importar expxmedia devolve __version__ igual a 0.1.0 e cada dependência declarada é importável no ambiente do uv.
criterio_aceite: `cd motor && uv run pytest tests/test_pacote.py` termina com 0 failed
depende_de: []
paralelizavel: false
status: concluida
concluida: 2026-09-24 · suíte: 37 passed, 0 failed
```

---

### T-01.02 — Conftest com rede bloqueada e marcador integracao_local

```yaml
id: T-01.02
titulo: Conftest com rede bloqueada e marcador integracao_local
fase: F-01.1
objetivo: Bloquear rede externa na suíte e pular testes locais quando o binário faltar (D-14).
arquivos:
  cria: [motor/tests/conftest.py, motor/tests/test_harness.py]
  altera: []
teste_integracao: Um teste que abre socket para host externo recebe ConnectionError enquanto 127.0.0.1 continua permitido, e HF_HUB_OFFLINE=1 está definido na sessão.
teste_funcional: A fixture requer_binario com um nome inexistente marca o teste como pulado com o nome no motivo.
criterio_aceite: `cd motor && uv run pytest tests/test_harness.py` termina com 0 failed
depende_de: [T-01.01]
paralelizavel: false
status: concluida
concluida: 2026-09-24 · suíte: 11 passed, 0 failed (suíte 48 passed)
```

---

### T-01.03 — Fixture de instalacao com Alma ficticia

```yaml
id: T-01.03
titulo: Fixture de instalacao com Alma ficticia
fase: F-01.1
objetivo: Criar uma empresa fictícia completa, a fixture que monta uma instalação em pasta temporária e a fixture de rosto gerada de skimage.data.astronaut (domínio público) (D-02, D-43).
arquivos:
  cria: [motor/tests/fixtures/alma-ficticia/alma/alma.json, motor/tests/fixtures/alma-ficticia/alma/voz.md, motor/tests/fixtures/alma-ficticia/alma/assets/logo.svg, motor/tests/fixtures/alma-ficticia/alma/assets/retratos/porta-voz-teste/01.png, motor/tests/fixtures/rosto/astronauta.png, motor/tests/fixtures/instalacao.py, motor/tests/test_instalacao.py]
  altera: [motor/tests/conftest.py]
teste_integracao: A fixture instalacao cria em tmp_path as pastas alma/, pecas/, estado/, eventos/ e um .env vazio.
teste_funcional: O alma.json fictício contém todas as seções do CONTRATO-alma e nenhuma string da varredura de marca.
criterio_aceite: `cd motor && uv run pytest tests/test_instalacao.py` termina com 0 failed
depende_de: [T-01.02]
paralelizavel: true
status: concluida
concluida: 2026-09-24 · suíte: 12 passed, 0 failed (suíte 67 passed)
```

---

### T-01.04 — Stub HTTP local

```yaml
id: T-01.04
titulo: Stub HTTP local
fase: F-01.1
objetivo: Criar um servidor HTTP local que registra rotas e grava as requisições, para testar provedores sem rede.
arquivos:
  cria: [motor/tests/stubs/servidor.py, motor/tests/test_stub.py]
  altera: []
teste_integracao: O stub sobe em 127.0.0.1 numa porta livre e responde à rota registrada apesar do bloqueio de rede.
teste_funcional: Uma rota POST registrada com resposta JSON devolve esse JSON e guarda corpo e cabeçalhos recebidos.
criterio_aceite: `cd motor && uv run pytest tests/test_stub.py` termina com 0 failed
depende_de: [T-01.02]
paralelizavel: true
status: concluida
concluida: 2026-09-24 · suíte: 7 passed, 0 failed
```

---

### T-01.05 — Kit Remotion com versoes travadas e registro gerado

```yaml
id: T-01.05
titulo: Kit Remotion com versoes travadas e registro gerado
fase: F-01.2
objetivo: Criar o kit TypeScript com versões exatas de remotion, @remotion/bundler, @remotion/renderer, @remotion/cli, @remotion/fonts, @remotion/captions e @remotion/layout-utils em 4.0.528, react e react-dom 19.3.0, typescript 5.8.3, @types/react e @fontsource/inter, gerando o package-lock.json com npm install (rede, uma vez), uma composição de teste e o Root que importa um registro gerado atomicamente a partir das pastas src/composicoes/*, para que nenhuma task futura edite o Root (D-17, D-46).
arquivos:
  cria: [motor/kit-remotion/package.json, motor/kit-remotion/package-lock.json, motor/kit-remotion/tsconfig.json, motor/kit-remotion/src/index.ts, motor/kit-remotion/src/Root.tsx, motor/kit-remotion/scripts/registrar.mjs, motor/kit-remotion/src/composicoes/Vazio/index.tsx, motor/tests/test_kit_remotion.py]
  altera: [.gitignore]
teste_integracao: Com o kit instalado, rodar scripts/registrar.mjs e npx remotion compositions lista a composição Vazio vinda de src/composicoes/Vazio.
teste_funcional: O package.json declara os pacotes listados sem ^ nem ~ e cada um deles existe em node_modules na versão declarada.
criterio_aceite: `cd motor && uv run pytest tests/test_kit_remotion.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-01.02]
paralelizavel: false
status: concluida
concluida: 2026-09-24 · suíte: 18 passed, 0 failed, 0 skipped
```

---

### T-01.06 — Varredura de marca

```yaml
id: T-01.06
titulo: Varredura de marca
fase: F-01.2
objetivo: Garantir por teste que nenhum código do núcleo carrega marca (M13, D-02).
arquivos:
  cria: [motor/tests/test_marca.py, motor/tests/marca_proibida.txt]
  altera: []
teste_integracao: A varredura percorre motor/src, motor/kit-remotion/src, motor/kit-remotion/scripts, nucleo/ e templates/ e falha com arquivo e linha quando acha termo proibido.
teste_funcional: Um arquivo temporário contendo o nome do dono dos projetos de origem é apontado pela função de varredura.
criterio_aceite: `cd motor && uv run pytest tests/test_marca.py` termina com 0 failed
depende_de: [T-01.02]
paralelizavel: true
status: concluida
concluida: 2026-09-24 · suíte: 6 passed, 0 failed
```

---

### T-01.08 — Preparacao do ambiente local

```yaml
id: T-01.08
titulo: Preparacao do ambiente local
fase: F-01.2
objetivo: Criar o script de preparação, rodado uma vez pela task (fora da suíte): uv sync, playwright install chromium, npm ci do kit, npx remotion browser ensure com o browser compartilhado pelo runner, cópia da Inter (OFL) de @fontsource/inter para recursos/fontes/Inter, download de faster-whisper small e medium e do u2net se ausentes; o teste só confere presença de binários, caches (faster-whisper small e medium, u2net, chrome-headless-shell, Chromium) e arquivos (D-42).
arquivos:
  cria: [motor/scripts/preparar_ambiente.py, motor/src/expxmedia/recursos/fontes/Inter/OFL.txt, motor/src/expxmedia/recursos/fontes/Inter/inter-latin-400-normal.woff2, motor/src/expxmedia/recursos/fontes/Inter/inter-latin-700-normal.woff2, motor/tests/test_ambiente_local.py]
  altera: []
teste_integracao: Depois da execução única do script, o teste encontra Chromium do Playwright, chrome-headless-shell do Remotion, faster-whisper small e medium, u2net e os woff2 da Inter, sem executar instalação nenhuma.
teste_funcional: O teste de ambiente falha citando o nome do item quando um binário da lista (ffmpeg, say, node, claude) não está no PATH.
criterio_aceite: `cd motor && uv run pytest tests/test_ambiente_local.py` termina com 0 failed e 0 skipped nesta maquina
depende_de: [T-01.05]
paralelizavel: false
status: concluida
concluida: 2026-09-24 · suíte: 17 passed, 0 failed, 0 skipped
```

---

### T-01.07 — Goldens do sistema atual

```yaml
id: T-01.07
titulo: Goldens do sistema atual
fase: F-01.2
objetivo: Gravar em cópia temporária as saídas de referência: G1 render e render.json do layout Instagram-Carrosseis/galeria/layouts/0001-pos-paineis-de-pagamento com seu exemplo.json, a alma-golden.json com as cores do tema e as fontes baixadas; G2 timeline.json e trilha.wav de Instragram-Videos/remotion/src/reels/recriado-ia-decide com videos/recriado-ia-decide; G3 caps, end.png e legendas.json de Instragram-Videos/videos/firecrawl-firecrawl; G4 MP4 e resumo ffprobe do compose do mesmo vídeo, com uma alma-golden-reel.json que reproduz as cores de captions.py/compose.py e aponta a fonte local do sistema usada na origem só para os testes (D-47); G5 legendas.json, SRT e cues.json de cursos-ia/radar-ia-09-jev-calibracao; G6 deck.json de youtube-squad/apresentacoes/decks/2026-09-24-claude-code-ficou-caro-quanto-custa-de-verdade-e; G7 transcrição, transcrição recasada e trecho escolhido por momentos.py em Instragram-Videos/videos/yt-04hAay1cjyU-t0239; G8 a narração falada de videos/recriado-ia-decide (D-16, D-37).
arquivos:
  cria: [motor/scripts/gerar_golden.py, motor/tests/golden/manifesto.json, motor/tests/golden/README.md, motor/tests/test_golden_presentes.py]
  altera: []
teste_integracao: O script executa o código dos projetos de origem numa cópia temporária e o sha256 de cada arquivo de origem lido é igual antes e depois da execução.
teste_funcional: O manifesto lista G1 a G8 com sha256, comando de origem e entrada usada, e o teste falha se qualquer um dos oito ou um arquivo listado faltar.
criterio_aceite: `cd motor && uv run pytest tests/test_golden_presentes.py` termina com 0 failed
depende_de: [T-01.03, T-01.08]
paralelizavel: false
status: concluida
concluida: 2026-09-24 · suíte: 12 passed, 0 failed (suíte 120 passed)
```
