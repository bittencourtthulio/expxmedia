# Transcrição com tempo por palavra (capacidade `transcrever`)

Origem: `Instragram-Videos/pipeline/transcrever.py` (219 linhas) e um segundo consumidor em
`Instragram-Videos/pipeline/analisar_reel.py:119-130`. Alimenta `legendar` (via `captions.py`,
fora desta área) e a escolha de trecho (`momentos.py`, ver `corte-e-reenquadramento.md`).

## Contrato de entrada

- CLI: `python3 pipeline/transcrever.py <dir> [--alinhar] [--modelo M] [--audio ARQ] [--recasar]`
  (`Instragram-Videos/pipeline/transcrever.py:28-36`).
- Três modos, escolhidos por flag:
  1. **Varredura da aula inteira** (padrão): entrada `<dir>/fonte.m4a`
     (`Instragram-Videos/pipeline/transcrever.py:99`), onde `<dir>` = `fontes/<video_id>`.
     Serve só para escolher trecho; erro de grafia aqui não vai à tela
     (`Instragram-Videos/pipeline/transcrever.py:6-8`).
  2. **Alinhamento do corte** (`--alinhar`): entrada `<dir>/corte9x16.mp4`
     (`Instragram-Videos/pipeline/transcrever.py:97`), onde `<dir>` = `videos/<slug>`. Este texto vai
     queimado na tela (`Instragram-Videos/pipeline/transcrever.py:9-11`).
  3. **Recasamento** (`--recasar`): entrada `<dir>/alignment.json` + `<dir>/roteiro.txt` corrigido à
     mão (`Instragram-Videos/pipeline/transcrever.py:54-56`). Não chama modelo nenhum.
- `--audio` sobrescreve o arquivo de entrada (`Instragram-Videos/pipeline/transcrever.py:94-95`).
- Qualquer formato que o ffmpeg/whisper leia; a duração é medida por `ffprobe format=duration`
  (`Instragram-Videos/pipeline/transcrever.py:108`).
- Modelo padrão: `small` na varredura, `medium` no `--alinhar`
  (`Instragram-Videos/pipeline/transcrever.py:41`). Confirmado nos artefatos reais: as 15
  `fontes/*/transcricao.json` gravam `"modelo": "small"` e as 16 `videos/yt-*/transcricao_corte.json`
  gravam `"modelo": "medium"`, todas com `"motor": "faster-whisper"`.
- **Idioma fixo `pt`** nos dois motores (`Instragram-Videos/pipeline/transcrever.py:132`, `:152`).
  `analisar_reel.py` não fixa idioma e lê `info.language` (`Instragram-Videos/pipeline/analisar_reel.py:123-130`).

## Contrato de saída

- **Varredura**: `<dir>/transcricao.json` (`Instragram-Videos/pipeline/transcrever.py:103`) com
  `{"fonte", "modelo", "motor", "palavras": [{"w","t0","t1"}], "segmentos": [{"t0","t1","texto"}]}`
  (`Instragram-Videos/pipeline/transcrever.py:143-148`, `:170-171`). Tempos arredondados a 3 casas
  (`:143`, `:148`).
- **Alinhamento**: `<dir>/transcricao_corte.json` (mesmo esquema, `:103`) **e** `<dir>/roteiro.txt` +
  `<dir>/alignment.json` (`:208-213`). O `alignment.json` sai **no formato da ElevenLabs**:
  `characters`, `character_start_times_seconds`, `character_end_times_seconds`, tempos a 4 casas
  (`:13-14`, `:209-213`). É o que torna `legendar` agnóstico da origem (narração ou fala gravada).
- Conversão palavra → caractere (`Instragram-Videos/pipeline/transcrever.py:180-200`):
  - tempo distribuído uniformemente dentro da palavra (`:195-198`); erro máximo declarado
    "dezenas de milissegundos" (`:182-184`);
  - separador entre palavras é `\n` se a anterior termina em `. ? ! :`, senão espaço (`:191`); o
    separador ocupa o silêncio entre as palavras (`:192`);
  - duração mínima de palavra 0,02 s (`:194`); início nunca antes do fim da anterior (`:194`).
- Invariantes afirmadas com `assert` (`Instragram-Videos/pipeline/transcrever.py:203-206`):
  `len(chars) == len(texto)`, `"".join(chars) == texto`, tempos monotônicos (tolerância 1e-6).
  São as mesmas de `.claude/rules/narracao/elevenlabs.md` (`:15-17`).
- **Recasamento** (`Instragram-Videos/pipeline/transcrever.py:52-92`): `difflib.SequenceMatcher`
  com `autojunk=False` (`:62`); trecho igual copia tempos exatos (`:64-65`); trecho trocado distribui
  o intervalo uniformemente (`:79-81`); **inserção pura no meio tem largura zero**, só no fim do texto
  estica 0,02 s por caractere (`:70-78`, bug real documentado: "pull " em "esse request"). Mesmas
  asserções de invariante (`:82-84`). Se o texto não mudou, sai 0 sem escrever (`:57-59`).
- Mensagens de próximo passo embutidas: `momentos.py` após varredura (`:176`); `--recasar` e
  `broll.py --plano` após alinhamento (`:214-219`). Acoplamento de pipeline, não de capacidade.

## Limites e cotas

- Sem API, sem chave, sem cota: roda local em CPU (`device="cpu", compute_type="int8"`,
  `Instragram-Videos/pipeline/transcrever.py:125`; idem `Instragram-Videos/pipeline/analisar_reel.py:122`).
- Parâmetros do `faster-whisper` (`Instragram-Videos/pipeline/transcrever.py:132-134`):
  `word_timestamps=True`, `vad_filter=True`, `condition_on_previous_text=False`,
  `beam_size=5` no `--alinhar` e `1` (gulosa) na varredura.
- Parâmetros do `whisper` de referência (CLI) (`Instragram-Videos/pipeline/transcrever.py:152-154`):
  `--model M --language pt --word_timestamps True --output_format json --fp16 False`.
- Tempo medido: aula de 14 min com `small` → ~30 min no whisper de referência em CPU contra "poucos
  minutos" no faster-whisper; ganho declarado de 4 a 8x (`Instragram-Videos/pipeline/transcrever.py:109-113`,
  `Instragram-Videos/CLAUDE.md:157-160`).
- Sem `condition_on_previous_text=False`: laço de repetição medido em "15 min de CPU a 400% sem
  fechar" (`Instragram-Videos/pipeline/transcrever.py:127-130`).
- Progresso impresso a cada 60 s de áudio consumido (`Instragram-Videos/pipeline/transcrever.py:137-142`).
- Cache: `transcricao.json` da varredura é reaproveitado se existir; para refazer, apagar o arquivo
  (`Instragram-Videos/pipeline/transcrever.py:104-106`). O `--alinhar` **sempre** retranscreve (`:104`).
- Modelos presentes na máquina (verificado no disco, não no código): cache HF com
  `Systran/faster-whisper-small`, `-medium`, `-large-v3`; `~/.cache/whisper` com `base.pt`, `small.pt`,
  `medium.pt`. Download automático do modelo na primeira execução: NÃO DOCUMENTADO no código.
- Não usa `initial_prompt`, `hotwords` nem vocabulário: NÃO DOCUMENTADO/não implementado.
- GPU/Metal: NÃO DOCUMENTADO (sempre CPU).

## Erros conhecidos e tratamento

| Erro | Tratamento | Fonte |
|---|---|---|
| Diretório inexistente | `sys.exit("ERRO: ... não existe.")` | `Instragram-Videos/pipeline/transcrever.py:38-40` |
| Entrada ausente (etapa anterior não rodou) | `sys.exit` pedindo a etapa anterior | `:100-101` |
| `faster_whisper` não instalado | cai para o CLI `whisper` silenciosamente, anuncia o motor | `:114-119` |
| CLI `whisper` falha ou não gera JSON | `sys.exit` com os últimos 1200 caracteres do stderr | `:156-158` |
| Nenhuma palavra com tempo | `sys.exit` dizendo que `--word_timestamps True` exige openai-whisper recente | `:167-169` |
| Laço de repetição em áudio longo | prevenido com `condition_on_previous_text=False` | `:127-130` |
| Silêncio longo gastando decoder | `vad_filter=True` | `:126-127` |
| Whisper erra nome próprio e jargão ("Claude Code", "software house", "MCP") | **manual**: corrigir `roteiro.txt` e rodar `--recasar`; sem isso a correção é ignorada em silêncio pela legenda | `:43-48`, `:214-219`; `Instragram-Videos/.claude/skills/gerar-reel-corte/SKILL.md:94-99` |
| Recasamento quebrando monotonicidade | inserção pura com largura zero | `:70-78` |
| `alignment.json` que não reconstrói `roteiro.txt` | gate de saída do agente `corte` reprova | `Instragram-Videos/.claude/hooks/corte/stop-gate.sh:29-36` |

## Riscos para a nossa implementação

1. **Idioma cravado em `pt`** (`transcrever.py:132`, `:152`). No núcleo o idioma tem que vir da Alma
   (ou da peça). Extrair como está faz qualquer instalação não-lusófona transcrever errado sem erro.
2. **Duas passagens com modelos diferentes é decisão de qualidade, não detalhe.** `small`+gulosa na
   varredura (barato, só para escolher) e `medium`+beam 5 no trecho que vai à tela. Unificar em um só
   modelo ou deixar `small` no alinhamento degrada a legenda queimada; usar `medium` na aula inteira
   custa minutos de CPU. Os dois precisam virar parâmetros da capacidade (`modelo_varredura`,
   `modelo_alinhamento`, `beam`).
3. **O formato de saída "igual ao da ElevenLabs" é o contrato que desacopla `legendar` da origem.**
   Se o núcleo definir outro formato para `transcrever`, perde-se o reuso e as invariantes de
   `len/join/monotonia`. O fluxo `--recasar` (difflib com a regra de inserção de largura zero) tem que
   ir junto — sem ele, correção manual de grafia é descartada em silêncio.
4. **O fallback para o whisper de referência transforma minutos em ~30 min** (`transcrever.py:109-113`).
   O `doctor` precisa distinguir "`transcrever` habilitada com faster-whisper" de "habilitada só com
   whisper de referência", senão a capacidade parece ok e o comando trava na prática.
5. **Glossário de jargão/nome próprio é dado de marca**: hoje é um comentário ("Claude Code",
   "software house", "MCP" em `transcrever.py:44`) e uma revisão manual. No núcleo deve virar lista na
   Alma; o uso dela como `initial_prompt`/`hotwords` é NÃO DOCUMENTADO na fonte (não existe hoje).
6. **Dois consumidores divergentes**: `analisar_reel.py:119-130` usa `faster-whisper` sem idioma,
   com `vad_filter`, sem `condition_on_previous_text=False` e com esquema de saída diferente
   (`palavra/inicio/fim` em vez de `w/t0/t1`). A capacidade única tem que absorver os dois esquemas
   ou os consumidores migram juntos.
7. **Caminhos e nomes de arquivo fixos** (`fonte.m4a`, `corte9x16.mp4`, `transcricao.json`,
   `transcricao_corte.json`, `roteiro.txt`, `alignment.json`) e diretórios `fontes/`/`videos/`
   (`Instragram-Videos/pipeline/lib.py:5-6`) são convenção da instalação atual; no núcleo, entrada
   e saída devem ser caminhos passados pela peça (ver `CONTRATO-peca.md`).
8. **Sem pino de versão**: o projeto não tem `requirements.txt`/`pyproject.toml`. Versões abaixo são
   as instaladas na máquina, não um contrato.
9. Heurística de quebra de linha por pontuação (`transcrever.py:191`) depende do whisper pontuar;
   `momentos.py` também depende disso (ver `corte-e-reenquadramento.md`, erro "transcrição sem
   pontuação").

## Fonte

- `Instragram-Videos/pipeline/transcrever.py:1-219` (lido inteiro).
- `Instragram-Videos/pipeline/analisar_reel.py:110-135`.
- `Instragram-Videos/pipeline/lib.py:5-6`, `:280-291` (`ler_json`, `escrever_json`, `ffprobe`).
- `Instragram-Videos/.claude/skills/gerar-reel-corte/SKILL.md:74-99`.
- `Instragram-Videos/.claude/commands/new-video-youtube-cut.md:58-60`, `:82-91`.
- `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:1-15`.
- `Instragram-Videos/.claude/hooks/corte/stop-gate.sh`.
- `Instragram-Videos/CLAUDE.md:155-160`.
- Artefatos: `Instragram-Videos/fontes/*/transcricao.json`, `Instragram-Videos/videos/yt-*/transcricao_corte.json`.
- Ambiente medido em 2026-09-24 (`pip show`, `which`): faster-whisper 1.2.1, ctranslate2 4.8.2,
  openai-whisper 20250625, torch 2.10.0, av 18.1.0, Python 3.11.7, ffmpeg 8.0.1.
- Testes: nenhum teste cobre `transcrever.py` (busca em `Instragram-Videos/tests/`);
  `Instragram-Videos/tests/test_analisar_reel.py:53-63` injeta um `transcrever_falso`.
- `git log` de `Instragram-Videos`: um único commit (`cc1e39d Initial commit`); todo o código está
  não rastreado — sem histórico de decisões além dos comentários no código.
