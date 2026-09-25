# Verificação e gates do reel

Fonte extraída: `Instragram-Videos/pipeline/verify.py`, funções de gate de `Instragram-Videos/pipeline/lib.py`,
os `stop-gate.sh` de `Instragram-Videos/.claude/hooks/*/` e o plugin equivalente do OpenCode
(`Instragram-Videos/.opencode/plugin/gates.ts`). Formato "recriado" e corte (`--sem-cta`) só aparecem
onde mudam o gate comum.

## Contrato de entrada

- `verify.py videos/<slug> [--sem-cta]` (`Instragram-Videos/pipeline/verify.py:6,16-22`).
- Lê: `<slug>.mp4` (nome = nome da pasta, `Instragram-Videos/pipeline/verify.py:25`), `caps/*.png`,
  `caps.txt`, `legendas.json`, `alignment.json`, `roteiro.txt`; opcionais `abertura.json`,
  `corte.json`, `recriado.json` (`Instragram-Videos/pipeline/verify.py:52-75,107-166`).
- Constantes de `lib.py`: `W, H, FPS, SAFE_BOTTOM, TARGET_LUFS`, `CAP_BLOCO_MIN_S`,
  `CAP_CURTOS_MAX_FRAC` (`Instragram-Videos/pipeline/lib.py:9-13,44,90`). **Fonte única da verdade**:
  mudar `lib.py` muda o que o gate cobra (`Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:92-96`).

## Contrato de saída

- Uma linha `  OK   ...` ou `  FALHA ...` por checagem (`Instragram-Videos/pipeline/lib.py:294-299`), e
  no fim `APROVADO: ...` (exit 0) ou `REPROVADO: N checagem(ns) falharam.` (exit 1)
  (`Instragram-Videos/pipeline/verify.py:168-172`). Sem o `.mp4`: sai com erro "rode compose.py antes"
  (`Instragram-Videos/pipeline/verify.py:35-36`).
- Gate de agente (hook `Stop`): exit 2 bloqueia o agente de concluir (`Instragram-Videos/.claude/hooks/montagem/stop-gate.sh:13-15`).

## Limites e cotas

Checagens de `verify.py` (todas mecânicas; veracidade **não** é checada por script —
`Instragram-Videos/pipeline/verify.py:4-5`; `Instragram-Videos/.claude/rules/veracidade.md:26-30`):

| # | Checagem | Limiar | Referência |
|---|---|---|---|
| 1 | resolução | 1080×1920 | `Instragram-Videos/pipeline/verify.py:38-39` |
| 2 | framerate | `30/1` exato | `Instragram-Videos/pipeline/verify.py:41-42` |
| 3 | duração | 50–70s (corte: 50–185s, avisa > 75s; recriado 30–70s) | `Instragram-Videos/pipeline/verify.py:68-78`; `Instragram-Videos/pipeline/lib.py:138,305-306` |
| 4 | codecs | contém `h264` e `aac` | `Instragram-Videos/pipeline/verify.py:80-81` |
| 5 | loudness integrada (`ebur128=peak=true`) | −14 ±1 LUFS | `Instragram-Videos/pipeline/verify.py:83-88` |
| 6 | pico | ≤ −1,0 dBFS | `Instragram-Videos/pipeline/verify.py:89-90` |
| 7 | safe area | nenhum pixel com alfa em `y ≥ H − 420` em `caps/*.png` (exceto `blank.png`) | `Instragram-Videos/pipeline/verify.py:107-116` |
| 8 | legibilidade da legenda | ≤ 35% dos cartões visíveis com < 0,7s na tela; mensagem com "N de M (x%) … mediana, mínimo" | `Instragram-Videos/pipeline/verify.py:118-123`; `Instragram-Videos/pipeline/lib.py:259-277` |
| 9 | sincronia | fim do último caractere + `offset_audio` ≤ duração + 0,05s | `Instragram-Videos/pipeline/verify.py:125-128` |
| 10 | cauda morta / loop | último frame (extraído com `-sseof -1`) comparado por pixel com o último cartão, na máscara dos pixels 100% opacos: erro médio ≤ 12/255 | `Instragram-Videos/pipeline/verify.py:130-158` |
| 10b | cauda sem CTA (`--sem-cta`) | ≤ 0,80s depois da última legenda | `Instragram-Videos/pipeline/verify.py:136-141` |
| 11 | CTA | `legendas.cta` existe e aparece no `roteiro.txt`; com `--sem-cta`, `cta` tem de ser `null` | `Instragram-Videos/pipeline/verify.py:160-166` |
| — | abertura | só informa a coorte (`montado_em`), não reprova | `Instragram-Videos/pipeline/verify.py:46-60` |

Gates de agente (hooks `Stop` do Claude Code; o OpenCode roda os **mesmos** scripts depois de cada
comando `pipeline/*.py` ou `browser-harness` — `Instragram-Videos/.opencode/plugin/gates.ts:3-27`):

| Agente | O que cobra | Referência |
|---|---|---|
| roteirista | 130–180 palavras; `cta.txt` não vazio e contido no roteiro; regex `[–—*#`]|\d+[.,]\d` reprova travessão, markdown e número decimal em algarismo | `Instragram-Videos/.claude/hooks/roteirista/stop-gate.sh:8-19` |
| narracao | existem `narracao.mp3`, `alignment.json`, `legendas.json`, `caps.txt` e ≥ 5 PNGs em `caps/` | `Instragram-Videos/.claude/hooks/narracao/stop-gate.sh:8-15` |
| captura | `strip.png` com 1080 de largura e ≤ 16384 de altura; se `captura.fonte == "site"`, `site.md` com ≥ 1200 chars | `Instragram-Videos/.claude/hooks/captura/stop-gate.sh:8-28` |
| montagem | `verify.py` verde (com `--sem-cta` se existe `corte.json`) | `Instragram-Videos/.claude/hooks/montagem/stop-gate.sh:9-15` |

Guardas `PreToolUse`: bloqueiam `git push/commit`, `npm publish`, `deploy`, `rm -rf`, `curl*instagram`,
`gh release` nos agentes de domínio (`Instragram-Videos/.claude/hooks/narracao/pre-bash-guard.sh:5-9`); o de
captura bloqueia também `activate_tab` (`Instragram-Videos/.claude/hooks/captura/pre-bash-guard.sh:6`);
escopo de escrita por agente (`Instragram-Videos/.claude/hooks/roteirista/pre-edit-scope.sh:8-11`); revisor
read-only nega Edit/Write e comandos mutáveis e os scripts de pipeline
(`Instragram-Videos/.claude/hooks/revisor-video/pre-tool-use.sh:6-15`).

## Erros conhecidos e tratamento

| Situação | Tratamento | Referência |
|---|---|---|
| Teto de ritmo **médio** (antigo `RITMO_TETO ≈ 4,29`) aprovou narração a 4,235 pal/s com 71% dos blocos < 0,7s (mediana 0,60s, mínimo 0,22s) | removido; gate passou a ser por **distribuição** no `caps.txt` | `Instragram-Videos/pipeline/lib.py:73-79`; `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:107-126` |
| Gate de legibilidade reprova | **reprova e informa; não desacelera** — desacelerar é decisão do dono | `Instragram-Videos/pipeline/verify.py:118-123`; `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:153-156` |
| Checar cauda só pelo tempo | não pega o caso do concat arredondar e o último frame cair no blank; por isso comparação por pixel | `Instragram-Videos/pipeline/verify.py:130-132` |
| Selo de CTA sobreposto ao card no último frame | a montagem tira o selo 0,05s antes do card para o pixel bater | `Instragram-Videos/pipeline/compose.py:249-252` |
| Corte chamado sem `--sem-cta` | reprova por não achar card que não deve existir; o hook passa a flag | `Instragram-Videos/.claude/hooks/montagem/stop-gate.sh:9-12` |
| Card final estourando a largura | **não** detectado pelo verify (só safe area vertical) | `Instragram-Videos/pipeline/captions.py:158-161` |
| Declarar verde sem ver | proibido: "Só diga que está pronto com a saída real de `pipeline/verify.py` colada" | `Instragram-Videos/.claude/agents/orquestrador.md:80-83` |

## Riscos para a nossa implementação

- **Os limiares 50–70s, 420px, 30fps, −14 LUFS são do canal Instagram/Reels**
  (`Instragram-Videos/.claude/rules/formato-entrega.md:5-14`). Pelo `CONTRATO-peca.md`, limite de
  plataforma é regra do pack do canal. O núcleo precisa receber esses números como parâmetros do pack
  (ou do formato), mantendo `lib.py`-como-fonte-única: gate e montagem lendo o mesmo lugar.
- **Stop-gates escolhem "o vídeo mais recentemente modificado"** (`ls -td videos/*/ | head -1`,
  `Instragram-Videos/.claude/hooks/montagem/stop-gate.sh:5`). Com várias peças produzidas ao mesmo tempo
  (plano do dia com várias vagas), o gate pode verificar a peça errada. No núcleo o gate precisa receber
  o id da peça.
- Gate do roteirista só pega **número decimal** em algarismo (`\d+[.,]\d`), não inteiro ("4ms" passa)
  (`Instragram-Videos/.claude/hooks/roteirista/stop-gate.sh:16`), embora a regra proíba qualquer
  algarismo (`Instragram-Videos/.claude/rules/voz-e-cta.md:137-138`). Reproduzir como está mantém o buraco.
- Faixa 130–180 palavras está duplicada: `lib.py:13` e literal no hook
  (`Instragram-Videos/.claude/hooks/roteirista/stop-gate.sh:12`). Fonte única se perde se só um mudar.
- Gate de pico −1,0 vs alvo −1,5 na montagem: não é bug, é folga; mas precisa ficar explícito.
- O que derruba a qualidade se extraído de forma ingênua:
  1. Trocar o gate de legibilidade por média de ritmo (volta o caso dos 71%).
  2. Comparar último frame só por tempo (volta o loop congelado na rolagem).
  3. Tirar a exclusão de `blank`/`end` da fração (mede pausa, não leitura).
  4. Deixar o gate "avisar" em vez de reprovar: o harness depende do exit code para travar o agente.
  5. Esquecer que veracidade **não** é mecânica — precisa do revisor humano/agente
     (`Instragram-Videos/.claude/rules/veracidade.md:26-36`).
- Testes existentes cobrem só o caminho do recriado e a detecção de formato por marcador
  (`Instragram-Videos/tests/test_verify_recriado.py:37-79`); **nenhum** teste cobre as checagens 7–11 do
  reel narrado. A fixture `gerar_video` (`Instragram-Videos/tests/conftest.py:29-40`) gera mp4 sintético
  1080×1920 30fps e a fixture autouse `sem_rede` bloqueia qualquer rede fora de localhost
  (`Instragram-Videos/tests/conftest.py:17-26`) — padrão reaproveitável.

## Fonte

- `Instragram-Videos/pipeline/verify.py` (1–172)
- `Instragram-Videos/pipeline/lib.py` (9–13, 42–90, 195–299)
- `Instragram-Videos/.claude/hooks/{roteirista,narracao,captura,montagem}/stop-gate.sh`
- `Instragram-Videos/.claude/hooks/*/pre-bash-guard.sh`, `pre-edit-scope.sh`, `revisor-video/pre-tool-use.sh`
- `Instragram-Videos/.opencode/plugin/gates.ts` (1–29)
- `Instragram-Videos/.claude/rules/formato-entrega.md` (1–38)
- `Instragram-Videos/.claude/rules/veracidade.md` (26–36)
- `Instragram-Videos/tests/conftest.py`, `tests/test_verify_recriado.py`, `tests/test_harness.py`
