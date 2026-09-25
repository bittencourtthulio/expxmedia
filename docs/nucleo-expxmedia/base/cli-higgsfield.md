# Higgsfield (CLI `higgsfield`)

## Contrato de entrada

Provedor `higgsfield` das capacidades `rosto_ia` (imagem do porta-voz em cena nova, via Soul) e `video_ia` (texto/imagem → vídeo curto, via Seedance). O contrato do motor usa o **CLI**, satisfeito pelo login do CLI.
Evidências usadas: README oficial do CLI (GitHub), `--help` do CLI instalado (v1.1.26), esquemas retornados por `higgsfield model get` (consulta só de leitura, sem gerar nada) e as skills oficiais instaladas em `~/.claude/skills/higgsfield-*` (v0.12.0, idênticas às de `Instagram-Carrosseis/.claude/skills/higgsfield-*`; `diff -rq` sem diferença).

**Instalação** — https://github.com/higgsfield-ai/cli (README):
- `curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh | sh`, `brew install higgsfield-ai/tap/higgsfield` ou `npm install -g @higgsfield/cli` (multiplataforma, inclusive Windows).
- Fixar versão: `install.sh | sh -s -- --tag v1.1.2` ou `npm install -g @higgsfield/cli@1.1.2`.
- Pacote npm `@higgsfield/cli`, licença MIT; a versão local é 1.1.26, build de 2026-09-18 (`higgsfield --version`).
- Aliases do binário: `higgsfield`, `higgs`, `hf` (`higgsfield --help`).

**Autenticação:**
- `higgsfield auth login`: "browser-based OAuth login" (OAuth 2.0 PKCE); `auth logout`; `auth token` imprime o token atual (`higgsfield auth --help`).
- Credenciais guardadas localmente em `~/.config/higgsfield/credentials.json` (permissão 0600), ao lado de `config.json` (observado na máquina; o caminho não aparece na doc).
- "tokens are short-lived. Re-run `higgsfield auth login`" — README, seção Troubleshooting.
- **Checar se o provedor está satisfeito:** `higgsfield account status` → "Show account email, plan, and available credits"; falha com `Session expired` / `Not authenticated` quando não há login — skill `higgsfield-generate` (Step 0) e `higgsfield account --help`.
- Workspace de cobrança: `higgsfield workspace` (list / select / unset) — README.

**Comando de geração** — `higgsfield generate create <job_type> [--param valor]... [--wait] [--json]` (`higgsfield generate create --help`):
- Mídia: `--image-references`, `--video-references`, `--audio-references`, `--start-image`, `--end-image` (atalhos `--image`, `--video`, `--audio`). Aceitam **caminho local (upload automático) ou UUID** (upload id ou job id).
- `--wait` bloqueia até o fim; `--wait-timeout` (padrão `10m`), `--wait-interval` (padrão `3s`) — README, seção Flags.
- Esquema de parâmetros de cada modelo: `higgsfield model get <job_type> [--json]`. Estimar custo sem gerar: `higgsfield generate cost <job_type> ...` — skill `higgsfield-generate`, `references/troubleshooting.md`.

**`text2image_soul_v2`** (Higgsfield Soul 2.0, `type: image`) — `higgsfield model get text2image_soul_v2 --json`:
- `prompt` (obrigatório).
- `aspect_ratio`: `1:1` (padrão), `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`.
- `quality`: `1.5k` | `2k` (padrão `2k`). A skill diz que o backend mapeia para 720p/1080p.
- `custom_reference_id` (string|null) — o ID do Soul Character treinado.
- `image_references` (máx. 1), `style_id` (não combina com `image_references`), `seed`.
- A skill documenta `--soul-id <ref_id>`, mas o esquema do servidor declara `custom_reference_id` (ver Riscos).

**Soul Character (pré-requisito do `rosto_ia`)** — skill `higgsfield-soul-id`:
- `higgsfield soul-id create --name "<nome>" --soul-2 --image <foto>...` (5–20 fotos do rosto, ângulos e luz variados); `--soul-cinematic` para uso cinematográfico.
- `higgsfield soul-id wait <id>` (timeout padrão 30m); `soul-id list`, `soul-id get <id>`.
- "Soul training requires a paid plan (Basic+)"; erro `Minimum Basic plan required`.

**`seedance_2_5`** (Seedance 2.5, vídeo) — `higgsfield model get seedance_2_5 --json`:
- `prompt` (obrigatório); `mode`: `t2v` (padrão), `omni_reference`, `video_edit`, `video_extension`.
- `start_image`, `end_image` (objetos), `image_references`, `video_references`, `audio_references`.
- `duration` (inteiro, padrão 5; faixa **não** declarada no esquema; a skill diz "4–30s").
- `resolution`: `480p`, `720p` (padrão), `1080p`; `aspect_ratio`: `auto`, `21:9`, `16:9` (padrão), `4:3`, `1:1`, `3:4`, `9:16`.
- `generate_audio` (bool, **padrão true**), `bitrate_mode` (`standard` | `high`), `extension_mode` (`backward` | `forward`, só em `video_extension`).
- Regras do servidor: **`start_image` e `end_image` só são aceitos em `mode = omni_reference`**; `t2v` não aceita mídia; `omni_reference` exige ao menos uma mídia; no máximo 30 imagens (contando start/end) e 50 mídias no total.
- Exemplo da skill: `higgsfield generate create seedance_2_5 --prompt "camera dollies in" --mode omni_reference --start-image ./first.png --duration 12 --resolution 1080p --wait`.

**`seedance_2_0`** (alternativa com 4K) — `higgsfield model get seedance_2_0 --json`:
- `mode`: `std` | `fast`; `resolution`: `480p`, `720p`, `1080p`, `4k`; aceita `start_image` e `end_image` sem restrição de modo; `genre`; no máximo 9 imagens (contando start/end), 3 vídeos, 3 áudios e 12 mídias no total.
- A skill manda não passar `--generate-audio` para `seedance_2_0`, porque o esquema não o declararia. O esquema consultado **declara** `generate_audio` (padrão true). Contradição (ver Riscos).

## Contrato de saída

- Com `--wait`: imprime a URL do resultado no stdout. Com `--wait --json`: array com o objeto final do job. Sem `--wait`: os IDs dos jobs — skill `higgsfield-generate`.
- Objeto de job (`higgsfield generate list --json`, observado): `id`, `job_type`, `display_name`, `status`, `params`, `result_url`, `min_result_url`, `created_at`.
- Valores de `status` no CLI: só `completed` observado. A skill cita falhas `failed`, `nsfw`, `ip_detected` (`references/troubleshooting.md`). Lista completa: NÃO DOCUMENTADO para o CLI.
- Retomar job: `higgsfield generate get <id> --json`, `higgsfield generate wait <id>` (`--interval` 3s, `--timeout` 10m) — `higgsfield generate wait --help`.
- Retenção da `result_url` no CLI: NÃO DOCUMENTADO. Na API HTTP da Higgsfield (produto separado, abaixo), "Output files are available for at least seven days" — https://docs.higgsfield.ai/docs/concepts/requests

**API HTTP (alternativa, não usada pelo contrato atual)** — https://docs.higgsfield.ai/docs:
- Base `https://api.higgsfield.ai`, header `Authorization: Key ${HF_API_KEY_ID}:${HF_API_KEY_SECRET}` (chaves em https://console.higgsfield.ai).
- Status `queued`, `in_progress`, `completed`, `failed`, `nsfw`, `canceled`; cancelamento só em `queued` — https://docs.higgsfield.ai/docs/concepts/requests
- Se os mesmos modelos (Soul 2.0, Seedance 2.5) existem nessa API: NÃO DOCUMENTADO nas páginas lidas.

## Limites e cotas

- Cobrança em **créditos**; saldo em `higgsfield account status`; extrato em `higgsfield account transactions` (`higgsfield account --help`).
- Custo por job: `higgsfield generate cost ...`. Tabela pública de créditos por modelo: NÃO DOCUMENTADO nas fontes lidas.
- Rate limit: existe (`Higgsfield API error (HTTP 429)`, "Back off"); valores NÃO DOCUMENTADO — skill, `references/troubleshooting.md`.
- Concorrência de jobs: NÃO DOCUMENTADO.
- Treinar Soul exige plano Basic ou superior — skill `higgsfield-soul-id`.
- Limites de mídia por modelo: ver regras do esquema acima (Seedance 2.5: até 30 imagens e 50 mídias; Seedance 2.0: até 12 mídias).

## Erros conhecidos e tratamento

Mensagens documentadas na skill (`higgsfield-generate` SKILL.md e `references/troubleshooting.md`) e no README:

| Mensagem | Causa | Tratamento |
|---|---|---|
| `Session expired.` / `Not authenticated.` | token curto expirou / sem login | capacidade passa a "não satisfeita"; orientar `higgsfield auth login` (interativo, abre navegador) |
| `Stored credentials are for ... but current environment ...` | credencial de outro ambiente | `higgsfield auth login` |
| `Missing required params: prompt` | faltou prompt | erro de chamada |
| `Invalid values: <param>=<v> (allowed: ...)` | enum inválido | validar antes contra `model get` |
| `Unknown params: <name>` | flag não declarada no esquema | idem |
| `Unknown model "<name>"` | `job_type` saiu do catálogo | `higgsfield model list` |
| `Job ended with status "failed"` | falha no servidor, muitas vezes segurança do prompt | reformular; não repetir igual |
| `nsfw` / `ip_detected` | política de conteúdo | reformular |
| `Timeout after 10m` | modelo lento | aumentar `--wait-timeout` ou retomar com `generate wait <id>` (não recriar) |
| `Higgsfield API error (HTTP 429)` | rate limit | backoff |
| `Failed to decode response. Body: <html>...captcha-delivery...` | anti-bot (CloudFlare/DataDome) | esperar 30 s e repetir |
| `Minimum Basic plan required` | Soul em plano grátis | avisar |

- O servidor também devolve `adjustments` para coerções não fatais (ex.: `aspect_ratio=99:99` vira o mais próximo) — skill `higgsfield-generate`.
- Códigos de saída do processo (exit codes): NÃO DOCUMENTADO.

## Riscos para a nossa implementação

1. **Login interativo por OAuth no navegador, com token de vida curta:** não serve para o agendador/execução sem pessoa na frente. Cada `Session expired` exige ação humana. O `doctor` deve checar com `higgsfield account status` antes de cada lote, não só na instalação.
2. **Contrato instável e dirigido pelo servidor:** parâmetros vêm de `model get` e mudam sem versão do CLI (ex.: skill diz `--soul-id`, esquema diz `custom_reference_id`; skill diz que `seedance_2_0` não aceita `generate_audio`, esquema aceita). O motor deve validar parâmetros contra `higgsfield model get <jt> --json` em tempo de execução e registrar o esquema usado na peça.
3. **`end_image` no Seedance 2.5 exige `--mode omni_reference`**; sem isso, o servidor rejeita. Em `seedance_2_0` não há essa restrição.
4. **`generate_audio` tem padrão `true`** no Seedance 2.0/2.5: b-roll sai com áudio gerado (e possivelmente custo maior) se o motor não passar `false`.
5. O saldo mostrado em `account status` inclui **o e-mail da conta**: não gravar a saída crua em logs ou no rastro.
6. Parsing de saída: usar sempre `--json`; o texto padrão é para humanos. Os campos do job (`result_url`, `status`) foram observados, não documentados formalmente.
7. Um `--wait` interrompido não cancela o job: guardar o `id` (com `--json` sem `--wait`) e usar `generate wait <id>`, para não pagar duas vezes.
8. Anti-bot (DataDome) pode responder HTML em vez de JSON: tratar erro de parse como transitório.
9. A API HTTP oficial (chave ID+secret) seria uma alternativa não interativa, mas cobre um catálogo de modelos não confirmado. Decisão para a F2.

## Fonte

Acesso em 2026-09-24:

- https://github.com/higgsfield-ai/cli (README em https://raw.githubusercontent.com/higgsfield-ai/cli/main/README.md)
- CLI local `higgsfield` 1.1.26: `--help`, `auth --help`, `account --help`, `generate --help`, `generate create --help`, `generate wait --help`, `model get text2image_soul_v2|seedance_2_5|seedance_2_0 --json`, `generate list --json` (só a estrutura)
- `~/.claude/skills/higgsfield-generate/SKILL.md` e `references/{troubleshooting,media-inputs}.md` (v0.12.0)
- `~/.claude/skills/higgsfield-soul-id/SKILL.md` (v0.12.0)
- Demais `~/.claude/skills/higgsfield-*/SKILL.md` (brandkit, marketplace-cards, product-photoshoot, video-explainer, websites, youtube-thumbnail): lidos por varredura, sem conteúdo adicional sobre auth/limites
- https://docs.higgsfield.ai/docs e https://docs.higgsfield.ai/docs/concepts/requests (API HTTP)
- https://docs.higgsfield.ai/llms.txt (tentado, 404)
