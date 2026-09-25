"""Galeria local: busca de templates (CONTRATO-template, seção "A busca").

Duas fontes, nesta ordem de preferência:

- `galeria/templates/<template_id>/template.json` na raiz da instalação (galeria local);
- `templates/<tipo>/<template_id>/template.json` embarcados no repositório do núcleo
  (pasta configurável; padrão: `templates/` na raiz do repositório).

Mesmo `template_id` nas duas: vale o da galeria local.

A busca, na ordem do contrato:

1. filtra por `tipo` e `formato`;
2. descarta todo template com requisito não habilitado — o requisito efetivo é a união de
   `requisitos` do template e dos `kinds` que serão usados (todos os declarados, se a chamada não
   disser quais) — conferido por `ambiente.verificar`;
3. descarta `exige_porta_voz: true` se a Alma não tem porta-voz;
4. ordena por aderência a `serve_para` e depois a `estilos` do pedido; no empate, o
   desempenho local (critério injetável: as métricas de peça ainda não são coletadas pelo
   núcleo), depois a galeria local antes da embarcada, depois o `template_id`.

Também não entram: `template.json` ilegível ou fora do contrato, e `status` `reprovado` ou `fora`.
Os descartes voltam em `buscar_detalhado`, com o `como_habilitar` de cada capacidade faltante,
para a skill responder quando a pessoa pede explicitamente um template descartado.

Uso:

    from expxmedia.template import galeria_local
    galeria_local.buscar(raiz, tipo="reel", formato="9:16", serve_para=["conceito"])
    galeria_local.buscar_detalhado(raiz, tipo="carrossel", formato="4:5", kinds=["capa"])
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath
from typing import Any

from expxmedia.ambiente.catalogo import ErroCatalogo
from expxmedia.ambiente.verificar import Verificador
from expxmedia.nucleo import arquivos
from expxmedia.template import schema

__all__ = [
    "GALERIA_LOCAL",
    "STATUS_FORA_DA_BUSCA",
    "pasta_embarcados",
    "listar",
    "requisito_efetivo",
    "buscar",
    "buscar_detalhado",
]

GALERIA_LOCAL = PurePosixPath("galeria") / "templates"
STATUS_FORA_DA_BUSCA = frozenset({"reprovado", "fora"})
MANIFESTO = "template.json"

Desempenho = Callable[[str], float]


def pasta_embarcados() -> Path:
    """`templates/` na raiz do repositório do núcleo (irmã de `motor/`)."""
    return Path(__file__).resolve().parents[4] / "templates"


# ---------------------------------------------------------------- leitura


def _ler(caminho: Path) -> tuple[dict[str, Any] | None, str | None]:
    """(dados, None) se o template.json é legível e cumpre o contrato; (dados|None, motivo) se não."""
    try:
        dados = arquivos.ler_json(caminho)
        violacoes = schema.validar(dados)
    except (arquivos.ErroArquivo, schema.ErroTemplateRejeitado) as erro:
        return None, str(erro)
    if violacoes:
        primeira = violacoes[0]
        return dados, f"{len(violacoes)} violação(ões) do contrato; a primeira: {primeira['caminho']}: {primeira['mensagem']}"
    return dados, None


def listar(raiz: Path | str, embarcados: Path | str | None = None) -> list[dict[str, Any]]:
    """Todo template encontrado nas duas fontes, local antes de embarcado, sem repetir id.

    Cada item: `template_id`, `galeria` (`local`|`embarcada`), `caminho` (relativo: à raiz da
    instalação para a local; à pasta-mãe de `templates/` para a embarcada), `dados` (ou None) e
    `erro` (None quando o manifesto é válido).
    """
    raiz = Path(raiz)
    base_emb = Path(embarcados) if embarcados is not None else pasta_embarcados()
    itens: list[dict[str, Any]] = []
    vistos: set[str] = set()

    pasta_local = raiz / GALERIA_LOCAL
    locais = sorted(pasta_local.glob(f"*/{MANIFESTO}")) if pasta_local.is_dir() else []
    for manifesto in locais:
        rel = (GALERIA_LOCAL / manifesto.parent.name).as_posix()
        itens.append(_item(manifesto, "local", rel))
    emb = sorted(base_emb.glob(f"*/*/{MANIFESTO}")) if base_emb.is_dir() else []
    for manifesto in emb:
        rel = PurePosixPath(base_emb.name, manifesto.parent.parent.name, manifesto.parent.name).as_posix()
        itens.append(_item(manifesto, "embarcada", rel))

    unicos = []
    for item in itens:
        if item["template_id"] in vistos:
            continue
        vistos.add(item["template_id"])
        unicos.append(item)
    return unicos


def _item(manifesto: Path, galeria: str, caminho: str) -> dict[str, Any]:
    dados, erro = _ler(manifesto)
    template_id = manifesto.parent.name
    if isinstance(dados, dict) and isinstance(dados.get("template_id"), str):
        template_id = dados["template_id"]
    return {"template_id": template_id, "galeria": galeria, "caminho": caminho, "dados": dados, "erro": erro}


# ---------------------------------------------------------------- requisito efetivo


def requisito_efetivo(dados: dict[str, Any], kinds: Iterable[str] | None = None) -> list[str]:
    """União de `requisitos` do template e dos `kinds` usados, na ordem em que aparecem.

    `kinds` None: todos os kinds declarados (quem não diz quais vai usar pode usar qualquer um).
    Kind pedido que o template não tem é ignorado.
    """
    declarados = dados.get("kinds") if isinstance(dados.get("kinds"), dict) else {}
    usados = list(declarados) if kinds is None else [k for k in kinds if k in declarados]
    efetivo: list[str] = []
    for req in [*(dados.get("requisitos") or []), *(r for k in usados for r in declarados[k].get("requisitos") or [])]:
        if req not in efetivo:
            efetivo.append(req)
    return efetivo


# ---------------------------------------------------------------- busca


def _tem_porta_voz(raiz: Path) -> bool:
    try:
        alma = arquivos.ler_json(raiz / "alma" / "alma.json", padrao=None)
    except arquivos.ErroArquivo:
        return False
    vozes = alma.get("porta_vozes") if isinstance(alma, dict) else None
    return isinstance(vozes, list) and any(isinstance(p, dict) and p.get("id") for p in vozes)


def _contar(pedido: Iterable[str], do_template: Any) -> int:
    alvo = set(do_template) if isinstance(do_template, list) else set()
    return len(set(pedido) & alvo)


def buscar_detalhado(
    raiz: Path | str,
    *,
    tipo: str,
    formato: str,
    serve_para: Iterable[str] = (),
    estilos: Iterable[str] = (),
    kinds: Iterable[str] | None = None,
    porta_voz: str | None = None,
    embarcados: Path | str | None = None,
    verificador: Verificador | None = None,
    desempenho: Desempenho | None = None,
) -> dict[str, Any]:
    """`{"templates": [...], "descartados": [...]}` para `tipo` e `formato`.

    Template aceito: `template_id`, `titulo`, `tipo`, `formato`, `motor`, `galeria`, `caminho`,
    `requisitos` (efetivo), `exige_porta_voz`, `serve_para`, `estilos`, `aderencia`.
    Descartado: `template_id`, `galeria`, `caminho`, `motivo` (`invalido`, `status`,
    `requisito_nao_habilitado`, `sem_porta_voz`), `detalhe`, `requisitos`, `falta`,
    `como_habilitar` ({capacidade: texto}).
    Só entram em `descartados` os que já batem em tipo e formato (ou os ilegíveis).
    """
    raiz = Path(raiz)
    serve_para = list(serve_para)
    estilos = list(estilos)
    kinds = list(kinds) if kinds is not None else None
    verif = verificador or Verificador(raiz)
    tem_porta_voz = _tem_porta_voz(raiz)
    consultas: dict[str, dict[str, Any]] = {}

    def consulta(capacidade: str) -> dict[str, Any]:
        if capacidade not in consultas:
            try:
                consultas[capacidade] = verif.verificar(capacidade, porta_voz)
            except ErroCatalogo:
                consultas[capacidade] = {
                    "habilitada": False,
                    "como_habilitar": f"{capacidade} não é capacidade do núcleo nem de pack registrado.",
                }
        return consultas[capacidade]

    aceitos: list[tuple[tuple, dict[str, Any]]] = []
    descartados: list[dict[str, Any]] = []
    for ordem, item in enumerate(listar(raiz, embarcados)):
        dados = item["dados"]
        if item["erro"] is not None:
            if dados is None or (dados.get("tipo") == tipo and dados.get("formato") == formato):
                descartados.append(_descarte(item, "invalido", item["erro"], [], []))
            continue
        if dados["tipo"] != tipo or dados["formato"] != formato:
            continue
        requisitos = requisito_efetivo(dados, kinds)
        if dados["status"] in STATUS_FORA_DA_BUSCA:
            descartados.append(_descarte(item, "status", f"status {dados['status']}", requisitos, []))
            continue
        falta = [r for r in requisitos if not consulta(r)["habilitada"]]
        if falta:
            como = {r: consulta(r)["como_habilitar"] for r in falta}
            descartados.append(_descarte(
                item, "requisito_nao_habilitado", f"falta habilitar: {', '.join(falta)}", requisitos, falta, como,
            ))
            continue
        if dados["exige_porta_voz"] is True and not tem_porta_voz:
            descartados.append(_descarte(
                item, "sem_porta_voz", "o template exige porta-voz e a Alma não tem nenhum em porta_vozes",
                requisitos, [],
            ))
            continue
        aderencia = {"serve_para": _contar(serve_para, dados["serve_para"]),
                     "estilos": _contar(estilos, dados["estilos"])}
        nota = desempenho(item["template_id"]) if desempenho is not None else 0.0
        chave = (-aderencia["serve_para"], -aderencia["estilos"], -nota,
                 0 if item["galeria"] == "local" else 1, item["template_id"], ordem)
        aceitos.append((chave, {
            "template_id": item["template_id"],
            "titulo": dados["titulo"],
            "tipo": dados["tipo"],
            "formato": dados["formato"],
            "motor": dados["motor"],
            "galeria": item["galeria"],
            "caminho": item["caminho"],
            "requisitos": requisitos,
            "exige_porta_voz": dados["exige_porta_voz"],
            "serve_para": list(dados["serve_para"]),
            "estilos": list(dados["estilos"]),
            "aderencia": aderencia,
        }))
    aceitos.sort(key=lambda par: par[0])
    return {"templates": [t for _, t in aceitos], "descartados": descartados}


def buscar(raiz: Path | str, **kwargs: Any) -> list[dict[str, Any]]:
    """Só os templates aceitos de `buscar_detalhado`, já ordenados."""
    return buscar_detalhado(raiz, **kwargs)["templates"]


def _descarte(item: dict[str, Any], motivo: str, detalhe: str, requisitos: list[str], falta: list[str],
              como: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "template_id": item["template_id"],
        "galeria": item["galeria"],
        "caminho": item["caminho"],
        "motivo": motivo,
        "detalhe": detalhe,
        "requisitos": requisitos,
        "falta": falta,
        "como_habilitar": como or {},
    }
