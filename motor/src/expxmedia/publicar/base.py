"""Base da publicação: provedor pela verificação, intenção antes do envio, idempotência (D-07, D-29).

Toda publicação (capacidades `publicar` e `agendar`) passa por `publicar()`, que:

1. escolhe o provedor por `ambiente.verificar` (regras 1 a 3 do CONTRATO-capacidades). Um
   `PROVEDOR_*` apontando para provedor não satisfeito é erro com orientação: **nunca** troca
   para o outro em silêncio (D-07). Adaptador de outro provedor também é recusado;
2. confere a peça (aprovada, agendada ou publicada; dry-run aceita produzida) e o horário
   (ISO 8601 com fuso, M5);
3. **idempotência**: se o mesmo canal já tem, para o mesmo horário, publicação `agendada`,
   `publicada` ou um envio de resultado desconhecido, recusa com `ErroDuplicada` sem chamar o
   provedor. Horário diferente com publicação viva no canal também é recusado (`canal_ocupado`):
   o contrato guarda uma publicação por canal, e sobrescrever perderia o id do agendamento;
4. pede ao adaptador os achados de validação (proporção, itens, legenda) antes de gravar nada;
5. grava a **intenção** na peça antes do envio: a entrada do canal fica `falhou` com o erro
   começando por `MARCA_INCERTO`. Se o processo cair durante o POST, é isso que fica, e a peça
   volta para a pessoa decidir (confere no provedor e reenvia com `forcar=True`);
6. chama o adaptador **uma vez**. POST nunca é retentado (D-29): `post_json`/`post_multipart`
   fazem exatamente uma requisição. 5xx, timeout e queda de conexão depois do envio viram
   `ErroEnvio(incerto=True)`, porque o provedor pode ter criado o post;
7. grava o resultado de cada canal na peça, muda o `status` (agendada/publicada) e registra no
   rastro `publicacao_agendada`, `publicacao_concluida` ou `publicacao_falhou`.

O retorno (dry-run e envio) traz `avisos`: lista com o aviso de `Verificador.aviso()` quando mais
de um provedor está satisfeito e `PROVEDOR_<CAPACIDADE>` não está no `.env` (regra 2); vazia senão.

Dry-run valida e monta o envio pelo adaptador, sem gravar nada na peça nem no rastro.

Contrato do adaptador (duck typing): atributo `provedor` e os métodos
`validar(pedido) -> list[dict]` (achados `{"codigo", "mensagem"}`) e
`enviar(pedido) -> Resultado`. Falha de envio sai como `ErroEnvio`.

Uso:

    from expxmedia.publicar import base
    base.publicar(raiz, "P-20260924-A3F9", agendada_para="2026-09-25T12:00:00-03:00")
    base.publicar(raiz, peca_id, dry_run=True)   # só monta e valida
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from expxmedia.ambiente.verificar import ErroCapacidade, ErroProvedor, Verificador
from expxmedia.nucleo import rastro, tempo
from expxmedia.nucleo.raiz import ErroCaminho, relativo
from expxmedia.peca import modelo

__all__ = [
    "ErroPublicacao",
    "ErroDuplicada",
    "ErroValidacao",
    "ErroEnvio",
    "Pedido",
    "Resultado",
    "ResultadoCanal",
    "MARCA_INCERTO",
    "publicar",
    "post_json",
    "post_json_com_status",
    "post_multipart",
    "midias",
    "legenda",
    "separar_hashtags",
]

MARCA_INCERTO = "resultado desconhecido"
STATUS_PUBLICAVEIS = ("aprovada", "agendada", "publicada")
STATUS_DRY_RUN = ("produzida", *STATUS_PUBLICAVEIS)
TIMEOUT_POST = 180  # s; origem: Instagram-Carrosseis/publicar/publicar.py:296
CAUDA_ERRO = 800  # caracteres da resposta não-JSON; origem: Instragram-Videos/pipeline/expxflow.py:50
_EVENTO_POR_ESTADO = {
    "agendada": ("publicacao_agendada", "ok"),
    "publicada": ("publicacao_concluida", "ok"),
    "falhou": ("publicacao_falhou", "falha"),
}


class ErroPublicacao(RuntimeError):
    """Publicação recusada ou falha. `codigo` estável; a mensagem nunca traz segredo (M14)."""

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


class ErroDuplicada(ErroPublicacao):
    """O canal já tem envio para esse horário (ou um envio vivo); nada foi chamado."""


class ErroValidacao(ErroPublicacao):
    """A peça não cabe no provedor; `achados` lista o que falta. Nada foi chamado nem gravado."""

    def __init__(self, achados: list[dict[str, str]]) -> None:
        texto = "; ".join(a.get("mensagem", a.get("codigo", "")) for a in achados)
        super().__init__("validacao", f"a peça não cabe no provedor: {texto}")
        self.achados = achados


class ErroEnvio(ErroPublicacao):
    """O envio ao provedor falhou. `incerto`: o provedor pode ter criado o post mesmo assim."""

    def __init__(self, codigo: str, mensagem: str, *, status_http: int | None = None,
                 incerto: bool = False, corpo: Any = None) -> None:
        super().__init__(codigo, mensagem)
        self.status_http = status_http
        self.incerto = incerto
        self.corpo = corpo


@dataclass
class Pedido:
    """O que o adaptador recebe: a peça já carregada e o que publicar."""

    raiz: Path
    peca: dict[str, Any]
    pasta: Path
    capacidade: str
    canais: list[str]
    agendada_para: str | None
    dry_run: bool
    automacao: dict[str, Any] | None
    chave_idempotencia: str


@dataclass
class ResultadoCanal:
    estado: str  # agendada | publicada | falhou
    id_externo: str | None = None
    url: str | None = None
    publicada_em: str | None = None
    automacao_dm: dict[str, str] | None = None
    erro: str | None = None


@dataclass
class Resultado:
    canais: dict[str, ResultadoCanal] = field(default_factory=dict)
    payload: Any = None  # o que foi (ou seria, no dry-run) enviado, sem segredo
    detalhe: str | None = None


# ---------------------------------------------------------------- publicar


def publicar(
    raiz: Path | str,
    peca_id: str,
    *,
    canais: list[str] | tuple[str, ...] = ("instagram",),
    agendada_para: str | None = None,
    automacao: dict[str, Any] | None = None,
    dry_run: bool = False,
    forcar: bool = False,
    adaptador: Any = None,
    fabricas: Mapping[str, Callable[..., Any]] | None = None,
    verificador: Verificador | None = None,
    origem: str = "skill",
    agente: str | None = None,
) -> dict[str, Any]:
    """Publica (sem `agendada_para`) ou agenda a peça nos `canais`. Ver o docstring do módulo."""
    raiz = Path(raiz)
    canais = _canais(canais)
    horario = _horario(agendada_para)
    capacidade = "agendar" if agendada_para else "publicar"
    verificador = verificador or Verificador(raiz)
    provedor = _escolher(raiz, verificador, capacidade, peca_id, origem, agente)
    aviso = verificador.aviso(capacidade)  # escolha implícita entre vários satisfeitos (regra 2)
    avisos = [aviso] if aviso else []
    if automacao is not None:
        _escolher(raiz, verificador, "automacao_dm", peca_id, origem, agente)
        if provedor != "expxflow":
            raise ErroPublicacao("automacao_indisponivel",
                                 f"automação de DM só existe pelo expxflow; o provedor de {capacidade} é {provedor}")
    if adaptador is None:
        adaptador = _fabricar(provedor, raiz, verificador, fabricas)
    elif getattr(adaptador, "provedor", None) != provedor:
        raise ErroProvedor(
            f"{capacidade} está configurada para {provedor}, mas o adaptador recebido é "
            f"{getattr(adaptador, 'provedor', None)}. O sistema não troca de provedor sozinho."
        )

    peca = modelo.carregar(raiz, peca_id)
    permitidos = STATUS_DRY_RUN if dry_run else STATUS_PUBLICAVEIS
    if peca["status"] not in permitidos:
        raise ErroPublicacao("peca_nao_aprovada",
                             f"a peça {peca_id} está {peca['status']}; publicar exige {' ou '.join(permitidos)}")
    if not forcar:
        _conferir_idempotencia(peca, canais, horario)

    pedido = Pedido(
        raiz=raiz, peca=peca, pasta=modelo.pasta(raiz, peca_id), capacidade=capacidade, canais=canais,
        agendada_para=agendada_para, dry_run=dry_run, automacao=automacao,
        chave_idempotencia=f"{peca_id}-{'+'.join(canais)}-{_chave_horario(horario)}",
    )
    achados = list(adaptador.validar(pedido) or [])
    if achados:
        raise ErroValidacao(achados)

    if dry_run:
        resultado = adaptador.enviar(pedido)
        return {"peca_id": peca_id, "capacidade": capacidade, "provedor": provedor, "dry_run": True,
                "payload": resultado.payload, "canais": {}, "avisos": avisos}

    inicio = tempo.agora_iso(raiz)
    for canal in canais:  # intenção antes do envio (D-29)
        modelo.registrar_publicacao(raiz, peca_id, {
            "canal": canal, "provedor": provedor, "estado": "falhou", "agendada_para": agendada_para,
            "erro": f"{MARCA_INCERTO}: envio iniciado em {inicio} e sem resposta registrada; "
                    "confira no provedor antes de enviar de novo",
        })

    try:
        resultado = adaptador.enviar(pedido)
    except ErroEnvio as erro:
        texto = f"{MARCA_INCERTO}: {erro}" if erro.incerto else str(erro)
        for canal in canais:
            _gravar_canal(raiz, peca_id, canal, provedor, capacidade, agendada_para,
                          ResultadoCanal(estado="falhou", erro=texto), origem, agente)
        raise
    except Exception:
        # a intenção fica gravada como está: o resultado é desconhecido
        rastro.registrar(raiz, origem=origem, evento="publicacao_falhou", resultado="falha", pack=peca["pack"],
                         peca_id=peca_id, agente=agente, capacidade=capacidade, provedor=provedor,
                         detalhe=f"{', '.join(canais)}: envio interrompido; {MARCA_INCERTO}")
        raise

    saida: dict[str, Any] = {}
    for canal in canais:
        rc = resultado.canais.get(canal) or ResultadoCanal(
            estado="falhou", erro=f"{MARCA_INCERTO}: o provedor não informou o estado de {canal}")
        _gravar_canal(raiz, peca_id, canal, provedor, capacidade, agendada_para, rc, origem, agente)
        saida[canal] = {"estado": rc.estado, "id_externo": rc.id_externo, "url": rc.url, "erro": rc.erro}
    _mudar_status(raiz, peca_id, [c["estado"] for c in saida.values()], origem, agente)
    return {"peca_id": peca_id, "capacidade": capacidade, "provedor": provedor, "dry_run": False,
            "payload": resultado.payload, "canais": saida, "avisos": avisos}


def _escolher(raiz: Path, verificador: Verificador, capacidade: str, peca_id: str, origem: str,
              agente: str | None) -> str:
    try:
        return verificador.escolher_provedor(capacidade)
    except ErroCapacidade as erro:
        rastro.registrar(raiz, origem=origem, evento="capacidade_ausente", resultado="bloqueado",
                         peca_id=peca_id, agente=agente, capacidade=capacidade, detalhe=str(erro))
        raise


def _fabricar(provedor: str, raiz: Path, verificador: Verificador,
              fabricas: Mapping[str, Callable[..., Any]] | None) -> Any:
    if fabricas is None:
        from expxmedia.publicar import expxflow, meta_graph  # import tardio: os adaptadores importam a base

        fabricas = {"expxflow": expxflow.ExpxFlow.da_instalacao, "meta_graph": meta_graph.MetaGraph.da_instalacao}
    if provedor not in fabricas:
        raise ErroPublicacao("provedor_sem_adaptador", f"o núcleo não tem adaptador de publicação para {provedor}")
    return fabricas[provedor](raiz, verificador.env)


def _canais(canais: list[str] | tuple[str, ...]) -> list[str]:
    lista = list(canais)
    if not lista or len(set(lista)) != len(lista) or any(c not in modelo.CANAIS for c in lista):
        raise ErroPublicacao("canal_invalido", f"canais inválidos: {lista!r} (válidos: {', '.join(sorted(modelo.CANAIS))})")
    return lista


def _horario(texto: str | None) -> datetime | None:
    if texto is None:
        return None
    try:
        momento = datetime.fromisoformat(texto)
    except (TypeError, ValueError):
        raise ErroPublicacao("horario_invalido", f"agendada_para não é ISO 8601: {texto!r}") from None
    if momento.tzinfo is None or momento.utcoffset() is None:
        raise ErroPublicacao("horario_invalido", "agendada_para precisa de fuso (M5), ex.: 2026-09-25T12:00:00-03:00")
    return momento


def _chave_horario(momento: datetime | None) -> str:
    return momento.astimezone().strftime("%Y%m%dT%H%M%z") if momento else "agora"


def _mesmo_horario(texto: str | None, momento: datetime | None) -> bool:
    if texto is None or momento is None:
        return texto is None and momento is None
    try:
        return _horario(texto) == momento
    except ErroPublicacao:
        return False


def _viva(pub: dict[str, Any]) -> bool:
    """Publicação que existe (ou pode existir) no provedor."""
    if pub.get("estado") in ("agendada", "publicada"):
        return True
    erro = pub.get("erro") or ""
    return pub.get("estado") == "falhou" and (bool(pub.get("id_externo")) or erro.startswith(MARCA_INCERTO))


def _conferir_idempotencia(peca: dict[str, Any], canais: list[str], horario: datetime | None) -> None:
    for pub in peca["publicacoes"]:
        if pub.get("canal") not in canais or not _viva(pub):
            continue
        if _mesmo_horario(pub.get("agendada_para"), horario):
            raise ErroDuplicada(
                "ja_enviada",
                f"{pub['canal']} já tem envio para esse horário ({pub['estado']}, {pub['provedor']}). "
                "Nada foi enviado. Se o envio anterior falhou de verdade, confira no provedor e use forcar.",
            )
        raise ErroDuplicada(
            "canal_ocupado",
            f"{pub['canal']} já tem publicação {pub['estado']} para {pub.get('agendada_para') or 'agora'}; "
            "a peça guarda uma publicação por canal. Cancele a anterior no provedor e use forcar.",
        )


def _gravar_canal(raiz: Path, peca_id: str, canal: str, provedor: str, capacidade: str,
                  agendada_para: str | None, rc: ResultadoCanal, origem: str, agente: str | None) -> None:
    if rc.estado not in _EVENTO_POR_ESTADO:
        rc = ResultadoCanal(estado="falhou", id_externo=rc.id_externo,
                            erro=f"{MARCA_INCERTO}: estado {rc.estado!r} fora do contrato")
    publicada_em = rc.publicada_em or (tempo.agora_iso(raiz) if rc.estado == "publicada" else None)
    peca = modelo.registrar_publicacao(raiz, peca_id, {
        "canal": canal, "provedor": provedor, "estado": rc.estado, "agendada_para": agendada_para,
        "publicada_em": publicada_em, "id_externo": rc.id_externo, "url": rc.url,
        "automacao_dm": rc.automacao_dm, "erro": rc.erro,
    })
    evento, resultado = _EVENTO_POR_ESTADO[rc.estado]
    if rc.estado != "falhou" and rc.erro:
        resultado = "aviso"  # publicado, mas algo em volta falhou (ex.: automação de DM)
    detalhe = f"{canal}: {rc.estado}" + (f" ({rc.erro})" if rc.erro else "")
    rastro.registrar(raiz, origem=origem, evento=evento, resultado=resultado, pack=peca["pack"], peca_id=peca_id,
                     agente=agente, capacidade=capacidade, provedor=provedor, detalhe=detalhe)


def _mudar_status(raiz: Path, peca_id: str, estados: list[str], origem: str, agente: str | None) -> None:
    atual = modelo.carregar(raiz, peca_id)["status"]
    alvo = "publicada" if "publicada" in estados else "agendada" if "agendada" in estados else None
    if alvo and alvo != atual and alvo in modelo.TRANSICOES.get(atual, frozenset()):
        modelo.mudar_status(raiz, peca_id, alvo, origem=origem, agente=agente)


# ---------------------------------------------------------------- HTTP sem retentativa


def post_json(url: str, corpo: Any, *, cabecalhos: Mapping[str, str] | None = None,
              timeout: float = TIMEOUT_POST) -> Any:
    """Um POST JSON, **uma** tentativa (D-29). Devolve o corpo JSON de 2xx; senão ErroEnvio."""
    return _post(url, timeout, cabecalhos, json=corpo)[1]


def post_json_com_status(url: str, corpo: Any, *, cabecalhos: Mapping[str, str] | None = None,
                         timeout: float = TIMEOUT_POST) -> tuple[int, Any]:
    """Como `post_json`, devolvendo também o status 2xx (201 e 207 significam coisas diferentes)."""
    return _post(url, timeout, cabecalhos, json=corpo)


def post_multipart(url: str, arquivo: Path, tipo: str, *, cabecalhos: Mapping[str, str] | None = None,
                   timeout: float = TIMEOUT_POST) -> Any:
    """Upload multipart (campo `file`), uma tentativa. Devolve o corpo JSON de 2xx."""
    with Path(arquivo).open("rb") as fh:
        return _post(url, timeout, cabecalhos, files={"file": (Path(arquivo).name, fh, tipo)})[1]


def _post(url: str, timeout: float, cabecalhos: Mapping[str, str] | None, **kw: Any) -> tuple[int, Any]:
    try:
        resposta = requests.post(url, headers=dict(cabecalhos or {}), timeout=timeout, **kw)
    except requests.exceptions.ConnectTimeout:
        raise ErroEnvio("sem_conexao", "não foi possível conectar ao provedor (tempo esgotado)") from None
    except requests.ConnectionError as erro:
        # conexão nunca aberta: o provedor não recebeu nada. Caída depois de aberta: incerto.
        nunca = "NewConnectionError" in repr(erro) or "refused" in str(erro).lower()
        if nunca:
            raise ErroEnvio("sem_conexao", "não foi possível conectar ao provedor") from None
        raise ErroEnvio("sem_resposta", f"a conexão caiu sem resposta do provedor ({type(erro).__name__})",
                        incerto=True) from None
    except requests.Timeout:
        raise ErroEnvio("sem_resposta", f"o provedor não respondeu em {timeout:g} s", incerto=True) from None
    except requests.RequestException as erro:
        raise ErroEnvio("sem_resposta", f"falha no envio ({type(erro).__name__})", incerto=True) from None
    corpo = _corpo(resposta)
    if 200 <= resposta.status_code < 300:
        return resposta.status_code, corpo
    raise ErroEnvio(
        f"http_{resposta.status_code}",
        f"o provedor respondeu HTTP {resposta.status_code}: {_mensagem(corpo)}",
        status_http=resposta.status_code, incerto=resposta.status_code >= 500, corpo=corpo,
    )


def _corpo(resposta: requests.Response) -> Any:
    try:
        return resposta.json()
    except ValueError:
        return {"raw": resposta.text[:CAUDA_ERRO]}


def _mensagem(corpo: Any) -> str:
    if isinstance(corpo, dict):
        erro = corpo.get("error")
        if isinstance(erro, dict):  # formato da Graph API
            return str(erro.get("message") or erro)[:CAUDA_ERRO]
        if erro:
            detalhes = corpo.get("details")
            return (f"{erro} {detalhes}" if detalhes else str(erro))[:CAUDA_ERRO]
        if "raw" in corpo:
            return str(corpo["raw"])[:CAUDA_ERRO]
    return str(corpo)[:CAUDA_ERRO]


# ---------------------------------------------------------------- mídia e legenda da peça


def midias(pedido: Pedido) -> list[dict[str, Any]]:
    """Mídias a publicar, na ordem: `[{"caminho": Path, "midia": "imagem"|"video"}]`.

    Carrossel e post único vêm de `slides` (na ordem de `n`); reel, apresentação e aula, dos
    arquivos `papel: final`. Caminho fora da pasta da peça é recusado (M9).
    """
    peca = pedido.peca
    if peca["tipo"] in ("carrossel", "post_unico") and peca["slides"]:
        itens = [(s["arquivo"], s.get("midia") or "imagem") for s in sorted(peca["slides"], key=lambda s: s["n"])]
        if peca["tipo"] == "post_unico":
            itens = itens[:1]
    else:
        finais = [a for a in peca["arquivos"] if a.get("papel") == "final"]
        if peca["tipo"] == "post_unico" and not finais:
            finais = [a for a in peca["arquivos"] if a.get("papel") == "slide"][:1]
        itens = [(a["caminho"], _tipo_por_extensao(a["caminho"])) for a in finais[:1]]
    saida = []
    for caminho, midia in itens:
        try:
            rel = relativo(pedido.pasta, pedido.pasta / caminho)
        except ErroCaminho:
            raise ErroPublicacao("midia_fora_da_peca", f"mídia fora da pasta da peça: {caminho}") from None
        saida.append({"caminho": pedido.pasta / rel, "midia": midia})
    return saida


def _tipo_por_extensao(caminho: str) -> str:
    return "video" if Path(caminho).suffix.lower() in (".mp4", ".mov", ".m4v", ".webm") else "imagem"


def legenda(pedido: Pedido) -> str:
    """Texto da legenda: `conteudo.legenda` é caminho de arquivo na pasta da peça ou o próprio texto."""
    valor = (pedido.peca.get("conteudo") or {}).get("legenda")
    if not valor:
        return ""
    candidato = pedido.pasta / valor
    try:
        relativo(pedido.pasta, candidato)
        if candidato.is_file():
            return candidato.read_text(encoding="utf-8-sig").strip()
    except (ErroCaminho, OSError, ValueError):
        pass
    return str(valor).strip()


def separar_hashtags(texto: str) -> tuple[str, str]:
    """(legenda, hashtags): as linhas finais só de #tags viram o campo de hashtags.

    origem: Instagram-Carrosseis/publicar/publicar.py:155-160
    """
    linhas = texto.rstrip().split("\n")
    tags: list[str] = []
    while linhas and linhas[-1].strip() and all(t.startswith("#") for t in linhas[-1].split()):
        tags.insert(0, linhas.pop().strip())
    return "\n".join(linhas).rstrip(), " ".join(tags)


def contar_hashtags(texto: str) -> int:
    return len(re.findall(r"(?<!\w)#\w+", texto))
