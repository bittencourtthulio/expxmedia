"""Cues da aula: marcadores `[[nome]]` do roteiro -> `cues.json` a partir do alinhamento da narração.

Porta de `gerar_voz.py` das aulas, versão mais evoluída (idêntica de 06 a 09).
origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:22-28 e :58-67. A síntese em si é da
capacidade `narrar`; aqui fica só o que a origem fazia com o alinhamento devolvido.

- O roteiro traz `[[nome]]` antes do trecho (`nome` casa `\\w+`): `s1`, `s2`... para cenas e
  subcues como `s2_math` para eventos dentro de uma cena. Os marcadores saem do texto falado e
  cada um guarda o seu offset em caracteres no texto limpo.
- O cue é o início do **primeiro caractere não-espaço** a partir do offset: um marcador seguido de
  espaços ou quebra aponta para a próxima letra falada, senão a cena entra antes da palavra
  (base/aula-pipeline.md, risco 3). Marcador no fim do texto usa o último caractere.
- `duration` = fim do último caractere + 1,5 s; 3 casas decimais.

Formato gravado (as duas primeiras chaves são as que a composição lê, iguais às da origem):

    {"duration": 296.205, "cues": {"s1": 0.0, "s2": 45.616, ...},
     "narracao": "narracao.mp3", "narracao_sha256": "...", "desatualizados": [],
     "atualizado_em": "..."}

Dependência da narração (base/aula-pipeline.md, risco 4): cenas, legenda, avatar e tela leem os
mesmos segundos, e regerar a voz invalida todos. O `cues.json` grava o sha256 do mp3; quando ele
muda em relação ao `cues.json` anterior, todo dependente **existente** na pasta (`avatar.mp4`,
`legendas.json`, `*.srt`, `demo.mp4`, `demo.json`) entra em `desatualizados`. Sem `cues.json`
anterior não há como saber de que narração o dependente veio, e ele também entra. Quem regera um
dependente dá baixa com `marcar_atualizado`. Nada disso apaga arquivo.

Uso:

    from expxmedia.aula import cues
    texto = cues.texto_falado(roteiro)            # o que vai para narrar
    narrar.base.narrar(raiz, texto, porta_voz, "aula", "pecas/.../midia")
    cues.gerar(raiz, roteiro, "pecas/.../midia")  # grava midia/cues.json
    cues.desatualizados("pecas/.../midia")        # ['avatar.mp4', ...]
"""
from __future__ import annotations

import hashlib
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from expxmedia.nucleo import arquivos, tempo
from expxmedia.nucleo import raiz as instalacao

__all__ = [
    "ErroCues",
    "MARCADOR",
    "FOLGA_FINAL_S",
    "ARQUIVO_CUES",
    "DEPENDENTES",
    "separar",
    "texto_falado",
    "calcular",
    "hash_arquivo",
    "gerar",
    "ler",
    "desatualizados",
    "marcar_atualizado",
    "narracao_mudou",
]

MARCADOR = re.compile(r"\[\[(\w+)\]\]")  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:24
FOLGA_FINAL_S = 1.5  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:65
CASAS = 3  # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:64-65
ARQUIVO_CUES = "cues.json"
ARQUIVO_NARRACAO = "narracao.mp3"  # CONTRATO-peca: midia/narracao.mp3
ARQUIVO_ALINHAMENTO = "alinhamento.json"  # CONTRATO-peca: midia/alinhamento.json
# O que é produzido a partir da narração e dos cues (base/aula-pipeline.md, contrato de saída).
DEPENDENTES = ("avatar.mp4", "legendas.json", "*.srt", "demo.mp4", "demo.json")


class ErroCues(ValueError):
    """Roteiro ou alinhamento que não dá cue confiável, com `codigo` estável."""

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


def separar(roteiro: str) -> tuple[str, dict[str, int]]:
    """Texto falado (sem marcadores, sem espaço nas pontas) e o offset de cada marcador nele.

    origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:22-28. A narração do núcleo recebe o
    texto sem espaço nas pontas; os offsets descontam o que sobra no começo depois de tirar os
    marcadores (ex.: `[[s1]] Olá`).
    """
    bruto = roteiro.strip()
    limpo, offsets, pos = "", {}, 0
    for m in MARCADOR.finditer(bruto):
        limpo += bruto[pos : m.start()]
        if m.group(1) in offsets:
            # a origem sobrescrevia em silêncio e perdia a cena anterior
            raise ErroCues("marcador_repetido", f"o marcador [[{m.group(1)}]] aparece mais de uma vez no roteiro")
        offsets[m.group(1)] = len(limpo)
        pos = m.end()
    limpo += bruto[pos:]
    if not offsets:
        raise ErroCues("sem_marcador", "o roteiro não tem nenhum marcador [[nome]]")
    esquerda = len(limpo) - len(limpo.lstrip())
    texto = limpo.strip()
    return texto, {nome: min(max(0, off - esquerda), len(texto)) for nome, off in offsets.items()}


def texto_falado(roteiro: str) -> str:
    """O texto que vai para a narração: o roteiro sem os marcadores."""
    return separar(roteiro)[0]


def calcular(roteiro: str, alinhamento: dict[str, Any]) -> dict[str, Any]:
    """`{"duration", "cues"}` a partir do alinhamento por caractere do texto falado."""
    texto, offsets = separar(roteiro)
    try:
        chars = alinhamento["characters"]
        inicios = alinhamento["character_start_times_seconds"]
        fins = alinhamento["character_end_times_seconds"]
    except (KeyError, TypeError):
        raise ErroCues("alinhamento_invalido", "alinhamento sem characters e tempos por caractere") from None
    if "".join(chars) != texto or not len(chars) == len(inicios) == len(fins) or not chars:
        raise ErroCues(
            "alinhamento_divergente",
            "o alinhamento não é do texto falado deste roteiro; narre cues.texto_falado(roteiro)",
        )

    def tempo_em(indice: int) -> float:
        # origem: cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:58-61
        while indice < len(texto) and texto[indice].isspace():
            indice += 1
        return inicios[min(indice, len(inicios) - 1)]

    return {
        "duration": round(fins[-1] + FOLGA_FINAL_S, CASAS),
        "cues": {nome: round(tempo_em(i), CASAS) for nome, i in offsets.items()},
    }


def hash_arquivo(caminho: Path | str) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _dependentes_existentes(pasta: Path) -> set[str]:
    return {
        p.name for p in pasta.iterdir()
        if p.is_file() and any(fnmatch(p.name, padrao) for padrao in DEPENDENTES)
    }


def ler(pasta: Path | str) -> dict[str, Any] | None:
    """O `cues.json` da pasta, ou None quando não existe."""
    return arquivos.ler_json(Path(pasta) / ARQUIVO_CUES, padrao=None)


def gerar(
    raiz: Path | str,
    roteiro: str,
    pasta: Path | str,
    *,
    alinhamento: dict[str, Any] | None = None,
    narracao: str = ARQUIVO_NARRACAO,
) -> dict[str, Any]:
    """Calcula e grava `<pasta>/cues.json`; devolve o que foi gravado.

    `pasta` é a pasta de mídia (relativa à raiz ou absoluta dentro dela) com `narracao.mp3` e,
    quando `alinhamento` não é passado, `alinhamento.json` (as saídas de `narrar`).
    """
    raiz = Path(raiz)
    pasta = raiz / instalacao.relativo(raiz, pasta)
    mp3 = pasta / narracao
    if not mp3.is_file():
        raise ErroCues("sem_narracao", f"{narracao} não existe na pasta de mídia; narre antes de gerar os cues")
    if alinhamento is None:
        try:
            alinhamento = arquivos.ler_json(pasta / ARQUIVO_ALINHAMENTO)
        except arquivos.ErroArquivo as erro:
            raise ErroCues("sem_alinhamento", str(erro)) from None
    saida = calcular(roteiro, alinhamento)
    sha = hash_arquivo(mp3)

    anterior = ler(pasta)
    existentes = _dependentes_existentes(pasta)
    if isinstance(anterior, dict) and anterior.get("narracao_sha256") == sha:
        # mesma narração: só continua desatualizado o que já estava (e ainda existe)
        marcados = set(anterior.get("desatualizados") or []) & existentes
    else:
        # narração nova (ou de origem desconhecida): todo dependente existente foi feito de outra fala
        marcados = existentes

    saida.update({
        "narracao": narracao,
        "narracao_sha256": sha,
        "desatualizados": sorted(marcados),
        "atualizado_em": tempo.agora_iso(raiz),  # M10
    })
    arquivos.gravar_json(pasta / ARQUIVO_CUES, saida)
    return saida


def desatualizados(pasta: Path | str) -> list[str]:
    """Dependentes gerados de uma narração anterior que ainda existem na pasta."""
    pasta = Path(pasta)
    dados = ler(pasta)
    if not isinstance(dados, dict):
        return []
    return sorted(set(dados.get("desatualizados") or []) & _dependentes_existentes(pasta))


def marcar_atualizado(raiz: Path | str, pasta: Path | str, nome: str) -> list[str]:
    """Dá baixa em `nome` (regerado a partir da narração atual); devolve a lista que sobrou."""
    raiz = Path(raiz)
    pasta = raiz / instalacao.relativo(raiz, pasta)
    if not any(fnmatch(nome, padrao) for padrao in DEPENDENTES):
        raise ErroCues("nao_dependente", f"{nome} não é dependente da narração ({', '.join(DEPENDENTES)})")
    dados = ler(pasta)
    if not isinstance(dados, dict):
        raise ErroCues("sem_cues", f"{ARQUIVO_CUES} não existe na pasta de mídia")
    restantes = sorted((set(dados.get("desatualizados") or []) - {nome}) & _dependentes_existentes(pasta))
    dados["desatualizados"] = restantes
    dados["atualizado_em"] = tempo.agora_iso(raiz)  # M10
    arquivos.gravar_json(pasta / ARQUIVO_CUES, dados)
    return restantes


def narracao_mudou(pasta: Path | str) -> bool:
    """True quando o mp3 atual não é o que gerou o `cues.json` (ou não há `cues.json`)."""
    pasta = Path(pasta)
    dados = ler(pasta)
    if not isinstance(dados, dict):
        return True
    mp3 = pasta / (dados.get("narracao") or ARQUIVO_NARRACAO)
    return not mp3.is_file() or hash_arquivo(mp3) != dados.get("narracao_sha256")
