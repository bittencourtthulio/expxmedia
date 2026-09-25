"""Cota diária de geração por provedor, no estado da instalação (`estado/cotas.json`).

Gerar imagem ou vídeo custa dinheiro e a rotina roda sozinha: o teto do dia é o freio
(origem: Instagram-Carrosseis/galeria/_galeria.py:703, `GERADAS_POR_DIA = 12`). Na origem o teto
era um só para duas carteiras; aqui cada provedor tem o seu.

- A cota é conferida **antes** da chamada e anotada **depois, mesmo se a chamada falhar**: o que
  saiu do cartão conta, sirva ou não a resposta (origem: _galeria.py:778-789).
- Leitura-modificação-gravação sob a trava de `nucleo.arquivos` (M15), gravação atômica.
- O dia é o da empresa (`empresa.fuso` da Alma, M5). Dias passados são descartados ao gravar.

Formato:

    {"expxmedia_cotas": 1, "atualizado_em": "2026-09-25T10:00:00-03:00",
     "dias": {"2026-09-25": {"openrouter": 3, "higgsfield": 1}}}

Uso (os provedores recebem `cota=Cota(raiz).consumir`):

    from expxmedia.imagem import cota
    c = cota.Cota(raiz)
    with c.consumir("openrouter"):
        ...  # a chamada paga
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from expxmedia.nucleo import arquivos, tempo

__all__ = ["ErroCota", "Cota", "TETO_PADRAO", "TETOS", "CAMINHO", "VERSAO"]

CAMINHO = "estado/cotas.json"
CHAVE_VERSAO = "expxmedia_cotas"
VERSAO = 1
TETO_PADRAO = 12  # gerações por dia; origem: Instagram-Carrosseis/galeria/_galeria.py:703
TETOS: dict[str, int] = {"openrouter": TETO_PADRAO, "higgsfield": TETO_PADRAO}


class ErroCota(RuntimeError):
    """Teto do dia atingido, ou `cotas.json` ilegível ou de versão maior (M2)."""


class Cota:
    def __init__(self, raiz: Path | str, tetos: Mapping[str, int] | None = None) -> None:
        self.raiz = Path(raiz)
        self.caminho = self.raiz / CAMINHO
        self._tetos = {**TETOS, **(tetos or {})}

    def teto(self, provedor: str) -> int:
        return int(self._tetos.get(provedor, TETO_PADRAO))

    def _ler(self) -> dict[str, Any]:
        try:
            dados = arquivos.ler_json(self.caminho, padrao=None)
        except arquivos.ErroArquivo as erro:
            raise ErroCota(f"{CAMINHO} ilegível: {erro}") from None
        if dados is None:
            return {CHAVE_VERSAO: VERSAO, "atualizado_em": None, "dias": {}}
        if not isinstance(dados, dict) or not isinstance(dados.get(CHAVE_VERSAO), int):
            raise ErroCota(f"{CAMINHO} sem a chave de versão {CHAVE_VERSAO}")
        if dados[CHAVE_VERSAO] > VERSAO:
            raise ErroCota(f"{CAMINHO} é da versão {dados[CHAVE_VERSAO]}; este motor lê até a {VERSAO}")
        if not isinstance(dados.get("dias"), dict):
            dados["dias"] = {}
        return dados

    def usadas(self, provedor: str, dia: str | None = None) -> int:
        dia = dia or tempo.hoje(self.raiz)
        return int((self._ler()["dias"].get(dia) or {}).get(provedor, 0))

    def conferir(self, provedor: str) -> None:
        usadas, teto = self.usadas(provedor), self.teto(provedor)
        if usadas >= teto:
            raise ErroCota(
                f"{provedor}: já foram {usadas} gerações hoje (teto: {teto}). Gerar custa dinheiro; "
                "use o que já existe, busque no banco de imagens ou espere amanhã."
            )

    def anotar(self, provedor: str) -> int:
        """Soma uma geração de hoje ao provedor e devolve o total do dia."""
        with arquivos.trava(self.caminho):
            dados = self._ler()
            hoje = tempo.hoje(self.raiz)
            dias = {d: q for d, q in dados["dias"].items() if d >= hoje and isinstance(q, dict)}
            do_dia = dict(dias.get(hoje) or {})
            do_dia[provedor] = int(do_dia.get(provedor, 0)) + 1
            dias[hoje] = do_dia
            arquivos.gravar_json(self.caminho, {
                CHAVE_VERSAO: VERSAO,
                "atualizado_em": tempo.agora_iso(self.raiz),
                "dias": dias,
            })
            return do_dia[provedor]

    @contextmanager
    def consumir(self, provedor: str) -> Iterator[None]:
        """Confere o teto antes; anota ao sair, com sucesso ou com erro."""
        self.conferir(provedor)
        try:
            yield
        finally:
            self.anotar(provedor)
