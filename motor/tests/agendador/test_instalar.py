"""T-08.06: instalação do agendador local por sistema operacional (D-08, D-30).

Nenhum teste aplica no sistema de verdade: `home` é temporário e `executar` é um espião, então
nem launchctl, nem schtasks, nem systemctl rodam. O ~/Library/LaunchAgents real é conferido
antes e depois.
"""
import json
import plistlib
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from expxmedia.agendador import instalar
from expxmedia.ambiente.verificar import Verificador

EXE = "/opt/ferramentas/bin/expxmedia-motor"
LAUNCH_AGENTS_REAL = Path.home() / "Library" / "LaunchAgents"


def _foto_real():
    return sorted(p.name for p in LAUNCH_AGENTS_REAL.iterdir()) if LAUNCH_AGENTS_REAL.is_dir() else None


class Espiao:
    def __init__(self, codigo=0):
        self.chamadas = []
        self.codigo = codigo

    def __call__(self, argv, **kw):
        self.chamadas.append(list(argv))
        return self.codigo


@pytest.fixture
def casa(tmp_path):
    return tmp_path / "casa"


# --- integração -------------------------------------------------------------------------

def test_macos_sem_aplicar_devolve_o_plist_e_nao_escreve_em_launchagents(instalacao, casa):
    antes = _foto_real()
    espiao = Espiao()

    saida = instalar.instalar(instalacao, sistema="macos", executavel=EXE, home=casa, executar=espiao)

    assert saida["aplicado"] is False and saida["sistema"] == "macos"
    [arquivo] = saida["arquivos"]
    assert arquivo["destino"].startswith(str(casa / "Library" / "LaunchAgents"))
    assert arquivo["destino"].endswith(".plist")
    plist = plistlib.loads(arquivo["conteudo"].encode("utf-8"))
    assert plist["ProgramArguments"] == [EXE, "agendador", "rodar", "--raiz", str(instalacao.resolve())]
    assert plist["StartInterval"] == 60  # D-30: verifica a cada minuto
    assert plist["Label"] == Path(arquivo["destino"]).stem
    assert plist["WorkingDirectory"] == str(instalacao.resolve())
    assert "KeepAlive" not in plist  # disparo periódico, não processo eterno
    assert "PATH" in plist["EnvironmentVariables"]  # o launchd roda com ambiente pelado
    assert plist["StandardOutPath"].startswith(str(instalacao.resolve() / ".expxmedia"))
    # nada foi aplicado
    assert espiao.chamadas == []
    assert not casa.exists()
    assert not (instalacao / ".expxmedia" / "agendador.json").exists()
    assert _foto_real() == antes
    # o comando que aplicaria aparece para a pessoa conferir
    assert any(c[:2] == ["launchctl", "bootstrap"] for c in saida["comandos"])


def test_macos_com_aplicar_escreve_o_plist_carrega_e_grava_o_marcador(instalacao, casa):
    antes = _foto_real()
    espiao = Espiao()

    saida = instalar.instalar(instalacao, sistema="macos", executavel=EXE, home=casa, aplicar=True, executar=espiao)

    destino = Path(saida["arquivos"][0]["destino"])
    assert destino.parent == casa / "Library" / "LaunchAgents" and destino.is_file()
    assert plistlib.loads(destino.read_bytes())["StartInterval"] == 60
    assert ["launchctl", "bootstrap", f"gui/{instalar._uid()}", str(destino)] in espiao.chamadas
    marcador = json.loads((instalacao / ".expxmedia" / "agendador.json").read_text(encoding="utf-8"))
    assert marcador["instalado"] is True and marcador["sistema"] == "macos"
    assert marcador["instalado_em"][:4].isdigit() and marcador["instalado_em"][-6] in "+-"
    assert str(instalacao) not in json.dumps(marcador)  # M9: nenhum caminho absoluto no marcador
    # o verificador do ambiente passa a enxergar o agendador
    assert Verificador(instalacao)._marcador("agendador_local") is True
    assert _foto_real() == antes


def test_falha_ao_carregar_nao_grava_marcador(instalacao, casa):
    with pytest.raises(instalar.ErroInstalacao):
        instalar.instalar(instalacao, sistema="macos", executavel=EXE, home=casa, aplicar=True,
                          executar=Espiao(codigo=5))
    assert not (instalacao / ".expxmedia" / "agendador.json").exists()


# --- funcional --------------------------------------------------------------------------

def test_linux_gera_service_e_timer_de_minuto_com_instrucao_de_linger(instalacao, casa):
    espiao = Espiao()

    saida = instalar.instalar(instalacao, sistema="linux", executavel=EXE, home=casa, executar=espiao,
                              systemd=True)

    assert espiao.chamadas == [] and not casa.exists()
    por_extensao = {Path(a["destino"]).suffix: a for a in saida["arquivos"]}
    assert set(por_extensao) == {".service", ".timer"}
    for a in saida["arquivos"]:
        assert Path(a["destino"]).parent == casa / ".config" / "systemd" / "user"
    servico = por_extensao[".service"]["conteudo"]
    timer = por_extensao[".timer"]["conteudo"]
    assert "[Service]" in servico and "Type=oneshot" in servico
    assert f'ExecStart={EXE} agendador rodar --raiz {instalacao.resolve()}' in servico
    assert "[Timer]" in timer
    assert "OnCalendar=*-*-* *:*:00" in timer  # de minuto em minuto
    assert "Persistent=false" in timer  # disparo perdido não vira publicação atrasada (D-30)
    assert f"Unit={Path(por_extensao['.service']['destino']).name}" in timer
    assert "WantedBy=timers.target" in timer
    texto = " ".join(saida["instrucoes"])
    assert "loginctl enable-linger" in texto
    assert ["systemctl", "--user", "enable", "--now", Path(por_extensao[".timer"]["destino"]).name] in saida["comandos"]


def test_linux_com_caminho_com_espaco_aspas_no_execstart(tmp_path, casa):
    raiz = tmp_path / "minha instalacao"
    raiz.mkdir()
    saida = instalar.gerar(raiz, sistema="linux", executavel=EXE, home=casa, systemd=True)
    servico = next(a["conteudo"] for a in saida["arquivos"] if a["destino"].endswith(".service"))
    assert f'--raiz "{raiz.resolve()}"' in servico


def test_linux_sem_systemd_cai_para_cron(instalacao, casa):
    saida = instalar.gerar(instalacao, sistema="linux", executavel=EXE, home=casa, systemd=False)
    assert saida["sistema"] == "linux_cron" and saida["arquivos"] == []
    linha = saida["cron"]
    assert linha.startswith("* * * * * ")
    assert f"{EXE} agendador rodar --raiz {instalacao.resolve()}" in linha


def test_windows_gera_tarefa_a_cada_minuto_ao_fazer_logon(instalacao, casa):
    espiao = Espiao()

    saida = instalar.instalar(instalacao, sistema="windows", executavel=EXE, home=casa, executar=espiao)

    assert espiao.chamadas == []
    [arquivo] = saida["arquivos"]
    raiz_xml = ET.fromstring(arquivo["conteudo"].encode("utf-16"))  # o XML declara UTF-16
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    gatilho = raiz_xml.find("t:Triggers/t:LogonTrigger", ns)
    assert gatilho is not None
    assert gatilho.find("t:Repetition/t:Interval", ns).text == "PT1M"
    assert raiz_xml.find("t:Settings/t:MultipleInstancesPolicy", ns).text == "IgnoreNew"
    acao = raiz_xml.find("t:Actions/t:Exec", ns)
    assert acao.find("t:Command", ns).text == EXE
    assert acao.find("t:Arguments", ns).text == f'agendador rodar --raiz "{instalacao.resolve()}"'
    [comando] = [c for c in saida["comandos"] if c[0] == "schtasks"]
    assert comando[:2] == ["schtasks", "/create"] and "/xml" in comando and "/f" in comando
    assert comando[comando.index("/xml") + 1] == arquivo["destino"]


def test_detecta_o_sistema_pela_plataforma(monkeypatch):
    for plataforma, esperado in (("Darwin", "macos"), ("Windows", "windows"), ("Linux", "linux")):
        monkeypatch.setattr(instalar.platform, "system", lambda p=plataforma: p)
        assert instalar.detectar_sistema() == esperado
    monkeypatch.setattr(instalar.platform, "system", lambda: "Plan9")
    with pytest.raises(instalar.ErroInstalacao):
        instalar.detectar_sistema()


def test_rotulo_e_estavel_por_instalacao_e_distinto_entre_instalacoes(tmp_path, casa):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    ra = instalar.gerar(a, sistema="macos", executavel=EXE, home=casa)["rotulo"]
    assert ra == instalar.gerar(a, sistema="macos", executavel=EXE, home=casa)["rotulo"]
    assert ra != instalar.gerar(b, sistema="macos", executavel=EXE, home=casa)["rotulo"]


def test_sem_executavel_encontrado_e_erro_com_orientacao(instalacao, casa, monkeypatch):
    monkeypatch.setattr(instalar.shutil, "which", lambda nome: None)
    monkeypatch.setattr(instalar, "_candidato_ao_lado", lambda: None)
    with pytest.raises(instalar.ErroInstalacao, match="expxmedia-motor"):
        instalar.gerar(instalacao, sistema="macos", home=casa)
