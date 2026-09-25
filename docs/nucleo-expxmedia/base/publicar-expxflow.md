# Publicação pelo Expx Flow (provedor `expxflow` de `publicar`, `agendar`, `automacao_dm`)

Duas implementações de origem falam com a mesma API pública do Expx Flow:

- `Instagram-Carrosseis/publicar/publicar.py` (410 linhas, `requests`): carrossel e post único de imagem, upload próprio, cache `uploads.json`, dry-run, validação por schema, `Idempotency-Key`, registro de automação reaproveitável.
- `Instragram-Videos/pipeline/publish.py` + `pipeline/expxflow.py` (`urllib`): reel pelo `post-api` com `content_type: reel`, mídia exposta por túnel temporário (ver `tunel-url-publica.md`).

Referências da API usadas: `Instagram-Carrosseis/_referencias/llms (4).txt` (baixada 2026-09-11) e a cópia mais nova `Instragram-Videos/docs/expx-flow/llms.txt` (baixada 2026-09-17, `Instragram-Videos/docs/expx-flow/README.md:3`). Quando divergem, vale a mais nova, citada abaixo como `llms.txt (Videos)`.

## Contrato de entrada

**Autenticação e base**
- Cabeçalho `X-API-Key`; a empresa é derivada da chave, não há campo de empresa no corpo (`llms (4).txt:9`).
- Permissões da chave: `carousel` (upload, carrossel, post único) e `instagram_automation` (automação avulsa) (`llms (4).txt:143,196,854`; `llms.txt (Videos):1002-1009`).
- A URL base é um projeto Supabase fixo, **embutida no código** como padrão: `Instagram-Carrosseis/publicar/publicar.py:49` (padrão de `EXPX_API_BASE_URL`) e `Instragram-Videos/pipeline/expxflow.py:5` (constante `BASE`, sem variável). Valor não reproduzido aqui (regra M14).
- Nomes de variável na origem: `EXPX_API_KEY`, `EXPX_CLIENT_ID`, `EXPX_API_BASE_URL`, `EXPX_APP_URL`, `EXPX_PLATFORMS`, `EXPX_TIMEZONE`, `EXPX_HORA_PADRAO`, `EXPX_TITULO_PREFIXO`, `EXPX_HASHTAGS_EXTRA`, `EXPX_AUTOMACAO_*` (`Instagram-Carrosseis/publicar/.env.example`, só nomes lidos). O projeto de vídeos acha a chave por regex de prefixo em qualquer linha do `.env` (`Instragram-Videos/pipeline/expxflow.py:13`) e o `client_id` pela primeira linha que contenha "client" seguida de UUID (`expxflow.py:25`). Nomes canônicos do contrato: `EXPXFLOW_API_KEY`, `EXPXFLOW_CLIENT_ID` (`ExpxMedia/docs/contrato/CONTRATO-capacidades.md:47,161`).

**Endpoints usados**

| Endpoint | Uso | Entrada principal | Fonte |
|---|---|---|---|
| `GET /clients-api` | descobrir `client_id` | `search`, `limit` (≤ 200), `offset` | `llms (4).txt:17-30`; `publicar.py:73-83` |
| `POST /media-upload-api` | hospedar **imagem** | multipart campo `file` ou binário cru; PNG, JPEG, WebP, GIF | `llms (4).txt:139-149`; `publicar.py:140-141` |
| `POST /carousel-api` | carrossel agendado | `slides[]` (2–20, cada um com `image_url`), `platforms`, `scheduled_at` **ou** `publish_now`, `caption`, `hashtags`, `title`, `client_id`, `automation` **ou** `automation_id` | `llms (4).txt:192-223`; `llms.txt (Videos):202-226` |
| `POST /post-api` | mídia única (imagem, vídeo, reel) | `image_url` ("Link público da imagem ou vídeo"), `content_type` = `image`\|`video`\|`reel`, demais campos iguais ao carrossel | `llms.txt (Videos):1015-1024`; `llms (4).txt:1008-1017` |
| `POST /instagram-automation-api` | automação em post existente | `acao` = `vincular_automacao`\|`remover_automacao`\|`listar_automacoes`, `scheduled_post_id`, `automacao{}` | `llms (4).txt:850-871` |

**Regras de payload cobradas (espelhadas nos schemas locais)**
- `scheduled_at` ISO 8601 com fuso, ≥ 2 min no futuro (`llms.txt (Videos):205,1017`). O código recusa com folga de 3 min (`publicar.py:105`) e 2 min (`Instragram-Videos/pipeline/publish.py:76`).
- Exatamente um entre `scheduled_at` e `publish_now` (`Instagram-Carrosseis/contratos/carrossel.schema.json:29`, `post-unico.schema.json:19`).
- `automation` e `automation_id` mutuamente exclusivos, 400 se juntos (`llms (4).txt:223`; schemas `carrossel.schema.json:30`, `post-unico.schema.json:20`).
- Bloco `automation`: `keywords` (≥ 1, únicas) e `mensagem` obrigatórios; `link` http(s); `link_label` ≤ 20 caracteres; `match_mode` `any`\|`all`\|`exact`; `public_reply_enabled: true` exige `public_reply_text` (`Instagram-Carrosseis/contratos/automacao.schema.json:6-29`). A doc mais nova acrescenta `public_reply_mode` (`fixo`\|`ia`), `public_reply_prompt`, `public_reply_fallback_text` (`llms.txt (Videos):223-225`); o schema dos carrosséis tem `additionalProperties: false` (`automacao.schema.json:30`) e **recusa** esses três campos; o `publish.py` dos vídeos os envia (`publish.py:151-154`).
- Automação exige `instagram` em `platforms` e `client_id` de cliente com Instagram vinculado (`llms (4).txt:215,1111`).
- Mídia por URL pública; `data:` recusado (`llms (4).txt:203,1008`).
- `Idempotency-Key` recomendado no carrossel (`llms (4).txt:383`). Carrosséis montam `<serie>-<cliente>-<bloco>-<id>-<scheduled_at|agora>` (`publicar.py:383`); o plano usa `plano-<serie>-<item>-<AAAAMMDDTHHMM>` (`Instagram-Carrosseis/planejar.py:645`). Vídeos **não enviam** a chave (`Instragram-Videos/pipeline/expxflow.py:31-50`).

**Escolha de endpoint no código**: 1 imagem → `post-api`; 2+ → `carousel-api` (`publicar.py:242-262,384`). Imagens detectadas por `slide_*.png`, senão `post-*.png` (`publicar.py:113-119`) — só PNG.

**Dry-run**: carrosséis montam e validam o payload, trocam upload por URL fictícia e não enviam (`publicar.py:136-137,394-396`); vídeos imprimem o payload com URL de marcação e saem (`publish.py:160-164`).

**Fonte editorial normalizada** (`Instagram-Carrosseis/contratos/fonte-publicacao.schema.json`): `contract_version: 1`, `tipo` (`carrossel`\|`post-unico`\|`cta`), `colecao`, `block_id` kebab, `itens[]` com `id`, `nome`, `legenda`; precedência de automação: inline no item → `automation_ref` → `default_automation_ref` → `publication.automation` (`Instagram-Carrosseis/contratos/FONTE-PUBLICACAO.md:5`; `publicar/contratos.py:23-40`).

## Contrato de saída

- Envelope: sucesso `{ "success": true, "data": {...} }`; erro `{ "success": false, "error": "...", "details"? }` (`llms (4).txt:13`).
- Upload: 201 com `data.image_url`, `content_type`, `size_bytes`; URL "pública e permanente" (`llms (4).txt:164-186`).
- Carrossel: 201 com `project_id`, `scheduled_post_id`, `slides_count`, `scheduled_at` (UTC), `published_now`, `editor_url` relativo (`llms (4).txt:261-272`). **Não documenta** `trigger_id` no retorno do carrossel, embora `publicar.py:287,305` o leia.
- Post único: 201 com `scheduled_post_id`, `media_url`, `content_type`, `scheduled_at`, `published_now`, `trigger_id`, `automation_status`, `automation_error` (`llms (4).txt:1048-1061`).
- `vincular_automacao`: 200 com `trigger_id`, `flow_id`, `status: "aguardando_publicacao"` (`llms (4).txt:900-908`).
- Nenhum endpoint devolve a URL final do post no Instagram nem o id de mídia do Instagram no momento do agendamento: NÃO DOCUMENTADO. O campo `publicacoes[].url` do `peca.json` (`ExpxMedia/docs/contrato/CONTRATO-peca.md:135`) não tem fonte neste provedor sem consulta posterior.
- Registros locais de origem:
  - `publicar/publicacoes-<serie>.json`: lista JSON reescrita por inteiro a cada envio (`publicar.py:276-291`), campos `id`, `repositorio`, `http`, `enviado_em`, `scheduled_at`, `project_id`, `scheduled_post_id`, `editor_url`, `automation_trigger_id`, `keywords`.
  - `publicar/estado/automacoes.json`: `{"version": 1, "automations": {"<client>:<bloco>:<sha256>": {client_id, block_id, config_hash, automation_id, created_at}}}`, gravado por temporário + `replace` (`publicar.py:179-239`).
  - `<pasta dos slides>/uploads.json`: mapa `"<nome>:<tamanho>:<mtime>" → url` (`publicar.py:126-150`), gravado sem atomicidade (`publicar.py:148`).
  - `videos/<slug>/publicacao.json` (vídeos): `scheduled_post_id`, `trigger_id`, `scheduled_at`, `media_url`, `content_type`, `automation_status`, `automation_error`, `assunto`, `keywords`, `enviado_em` (`publish.py:180-186`).
- Mapeamento para `peca.json.publicacoes[]`: `id_externo` ← `scheduled_post_id`; `automacao_dm.id_externo` ← `trigger_id` (`CONTRATO-peca.md:134-136`). Mapeamento explícito na origem: NÃO DOCUMENTADO (derivação nossa).

## Limites e cotas

| Limite | Valor | Fonte |
|---|---|---|
| Imagem no upload | 10 MB; PNG, JPEG, WebP, GIF | `llms (4).txt:149,181-182` |
| Vídeo no upload | não aceito: 415 para `video/mp4` | `Instragram-Videos/docs/expx-flow/README.md:25`; `Instragram-Videos/.claude/rules/publicacao.md:41` |
| Slides por carrossel | 2 a 20 | `llms (4).txt:202`; `carrossel.schema.json:14-15` |
| Antecedência mínima | 2 min | `llms (4).txt:205` |
| Janela de saída | fila varrida a cada minuto; "18:00 sai entre 18:00 e 18:01" | `llms.txt (Videos):387` |
| `link_label` | ≤ 20 caracteres | `llms (4).txt:219` |
| Mensagens de DM por comentário | 1; enviada em até 7 dias do comentário (limite da Meta) | `llms (4).txt:989` |
| `clients-api` `limit` | até 200, padrão 50 | `llms (4).txt:29` |
| Rate limit da API | NÃO DOCUMENTADO | busca em `llms (4).txt` e `llms.txt (Videos)` |
| Timeouts do cliente | upload 120 s, criação 180 s, clientes 60 s | `publicar.py:77,141,296,311` |
| Timeouts nos vídeos | nenhum (`urlopen` sem `timeout`) | `expxflow.py:43` |
| Vídeo no `post-api` (tamanho, duração, codec) | NÃO DOCUMENTADO pela API do Expx Flow | `llms.txt (Videos):1003-1024` |

## Erros conhecidos e tratamento

| Código | Significado | Tratamento de origem | Fonte |
|---|---|---|---|
| 400 | payload inválido, com `details` | carrosséis saem com `sys.exit(1)` | `llms (4).txt:374`; `publicar.py:299-300` |
| 401 / 403 | chave ausente/inválida / sem permissão | idem | `llms (4).txt:375-376` |
| 404 | `client_id` fora da empresa; na automação, conta ou post não encontrado | idem | `llms (4).txt:377,981` |
| 409 | automação em post já publicado | NÃO TRATADO no código | `llms (4).txt:982` |
| 413 / 415 | upload > 10 MB / tipo não suportado | `sys.exit(1)` | `llms (4).txt:181-182`; `publicar.py:142-145` |
| 422 | "Uma das imagens não pôde ser baixada ou não é uma imagem" | `sys.exit(1)` | `llms (4).txt:378` |
| 207 | carrossel criado, **agendamento falhou** | aviso e segue como registrado | `llms (4).txt:379`; `publicar.py:301-302`; regra: tratar como parcial (`Instagram-Carrosseis/.claude/rules/publicacao/publicacao-fluxo.md:25-26`) |
| 201 com `automation_status: falhou` | post agendado, automação falhou | vídeos: `sys.exit(1)` e aviso (`publish.py:191-193`); regra diz que não é sucesso (`Instragram-Videos/.claude/rules/publicacao.md:57-61`) | `llms (4).txt:1112` |
| Resposta não-JSON | — | vídeos devolvem `{"raw": texto[:800]}` (`expxflow.py:47-50`) | — |

- Sem retentativa automática em nenhum dos dois clientes; a proteção contra duplicata em nova tentativa é o `Idempotency-Key` (só nos carrosséis).
- Automação: registro com `automation_id` ausente interrompe o lote para não duplicar (`publicar.py:212-216`). A doc antiga não garantia vínculo muitos-para-muitos (`Instagram-Carrosseis/contratos/AUTOMACAO.md:7`); a doc nova afirma que "a mesma automação pode ser reaproveitada por vários posts" (`llms.txt (Videos):226`).
- A API **não tem exclusão de post agendado**; desfaz-se só pela tela (`Instragram-Videos/.claude/rules/publicacao.md:12-14`).
- Automação nasce desativada e ativa ao publicar; se o post falhar, continua aguardando; publicado só no Facebook, fica aguardando (`llms (4).txt:988-991`).

## Riscos para a nossa implementação

1. **Carrossel com vídeo nos filhos não é suportado pelo que está documentado.** `slides[].image_url` é "URL pública da imagem do slide" (`llms.txt (Videos):203`), o 422 é para "não é uma imagem" (`llms.txt (Videos):381`), e o upload recusa `video/mp4` (`README.md:25`). O schema local só conhece `image_url` (`carrossel.schema.json:18-19`). O `CONTRATO-peca.md:186-187` assume que os provedores aceitam; para `expxflow` o adaptador precisa recusar carrossel misto com orientação, ou alguém precisa confirmar com chamada real ou pelo código da edge function. A própria documentação já divergiu do que estava no ar (`README.md:14-17`).
2. **Duas cópias da doc divergentes e schema local mais restrito que o servidor** (campos `public_reply_mode`, `public_reply_prompt`, `public_reply_fallback_text`). O núcleo precisa de **um** schema do provedor.
3. **Acoplamentos que viram `.env`/Alma** (M13): URL base embutida (`publicar.py:49`, `expxflow.py:5`); rótulo "Ver repositório" (`publicar.py:169`); resposta pública "Te chamei no direct!" (`publicar.py:173`) → texto da Alma; hora padrão 23:15 (`publicar.py:99`) e fuso fixo -03:00 (`publicar.py:88`) → `empresa.fuso` da Alma (M5); catálogo padrão `150-repositorios-carrossel.json` e log histórico `publicacoes-github.json` (`publicar.py:34-36,340`); `EXPX_PERFIL_NOME`, `EXPX_PERFIL_HANDLE`, `EXPX_AVATAR_PATH` (identidade no `.env`, `publicar/.env.example`) → Alma/porta-voz; mensagem de erro aponta "Configurações → API Keys" do produto (`publicar.py:55`). A URL base não tem nome canônico no catálogo (`CONTRATO-capacidades.md:153-165`); criar uma variável exige mudar o contrato (M12).
4. **Nomes de variável**: origem usa `EXPX_API_KEY`/`EXPX_CLIENT_ID` e regex de prefixo; o contrato exige `EXPXFLOW_API_KEY`/`EXPXFLOW_CLIENT_ID` (`CONTRATO-capacidades.md:167-168`).
5. **Idempotência desigual**: sem `Idempotency-Key` nos vídeos, uma nova tentativa depois de timeout pode duplicar o agendamento, e não há exclusão pela API.
6. **Escrita não atômica** de `uploads.json` e do log de publicações (`publicar.py:148,290`) contraria M15.
7. **Tipo de imagem**: só PNG é procurado (`publicar.py:116-119`); peça com JPEG ou WebP não seria achada.
8. `publish_now` é proibido por padrão pela regra dos vídeos (`Instragram-Videos/.claude/rules/publicacao.md:28-31`); o núcleo precisa decidir se `publicar` agora é permitido sem pedido explícito.
9. `trigger_id` no retorno do carrossel não está documentado; o registro de automação reaproveitável depende dele (`publicar.py:228`).

## Fonte

- `Instagram-Carrosseis/publicar/publicar.py` (linhas citadas)
- `Instagram-Carrosseis/publicar/contratos.py:23-124`
- `Instagram-Carrosseis/publicar/.env.example` (só nomes de variável)
- `Instagram-Carrosseis/contratos/{carrossel,post-unico,automacao,fonte-publicacao}.schema.json`, `CARROSSEL.md`, `POST-UNICO.md`, `AUTOMACAO.md`, `FONTE-PUBLICACAO.md`, `README.md`
- `Instagram-Carrosseis/contratos/grafias_keywords.py:1-56` (variações de palavra-chave: 0 a 4 por item, `MAXIMO_PADRAO = 4` em `:26`; palavra mínima 4 e variação mínima 5 caracteres em `:27,30`; "a documentação da API não diz se a comparação é por palavra inteira ou por trecho" em `:28-29`)
- `Instagram-Carrosseis/.claude/skills/publicar-serie/SKILL.md`, `.claude/agents/publicacao.md`, `.claude/rules/publicacao/publicacao-fluxo.md`, `.claude/hooks/publicacao/pre-bash-guard.sh:7-24` (bloqueia `publicar.py` sem `--dry-run`, exceto chave `plano-` com `publicacao_automatica: true`)
- `Instagram-Carrosseis/_referencias/llms (4).txt` e `openapi (4).json` (baixados 2026-09-11)
- `Instragram-Videos/pipeline/publish.py`, `pipeline/expxflow.py`, `.claude/rules/publicacao.md`
- `Instragram-Videos/docs/expx-flow/llms.txt`, `README.md` (baixados 2026-09-17)
- Base anterior: `Instagram-Carrosseis/docs/contratos-publicacao/base/api-publicacao.md`
