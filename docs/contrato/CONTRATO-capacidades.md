# Contrato `expxmedia-capacidades` v1

Uma **capacidade** é algo que o sistema sabe fazer: renderizar um slide, narrar um texto,
gerar um avatar, publicar um post. Um **provedor** é quem faz: Playwright, ElevenLabs, HeyGen,
Expx Flow. Uma capacidade está **habilitada** quando pelo menos um provedor dela está
satisfeito — a chave está no `.env`, o login do CLI está feito, o binário existe.

A regra que governa tudo:

> **Recurso sem chave não existe.** Não aparece, não é sugerido, não quebra. Se a pessoa pedir
> explicitamente, recebe a instrução exata do que falta e onde conseguir.

Packs e templates **nunca falam de provedor**. Eles pedem capacidade (`narrar`); o motor escolhe
o provedor. Trocar ElevenLabs por outro serviço é mudar o `.env`, não um pack.

---

## O catálogo

| Capacidade | O que faz | Provedores (id) | Satisfeito por |
|---|---|---|---|
| `renderizar_html` | HTML/CSS → PNG | `playwright` | binário: Chromium do Playwright |
| `renderizar_motion` | cenas → MP4 | `remotion` | binários: Node ≥ 20, ffmpeg |
| `editar_video` | cortar, juntar, reenquadrar, normalizar áudio | `ffmpeg` | binário: ffmpeg |
| `narrar` | texto → voz, com tempo por caractere | `elevenlabs` | `ELEVENLABS_API_KEY` |
| `transcrever` | áudio/vídeo → texto com tempo por palavra | `whisper_local` | binário: whisper ou faster-whisper |
| `legendar` | alinhamento → legenda queimada e SRT | `local` | depende de `transcrever` ou `narrar` |
| `avatar` | áudio → vídeo de porta-voz falando | `heygen` | `HEYGEN_API_KEY` |
| `imagem_ia` | texto → imagem | `openrouter` | `OPENROUTER_API_KEY` |
| `rosto_ia` | imagem do porta-voz em cena nova | `higgsfield` | login do CLI `higgsfield` |
| `video_ia` | texto/imagem → vídeo curto | `higgsfield` | login do CLI `higgsfield` |
| `banco_imagens` | busca de foto de banco | `pexels` | `PEXELS_API_KEY` |
| `capturar_pagina` | screenshot e rolagem de página web | `playwright` | binário: Chromium do Playwright |
| `publicar` | publicar agora | `expxflow` · `meta_graph` · `youtube_api` | ver abaixo |
| `agendar` | publicar num horário futuro | `expxflow` · `meta_graph` | ver abaixo |
| `automacao_dm` | comentário com palavra-chave → mensagem direta | `expxflow` | `EXPXFLOW_API_KEY` + `EXPXFLOW_CLIENT_ID` |
| `metricas_instagram` | alcance, salvos, retenção por peça | `meta_graph` | `META_GRAPH_TOKEN` + `META_IG_USER_ID` |
| `metricas_youtube` | analytics do canal e dos vídeos | `youtube_api` | `YOUTUBE_CLIENT_SECRET_FILE` + OAuth feito |
| `anuncios_meta` | ler e operar conta de anúncios | `meta_graph` | `META_GRAPH_TOKEN` + `META_AD_ACCOUNT_ID` |
| `galeria_compartilhada` | baixar e enviar templates da galeria pública | `github` | login do `gh` + aceite (ver template) |

`publicar` e `agendar` por provedor:

| Provedor | Satisfeito por | Observação |
|---|---|---|
| `expxflow` | `EXPXFLOW_API_KEY` + `EXPXFLOW_CLIENT_ID` | agenda no servidor; hospeda a mídia |
| `meta_graph` | `META_GRAPH_TOKEN` + `META_IG_USER_ID` (+ `META_PAGE_ID` para Facebook); para `agendar`, também o **agendador local** instalado | a API do Instagram não agenda: quem agenda é o agendador local (abaixo), e **a máquina precisa estar ligada no horário** |
| `youtube_api` | `YOUTUBE_CLIENT_SECRET_FILE` + OAuth com escopo de upload | só `publicar` (com `publishAt`, que o próprio YouTube agenda) |

### O agendador local

Quando `agendar` vai usar `meta_graph`, o `/expxmedia:ambiente` (e o `doctor`) detecta o sistema
operacional e instala o **agendador local**: um programa Python do motor que fica rodando na
máquina e publica cada peça no horário marcado.

| Sistema | Como fica residente |
|---|---|
| macOS | LaunchAgent do usuário (`~/Library/LaunchAgents/`) |
| Windows | Tarefa do Agendador de Tarefas, ao fazer logon |
| Linux | serviço de usuário do systemd; na falta dele, cron |

O agendador:

- lê as publicações `agendada` com `provedor: meta_graph` nos `peca.json` da instalação;
- no horário, torna a mídia acessível por URL pública pelo tempo da publicação (túnel temporário,
  como o `tunel.py` dos vídeos faz hoje) e chama a Graph API;
- grava o resultado na peça e no rastro (`publicacao_concluida` / `publicacao_falhou`);
- ao voltar de um período desligado, **não publica atrasado em silêncio**: marca como `falhou`
  com o motivo e a peça volta para a pessoa decidir.

Enquanto o agendador não estiver instalado, `agendar` via `meta_graph` não está habilitada.

Capacidades **derivadas** declaram de quem dependem: `legendar` está habilitada se `narrar` **ou**
`transcrever` estiver. O motor resolve a dependência; o pack pede só `legendar`.

### O que já funciona sem chave nenhuma

`renderizar_html`, `renderizar_motion`, `editar_video`, `transcrever`, `legendar` (a partir de
transcrição) e `capturar_pagina`, desde que os binários estejam instalados — o `doctor` da central
os confere. Na prática: post único, carrossel, apresentação e reel sem narração saem no primeiro
dia.

## Provedor padrão

Quando mais de um provedor de uma capacidade está satisfeito, o padrão é escolhido no `.env`:

```sh
PROVEDOR_PUBLICAR=expxflow      # expxflow | meta_graph
PROVEDOR_AGENDAR=expxflow       # expxflow | meta_graph
```

O padrão vale para qualquer capacidade com mais de um provedor: `PROVEDOR_<CAPACIDADE>`, em
maiúsculas.

Regras:

1. **Com um só provedor satisfeito**, ele é usado, com ou sem `PROVEDOR_*`.
2. **Com mais de um e sem `PROVEDOR_*`**, vale a ordem da tabela acima (o primeiro listado). O
   `doctor` avisa que a escolha está implícita.
3. **`PROVEDOR_*` apontando para provedor não satisfeito** é erro com orientação. O sistema **não
   troca para o outro em silêncio** — publicar por um canal que a pessoa não escolheu é uma ação
   para fora que ela não autorizou.

## O `.env`

Criado por `/expxmedia:ambiente` a partir do `.env.example`, que a central gera juntando as
variáveis que **os packs instalados** declaram (ver [`CONTRATO-pack.md`](./CONTRATO-pack.md)).
Pack não instalado não polui o `.env`.

```sh
# ---------------------------------------------------------------------------
# ExpxMedia — ambiente desta instalação. NUNCA versione este arquivo.
# Cada bloco diz o que a chave libera. Deixe vazio o que não for usar.
# ---------------------------------------------------------------------------

# narrar — voz clonada do porta-voz em reels, aulas e apresentações narradas
# Onde conseguir: https://elevenlabs.io → Profile → API Keys
ELEVENLABS_API_KEY=

# publicar, agendar, automacao_dm — publicação no Instagram e Facebook pelo Expx Flow
EXPXFLOW_API_KEY=
EXPXFLOW_CLIENT_ID=

# publicar, agendar, metricas_instagram — Graph API direta da Meta
META_GRAPH_TOKEN=
META_IG_USER_ID=

# Provedor padrão quando houver mais de um
PROVEDOR_PUBLICAR=expxflow
```

`/expxmedia:ambiente` não pede chave nenhuma de uma vez. Ele mostra o que cada bloco libera,
pergunta o que a pessoa quer usar agora, e para cada escolha explica onde conseguir a chave. A
pessoa cola a chave **no arquivo**, nunca na conversa: chave colada na conversa fica no histórico
do modelo. Se ela colar mesmo assim, o sistema grava no `.env` e avisa que é bom girar a chave.

### Nomes canônicos

| Variável | Capacidades |
|---|---|
| `ELEVENLABS_API_KEY` | `narrar` |
| `HEYGEN_API_KEY` | `avatar` |
| `OPENROUTER_API_KEY` | `imagem_ia` |
| `PEXELS_API_KEY` | `banco_imagens` |
| `EXPXFLOW_API_KEY`, `EXPXFLOW_CLIENT_ID` | `publicar`, `agendar`, `automacao_dm` |
| `META_GRAPH_TOKEN`, `META_IG_USER_ID`, `META_PAGE_ID` | `publicar`, `agendar`, `metricas_instagram` |
| `META_AD_ACCOUNT_ID` | `anuncios_meta` |
| `YOUTUBE_CLIENT_SECRET_FILE` | `publicar` (YouTube), `metricas_youtube` |
| `PROVEDOR_<CAPACIDADE>` | escolha de provedor padrão |

Os projetos de origem usam nomes minúsculos (`elevenlabs_apikey`, `ExpxFlow_apikey`,
`PEXELS_APIKEY`). Na extração, todos passam para os nomes acima; nenhum pack lê nome antigo.

## Como a capacidade é verificada

O motor expõe uma consulta única, que pack, galeria e painel usam:

```json
{
  "capacidade": "narrar",
  "habilitada": true,
  "provedor": "elevenlabs",
  "provedores": [
    { "id": "elevenlabs", "satisfeito": true, "falta": [] }
  ],
  "como_habilitar": null
}
```

```json
{
  "capacidade": "avatar",
  "habilitada": false,
  "provedor": null,
  "provedores": [
    { "id": "heygen", "satisfeito": false, "falta": ["HEYGEN_API_KEY"] }
  ],
  "como_habilitar": "Coloque HEYGEN_API_KEY no .env. Onde conseguir: https://app.heygen.com → Settings → API."
}
```

A verificação é **local e barata**: confere presença da variável, do login e do binário. Ela
**não chama a API** do provedor — isso é trabalho do `doctor`, sob pedido (`expxmedia doctor
--online`), porque validar chave consome cota e pode demorar.

Capacidade que depende de porta-voz (`narrar`, `avatar`, `rosto_ia`) só está habilitada **para um
porta-voz** que tenha o id correspondente preenchido na Alma. A consulta
recebe o porta-voz quando a peça tem um.

## Quem usa a verificação, e como

| Quem | O que faz com ela |
|---|---|
| **Galeria** | template com requisito não habilitado **nem entra** na busca |
| **Skill de pack** | antes de produzir, confere os requisitos da peça; faltando, para e mostra `como_habilitar` |
| **Plano do dia** | não cria vaga para tipo de peça cujo requisito não está habilitado |
| **Painel** | mostra uma aba "Ambiente" com o que está ligado e desligado |
| **`doctor`** | lista tudo, e com `--online` testa cada chave de verdade |
