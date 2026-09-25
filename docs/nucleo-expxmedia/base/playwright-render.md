# Playwright (Python)

## Contrato de entrada

Provedor `playwright` das capacidades `renderizar_html` (HTML/CSS → PNG) e `capturar_pagina` (screenshot e rolagem de página web). Os pontos de interesse são: screenshot com JavaScript desligado, instalação do Chromium e bloqueio de rede via `route`.

**Instalação** — https://playwright.dev/python/docs/intro e https://playwright.dev/python/docs/browsers
- Pacote `playwright` (PyPI; versão mais recente em 2026-09-24: **1.63.0**, segundo `pip index versions playwright`).
- "Each version of Playwright needs specific versions of browser binaries… every time you update Playwright, you might need to re-run the install CLI command." — https://playwright.dev/python/docs/browsers
- Instalar só o Chromium: `playwright install chromium`; com dependências do SO: `playwright install --with-deps chromium`; só as dependências: `playwright install-deps [chromium]` — https://playwright.dev/python/docs/browsers
- **Só o headless shell** (evita baixar o Chromium completo quando nada roda com janela e o `channel` não é definido): `playwright install --with-deps --only-shell` — https://playwright.dev/python/docs/browsers
- Local dos binários: `%USERPROFILE%\AppData\Local\ms-playwright` (Windows), `~/Library/Caches/ms-playwright` (macOS), `~/.cache/ms-playwright` (Linux); pasta alternativa via `PLAYWRIGHT_BROWSERS_PATH` (valendo na instalação **e** na execução) — https://playwright.dev/python/docs/browsers
- Tamanho de exemplo: `281M chromium-XXXXXX` — https://playwright.dev/python/docs/browsers
- Rede corporativa: `HTTPS_PROXY`, `NODE_EXTRA_CA_CERTS`, `PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT` (ms), `PLAYWRIGHT_DOWNLOAD_HOST` (espelho interno). Download padrão pela CDN da Microsoft — https://playwright.dev/python/docs/browsers
- Versões antigas de browser são removidas automaticamente quando o Playwright é atualizado; `playwright uninstall [--all]` — https://playwright.dev/python/docs/browsers
- **Requisitos do sistema:** Python 3.8+; Windows 11+, Windows Server 2019+ ou WSL; **macOS 14 (Sonoma) ou posterior**; Debian 12/13, Ubuntu 22.04/24.04/26.04 (x86-64 ou arm64) — https://playwright.dev/python/docs/intro

**JavaScript desligado** — https://playwright.dev/python/docs/api/class-browser#browser-new-context
- `browser.new_context(java_script_enabled=False)`: "Whether or not to enable JavaScript in the context. Defaults to `true`." É opção do **contexto**, não da página.
- Outras opções relevantes do mesmo método: `viewport` (padrão 1280x720), `device_scale_factor` (padrão 1), `offline` (padrão `false`), `service_workers` (`'allow'` padrão | `'block'`), `bypass_csp` (padrão `false`), `reduced_motion` (`'reduce'` | `'no-preference'`), `base_url`.

**Bloqueio de rede via `route`** — https://playwright.dev/python/docs/api/class-page (seção `page.route`) e https://playwright.dev/python/docs/network
- `page.route(url_glob_ou_regex, handler)` ou `context.route(...)` (vale também para popups e links abertos).
- "Once routing is enabled, every request matching the url pattern will stall unless it's continued, fulfilled or aborted."
- Handler: `route.abort(error_code=...)`, `route.continue_(headers|method|post_data|url)`, `route.fulfill(status|body|content_type|headers|json|path|response)`, `route.fallback()` — https://playwright.dev/python/docs/api/class-route
- `error_code` de `abort` (padrão `'failed'`): `aborted`, `accessdenied`, `addressunreachable`, `blockedbyclient`, `blockedbyresponse`, `connectionaborted`, `connectionclosed`, `connectionfailed`, `connectionrefused`, `connectionreset`, `internetdisconnected`, `namenotresolved`, `timedout`, `failed` — https://playwright.dev/python/docs/api/class-route
- Filtrar por tipo: `route.request.resource_type` (ex. `"image"`) — https://playwright.dev/python/docs/network
- Glob "must match the entire URL, not just a part of it" — https://playwright.dev/python/docs/network
- Alternativa sem handler: `new_context(offline=True)`.

**Carregar HTML e capturar** — https://playwright.dev/python/docs/api/class-page e https://playwright.dev/python/docs/screenshots
- `page.set_content(html, wait_until=..., timeout=...)` e `page.goto(url, wait_until=...)`; `wait_until` ∈ `domcontentloaded`, `load`, `networkidle`, `commit`. Timeout padrão de navegação: 30 s (0 desativa).
- `page.screenshot(...)`: `path`, `type` (`png` | `jpeg`), `quality` (0–100, só jpeg), `full_page`, `clip`, `omit_background` (fundo transparente), `scale` (`css` | `device`), `animations` (`allow` | `disabled`), `caret` (`hide` | `initial`), `mask`, `style` (CSS aplicado durante a captura), `timeout`. Sem `path`, retorna bytes. Também existe `locator.screenshot(...)` para um elemento só.

## Contrato de saída

- `page.screenshot()` grava em `path` e/ou retorna os bytes da imagem (PNG ou JPEG) — https://playwright.dev/python/docs/screenshots
- Dimensão em pixels = viewport × `device_scale_factor` quando `scale="device"`; com `full_page=True`, a altura é a da página rolável inteira — https://playwright.dev/python/docs/api/class-page e https://playwright.dev/python/docs/api/class-browser. A fórmula exata não é dada como tal: é inferência dos dois parâmetros.
- Requisições abortadas aparecem para a página como falha de rede com o `error_code` escolhido — https://playwright.dev/python/docs/api/class-route

## Limites e cotas

- Serviço local, sem cota.
- Timeout padrão de 30 s por navegação ou ação, ajustável com `page.set_default_timeout()` — https://playwright.dev/python/docs/api/class-page
- Disco: cerca de 281 MB para o Chromium (exemplo da doc) — https://playwright.dev/python/docs/browsers
- Limite de altura para `full_page` (o Chromium tem teto de textura): NÃO DOCUMENTADO.

## Erros conhecidos e tratamento

Notas da própria doc — https://playwright.dev/python/docs/api/class-page (`page.route`):
- "`page.route()` will not intercept requests intercepted by Service Worker… We recommend disabling Service Workers when using request interception by setting `service_workers` to `'block'`."
- "`page.route()` will not intercept the first request of a popup page. Use `browser_context.route()` instead."
- "The handler will only be called for the first url if the response is a redirect."
- "Enabling routing disables http cache."
- Handler que não chama `continue_`/`fulfill`/`abort` deixa a requisição parada ("will stall"), o que acaba em timeout.

Outros:
- Browser não instalado ou de versão diferente da do pacote: é preciso rodar `playwright install` de novo após atualizar o pacote — https://playwright.dev/python/docs/browsers
- Linux sem bibliotecas: `playwright install-deps chromium` (precisa de root; com proxy, rodar com `sudo HTTPS_PROXY=...`) — https://playwright.dev/python/docs/browsers
- Certificado autoassinado no proxy: "self signed certificate in certificate chain" → `NODE_EXTRA_CA_CERTS` — https://playwright.dev/python/docs/browsers
- Chrome/Edge da marca (via `channel`) usam o "new headless", com comportamento diferente do headless shell padrão (issue #33566) — https://playwright.dev/python/docs/browsers

## Riscos para a nossa implementação

1. **`java_script_enabled=False` é por contexto:** o motor precisa de um contexto dedicado para render estático; reusar o contexto de `capturar_pagina` (que precisa de JS) mistura as duas coisas.
2. Com JS desligado, se `page.evaluate()`/`wait_for_function` continuam funcionando (usados para medir overflow, fontes carregadas etc.): NÃO DOCUMENTADO na página lida. Validar num teste antes de depender disso.
3. **Fontes web com JS desligado e rede bloqueada:** `@font-face` remoto (Google Fonts) é bloqueado pelo `route`. O HTML de template deve referenciar fontes locais (`file://` ou `route.fulfill(path=...)`). Se `route` intercepta `file://`/`data:`: NÃO DOCUMENTADO.
4. **Service Workers escapam do `route`**: sempre `service_workers='block'` em `capturar_pagina`.
5. Popups: usar `context.route` em vez de `page.route`.
6. `route` desliga o cache HTTP, o que deixa `capturar_pagina` mais lento em páginas pesadas.
7. **Requisitos de SO do Playwright (macOS 14+) diferem dos do Remotion (macOS 15+)**: o `doctor` deve reportar cada capacidade separadamente.
8. A versão do pacote e a do browser andam juntas: fixar a versão do `playwright` no motor e rodar `playwright install chromium` (ou `--only-shell`) na instalação e em cada atualização; guardar os binários em `PLAYWRIGHT_BROWSERS_PATH` próprio da instalação, se quisermos isolamento.
9. Linux: `install-deps` precisa de root, o que não serve para instalação sem privilégio. `como_habilitar` deve explicar isso.
10. Download pela CDN da Microsoft no primeiro uso: sem rede, a capacidade fica indisponível.

## Fonte

Acesso em 2026-09-24:

- https://playwright.dev/python/docs/intro
- https://playwright.dev/python/docs/browsers
- https://playwright.dev/python/docs/screenshots
- https://playwright.dev/python/docs/network
- https://playwright.dev/python/docs/api/class-page
- https://playwright.dev/python/docs/api/class-browser#browser-new-context
- https://playwright.dev/python/docs/api/class-route
- `pip index versions playwright` (versão publicada no PyPI)
