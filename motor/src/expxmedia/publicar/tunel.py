"""URL pública temporária por túnel do Cloudflare (apoio de `publicar` e `agendar`).

Porta de `Instragram-Videos/pipeline/tunel.py`. Os provedores de publicação baixam a mídia de
uma URL pública: o Expx Flow durante a chamada do `post-api`, a Graph API durante o
processamento do contêiner. O túnel expõe só as cópias da mídia, pelo tempo em que estiver
aberto (base/tunel-url-publica.md):

- as cópias vão para um diretório temporário só com elas, sob nomes aleatórios de 16 bytes
  (tunel.py:30-34); o servidor HTTP local escuta só em 127.0.0.1 (tunel.py:37-39);
- `cloudflared tunnel --no-autoupdate --url http://127.0.0.1:<porta>` (tunel.py:43-45); o
  stdout/stderr do processo é drenado numa thread o tempo todo, porque pipe cheio trava o
  túnel no meio da transferência (tunel.py:47-54);
- a URL `https://<sub>.trycloudflare.com` impressa pelo processo é a base (tunel.py:68);
  sem ela em `TEMPO_LIMITE` segundos, ou se o processo morre, `ErroTunel` e o processo é
  encerrado;
- a confirmação externa (GET com `Range: bytes=0-0`) que falha vira **aviso**, não aborto:
  quem baixa é o servidor remoto, e o DNS local costuma guardar o NXDOMAIN do subdomínio
  novo (tunel.py:75-97);
- fechar encerra o processo (espera até 10 s e mata se preciso), para o servidor e apaga as
  cópias (tunel.py:100-107).

Um túnel pode expor vários arquivos (carrossel da Graph tem até 10), e precisa ficar aberto
até o provedor terminar de baixar (na Graph, até o contêiner ficar FINISHED).

Uso:

    from expxmedia.publicar import tunel
    with tunel.abrir([jpeg1, jpeg2]) as t:
        t.url_de(jpeg1)
    with tunel.url_publica_temporaria(video) as url:
        ...
"""
from __future__ import annotations

import contextlib
import http.server
import queue
import re
import secrets
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from urllib.request import Request, urlopen

__all__ = ["ErroTunel", "Tunel", "abrir", "url_publica_temporaria", "TEMPO_LIMITE"]

# Segundos para o túnel imprimir a URL. A origem usa 60 (Instragram-Videos/pipeline/tunel.py:15);
# o plano do núcleo fixa 30 s (sprint-08, T-08.03).
TEMPO_LIMITE = 30
ESPERA_ENCERRAR = 10  # s; origem: Instragram-Videos/pipeline/tunel.py:103
TENTATIVAS_CONFIRMACAO = 6  # origem: Instragram-Videos/pipeline/tunel.py:83
PAUSA_CONFIRMACAO = 3  # s; origem: Instragram-Videos/pipeline/tunel.py:94
TIMEOUT_CONFIRMACAO = 10  # s; origem: Instragram-Videos/pipeline/tunel.py:85
BYTES_NOME = 16  # origem: Instragram-Videos/pipeline/tunel.py:33
_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")  # origem: Instragram-Videos/pipeline/tunel.py:68
EXECUTAVEL = "cloudflared"


class ErroTunel(RuntimeError):
    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Tunel:
    """Túnel aberto: `base`, `url_de(arquivo)`, `url_local`, `processo`; `fechar()` encerra tudo."""

    def __init__(self, pasta: Path, nomes: dict[Path, str], servidor: http.server.ThreadingHTTPServer,
                 processo: subprocess.Popen, base: str, url_local: str) -> None:
        self.pasta = pasta
        self._nomes = nomes
        self._servidor = servidor
        self.processo = processo
        self.base = base
        self.url_local = url_local
        self._fechado = False

    def url_de(self, arquivo: Path | str) -> str:
        chave = Path(arquivo).resolve()
        if chave not in self._nomes:
            raise ErroTunel("arquivo_fora_do_tunel", f"{Path(arquivo).name} não foi exposto por este túnel")
        return f"{self.base}/{self._nomes[chave]}"

    @property
    def urls(self) -> list[str]:
        return [f"{self.base}/{nome}" for nome in self._nomes.values()]

    def fechar(self) -> None:
        if self._fechado:
            return
        self._fechado = True
        _encerrar(self.processo)
        self._servidor.shutdown()
        self._servidor.server_close()
        shutil.rmtree(self.pasta, ignore_errors=True)

    def __enter__(self) -> "Tunel":
        return self

    def __exit__(self, *exc: object) -> None:
        self.fechar()


def _encerrar(processo: subprocess.Popen) -> None:
    if processo.poll() is not None:
        return
    processo.terminate()
    try:
        processo.wait(timeout=ESPERA_ENCERRAR)
    except subprocess.TimeoutExpired:
        processo.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            processo.wait(timeout=ESPERA_ENCERRAR)


def abrir(
    arquivos: list[Path | str],
    *,
    tempo_limite: float = TEMPO_LIMITE,
    confirmar: bool = True,
    tentativas_confirmacao: int = TENTATIVAS_CONFIRMACAO,
    pausa_confirmacao: float = PAUSA_CONFIRMACAO,
    avisar: Callable[[str], None] | None = None,
) -> Tunel:
    """Expõe `arquivos` por um Quick Tunnel e devolve o `Tunel` aberto (feche com `fechar()`)."""
    executavel = shutil.which(EXECUTAVEL)
    if executavel is None:
        raise ErroTunel(
            "sem_cloudflared",
            "cloudflared não encontrado no PATH. Instale o cloudflared (macOS: brew install cloudflared; "
            "Linux e Windows: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) "
            "ou informe a mídia já hospedada numa URL pública.",
        )
    origem = [Path(a) for a in arquivos]
    if not origem:
        raise ErroTunel("sem_arquivos", "nada para expor")
    for arquivo in origem:
        if not arquivo.is_file():
            raise ErroTunel("arquivo_ausente", f"arquivo não encontrado: {arquivo.name}")

    pasta = Path(tempfile.mkdtemp(prefix="expxmedia-tunel-"))
    nomes: dict[Path, str] = {}
    for arquivo in origem:
        nome = f"{secrets.token_urlsafe(BYTES_NOME)}{arquivo.suffix.lower()}"
        shutil.copy2(arquivo, pasta / nome)
        nomes[arquivo.resolve()] = nome

    porta = _porta_livre()

    def fabrica(*a: object, **k: object) -> _Silencioso:
        return _Silencioso(*a, directory=str(pasta), **k)

    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", porta), fabrica)
    servidor.daemon_threads = True
    threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
    url_local = f"http://127.0.0.1:{porta}"

    try:
        processo = subprocess.Popen(
            [executavel, "tunnel", "--no-autoupdate", "--url", url_local],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
    except OSError as erro:
        servidor.shutdown()
        servidor.server_close()
        shutil.rmtree(pasta, ignore_errors=True)
        raise ErroTunel("cloudflared_falhou", f"não foi possível iniciar o cloudflared ({erro.strerror})") from None

    linhas: queue.Queue[str] = queue.Queue()

    def drenar() -> None:
        assert processo.stdout is not None
        for linha in processo.stdout:
            linhas.put(linha)

    threading.Thread(target=drenar, daemon=True).start()

    base = None
    limite = time.monotonic() + tempo_limite
    while base is None and time.monotonic() < limite:
        try:
            linha = linhas.get(timeout=min(0.2, max(limite - time.monotonic(), 0.01)))
        except queue.Empty:
            if processo.poll() is not None and linhas.empty():
                break
            continue
        achado = _URL.search(linha)
        if achado:
            base = achado.group(0)

    t = Tunel(pasta, nomes, servidor, processo, base or "", url_local)
    if base is None:
        t.fechar()
        raise ErroTunel("tunel_nao_subiu", f"o túnel do Cloudflare não subiu a tempo ({tempo_limite:g} s)")
    if confirmar:
        _confirmar(t, tentativas_confirmacao, pausa_confirmacao, avisar)
    return t


def _confirmar(t: Tunel, tentativas: int, pausa: float, avisar: Callable[[str], None] | None) -> None:
    """GET com Range na primeira URL; falha vira aviso (origem: Instragram-Videos/pipeline/tunel.py:82-97)."""
    url = t.urls[0]
    ultimo = None
    for tentativa in range(tentativas):
        try:
            with urlopen(Request(url, headers={"Range": "bytes=0-0"}), timeout=TIMEOUT_CONFIRMACAO) as r:
                if r.status in (200, 206):
                    return
                ultimo = f"HTTP {r.status}"
        except Exception as erro:  # qualquer falha local só vira aviso
            ultimo = type(erro).__name__
        if tentativa < tentativas - 1:
            time.sleep(pausa)
    if avisar is not None:
        avisar(f"aviso: não confirmei a URL do túnel daqui ({ultimo}); o DNS local costuma demorar no "
               "subdomínio novo. Seguindo, porque quem baixa é o provedor.")


@contextlib.contextmanager
def url_publica_temporaria(arquivo: Path | str, **opcoes: object) -> Iterator[str]:
    """Expõe UM arquivo pelo tempo do bloco `with` e rende a URL pública dele."""
    t = abrir([arquivo], **opcoes)  # type: ignore[arg-type]
    try:
        yield t.url_de(arquivo)
    finally:
        t.fechar()
