# Goldens do sistema atual (T-01.07)

Saídas de referência do código dos projetos de origem, usadas pelos testes de paridade do
núcleo (D-16): a mesma entrada, rodada pelo núcleo, tem de dar a mesma saída (ou ficar dentro
da tolerância declarada em cada task).

Tudo aqui foi gerado por `motor/scripts/gerar_golden.py`, que roda o código de origem numa
**cópia temporária** (D-37). O sha256 de cada arquivo de origem lido é anotado antes e
conferido depois da execução; se algum mudar, o script para com erro. O `.env` dos projetos
de origem nunca é lido.

`manifesto.json` lista, por golden: `descricao`, `comando` (pasta de trabalho e argumentos),
`codigo` e `entradas` (caminho relativo à pasta `projects/` que contém os projetos de origem,
com sha256), `arquivos` (caminho relativo a esta pasta, com sha256), `origem_intacta`,
`igual_a_origem` (quando a origem já tinha gravado a mesma saída) e `observacoes`.
`tests/test_golden_presentes.py` falha se faltar um dos oito goldens ou qualquer arquivo listado.

## Os oito goldens

| Golden | Origem | O que guarda |
|---|---|---|
| G1 | `Instagram-Carrosseis/galeria` (`galeria.renderizar`) | prévia do layout `0001-pos-paineis-de-pagamento` com o `exemplo.json` dele: `slide_1..4.png` (1080×1350), `render.json` com o encaixe e os achados, `alma-golden.json` (tema `referencia` nos papéis de cor) e `fontes/` (woff2 baixados do Google Fonts no render, com `fontes.css` local) |
| G2 | `Instragram-Videos/remotion/scripts/montar-reel.mjs` | `timeline.json` e `trilha.wav` do reel `recriado-ia-decide`, com as entradas (`cenas.json`, `alignment.json`, `narracao.mp3`) |
| G3 | `Instragram-Videos/pipeline/captions.py` | legendas do reel `firecrawl-firecrawl`: `caps/NNN.png`, `caps/blank.png`, `caps/end.png`, `caps.txt`, `legendas.json`, e as entradas |
| G4 | `Instragram-Videos/pipeline/compose.py` | o MP4 montado do mesmo vídeo, `ffprobe.json` (resumo), `visual.json`, as entradas (tira, captura, narração, `impacto.txt`) e `alma-golden-reel.json` |
| G5 | `cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py` | `legendas.json` (42×2), o SRT, `cues.json` e as entradas (roteiro e JSON do whisper) |
| G6 | `youtube-squad/apresentacoes/decks/...` | `deck.json` |
| G7 | `Instragram-Videos/pipeline/momentos.py` e `transcrever.py` | `transcricao.json` (varredura, entrada do `momentos.py`), `candidatos.json` (o trecho escolhido é o primeiro), `transcricao_corte.json`, `alignment.whisper.json` + `roteiro.whisper.txt` (o `--alinhar`), `roteiro.txt` corrigido e `alignment.recasado.json` (o `--recasar`) |
| G8 | `Instragram-Videos/videos/recriado-ia-decide` | `narracao.mp3`, `alignment.json` e `roteiro.txt` da narração falada |

Particularidades (os detalhes estão em `observacoes` no manifesto):

- **G1:** a prancha não é guardada, porque recorta a referência de terceiros. A Alma golden
  tem identidade neutra de teste; só o visual reproduz a origem. O papel `negativo` não
  existe no tema e foi preenchido com uma cor que o layout não usa.
- **G4:** o vídeo da origem é anterior ao cartão de impacto; o gerador cria um `impacto.txt`
  curto na cópia para exercitar o cartão e o selo. A `alma-golden-reel.json` aponta para a
  fonte do sistema usada na origem, **só para os testes**, e o arquivo da fonte não é copiado
  para o repositório (D-47). Fora do macOS esses testes não têm a fonte.
- **G5:** `cues.json` é o que a origem gravou. O `gerar_voz.py` calcula os cues a partir do
  alinhamento devolvido pela ElevenLabs e não o salva; sem ele não há como regerar sem
  chamada paga (D-15).
- **G7:** o whisper do `--alinhar` é substituído por um módulo que devolve a
  `transcricao_corte.json` gravada pela origem; a conversão palavra→caractere e o recasamento
  são o código da origem.

## Como regerar

```bash
cd motor && uv run python scripts/gerar_golden.py                 # G1 a G8
cd motor && uv run python scripts/gerar_golden.py --so G5,G7      # só alguns (atualiza o manifesto)
cd motor && uv run python scripts/gerar_golden.py --saida /tmp/g  # outra pasta
```

Requisitos: os projetos de origem na pasta que contém o repositório (ou `--origens`),
`node`, `ffmpeg`/`ffprobe`, o Chromium do Playwright e rede **só** para o Google Fonts do G1.
Nenhuma chamada paga e nenhuma publicação.

Regerar muda sha256 (PNGs, MP4, datas das Almas golden); depois de regerar, rode
`cd motor && uv run pytest tests/test_golden_presentes.py` e revise o diff antes de versionar.

## Licença e uso

Os dados de teste aqui são derivados de projetos do mesmo dono deste repositório e são
usados **só como referência de paridade** nos testes do núcleo; não são material de marca
nem conteúdo para reuso. Nenhum vídeo de referência de terceiros é guardado. As fontes do G1
(Inter Tight) vêm do Google Fonts sob a SIL Open Font License.
