"""Leitor do `.env` da raiz da instalação (regras M12 e M14).

O `.env` é a única fonte de segredo e de escolha de provedor. Este módulo lê o arquivo e
devolve um `Env`: um mapeamento somente leitura de nome para valor que **nunca** mostra valor
em `repr`, `str` ou mensagem de erro. Erro cita o nome da variável (ou o número da linha,
quando o nome não se sabe), nunca o conteúdo.

Formato aceito (o mesmo dos `.env` das origens, `Instagram-Carrosseis/telegram_bot.py:50-61`):

- linha vazia e linha iniciada por `#` são ignoradas; BOM no início é tolerado (M16);
- `NOME=valor`, com espaços em volta do nome e do valor descartados e `export ` opcional;
- valor entre aspas simples fica literal; entre aspas duplas aceita `\\n`, `\\t`, `\\"` e `\\\\`;
- valor sem aspas termina no primeiro ` #` (comentário de fim de linha);
- nome repetido: vale a última ocorrência.

Uso:

    from expxmedia.ambiente import env
    ambiente = env.carregar(raiz)
    ambiente.preenchida("ELEVENLABS_API_KEY")          # True/False, sem expor o valor
    chaves = ambiente.exigir("EXPXFLOW_API_KEY", "EXPXFLOW_CLIENT_ID")  # ErroEnv com os nomes que faltam
"""
from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from pathlib import Path

__all__ = ["ErroEnv", "Env", "interpretar", "ler_env", "carregar", "NOME_ARQUIVO"]

NOME_ARQUIVO = ".env"
_NOME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}


class ErroEnv(ValueError):
    """Problema no `.env` ou variável ausente/inválida. A mensagem nunca contém valor (M14)."""


class Env(Mapping[str, str]):
    """Variáveis lidas do `.env`. Mapeamento somente leitura que não mostra valores."""

    __slots__ = ("_valores",)

    def __init__(self, valores: Mapping[str, str] | None = None) -> None:
        self._valores: dict[str, str] = dict(valores or {})

    def __getitem__(self, nome: str) -> str:
        return self._valores[nome]

    def __iter__(self) -> Iterator[str]:
        return iter(self._valores)

    def __len__(self) -> int:
        return len(self._valores)

    def __repr__(self) -> str:
        nomes = ", ".join(f"{n}={'***' if v.strip() else ''}" for n, v in self._valores.items())
        return f"Env({nomes})"

    __str__ = __repr__

    def preenchida(self, nome: str) -> bool:
        """Se a variável existe e tem valor não vazio (espaços não contam)."""
        return bool(self._valores.get(nome, "").strip())

    def exigir(self, *nomes: str) -> dict[str, str]:
        """{nome: valor} das variáveis pedidas; ErroEnv citando **todas** as que faltam."""
        faltam = [n for n in nomes if not self.preenchida(n)]
        if faltam:
            raise ErroEnv(f"falta no .env: {', '.join(faltam)}")
        return {n: self._valores[n].strip() for n in nomes}

    def inteiro(self, nome: str) -> int:
        """Valor inteiro de `nome`; ErroEnv (sem o valor) se faltar ou não for inteiro."""
        texto = self.exigir(nome)[nome]
        try:
            return int(texto)
        except ValueError:
            pass
        raise ErroEnv(f"{nome} no .env precisa ser um número inteiro")


def interpretar(texto: str) -> dict[str, str]:
    """Interpreta o conteúdo de um `.env`. ErroEnv cita linha e nome, nunca o valor."""
    valores: dict[str, str] = {}
    for numero, bruta in enumerate(texto.lstrip("﻿").splitlines(), start=1):
        linha = bruta.strip()
        if not linha or linha.startswith("#"):
            continue
        if "=" not in linha:
            raise ErroEnv(f".env, linha {numero}: esperado NOME=valor")
        nome, valor = linha.split("=", 1)
        nome = nome.strip()
        if nome.startswith("export ") or nome.startswith("export\t"):
            nome = nome[len("export"):].strip()
        if not _NOME.match(nome):
            raise ErroEnv(f".env, linha {numero}: nome de variável inválido")
        valores[nome] = _valor(nome, valor.strip(), numero)
    return valores


def _valor(nome: str, valor: str, numero: int) -> str:
    if valor[:1] in ("'", '"'):
        aspa = valor[0]
        fim = _fecha_aspas(valor, aspa)
        if fim is None:
            raise ErroEnv(f".env, linha {numero}: valor de {nome} com aspas sem fechar")
        resto = valor[fim + 1:].strip()
        if resto and not resto.startswith("#"):
            raise ErroEnv(f".env, linha {numero}: texto depois das aspas no valor de {nome}")
        miolo = valor[1:fim]
        if aspa == '"':
            miolo = re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(0)), miolo)
        return miolo
    comentario = re.search(r"\s#", valor)
    return (valor[: comentario.start()] if comentario else valor).strip()


def _fecha_aspas(valor: str, aspa: str) -> int | None:
    i = 1
    while i < len(valor):
        if aspa == '"' and valor[i] == "\\":
            i += 2
            continue
        if valor[i] == aspa:
            return i
        i += 1
    return None


def ler_env(caminho: Path | str) -> Env:
    """`Env` do arquivo `caminho`. Arquivo ausente é ambiente vazio (recurso sem chave não existe)."""
    try:
        texto = Path(caminho).read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return Env()
    except UnicodeDecodeError:
        raise ErroEnv(".env não está em UTF-8") from None
    return Env(interpretar(texto))


def carregar(raiz: Path | str) -> Env:
    """`Env` do `.env` da raiz da instalação."""
    return ler_env(Path(raiz) / NOME_ARQUIVO)
