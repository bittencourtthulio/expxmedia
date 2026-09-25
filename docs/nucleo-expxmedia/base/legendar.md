# Legendar (capacidade `legendar`)

Fonte extraída: `Instragram-Videos/pipeline/captions.py`, constantes e gate em
`Instragram-Videos/pipeline/lib.py`, termos multi-palavra em `Instragram-Videos/pipeline/pronuncia.py`.
Legenda é **PNG por bloco + concat demuxer**, composta por `overlay` (ver `montagem-reel-ffmpeg.md`).

## Contrato de entrada

- `alignment.json` no formato ElevenLabs (`characters`, `character_start_times_seconds`,
  `character_end_times_seconds`), **no espaço do roteiro** (`Instragram-Videos/pipeline/captions.py:38-39`).
  Vem de `narrar` ou de `transcrever` no mesmo formato (`Instragram-Videos/pipeline/captions.py:4-5`).
- `roteiro.txt` — usado para conferir que a palavra do CTA aparece na narração
  (`Instragram-Videos/pipeline/captions.py:43,55-57`).
- `cta.txt` — palavra do CTA, fonte da verdade; convertida para maiúsculas
  (`Instragram-Videos/pipeline/captions.py:44-48`). Sem `cta.txt`, fallback por regex
  `[Cc]omenta\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9]{3,})` no roteiro (`Instragram-Videos/pipeline/captions.py:50`).
- Flags: `--sem-cta` (sem palavra destacada e sem card final) e `--offset` (padrão 0.6s; "use 0 no
  corte") (`Instragram-Videos/pipeline/captions.py:17-26`). Offset 0,6s = "um beat antes da primeira
  palavra" (`Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:55`).
- Fonte TrueType: `/System/Library/Fonts/Supplemental/Arial Black.ttf` (`Instragram-Videos/pipeline/captions.py:30`).
- Dimensões do quadro: `W=1080`, `H=1920`, `SAFE_BOTTOM=420` (`Instragram-Videos/pipeline/lib.py:9-10`).

## Contrato de saída

- `caps/NNN.png` — um PNG RGBA 1080×1920 transparente por bloco (`Instragram-Videos/pipeline/captions.py:143-151`).
- `caps/blank.png` — quadro transparente para os intervalos (`Instragram-Videos/pipeline/captions.py:145`).
- `caps/end.png` — card final do CTA ("Comenta <CTA> / para receber o link") quando há CTA
  (`Instragram-Videos/pipeline/captions.py:154-181`).
- `caps.txt` — concat demuxer: `file 'caps/xxx.png'` + `duration s`, blanks inseridos quando o
  intervalo > 0,02s, fecha com uma sobra de blank de 0,4s e repete o último `file` (regra do concat)
  (`Instragram-Videos/pipeline/captions.py:183-191`).
- `legendas.json` — `{blocos, cta, duracao, offset_audio, ritmo_cadencia, palavras_por_bloco}`
  (`Instragram-Videos/pipeline/captions.py:193-195`). Exemplo real: `blocos 41, cta NUVEM, duracao 54.33,
  offset_audio 0.6, ritmo_cadencia 4.058, palavras_por_bloco 5` (`Instragram-Videos/videos/appwrite-appwrite/legendas.json`).
  `offset_audio` e `duracao` são consumidos pela montagem (`Instragram-Videos/pipeline/compose.py:124,135`).
- SRT: **não é gerado** por esta fonte. O contrato de capacidades pede "legenda queimada e SRT"; o SRT
  teria de ser derivado de `caps.txt`/blocos (NÃO DOCUMENTADO na fonte).
- Linha impressa: blocos, cadência, palavras por bloco, CTA, duração (`Instragram-Videos/pipeline/captions.py:196-197`).

## Limites e cotas

Segmentação em palavras e blocos:
- Palavra = sequência de caracteres não-espaço; início = início do 1º char, fim = fim do último
  (`Instragram-Videos/pipeline/captions.py:59-69`).
- **Cadência medida no próprio alinhamento**: `ritmo = 1 / mediana(intervalo início→início entre
  palavras)` — a mediana ignora pausas entre frases (`Instragram-Videos/pipeline/captions.py:84-91`).
- **Palavras por bloco derivadas da cadência**: `ceil(ritmo * CAP_BLOCO_ALVO_S)` preso entre
  `CAP_PALAVRAS_BLOCO = 3` e `CAP_PALAVRAS_BLOCO_MAX = 6` (`Instragram-Videos/pipeline/lib.py:246-256`).
  `CAP_BLOCO_ALVO_S = 1.1s` (~1,6× o piso de leitura) (`Instragram-Videos/pipeline/lib.py:54-59`). Teto 6
  vem de caber em 2 linhas a 54px (`Instragram-Videos/pipeline/lib.py:61-67`). Caso âncora: 4,07 pal/s,
  3 palavras/bloco → 49% de cartões curtos; com o alvo → 5 palavras, 17% (`Instragram-Videos/pipeline/lib.py:46-58`).
- Fecha bloco quando: atinge `POR_BLOCO`, **ou** a palavra termina em `.:?!`, **ou** o bloco passa de
  **1,6s** (`Instragram-Videos/pipeline/captions.py:94-101`).
- **Termo multi-palavra do lexicon não é rachado** nem entre blocos nem entre linhas
  (`TERMOS_MULTI`, `Instragram-Videos/pipeline/pronuncia.py:82-84`; `Instragram-Videos/pipeline/captions.py:71-82,98-99,113-115`).

Desenho:
- Largura útil `LARG_MAX = W - 140 = 940px` (`Instragram-Videos/pipeline/captions.py:32`).
- Escada de fonte 78 → 72 → 66 → 60 → 54px; tenta 1 linha, depois 2 linhas; fallback 54px numa linha
  (`Instragram-Videos/pipeline/captions.py:108-120`).
- Caixa arredondada `radius 26`, cor `(0,0,0,205)`, padding +72px de largura, +40px de altura, altura
  de linha `tamanho + 18` (`Instragram-Videos/pipeline/captions.py:35,123-131`).
- Base da caixa `CAIXA_BASE = H - SAFE_BOTTOM - 1 = 1499` — **uma linha antes** da safe area
  (`Instragram-Videos/pipeline/captions.py:33-34`). A legenda mais alta (2 linhas a 78px) começa em ~1267
  (`Instragram-Videos/pipeline/compose.py:53,241-242`).
- Texto branco `(255,255,255,255)`, palavra do CTA verde `(63,185,80,255)` (`Instragram-Videos/pipeline/captions.py:35,136`).
- Card final: escada 88 → 48px para não estourar 1080px com CTA longo ("TRADINGAGENTS")
  (`Instragram-Videos/pipeline/captions.py:158-166`); começa 0,15s após o fim da narração e dura
  `SEGURA_CTA = 2.2s` (`Instragram-Videos/pipeline/captions.py:36,181`).
- Tempos dos blocos = tempos do alinhamento + `OFFSET` (`Instragram-Videos/pipeline/captions.py:151`).

Gate de legibilidade (cobrado depois, em `verify.py` — ver `verificar-reel-gates.md`):
- `CAP_BLOCO_MIN_S = 0.7s` (piso de leitura) (`Instragram-Videos/pipeline/lib.py:44`).
- Reprova se mais de `CAP_CURTOS_MAX_FRAC = 0.35` dos cartões visíveis ficam < 0,7s; `blank` e `end`
  fora da conta (`Instragram-Videos/pipeline/lib.py:81-90,219-243,259-277`). Justificativa do 0,35:
  ~20% é normal num roteiro de 130–180 palavras; 0,35 ≈ 1,75× isso e metade do caso que falhou (71%)
  (`Instragram-Videos/pipeline/lib.py:82-89`).

Custo: zero; `captions.py` pode rodar quantas vezes quiser ("de graça, pode repetir à vontade" —
`Instragram-Videos/.claude/agents/narracao.md:32`).

## Erros conhecidos e tratamento

| Situação | Tratamento | Referência |
|---|---|---|
| Sem `cta.txt` e sem "Comenta PALAVRA" no roteiro | sai com instrução para criar `cta.txt` | `Instragram-Videos/pipeline/captions.py:52-54` |
| CTA não aparece no roteiro | sai: "a narração não vai pedir o que a legenda mostra" | `Instragram-Videos/pipeline/captions.py:55-57` |
| Inferir CTA pelo 1º token em caixa alta | proibido — pinta sigla (PDF, MIT, API) de verde; já aconteceu | `Instragram-Videos/pipeline/captions.py:41-42`; `Instragram-Videos/.claude/rules/voz-e-cta.md:145-146` |
| Card final estourando 1080px com CTA longo | escada de tamanho; `verify.py` não pega (só olha a safe area vertical) | `Instragram-Videos/pipeline/captions.py:158-166` |
| "Claude Code" rachado entre blocos | `TERMOS_MULTI` proíbe corte no meio do termo | `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:212-217` |
| Legenda invadindo safe area | base da caixa 1 px acima de `H - SAFE_BOTTOM` | `Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:66-67` |
| `subtitles`/`ass` do ffmpeg | não existe nesta build (sem libass) — por isso PNG | `Instragram-Videos/.claude/rules/montagem/ffmpeg.md:3-7` |
| Alinhamento com ≤ 1 palavra ou mediana de intervalo 0 | NÃO DOCUMENTADO (o código faria `IndexError`/divisão por zero em `Instragram-Videos/pipeline/captions.py:90-91`) | — |
| Palavra isolada maior que 940px a 54px | cai no fallback de uma linha estourando a caixa; não há aviso | `Instragram-Videos/pipeline/captions.py:120` |

## Riscos para a nossa implementação

Acoplamentos de marca / plataforma:
- Fonte do macOS por caminho absoluto `/System/Library/Fonts/Supplemental/Arial Black.ttf`
  (`Instragram-Videos/pipeline/captions.py:30`) → `alma.visual.fontes` (e baixar/embutir a fonte;
  Windows/Linux não têm esse caminho). Violaria M9 e M13.
- Cores fixas: texto branco, destaque do CTA verde `(63,185,80)` (é o `#3FB950` do GitHub), caixa preta
  80% (`Instragram-Videos/pipeline/captions.py:35`) → papéis `texto_inverso`, `destaque`/`positivo`,
  `fundo` da Alma.
- Copy fixa do card final: "Comenta <CTA> para receber o link" (`Instragram-Videos/pipeline/captions.py:156-157`)
  e regex "Comenta" (`Instragram-Videos/pipeline/captions.py:50`) → texto do CTA vem da Alma/peça
  (`conteudo.cta`, `cta_forma: comentario`); idioma PT fixo.
- `SAFE_BOTTOM = 420` e duração do card são regras do **canal Instagram**, não do núcleo — pelo
  `CONTRATO-peca.md` limites de plataforma pertencem ao pack do canal.
- `OFFSET = 0.6` padrão acopla legenda à montagem de reel narrado; em fala gravada é 0.

O que derruba a qualidade se extraído de forma ingênua:
1. **Bloco de tamanho fixo** (3 palavras): a 4,07–4,24 pal/s deu 49–71% de cartões piscando < 0,7s. O
   bloco tem de derivar da cadência medida pela **mediana**, não da média (pausas mascaram).
2. **Medir cadência por `palavras / duração total`** → encolhe o bloco onde ele precisa crescer
   (`Instragram-Videos/pipeline/captions.py:84-88`).
3. Perder as condições de corte (`.:?!` e janela de 1,6s) → blocos atravessam frases e ficam longos.
4. Perder a proteção de termo multi-palavra → nomes aparecem pela metade em duas telas.
5. Ancorar a caixa exatamente em `H - SAFE_BOTTOM` → reprova no gate de safe area.
6. Tirar `blank`/`end` do cálculo errado no gate → mede pausa em vez de legibilidade.
7. Trocar PNG+overlay por filtro `subtitles` sem checar libass → quebra em builds sem libass.
8. Card final com tamanho fixo 88px → CTA longo sai cortado nas bordas.
9. O último cartão (`end.png`) é o frame que o `verify.py` compara por pixel com o último quadro do
   vídeo (`Instragram-Videos/pipeline/verify.py:143-158`): mudar o desenho do card sem mudar o gate quebra
   a verificação de cauda morta.

## Fonte

- `Instragram-Videos/pipeline/captions.py` (1–197)
- `Instragram-Videos/pipeline/lib.py` (9–10, 42–90, 195–277)
- `Instragram-Videos/pipeline/pronuncia.py` (82–84)
- `Instragram-Videos/.claude/rules/narracao/elevenlabs.md` (107–156, 212–217)
- `Instragram-Videos/.claude/rules/voz-e-cta.md` (141–148)
- `Instragram-Videos/.claude/rules/montagem/ffmpeg.md` (1–20)
- `Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md` (46–67)
- `Instragram-Videos/videos/appwrite-appwrite/legendas.json`, `caps.txt` (artefatos reais)
- Testes: nenhum teste exercita `captions.py` nem `gate_cartoes_curtos` (grep em `Instragram-Videos/tests/`).
