"""Palco da apresentação: `apresentacao.html` autocontida e navegável por teclado.

Porte de `palco_html` + `apresentacoes/palco.html` da origem (youtube-squad), com duas mudanças:

1. **Os slides são HTML**, não um `<video>` por slide: a apresentação existe sem render de vídeo
   (CONTRATO-peca: o `papel: final` da apresentação é o HTML navegável; o MP4 é extra). Cada tipo
   de slide do deck é desenhado com a moldura e as medidas das cenas de `apresentacoes/motion`
   (fundo em malha, cabeçalho `NN / TOTAL`, entradas escalonadas, palavra a palavra com `<b>` na
   cor de destaque, tamanho de título como teto), num quadro de 1920×1080 escalado para a tela.
2. **Autocontida e sem marca**: fontes da Alma e imagens entram como data URI (abre por
   `file://`, sem rede); cores e famílias vêm dos tokens `--alma-*` (M13). A cor do `tema` do deck
   troca só o destaque; o CTA fica sempre na cor da casa (`destaque` da Alma).

O teclado é o da origem: → espaço PageDown Enter avançam; ← PageUp Backspace voltam; Home/End;
F tela cheia; R repete a animação; clique na metade esquerda/direita; `#N` abre no slide N; o HUD
some depois de 3 s sem mouse.

Imagem citada e ausente em `ativos/` sai como `null`, com aviso (origem: D-48 da apresentação):
o slide mostra a moldura com o texto, nunca uma imagem quebrada.

Uso:

    from expxmedia.producao.apresentacao import palco
    r = palco.gerar(deck, alma, "saida/apresentacao.html", raiz=raiz, ativos="ativos/")
    # {"arquivo": Path, "slides": 9, "avisos": [...], "fontes": [...]}
"""
from __future__ import annotations

import html as _html
import re
from pathlib import Path
from typing import Any

from expxmedia.alma import fontes as _fontes
from expxmedia.alma import tokens as _tokens
from expxmedia.producao.apresentacao import deck as _deck
from expxmedia.render_html import renderizar as _render

__all__ = [
    "ErroDeck",
    "MODELO",
    "LARGURA",
    "ALTURA",
    "rotulo",
    "url_visivel",
    "resolver_imagens",
    "html_palco",
    "gerar",
]

MODELO = Path(__file__).resolve().parents[2] / "recursos" / "palco.html"
# origem: youtube-squad/apresentacoes/motion/src/deck.ts:42-45 (1920x1080)
LARGURA = 1920
ALTURA = 1080
# Slide.tsx:16-20: pad = 5% da largura, u = largura / 1920
PAD = round(LARGURA * 0.05)
INTERNO = LARGURA - 2 * PAD
ALTURA_UTIL = ALTURA - 2 * PAD
# Fluxo.tsx:11-13: primeiro nó no quadro 24, um nó a cada 9 quadros, seta 5 quadros depois
FLUXO_INICIO = 24
FLUXO_POR_NO = 9
FLUXO_SETA_ATRASO = 5
# Etapas.tsx:14 horizontal com 4 ou mais itens; Grade.tsx:10 até 4 colunas, senão 3
ETAPAS_HORIZONTAL_A_PARTIR = 4
GRADE_MAX_COLUNAS = 4
# Estatisticas.tsx:12 tamanho do número conforme 1, 2 ou 3+ números
TAMANHO_NUMERO = {1: 200, 2: 150}
TAMANHO_NUMERO_MUITOS = 110
VARIANTES = ("", "v-esq", "v-desce", "v-dir")  # Entrance.tsx:19-22 (rise, left, fall, right)


class ErroDeck(ValueError):
    """O deck não cumpre o schema; `achados` traz todos de uma vez."""

    def __init__(self, achados: list[dict[str, str]]) -> None:
        super().__init__("deck inválido: " + "; ".join(f"{a['campo']}: {a['detalhe']}" for a in achados))
        self.achados = list(achados)


# ---------------------------------------------------------------- apoio


def _dados(alma: Any) -> dict[str, Any]:
    return (alma.dados if hasattr(alma, "dados") else alma) or {}


def _esc(texto: Any) -> str:
    return _html.escape(str(texto), quote=True)


def _empresa(alma: Any) -> str:
    empresa = _dados(alma).get("empresa") or {}
    for chave in ("nome_curto", "nome"):
        if isinstance(empresa.get(chave), str) and empresa[chave].strip():
            return empresa[chave].strip()
    return ""


def rotulo(d: dict[str, Any], alma: Any) -> str:
    """O nome no cabeçalho dos slides: o do tema do deck, senão o da empresa (Alma)."""
    tema = d.get("tema")
    if isinstance(tema, dict) and isinstance(tema.get("nome"), str) and tema["nome"].strip():
        return tema["nome"].strip()
    return _empresa(alma)


def url_visivel(url: str | None) -> str:
    """O endereço como aparece no slide: sem esquema, sem `www.` e sem barra final."""
    if not isinstance(url, str):
        return ""
    return re.sub(r"^(?:[a-z][a-z0-9+.-]*:)?//", "", url.strip(), flags=re.I).removeprefix("www.").rstrip("/")


def resolver_imagens(d: dict[str, Any], ativos: Path | str | None) -> tuple[dict[str, Any], list[str]]:
    """Cópia do deck com cada imagem trocada pelo arquivo resolvido em `ativos/` (ou `None` + aviso).

    origem: youtube-squad/apresentacao.py:856-872 (D-48 de lá: imagem ausente vira null, o deck não muda)
    """
    import copy

    d = copy.deepcopy(d)
    avisos: list[str] = []
    base = Path(ativos).resolve() if ativos is not None else None

    def confere(onde: str, nome: Any) -> Path | None:
        if not isinstance(nome, str) or not nome:
            return None
        arq = (base / nome).resolve() if base is not None else None
        if arq is None or base not in arq.parents or not arq.is_file():
            avisos.append(f"{onde}: ativos/{nome} não existe; o slide sai sem a imagem")
            return None
        return arq

    if isinstance(d.get("tema"), dict):
        d["tema"]["logo"] = confere("tema.logo", d["tema"].get("logo"))
    for i, s in enumerate(d.get("slides") or []):
        if isinstance(s, dict) and "imagem" in s:
            s["imagem"] = confere(f"slides[{i}].imagem", s.get("imagem"))
    return d, avisos


def _img(arq: Path | None, alt: str = "") -> str:
    return f'<img src="{_render._data_uri(arq)}" alt="{_esc(alt)}">' if arq is not None else ""


def _e(conteudo: str, d: int, *, tag: str = "div", classe: str = "", variante: str = "", sobe: int | None = None,
       estilo: str = "") -> str:
    """Elemento com entrada: `d` é o atraso em quadros (Entrance.tsx `delay`)."""
    classes = " ".join(c for c in ("e", variante, classe) if c)
    estilo = f"--d:{d}" + (f";--sobe:{sobe}px" if sobe is not None else "") + (f";{estilo}" if estilo else "")
    return f'<{tag} class="{classes}" style="{estilo}">{conteudo}</{tag}>'


def _tokens_palavras(texto: str) -> list[tuple[str, bool]]:
    """Palavras do texto e se estão em `<b>`. origem: youtube-squad/apresentacoes/motion/src/components/WordReveal.tsx:9-20"""
    saida: list[tuple[str, bool]] = []
    for parte in re.split(r"(<b>.*?</b>)", texto):
        if not parte:
            continue
        m = re.fullmatch(r"<b>(.*?)</b>", parte)
        trecho = m.group(1) if m else parte
        saida.extend((w, bool(m)) for w in trecho.split(" ") if w)
    return saida


def _revela(texto: str, *, tag: str, atraso: int, teto: float, largura: float, por: int = 3, classe: str = "") -> str:
    """WordReveal: uma palavra a cada `por` quadros a partir de `atraso`; `teto` é o tamanho máximo."""
    palavras = "".join(
        f'<span class="p{" b" if b else ""}" style="--d:{atraso + i * por}">{_esc(w)}</span>'
        for i, (w, b) in enumerate(_tokens_palavras(texto))
    )
    classes = " ".join(c for c in ("revela", classe) if c)
    return (f'<{tag} class="{classes}" data-teto="{teto:g}" data-largura="{largura:g}" '
            f'style="font-size:{teto:g}px">{palavras}</{tag}>')


def _formatar_numero(valor: float) -> tuple[str, int]:
    casas = 0 if float(valor).is_integer() else 1  # Counter.tsx:17
    texto = f"{valor:,.{casas}f}".replace(",", " ") if casas else f"{int(valor):,}".replace(",", " ")
    return texto, casas


# ---------------------------------------------------------------- cenas


def _secao(texto: str) -> str:
    return _e(_esc(texto), 4, tag="h2", classe="secao")


def _cena_titulo(s: dict[str, Any]) -> str:
    partes = []
    if s.get("kicker"):
        partes.append(_e(_esc(s["kicker"]), 4, tag="p", classe="kicker"))
    partes.append(_revela(s["titulo"], tag="h1", atraso=8, teto=138, largura=INTERNO * 0.88))
    partes.append('<div class="linha"></div>')
    if s.get("subtitulo"):
        partes.append(_e(_esc(s["subtitulo"]), 36, tag="p", classe="subtitulo"))
    return "".join(partes)


def _cena_declaracao(s: dict[str, Any]) -> str:
    autor = _e(_esc(s["autor"]), 44, tag="p", classe="autor") if s.get("autor") else ""
    return ('<div class="bloco">' + _e('<span class="aspas">“</span>', 2, variante="v-pop")
            + "<div>" + _revela(s["texto"], tag="p", atraso=8, teto=82, largura=INTERNO * 0.78) + autor + "</div></div>")


def _cena_grade(s: dict[str, Any]) -> str:
    itens = s["itens"]
    colunas = min(len(itens), GRADE_MAX_COLUNAS) if len(itens) <= GRADE_MAX_COLUNAS else 3
    cartoes = "".join(
        _e(f'<div class="cartao"><p class="ordem">{i + 1:02d}</p><h3>{_esc(it["titulo"])}</h3><p>{_esc(it["texto"])}</p></div>',
           22 + i * 5, variante=VARIANTES[i % 4])
        for i, it in enumerate(itens)
    )
    return _secao(s["titulo"]) + f'<div class="cartoes" style="grid-template-columns:repeat({colunas},minmax(0,1fr))">{cartoes}</div>'


def _coluna(col: dict[str, Any], destaque: bool, inicio: int) -> str:
    itens = "".join(_e(_esc(item), inicio + j * 5, tag="p") for j, item in enumerate(col["itens"]))
    return f'<div class="coluna{" destaque" if destaque else ""}"><h3>{_esc(col["titulo"])}</h3><div class="itens">{itens}</div></div>'


def _cena_comparacao(s: dict[str, Any]) -> str:
    return (_secao(s["titulo"]) + '<div class="colunas">'
            + _e(_coluna(s["esquerda"], False, 30), 18, variante="v-dir")
            + _e(_coluna(s["direita"], True, 36), 24, variante="v-esq") + "</div>")


def _cena_etapas(s: dict[str, Any]) -> str:
    itens = s["itens"]
    horizontal = len(itens) >= ETAPAS_HORIZONTAL_A_PARTIR
    passos = "".join(
        _e(f'<div class="passo"><span class="bola">{i + 1}</span><div><h3>{_esc(it["titulo"])}</h3><p>{_esc(it["texto"])}</p></div></div>',
           24 + i * 6, variante="" if horizontal else "v-esq")
        for i, it in enumerate(itens)
    )
    grade = f' style="grid-template-columns:repeat({len(itens)},minmax(0,1fr))"' if horizontal else ""
    return (_secao(s["titulo"]) + f'<div class="trilho-caixa{" horizontal" if horizontal else ""}"><div class="trilho"></div>'
            f'<div class="passos"{grade}>{passos}</div></div>')


def _cena_estatisticas(s: dict[str, Any]) -> str:
    numeros = s["numeros"]
    tamanho = TAMANHO_NUMERO.get(len(numeros), TAMANHO_NUMERO_MUITOS)
    cartoes = []
    for i, n in enumerate(numeros):
        texto, casas = _formatar_numero(n["valor"])
        sufixo = n.get("sufixo") or ""
        valor = (f'<div class="valor" style="font-size:{tamanho}px" data-alvo="{n["valor"]}" data-casas="{casas}" '
                 f'data-sufixo="{_esc(sufixo)}" data-atraso="{24 + i * 6}">{_esc(texto + sufixo)}</div>')
        cartoes.append(_e(f'<div class="cartao">{valor}<p class="rotulo">{_esc(n["rotulo"])}</p>'
                          f'<p class="fonte">fonte: {_esc(n["fonte"])}</p></div>', 20 + i * 6))
    return (_secao(s["titulo"]) + f'<div class="numeros" style="grid-template-columns:repeat({len(numeros)},minmax(0,1fr))">'
            + "".join(cartoes) + "</div>")


def _caixas(n: int) -> tuple[list[dict[str, float]], float]:
    """Posição dos nós do fluxo. origem: youtube-squad/apresentacoes/motion/src/scenes/Fluxo.tsx:17-31"""
    linhas = 1 if n <= 4 else 2
    colunas = n if linhas == 1 else -(-n // 2)
    gap_x, gap_y = 96, 120
    w = (INTERNO - gap_x * (colunas - 1)) / colunas
    h = 230 if linhas == 1 else 200
    itens = []
    for i in range(n):
        linha, coluna = divmod(i, colunas)
        itens.append({"x": coluna * (w + gap_x), "y": linha * (h + gap_y), "w": w, "h": h, "linha": linha})
    return itens, linhas * h + (linhas - 1) * gap_y


def _seta(a: dict[str, float], b: dict[str, float]) -> tuple[str, float, float, float]:
    """Caminho da seta entre dois nós, comprimento e ponta. origem: .../scenes/Fluxo.tsx:34-49"""
    folga = 14
    if a["linha"] == b["linha"]:
        x1, x2, y = a["x"] + a["w"] + folga, b["x"] - folga, a["y"] + a["h"] / 2
        return f"M {x1:.1f} {y:.1f} L {x2:.1f} {y:.1f}", max(1.0, x2 - x1), x2, y
    x1, y1 = a["x"] + a["w"] + folga, a["y"] + a["h"] / 2
    x_dir = x1 + 34
    y_meio = a["y"] + a["h"] + (b["y"] - (a["y"] + a["h"])) / 2
    x_esq = b["x"] - 34 - folga
    x2, y2 = b["x"] - folga, b["y"] + b["h"] / 2
    d = f"M {x1:.1f} {y1:.1f} L {x_dir:.1f} {y1:.1f} L {x_dir:.1f} {y_meio:.1f} L {x_esq:.1f} {y_meio:.1f} L {x_esq:.1f} {y2:.1f} L {x2:.1f} {y2:.1f}"
    comprimento = (x_dir - x1) + (y_meio - y1) + (x_dir - x_esq) + (y2 - y_meio) + (x2 - x_esq)
    return d, comprimento, x2, y2


def _cena_fluxo(s: dict[str, Any]) -> str:
    nos = s["nos"]
    n = len(nos)
    caixas, altura = _caixas(n)
    fim = FLUXO_INICIO + n * FLUXO_POR_NO + 30  # Fluxo.tsx:57
    setas = []
    for i, (a, b) in enumerate(zip(caixas, caixas[1:])):
        d, comprimento, px, py = _seta(a, b)
        atraso = FLUXO_INICIO + (i + 1) * FLUXO_POR_NO + FLUXO_SETA_ATRASO
        setas.append(f'<path d="{d}" style="--len:{comprimento:.1f};--d:{atraso}"></path>'
                     f'<path class="ponta" style="--d:{atraso + 12}" '
                     f'd="M {px - 9:.1f} {py - 5:.1f} L {px + 1:.1f} {py:.1f} L {px - 9:.1f} {py + 5:.1f} z"></path>')
    blocos = []
    for i, (no, c) in enumerate(zip(nos, caixas)):
        texto = f'<p>{_esc(no["texto"])}</p>' if no.get("texto") else ""
        cartao = f'<div class="cartao" style="height:100%"><span class="ordem">{i + 1:02d}</span><h3>{_esc(no["titulo"])}</h3>{texto}</div>'
        blocos.append(
            f'<div class="no" style="left:{c["x"]:.1f}px;top:{c["y"]:.1f}px;width:{c["w"]:.1f}px;height:{c["h"]:.1f}px;'
            f'--i:{i};--n:{n};--fim:{fim}">'
            + _e(cartao, FLUXO_INICIO + i * FLUXO_POR_NO, variante="" if i % 2 == 0 else "v-desce", estilo="height:100%")
            + "</div>"
        )
    blocos_html = "".join(blocos)
    return (_secao(s["titulo"]) + f'<div class="diagrama" style="width:{INTERNO}px;height:{altura:.1f}px">'
            f'<svg width="{INTERNO}" height="{altura:.1f}" viewBox="0 0 {INTERNO} {altura:.1f}">{"".join(setas)}</svg>'
            f"{blocos_html}</div>")


def _cena_screenshot(s: dict[str, Any]) -> str:
    img = s.get("imagem")
    janela = (_img(img, s.get("legenda") or s["titulo"]) if img is not None
              else f'<div class="vazia">{_esc(s.get("legenda") or "captura não disponível")}</div>')
    moldura = f'<div class="barra-janela"><i></i><i></i><i></i></div><div class="janela">{janela}</div>'
    legenda = _e(_esc(s["legenda"]), 30, tag="p", classe="legenda") if s.get("legenda") and img is not None else ""
    return _e(_esc(s["titulo"]), 4, tag="h2") + _e(moldura, 14, classe="moldura", sobe=40) + legenda


def _cena_cta(s: dict[str, Any], empresa: str) -> str:
    destino = url_visivel(s.get("url"))
    esquerda = []
    if s.get("titulo"):
        esquerda.append(_revela(s["titulo"], tag="h1", atraso=8, teto=96, largura=INTERNO * 0.5))
    if s.get("texto"):
        esquerda.append(_e(_esc(s["texto"]), 30, tag="p", classe="texto"))
    if destino:
        esquerda.append(_e(_esc(destino), 40, classe="chip", variante="v-pop"))
    img = s.get("imagem")
    if img is not None:
        cartaz = _img(img, destino or empresa)
    else:
        cartaz = (f'<div class="vazia"><span class="nome">{_esc(empresa)}</span>'
                  + (f'<span class="destino">{_esc(destino)}</span>' if destino else "") + "</div>")
    return ('<div class="colunas"><div>' + "".join(esquerda) + "</div>"
            + _e(f'<div class="cartaz">{cartaz}</div>', 16, variante="v-esq") + "</div>")


def _slide(s: dict[str, Any], i: int, total: int, *, rotulo_slide: str, logo: Path | None, empresa: str) -> str:
    tipo = s["tipo"]
    if tipo == "titulo":
        miolo = _cena_titulo(s)
    elif tipo == "declaracao":
        miolo = _cena_declaracao(s)
    elif tipo == "grade":
        miolo = _cena_grade(s)
    elif tipo == "comparacao":
        miolo = _cena_comparacao(s)
    elif tipo == "etapas":
        miolo = _cena_etapas(s)
    elif tipo == "estatisticas":
        miolo = _cena_estatisticas(s)
    elif tipo == "fluxo":
        miolo = _cena_fluxo(s)
    elif tipo == "screenshot":
        miolo = _cena_screenshot(s)
    else:
        miolo = _cena_cta(s, empresa)
    # o CTA é da casa: cabeçalho com o nome da empresa e o ponto na cor da casa (Cta.tsx: marcaTexto e cor)
    nome = empresa if tipo == "cta" else rotulo_slide
    marca = (_img(logo, nome) if logo is not None and tipo != "cta" else '<span class="ponto"></span>') + f"<span>{_esc(nome)}</span>"
    cabecalho = _e(f'<span class="contador-slide">{i + 1:02d} / {total:02d}</span><span class="marca">{marca}</span>',
                   0, tag="header", classe="cabecalho", sobe=16)
    titulo = s.get("titulo") or s.get("texto") or tipo
    return (f'<section class="slide t-{tipo}" id="slide-{i + 1}" data-tipo="{tipo}" '
            f'aria-label="slide {i + 1} de {total}: {_esc(re.sub(r"</?b>", "", str(titulo)))}">'
            '<div class="fundo"><i class="b1"></i><i class="b2"></i><i class="malha"></i></div>'
            f'<div class="quadro">{cabecalho}<div class="miolo">{miolo}</div></div>'
            '<div class="acabamento"><i class="tinta"></i><i class="sombra"></i><i class="grao"></i><i class="vinheta"></i></div>'
            "</section>")


# ---------------------------------------------------------------- página


def _estilo_tema(d: dict[str, Any]) -> str:
    tema = d.get("tema")
    cor = tema.get("cor") if isinstance(tema, dict) else None
    if not isinstance(cor, str) or not _deck.HEX.fullmatch(cor):
        return ""
    # theme.ts aplicarMarca: a cor do tema troca só o destaque; o segundo destaque é ela clareada 18%
    return (f":root {{ --cor-destaque: {cor}; "
            f"--cor-destaque-2: color-mix(in srgb, {cor} 82%, white); }}\n")


def html_palco(
    d: dict[str, Any],
    alma: Any,
    *,
    raiz: Path | str | None = None,
    ativos: Path | str | None = None,
    cache_fontes: Path | str | None = None,
    url_fontes: str = _fontes.URL_GOOGLE_FONTS,
    css_template: str | None = None,
    validar: bool = True,
) -> tuple[str, list[str], list[dict[str, Any]]]:
    """(HTML do palco, avisos, relato das fontes). Levanta ErroDeck se o deck não valida."""
    if validar:
        achados = _deck.validar(d, alma=alma)
        if achados:
            raise ErroDeck(achados)
    completo, avisos = _deck.completar_cta(d, alma)
    resolvido, avisos_img = resolver_imagens(completo, ativos)
    avisos += avisos_img
    css_fontes, relato, _familias, _impressao, por_papel, avisos_fonte = _render._preparar_fontes(
        alma, Path(raiz) if raiz is not None else None, cache_fontes, url_fontes)
    avisos += [a["detalhe"] for a in avisos_fonte]
    estilo_alma = css_fontes + "\n" + _tokens.tokens_css(alma, familias=por_papel)
    empresa = _empresa(alma)
    nome = rotulo(completo, alma)
    tema = resolvido.get("tema") if isinstance(resolvido.get("tema"), dict) else {}
    slides = resolvido["slides"]
    corpo = "\n".join(
        _slide(s, i, len(slides), rotulo_slide=nome, logo=tema.get("logo"), empresa=empresa) for i, s in enumerate(slides)
    )
    idioma = ((_dados(alma).get("empresa") or {}).get("idioma")) or ""
    modelo = MODELO.read_text(encoding="utf-8")
    pagina = (modelo.replace("__ESTILO_ALMA__", estilo_alma)
              .replace("__ESTILO_TEMA__", _estilo_tema(d))
              .replace("/*__CSS_TEMPLATE__*/", css_template or "")
              .replace("__IDIOMA__", _esc(idioma))
              .replace("__TITULO__", _esc(d.get("titulo") or "Apresentação"))
              .replace("__ROTULO__", _esc(nome))
              .replace("__TOTAL__", f"{len(slides):02d}")
              .replace("__SLIDES__", corpo))
    return pagina, avisos, relato


def gerar(
    d: dict[str, Any],
    alma: Any,
    saida: Path | str,
    **opcoes: Any,
) -> dict[str, Any]:
    """Grava o palco em `saida` (normalmente `saida/apresentacao.html`) e devolve o relato."""
    pagina, avisos, relato = html_palco(d, alma, **opcoes)
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    temporario = saida.with_name(saida.name + ".tmp")
    temporario.write_text(pagina, encoding="utf-8")
    temporario.replace(saida)
    return {"arquivo": saida, "slides": len(d["slides"]), "avisos": avisos, "fontes": relato}
