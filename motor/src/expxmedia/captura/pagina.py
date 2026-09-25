"""Captura de página: a capacidade `capturar_pagina`, provedor `playwright` (D-25).

Porta de `Instragram-Videos/pipeline/capture_site.py` e `stitch.py` para um Chromium headless
próprio (o do Playwright), em vez do Chrome da pessoa por CDP. O caminho é o mesmo da origem:

1. abre a página num viewport estreito (700 CSS px × 1200, escala 2, esquema escuro): texto
   grande no vídeo vem de **estreitar o viewport, nunca de aumentar a fonte por CSS**;
2. **limpa**: esconde consentimento/cookies, modais, widgets de chat e os ajustes por host
   (dado de quem chama, não do núcleo); desliga animação e transição; imagem preguiçosa vira
   `eager`. Cada grupo conta quantos elementos casou (`ocultos`), para a podridão de seletor
   aparecer no JSON em vez de virar banner no vídeo;
3. **rolagem**: passada de 900 px com pausa de 0,22 s, até 60 voltas, acompanhando o
   crescimento do `scrollHeight` (reveal por IntersectionObserver, imagem preguiçosa);
4. **congela o layout**: `sticky` vira `static`; `fixed` fora da tela, cobrindo ≥ 80% da altura
   ou fora do topo some, e a barra do topo (≤ 30%) vira `static` — nunca `fixed → static` no
   atacado, que abre o reel com tela vazia; rede de segurança de opacidade;
5. mede as **seções** (h1–h3 visíveis, 3–80 caracteres, deduplicadas a < 40 px) com o `y` de
   cada uma, e onde o conteúdo começa (`y_conteudo`);
6. recusa página que rola menos de 1600 CSS px e texto renderizado com menos de 1200
   caracteres no `site.md`; corta a página alta no teto de textura, de preferência numa
   fronteira de seção;
7. captura em **faixas** de 1100 CSS px (`Page.captureScreenshot` com `captureBeyondViewport`),
   nunca a página inteira numa chamada, e **costura** a tira na largura do vídeo.

Saída na pasta `saida`: `chunks/NNN.png`, `tira.png`, `site.md` (texto renderizado do DOM, não o
HTML servido: é a âncora de veracidade do roteiro) e `captura.json`.

Uso:

    from expxmedia.captura import pagina
    r = pagina.capturar("https://exemplo.example/docs", "pecas/.../midia/captura")
    r["secoes"], r["site_chars"], r["strip_h"]
"""
from __future__ import annotations

import base64
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from expxmedia.nucleo import arquivos, tempo

__all__ = [
    "ErroCaptura",
    "ErroPaginaCurta",
    "ErroConteudoInsuficiente",
    "LARGURA_CSS",
    "ALTURA_VIEWPORT",
    "FAIXA_CSS",
    "ESCALA",
    "LARGURA_VIDEO",
    "LIMITE_TEXTURA",
    "MIN_CSS",
    "ALERTA_CSS",
    "MIN_CHARS_SITE",
    "MAX_CHARS_SITE",
    "capturar",
    "costurar",
]

LARGURA_CSS = 700          # origem: Instragram-Videos/pipeline/capture_site.py:19 (estreito => texto grande no vídeo)
ALTURA_VIEWPORT = 1200     # origem: Instragram-Videos/pipeline/capture_site.py:52
FAIXA_CSS, ESCALA = 1100, 2  # origem: Instragram-Videos/pipeline/capture_site.py:21
LARGURA_VIDEO = 1080       # origem: Instragram-Videos/pipeline/capture_site.py:22 (lib.py:9, W)
LIMITE_TEXTURA = 16384     # origem: Instragram-Videos/pipeline/capture_site.py:22 (stitch.py:23)
ESQUEMA = "dark"           # origem: Instragram-Videos/pipeline/capture_site.py:20
MIN_CSS = 1600             # origem: Instragram-Videos/pipeline/capture_site.py:40
ALERTA_CSS = 4000          # origem: Instragram-Videos/pipeline/capture_site.py:41
Y_CONTEUDO_AVISO = 400     # origem: Instragram-Videos/pipeline/capture_site.py:222
PX_POR_SEGUNDO_ABERTURA = 160  # origem: Instragram-Videos/pipeline/capture_site.py:224 (estimativa de tela vazia)
MIN_CHARS_SITE = 1200      # origem: Instragram-Videos/.claude/hooks/captura/stop-gate.sh:24
MAX_CHARS_SITE = 60000     # origem: Instragram-Videos/pipeline/capture_site.py:204
ESPERA_CARGA_S = 1.5       # origem: Instragram-Videos/pipeline/capture_site.py:56 (fonte e hero chegam depois do load)
PASSO_ROLAGEM = 900        # origem: Instragram-Videos/pipeline/capture_site.py:119
PAUSA_ROLAGEM_S = 0.22     # origem: Instragram-Videos/pipeline/capture_site.py:118
VOLTAS_ROLAGEM = 60        # origem: Instragram-Videos/pipeline/capture_site.py:116
PAUSA_TOPO_S = 0.8         # origem: Instragram-Videos/pipeline/capture_site.py:124
FRACAO_FRONTEIRA = 0.8     # origem: Instragram-Videos/pipeline/capture_site.py:233 (corte em seção entre 0,8×teto e o teto)
FUNDO_TIRA = (33, 40, 48)  # origem: Instragram-Videos/pipeline/stitch.py:17
TIMEOUT_MS = 60_000        # origem: Instragram-Videos/pipeline/capture.py:107-111 (60 s por faixa)
VERSAO = 1

# origem: Instragram-Videos/pipeline/capture_site.py:64-107
LIMPAR_JS = """
(ajustes) => {
  const ocultos = {};
  const sumir = (nome, els) => {
    els.forEach(e => e.style.setProperty('display', 'none', 'important'));
    ocultos[nome] = (ocultos[nome] || 0) + els.length;
  };
  const q = sel => Array.from(document.querySelectorAll(sel));

  // Banner de cookie/consentimento: por atributo semântico e por vocabulário no id/classe.
  sumir('consentimento', q([
    '[id*="cookie" i]', '[class*="cookie" i]', '[id*="consent" i]', '[class*="consent" i]',
    '[aria-label*="cookie" i]', '[data-testid*="cookie" i]', '#onetrust-banner-sdk',
    '#CybotCookiebotDialog', '.cc-window', '[class*="gdpr" i]'
  ].join(',')));

  // Modal, toast e widget de chat de suporte — tudo que flutua por cima do conteúdo.
  sumir('overlays', q([
    'dialog[open]', '[role="dialog"]', '[role="alertdialog"]', '.modal.show',
    '#intercom-container', '.intercom-lightweight-app', '#crisp-chatbox',
    '#drift-widget-container', '#hubspot-messages-iframe-container',
    '[id*="chat-widget" i]', '[class*="cookie-banner" i]', '[class*="announcement" i]'
  ].join(',')));

  // Animação de entrada: sem desligar, a faixa sai com texto pela metade ou invisível.
  const css = document.createElement('style');
  css.textContent = `*,*::before,*::after{animation:none!important;transition:none!important}
    html{scroll-behavior:auto!important}
    html,body{scroll-snap-type:none!important;overflow:visible!important;height:auto!important}`;
  document.documentElement.appendChild(css);

  // Imagem preguiçosa nunca carrega se a faixa é capturada sem passar por ela.
  q('img').forEach(i => {
    i.loading = 'eager';
    if (!i.getAttribute('src') && i.dataset && i.dataset.src) i.src = i.dataset.src;
  });
  q('iframe').forEach(i => { i.loading = 'eager'; });

  sumir('ajuste_do_site', ajustes.length ? q(ajustes.join(',')) : []);
  return ocultos;
}
"""

# origem: Instragram-Videos/pipeline/capture_site.py:127-206
CONGELAR_JS = """
() => {
  const VP = innerHeight, VW = innerWidth;
  let presos = 0, flutuantes = 0;
  document.querySelectorAll('*').forEach(e => {
    const pos = getComputedStyle(e).position;
    if (pos !== 'sticky' && pos !== 'fixed') return;
    if (pos === 'sticky') { e.style.setProperty('position','static','important'); presos++; return; }
    const b = e.getBoundingClientRect();
    const foraDaTela = b.right <= 4 || b.bottom <= 4 || b.left >= VW - 4 || b.top >= VP - 4;
    const cobreATela = b.height >= VP * 0.8;
    const noTopo = b.top <= 4 && b.height <= VP * 0.3;
    if (foraDaTela || cobreATela || !noTopo) {
      e.style.setProperty('display','none','important'); flutuantes++;
    } else {
      e.style.setProperty('position','static','important'); presos++;
    }
  });

  // Rede de segurança: bloco de texto que continuou invisível depois da passada de rolagem.
  let revelados = 0;
  document.querySelectorAll('section,div,article,p,h1,h2,h3,li').forEach(e => {
    const s = getComputedStyle(e);
    if (parseFloat(s.opacity) >= 0.05) return;
    if (e.getAttribute('aria-hidden') === 'true' || e.closest('[hidden]')) return;
    if (e.closest('[style*="display: none"]')) return;
    const r = e.getBoundingClientRect();
    if (r.width < 40 || r.height < 10) return;
    if (!(e.innerText || '').trim()) return;
    e.style.setProperty('opacity','1','important');
    e.style.setProperty('transform','none','important');
    revelados++;
  });

  window.scrollTo(0, 0);
  const vis = e => {
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden';
  };
  const secoes = [];
  document.querySelectorAll('h1,h2,h3').forEach(h => {
    const t = (h.textContent || '').trim().replace(/\\s+/g, ' ');
    if (t.length < 3 || t.length > 80 || !vis(h)) return;
    const y = Math.round(h.getBoundingClientRect().top + window.scrollY);
    if (secoes.length && Math.abs(secoes[secoes.length - 1].y - y) < 40) return;
    secoes.push({t: t.slice(0, 30), y});
  });

  // Onde o conteúdo realmente começa: abertura vazia é o pior defeito de um reel.
  let y_conteudo = Infinity;
  document.querySelectorAll('h1,h2,h3,p,li,td,img,button,a,span').forEach(e => {
    const b = e.getBoundingClientRect();
    if (b.width < 20 || b.height < 8) return;
    if (getComputedStyle(e).visibility === 'hidden') return;
    if (e.tagName !== 'IMG' && !(e.innerText || '').trim()) return;
    y_conteudo = Math.min(y_conteudo, Math.round(b.top + window.scrollY));
  });

  return {
    altura: document.documentElement.scrollHeight,
    presos, flutuantes, revelados, secoes,
    y_conteudo: isFinite(y_conteudo) ? y_conteudo : -1,
    titulo: document.title || '',
    url_final: location.href,
    topo: (document.body.innerText || '').slice(0, 90).replace(/\\n/g, ' | '),
    texto: (document.body.innerText || '').slice(0, MAX_CHARS),
  };
}
""".replace("MAX_CHARS", str(MAX_CHARS_SITE))


class ErroCaptura(RuntimeError):
    """A captura não pôde ser feita ou não serve (tira acima do teto, página inacessível)."""


class ErroPaginaCurta(ErroCaptura):
    """A página rola menos que o mínimo: não dá material para o scroll do reel."""


class ErroConteudoInsuficiente(ErroCaptura):
    """O texto renderizado não chega ao piso do `site.md`: o roteiro ficaria sem lastro."""


def _ajustes_do_host(url: str, ajustes: dict[str, list[str]] | list[str] | None) -> list[str]:
    """Seletores extras a esconder. Dict: `{host: [seletores]}`, casado por trecho da URL (como na
    origem); lista: vale para qualquer host."""
    if not ajustes:
        return []
    if isinstance(ajustes, dict):
        return [s for host, sels in ajustes.items() if host in url for s in sels]
    return list(ajustes)


def _site_md(titulo: str, url_final: str, texto: str, data: str) -> str:
    # origem: Instragram-Videos/pipeline/capture_site.py:251-257
    return (f"# {titulo}\n\n"
            f"Fonte: {url_final}\n"
            f"Capturado em: {data}\n"
            "Texto renderizado da página (âncora de veracidade do roteiro).\n\n---\n\n"
            f"{texto}\n")


def _hoje(raiz: Path | str | None) -> str:
    if raiz is not None:
        return tempo.hoje(raiz)
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def capturar(
    url: str,
    saida: Path | str,
    *,
    largura_css: int = LARGURA_CSS,
    escala: int | float = ESCALA,
    largura_final: int = LARGURA_VIDEO,
    esquema: str = ESQUEMA,
    ajustes: dict[str, list[str]] | list[str] | None = None,
    raiz: Path | str | None = None,
    timeout_ms: float = TIMEOUT_MS,
) -> dict[str, Any]:
    """Captura `url` em faixas, costura a tira e grava `site.md` e `captura.json` em `saida`.

    Levanta ErroPaginaCurta (rola < 1600 CSS px), ErroConteudoInsuficiente (`site.md` < 1200
    caracteres) ou ErroCaptura. Devolve o conteúdo do `captura.json`, com `avisos`.
    """
    esquema_url = urlsplit(url).scheme
    if esquema_url not in ("http", "https", "file"):
        raise ErroCaptura(f"URL não suportada: {url!r} (use http, https ou file)")
    if esquema not in ("dark", "light", "no-preference"):
        raise ErroCaptura(f"esquema inválido: {esquema!r} (dark, light ou no-preference)")
    saida = Path(saida)
    max_css = int(LIMITE_TEXTURA * largura_css / largura_final)  # origem: Instragram-Videos/pipeline/capture_site.py:23
    avisos: list[str] = []

    from playwright.sync_api import Error as ErroPlaywright
    from playwright.sync_api import sync_playwright

    faixas: list[bytes] = []
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            contexto = navegador.new_context(
                viewport={"width": largura_css, "height": ALTURA_VIEWPORT},
                device_scale_factor=escala, color_scheme=esquema,
            )
            pagina = contexto.new_page()
            pagina.set_default_timeout(timeout_ms)
            try:
                resposta = pagina.goto(url, wait_until="load", timeout=timeout_ms)
            except ErroPlaywright as erro:
                raise ErroCaptura(f"não consegui abrir {url}: {str(erro).splitlines()[0]}") from None
            if resposta is not None and resposta.status >= 400:
                raise ErroCaptura(f"{url} respondeu {resposta.status}")
            pagina.wait_for_timeout(ESPERA_CARGA_S * 1000)

            # 1. limpar
            ocultos = pagina.evaluate(LIMPAR_JS, _ajustes_do_host(url, ajustes))

            # 2. passada de rolagem
            altura = int(pagina.evaluate("document.documentElement.scrollHeight"))
            y, voltas = 0, 0
            while y < altura and voltas < VOLTAS_ROLAGEM:
                pagina.evaluate(f"window.scrollTo(0,{y})")
                pagina.wait_for_timeout(PAUSA_ROLAGEM_S * 1000)
                y += PASSO_ROLAGEM
                altura = max(altura, int(pagina.evaluate("document.documentElement.scrollHeight")))
                voltas += 1
            pagina.evaluate("window.scrollTo(0,0)")
            pagina.wait_for_timeout(PAUSA_TOPO_S * 1000)

            # 3. congelar o layout e medir
            info = pagina.evaluate(CONGELAR_JS)
            total = int(info["altura"])
            if total < MIN_CSS:
                raise ErroPaginaCurta(
                    f"a página rola só {total} CSS px (mínimo {MIN_CSS}): não dá material para o scroll. "
                    "Quase sempre é landing de uma tela só ou site com scroller próprio; escolha outra página."
                )
            texto = re.sub(r"\n{3,}", "\n\n", info["texto"]).strip()
            titulo = (info["titulo"] or "").strip()
            conteudo_md = _site_md(titulo, info["url_final"], texto, _hoje(raiz))
            if len(conteudo_md) < MIN_CHARS_SITE:
                raise ErroConteudoInsuficiente(
                    f"site.md com {len(conteudo_md)} caracteres (mínimo {MIN_CHARS_SITE}): "
                    "a página não renderizou texto suficiente para servir de fonte ao roteiro."
                )
            if info["y_conteudo"] > Y_CONTEUDO_AVISO:
                avisos.append(f"o conteúdo só começa em {info['y_conteudo']} CSS px: a abertura teria "
                              f"~{info['y_conteudo'] / PX_POR_SEGUNDO_ABERTURA:.0f}s de tela vazia "
                              "(confira flutuantes_ocultos)")
            if total < ALERTA_CSS:
                avisos.append(f"página curta ({total} CSS px): o scroll vai ficar lento")

            # corta numa fronteira de seção perto do teto; senão, no teto seco
            h_total = total
            if total > max_css:
                fronteiras = [s["y"] for s in info["secoes"] if FRACAO_FRONTEIRA * max_css <= s["y"] <= max_css]
                h_total = max(fronteiras) if fronteiras else max_css
            secoes = [s for s in info["secoes"] if s["y"] <= h_total]

            # 4. faixas
            # a escala vai no clip, como na origem (capture_site.py:242-243): com captureBeyondViewport o
            # Chromium headless ignora o deviceScaleFactor do contexto e a faixa sairia em 1×
            sessao = contexto.new_cdp_session(pagina)
            for y in range(0, h_total, FAIXA_CSS):
                h = min(FAIXA_CSS, h_total - y)
                r = sessao.send("Page.captureScreenshot", {
                    "format": "png", "captureBeyondViewport": True,
                    "clip": {"x": 0, "y": y, "width": largura_css, "height": h, "scale": escala},
                })
                faixas.append(base64.b64decode(r["data"]))
        finally:
            navegador.close()

    # 5. gravar: faixas, tira, site.md e captura.json
    pasta_faixas = saida / "chunks"
    pasta_faixas.mkdir(parents=True, exist_ok=True)
    for antiga in pasta_faixas.glob("*.png"):
        antiga.unlink()  # faixa sobrando de uma captura mais alta entraria na tira
    caminhos = []
    for n, dados in enumerate(faixas):
        caminho = pasta_faixas / f"{n:03d}.png"
        caminho.write_bytes(dados)
        caminhos.append(caminho)
    strip_w, strip_h = costurar(caminhos, saida / "tira.png", largura_final=largura_final)
    (saida / "site.md").write_text(conteudo_md, encoding="utf-8")

    resultado: dict[str, Any] = {
        "expxmedia_captura": VERSAO,
        "url": url,
        "url_final": info["url_final"],
        "titulo": titulo,
        "fonte": "site",
        "altura_css": h_total,
        "altura_pagina_css": total,
        "cortada": h_total < total,
        "css_w": largura_css,
        "band": FAIXA_CSS,
        "scale": escala,
        "esquema": esquema,
        "chunks": len(caminhos),
        "secoes": secoes,
        "topo": info["topo"],
        "site_chars": len(conteudo_md),
        "ocultos": ocultos,
        "sticky_neutralizados": info["presos"],
        "flutuantes_ocultos": info["flutuantes"],
        "y_conteudo": info["y_conteudo"],
        "blocos_revelados": info["revelados"],
        "tira": "tira.png",
        "site_md": "site.md",
        "strip_w": strip_w,
        "strip_h": strip_h,
        "px_por_css": strip_h / h_total,
        "avisos": avisos,
    }
    arquivos.gravar_json(saida / "captura.json", resultado)
    return resultado


def costurar(faixas: list[Path | str], destino: Path | str, *, largura_final: int = LARGURA_VIDEO) -> tuple[int, int]:
    """Cola as faixas na ordem e reduz a tira para `largura_final`. Devolve (largura, altura).

    Tira acima do limite de textura (16384 px) é erro, não corte silencioso.
    """
    from PIL import Image

    # origem: Instragram-Videos/pipeline/stitch.py:13-27
    imagens = []
    for caminho in faixas:
        with Image.open(caminho) as bruta:
            imagens.append(bruta.convert("RGB"))
    if not imagens:
        raise ErroCaptura("nenhuma faixa capturada: a captura falhou")
    larg, total = imagens[0].width, sum(i.height for i in imagens)
    altura_final = round(total * largura_final / larg)
    if altura_final > LIMITE_TEXTURA:
        raise ErroCaptura(f"tira de {altura_final} px passa do limite de textura ({LIMITE_TEXTURA})")
    tira = Image.new("RGB", (larg, total), FUNDO_TIRA)
    y = 0
    for img in imagens:
        tira.paste(img, (0, y))
        y += img.height
    if (larg, total) != (largura_final, altura_final):
        tira = tira.resize((largura_final, altura_final), Image.LANCZOS)
    destino = Path(destino)
    temporario = destino.with_name(destino.name + ".tmp.png")
    tira.save(temporario)
    temporario.replace(destino)
    return largura_final, altura_final
