"""Preparação do ambiente local do motor (T-01.08, D-42).

Usa a rede e roda UMA vez, fora da suíte:

    cd motor && uv run python scripts/preparar_ambiente.py

Passos (todos idempotentes):
1. `uv sync` em motor/
2. `uv run playwright install chromium`
3. `npm ci` em motor/kit-remotion (o postinstall regenera o registro de composições)
4. `npx remotion browser ensure` no kit (chrome-headless-shell em node_modules/.remotion)
5. cópia da Inter 400 e 700 (latin, normal) e da licença OFL de @fontsource/inter para
   src/expxmedia/recursos/fontes/Inter/ (fonte padrão embarcada, D-21)
6. download, só se ausentes, dos modelos faster-whisper small e medium (Systran) e do u2net do rembg

As funções de checagem abaixo só olham a presença das coisas; a suíte
(tests/test_ambiente_local.py) as usa sem instalar nada.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
KIT = MOTOR / "kit-remotion"
FONTSOURCE_INTER = KIT / "node_modules" / "@fontsource" / "inter"
INTER = MOTOR / "src" / "expxmedia" / "recursos" / "fontes" / "Inter"
ARQUIVOS_INTER = {
    "inter-latin-400-normal.woff2": Path("files") / "inter-latin-400-normal.woff2",
    "inter-latin-700-normal.woff2": Path("files") / "inter-latin-700-normal.woff2",
}
# o pacote @fontsource/inter traz a licença OFL com o nome LICENSE; aqui ela vira OFL.txt
LICENCA_ORIGEM = ("OFL.txt", "LICENSE", "LICENSE.txt")

BINARIOS = ("ffmpeg", "say", "node", "npx", "claude", "uv")
MODELOS_WHISPER = ("small", "medium")


# ---------------------------------------------------------------- checagem (sem rede, sem instalar)


def binarios_ausentes():
    """Nomes da lista BINARIOS que não estão no PATH atual, na ordem da lista."""
    return [nome for nome in BINARIOS if shutil.which(nome) is None]


def _raiz_playwright():
    definida = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if definida and definida != "0":
        return Path(definida).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    if sys.platform.startswith("win"):
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ms-playwright"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ms-playwright"


def pastas_chromium_playwright():
    """Pastas do Chromium (e do headless shell) na revisão pedida pelo playwright do venv."""
    import playwright

    browsers = Path(playwright.__file__).parent / "driver" / "package" / "browsers.json"
    raiz = _raiz_playwright()
    pastas = []
    for b in json.loads(browsers.read_text(encoding="utf-8"))["browsers"]:
        if b["name"] in ("chromium", "chromium-headless-shell"):
            pastas.append(raiz / f"{b['name'].replace('-', '_')}-{b['revision']}")
    return pastas


def chrome_headless_shell_remotion():
    """Executável chrome-headless-shell baixado pelo Remotion no kit, ou None."""
    base = KIT / "node_modules" / ".remotion" / "chrome-headless-shell"
    if not base.is_dir():
        return None
    for candidato in sorted(base.rglob("chrome-headless-shell*")):
        if candidato.is_file() and candidato.name in ("chrome-headless-shell", "chrome-headless-shell.exe"):
            return candidato
    return None


def _cache_hf():
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"]).expanduser()
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]).expanduser() / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def cache_faster_whisper(modelo):
    return _cache_hf() / f"models--Systran--faster-whisper-{modelo}"


def _whisper_presente(modelo):
    return any((cache_faster_whisper(modelo) / "snapshots").glob("*/model.bin"))


def arquivo_u2net():
    base = os.environ.get("U2NET_HOME") or (Path.home() / ".u2net")
    return Path(base).expanduser() / "u2net.onnx"


def verificar():
    """Lista de problemas (vazia quando tudo está presente). Cada item cita o nome do que falta."""
    problemas = [f"binário ausente: {nome}" for nome in binarios_ausentes()]
    for pasta in pastas_chromium_playwright():
        if not (pasta / "INSTALLATION_COMPLETE").is_file():
            problemas.append(f"Chromium do Playwright ausente: {pasta.name}")
    if chrome_headless_shell_remotion() is None:
        problemas.append("chrome-headless-shell do Remotion ausente")
    for modelo in MODELOS_WHISPER:
        if not _whisper_presente(modelo):
            problemas.append(f"faster-whisper {modelo} ausente do cache")
    if not arquivo_u2net().is_file():
        problemas.append("u2net.onnx ausente")
    for nome in (*ARQUIVOS_INTER, "OFL.txt"):
        if not (INTER / nome).is_file():
            problemas.append(f"Inter ausente: {nome}")
    return problemas


# ---------------------------------------------------------------- preparação (com rede)


def _rodar(resumo, rotulo, comando, cwd):
    print(f"==> {rotulo}: {' '.join(comando)}", flush=True)
    subprocess.run(comando, cwd=cwd, check=True)
    resumo.append(f"ok   {rotulo}")


def _copiar_inter(resumo):
    INTER.mkdir(parents=True, exist_ok=True)
    for destino, origem in ARQUIVOS_INTER.items():
        shutil.copyfile(FONTSOURCE_INTER / origem, INTER / destino)
    licenca = next((FONTSOURCE_INTER / n for n in LICENCA_ORIGEM if (FONTSOURCE_INTER / n).is_file()), None)
    if licenca is None:
        raise FileNotFoundError(f"licença OFL não encontrada em {FONTSOURCE_INTER}")
    shutil.copyfile(licenca, INTER / "OFL.txt")
    resumo.append(f"ok   Inter copiada (licença {licenca.name} -> OFL.txt)")


def _baixar_modelos(resumo):
    # a suíte roda com HF_HUB_OFFLINE=1; aqui o download é permitido
    os.environ.pop("HF_HUB_OFFLINE", None)
    for modelo in MODELOS_WHISPER:
        if _whisper_presente(modelo):
            resumo.append(f"já   faster-whisper {modelo} em cache")
            continue
        from faster_whisper import download_model

        download_model(modelo)
        resumo.append(f"ok   faster-whisper {modelo} baixado")
    if arquivo_u2net().is_file():
        resumo.append("já   u2net.onnx presente")
    else:
        from rembg import new_session

        new_session("u2net")
        resumo.append("ok   u2net.onnx baixado")


def main():
    resumo = []
    _rodar(resumo, "uv sync", ["uv", "sync"], MOTOR)
    _rodar(resumo, "playwright chromium", ["uv", "run", "playwright", "install", "chromium"], MOTOR)
    _rodar(resumo, "npm ci do kit", ["npm", "ci"], KIT)
    _rodar(resumo, "remotion browser ensure", ["npx", "remotion", "browser", "ensure"], KIT)
    _copiar_inter(resumo)
    _baixar_modelos(resumo)

    problemas = verificar()
    print("\nResumo da preparação do ambiente:")
    for linha in resumo:
        print(f"  {linha}")
    print(f"  plataforma: {platform.system()} {platform.machine()}")
    if problemas:
        print("\nAinda falta:")
        for p in problemas:
            print(f"  - {p}")
        return 1
    print("\nAmbiente completo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
