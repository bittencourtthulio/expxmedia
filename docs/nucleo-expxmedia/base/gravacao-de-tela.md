# Gravação de tela e edição da demo (cursos-ia)

Área: capturar a demonstração (navegador e VS Code) de forma autônoma, marcar o tempo de cada passo e
cortar a gravação para caber na fala (`editar_demo.py`), com enquadramento 16:9 e "câmera" 9:16. Vira as
capacidades `capturar_pagina` e `editar_video` e o papel `tela` da peça `aula`
(`ExpxMedia/docs/contrato/CONTRATO-capacidades.md:44,35`; `ExpxMedia/docs/contrato/CONTRATO-peca.md:194-196`).

Evolução: `aula-skills-2` e `radar-ia-06` pediam gravação manual com plano de passos
(`cursos-ia/aula-skills-2/plano-gravacao.md:1-47`; `cursos-ia/radar-ia-06-jev-openrouter/plano-gravacao.md:6-81`);
`radar-ia-06` foi gravado de forma automatizada no navegador (`README.md:8-17`); `radar-ia-07` a `09`
somam VS Code controlado por teclado do sistema (`cursos-ia/radar-ia-07-jev-codigo/README.md:15-39`).
Versões mais evoluídas: `gravador.py`, `demo.py`, `passos.py` idênticos de 06 a 09 (md5); `kb.py`
idêntico de 07 a 09; `preparar.py` e `editar_demo.py` de `radar-ia-09`; `acao.py` só em 06.

## Contrato de entrada

### Navegador: `gravador.py` (roda dentro do browser-harness)

- Uso: `GRAV_DIR=<pasta> browser-harness < gravador.py`
  (`cursos-ia/radar-ia-09-jev-calibracao/gravacao/gravador.py:2`). Para quando existir o arquivo
  `<pasta>/PARAR` (`:5,11`).
- Liga `Emulation.setFocusEmulationEnabled` para gravar com a aba em segundo plano (`:6`;
  `cursos-ia/radar-ia-06-jev-openrouter/README.md:11-12`) e desliga no `finally` (`:35`).
- `Page.startScreencast` JPEG qualidade 88, até 1920×1080, todo quadro (`:8`); confirma cada quadro com
  `Page.screencastFrameAck` (`:27`); grava `NNNNNN.jpg` e o índice com o `metadata.timestamp` (`:29-31`).
- Sem quadro por mais de 3,0 s: para e reinicia o screencast, porque página parada não gera quadro e a
  navegação pode derrubar o screencast (`:12-22`). Laço de 20 ms (`:32`).

### Navegador: `demo.py` + `passos.py` + roteiro de ações (exec dentro do browser-harness)

- `setup_demo()`: viewport 1440×810 com `deviceScaleFactor` 4/3, que dá quadros de 1920×1080
  (`gravacao/demo.py:26-29`; `radar-ia-06-jev-openrouter/README.md:9-10`), e injeta o cursor em toda
  página nova (`Page.addScriptToEvaluateOnNewDocument`, `:28`).
- Cursor visível: SVG branco com contorno, anel de clique `#d4ff3a` que expande em 0,35 s, posição
  salva em `sessionStorage` para sobreviver à navegação, padrão `[720,405]` (`demo.py:3-23`).
- `move(x, y, dur=0.6)`: easing smoothstep `t²(3-2t)`, 40 passos por segundo, mínimo 8 (`:37-42`).
- `click`: move, pausa 0,25 s, `mousePressed`, 0,08 s, `mouseReleased` (`:44-48`).
- `wheel(dy, dur=1.0)`: 30 eventos por segundo, mínimo 6 (`:50-55`).
- `type_slow(text, cps=18)`: `Input.insertText` caractere a caractere; `\n` vira Enter (`:57-63`).
- `box(expr)`: centro e tamanho do elemento via `getBoundingClientRect` (`:65-67`); `by_text(sel, texto)`
  acha elemento pelo início do `innerText` (`:69-70`).
- `mark(label)`: acrescenta `{"label", "t": time.time()}` em `MARKS` (`:72-75`); `MARKS` não é definido
  em `demo.py`, o chamador precisa definir.
- `passos.py`: `wait_run` espera o botão "Stop" sumir, até 80 × 0,25 s (`gravacao/passos.py:3-8`);
  `scroll_to` rola pela coluna lateral (x 220, y 700) porque com o cursor sobre textarea a roda rolaria
  o campo, tolerância 8 px (`:13-17`).
- `acao.py` (só 06): a sequência do episódio, com `mark()` por passo, `assert` de que o botão está na
  viewport e de que o resultado apareceu, e espera por regex até 120 s
  (`cursos-ia/radar-ia-06-jev-openrouter/gravacao/acao.py:6-77`). É roteiro específico do site, não
  infraestrutura.

### VS Code: `kb.py`, `preparar.py`, `fluxo_vscode*.py`

- `kb.py`: teclado via `osascript`/System Events com o VS Code em primeiro plano
  (`cursos-ia/radar-ia-09-jev-calibracao/gravacao/kb.py:1-2,8-17`); teclas por key code
  (`:24-29`); atalhos com modificadores (`:32-34`).
- `digitar(texto, pedaco=4, pausa=0.02)`: **cola** pedaços de 4 caracteres pela área de transferência
  (`pbcopy` + Cmd+V) em vez de digitar, porque o layout ABNT tem teclas mortas para crase e til
  (`kb.py:1-2,37-66`; `cursos-ia/radar-ia-07-jev-codigo/README.md:29-30`). Quebra de linha e a indentação
  que vem depois entram num pedaço só (`kb.py:52-57`). Limpa a área de transferência no fim (`:66`).
- `preparar.py`: fecha as janelas da instância (até 4 tentativas), abre `code -n --profile "Aula Jev"`,
  posiciona a janela e ajusta o tamanho para 1920×1080, limpa notificações, abre terminal em `~`
  (`cursos-ia/radar-ia-09-jev-calibracao/gravacao/preparar.py:13-28`). Posição da janela: `{0, 30}` em
  09 (`:20`) e `{1512, -98}` em 07/08 (diff de `cursos-ia/radar-ia-07-jev-codigo/gravacao/preparar.py`).
- Perfil do VS Code separado, sem extensões, sem autocompletar e sem fechar parênteses
  (`cursos-ia/radar-ia-07-jev-codigo/README.md:24-26`); `editor.wordWrap: on` depois que linhas longas
  rolaram o editor para a direita no take 1 da aula 08
  (`cursos-ia/radar-ia-08-jev-cascata/README.md:39-40`).
- `fluxo_vscode9.py <pasta-do-projeto> <marks.jsonl> [pedaco]`: exige o VS Code na frente
  (`assert kb.frente() == "Code"`, `:24`), abre o projeto com `code -r .` (`:28`), cola o arquivo de dados
  de uma vez e "digita" o código (`:38,53`), roda `node --env-file=.env` e maximiza o painel (`:61-62`),
  segura 12 s no resultado (`:63`), com `kb.mark` em cada passo
  (`cursos-ia/radar-ia-09-jev-calibracao/gravacao/fluxo_vscode9.py`).
- `fluxo_vscode8.py`: insere blocos em linhas calculadas a partir da diferença entre a versão inicial e
  a final do arquivo, indo à linha por Quick Open `:N` porque Ctrl+G não abre naquele perfil
  (`cursos-ia/radar-ia-08-jev-cascata/gravacao/fluxo_vscode8.py:14-30`;
  `cursos-ia/radar-ia-08-jev-cascata/README.md:37-38`).
- Alternativa tentada em 07: `vsc.py` controla o VS Code por `orca computer` (`paste-text`,
  `type-text` em blocos de 6 caracteres a 28 cps) (`cursos-ia/radar-ia-07-jev-codigo/gravacao/vsc.py:1-57`).
  Os fluxos usados importam `kb`, não `vsc` (`fluxo_vscode.py:4`, `fluxo_vscode8.py:5`).
- Captura do VS Code: `ffmpeg` com avfoundation da tela (`cursos-ia/radar-ia-07-jev-codigo/README.md:20`).
  O instante de início fica em `gravacao/ffmpeg-inicio.txt` (epoch) e o PID em `gravacao/ffmpeg.pid`
  (`cursos-ia/radar-ia-09-jev-calibracao/gravacao/ffmpeg-inicio.txt:1`). Geometria de 09: tela principal
  3008×1692 (captura 6016×3384), janela em (0, 30) com 1920×1080 lógicos, filtro
  `crop=3840:2160:0:60,scale=1920:1080` (`cursos-ia/radar-ia-09-jev-calibracao/README.md:42-45`). A linha
  de comando completa do ffmpeg: NÃO DOCUMENTADO (não há script; o log só tem avisos do objc,
  `raw/vscode-ffmpeg.log:1-3`).

### Marcas de tempo

- `marks.jsonl`: uma linha `{"label": str, "t": epoch}` por passo (`demo.py:72-75`, `kb.py:69-71`).
- `marks-rel.json`: `{"t0": epoch, "marks": [{"label", "s": segundos desde t0}]}`
  (`cursos-ia/radar-ia-09-jev-calibracao/gravacao/vscode-marks-rel.json`). Observado nos dados: para o
  VS Code, `t0` é o valor de `ffmpeg-inicio.txt` (1790289468.0898628 nos dois arquivos de 09); para o
  screencast, `t0` é o timestamp do primeiro quadro (`nav/marks-rel.json` `t0` = `nav/frames.json[0].t`
  = 1790264059.414433, em 07). O script que faz essa conversão: NÃO DOCUMENTADO (não está no repositório).
- Quadros → vídeo: `concat.txt` no formato do demuxer concat do ffmpeg, `file`/`duration` por quadro com
  a duração real de cada um, último quadro repetido no fim
  (`cursos-ia/radar-ia-07-jev-codigo/gravacao/nav/concat.txt:1-4,1187-1189`;
  `radar-ia-06-jev-openrouter/README.md:18`). O script que gera o `concat.txt` e o comando que monta
  `raw/<trecho>.mp4`: NÃO DOCUMENTADO.

### `editar_demo.py` (versão de `radar-ia-09`)

- Entrada: `src/cues.json`, `gravacao/*marks-rel.json`, os arquivos que foram digitados e
  `raw/<arquivo>.mp4` (`cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:10-21,47-50`).
- `JANELAS`: lista `(cue, arquivo, início, fim, rótulo, câmera, crop 16:9, crop 9:16)` que diz qual
  trecho da gravação cobre cada cue (`:32-44`). O fim de cada janela é o início do cue seguinte
  (`:45,53`).
- Pontos dentro de uma digitação longa são estimados **proporcionalmente aos caracteres**: o instante
  em que "`const FAIXAS`" começa a ser digitado = início + duração × posição no arquivo / tamanho
  (`:18-21`; mesma técnica em `radar-ia-07/editar_demo.py:19-23` e `radar-ia-08/editar_demo.py:19-27`).
- Por trecho: `rate = max(1.0, duração_gravada / duração_da_fala)`; se a gravação é mais curta, roda em
  1× e congela o último quadro por `hold` (`:53-60`). Nunca desacelera.
- Filtro ffmpeg por trecho: `trim`, `setpts=(PTS-STARTPTS)/rate`, `fps=30`, `scale=1920:1080`,
  `tpad=stop_mode=clone`, `trim=duration`; depois `concat` e `yuv420p` (`:57-65`); `libx264 -crf 18
  -preset medium` (`:67-68`). `SO_JSON=1` regrava só o `demo.json` (`:66`).
- Enquadramentos em px da gravação 1920×1080: `TELA`, `EDITOR` (x 213, y 86, 1707×960), recortes da
  saída do terminal e `QUADRADO` 800×800 para o 9:16 (`:25-30`; README `:46-47`). Em 07/08 o
  `EDITOR` era x 302, y 128, 1618×910 e havia `PAGINA`/`OPENROUTER` (`radar-ia-07/editar_demo.py:26-29`).
- Câmera do 9:16: lista de `(t na gravação, cx)` por janela, convertida para o tempo do `demo.mp4`
  (`:62`). Em 06 a câmera mostrava "uma faixa de 1050 px de largura" e era uma lista global por marca
  (`cursos-ia/radar-ia-06-jev-openrouter/editar_demo.py:52-73`).

## Contrato de saída

- Pasta de take: `NNNNNN.jpg`, `frames.json` (`[{"f", "t"}]`), `marks.jsonl`, `gravador.log`
  (`frames N`), `PARAR`, `concat.txt`, `marks-rel.json` (`radar-ia-07-jev-codigo/gravacao/nav/`).
- `raw/<trecho>.mp4` 1920×1080 por trecho gravado (`cursos-ia/radar-ia-07-jev-codigo/README.md:17-22`).
- `public/demo.mp4`: começa no cue `s2`, sem áudio, soma exata das durações das falas
  (`editar_demo.py:4,69`).
- `src/demo.json`: `{"inicio": cues.s2, "segmentos": [{cue, de, ate, rate, janela, camera[{t,cx}],
  crop{x,y,w,h}, crop9}], "camera": [...]}` (`editar_demo.py:63,69`;
  `cursos-ia/radar-ia-09-jev-calibracao/src/demo.json`). Consumido por `Aula.tsx` (rótulo da janela, selo
  de aceleração, crop e câmera; ver `aula-pipeline.md`).

## Limites e cotas

- Screencast: JPEG q88, ≤ 1920×1080 (`gravador.py:8`); reinício após 3,0 s sem quadro (`:12`).
- Viewport 1440×810 × 4/3 (`demo.py:27`).
- `wait_run`: até 20 s (80 × 0,25 s, `passos.py:5`); Jev Lab: até 120 s (`acao.py:67`).
- `kb.digitar`: 4 caracteres a cada 20 ms de pausa + latência do osascript por pedaço (`kb.py:47,64`);
  `avaliar.js` de 75 linhas levou 143 s de digitação (`vscode-marks-rel.json`: `avaliar` 51,111 s →
  `avaliar_fim` 194,163 s).
- Aceleração máxima: sem teto no código (`editar_demo.py:54`). Selo na tela a partir de 1,5×
  (`Aula.tsx:108`).
- Custo de gravação com API paga do tema: ~US$ 0,05 para três passagens em 06
  (`cursos-ia/radar-ia-06-jev-openrouter/README.md:36-40`); chave temporária com validade de 1 dia e
  limite de US$ 1 (`cursos-ia/radar-ia-07-jev-codigo/README.md:34-39`).

## Erros conhecidos e tratamento

- Chrome pede "Allow remote debugging?" e o browser-harness espera
  (`cursos-ia/radar-ia-06-jev-openrouter/raw/ref/lab.log:1`).
- Take 2 de 06: a rolagem caiu dentro de um campo de texto e o score não rodou; resolvido rolando pela
  coluna lateral e refazendo o take (`radar-ia-06-jev-openrouter/README.md:16-17`; `passos.py:16`).
- Screencast para de mandar quadro com a página parada ou após navegação: reinício automático
  (`gravador.py:12-22`).
- Teclas mortas do ABNT corrompem a digitação: colar em pedaços (`kb.py:1-2`). Arquivos digitados
  conferidos com `diff` contra a referência (`radar-ia-07-jev-codigo/README.md:31`,
  `radar-ia-08-jev-cascata/README.md:41`).
- Janela errada na frente: `assert kb.frente() == "Code"` aborta o fluxo (`fluxo_vscode9.py:24`).
- Linhas longas rolavam o editor: take descartado, `wordWrap` ligado (`radar-ia-08-jev-cascata/README.md:39-40`).
- Confiança de pasta do VS Code interrompe a gravação: `security.workspace.trust.enabled` desligado só
  durante a gravação e restaurado byte a byte (`radar-ia-07-jev-codigo/README.md:32-33`).
- Verificação de e-mail no meio da criação da chave: o usuário digitou o código e o trecho foi cortado
  (`radar-ia-08-jev-cascata/README.md:32-33`). A partir de 09, criação e exclusão da chave não aparecem
  no vídeo, a pedido do usuário (`radar-ia-09-jev-calibracao/README.md:36-41`).
- Mudança de monitores entre sessões mudou crop e enquadramento (`radar-ia-09-jev-calibracao/README.md:42-47`).

## Riscos para a nossa implementação

Acoplamentos de máquina e de marca que precisam virar config:

| Acoplamento | Onde |
|---|---|
| Geometria de monitores: posição `{0,30}` / `{1512,-98}`, 3008×1692, crop `3840:2160:0:60` | `preparar.py:20` (07 e 09); `radar-ia-09-jev-calibracao/README.md:42-45` |
| Enquadramentos em px (`EDITOR`, `PAGINA`, `QUADRADO`, câmera `cx`) calibrados para aquela janela | `editar_demo.py:25-44` (09), `:26-46` (07) |
| Teclado ABNT (motivo do colar em pedaços) e key codes do macOS | `kb.py:1-2,24` |
| Perfil de VS Code "Aula Jev" e nome do app "Visual Studio Code" / processo "Code" | `preparar.py:19`; `kb.py:16` |
| Cor do anel de clique `#d4ff3a` | `demo.py:14` |
| Seletores e textos do site gravado (`Run decision`, `Preview`, `Jev Lab`) | `passos.py:2-20`; `acao.py` |
| `osascript`, `pbcopy`, avfoundation: só macOS | `kb.py:9,38`; `radar-ia-07-jev-codigo/README.md:20` |

O que derruba a qualidade se extraído ingenuamente:

1. **Gravação primeiro, roteiro depois.** A narração cita números reais da tela; inverter a ordem produz
   fala que não bate com o que aparece (`radar-ia-06-jev-openrouter/plano-gravacao.md:6-10`).
2. **Regra só-acelera/congela** (`rate >= 1`, `tpad clone`) e o selo "▶▶ N×" são o que mantém a tela
   em sincronia com a fala sem câmera lenta. Um "stretch" genérico desacelera e fica visível.
3. **Interpolação por caracteres** para achar o meio de uma digitação só funciona porque o texto é colado
   em ritmo constante; digitação com ritmo variável quebra o corte.
4. **Glue ausente**: frames → `concat.txt` → `raw/*.mp4` e marks → `marks-rel.json` não estão em
   script. O motor precisa implementar e testar isso; não há código para extrair.
5. **Segurança de chave na gravação**: chave nova por aula, validade de 1 dia, limite de US$ 1, lida da
   área de transferência para arquivo 0600, nunca impressa, mascarada na tela, excluída no fim com
   confirmação de 401 (`radar-ia-07-jev-codigo/README.md:34-39`). Isso é processo, não código.
6. **Estado do sistema alterado** (confiança de pasta, perfil do editor, área de transferência) precisa de
   restauração garantida; hoje é manual ("restaurado byte a byte").
7. **Foco**: o navegador grava em segundo plano com emulação de foco; o VS Code exige primeiro plano e
   bloqueia a máquina durante o take.
8. **Dependência de ferramenta local**: `browser-harness` (e `orca computer` na alternativa) não estão no
   catálogo de capacidades; `capturar_pagina` prevê Playwright (`CONTRATO-capacidades.md:44`), que não
   usa o Chrome logado do usuário que as aulas 06-09 exigiram.

## Fonte

- `cursos-ia/radar-ia-09-jev-calibracao/gravacao/{gravador.py, demo.py, passos.py, kb.py, preparar.py, fluxo_vscode9.py, ffmpeg-inicio.txt, vscode-marks-rel.json}`
- `cursos-ia/radar-ia-09-jev-calibracao/{editar_demo.py, README.md, src/demo.json, raw/vscode-ffmpeg.log}`
- `cursos-ia/radar-ia-08-jev-cascata/{editar_demo.py, README.md, gravacao/fluxo_vscode8.py}`
- `cursos-ia/radar-ia-07-jev-codigo/{editar_demo.py, README.md, gravacao/vsc.py, gravacao/fluxo_vscode.py, gravacao/preparar.py, gravacao/nav/*}`
- `cursos-ia/radar-ia-06-jev-openrouter/{editar_demo.py, README.md, plano-gravacao.md, roteiro-rascunho.md, gravacao/acao.py, raw/ref/lab.log}`
- `cursos-ia/aula-skills-2/plano-gravacao.md`
- md5 dos scripts de `gravacao/` de 06 a 09
