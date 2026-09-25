"""Verificação de capacidades: habilitada, por qual provedor e o que falta (CONTRATO-capacidades).

A consulta devolve exatamente a forma do contrato:

    {"capacidade": "narrar", "habilitada": false, "provedor": null,
     "provedores": [{"id": "elevenlabs", "satisfeito": false, "falta": ["ELEVENLABS_API_KEY"]}],
     "como_habilitar": "Coloque ELEVENLABS_API_KEY no .env. Onde conseguir: ..."}

A verificação é **local e barata** (D-15): confere variável preenchida no `.env`, executável no
PATH, um comando de status rápido para login de CLI (`higgsfield account status`,
`gh auth status`, com tempo-limite), pasta do Chromium baixado pelo Playwright, pacote Python
instalado e marcadores de estado da instalação. Não chama API de provedor nenhum. Nenhum valor
do `.env` sai na consulta, no aviso ou em erro (M14).

Provedor padrão (regras 1 a 3 do contrato, D-07):

1. um só provedor satisfeito: ele é usado, com ou sem `PROVEDOR_<CAPACIDADE>`;
2. mais de um e sem `PROVEDOR_*`: vale a ordem do catálogo; `aviso()` diz que a escolha é implícita;
3. `PROVEDOR_*` apontando para provedor não satisfeito (ou inexistente) é erro com orientação:
   a capacidade fica desabilitada e o sistema **não troca para outro em silêncio**.

Marcadores de estado, lidos em `.expxmedia/` na raiz da instalação:

- `aceite_galeria`: `galeria.json` com `"aceite": true` (CONTRATO-template, "O aceite");
- `agendador_local`: `agendador.json` com `"instalado": true` (gravado por quem instala o agendador);
- `oauth_youtube`: `youtube.json` com `"oauth": true` (gravado por quem faz o OAuth).

Capacidade com porta-voz (`narrar`, `avatar`, `rosto_ia`): com `porta_voz` na consulta, o id
correspondente precisa estar preenchido naquele porta-voz em `alma/alma.json` (lido cru; a carga
validada da Alma é de `expxmedia.alma`). Sem `porta_voz`, vale só o provedor.

Uso:

    from expxmedia.ambiente import verificar
    verificar.verificar("narrar", raiz, porta_voz="ana-souza")
    v = verificar.Verificador(raiz)
    v.verificar_tudo(); v.escolher_provedor("publicar"); v.aviso("publicar")
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from expxmedia.ambiente import env as leitor_env
from expxmedia.ambiente.catalogo import FLAG_TESTE, MARCADORES, Capacidade, Catalogo, Provedor
from expxmedia.nucleo import arquivos
from expxmedia.nucleo import raiz as instalacao

__all__ = [
    "ErroCapacidade",
    "ErroProvedor",
    "Verificador",
    "verificar",
    "STATUS_CLI",
    "TIMEOUT_STATUS",
]

# Comando de status de cada CLI com login: sai 0 com login feito.
STATUS_CLI: dict[str, tuple[str, ...]] = {
    "higgsfield": ("account", "status"),  # base/cli-higgsfield.md:18
    "gh": ("auth", "status"),
}
TIMEOUT_STATUS = 10.0  # segundos; comando de status que trava conta como não satisfeito

# Onde cada marcador é lido (relativo à raiz) e a chave que precisa ser true.
_MARCADORES_ARQUIVO = {
    "aceite_galeria": (".expxmedia/galeria.json", "aceite"),
    "agendador_local": (".expxmedia/agendador.json", "instalado"),
    "oauth_youtube": (".expxmedia/youtube.json", "oauth"),
}
# Binário que é pacote Python, não executável.
_MODULOS = {"faster-whisper": "faster_whisper"}
_CHROMIUM = "chromium-playwright"


class ErroCapacidade(RuntimeError):
    """Capacidade não habilitada. A mensagem é o `como_habilitar`, sem valor de segredo."""


class ErroProvedor(ErroCapacidade):
    """`PROVEDOR_<CAPACIDADE>` aponta para provedor inexistente ou não satisfeito (regra 3)."""


Executar = Callable[[list[str], float], int | None]


def _executar(argv: list[str], timeout: float) -> int | None:
    """Código de saída do comando, sem entrada e com a saída descartada; None se não rodou."""
    try:
        return subprocess.run(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=timeout, check=False,
        ).returncode
    except (OSError, subprocess.SubprocessError):
        return None


def _versao(argv: list[str], timeout: float) -> tuple[int, ...] | None:
    try:
        saida = subprocess.run(
            argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", saida or "")
    return tuple(int(g) for g in m.groups() if g is not None) if m else None


def _pastas_playwright() -> list[Path]:
    definida = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if definida and definida != "0":
        return [Path(definida)]
    if definida == "0":
        espec = importlib.util.find_spec("playwright")
        if espec and espec.origin:
            return [Path(espec.origin).parent / "driver" / "package" / ".local-browsers"]
        return []
    casa = Path.home()
    if sys.platform == "darwin":
        return [casa / "Library" / "Caches" / "ms-playwright"]
    if sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA")
        return [Path(local) / "ms-playwright"] if local else []
    return [Path(os.environ.get("XDG_CACHE_HOME") or casa / ".cache") / "ms-playwright"]


def _chromium_playwright() -> bool:
    """Se há um Chromium (ou chromium_headless_shell) baixado pelo Playwright."""
    for pasta in _pastas_playwright():
        try:
            if any(
                p.is_dir() and (p.name.startswith("chromium-") or p.name.startswith("chromium_headless_shell-"))
                for p in pasta.iterdir()
            ):
                return True
        except OSError:
            continue
    return False


def _modulo_python(nome: str) -> bool:
    try:
        return importlib.util.find_spec(nome) is not None
    except (ImportError, ValueError):
        return False


class Verificador:
    """Consulta de capacidades de uma instalação. Sondas locais são injetáveis para teste.

    Resultados de binário, CLI e dependência ficam em cache na instância: `verificar_tudo`
    roda cada comando de status uma vez só.
    """

    def __init__(
        self,
        raiz: Path | str,
        env: Mapping[str, str] | None = None,
        catalogo: Catalogo | None = None,
        *,
        processo: Mapping[str, str] | None = None,
        which: Callable[[str], str | None] = shutil.which,
        executar: Executar = _executar,
        versao: Callable[[list[str], float], tuple[int, ...] | None] = _versao,
        chromium_playwright: Callable[[], bool] = _chromium_playwright,
        modulo_python: Callable[[str], bool] = _modulo_python,
        timeout: float = TIMEOUT_STATUS,
    ) -> None:
        self.raiz = Path(raiz)
        self.env = leitor_env.Env(env) if env is not None else leitor_env.carregar(self.raiz)
        self.catalogo = catalogo or Catalogo()
        self._processo = os.environ if processo is None else processo
        self._which = which
        self._executar = executar
        self._versao = versao
        self._chromium = chromium_playwright
        self._modulo = modulo_python
        self._timeout = timeout
        self._cache: dict[tuple[str, str], bool] = {}
        self._alma: Any = None
        self._alma_lida = False

    # ---------- consulta ----------

    @property
    def teste(self) -> bool:
        """Provedores de teste existem? `EXPXMEDIA_PROVEDORES_TESTE=1` no processo ou no `.env`."""
        return self._processo.get(FLAG_TESTE, "").strip() == "1" or self.env.get(FLAG_TESTE, "").strip() == "1"

    def verificar(self, capacidade: str, porta_voz: str | None = None) -> dict[str, Any]:
        return self._consultar(capacidade, porta_voz, frozenset())

    def verificar_tudo(self, porta_voz: str | None = None) -> list[dict[str, Any]]:
        return [self.verificar(c.id, porta_voz) for c in self.catalogo.capacidades()]

    def escolher_provedor(self, capacidade: str, porta_voz: str | None = None) -> str:
        """Id do provedor a usar; ErroProvedor (regra 3) ou ErroCapacidade com a orientação."""
        consulta = self.verificar(capacidade, porta_voz)
        if consulta["habilitada"]:
            return consulta["provedor"]
        variavel = _variavel_padrao(capacidade)
        if self.env.get(variavel, "").strip():
            raise ErroProvedor(consulta["como_habilitar"])
        raise ErroCapacidade(f"{capacidade} não está habilitada. {consulta['como_habilitar']}")

    def aviso(self, capacidade: str, porta_voz: str | None = None) -> str | None:
        """Aviso do `doctor` quando a escolha entre vários provedores satisfeitos é implícita (regra 2)."""
        consulta = self.verificar(capacidade, porta_voz)
        satisfeitos = [p["id"] for p in consulta["provedores"] if p["satisfeito"]]
        variavel = _variavel_padrao(capacidade)
        if len(satisfeitos) > 1 and not self.env.get(variavel, "").strip():
            return (
                f"{capacidade}: {', '.join(satisfeitos)} estão satisfeitos e {variavel} não está no "
                f".env; usando {consulta['provedor']} (o primeiro do catálogo). Defina {variavel} "
                "para deixar a escolha explícita."
            )
        return None

    def _consultar(self, capacidade: str, porta_voz: str | None, pilha: frozenset[str]) -> dict[str, Any]:
        cap = self.catalogo.obter(capacidade)
        provedores = cap.provedores_ativos(self.teste)
        falta_porta_voz = self._falta_porta_voz(cap, porta_voz)
        estado = []
        for prov in provedores:
            falta = self._falta(cap, prov, porta_voz, pilha) + falta_porta_voz
            estado.append((prov, falta))
        lista = [{"id": p.id, "satisfeito": not f, "falta": f} for p, f in estado]
        satisfeitos = [p for p, f in estado if not f]

        variavel = _variavel_padrao(cap.id)
        escolhido = self.env.get(variavel, "").strip()
        if escolhido:
            ids = [p.id for p in provedores]
            if escolhido not in ids:
                orientacao = (
                    f"{variavel}={escolhido} no .env, mas {cap.id} não tem esse provedor. "
                    f"Use um de: {', '.join(ids)}."
                )
                return _consulta(cap.id, None, lista, orientacao)
            prov, falta = next((p, f) for p, f in estado if p.id == escolhido)
            if falta:
                orientacao = (
                    f"{variavel}={escolhido} no .env, mas {escolhido} não está satisfeito "
                    f"(falta: {', '.join(falta)}). O sistema não troca de provedor sozinho. "
                    f"{self._como(cap, prov, falta, porta_voz, pilha)} "
                    f"Ou mude {variavel} para outro provedor."
                )
                return _consulta(cap.id, None, lista, orientacao)
            return _consulta(cap.id, escolhido, lista, None)

        if satisfeitos:
            return _consulta(cap.id, satisfeitos[0].id, lista, None)
        if len(estado) == 1:
            prov, falta = estado[0]
            return _consulta(cap.id, None, lista, self._como(cap, prov, falta, porta_voz, pilha))
        partes = [f"Por {p.id}: {self._como(cap, p, f, porta_voz, pilha)}" for p, f in estado]
        return _consulta(cap.id, None, lista, " ".join(partes))

    def _como(self, cap: Capacidade, prov: Provedor, falta: list[str], porta_voz: str | None,
              pilha: frozenset[str]) -> str:
        """Instrução do provedor, mais o que falta na Alma e nas capacidades de que depende."""
        texto = prov.como_habilitar
        if cap.derivada_de and any(f == _falta_derivada(cap) for f in falta):
            dependencias = [
                f"{dep}: {self._consultar(dep, porta_voz, pilha | {cap.id})['como_habilitar']}"
                for dep in cap.derivada_de
                if dep not in pilha
            ]
            texto = " ".join([texto, *dependencias])
        if cap.porta_voz and any(f.startswith("alma: ") for f in falta):
            texto += (
                f" Preencha {cap.porta_voz} do porta-voz {porta_voz} em porta_vozes de "
                "alma/alma.json."
            )
        return texto

    # ---------- o que falta ----------

    def _falta(self, cap: Capacidade, prov: Provedor, porta_voz: str | None,
               pilha: frozenset[str]) -> list[str]:
        falta = [nome for nome in prov.env if not self.env.get(nome, "").strip()]
        if prov.cli:
            falta += self._falta_cli(prov.cli)
        for binario in prov.binarios:
            if not self._binario(binario):
                falta.append(_descrever_binario(binario))
        for marcador in prov.marcadores:
            if not self._marcador(marcador):
                falta.append(MARCADORES.get(marcador, marcador))
        if cap.derivada_de:
            habilitada = any(
                dep not in pilha and self._consultar(dep, porta_voz, pilha | {cap.id})["habilitada"]
                for dep in cap.derivada_de
            )
            if not habilitada:
                falta.append(_falta_derivada(cap))
        return falta

    def _falta_cli(self, cli: str) -> list[str]:
        caminho = self._which(cli)
        if caminho is None:
            return [f"binário {cli}"]
        status = STATUS_CLI.get(cli)
        if status is None:  # CLI de pack sem comando de status conhecido: basta existir
            return []
        chave = ("cli", cli)
        if chave not in self._cache:
            self._cache[chave] = self._executar([caminho, *status], self._timeout) == 0
        return [] if self._cache[chave] else [f"login do {cli} ({cli} {' '.join(status)})"]

    def _binario(self, especificacao: str) -> bool:
        chave = ("bin", especificacao)
        if chave not in self._cache:
            self._cache[chave] = any(self._alternativa(a.strip()) for a in especificacao.split("|"))
        return self._cache[chave]

    def _alternativa(self, nome: str) -> bool:
        if nome == _CHROMIUM:
            return self._chromium()
        if nome in _MODULOS:
            return self._modulo(_MODULOS[nome])
        m = re.fullmatch(r"([A-Za-z0-9_.-]+)>=(\d+(?:\.\d+)*)", nome)
        executavel = m.group(1) if m else nome
        caminho = self._which(executavel)
        if caminho is None:
            return False
        if not m:
            return True
        minima = tuple(int(x) for x in m.group(2).split("."))
        atual = self._versao([caminho, "--version"], self._timeout)
        return atual is not None and atual[: len(minima)] >= minima

    def _marcador(self, marcador: str) -> bool:
        onde = _MARCADORES_ARQUIVO.get(marcador)
        if onde is None:
            return False
        caminho, campo = onde
        try:
            dados = arquivos.ler_json(self.raiz / caminho, padrao=None)
        except arquivos.ErroArquivo:
            return False
        return isinstance(dados, dict) and dados.get(campo) is True

    def _falta_porta_voz(self, cap: Capacidade, porta_voz: str | None) -> list[str]:
        if not cap.porta_voz or porta_voz is None:
            return []
        alma = self._ler_alma()
        vozes = alma.get("porta_vozes") if isinstance(alma, dict) else None
        registro = next(
            (p for p in vozes or [] if isinstance(p, dict) and p.get("id") == porta_voz), None
        )
        if registro is None:
            return [f"alma: porta-voz {porta_voz} não existe em alma/alma.json"]
        valor: Any = registro
        for parte in cap.porta_voz.split("."):
            valor = valor.get(parte) if isinstance(valor, dict) else None
        if not (isinstance(valor, str) and valor.strip()):
            return [f"alma: porta-voz {porta_voz} sem {cap.porta_voz}"]
        return []

    def _ler_alma(self) -> Any:
        if not self._alma_lida:
            try:
                self._alma = arquivos.ler_json(self.raiz / "alma" / "alma.json", padrao=None)
            except arquivos.ErroArquivo:
                self._alma = None
            self._alma_lida = True
        return self._alma


def _consulta(capacidade: str, provedor: str | None, provedores: list[dict[str, Any]],
              como_habilitar: str | None) -> dict[str, Any]:
    return {
        "capacidade": capacidade,
        "habilitada": provedor is not None,
        "provedor": provedor,
        "provedores": provedores,
        "como_habilitar": como_habilitar,
    }


def _variavel_padrao(capacidade: str) -> str:
    return f"PROVEDOR_{capacidade.upper()}"


def _falta_derivada(cap: Capacidade) -> str:
    return f"{' ou '.join(cap.derivada_de)} habilitada"


def _descrever_binario(especificacao: str) -> str:
    if especificacao == _CHROMIUM:
        return "Chromium do Playwright"
    return "binário " + " ou ".join(a.strip() for a in especificacao.split("|"))


def verificar(capacidade: str, raiz: Path | str | None = None, porta_voz: str | None = None) -> dict[str, Any]:
    """Consulta única do contrato. Sem `raiz`, usa a instalação da pasta atual."""
    base = Path(raiz) if raiz is not None else instalacao.encontrar_raiz()
    return Verificador(base).verificar(capacidade, porta_voz)
