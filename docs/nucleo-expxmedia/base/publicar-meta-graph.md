# Publicação direta pela Graph API da Meta (provedor `meta_graph` de `publicar` e `agendar`)

Nenhum projeto de origem **publica** pela Graph API: o `meta_graph` é provedor novo. O que existe
hoje é cliente de **leitura** (`Instragram-Videos/pipeline/insights.py`, Graph v23.0) e um cliente
genérico com retentativa (`ExpxMeta/meta/client.py`, Graph v21.0) usado para anúncios. Este arquivo
junta o que a documentação oficial diz sobre publicação no Instagram com o padrão de cliente que já
existe.

Documentação oficial acessada em 2026-09-24 (todas as URLs em **Fonte**).

## Contrato de entrada

**Credenciais** (nomes canônicos em `ExpxMedia/docs/contrato/CONTRATO-capacidades.md:63,162`):
`META_GRAPH_TOKEN`, `META_IG_USER_ID`, `META_PAGE_ID` (Facebook). A origem lê `META_GRAPH_TOKEN`
do `.env` por regex ou do ambiente (`Instragram-Videos/pipeline/lib.py:151-165`) e por parser de
`.env` (`ExpxMeta/meta/config.py:46-74`). Escopos pedidos hoje, só de leitura: `instagram_basic`,
`instagram_manage_insights`, `instagram_manage_comments`, `pages_show_list`,
`pages_read_engagement` (`lib.py:163-165`).

**Permissões para publicar no Instagram** (oficial): `instagram_basic`, `instagram_content_publish`,
`pages_read_engagement` (referência IG User Media); em `media_publish` também `ads_management` ou
`ads_read` se o usuário tiver papel no Business Manager, e tarefa `MANAGE` ou `CREATE_CONTENT` na
Página (referência IG User Media Publish).

**Host**: `graph.instagram.com` ou `graph.facebook.com`; `rupload.facebook.com` só para upload
retomável de vídeo (guia Content Publishing).

**Fluxo em duas etapas** (guia Content Publishing):

1. `POST /{ig-user-id}/media` cria um **contêiner**:
   - imagem: `image_url` (URL pública), `caption`;
   - reel: `media_type=REELS`, `video_url`, opcionais `share_to_feed`, `cover_url`, `thumb_offset` (ms, padrão 0);
   - item de carrossel: `is_carousel_item=true` com `image_url` **ou** `video_url` (`media_type=VIDEO` para vídeo);
   - carrossel: `media_type=CAROUSEL`, `children` = até 10 ids de contêiner, `caption`;
   - vídeo grande: `upload_type=resumable` via `rupload.facebook.com`.
2. Consultar `GET /{container-id}?fields=status_code` até `FINISHED`.
3. `POST /{ig-user-id}/media_publish` com `creation_id` = id do contêiner.

**Facebook (Página)**, para `META_PAGE_ID`: `POST /{page_id}/photos` para foto; agendamento nativo com
`published=false` + `scheduled_publish_time`; permissões `pages_manage_posts`,
`pages_manage_engagement`, `pages_read_engagement`, `pages_read_user_engagement`, `publish_video`
para vídeo (guia Pages API Posts). Carrossel de Página e vídeo de Página: NÃO DOCUMENTADO nesta
ingestão (a página remete à Video API, não lida).

**Padrão de cliente existente** (`ExpxMeta/meta/client.py`):
- `Client(token, url_base)`, base `https://graph.facebook.com/{VERSAO_API}` (`client.py:34-36`);
  versão única em constante `VERSAO_API = "v21.0"` (`ExpxMeta/meta/config.py:17`).
- `get` põe `access_token` na query (`client.py:44-48`); `post` põe `access_token` no **corpo JSON**
  (`client.py:54-58`).
- `__repr__` mascara o token (`client.py:39-40`; `config.py:34-38`).
- `insights.py` usa a versão v23.0 em constante própria (`Instragram-Videos/pipeline/insights.py:37`)
  e nunca ecoa a URL com o token (`insights.py:63-64`).

## Contrato de saída

- Criação de contêiner: `{ "id": "<container-id>" }` (guia Content Publishing; formato idêntico ao
  de `media_publish`).
- `status_code`: `EXPIRED`, `ERROR`, `FINISHED`, `IN_PROGRESS`, `PUBLISHED` (guia Content Publishing).
- `media_publish`: `{ "id": "<ig-media-id>" }`; ler, atualizar e excluir pelo endpoint não são
  suportados (referência IG User Media Publish).
- `permalink` da mídia publicada: obtido por `GET /{ig-media-id}?fields=permalink` — padrão usado em
  leitura em `insights.py:82`; que o `media_publish` o devolva: NÃO DOCUMENTADO.
- Cota: `GET /{ig-user-id}/content_publishing_limit` devolve `quota_usage` e `config` com
  `quota_total` e `quota_duration` (referência Content Publishing Limit).
- Mapeamento para `peca.json.publicacoes[]` (`CONTRATO-peca.md:127-139`): `id_externo` ← id da mídia;
  `url` ← `permalink`; `publicada_em` ← hora do `media_publish`. Derivação nossa; a origem não tem.

## Limites e cotas

| Limite | Valor | Fonte |
|---|---|---|
| Publicações por 24 h (janela móvel) | **50** na referência `media_publish` e `content_publishing_limit` (`quota_total` 50, `quota_duration` 86400 s); **100** no guia Content Publishing. Divergência oficial; carrossel conta como 1 | refs. IG User Media Publish e Content Publishing Limit; guia Content Publishing |
| Itens por carrossel | até 10, imagens, vídeos ou mistura | ref. IG User Media |
| Reel dentro de carrossel | "Reels cannot appear in carousels" | ref. IG User Media |
| Recorte no carrossel | todas as imagens cortadas pelo primeiro item; padrão 1:1 | guia Content Publishing |
| Validade do contêiner | 24 h, depois `EXPIRED` | ref. IG User Media; guia |
| Consulta de status | "once per minute, for no more than 5 minutes" | guia Content Publishing |
| Imagem | **só JPEG**; ≤ 8 MB; proporção 4:5 a 1.91:1; largura 320–1440 px; sRGB | ref. IG User Media |
| Reel | MOV ou MP4, moov no início, sem edit lists; H.264 ou HEVC, GOP fechado, 4:2:0; AAC ≤ 48 kHz, 1–2 canais, 128 kbps; 23–60 fps; largura ≤ 1920; proporção 0.01:1 a 10:1 (recomendado 9:16); ≤ 25 Mbps; 3 s a 15 min; ≤ 300 MB | ref. IG User Media |
| Vídeo dentro de carrossel (specs próprias) | NÃO DOCUMENTADO separadamente | ref. IG User Media |
| Legenda | até 2200 caracteres, 30 hashtags, 20 @menções | ref. IG User Media |
| **Agendamento no Instagram** | **nenhum parâmetro de agendamento** no guia nem nas referências de `media` e `media_publish`; a publicação ocorre no `media_publish` | guia Content Publishing; refs. |
| Agendamento de Página do Facebook | `scheduled_publish_time` entre 10 min e 30 dias no futuro | guia Pages API Posts |
| Versões | v21.0 disponível até 2027-01-21; v23.0 até 2027-10-08; mais nova v26.0 (2026-07-29) | Graph API Changelog Versions |
| Retentativa do cliente | 5 tentativas, pausa 1·2^n s | `ExpxMeta/meta/client.py:24-26,80-81` |
| Timeout do cliente | 30 s | `client.py:70`; `insights.py:57` |

Observação: sites de terceiros afirmam existir agendamento nativo para feed "entre 10 minutos e 75
dias" (busca web de 2026-09-24, p. ex. posteverywhere.ai). A documentação oficial lida não confirma;
tratamos como NÃO DOCUMENTADO e seguimos o contrato (agendador local).

## Erros conhecidos e tratamento

Códigos oficiais de publicação (referência Error Codes):

| Código | Subcódigo | Significado | Ação oficial |
|---|---|---|---|
| -2 | 2207003 | download da mídia demorou demais | tentar de novo |
| -2 | 2207020 | mídia expirou | novo contêiner |
| -1 | 2207001 | erro de servidor | tentar de novo |
| -1 | 2207032 | falha ao criar contêiner | tentar de novo |
| 1 | 2207057 | `thumb_offset` além da duração | corrigir offset |
| 4 | 2207051 | atividade restrita (spam) | revisar; recorrer |
| 9 | 2207042 | **limite diário de publicação atingido** | tentar no dia seguinte |
| 24 | 2207006 | mídia não encontrada | novo contêiner |
| 24 | 2207008 | contêiner expirado ou inexistente | tentar em 2 min ou novo contêiner |
| 25 | 2207050 | conta restrita ou inativa | resolver no app |
| 100 | 2207028 | carrossel exige 2 a 10 itens | ajustar |
| 352 | 2207026 | formato de vídeo não suportado | MP4 ou MOV |
| 9004 | 2207052 | URI inalcançável ou inválida | URL pública válida |
| 9007 | 2207027 | contêiner não pronto | aguardar `FINISHED` |
| 36000 | 2207004 | imagem > 8 MiB | comprimir |
| 36003 | 2207009 | proporção inválida | 4:5 a 1.91:1 |

Tratamento de origem (`ExpxMeta/meta/client.py:1-9,95-104`; `ExpxMeta/meta/erros.py`):
- `190` ou `OAuthException` → `TokenError`, sem retentativa.
- `4, 17, 32, 613, 80004` → `RateLimitError`, retenta com backoff; status ≥ 500 também retenta.
- demais → `ErroGraph` com `codigo` e `subcodigo`.
- `insights.py:60-64`: 190 vira mensagem que cita o **nome** `META_GRAPH_TOKEN`, nunca a URL.

## Riscos para a nossa implementação

1. **Retentativa de POST em 5xx pode duplicar publicação.** `client.py:77-82` retenta qualquer método em 5xx; em `media_publish` isso pode publicar duas vezes. O código `-1/2207001` pede nova tentativa oficialmente, mas sem chave de idempotência na Graph API (NÃO DOCUMENTADO que exista). O adaptador precisa retentar `media` e **não** retentar `media_publish` às cegas: antes, consultar `status_code` (`PUBLISHED`).
2. **Códigos retentáveis do ExpxMeta vêm da Marketing API**, não da publicação: `9/2207042` (limite diário) não está no conjunto e não deve ser retentado; `-2/2207003`, `-1/2207001`, `9007/2207027` pedem espera, não erro final.
3. **PNG não é aceito**: slides saem em PNG (`Instagram-Carrosseis/publicar/publicar.py:116-119`); precisa converter para JPEG sRGB. Proporção **9:16 em imagem é recusada** (4:5 a 1.91:1), então post único 9:16 não publica pelo `meta_graph`.
4. **Limite de 10 itens** contra 20 do Expx Flow (`llms (4).txt:202`): carrossel de 11–20 slides é aceito por um provedor e recusado pelo outro.
5. **Reel não entra em carrossel**; vídeo como item do carrossel usa `media_type=VIDEO`. O `CONTRATO-peca.md:181-187` (carrossel misto) é viável neste provedor, com recorte pelo primeiro item.
6. **URL pública durante o processamento**: a mídia precisa estar acessível "at publishing attempt time"; com túnel, ele deve ficar aberto até `FINISHED` (até ~5 min de consulta), não só durante a chamada (ver `tunel-url-publica.md`).
7. **Cota divergente (50 vs 100)**: ler `content_publishing_limit` em vez de assumir.
8. **Versões diferentes na origem** (v21.0 e v23.0) — o núcleo precisa de uma constante única; v21.0 expira em 2027-01-21.
9. **Acoplamento de conta**: `insights.py:38` fixa o `@` da conta (`USUARIO`) e descobre o `ig_user_id` por nome de usuário em `me/accounts` (`insights.py:74-78`); no núcleo isso vira `META_IG_USER_ID` do `.env`. Os limiares `alcance-min` 150 (`insights.py:42`) e o deslocamento fixo de -3 h (`insights.py:105`) viram `empresa.fuso` da Alma.
10. Token no corpo do POST e na query do GET: qualquer log de requisição expõe o segredo (M14); o `__repr__` mascarado precisa ser mantido e os erros não podem ecoar URL.
11. Token de usuário "dura horas" (`Instragram-Videos/pipeline/lib.py:154-155`): um agendador residente precisa de token de longa duração ou de sistema; como obtê-lo: NÃO DOCUMENTADO nesta ingestão.

## Fonte

- Guia Content Publishing — https://developers.facebook.com/docs/instagram-platform/content-publishing (acesso 2026-09-24)
- Referência IG User Media — https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media (acesso 2026-09-24)
- Referência IG User Media Publish — https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media_publish (acesso 2026-09-24)
- Referência IG User Content Publishing Limit — https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/content_publishing_limit (acesso 2026-09-24)
- Códigos de erro — https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/error-codes (acesso 2026-09-24)
- Pages API Posts — https://developers.facebook.com/docs/pages-api/posts (acesso 2026-09-24)
- Graph API Versions — https://developers.facebook.com/docs/graph-api/changelog/versions (acesso 2026-09-24)
- `ExpxMeta/meta/client.py`, `ExpxMeta/meta/config.py`, `ExpxMeta/meta/erros.py`
- `Instragram-Videos/pipeline/insights.py:37-78`, `Instragram-Videos/pipeline/lib.py:151-178`
