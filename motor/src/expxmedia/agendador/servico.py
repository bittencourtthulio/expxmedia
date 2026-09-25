"""Serviço do agendador local: publica no horário o que foi agendado via `meta_graph` (D-08, D-30).

A Graph API não agenda. `agendar` por `meta_graph` só grava a publicação `agendada` na peça
(`publicar.meta_graph`); quem publica no horário é esta rodada, disparada a cada minuto pelo
sistema operacional (`agendador.instalar`: LaunchAgent, Agendador de Tarefas, systemd/cron).

Uma rodada:

1. pega a **trava de instância única** (`.expxmedia/agendador-rodada.lock`, `filelock`, sem
   esperar). Se outra rodada ainda está rodando (a Graph pode levar minutos processando um
   contêiner), esta sai sem fazer nada. A trava do sistema operacional some com o processo, então
   não existe trava velha a descartar (a origem, `Instagram-Carrosseis/rotina.sh:45-53`, usava
   `mkdir` e precisava expirar em 120 min);
2. varre `pecas/**/peca.json` atrás de publicações `estado: agendada` com `provedor: meta_graph`
   (peça descartada é ignorada; `peca.json` ilegível é listado e pulado, sem derrubar a rodada);
3. compara `agendada_para` com agora pelo **instante** (o fuso vem no texto, M5):
   - ainda não chegou: fica como está;
   - chegou há no máximo 15 minutos (`TOLERANCIA_ATRASO`, D-30): publica;
   - passou disso: **não publica atrasado em silêncio** (CONTRATO-capacidades). Marca `falhou`
     com erro começando por `atraso`, sem chamar o provedor, e a peça volta para a pessoa decidir.
     A regra vive aqui, e não no agendador do SO, porque `Persistent=` do systemd e o
     coalescimento do launchd disparam ao voltar de um período desligado
     (base/agendador-local-por-so.md, risco 1);
4. para publicar, segue a mesma disciplina de `publicar.base` (D-29): valida pelo adaptador,
   grava a **intenção** (`falhou` + `MARCA_INCERTO`) antes do envio, chama o adaptador **uma**
   vez com `agendada_para=None` (é o que faz o `MetaGraph` publicar de verdade) e grava o
   resultado. Erro de envio vira `falhou`, e o incerto leva a marca: na rodada seguinte a
   publicação já não está `agendada`, então nunca há reenvio automático;
5. registra no rastro, com `origem: rotina`, `publicacao_concluida` ou `publicacao_falhou`, e
   passa a peça de `agendada` para `publicada` quando publica.

O adaptador só é criado quando há algo a publicar: rodada sem nada devido não exige credencial.

Uso:

    from expxmedia.agendador import servico
    servico.rodar(raiz)                              # o que o sistema operacional chama
    servico.rodar(raiz, agora=momento, adaptador=f)  # testes: relógio e adaptador injetados
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from filelock import Timeout

from expxmedia.nucleo import arquivos, rastro, tempo
from expxmedia.nucleo.raiz import relativo
from expxmedia.peca import modelo
from expxmedia.publicar import base

__all__ = ["TOLERANCIA_ATRASO", "PROVEDOR", "ORIGEM", "rodar", "caminho_trava"]

TOLERANCIA_ATRASO = timedelta(minutes=15)  # D-30: publica até 15 min depois do horário, senão falhou
PROVEDOR = "meta_graph"
ORIGEM = "rotina"
CAPACIDADE = "agendar"


def caminho_trava(raiz: Path | str) -> Path:
    """Caminho associado à trava de instância única (o arquivo real é `<nome>.lock`)."""
    return Path(raiz) / ".expxmedia" / "agendador-rodada"


def rodar(
    raiz: Path | str,
    *,
    agora: datetime | None = None,
    adaptador: Any = None,
    fabricar: Callable[[Path], Any] | None = None,
) -> dict[str, Any]:
    """Uma rodada do agendador. Devolve o resumo do que fez (ver o docstring do módulo).

    `agora` (com fuso) controla o relógio; `adaptador` substitui o da instalação; `fabricar(raiz)`
    cria o adaptador quando há algo a publicar (padrão: `MetaGraph.da_instalacao`).
    """
    raiz = Path(raiz)
    if agora is not None and (agora.tzinfo is None or agora.utcoffset() is None):
        raise ValueError("agora sem fuso é ambíguo (M5); use um datetime com tzinfo")
    saida: dict[str, Any] = {"travado": False, "publicadas": [], "atrasadas": [], "falhas": [],
                             "pendentes": 0, "ilegiveis": []}
    try:
        with arquivos.trava(caminho_trava(raiz), timeout=0):
            momento = agora or tempo.agora(raiz)
            _rodada(raiz, momento, _Fonte(raiz, adaptador, fabricar), saida)
    except Timeout:
        saida["travado"] = True
    return saida


class _Fonte:
    """Cria o adaptador uma vez, só quando for preciso. Falha de criação vira o erro de cada envio."""

    def __init__(self, raiz: Path, adaptador: Any, fabricar: Callable[[Path], Any] | None) -> None:
        self._raiz = raiz
        self._adaptador = adaptador
        self._fabricar = fabricar or _fabricar_da_instalacao
        self._erro: base.ErroPublicacao | None = None

    def obter(self) -> Any:
        if self._adaptador is None and self._erro is None:
            try:
                self._adaptador = self._fabricar(self._raiz)
            except base.ErroPublicacao as erro:
                self._erro = erro
        if self._erro is not None:
            raise self._erro
        if getattr(self._adaptador, "provedor", None) != PROVEDOR:
            raise base.ErroPublicacao("provedor_sem_adaptador",
                                      f"o agendador local publica por {PROVEDOR}, não por "
                                      f"{getattr(self._adaptador, 'provedor', None)}")
        return self._adaptador


def _fabricar_da_instalacao(raiz: Path) -> Any:
    from expxmedia.ambiente import env as leitor_env
    from expxmedia.publicar import meta_graph

    return meta_graph.MetaGraph.da_instalacao(raiz, leitor_env.carregar(raiz))


def _rodada(raiz: Path, agora: datetime, fonte: _Fonte, saida: dict[str, Any]) -> None:
    for caminho in sorted((raiz / "pecas").glob("**/peca.json")):
        try:
            peca = arquivos.ler_json(caminho)
            peca_id = peca["peca_id"]
            peca = modelo.carregar(raiz, peca_id)
        except (arquivos.ErroArquivo, modelo.ErroPeca, KeyError, TypeError):
            saida["ilegiveis"].append(relativo(raiz, caminho))
            continue
        if peca["status"] == "descartada":
            continue
        for pub in list(peca["publicacoes"]):
            if pub.get("provedor") != PROVEDOR or pub.get("estado") != "agendada":
                continue
            _tratar(raiz, peca, pub, agora, fonte, saida)


def _tratar(raiz: Path, peca: dict[str, Any], pub: dict[str, Any], agora: datetime, fonte: _Fonte,
            saida: dict[str, Any]) -> None:
    peca_id, canal = peca["peca_id"], pub["canal"]
    item = {"peca_id": peca_id, "canal": canal}
    try:
        horario = datetime.fromisoformat(pub.get("agendada_para") or "")
        if horario.tzinfo is None or horario.utcoffset() is None:
            raise ValueError
    except (TypeError, ValueError):
        _falhar(raiz, peca, pub, f"agendada_para inválido ({pub.get('agendada_para')!r}): precisa de ISO 8601 "
                                 "com fuso (M5); nada foi publicado")
        saida["falhas"].append(item)
        return
    if agora < horario:
        saida["pendentes"] += 1
        return
    atraso = agora - horario
    if atraso > TOLERANCIA_ATRASO:
        minutos = int(atraso.total_seconds() // 60)
        _falhar(raiz, peca, pub, f"atraso: o horário {pub['agendada_para']} passou há {minutos} min (a tolerância "
                                 f"é de {int(TOLERANCIA_ATRASO.total_seconds() // 60)} min, D-30); nada foi "
                                 "publicado. A máquina estava desligada ou dormindo? Reagende a peça.")
        saida["atrasadas"].append(item)
        return
    if _publicar(raiz, peca, pub, fonte):
        saida["publicadas"].append(item)
    else:
        saida["falhas"].append(item)


def _publicar(raiz: Path, peca: dict[str, Any], pub: dict[str, Any], fonte: _Fonte) -> bool:
    peca_id, canal = peca["peca_id"], pub["canal"]
    try:
        adaptador = fonte.obter()
    except base.ErroPublicacao as erro:
        _falhar(raiz, peca, pub, f"{erro}; nada foi publicado")
        return False
    pedido = base.Pedido(
        raiz=raiz, peca=peca, pasta=modelo.pasta(raiz, peca_id), capacidade=CAPACIDADE, canais=[canal],
        agendada_para=None, dry_run=False, automacao=None,
        chave_idempotencia=f"{peca_id}-{canal}-{pub['agendada_para']}",
    )
    try:
        achados = list(adaptador.validar(pedido) or [])
    except base.ErroPublicacao as erro:
        achados = [{"codigo": erro.codigo, "mensagem": str(erro)}]
    if achados:
        texto = "; ".join(a.get("mensagem", a.get("codigo", "")) for a in achados)
        _falhar(raiz, peca, pub, f"a peça não cabe no provedor: {texto}; nada foi publicado")
        return False

    inicio = tempo.agora_iso(raiz)
    _gravar(raiz, peca_id, pub, estado="falhou",  # intenção antes do envio (D-29)
            erro=f"{base.MARCA_INCERTO}: envio do agendador iniciado em {inicio} e sem resposta registrada; "
                 "confira no provedor antes de enviar de novo")
    try:
        resultado = adaptador.enviar(pedido)
    except base.ErroEnvio as erro:
        texto = f"{base.MARCA_INCERTO}: {erro}" if erro.incerto else str(erro)
        _falhar(raiz, peca, pub, texto)
        return False
    except base.ErroPublicacao as erro:  # recusa antes do envio (ex.: mídia fora da peça)
        _falhar(raiz, peca, pub, str(erro))
        return False
    except Exception as erro:  # a intenção fica gravada como está: o resultado é desconhecido
        _evento(raiz, peca, "publicacao_falhou", "falha",
                f"{canal}: envio interrompido ({type(erro).__name__}); {base.MARCA_INCERTO}")
        return False

    rc = resultado.canais.get(canal)
    if rc is None or rc.estado != "publicada":
        motivo = rc.erro if rc is not None and rc.erro else f"o provedor não informou publicação de {canal}"
        _falhar(raiz, peca, pub, f"{base.MARCA_INCERTO}: {motivo}")
        return False
    _gravar(raiz, peca_id, pub, estado="publicada", publicada_em=rc.publicada_em or tempo.agora_iso(raiz),
            id_externo=rc.id_externo, url=rc.url, erro=rc.erro)
    atual = modelo.carregar(raiz, peca_id)["status"]
    if "publicada" in modelo.TRANSICOES.get(atual, frozenset()):
        modelo.mudar_status(raiz, peca_id, "publicada", origem=ORIGEM)
    _evento(raiz, peca, "publicacao_concluida", "aviso" if rc.erro else "ok",
            f"{canal}: publicada pelo agendador local (agendada para {pub['agendada_para']})")
    return True


def _falhar(raiz: Path, peca: dict[str, Any], pub: dict[str, Any], erro: str) -> None:
    _gravar(raiz, peca["peca_id"], pub, estado="falhou", erro=erro)
    _evento(raiz, peca, "publicacao_falhou", "falha", f"{pub['canal']}: falhou ({erro})")


def _gravar(raiz: Path, peca_id: str, pub: dict[str, Any], *, estado: str, erro: str | None = None,
            publicada_em: str | None = None, id_externo: str | None = None, url: str | None = None) -> None:
    modelo.registrar_publicacao(raiz, peca_id, {
        "canal": pub["canal"], "provedor": PROVEDOR, "estado": estado, "agendada_para": pub.get("agendada_para"),
        "publicada_em": publicada_em, "id_externo": id_externo, "url": url,
        "automacao_dm": pub.get("automacao_dm"), "erro": erro,
    })


def _evento(raiz: Path, peca: dict[str, Any], evento: str, resultado: str, detalhe: str) -> None:
    rastro.registrar(raiz, origem=ORIGEM, evento=evento, resultado=resultado, pack=peca["pack"],
                     peca_id=peca["peca_id"], capacidade=CAPACIDADE, provedor=PROVEDOR, detalhe=detalhe)
