"""Render HTML → PNG medido: a capacidade `renderizar_html`, provedor `playwright` (D-20).

Porta do `galeria.renderizar` de origem para o template do núcleo (CONTRATO-template):

- **Cores e fontes vêm da Alma.** O motor injeta no `:root` os tokens `--alma-<papel>` e
  `--alma-fonte-titulo`/`--alma-fonte-texto` (`alma.tokens`); o CSS do template só usa
  `var(--alma-*)`. As fontes são resolvidas por `alma.fontes` (Google Fonts em cache local, fonte
  local da instalação, ou a Inter embarcada) e entram na página como data URI: nada é buscado
  pela página, nem o Google Fonts.
- **A página roda com JavaScript desligado** (`java_script_enabled=False`): script do template
  não executa. O encaixe e a medição rodam por `page.evaluate`, do lado do Playwright — o CDP
  avalia expressão mesmo com o script da página desligado, como na origem
  (`Instagram-Carrosseis/galeria/_galeria.py:1587-1589`); `test_renderizar.py` prova as duas coisas.
- **Rede fechada:** só `data:`, `about:` e `blob:` passam. Qualquer outro pedido é abortado e
  vira o achado `rede_barrada` com o host.
- **Canvas do template** (`canvas.w` × `canvas.h`, `device_scale_factor=1`).

Pipeline por slide, na ordem da origem: montar HTML → `set_content` (networkidle) → fontes
prontas + 150 ms → encaixe → medição do DOM → rede barrada → fonte que não carregou → PNG →
PNG sem a tinta do texto → leitura por pixel (contraste) → ocupação → aviso de zoom.

Saída em `saida/`: `slide_N.png` (e `slide_N.html` com `salvar_html`), `_prancha.png` e
`render.json` (prancha.py). Copy inválida não abre navegador nem grava nada.

Uso:

    from expxmedia.render_html import renderizar
    r = renderizar.renderizar("galeria/templates/x", {"slides": [...]}, alma, "pecas/.../slides")
    r["ok"], r["slides"][0]["problemas"]
"""
from __future__ import annotations

import base64
import hashlib
import html as html_lib
import json
import mimetypes
import os
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.request import url2pathname
from zoneinfo import ZoneInfo

from expxmedia.alma import fontes as _fontes
from expxmedia.alma import tokens as _tokens
from expxmedia.nucleo import arquivos
from expxmedia.render_html import contraste, encaixe, prancha

__all__ = [
    "ErroRender",
    "IMAGENS",
    "CHAVES_TRATAMENTO",
    "MODELO_RECORTE",
    "ESQUEMAS_LIBERADOS",
    "ESPERA_FONTES_MS",
    "carregar_template",
    "texto_html",
    "preencher",
    "conferir_modelo",
    "nomes_usados",
    "validar_copy",
    "erro_de_imagem",
    "erro_de_tratamento",
    "tratar_imagem",
    "html_do_slide",
    "renderizar",
]

IMAGENS = (".png", ".jpg", ".jpeg", ".webp", ".svg")  # origem: Instagram-Carrosseis/galeria/_galeria.py:79 (+ .svg, :1100)
ESQUEMAS_LIBERADOS = ("data", "about", "blob")         # origem: Instagram-Carrosseis/galeria/_galeria.py:1594 (sem o Google Fonts: a fonte chega do cache)
ESPERA_FONTES_MS = 150                                 # origem: Instagram-Carrosseis/galeria/_galeria.py:1607
MANIFESTO = "template.json"
CSS = "template.css"
NOME = re.compile(r"^[\w-]+$")  # origem: Instagram-Carrosseis/galeria/_galeria.py:104 (kind, slot e campo viram classe CSS e nome de arquivo)

# Tratamento de imagem declarado no slot (origem: Instagram-Carrosseis/galeria/tratamento.py)
CHAVES_TRATAMENTO = {"sem_fundo", "pb", "contraste", "enquadrar", "modo", "modelo_recorte"}  # origem: Instagram-Carrosseis/galeria/tratamento.py:20
MODELO_RECORTE = "u2net"             # origem: Instagram-Carrosseis/galeria/tratamento.py:21 (nunca u2netp: deixa fantasma de fundo)
MODOS_ENQUADRAR = ("cover", "contain")
CONTRASTE_TRATAMENTO = (0.2, 3)      # origem: Instagram-Carrosseis/galeria/tratamento.py:47
MODO_PADRAO_RENDER = "contain"       # origem: Instagram-Carrosseis/galeria/tratamento.py:103


# origem: Instagram-Carrosseis/galeria/_galeria.py:1612-1617 (família usada por algum texto; aqui com peso e estilo)
USADAS_JS = """() => {
  const usadas = {};
  for (const e of document.querySelectorAll('.slide, .slide *')) {
    if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const cs = getComputedStyle(e), f = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim().toLowerCase();
    const forma = cs.fontStyle + ' ' + cs.fontWeight;
    (usadas[f] = usadas[f] || []).includes(forma) || usadas[f].push(forma);
  }
  return usadas;
}"""
CHECA_FONTE_JS = "([forma, f]) => document.fonts.check(`${forma} 16px \"${f}\"`)"


class ErroRender(ValueError):
    """Entrada que impede montar o HTML (imagem fora da pasta, template sem fragmento...)."""


# ---------------------------------------------------------------- template


def carregar_template(template: Path | str | dict[str, Any]) -> dict[str, Any]:
    """O `template.json` lido, com `_dir` apontando a pasta do template."""
    if isinstance(template, dict):
        if "_dir" not in template:
            raise ErroRender("template em dict precisa de `_dir` com a pasta do template")
        return template
    pasta = Path(template)
    dados = arquivos.ler_json(pasta / MANIFESTO)
    if not isinstance(dados, dict):
        raise ErroRender(f"{MANIFESTO} não é um objeto JSON")
    return {**dados, "_dir": pasta}


# ---------------------------------------------------------------- modelo (um mustache pequeno)
# origem: Instagram-Carrosseis/galeria/_galeria.py:941-1014

TAG = re.compile(r"\{\{\s*([#^/]?)\s*([\w.@-]+)\s*\}\}")
EMBUTIDOS = ("_n", "_nn", "_total")


def texto_html(v: Any) -> str:
    """Escapa; `*palavra*` vira `<em>` e quebra de linha vira `<br>`."""
    if v is None or isinstance(v, (dict, list)):
        return ""
    t = html_lib.escape(str(v), quote=True)
    return re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", t).replace("\n", "<br>")


def _valor(nome: str, pilha: list[Any]) -> Any:
    if nome == ".":
        return pilha[-1]
    for ctx in reversed(pilha):
        if isinstance(ctx, dict) and nome in ctx:
            return ctx[nome]
    return None


def _fecha(modelo: str, nome: str, pos: int) -> re.Match[str]:
    fundo = 1
    for m in TAG.finditer(modelo, pos):
        if m.group(2) == nome:
            fundo += 1 if m.group(1) in ("#", "^") else -1 if m.group(1) == "/" else 0
            if fundo == 0:
                return m
    raise ValueError(f"seção {{{{#{nome}}}}} sem fechamento")


def preencher(modelo: str, pilha: list[Any]) -> str:
    """{{slot}}, {{#lista}}…{{/lista}} com {{.}}, {{@n}}, {{@nn}}, e {{^slot}} (substituto quando vazio)."""
    saida, pos = [], 0
    while True:
        m = TAG.search(modelo, pos)
        if not m:
            return "".join(saida) + modelo[pos:]
        saida.append(modelo[pos:m.start()])
        tipo, nome = m.groups()
        if tipo == "/":
            raise ValueError(f"{{{{/{nome}}}}} sem abertura")
        if not tipo:
            saida.append(texto_html(_valor(nome, pilha)))
            pos = m.end()
            continue
        fim = _fecha(modelo, nome, m.end())
        miolo, v = modelo[m.end():fim.start()], _valor(nome, pilha)
        if tipo == "^":
            saida.append("" if v else preencher(miolo, pilha))
        elif isinstance(v, list):
            saida.extend(preencher(miolo, pilha + [{"@n": i, "@nn": f"{i:02d}"}, item]) for i, item in enumerate(v, 1))
        elif v:
            saida.append(preencher(miolo, pilha + [v]))  # dict abre contexto; texto vale como {{.}}
        pos = fim.end()


def conferir_modelo(modelo: str) -> None:
    """Seções abertas e fechadas na ordem, e nenhuma marca fora do dialeto. Levanta ValueError."""
    abertas: list[str] = []
    for tipo, nome in TAG.findall(modelo):
        if tipo in ("#", "^"):
            abertas.append(nome)
        elif tipo == "/" and (not abertas or abertas.pop() != nome):
            raise ValueError(f"{{{{/{nome}}}}} fecha uma seção que não é a última aberta")
    if abertas:
        raise ValueError(f"seção {{{{#{abertas[-1]}}}}} sem fechamento")
    if "{{{" in modelo or "{{" in TAG.sub("", modelo):
        raise ValueError("marca `{{…}}` fora do dialeto (só {{slot}}, {{#x}}, {{^x}}, {{/x}}, {{.}}, {{@n}}, {{@nn}})")


def nomes_usados(modelo: str) -> set[str]:
    return {n for _, n in TAG.findall(modelo) if n != "." and not n.startswith("@") and n not in EMBUTIDOS}


# ---------------------------------------------------------------- copy
# origem: Instagram-Carrosseis/galeria/_galeria.py:1026-1114 ("reprova como o MiniMax: não corta nem completa em silêncio")


def _nomes_inseguros(m: dict[str, Any]) -> list[str]:
    erros = []
    for k, kind in (m.get("kinds") or {}).items():
        slots = (kind or {}).get("slots") or {}
        ruins = [n for n in (k, *slots, *(c for sp in slots.values() for c in (sp or {}).get("campos") or [])) if not NOME.match(str(n))]
        erros += [f"kind {k}: nome '{n}' só pode ter letra, número, hífen e sublinhado" for n in ruins]
    return erros


def erro_de_imagem(caminho: str) -> str | None:
    """Slot de imagem é caminho relativo, para baixo da pasta da copy, e de imagem: senão `../../.env`
    viraria data URI dentro do HTML."""
    p = Path(caminho)
    if p.is_absolute() or ".." in p.parts:
        return "caminho de imagem é relativo à pasta da copy, sem `..`"
    if p.suffix.lower() not in IMAGENS:
        return f"imagem aceita {', '.join(IMAGENS)}"
    return None


def _slot_imagem(spec: dict[str, Any]) -> bool:
    return spec.get("tipo") in ("asset", "imagem")


def validar_copy(m: dict[str, Any], copy: dict[str, Any], exemplo: bool = False) -> list[str]:
    """A copy contra os slots do template. `exemplo=True`: a copy é o exemplo do template (prova
    todos os kinds, na ordem da `sequencia`, e post único pode mostrar vários)."""
    erros: list[str] = []
    slides = copy.get("slides") if isinstance(copy, dict) else None
    if not isinstance(slides, list) or not slides:
        return ["copy sem `slides`"]
    kinds = m.get("kinds") or {}
    if m.get("tipo") == "post_unico" and len(slides) != 1 and not exemplo:
        erros.append("template de post único pede exatamente 1 slide")
    if exemplo:
        usados = [s.get("kind") if isinstance(s, dict) else None for s in slides]
        erros += [f"nenhum slide do exemplo usa o kind '{k}': kind sem prova não entra" for k in kinds if k not in usados]
        if m.get("sequencia") and usados != list(m["sequencia"]):
            erros.append("o exemplo tem os mesmos kinds da `sequencia`, na mesma ordem")
    for i, s in enumerate(slides, 1):
        if not isinstance(s, dict):
            erros.append(f"slide {i}: é um objeto com `kind` e os slots")
            continue
        kind = kinds.get(s.get("kind"))
        if not kind:
            erros.append(f"slide {i}: kind '{s.get('kind')}' não existe no template ({', '.join(kinds)})")
            continue
        slots = kind.get("slots") or {}
        for nome in sorted(set(s) - set(slots) - {"kind"}):
            erros.append(f"slide {i} ({s['kind']}): slot '{nome}' não existe neste kind")
        for nome, spec in slots.items():
            v, onde = s.get(nome), f"slide {i} ({s['kind']}), slot '{nome}'"
            if v in (None, "", []):
                if spec.get("obrigatorio", True) and not (_slot_imagem(spec) and spec.get("asset")):
                    erros.append(f"{onde}: obrigatório")
                continue
            tipo = spec.get("tipo")
            if tipo == "lista":
                faixa = spec.get("n")
                lo, hi = (faixa, faixa) if isinstance(faixa, int) else faixa or (1, 99)
                if not isinstance(v, list) or not lo <= len(v) <= hi:
                    erros.append(f"{onde}: lista de {lo} a {hi} itens")
                    continue
                campos = spec.get("campos")
                for item in v:
                    if campos and (not isinstance(item, dict) or set(item) - set(campos) or not item.get(campos[0])):
                        erros.append(f"{onde}: cada item é um objeto com {', '.join(campos)}")
                        continue
                    if not campos and not isinstance(item, str):
                        erros.append(f"{onde}: cada item é um texto")
                        continue
                    pares = item.items() if isinstance(item, dict) else [(None, item)]
                    for campo, t in pares:
                        limite = spec.get("max", {}).get(campo) if isinstance(spec.get("max"), dict) else spec.get("max")
                        if limite and len(str(t).replace("*", "")) > limite:
                            erros.append(f"{onde}{', campo ' + campo if campo else ''}: {len(str(t).replace('*', ''))} caracteres, "
                                         f"o template aguenta {limite}")
            elif tipo == "numero":
                if isinstance(v, bool) or not isinstance(v, (str, int, float)):
                    erros.append(f"{onde}: número ou texto curto")
                elif spec.get("max") and len(str(v).replace("*", "")) > spec["max"]:
                    erros.append(f"{onde}: {len(str(v).replace('*', ''))} caracteres, o template aguenta {spec['max']}")
            elif not isinstance(v, str):
                erros.append(f"{onde}: texto")
            elif _slot_imagem(spec):
                if spec.get("tratamento") is not None and erro_de_tratamento(spec["tratamento"]):
                    erros.append(f"{onde}: {erro_de_tratamento(spec['tratamento'])}")
                if not v.startswith("data:image/") and erro_de_imagem(v):
                    erros.append(f"{onde}: {erro_de_imagem(v)}")
            elif spec.get("max") and len(v.replace("*", "")) > spec["max"]:
                erros.append(f"{onde}: {len(v.replace('*', ''))} caracteres, o template aguenta {spec['max']}")
    return erros


# ---------------------------------------------------------------- tratamento de imagem
# origem: Instagram-Carrosseis/galeria/tratamento.py e processar.py (enquadrar, remover_fundo)


def _medida(texto: Any) -> tuple[int, int] | None:
    partes = str(texto).lower().split("x")
    if len(partes) != 2 or not all(p.strip().isdigit() for p in partes):
        return None
    largura, altura = (int(p) for p in partes)
    return (largura, altura) if largura > 0 and altura > 0 else None


def erro_de_tratamento(t: Any, nome: str = "tratamento") -> str | None:
    """Chave desconhecida é erro, não aviso: senão um typo vira slide sem tratamento."""
    if t is None:
        return None
    if not isinstance(t, dict):
        return f"`{nome}` é um objeto com {', '.join(sorted(CHAVES_TRATAMENTO))}"
    fora = sorted(set(t) - CHAVES_TRATAMENTO)
    if fora:
        return f"`{nome}` não conhece {', '.join(fora)} (aceita {', '.join(sorted(CHAVES_TRATAMENTO))})"
    if t.get("modo") and t["modo"] not in MODOS_ENQUADRAR:
        return f"`{nome}.modo` é {' ou '.join(MODOS_ENQUADRAR)}"
    if t.get("enquadrar") and not _medida(t["enquadrar"]):
        return f"`{nome}.enquadrar` é LARGURAxALTURA em px, como 900x1200"
    lo, hi = CONTRASTE_TRATAMENTO
    if t.get("contraste") is not None and not (isinstance(t["contraste"], (int, float)) and lo <= t["contraste"] <= hi):
        return f"`{nome}.contraste` é um número entre {lo} e {hi} (1 não muda nada)"
    return None


def _pedido(t: dict[str, Any] | None) -> dict[str, Any]:
    """Só o que muda a imagem. O modelo de recorte entra explícito: ele faz parte da impressão do cache."""
    p = {k: v for k, v in (t or {}).items() if v not in (None, False, "")}
    if p.get("sem_fundo"):
        p["modelo_recorte"] = p.get("modelo_recorte") or MODELO_RECORTE
    return p


def _enquadrar(img: Any, largura: int, altura: int, modo: str) -> Any:
    """Cover: corte centralizado. Contain: faixas transparentes. Origem: Instagram-Carrosseis/galeria/processar.py:35-56."""
    from PIL import Image

    w, h = img.size
    if modo == "cover":
        k = max(largura / w, altura / h)
        nw, nh = round(w * k), round(h * k)
        redim = img.resize((nw, nh), Image.LANCZOS)
        x, y = (nw - largura) // 2, (nh - altura) // 2
        return redim.crop((x, y, x + largura, y + altura))
    k = min(largura / w, altura / h)
    nw, nh = round(w * k), round(h * k)
    redim = img.resize((nw, nh), Image.LANCZOS)
    tela = Image.new(img.mode, (largura, altura), (0, 0, 0, 0) if img.mode == "RGBA" else (0, 0, 0))
    tela.paste(redim, ((largura - nw) // 2, (altura - nh) // 2))
    return tela


def _remover_fundo(img: Any, modelo: str) -> Any:
    try:
        from rembg import new_session, remove
    except ImportError as erro:  # pragma: no cover - rembg é dependência declarada (D-42)
        raise ErroRender("o slot pede `sem_fundo` e o rembg não está instalado") from erro
    return remove(img, session=new_session(modelo))


def cache_tratadas_padrao() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "expxmedia" / "tratadas"


def tratar_imagem(arq: Path | str, tratamento: dict[str, Any] | None, pasta: Path | str | None = None) -> Path:
    """Caminho da imagem tratada (ou a própria, sem tratamento), em cache por impressão digital.
    Ordem fixa: tira o fundo, trata a cor, e só então enquadra."""
    arq = Path(arq)
    t = _pedido(tratamento)
    if not t:
        return arq
    h = hashlib.sha256(arq.read_bytes())
    h.update(json.dumps(t, sort_keys=True, ensure_ascii=False).encode())
    destino = (Path(pasta) if pasta else cache_tratadas_padrao()) / f"{arq.stem[:40]}-{h.hexdigest()[:16]}.png"
    if destino.is_file():
        return destino
    from PIL import Image, ImageEnhance, ImageOps

    with Image.open(arq) as bruta:
        img = ImageOps.exif_transpose(bruta)
        img.load()
    if t.get("sem_fundo"):
        img = _remover_fundo(img, t["modelo_recorte"])
    img = img.convert("RGBA")
    alfa = img.split()[3]
    if t.get("pb"):
        img = Image.merge("RGBA", (*ImageOps.grayscale(img.convert("RGB")).convert("RGB").split(), alfa))
    if t.get("contraste"):
        img = Image.merge("RGBA", (*ImageEnhance.Contrast(img.convert("RGB")).enhance(float(t["contraste"])).split(), alfa))
    if t.get("enquadrar"):
        largura, altura = _medida(t["enquadrar"])  # type: ignore[misc]
        img = _enquadrar(img, largura, altura, t.get("modo") or MODO_PADRAO_RENDER)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".tmp.png")
    img.save(temporario, "PNG")
    temporario.replace(destino)
    return destino


# ---------------------------------------------------------------- HTML


def _data_uri(arq: Path) -> str:
    tipo = mimetypes.guess_type(arq.name)[0] or "application/octet-stream"
    if arq.suffix.lower() == ".woff2":
        tipo = "font/woff2"
    return f"data:{tipo};base64,{base64.b64encode(arq.read_bytes()).decode()}"


def embutir_assets(texto: str, pasta: Path) -> str:
    """`assets/x.svg` no CSS e nos fragmentos vira data URI: o HTML é carregado sem endereço."""
    raiz_assets = (pasta / "assets").resolve()

    def troca(m: re.Match[str]) -> str:
        arq = (pasta / "assets" / m.group(2)).resolve()
        if arq.is_file() and raiz_assets in arq.parents:
            return m.group(1) + _data_uri(arq)
        return m.group(0)

    return re.sub(r"""(["'(])assets/([^"')\s]+)""", troca, texto)


def _no_caminho(dados: Any, caminho: str) -> Any:
    atual = dados
    for parte in caminho.split("."):
        if not isinstance(atual, dict):
            return None
        atual = atual.get(parte)
    return atual


def _asset_padrao(m: dict[str, Any], spec: dict[str, Any], alma: Any, raiz: Path | None) -> Path | None:
    """O arquivo que preenche um slot `asset` vazio: o asset neutro do template, ou o da Alma que
    substitui um asset de marca (CONTRATO-template, "Assets: o que é identidade")."""
    ident = spec.get("asset")
    registro = next((a for a in m.get("assets") or [] if isinstance(a, dict) and a.get("id") == ident), None)
    if registro is None:
        return None
    classe = registro.get("classe") or "marca"  # sem classificação é tratado como marca: na dúvida, não vaza
    if classe == "neutro":
        arq = (Path(m["_dir"]) / str(registro.get("arquivo") or "")).resolve()
        return arq if arq.is_file() and Path(m["_dir"]).resolve() in arq.parents else None
    alvo = registro.get("substituir_por")
    if classe == "marca" and isinstance(alvo, str) and alvo.startswith("alma.") and raiz is not None:
        relativo = _no_caminho(alma.dados if hasattr(alma, "dados") else alma, alvo[len("alma."):])
        if isinstance(relativo, str) and relativo.strip() and not erro_de_imagem(relativo):
            arq = (Path(raiz) / relativo).resolve()
            return arq if arq.is_file() and Path(raiz).resolve() in arq.parents else None
    return None  # pessoa: o retrato do porta-voz entra pela copy


def html_do_slide(
    m: dict[str, Any],
    copy: dict[str, Any],
    i: int,
    *,
    cabeca: str,
    base_copy: Path | str | None = None,
    alma: Any = None,
    raiz: Path | str | None = None,
    cache_tratadas: Path | str | None = None,
) -> str:
    """O HTML completo do slide `i` (1-based). `cabeca` é o CSS do motor (fontes + tokens da Alma)."""
    pasta = Path(m["_dir"])
    slides = copy["slides"]
    s = dict(slides[i - 1])
    kind = m["kinds"][s["kind"]]
    for nome, spec in (kind.get("slots") or {}).items():
        valor = s.get(nome)
        if _slot_imagem(spec):
            if isinstance(valor, str) and valor.startswith("data:image/"):
                continue
            if valor:
                base = Path(base_copy or pasta).resolve()
                arq = (base / valor).resolve()
                if erro_de_imagem(valor) or base not in arq.parents or not arq.is_file():  # resolve() também pega symlink para fora
                    raise ErroRender(f"slide {i}: imagem '{valor}' não existe dentro da pasta da copy (caminho relativo a ela)")
            else:
                arq = _asset_padrao(m, spec, alma, Path(raiz) if raiz else None)
                if arq is None:
                    s[nome] = ""
                    continue
            s[nome] = _data_uri(tratar_imagem(arq, spec.get("tratamento"), cache_tratadas))
        elif spec.get("tipo") == "lista" and spec.get("campos") and isinstance(valor, list):
            # campo opcional ausente é vazio, não o slot homônimo do slide
            s[nome] = [{c: item.get(c, "") for c in spec["campos"]} for item in valor]
    fragmento = pasta / "slides" / f"{s['kind']}.html"
    if not fragmento.is_file():
        raise ErroRender(f"o template não tem slides/{s['kind']}.html")
    modelo = embutir_assets(fragmento.read_text(encoding="utf-8"), pasta)  # antes de preencher: texto da copy não vira asset
    miolo = preencher(modelo, [{"_n": i, "_nn": f"{i:02d}", "_total": len(slides)}, s])
    w, h = m["canvas"]["w"], m["canvas"]["h"]
    base_css = f"*{{box-sizing:border-box}}html,body{{margin:0;padding:0}}.slide{{width:{w}px;height:{h}px;position:relative;overflow:hidden}}"
    fixo = ' data-fit="fixo"' if kind.get("fit") == "fixo" else ""
    corpo = f'<section class="slide {html_lib.escape(s["kind"])}" id="slide-{i}"{fixo}>{miolo}</section>'
    css_arq = pasta / CSS
    css = embutir_assets(css_arq.read_text(encoding="utf-8"), pasta) if css_arq.is_file() else ""
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{cabeca}{base_css}{css}</style></head><body>{corpo}</body></html>'


# ---------------------------------------------------------------- fontes


_URL_ARQUIVO = re.compile(r"url\(\s*(['\"]?)(file://[^'\")]+)\1\s*\)")


def _preparar_fontes(alma: Any, raiz: Path | None, cache: Path | str | None, url_fontes: str) -> tuple[str, list[dict[str, Any]], list[str], list[dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
    """(CSS @font-face com data URI, relato por papel, famílias usadas, impressão das fontes,
    família usada por papel, avisos `fonte_substituida`).

    As famílias são as de fato resolvidas: fonte da Alma que não resolveu (sem rede, sem cache,
    arquivo ausente) vira a Inter embarcada na pilha CSS, no @font-face e na checagem de fonte
    carregada, com aviso explícito da família pedida e da usada (D-21), e não reprova a peça.
    """
    css, resolvidas = _fontes.css_fontes(alma, raiz=raiz, cache=cache, url_base=url_fontes)
    permitidos = {p.resolve() for r in resolvidas for p in r.arquivos}
    permitidos |= {p.resolve() for p in _fontes.PASTA_INTER.glob("*.woff2")}

    def embutir(m: re.Match[str]) -> str:
        caminho = Path(url2pathname(urllib.parse.urlsplit(m.group(2)).path)).resolve()
        if caminho in permitidos and caminho.is_file():
            return f"url('{_data_uri(caminho)}')"
        return m.group(0)  # fica file:// e a rede fechada barra

    css = _URL_ARQUIVO.sub(embutir, css)
    relato = [{"papel": r.papel, "familia": r.familia, "origem": r.origem, "aviso": r.aviso} for r in resolvidas]
    familias = list(dict.fromkeys([r.familia for r in resolvidas] + [_tokens.FAMILIA_RESERVA]))
    por_papel = {r.papel: r.familia for r in resolvidas}
    avisos = [{"tipo": "fonte_substituida", "papel": r.papel, "pedida": r.pedida, "usada": r.familia,
               "detalhe": f"fonte '{r.pedida}' ({r.papel}) substituída pela '{r.familia}' embarcada: {r.aviso}"}
              for r in resolvidas if r.origem == "embarcada" and r.pedida]
    impressao = [{"papel": r.papel, "familia": r.familia, "origem": r.origem,
                  "arquivos": sorted(hashlib.sha256(p.read_bytes()).hexdigest() for p in r.arquivos if p.is_file())}
                 for r in resolvidas]
    return css, relato, familias, impressao, por_papel, avisos


# ---------------------------------------------------------------- render


def _agora(alma: Any) -> str:
    dados = alma.dados if hasattr(alma, "dados") else alma
    fuso = ((dados or {}).get("empresa") or {}).get("fuso")
    try:
        momento = datetime.now(ZoneInfo(fuso)) if isinstance(fuso, str) and fuso else datetime.now().astimezone()
    except (KeyError, ValueError):
        momento = datetime.now().astimezone()
    return momento.isoformat(timespec="seconds")


def _falha(m: dict[str, Any] | None, erros: list[str]) -> dict[str, Any]:
    return {"expxmedia_render": 1, "ok": False, "template": (m or {}).get("template_id"), "erros": erros, "avisos": [], "slides": []}


def renderizar(
    template: Path | str | dict[str, Any],
    copy: dict[str, Any] | Path | str,
    alma: Any,
    saida: Path | str,
    *,
    raiz: Path | str | None = None,
    base_copy: Path | str | None = None,
    cache_fontes: Path | str | None = None,
    url_fontes: str = _fontes.URL_GOOGLE_FONTS,
    cache_tratadas: Path | str | None = None,
    salvar_html: bool = False,
    gerar_prancha: bool = True,
    exemplo: bool = False,
    timeout_ms: float = 30_000,
    log: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Renderiza a copy no template com a Alma e mede cada slide.

    `copy`: dict `{"slides": [{"kind": ..., <slot>: ...}]}` ou caminho de um JSON (a pasta dele
    vira `base_copy`, contra a qual caminho relativo de imagem é resolvido). Devolve o relatório
    (o mesmo gravado em `saida/render.json`); `ok` é falso se algum slide tem problema.
    """
    try:
        m = carregar_template(template)
    except (arquivos.ErroArquivo, ErroRender) as erro:
        return _falha(None, [str(erro)])
    if not isinstance(copy, dict):
        base_copy = base_copy or Path(copy).parent
        copy = arquivos.ler_json(copy)
    erros = _nomes_inseguros(m) or validar_copy(m, copy, exemplo=exemplo)
    if erros:
        return _falha(m, erros)
    try:
        _tokens.tokens(alma)
    except _tokens.ErroTokens as erro:
        return _falha(m, [str(erro)])
    raiz_p = Path(raiz) if raiz is not None else None
    fit, tipografia = encaixe.configuracao(m)
    css_fontes, relato_fontes, familias, impressao_fontes, familia_por_papel, avisos_fontes = _preparar_fontes(
        alma, raiz_p, cache_fontes, url_fontes)
    # a pilha --alma-fonte-* nomeia a família de fato usada (D-21), coerente com @font-face e checagem
    tokens = _tokens.tokens(alma, familia_por_papel)
    cabeca = css_fontes + _tokens.tokens_css(alma, familias=familia_por_papel)
    if log:
        for a in avisos_fontes:
            log(f"aviso: {a['detalhe']}")
    try:
        documentos = [html_do_slide(m, copy, i, cabeca=cabeca, base_copy=base_copy, alma=alma, raiz=raiz_p,
                                    cache_tratadas=cache_tratadas) for i in range(1, len(copy["slides"]) + 1)]
    except (ErroRender, ValueError) as erro:
        return _falha(m, [str(erro)])

    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    canvas = {"w": int(m["canvas"]["w"]), "h": int(m["canvas"]["h"])}
    recorte = {"x": 0, "y": 0, "width": canvas["w"], "height": canvas["h"]}
    relato: list[dict[str, Any]] = []
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            # Template pode vir de terceiros: página sem JavaScript próprio (o encaixe roda por fora,
            # via evaluate) e sem rede nenhuma — é isto, e não a validação de texto, que impede o
            # template de mandar dado para fora.
            pagina = navegador.new_page(viewport={"width": canvas["w"], "height": canvas["h"]},
                                        device_scale_factor=1, java_script_enabled=False)
            barrados: list[str] = []

            def porteiro(rota: Any) -> None:
                url = urllib.parse.urlsplit(rota.request.url)
                if url.scheme in ESQUEMAS_LIBERADOS:
                    rota.continue_()
                    return
                barrados.append(url.hostname or url.scheme)
                rota.abort()

            pagina.route("**/*", porteiro)
            for i, (s, doc) in enumerate(zip(copy["slides"], documentos), 1):
                barrados.clear()
                if salvar_html:
                    (saida / f"slide_{i}.html").write_text(doc, encoding="utf-8")
                pagina.set_content(doc, wait_until="networkidle", timeout=timeout_ms)
                pagina.evaluate("document.fonts.ready.then(()=>1)")
                pagina.wait_for_timeout(ESPERA_FONTES_MS)
                resultado_encaixe = encaixe.encaixar(pagina, fit)
                medida = encaixe.medir(pagina, fit, tipografia, familias)
                caixas = medida.pop("caixas", [])
                medida["problemas"] += [{"tipo": "rede_barrada", "detalhe": f"rede barrada: o layout tentou buscar {h}"}
                                        for h in sorted(set(barrados))]
                # peça com a fonte errada não é peça pronta: família da Alma usada em algum texto e não carregada reprova
                # só as famílias que algum texto do slide usa, no peso e estilo em que usa: o navegador não baixa
                # face que nenhum texto pede (a origem conferia só o peso normal, e título só em negrito reprovava à toa)
                usadas = pagina.evaluate(USADAS_JS)
                medida["problemas"] += [{"tipo": "fonte_nao_carregou", "detalhe": f"fonte '{f}' não carregou"} for f in familias
                                        if any(not pagina.evaluate(CHECA_FONTE_JS, [u, f]) for u in usadas.get(f.lower(), []))]
                arte = pagina.screenshot(path=str(saida / f"slide_{i}.png"), clip=recorte)
                fundo = contraste.foto_sem_tinta(pagina, recorte)  # o mesmo slide sem a tinta do texto
                medida["problemas"] += contraste.conferir_leitura(arte, fundo, caixas, tipografia)
                if not m["kinds"][s["kind"]].get("vazio_ok"):
                    medida["problemas"] += encaixe.conferir_ocupacao(arte, tipografia)
                medida["avisos"] += encaixe.aviso_de_zoom(resultado_encaixe, fit["container"])
                relato.append({"slide": i, "kind": s["kind"], "arquivo": f"slide_{i}.png", "encaixe": resultado_encaixe,
                               "problemas": medida["problemas"], "avisos": medida["avisos"],
                               "fontes_com_erro": medida["fontes_com_erro"]})
                if log:
                    log(f"slide_{i}.png  {s['kind']:14s} {resultado_encaixe}"
                        + "".join(f"\n   PROBLEMA {x['detalhe']}" for x in medida["problemas"])
                        + "".join(f"\n   aviso: {x['detalhe']}" for x in medida["avisos"]))
        finally:
            navegador.close()

    impressao = prancha.impressao_digital(Path(m["_dir"]), m, copy, tokens, impressao_fontes,
                                          extras={"canvas": canvas, "base_copy": _imagens_da_copy(copy, base_copy)})
    resultado = {
        "expxmedia_render": 1,
        "ok": not any(r["problemas"] for r in relato),
        "template": m.get("template_id"),
        "impressao": impressao,
        "em": _agora(alma),
        "canvas": canvas,
        "fontes": relato_fontes,
        "avisos": avisos_fontes,
        "erros": [],
        "slides": relato,
        "prancha": None,
    }
    if gerar_prancha:
        prancha.gerar_prancha([saida / r["arquivo"] for r in relato], saida / prancha.NOME_PRANCHA)
        resultado["prancha"] = prancha.NOME_PRANCHA
    prancha.gravar_relatorio(saida, resultado)
    return resultado


def _imagens_da_copy(copy: dict[str, Any], base_copy: Path | str | None) -> list[str]:
    """sha256 das imagens que a copy aponta por caminho: trocar o arquivo muda o PNG."""
    if base_copy is None:
        return []
    base = Path(base_copy)
    hashes = []
    for s in copy.get("slides") or []:
        for v in (s or {}).values():
            if isinstance(v, str) and not v.startswith("data:") and Path(v).suffix.lower() in IMAGENS and not erro_de_imagem(v):
                arq = base / v
                if arq.is_file():
                    hashes.append(v + ":" + hashlib.sha256(arq.read_bytes()).hexdigest())
    return hashes
