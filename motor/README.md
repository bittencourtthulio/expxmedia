# Motor do núcleo

O motor é a parte em Python do ExpxMedia que faz o trabalho pesado: lê a Alma da empresa, confere
o que está habilitado no `.env`, produz as peças (post único, carrossel, carrossel misto, reel,
apresentação e aula), narra, transcreve, legenda, renderiza, verifica e publica. As skills do
plugin [`nucleo/`](../nucleo/README.md) não fazem nada disso sozinhas: elas conversam com a pessoa
e chamam o motor pelo CLI `expxmedia-motor`, que recebe argumentos e devolve sempre JSON em stdout.

O motor não carrega marca nenhuma (regra M13). Nome, cores, fontes, logotipo, voz, CTA e
porta-vozes vêm da Alma (`alma/alma.json`) da instalação; chaves de provedor vêm do `.env`.

## Requisitos

| O quê | Para quê |
|---|---|
| Python 3.11 ou mais novo | o motor |
| [uv](https://docs.astral.sh/uv/) | ambiente virtual, dependências e execução (`uv run ...`) |
| Node 20 (com `npx`) | o kit Remotion em `kit-remotion/` (reel, apresentação em MP4, aula) |
| ffmpeg 8 (com `ffprobe`) | corte, montagem, normalização de áudio e verificação de vídeo |
| Chromium do Playwright | render de HTML em PNG (post, carrossel, captura de página) |
| chrome-headless-shell do Remotion | render das composições do kit |
| modelos faster-whisper `small` e `medium` | transcrição e alinhamento por palavra |
| modelo `u2net` do rembg | recorte do retrato do porta-voz |
| `say` (macOS) | **só nos testes**: narração falsa sem provedor pago; não é usado em produção |

Provedores pagos (narração, avatar, imagem por IA, banco de imagens, publicação) são opcionais:
cada capacidade só liga quando a chave dela está no `.env`. Veja `expxmedia-motor capacidades`.

## Preparação

Uma vez por máquina, com rede:

```bash
cd motor
uv run python scripts/preparar_ambiente.py
```

O script é idempotente e faz: `uv sync`; `playwright install chromium`; `npm ci` no
`kit-remotion/`; `npx remotion browser ensure`; a cópia da fonte padrão embarcada (Inter, licença
OFL) para `src/expxmedia/recursos/fontes/`; e o download, só se faltarem, dos modelos
faster-whisper `small` e `medium` e do `u2net`. Depois disso a suíte roda sem rede.

## Arquitetura

Tudo mora em `src/expxmedia/`. Cada pacote cuida de uma coisa; os de produção só combinam os
de baixo.

| Pacote | O que faz |
|---|---|
| `nucleo` | base comum: raiz da instalação, gravação atômica de arquivos, ids, relógio e rastro de eventos |
| `ambiente` | catálogo de capacidades e variáveis, leitura do `.env` sem expor valor, `.env.example`, verificação do que está habilitado |
| `alma` | schema e carga da Alma, portão de primeiro uso, extração da proposta a partir do site, tokens visuais e fontes |
| `peca` | o `peca.json`: criação da pasta da peça, validação contra o contrato e ciclo de vida do status |
| `template` | schema dos templates, validação e galeria local (busca por tipo, formato e requisitos) |
| `render_html` | render de HTML em PNG, encaixe do texto nos slots, contraste e prancha de conferência |
| `imagem` | banco de imagens, imagem por IA, rosto do porta-voz em cena nova, retratos e cota de gasto |
| `captura` | captura de página web em tira, `site.md` e seções |
| `video` | chamadas ao ffmpeg, montagem do reel de página e verificação de entrega por perfil |
| `narrar` | narração na voz do porta-voz (provedor real ou de teste), pronúncia e ritmo, com alinhamento por caractere |
| `transcrever` | transcrição com tempo por palavra (faster-whisper) e recasamento com o roteiro |
| `legendar` | legenda do reel em PNG, legenda de aula 42×2, SRT e queima no vídeo |
| `motion` | render e prévia das composições do kit Remotion |
| `referencia` | análise do vídeo de referência e o formato sob medida do reel por referência |
| `corte` | reel de corte: escolha de momentos, corte 9:16 que segue o rosto e b-roll |
| `aula` | cues do roteiro, edição da gravação de tela no tempo da fala e compilação de aulas |
| `avatar` | vídeo do porta-voz falando a partir do áudio da narração (provedor real ou de teste) |
| `publicar` | publicação e agendamento pelos provedores (Expx Flow e Graph API da Meta), com dry-run e túnel de URL pública |
| `agendador` | agendador local: a rodada que publica no horário e a instalação do disparo no sistema operacional |
| `revisar` | revisões mecânicas: copy pela Alma e portão do roteiro antes da narração |
| `producao` | a produção de cada tipo de peça, do `entrada.json` à peça produzida |
| `cli` + `cli_comandos` | o CLI: `cli.py` descobre os módulos de `cli_comandos/`, e cada módulo registra os seus subcomandos |

Fora do pacote: `kit-remotion/` (composições Remotion em TypeScript), `scripts/` (preparação do
ambiente e geração dos goldens) e `src/expxmedia/recursos/` (fontes e arquivos embarcados).

Para acrescentar um subcomando, crie ou edite um módulo em `cli_comandos/` com
`registrar(subparsers)`; o `cli.py` não precisa mudar. Documente o subcomando novo aqui:
`tests/test_documentacao.py` falha se o CLI e este arquivo divergirem.

## Referência do CLI

```bash
cd motor
uv run expxmedia-motor --help
uv run expxmedia-motor <grupo> --help
uv run expxmedia-motor <grupo> <subcomando> --help
```

`--raiz RAIZ` é global e vale em qualquer nível: aponta a raiz da instalação. Sem ele, a raiz é
procurada subindo a partir da pasta atual. Todo subcomando aceita `-h`. As linhas de uso abaixo
saíram do `--help` real (sem `-h` e `--raiz`, que valem para todos).

<!-- cli:inicio -->

### `agendador`

Agendador local (publica no horário via meta_graph).

#### `agendador instalar`

Instala o disparo de minuto em minuto no SO (sem --aplicar só mostra).

```
expxmedia-motor agendador instalar [--aplicar] [--sistema {macos,windows,linux}] [--executavel EXECUTAVEL]
```

#### `agendador rodar`

Uma rodada: publica o que chegou no horário (chamado pelo SO).

```
expxmedia-motor agendador rodar
```

### `agendar`

Agenda a peça para um horário (dry-run sem --confirmar).

```
expxmedia-motor agendar --peca PECA [--canal {facebook,instagram,linkedin,meta_ads,tiktok,youtube}] [--dm DM] [--confirmar] [--forcar] --para PARA
```

### `alma`

Alma da empresa.

#### `alma confirmar`

O "confirmo tudo": valida a proposta e a grava como alma/alma.json.

```
expxmedia-motor alma confirmar [--proposta PROPOSTA]
```

#### `alma extrair-site`

Lê o site da empresa e grava a proposta de Alma (nunca a Alma).

```
expxmedia-motor alma extrair-site --url URL [--saida SAIDA]
```

#### `alma validar`

Valida alma/alma.json contra o contrato e mostra o portão.

```
expxmedia-motor alma validar
```

### `ambiente`

O .env da instalação, sem nunca mostrar valor de chave.

#### `ambiente criar-env`

Cria o .env a partir do .env.example, só se ainda não existir.

```
expxmedia-motor ambiente criar-env
```

#### `ambiente exemplo`

Gera o .env.example: o que cada chave libera e onde conseguir.

```
expxmedia-motor ambiente exemplo
```

#### `ambiente gravar-chave`

Grava no .env uma variável do catálogo com o valor lido do stdin.

```
expxmedia-motor ambiente gravar-chave --nome NOME
```

### `aula`

Compilação de aulas e edição da gravação de tela.

#### `aula compilar`

Trechos de aulas produzidas num MP4 só, com um SRT único deslocado.

```
expxmedia-motor aula compilar --partes PARTES --titulo TITULO [--formato {16:9,9:16}] [--serie SERIE]
```

#### `aula editar-tela`

Corta a gravação de tela por cues: acelera ou congela para caber na fala.

```
expxmedia-motor aula editar-tela --cues CUES --janelas JANELAS --saida SAIDA [--json DESTINO_JSON] [--marcas MARCAS] [--cue-final CUE_FINAL] [--so-json]
```

### `avatar`

Vídeo do porta-voz falando a partir do áudio da narração.

#### `avatar gerar`

Gera o avatar do porta-voz a partir do ÁUDIO (nunca do texto).

```
expxmedia-motor avatar gerar --audio AUDIO --saida SAIDA [--porta-voz PORTA_VOZ]
```

### `capacidades`

O que está habilitado nesta instalação e como habilitar o resto.

```
expxmedia-motor capacidades [--capacidade CAPACIDADE] [--porta-voz PORTA_VOZ]
```

### `capturar`

Captura de conteúdo.

#### `capturar pagina`

Captura uma página web em tira, site.md e seções.

```
expxmedia-motor capturar pagina --url URL --saida SAIDA [--largura-css LARGURA_CSS] [--esquema {dark,light,no-preference}] [--ocultar OCULTAR]
```

### `galeria`

Galeria local de templates.

#### `galeria buscar`

Templates por tipo e formato, sem os que não dá para usar aqui.

```
expxmedia-motor galeria buscar --tipo {post_unico,carrossel,reel,apresentacao,aula} --formato {16:9,1:1,4:5,9:16} [--serve-para SERVE_PARA] [--estilo ESTILOS] [--kind KINDS] [--porta-voz PORTA_VOZ] [--embarcados EMBARCADOS]
```

### `imagem`

Imagens da peça: banco, geração, retrato.

#### `imagem openrouter`

Gera imagem pelo OpenRouter (imagem_ia), dentro da cota.

```
expxmedia-motor imagem openrouter --prompt PROMPT --saida SAIDA [--proporcao PROPORCAO] [--modelo MODELO] [--base BASE]
```

#### `imagem pexels`

Busca foto ou vídeo no Pexels (banco_imagens).

```
expxmedia-motor imagem pexels --termo TERMO [--midia {foto,video}] [--orientacao {portrait,landscape,square}] [--quantos QUANTOS] [--baixar BAIXAR] [--sem-filtro] [--lado-minimo LADO_MINIMO] [--conhecido CONHECIDOS]
```

#### `imagem retrato`

Retrato do porta-voz para o slot pessoa (ou o substituto desenhado).

```
expxmedia-motor imagem retrato [--porta-voz PORTA_VOZ] [--recortar-em RECORTAR_EM] [--indice INDICE]
```

#### `imagem rosto`

Porta-voz em cena nova pelo Higgsfield (rosto_ia), dentro da cota.

```
expxmedia-motor imagem rosto --porta-voz PORTA_VOZ --prompt PROMPT --saida SAIDA
```

### `legendar`

Legendas em PNG (reel) ou SRT (aula).

#### `legendar aula`

Legenda de aula: texto do roteiro nos tempos da transcrição (42x2) e SRT.

```
expxmedia-motor legendar aula --roteiro ROTEIRO --transcricao TRANSCRICAO --saida SAIDA
```

#### `legendar reel`

Legenda do reel: PNG por bloco, caps.txt, legendas.json, card do CTA e SRT.

```
expxmedia-motor legendar reel --alinhamento ALINHAMENTO --roteiro ROTEIRO --saida SAIDA [--cta CTA] [--sem-cta] [--card-final CARD_FINAL] [--offset OFFSET] [--porta-voz PORTA_VOZ]
```

### `motion`

Render e prévia de composições do kit Remotion.

#### `motion previa`

Um still a 60% de cada cena com as guias da área segura e a folha.

```
expxmedia-motor motion previa --composicao COMPOSICAO --timeline TIMELINE --saida SAIDA [--props PROPS] [--public-dir PUBLIC_DIR] [--escala ESCALA] [--versao VERSAO]
```

#### `motion render`

Renderiza uma composição do kit Remotion em MP4.

```
expxmedia-motor motion render --composicao COMPOSICAO --saida SAIDA [--props PROPS] [--public-dir PUBLIC_DIR] [--versao VERSAO] [--codec CODEC]
```

### `narrar`

Narra um roteiro na voz do porta-voz: mp3 + alinhamento por caractere.

```
expxmedia-motor narrar --roteiro ROTEIRO --porta-voz PORTA_VOZ [--tipo {reel,aula,post_unico,carrossel,apresentacao}] --saida SAIDA
```

### `peca`

Peças (peca.json).

#### `peca criar`

Cria a pasta e o peca.json de uma peça nova.

```
expxmedia-motor peca criar --tipo {post_unico,carrossel,reel,apresentacao,aula} --formato FORMATO [--titulo TITULO] [--serie SERIE] [--pack PACK]
```

#### `peca status`

Mostra ou muda o status da peça pelo ciclo de vida.

```
expxmedia-motor peca status [--novo {ideia,roteiro,produzida,aprovada,agendada,publicada,medida,descartada}] [--motivo MOTIVO] peca_id
```

### `produzir`

Produção de peças.

#### `produzir abertura`

Abertura gerada por IA que troca o fundo do começo do reel (video_ia).

```
expxmedia-motor produzir abertura --pasta PASTA [--prompt PROMPT] [--tipo TIPO] [--porta-voz PORTA_VOZ] [--duracao DURACAO] [--estilo ESTILO] [--sem-transformar] [--dispensar]
```

#### `produzir apresentacao`

Apresentação em HTML navegável; com --mp4, também MP4 e PNG por slide.

```
expxmedia-motor produzir apresentacao --entrada ENTRADA [--mp4] [--embarcados EMBARCADOS]
```

#### `produzir aula`

Aula narrada em 16:9 e/ou 9:16: cues, legenda 42x2, avatar e tela opcionais, SRT.

```
expxmedia-motor produzir aula --entrada ENTRADA [--embarcados EMBARCADOS]
```

#### `produzir carrossel`

Carrossel de imagem: slides, prancha e legenda.

```
expxmedia-motor produzir carrossel --entrada ENTRADA [--embarcados EMBARCADOS]
```

#### `produzir post`

Post único a partir de template e slots.

```
expxmedia-motor produzir post --entrada ENTRADA [--embarcados EMBARCADOS]
```

#### `produzir reel`

Reel narrado em Remotion a partir de um template de reel.

```
expxmedia-motor produzir reel --entrada ENTRADA [--embarcados EMBARCADOS]
```

#### `produzir reel-corte`

Reel de corte: trecho de vídeo longo em 9:16 com a fala original.

```
expxmedia-motor produzir reel-corte --entrada ENTRADA
```

#### `produzir reel-pagina`

Reel a partir de página: captura, gate, narração, legenda, montagem e verificação.

```
expxmedia-motor produzir reel-pagina --entrada ENTRADA
```

### `publicar`

Publica a peça agora (dry-run sem --confirmar).

```
expxmedia-motor publicar --peca PECA [--canal {facebook,instagram,linkedin,meta_ads,tiktok,youtube}] [--dm DM] [--confirmar] [--forcar]
```

### `referencia`

Reel por referência sob medida: análise, pasta, montagem, prévia e render.

#### `referencia analisar`

Quadros, folhas de contato, cortes e fala do vídeo de referência em analise/.

```
expxmedia-motor referencia analisar --video VIDEO --pasta PASTA [--sem-fala] [--modelo MODELO] [--idioma IDIOMA]
```

#### `referencia criar`

Cria referencias/<slug>/ com o cenas.json esqueleto e o Reel.tsx do kit.

```
expxmedia-motor referencia criar [--titulo TITULO] [--origem-url ORIGEM_URL] [--pedido PEDIDO] slug
```

#### `referencia montar`

Linha do tempo pelas âncoras e trilha com os efeitos em midia/.

```
expxmedia-motor referencia montar --pasta PASTA
```

#### `referencia previa`

Um still a 60% de cada cena com as guias e a folha em previa/NN/ (até 3 voltas).

```
expxmedia-motor referencia previa --pasta PASTA [--porta-voz PORTA_VOZ] [--canal CANAL]
```

#### `referencia render`

Render, normalização, verificação no perfil sob_medida e a peça produzida.

```
expxmedia-motor referencia render --pasta PASTA [--porta-voz PORTA_VOZ] [--canal CANAL]
```

### `revisar`

Revisões mecânicas antes de renderizar ou publicar.

#### `revisar copy`

Bloqueantes mecânicos da copy pela Alma: travessão, tratamento, palavras proibidas, palavra do CTA e abertura repetida em 14 dias.

```
expxmedia-motor revisar copy [--arquivo ARQUIVO] [--texto TEXTO] [--peca PECA] [--palavra-publicacao PALAVRA_PUBLICACAO] [--serie SERIE]
```

### `transcrever`

Transcreve áudio ou vídeo com tempo por palavra.

```
expxmedia-motor transcrever --audio AUDIO --saida SAIDA [--modo {varredura,alinhamento}] [--modelo MODELO] [--idioma IDIOMA] [--alinhamento ALINHAMENTO]
```

### `verificar`

Verificação de entrega de um vídeo num perfil.

```
expxmedia-motor verificar --perfil PERFIL [--pasta PASTA] [--caps CAPS] [--legendas LEGENDAS] [--alinhamento ALINHAMENTO] [--roteiro ROTEIRO] [--srt SRT] [--legenda-post LEGENDA_POST] video
```

<!-- cli:fim -->

## Códigos de saída

A saída é sempre JSON em stdout, inclusive nos erros.

| Código | Quando |
|---|---|
| 0 | ok |
| 1 | erro genérico |
| 2 | entrada inválida: argumento errado, peça, Alma ou capacidade fora do contrato, instalação não encontrada |
| 3 | capacidade não habilitada: o JSON traz `como_habilitar`, com a chave que falta e onde conseguir |

Um subcomando pode sair com outro código e um JSON próprio (`Falha(codigo, dados)` em `cli.py`).

## Testes

```bash
cd motor
uv run pytest                          # a suíte inteira
uv run pytest tests/test_cli.py        # um arquivo
uv run pytest -m "not integracao_local" # só o que não depende de binário local
```

- Nenhum teste chama provedor pago nem publica de verdade: os provedores rodam contra o stub
  HTTP local (`tests/stubs/`) ou executáveis falsos, e a rede fica barrada nos testes que usam
  a fixture `sem_rede`.
- O marcador `integracao_local` marca os testes que exigem binário local (ffmpeg, `say`,
  `claude`, whisper...). Quando o binário falta, o teste pula e diz qual é.
- `tests/test_marca.py` varre `motor/src`, o kit Remotion, `nucleo/` e `templates/` atrás dos
  termos de `tests/marca_proibida.txt` (regra M13).
- A Alma fictícia e a instalação de teste ficam em `tests/fixtures/`.

### Goldens

`tests/golden/` guarda as saídas de referência do sistema anterior (G1 a G8), usadas nos testes
de paridade: a mesma entrada, rodada pelo motor, tem de dar a mesma saída ou ficar dentro da
tolerância declarada. O `manifesto.json` descreve cada golden e `tests/test_golden_presentes.py`
falha se faltar algum arquivo. Para regerar (precisa dos projetos de origem ao lado deste
repositório; o código deles roda só numa cópia temporária e nunca é alterado):

```bash
cd motor
uv run python scripts/gerar_golden.py              # G1 a G8
uv run python scripts/gerar_golden.py --so G5,G7   # só alguns
```

Detalhes de cada golden em [`tests/golden/README.md`](tests/golden/README.md).

## Pendência comercial: licença do Remotion

O reel, a apresentação em MP4 e a aula são renderizados com o Remotion, cuja licença pode exigir
licença paga para empresas acima de um certo porte. Se a empresa que instala o ExpxMedia precisa
de licença é uma decisão comercial ainda em aberto: **PENDENTE-01** em
[`docs/nucleo-expxmedia/00-DECISOES.md`](../docs/nucleo-expxmedia/00-DECISOES.md). Enquanto isso,
o `/expxmedia:ambiente` informa os termos. Se a decisão for não usar Remotion, a capacidade de
motion ganha outro provedor atrás da mesma interface.
