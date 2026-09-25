# Pipeline de aula (cursos-ia)

Área: produção do tipo `aula` (MP4 16:9 + MP4 9:16 + SRT) a partir de um roteiro com marcadores,
narração clonada, avatar em PiP, legenda queimada e, opcionalmente, gravação de tela. Origem: os 12
episódios de `cursos-ia/` (repositório com um único commit, `7ce0680 Initial commit`; não há histórico
para datar a evolução, a ordem abaixo é a dos nomes e dos READMEs). Gravação de tela e `editar_demo.py`
estão em `gravacao-de-tela.md`; o avatar em `avatar-heygen-processo-atual.md`.

## Contrato de entrada

### Ordem do pipeline (versão mais evoluída: `radar-ia-07` a `radar-ia-09`)

`roteiro.txt` → `gerar_voz.py` → (`editar_demo.py`, se houver tela) → avatar HeyGen → whisper →
`gerar_legendas.py` → `npm run render` e `npm run render:9x16`
(`cursos-ia/radar-ia-07-jev-codigo/README.md:53-56`; ordem sem tela em `cursos-ia/radar-ia-01-jev/README.md:9-15`).
Nos episódios com tela, a gravação vem **antes** do roteiro final: o roteiro é escrito em cima do que
aconteceu na tela, com os números reais (`cursos-ia/radar-ia-06-jev-openrouter/plano-gravacao.md:6-10`,
`cursos-ia/radar-ia-06-jev-openrouter/roteiro-rascunho.md:3-5`).

### Qual versão de cada script é a mais evoluída

| Script | Versão mais evoluída | Evidência |
|---|---|---|
| `gerar_voz.py` | `radar-ia-06` = `07` = `08` = `09` (md5 idêntico) | única diferença para `aula-skills-2`…`radar-ia-05` é `"speed": 0.94` (`cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:41`); `aula-skills` é a primeira versão, sem `speed` |
| `gerar_legendas.py` | `radar-ia-01` a `09` (lógica idêntica; muda só o nome do SRT) | `aula-skills-2` tem `MAX_CHARS = 40` e não tem o corte equilibrado em 2 linhas (diff contra `cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:14,54-60`) |
| `marca.tsx` | `radar-ia-02` a `09` (md5 idêntico) | `cursos-ia/radar-ia-02-jev-fluxo/README.md:8-9` |
| Composição com tela | `cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx` | tem `crop9` por segmento (`:94`), o que 06-08 não têm |
| Composição só com cenas | `cursos-ia/radar-ia-05-jev-limites/src/AulaJev.tsx` (01-05 iguais na estrutura) | `CENAS` vindo de `Cenas.tsx` |
| Compilação | `cursos-ia/radar-ia-jev-completo/` | único |

### `roteiro.txt`

- Texto corrido com marcadores `[[nome]]` antes do trecho; `nome` casa `\w+`
  (`cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:24`). Convenção observada: `s1`, `s2`… para
  cenas e subcues `s2_math`, `s5_in`, `s7_cta` para eventos dentro de uma cena
  (`cursos-ia/radar-ia-05-jev-limites/src/cues.json`; `cursos-ia/aula-skills-2/src/AulaSkills2.tsx:128`).
- Heurística de escrita para TTS (observada, não escrita como regra): números por extenso
  ("noventa por cento") e extensões faladas ("tickets ponto json", "ponto env")
  (`cursos-ia/radar-ia-09-jev-calibracao/roteiro.txt:1-5`). A legenda usa esse mesmo texto (ver saída).

### `gerar_voz.py` (narrar)

- Uso: `python3 gerar_voz.py <voice_id>` (`cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:3`). O
  `voice_id` vem por argumento; o valor usado está só no README: `<voice_id do dono na origem>`
  (`cursos-ia/radar-ia-01-jev/README.md:10`).
- Chave: lê `../.env` linha a linha e pega `elevenlabs_apikey` (`gerar_voz.py:14-19`). Único nome no
  `.env` de `cursos-ia` (só o nome foi lido).
- Remove os marcadores e guarda o offset em caracteres de cada um no texto limpo (`gerar_voz.py:23-28`).
- `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128`
  (`gerar_voz.py:31`), `model_id: eleven_multilingual_v2` (`:35`), `stability 0.5`,
  `similarity_boost 0.85`, `style 0.15`, `use_speaker_boost true`, `speed 0.94` (`:37-41`), timeout 300 s
  (`:47`). O texto vai numa chamada só (roteiro de ~5 min em `radar-ia-09`: `duration` 296,205 s,
  `cursos-ia/radar-ia-09-jev-calibracao/src/cues.json:2`). Detalhes da API: `api-elevenlabs.md` e
  `narrar-elevenlabs.md` desta base.

### Whisper (transcrever)

`whisper public/narracao.mp3 --model medium --language pt --word_timestamps True --output_format json --output_dir raw/whisper`
(`cursos-ia/radar-ia-01-jev/README.md:11`). Roda em CPU com FP32 (aviso em
`cursos-ia/radar-ia-09-jev-calibracao/raw/whisper.log:1-2`). Instalado: `openai-whisper 20250625`
(Python 3.11, verificado com `pip show`). Ver `transcrever-whisper.md` desta base.

### `gerar_legendas.py` (legendar)

Entrada: `roteiro.txt` e `raw/whisper/narracao.json` (`gerar_legendas.py:4`). Algoritmo
(`cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py`):

1. Palavras do roteiro sem marcadores (`:17`) contra palavras do whisper (`:19`), ambas normalizadas:
   minúscula, NFKD, só `[a-z0-9]` (`:22-24`).
2. `difflib.SequenceMatcher(autojunk=False)` (`:30`). `equal`: tempo do whisper palavra a palavra
   (`:32-34`). `replace`: distribui o trecho do whisper proporcionalmente pelas palavras do roteiro
   (`:35-40`). Palavra sem par: interpola entre vizinhas; sem vizinha à direita, `prev + 0.3` s (`:43-47`).
3. Frases terminam em `.`, `:`, `?`, `!` (`:107`). Frase terminada em `:` ou com até 3 palavras junta
   com a seguinte (`:116`).
4. `wrap`: `MAX_CHARS = 42` por linha, `MAX_LINES = 2` (`:14-15`); acima de 42 escolhe o corte em
   duas linhas que minimiza a linha mais longa (`:56-60`), senão quebra guloso (`:61-70`).
5. `split_balanced`: frase que não cabe em 2 linhas vira `k = ceil(linhas/2)` blocos (`:80`), com custo
   `|comprimento - alvo| + 20 × órfãs - 6 se o corte cai depois de vírgula`; linha órfã = menos de
   18 caracteres (`:93-94`).
6. Tempo final: `end = min(max(end + 0.25, start + 1.0), próximo_start - 0.05)`; a última usa
   `end + 1.5` como "próximo" (`:127-129`).

### Remotion (renderizar_motion)

- Uma `Composition` por formato no `Root.tsx`, ambas com a mesma duração
  `ceil(cues.duration × FPS)`, 1920×1080 e 1080×1920, FPS 30
  (`cursos-ia/radar-ia-09-jev-calibracao/src/Root.tsx:6-11`; `src/marca.tsx:8`).
- `cue(nome) = round(cues[nome] × FPS)` e `rel(nome, cena)` relativo ao início da cena
  (`src/marca.tsx:28-30`). As cenas rodam em `<Sequence from={cue(s)}>`
  (`cursos-ia/radar-ia-05-jev-limites/src/AulaJev.tsx`, bloco `CENAS.map`).
- O mesmo componente atende os dois formatos: `Vertical` (React context) empilha colunas no 9:16
  (`src/marca.tsx:32-34`, `Row` em `:109-112`).
- Tipo `Layout` com `vertical, pad, demo, pip, card?, legenda, legendaFont, header, progress`
  (`cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:33-43`).

| Layout | 16:9 (`L16`) | 9:16 (`L9`) |
|---|---|---|
| pad das cenas | `120px 440px 170px 110px` (`Aula.tsx:48`) | `168px 56px 760px 56px` (`Aula.tsx:61`) |
| tela (com barra de 34 px) | left 48, top 96+34, 1392×783 (`:49`, `DEMO_BAR :15`) | left 56, top 168+34, 968×962 (`:62`) |
| PiP do avatar | left 1484, top 500, 380×440 (`:50`) | centrado, top 1318, 272×340 (`:63`) |
| cartão do passo | left 1484, top 130, w 380 (`:51`) | não existe |
| legenda | left 48, w 1392, bottom 44, fonte 28 (`:52-53`) | left 56, w 968, top 1198, fonte 32 (`:64-65`) |
| cabeçalho / progresso | top 38 / progresso na coluna direita, bottom 60 (`:54-55`) | top 52 / bottom 220 (`:66-67`) |

- Safe area do 9:16: `SAFE = { top: 168, right: 56, bottom: 280, left: 56 }`, "faixas seguras p/ UI
  do Reels" (`cursos-ia/aula-skills/src/Aula9x16.tsx:37`, repetido em
  `cursos-ia/aula-skills-2/src/AulaSkills2_9x16.tsx:32` e citado em
  `cursos-ia/radar-ia-05-jev-limites/src/AulaJev.tsx`, comentário do `L9`). Em `L9` a área das cenas
  termina 760 px acima da base para caber legenda (top 1198) e PiP (1318-1658)
  (`Aula.tsx:61-64`).
- Na composição sem tela (01-05), `L16.pip` = 300×382 no canto inferior direito
  (`1920-58-300`, `1080-72-382`) e legenda com largura `1920-62-420`
  (`cursos-ia/radar-ia-jev-completo/src/JevCompleto.tsx:66-74`, igual em `AulaJev.tsx` dos episódios).
- Camadas e ordem (`Aula.tsx:255-270`): fundo + retícula + cantos, `<Audio narracao.mp3>`, intro até
  `s2`, tela de `s2` a `s12`, outro a partir de `s12`, cartão, PiP até `duration - 1.5 s`, legenda,
  cabeçalho com barra de progresso `frame / durationInFrames`.
- "Câmera" do 9:16: `cameraX(t)` interpola o centro horizontal entre pontos de `demo.json.camera` com
  transição de ±0,3 s (`Aula.tsx:78-86`); o 9:16 recorta dentro de `seg.crop9`, o 16:9 escala `seg.crop`
  para a largura da tela (`Aula.tsx:94-103`). Selo "▶▶ N× acelerado" quando `rate >= 1.5`
  (`Aula.tsx:108`).
- Render duplo: `npm run render` e `npm run render:9x16`, que são `remotion render src/index.ts <id> out/<ep>.mp4`
  (`cursos-ia/radar-ia-09-jev-calibracao/package.json:6-7`). Sem `remotion.config.ts` em cursos-ia.

### Compilação de episódios (`radar-ia-jev-completo`)

- `src/partes.json`: `{ep, ini, fim|null, nome}` por parte; `fim: null` = até o fim
  (`cursos-ia/radar-ia-jev-completo/src/partes.json:2-6`). Cortes escolhidos no meio das pausas,
  medidos com `silencedetect` (`cursos-ia/radar-ia-jev-completo/README.md:18`); corta ganchos "no
  próximo episódio" e "no episódio anterior" (`README.md:10-16`).
- Nada é regravado: cenas, narração, avatar e legendas de cada episódio copiados para `src/partes/epN/`
  e `public/epN/` (`README.md:6-7`).
- `PARTES` acumula `from`, `trim = round(ini × FPS)`, `frames = round((fim-ini) × FPS)`
  (`src/JevCompleto.tsx:34-42`); cada parte é `<Sequence from={from}><Sequence from={-trim}>`
  (`:166-183`); avatar troca por dentro da mesma moldura (`:88-111`); legendas reposicionadas na
  linha do tempo longa (`:46-50`); marcas de início de parte na barra de progresso (`:158-160`).
- `gerar_srt.py` repete a mesma regra de corte em Python para o SRT (`cursos-ia/radar-ia-jev-completo/gerar_srt.py:12-19`).
- Render com `--timeout=120000` (`cursos-ia/radar-ia-jev-completo/package.json:6-7`).

### Estrutura pedagógica

- Curso "Claude Code para Iniciantes": aulas de no máximo 3 min, alvo 2min20-3min
  (`cursos-ia/ementa-claude-code-iniciantes.md:4,25`); 22 aulas em 6 módulos + bônus
  (`ementa-claude-code-iniciantes.md:29-853`).
- Oito blocos fixos por aula, sempre na mesma ordem (`ementa-claude-code-iniciantes.md:14-23`):
  1 "O que você vai aprender" (uma frase), 2 "Pense assim" (analogia do dia a dia), 3 "O problema",
  4 "A solução", 5 "Vamos fazer juntos" (passo a passo na tela), 6 "Cuidado com isso" (erro mais
  comum), 7 "Sua vez" (tarefa), 8 "O que vem depois" (gancho).
- Série Radar IA: episódios de até 1min30 (`cursos-ia/radar-ia-01-jev/README.md:3-4`), depois 3 a 5
  min com tela (`cursos-ia/radar-ia-06-jev-openrouter/plano-gravacao.md:3`). Os episódios gravados
  não seguem os 8 blocos: seguem abertura animada → passos numerados (`PASSOS`,
  `cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:20-31`) → "Resumindo" (`:235-253`) → gancho
  do próximo episódio. `aula-skills` usa 6 cenas (problema, o que é, onde mora, como é ativada,
  exemplo, resumo; `cursos-ia/aula-skills/src/Aula9x16.tsx:43-50`).
- Checagem de fonte: cada README de episódio lista as URLs checadas com data e explica números
  omitidos por divergirem entre fontes (`cursos-ia/radar-ia-01-jev/README.md:17-28`).

## Contrato de saída

| Arquivo | Produzido por | Formato |
|---|---|---|
| `public/narracao.mp3` | `gerar_voz.py:49-52` | MP3 44,1 kHz 128 kbps (ffprobe) |
| `src/cues.json` | `gerar_voz.py:64-67` | `{"duration": fim_da_fala + 1.5, "cues": {nome: segundos}}`, 3 casas; cue = início do primeiro caractere não-espaço após o marcador (`:58-61`) |
| `raw/whisper/narracao.json` | whisper | JSON com `segments[].words[] {word, start, end}` (lido em `gerar_legendas.py:19`) |
| `src/legendas.json` | `gerar_legendas.py:131` | `[{start, end, lines: [≤2 strings ≤42]}]` |
| `out/<ep>.srt` | `gerar_legendas.py:139-142` | SRT com `HH:MM:SS,mmm`; **texto do roteiro**, não do whisper |
| `public/avatar.mp4` | HeyGen (manual) | ver `avatar-heygen-processo-atual.md` |
| `public/demo.mp4`, `src/demo.json` | `editar_demo.py` | ver `gravacao-de-tela.md` |
| `out/<ep>.mp4`, `out/<ep>-9x16.mp4` | `npm run render`, `render:9x16` | 1920×1080 e 1080×1920, 30 fps |
| `out/radar-ia-jev-completo.srt` | `gerar_srt.py:28-30` | SRT da compilação |

No contrato alvo (`ExpxMedia/docs/contrato/CONTRATO-peca.md:189-198`) isso vira `arquivos[]` com papéis
`audio`, `alinhamento`, `avatar`, `tela`, `srt` e um `final` por formato; `slides: []`.

## Limites e cotas

- Duração: `duration = último end do alinhamento + 1,5 s` (`gerar_voz.py:65`); o PiP some 15 frames antes
  de `duration - 1,5 s` (`Aula.tsx:10,135-136`).
- ElevenLabs numa chamada só com timeout 300 s (`gerar_voz.py:47`); roteiro mais longo já testado:
  296 s de áudio (`cursos-ia/radar-ia-09-jev-calibracao/src/cues.json:2`). Limite de caracteres por
  chamada: NÃO DOCUMENTADO na fonte (ver `api-elevenlabs.md`).
- Legenda: 42 caracteres × 2 linhas, mínimo 1,0 s em tela, folga de 0,05 s para a próxima
  (`gerar_legendas.py:14-15,129`).
- Compilação: render com `--timeout=120000` (ms), único episódio que precisou aumentar o timeout padrão
  do Remotion (`cursos-ia/radar-ia-jev-completo/package.json:6-7`); o motivo: NÃO DOCUMENTADO.
- Tempo de render das aulas: NÃO DOCUMENTADO.
- Custo de ElevenLabs por aula: NÃO DOCUMENTADO.

## Erros conhecidos e tratamento

- `gerar_voz.py` não trata erro nenhum: chave ausente vira `KeyError` (`:19`), HTTP vira exceção de
  `urllib` (`:47`); não há retry.
- Whisper erra nomes próprios e números ("Jeve" por "Jev", "90%" por "noventa por cento":
  `cursos-ia/radar-ia-09-jev-calibracao/raw/whisper.log:3-5`). Tratamento: a legenda usa o texto do
  roteiro e só o **tempo** do whisper (`gerar_legendas.py:1,50`).
- Palavra do roteiro sem par no whisper: interpolada entre vizinhas (`gerar_legendas.py:42-47`).
- Legendas em 2 linhas com palavra órfã: corrigido na versão 01+ pelo corte equilibrado
  (`gerar_legendas.py:54-60`); `aula-skills-2` ainda quebra guloso com 40 caracteres.
- Regra de ordem: "Rodar de novo sempre que o roteiro ou a narração mudarem, antes do render"
  (`cursos-ia/aula-skills-2/plano-gravacao.md:72-75`). Nada no código impede renderizar com
  `legendas.json`, `demo.json` ou `avatar.mp4` desatualizados em relação ao `cues.json`.
- Compilação: se um episódio mudar, recopiar arquivos, ajustar `partes.json`, rodar `gerar_srt.py` e
  renderizar de novo (`cursos-ia/radar-ia-jev-completo/README.md:21-23`); não há verificação automática.

## Riscos para a nossa implementação

Acoplamentos de marca que precisam virar dado (Alma/.env/config), com a origem:

| Acoplamento | Onde | Vira |
|---|---|---|
| `voice_id` `<voice_id do dono na origem>` | `cursos-ia/radar-ia-01-jev/README.md:10` | id de voz do porta-voz na Alma |
| nome de chave `elevenlabs_apikey` lido de `../.env` | `gerar_voz.py:14-19` | `ELEVENLABS_API_KEY` (`CONTRATO-capacidades.md:157,167-168`) |
| `voice_settings` e `speed 0.94` | `gerar_voz.py:37-41` | config do porta-voz (a velocidade foi ajustada depois da primeira aula) |
| rótulo do PiP `thulio.mov` | `cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:143`; `radar-ia-jev-completo/src/JevCompleto.tsx:99` | nome/handle do porta-voz |
| título da série "Radar IA · Jev / ep.09", "Radar IA · Jev · ep." | `Aula.tsx:188,219`; `src/marca.tsx:118`; `JevCompleto.tsx:152` | `serie` da peça + número do episódio |
| janela "Jev [TypeSafe AI]" | `src/marca.tsx:122` | dado da peça |
| paleta e fontes da série (rosa `#E58CA1`, Inter Tight, VT323, JetBrains Mono) copiadas da marca da ferramenta do tema | `src/marca.tsx:10-25` | tema visual da série/peça (mesma ideia do `deck.marca` das apresentações) |
| paleta laranja `#D97757` de `aula-skills` | `cursos-ia/aula-skills-2/src/AulaSkills2.tsx:20-28` | idem |
| CTA "Na próxima revisão: /revisar-pr" | `AulaSkills2.tsx:128-130` | texto da peça |
| conteúdo da aula dentro do TSX: `PASSOS`, `Intro`, `RESUMO`, "avaliar.js · 75 linhas" | `Aula.tsx:20-31,212-253` | dados da peça (JSON), não código |
| ids de composição `AulaJev`, `AulaSkills`, nomes de saída | `Root.tsx:10-11`; `package.json:6-7`; SRT com nome fixo em `gerar_legendas.py:140` | derivados do `peca_id`/slug |

O que derruba a qualidade se extraído ingenuamente:

1. **Legenda pelo texto do whisper em vez do roteiro.** O ganho de qualidade está em alinhar o texto
   exato do roteiro aos tempos do whisper; usar a transcrição direta traz "Jeve" e números em algarismo
   diferentes da fala (`raw/whisper.log:3-5`).
2. **Perder as heurísticas de corte**: 42/2, corte equilibrado, órfã < 18, bônus de vírgula,
   junção de frases curtas e de `:` (`gerar_legendas.py:53-120`). Um wrap simples gera a legenda que a
   versão de `aula-skills-2` gerava.
3. **Cue no espaço**: o tempo do cue pula espaços/quebras até a próxima letra falada
   (`gerar_voz.py:58-61`); sem isso a cena entra antes da palavra.
4. **Tudo depende de `cues.json`**: cenas, legenda, PiP, `editar_demo.py` e a compilação leem os mesmos
   segundos. Regerar a voz invalida demo, avatar e legendas; o motor precisa tratar isso como
   dependência (hoje é disciplina manual, `plano-gravacao.md:72-75`).
5. **Layouts são números calibrados à mão** (L16/L9, SAFE 168/280, PiP 272×340 em top 1318). Trocar por
   proporções genéricas quebra a sobreposição cuidadosa com a UI do Reels; a safe area precisa ser dado
   do formato/canal, não constante.
6. **Hardcode frágil**: `PIP_DURATION = Math.floor(90.8 * FPS)` fixo em
   `cursos-ia/aula-skills/src/Aula9x16.tsx:36`; as versões seguintes derivam de `data.duration`.
7. **Conteúdo em TSX**: cada episódio é código novo (`Cenas.tsx` 145-305 linhas por episódio). Para o
   núcleo gerar aulas sem escrever React, cenas precisam ser templates parametrizados por JSON (o que o
   deck do youtube-squad já faz).
8. **Estrutura pedagógica de 8 blocos** existe só na ementa; nenhum script a valida. Se virar regra do
   tipo `aula`, é inteligência nova, não extração.
9. Versões: `remotion ^4.0.527` com `typescript ^7.0.2` em cursos-ia contra `4.0.522` fixo e TS 5.6.3 no
   youtube-squad (ver `apresentacao-deck.md`); o núcleo precisa escolher uma.

## Fonte

- `cursos-ia/radar-ia-09-jev-calibracao/{gerar_voz.py, gerar_legendas.py, roteiro.txt, package.json, tsconfig.json, README.md, raw/whisper.log}`
- `cursos-ia/radar-ia-09-jev-calibracao/src/{Root.tsx, Aula.tsx, marca.tsx, cues.json, demo.json, legendas.json}`
- `cursos-ia/radar-ia-0{1..8}-*/{README.md, gerar_voz.py, gerar_legendas.py, src/*.tsx}` (comparados por md5 e diff)
- `cursos-ia/aula-skills/{gerar_voz.py, src/Aula9x16.tsx, src/Root.tsx, package.json}`
- `cursos-ia/aula-skills-2/{gerar_voz.py, gerar_legendas.py, plano-gravacao.md, src/AulaSkills2.tsx, src/AulaSkills2_9x16.tsx}`
- `cursos-ia/radar-ia-jev-completo/{README.md, gerar_srt.py, package.json, src/partes.json, src/JevCompleto.tsx, src/Root.tsx}`
- `cursos-ia/ementa-claude-code-iniciantes.md`
- `cursos-ia/.env` (só o nome da chave), `cursos-ia/.gitignore`, `git log` de cursos-ia
- Versões instaladas conferidas em `node_modules/*/package.json` e `pip show openai-whisper`
- `ExpxMedia/docs/contrato/CONTRATO-peca.md`, `ExpxMedia/docs/contrato/CONTRATO-capacidades.md`
