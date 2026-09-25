"""Gera o `.env.example` da instalação a partir do catálogo (CONTRATO-capacidades, "O `.env`").

Um bloco comentado por grupo de variáveis: a primeira linha diz quais capacidades o bloco
libera, a segunda diz onde conseguir a chave, e as variáveis vêm vazias. Depois vem o bloco
`PROVEDOR_<CAPACIDADE>` de cada capacidade com mais de um provedor.

Entram as capacidades do catálogo passado: o núcleo e as `fornece` dos packs registrados nele.
Pack não registrado não polui o exemplo. O provedor de teste não entra (não é para a pessoa).
O `.env` nunca é lido nem tocado aqui: o exemplo não tem valor nenhum (M14).

Uso:

    from expxmedia.ambiente import envexample
    envexample.escrever(raiz)          # grava <raiz>/.env.example de forma atômica
    texto = envexample.gerar(catalogo)
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from expxmedia.ambiente.catalogo import Catalogo, Provedor

__all__ = ["gerar", "escrever", "NOME_ARQUIVO"]

NOME_ARQUIVO = ".env.example"

_CABECALHO = """\
# ---------------------------------------------------------------------------
# ExpxMedia — ambiente desta instalação. Copie para .env e NUNCA versione o .env.
# Cada bloco diz o que a chave libera. Deixe vazio o que não for usar.
# Cole a chave no arquivo, nunca na conversa com o assistente.
# ---------------------------------------------------------------------------
"""


class _Bloco:
    def __init__(self, env: tuple[str, ...], provedor: Provedor) -> None:
        self.env = env
        self.provedor = provedor
        self.capacidades: list[str] = []
        self.descricoes: list[str] = []
        self.opcionais: list[str] = []


def _onde(provedor: Provedor) -> str:
    texto = provedor.como_habilitar.strip()
    marca = "Onde conseguir:"
    if marca in texto:
        return "# " + texto[texto.index(marca):]
    return f"# Como habilitar: {texto}"


def gerar(catalogo: Catalogo | None = None) -> str:
    """Texto do `.env.example` para as capacidades de `catalogo` (padrão: só o núcleo)."""
    cat = catalogo or Catalogo()
    blocos: dict[tuple[str, ...], _Bloco] = {}
    padroes: list[tuple[str, list[str]]] = []
    for cap in cat.capacidades():
        reais = cap.provedores_ativos(teste=False)
        if len(reais) > 1:
            padroes.append((cap.id, [p.id for p in reais]))
        for prov in reais:
            if not prov.env:
                continue
            bloco = blocos.setdefault(prov.env, _Bloco(prov.env, prov))
            if cap.id not in bloco.capacidades:
                bloco.capacidades.append(cap.id)
                bloco.descricoes.append(cap.descricao)
            for nome in prov.env_opcional:
                if nome not in bloco.opcionais:
                    bloco.opcionais.append(nome)

    partes = [_CABECALHO]
    escritas: set[str] = set()
    for bloco in blocos.values():
        novas = [n for n in (*bloco.env, *bloco.opcionais) if n not in escritas]
        if not novas:
            continue
        titulo = f"# {', '.join(bloco.capacidades)} — {bloco.provedor.id}: {'; '.join(d for d in bloco.descricoes if d)}"
        linhas = [titulo.rstrip(": ")]
        linhas.append(_onde(bloco.provedor))
        repetidas = [n for n in bloco.env if n in escritas]
        if repetidas:
            linhas.append(f"# Também usa {', '.join(repetidas)} (definida acima).")
        opcionais = [n for n in bloco.opcionais if n in novas]
        if opcionais:
            linhas.append(f"# Opcional (amplia o provedor, ex.: Facebook): {', '.join(opcionais)}.")
        linhas += [f"{n}=" for n in novas]
        escritas.update(novas)
        partes.append("\n".join(linhas) + "\n")

    if padroes:
        linhas = [
            "# Provedor padrão quando houver mais de um satisfeito. Vazio: vale o primeiro da lista.",
            "# Apontar para um provedor sem chave é erro: o sistema não troca de provedor sozinho.",
        ]
        for cap_id, ids in padroes:
            variavel = f"PROVEDOR_{cap_id.upper()}"
            if variavel in escritas:
                continue
            linhas.append(f"# {variavel}: {' | '.join(ids)}")
            linhas.append(f"{variavel}=")
            escritas.add(variavel)
        partes.append("\n".join(linhas) + "\n")
    return "\n".join(partes)


def escrever(raiz: Path | str, catalogo: Catalogo | None = None) -> Path:
    """Grava `<raiz>/.env.example` de forma atômica (M15) e devolve o caminho. Não toca no `.env`."""
    destino = Path(raiz) / NOME_ARQUIVO
    texto = gerar(catalogo)
    fd, temporario = tempfile.mkstemp(dir=destino.parent, prefix=destino.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporario, destino)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise
    return destino
