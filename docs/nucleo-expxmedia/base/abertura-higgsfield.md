# Abertura gerada com Higgsfield (capacidades `video_ia` e `rosto_ia`)

Fonte extraída: `Instragram-Videos/pipeline/abertura.py`, config `Instragram-Videos/aberturas.json`,
regra `Instragram-Videos/.claude/rules/montagem/abertura.md`. É **teste configurável**, não padrão do
formato (`Instragram-Videos/CLAUDE.md:114-131`). A composição na tela está em `montagem-reel-ffmpeg.md`.

## Contrato de entrada

- `python3 pipeline/abertura.py videos/<slug> [--prompt ...] [--duracao s] [--com-abertura|--sem-abertura]
  [--tipo objeto|thulio] [--refazer] [--so-montar]` (`Instragram-Videos/pipeline/abertura.py:21-28,360-374`).
  Roda **depois** do `stitch.py` e **antes** do `compose.py` (`Instragram-Videos/.claude/rules/montagem/abertura.md:248-257`).
- `abertura.txt` (ou `--prompt`): prompt **em inglês**, uma ou duas frases, sujeito + luz + o que acontece;
  algo que chame atenção e possa se desmontar; sem texto, número, logo, interface nem gente (no tipo
  `objeto`); não escrever a transformação (`Instragram-Videos/.claude/rules/montagem/abertura.md:231-246`;
  `Instragram-Videos/pipeline/abertura.py:431-435`). Escrito pelo roteirista a partir do gancho
  (`Instragram-Videos/.claude/agents/roteirista.md:77-98`).
- `strip.png` → quadro de destino `abertura_destino.png` = recorte 1080×1920 do topo da tira (o que o
  conteúdo mostra quando a abertura sai); fallback: 1º frame de `scroll.mp4`/`<slug>.mp4`
  (`Instragram-Videos/pipeline/abertura.py:80-102`).
- `aberturas.json` na raiz (`Instragram-Videos/aberturas.json:1-67`):
  - `ativo` (freio que ninguém vence) — `true` (`:3`); `formatos` (padrão de quem não decidiu) — só `repo: true` (`:4-9`);
  - `tipo_padrao: objeto` (`:10`); `modo: por-cima` (único implementado) (`:11`); `duracao_na_tela: 2.5` (`:12`);
    `audio: mudo` (`:13`); `transformar_no_conteudo: true` (`:15`); `teto_creditos_dia: 80` (`:16`);
  - `tipos.objeto`: `seedance_2_0`, `parametros.mode std`, `duracao_gerada 4`, `9:16`, `720p`,
    `creditos_por_abertura 19`, `estilo` e `transformacao` (prompts fixos) (`:18-30`);
  - `tipos.thulio`: igual + `retrato` (`text2image_soul_v2`, `soul: ../Instagram-Carrosseis/galeria/retratos/soul/soul.json`,
    `9:16`, `2k`, `estilo` de enquadramento) (`:31-51`).
- Quem decide **se** leva e **qual tipo** é quem chama (plano da central → `--com-abertura`/`--sem-abertura`/`--tipo`);
  sem decisão, vale `formatos`/`tipo_padrao` (`Instragram-Videos/pipeline/abertura.py:388-409`;
  `Instragram-Videos/.claude/rules/montagem/abertura.md:153-169`).
- CLI `higgsfield` instalado (`npm i -g @higgsfield/cli`) e autenticado (`higgsfield auth login`)
  (`Instragram-Videos/pipeline/abertura.py:109-116`). Soul treinado com `status == "completed"`
  (`Instragram-Videos/pipeline/abertura.py:164-171`).

## Contrato de saída

- `abertura_bruta.mp4` (clipe do provedor), `abertura.mp4` (padronizado 1080×1920, 30fps, `yuv420p`, sem
  áudio, `libx264 slow crf 18`, `+faststart`) (`Instragram-Videos/pipeline/abertura.py:274-308`).
- `abertura_thulio.png` no tipo com gente — o revisor abre para confirmar o rosto
  (`Instragram-Videos/.claude/rules/montagem/abertura.md:62-63`).
- `abertura.json` (marcador de coorte) (`Instragram-Videos/pipeline/abertura.py:456-469`):
  `metodo, modo, tipo, modelo, retrato{soul,modelo,prompt}|null, duracao, duracao_gerada, parametros,
  janela{clipe_s,encaixe_s,de,ate}, rosto{topo,base,quadros}|null, transformou_no_conteudo, creditos, job,
  prompt, gerado_em, pedido_por, montado_em:null`. `montado_em` só é preenchido pela montagem
  (`Instragram-Videos/pipeline/compose.py:305-309`). Exemplo real: `Instragram-Videos/videos/appwrite-appwrite/abertura.json`
  (janela 0,8–3,3s de um clipe de 4,064s, encaixe 3,2s, rosto y 366–987).
- A URL assinada do resultado **nunca** vai a disco nem a log; do job guarda-se só o id
  (`Instragram-Videos/pipeline/abertura.py:222-225`).

## Limites e cotas

- Chamada de vídeo: `higgsfield generate create <modelo> --prompt <prompt + estilo + transformacao>
  --aspect_ratio 9:16 --duration 4 [--resolution 720p] [--<parametros>] [--start-image] [--end-image]
  --wait --wait-timeout 20m --json` (`Instragram-Videos/pipeline/abertura.py:190-218`). `parametros` é
  passagem direta para o schema do modelo — trocar de modelo é mexer no config, não no código
  (`Instragram-Videos/pipeline/abertura.py:206-210`).
- Chamada de retrato (Soul): `generate create text2image_soul_v2 --prompt <estilo + prompt>[:900]
  --custom-reference-id <soul> --aspect-ratio 9:16 --quality 2k --wait --wait-timeout 15m --json`
  (`Instragram-Videos/pipeline/abertura.py:172-177`). **Nenhum modelo de vídeo da Higgsfield aceita Soul
  direto** (conferido em 20/09/2026) — por isso 2 passos: Soul faz a imagem → vira `--start-image`
  (`Instragram-Videos/pipeline/abertura.py:154-157`; `Instragram-Videos/.claude/rules/montagem/abertura.md:46-51`).
- Timeout do subprocesso 1800s; download 300s (`Instragram-Videos/pipeline/abertura.py:106,182,227`).
- Duração na tela: 1–5s aceita; não pode exceder `duracao_gerada` (`Instragram-Videos/pipeline/abertura.py:417-421`).
  O modelo não gera abaixo de 4s (`Instragram-Videos/aberturas.json:59`).
- **Janela pelo encaixe, não pelo fim do arquivo** (`instante_do_encaixe`, `Instragram-Videos/pipeline/abertura.py:235-271`):
  quadros em miniatura 96×171 a 10 fps, diferença média em cinza contra o destino; se `teto − piso < 3,0`
  não há encaixe; limiar = `piso + 15% (teto − piso)`; mínimo 6 quadros; janela termina no encaixe + 0,1s
  e começa `dur` antes (`Instragram-Videos/pipeline/abertura.py:284-300`). Medição: morph fechou em 2,60s
  num clipe de 4,09s (`Instragram-Videos/.claude/rules/montagem/abertura.md:141-150`).
- **Faixa do rosto** (`faixa_do_rosto`, `Instragram-Videos/pipeline/abertura.py:311-357`): OpenCV Haar
  `haarcascade_frontalface_default`, amostra ~a cada `fps/4` quadros (~0,25s), frame reduzido a 640 de
  largura, `detectMultiScale(1.1, 5, minSize=60×60)`, maior rosto do quadro, **união** do topo mais alto e
  base mais baixa no clipe inteiro. Medida **depois** de padronizar. Só roda em tipo com `retrato`.
- Custos: estimativa `creditos_por_abertura` 19 (`Instragram-Videos/aberturas.json:27,40`); medido no saldo:
  `seedance_2_0 std 720p 4s` = **25,5** com `end_image` só e **18,12** com start+end (incluindo 0,12 do Soul);
  cotação dizia 18 (`Instragram-Videos/aberturas.json:63`; `Instragram-Videos/.claude/rules/montagem/abertura.md:204-210`).
  Cotações: kling3_0 pro 7, std 6, seedance_2_0 18, seedance_2_5 28, gemini_omni 12
  (`Instragram-Videos/.claude/rules/montagem/abertura.md:204-210`). Soul: ~0,12 crédito
  (`Instragram-Videos/pipeline/abertura.py:173`).
- Teto diário: soma `creditos` dos `videos/*/abertura.json` com `gerado_em` de hoje; marcador apagado devolve o
  crédito ao teto (`Instragram-Videos/pipeline/abertura.py:66-77,191-195`).
- Modelos com `end_image`: `seedance_2_0` e `seedance_2_5` funcionam; `kling3_0` declara e **não funciona**;
  `gemini_omni` não tem (`Instragram-Videos/aberturas.json:62`).

## Erros conhecidos e tratamento

| Situação | Tratamento | Referência |
|---|---|---|
| CLI ausente | sai com instrução de instalação | `Instragram-Videos/pipeline/abertura.py:110-111` |
| "Not authenticated" / "Session expired" | sai: `higgsfield auth login` | `Instragram-Videos/pipeline/abertura.py:115-116` |
| Erro do CLI em JSON multilinha | junta tudo numa linha, **apaga URLs** (`<url-omitida>`), corta em 700 chars | `Instragram-Videos/pipeline/abertura.py:117-124` |
| Saída não-JSON | sai | `Instragram-Videos/pipeline/abertura.py:125-128` |
| Forma da resposta muda entre versões do CLI | varredura do JSON atrás da 1ª URL com sufixo de mídia (limite 5000 nós); resposta pode ser lista com 1 job | `Instragram-Videos/pipeline/abertura.py:131-148,224-225` |
| Job sem URL de vídeo | sai | `Instragram-Videos/pipeline/abertura.py:219-221` |
| Falha no download | sai com o **tipo** da exceção (sem URL) | `Instragram-Videos/pipeline/abertura.py:184-185,229-230` |
| `kling3_0` com `end_image` | `status: failed` sem mensagem em 5 jobs isolando variáveis; Higgsfield estorna | `Instragram-Videos/.claude/rules/montagem/abertura.md:183-202` |
| `status: ip_detected` (moderação barrou start_image de rosto em close) | refazer; se insistir, afastar o enquadramento | `Instragram-Videos/.claude/rules/montagem/abertura.md:73` |
| Rosto ilegível (plano aberto, rosto ~4% da altura) | `retrato.estilo` exige plano médio, rosto no terço superior | `Instragram-Videos/aberturas.json:46-47`; `Instragram-Videos/.claude/rules/montagem/abertura.md:69-70,115-120` |
| Modelo despedaça a pessoa / troca roupa | `transformacao` do tipo manda manter a pessoa intacta até o último instante | `Instragram-Videos/aberturas.json:50`; `Instragram-Videos/.claude/rules/montagem/abertura.md:71-72` |
| Clipe ignora o frame final | encaixe `None` → usa o fim do arquivo | `Instragram-Videos/pipeline/abertura.py:248-249,294-295` |
| Sem OpenCV | AVISO; cartão na posição padrão | `Instragram-Videos/pipeline/abertura.py:326-330` |
| Tipo com gente sem rosto detectado | AVISO "confira o frame antes de publicar" | `Instragram-Videos/pipeline/abertura.py:453-455` |
| Teto diário estourado | sai; opções `--sem-abertura` ou subir o teto | `Instragram-Videos/pipeline/abertura.py:193-195` |
| Soul ausente / não pronto | sai; ele é treinado na central | `Instragram-Videos/pipeline/abertura.py:166-171` |
| Já existe abertura | no-op; `--refazer` gera outra; `--so-montar` repadroniza sem custo | `Instragram-Videos/pipeline/abertura.py:412-415,425-427` |
| Mandar o cartão/texto ao modelo | proibido: gerador de vídeo devolve letra embaralhada | `Instragram-Videos/pipeline/abertura.py:87-89` |

## Riscos para a nossa implementação

Acoplamentos de marca:
- Tipo chamado `thulio`, função `quadro_do_thulio`, mensagens "o Soul do Thulio"
  (`Instragram-Videos/pipeline/abertura.py:151-187`; `Instragram-Videos/aberturas.json:31-51`) → tipo
  genérico "porta_voz" com id vindo de `alma.porta_vozes[].rosto_ia.id`.
- Caminho do Soul em outro projeto: `../Instagram-Carrosseis/galeria/retratos/soul/soul.json`
  (`Instragram-Videos/aberturas.json:43`) → Alma. Revisor compara rosto com `../Instagram-Carrosseis/galeria/retratos/`
  (`Instragram-Videos/.claude/agents/revisor-video.md:70-71`) → `alma.porta_vozes[].retratos`.
- Regra "pessoa na nossa arte é sempre o Thulio" (`Instragram-Videos/.claude/rules/montagem/abertura.md:57-60`) →
  "só porta-vozes cadastrados".
- `MARCADORES` → formatos do pack (`repo/llm/release/corte`) (`Instragram-Videos/pipeline/abertura.py:46`);
  `formatos` no config também.
- Prompts `estilo`/`transformacao` (`Instragram-Videos/aberturas.json:28-29,49-50`) são estética de marca
  ("photoreal, cinematic, very high contrast, dramatic hard lighting") → template/Alma, com as **travas
  negativas** (sem texto, sem logo, sem UI, sem outras pessoas) no núcleo.
- Conta Higgsfield via login do CLI (não há chave no `.env`) — condiz com o contrato ("login do CLI").

O que derruba a qualidade se extraído de forma ingênua:
1. **Colar a abertura antes do vídeo** → silêncio no começo e vídeo mais longo (decisão revertida).
2. **Cortar "os últimos N segundos"** às cegas → tempo morto dentro da abertura e o impacto jogado fora.
3. **Não mandar o quadro do conteúdo como `end_image`** → corte seco em vez de transformação.
4. **Descrever aparência da pessoa no prompt** → briga com o Soul e afasta a semelhança.
5. **Posição fixa do cartão** com rosto → tapa os olhos (3 alturas fixas falharam).
6. **Medir o rosto num quadro só** (não na união do clipe) → o cartão fixo encosta no rosto quando ele se mexe.
7. **Confiar na cotação** para o teto diário → custo real até 42% maior (25,5 vs 18).
8. **Logar a resposta do CLI** → vaza URL assinada (credencial de leitura).
9. **Clipe com áudio** → mexe no loudness/pico que o gate cobra.
10. Escrever `montado_em` na geração → coorte mente quando a montagem falha.

Inconsistências na fonte (decidir antes de extrair):
- `creditos_por_abertura 19` vs medido 25,5/18,12 (`Instragram-Videos/aberturas.json:27,63`).
- Encaixe "~2,9s" no docstring (`Instragram-Videos/pipeline/abertura.py:239`) vs "2,60s" na regra
  (`Instragram-Videos/.claude/rules/montagem/abertura.md:142`) vs 3,2s no artefato do appwrite.
- `performance.md` cita `aberturas.json > tipos.thulio.cartao_y` e cartão movido para y=1040
  (`Instragram-Videos/.claude/rules/performance.md:412-414`) — campo que **não existe** mais; hoje a posição é medida.
- `abertura.txt` do appwrite descreve "the man's face" (`Instragram-Videos/videos/appwrite-appwrite/abertura.txt`),
  em tensão com "nada sobre a aparência" da regra — no tipo com gente o prompt fala da situação e do enquadramento.

## Fonte

- `Instragram-Videos/pipeline/abertura.py` (1–476)
- `Instragram-Videos/aberturas.json` (1–67)
- `Instragram-Videos/.claude/rules/montagem/abertura.md` (1–262)
- `Instragram-Videos/pipeline/compose.py` (31–110, 186–191, 301–309)
- `Instragram-Videos/.claude/agents/roteirista.md` (77–98), `montagem.md` (34–56), `revisor-video.md` (63–90)
- `Instragram-Videos/.claude/rules/central.md` (21–31), `performance.md` (394, 403–423)
- `Instragram-Videos/videos/appwrite-appwrite/abertura.json`, `abertura.txt` (artefatos reais)
- Testes: nenhum teste cobre `abertura.py`.
