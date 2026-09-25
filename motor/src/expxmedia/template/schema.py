"""Validação do `template.json` pelo JSON Schema do contrato (CONTRATO-template, M2, M7).

Mesmo formato de saída da Alma: rejeição (`ErroTemplateRejeitado`) para o que não dá para ler,
e lista de violações `{"tipo", "caminho", "mensagem"}` (`chave_omitida`, `tipo_invalido`,
`valor_invalido`) para o resto. Além do schema, confere a coerência que o JSON Schema não
expressa bem: formato aceito pelo tipo, motor aceito pelo tipo, e a versão do Remotion travada
quando o motor é Remotion.

Uso:

    from expxmedia.template import schema
    schema.validar(dados)   # [] quando o template.json cumpre o contrato
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from expxmedia.alma.schema import validar_contra_schema
from expxmedia.peca.modelo import TIPOS

__all__ = ["ErroTemplateRejeitado", "VERSAO", "MOTORES_POR_TIPO", "carregar_schema", "validar"]

VERSAO = 1
CAMINHO_SCHEMA = Path(__file__).with_name("template.schema.json")

# Tabela "Tipos e motores" do contrato.
MOTORES_POR_TIPO: dict[str, frozenset[str]] = {
    "post_unico": frozenset({"html"}),
    "carrossel": frozenset({"html", "html_remotion"}),
    "reel": frozenset({"remotion"}),
    "apresentacao": frozenset({"remotion", "html"}),
    "aula": frozenset({"remotion"}),
}
_MOTORES_COM_REMOTION = frozenset({"remotion", "html_remotion"})


class ErroTemplateRejeitado(ValueError):
    """O template.json não pode ser lido: não é objeto, sem versão, ou versão maior (M2)."""


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    return json.loads(CAMINHO_SCHEMA.read_text(encoding="utf-8"))


def carregar_schema() -> dict[str, Any]:
    return json.loads(json.dumps(_schema()))


def validar(dados: Any) -> list[dict[str, str]]:
    """Violações do `template.json` já lido. Levanta ErroTemplateRejeitado no que é rejeição."""
    if not isinstance(dados, dict):
        raise ErroTemplateRejeitado(f"template.json deve ser um objeto JSON, não {type(dados).__name__}")
    if "expxmedia_template" not in dados:
        raise ErroTemplateRejeitado("template.json sem a chave de versão expxmedia_template (M2)")
    versao = dados["expxmedia_template"]
    if not isinstance(versao, int) or isinstance(versao, bool) or versao < 1:
        raise ErroTemplateRejeitado(f"expxmedia_template inválida: {versao!r} (esperado inteiro, M2)")
    if versao > VERSAO:
        raise ErroTemplateRejeitado(
            f"template.json na versão {versao} do contrato; este motor só lê até a versão {VERSAO} (M2)"
        )
    violacoes = validar_contra_schema(_schema(), dados)
    ja = {v["caminho"] for v in violacoes}

    def anotar(caminho: str, mensagem: str) -> None:
        if caminho not in ja:
            violacoes.append({"tipo": "valor_invalido", "caminho": caminho, "mensagem": mensagem})

    tipo, formato, motor = dados.get("tipo"), dados.get("formato"), dados.get("motor")
    if tipo in TIPOS and isinstance(formato, str) and formato not in TIPOS[tipo]:
        anotar("formato", f"formato {formato} não é aceito por {tipo} (aceitos: {', '.join(TIPOS[tipo])})")
    if tipo in MOTORES_POR_TIPO and isinstance(motor, str) and motor not in MOTORES_POR_TIPO[tipo]:
        anotar("motor", f"motor {motor} não serve a {tipo} (aceitos: {', '.join(sorted(MOTORES_POR_TIPO[tipo]))})")
    versoes = dados.get("versoes")
    if motor in _MOTORES_COM_REMOTION and isinstance(versoes, dict) and "remotion" in versoes:
        if not isinstance(versoes["remotion"], str) or not versoes["remotion"].strip():
            anotar("versoes.remotion", "motor com Remotion trava a versão do Remotion em versoes.remotion")
    violacoes.sort(key=lambda v: (v["caminho"], v["tipo"]))
    return violacoes
