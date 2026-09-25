"""Cache de fontes semeado para a Alma fictícia, sem rede (T-03.10 a T-03.13).

A Alma fictícia pede Fraunces e Nunito Sans do Google Fonts. A suíte roda offline (D-14), então
o cache local de fontes (`alma.fontes`, `<cache>/<slug-da-família>/`) é semeado com os arquivos
da Inter embarcada no motor declarados com o nome dessas famílias. O render passa a achar as
duas famílias "em cache", como numa instalação que já baixou as fontes uma vez.

Uso:

    from fontes_ficticias import semear_cache
    cache = semear_cache(tmp_path / "fontes")           # passa como cache_fontes=
    semear_cache(tmp_path / "xdg" / "expxmedia" / "fontes")  # ou XDG_CACHE_HOME=tmp_path/"xdg"
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from expxmedia.alma.fontes import PASTA_INTER
from expxmedia.nucleo.ids import slug

FAMILIAS = ("Fraunces", "Nunito Sans")
PESOS = {400: "inter-latin-400-normal.woff2", 700: "inter-latin-700-normal.woff2"}


def semear_cache(cache: Path, familias=FAMILIAS) -> Path:
    cache = Path(cache)
    for familia in familias:
        pasta = cache / slug(familia)
        pasta.mkdir(parents=True, exist_ok=True)
        blocos = []
        for peso, nome in PESOS.items():
            destino = pasta / nome
            shutil.copyfile(PASTA_INTER / nome, destino)
            blocos.append(
                "@font-face {\n"
                f"  font-family: '{familia}';\n  font-style: normal;\n  font-weight: {peso};\n"
                f"  src: url('{destino.resolve().as_uri()}') format('woff2');\n}}"
            )
        (pasta / "fontes.css").write_text("\n".join(blocos) + "\n", encoding="utf-8")
        (pasta / "arquivos.json").write_text(json.dumps(list(PESOS.values())), encoding="utf-8")
    return cache
