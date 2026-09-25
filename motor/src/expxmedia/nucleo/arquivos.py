"""Leitura e escrita de estado em disco (regra M15).

- JSON: grava num temporário **na mesma pasta** e troca por `os.replace`. Quem lê ao mesmo
  tempo (o painel, outro processo) vê o arquivo antigo ou o novo, nunca a metade.
- JSONL: só acréscimo, uma linha inteira por vez, sob trava de arquivo entre processos.
  Ninguém reescreve linha antiga. A leitura pula e conta linha corrompida, sem derrubar o resto.

A trava usa `filelock`, que funciona em POSIX e no Windows (o agendador local roda nos dois).
Ela vive num arquivo irmão `<nome>.lock` e é consultiva: protege contra quem também passa por
este módulo. Para ler-modificar-gravar um JSON sem perder a escrita de outro processo, use
`trava(caminho)` em volta das duas operações.

Uso:

    from expxmedia.nucleo import arquivos
    arquivos.gravar_json(raiz / "pecas/.../peca.json", dados)
    arquivos.acrescentar_jsonl(raiz / "eventos/2026-09.jsonl", {"ts": ...})
    eventos, corrompidas = arquivos.ler_jsonl(raiz / "eventos/2026-09.jsonl")
    with arquivos.trava(caminho):
        dados = arquivos.ler_json(caminho); ...; arquivos.gravar_json(caminho, dados)

Padrão de origem: youtube-squad/comum.py:21-77 (ler_json, gravar_json, anexar_jsonl,
ler_jsonl), trocando `fcntl.flock` (só POSIX) por `filelock`, e sem engolir JSON quebrado.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from filelock import FileLock

__all__ = ["ErroArquivo", "ler_json", "gravar_json", "acrescentar_jsonl", "ler_jsonl", "trava"]

_AUSENTE: Any = object()


class ErroArquivo(ValueError):
    """JSON ilegível, dado que não vira JSON, ou arquivo obrigatório ausente."""


def trava(caminho: Path | str, timeout: float = -1) -> FileLock:
    """Trava exclusiva entre processos associada a `caminho` (arquivo `<nome>.lock` ao lado).

    Use como gerenciador de contexto. `timeout` em segundos; -1 espera o quanto for preciso.
    A mesma trava é a que `acrescentar_jsonl` usa, então segurá-la suspende os acréscimos.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(caminho.with_name(caminho.name + ".lock")), timeout=timeout)


def ler_json(caminho: Path | str, padrao: Any = _AUSENTE) -> Any:
    """Conteúdo JSON de `caminho`. Tolera BOM na entrada (M16).

    Arquivo ausente devolve `padrao` quando ele é passado; sem `padrao`, levanta ErroArquivo.
    JSON inválido **sempre** levanta ErroArquivo: um `peca.json` quebrado não pode virar
    "vazio" em silêncio.
    """
    caminho = Path(caminho)
    try:
        texto = caminho.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        if padrao is not _AUSENTE:
            return padrao
        raise ErroArquivo(f"arquivo não encontrado: {caminho.name}") from None
    except UnicodeDecodeError:
        raise ErroArquivo(f"{caminho.name} não está em UTF-8") from None
    try:
        return json.loads(texto)
    except ValueError as erro:
        raise ErroArquivo(f"{caminho.name} não é JSON válido: {erro}") from None


def gravar_json(caminho: Path | str, dados: Any) -> None:
    """Grava `dados` em `caminho` de forma atômica (M15): UTF-8 sem BOM, indentação 2, `\\n` final.

    Serializa antes de tocar no disco: dado que não vira JSON (objeto qualquer, NaN, infinito)
    levanta ErroArquivo e o arquivo anterior fica intacto. Cria as pastas que faltarem.
    Não atualiza `atualizado_em` (M10): isso é de quem monta `dados`.
    """
    caminho = Path(caminho)
    texto = _serializar(dados, indent=2) + "\n"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(dir=caminho.parent, prefix=caminho.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporario, caminho)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise


def acrescentar_jsonl(caminho: Path | str, objeto: dict[str, Any]) -> None:
    """Acrescenta `objeto` como uma linha JSON no fim de `caminho`, sob trava entre processos.

    A linha é serializada antes de pegar a trava: objeto que não vira JSON levanta ErroArquivo
    sem tocar no arquivo. Quebras de linha dentro de textos saem escapadas (`\\n`), então uma
    chamada é sempre exatamente uma linha.
    """
    if not isinstance(objeto, dict):
        raise ErroArquivo(f"cada linha de JSONL é um objeto, não {type(objeto).__name__}")
    dados = (_serializar(objeto, indent=None) + "\n").encode("utf-8")
    caminho = Path(caminho)
    with trava(caminho):
        with open(caminho, "ab", buffering=0) as f:
            vista = memoryview(dados)
            while vista:
                escritos = f.write(vista)
                vista = vista[escritos:]
            os.fsync(f.fileno())


def ler_jsonl(caminho: Path | str) -> tuple[list[dict[str, Any]], int]:
    """(objetos, corrompidas) de um JSONL. Tolera BOM na entrada (M16).

    Linha em branco é ignorada; linha que não é JSON, ou não é objeto, é pulada e contada.
    Arquivo ausente devolve `([], 0)`.
    """
    try:
        bruto = Path(caminho).read_bytes()
    except FileNotFoundError:
        return [], 0
    objetos: list[dict[str, Any]] = []
    corrompidas = 0
    for linha in bruto.decode("utf-8-sig", errors="replace").splitlines():
        if not linha.strip():
            continue
        try:
            objeto = json.loads(linha)
        except ValueError:
            corrompidas += 1
            continue
        if isinstance(objeto, dict):
            objetos.append(objeto)
        else:
            corrompidas += 1
    return objetos, corrompidas


def _serializar(dados: Any, indent: int | None) -> str:
    try:
        return json.dumps(dados, ensure_ascii=False, indent=indent, allow_nan=False)
    except (TypeError, ValueError) as erro:
        raise ErroArquivo(f"dado não serializável em JSON: {erro}") from None
