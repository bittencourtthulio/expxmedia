# HeyGen

## Contrato de entrada

Provedor `heygen` da capacidade `avatar` (áudio → vídeo de porta-voz falando). A doc atual é a **API v3**; v1/v2 (incluindo `POST /v2/video/generate`) estão em fim de vida (ver Riscos).

- **Base URL:** `https://api.heygen.com` — https://developers.heygen.com/docs/api-key.md
- **Autenticação:** header `X-Api-Key: <HEYGEN_API_KEY>`; falha retorna `unauthorized` (401). A chave é gerada em https://app.heygen.com/developers/api — https://developers.heygen.com/docs/api-key.md. A spec OpenAPI também lista `BearerAuth` (OAuth), que a doc descreve como "trial-scale" e cobrado dos créditos da assinatura web, não do plano de API — https://developers.heygen.com/llms.txt
- **Verificar chave/saldo:** `GET /v3/users/me` → perfil, `billing_type` (`wallet` com `wallet.remaining_balance` e `wallet.currency` `usd|credits`; ou `subscription` com `subscription.plan` e pools de créditos) — https://developers.heygen.com/user-profile.md

**Passo 1 — subir o áudio** — https://developers.heygen.com/assets.md
- `POST /v3/assets`, multipart, campo `file`. Tipos: imagem PNG/JPEG, vídeo MP4/WebM, **áudio MP3/WAV**, PDF. Máx. **32 MB**; MIME detectado pelos bytes.
- Resposta: `data.asset_id`, `data.url`, `data.mime_type`, `data.size_bytes`. (O exemplo em Python da página Audio to Video lê `["data"]["id"]` — divergência, ver Riscos.)
- Acima de 32 MB: fluxo direto em 3 passos — `POST /v3/assets/direct-uploads` (`filename`, `content_type`, `size_bytes` exato) → `PUT` dos bytes em `upload_url` com `upload_headers` antes de `expires_in_seconds` → `POST /v3/assets/{asset_id}/complete` (idempotente; o `asset_id` só vale depois). Teto informado em `max_bytes` — https://developers.heygen.com/assets.md

**Passo 2 — gerar o vídeo** — `POST /v3/videos` — https://developers.heygen.com/audio-to-video.md e https://developers.heygen.com/reference/create-video.md
- `type`: `avatar` (avatar/twin existente) ou `image` (qualquer foto de uma pessoa).
- `avatar_id` (obrigatório para `avatar`): ID do **look**, listado em `GET /v3/avatars/looks` — https://developers.heygen.com/docs/avatar-looks.md. Um digital twin é um avatar treinado a partir de vídeo — https://developers.heygen.com/generate-avatar-video.md
- Áudio: exatamente um de `audio_url` (URL HTTPS pública) ou `audio_asset_id`; mutuamente exclusivo com `script`. A duração do vídeo segue o áudio — https://developers.heygen.com/audio-to-video.md
- `engine`: padrão Avatar IV; `{ "type": "avatar_v" }` em looks elegíveis (`supported_api_engines`).
- `motion_prompt`, `expressiveness` (padrão `low`), `background` (`color` `#RRGGBB` ou `image` com `url`/`asset_id`), `remove_background` (twin treinado com matting), `output_format` `mp4` (padrão) ou `webm` (fundo transparente).
- Saída: `aspect_ratio` `16:9` (padrão), `9:16`, `4:5`, `5:4`, `1:1`, `auto`; `resolution` `720p`, `1080p`, `4k`; `fit` `cover|contain`; `caption` (SRT em `subtitle_url`; `"style": "default"` queima a legenda); `callback_url`, `callback_id`; `title` — https://developers.heygen.com/audio-to-video.md
- Recomendação da doc: `aspect_ratio: "auto"` e `resolution: "1080p"` — https://developers.heygen.com/llms.txt
- 4K: Avatar IV e V renderizam o avatar até 1080p; com `4k` ele é composto numa tela 4K, não renderizado nativamente. 4K nativo só para digital twins e studio avatars no Avatar III; photo avatar não tem 4K — https://developers.heygen.com/reference/create-video.md
- Header opcional `Idempotency-Key` (1–255 caracteres `[A-Za-z0-9_:.-]`): repetições em 24 h reproduzem a resposta original; repetição enquanto a primeira ainda roda → 409 `request_in_progress` — https://developers.heygen.com/reference/create-video.md

**Passo 3 — polling** — `GET /v3/videos/{video_id}` — https://developers.heygen.com/reference/get-video.md
- Alternativa: webhook (`POST /v3/webhooks/endpoints`, eventos `avatar_video.success`, `avatar_video.fail`; a resposta traz um `secret` para verificar a assinatura, mostrado uma vez só) — https://developers.heygen.com/docs/webhooks.md
- Intervalo de polling: NÃO DOCUMENTADO (o exemplo da doc usa 10 s).

## Contrato de saída

- `POST /v3/videos` → `{"data": {"video_id": "...", "status": "waiting", "output_format": "mp4"}}` — https://developers.heygen.com/audio-to-video.md
- `GET /v3/videos/{video_id}` → `data` (VideoDetail): `id`, `title`, `status` (enum `pending | processing | completed | failed`), `created_at`, `completed_at` (unix), `video_url` (**URL pré-assinada**), `thumbnail_url`, `gif_url`, `captioned_video_url`, `subtitle_url` (SRT), `duration` (s), `failure_code`, `failure_message` — https://developers.heygen.com/reference/get-video.md
- Download: `GET` simples em `video_url`. Validade da URL pré-assinada: NÃO DOCUMENTADO.
- Especificação de saída: 25 fps em vídeos com avatar; largura/altura entre 128 e 4.096 px; padrão 1080p — https://developers.heygen.com/docs/usage-limits.md

## Limites e cotas

Todos de https://developers.heygen.com/docs/usage-limits.md, salvo indicação:

- **Concorrência** (jobs assíncronos em andamento: renders de avatar, traduções, sessões de Video Agent): Pay-As-You-Go **10**; Enterprise **20** + burst de até +50 por tipo, cobrado a 1,5×. Estourar → 429 com `Retry-After`.
- **Rate limit:** todos os endpoints; 429 + `Retry-After` (segundos). Valor em requests/min: NÃO DOCUMENTADO.
- **Upload (`POST /v3/assets`):** 32 MB, inclusive para arquivos passados por URL.
- **Entradas de `POST /v3/videos`:** áudio WAV/MP3 até **50 MB**; imagem JPG/PNG até 50 MB e < 2K; vídeo MP4/WebM até 100 MB e < 2K. URLs precisam ser públicas, com extensão igual ao formato real; senão `download_failed`.
- **Duração do áudio — conflito na doc:** "Avatar Input — Audio input: Maximum 10 minutes (600 seconds)" (https://developers.heygen.com/docs/usage-limits.md) **vs.** "One request renders up to 30 minutes of audio" (https://developers.heygen.com/audio-to-video.md) e "Maximum duration: 30 minutes per scene" (usage-limits).
- **Aspect ratio — conflito na doc:** a seção "Output Video Specifications" diz "16:9 or 9:16" (usage-limits), enquanto Audio to Video aceita `16:9`, `9:16`, `4:5`, `5:4`, `1:1`, `auto`.
- Script de texto (caso não usemos áudio): 5.000 caracteres.
- **Créditos/preço:** preço por operação do plano self-serve fica só no dashboard (https://app.heygen.com/developers/api?modal=pricing); Enterprise não é publicado — https://developers.heygen.com/llms.txt. Custo em créditos por minuto de avatar: NÃO DOCUMENTADO nas páginas públicas consultadas.
- Lote: até 100 vídeos por `POST` de batch — https://developers.heygen.com/batch-videos.md (não previsto para o motor).

## Erros conhecidos e tratamento

Formato: `{"error": {"code", "message", "param"?, "doc_url"}}` — https://developers.heygen.com/docs/error-codes.md

| HTTP | `code` | Tratamento |
|---|---|---|
| 400 | `invalid_parameter` (`param` indica o campo) | não repetir; corrigir o pedido |
| 400 | `download_failed` | URL de áudio/imagem inacessível ou formato ≠ extensão; preferir `audio_asset_id` |
| 400 | `content_policy_violation`, `avatar_not_usable`, `avatar_consent_required` | terminal; orientar a pessoa (consentimento via `POST /v3/avatars/{group_id}/consent`) |
| 401 | `unauthorized` | chave inválida/expirada/ausente |
| 402 | `insufficient_credit` (mensagem diz saldo e necessário), `trial_limit_exceeded`, `subscription_required`, `plan_upgrade_required` (ex.: resolução ou avatar premium fora do plano) | não repetir; avisar a pessoa |
| 403 | `forbidden`, `insufficient_api_key_scope`, `resource_access_denied`, `phone_verification_required`, `voice_not_usable` | não repetir |
| 404 | `avatar_not_found` (inclui avatar ainda em treino), `asset_not_found` (upload não concluído), `video_not_found` | checar IDs |
| 409 | `request_in_progress` (Idempotency-Key em voo), `resource_not_ready` | esperar e repetir |
| 429 | `rate_limit_exceeded` | backoff exponencial respeitando `Retry-After` |
| 429 | `quota_exceeded` (cota do plano) | não adianta repetir já; avisar |
| 500 | `internal_error` | repetir com backoff |
| 503 | `service_unavailable` | transitório; repetir |

- Falha no render (depois de aceito) aparece como `status: failed` com `failure_code`/`failure_message` no GET, não como erro HTTP — https://developers.heygen.com/reference/get-video.md
- Chamadas v1/v2 retornam `Deprecation: true`, `Sunset: Sat, 31 Oct 2026 00:00:00 GMT` e um objeto `warning` no JSON — https://developers.heygen.com/endpoint-version-comparison.md

## Riscos para a nossa implementação

1. **Fim de vida da v2 em 2026-10-31/11-01** (cerca de 5 semanas depois da data desta ingestão) — https://developers.heygen.com/endpoint-version-comparison.md. O motor deve nascer na v3 (`/v3/assets`, `/v3/videos`); qualquer código de referência baseado em `v2/video/generate` ou `upload.heygen.com` está obsoleto.
2. **Contradições na doc:** limite de áudio (10 min vs. 30 min); aspect ratios; `status` inicial `waiting` no exemplo vs. enum `pending|processing|completed|failed`; campo do upload `asset_id` vs. `id` no exemplo Python. O motor deve tratar qualquer status fora de `completed`/`failed` como "em andamento" e ler `asset_id` com fallback — e o plano deve fatiar áudio de forma conservadora (≤ 10 min) até confirmar.
3. **Timeout de polling:** a doc não informa tempo típico de render; o motor precisa de teto configurável e de estado retomável (guardar o `video_id` na peça) para não gerar de novo, e pagar de novo, quando reiniciar.
4. **Cobrança dupla em retry:** usar `Idempotency-Key` no `POST /v3/videos`.
5. **OAuth vs. API key:** OAuth consome créditos da assinatura web e é "trial-scale"; o `.env` deve exigir `HEYGEN_API_KEY` (plano de API é cobrado à parte da assinatura web).
6. **Consentimento de digital twin**: sem consentimento, `avatar_consent_required`. É um passo fora do motor, que o `como_habilitar` precisa explicar.
7. **URL pré-assinada** com validade não documentada: baixar logo após `completed`.
8. **4K** em Avatar IV/V não é nativo: pedir `4k` só aumenta a tela.
9. Pedir `9:16` para reel com um twin gravado em 16:9 depende de `fit` (`cover` corta); o comportamento exato do corte: NÃO DOCUMENTADO.

## Fonte

Acesso em 2026-09-24:

- https://developers.heygen.com/llms.txt (redirecionado de https://docs.heygen.com/llms.txt)
- https://developers.heygen.com/audio-to-video.md
- https://developers.heygen.com/assets.md
- https://developers.heygen.com/reference/create-video.md
- https://developers.heygen.com/reference/get-video.md
- https://developers.heygen.com/docs/usage-limits.md
- https://developers.heygen.com/docs/error-codes.md
- https://developers.heygen.com/endpoint-version-comparison.md
- https://developers.heygen.com/docs/api-key.md
- https://developers.heygen.com/user-profile.md
- https://developers.heygen.com/docs/webhooks.md
- https://developers.heygen.com/docs/avatar-looks.md
- https://developers.heygen.com/generate-avatar-video.md
