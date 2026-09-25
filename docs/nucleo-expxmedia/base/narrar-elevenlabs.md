# Narrar com ElevenLabs (capacidade `narrar`)

Fonte extraída: pipeline de reel de `Instragram-Videos` — `pipeline/tts.py`, `pipeline/pronuncia.py`,
`pipeline/lib.py` e a regra `.claude/rules/narracao/elevenlabs.md`. Formatos "recriado" e corte de
YouTube ficam fora deste arquivo (o corte não chama TTS: `Instragram-Videos/CLAUDE.md:107`).

## Contrato de entrada

- Diretório da peça com `roteiro.txt` (texto puro PT-BR, sem markdown, parágrafos separados por linha
  em branco — `Instragram-Videos/.claude/rules/roteirista/estrutura.md:92`). Invocação:
  `python3 pipeline/tts.py videos/<slug>` (`Instragram-Videos/pipeline/tts.py:5`).
- Faixa de palavras do roteiro: 130–180 (`Instragram-Videos/pipeline/lib.py:13`), contada com
  `len(roteiro.split())` sobre o **roteiro**, não sobre a fala (`Instragram-Videos/pipeline/tts.py:102-106`).
  Fora da faixa o script sai **antes** de chamar a API.
- Números por extenso no roteiro ("quatro vírgula quatro milissegundos"), nada de algarismo, emoji ou
  markdown (`Instragram-Videos/.claude/rules/voz-e-cta.md:137-139`). A palavra do CTA em CAIXA ALTA no
  roteiro funciona como deixa de ênfase para o TTS (`Instragram-Videos/pipeline/pronuncia.py:90-92`).
- Chave: `lib.chave_elevenlabs()` procura o primeiro `sk_[A-Za-z0-9]+` em **qualquer linha** do `.env`
  (`Instragram-Videos/pipeline/lib.py:107-111`); só depois tenta `ELEVENLABS_API_KEY`, `ELEVEN_API_KEY`,
  `XI_API_KEY` no ambiente (`Instragram-Videos/pipeline/lib.py:112-114`). No `.env` real a chave está
  com o nome `elevenlabs_apikey` (nome antigo que o contrato manda renomear).
- Parâmetros por ambiente: `VOICE_ID` (padrão `<voice_id do dono na origem>`, "Thulio Pro" —
  `Instragram-Videos/pipeline/tts.py:15`), `TTS_MODEL` (padrão `eleven_multilingual_v2` —
  `Instragram-Videos/pipeline/tts.py:16`), `TTS_SPEED` (padrão `SPEED_PADRAO = 1.2` —
  `Instragram-Videos/pipeline/tts.py:27`, `Instragram-Videos/pipeline/lib.py:24`).
- Camada de pronúncia: `pronuncia.aplicar(roteiro)` devolve `(fala, segmentos)`
  (`Instragram-Videos/pipeline/pronuncia.py:104-130`). `LEXICON` com 8 entradas
  (`Instragram-Videos/pipeline/pronuncia.py:53-70`): `software house→sóftwer ráuse`,
  `harnesses→rárneses`, `harness→rárnes`, `hooks→rúks`, `skill→skil`, `task→tésk`, `runx→run éks`,
  `memox→memo éxi`.

## Contrato de saída

- `narracao.mp3` — gravado **imediatamente** após a resposta, antes de qualquer validação ("o áudio
  já foi pago") (`Instragram-Videos/pipeline/tts.py:125-126`). Formato pedido à API:
  `mp3_44100_128` (`Instragram-Videos/pipeline/tts.py:118`). Se passou por `atempo`, é re-encodado a
  `libmp3lame 192k` (`Instragram-Videos/pipeline/tts.py:90-92`).
- `alignment.json` — `{"characters", "character_start_times_seconds", "character_end_times_seconds"}`
  **no espaço do `roteiro.txt`**, nunca no da fala (`Instragram-Videos/pipeline/tts.py:145-149`;
  `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:235-251`). Invariantes cobradas antes de
  gravar: `len(characters) == len(roteiro)` e `"".join(characters) == roteiro`
  (`Instragram-Videos/pipeline/pronuncia.py:160-161`). Tempos já descrevem o mp3 final (reescalados
  pelo fator do `atempo`: `Instragram-Videos/pipeline/tts.py:30-42`).
- Em caso de texto normalizado pela API: `alignment.raw.json` + `narracao.mp3` gravados e saída com
  erro — **não** grava `alignment.json` (`Instragram-Videos/pipeline/tts.py:128-139`).
- Linha final impressa: duração, palavras, modelo, speed, fator do atempo e nº de termos com pronúncia
  forçada (`Instragram-Videos/pipeline/tts.py:151-153`).
- Formato de alinhamento compartilhado: o corte de YouTube gera `alignment.json` no **mesmo formato**
  a partir do whisper, justamente para `captions.py` não mudar (`Instragram-Videos/CLAUDE.md:80-83`).
  Isso é o que no contrato vira a dependência `legendar ← narrar | transcrever`.
- Para `peca.json`: `narracao.mp3` → `arquivos[].papel = "audio"`; `alignment.json` →
  `papel = "alinhamento"` (enums em `ExpxMedia/docs/contrato/CONTRATO-peca.md`). Mapeamento é
  inferência nossa; a fonte não conhece `peca.json`.

## Limites e cotas

- Endpoint: `POST https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps`
  (`Instragram-Videos/pipeline/tts.py:118`). Sempre `/with-timestamps`: dá o alinhamento por caractere
  "de graça"; transcrever de volta é "pior e mais lento" (`Instragram-Videos/.claude/rules/narracao/elevenlabs.md:6-8`).
- `voice_settings`: `stability 0.45`, `similarity_boost 0.8`, `style 0.25`, `use_speaker_boost true`,
  `speed` (`Instragram-Videos/pipeline/tts.py:113-114`).
- `speed` aceito pela API: 0.7–1.2, padrão 1.0; 1.2 é o **teto** e o valor do canal; 1.3 é recusado
  (`Instragram-Videos/pipeline/tts.py:17-20`; `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:18-25`).
- `speed` **não garante ritmo**: 4 chamadas iguais a `speed` 1.1 deram 3,18 / 2,79 / 3,26 / 3,42 pal/s
  (14% de variação) (`Instragram-Videos/.claude/rules/narracao/elevenlabs.md:37-53`; `Instragram-Videos/pipeline/lib.py:16-19`).
- Piso de ritmo derivado: `RITMO_MIN = RITMO_APROVADO(3.18) * SPEED_PADRAO(1.2) / SPEED_APROVADO(1.1) ≈ 3,47 pal/s`
  (`Instragram-Videos/pipeline/lib.py:23-38`). É **piso, nunca alvo**. `TTS_SPEED` no ambiente não move
  o piso (`Instragram-Videos/pipeline/lib.py:31-32`).
- Correção de ritmo (`fixar_ritmo`, `Instragram-Videos/pipeline/tts.py:45-97`):
  - `fator = duração_atual / (palavras / RITMO_MIN)`;
  - `fator ≤ 1 + RITMO_TOL (0.03)` → nada, sem re-encode (`Instragram-Videos/pipeline/tts.py:74-79`; tolerância em `Instragram-Videos/pipeline/lib.py:39`);
  - veio mais rápida que o piso → nada (nunca freia) (`Instragram-Videos/pipeline/tts.py:52-54`);
  - `fator > ATEMPO_MAX (1.35)` → avisa alto e **não aplica** (`Instragram-Videos/pipeline/tts.py:81-87`; `Instragram-Videos/pipeline/lib.py:40`);
  - resto → `ffmpeg -filter:a atempo=<fator>` + `libmp3lame 192k` (`Instragram-Videos/pipeline/tts.py:89-93`).
  - `atempo` preserva o tom; `asetrate` desafinaria a voz clonada (`Instragram-Videos/pipeline/tts.py:66-67`).
- Não existe mais teto de ritmo médio no TTS: a leitura rápida demais é reprovada pela distribuição
  dos cartões de legenda em `verify.py` (ver `legendar.md`) (`Instragram-Videos/pipeline/tts.py:56-64`;
  `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:107-156`).
- Custo: "Crédito é dinheiro"; uma chamada de TTS por vídeo (`Instragram-Videos/CLAUDE.md:106`;
  `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:12-14`). Probe numerado de pronúncia custa
  "~15% de uma narração" (`Instragram-Videos/.claude/rules/narracao/elevenlabs.md:270`). Preço por
  caractere, cota mensal e limite de requisições da conta: NÃO DOCUMENTADO.
- A chave usada **não tem** permissão `voices_read` (`GET /v1/voices/<id>` devolve 401 e isso não é
  chave quebrada) (`Instragram-Videos/.claude/rules/narracao/elevenlabs.md:9-11`).
- Timeout HTTP da chamada: NÃO DOCUMENTADO (o `urlopen` é chamado sem `timeout`:
  `Instragram-Videos/pipeline/tts.py:121`).

## Erros conhecidos e tratamento

| Situação | Tratamento na fonte | Referência |
|---|---|---|
| Roteiro fora de 130–180 palavras | sai antes de gastar crédito | `Instragram-Videos/pipeline/tts.py:104-106` |
| HTTP de erro da API | `ERRO ElevenLabs <código>: <400 primeiros chars do corpo>` e sai | `Instragram-Videos/pipeline/tts.py:122-123` |
| API normalizou o texto (alinhamento não reconstrói a fala enviada) | grava `alignment.raw.json` + mp3, mostra 200 chars dos dois lados, **proíbe chamar a API de novo** | `Instragram-Videos/pipeline/tts.py:128-139`; `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:253-260` |
| Remapeamento não reconstrói o roteiro | `ValueError` | `Instragram-Videos/pipeline/pronuncia.py:160-161` |
| Ritmo lento demais (fator > 1,35) | não aplica atempo, avisa "algo mais está errado (roteiro, voz ou speed)" | `Instragram-Videos/pipeline/tts.py:81-87` |
| Chave ausente | `ERRO: chave da ElevenLabs não encontrada em .env nem no ambiente.` | `Instragram-Videos/pipeline/lib.py:115` |
| `eleven_v3` | testado com crédito e reprovado pelo ouvido do dono ("a voz não soou como eu") — não repropor | `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:273-279` |
| Tag SSML `<phoneme>` | só funciona no `eleven_flash_v2`; trocar de modelo muda a voz clonada — usa-se alias | `Instragram-Videos/pipeline/pronuncia.py:6-10`; `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:184-189` |
| Oclusiva final (/d/, /g/, /t/) | v2 insere vogal epentética; 4 grafias de "Code" falharam; termo vai cru ou sai do roteiro | `Instragram-Videos/pipeline/pronuncia.py:38-40`; `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:281-286` |
| Epêntese no meio ("so-fit") | o "w" de `sóftwer` segura o grupo consonantal | `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:288-292` |
| "r" inicial PT = /h/ | só use grafia com "r" inicial se a palavra inglesa começar com H; não existe grafia PT para /ɹ/ | `Instragram-Videos/pipeline/pronuncia.py:20-34` |
| Grafia crua às vezes ganha | `bug` e `MIT` saíram do lexicon após probe | `Instragram-Videos/pipeline/pronuncia.py:43,50-52` |
| Casamento do lexicon | case-insensitive, `\b` nas duas pontas, frases longas antes das curtas; plural precisa de entrada própria (`harnesses`) | `Instragram-Videos/pipeline/pronuncia.py:56-59,72-80` |
| Caixa do alias | preserva a caixa do roteiro (`RUNX→RUN ÉKS`); comprimento pode mudar, segmentos usam `len()` da string final | `Instragram-Videos/pipeline/pronuncia.py:87-101`; `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:202-210` |
| Erro de rede (não-HTTP) | NÃO DOCUMENTADO (só `HTTPError` é capturado; `URLError`/timeout estouram traceback) | `Instragram-Videos/pipeline/tts.py:120-123` |
| Retry automático | não existe; nenhuma regra fala de retry | — |

Procedimentos da fonte que precisam sobreviver:
- **Probe numerado** para decidir pronúncia: texto curto com variantes anunciadas por número falado; o
  dono responde por número; nunca decidir de ouvido próprio (`Instragram-Videos/.claude/rules/narracao/elevenlabs.md:266-271`).
- **Ampliar lexicon é decisão do dono**; entrada não ouvida é marcada incerta (`Instragram-Videos/.claude/rules/narracao/elevenlabs.md:199-200`).
- **Teste do remapeamento offline e sem crédito** com alinhamento sintético; os quatro caminhos de
  `fixar_ritmo` com mp3 sintético `sine=` do ffmpeg, sem tocar narração real
  (`Instragram-Videos/.claude/rules/narracao/elevenlabs.md:158-164,300-305`). Tabela de verificação dos
  caminhos: 3,04 pal/s→fator 1,141 acelera; 3,49→0,994 nada; 3,73→0,930 nada; 5,00→0,694 nada
  (`Instragram-Videos/.claude/rules/narracao/elevenlabs.md:173-178`).

## Riscos para a nossa implementação

Acoplamentos de marca que viram dado (M13/M14):
- `VOICE_ID` fixo "Thulio Pro" (`Instragram-Videos/pipeline/tts.py:15`;
  `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:3`) → `alma.porta_vozes[].voz.voz_id`.
- `RITMO_APROVADO = 3.18` e `SPEED_APROVADO = 1.1` são **medidas da voz do Thulio** aprovadas pelo
  ouvido dele (`Instragram-Videos/pipeline/lib.py:23-25`). Com outra voz o piso ≈3,47 pal/s não tem
  base. Precisa virar dado por porta-voz (ex.: ritmo aprovado + speed aprovado), senão o `atempo`
  acelera ou deixa de acelerar vozes errado. Campo equivalente na Alma: NÃO DOCUMENTADO no
  `CONTRATO-alma.md` — lacuna de contrato.
- `voice_settings` (0.45/0.8/0.25/boost) calibrados para a voz clonada dele
  (`Instragram-Videos/pipeline/tts.py:113-114`); origem da calibragem NÃO DOCUMENTADO. Deve ser dado
  por porta-voz com esse valor como padrão.
- `LEXICON` mistura jargão genérico (`harness`, `hooks`, `skill`, `task`, `software house`) com nomes
  de produtos da marca (`runx`, `memox`) (`Instragram-Videos/pipeline/pronuncia.py:53-70`). Os de
  produto vão para a Alma; os genéricos podem ser um lexicon-base do núcleo — mas cada entrada foi
  aprovada **para esta voz e este modelo**; não há campo de lexicon na Alma (lacuna de contrato).
- Nome de variável `elevenlabs_apikey` e busca por regex `sk_` em qualquer linha do `.env`
  (`Instragram-Videos/pipeline/lib.py:107-111`) → ler só `ELEVENLABS_API_KEY` (contrato de capacidades).
  Manter o regex ingênuo pode pegar outra chave `sk_` de outro provedor no mesmo `.env`.

O que derruba a qualidade se extraído de forma ingênua:
1. **Mandar o roteiro direto ao TTS sem a camada de alias** → jargão inglês abrasileirado.
2. **Gravar o alinhamento no espaço da fala** → legenda mostra "sóftwer ráuse" e "RUN ÉKS"; o CTA pintado
   deixa de casar (`Instragram-Videos/.claude/rules/narracao/elevenlabs.md:237-240`).
3. **Remapear em cima de texto normalizado pela API** → legenda torta e silenciosa; tem de parar.
4. **Tratar `RITMO_MIN` como alvo bidirecional** (frear leitura rápida) → desfaz a melhoria pedida e
   perde qualidade numa 2ª geração de mp3 (`Instragram-Videos/.claude/rules/narracao/elevenlabs.md:62-68`).
5. **Voltar a checar ritmo médio** no lugar da distribuição de cartões → deixa passar 71% de blocos
   ilegíveis (caso real 4,235 pal/s, `Instragram-Videos/.claude/rules/narracao/elevenlabs.md:114-126`).
6. **Usar `asetrate`** ou `speed > 1.2` para acelerar.
7. **Validar antes de gravar o mp3** → crédito perdido em qualquer falha posterior.
8. **Normalizar a caixa do alias** para minúscula → apaga a ênfase do CTA.
9. **Re-chamar a API em loop de retry** sem teto → gasto duplo; a fonte proíbe regenerar para testar
   (`Instragram-Videos/.claude/rules/segredos.md:14-16`).
10. Remapeamento de trecho substituído distribui o tempo **uniformemente** sobre os caracteres
    originais (`Instragram-Videos/pipeline/pronuncia.py:152-158`) — é aproximação aceita; não trocar
    por outra sem teste offline.

## Fonte

- `Instragram-Videos/pipeline/tts.py` (1–153)
- `Instragram-Videos/pipeline/pronuncia.py` (1–164)
- `Instragram-Videos/pipeline/lib.py` (8–40, 105–115)
- `Instragram-Videos/.claude/rules/narracao/elevenlabs.md` (1–307)
- `Instragram-Videos/.claude/rules/segredos.md` (1–16)
- `Instragram-Videos/.claude/agents/narracao.md` (1–49)
- `Instragram-Videos/CLAUDE.md` (80–83, 106–107, 146–148)
- `Instragram-Videos/.env` (só nomes de variáveis lidos; valores não)
- Testes: nenhum teste em `Instragram-Videos/tests/` exercita `tts.py` ou `pronuncia.py` (conferido por grep).
- Git: o repositório tem um único commit (`cc1e39d Initial commit`, 2026-09-17) e quase tudo está não
  rastreado; histórico de decisão só existe nas regras.
