# Capturar página (capacidade `capturar_pagina`)

Fonte extraída: `Instragram-Videos/pipeline/capture.py` (DOM do GitHub), `Instragram-Videos/pipeline/capture_site.py`
(qualquer site: laboratório de LLM, changelog) e `Instragram-Videos/pipeline/stitch.py`, rodando **dentro do
browser-harness** (CDP no Chrome do usuário). Regra: `Instragram-Videos/.claude/rules/captura/cdp.md`.

## Contrato de entrada

- Execução: `REPO_URL=<url> OUT=videos/<slug> browser-harness < pipeline/capture.py` ou
  `SITE_URL=<url> OUT=videos/<slug> browser-harness < pipeline/capture_site.py`
  (`Instragram-Videos/pipeline/capture.py:1-5`; `Instragram-Videos/pipeline/capture_site.py:1-6`). Os helpers
  `new_tab, wait_for_load, js, cdp, list_tabs, switch_tab, current_tab, close_tab` vêm pré-importados.
- Variáveis de `capture_site.py`: `CSS_W` (padrão 700), `ESQUEMA` (padrão `dark`)
  (`Instragram-Videos/pipeline/capture_site.py:19-20`).
- Parâmetros fixos: `CSS_W 700`, `BAND 1100` CSS px, `SCALE 2` (deviceScaleFactor), `W_VIDEO 1080`,
  `LIMITE_TEXTURA 16384`, `MAX_CSS = int(16384*700/1080) = 10619` (`Instragram-Videos/pipeline/capture.py:11,18-19`;
  `Instragram-Videos/pipeline/capture_site.py:19-23`).
- Viewport emulado: `Emulation.setDeviceMetricsOverride width=700 height=1200 deviceScaleFactor=2 mobile=False` e
  `prefers-color-scheme: dark` (`Instragram-Videos/pipeline/capture.py:28-29`; `Instragram-Videos/pipeline/capture_site.py:52-54`).
- Ajustes por host em `capture_site.py`: `AJUSTES = {"huggingface.co": ['[data-target="InferenceWidget"]']}`
  (`Instragram-Videos/pipeline/capture_site.py:32-34`).

## Contrato de saída

- `chunks/NNN.png` — faixas de até 1100 CSS px, `Page.captureScreenshot format=png captureBeyondViewport=True clip{x:0,y,width:700,height:h,scale:2}`
  (`Instragram-Videos/pipeline/capture.py:104-114`; `Instragram-Videos/pipeline/capture_site.py:238-245`). Faixas
  antigas são apagadas antes (`Instragram-Videos/pipeline/capture.py:21-23`).
- `captura.json`:
  - comum: `altura_css, altura_pagina_css, cortada, css_w, band, scale, chunks, secoes[{t,y}], topo, url, ocultos`
    (`Instragram-Videos/pipeline/capture.py:116-120`);
  - GitHub: `breadcrumb` (`Instragram-Videos/pipeline/capture.py:119`);
  - site: `esquema, url_final, titulo, fonte:"site", site_chars, sticky_neutralizados, flutuantes_ocultos,
    y_conteudo, blocos_revelados` (`Instragram-Videos/pipeline/capture_site.py:259-267`);
  - depois do `stitch.py`: `strip_w, strip_h, px_por_css` (`Instragram-Videos/pipeline/stitch.py:29-31`).
- `site.md` (só `capture_site.py`) — **texto renderizado do DOM** (não o HTML servido), até 60.000 chars,
  com cabeçalho `# título / Fonte / Capturado em`; é a âncora de veracidade do roteiro
  (`Instragram-Videos/pipeline/capture_site.py:204,247-257`; `Instragram-Videos/.claude/rules/veracidade.md:45-48`).
- `strip.png` — tira única 1080 de largura (`Instragram-Videos/pipeline/stitch.py:26-27`).
- Frame de abertura: o topo da tira precisa mostrar a âncora (nome do repositório + stars, nome do modelo,
  ferramenta + versão) (`Instragram-Videos/.claude/agents/captura.md:48-50`; `Instragram-Videos/.claude/skills/gerar-reel-release/SKILL.md:82-83`).
- Para `peca.json`: `site.md` → `papel: "fonte"`; `strip.png`/`chunks` são intermediários (NÃO DOCUMENTADO
  qual papel teriam; não há papel "tira" no enum).

## Limites e cotas

- Texto legível: 700 CSS px ×2 reduzido a 1080 → texto de 16px do GitHub vira ~25px no vídeo; **estreitar
  o viewport, nunca aumentar fonte via CSS** (`Instragram-Videos/.claude/rules/captura/cdp.md:27-31`).
- Captura por faixas, não página inteira: `captureBeyondViewport` de 20.000px "falha ou vem cortada"
  (`Instragram-Videos/.claude/rules/captura/cdp.md:109-112`).
- Timeout por faixa: `_response_timeout=60.0` no `capture.py` (padrão do daemon é 5s; faixa pesada passava)
  (`Instragram-Videos/pipeline/capture.py:107-111`). `capture_site.py` **não** passa esse timeout
  (`Instragram-Videos/pipeline/capture_site.py:242-243`).
- Página alta: corta em `MAX_CSS`; prefere fronteira de seção entre `0.8*MAX_CSS` e `MAX_CSS`; seções depois
  do corte são removidas para o compose não anunciar fim que a tira não tem
  (`Instragram-Videos/pipeline/capture.py:95-102`; `Instragram-Videos/pipeline/capture_site.py:230-236`).
- Seções: GitHub = `article h1, article h2` (`Instragram-Videos/pipeline/capture.py:77-80`); site = `h1,h2,h3`
  visíveis, texto 3–80 chars, deduplicadas a < 40px (`Instragram-Videos/pipeline/capture_site.py:175-182`).
- Site genérico:
  - espera 1,5s após load (fonte/hero tardios) (`Instragram-Videos/pipeline/capture_site.py:56`);
  - desliga `animation`/`transition`, `scroll-behavior`, `scroll-snap`, `overflow` do html/body
    (`Instragram-Videos/pipeline/capture_site.py:90-94`);
  - `loading=eager` em img/iframe e `data-src → src` (`Instragram-Videos/pipeline/capture_site.py:96-101`);
  - **passada de rolagem** de 900px com pausa 0,22s, até 60 voltas, acompanhando o crescimento do
    `scrollHeight`, depois volta ao topo com 0,8s (`Instragram-Videos/pipeline/capture_site.py:114-124`);
  - `sticky → static`; `fixed`: fora da tela (4px), cobrindo ≥ 80% da altura, ou fora do topo/mais de 30% →
    `display:none`; no topo e ≤ 30% → `static` (é a barra de marca) (`Instragram-Videos/pipeline/capture_site.py:127-150`;
    tabela em `Instragram-Videos/.claude/rules/captura/cdp.md:61-66`);
  - rede de segurança: elementos com `opacity < 0.05`, caixa ≥ 40×10, com texto e não escondidos de
    propósito → `opacity:1; transform:none` (`Instragram-Videos/pipeline/capture_site.py:152-168`);
  - `MIN_CSS = 1600` recusa; `ALERTA_CSS = 4000` avisa página curta (`Instragram-Videos/pipeline/capture_site.py:36-41,215-228`);
  - `y_conteudo > 400` CSS px avisa abertura vazia, estimando `y/160` segundos
    (`Instragram-Videos/pipeline/capture_site.py:221-225`).
- GitHub: esconde overlays (`.js-notice, .flash, dialog, .Popover, footer, .js-cookie-consent, …`), o cluster
  `[data-testid="top-nav-right"]` e a busca do centro **só se o breadcrumb for achado**; mantém o breadcrumb
  `owner / repo` (`Instragram-Videos/pipeline/capture.py:45-71`).
- Site: esconde consentimento (cookie/consent/gdpr/OneTrust/Cookiebot), modais, widgets de chat
  (Intercom, Crisp, Drift, HubSpot) e anúncios (`Instragram-Videos/pipeline/capture_site.py:73-86`).
- Seletores sempre por atributo estável (`data-testid`, `data-component`, `data-target`), **nunca por classe
  hasheada** de build; cada grupo conta quantos casou em `ocultos` para a podridão aparecer no log
  (`Instragram-Videos/pipeline/capture.py:40-44`; `Instragram-Videos/pipeline/capture_site.py:29-31`).
- Custo: zero de API. Depende do Chrome do usuário com remote debugging (browser-harness).

## Erros conhecidos e tratamento

| Situação | Tratamento | Referência |
|---|---|---|
| Seletor que casa 0 elementos (DOM mudou) | AVISO por grupo | `Instragram-Videos/pipeline/capture.py:86-90` |
| Breadcrumb não encontrado | AVISO "abertura pode estar sem o nome do repo" | `Instragram-Videos/pipeline/capture.py:91-92` |
| `.AppHeader` apodreceu (classe hasheada) | trocado por `data-testid` | `Instragram-Videos/pipeline/capture.py:40-43` |
| Esconder a barra global inteira | apagava `owner / repo` da abertura — "o acidente que cdp.md registra" | `Instragram-Videos/pipeline/capture.py:35-38`; `Instragram-Videos/.claude/rules/captura/cdp.md:35-38` |
| Sticky/fixed repetido em toda faixa | neutralizado antes de capturar | `Instragram-Videos/.claude/rules/captura/cdp.md:44-47` |
| `fixed` no atacado para `static` | doc da OpenAI: conteúdo desceu de y=64 para y=2050, reel abria com ~20s de tela preta | `Instragram-Videos/.claude/rules/captura/cdp.md:49-73` |
| Reveal por IntersectionObserver / imagem preguiçosa | passada de rolagem obrigatória + rede de opacidade | `Instragram-Videos/.claude/rules/captura/cdp.md:75-87` |
| Página < 1600 CSS px (landing de uma tela, scroller próprio tipo Lenis) | `SystemExit` — escolher outra página, não outro parâmetro | `Instragram-Videos/pipeline/capture_site.py:215-220`; `Instragram-Videos/.claude/agents/captura.md:65-66` |
| Widget vazio do Hugging Face (~900 CSS px = ~6s parados) | `AJUSTES` por host | `Instragram-Videos/.claude/rules/captura/cdp.md:94-101` |
| Faixa lenta passando de 5s | timeout 60s por faixa (só no `capture.py`) | `Instragram-Videos/pipeline/capture.py:107-111` |
| Marcador do cavalo do harness no título (`🐴`) | removido do título antes de ir ao `site.md` | `Instragram-Videos/pipeline/capture_site.py:209-212` |
| Fechar a aba errada (aba anexada migra) | GitHub: acha por URL, `switch_tab`, confere `current_tab().url` e só então fecha; site: fecha pelo `targetId` guardado logo após `new_tab`, com a **origem** como 2ª confirmação; sem `targetId`, deixa aberta e avisa | `Instragram-Videos/pipeline/capture.py:122-129`; `Instragram-Videos/pipeline/capture_site.py:269-284`; `Instragram-Videos/.claude/rules/captura/cdp.md:7-21` |
| `activate_tab()` | proibido (rouba o foco); bloqueado por hook | `Instragram-Videos/.claude/rules/captura/cdp.md:23-25`; `Instragram-Videos/.claude/hooks/captura/pre-bash-guard.sh:6` |
| Emulação vazando para outras abas | `Emulation.clearDeviceMetricsOverride` ao fim | `Instragram-Videos/pipeline/capture.py:131`; `Instragram-Videos/pipeline/capture_site.py:286` |
| Tira > 16384px | `stitch.py` aborta | `Instragram-Videos/pipeline/stitch.py:23-25` |
| `site.md` raquítico | gate reprova < 1200 chars | `Instragram-Videos/.claude/hooks/captura/stop-gate.sh:20-24` |
| URL candidata de página oficial | 200 aceita; 403/429 aceita (proteção de bot recusa urllib e abre no Chrome); 404/410 nunca | `Instragram-Videos/pipeline/pick_llm.py:82-99`; `Instragram-Videos/pipeline/pick_release.py:205-219` |

## Riscos para a nossa implementação

- **Provedor diverge do contrato**: `CONTRATO-capacidades.md` lista `capturar_pagina` → `playwright`
  (Chromium do Playwright). A fonte usa **browser-harness/CDP no Chrome do usuário**. Tudo aqui é CDP puro
  (`Emulation.*`, `Page.captureScreenshot` com `clip` e `captureBeyondViewport`), que o Playwright expõe via
  sessão CDP no Chromium — mas: (a) perde a sessão logada do usuário; (b) sites com proteção de bot que
  "abrem normal no Chrome" (`Instragram-Videos/pipeline/pick_llm.py:88-90`) podem bloquear o Chromium
  headless. Não documentado como a fonte se comportaria em headless.
- Ganchos específicos de pack: seletores do GitHub (`capture.py`) e o ajuste do Hugging Face são
  conhecimento de fonte, não do núcleo; o núcleo deve aceitar "ajustes por host" como dado.
- Não há marca embutida nestes scripts, exceto a escolha de `ESQUEMA=dark` (estética) e `CSS_W 700`
  pensado para 1080 de largura (9:16). Para 4:5 / 16:9 a razão muda.
- O que derruba a qualidade se extraído de forma ingênua:
  1. Screenshot de página inteira numa chamada → falha/corta em páginas altas.
  2. Aumentar fonte por CSS em vez de estreitar viewport → layout quebrado.
  3. Capturar sem a passada de rolagem → faixas com texto invisível.
  4. `fixed → static` no atacado → abertura com tela vazia (o pior defeito: decide a retenção).
  5. Esconder a barra de navegação/cabeçalho → reel sem âncora no frame 0.
  6. Seletor por classe utilitária/hasheada sem contagem → apodrece em silêncio.
  7. Fechar aba por URL (ou sem conferir) → fecha aba do usuário.
  8. Não cortar a tira em fronteira de seção / não filtrar `secoes` → scroll termina fora do conteúdo.
  9. Derivar `site.md` do HTML servido → texto vazio em sites JS, e o roteiro fica sem lastro.
- Divergência de documentação: `cdp.md:35` ainda manda esconder `header.AppHeader`, mas o código não
  esconde mais a barra global (`Instragram-Videos/pipeline/capture.py:35-38`). O código é a versão certa.

## Fonte

- `Instragram-Videos/pipeline/capture.py` (1–133)
- `Instragram-Videos/pipeline/capture_site.py` (1–292)
- `Instragram-Videos/pipeline/stitch.py` (1–32)
- `Instragram-Videos/pipeline/pick_llm.py` (82–99), `Instragram-Videos/pipeline/pick_release.py` (205–219)
- `Instragram-Videos/.claude/rules/captura/cdp.md` (1–114)
- `Instragram-Videos/.claude/agents/captura.md` (1–71)
- `Instragram-Videos/.claude/hooks/captura/stop-gate.sh`, `pre-bash-guard.sh`
- `Instragram-Videos/.claude/skills/gerar-reel-llm/SKILL.md` (44–73), `gerar-reel-release/SKILL.md` (73–96)
- `Instragram-Videos/videos/appwrite-appwrite/captura.json` (artefato real)
- Harness do browser: CLI `browser-harness`, instalado fora do projeto; o contrato dos helpers não está
  no repositório de origem — NÃO DOCUMENTADO ali.
- Testes: nenhum teste cobre captura ou stitch.
