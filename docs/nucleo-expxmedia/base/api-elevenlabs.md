# ElevenLabs

## Contrato de entrada

Provedor `elevenlabs` da capacidade `narrar` (texto → voz com tempo por caractere).

- **Base URL:** `https://api.elevenlabs.io/v1/` — https://elevenlabs.io/docs/api-reference/authentication
- **Autenticação:** header `xi-api-key: ELEVENLABS_API_KEY`. Chaves aceitam restrição de escopo (endpoints), cota de créditos e allowlist de IP/CIDR — https://elevenlabs.io/docs/api-reference/authentication
- **Endpoint que o motor usa:** `POST /v1/text-to-speech/{voice_id}/with-timestamps` — https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
- **Path:** `voice_id` (string, obrigatório).
- **Query:**
  - `output_format` (enum, padrão `mp3_44100_128`). Valores: `alaw_8000`, `mp3_22050_32`, `mp3_24000_48`, `mp3_44100_32`, `mp3_44100_64`, `mp3_44100_96`, `mp3_44100_128`, `mp3_44100_192`, `opus_48000_32|64|96|128|192`, `pcm_8000|16000|22050|24000|32000|44100|48000`, `ulaw_8000`, `wav_8000|16000|22050|24000|32000|44100|48000` — https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
  - `enable_logging` (bool, padrão `true`; `false` = modo de retenção zero) — mesma URL.
  - `optimize_streaming_latency` (inteiro 0–4) — mesma URL.
- **Body (JSON):**
  - `text` (string, obrigatório).
  - `model_id` (string, padrão `eleven_multilingual_v2`).
  - `language_code` (string, opcional).
  - `voice_settings` (objeto, opcional): `stability` (0–1, padrão 0.5), `similarity_boost` (padrão 0.75), `style` (padrão 0), `use_speaker_boost` (bool, padrão true), `speed` (padrão 1.0) — https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
  - Faixa de `speed`: mínimo 0.7, máximo 1.2, padrão 1.0; "valores extremos podem afetar a qualidade" — https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/can-i-change-the-pace-of-the-voice
  - `seed` (inteiro 0–4294967295), `previous_text`, `next_text` (continuidade entre blocos), `apply_text_normalization` (`auto|on|off`, padrão `auto`) — https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
- **Modelos** — https://elevenlabs.io/docs/models:
  - `eleven_multilingual_v2`: 29 idiomas.
  - `eleven_v3`: 70+ idiomas.
  - `eleven_flash_v2_5`: 32 idiomas, ~75 ms (excluindo latência de aplicação e rede).
  - `eleven_turbo_v2_5`: descrito como "funcionalmente equivalente" ao flash_v2_5 e marcado como deprecado.
  - `eleven_v3_conversational`: ~280 ms (voltado a agentes).

## Contrato de saída

Resposta 200 em JSON — https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps:

- `audio_base64` (string): o áudio no `output_format` pedido, em base64.
- `alignment` com três arrays paralelos: `characters`, `character_start_times_seconds`, `character_end_times_seconds`.
- `normalized_alignment`: mesma estrutura, sobre o texto normalizado (números/abreviações por extenso).

Tempo por **palavra** não vem pronto: é derivado agrupando caracteres (NÃO DOCUMENTADO como a API trata pontuação/espaços no agrupamento).

## Limites e cotas

- **Caracteres por request** — https://elevenlabs.io/docs/models: `eleven_multilingual_v2` 10.000; `eleven_v3` 5.000; `eleven_flash_v2_5` 40.000. `eleven_turbo_v2_5` e `eleven_v3_conversational`: NÃO DOCUMENTADO na tabela.
- **Concorrência por plano** (requests simultâneos) — https://elevenlabs.io/docs/models:

| Plano | Multilingual v2 | Flash |
|---|---|---|
| Free | 2 | 4 |
| Starter | 3 | 6 |
| Creator | 5 | 10 |
| Pro | 10 | 20 |
| Scale | 15 | 30 |
| Business | 15 | 30 |
| Enterprise | elevada | elevada |

- **Formato por plano:** PCM/WAV em 44,1 kHz exige plano Pro ou superior; MP3 192 kbps exige Creator ou superior — https://elevenlabs.io/docs/help-center/troubleshooting/what-audio-formats-do-you-support (consultado via busca; mesma regra citada em https://elevenlabs.io/docs/api-reference/text-to-speech/convert).
- Cota mensal de créditos por plano: NÃO DOCUMENTADO nas páginas consultadas (fica na página de preços).
- Limite de requests por minuto (além de concorrência): NÃO DOCUMENTADO.

## Erros conhecidos e tratamento

Tabela oficial — https://elevenlabs.io/docs/eleven-api/resources/errors:

| HTTP | Tipo | Significado | Retry |
|---|---|---|---|
| 400 | `validation_error` / `invalid_request` | parâmetros inválidos, texto acima do limite, campo faltando | não |
| 401 | `authentication_error` (`invalid_api_key`, `missing_api_key`) | chave inválida/ausente | não |
| 402 | `payment_required` | créditos insuficientes | não |
| 403 | `authorization_error` | sem permissão (ex.: escopo da chave) | não |
| 404 | `not_found` | voz/recurso inexistente | não |
| 409 | `conflict` | conflito de estado | não |
| 422 | Unprocessable Entity (listado na página do endpoint) | corpo inválido | não |
| 429 | `rate_limit_error` (`rate_limit_exceeded`, `concurrent_limit_exceeded`) | excesso | sim, backoff exponencial / esperar requests em curso |
| 500 | `internal_error` | erro do servidor | sim |
| 503 | `service_unavailable` | indisponível | sim |

- A página de ajuda do 429 cita as mensagens `too_many_concurrent_requests` (limite de concorrência do plano) e `system_busy` (tráfego alto do serviço) — https://elevenlabs.io/docs/help-center/technical/api-error-code-429
- Cota estourada numa janela curta de cobrança retorna **401** (não 429), segundo a página de ajuda de 400/401 — https://help.elevenlabs.io/hc/en-us/articles/19572237925521-API-Error-Code-400-or-401 (conteúdo lido via resumo de busca; texto integral não conferido).

## Riscos para a nossa implementação

1. **Duas nomenclaturas de erro coexistem** (`too_many_concurrent_requests`/`system_busy` na ajuda vs. `concurrent_limit_exceeded`/`rate_limit_exceeded` na referência). O tratamento deve decidir por **status HTTP** e registrar o corpo, sem depender da string.
2. **401 pode significar cota estourada**, não chave errada. A mensagem ao usuário não pode afirmar "chave inválida" só pelo 401: precisa ler o corpo.
3. **Limite de caracteres muda por modelo** (5.000 no v3 vs. 10.000 no multilingual v2). Textos longos exigem fatiamento e costura dos `alignment` com deslocamento de tempo; usar `previous_text`/`next_text` para continuidade de prosódia.
4. **Concorrência baixa nos planos de entrada** (Free 2, Starter 3 no multilingual v2): o motor deve limitar paralelismo por configuração, não assumir.
5. `output_format` de alta qualidade depende do plano; pedir `pcm_44100`/`wav_44100` em plano abaixo do Pro deve falhar. Padrão seguro: `mp3_44100_128`.
6. `enable_logging=true` é o padrão (a ElevenLabs retém). Retenção zero (`false`) — NÃO DOCUMENTADO nesta página em quais planos é permitida.
7. `eleven_turbo_v2_5` está deprecado: não usar como padrão.
8. `alignment` vs `normalized_alignment`: para legenda fiel ao texto escrito, usar `alignment`; `normalized_alignment` diverge do texto original quando há números.

## Fonte

Acesso em 2026-09-24:

- https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
- https://elevenlabs.io/docs/api-reference/authentication
- https://elevenlabs.io/docs/models
- https://elevenlabs.io/docs/eleven-api/resources/errors
- https://elevenlabs.io/docs/help-center/technical/api-error-code-429
- https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/can-i-change-the-pace-of-the-voice
- https://elevenlabs.io/docs/help-center/troubleshooting/what-audio-formats-do-you-support
- https://help.elevenlabs.io/hc/en-us/articles/19572237925521-API-Error-Code-400-or-401
