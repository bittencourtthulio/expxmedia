# Montagem de reel com ffmpeg (capacidade `editar_video`)

Fonte extraída: `Instragram-Videos/pipeline/compose.py` (scroll + cartão de impacto + selo de CTA +
abertura de fundo + legendas + narração + loudnorm), `Instragram-Videos/pipeline/stitch.py` (tira) e
`Instragram-Videos/.claude/rules/montagem/ffmpeg.md`. A abertura gerada em si está em
`abertura-higgsfield.md`; os gates em `verificar-reel-gates.md`.

## Contrato de entrada

Diretório da peça com (`Instragram-Videos/pipeline/compose.py:12-13,161,267-269`):
- `strip.png` — tira vertical já em 1080px de largura (de `stitch.py`).
- `captura.json` — com `strip_h`, `px_por_css`, `secoes[{t,y}]` (`Instragram-Videos/pipeline/stitch.py:29-31`;
  `Instragram-Videos/pipeline/compose.py:137,147-148`).
- `caps.txt` + `caps/*.png` + `legendas.json` (`duracao`, `offset_audio`, `cta`) (de `captions.py`).
- `narracao.mp3`.
- `impacto.txt` (até 3 linhas, CAIXA ALTA) — obrigatório quando o visual v2 está ligado
  (`Instragram-Videos/pipeline/compose.py:111-114,193-196`).
- Opcional: `abertura.mp4` + `abertura.json` (com `rosto`), de `abertura.py`
  (`Instragram-Videos/pipeline/compose.py:38-40,101-103`).
- Flags: `--sem-impacto`, `--sem-selo`, `--sem-abertura` (`Instragram-Videos/pipeline/compose.py:4,28-29,39`).
- Gatilho do visual v2: existe `repo.json` **ou** existe `impacto.txt` (`Instragram-Videos/pipeline/compose.py:27`).

Constantes de formato (`Instragram-Videos/pipeline/lib.py:9-12`): `W=1080`, `H=1920`, `FPS=30`,
`TARGET_LUFS=-14.0`, `TARGET_TP=-1.5`.

## Contrato de saída

- `<slug>.mp4` final (`Instragram-Videos/pipeline/compose.py:293`).
- Intermediários: `scroll.mp4`, `bruto.mp4` (apagado ao fim — `Instragram-Videos/pipeline/compose.py:299`),
  `impacto.png` (véu + cartão), `impacto_cartao.png` (só o cartão), `selo.png`
  (`Instragram-Videos/pipeline/compose.py:203-219,248`).
- `visual.json` — marcador de coorte do que **foi ao ar**: `{metodo:"visual-v2", impacto:[linhas]|null,
  selo_cta, abertura_gerada: segundos|null}` (`Instragram-Videos/pipeline/compose.py:259-264`).
- `abertura.json.montado_em` — escrito **só depois** do mp4 final existir; `null` se montou sem abertura
  (`Instragram-Videos/pipeline/compose.py:301-309`).
- Para `peca.json`: `<slug>.mp4` → `papel: "final"`, `formato: "9:16"`. Os marcadores `visual.json`/
  `abertura.json` são "detalhe do pack" dentro da pasta, como o contrato permite.

## Limites e cotas

Pipeline em 3 passes de ffmpeg:

1. **Scroll** (`Instragram-Videos/pipeline/compose.py:160-166`):
   `-loop 1 -framerate 30 -i strip.png -vf crop=w=1080:h=1920:x=0:y='if(lt(t,HOLD),0,min((t-HOLD)*vel,percurso))',format=yuv420p`,
   `libx264 -preset slow -crf 18`.
   - `HOLD = IMPACTO_S + 1.0 = 3,5s` com cartão; `2,0s` sem (`Instragram-Videos/pipeline/compose.py:117`).
   - Velocidade: `IDEAL 160`, `MIN_V 90`, `MAX_V 230` px/s ("abaixo arrasta, acima borra")
     (`Instragram-Videos/pipeline/compose.py:138`; `Instragram-Videos/.claude/rules/formato-entrega.md:32-37`).
   - Ponto de parada: percorre `secoes` (títulos da página) e escolhe a fronteira cujo `y*px_por_css - H`
     dá velocidade dentro de 90–230 e mais perto de 160; senão, `min(percurso_max, 160*tempo_scroll)`
     (`Instragram-Videos/pipeline/compose.py:145-158`).
   - `crop` sem `eval` (removido no ffmpeg 8) (`Instragram-Videos/.claude/rules/montagem/ffmpeg.md:9-13`).
2. **Composição** (`Instragram-Videos/pipeline/compose.py:266-281`), com `cwd` na pasta da peça e todas
   as entradas relativas (`Instragram-Videos/.claude/rules/montagem/ffmpeg.md:15-20`):
   - entradas: `scroll.mp4`, `-f concat -safe 0 -i caps.txt`, `narracao.mp3`, extras;
   - legendas: `[1:v]format=rgba,fps=30,scale=1080:1920` + `overlay` (com `enable='gte(t,2.5)'` quando a
     abertura tem rosto — `Instragram-Videos/pipeline/compose.py:272-273`);
   - áudio: `aresample=48000,asetpts=PTS-STARTPTS,adelay=delays=<offset_ms>:all=1,apad`
     (`Instragram-Videos/pipeline/compose.py:276`). `adelay` vira silêncio real; **nunca `-itsoffset`**
     (edit list não sobrevive ao re-encode do Instagram — `Instragram-Videos/pipeline/compose.py:133-135`).
     `all=1` porque a narração é mono (`Instragram-Videos/pipeline/compose.py:275`).
   - `libx264 -preset slow -crf 19 -pix_fmt yuv420p -r 30`, `aac 192k`, `+faststart`
     (`Instragram-Videos/pipeline/compose.py:278-279`).
   - Duração `-t DUR`: `DUR = min(legendas.duracao, floor(fim_do_último_cartão * 30)/30)` — o vídeo fecha
     **junto com o card do CTA**, um quadro de folga para o último frame ainda ser o cartão
     (`Instragram-Videos/pipeline/compose.py:118-132`).
3. **Loudnorm em duas passagens** (`Instragram-Videos/pipeline/compose.py:283-299`): mede
   `loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json` **sobre `narracao.mp3`**, aplica com `measured_*`,
   `offset`, `linear=true`; `-c:v copy` (não re-encoda vídeo), `aac 192k -ar 48000 +faststart`.
   (`Instragram-Videos/.claude/rules/montagem/ffmpeg.md:22-29`.)

Cartão de impacto (visual v2, desde 19/09/2026 — `Instragram-Videos/pipeline/compose.py:15-29`):
- Janela `IMPACTO_S = 2.5s` (`Instragram-Videos/pipeline/compose.py:25`); máximo 3 linhas
  (`Instragram-Videos/pipeline/compose.py:194-196`).
- Caixa amarela `(255,212,0)`, texto preto, `radius 34`, largura = maior linha + 110, altura =
  `round(tam*1.18)*linhas + 70` (`Instragram-Videos/pipeline/compose.py:197-216`).
- Tamanho: maior de 150 → 72px (passo 2) que caiba em `W - 200` (`Instragram-Videos/pipeline/compose.py:62,73-76`).
- Posição: centro y=780 sem rosto; com rosto medido, faixas "abaixo do rosto" (base do rosto → piso) e
  "acima do rosto" (`TOPO_UI = 250` → topo do rosto), maior primeiro, encolhendo até caber; não coube →
  **AVISO** explícito, nunca silêncio (`Instragram-Videos/pipeline/compose.py:52-53,62-91`). Piso = 1260
  (`LEGENDA_TOPO`) ou `H - SAFE_BOTTOM = 1500` quando a legenda espera o cartão sair
  (`Instragram-Videos/pipeline/compose.py:107`).
- Sem abertura: página desfocada `gblur sigma=26` até `IMPACTO_S - 0.15`, véu `(0,0,0,120)`
  (`Instragram-Videos/pipeline/compose.py:218,224-227`). Com abertura: sem véu e sem desfoque; o clipe é o
  fundo (`Instragram-Videos/pipeline/compose.py:31-37,220-223`).
- Saída do cartão: `fade=t=out:st=2.2:d=0.3:alpha=1` (`Instragram-Videos/pipeline/compose.py:228`).
- Abertura: `overlay=0:0:eof_action=pass:enable='lt(t,ABERT_S)'` sobre o scroll
  (`Instragram-Videos/pipeline/compose.py:186-191`).

Selo de CTA (`Instragram-Videos/pipeline/compose.py:233-258`):
- "Comenta <CTA>" em 44px, pílula 84px de altura, `radius 42`, fundo `(0,0,0,225)`, contorno verde
  `(63,185,80)` 4px, base em y=1240 (a legenda mais alta começa em ~1267).
- Visível de `SELO_INICIO_S = 5.0s` até 0,05s antes do card final (o card já é o CTA grande e é o que o
  `verify.py` compara por pixel) (`Instragram-Videos/pipeline/compose.py:25,249-256`).
- Só liga se `legendas.json.cta` existe (`Instragram-Videos/pipeline/compose.py:29`).

Tira (`Instragram-Videos/pipeline/stitch.py`):
- Cola `chunks/*.png` em ordem sobre fundo `(33,40,48)`, redimensiona para 1080 de largura com LANCZOS
  (`Instragram-Videos/pipeline/stitch.py:13-27`).
- Limite 16384px de altura (textura ffmpeg/PIL) — aborta acima (`Instragram-Videos/pipeline/stitch.py:22-25`).
- Grava `strip_w`, `strip_h`, `px_por_css` em `captura.json` (`Instragram-Videos/pipeline/stitch.py:29-31`).

Ambiente verificado: ffmpeg 8.0.1 **sem libass**; `crop` sem `eval` (`Instragram-Videos/CLAUDE.md:152-153`).

## Erros conhecidos e tratamento

| Situação | Tratamento | Referência |
|---|---|---|
| `impacto.txt` ausente com visual v2 | sai com instrução; válvula `--sem-impacto` | `Instragram-Videos/pipeline/compose.py:111-114` |
| `impacto.txt` com > 3 linhas | sai: "O cartão fica 2,5s na tela: mais que isso ninguém lê" | `Instragram-Videos/pipeline/compose.py:194-196` |
| Falha no scroll / composição / normalização | sai com stderr do ffmpeg | `Instragram-Videos/pipeline/compose.py:165-166,280-281,297-298` |
| Medição de loudness sem JSON | sai com cauda do stderr | `Instragram-Videos/pipeline/compose.py:286-288` |
| `Error applying option 'eval' to filter 'crop'` | tirar `eval=frame` | `Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:62` |
| `No such filter: 'subtitles'` | build sem libass: PNG + overlay | `Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:63` |
| Caminho absoluto misturado com `cwd=OUT` | "arquivo não existe" (prefixo duplicado) | `Instragram-Videos/.claude/rules/montagem/ffmpeg.md:15-20` |
| Contagem de índices de entrada por token | quebrava com entradas de nº de flags diferentes; `entrada()` devolve índice | `Instragram-Videos/pipeline/compose.py:171-181` |
| Cauda muda após o card (rolagem sem legenda nem áudio) | corte no fim do último cartão alinhado à grade de quadros | `Instragram-Videos/pipeline/compose.py:118-132` |
| `adelay "600|600"` em narração mono | silenciava o 2º valor; usar `all=1` | `Instragram-Videos/pipeline/compose.py:275` |
| Cartão tapando rosto da abertura | escolha por faixa medida + AVISO; 3 alturas fixas (780, 1230, 1040) falharam | `Instragram-Videos/pipeline/compose.py:41-51`; `Instragram-Videos/.claude/rules/montagem/abertura.md:75-96` |
| Cartão caindo sobre a legenda | com rosto, legenda só entra após 2,5s (narração segue do zero) | `Instragram-Videos/pipeline/compose.py:95-103,273`; `Instragram-Videos/.claude/rules/montagem/abertura.md:98-111` |
| `montado_em` marcado antes do mp4 existir | proibido — coorte "nasceria mentindo" | `Instragram-Videos/pipeline/compose.py:301-304` |
| Tira > 16384px | `stitch.py` aborta; aumentar `CSS_W` em vez de reduzir qualidade | `Instragram-Videos/pipeline/stitch.py:23-25`; `Instragram-Videos/.claude/rules/captura/cdp.md:103-107` |
| Nenhuma faixa em `chunks/` | "a captura falhou" | `Instragram-Videos/pipeline/stitch.py:14-15` |

## Riscos para a nossa implementação

Acoplamentos de marca / plataforma:
- Fonte `/System/Library/Fonts/Supplemental/Arial Black.ttf` (`Instragram-Videos/pipeline/compose.py:94,169`) → Alma.
- Amarelo `(255,212,0)` do cartão, verde `(63,185,80)` do selo, véu/pílula pretos
  (`Instragram-Videos/pipeline/compose.py:213,218,244-247`) → papéis de cor da Alma (`destaque`, `positivo`…).
- Copy "Comenta " no selo (`Instragram-Videos/pipeline/compose.py:236`) → `conteudo.cta`/Alma.
- `TOPO_UI = 250`, `SAFE_BOTTOM = 420`, `LEGENDA_TOPO = 1260`, selo em 1240, duração 50–70s — medidas
  de UI do **Instagram** e da legenda atual; são do pack do canal, não do núcleo.
- Gatilho do visual v2 por existência de `repo.json` (`Instragram-Videos/pipeline/compose.py:27`) =
  acoplamento ao formato "repositório" (marcador de pack). No núcleo deve ser opção da peça/template.
- `IMPACTO_S 2.5`, `SELO_INICIO_S 5.0`, `HOLD` são **testes em andamento** com marco em
  `performance.md` (`Instragram-Videos/.claude/rules/performance.md:389-394`) — parâmetros de template,
  não constantes.

O que derruba a qualidade se extraído de forma ingênua:
1. **Velocidade fixa de scroll** em vez de escolher a fronteira de seção dentro de 90–230 px/s → texto
   borrado ou scroll arrastado e fim no meio de seção.
2. **Duração = duração do áudio + folga** em vez do fim do último cartão alinhado ao quadro → cauda
   morta e último frame (congelado no loop) errado; o gate por pixel reprova.
3. **Loudnorm de uma passagem** ou ganho fixo → fora de −14 ±1 LUFS; re-encodar vídeo na 3ª etapa →
   perda de qualidade.
4. **Medir loudness só da narração** funciona porque o único áudio é a narração
   (`Instragram-Videos/pipeline/compose.py:284`). Se o núcleo somar trilha/efeitos (b-roll, música),
   a medição tem de ser sobre a mistura final — extrair como está quebraria o alvo.
5. **`-itsoffset` para o lead-in** → o atraso some no re-encode da plataforma e desincroniza legenda.
6. **Posição fixa do cartão** quando há rosto na abertura → cobre os olhos (medido).
7. **Colar a abertura na frente** (alongando o vídeo) → silêncio no começo; foi descartado
   (`Instragram-Videos/.claude/rules/montagem/abertura.md:16-34`).
8. **Marcadores escritos antes do final** → análise de coorte errada.
9. Divergência de alvo de pico: montagem mira `TP -1.5` mas o gate aceita até `-1.0 dBFS`
   (`Instragram-Videos/pipeline/lib.py:12`; `Instragram-Videos/pipeline/verify.py:89-90`) — manter os dois
   valores com o mesmo significado.
10. Stale doc: a skill ainda diz "hold inicial 2,0s" (`Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:53`),
    mas com cartão o código usa 3,5s (`Instragram-Videos/pipeline/compose.py:117`). Extrair da regra e
    não do código perde o ajuste.

## Fonte

- `Instragram-Videos/pipeline/compose.py` (1–311)
- `Instragram-Videos/pipeline/stitch.py` (1–32)
- `Instragram-Videos/pipeline/lib.py` (9–12, 195–216, 288–291)
- `Instragram-Videos/.claude/rules/montagem/ffmpeg.md` (1–31)
- `Instragram-Videos/.claude/rules/formato-entrega.md` (1–38)
- `Instragram-Videos/.claude/rules/voz-e-cta.md` (231–268)
- `Instragram-Videos/.claude/rules/montagem/abertura.md` (16–34, 75–111)
- `Instragram-Videos/.claude/agents/montagem.md` (1–79)
- `Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md` (22–97)
- `Instragram-Videos/CLAUDE.md` (92–93, 110–131, 150–154)
- `Instragram-Videos/videos/appwrite-appwrite/visual.json` (artefato real)
- Testes: nenhum exercita `compose.py` nem `stitch.py`; `Instragram-Videos/tests/test_harness.py:12-16`
  só confere que o vídeo sintético do `conftest.py` tem o formato.
