"""Retratos do porta-voz, recorte de fundo, filtros de banco e o slot `pessoa`.

- **Recorte com rembg `u2net`, nunca `u2netp`**: o leve deixa refletor e névoa de fundo na foto
  recortada (origem: Instagram-Carrosseis/galeria/tratamento.py:21-22). O modelo vem do cache
  local do rembg (`~/.u2net`, ou `U2NET_HOME`); nada é baixado nos testes.
- **Filtros de banco** (antes de baixar, origem: Instagram-Carrosseis/galeria/_galeria.py:512-524):
  duplicata (id já conhecido ou repetido), lado curto abaixo do mínimo e pessoa no `alt`. Foto de
  banco nunca faz o papel de uma pessoa da empresa.
- **Slot `pessoa` só aceita retrato do porta-voz** (`porta_vozes[].retratos` da Alma). Sem
  porta-voz, ou sem retrato no disco, o slot recebe um **substituto desenhado** (silhueta em SVG
  com as cores da Alma) e um aviso pedindo foto (origem: Instagram-Carrosseis/.claude/agents/galerista.md:72-74).

Uso:

    from expxmedia.imagem import retratos
    retratos.recortar_retrato(raiz, "ana-souza", "pecas/.../retrato-sem-fundo.png")
    retratos.filtrar_banco(itens_do_pexels, conhecidos={123})
    retratos.resolver_slot_pessoa(raiz, porta_voz=None)
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from expxmedia.nucleo import arquivos
from expxmedia.nucleo import raiz as instalacao

__all__ = [
    "ErroRetrato",
    "MODELO_RECORTE",
    "LADO_MINIMO_BANCO",
    "PESSOA_NO_ALT",
    "recortar",
    "recortar_retrato",
    "retratos_do_porta_voz",
    "filtrar_banco",
    "resolver_slot_pessoa",
    "substituto_svg",
]

MODELO_RECORTE = "u2net"  # origem: Instagram-Carrosseis/galeria/tratamento.py:21
LADO_MINIMO_BANCO = 1200  # px de lado curto; origem: Instagram-Carrosseis/galeria/_galeria.py:449
# origem: Instagram-Carrosseis/galeria/_galeria.py:456
PESSOA_NO_ALT = re.compile(
    r"\b(man|men|woman|women|person|people|boy|girl|guy|lady|male|female|portrait|face|selfie|model|"
    r"couple|team|crowd|businessman|businesswoman)\b",
    re.I,
)

_SESSOES: dict[str, Any] = {}


class ErroRetrato(ValueError):
    """Recorte com modelo proibido, retrato ausente, ou imagem que não pode ocupar o slot pessoa."""


# ---------- recorte ----------

def _sessao(modelo: str) -> Any:
    import rembg

    if modelo not in _SESSOES:
        _SESSOES[modelo] = rembg.new_session(modelo)
    return _SESSOES[modelo]


def recortar(raiz: Path | str, origem: str | Path, saida: str | Path, *, modelo: str = MODELO_RECORTE) -> dict[str, Any]:
    """Tira o fundo de `origem` e grava PNG RGBA em `saida` (ambos relativos à raiz).

    Só `u2net` é aceito: pedir outro modelo é erro, não troca silenciosa.
    """
    if modelo != MODELO_RECORTE:
        raise ErroRetrato(f"recorte só com {MODELO_RECORTE}: {modelo} deixa fantasma de fundo na foto")
    raiz = Path(raiz)
    arquivo = instalacao.absoluto(raiz, origem)
    destino = instalacao.absoluto(raiz, saida)
    if not arquivo.is_file():
        raise ErroRetrato(f"imagem não encontrada: {instalacao.relativo(raiz, arquivo)}")
    import rembg
    from PIL import Image, ImageOps

    with Image.open(arquivo) as img:
        img = ImageOps.exif_transpose(img)
        img.load()
        recortada = rembg.remove(img, session=_sessao(modelo)).convert("RGBA")
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".parcial")
    recortada.save(temporario, "PNG")
    temporario.replace(destino)
    return {
        "caminho": instalacao.relativo(raiz, destino),
        "origem": instalacao.relativo(raiz, arquivo),
        "modelo": modelo,
    }


def _porta_vozes(raiz: Path) -> list[dict[str, Any]]:
    alma = arquivos.ler_json(raiz / "alma" / "alma.json")
    return [p for p in alma.get("porta_vozes") or [] if isinstance(p, dict)]


def retratos_do_porta_voz(raiz: Path | str, porta_voz: str) -> list[str]:
    """Retratos declarados na Alma para o porta-voz que existem no disco (caminhos relativos)."""
    raiz = Path(raiz)
    registro = next((p for p in _porta_vozes(raiz) if p.get("id") == porta_voz), None)
    if registro is None:
        raise ErroRetrato(f"o porta-voz {porta_voz} não existe em alma/alma.json")
    achados = []
    for caminho in registro.get("retratos") or []:
        try:
            if instalacao.absoluto(raiz, caminho).is_file():
                achados.append(instalacao.relativo(raiz, caminho))
        except instalacao.ErroCaminho:
            continue
    return achados


def recortar_retrato(raiz: Path | str, porta_voz: str, saida: str | Path, *, indice: int = 0) -> dict[str, Any]:
    """Recorta o retrato `indice` do porta-voz. O original em `alma/assets/` nunca é reescrito."""
    disponiveis = retratos_do_porta_voz(raiz, porta_voz)
    if not disponiveis:
        raise ErroRetrato(f"o porta-voz {porta_voz} não tem retrato no disco")
    if not 0 <= indice < len(disponiveis):
        raise ErroRetrato(f"o porta-voz {porta_voz} tem {len(disponiveis)} retrato(s); índice {indice} fora")
    return {**recortar(raiz, disponiveis[indice], saida), "porta_voz": porta_voz}


# ---------- filtros de banco ----------

def filtrar_banco(
    itens: Iterable[dict[str, Any]],
    *,
    conhecidos: Iterable[Any] = (),
    lado_minimo: int = LADO_MINIMO_BANCO,
) -> dict[str, list[dict[str, Any]]]:
    """Separa itens normalizados do banco em aprovados e descartados, com o motivo de cada descarte.

    Ordem da origem: duplicata (id conhecido ou já visto nesta lista), tamanho (lado curto abaixo
    de `lado_minimo`, que vem do formato da peça) e pessoa no `alt`.
    """
    vistos = {str(c) for c in conhecidos}
    aprovados: list[dict[str, Any]] = []
    descartados: list[dict[str, Any]] = []
    for item in itens:
        chave = str(item.get("id"))
        largura, altura = int(item.get("largura") or 0), int(item.get("altura") or 0)
        achado = PESSOA_NO_ALT.search(item.get("alt") or "")
        if chave in vistos:
            motivo, detalhe = "duplicata", f"o item {chave} já foi visto"
        elif min(largura, altura) < lado_minimo:
            motivo, detalhe = "tamanho", f"{largura}×{altura}: lado curto abaixo de {lado_minimo} px"
        elif achado:
            motivo, detalhe = "pessoa_no_alt", f"o alt diz '{achado.group(0)}': pessoa em foto de banco não entra"
        else:
            motivo = detalhe = None
        vistos.add(chave)
        if motivo:
            descartados.append({"id": item.get("id"), "motivo": motivo, "detalhe": detalhe})
        else:
            aprovados.append(item)
    return {"aprovados": aprovados, "descartados": descartados}


# ---------- slot pessoa ----------

def substituto_svg(raiz: Path | str, largura: int = 400, altura: int = 500) -> str:
    """Silhueta desenhada com as cores da Alma (`fundo_alt` e `apoio`), para o slot pessoa sem foto."""
    alma = arquivos.ler_json(Path(raiz) / "alma" / "alma.json")
    cores = ((alma.get("visual") or {}).get("cores") or {})
    fundo = cores.get("fundo_alt") or cores.get("fundo") or "currentColor"
    figura = cores.get("apoio") or cores.get("texto") or "currentColor"
    cx, r = largura / 2, min(largura, altura) * 0.2
    cy = altura * 0.38
    ombro = altura * 0.72
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" '
        f'width="{largura}" height="{altura}" role="img" aria-label="retrato a preencher">'
        f'<rect width="{largura}" height="{altura}" fill="{fundo}"/>'
        f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{figura}"/>'
        f'<path d="M{largura * 0.15:g} {altura} C{largura * 0.15:g} {ombro:g} {largura * 0.85:g} {ombro:g} '
        f'{largura * 0.85:g} {altura} Z" fill="{figura}"/>'
        "</svg>"
    )


def _principal(raiz: Path) -> str | None:
    vozes = _porta_vozes(raiz)
    escolhido = next((p for p in vozes if p.get("principal") is True), vozes[0] if vozes else None)
    return escolhido.get("id") if escolhido else None


def resolver_slot_pessoa(
    raiz: Path | str,
    porta_voz: str | None = None,
    *,
    valor: str | Path | None = None,
) -> dict[str, Any]:
    """O que ocupa um slot `pessoa`: retrato do porta-voz ou o substituto desenhado.

    `porta_voz` None usa o principal da Alma. `valor` (caminho pedido para o slot) só é aceito se
    for um retrato desse porta-voz; foto de banco, imagem gerada sem aprovação ou arquivo qualquer
    é `ErroRetrato`.
    """
    raiz = Path(raiz)
    porta_voz = porta_voz or _principal(raiz)
    disponiveis = retratos_do_porta_voz(raiz, porta_voz) if porta_voz else []
    if valor is not None:
        pedido = instalacao.relativo(raiz, valor)
        if pedido not in disponiveis:
            raise ErroRetrato(
                f"slot pessoa só aceita retrato do porta-voz ({porta_voz or 'nenhum na Alma'}); "
                f"{pedido} não está em porta_vozes[].retratos"
            )
        return {"tipo": "retrato", "caminho": pedido, "porta_voz": porta_voz, "svg": None, "aviso": None}
    if disponiveis:
        return {"tipo": "retrato", "caminho": disponiveis[0], "porta_voz": porta_voz, "svg": None, "aviso": None}
    aviso = (
        f"o porta-voz {porta_voz} não tem retrato no disco" if porta_voz else "a Alma não tem porta-voz"
    ) + ": o slot pessoa saiu com o substituto desenhado. Coloque uma foto em alma/assets/retratos/ e declare em porta_vozes[].retratos."
    return {"tipo": "substituto", "caminho": None, "porta_voz": porta_voz, "svg": substituto_svg(raiz), "aviso": aviso}
