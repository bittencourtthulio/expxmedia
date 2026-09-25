# Remotion — render e licença

## Contrato de entrada

Provedor `remotion` da capacidade `renderizar_motion` (cenas → MP4). O motor (Python) chama o Remotion por **CLI** (`npx remotion render`) ou por um script Node que usa `renderMedia()` de `@remotion/renderer`.

**Requisitos de sistema** — https://www.remotion.dev/docs
- "To use Remotion, you need at least Node 16 or Bun 1.0.3."
- "macOS 15 (Sequoia) or later is required. Older versions are not supported."
- "Linux distros need at least version 2.35 of Libc", mais pacotes extras; "Alpine Linux and nixOS are unsupported." Lista de pacotes por distro (Ubuntu 22.04/24.04, Debian, Amazon Linux 2023) em https://www.remotion.dev/docs/miscellaneous/linux-dependencies.md
- Windows: suportado em x64 para o Chrome Headless Shell — https://www.remotion.dev/docs/miscellaneous/chrome-headless-shell.md

**Chrome headless** — https://www.remotion.dev/docs/miscellaneous/chrome-headless-shell.md
- Desde a v4.0.247 o Remotion **instala sozinho** o "Chrome Headless Shell" em `node_modules/.remotion/chrome-headless-shell/[platform]/` (plataformas `mac-arm64`, `mac-x64`, `linux64`, `linux-arm64`, `win64`), com a versão fixada num arquivo `VERSION` (ex. `149.0.7790.0`). Se a versão não bater, ele apaga e baixa de novo.
- Pré-download recomendado para render em servidor: `npx remotion browser ensure` (CLI) ou `ensureBrowser()` (API).
- Plataformas: macOS x64/arm64, Windows x64, Linux x64 (com dependências), Linux arm64 (só Headless Shell).
- Usar um Chrome próprio (`--browser-executable` / `browserExecutable`) é possível, mas "may be less deterministic"; a recomendação é o binário fixado pelo Remotion.
- `--chrome-mode="chrome-for-testing"` só para render com GPU no Linux.

**FFmpeg:** "Since Remotion v4.0, Remotion comes bundled with a lightweight version of FFmpeg. An installation of FFmpeg is no longer needed." — https://www.remotion.dev/docs/ffmpeg.md

**Fixar versão** — https://www.remotion.dev/docs/version-mismatch.md
- Todos os pacotes (`remotion`, `@remotion/cli`, `@remotion/renderer`, etc.) precisam ter **exatamente a mesma versão**; usar versão exata, sem `^`. Conferir com `npx remotion versions`.
- Versão `latest` no npm em 2026-09-24: `4.0.528` (`npm view remotion dist-tags`); existe `4.1.0-alpha12` na tag `alpha`.

**CLI** — `npx remotion render <entry-point|serve-url>? <composition-id> <output-location>` — https://www.remotion.dev/docs/cli/render.md
- `--props`: JSON inline ou **caminho de arquivo JSON**. "Inline JSON string isn't supported on Windows shells… use a file name instead." Props "must be an object and serializable to JSON" — https://www.remotion.dev/docs/passing-props.md
- `--codec`: `h264` (padrão), `h265`, `av1`, `png`, `vp8`, `vp9`, `mp3`, `aac`, `wav`, `prores`, `h264-mkv`.
- `--concurrency`, `--width`, `--height`, `--fps`, `--duration`, `--crf` (não combina com `--video-bitrate` nem com aceleração de hardware), `--scale` (>0 e ≤16), `--timeout` (ms por frame para os `delayRender()`; padrão **30000**), `--overwrite` (padrão ligado), `--log` (`error|warn|info|verbose`), `--output`, `--public-dir`, `--binaries-directory`, `--browser-executable`, `--chrome-mode`, `--disallow-parallel-encoding` (menos memória, mais lento).

**API Node** — `renderMedia()` — https://www.remotion.dev/docs/renderer/render-media.md
- `serveUrl` (bundle local de `bundle()` ou URL), `composition` (de `selectComposition()`), `codec`, `outputLocation` (sem ele o resultado volta em buffer), `inputProps` (objeto JSON; lido com `getInputProps()`), `concurrency`, `timeoutInMilliseconds` (padrão 30000), `onProgress`, `cancelSignal` (`makeCancelSignal()`), `chromiumOptions`, `chromeMode`, `browserExecutable`, `onBrowserDownload`, `licenseKey` (v4.0.409+), `isProduction` (padrão `true`).

**Concorrência** — https://www.remotion.dev/docs/renderer/render-media.md e https://www.remotion.dev/docs/terminology/concurrency.md
- Número de abas do Chrome em paralelo; aceita número, porcentagem (`"50%"`) ou `null`. **Padrão: metade das threads de CPU.**
- "too high concurrency will lead to diminishing returns and to overload of the machines, which might crash a render."

**Fontes** — https://www.remotion.dev/docs/fonts.md
- Google Fonts via `@remotion/google-fonts` (`loadFont(...)`), via CSS `@import` (a partir da v2.2 o Remotion espera as fontes carregarem), ou fontes locais em `public/` com `@remotion/fonts` (v4.0.164+) e `staticFile()`.

## Contrato de saída

- CLI: arquivo em `output-location` (padrão: pasta `out`) — https://www.remotion.dev/docs/cli/render.md
- `renderMedia()` retorna `buffer` (quando não há `outputLocation`, senão `null`), `slowestFrames` (os 10 frames mais lentos) e `contentType` (ex. `video/mp4`) — https://www.remotion.dev/docs/renderer/render-media
- Progresso: callback `onProgress` na API; na CLI, só o log em texto. Formato de progresso legível por máquina na CLI: NÃO DOCUMENTADO.
- Códigos de saída do processo CLI: NÃO DOCUMENTADO.

## Limites e cotas

**Licença (o que vale hoje, Remotion 4.x)** — https://raw.githubusercontent.com/remotion-dev/remotion/main/LICENSE.md
- **Free License**: indivíduo; "a for-profit organization with up to 3 employees"; organização sem fins lucrativos; ou quem ainda está avaliando, sem uso comercial. Permite uso "non-commercially or commercially for the purpose of creating videos and images".
- Proibido: "copy or modify Remotion code for the purpose of selling, renting, licensing, relicensing, or sublicensing your own derivate of Remotion."
- **Company License** obrigatória para quem não se enquadra no Free.
- O próprio arquivo avisa: "In Remotion 5.0, the license will slightly change."

**Preço e definição de automação (FAQ atual)** — https://www.remotion.dev/docs/license/faq
- "Remotion for Creators": **US$ 25/mês por pessoa** que escreve código Remotion (inclusive com agentes de código).
- "Remotion for Automators": **US$ 0,01 por render, mínimo de US$ 100/mês**. Usando as duas opções, o mínimo combinado é US$ 100/mês.
- **Automação** = "owning code that programmatically calls" `renderMedia()`, `renderStill()`, `npx remotion render`, `npx remotion still`, `<Player>`, entre outros. **O ExpxMedia chamando `npx remotion render` se enquadra nessa definição.**
- 1 render = geração bem-sucedida de vídeo, áudio, GIF, still ou PDF; previews no Studio ou no Player não contam.
- Quem se qualifica para o Free License pode rodar automação e SaaS sem pagar.
- Uso comercial permitido "as long as you are not selling Remotion as a product itself or allowing people to circumvent cases where they would have to buy a license themselves". Aceito: usuários renderizarem vídeos personalizados a partir do seu template. Não aceito: usuários enviarem qualquer projeto Remotion para renderizar.
- Enterprise: mínimo de US$ 500/mês.
- Quem precisa do Automators deve manter a licença ativa enquanto a automação roda.

**Termos v5.0 (publicados como "Upcoming document", valem a partir do lançamento do Remotion 5.0)** — https://www.remotion.dev/docs/terms
- Os termos atuais em vigor são os v4.0 ("Latest update: November 23, 2023"), que remetem à licença do software — https://www.remotion.pro/terms-4-0
- "Native application distribution": é permitido usar o Remotion dentro de um app desktop (ex. Electron, Tauri) e distribuí-lo "provided the User introduces an abstraction layer between the end-user and the Remotion Software… the end-user must not have direct access to edit or upload Remotion code". "the regular licensing requirements still apply, including reporting renders". Se o app deixar de ser mantido, é preciso manter a Company License ativa por 1 ano após a última versão publicada.
- "End-user code access": se o usuário final **pode ver ou modificar** o código Remotion, ele passa a estar "directly engaging with a Remotion project" e precisa da **própria** Company License, caso se enquadre.
- "Download functionality and attribution": quem permite baixar um projeto ou código Remotion precisa indicar que ele é feito com Remotion e linkar `remotion.pro/license`.
- Telemetria obrigatória para "Remotion for Automators" na v5.0: `licenseKey` em `renderMedia()`; envia IP, produção/desenvolvimento e vídeo/still; nenhum conteúdo — https://www.remotion.dev/docs/telemetry
- Quem é Free declara isso com `licenseKey: "free-license"`. No render em servidor, a telemetria só é enviada quando `licenseKey` está definido — https://www.remotion.dev/docs/telemetry
- Headcount: "A license is mandatory when the total number of personnel across all involved parties that operate the Remotion Software reaches the threshold of four or more." — https://www.remotion.dev/docs/terms
- Uso sem licença: pagar as taxas devidas; em infração significativa, juros de 10% ao mês — https://www.remotion.dev/docs/terms

## Erros conhecidos e tratamento

- **Timeout de `delayRender()`**: "A delayRender() was called but not cleared after 28000ms. See https://remotion.dev/docs/timeout for help." Causas: `continueRender()` não chamado; asset de rede (fonte, imagem, vídeo) inacessível; **concorrência alta demais** (o Chrome falha ao carregar vídeo HTML5); vídeo grande no `<OffthreadVideo>`. Correções: `--timeout`, `timeoutInMilliseconds` ou `delayRenderTimeoutInMilliseconds` — https://www.remotion.dev/docs/timeout
- **Versões divergentes** entre pacotes `@remotion/*`: "subtle bugs or even complete breakage" — https://www.remotion.dev/docs/version-mismatch.md
- **Chrome ausente ou com versão errada**: baixado de novo automaticamente; em máquina sem rede no primeiro render, falha. Mitigação: `npx remotion browser ensure` no `doctor` — https://www.remotion.dev/docs/miscellaneous/chrome-headless-shell.md
- **Linux sem bibliotecas compartilhadas**: o Chrome Headless Shell não sobe; instalar a lista de pacotes — https://www.remotion.dev/docs/miscellaneous/linux-dependencies.md
- `av1` indisponível em Linux ARM64 GNU — https://www.remotion.dev/docs/cli/render.md
- `--props` inline quebra no Windows: sempre passar arquivo.
- Telemetria "never blocks or fails a render" — https://www.remotion.dev/docs/telemetry

## Riscos para a nossa implementação

1. **LICENÇA — risco principal para um produto distribuído.**
   - O ExpxMedia chama `npx remotion render` em código próprio: isso é "automação" pela definição da FAQ.
   - **Quem é o "User" que precisa da licença é quem opera o Remotion.** Com o ExpxMedia instalado e rodando na máquina do cliente, o cliente é quem renderiza. Se ele for empresa com fins lucrativos e **4 pessoas ou mais**, precisa da própria Company License (Automators: US$ 0,01/render, mínimo de US$ 100/mês), independentemente do que a Expx tiver.
   - Se o template/composição Remotion ficar **visível e editável** na instalação (código-fonte TSX em disco, "template de vídeo com código", galeria compartilhada), cai na cláusula "End-user code access" dos termos v5.0: o cliente se torna usuário direto e precisa da própria licença, se qualificar.
   - A Expx, se tiver 4 pessoas ou mais trabalhando no código Remotion, precisa de licença própria (Creators, US$ 25/pessoa/mês) para desenvolver os templates.
   - Distribuir o pacote com o Remotion dentro exige camada de abstração (o usuário não edita código Remotion) e **continuar reportando renders**; e manter licença por 1 ano após a última versão publicada (termos v5.0).
   - Operar um **serviço** onde o cliente envia o próprio projeto Remotion para renderizar é proibido sem autorização escrita.
   - **Decisão necessária na F2:** (a) o ExpxMedia avisa no `como_habilitar`/`doctor` que empresas com 4+ pessoas precisam de licença própria em remotion.pro e passa `licenseKey` configurável (`"free-license"` quando elegível); ou (b) a Expx negocia licença Enterprise que cubra os clientes; ou (c) `renderizar_motion` fica como capacidade opcional com aceite explícito dos termos. A doc **não diz** se a licença de um fornecedor que distribui software cobre os renders feitos por clientes nas próprias máquinas: é NÃO DOCUMENTADO e deve ir para a Remotion AG (endereço de contato na FAQ).
2. **Remotion 5.0 muda termos e torna telemetria obrigatória** para Automators. Fixar a versão 4.0.x exata protege só a parte técnica; a licença do 4.x continua valendo para o 4.x.
3. **macOS 15 (Sequoia) ou superior é obrigatório.** Instalações em macOS 14 ou anterior não rodam: o `doctor` precisa checar a versão do SO, não só Node/ffmpeg.
4. O contrato de capacidades diz que `renderizar_motion` é satisfeito por "Node ≥ 20, ffmpeg". A doc diz que o mínimo é Node 16 e que o **ffmpeg já vem embutido** desde a v4. O requisito real inclui SO suportado (macOS 15+, glibc ≥ 2.35, sem Alpine/nixOS) e o download do Chrome Headless Shell (rede no primeiro uso, cerca de centenas de MB, tamanho NÃO DOCUMENTADO).
5. Concorrência padrão = metade das threads; somada a outros jobs do motor (Playwright, ffmpeg), pode travar a máquina. Configurar explicitamente.
6. Fontes via Google Fonts dependem de rede no render; para render determinístico e offline, usar fontes locais em `public/` com `@remotion/fonts`.
7. Tudo que estiver em `--props` é serializado em JSON: sem `Date`, funções ou binários; mídia deve ir por caminho/URL servido pelo `public-dir`.

## Fonte

Acesso em 2026-09-24:

- https://www.remotion.dev/llms.txt
- https://www.remotion.dev/docs (requisitos de sistema)
- https://www.remotion.dev/docs/cli/render.md
- https://www.remotion.dev/docs/renderer/render-media.md
- https://www.remotion.dev/docs/passing-props.md
- https://www.remotion.dev/docs/fonts.md
- https://www.remotion.dev/docs/terminology/concurrency.md
- https://www.remotion.dev/docs/version-mismatch.md
- https://www.remotion.dev/docs/ffmpeg.md
- https://www.remotion.dev/docs/miscellaneous/chrome-headless-shell.md
- https://www.remotion.dev/docs/miscellaneous/linux-dependencies.md
- https://www.remotion.dev/docs/timeout
- https://www.remotion.dev/docs/telemetry
- https://www.remotion.dev/docs/license e https://www.remotion.dev/docs/license/faq (conteúdo idêntico em https://www.remotion.pro/faq)
- https://www.remotion.dev/docs/terms (Termos v5.0, "Upcoming document")
- https://www.remotion.pro/terms-4-0 (Termos v4.0 vigentes, atualizados em 2023-11-23)
- https://raw.githubusercontent.com/remotion-dev/remotion/main/LICENSE.md
- `npm view remotion dist-tags` (versão publicada)
