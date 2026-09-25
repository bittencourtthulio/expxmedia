"""Instalação do agendador local por sistema operacional (D-08, D-30; base/agendador-local-por-so.md).

O agendador é um disparo **periódico de minuto em minuto** de `expxmedia-motor agendador rodar
--raiz <raiz>` (`agendador.servico`), não um processo eterno: cada rodada dura o que tiver de
publicar e sai. A regra de atraso vive no serviço, então nenhum mecanismo do SO de "recuperar
disparo perdido" é usado (base, risco 1).

| Sistema | O que é gerado | Onde |
|---|---|---|
| macOS | LaunchAgent `.plist` com `StartInterval` 60 | `~/Library/LaunchAgents/` |
| Windows | XML do Agendador de Tarefas: gatilho ao fazer logon repetindo a cada minuto (PT1M) | `.expxmedia/agendador/` + `schtasks /create /xml` |
| Linux | `.service` (oneshot) + `.timer` (`OnCalendar=*-*-* *:*:00`, `Persistent=false`) | `~/.config/systemd/user/` |
| Linux sem systemd | linha de crontab `* * * * *` | crontab do usuário |

Por padrão **só gera** e devolve o conteúdo, os destinos e os comandos, sem tocar em nada.
Com `aplicar=True`, escreve os arquivos, roda os comandos (launchctl, schtasks, systemctl ou
crontab) e, só se tudo deu certo, grava o marcador `.expxmedia/agendador.json`
`{"instalado": true, "sistema", "instalado_em"}`, que o `ambiente.verificar` lê para habilitar
`agendar` via `meta_graph`.

O plist, a unidade e a tarefa levam o caminho absoluto da instalação e do executável: o SO não
resolve caminho relativo. O marcador, que é artefato do ExpxMedia, não leva nenhum (M9).
O ambiente do agendador do SO é pelado (`Instagram-Carrosseis/rotina.sh:2-3`): o `PATH` do momento
da instalação vai junto, para `ffmpeg` e `cloudflared` serem achados na rodada.

Uso:

    from expxmedia.agendador import instalar
    instalar.gerar(raiz)                     # só mostra o que seria instalado neste SO
    instalar.instalar(raiz, aplicar=True)    # instala de verdade
"""
from __future__ import annotations

import hashlib
import os
import platform
import plistlib
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from expxmedia.nucleo import arquivos, tempo

__all__ = ["ErroInstalacao", "INTERVALO_S", "detectar_sistema", "gerar", "instalar"]

INTERVALO_S = 60  # D-30: o agendador verifica a cada minuto
TIMEOUT_COMANDO = 60  # s por comando de instalação
EXECUTAVEL = "expxmedia-motor"
MARCADOR = Path(".expxmedia") / "agendador.json"
PASTA_LOGS = Path(".expxmedia") / "logs"
_NS_TAREFA = "http://schemas.microsoft.com/windows/2004/02/mit/task"

Executar = Callable[..., int]


class ErroInstalacao(RuntimeError):
    """Sistema não suportado, executável não achado ou comando de instalação que falhou."""


def detectar_sistema() -> str:
    nome = platform.system()
    sistemas = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}
    if nome not in sistemas:
        raise ErroInstalacao(f"sistema operacional sem agendador local suportado: {nome!r} "
                             "(suportados: macOS, Windows, Linux)")
    return sistemas[nome]


def gerar(
    raiz: Path | str,
    *,
    sistema: str | None = None,
    executavel: str | None = None,
    home: Path | str | None = None,
    systemd: bool | None = None,
) -> dict[str, Any]:
    """O que seria instalado, sem tocar em nada.

    Devolve `{"sistema", "rotulo", "arquivos": [{"destino", "conteudo"}], "comandos": [[...]],
    "instrucoes": [...], "cron"}`. No Linux, `systemd=None` detecta pelo `systemctl` no PATH e,
    sem ele, cai para cron (`sistema: linux_cron`).
    """
    raiz = Path(raiz).resolve()
    sistema = sistema or detectar_sistema()
    exe = executavel or _achar_executavel()
    home = Path(home) if home is not None else Path.home()
    rotulo = _rotulo(raiz)
    argumentos = ["agendador", "rodar", "--raiz", str(raiz)]
    caminho_env = _path(exe)
    if sistema == "macos":
        return _macos(raiz, exe, argumentos, home, rotulo, caminho_env)
    if sistema == "windows":
        return _windows(raiz, exe, rotulo)
    if sistema == "linux":
        if systemd is None:
            systemd = shutil.which("systemctl") is not None
        if systemd:
            return _systemd(raiz, exe, argumentos, home, rotulo, caminho_env)
        return _cron(raiz, exe, argumentos, rotulo, caminho_env)
    raise ErroInstalacao(f"sistema desconhecido: {sistema!r} (use macos, windows ou linux)")


def instalar(
    raiz: Path | str,
    *,
    sistema: str | None = None,
    aplicar: bool = False,
    executavel: str | None = None,
    home: Path | str | None = None,
    systemd: bool | None = None,
    executar: Executar | None = None,
) -> dict[str, Any]:
    """Gera e, com `aplicar=True`, instala. Devolve o mesmo que `gerar` mais `aplicado`."""
    raiz = Path(raiz).resolve()
    plano = gerar(raiz, sistema=sistema, executavel=executavel, home=home, systemd=systemd)
    plano["aplicado"] = False
    if not aplicar:
        return plano
    executar = executar or _executar
    (raiz / PASTA_LOGS).mkdir(parents=True, exist_ok=True)
    for arquivo in plano["arquivos"]:
        destino = Path(arquivo["destino"])
        destino.parent.mkdir(parents=True, exist_ok=True)
        if plano["sistema"] == "windows":
            destino.write_text(arquivo["conteudo"], encoding="utf-16")  # o schtasks lê o XML em UTF-16
        else:
            destino.write_text(arquivo["conteudo"], encoding="utf-8")
    for comando in plano["comandos"]:
        codigo = executar(comando)
        if codigo != 0 and not _tolerado(comando):
            raise ErroInstalacao(f"o comando de instalação falhou (código {codigo}): {' '.join(comando[:3])}; "
                                 "o agendador não foi dado como instalado")
    arquivos.gravar_json(raiz / MARCADOR, {
        "instalado": True, "sistema": plano["sistema"], "instalado_em": tempo.agora_iso(raiz),
    })
    plano["aplicado"] = True
    return plano


# ---------------------------------------------------------------- por sistema


def _macos(raiz: Path, exe: str, argumentos: list[str], home: Path, rotulo: str, caminho_env: str) -> dict[str, Any]:
    destino = home / "Library" / "LaunchAgents" / f"{rotulo}.plist"
    log = raiz / PASTA_LOGS / "agendador.log"
    plist = {
        "Label": rotulo,
        "ProgramArguments": [exe, *argumentos],
        "StartInterval": INTERVALO_S,
        "RunAtLoad": True,
        "WorkingDirectory": str(raiz),
        "EnvironmentVariables": {"PATH": caminho_env},
        "StandardOutPath": str(log),
        "StandardErrorPath": str(log),
    }
    dominio = f"gui/{_uid()}"
    return _plano("macos", rotulo, [(destino, plistlib.dumps(plist).decode("utf-8"))], [
        ["launchctl", "bootout", dominio, str(destino)],  # pode não estar carregado ainda
        ["launchctl", "bootstrap", dominio, str(destino)],
    ], [
        f"O LaunchAgent roda a cada {INTERVALO_S} s enquanto a sessão do usuário estiver aberta. Com o Mac "
        "dormindo ou desligado nada é publicado; o que passar da tolerância vira falhou com motivo atraso.",
        f"Para remover: launchctl bootout {dominio} {destino} e apague o arquivo.",
    ])


def _windows(raiz: Path, exe: str, rotulo: str) -> dict[str, Any]:
    destino = raiz / ".expxmedia" / "agendador" / f"{rotulo}.xml"
    argumentos = f'agendador rodar --raiz "{raiz}"'
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="{_NS_TAREFA}">
  <RegistrationInfo>
    <Description>Agendador local do ExpxMedia: publica no horário as peças agendadas.</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT1M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Autor">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>false</StartWhenAvailable>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Autor">
    <Exec>
      <Command>{escape(exe)}</Command>
      <Arguments>{escape(argumentos)}</Arguments>
      <WorkingDirectory>{escape(str(raiz))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""
    return _plano("windows", rotulo, [(destino, xml)], [
        ["schtasks", "/create", "/tn", rotulo, "/xml", str(destino), "/f"],
    ], [
        "A tarefa começa ao fazer logon e repete a cada minuto enquanto a sessão estiver aberta.",
        f"Para testar: schtasks /run /tn {rotulo}. Para remover: schtasks /delete /tn {rotulo} /f.",
    ])


def _systemd(raiz: Path, exe: str, argumentos: list[str], home: Path, rotulo: str,
             caminho_env: str) -> dict[str, Any]:
    pasta = home / ".config" / "systemd" / "user"
    nome = rotulo.replace(".", "-")
    servico, timer = pasta / f"{nome}.service", pasta / f"{nome}.timer"
    exec_start = " ".join(_aspas_systemd(p) for p in (exe, *argumentos))
    unidade = f"""[Unit]
Description=Agendador local do ExpxMedia (uma rodada)

[Service]
Type=oneshot
WorkingDirectory={_aspas_systemd(str(raiz))}
Environment={_aspas_systemd("PATH=" + caminho_env)}
ExecStart={exec_start}
"""
    relogio = f"""[Unit]
Description=Agendador local do ExpxMedia, de minuto em minuto

[Timer]
OnCalendar=*-*-* *:*:00
AccuracySec=1s
Persistent=false
Unit={servico.name}

[Install]
WantedBy=timers.target
"""
    usuario = os.environ.get("USER") or os.environ.get("LOGNAME") or "$USER"
    return _plano("linux", rotulo, [(servico, unidade), (timer, relogio)], [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", timer.name],
    ], [
        f"Sem sessão aberta o systemd de usuário para. Para o agendador rodar depois do logout e no boot, "
        f"rode uma vez: loginctl enable-linger {usuario}",
        f"Para conferir: systemctl --user list-timers {timer.name}. Para remover: "
        f"systemctl --user disable --now {timer.name} e apague os dois arquivos.",
    ])


def _cron(raiz: Path, exe: str, argumentos: list[str], rotulo: str, caminho_env: str) -> dict[str, Any]:
    log = raiz / PASTA_LOGS / "agendador.log"
    comando = " ".join(shlex.quote(p) for p in (exe, *argumentos))
    linha = (f"* * * * * cd {shlex.quote(str(raiz))} && PATH={shlex.quote(caminho_env)} {comando} "
             f">> {shlex.quote(str(log))} 2>&1 # {rotulo}")
    script = (f"(crontab -l 2>/dev/null | grep -v -F {shlex.quote('# ' + rotulo)}; "
              f"echo {shlex.quote(linha)}) | crontab -")
    plano = _plano("linux_cron", rotulo, [], [["sh", "-c", script]], [
        "Sem systemd de usuário: o agendador entra no crontab do usuário, de minuto em minuto.",
        f"Para remover: crontab -e e apague a linha terminada em # {rotulo}.",
    ])
    plano["cron"] = linha
    return plano


# ---------------------------------------------------------------- apoio


def _plano(sistema: str, rotulo: str, arquivos_: list[tuple[Path, str]], comandos: list[list[str]],
           instrucoes: list[str]) -> dict[str, Any]:
    return {
        "sistema": sistema,
        "rotulo": rotulo,
        "arquivos": [{"destino": str(d), "conteudo": c} for d, c in arquivos_],
        "comandos": comandos,
        "instrucoes": instrucoes,
        "cron": None,
    }


def _rotulo(raiz: Path) -> str:
    """Estável por instalação e distinto entre instalações na mesma máquina."""
    return f"local.expxmedia.agendador.{hashlib.sha256(str(raiz).encode('utf-8')).hexdigest()[:8]}"


def _achar_executavel() -> str:
    achado = shutil.which(EXECUTAVEL) or _candidato_ao_lado()
    if not achado:
        raise ErroInstalacao(f"não achei o executável {EXECUTAVEL} no PATH nem ao lado do Python em uso; "
                             "instale o motor (uv tool install / uv sync) ou informe o caminho")
    return str(Path(achado).resolve())


def _candidato_ao_lado() -> str | None:
    pasta = Path(sys.executable).parent
    for nome in (EXECUTAVEL, f"{EXECUTAVEL}.exe"):
        if (pasta / nome).is_file():
            return str(pasta / nome)
    return None


def _path(exe: str) -> str:
    partes = [str(Path(exe).parent), *os.environ.get("PATH", "").split(os.pathsep)]
    vistas: list[str] = []
    for parte in partes:
        if parte and parte not in vistas:
            vistas.append(parte)
    return os.pathsep.join(vistas)


def _aspas_systemd(valor: str) -> str:
    if not any(c in valor for c in ' "\\\t'):
        return valor
    return '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _uid() -> int:
    return os.getuid() if hasattr(os, "getuid") else 0


def _tolerado(comando: list[str]) -> bool:
    """`launchctl bootout` falha quando o agente ainda não estava carregado: não é erro."""
    return comando[:2] == ["launchctl", "bootout"]


def _executar(argv: list[str]) -> int:
    try:
        return subprocess.run(argv, capture_output=True, timeout=TIMEOUT_COMANDO, check=False).returncode
    except (OSError, subprocess.TimeoutExpired):
        return -1
