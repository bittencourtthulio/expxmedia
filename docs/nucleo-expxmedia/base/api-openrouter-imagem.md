# OpenRouter — geração de imagem

## Contrato de entrada

Provedor `openrouter` da capacidade `imagem_ia` (texto → imagem). A OpenRouter oferece **dois caminhos**: a Image API dedicada (`POST /api/v1/images`) e o caminho antigo por chat (`POST /api/v1/chat/completions` com `modalities`). Os dois estão documentados.

- **Autenticação:** `Authorization: Bearer <OPENROUTER_API_KEY>` — https://openrouter.ai/docs/guides/overview/multimodal/image-generation.md

**Caminho A — Image API dedicada (recomendado pela doc)** — https://openrouter.ai/docs/guides/overview/multimodal/image-generation.md
- `POST https://openrouter.ai/api/v1/images`, JSON.
- Obrigatórios: `model` (slug, ex. `google/gemini-3.1-flash-image`), `prompt`.
- Opcionais: `n` (1–10; provedores de imagem única rejeitam `n > 1`), `resolution` (`512`, `1K`, `2K`, `4K`), `aspect_ratio` (ex. `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `4:5`, `5:4`, `21:9`…; `auto` deixa o provedor escolher; "Providers clamp to their supported subset"), `size` (atalho: nível ou pixels explícitos `"2048x2048"`; pixels explícitos junto com `resolution`/`aspect_ratio` divergentes → 400), `quality` (`auto|low|medium|high`), `output_format` (`png|jpeg|webp|svg`), `background` (`auto|transparent|opaque`), `output_compression` (0–100), `seed`, `stream`, `input_references` (imagens de referência como URL HTTP(S) ou data URL base64), `user`, `provider.{only, order, ignore, sort, allow_fallbacks, options}`.
- **Descoberta de capacidades por modelo:** `GET https://openrouter.ai/api/v1/images/models` (lista, com `supported_parameters` por modelo) e `GET /api/v1/images/models/{slug}/endpoints` (parâmetros definitivos e preço por provedor). Parâmetro ausente = não suportado — mesma URL.
- Modelos Google listados em `GET /api/v1/images/models` (consulta pública feita em 2026-09-24): `google/gemini-2.5-flash-image`, `google/gemini-3-pro-image`, `google/gemini-3-pro-image-preview`, `google/gemini-3.1-flash-image`, `google/gemini-3.1-flash-image-preview`, `google/gemini-3.1-flash-lite-image`. Todos com `n` máx. 1. `aspect_ratio` aceitos, por exemplo em `gemini-3.1-flash-image`: `1:1, 1:4, 1:8, 2:3, 3:2, 3:4, 4:1, 4:3, 4:5, 5:4, 8:1, 9:16, 16:9, 21:9`; `resolution`: `512, 1K, 2K, 4K`; `input_references` 0–14 (0–3 no `gemini-2.5-flash-image`) — https://openrouter.ai/api/v1/images/models

**Caminho B — chat completions** — https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request.md
- `POST https://openrouter.ai/api/v1/chat/completions` com `messages`, `model` e `modalities: ["image", "text"]` (valores aceitos: `text`, `image`, `audio`).
- `image_config`: "Provider-specific image configuration options. Keys and values vary by model/provider", ex. `{"aspect_ratio": "16:9", "quality": "high"}`.

## Contrato de saída

**Caminho A** — https://openrouter.ai/docs/guides/overview/multimodal/image-generation.md
- `{"created", "data": [{"b64_json": "<base64>", "media_type": "image/png"}], "usage": {"prompt_tokens", "completion_tokens", "total_tokens", "cost"}}`.
- `b64_json` são **bytes em base64 puros** (sem o prefixo `data:`). `media_type` aparece quando o formato é identificável; é omitido quando não é.
- `usage.cost` em USD.
- Streaming (SSE): eventos `image_generation.partial_image`, `image_generation.completed` (com `b64_json`, `media_type`, `usage`) e `error`; termina em `data: [DONE]`.

**Caminho B** — https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request.md
- `choices[].message.images[].image_url.url`, uma **data URL** (`data:image/png;base64,...`); a descrição do campo diz "URL or base64-encoded data of the generated image".

Dimensões em pixels por `aspect_ratio` × `resolution`: NÃO DOCUMENTADO ("Concrete pixel dimensions are derived per-provider").

## Limites e cotas

- **Modelos pagos:** sem limite de requests da plataforma; ficam sujeitos ao rate limit do provedor upstream — https://openrouter.ai/docs/api_reference/limits
- **Modelos gratuitos (`:free`):** 20 req/min; 50 req/dia com menos de US$ 10 em créditos comprados; 1.000 req/dia com US$ 10 ou mais — https://openrouter.ai/docs/api_reference/limits
- **Créditos:** saldo negativo → 402 mesmo em modelo gratuito; limite opcional por chave; "in-flight budget" reserva o custo estimado das requisições em andamento e pode rejeitar mesmo com saldo positivo — https://openrouter.ai/docs/api_reference/limits
- **Consultar a chave:** `GET https://openrouter.ai/api/v1/key` → `limit_remaining`, `usage`, `usage_daily|weekly|monthly`, `free_model_daily_requests` — https://openrouter.ai/docs/api_reference/limits
- **Cobrança de imagem é tudo ou nada:** falha ou cancelamento não é cobrado e retorna `502`; preview parcial em stream não é cobrado — https://openrouter.ai/docs/guides/overview/multimodal/image-generation.md
- Preço por imagem: varia por endpoint, em `pricing[]` de `/api/v1/images/models/{slug}/endpoints` (ex. da doc: seedream-4.5 US$ 0,05/imagem; gpt-image-2 em 16:9 alta qualidade US$ 0,13 e 94 s) — https://openrouter.ai/docs/guides/overview/multimodal/image-generation.md
- Tamanho máximo do prompt / timeout do servidor: NÃO DOCUMENTADO.

## Erros conhecidos e tratamento

Formato: `{"error": {"code": <número>, "message": "...", "metadata": {...}}}` — https://openrouter.ai/docs/api_reference/errors-and-debugging

| HTTP | Significado (doc) | Tratamento |
|---|---|---|
| 400 | parâmetros inválidos/ausentes (ex.: `size` em pixels conflitando com `aspect_ratio`) | não repetir |
| 401 | chave ausente, inválida, desativada ou sessão OAuth expirada | não repetir |
| 402 | créditos insuficientes; `error.metadata.limit_source` distingue saldo da conta, limite da chave ou in-flight budget | não repetir; avisar |
| 403 | permissão, guardrail ou moderação; metadata `reasons[]`, `flagged_input` (até 100 caracteres), `provider_name`, `model_slug` | não repetir; mostrar motivo |
| 408 | timeout | repetir |
| 429 | rate limit (plataforma ou upstream) | backoff exponencial, respeitar `Retry-After` |
| 502 | modelo fora do ar / resposta inválida; **também a falha de geração de imagem (não cobrada)** | repetir, ou trocar de provedor via `provider` |
| 503 | nenhum provedor atende aos requisitos de roteamento | relaxar `provider.only` / `allow_fallbacks` |

- Erro no meio do stream chega como evento SSE com HTTP 200 já enviado — https://openrouter.ai/docs/api_reference/errors-and-debugging
- Metadata de erro de provedor: `error_type` e, opcionalmente, `provider_code` — mesma URL.

## Riscos para a nossa implementação

1. **Dois formatos de saída:** Caminho A devolve base64 puro (`b64_json`); Caminho B devolve data URL com prefixo. O decodificador precisa saber de qual caminho veio. Recomenda-se o Caminho A por ter `aspect_ratio`/`resolution` normalizados e descobríveis.
2. **`aspect_ratio` é "clamped" em silêncio** para o subconjunto do provedor: pedir 9:16 num modelo que não aceita pode vir em outra proporção sem erro. O motor deve validar contra `supported_parameters` antes e conferir as dimensões do PNG depois.
3. **Slugs de modelo mudam** (`-preview` coexistindo com estável; a doc cita `gemini-2.5-flash-image` e o catálogo já tem `gemini-3.x`). Não fixar slug no código: vir do `.env`/config e validar em `/api/v1/images/models`.
4. `media_type` pode faltar: detectar o formato pelos bytes (magic number) ao gravar o arquivo.
5. Modelos pagos não têm teto da plataforma; o gasto é controlado só por créditos e pelo limite por chave. Recomendar limite de crédito por chave no `como_habilitar`.
6. `provider.allow_fallbacks` (padrão permite) pode rotear para outro provedor com preço/qualidade diferente.
7. O Caminho B documenta `image_config` só como "provider-specific". As chaves aceitas pelo Gemini nesse caminho (ex. `image_size`) estão NÃO DOCUMENTADO na referência consultada.

## Fonte

Acesso em 2026-09-24:

- https://openrouter.ai/docs/llms.txt
- https://openrouter.ai/docs/guides/overview/multimodal/image-generation.md
- https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request.md
- https://openrouter.ai/docs/guides/features/server-tools/image-generation.md
- https://openrouter.ai/docs/api_reference/limits
- https://openrouter.ai/docs/api_reference/errors-and-debugging
- https://openrouter.ai/api/v1/images/models (catálogo público, consultado ao vivo)
