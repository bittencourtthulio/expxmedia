# Agendador local residente por sistema operacional (`agendar` via `meta_graph`)

O contrato exige um programa Python do motor que fica residente e publica no horário, instalado
por `/expxmedia:ambiente` e pelo `doctor` como LaunchAgent (macOS), tarefa do Agendador de Tarefas
ao logon (Windows) ou serviço de usuário do systemd, com cron como alternativa (Linux)
(`ExpxMedia/docs/contrato/CONTRATO-capacidades.md:66-87`). Nenhum projeto de origem tem agendador
residente: o que existe é `Instagram-Carrosseis/rotina.sh`, chamado pelo cron, com trava por
diretório.

## Contrato de entrada

**Comportamento exigido pelo contrato** (`CONTRATO-capacidades.md:78-87`):
- lê publicações `agendada` com `provedor: meta_graph` nos `peca.json`;
- no horário, abre a URL pública temporária e chama a Graph API;
- grava o resultado na peça e no rastro (`publicacao_concluida` / `publicacao_falhou`);
- ao voltar de um período desligado, **não publica atrasado**: marca `falhou` com motivo;
- sem o agendador instalado, `agendar` via `meta_graph` não está habilitada.

**macOS — launchd** (documentação Apple):
- Agente por usuário em `~/Library/LaunchAgents` (também `/Library/LaunchAgents`, `/System/Library/LaunchAgents`).
- Chaves obrigatórias: `Label` e `ProgramArguments`.
- Execução periódica: `StartInterval` (segundos) ou `StartCalendarInterval` (dicionário; chave ausente = curinga).
- `RunAtLoad` (padrão false), `KeepAlive` (padrão false), `EnvironmentVariables`, `StandardOutPath`.
- O processo **não pode se daemonizar** (`fork`/`exec`/`daemon`), senão o launchd o considera morto.

**Windows — `schtasks /create`** (Microsoft Learn):
- `/sc ONLOGON` (roda quando **qualquer** usuário faz logon; com `/ru`, quando aquele usuário faz logon) ou `/sc MINUTE /mo <1–1439>`.
- `/tn` nome único (≤ 238 caracteres), `/tr` caminho do programa (≤ 262 caracteres), `/ru`, `/it` (só quando o usuário está logado), `/rl LIMITED|HIGHEST` (padrão LIMITED), `/delay mmmm:ss` (só ONSTART, ONLOGON, ONEVENT), `/f` (sobrescreve sem aviso).
- "Each task runs only one program": para vários comandos, um `.bat`.

**Linux — systemd de usuário** (man pages systemd):
- Timer: `OnCalendar=` (relógio), `OnBootSec=`/`OnUnitActiveSec=` (relativos), `Unit=` (padrão: serviço de mesmo nome), `Persistent=`, `AccuracySec=`, `WakeSystem=`.
- Serviço: `Type=simple` implícito quando há `ExecStart=`; `Restart=` (`no` padrão, `on-failure`, `always`…), `RestartSec=` (padrão 100 ms).
- Sem sessão aberta, o gerenciador de usuário só existe com `loginctl enable-linger`: "a user manager is spawned for the user at boot and kept around after logouts".
- Alternativa: cron (padrão hoje em `Instagram-Carrosseis/rotina.sh:2-4`).

**Padrão de origem (`Instagram-Carrosseis/rotina.sh`)** a reaproveitar:
- monta ambiente porque "o cron roda com ambiente pelado (sem PATH, sem pasta)" (`rotina.sh:2-3,31-39`);
- exporta `USER`/`LOGNAME` porque o login do Claude mora no Keychain e "launchd e outros agendadores nem sempre" definem `USER` (`rotina.sh:34-36`);
- trava por rotina com `mkdir` atômico, removida ao sair por `trap`, e trava com mais de 120 min é descartada (`rotina.sh:45-53`);
- log por dia em `planejamento/logs/AAAA-MM-DD_<rotina>.log` (`rotina.sh:41-43`);
- atalho que não acorda o modelo se nada está pendente (`rotina.sh:55-62`).

## Contrato de saída

- Instalação: arquivo `.plist` (macOS), tarefa registrada (Windows), `.service` + `.timer` em `~/.config/systemd/user` (Linux). Local exato dos arquivos de unidade de usuário: NÃO DOCUMENTADO na página lida (man `systemd.timer` só cita o "per-user service manager").
- Execução: eventos `publicacao_concluida` / `publicacao_falhou` com `origem: rotina` (`ExpxMedia/docs/contrato/CONTRATO-estado-eventos.md:44-58,70`) e atualização de `publicacoes[]` no `peca.json`.
- Log: a origem grava em arquivo por dia (`rotina.sh:43`); no launchd, `StandardOutPath`.

## Limites e cotas

| Item | Valor | Fonte |
|---|---|---|
| launchd: espaçamento mínimo entre execuções | 10 s por padrão (`ThrottleInterval`) | man `launchd.plist(5)` |
| launchd: tempo mínimo vivo | "do not shut down for at least 10 seconds after launch" | Apple, Creating Launch Daemons and Agents |
| launchd `StartCalendarInterval` com Mac dormindo | roda ao acordar; vários disparos perdidos viram **um** | man `launchd.plist(5)` |
| launchd `StartInterval` com Mac dormindo | o disparo é perdido | man `launchd.plist(5)` |
| launchd com Mac desligado | NÃO DOCUMENTADO | man `launchd.plist(5)` |
| schtasks `/mo` em MINUTE | 1 a 1439 min, padrão 1 | Microsoft Learn |
| schtasks limite de execução padrão | exemplo de consulta mostra "Stop Task If Runs X Hours and X Mins: 72:0" — limite padrão para processo residente não afirmado no texto | Microsoft Learn |
| systemd `AccuracySec=` | padrão 1 min | man `systemd.timer(5)` |
| systemd `Persistent=true` | dispara **imediatamente** se um disparo foi perdido enquanto inativo | man `systemd.timer(5)` |
| systemd `RestartSec=` | padrão 100 ms | man `systemd.service(5)` |
| Trava da rotina de origem | expira em 120 min | `rotina.sh:46-48` |
| Trava de execução do plano | expira em 50 min (`trava_expira_min`) | `Instagram-Carrosseis/planejar.py:43,655-660` |
| Janela de atraso tolerada antes de declarar `falhou` | NÃO DOCUMENTADO no contrato | `CONTRATO-capacidades.md:84-85` |

## Erros conhecidos e tratamento

- launchd: processo que sai rápido demais é tratado como crash e pode ser suspenso (Apple).
- schtasks: não confere caminho do programa nem senha; tarefa com caminho errado é criada e não roda; troca de senha da conta faz a tarefa parar (Microsoft Learn, Remarks). Teste com `schtasks /run` e log em `SchedLgU.txt`.
- systemd de usuário sem linger: serviço para no logout (loginctl).
- Origem: execução concorrente sai em silêncio com linha no log (`rotina.sh:49-52`); código de saída do comando fica no log (`rotina.sh:74-77`).
- Origem, plano: vaga de dia passado vira `perdido`; vaga atrasada é **empurrada** para mais tarde no mesmo dia até 22:30 (`Instagram-Carrosseis/planejar.py:585,592-609,621-627`).

## Riscos para a nossa implementação

1. **Recuperação automática contradiz o contrato.** `Persistent=true` (systemd) e o coalescimento do `StartCalendarInterval` (launchd) disparam ao voltar; o plano de origem **reagenda** vaga atrasada (`planejar.py:592-609`). O contrato manda **não** publicar atrasado (`CONTRATO-capacidades.md:84-85`). A regra tem de viver no programa (comparar `agendada_para` com agora e uma tolerância), não no agendador do SO. Tolerância: NÃO DOCUMENTADO, precisa de decisão.
2. **Residente vs. periódico**: o contrato diz "fica rodando" (`:69-70`). Com launchd, `KeepAlive` mantém vivo; com Windows ONLOGON, só roda depois do logon e pode haver limite de execução; com systemd, exige linger. Um disparo periódico por minuto (`StartInterval=60`, `/sc MINUTE`, `OnCalendar=minutely`) evita processo eterno mas perde disparos com o Mac dormindo (`StartInterval`).
3. **Máquina desligada ou dormindo**: nenhum dos três publica; `WakeSystem=` (Linux) acorda de suspensão, e equivalentes em macOS/Windows: NÃO DOCUMENTADO nesta ingestão.
4. **Ambiente pelado**: caminhos de Python e Node hardcoded na origem (`rotina.sh:32-33`), `TZ="America/Sao_Paulo"` e `LANG=pt_BR` fixos (`rotina.sh:37`) → fuso da Alma (`empresa.fuso`, M5) e caminho do interpretador detectado na instalação. `rotina.sh:74` roda `claude -p ... --permission-mode bypassPermissions`: o agendador de publicação não deve depender do modelo.
5. **Trava por `mkdir`** é portátil; a trava do plano por mtime (`planejar.py:655-660`) não é atômica (checa e depois escreve).
6. **Concorrência com o painel e o motor**: o agendador altera `peca.json`; precisa da escrita atômica (M15).
7. **Acoplamento de pessoa**: `rotina.sh:13` cita o dono pelo nome; o guard cita-o como quem liga a publicação automática (`Instagram-Carrosseis/.claude/hooks/publicacao/pre-bash-guard.sh:13-14`).
8. Fontes de launchd: a página Apple é do arquivo histórico ("Documentation Archive"); o `launchd.plist(5)` foi lido de espelho da man page, não do site da Apple.

## Fonte

- `ExpxMedia/docs/contrato/CONTRATO-capacidades.md:58-87`
- `Instagram-Carrosseis/rotina.sh:1-77`
- `Instagram-Carrosseis/planejar.py:37-46,584-660`
- Apple, Creating Launch Daemons and Agents — https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html (acesso 2026-09-24)
- `launchd.plist(5)` (espelho da man page do Xcode) — https://keith.github.io/xcode-man-pages/launchd.plist.5.html (acesso 2026-09-24)
- Microsoft Learn, `schtasks create` — https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create (acesso 2026-09-24)
- `systemd.timer(5)` — https://man7.org/linux/man-pages/man5/systemd.timer.5.html (acesso 2026-09-24; freedesktop.org devolveu 403)
- `systemd.service(5)` — https://man7.org/linux/man-pages/man5/systemd.service.5.html (acesso 2026-09-24)
- `loginctl(1)` — https://man7.org/linux/man-pages/man1/loginctl.1.html (acesso 2026-09-24)
