# Reel recriado: roteiro, cenas, linha do tempo e trilha

Como a leitura da referência vira narração, cenas com tempo, eventos de animação, legenda e som. Existem **dois
caminhos** no código, e só um é o formato vigente:

| caminho | onde | status |
|---|---|---|
| **sob medida** (vigente desde 24/09/2026): código Remotion próprio por reel, `cenas.json` + `Reel.tsx` + cenas, linha do tempo por `montar-reel.mjs`, trilha sintetizada por `audio.mjs` | `Instragram-Videos/remotion/src/reels/<slug>/`, `Instragram-Videos/remotion/scripts/` | é o formato; "não há recuo" para o antigo (`Instragram-Videos/.claude/rules/recriado.md:16-19`) |
| **tipos fixos** (legado): `roteiro_remotion.json` com 7 tipos de cena, composição `ReelRecriado` | `Instragram-Videos/pipeline/roteiro_remotion.py`, `Instragram-Videos/remotion/src/cenas.tsx` | "saem genéricos e não são mais o formato"; só para vídeos antigos (`Instragram-Videos/.claude/rules/recriado.md:18-19`; red flag em `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:143`) |

O que liga tudo é a **âncora**: cada cena declara o trecho da narração em que entra, e o tempo sai do alinhamento
por caractere da voz sintetizada. Nenhum segundo é escrito à mão
(`Instragram-Videos/pipeline/roteiro_remotion.py:4-6`; `Instragram-Videos/remotion/scripts/montar-reel.mjs:79-91`).

## Contrato de entrada

### Roteiro (`videos/<slug>/roteiro.txt`)

- 130 a 180 palavras (`Instragram-Videos/pipeline/lib.py:13`; gate em `Instragram-Videos/pipeline/tts.py:103-106`,
  medido sobre o roteiro, não sobre a fala). Com o ritmo do canal dá ~37 a ~57 s (`Instragram-Videos/pipeline/lib.py:305`).
  O reel aprovado tem 160 palavras e 42,6 s (`wc -w` e `ffprobe` de `Instragram-Videos/videos/recriado-ia-decide/`, 2026-09-24).
- Heurística de escrita (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:70-73`): a mesma ideia e a
  **mesma sequência de beats da referência**, ~um parágrafo por cena, "nosso ângulo para dono de software house",
  gancho nos 3 primeiros s, uma afirmação por frase, fecho com CTA falado (seguir ou salvar) de `editorial/cta.md`,
  número por extenso quando a voz tropeça. Grava também `legenda.txt` (legenda do feed, hashtags na última linha).
- Voz: `Instagram-Carrosseis/editorial/voz.md` e `cta.md` (só leitura); sem travessão; sempre "você"; sem "comenta
  PALAVRA" (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:30-31`).

### Narração (`pipeline/tts.py`, uma chamada)

- ElevenLabs `with-timestamps`, `output_format=mp3_44100_128` (`Instragram-Videos/pipeline/tts.py:118`), modelo
  `eleven_multilingual_v2` por padrão (`:16`), `voice_settings` stability 0.45, similarity_boost 0.8, style 0.25,
  speaker_boost, `speed` = `TTS_SPEED` ou 1.2 (`:27,113-114`; `Instragram-Videos/pipeline/lib.py:24`).
- Saída: `narracao.mp3` e `alignment.json` **no espaço do `roteiro.txt`** (caracteres do roteiro, não da fala com
  grafia de pronúncia) e já reescalado ao ritmo final (`Instragram-Videos/pipeline/tts.py:141-148`).
- Formato do alinhamento (ElevenLabs): `characters`, `character_start_times_seconds`, `character_end_times_seconds`
  (`Instragram-Videos/pipeline/render_remotion.py:35-36`; `Instragram-Videos/remotion/scripts/montar-reel.mjs:64-66`).
- Uma chamada só: "Não chame de novo por ajuste de cena" (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:81`).

### Especificação do reel sob medida (`remotion/src/reels/<slug>/cenas.json`)

Documentada no topo de `Instragram-Videos/remotion/scripts/montar-reel.mjs:11-21`:

```
{ "trilha": { "bpm", "acordes": [[raizHz, [notasHz...]], ...], "instrumentos": {kick, caixa|palma, chimbal, pluck|sino, pad, baixo},
              "arpejo": [índices], "ganho", "fade_s"?, "semente"? },
  "troca":  [{ "f": frames relativos ao início da cena, "tipo": efeito, "desde": índice da 1ª cena, "vol"? }],
  "legenda": { "palavras_por_bloco": N },
  "cauda_s": s,
  "cenas": [{ "id", "ancora", "ev": {evento: fração da duração da cena}, "sons": [[ref, tipo, durFrac?, vol?]], ...livre }] }
```

- `ancora`: primeiras palavras da narração em que a cena entra (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:88`).
- `ev`: eventos da animação como **fração da duração da cena**; a mesma chave dispara imagem e som
  (`Instragram-Videos/remotion/scripts/montar-reel.mjs:20-21`).
- `sons[i][0]` (ref): nome de evento, `"0"` (início da cena) ou soma `"i0+viagem"` (`:20,118-126`).
- Campos livres por cena passam direto para o componente (ex.: `tag: [linha1, linha2]` usado pela etiqueta,
  `Instragram-Videos/remotion/src/reels/recriado-ia-decide/cenas.json:86-89`; `.../Reel.tsx:13,80`).
- Exemplo aprovado: 10 cenas, `trilha` bpm 100 com 4 acordes, instrumentos kick 0.35 / caixa 0.1 / chimbal 0.035 /
  pluck 0.022 / pad 0.028 / baixo 0.2, ganho 0.55, semente 7; `troca` whoosh em f −3 (vol 0.7, desde 1), pop em f 5
  (vol 0.5, desde 0), check em f 14 (desde 1); `palavras_por_bloco` 3; `cauda_s` 1.4
  (`Instragram-Videos/remotion/src/reels/recriado-ia-decide/cenas.json:2-81`).

### Componentes do reel sob medida

- `Reel.tsx` exporta `export const Reel: React.FC`, lê `./timeline.json`, carrega fontes, desenha a tela fixa, uma
  `Sequence` por cena, a legenda no estilo da referência e toca `narracao.mp3` e `trilha.wav` (volume ~0.8)
  (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:93-95`).
- Cada cena recebe `f` (frame local), `d` (duração em frames) e `ev(nome)` (frame local do evento)
  (`Instragram-Videos/remotion/src/reels/recriado-ia-decide/cenas.tsx:7`); `ev("0") = 0`, senão
  `round(ev[nome] * dur)` (`.../Reel.tsx:64`). Registro `CENAS: Record<id, componente>` e `FUNDOS: Record<id, cor>`
  (`.../cenas.tsx:9-20,453-464`).
- Kit comum obrigatório (`Instragram-Videos/remotion/src/kit/`): `anim.ts` (`clamp`, `rampa`, `mola`,
  `AREA_SEGURA`, `centralizarNaArea`) e `SeloPerfil.tsx` (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:98-101`).

### Legado: `roteiro_remotion.json`

Tipos e limites em caracteres (`Instragram-Videos/pipeline/roteiro_remotion.py:22-33`):

| tipo | campos (limite) |
|---|---|
| `titulo` | `texto` (60), `apoio?` (90) |
| `lista` | `titulo?` (50), `itens` (2 a 5, cada um até 42) |
| `numero` | `valor` (8), `texto` (70) |
| `citacao` | `texto` (140), `autor?` (40) |
| `imagem` | `arquivo` (.jpg/.jpeg/.png/.webp na pasta do vídeo), `texto?` (70) |
| `video` | `arquivo` (.mp4/.mov/.webm na pasta do vídeo), `texto?` (70) |
| `cta` | `texto` (60), `apoio?` (90) |

3 a 14 cenas (`:22`); toda cena tem `ancora` (`:91-93`); `acento` opcional no topo (`Instragram-Videos/pipeline/render_remotion.py:105`).

## Contrato de saída

### `node scripts/montar-reel.mjs <slug>` (cwd `remotion/`)

Pré-requisitos, com falha e mensagem se faltar: `cenas.json` e `Reel.tsx` do reel, `videos/<slug>/alignment.json` e
`narracao.mp3` (`Instragram-Videos/remotion/scripts/montar-reel.mjs:43-46`). Grava:

1. `src/reels/<slug>/timeline.json` = `{fps, totalFrames, cenas, blocos}` (`:138`):
   - **palavras**: agrupa caracteres do alinhamento separados por espaço em `{w, t0, t1}` (`:63-77`);
   - **normalização da âncora**: minúsculas, NFD sem diacríticos, só `[a-z0-9]` por palavra (`:79`);
   - **início da cena**: primeira ocorrência da âncora a partir do cursor (em ordem); cena 0 começa em 0; as demais
     em `t0 da palavra − 0.12 s` (`:81-91`);
   - `totalFrames = round((fim da última palavra + cauda_s) * 30)`, `cauda_s` padrão 1.4 (`:93-94`);
   - cena = campos livres + `ev` + `inicio` (frame) + `dur` (até o início da próxima; a última até `totalFrames`);
     `ancora` e `sons` saem (`:95-100`);
   - aviso (não falha) se a cena dura menos de 30 frames: "curta demais para a animação respirar" (`:101-103`);
   - **blocos de legenda**: N palavras por bloco (padrão 3), fechando também em palavra terminada em `. , : ? !`,
     cada palavra com `f0`/`f1` em frames (`:105-115`).
2. `public/reels/<slug>/narracao.mp3` (cópia) e `public/reels/<slug>/trilha.wav` (música + efeitos) (`:139-146`).
3. `src/reels/registro.ts` regenerado com uma composição por pasta que tenha `Reel.tsx` e `timeline.json`, em ordem
   alfabética; arquivo marcado "GERADO ... não edite à mão" (`:148-163`; exemplo
   `Instragram-Videos/remotion/src/reels/registro.ts:1-8`).
4. Console: `"<slug>: N cenas · F frames (Xs) · E efeitos"` e uma linha por cena com início e duração (`:165-166`).

Exemplo real (`Instragram-Videos/remotion/src/reels/recriado-ia-decide/timeline.json`): `totalFrames` 1275, 10 cenas
(corrida 0+166, loop 166+122, milhao 288+116, casos 404+89, decisao 493+85, confianca 578+128, rota 706+171,
custo 877+130, feature 1007+166, cta 1173+102), 62 blocos de legenda (lido com python em 2026-09-24).

### Sons (`montar-reel.mjs` + `audio.mjs`)

- Frame de evento = `inicio + round(soma das frações * dur)`; evento citado que não existe em `ev` = falha
  (`Instragram-Videos/remotion/scripts/montar-reel.mjs:118-126`).
- `troca` padrão, se ausente: whoosh em f −3 desde a cena 1 e pop em f 5 desde a cena 0 (`:128`).
- Duração de som por fração da cena: `durFrac * dur / 30` s (`:133-135`).
- Trilha: `criarMix(totalFrames/30 + 0.5, semente ?? 7)`, `musica(trilha, totalFrames/30)`, efeitos em `f/30` s (`:143-146`).
- WAV estéreo 16 bit, 44100 Hz, saturação suave `tanh` × 32000 (`Instragram-Videos/remotion/scripts/audio.mjs:11,266-285`).
- PRNG determinístico (Park-Miller 16807) com semente (`Instragram-Videos/remotion/scripts/audio.mjs:18-19`).
- Música: compasso de 4 tempos, `BEAT = 60/bpm`; pad (notas/2), baixo em 0 e 2,5 tempos, kick em 1 e 3, caixa/palma em
  2 e 4, chimbal em colcheias, arpejo em colcheias (pula metade nos compassos ímpares); fade final `fade_s` padrão 1.6 s,
  `ganho` padrão 0.55, aplicados só ao que a música escreveu (`Instragram-Videos/remotion/scripts/audio.mjs:215-256`).
- Arpejo padrão `[0,1,2,1,2,0,1,2]` (`:218`).
- Biblioteca de efeitos (20): whoosh, pop, bolha, check, ding, tick, digita, erro, carimbo, impacto, subida, descida,
  moeda, snip, clack, plim, hum, chime, passos, pagina (`Instragram-Videos/remotion/scripts/audio.mjs:102-210`).
  Efeito desconhecido lança erro listando os existentes (`:261-264`).
- Instrumentos: kick, caixa, palma, chimbal, pluck, sino, baixo, pad (`:54-96`).

### Reel sob medida em tela (exemplo aprovado)

`Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx`:

- fundo `#EFE8DA` + dois gradientes radiais (`:174-175`);
- bloco inteiro desenhado entre y 124 e 1482 e passado por `centralizarNaArea(124, 1482)` (`:176-178`);
- cartão `x 60, y 330, w 960, h 780`, raio 40, SVG `viewBox 0 0 960 780` (`:18,70-78`);
- transição: `TRANS = 12` frames de sobreposição (a `Sequence` dura `dur + 12`, menos a última), wipe circular
  `circle(0→160% at 100% 45%)` e zoom 1.05→1.00 em 20 frames (`:19,65-66,72,180`);
- etiqueta de 2 linhas acima do cartão (`top: CARD.y − 62`, altura 116, largura `maior linha * 25 + 160`), mola
  (3, 11, 170), ícone girando `f*3` graus (`:22-59`);
- barra de progresso em y 170, de x 100 a 980, pontos por cena, cabeça com o mascote, ícone final diferente (`:85-132`);
- legenda por blocos: top 1135, altura 240, fonte `"Rockwell, Georgia, serif"` 700 90 px, palavra dita em
  `P.ferrugem`, não dita `#CDBDA6`, entra 2 frames antes da primeira palavra com mola (12, 200) (`:20,134-165`);
- `SeloPerfil` em y 1392 (`:186`);
- áudio: `narracao.mp3` volume 1 e `trilha.wav` volume 0.8 (`:188-189`).

### Legado: props da composição `ReelRecriado`

`montar_props` (`Instragram-Videos/pipeline/render_remotion.py:79-105`) → `{cenas: [{...tipo, inicioFrame, duracaoFrames}],
legendas: Caption[], audio, duracaoFrames, acento}`; `duracaoFrames = ceil((fim do alinhamento + 0.8) * 30)` (`:30,88-89`);
início da cena = tempo da palavra da âncora sem recuo (diferente do −0.12 s do sob medida) (`:96`); legendas no formato
`@remotion/captions` com espaço antes de cada palavra menos a primeira, `timestampMs` = meio da palavra,
`confidence: None` (`:53-60`).

## Limites e cotas

| item | valor | fonte |
|---|---|---|
| fps da linha do tempo | 30 | `Instragram-Videos/remotion/scripts/montar-reel.mjs:30` |
| recuo da cena antes da palavra-âncora | 0.12 s | `Instragram-Videos/remotion/scripts/montar-reel.mjs:87` |
| cauda depois da última palavra (sob medida) | 1.4 s padrão | `Instragram-Videos/remotion/scripts/montar-reel.mjs:94` |
| cauda (legado) | 0.8 s | `Instragram-Videos/pipeline/render_remotion.py:30` |
| duração mínima recomendada por cena | 30 frames (1 s), só aviso | `Instragram-Videos/remotion/scripts/montar-reel.mjs:102` |
| palavras por bloco de legenda | 3 padrão | `Instragram-Videos/remotion/scripts/montar-reel.mjs:106` |
| cenas (legado) | 3 a 14 | `Instragram-Videos/pipeline/roteiro_remotion.py:22` |
| itens de lista (legado) | 2 a 5 | `Instragram-Videos/pipeline/roteiro_remotion.py:33` |
| palavras do roteiro | 130 a 180 | `Instragram-Videos/pipeline/lib.py:13` |
| taxa de amostragem da trilha | 44100 Hz | `Instragram-Videos/remotion/scripts/audio.mjs:11` |
| volume da trilha no Remotion | 0.8 | `Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:189` |
| orçamento: roteiro+TTS ~5 min, código ~35, prévia e ajuste ~20, render e verificação ~10 | | `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:33-34` |
| cenas no exemplo aprovado | 10 | `Instragram-Videos/remotion/src/reels/recriado-ia-decide/cenas.tsx:453-464` |

Número máximo de cenas no sob medida, duração máxima de cena, teto de efeitos: NÃO DOCUMENTADO.

## Erros conhecidos e tratamento

| erro | tratamento | fonte |
|---|---|---|
| âncora não casa com a narração, em ordem | falha com cena e âncora | `Instragram-Videos/remotion/scripts/montar-reel.mjs:90`; legado `Instragram-Videos/pipeline/render_remotion.py:93-94` |
| âncora fora de ordem ou fora do roteiro (legado) | mensagem distingue os dois casos | `Instragram-Videos/pipeline/roteiro_remotion.py:95-99` |
| trilha igual à de outro reel (mesmo bpm, acordes e conjunto de instrumentos) | recusa: "Cada reel tem a sua: mude andamento, harmonia ou timbre." | `Instragram-Videos/remotion/scripts/montar-reel.mjs:50-60` |
| `cenas.json` sem `trilha.bpm` ou `trilha.acordes` | falha | `Instragram-Videos/remotion/scripts/montar-reel.mjs:51` |
| som cita evento inexistente | falha | `Instragram-Videos/remotion/scripts/montar-reel.mjs:123` |
| efeito de som desconhecido | exceção com a lista | `Instragram-Videos/remotion/scripts/audio.mjs:262` |
| **transição chiando** (ruído branco aberto até 4 kHz): usuário reprovou "muito alto e feio, parece um chiado" | `whoosh` refeito: ruído filtrado duas vezes (até ~900 Hz), envelope sin², tom subindo por baixo, 30% do volume | `Instragram-Videos/remotion/scripts/audio.mjs:5-8,103-113`; `Instragram-Videos/.claude/rules/recriado.md:61-62` |
| música competindo com a voz | ganho ~0.55 antes do mix e trilha a 0.8 no Remotion | `Instragram-Videos/remotion/scripts/audio.mjs:8` |
| roteiro fora de 130-180 palavras | `tts.py` para antes de gastar crédito | `Instragram-Videos/pipeline/tts.py:103-106` |
| alinhamento devolvido ≠ texto enviado | grava `alignment.raw.json` e para; "NÃO chame a API de novo" | `Instragram-Videos/pipeline/tts.py:129-139` |
| cenas genéricas (tipos fixos): as 3 primeiras recriações saíram "só tipografia sobre fundo escuro" | troca de formato para o sob medida | `Instragram-Videos/videos/recriado-20260924-151859/revisao.md` (seção 2); `Instragram-Videos/.claude/rules/recriado.md:10-19` |
| comentário desatualizado: `cenas.tsx` cita `scripts/montar-iadecide.mjs`, que não existe (o script é `montar-reel.mjs`) | não tratado | `Instragram-Videos/remotion/src/reels/recriado-ia-decide/cenas.tsx:6` |

Testes: legado coberto (`Instragram-Videos/tests/test_roteiro_remotion.py:27-55`,
`Instragram-Videos/tests/test_render_remotion.py:37-63`). **`montar-reel.mjs` e `audio.mjs` não têm teste** (nenhum
arquivo em `Instragram-Videos/tests/` os cita; listagem dos `def test` em 2026-09-24).

## Riscos para a nossa implementação

1. **Extrair o legado em vez do sob medida.** `roteiro_remotion.py` + `cenas.tsx` são os únicos com contrato Python e
   teste, e parecem "o núcleo". Mas são exatamente o que o dono reprovou como genérico. O valor está em
   `montar-reel.mjs` (âncora → frames, eventos, blocos), `audio.mjs` e na estrutura `cenas.json` + `Reel.tsx` + cenas.
2. **Âncora com recuo diferente entre caminhos** (0.12 s no sob medida, 0 no legado). Portar um só dos cálculos muda o
   sincronismo percebido.
3. **Evento = fração da duração da cena.** Se a narração mudar, os eventos esticam junto (é o que mantém som e imagem
   presos). Converter para segundos absolutos quebra essa propriedade.
4. **`fps` 30 duplicado**: `montar-reel.mjs:30`, `kit/anim.ts:11` (mola com `fps: 30` fixo), `Root.tsx:14,21`,
   `lib.py:9`. Mudar em um lugar só dessincroniza a mola da linha do tempo.
5. **Determinismo do áudio** depende da semente e do PRNG próprios (`audio.mjs:18-19`). Trocar por `Math.random` ou
   outra biblioteca muda a trilha a cada render.
6. **Anti-repetição fraca**: a assinatura da trilha compara só bpm, acordes e **nomes** de instrumentos (não volumes,
   arpejo nem semente) (`montar-reel.mjs:52`). Personagem e cena "não reaproveitados" não têm gate mecânico; dependem
   do revisor.
7. **Alinhamento por caractere é específico da ElevenLabs.** Outro provedor de TTS precisa entregar o mesmo formato
   (`characters` + tempos) ou um adaptador; o `verify` exige `alignment.json` caractere a caractere igual ao roteiro
   (`Instragram-Videos/pipeline/verify.py:99`).
8. **`registro.ts` gerado reescreve o `Root`** a cada montagem com todos os reels da pasta; um reel quebrado derruba o
   bundle de todos (inferência do fato de `Root.tsx:20-22` importar todos; comportamento em falha: NÃO DOCUMENTADO).
9. **Acoplamento de marca e de pessoa a virar dado da Alma**: "dono de software house" como ângulo, CTA de
   `editorial/cta.md`, voz de `editorial/voz.md`, voz clonada, "sempre você", "sem travessão"
   (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:30-31,70-73`); textos literais nas cenas do exemplo
   ("ERP", "CRM", "CLÍNICA", "Salva este vídeo") (`.../recriado-ia-decide/cenas.tsx:395`, `.../cenas.json` âncora da cena `cta`).
10. **Faixa de palavras acoplada ao TTS do canal**: uma referência de 15 s não cabe em 130-180 palavras (achado de
    auditoria `Instagram-Carrosseis/docs/reels-recriados-remotion/00-AUDITORIA.md:22`); a duração do recriado
    não segue a da referência.

## Fonte

- `Instragram-Videos/remotion/scripts/montar-reel.mjs:1-166` — lido em 2026-09-24
- `Instragram-Videos/remotion/scripts/audio.mjs:1-288` — lido em 2026-09-24
- `Instragram-Videos/remotion/src/reels/recriado-ia-decide/{Reel.tsx,cenas.tsx,pecas.tsx,cenas.json,timeline.json}` — lidos em 2026-09-24
- `Instragram-Videos/remotion/src/reels/registro.ts:1-8` — lido em 2026-09-24
- `Instragram-Videos/pipeline/roteiro_remotion.py:1-120` — lido em 2026-09-24
- `Instragram-Videos/pipeline/render_remotion.py:30-105` — lido em 2026-09-24
- `Instragram-Videos/pipeline/tts.py:10-148`, `Instragram-Videos/pipeline/lib.py:9-40,302-306` — lidos em 2026-09-24
- `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md`, `Instragram-Videos/.claude/rules/recriado.md` — lidos em 2026-09-24
- `Instragram-Videos/tests/` (listagem dos testes) — lido em 2026-09-24
- `Instagram-Carrosseis/docs/reels-recriados-remotion/00-AUDITORIA.md` — lido em 2026-09-24
