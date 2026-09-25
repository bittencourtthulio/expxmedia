# Apresentação: deck animado e palco (youtube-squad)

Área: produção do tipo `apresentacao` (HTML navegável que simula PPT, PNG por slide e MP4 por slide) a
partir de um `deck.json` validado por schema, com identidade da ferramenta do tema, score antes do render e
render pela API Node do Remotion. Origem: `youtube-squad/` (um commit, `1444025 Initial commit`), feature
planejada em `youtube-squad/docs/apresentacoes-e-pautas/` (D-01 a D-54). Contrato alvo:
`ExpxMedia/docs/contrato/CONTRATO-peca.md:17-23,189-198`.

## Contrato de entrada

### Pastas

`apresentacoes/decks/<slug>/`: `deck.json` (só o agente `apresentador` escreve), `estado.json` (só pelo
script), `ativos/` (logo, screenshots) e `saida/` (render, fora do git); `apresentacoes/comuns/`
(`expxplay.png`, `marcas.json`); `apresentacoes/fila.json`; `apresentacoes/palco.html` (template);
`apresentacoes/motion/` (projeto Remotion) (`youtube-squad/apresentacao.py:17-18`;
`youtube-squad/apresentacoes/README.md:6-13`; `youtube-squad/.gitignore`).

### CLI `apresentacao.py` (`youtube-squad/apresentacao.py:3-15,962-987`)

`slug --titulo`, `validar-deck <slug>`, `validar <slug> --score N --motivo ... [--por]`,
`status <slug> aberta|gravada`, `lista [--json]`, `pauta --titulo --angulo --origem --score --motivo`,
`referencia [--json]`, `candidatas [--json]`, `marca <url> [--deck]`, `ler <url> [--json]`,
`screenshot --deck [--url] [--nome] [--atualizar]`, `render <slug>`, `abrir <slug>`. Erro de entrada é
`Erro(ValueError)` e vira `erro: ...` no stderr com saída 1 (`:39-40,990-996`); o painel converte em 400
(`youtube-squad/painel.py:511`).

### `deck.json` (schema: `youtube-squad/tests/decks.py:3-24`; validação: `youtube-squad/apresentacao.py:82-253`)

- Raiz: `slug`, `titulo`, `criado_em`, `gerado_por` texto obrigatório (`apresentacao.py:220-222`);
  `pauta_id` 12 hex ou `null` (`:223-224`); `pauta` objeto com `origem` (`:225-226`);
  `marca {nome, cor, cor_2, logo, site, origem}` (`:227-242`).
- `marca.cor` e `cor_2` em `#RRGGBB` (`cor_2` pode ser `null`); contraste de `cor` sobre `#16181A` ≥ 3,0:1
  (`:82,86-87,231-238`); `logo` é nome de arquivo em `ativos/` (`:83,239-240`); `origem` ∈
  `tabela|site|expx` (`:241-242`).
- `slides`: de 6 a 10; o primeiro `titulo`, o último `cta` (`:243-250`).
- Tipos e teto de palavras por campo (`:88-94`) e de itens (`:163-212`):

| tipo | campos (palavras) | itens |
|---|---|---|
| `titulo` | kicker 4, titulo 10, subtitulo 20 | |
| `declaracao` | texto 20, autor 4 (opcional) | |
| `grade` | titulo 8 | 3-6 × {titulo 5, texto 14} |
| `comparacao` | titulo 8 | esquerda/direita {titulo 4, itens 1-5 × 8} |
| `etapas` | titulo 8 | 3-5 × {titulo 4, texto 10} |
| `estatisticas` | titulo 8 | numeros 1-4 × {valor número, sufixo texto, rotulo 4, fonte obrigatória} |
| `fluxo` | titulo 8 | nos 3-6 × {titulo 4, texto 8 opcional} |
| `screenshot` | titulo 6, legenda 12 | imagem em `ativos/` ou `null` |
| `cta` | titulo 10, texto 16 | `url` fixa, imagem em `ativos/` ou `null` |

- Proibido em qualquer texto: travessão `—`, meia-risca `–`, `\n` (`:84-85,126-129`). `<b>palavra</b>` só em
  `titulo.titulo` e `declaracao.texto` (`:95,130-131`); `<b>` não conta como palavra (`:100-101`).
- `fonte` de número não pode citar métrica do próprio canal: regex
  `diagn[oó]stico|leitura\.json|inscritos|views|youtube analytics|nosso canal` (`:96-97,203-206`; D-53 em
  `youtube-squad/docs/apresentacoes-e-pautas/00-DECISOES.md`).
- `cta.url` precisa ser literalmente `expxplay.com.br` (`apresentacao.py:209-212`).
- Espelho TypeScript do schema em `youtube-squad/apresentacoes/motion/src/deck.ts:1-40`.

### Identidade da ferramenta: `marca <url> [--deck]` (`apresentacao.py:528-659`)

Ordem: tabela curada `comuns/marcas.json` por host (`:605-615`) → sinais do HTML (`theme-color`, hex
saturado mais frequente com saturação ≥ 0,35 e luminância entre 0,06 e 0,9, título até o separador, ícone
`rel=icon` não-apple) (`:567-602`) → identidade EXPX (`:528`). Cor do site é clareada com branco em passos
de 10% (até 12) até passar 3:1 (`:549-558`). Com `--deck`, baixa o ícone (png/jpg/webp/svg) para
`ativos/logo.png|svg` (`:646-658`). Nunca lança por rede: vira `avisos` (`:630-634,657-658`). HTML
limitado a 2 000 000 bytes, User-Agent de navegador (Cloudflare devolve vazio sem ele) (`:529-539`).
`marcas.json` tem 11 entradas "não oficial", medidas em 2026-09-23; `cor: null` usa EXPX
(`youtube-squad/apresentacoes/comuns/marcas.json:2-14`).

### Conteúdo: `ler <url>` e `screenshot`

- `ler`: título, descrição, h1-h3, p, li sem script/style/nav/footer/header; corta em 20 000 caracteres;
  recusa YouTube (`apresentacao.py:669-697`).
- `screenshot`: roda `browser-harness` por subprocesso com um script que abre a aba, espera o load (ou 6 s),
  força 1920×1080, espera 3 s e captura PNG (`:715-749`); timeout 60 s (`:714`). O site do CTA é cacheado
  uma vez em `comuns/expxplay.png` e copiado para `ativos/`; `--atualizar` recaptura (`:752-781`). Falha
  vira aviso, nunca erro (`:735-749`). Executável via `APRESENTACAO_BH` ou PATH (`:731-732`).

### Score, estado e fila (`apresentacao.py:281-415`)

- Corte `CORTE = 80`; motivo ≥ 40 caracteres; score inteiro 0-100 (`:283-300`).
- `validar`: ≥ 80 → `aberta`, < 80 → `descartada`; grava histórico em `validacoes` (`:303-313`).
- `status`: só `aberta` ↔ `gravada`; descartada não reabre por status (`:316-327`; D-44).
- `pauta_id = sha1(título normalizado sem acento + "|" + origem)[:12]` (`:330-335`; D-45); fila só com
  score ≥ 80, mesma pauta substitui (`:347-359`).
- Rubrica do agente `validador`: 4 eixos de 25 (afinidade, gancho, tração, atualidade), motivo eixo a eixo
  com números de `referencia` (`youtube-squad/.claude/agents/validador.md:31-42`). `referencia`: top 10 por
  views e top 5 por inscritos/mil views com ≥ 100 views, do `diagnostico.json` mais recente
  (`apresentacao.py:423-471`); sem diagnóstico sai com erro (`:434-439`).

### Render (`apresentacao.py:846-936`; `youtube-squad/apresentacoes/motion/scripts/render.mjs`)

- Pré-condições, nesta ordem: estado existe (`:891-892`), não está descartado (`:893-894`), deck válido
  (`:895-897`), `render.mjs` existe (`:898-899`), node ≥ 18 achado por `APRESENTACAO_NODE` → PATH → versão
  mais nova do nvm (`:811-839`), `npm install` só se faltar `node_modules` (`:875-883`; npm por
  `APRESENTACAO_NPM`, `:842-843`).
- Imagem citada e ausente em `ativos/` (inclusive `marca.logo`) é trocada por `null` numa cópia
  `saida/deck-render.json`, com aviso; o `deck.json` não muda (`:856-872,906-908`; D-48).
- `node scripts/render.mjs <deck-render.json> <saida> <ativos>` (`:912`): `ensureBrowser()`, **um**
  `bundle()` com `publicDir = ativos/`, depois por slide `selectComposition` (`slide-N`), `renderMedia`
  h264 CRF 18 e `renderStill` PNG do último frame; imprime `slide i/N ok` (`render.mjs:30-60`).
- `Root.tsx` registra uma composição por slide a partir de `getInputProps()`; sem props usa
  `DECK_EXEMPLO` (`youtube-squad/apresentacoes/motion/src/Root.tsx:32-58`). `aplicarMarca` roda no Root,
  em todo worker (`Root.tsx:42`; `theme.ts:61-73`).
- Cada slide: 240 frames, 30 fps, 1920×1080 (`motion/src/deck.ts:42-45`; D-09: entrada nos 3 s iniciais,
  depois respiro, sem som e sem animação de saída).
- Config: `setVideoImageFormat("jpeg")`, `setOverwriteOutput(true)` (`motion/remotion.config.ts:3-4`).

### Cenas (`youtube-squad/apresentacoes/motion/src/scenes/`)

Nove cenas mapeadas por tipo (`Root.tsx:20-30`): `Titulo`, `Declaracao`, `Grade`, `Comparacao`, `Etapas`,
`Estatisticas`, `Fluxo`, `Screenshot`, `Cta`. Moldura comum (`scenes/Slide.tsx:54-85`): pilha
BgMesh → conteúdo → Finish (grade, grão, vinheta), cabeçalho `NN / TOTAL` + ícone/ponto + nome da marca
(`:22-52`), respiro vertical de 3 px em 5 s (`:76`; `components/Timeline.ts:29-31`). Medidas derivadas de
`useVideoConfig().width` (`pad = 5%`, `u = width/1920`) (`Slide.tsx:16-20`). Heurísticas por cena:
`Estatisticas` com fonte 200/150/110 conforme 1/2/3+ números e "fonte:" sob cada número
(`scenes/Estatisticas.tsx:12,27`); `Fluxo` em 1 linha até 4 nós, 2 linhas acima, nós entram a cada 9 frames
a partir do 24, seta 5 frames depois, brilho percorre nós a cada 1,2 s (`scenes/Fluxo.tsx:11-13,18-23,60`);
`Etapas` horizontal com 4+ itens (`scenes/Etapas.tsx:14`); `Grade` em até 4 colunas, senão 3
(`scenes/Grade.tsx:10`); `Screenshot` e `Cta` sem imagem desenham moldura com texto, nunca `<Img>`
inexistente (`scenes/Screenshot.tsx:37-43`; `scenes/Cta.tsx:66-75`). `WordReveal`: palavra a palavra a
cada 3 frames, `<b>` na cor de destaque, `fitText` com `validateFontIsLoaded: true` e o `fontSize` como
teto (`components/WordReveal.tsx:1-4,41-49`).

### Tema (`youtube-squad/apresentacoes/motion/src/theme.ts`, `fonts.ts`)

Paleta base fixa (`bg #16181A`, `surface #232729`, `text #F2F5F3`, `textSoft #A8B0AC`) com destaque EXPX
`#22C55E`/`#4ADE80`/`#86EFAC` (`theme.ts:7,31-44`); `aplicarMarca` troca só o destaque, `accent2` =
clarear 18%, `accent3` = clarear 45%, `glow` = rgba 0,35 (`:62-73`). Curvas `out`, `inOut`, `in` e springs
`snappy`, `smooth`, `bouncy` (`:49-58`). Fontes Anton (display), Chakra Petch (corpo), JetBrains Mono,
via `@remotion/google-fonts`; a tipografia não muda com a marca (`fonts.ts:1-16`; D-12). Origem declarada:
"portados do template EXPX" do ExpxOS (`theme.ts:1-3`; `components/Timeline.ts:1`; D-07).

### Palco (`youtube-squad/apresentacoes/palco.html`; montado por `apresentacao.py:794-806`)

Um `<video>` por slide (`slide-NN.mp4`, `poster=slide-NN.png`, `preload auto` só nos 2 primeiros,
`muted playsinline`, `aria-label`) (`apresentacao.py:799-802`). Placeholders `__TITULO__`, `__MARCA__`,
`__TOTAL__`, `__COR__`, `__VIDEOS__` (`:804-806`). Teclado: → espaço PageDown Enter avançam; ← PageUp
Backspace voltam; Home/End; F tela cheia no container; R repete (`palco.html:73-82`). Clique na metade
esquerda/direita (`:83-89`); HUD some após 3 s sem mouse (`:90-96`); `#N` na URL abre no slide N
(`:65,97-98`); pré-carrega o próximo (`:62`); vídeo sem `loop`, segura o último frame (D-06). Abre por
`file://` (`apresentacao.py:939-945`).

## Contrato de saída

- `saida/slide-NN.mp4` (H.264 CRF 18, 1920×1080, 8 s) e `saida/slide-NN.png` (último frame) por slide;
  `saida/capa.png` = cópia do slide 1; `saida/palco.html`; `saida/deck-render.json`
  (`apresentacao.py:907,922-928`). Se faltar algum mp4/png depois de o node sair 0, o render é marcado
  falho (`:922-925`).
- `estado.json`: `{slug, score, motivo, validado_em, validado_por, status, gravado_em, validacoes[],
  render{em, slides, ok, avisos, segundos, erro}}` (`apresentacao.py:308-312,921,929-930`); exemplo real
  em `youtube-squad/apresentacoes/decks/2026-09-23-claude-code-ou-opencode-na-software-house/estado.json`.
- `fila.json`: `{"pautas": [{pauta_id, titulo, angulo, origem, score, motivo, registrada_em}]}` por score
  decrescente (`apresentacao.py:356-358`).
- `lista`: `{abertas, gravadas, descartadas, sem_score, fila}` (`:371-384`), consumida pela aba
  Apresentações do painel (`youtube-squad/painel.py:494,509`).
- No contrato alvo: `slides[]` com `kind` = tipo do deck e um arquivo `papel: final` que é o HTML
  navegável; PNG por slide `papel: slide`; MP4 extra `papel: final` (`CONTRATO-peca.md:191-193`). O
  `estado.json` do deck corresponde a `status`/`producao` da peça; `score` e `validacoes` não têm campo no
  contrato.

## Limites e cotas

- 6 a 10 slides, ideal 8 (`apresentacao.py:244`; `.claude/agents/apresentador.md:47`); 240 frames por
  slide (`motion/src/deck.ts:45`).
- Timeouts: `npm install` 600 s, render 1800 s (`apresentacao.py:848-849`); screenshot 60 s (`:714`);
  Bash do agente 600 000 ms (`.claude/skills/apresentacao/SKILL.md:39`).
- Tempo medido: ~20 s por slide + 15 s de bundle; 162 s para 8 slides; primeira vez +~30 s para instalar
  e baixar o Chrome (`.claude/skills/apresentacao/SKILL.md:39-41`). Registros reais: 163,1 s / 8 slides,
  160,4 s / 9, 151,0 s / 9 (`estado.json` dos decks de 2026-09-23 e 2026-09-24).
- Download do Chrome Headless Shell ~90 MB (D-31/D-51 em `00-DECISOES.md`).
- HTML lido até 2 MB; texto de `ler` até 20 000 caracteres; ícone até 5 MB (`apresentacao.py:530,546,669`).
- Licença do Remotion: sem `licenseKey`; com 4 ou mais pessoas operando o código é Company License
  (mínimo US$ 100/mês) (`youtube-squad/apresentacoes/README.md:26`; D-43;
  `youtube-squad/.claude/rules/apresentacoes.md:19-21`).

## Erros conhecidos e tratamento

- Deck inválido: lista todas as violações de uma vez, saída 1 (`apresentacao.py:274-278`).
- Render sem score, descartado ou inválido: recusado antes do node (`:891-897`).
- Node < 18 ou ausente: `Erro` com instrução (nvm ou `APRESENTACAO_NODE`) (`:833-839`).
- `npm install` falho: últimos 300 caracteres do erro (`:880-882`).
- Node sai ≠ 0: última linha do stderr vai para `estado.render.erro` e o estado é gravado antes de lançar
  (`:914,929-934`); timeout e `OSError` idem (`:916-919`).
- Imagem ausente derrubaria o render (`<Img>` que falha cancela): trocada por `null` com aviso (D-48).
- Fonte não carregada vira serifada silenciosa no Chromium: `validateFontIsLoaded` transforma em erro
  (`components/WordReveal.tsx:3-4`; `fonts.ts:2`).
- Rede no `marca`/`screenshot`: vira aviso e cai na EXPX ou sai sem imagem (`apresentacao.py:630-634,735-749`).
- Chrome pede "Allow" no browser-harness: aparece como timeout "(Chrome pediu Allow?)" (`:743-744`).
- Achados abertos da auditoria (`youtube-squad/docs/apresentacoes-e-pautas/00-AUDITORIA.md`, tabela
  "Achados novos"): escopo do agente cobrindo `estado.json` (corrigido depois para
  `apresentacoes/decks/*/deck.json`, `youtube-squad/.claude/hooks/regras_agentes.py:22`), caminho de
  imagem `null` nunca renderizado de verdade em teste, métrica `null` sem teste.
- Pastas órfãs: `apresentacoes/decks/placeholder/ativos/logo.png` e
  `apresentacoes/decks/2026-09-24-abandonei-o-claude-code-e-voltei-o-que-o-opus-5-5-mudou/ativos/logo.png`
  sem `deck.json`; `marca --deck` cria `ativos/` sem conferir se o deck existe (`apresentacao.py:646-656`).
  `lista` as ignora (`:374-376`). Como surgiram: NÃO DOCUMENTADO.

### Testes existentes (o que já está coberto)

- Framework: pytest (`youtube-squad/pytest.ini:1-4`, `testpaths = tests`, `pythonpath = . editorial/analises`,
  `-p no:cacheprovider`); comando: `.venv/bin/python -m pytest` (instalação em
  `youtube-squad/requirements.txt:1`). Rodado nesta ingestão: `tests/test_apresentacao.py`,
  `tests/test_motion.py`, `tests/test_comum.py` → 72 passed em 5,76 s.
- Guarda de rede no nível do socket para todo teste (`youtube-squad/tests/conftest.py:1-46`).
- Falsos por subprocesso: `tests/node_falso.py` (mesma linha de comando do `render.mjs`, `--version` v20,
  falha por `NODE_FALSO_FALHA`) e `tests/npm_falso.py` (`:1-35`, `:1-19`); injetados por
  `APRESENTACAO_NODE`/`APRESENTACAO_NPM` (fixture `motion`, `tests/test_apresentacao.py:507-521`).
- `DECK_OK` canônico, `diagnostico_mini()` e PNG válido gerado com a stdlib (`tests/decks.py:30-116`).
- Violação a violação do schema parametrizada (`tests/test_apresentacao.py:163-180`); JS do palco
  checado com `node --check` (`:494-503`).
- `test_motion.py`: todos os pacotes Remotion na mesma versão `4.0.522` sem `@remotion/player`, react
  18.3.1 (`:14,21-29`); sem `licenseKey` (`:32-34`); `tsc --noEmit` só com `node_modules` (`:44-48`);
  nove cenas mapeadas, sem `useExit`, `Cta` usa `EXPX_ACCENT` (`:66-82`); um `bundle(` no `render.mjs`
  (`:85-91`).

## Riscos para a nossa implementação

Acoplamentos de marca que precisam virar dado da Alma/config:

| Acoplamento | Onde |
|---|---|
| CTA fixo `expxplay.com.br`, validado como regra | `apresentacao.py:209-212,712-713`; `motion/src/deck.ts:53`; `tests/decks.py:23,60` |
| Cena `Cta` sempre verde EXPX, rótulo "ExpxPlay", logotipo "Expx**Play**", "Próximo passo" | `motion/src/scenes/Cta.tsx:1-3,19-24,71` |
| Destaque EXPX `#22C55E`/`#4ADE80` como padrão e fallback | `apresentacao.py:528`; `theme.ts:7,40-43`; `palco.html` via `apresentacao.py:803-806` |
| Paleta de fundo `#16181A` e contraste medido contra ela | `apresentacao.py:86-87`; `theme.ts:32` |
| Fontes Anton/Chakra Petch/JetBrains Mono | `motion/src/fonts.ts:3-16`; `palco.html:8` |
| `marcas.json` com as ferramentas do território e `expxplay` | `apresentacoes/comuns/marcas.json:4-14` |
| `origem: "expx"` como enum | `apresentacao.py:241-242`; `motion/src/deck.ts:8` |
| Autor "Thulio", slide "para o Thulio apresentar" | `tests/decks.py:37`; `.claude/skills/apresentacao/SKILL.md:5`; `.claude/agents/apresentador.md:24` |
| Regra "métrica do nosso canal não entra em slide" com regex em português de YouTube | `apresentacao.py:96-97` |
| Score acoplado ao YouTube (`diagnostico.json`, views, inscritos por mil) | `apresentacao.py:434-471`; `.claude/agents/validador.md:23-42` |
| `SITE_DO_CTA` e cache `comuns/expxplay.png` | `apresentacao.py:712-713,764-774` |

O que derruba a qualidade se extraído ingenuamente:

1. **Limites de palavras e a trava de estouro** (`TIPOS`, `fitText` como teto, `validateFontIsLoaded`)
   são o que garante que o texto cabe no quadro com a fonte certa. Trocar a fonte por marca sem remedir os
   limites quebra o layout (D-12 cita `tipos.md:362-374` do template).
2. **Contraste ≥ 3:1 e o clarear em 10%**: sem eles, cor de marca escura some no fundo; `BgMesh` concatena
   alfa em hex e quebra em silêncio com `rgb()` ou hex curto (D-47).
3. **Um bundle para N slides** e `publicDir = ativos/` (D-10): renderizar por CLI rebundla a cada slide.
4. **Imagem ausente → null** e moldura sem `<Img>`: sem isso um screenshot que falhou cancela o render
   inteiro (D-48).
5. **Frame final estático, sem loop, sem som** (D-06, D-09): é o que permite falar ao vivo por cima; o
   palco depende disso.
6. **Score antes do render** e máquina de estados (D-22, D-44) economizam minutos de render; o critério em
   si é do canal YouTube e vira capacidade/pack, não núcleo.
7. **Schema duplicado** em Python (`apresentacao.py`), TypeScript (`deck.ts`) e docstring (`tests/decks.py`)
   sem gerador comum: fácil divergir.
8. **Estado global mutável** no tema (`Object.assign(theme.colors, ...)` em `theme.ts:66`) funciona porque
   o Root roda em cada worker; outro uso (dois decks no mesmo bundle) mistura cores.
9. **Dependência de `browser-harness`** para screenshot, fora do catálogo (`capturar_pagina` prevê
   Playwright, `CONTRATO-capacidades.md:44`).
10. **Remotion 4.0.522 fixo** aqui e `^4.0.527` em cursos-ia; TypeScript 5.6.3 aqui e 7.0.2 lá. O teste
    `test_motion.py:14,26` trava a versão.
11. **O palco não é "PPT"**: não tem notas, não tem edição, e é HTML com MP4 ao lado (não é arquivo
    único); `saida/` inteira precisa ir junto.

## Fonte

- `youtube-squad/apresentacao.py`, `youtube-squad/comum.py`, `youtube-squad/painel.py` (rotas das apresentações)
- `youtube-squad/apresentacoes/{README.md, palco.html, fila.json, comuns/marcas.json}`
- `youtube-squad/apresentacoes/decks/*/{deck.json, estado.json, ativos/}`
- `youtube-squad/apresentacoes/motion/{package.json, remotion.config.ts, tsconfig.json, scripts/render.mjs}`
- `youtube-squad/apresentacoes/motion/src/{Root.tsx, index.ts, deck.ts, theme.ts, fonts.ts}`, `src/scenes/*.tsx`, `src/components/{WordReveal.tsx, Timeline.ts, Layers.tsx}`
- `youtube-squad/tests/{decks.py, conftest.py, node_falso.py, npm_falso.py, test_apresentacao.py, test_motion.py, test_comum.py}`, `youtube-squad/pytest.ini`, `youtube-squad/requirements.txt`
- `youtube-squad/.claude/skills/apresentacao/SKILL.md`, `.claude/agents/{apresentador.md, validador.md}`, `.claude/rules/apresentacoes.md`, `.claude/commands/apresentacao.md`, `.claude/hooks/regras_agentes.py`
- `youtube-squad/docs/apresentacoes-e-pautas/{00-DECISOES.md, 00-AUDITORIA.md, 00-BLOQUEIOS.md}`
- `git log` de youtube-squad; versões em `apresentacoes/motion/node_modules/*/package.json`
