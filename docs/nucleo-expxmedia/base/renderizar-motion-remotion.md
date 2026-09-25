# Renderizar motion com Remotion (projeto, render, prévia, normalização e gate)

A base Remotion do projeto de vídeos: pacote pinado, composições, como o Python chama o render, a folha de prévia
para comparar com a referência, a normalização de loudness depois do encode e o gate mecânico de entrega
(`verify.py` no modo recriado). É a capacidade que o núcleo chama de `renderizar_motion` (provedor `remotion`,
ver `ExpxMedia/docs/contrato/CONTRATO-peca.md:122`).

## Contrato de entrada

### Projeto `remotion/`

- `package.json`, todas as versões exatas, sem `^` (`Instragram-Videos/remotion/package.json:9-22`):

| pacote | versão |
|---|---|
| `remotion` | 4.0.528 (`:17`) |
| `@remotion/cli` | 4.0.528 (`:12`) |
| `@remotion/renderer` | 4.0.528 (`:14`) |
| `@remotion/captions` | 4.0.528 (`:11`) |
| `@remotion/fonts` | 4.0.528 (`:13`) |
| `@fontsource/inter` | 5.3.0 (`:10`) |
| `react` / `react-dom` | 19.3.0 (`:15-16`) |
| `@types/react` | 19.3.0 (`:20`) |
| `typescript` | 5.8.3 (`:21`) |

- Instalado de fato: `node_modules/remotion` 4.0.528 e `react` 19.3.0 (lido nos `package.json` de `node_modules` em
  2026-09-24); Chrome Headless Shell `149.0.7790.0` em `remotion/node_modules/.remotion/chrome-headless-shell/`
  (arquivo `VERSION`, lido em 2026-09-24). Node `v20.20.1`, npm `10.8.2` (medido em 2026-09-24). Versão de Node
  exigida pelo projeto: NÃO DOCUMENTADO (sem `engines` nem `.nvmrc`).
- Teste de pinagem: `test_pacotes_pinados_na_mesma_versao` (`Instragram-Videos/tests/test_remotion_projeto.py:12`).
- `tsconfig.json`: ES2022, `moduleResolution: bundler`, `jsx: react-jsx`, `strict`, `resolveJsonModule` (o
  `timeline.json` é importado como módulo) (`Instragram-Videos/remotion/tsconfig.json:2-12`).
- Entrada `src/index.ts` → `registerRoot(RemotionRoot)` (`Instragram-Videos/remotion/src/index.ts:1-4`).
- Composições (`Instragram-Videos/remotion/src/Root.tsx:7-24`):
  - `ReelRecriado` (legado): 1080x1920, 30 fps, `defaultProps` = `amostra.json`, duração por `calculateMetadata`
    = `props.duracaoFrames` (`:9-18`);
  - uma por reel sob medida, de `REELS` (`registro.ts`): `id` = slug, 1080x1920, 30 fps,
    `durationInFrames = timeline.totalFrames`, sem props (`:20-22`).
- Arquivos só de `public/` via `staticFile` (Remotion só serve arquivo de `public/`,
  `Instragram-Videos/pipeline/render_remotion.py:19-20`): `public/fonts/inter-latin-{400,700,800,900}-normal.woff2`,
  `public/marca/perfil.jpg`, `public/reels/<slug>/{narracao.mp3,trilha.wav}`, `public/amostra/{clipe.mp4,foto.jpg}`,
  `public/midia/<slug>/` (temporária no legado) (listagem de `Instragram-Videos/remotion/public/` em 2026-09-24).
- Fontes locais para o render não depender de rede: `loadFont` do `@remotion/fonts`, família "Inter", pesos 400, 700,
  800, 900 (`Instragram-Videos/remotion/src/tema.ts:14-22`), carregadas com `delayRender("fontes")` →
  `continueRender`/`cancelRender` (`Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:168-171`).

### Chamada pelo Python

`python3 pipeline/render_remotion.py videos/<slug> [--manter-props] [--previa]`
(`Instragram-Videos/pipeline/render_remotion.py:8-9,237-248`). Decisão de caminho:
`sob_medida(slug)` = existe `remotion/src/reels/<slug>/Reel.tsx` (`:142-143,203-204`).

Entradas do sob medida: `videos/<slug>/alignment.json` e `narracao.mp3`, `remotion/src/reels/<slug>/cenas.json` e
`Reel.tsx` (checados por `montar-reel.mjs`, `Instragram-Videos/remotion/scripts/montar-reel.mjs:43-46`).
Entradas do legado: `roteiro.txt`, `alignment.json`, `narracao.mp3`, `roteiro_remotion.json` e mídias citadas
(`Instragram-Videos/pipeline/render_remotion.py:4-5`).

## Contrato de saída

### Render sob medida (`renderizar_sob_medida`, `Instragram-Videos/pipeline/render_remotion.py:154-164`)

1. `node scripts/montar-reel.mjs <slug>` com `cwd=remotion/` (`:146-151`): gera `timeline.json`, `trilha.wav`, copia a
   narração para `public/reels/<slug>/`, regenera `registro.ts`.
2. `npx remotion render src/index.ts <slug> <tmp>/bruto.mp4 --codec=h264 --log=error`, `cwd=remotion/`, timeout 1800 s
   (`:31,159-160`).
3. `normalizar_audio(bruto, videos/<slug>/<slug>.mp4)` (`:163`).

Diferente do legado, o sob medida **não apaga** `public/reels/<slug>/` depois do render (não há `rmtree` no caminho
sob medida, `:154-164`; a pasta do exemplo continua lá, `Instragram-Videos/remotion/public/reels/recriado-ia-decide/`).

### Render legado (`renderizar`, `:200-234`)

Monta props (`:206`), copia narração e mídias para `public/midia/<slug>/` (`:207-217`), grava
`props_remotion.json` (`:218-219`), roda `npx remotion render src/index.ts ReelRecriado <bruto> --props=<arq>
--codec=h264 --log=error` (`:222-223`), normaliza (ou copia sem normalizar quando não há áudio, `:226-229`), apaga o
`props_remotion.json` salvo com `--manter-props` (`:230-231`) e **sempre** apaga `public/midia/<slug>/` no `finally`
(`:232-233`; teste em `Instragram-Videos/tests/test_render_remotion.py:79`).

### Normalização (`normalizar_audio`, `:121-139`)

- Passada 1 (medição): `loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json` (`:122`; alvos em
  `Instragram-Videos/pipeline/lib.py:11-12`).
- Passada 2 (aplicação linear com os valores medidos), vídeo `-c:v copy`, áudio `aac` 192k, 48000 Hz,
  `+faststart` (`Instragram-Videos/pipeline/render_remotion.py:127-132`).
- Passada 3 condicional: mede o pico depois do encode (`ebur128=peak=true`, `:112-115`); se passar de
  `PICO_MAX = -1.0` dBFS (`:118`), refaz com ganho extra `PICO_MAX − 0.3 − pico` dB (`:137-139`). Motivo registrado:
  "O AAC passa do pico que o loudnorm entregou (overshoot do encode, medido: -0,7 dBFS com alvo -2)" (`:135-136`).

Saída final: `videos/<slug>/<slug>.mp4`, 1080x1920, 30 fps, h264 + aac, −14 LUFS, pico até −1 dBFS
(`Instragram-Videos/pipeline/render_remotion.py:5-6`; `Instragram-Videos/.claude/rules/recriado.md:76`).

### Prévia (`--previa`, `previa`, `Instragram-Videos/pipeline/render_remotion.py:167-197`)

- Só para sob medida (`:171-172`). Roda `montar-reel.mjs`, depois um `npx remotion still src/index.ts <slug> <png>
  --frame=<n> --scale=0.3 --log=error` por cena, timeout 600 s (`:173-181`).
- Quadro escolhido: `inicio + int(dur * 0.6)` (60% da cena) (`:179`).
- Desenha linhas vermelhas em y 220 e 1500 (guias da área segura) e o número + id da cena (`:186-188`).
- Monta grade de 5 colunas em `videos/<slug>/previa.jpg`, qualidade 85 (`:190-196`).
- Uso no processo: abrir a prévia **ao lado das folhas da referência** e cobrar composição, tipo e ordem de cena,
  estilo de legenda, tudo entre as guias e centrado, texto saindo do cartão; no máximo 3 voltas
  (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:110-121`). Instante avulso:
  `npx remotion still src/index.ts <slug> /tmp/q.png --frame=<n> --scale=0.5` (`:120`).

### Gate de entrega (`verify.py`, modo recriado)

Ativado pela existência de `videos/<slug>/recriado.json` (`Instragram-Videos/pipeline/verify.py:68`). Checa
(`Instragram-Videos/pipeline/verify.py:38-105`):

| checagem | critério | linha |
|---|---|---|
| resolução | 1080x1920 | `:38-39` (`lib.py:9`) |
| fps | `30/1` | `:41-42` |
| duração | 30 a 70 s | `:69-72` (`Instragram-Videos/pipeline/lib.py:305-306`) |
| codecs | h264 + aac | `:80-81` |
| loudness | −14 ± 1 LUFS | `:87-88` |
| pico | ≤ −1.0 dBFS | `:89-90` |
| arquivos | `alignment.json`, `roteiro.txt`, `legenda.txt` presentes | `:93-94` |
| narração cabe no vídeo | fim do alinhamento ≤ duração + 0.05 s | `:97-98` |
| alinhamento = roteiro | `"".join(characters) == roteiro.txt` | `:99` |

Não confere caps/PNG de legenda (legenda é queimada no render) (`:66-67,70`). Saída `APROVADO`/`REPROVADO` com código
0/1 (`:100-105`). Veracidade não é conferida por script (`:4-5`).

## Limites e cotas

| item | valor | fonte |
|---|---|---|
| canvas | 1080x1920 | `Instragram-Videos/remotion/src/Root.tsx:12-13,21` |
| fps | 30 | `Instragram-Videos/remotion/src/Root.tsx:14,21`; `Instragram-Videos/pipeline/lib.py:9` |
| timeout do render | 1800 s | `Instragram-Videos/pipeline/render_remotion.py:31` |
| timeout de cada still da prévia | 600 s | `Instragram-Videos/pipeline/render_remotion.py:181` |
| escala da prévia | 0.3 | `Instragram-Videos/pipeline/render_remotion.py:174` |
| colunas da prévia | 5 | `Instragram-Videos/pipeline/render_remotion.py:190` |
| alvo de loudness | −14 LUFS | `Instragram-Videos/pipeline/lib.py:11` |
| true peak alvo do loudnorm | −1.5 dBTP | `Instragram-Videos/pipeline/lib.py:12` |
| pico máximo depois do encode | −1.0 dBFS | `Instragram-Videos/pipeline/render_remotion.py:118`; `Instragram-Videos/pipeline/verify.py:89` |
| margem da passada extra | 0.3 dB | `Instragram-Videos/pipeline/render_remotion.py:139` |
| áudio final | aac 192k 48000 Hz | `Instragram-Videos/pipeline/render_remotion.py:131-132` |
| duração aceita | 30 a 70 s | `Instragram-Videos/pipeline/lib.py:305-306` |
| licença Remotion | grátis até 3 pessoas; acima, Company License; "decisão de compra é do Thulio" | `Instragram-Videos/.claude/rules/recriado.md:74-75` |
| Company License (Automators) | US$ 0,01 por render, mínimo US$ 100/mês | `Instagram-Carrosseis/docs/reels-recriados-remotion/base/remotion.md:123` |
| render medido (sonda sintética, 15 s) | 16,7 a 18,0 s de parede | `Instagram-Carrosseis/docs/reels-recriados-remotion/base/remotion.md:109-110` |
| `node_modules` | 416 MB, dos quais 193 MB de Chrome | `Instagram-Carrosseis/docs/reels-recriados-remotion/base/remotion.md:28` |

Tempo real de render do reel sob medida (42,6 s, 10 cenas SVG): NÃO DOCUMENTADO. `--concurrency`, `--crf`: não
passados, ficam no padrão do Remotion (`Instragram-Videos/pipeline/render_remotion.py:159`).

## Erros conhecidos e tratamento

| erro | tratamento | fonte |
|---|---|---|
| render falha ou não gera o bruto | `sys.exit` com os últimos 1500 caracteres de stdout+stderr | `Instragram-Videos/pipeline/render_remotion.py:161-162,224-225` |
| `montar-reel.mjs` falha | `sys.exit` com os últimos 1500 caracteres | `Instragram-Videos/pipeline/render_remotion.py:147-149` |
| still de uma cena falha na prévia | `sys.exit` com id da cena | `Instragram-Videos/pipeline/render_remotion.py:182-183` |
| medição de loudness sem bloco JSON | `sys.exit` com stderr | `Instragram-Videos/pipeline/render_remotion.py:123-125` |
| **AAC estoura o pico depois do loudnorm** (medido −0,7 dBFS com alvo −2) | passada extra automática com ganho negativo | `Instragram-Videos/pipeline/render_remotion.py:135-139`; `Instragram-Videos/.claude/rules/recriado.md:63` |
| **conteúdo "muito para cima"** na 1ª versão do reel aprovado | `centralizarNaArea(topo, base)` + guias 220/1500 na prévia | `Instragram-Videos/remotion/src/kit/anim.ts:13-26`; `Instragram-Videos/.claude/rules/recriado.md:56-58` |
| fonte do Google exige rede e estoura `delayRender` sem ela | fontes `.woff2` locais | `Instragram-Videos/remotion/src/tema.ts:16`; `Instagram-Carrosseis/docs/reels-recriados-remotion/00-AUDITORIA.md:36` |
| mídias acumulando em `public/` (bundle mais lento) | legado apaga no `finally`; sob medida não apaga | `Instragram-Videos/pipeline/render_remotion.py:232-233` |
| sem narração no legado | copia o bruto sem normalizar; `verify` reprova depois | `Instragram-Videos/pipeline/render_remotion.py:226-227` |
| `verify` reprovado | volta ao passo 3 (roteiro) ou 5 (código) | `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:130-131` |
| revisão reprovada | corrigir e renderizar de novo, no máximo 2 voltas; não fechou → `videos/<slug>/falha.txt` e parar | `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:131-133` |

Testes: `Instragram-Videos/tests/test_remotion_projeto.py:12-45` (pinagem, composição registrada, render da amostra
com duração ±0,1 s, still de cada tipo > 10 000 bytes), `Instragram-Videos/tests/test_render_remotion.py:37-79`
(render real 6 s sai 1080x1920 30/1 aac, −14 ±1 LUFS, pico ≤ −1), `Instragram-Videos/tests/test_verify_recriado.py:37-77`.
**O caminho sob medida e a `--previa` não têm teste** (nenhum `def test` os cobre, listagem em 2026-09-24).

## Riscos para a nossa implementação

1. **Versão do Remotion.** A mesma composição renderiza diferente entre versões (`ExpxMedia/docs/contrato/CONTRATO-template.md:48`).
   Travar `4.0.528` exata em todos os `@remotion/*` e `react 19.3.0`. O Remotion 5.0 muda `loadFont`, `inputProps`
   e `licenseKey` (`Instagram-Carrosseis/docs/reels-recriados-remotion/base/remotion.md:153`).
2. **Fontes de sistema no código do reel.** O reel aprovado usa `"Rockwell, Georgia, serif"` na legenda
   (`Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:20`) e a skill diz que "serifas e slab do sistema
   funcionam no render (Georgia, Rockwell, New York)" (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:102-103`).
   Em outra máquina (Linux, CI, isolamento sem fontes do macOS) a legenda cai em outra fonte e a fidelidade quebra
   sem erro. Precisa virar fonte local entregue pelo motor.
3. **Chrome Headless Shell** `149.0.7790.0` baixado na instalação; versão diferente pode mudar o raster (inferência;
   Remotion apaga e baixa de novo a versão errada, `Instagram-Carrosseis/docs/reels-recriados-remotion/base/remotion.md:115`).
4. **`fps` e canvas repetidos** em `Root.tsx:12-14,21`, `montar-reel.mjs:30`, `kit/anim.ts:11`, `lib.py:9`,
   `verify.py:42`. Um único dado do motor.
5. **Loudness depende do ffmpeg externo** e da passada extra; extrair só o `npx remotion render` entrega áudio fora de
   −14 LUFS e com pico acima de −1.
6. **`registro.ts` + composição sem props**: o sob medida lê tudo de arquivos importados (`timeline.json`) e de
   `staticFile("reels/<slug>/...")` literal (`Reel.tsx:188-189`). Contradiz o contrato do template ("caminho de asset
   fixo é violação", `ExpxMedia/docs/contrato/CONTRATO-template.md:66-67`); precisa virar props/slots.
7. **`montar-reel.mjs` usa `fs` e escreve em `src/`** (build-time). Pelo contrato, código de template não pode importar
   `fs` (`ExpxMedia/docs/contrato/CONTRATO-template.md:63-64`): a montagem da linha do tempo e a síntese da trilha têm
   de ser do motor, não do template.
8. **Licença**: acima de 3 pessoas, render por automação é pago (`Instragram-Videos/.claude/rules/recriado.md:74-75`).
   Número de pessoas de cada instalação do ExpxMedia: fora da fonte.
9. **`public/reels/<slug>/` não é limpo** no sob medida: acumula e deixa o bundle mais lento com o tempo.
10. **Gate não mede fidelidade.** O `verify` é só mecânico; parecença com a referência é julgada pelo modelo
    (prévia × folhas) e pelo revisor. Área segura e selo não são checados por script.
11. **Acoplamento de marca**: `tema.ts` (cores EXPX, Inter) e `SeloPerfil` (nome, arroba, foto) — ver
    `inteligencia-reel-recriado.md`.

## Fonte

- `Instragram-Videos/pipeline/render_remotion.py:1-252` — lido em 2026-09-24
- `Instragram-Videos/pipeline/verify.py:1-110`, `Instragram-Videos/pipeline/lib.py:9-13,302-306` — lidos em 2026-09-24
- `Instragram-Videos/remotion/package.json`, `tsconfig.json`, `src/index.ts`, `src/Root.tsx`, `src/tema.ts`, `amostra.json` — lidos em 2026-09-24
- `Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx`, `src/kit/anim.ts` — lidos em 2026-09-24
- `Instragram-Videos/tests/test_remotion_projeto.py`, `test_render_remotion.py`, `test_verify_recriado.py` — lidos em 2026-09-24
- `node --version`, `npm --version`, `node_modules/{remotion,react,...}/package.json`, `node_modules/.remotion/chrome-headless-shell/*/VERSION` — executado em 2026-09-24
- `Instagram-Carrosseis/docs/reels-recriados-remotion/base/remotion.md`, `00-AUDITORIA.md` — lidos em 2026-09-24
- `ExpxMedia/docs/contrato/CONTRATO-template.md:1-130`, `CONTRATO-peca.md:122` — lidos em 2026-09-24
