"""Prancha dos slides e `render.json` com a impressão digital da renderização.

- **Prancha** (`_prancha.png`): os slides lado a lado, na ordem, cada um reduzido para caber numa
  célula de 432×540 com folga de 16 px sobre fundo cinza-escuro (os números da prancha de origem,
  que punha original × reconstrução; no núcleo não há original de terceiros, só a peça).
- **Impressão digital**: sha256 (16 hex) de tudo que muda o PNG — o manifesto do template sem os
  campos voláteis, o CSS, os fragmentos, os assets, a copy, os tokens da Alma e os bytes das
  fontes usadas. Mesmas entradas, mesma impressão; é o que diz se uma prévia em disco ainda vale.
- **render.json**: o resultado da renderização, com a chave de versão primeiro (M2), só caminhos
  relativos à pasta de saída (M9) e escrita atômica (M15).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from expxmedia.nucleo import arquivos

__all__ = [
    "LADO",
    "ALTURA",
    "FOLGA",
    "FUNDO",
    "NOME_PRANCHA",
    "NOME_RELATORIO",
    "VOLATEIS",
    "gerar_prancha",
    "impressao_digital",
    "gravar_relatorio",
]

LADO, ALTURA, FOLGA = 432, 540, 16  # origem: Instagram-Carrosseis/galeria/_galeria.py:1544
FUNDO = (40, 40, 40)                # origem: Instagram-Carrosseis/galeria/_galeria.py:1546
NOME_PRANCHA = "_prancha.png"
NOME_RELATORIO = "render.json"
# Campos do template.json que não mudam o PNG (origem: Instagram-Carrosseis/galeria/_galeria.py:93, no vocabulário do contrato).
VOLATEIS = ("template_id", "titulo", "status", "origem", "estilos", "serve_para", "criado_em", "atualizado_em",
            "validacao", "compartilhamento", "requisitos", "exige_porta_voz", "versoes", "dependencias")


def gerar_prancha(pngs: Iterable[Path | str], destino: Path | str) -> Path:
    """Os slides lado a lado numa folha só. Amplia também, se o slide for menor que a célula."""
    from PIL import Image

    caminhos = [Path(p) for p in pngs]
    n = max(1, len(caminhos))
    folha = Image.new("RGB", (n * LADO + (n + 1) * FOLGA, ALTURA + 2 * FOLGA), FUNDO)
    for coluna, caminho in enumerate(caminhos):
        if not caminho.is_file():
            continue
        with Image.open(caminho) as bruta:
            img = bruta.convert("RGB")
        k = min(LADO / img.width, ALTURA / img.height)
        img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
        folha.paste(img, (FOLGA + coluna * (LADO + FOLGA), FOLGA))
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".tmp.png")
    folha.save(temporario, optimize=True)
    temporario.replace(destino)
    return destino


def impressao_digital(
    pasta_template: Path,
    manifesto: dict[str, Any],
    copy: dict[str, Any],
    tokens: dict[str, str],
    fontes: list[dict[str, Any]],
    extras: dict[str, Any] | None = None,
) -> str:
    """sha256 (16 hex) das entradas que mudam o PNG. Nenhum caminho absoluto entra na conta."""
    pasta = Path(pasta_template)
    estavel = {k: v for k, v in manifesto.items() if not k.startswith("_") and k not in VOLATEIS}
    h = hashlib.sha256()
    h.update(json.dumps({"template": estavel, "copy": copy, "tokens": tokens, "fontes": fontes, "extras": extras or {}},
                        sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
    for arq in [pasta / "template.css", *sorted((pasta / "slides").glob("*.html")),
                *sorted(a for a in (pasta / "assets").glob("**/*") if a.is_file())]:
        if arq.is_file():
            h.update(arq.relative_to(pasta).as_posix().encode("utf-8") + b"\0" + arq.read_bytes())
    return h.hexdigest()[:16]


def gravar_relatorio(saida: Path | str, resultado: dict[str, Any]) -> Path:
    """Grava `render.json` na pasta de saída, de forma atômica."""
    destino = Path(saida) / NOME_RELATORIO
    arquivos.gravar_json(destino, resultado)
    return destino
