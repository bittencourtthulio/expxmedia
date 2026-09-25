"""Revisão mecânica de copy: os bloqueantes que dá para conferir sem modelo (D-45).

Portados da revisão editorial de origem (bloqueantes 1, 2, 12 e 13 e o item 10 da voz), com o
que era marca trocado por dado da Alma (M13):

| tipo                | bloqueia quando                                                     | parâmetro da Alma        |
|---------------------|---------------------------------------------------------------------|--------------------------|
| `travessao`         | há "—" ou "–" e alguma regra da voz proíbe travessão                | `voz.regras`             |
| `tratamento`        | o texto trata o leitor diferente do tratamento da empresa           | `voz.tratamento`         |
| `palavra_proibida`  | aparece um termo da lista de proibidos                              | `voz.palavras_proibidas` |
| `palavra_cta`       | a palavra do "comente PALAVRA" difere da palavra da publicação      | (peça ou argumento)      |
| `abertura_repetida` | a primeira frase repete a abertura de peça criada nos últimos 14 d  | (peças da instalação)    |

Cada ocorrência vira um bloqueante com a posição: `arquivo`, `linha` e `coluna` (a partir de 1) e
`indice` (a partir de 0, no texto do arquivo). O que não dá para conferir (Alma sem tratamento,
nenhuma palavra de publicação conhecida) vai em `nao_conferidos` com o motivo: o leitor não
preenche padrão em silêncio (M7).

"Mesma estrutura de abertura" é julgamento do revisor editorial; o mecânico aqui pega o caso que
já foi ao ar: a mesma primeira frase, ou as mesmas três primeiras palavras (o molde repetido).

Uso:

    from expxmedia.revisar import copy
    r = copy.revisar(raiz, {"legenda.txt": texto}, peca_id="P-20260924-A3F9")
    r["aprovado"], r["bloqueantes"]
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from expxmedia.alma import carregar as alma_carregar
from expxmedia.nucleo import arquivos, tempo
from expxmedia.peca import modelo

__all__ = ["revisar", "JANELA_ABERTURA_DIAS", "TIPOS", "ErroRevisao"]

# origem: Instagram-Carrosseis/editorial/revisao.md:26-27 e Instagram-Carrosseis/editorial/ganchos.md:38-40
JANELA_ABERTURA_DIAS = 14
# Palavras iniciais que definem o molde da abertura.
PALAVRAS_MOLDE = 3

TIPOS = ("travessao", "tratamento", "palavra_proibida", "palavra_cta", "abertura_repetida")

# origem: Instagram-Carrosseis/.claude/agents/revisor-editorial.md:26 (grep -n "—\|–")
TRAVESSOES = ("—", "–")
# origem: Instagram-Carrosseis/editorial/revisao.md:28 ("tu", "teu", "tua", "teus", "tuas", "contigo")
FORMAS_TU = ("tu", "teu", "tua", "teus", "tuas", "contigo")
FORMAS_VOCE = ("você", "voce", "vocês", "voces")
# Quem a Alma não quer ver no texto, por tratamento. `nos` fala em primeira pessoa do plural e não
# diz como trata o leitor: nada a conferir.
PROIBIDOS_POR_TRATAMENTO: dict[str, tuple[str, ...]] = {
    "voce": FORMAS_TU,
    "tu": FORMAS_VOCE,
    "impessoal": FORMAS_TU + FORMAS_VOCE,
}

# "Comente PALAVRA" / "Comenta PALAVRA": a palavra em caixa alta logo depois do verbo.
_RE_CTA = re.compile(r"(?<!\w)coment[ae](?!\w)\s+[\"'“‘]?(?P<palavra>[A-ZÀ-ÖØ-Þ0-9]{2,})(?!\w)", re.IGNORECASE)
_RE_FIM_FRASE = re.compile(r"[.!?…](?=\s|$)")


class ErroRevisao(ValueError):
    """Entrada da revisão inválida (peça inexistente, texto vazio)."""


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.casefold()) if unicodedata.category(c) != "Mn")


def _palavras(texto: str) -> list[str]:
    return re.findall(r"\w+", _sem_acento(texto))


def _termo(texto: str) -> re.Pattern[str]:
    partes = [re.escape(p) for p in texto.split()]
    return re.compile(r"(?<!\w)" + r"\s+".join(partes) + r"(?!\w)", re.IGNORECASE)


def _posicao(texto: str, indice: int) -> tuple[int, int]:
    linha = texto.count("\n", 0, indice) + 1
    coluna = indice - (texto.rfind("\n", 0, indice) + 1) + 1
    return linha, coluna


def _bloqueante(tipo: str, arquivo: str, texto: str, inicio: int, fim: int, mensagem: str, **extras: Any) -> dict[str, Any]:
    linha, coluna = _posicao(texto, inicio)
    return {"tipo": tipo, "mensagem": mensagem, "trecho": texto[inicio:fim], "arquivo": arquivo,
            "linha": linha, "coluna": coluna, "indice": inicio, **extras}


def _primeira_frase(texto: str) -> tuple[int, int] | None:
    """(início, fim) da primeira frase: da primeira linha com texto até o primeiro fim de frase."""
    m = re.search(r"\S", texto)
    if m is None:
        return None
    inicio = m.start()
    fim_linha = texto.find("\n", inicio)
    fim_linha = len(texto) if fim_linha < 0 else fim_linha
    ponto = _RE_FIM_FRASE.search(texto, inicio, fim_linha)
    fim = ponto.end() if ponto else fim_linha
    return inicio, len(texto[:fim].rstrip())


def _mesma_abertura(a: str, b: str) -> bool:
    pa, pb = _palavras(a), _palavras(b)
    if not pa or not pb:
        return False
    if pa == pb:
        return True
    return len(pa) >= PALAVRAS_MOLDE and len(pb) >= PALAVRAS_MOLDE and pa[:PALAVRAS_MOLDE] == pb[:PALAVRAS_MOLDE]


def _pecas(raiz: Path) -> list[dict[str, Any]]:
    pecas = []
    for caminho in sorted((raiz / "pecas").glob(f"*/*/{modelo.NOME_ARQUIVO}")):
        try:
            dados = arquivos.ler_json(caminho)
        except arquivos.ErroArquivo:
            continue
        if isinstance(dados, dict):
            pecas.append(dados)
    return pecas


def _momento(texto: Any) -> datetime | None:
    if not isinstance(texto, str):
        return None
    try:
        momento = datetime.fromisoformat(texto)
    except ValueError:
        return None
    return momento if momento.tzinfo is not None else None


def _palavras_publicacao(peca: dict[str, Any]) -> list[str]:
    palavras = []
    for pub in peca.get("publicacoes") or []:
        dm = pub.get("automacao_dm") if isinstance(pub, dict) else None
        palavra = dm.get("palavra") if isinstance(dm, dict) else None
        if isinstance(palavra, str) and palavra.strip() and palavra.strip() not in palavras:
            palavras.append(palavra.strip())
    return palavras


def revisar(
    raiz: Path | str,
    textos: dict[str, str] | str,
    *,
    peca_id: str | None = None,
    palavra_publicacao: str | None = None,
    serie: str | None = None,
    agora: datetime | None = None,
) -> dict[str, Any]:
    """Confere `textos` ({nome do arquivo: texto}, ou um texto só) contra a Alma e as peças da instalação.

    `peca_id`: a peça revisada (fica fora da comparação de abertura e dá a palavra da publicação).
    `palavra_publicacao`: a palavra do CTA da publicação, quando não vem da peça.
    `serie`: compara a abertura só com peças desta série.
    Devolve {"aprovado", "bloqueantes", "conferidos", "nao_conferidos", "alma_confirmada"}.
    """
    raiz = Path(raiz)
    if isinstance(textos, str):
        textos = {"texto": textos}
    if not textos or not any(t.strip() for t in textos.values()):
        raise ErroRevisao("nada para revisar: texto vazio")
    alma = alma_carregar.carregar(raiz)
    voz = alma.dados.get("voz") if isinstance(alma.dados.get("voz"), dict) else {}
    bloqueantes: list[dict[str, Any]] = []
    conferidos: list[str] = []
    nao_conferidos: list[dict[str, str]] = []
    ordem = {nome: i for i, nome in enumerate(textos)}

    # travessão
    regras = [r for r in voz.get("regras") or [] if isinstance(r, str)]
    regra_travessao = next((r for r in regras if "travess" in _sem_acento(r)), None)
    if regra_travessao is not None:
        conferidos.append("travessao")
        for nome, texto in textos.items():
            for i, caractere in enumerate(texto):
                if caractere in TRAVESSOES:
                    bloqueantes.append(_bloqueante("travessao", nome, texto, i, i + 1,
                                                   f"travessão proibido pela voz da Alma: {regra_travessao!r}"))
    else:
        nao_conferidos.append({"tipo": "travessao", "motivo": "nenhuma regra de voz.regras proíbe travessão"})

    # tratamento
    tratamento = voz.get("tratamento")
    proibidos = PROIBIDOS_POR_TRATAMENTO.get(tratamento) if isinstance(tratamento, str) else None
    if proibidos:
        conferidos.append("tratamento")
        padrao = re.compile(r"(?<!\w)(" + "|".join(re.escape(f) for f in proibidos) + r")(?!\w)", re.IGNORECASE)
        for nome, texto in textos.items():
            for m in padrao.finditer(texto):
                bloqueantes.append(_bloqueante("tratamento", nome, texto, m.start(), m.end(),
                                               f"{m.group(0)!r} foge do tratamento da Alma (voz.tratamento = {tratamento})"))
    else:
        motivo = ("voz.tratamento é null" if tratamento is None
                  else f"voz.tratamento = {tratamento!r} não define como tratar o leitor")
        nao_conferidos.append({"tipo": "tratamento", "motivo": motivo})

    # palavras proibidas
    termos = [t for t in voz.get("palavras_proibidas") or [] if isinstance(t, str) and t.strip()]
    conferidos.append("palavra_proibida")
    for termo in termos:
        padrao = _termo(termo)
        for nome, texto in textos.items():
            for m in padrao.finditer(texto):
                bloqueantes.append(_bloqueante("palavra_proibida", nome, texto, m.start(), m.end(),
                                               f"{termo!r} está em voz.palavras_proibidas da Alma"))

    # palavra do CTA contra a publicação
    peca = modelo.carregar(raiz, peca_id) if peca_id else None
    esperadas = [palavra_publicacao.strip()] if palavra_publicacao and palavra_publicacao.strip() else []
    if not esperadas and peca is not None:
        esperadas = _palavras_publicacao(peca)
    if esperadas:
        conferidos.append("palavra_cta")
        aceitas = {p.upper() for p in esperadas}
        for nome, texto in textos.items():
            for m in _RE_CTA.finditer(texto):
                palavra = m.group("palavra")
                if palavra != palavra.upper():
                    continue  # "comente abaixo": não é palavra-chave
                if palavra.upper() not in aceitas:
                    bloqueantes.append(_bloqueante(
                        "palavra_cta", nome, texto, m.start("palavra"), m.end("palavra"),
                        f"a palavra do CTA {palavra!r} difere da palavra da publicação ({', '.join(esperadas)})",
                    ))
    else:
        nao_conferidos.append({"tipo": "palavra_cta",
                               "motivo": "nenhuma palavra de publicação: informe a peça com automação de DM ou a palavra"})

    # abertura repetida em 14 dias
    conferidos.append("abertura_repetida")
    agora = agora or tempo.agora(raiz)
    limite = agora - timedelta(days=JANELA_ABERTURA_DIAS)
    primeiro = next(iter(textos))
    texto = textos[primeiro]
    frase = _primeira_frase(texto)
    if frase is not None:
        inicio, fim = frase
        abertura = texto[inicio:fim]
        for outra in _pecas(raiz):
            if outra.get("peca_id") == peca_id:
                continue
            if serie is not None and outra.get("serie") != serie:
                continue
            criada = _momento(outra.get("criada_em"))
            if criada is None or not (limite <= criada <= agora):
                continue
            conteudo = outra.get("conteudo") if isinstance(outra.get("conteudo"), dict) else {}
            gancho = conteudo.get("gancho")
            if isinstance(gancho, str) and _mesma_abertura(abertura, gancho):
                bloqueantes.append(_bloqueante(
                    "abertura_repetida", primeiro, texto, inicio, fim,
                    f"a primeira frase repete a abertura da peça {outra.get('peca_id')}, criada há menos de "
                    f"{JANELA_ABERTURA_DIAS} dias: {gancho!r}",
                    peca_id=outra.get("peca_id"), criada_em=outra.get("criada_em"),
                ))
                break

    bloqueantes.sort(key=lambda b: (ordem.get(b["arquivo"], 0), b["indice"], TIPOS.index(b["tipo"])))
    return {
        "aprovado": not bloqueantes,
        "bloqueantes": bloqueantes,
        "conferidos": conferidos,
        "nao_conferidos": nao_conferidos,
        "alma_confirmada": alma.confirmada,
    }
