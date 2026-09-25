# Corte de vídeo longo em reel (fonte, escolha do trecho, reenquadramento 9:16, montagem)

Capacidade do núcleo: `editar_video` (provedor `ffmpeg`), com detecção de rosto por OpenCV e fonte
por `yt-dlp`. Consome `transcrever` (ver `transcrever-whisper.md`) e `banco_imagens` (ver
`banco-imagens-pexels.md`). Origem: `Instragram-Videos/pipeline/pick_cut.py` (parte genérica),
`momentos.py`, `cut.py`, `compose_cut.py`, `lib.py`, o comando `/new-video-youtube-cut`, a skill
`gerar-reel-corte`, os agentes `corte`/`montagem`, as regras `curadoria-corte`, `montagem/ffmpeg`
e `formato-entrega`.

Sequência real (`Instragram-Videos/.claude/skills/gerar-reel-corte/SKILL.md:33-54`):
`pick_cut.py` → `transcrever.py fontes/<id>` → `momentos.py` (ou `--mapa`) → `cut.py` →
`transcrever.py videos/<slug> --alinhar` → `broll.py` → `gancho.txt` → `captions.py --sem-cta
--offset 0` → `compose_cut.py` → `verify.py --sem-cta`.

## Contrato de entrada

### Fonte (`pick_cut.py`, só a parte genérica)

- `--video <url ou id>` | automático sobre `--canal` (padrão fixo, ver Riscos) | `--n 20` vídeos |
  `--listar` (`Instragram-Videos/pipeline/pick_cut.py:104-109`).
- Extração do id a partir de URL: marcas `v=`, `youtu.be/`, `/shorts/`, `/live/`
  (`Instragram-Videos/pipeline/pick_cut.py:115-117`).
- Listagem: `yt-dlp --flat-playlist -J --playlist-end N <canal>/videos` (`:69-74`); metadados:
  `yt-dlp -J --skip-download` (`:77-81`); áudio: `yt-dlp -f "bestaudio[ext=m4a]/bestaudio"
  --no-playlist` (`:181-182`). Timeouts 600 s (padrão `ytdlp`, `:31`) e 1800 s no download (`:182`).
- Elegibilidade (`Instragram-Videos/pipeline/pick_cut.py:84-101`): recusa ao vivo/agendado (`:88-89`);
  recusa duração < `CORTE_FONTE_MIN_S` = 180 s (`:90-92`, `Instragram-Videos/pipeline/lib.py:139`);
  recusa vídeo "esgotado" quando o não usado < `CORTE_MAX_S` = 180 s (`:95-97`, `lib.py:137`).
- Fila: vídeo com cortes vai para o fim; com ≥ `CORTES_ANTES_DE_REBAIXAR` = 3 cortes cai mais
  (`Instragram-Videos/pipeline/pick_cut.py:28`, `:136-137`). Desempate, nunca veto.
- Com `--video`, barreiras viram aviso, **exceto faixa esgotada** (`:121-126`).
- Memória **por faixa de tempo**, lida de todos os `videos/*/corte.json` (inclusive cada trecho de
  cortes multi-trecho) (`Instragram-Videos/pipeline/pick_cut.py:35-58`).

### Escolha do trecho (`momentos.py`)

- Entrada: `fontes/<id>/transcricao.json` e, se houver, `fonte.json` (`faixas_ja_usadas`)
  (`Instragram-Videos/pipeline/momentos.py:84-88`).
- Parâmetros: `--n 8`, `--min` = `CORTE_MIN_S` (52 s), `--max 72.0`, `--mapa`
  (`Instragram-Videos/pipeline/momentos.py:71-82`). Obs.: a docstring diz `--max 62`
  (`:14`) e a regra diz janela "52–62s" (`Instragram-Videos/.claude/rules/curadoria-corte.md:62`) —
  o código usa 72.

### Recorte (`cut.py`)

- `fontes/<id>` + `--inicio/--fim` **ou** `--plano trechos.json` (`[{inicio, fim, por_que}]`), e
  válvulas `--sem-rosto`, `--fundo-desfocado`, `--sem-split`, `--slug`
  (`Instragram-Videos/pipeline/cut.py:395-406`).
- Validações antes de baixar (`Instragram-Videos/pipeline/cut.py:411-440`):
  - soma dos trechos em `[CORTE_MIN_S − 0,51 ; CORTE_MAX_S + 0,51]` = [51,49 ; 180,51] s (`:421-424`);
  - cada trecho ≥ 4 s (`:426-428`); sem sobreposição, ordenado por início (`:419`, `:429-430`);
  - sobreposição com faixa já usada > `CORTE_SOBREPOSICAO_MAX` = 0,20 reprova (`:431-437`,
    `Instragram-Videos/pipeline/lib.py:140`);
  - aviso se total > `CORTE_ALVO_S` × 1,25 = 75 s (`:438-440`, `lib.py:136`).

### Montagem (`compose_cut.py`)

- `videos/<slug>/` com `corte9x16.mp4`, `legendas.json`, `caps.txt` (de `captions.py`), `brolls.json`
  (opcional com aviso) e `gancho.txt` (obrigatório salvo `--sem-gancho`)
  (`Instragram-Videos/pipeline/compose_cut.py:17-26`, `:69-74`).

## Contrato de saída

- `fontes/<id>/fonte.json` (`video_id, url, titulo, canal, duracao_s, publicado_em, views, largura,
  altura, faixas_ja_usadas, baixado_em, motivos_curadoria`) + `fonte.m4a`
  (`Instragram-Videos/pipeline/pick_cut.py:162-186`). Cache reaproveitado se > 10000 bytes (`:177`).
- `fontes/<id>/candidatos.json` = `{gerados, candidatos:[{inicio, fim, duracao, palavras, pontos,
  silencio_frac, ja_usado_frac, notas, texto}]}` sem sobreposição
  (`Instragram-Videos/pipeline/momentos.py:184-204`). `--mapa` imprime segmentos com instante e um
  exemplo de plano (`:97-111`).
- `videos/<slug>/` com slug `yt-<id>-t<mmss>` (`Instragram-Videos/pipeline/cut.py:444`):
  `pecas/NN_src.mp4` (trecho baixado), `pecas/NN.mp4` (reenquadrado), `corte9x16.mp4` (concat
  `-c copy +faststart`, `:481-490`) e `corte.json` com `video_id, url, titulo, canal, trechos[{inicio,
  fim, por_que, duracao, enquadramento, screencast[[t0,t1,lado,largura_tela,h_topo]],
  deslocamento_px}], inicio, fim, duracao, montagem, cta: null` (`:473-500`).
- Rótulos de enquadramento: `fundo desfocado` | `split screencast` (cobertura > 0,9) | `misto (fala +
  screencast)` | `rosto` (deslocamento > 1 px) | `central fixo` (`Instragram-Videos/pipeline/cut.py:474-477`).
- `videos/<slug>/<slug>.mp4` final (`Instragram-Videos/pipeline/compose_cut.py:134`), `gancho.png`
  (`:102`). Formato: 1080×1920, 30 fps (`Instragram-Videos/pipeline/lib.py:9`), H.264 + AAC 192k
  48 kHz, `+faststart`, −14 LUFS ±1, pico ≤ −1,0 dBFS, safe area inferior 420 px
  (`Instragram-Videos/.claude/rules/formato-entrega.md:5-14`, `lib.py:10-12`).
- Gate final `verify.py --sem-cta`: duração 50–185 s quando há `corte.json`
  (`Instragram-Videos/pipeline/verify.py:73-75`, `CORTE_DUR_MAX_VIDEO` = 185 em `lib.py:138`), aviso
  acima de 75 s (`verify.py:76-78`), cauda ≤ 0,80 s após a última legenda (`verify.py:135-141`).

### Reenquadramento — algoritmo e números

Detecção de rosto (`Instragram-Videos/pipeline/cut.py:97-120`):
- Haar cascade `haarcascade_frontalface_default.xml` (`:100`); amostragem `AMOSTRAS_POR_S` = 4
  quadros/s (`:33`, `:103`); quadro reduzido a 640 px de largura, cinza (`:104`, `:112`);
  `detectMultiScale(g, 1.15, 6, minSize=(24, 24))` (`:113`); fica o maior rosto (`:115`).
- Crop 9:16: `crop_w = min(src_w, src_h·1080/1920)` par, `crop_h` idem (`:456-457`).

Caminho do rosto (`Instragram-Videos/pipeline/cut.py:297-343`):
- menos de 4 amostras fora de screencast → crop central fixo (`:300-301`);
- mediana móvel com janela `max(3, int(4 × SUAVE_S) | 1)` = 7 amostras, `SUAVE_S` = 1,5 s (`:37`, `:305-309`);
- suavização exponencial com fator 0,25 (`:310-313`);
- **zona morta** `ZONA_MORTA_FRAC` = 0,12 da largura do crop (`:34`, `:315-319`);
- simplificação Ramer-Douglas-Peucker com `EPS_PX` = 14 px (`:35`, `:322-333`) e teto
  `MAX_PONTOS` = 24 (`:36`, `:339-341`);
- vira expressão por partes `if(lt(t,..),..)` no `x` do filtro `crop` (`:346-353`, `:368`).

Screencast → tela em cima, rosto embaixo (`Instragram-Videos/pipeline/cut.py:39-57`, `:123-174`):
- rosto num painel se centro fora de [0,30 ; 0,70]·W **e** largura < 0,26·W (`:54-55`, `:125-127`);
  números medidos no canal (`:41-44`): fala 0,398–0,590 / 0,284–0,405; screencast 0,800–0,921 /
  0,144–0,236;
- buraco > 3/4 s (3 amostras) separa passagens (`:130`); passagem < `SCREENCAST_MIN_S` = 1,5 s
  descartada (`:56`, `:142`); folga `SCREENCAST_PAD_S` = 0,3 s (`:57`, `:141`);
- buraco < 2,0 s entre passagens é fundido (`:159-166`); cobertura ≥ 0,8 → a peça inteira vira
  screencast (`:170-173`).
- Fronteira tela/painel **medida** (`:177-213`): 5 quadros, Sobel horizontal `ksize=3`, estimativa
  `fx ∓ 0,70·fw`, janela ± 0,08·W, pico aceito se ≥ 2,0 × mediana; senão fica a estimativa. Medido:
  pico em 1399 px de 1920, 25x a mediana (`Instragram-Videos/.claude/rules/curadoria-corte.md:339-341`).
- Faixa útil vertical (tira tarja preta) (`:216-256`): 5 quadros, limiar 0,35 × percentil 95 do
  brilho por linha; se a faixa < 0,40 × altura devolve altura inteira (tema escuro); folga 8 px.
- Geometria (`:259-293`): `corte_x` preso a [0,45·W ; W − 1,05·fw] (webcam à direita) ou
  [1,05·fw ; 0,55·W] (esquerda); `h_topo` = altura proporcional presa a [460 ; 1240] px; rosto a
  35 % do topo do painel de baixo (`:287-289`).

Render de uma peça (`Instragram-Videos/pipeline/cut.py:357-391`):
- `--fundo-desfocado`: fundo `scale+crop 1080×1920, gblur sigma=40` e 16:9 inteiro centrado (`:359-364`);
- overlays de screencast com `enable='between(t,t0,t1)'` (`:372-381`);
- áudio com fade de 12 ms nas duas pontas para a emenda não estalar (`:386-387`);
- `libx264 -preset slow -crf 18`, AAC 192k 48 kHz (`:388-389`).
- Download do trecho: `yt-dlp -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b"
  --download-sections "*ini-fim" --force-keyframes-at-cuts --no-playlist`, timeout 1800 s
  (`Instragram-Videos/pipeline/cut.py:81-83`); cache se > 10000 bytes (`:77-79`).

### Montagem final (`compose_cut.py`)

- Duração = `min(legendas.duracao, duração do corte)` e fecha 0,25 s após o último cartão,
  arredondado ao quadro (`Instragram-Videos/pipeline/compose_cut.py:29-35`).
- B-roll: `setpts=PTS-STARTPTS+t/TB` + `overlay enable=between(t, t, t+d)` (`:51-57`).
- Legenda: concat demuxer de PNGs (`caps.txt`) em `overlay` (`:47`, `:58-59`) — build sem libass
  (`Instragram-Videos/.claude/rules/montagem/ffmpeg.md:3-7`).
- **Gancho fixo no topo** (padrão desde 19/09/2026) (`:62-107`): até 3 linhas (`:81-83`); fonte
  `Arial Black` do macOS (`:77`); tamanho de 84 a 42 px em passo 2 até caber em `W − 180` (`:84-87`);
  aviso abaixo de 56 px (`:88-90`); entrelinha 1,22 (`:91`); caixa +80 px de largura e +50 px de altura
  (`:92-93`), raio 26 (`:98`); amarelo `(255,212,0)` com texto preto (`:98-101`); faixa vertical entre
  `TOPO_UI` = 250 e `FAIXA_FIM` = 640 px (`:78-79`, `:97`).
- Áudio: `adelay` se `offset_audio` ≠ 0, `apad` (`:109-110`); vídeo `libx264 slow crf 19 yuv420p 30 fps`,
  AAC 192k (`:113-117`).
- Loudnorm em duas passagens, `I=-14 TP=-1.5 LRA=11`, segunda com `measured_*` e `linear=true`,
  vídeo `-c:v copy` (`:121-139`; `Instragram-Videos/.claude/rules/montagem/ffmpeg.md:22-29`).
- Pós-ajuste de pico: mede `ebur128=peak=true` no arquivo final; se pico > `PICO_MAX` = −1,0 dBFS,
  atenua até `PICO_MIRA` = −1,3, **só se** o loudness previsto ficar em −14 ± 1 LUFS; senão avisa e não
  mexe (`:142-183`). Motivo medido: loudnorm pedindo TP −1,5 entregou −0,5 dBFS após AAC (aula
  `3FsfiuvJrfs`, `:145-148`).

## Limites e cotas

| Item | Valor | Fonte |
|---|---|---|
| Fonte mínima | 180 s | `Instragram-Videos/pipeline/lib.py:139` |
| Corte: piso / alvo / teto (soma dos trechos) | 52 / 60 / 180 s | `lib.py:135-137` |
| Teto do `.mp4` final | 185 s | `lib.py:138` |
| Aviso de corte longo | > 75 s | `cut.py:438`, `verify.py:76` |
| Piso do gate de entrega | 50 s | `verify.py:75`; motivo do piso 52 em `lib.py:131-134` |
| Trecho mínimo | 4 s | `cut.py:426` |
| Sobreposição máxima com faixa usada | 20 % | `lib.py:140` |
| Janela de ranqueamento `momentos.py` | 52–72 s | `momentos.py:80-81` |
| Início de frase | pontuação `. ? !` ou pausa ≥ 0,6 s | `momentos.py:69`, `:116-120` |
| Palavras dos "3 primeiros segundos" | 12 | `momentos.py:58` |
| Cauda muda máxima | 0,80 s | `verify.py:141` |
| Rosto detectado < 15 % | só aviso se não há screencast | `cut.py:467-469` |
| yt-dlp | resolução ≤ 1080 p; 3 tentativas, espera 4·k s | `cut.py:69`, `:81`, `:91` |

Pontuação do `momentos.py` (desempate, **não** veredito — `:11-12`, `:213`), `Instragram-Videos/pipeline/momentos.py:147-183`:
ANÁFORA −3; MULETA −2; FORA_DO_REEL nas 12 primeiras palavras −3; falsa largada (1ª palavra > 3
letras repetida nas 5 primeiras) −1; GANCHO +2; número nas 12 primeiras +3 (senão, no trecho, +1);
HESITAÇÃO nas 12 primeiras −1,5; VAGO nas 12 primeiras −1,5; densidade `+2·(1 − min(silêncio/0,25, 1))`,
nota se silêncio > 20 %; faixa já usada `−5·fração`; duração < min + 4 s −0,5. Listas de palavras
em `:23-68` (todas em português).

Uso real (16 cortes em `Instragram-Videos/videos/yt-*/corte.json`, medido em 2026-09-24):
`fundo desfocado` em 10; `split screencast`/`misto` em 5; `rosto` em 1 trecho; `central fixo` em 1
trecho. B-roll: **0 inserções em todos os 16** (15 com `brolls.json` vazio, 1 sem `brolls.json`).
Gancho fixo em 6.

## Erros conhecidos e tratamento

| Erro | Tratamento | Fonte |
|---|---|---|
| yt-dlp 403 | retentativa ×3 com espera; se persistir, `pip install -U yt-dlp`; trocar `player_client` "só troca o erro de lugar" | `Instragram-Videos/pipeline/cut.py:69-93`; `Instragram-Videos/.claude/skills/gerar-reel-corte/SKILL.md:68-72`; `Instragram-Videos/CLAUDE.md:155-156` |
| Falha ao listar canal / metadados / áudio | `sys.exit` com os últimos 600/800 caracteres do stderr | `pick_cut.py:71-72`, `:79-80`, `:183-184` |
| Nenhum vídeo elegível | `sys.exit` sugerindo `--n` maior ou `--video` | `pick_cut.py:147-149` |
| Nenhum trecho fecha em fim de frase | `sys.exit` (transcrição sem pontuação ou sem bloco contínuo) | `momentos.py:189-192` |
| Transcrição sem palavras | `sys.exit` | `momentos.py:89-90` |
| Plano fora da janela / trecho < 4 s / sobreposição / faixa usada | `sys.exit` antes de baixar | `cut.py:421-437` |
| Limiar de screencast tirado de estimativa (0,15, só tamanho) não pegou nenhuma passagem real | trocado por posição **e** tamanho, medidos | `cut.py:51-53`; `Instragram-Videos/.claude/agents/corte.md:98-100` |
| Fronteira tela/painel derivada do rosto errou 400 px | passou a ser medida por gradiente | `cut.py:180-183`; `curadoria-corte.md:334-342` |
| Screencast piscando entre dois splits (buracos de detecção) | fusão de buracos < 2 s e extensão com cobertura ≥ 80 % | `cut.py:155-173` |
| Tela escura (editor) sem faixa clara | devolve altura inteira | `cut.py:223-225`, `:253-254` |
| Close ou screencast que o crop não conserta | válvula manual `--fundo-desfocado` | `curadoria-corte.md:300-309` |
| Estalo na emenda de trechos | afade 12 ms | `cut.py:386-387` |
| Erro no ffmpeg (reenquadrar/juntar/compor/normalizar) | `sys.exit` com a cauda do stderr | `cut.py:390-391`, `:489-490`; `compose_cut.py:118-119`, `:138-139` |
| `gancho.txt` ausente | recusa montar (válvula `--sem-gancho`) | `compose_cut.py:71-74` |
| Gancho com > 3 linhas | recusa | `compose_cut.py:81-83` |
| Pico acima de −1 dBFS após AAC | atenuação plana se couber no ±1 LUFS; senão aviso, sem atenuar | `compose_cut.py:162-183` |
| `crop` com `eval=frame` no ffmpeg 8 | proibido (aborta) | `Instragram-Videos/.claude/rules/montagem/ffmpeg.md:9-13` |
| Concat com caminho absoluto + `cwd` | todas as entradas relativas | `ffmpeg.md:15-20` |
| Abertura com anáfora, muleta, falsa largada, "vídeo anterior" | penalidade em `momentos.py`; em plano multi-trecho, **leitura manual** das 10 primeiras palavras | `SKILL.md:186-192` |

## Riscos para a nossa implementação

1. **Acoplamento de marca cravado no código** — precisa virar Alma/.env/parâmetro:
   - canal padrão `https://www.youtube.com/@softwarehouse.exponencial` (`Instragram-Videos/pipeline/pick_cut.py:26`) → `alma.canais[canal=youtube].url`;
   - exemplo de plano com "software house" (`momentos.py:104-106`);
   - fonte `/System/Library/Fonts/Supplemental/Arial Black.ttf` (só macOS) e cores do gancho
     amarelo/preto (`compose_cut.py:77`, `:98-101`) → tipografia e papéis de cor da Alma/template;
   - `TOPO_UI` 250 / `FAIXA_FIM` 640 / safe area 420 são geometria do **Instagram** (`compose_cut.py:78-79`,
     `lib.py:10`) → dado do destino/pack, não do núcleo;
   - slug `yt-<id>-t<mmss>`, `fontes/`, `videos/`, nomes de arquivo fixos (`cut.py:444`, `lib.py:5-6`);
   - `corte.json` `cta: null` e `--sem-cta` são decisão do formato do Thulio (`curadoria-corte.md:206-225`), não do núcleo.
2. **Heurísticas de abertura são calibradas numa conta e num idioma.** As regex (`momentos.py:23-68`)
   são português, e os pesos (+3 número, −3 anáfora…) vêm de 5 medições de uma única conta
   (`curadoria-corte.md:77-157`). Extrair como "regra universal" é errado; extrair como dado
   (`momentos` por idioma + pesos por pack/Alma) preserva. Remover (por ser "de marca") perde o
   sinal mais forte medido (número nas 10 primeiras palavras).
3. **Constantes de screencast foram medidas num template de canal** (artigo à esquerda, webcam à
   direita, `cut.py:41-49`). Outra empresa com outro layout vai falhar a detecção sem erro. O núcleo
   precisa expor esses limiares como calibráveis e manter a regra "se mexer, MEÇA de novo"
   (`Instragram-Videos/.claude/agents/corte.md:98-100`). A fronteira medida por gradiente e o
   fallback para estimativa são a parte que generaliza — não trocar por número fixo
   (`cut.py:188-189`).
4. **Documentação divergente do código** — extrair lendo só docs erra:
   - skill diz screencast "abaixo de 15 % da largura" (`SKILL.md:142-144`); código usa 0,26 + posição (`cut.py:54-55`);
   - regra/skill/agente dizem que "abaixo de 15 % de rosto cai para crop central" (`curadoria-corte.md:296-298`,
     `new-video-youtube-cut.md:87-88`, `corte.md:96-97`); no código 15 % só **avisa** (`cut.py:467-469`);
     o crop central só acontece com < 4 amostras (`cut.py:300-301`);
   - skill manda ler "deslocamento total" impresso (`SKILL.md:132-133`); o código não imprime, grava `deslocamento_px` no `corte.json` (`cut.py:479`);
   - janela 52–62 s na regra (`curadoria-corte.md:62`) × `--max 72` no código (`momentos.py:81`).
5. **Suavização é o que separa "decisão de câmera" de "correção que enjoa"**: mediana 7 amostras +
   EMA 0,25 + zona morta 12 % + RDP 14 px + teto 24 pontos. Um "siga o rosto" ingênuo (um crop por
   quadro) produz tremor; mais de ~24 segmentos também estoura a expressão do ffmpeg
   (`cut.py:36`). Manter os cinco juntos.
6. **Na prática, o enquadramento dominante é `--fundo-desfocado`** (10 de 16 cortes) e o b-roll nunca
   foi usado (0 de 16). O núcleo não deve assumir "siga o rosto" como único modo, e a escolha do modo
   hoje é manual. O gancho fixo só é seguro no fundo desfocado; fora dele exige conferência visual
   manual de que não tampa rosto/tela (`compose_cut.py`, `curadoria-corte.md:252-253`) — gate
   inexistente no código.
7. **Loudness e pico**: o pós-ajuste de pico no arquivo final é o que impede o gate de entrega de
   reprovar vídeo certo. Extrair só o loudnorm de duas passagens reintroduz o bug medido (−0,5 dBFS).
8. **Julgamento humano/agente é parte do pipeline**, não opcional: a nota do `momentos.py` é
   desempate; as quatro perguntas (sustenta sozinho? promete nos 3 s? fecha? rende sem a tela?) e as
   invioláveis (sem splice que crie frase, ressalva viaja com a afirmação, ordem cronológica)
   (`curadoria-corte.md:66-75`, `:166-191`) precisam virar gates/prompt do pack, não sumir.
   `cut.py` só cobra o mecânico (≥ 4 s, sem sobreposição, ordem).
9. **yt-dlp é frágil por natureza** (403 a cada poucos meses) e o YouTube como fonte é específico:
   o núcleo deve tratar "vídeo longo local" como entrada genérica e yt-dlp como um provedor de fonte.
   Download por `--download-sections` evita baixar a aula inteira (`SKILL.md:124-125`).
10. **Dependência de ambiente**: ffmpeg 8 sem libass e sem `eval` no `crop`
    (`Instragram-Videos/CLAUDE.md:152-153`); outra build com libass não quebra, mas uma < 8 com
    `crop` diferente: NÃO DOCUMENTADO.
11. **Sem testes automatizados** para `pick_cut.py`, `momentos.py`, `cut.py`, `compose_cut.py`
    (busca em `Instragram-Videos/tests/`). O único gate é o `stop-gate.sh` do agente `corte`
    (resolução, janela, alinhamento, b-roll — `Instragram-Videos/.claude/hooks/corte/stop-gate.sh:20-53`)
    e o `verify.py`. A extração precisa de testes de caracterização (ex.: caminho do rosto e
    detecção de screencast) antes de mexer.
12. **Custos medidos**: `cut.py` reencoda cada peça com `crf 18 slow` e `compose_cut.py` de novo com
    `crf 19 slow` — duas gerações de perda; tempo de CPU de `amostrar_rostos` (lê todo quadro, analisa
    4/s): NÃO DOCUMENTADO.

## Fonte

- `Instragram-Videos/pipeline/pick_cut.py:1-195`, `momentos.py:1-214`, `cut.py:1-502`,
  `compose_cut.py:1-185`, `lib.py:1-328` (lidos inteiros); `verify.py:55-80`, `:128-145`.
- `Instragram-Videos/.claude/commands/new-video-youtube-cut.md:1-151`.
- `Instragram-Videos/.claude/skills/gerar-reel-corte/SKILL.md:1-205`.
- `Instragram-Videos/.claude/agents/corte.md:1-109`, `montagem.md:1-79`.
- `Instragram-Videos/.claude/hooks/corte/{pre-bash-guard.sh,pre-edit-scope.sh,stop-gate.sh}`.
- `Instragram-Videos/.claude/rules/curadoria-corte.md:1-366`, `montagem/ffmpeg.md:1-31`,
  `formato-entrega.md:1-40`; `Instragram-Videos/CLAUDE.md:140-162`.
- Artefatos: `Instragram-Videos/videos/yt-*/{corte.json,brolls.json,gancho.txt}` (16 cortes),
  `Instragram-Videos/fontes/*/`.
- Ambiente medido em 2026-09-24: yt-dlp 2026.08.19, opencv-python-headless 4.13.0.92 (cv2 4.13.0),
  numpy 2.4.3, Pillow 12.3.0, ffmpeg 8.0.1, Python 3.11.7. Nenhuma versão pinada no projeto.
- `git log` de `Instragram-Videos`: só `cc1e39d Initial commit`, árvore inteira não rastreada.
