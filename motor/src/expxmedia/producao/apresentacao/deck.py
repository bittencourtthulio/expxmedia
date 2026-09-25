"""Deck da apresentação: o schema do `deck.json` e a validação (base/apresentacao-deck.md).

Porte de `validar_deck` da origem com os mesmos tetos de palavras e de itens, sem o que era do
canal de origem:

- **Sem CTA fixo** (M13): o último slide continua sendo `cta`, mas `titulo`, `texto` e `url`
  são opcionais; o que faltar vem da Alma (`cta.padrao` e `cta.destino`) em `completar_cta`.
  A origem exigia uma URL literal da própria marca.
- **Sem marca da empresa no deck**: cor, fontes e nome da empresa vêm da Alma. O antigo bloco
  `marca` (a identidade da ferramenta do tema) vira `tema`, opcional: `{nome, cor, logo}`.
  `cor` troca só a cor de destaque, e precisa de contraste ≥ 3:1 sobre o `fundo` da Alma
  (a origem media contra o fundo fixo dela).
- **Sem pauta nem score** (D-48): `slug`, `pauta_id`, `pauta`, `criado_em` e `gerado_por`
  eram da fila de pautas do canal; ficam fora do deck do núcleo (`de_origem` os descarta).
- A regra "métrica do nosso canal não entra em slide" (regex de YouTube) é política do canal
  de origem, não do núcleo: não foi portada. A `fonte` de todo número continua obrigatória.

Schema (espelhado em `motor/kit-remotion/src/composicoes/Apresentacao/cenas.tsx`):

    {
      "titulo": str,
      "tema": {"nome": str, "cor": "#RRGGBB" | null, "logo": "<arquivo em ativos/>" | null} | null,
      "slides": [6 a 10; o primeiro do tipo "titulo", o último do tipo "cta"]
    }
    Tipos e limites em palavras (<b>palavra</b> só em titulo.titulo e declaracao.texto):
      titulo       {kicker <=4 | null, titulo <=10, subtitulo <=20}
      declaracao   {texto <=20, autor <=4 | null}
      grade        {titulo <=8, itens 3-6 x {titulo <=5, texto <=14}}
      comparacao   {titulo <=8, esquerda {titulo <=4, itens 1-5 x <=8}, direita idem}
      etapas       {titulo <=8, itens 3-5 x {titulo <=4, texto <=10}}
      estatisticas {titulo <=8, numeros 1-4 x {valor número, sufixo texto, rotulo <=4, fonte obrigatória}}
      fluxo        {titulo <=8, nos 3-6 x {titulo <=4, texto <=8 | null}}
      screenshot   {titulo <=6, legenda <=12, imagem "<arquivo em ativos/>" | null}
      cta          {titulo <=10 | null, texto <=16 | null, url texto | null, imagem "<arquivo>" | null}
    Proibido em qualquer texto: travessão, meia-risca e quebra de linha.

Cada achado é `{"campo", "detalhe"}`; lista vazia = deck válido.

Uso:

    from expxmedia.producao.apresentacao import deck
    deck.validar(d)                      # [] quando o deck cumpre o schema
    deck.validar(d, alma=alma)           # + contraste da cor do tema sobre o fundo da Alma
    completo, avisos = deck.completar_cta(d, alma)
"""
from __future__ import annotations

import copy as _copy
import re
from typing import Any

__all__ = [
    "TIPOS",
    "COM_DESTAQUE",
    "SLIDES_MIN",
    "SLIDES_MAX",
    "CONTRASTE_MINIMO",
    "CHAVES_RAIZ",
    "palavras",
    "contraste",
    "validar",
    "validar_slide",
    "completar_cta",
    "de_origem",
    "imagens",
]

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
# origem: youtube-squad/apresentacao.py:83 (imagem é nome de arquivo dentro de ativos/, sem barra)
ARQUIVO_DE_ATIVO = re.compile(r"^[\w.-]+\.(?:png|jpg|jpeg|webp|svg)$", re.I)
TRAVESSAO = "—"
MEIA_RISCA = "–"
# origem: youtube-squad/apresentacao.py:87
CONTRASTE_MINIMO = 3.0
# origem: youtube-squad/apresentacao.py:244 (de 6 a 10 slides)
SLIDES_MIN = 6
SLIDES_MAX = 10
# Teto de palavras por campo. origem: youtube-squad/apresentacao.py:88-94
TIPOS: dict[str, dict[str, int]] = {
    "titulo": {"kicker": 4, "titulo": 10, "subtitulo": 20},
    "declaracao": {"texto": 20, "autor": 4},
    "grade": {"titulo": 8},
    "comparacao": {"titulo": 8},
    "etapas": {"titulo": 8},
    "estatisticas": {"titulo": 8},
    "fluxo": {"titulo": 8},
    "screenshot": {"titulo": 6, "legenda": 12},
    "cta": {"titulo": 10, "texto": 16},
}
# Campos opcionais por tipo. Na origem só `declaracao.autor` era opcional; aqui o kicker também
# (a cena já o tratava como opcional) e o texto do CTA, que vem da Alma quando falta.
OPCIONAIS = {("titulo", "kicker"), ("declaracao", "autor"), ("cta", "titulo"), ("cta", "texto")}
# origem: youtube-squad/apresentacao.py:95
COM_DESTAQUE = {("titulo", "titulo"), ("declaracao", "texto")}
# Itens: (mínimo, máximo, {campo: teto de palavras}). origem: youtube-squad/apresentacao.py:163-212
ITENS = {
    "grade": ("itens", 3, 6, {"titulo": 5, "texto": 14}),
    "etapas": ("itens", 3, 5, {"titulo": 4, "texto": 10}),
}
FLUXO_NOS = (3, 6, 4, 8)  # nós, teto do título, teto do texto. origem: youtube-squad/apresentacao.py:166-176
COMPARACAO = (1, 5, 4, 8)  # itens por lado, teto do título, teto do item. origem: youtube-squad/apresentacao.py:177-188
ESTATISTICAS = (1, 4, 4)  # números, teto do rótulo. origem: youtube-squad/apresentacao.py:189-206
CHAVES_RAIZ = ("titulo", "tema", "slides")
CHAVES_TEMA = ("nome", "cor", "logo")


def palavras(texto: str) -> int:
    """Palavras do texto; `<b>` e `</b>` não contam. origem: youtube-squad/apresentacao.py:100-101"""
    return len(re.sub(r"</?b>", "", texto).split())


def _luminancia(hex6: str) -> float:
    def canal(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex6[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def contraste(a: str, b: str) -> float:
    """Razão de contraste WCAG entre duas cores #RRGGBB. origem: youtube-squad/apresentacao.py:112-115"""
    la, lb = _luminancia(a), _luminancia(b)
    claro, escuro = max(la, lb), min(la, lb)
    return round((claro + 0.05) / (escuro + 0.05), 2)


def _achado(campo: str, detalhe: str) -> dict[str, str]:
    return {"campo": campo, "detalhe": detalhe}


def _texto(achados: list, onde: str, valor: Any, limite: int, *, obrigatorio: bool = True, destaque: bool = False) -> None:
    # origem: youtube-squad/apresentacao.py:118-133
    if valor is None or valor == "":
        if obrigatorio:
            achados.append(_achado(onde, "texto obrigatório"))
        return
    if not isinstance(valor, str):
        achados.append(_achado(onde, "precisa ser texto"))
        return
    if TRAVESSAO in valor or MEIA_RISCA in valor:
        achados.append(_achado(onde, "sem travessão nem meia-risca"))
    if "\n" in valor:
        achados.append(_achado(onde, "sem quebra de linha"))
    if not destaque and "<b>" in valor:
        achados.append(_achado(onde, "<b> só no título do slide titulo e no texto da declaracao"))
    if palavras(valor) > limite:
        achados.append(_achado(onde, f"no máximo {limite} palavras (tem {palavras(valor)})"))


def _itens(achados: list, onde: str, itens: Any, minimo: int, maximo: int, campos: dict[str, int]) -> None:
    if not isinstance(itens, list) or not minimo <= len(itens) <= maximo:
        achados.append(_achado(onde, f"de {minimo} a {maximo} itens"))
        return
    for j, item in enumerate(itens):
        if not isinstance(item, dict):
            achados.append(_achado(f"{onde}[{j}]", "precisa ser objeto"))
            continue
        for campo, limite in campos.items():
            _texto(achados, f"{onde}[{j}].{campo}", item.get(campo), limite)


def _imagem(achados: list, onde: str, valor: Any) -> None:
    if valor is None:
        return
    if not isinstance(valor, str) or not ARQUIVO_DE_ATIVO.fullmatch(valor):
        achados.append(_achado(onde, "imagem é o nome de um arquivo dentro de ativos/ (png, jpg, webp ou svg), sem barra"))


def validar_slide(i: int, s: Any) -> list[dict[str, str]]:
    """Achados de um slide (índice 0-based `i`). origem: youtube-squad/apresentacao.py:136-212"""
    achados: list[dict[str, str]] = []
    onde = f"slides[{i}]"
    tipo = s.get("tipo") if isinstance(s, dict) else None
    if tipo not in TIPOS:
        achados.append(_achado(f"{onde}.tipo", f"tipo inválido {tipo!r}; tipos aceitos: {', '.join(TIPOS)}"))
        return achados
    for campo, limite in TIPOS[tipo].items():
        _texto(achados, f"{onde}.{campo}", s.get(campo), limite,
               obrigatorio=(tipo, campo) not in OPCIONAIS, destaque=(tipo, campo) in COM_DESTAQUE)
    if tipo in ITENS:
        chave, minimo, maximo, campos = ITENS[tipo]
        _itens(achados, f"{onde}.{chave}", s.get(chave), minimo, maximo, campos)
    elif tipo == "fluxo":
        minimo, maximo, teto_titulo, teto_texto = FLUXO_NOS
        nos = s.get("nos")
        if not isinstance(nos, list) or not minimo <= len(nos) <= maximo:
            achados.append(_achado(f"{onde}.nos", f"de {minimo} a {maximo} nós"))
        else:
            for j, no in enumerate(nos):
                if not isinstance(no, dict):
                    achados.append(_achado(f"{onde}.nos[{j}]", "precisa ser objeto com titulo e texto"))
                    continue
                _texto(achados, f"{onde}.nos[{j}].titulo", no.get("titulo"), teto_titulo)
                _texto(achados, f"{onde}.nos[{j}].texto", no.get("texto"), teto_texto, obrigatorio=False)
    elif tipo == "comparacao":
        minimo, maximo, teto_titulo, teto_item = COMPARACAO
        for lado in ("esquerda", "direita"):
            col = s.get(lado)
            if not isinstance(col, dict):
                achados.append(_achado(f"{onde}.{lado}", "precisa ser objeto com titulo e itens"))
                continue
            _texto(achados, f"{onde}.{lado}.titulo", col.get("titulo"), teto_titulo)
            itens = col.get("itens")
            if not isinstance(itens, list) or not minimo <= len(itens) <= maximo:
                achados.append(_achado(f"{onde}.{lado}.itens", f"de {minimo} a {maximo} itens"))
            else:
                for j, item in enumerate(itens):
                    _texto(achados, f"{onde}.{lado}.itens[{j}]", item, teto_item)
    elif tipo == "estatisticas":
        minimo, maximo, teto_rotulo = ESTATISTICAS
        numeros = s.get("numeros")
        if not isinstance(numeros, list) or not minimo <= len(numeros) <= maximo:
            achados.append(_achado(f"{onde}.numeros", f"de {minimo} a {maximo} números"))
        else:
            for j, n in enumerate(numeros):
                valor = n.get("valor") if isinstance(n, dict) else None
                if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                    achados.append(_achado(f"{onde}.numeros[{j}].valor", "precisa ser número"))
                    continue
                _texto(achados, f"{onde}.numeros[{j}].rotulo", n.get("rotulo"), teto_rotulo)
                if not isinstance(n.get("sufixo", ""), str):
                    achados.append(_achado(f"{onde}.numeros[{j}].sufixo", "precisa ser texto"))
                if not isinstance(n.get("fonte"), str) or not n["fonte"].strip():
                    achados.append(_achado(f"{onde}.numeros[{j}].fonte",
                                           "número só entra com fonte externa do tema (site, documento, nota com endereço)"))
    elif tipo == "screenshot":
        _imagem(achados, f"{onde}.imagem", s.get("imagem"))
    elif tipo == "cta":
        _imagem(achados, f"{onde}.imagem", s.get("imagem"))
        url = s.get("url")
        if url is not None and (not isinstance(url, str) or not url.strip() or "\n" in url):
            achados.append(_achado(f"{onde}.url", "endereço em uma linha, ou null para usar o destino do CTA da Alma"))
    return achados


def _tema(achados: list, tema: Any, alma: Any) -> None:
    if tema is None:
        return
    if not isinstance(tema, dict):
        achados.append(_achado("tema", "objeto com nome, cor e logo, ou null"))
        return
    for chave in sorted(set(tema) - set(CHAVES_TEMA)):
        achados.append(_achado(f"tema.{chave}", f"chave desconhecida (válidas: {', '.join(CHAVES_TEMA)})"))
    if not isinstance(tema.get("nome"), str) or not tema["nome"].strip():
        achados.append(_achado("tema.nome", "texto obrigatório"))
    cor = tema.get("cor")
    if cor is not None:
        if not isinstance(cor, str) or not HEX.fullmatch(cor):
            achados.append(_achado("tema.cor", "cor no formato #RRGGBB, ou null para usar o destaque da Alma"))
        elif alma is not None:
            fundo = _cor_alma(alma, "fundo")
            if fundo is not None and contraste(cor, fundo) < CONTRASTE_MINIMO:
                achados.append(_achado("tema.cor", f"contraste {contraste(cor, fundo)}:1 sobre o fundo da Alma {fundo}; "
                                                   f"mínimo {CONTRASTE_MINIMO}:1"))
    _imagem(achados, "tema.logo", tema.get("logo"))


def _dados_alma(alma: Any) -> dict[str, Any]:
    return (alma.dados if hasattr(alma, "dados") else alma) or {}


def _cor_alma(alma: Any, papel: str) -> str | None:
    cor = ((_dados_alma(alma).get("visual") or {}).get("cores") or {}).get(papel)
    return cor if isinstance(cor, str) and HEX.fullmatch(cor) else None


def validar(d: Any, *, alma: Any = None, contar_slides: bool = True) -> list[dict[str, str]]:
    """Achados do deck (lista vazia = válido). Todos de uma vez, como na origem.

    `alma` liga a checagem de contraste da cor do tema sobre o `fundo` da Alma.
    `contar_slides=False` dispensa o número de slides e as pontas (título e CTA): serve para
    renderizar um trecho do deck (prévia), nunca para produzir a peça.
    origem: youtube-squad/apresentacao.py:215-253
    """
    if not isinstance(d, dict):
        return [_achado("deck", "o deck é um objeto JSON")]
    achados: list[dict[str, str]] = []
    for chave in sorted(set(d) - set(CHAVES_RAIZ)):
        achados.append(_achado(chave, f"chave desconhecida no deck (válidas: {', '.join(CHAVES_RAIZ)})"))
    if not isinstance(d.get("titulo"), str) or not d["titulo"].strip():
        achados.append(_achado("titulo", "texto obrigatório"))
    _tema(achados, d.get("tema"), alma)
    slides = d.get("slides")
    if not isinstance(slides, list) or not slides:
        achados.append(_achado("slides", f"de {SLIDES_MIN} a {SLIDES_MAX} slides (tem 0)"))
        return achados
    if contar_slides:
        if not SLIDES_MIN <= len(slides) <= SLIDES_MAX:
            achados.append(_achado("slides", f"de {SLIDES_MIN} a {SLIDES_MAX} slides (tem {len(slides)})"))
        if not isinstance(slides[0], dict) or slides[0].get("tipo") != "titulo":
            achados.append(_achado("slides[0]", "o primeiro slide é do tipo titulo"))
        if not isinstance(slides[-1], dict) or slides[-1].get("tipo") != "cta":
            achados.append(_achado(f"slides[{len(slides) - 1}]", "o último slide é do tipo cta"))
    for i, s in enumerate(slides):
        achados.extend(validar_slide(i, s))
    return achados


def completar_cta(d: dict[str, Any], alma: Any) -> tuple[dict[str, Any], list[str]]:
    """Cópia do deck com o CTA preenchido pela Alma onde o deck deixou vazio (o deck não muda).

    `titulo` vazio recebe `cta.padrao`; `url` vazia recebe `cta.destino`. Campo que nem o deck nem
    a Alma trazem fica `null`, com aviso: o núcleo não inventa CTA.
    """
    completo = _copy.deepcopy(d)
    cta_alma = _dados_alma(alma).get("cta") or {}
    avisos: list[str] = []
    for i, s in enumerate(completo.get("slides") or []):
        if not isinstance(s, dict) or s.get("tipo") != "cta":
            continue
        for campo, origem in (("titulo", "padrao"), ("url", "destino")):
            if isinstance(s.get(campo), str) and s[campo].strip():
                continue
            valor = cta_alma.get(origem)
            if isinstance(valor, str) and valor.strip():
                s[campo] = valor.strip()
            else:
                s[campo] = None
                avisos.append(f"slides[{i}].{campo}: vazio no deck e sem cta.{origem} na Alma; o slide sai sem ele")
        s.setdefault("texto", None)
        s.setdefault("imagem", None)
    return completo, avisos


def imagens(d: dict[str, Any]) -> list[tuple[str, str]]:
    """(campo, arquivo) de toda imagem citada pelo deck: logo do tema e imagens de slide."""
    saida: list[tuple[str, str]] = []
    tema = d.get("tema")
    if isinstance(tema, dict) and isinstance(tema.get("logo"), str):
        saida.append(("tema.logo", tema["logo"]))
    for i, s in enumerate(d.get("slides") or []):
        if isinstance(s, dict) and isinstance(s.get("imagem"), str):
            saida.append((f"slides[{i}].imagem", s["imagem"]))
    return saida


def de_origem(d: dict[str, Any]) -> dict[str, Any]:
    """Converte um `deck.json` do sistema de origem para o schema do núcleo.

    Descarta slug, pauta e metadados da fila (D-48); `marca` vira `tema` (a identidade da casa,
    `origem: expx`, vira `null`: a casa agora é a Alma); o `url` fixo do CTA vira `null` (vem da Alma).
    """
    marca = d.get("marca") if isinstance(d.get("marca"), dict) else None
    tema = None
    if marca is not None and marca.get("origem") != "expx":
        tema = {"nome": marca.get("nome"), "cor": marca.get("cor"), "logo": marca.get("logo")}
    slides = []
    for s in d.get("slides") or []:
        s = _copy.deepcopy(s)
        if isinstance(s, dict) and s.get("tipo") == "cta":
            s["url"] = None
        slides.append(s)
    return {"titulo": d.get("titulo"), "tema": tema, "slides": slides}
