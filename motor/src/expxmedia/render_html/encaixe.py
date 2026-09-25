"""Encaixe de texto e medição do DOM (D-20).

O encaixe roda depois que a página carregou, por `page.evaluate` (do lado do Playwright: a
página em si roda com JavaScript desligado). Ele encolhe a fonte dos seletores de `fit.encolher`
(× 0,96 por rodada, até 40 rodadas) até o bloco caber no container, e depois dá zoom no bloco
(passos de 0,02 entre 0,8 e 1,3) enquanto sobrar mais de 40 px e nenhum texto estourar a
largura da própria caixa. Kind com `fit: "fixo"` não encaixa.

A medição, depois do encaixe, reprova: texto fora do slide ou da margem, texto cortado, fonte
abaixo do mínimo (28 px; 18 px para o miúdo), família que não é da Alma e texto sobre texto. E
avisa colunas soltas. A ocupação do PNG reprova faixa vazia de mais de 22% no topo ou no rodapé.

Os números são os do `galeria.renderizar` de origem. O template pode subir `minimo`, `piso` e
`contraste`, e descer `vazio_max`, mas não o contrário: o contrato fixa o mínimo
(CONTRATO-template, `validacao.contraste_min` 3.0 e `fonte_min_px` 28).

Cada achado é `{"tipo", "detalhe"}`; `detalhe` é a frase da origem.
"""
from __future__ import annotations

import io
import re
from typing import Any

import numpy as np

from expxmedia.render_html.contraste import dominante

__all__ = [
    "FATOR_ENCOLHER",
    "RODADAS_ENCOLHER",
    "PASSO_ZOOM",
    "FOLGA_CRESCER_PX",
    "FIT_PADRAO",
    "TIPOGRAFIA_PADRAO",
    "GENERICAS",
    "configuracao",
    "encaixar",
    "medir",
    "aviso_de_zoom",
    "conferir_ocupacao",
]

FATOR_ENCOLHER = 0.96     # origem: Instagram-Carrosseis/galeria/_galeria.py:1279
RODADAS_ENCOLHER = 40     # origem: Instagram-Carrosseis/galeria/_galeria.py:1278
PASSO_ZOOM = 0.02         # origem: Instagram-Carrosseis/galeria/_galeria.py:1284-1285
FOLGA_CRESCER_PX = 40     # origem: Instagram-Carrosseis/galeria/_galeria.py:1284 (e o aviso de zoom, :1628)
ESTOURO_LARGURA_PX = 1    # origem: Instagram-Carrosseis/galeria/_galeria.py:1282
# origem: Instagram-Carrosseis/galeria/_galeria.py:84
FIT_PADRAO: dict[str, Any] = {"container": ".vis", "encolher": ["h1", "h2", "h3", "p", "li"], "zoom_min": 0.8, "zoom_max": 1.3, "margem": 0}
# origem: Instagram-Carrosseis/galeria/_galeria.py:86-91
TIPOGRAFIA_PADRAO: dict[str, Any] = {
    "minimo": 28,       # px: texto menor que isto não se lê no feed
    "piso": 18,         # px: nem o texto miúdo (paginação, cargo) desce daqui
    "miudo": [],        # seletores isentos do `minimo` (continuam presos ao `piso`)
    "decorativo": [],   # seletores de texto que não é para ler (mockup dentro da arte)
    "contraste": 3.0,   # razão WCAG entre a tinta do texto e o fundo atrás dele
    "vazio_max": 0.22,  # faixa vazia contínua no topo ou no rodapé, em fração da altura
}
# origem: Instagram-Carrosseis/galeria/_galeria.py:92
GENERICAS = ("sans-serif", "serif", "monospace", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace", "cursive", "fantasy", "inherit")
OCUPACAO_REDUCAO = 8      # origem: Instagram-Carrosseis/galeria/_galeria.py:1454-1456 (imagem 1/8, uma linha a cada 8 px)
OCUPACAO_DISTANCIA = 36   # origem: Instagram-Carrosseis/galeria/_galeria.py:1455 (pixel "não fundo")

# origem: Instagram-Carrosseis/galeria/_galeria.py:1268-1287 (os números chegam por cfg, vindos das constantes acima)
FIT_JS = """
(cfg) => {
  // encolhe a fonte até o bloco caber no container, depois cresce (zoom) se sobrar espaço
  const slide = document.querySelector('.slide'), vis = slide.querySelector(cfg.container);
  if (!vis || !vis.firstElementChild || slide.dataset.fit === 'fixo') return 'fixo';
  const kid = vis.firstElementChild;
  const free = () => vis.getBoundingClientRect().height - kid.getBoundingClientRect().height;
  let guard = 0;
  while (free() < 0 && guard++ < cfg.rodadas)
    for (const sel of cfg.encolher) slide.querySelectorAll(sel).forEach(e => { e.style.fontSize = (parseFloat(getComputedStyle(e).fontSize) * cfg.fator) + 'px'; });
  // só quem tem texto conta: enfeite em position absolute que sai da caixa não é texto estourando
  const comTexto = [...vis.querySelectorAll('*')].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()));
  const estoura = () => comTexto.some(e => e.scrollWidth > e.clientWidth + cfg.estouro);
  let z = 1;
  while (z < cfg.zoom_max && free() > cfg.folga && !estoura()) { z = +(z + cfg.passo).toFixed(2); kid.style.zoom = z; }
  while (z > cfg.zoom_min && (free() < 0 || estoura())) { z = +(z - cfg.passo).toFixed(2); kid.style.zoom = z; }
  return 'free=' + Math.round(free()) + ' shrink=' + guard + ' zoom=' + z;
}
"""

# origem: Instagram-Carrosseis/galeria/_galeria.py:1289-1338 (achados tipados; frases e tolerâncias iguais)
CHECK_JS = """
(cfg) => {
  const slide = document.querySelector('.slide'), b = slide.getBoundingClientRect(), m = cfg.margem || 0, ruins = [], caixas = [], range = document.createRange();
  const achado = (tipo, detalhe) => ruins.push({tipo, detalhe});
  for (const e of slide.querySelectorAll('*')) {
    const nos = [...e.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
    if (!nos.length) continue;
    const classe = e.getAttribute('class'), quem = e.tagName.toLowerCase() + (classe ? '.' + classe.split(' ')[0] : ''), cs = getComputedStyle(e);
    // tipografia: a família tem de ser uma das da Alma, e o tamanho não desce do mínimo legível
    const familia = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(), tamanho = parseFloat(cs.fontSize);
    if (cfg.familias.length && !cfg.familias.includes(familia.toLowerCase()) && !cfg.genericas.includes(familia.toLowerCase()))
      achado('fonte_fora_da_alma', quem + ": fonte '" + familia + "' não é da Alma (use var(--alma-fonte-titulo) ou var(--alma-fonte-texto))");
    const decorativo = (cfg.decorativo || []).some(sel => e.matches(sel) || e.closest(sel));
    const miudo = (cfg.miudo || []).some(sel => e.matches(sel));
    const piso = miudo ? cfg.piso : cfg.minimo;
    if (!decorativo && tamanho < piso - 0.5) achado('fonte_abaixo_do_minimo', quem + ': texto de ' + Math.round(tamanho) + 'px (o mínimo ' + (miudo ? 'de texto miúdo ' : '') + 'é ' + piso + 'px)');
    // mede o texto, não a caixa. Na vertical a tolerância é a sobra do glifo: título com entrelinha 0.8 passa da linha sem estar cortado
    const sobra = Math.max(0, parseFloat(cs.fontSize) * 1.2 - (parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2));
    for (const no of nos) {
      range.selectNodeContents(no);
      // texto de SVG se mede pela caixa do elemento: é ela que reflete textLength e viewBox
      const r = e instanceof SVGElement ? e.getBoundingClientRect() : range.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      if (cs.visibility !== 'hidden' && +cs.opacity > 0.05) caixas.push({e, quem, x1: r.left, x2: r.right, y1: r.top + r.height * 0.2, y2: r.bottom - r.height * 0.2,  // 20% de folga: entrelinha apertada não é colisão
                                                                        cheia: {x1: r.left, y1: r.top, x2: r.right, y2: r.bottom}, cor: cs.color,
                                                                        sobre: !!e.closest('[data-sobre]') || decorativo, decorativo,
                                                                        pintura: (cs.webkitBackgroundClip || cs.backgroundClip) === 'text' || cs.webkitTextFillColor === 'rgba(0, 0, 0, 0)'});
      if (r.left < b.left + m - 1 || r.right > b.right - m + 1 || r.top < b.top + m - 1 - sobra || r.bottom > b.bottom - m + 1 + sobra) achado('texto_fora_da_area', quem + ': texto fora da área do slide');
    }
    // cortado só existe onde a caixa corta; com overflow visível o texto que passa aparece, e quem pega é a medida acima
    if (cs.display !== 'inline' && ((cs.overflowX !== 'visible' && e.scrollWidth > e.clientWidth + 2) || (cs.overflowY !== 'visible' && e.scrollHeight > e.clientHeight + 2 + sobra))) achado('texto_cortado', quem + ': texto cortado');
  }
  // texto em cima de texto reprova; quando é de propósito (selo sobre palavra gigante), o elemento de baixo leva data-sobre
  for (let i = 0; i < caixas.length; i++) for (let j = i + 1; j < caixas.length; j++) {
    const p = caixas[i], q = caixas[j];
    if (p.e === q.e || p.e.contains(q.e) || q.e.contains(p.e)) continue;
    if (Math.min(p.x2, q.x2) - Math.max(p.x1, q.x1) > 6 && Math.min(p.y2, q.y2) - Math.max(p.y1, q.y1) > 6 && !(p.sobre || q.sobre)) achado('texto_sobre_texto', 'texto sobre texto: ' + p.quem + ' × ' + q.quem);
  }
  // alinhamento: bloco de texto que começa numa coluna só dele deixa a página torta. É aviso.
  const esquerdas = caixas.map(c => Math.round(c.x1));
  const colunas = [...new Set(esquerdas)].filter(x => esquerdas.filter(o => Math.abs(o - x) <= 8).length === 1);
  const fontes = [...document.fonts].filter(f => f.status === 'error').map(f => f.family);
  const vistos = new Set(), problemas = [];
  for (const r of ruins) if (!vistos.has(r.detalhe)) { vistos.add(r.detalhe); problemas.push(r); }
  return {problemas, avisos: colunas.length > 2 ? [{tipo: 'colunas_soltas', detalhe: 'blocos de texto em ' + colunas.length + ' colunas soltas: alinhe as margens'}] : [],
          fontes_com_erro: [...new Set(fontes)],
          caixas: caixas.filter(c => !c.decorativo).map(c => ({quem: c.quem, cor: c.cor, sobre: c.sobre, pintura: c.pintura, ...c.cheia}))};
}
"""


def _achado(tipo: str, detalhe: str) -> dict[str, str]:
    return {"tipo": tipo, "detalhe": detalhe}


def configuracao(template: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(fit, tipografia) do template, sobre os padrões da origem, com o piso do contrato preservado."""
    fit = {**FIT_PADRAO, **(template.get("fit") or {})}
    pedida = template.get("tipografia") or {}
    tipografia = {**TIPOGRAFIA_PADRAO, **{k: v for k, v in pedida.items() if k in TIPOGRAFIA_PADRAO}}
    # o template pode ser mais exigente que o contrato, nunca menos
    for chave in ("minimo", "piso", "contraste"):
        tipografia[chave] = max(float(tipografia[chave]), float(TIPOGRAFIA_PADRAO[chave]))
        if float(tipografia[chave]).is_integer() and chave != "contraste":
            tipografia[chave] = int(tipografia[chave])
    tipografia["vazio_max"] = min(float(tipografia["vazio_max"]), TIPOGRAFIA_PADRAO["vazio_max"])
    tipografia["miudo"] = list(tipografia.get("miudo") or [])
    tipografia["decorativo"] = list(tipografia.get("decorativo") or [])
    return fit, tipografia


def encaixar(pagina: Any, fit: dict[str, Any]) -> str:
    """Roda o encaixe na página e devolve `fixo` ou `free=N shrink=N zoom=Z`."""
    cfg = {**fit, "fator": FATOR_ENCOLHER, "rodadas": RODADAS_ENCOLHER, "passo": PASSO_ZOOM,
           "folga": FOLGA_CRESCER_PX, "estouro": ESTOURO_LARGURA_PX}
    return pagina.evaluate(FIT_JS, cfg)


def medir(pagina: Any, fit: dict[str, Any], tipografia: dict[str, Any], familias: list[str]) -> dict[str, Any]:
    """Medição do DOM depois do encaixe: {problemas, avisos, fontes_com_erro, caixas}."""
    cfg = {**fit, **{k: tipografia[k] for k in ("minimo", "piso", "miudo", "decorativo")},
           "familias": [f.lower() for f in familias], "genericas": list(GENERICAS)}
    return pagina.evaluate(CHECK_JS, cfg)


def aviso_de_zoom(encaixe: str, container: str) -> list[dict[str, str]]:
    """Encolheu com espaço sobrando: algum texto do container passa da própria caixa na largura.
    Origem: Instagram-Carrosseis/galeria/_galeria.py:1627-1629."""
    z = re.search(r"free=(-?\d+) .*zoom=([\d.]+)", encaixe or "")
    if z and float(z.group(2)) < 1 and int(z.group(1)) > FOLGA_CRESCER_PX:
        return [_achado("zoom_estoura_largura", f"zoom {z.group(2)} com {z.group(1)}px livres: "
                                                f"um texto dentro de {container} estoura a largura da caixa dele")]
    return []


def conferir_ocupacao(png: bytes, tipografia: dict[str, Any]) -> list[dict[str, str]]:
    """Faixa vazia contínua no topo ou no rodapé, e slide vazio.
    Origem: Instagram-Carrosseis/galeria/_galeria.py:1449-1465, com os mesmos números."""
    from PIL import Image

    with Image.open(io.BytesIO(png)) as img:
        arte = img.convert("RGB")
        reduzida = np.asarray(arte.resize((arte.width // OCUPACAO_REDUCAO, arte.height // OCUPACAO_REDUCAO)), dtype=np.int64)
        cor, _ = dominante(reduzida.reshape(-1, 3))
        cor_np = np.asarray(cor)
        linhas = []
        for y in range(0, arte.height, OCUPACAO_REDUCAO):
            faixa = np.asarray(arte.crop((0, y, arte.width, y + 1)).resize((arte.width // OCUPACAO_REDUCAO, 1)), dtype=np.int64)
            linhas.append(bool((np.abs(faixa.reshape(-1, 3) - cor_np).sum(axis=1) > OCUPACAO_DISTANCIA).any()))
    if not any(linhas):
        return [_achado("slide_vazio", "o slide está vazio")]
    topo, rodape = linhas.index(True), len(linhas) - 1 - linhas[::-1].index(True)
    achados = []
    for nome, vazio in (("no topo", topo), ("no rodapé", len(linhas) - 1 - rodape)):
        if vazio / len(linhas) > tipografia["vazio_max"]:
            achados.append(_achado("faixa_vazia", f"faixa vazia {nome}: {vazio / len(linhas):.0%} da altura sem nada "
                                                  f"(o limite é {tipografia['vazio_max']:.0%}; distribua o conteúdo "
                                                  "ou declare \"vazio_ok\": true no kind)"))
    return achados
