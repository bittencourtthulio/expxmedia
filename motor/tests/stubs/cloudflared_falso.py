"""Executável falso do `cloudflared` para os testes (D-15): nada sai para a rede.

Imita o Quick Tunnel: `cloudflared tunnel --no-autoupdate --url http://127.0.0.1:<porta>`
escreve no stderr as linhas de log do processo real, entre elas a URL
`https://<sub>.trycloudflare.com`, e fica rodando até ser encerrado.

Variáveis de ambiente:
- CLOUDFLARED_FALSO_MODO: `url` (padrão) imprime a URL; `mudo` nunca imprime URL e fica
  rodando; `morre` sai com código 1 sem imprimir URL;
- CLOUDFLARED_FALSO_SUB: subdomínio impresso (padrão `tunel-falso-de-teste`);
- CLOUDFLARED_FALSO_LOG: arquivo onde cada evento vira uma linha JSON:
  `{"evento": "inicio", "pid": ..., "argv": [...]}` e `{"evento": "encerrado", "pid": ...}`.

No teste, `instalar(pasta)` grava na pasta um `cloudflared` executável que roda este arquivo com o
Python atual; ponha a pasta no começo do PATH.
"""
from __future__ import annotations

import json
import os
import signal
import stat
import sys
import time
from pathlib import Path


def _log(evento: dict) -> None:
    caminho = os.environ.get("CLOUDFLARED_FALSO_LOG")
    if caminho:
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento) + "\n")


def _encerrar(*_a) -> None:
    _log({"evento": "encerrado", "pid": os.getpid()})
    sys.exit(0)


def main(argv: list[str]) -> int:
    _log({"evento": "inicio", "pid": os.getpid(), "argv": argv})
    signal.signal(signal.SIGTERM, _encerrar)
    signal.signal(signal.SIGINT, _encerrar)
    if argv[:1] != ["tunnel"] or "--url" not in argv:
        sys.stderr.write("comando não suportado pelo falso\n")
        return 2
    modo = os.environ.get("CLOUDFLARED_FALSO_MODO", "url")
    err = sys.stderr
    err.write("2026-09-25T10:00:00Z INF Thank you for trying Cloudflare Tunnel.\n")
    err.write("2026-09-25T10:00:00Z INF Requesting new quick Tunnel on trycloudflare.com...\n")
    err.flush()
    if modo == "morre":
        return 1
    if modo == "url":
        sub = os.environ.get("CLOUDFLARED_FALSO_SUB", "tunel-falso-de-teste")
        err.write("2026-09-25T10:00:01Z INF +----------------------------------------------------+\n")
        err.write("2026-09-25T10:00:01Z INF |  Your quick Tunnel has been created! Visit it at   |\n")
        err.write(f"2026-09-25T10:00:01Z INF |  https://{sub}.trycloudflare.com                   |\n")
        err.write("2026-09-25T10:00:01Z INF +----------------------------------------------------+\n")
        err.flush()
    while True:
        time.sleep(0.1)


def instalar(pasta: Path | str) -> Path:
    """Grava `pasta/cloudflared`, executável que roda este falso com o Python atual."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    alvo = pasta / "cloudflared"
    alvo.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{Path(__file__).resolve()}" "$@"\n', encoding="utf-8")
    alvo.chmod(alvo.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return alvo


def eventos(log: Path | str) -> list[dict]:
    caminho = Path(log)
    if not caminho.exists():
        return []
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]


try:
    import pytest
except ImportError:  # rodando como executável, fora do pytest
    pytest = None

if pytest is not None:

    @pytest.fixture
    def cloudflared_no_path(tmp_path, monkeypatch):
        """Põe o falso no começo do PATH; devolve o caminho do log de eventos."""
        pasta = tmp_path / "bin-cloudflared"
        instalar(pasta)
        log = tmp_path / "cloudflared.log"
        monkeypatch.setenv("PATH", f"{pasta}{os.pathsep}{os.environ.get('PATH', '')}")
        monkeypatch.setenv("CLOUDFLARED_FALSO_LOG", str(log))
        monkeypatch.delenv("CLOUDFLARED_FALSO_MODO", raising=False)
        return log


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
