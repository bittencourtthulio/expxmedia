"""Executável falso do CLI `higgsfield` para os testes (D-15, D-27): nada sai para a rede.

Responde aos subcomandos que o motor usa, com a forma observada no CLI real 1.1.26
(base/cli-higgsfield.md; esquemas copiados de `higgsfield model get <jt> --json`):

- `account status`            → sai 0 (login feito); com HIGGSFIELD_FALSO_SEM_LOGIN=1 sai 1 com
                                "Not authenticated.";
- `model get <jt> [--json]`   → o esquema do modelo; modelo desconhecido sai 1 com `Unknown model`;
- `generate create <jt> ...`  → como o servidor: parâmetro fora do esquema sai 1 com `Unknown params`,
                                valor fora do enum sai 1 com `Invalid values`; senão imprime a lista
                                com um job `completed` cujo `result_url` aponta para
                                HIGGSFIELD_FALSO_URL (o stub HTTP do teste).

Cada chamada é acrescentada como uma linha JSON (a lista de argumentos) em HIGGSFIELD_FALSO_LOG.

No teste, `instalar(pasta)` grava na pasta um `higgsfield` executável que roda este arquivo com o
Python atual; ponha a pasta no começo do PATH.
"""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

ESQUEMAS = {
    "seedance_2_0": {
        "display_name": "Seedance 2.0",
        "job_type": "seedance_2_0",
        "type": "video",
        "params": [
            {"name": "aspect_ratio", "type": "string", "default": "16:9", "required": False,
             "enum": ["auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]},
            {"name": "duration", "type": "integer", "default": 5, "required": False},
            {"name": "end_image", "type": "object|null", "default": None, "required": False},
            {"name": "generate_audio", "type": "boolean", "default": True, "required": False},
            {"name": "image_references", "type": "array", "default": None, "required": False},
            {"name": "mode", "type": "string", "default": "std", "required": False, "enum": ["std", "fast"]},
            {"name": "prompt", "type": "string", "default": None, "required": True},
            {"name": "resolution", "type": "string", "default": "720p", "required": False,
             "enum": ["480p", "720p", "1080p", "4k"]},
            {"name": "start_image", "type": "object|null", "default": None, "required": False},
        ],
        "rules": [],
    },
    "seedance_2_5": {
        "display_name": "Seedance 2.5",
        "job_type": "seedance_2_5",
        "type": "video",
        "params": [
            {"name": "aspect_ratio", "type": "string", "default": "16:9", "required": False,
             "enum": ["auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]},
            {"name": "duration", "type": "integer", "default": 5, "required": False},
            {"name": "end_image", "type": "object|null", "default": None, "required": False},
            {"name": "generate_audio", "type": "boolean", "default": True, "required": False},
            {"name": "mode", "type": "string", "default": "t2v", "required": False,
             "enum": ["t2v", "omni_reference", "video_edit", "video_extension"]},
            {"name": "prompt", "type": "string", "default": None, "required": True},
            {"name": "resolution", "type": "string", "default": "720p", "required": False,
             "enum": ["480p", "720p", "1080p"]},
            {"name": "start_image", "type": "object|null", "default": None, "required": False},
        ],
        "rules": [],
    },
    "text2image_soul_v2": {
        "display_name": "Higgsfield Soul 2.0",
        "job_type": "text2image_soul_v2",
        "type": "image",
        "params": [
            {"name": "aspect_ratio", "type": "string", "default": "1:1", "required": False,
             "enum": ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"]},
            {"name": "custom_reference_id", "type": "string|null", "default": None, "required": False},
            {"name": "image_references", "type": "array", "default": None, "required": False},
            {"name": "prompt", "type": "string", "default": None, "required": True},
            {"name": "quality", "type": "string", "default": "2k", "required": False, "enum": ["1.5k", "2k"]},
            {"name": "seed", "type": "integer|null", "default": None, "required": False},
            {"name": "style_id", "type": "string|null", "default": None, "required": False},
        ],
        "rules": [],
    },
}

# flags do CLI que não são parâmetro do modelo
_FLAGS_DO_CLI = {"wait", "json", "wait_timeout", "wait_interval"}
_FLAGS_SEM_VALOR = {"wait", "json"}


def _registrar(argv: list[str]) -> None:
    log = os.environ.get("HIGGSFIELD_FALSO_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(argv, ensure_ascii=False) + "\n")


def _falhar(mensagem: str) -> int:
    sys.stderr.write(mensagem + "\n")
    return 1


def _flags(resto: list[str]) -> dict[str, str | bool]:
    flags: dict[str, str | bool] = {}
    i = 0
    while i < len(resto):
        item = resto[i]
        if not item.startswith("--"):
            i += 1
            continue
        nome = item[2:].replace("-", "_")
        if nome in _FLAGS_SEM_VALOR or i + 1 >= len(resto) or resto[i + 1].startswith("--"):
            flags[nome] = True
            i += 1
        else:
            flags[nome] = resto[i + 1]
            i += 2
    return flags


def main(argv: list[str]) -> int:
    _registrar(argv)
    if argv[:2] == ["account", "status"]:
        if os.environ.get("HIGGSFIELD_FALSO_SEM_LOGIN") == "1":
            return _falhar("Not authenticated.")
        print("conta de teste")
        return 0
    if argv[:2] == ["model", "get"] and len(argv) >= 3:
        esquema = ESQUEMAS.get(argv[2])
        if esquema is None:
            return _falhar(f'Unknown model "{argv[2]}"')
        print(json.dumps(esquema, indent=2))
        return 0
    if argv[:2] == ["generate", "create"] and len(argv) >= 3:
        esquema = ESQUEMAS.get(argv[2])
        if esquema is None:
            return _falhar(f'Unknown model "{argv[2]}"')
        flags = _flags(argv[3:])
        params = {p["name"]: p for p in esquema["params"]}
        desconhecidos = sorted(n for n in flags if n not in params and n not in _FLAGS_DO_CLI)
        if desconhecidos:
            return _falhar(f"Unknown params: {', '.join(desconhecidos)}")
        invalidos = [f"{n}={v}" for n, v in flags.items()
                     if n in params and params[n].get("enum") and v not in params[n]["enum"]]
        if invalidos:
            return _falhar(f"Invalid values: {', '.join(invalidos)}")
        if "prompt" not in flags:
            return _falhar("Missing required params: prompt")
        base = os.environ.get("HIGGSFIELD_FALSO_URL", "http://127.0.0.1:9")
        sufixo = "png" if esquema["type"] == "image" else "mp4"
        job = {"id": "job-falso-0001", "job_type": argv[2], "status": "completed",
               "params": {}, "result_url": f"{base}/resultado.{sufixo}?assinatura=segredo",
               "created_at": "2026-09-25T10:00:00Z"}
        print(json.dumps([job]))
        return 0
    return _falhar(f"comando não suportado pelo falso: {' '.join(argv)}")


def instalar(pasta: Path | str) -> Path:
    """Grava `pasta/higgsfield`, executável que roda este falso com o Python atual."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    alvo = pasta / "higgsfield"
    alvo.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{Path(__file__).resolve()}" "$@"\n', encoding="utf-8")
    alvo.chmod(alvo.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return alvo


def chamadas(log: Path | str) -> list[list[str]]:
    """As chamadas registradas, na ordem."""
    caminho = Path(log)
    if not caminho.exists():
        return []
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
