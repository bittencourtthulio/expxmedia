"""Interface da capacidade `narrar`: texto do roteiro → mp3 + alinhamento por caractere (D-22, D-34).

    narrar(raiz, texto, porta_voz, tipo_peca, saida) -> dict

grava em `saida` (pasta relativa à raiz, M9) o `narracao.mp3` e o `alinhamento.json` no formato
compartilhado com a transcrição:

    {"characters": [...], "character_start_times_seconds": [...], "character_end_times_seconds": [...]}

**no espaço do texto do roteiro**, nunca no da fala: a legenda desenha os caracteres que estão
aqui (origem: Instragram-Videos/pipeline/tts.py:145-149).

O provedor sai de `ambiente.verificar` (quem escolhe é o `.env`, nunca o pack). Cada provedor é
um módulo com `PROVEDOR` e

    sintetizar(raiz, fala, voz, parametros, destino_mp3, *, tipo_peca, **opcoes) -> alinhamento da fala

que grava o mp3 **antes** de qualquer validação (o áudio já foi pago; origem:
Instragram-Videos/pipeline/tts.py:125-126). `voz` é o `porta_vozes[].voz` da Alma e `parametros`
o bloco do tipo de peça (`reel`, `aula` ou `padrao`, D-40), como está na Alma.

Ordem (origem: Instragram-Videos/pipeline/tts.py:108-149):

1. `pronuncia.aplicar`: o léxico do porta-voz vira a fala enviada ao provedor;
2. provedor sintetiza e grava o mp3;
3. `pronuncia.conferir_devolvido`: texto normalizado pela API → `alignment.raw.json` + erro;
4. `ritmo.aplicar`: só no reel, acelera até o piso e reescala o alinhamento;
5. `pronuncia.remapear`: alinhamento de volta ao texto do roteiro, gravado em `alinhamento.json`.

Uso:

    from expxmedia.narrar import base
    r = base.narrar(raiz, roteiro, "ana-souza", "reel", "pecas/2026-09/P-.../midia")
    r["audio"], r["arquivo_alinhamento"], r["alinhamento"], r["duracao_s"]
"""
from __future__ import annotations

import importlib
import subprocess
from pathlib import Path
from typing import Any

from expxmedia.ambiente.verificar import Verificador
from expxmedia.nucleo import arquivos
from expxmedia.nucleo import raiz as instalacao

__all__ = [
    "ErroNarrar",
    "CAPACIDADE",
    "ARQUIVO_AUDIO",
    "ARQUIVO_ALINHAMENTO",
    "ARQUIVO_ALINHAMENTO_BRUTO",
    "CHAVES_ALINHAMENTO",
    "PROVEDORES",
    "narrar",
    "contar_palavras",
    "validar_alinhamento",
    "bloco_parametros",
    "parametros_do_tipo",
    "porta_voz_da_alma",
    "duracao",
]

CAPACIDADE = "narrar"
ARQUIVO_AUDIO = "narracao.mp3"  # CONTRATO-peca: midia/narracao.mp3
ARQUIVO_ALINHAMENTO = "alinhamento.json"  # CONTRATO-peca: midia/alinhamento.json
ARQUIVO_ALINHAMENTO_BRUTO = "alignment.raw.json"  # origem: Instragram-Videos/pipeline/tts.py:133
CHAVES_ALINHAMENTO = ("characters", "character_start_times_seconds", "character_end_times_seconds")

# id do provedor (catálogo de capacidades) -> módulo que o implementa
PROVEDORES = {
    "elevenlabs": "expxmedia.narrar.elevenlabs",
    "teste": "expxmedia.narrar.teste",
}

# tipo de peça (CONTRATO-peca) -> bloco de `porta_vozes[].voz.parametros` (CONTRATO-alma, D-40)
_BLOCOS = {
    "reel": "reel",
    "aula": "aula",
    "post_unico": "padrao",
    "carrossel": "padrao",
    "apresentacao": "padrao",
}


class ErroNarrar(RuntimeError):
    """Falha da narração, com `codigo` estável. A mensagem nunca traz chave de provedor (M14)."""

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


def contar_palavras(texto: str) -> int:
    """Palavras do ROTEIRO, não da fala: o alias muda o som, não o conteúdo.

    origem: Instragram-Videos/pipeline/tts.py:102-103
    """
    return len(texto.split())


def validar_alinhamento(alinhamento: Any, texto: str | None = None) -> None:
    """Confere a forma do alinhamento e, com `texto`, que ele reconstrói o texto exato."""
    if not isinstance(alinhamento, dict) or any(c not in alinhamento for c in CHAVES_ALINHAMENTO):
        raise ErroNarrar("alinhamento_invalido", f"alinhamento sem as chaves {', '.join(CHAVES_ALINHAMENTO)}")
    chars, ini, fim = (alinhamento[c] for c in CHAVES_ALINHAMENTO)
    if not (isinstance(chars, list) and isinstance(ini, list) and isinstance(fim, list)):
        raise ErroNarrar("alinhamento_invalido", "as chaves do alinhamento precisam ser listas")
    if not len(chars) == len(ini) == len(fim):
        raise ErroNarrar(
            "alinhamento_invalido",
            f"listas do alinhamento com tamanhos diferentes ({len(chars)}, {len(ini)}, {len(fim)})",
        )
    if texto is not None and (len(chars) != len(texto) or "".join(chars) != texto):
        raise ErroNarrar("alinhamento_invalido", "o alinhamento não reconstrói o texto do roteiro")


def bloco_parametros(tipo_peca: str) -> str:
    """Qual bloco de parâmetros de voz vale para o tipo de peça: `reel`, `aula` ou `padrao` (D-40)."""
    try:
        return _BLOCOS[tipo_peca]
    except KeyError:
        raise ValueError(f"tipo de peça inválido: {tipo_peca!r} (válidos: {', '.join(_BLOCOS)})") from None


def parametros_do_tipo(voz: dict[str, Any] | None, tipo_peca: str) -> dict[str, Any]:
    """Cópia do bloco de parâmetros do tipo de peça como está na Alma; `{}` quando ausente.

    Completar o que falta com o padrão é do provedor (os padrões são dele, D-22).
    """
    bloco = bloco_parametros(tipo_peca)
    parametros = (voz or {}).get("parametros") if isinstance(voz, dict) else None
    valor = parametros.get(bloco) if isinstance(parametros, dict) else None
    return dict(valor) if isinstance(valor, dict) else {}


def porta_voz_da_alma(raiz: Path | str, porta_voz: str) -> dict[str, Any]:
    """O registro de `porta_vozes[]` com esse id, lido de `alma/alma.json`."""
    try:
        alma = arquivos.ler_json(Path(raiz) / "alma" / "alma.json")
    except arquivos.ErroArquivo as erro:
        raise ErroNarrar("alma_ilegivel", str(erro)) from None
    vozes = alma.get("porta_vozes") if isinstance(alma, dict) else None
    for registro in vozes or []:
        if isinstance(registro, dict) and registro.get("id") == porta_voz:
            return registro
    raise ErroNarrar("porta_voz_ausente", f"o porta-voz {porta_voz} não existe em alma/alma.json")


def duracao(mp3: Path | str) -> float:
    """Duração do arquivo em segundos (ffprobe)."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(mp3)],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise ErroNarrar("audio_invalido", f"ffprobe não leu a duração de {Path(mp3).name}") from None


def _modulo(provedor: str):
    try:
        return importlib.import_module(PROVEDORES[provedor])
    except KeyError:
        raise ErroNarrar("provedor_desconhecido", f"narrar não tem implementação para o provedor {provedor}") from None


def narrar(
    raiz: Path | str,
    texto: str,
    porta_voz: str,
    tipo_peca: str,
    saida: str | Path,
    **opcoes: Any,
) -> dict[str, Any]:
    """Narra `texto` na voz do porta-voz e grava `narracao.mp3` + `alinhamento.json` em `saida`.

    `opcoes` segue para o provedor (ex.: `url_base` da ElevenLabs, `palavras_por_segundo` do
    provedor de teste). Devolve `provedor`, `audio` e `arquivo_alinhamento` (relativos à raiz),
    `alinhamento`, `duracao_s` e `palavras`.
    """
    raiz = Path(raiz)
    bloco_parametros(tipo_peca)  # tipo inválido falha antes de gastar qualquer coisa
    texto = texto.strip()
    if not texto:
        raise ErroNarrar("texto_vazio", "não há texto para narrar")
    provedor = Verificador(raiz).escolher_provedor(CAPACIDADE, porta_voz)
    modulo = _modulo(provedor)
    registro = porta_voz_da_alma(raiz, porta_voz)
    voz = registro.get("voz") if isinstance(registro.get("voz"), dict) else {}
    parametros = parametros_do_tipo(voz, tipo_peca)

    pasta = raiz / instalacao.relativo(raiz, saida)
    pasta.mkdir(parents=True, exist_ok=True)
    mp3 = pasta / ARQUIVO_AUDIO

    from expxmedia.narrar import pronuncia, ritmo  # import tardio: os dois importam este módulo

    # Camada falada: o léxico do porta-voz vai na fala; o alinhamento volta ao roteiro.
    fala, segmentos = pronuncia.aplicar(texto, voz.get("pronuncia"))
    alinhamento_fala = modulo.sintetizar(raiz, fala, voz, parametros, mp3, tipo_peca=tipo_peca, **opcoes)
    validar_alinhamento(alinhamento_fala)
    pronuncia.conferir_devolvido(alinhamento_fala, fala, pasta)  # API normalizou: raw + erro, sem nova chamada

    # O ritmo do modelo varia entre chamadas: fixe o áudio ANTES de gravar o alinhamento, para que
    # ele descreva o mp3 final (só reel, D-40). origem: Instragram-Videos/pipeline/tts.py:141-149
    palavras = contar_palavras(texto)
    alinhamento_fala, info_ritmo = ritmo.aplicar(mp3, alinhamento_fala, palavras, tipo_peca, parametros)

    try:
        alinhamento = pronuncia.remapear(alinhamento_fala, texto, fala, segmentos)
    except ValueError as erro:
        raise ErroNarrar("remapeamento", str(erro)) from None
    validar_alinhamento(alinhamento, texto)

    destino = pasta / ARQUIVO_ALINHAMENTO
    arquivos.gravar_json(destino, alinhamento)
    return {
        "provedor": provedor,
        "audio": instalacao.relativo(raiz, mp3),
        "arquivo_alinhamento": instalacao.relativo(raiz, destino),
        "alinhamento": alinhamento,
        "duracao_s": duracao(mp3),
        "palavras": palavras,
        "termos_pronuncia": pronuncia.substituidos(texto, fala, segmentos),
        "fator_ritmo": info_ritmo["fator"],
        "aviso_ritmo": info_ritmo.get("aviso"),
    }
