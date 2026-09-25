"""Validação do `alma/alma.json` pelo JSON Schema do contrato (CONTRATO-alma, M2, M7).

Duas saídas diferentes, de propósito (M7):

- **Rejeição** (`ErroAlmaRejeitada`): o que não dá para ler. Documento que não é objeto, chave de
  versão ausente, ou versão maior que a suportada (M2).
- **Violação**: o arquivo é lido e o defeito fica à vista. `validar` devolve uma lista de
  dicionários `{"tipo", "caminho", "mensagem"}`, com `tipo` em:
    `chave_omitida`  a chave obrigatória não está lá (ausente é `null`, e a chave fica);
    `tipo_invalido`  o valor tem o tipo JSON errado;
    `valor_invalido` enum, formato, faixa ou tamanho fora do contrato.
  `caminho` é o do campo: `visual.cores.destaque`, `porta_vozes[0].voz.parametros.reel.speed`.

`null` é valor válido para campo sem evidência (regra 3 do contrato); só a chave ausente é
violação. O leitor não preenche padrão em silêncio: os padrões de voz abaixo são o que o
`/expxmedia:alma` grava ao criar um porta-voz, não o que o leitor supõe quando falta.

Uso:

    from expxmedia.alma import schema
    violacoes = schema.validar(dados)   # [] quando a Alma cumpre o contrato
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

__all__ = [
    "ErroAlmaRejeitada",
    "VERSAO",
    "MODELO_VOZ_PADRAO",
    "PARAMETROS_VOZ_PADRAO",
    "carregar_schema",
    "validar",
    "validar_contra_schema",
]

VERSAO = 1
CAMINHO_SCHEMA = Path(__file__).with_name("alma.schema.json")

# Padrões dos parâmetros de voz do porta-voz, por tipo de peça (D-22, D-40). São os valores
# calibrados na origem para a voz clonada de lá; a Alma de outra empresa os recebe como ponto de
# partida e ajusta ao ouvido do dono da voz.
# origem: Instragram-Videos/pipeline/tts.py:16 e cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:35
MODELO_VOZ_PADRAO = "eleven_multilingual_v2"

PARAMETROS_VOZ_PADRAO: dict[str, dict[str, Any]] = {
    "reel": {
        # origem: Instragram-Videos/pipeline/tts.py:113-114 (voice_settings)
        "stability": 0.45,
        "similarity_boost": 0.8,
        "style": 0.25,
        "use_speaker_boost": True,
        # origem: Instragram-Videos/pipeline/lib.py:24 (SPEED_PADRAO = 1.2, teto da API)
        "speed": 1.2,
        # origem: Instragram-Videos/pipeline/lib.py:38 (RITMO_MIN = 3.18 * 1.2 / 1.1 ≈ 3,47 pal/s;
        # piso, nunca alvo)
        "ritmo_min_pps": 3.47,
    },
    "aula": {
        # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:37-41 (voice_settings)
        "stability": 0.5,
        "similarity_boost": 0.85,
        "style": 0.15,
        "use_speaker_boost": True,
        "speed": 0.94,
        # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:47 (urlopen timeout=300)
        "timeout_s": 300,
    },
    # Demais tipos (slide narrado de carrossel misto, apresentação em vídeo): a calibragem da
    # capacidade narrar da origem, sem o piso de ritmo, que é só do reel (D-40).
    "padrao": {
        # origem: Instragram-Videos/pipeline/tts.py:113-114 e Instragram-Videos/pipeline/lib.py:24
        "stability": 0.45,
        "similarity_boost": 0.8,
        "style": 0.25,
        "use_speaker_boost": True,
        "speed": 1.2,
    },
}


class ErroAlmaRejeitada(ValueError):
    """A Alma não pode ser lida: não é objeto, sem chave de versão, ou versão maior (M2)."""


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    return json.loads(CAMINHO_SCHEMA.read_text(encoding="utf-8"))


def carregar_schema() -> dict[str, Any]:
    """Cópia do JSON Schema publicado em `alma.schema.json`."""
    return json.loads(json.dumps(_schema()))


def validar(dados: Any) -> list[dict[str, str]]:
    """Violações da Alma `dados` (já lida do JSON). Levanta ErroAlmaRejeitada no que é rejeição."""
    if not isinstance(dados, dict):
        raise ErroAlmaRejeitada(f"alma.json deve ser um objeto JSON, não {type(dados).__name__}")
    if "expxmedia_alma" not in dados:
        raise ErroAlmaRejeitada("alma.json sem a chave de versão expxmedia_alma (M2)")
    versao = dados["expxmedia_alma"]
    if not isinstance(versao, int) or isinstance(versao, bool) or versao < 1:
        raise ErroAlmaRejeitada(f"expxmedia_alma inválida: {versao!r} (esperado inteiro, M2)")
    if versao > VERSAO:
        raise ErroAlmaRejeitada(
            f"alma.json na versão {versao} do contrato; este motor só lê até a versão {VERSAO} (M2)"
        )
    return validar_contra_schema(_schema(), dados)


def validar_contra_schema(schema: dict[str, Any], dados: Any) -> list[dict[str, str]]:
    """Violações de `dados` contra um JSON Schema, no formato {tipo, caminho, mensagem} (M7).

    Genérico: serve a qualquer contrato do ExpxMedia (Alma, template).
    """
    vistos: set[tuple[str, str]] = set()
    violacoes: list[dict[str, str]] = []

    def anotar(tipo: str, caminho: str, mensagem: str) -> None:
        if (tipo, caminho) in vistos:
            return
        vistos.add((tipo, caminho))
        violacoes.append({"tipo": tipo, "caminho": caminho, "mensagem": mensagem})

    for erro in Draft202012Validator(schema).iter_errors(dados):
        partes = list(erro.absolute_path)
        if erro.validator == "required":
            instancia = erro.instance if isinstance(erro.instance, dict) else {}
            for chave in erro.validator_value:
                if chave not in instancia:
                    caminho = _caminho([*partes, chave])
                    anotar("chave_omitida", caminho, f"chave obrigatória ausente: {caminho} (M7: ausente é null)")
        elif erro.validator == "type":
            anotar("tipo_invalido", _caminho(partes), f"{_caminho(partes) or 'documento'}: {erro.message}")
        else:
            anotar("valor_invalido", _caminho(partes), f"{_caminho(partes) or 'documento'}: {erro.message}")
    violacoes.sort(key=lambda v: (v["caminho"], v["tipo"]))
    return violacoes


def _caminho(partes: list[Any]) -> str:
    texto = ""
    for parte in partes:
        texto += f"[{parte}]" if isinstance(parte, int) else (f".{parte}" if texto else str(parte))
    return texto
