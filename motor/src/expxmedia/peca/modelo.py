"""Modelo de peça: `pecas/<AAAA-MM>/<peca_id>-<slug>/peca.json` (CONTRATO-peca).

- Todas as chaves do contrato, sempre, na ordem dele (M7); ausente é `null`, lista vazia é `[]`.
- Gravação atômica sob trava (M15), reescrevendo `atualizado_em` (M10) no fuso da Alma (M5).
- O ciclo de vida é o do contrato; transição fora dele levanta ErroTransicao sem tocar no disco.
- Toda criação gera `peca_criada` e toda transição gera `peca_status` (`detalhe` = "a -> b") no
  rastro.
- `arquivos[].caminho` é relativo à pasta da peça, como no exemplo do contrato (M9).

Uso:

    from expxmedia.peca import modelo
    peca = modelo.criar(raiz, tipo="reel", titulo="...", formatos=["9:16"], pack="expx-instagram")
    modelo.registrar_arquivo(raiz, peca["peca_id"], "saida/final.mp4", papel="final", formato="9:16")
    modelo.registrar_producao(raiz, peca["peca_id"], capacidades=[...], provedores={...}, segundos=57.5)
    modelo.mudar_status(raiz, peca["peca_id"], "produzida")
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from expxmedia.nucleo import arquivos as _arquivos
from expxmedia.nucleo import ids, rastro, tempo
from expxmedia.nucleo.raiz import ErroCaminho, relativo

__all__ = [
    "ErroPeca",
    "ErroTransicao",
    "VERSAO",
    "TIPOS",
    "STATUS",
    "TRANSICOES",
    "criar",
    "carregar",
    "pasta",
    "mudar_status",
    "registrar_arquivo",
    "registrar_producao",
    "registrar_publicacao",
]

VERSAO = 1

# tipo -> formatos aceitos (tabela "Os tipos" do contrato)
TIPOS: dict[str, tuple[str, ...]] = {
    "post_unico": ("4:5", "1:1", "9:16"),
    "carrossel": ("4:5", "1:1"),
    "reel": ("9:16",),
    "apresentacao": ("16:9",),
    "aula": ("16:9", "9:16"),
}
STATUS: tuple[str, ...] = (
    "ideia", "roteiro", "produzida", "aprovada", "agendada", "publicada", "medida", "descartada",
)
STATUS_INICIAIS = ("ideia", "roteiro")
# Ciclo do contrato: ideia → roteiro → produzida → aprovada → agendada → publicada → medida;
# aprovada → publicada é a publicação imediata, sem agendamento; descartada de qualquer estado
# antes de publicada.
TRANSICOES: dict[str, frozenset[str]] = {
    "ideia": frozenset({"roteiro", "descartada"}),
    "roteiro": frozenset({"produzida", "descartada"}),
    "produzida": frozenset({"aprovada", "descartada"}),
    "aprovada": frozenset({"agendada", "publicada", "descartada"}),
    "agendada": frozenset({"publicada", "descartada"}),
    "publicada": frozenset({"medida"}),
    "medida": frozenset(),
    "descartada": frozenset(),
}
PAPEIS_ARQUIVO = frozenset(
    {"final", "slide", "legenda", "roteiro", "audio", "alinhamento", "srt", "avatar", "tela", "previa", "fonte"}
)
FORMATOS = frozenset({"4:5", "1:1", "9:16", "16:9"})
GANCHO_TIPOS = frozenset({"pergunta", "contraste", "numero", "lista", "historia", "processo", "polemica", "outro"})
CTA_FORMAS = frozenset({"comentario", "salvar", "compartilhar", "link", "seguir", "dm", "nenhum"})
CANAIS = frozenset({"instagram", "facebook", "youtube", "tiktok", "linkedin", "meta_ads"})
PROVEDORES_PUBLICACAO = frozenset({"expxflow", "meta_graph", "youtube_api", "manual"})
ESTADOS_PUBLICACAO = frozenset({"agendada", "publicada", "falhou", "cancelada"})
CHAVES_CONTEUDO = ("gancho", "gancho_tipo", "cta", "cta_forma", "legenda", "roteiro")
CHAVES_PUBLICACAO = (
    "canal", "provedor", "estado", "agendada_para", "publicada_em", "id_externo", "url", "automacao_dm", "erro",
)
NOME_ARQUIVO = "peca.json"


class ErroPeca(ValueError):
    """Peça fora do contrato, inexistente ou ilegível."""


class ErroTransicao(ErroPeca):
    """Mudança de status fora do ciclo de vida do contrato."""


# ---------------------------------------------------------------- criar e ler


def criar(
    raiz: Path | str,
    *,
    tipo: str,
    titulo: str,
    formatos: list[str],
    pack: str = "nucleo",
    slug: str | None = None,
    status: str = "ideia",
    serie: str | None = None,
    template: str | None = None,
    porta_voz: str | None = None,
    oferta: str | None = None,
    vaga: dict[str, str] | None = None,
    conteudo: dict[str, Any] | None = None,
    origem: str = "skill",
    agente: str | None = None,
) -> dict[str, Any]:
    """Cria a pasta e o `peca.json` da peça e registra `peca_criada`. Devolve o peca.json."""
    if tipo not in TIPOS:
        raise ErroPeca(f"tipo de peça inválido: {tipo!r} (válidos: {', '.join(TIPOS)})")
    if not isinstance(formatos, list) or not formatos:
        raise ErroPeca("formatos é uma lista com pelo menos um formato")
    fora = [f for f in formatos if f not in TIPOS[tipo]]
    if fora or len(set(formatos)) != len(formatos):
        raise ErroPeca(f"formatos {formatos!r} inválidos para {tipo} (aceitos: {', '.join(TIPOS[tipo])})")
    if status not in STATUS_INICIAIS:
        raise ErroPeca(f"uma peça nasce em {' ou '.join(STATUS_INICIAIS)}, não em {status!r}")
    if not isinstance(titulo, str) or not titulo.strip():
        raise ErroPeca("titulo vazio")
    parte = ids.slug(slug if slug is not None else titulo)
    if not parte:
        raise ErroPeca(f"o título não gera slug: {titulo!r}; informe slug")
    if vaga is not None and (not isinstance(vaga, dict) or set(vaga) != {"data", "id"}):
        raise ErroPeca("vaga é {\"data\": \"AAAA-MM-DD\", \"id\": \"vN\"} ou None")
    corpo_conteudo = _conteudo(conteudo)

    raiz = Path(raiz)
    agora = tempo.agora(raiz)
    peca_id = ids.novo_peca_id(agora, raiz=raiz)
    destino = raiz / "pecas" / agora.strftime("%Y-%m") / f"{peca_id}-{parte}"
    momento = tempo.iso(agora)
    peca: dict[str, Any] = {
        "expxmedia_peca": VERSAO,
        "peca_id": peca_id,
        "slug": parte,
        "titulo": titulo.strip(),
        "tipo": tipo,
        "formatos": list(formatos),
        "status": status,
        "pack": pack,
        "serie": serie,
        "template": template,
        "porta_voz": porta_voz,
        "oferta": oferta,
        "vaga": dict(vaga) if vaga is not None else None,
        "criada_em": momento,
        "atualizado_em": momento,
        "motivo_descarte": None,
        "conteudo": corpo_conteudo,
        "slides": [],
        "compoe": [],
        "arquivos": [],
        "producao": None,
        "publicacoes": [],
        "metricas": None,
    }
    # valida pack e origem antes de gravar: o rastro recusa o que o contrato não prevê
    _validar_evento(pack, origem)
    destino.mkdir(parents=True, exist_ok=False)
    caminho = destino / NOME_ARQUIVO
    _arquivos.gravar_json(caminho, peca)
    rastro.registrar(
        raiz, origem=origem, evento="peca_criada", resultado="ok", pack=pack, peca_id=peca_id, agente=agente,
        detalhe=f"{tipo} {', '.join(formatos)}: {peca['titulo']}", arquivos=[caminho],
    )
    return peca


def pasta(raiz: Path | str, peca_id: str) -> Path:
    """Pasta `pecas/<AAAA-MM>/<peca_id>-<slug>/` da peça."""
    if not ids.peca_id_valido(peca_id):
        raise ErroPeca(f"peca_id fora do formato P-AAAAMMDD-XXXX: {peca_id!r}")
    achadas = [p.parent for p in (Path(raiz) / "pecas").glob(f"*/{peca_id}-*/{NOME_ARQUIVO}")]
    if not achadas:
        raise ErroPeca(f"peça {peca_id} não encontrada em pecas/")
    if len(achadas) > 1:
        raise ErroPeca(f"peça {peca_id} em mais de uma pasta: {', '.join(sorted(p.name for p in achadas))}")
    return achadas[0]


def carregar(raiz: Path | str, peca_id: str) -> dict[str, Any]:
    """Conteúdo do `peca.json`. Rejeita versão ausente ou maior que a suportada (M2)."""
    caminho = pasta(raiz, peca_id) / NOME_ARQUIVO
    try:
        dados = _arquivos.ler_json(caminho)
    except _arquivos.ErroArquivo as erro:
        raise ErroPeca(str(erro)) from None
    if not isinstance(dados, dict) or "expxmedia_peca" not in dados:
        raise ErroPeca(f"{peca_id}: peca.json sem a chave de versão expxmedia_peca (M2)")
    versao = dados["expxmedia_peca"]
    if not isinstance(versao, int) or isinstance(versao, bool) or versao > VERSAO or versao < 1:
        raise ErroPeca(f"{peca_id}: peca.json na versão {versao!r}; este motor só lê até a versão {VERSAO} (M2)")
    return dados


# ---------------------------------------------------------------- status


def mudar_status(
    raiz: Path | str,
    peca_id: str,
    novo: str,
    *,
    motivo: str | None = None,
    origem: str = "skill",
    agente: str | None = None,
) -> dict[str, Any]:
    """Muda o `status` pelo ciclo do contrato, grava e registra `peca_status`.

    `descartada` exige `motivo` (vai para `motivo_descarte`). `produzida` exige `producao`
    registrada antes (registrar_producao). Transição inválida levanta ErroTransicao.
    """
    if novo not in STATUS:
        raise ErroTransicao(f"status desconhecido: {novo!r} (válidos: {', '.join(STATUS)})")
    if novo == "descartada" and (not isinstance(motivo, str) or not motivo.strip()):
        raise ErroPeca("descartar exige motivo (vai para motivo_descarte)")
    anterior: dict[str, str] = {}

    def aplicar(peca: dict[str, Any]) -> None:
        atual = peca["status"]
        if novo not in TRANSICOES.get(atual, frozenset()):
            permitidos = ", ".join(sorted(TRANSICOES.get(atual, ()))) or "nenhuma"
            raise ErroTransicao(f"transição inválida {atual} -> {novo} (a partir de {atual}: {permitidos})")
        if novo == "produzida" and peca.get("producao") is None:
            raise ErroPeca("produzida exige producao registrada antes (registrar_producao)")
        anterior["status"] = atual
        peca["status"] = novo
        if novo == "descartada":
            peca["motivo_descarte"] = motivo.strip()

    peca, caminho = _atualizar(raiz, peca_id, aplicar)
    rastro.registrar(
        raiz, origem=origem, evento="peca_status", resultado="ok", pack=peca["pack"], peca_id=peca_id,
        agente=agente, detalhe=f"{anterior['status']} -> {novo}", arquivos=[caminho],
    )
    return peca


# ---------------------------------------------------------------- registros


def registrar_arquivo(
    raiz: Path | str, peca_id: str, caminho: Path | str, *, papel: str, formato: str | None = None
) -> dict[str, Any]:
    """Acrescenta (ou atualiza, pelo caminho) uma entrada em `arquivos`.

    `caminho` é relativo à pasta da peça ou absoluto dentro dela; é gravado relativo (M9).
    """
    if papel not in PAPEIS_ARQUIVO:
        raise ErroPeca(f"papel de arquivo inválido: {papel!r} (válidos: {', '.join(sorted(PAPEIS_ARQUIVO))})")
    if formato is not None and formato not in FORMATOS:
        raise ErroPeca(f"formato inválido: {formato!r} (válidos: {', '.join(sorted(FORMATOS))} ou None)")
    base = pasta(raiz, peca_id)
    try:
        rel = relativo(base, caminho)
    except ErroCaminho:
        raise ErroPeca(f"arquivo fora da pasta da peça: {Path(caminho).name}") from None
    entrada = {"caminho": rel, "papel": papel, "formato": formato}

    def aplicar(peca: dict[str, Any]) -> None:
        lista = [a for a in peca["arquivos"] if a.get("caminho") != rel]
        posicao = next((i for i, a in enumerate(peca["arquivos"]) if a.get("caminho") == rel), len(lista))
        lista.insert(posicao, entrada)
        peca["arquivos"] = lista

    return _atualizar(raiz, peca_id, aplicar)[0]


def registrar_producao(
    raiz: Path | str,
    peca_id: str,
    *,
    capacidades: list[str],
    provedores: dict[str, str],
    segundos: float | int,
) -> dict[str, Any]:
    """Grava `producao` com as capacidades e provedores **efetivamente** usados e o tempo gasto."""
    if not isinstance(capacidades, list) or not all(isinstance(c, str) and c for c in capacidades):
        raise ErroPeca("capacidades é uma lista de nomes de capacidade")
    if not isinstance(provedores, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in provedores.items()):
        raise ErroPeca("provedores é um mapa capacidade -> provedor")
    if isinstance(segundos, bool) or not isinstance(segundos, (int, float)) or segundos < 0:
        raise ErroPeca("segundos é um número não negativo")
    momento = tempo.agora_iso(raiz)

    def aplicar(peca: dict[str, Any]) -> None:
        peca["producao"] = {
            "capacidades": list(capacidades),
            "provedores": dict(provedores),
            "segundos": segundos,
            "produzida_em": momento,
        }

    return _atualizar(raiz, peca_id, aplicar)[0]


def registrar_publicacao(raiz: Path | str, peca_id: str, publicacao: dict[str, Any]) -> dict[str, Any]:
    """Grava a publicação do canal (uma entrada por canal: substitui a do mesmo canal).

    `canal`, `provedor` e `estado` são obrigatórios; as demais chaves do contrato entram como
    `null` quando não vêm (M7). Não muda o `status` da peça: isso é mudar_status.
    """
    if not isinstance(publicacao, dict):
        raise ErroPeca("publicacao é um objeto")
    extras = sorted(set(publicacao) - set(CHAVES_PUBLICACAO))
    if extras:
        raise ErroPeca(f"chaves fora do contrato em publicacao: {', '.join(extras)}")
    for chave, validos in (("canal", CANAIS), ("provedor", PROVEDORES_PUBLICACAO), ("estado", ESTADOS_PUBLICACAO)):
        if publicacao.get(chave) not in validos:
            raise ErroPeca(f"publicacao.{chave} inválido: {publicacao.get(chave)!r} (válidos: {', '.join(sorted(validos))})")
    for chave in ("agendada_para", "publicada_em", "id_externo", "url", "erro"):
        valor = publicacao.get(chave)
        if valor is not None and not isinstance(valor, str):
            raise ErroPeca(f"publicacao.{chave} é texto ou None")
    dm = publicacao.get("automacao_dm")
    if dm is not None and (not isinstance(dm, dict) or set(dm) != {"palavra", "id_externo"}):
        raise ErroPeca("publicacao.automacao_dm é {\"palavra\", \"id_externo\"} ou None")
    entrada = {chave: publicacao.get(chave) for chave in CHAVES_PUBLICACAO}

    def aplicar(peca: dict[str, Any]) -> None:
        lista = peca["publicacoes"]
        for i, atual in enumerate(lista):
            if atual.get("canal") == entrada["canal"]:
                lista[i] = entrada
                return
        lista.append(entrada)

    return _atualizar(raiz, peca_id, aplicar)[0]


# ---------------------------------------------------------------- apoio


def _atualizar(raiz: Path | str, peca_id: str, aplicar) -> tuple[dict[str, Any], Path]:
    """Ler-modificar-gravar sob trava (M15), reescrevendo atualizado_em (M10)."""
    caminho = pasta(raiz, peca_id) / NOME_ARQUIVO
    with _arquivos.trava(caminho):
        peca = carregar(raiz, peca_id)
        aplicar(peca)
        peca["atualizado_em"] = tempo.agora_iso(raiz)
        _arquivos.gravar_json(caminho, peca)
    return peca, caminho


def _conteudo(conteudo: dict[str, Any] | None) -> dict[str, Any]:
    conteudo = dict(conteudo or {})
    extras = sorted(set(conteudo) - set(CHAVES_CONTEUDO))
    if extras:
        raise ErroPeca(f"chaves fora do contrato em conteudo: {', '.join(extras)}")
    saida = {chave: conteudo.get(chave) for chave in CHAVES_CONTEUDO}
    if saida["gancho_tipo"] is not None and saida["gancho_tipo"] not in GANCHO_TIPOS:
        raise ErroPeca(f"conteudo.gancho_tipo inválido: {saida['gancho_tipo']!r}")
    if saida["cta_forma"] is not None and saida["cta_forma"] not in CTA_FORMAS:
        raise ErroPeca(f"conteudo.cta_forma inválido: {saida['cta_forma']!r}")
    return saida


def _validar_evento(pack: str, origem: str) -> None:
    if origem not in rastro.ORIGENS:
        raise ErroPeca(f"origem inválida: {origem!r} (válidas: {', '.join(sorted(rastro.ORIGENS))})")
    if not isinstance(pack, str) or not rastro._PADRAO_PACK.fullmatch(pack):
        raise ErroPeca(f"pack inválido: {pack!r}")
