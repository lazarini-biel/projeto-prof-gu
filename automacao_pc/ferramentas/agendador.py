"""
Cria as tarefas do Agendador de Tarefas do Windows a partir do config.

Cada item de "agendamentos" vira uma tarefa na pasta "AutomacaoPC" do
Agendador, rodando `pythonw pc.py <comando>` (sem janela preta). As tarefas
são geradas em XML, o que permite:
  - rodar mesmo no notebook fora da tomada;
  - recuperar uma execução perdida (PC desligado no horário) — exceto
    comandos de energia, para não desligar o PC assim que você o ligar;
  - rodar o bot do Telegram sem limite de tempo.
"""

import ctypes
import datetime
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from .util import PASTA_BASE, WINDOWS, eh_admin

PASTA_AGENDADOR = "AutomacaoPC"
DIAS = {"dom": "Sunday", "seg": "Monday", "ter": "Tuesday", "qua": "Wednesday",
        "qui": "Thursday", "sex": "Friday", "sab": "Saturday"}


def usuario_atual():
    return f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}".lstrip("\\")


def _pythonw():
    exe = Path(sys.executable)
    sem_janela = exe.with_name("pythonw.exe")
    return sem_janela if sem_janela.exists() else exe


def _gatilho(item, usuario):
    quando = item.get("quando", "diario")
    hora = item.get("hora", "12:00")
    inicio = f"{datetime.date.today().isoformat()}T{hora}:00"
    if quando == "logon":
        atraso = int(item.get("atraso_segundos", 30))
        return (f"<LogonTrigger><Enabled>true</Enabled><UserId>{escape(usuario)}</UserId>"
                f"<Delay>PT{atraso}S</Delay></LogonTrigger>")
    if quando == "diario":
        return (f"<CalendarTrigger><StartBoundary>{inicio}</StartBoundary><Enabled>true</Enabled>"
                "<ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>")
    if quando == "semanal":
        dias = item.get("dias", ["dom"])
        try:
            tags = "".join(f"<{DIAS[d.lower()[:3]]} />" for d in dias)
        except KeyError as erro:
            raise ValueError(f"Dia inválido em '{item.get('nome')}': {erro}. Use dom, seg, ter...")
        return (f"<CalendarTrigger><StartBoundary>{inicio}</StartBoundary><Enabled>true</Enabled>"
                f"<ScheduleByWeek><DaysOfWeek>{tags}</DaysOfWeek><WeeksInterval>1</WeeksInterval>"
                "</ScheduleByWeek></CalendarTrigger>")
    if quando == "a_cada_horas":
        horas = int(item.get("horas", 1))
        return (f"<TimeTrigger><Repetition><Interval>PT{horas}H</Interval>"
                f"<StopAtDurationEnd>false</StopAtDurationEnd></Repetition>"
                f"<StartBoundary>{inicio}</StartBoundary><Enabled>true</Enabled></TimeTrigger>")
    raise ValueError(f"'quando' inválido em '{item.get('nome')}': {quando} "
                     "(use logon, diario, semanal ou a_cada_horas)")


def gerar_xml(item, usuario, pythonw=None, script=None):
    pythonw = pythonw or _pythonw()
    script = script or PASTA_BASE / "pc.py"
    comando = item["comando"]
    energia = comando.split()[0] == "energia"
    recuperar = item.get("recuperar_se_perdida", not energia)
    nivel = "HighestAvailable" if item.get("admin") else "LeastPrivilege"
    argumentos = f'"{script}" {comando}'
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>{escape(item.get('nome', comando))} — criado por AutomacaoPC</Description></RegistrationInfo>
  <Triggers>{_gatilho(item, usuario)}</Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{escape(usuario)}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>{nivel}</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>{str(recuperar).lower()}</StartWhenAvailable>
    <Enabled>true</Enabled>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(str(pythonw))}</Command>
      <Arguments>{escape(argumentos)}</Arguments>
      <WorkingDirectory>{escape(str(PASTA_BASE))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def _schtasks(*args):
    r = subprocess.run(["schtasks", *args], capture_output=True, encoding="oem",
                       errors="replace", creationflags=subprocess.CREATE_NO_WINDOW)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def _reabrir_como_admin(argumentos):
    """O Agendador exige administrador para tarefas "ao fazer logon"; pede o UAC."""
    params = " ".join(f'"{a}"' for a in [str(PASTA_BASE / "pc.py"), *argumentos])
    r = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params,
                                            str(PASTA_BASE), 1)
    return r > 32


def instalar(agendamentos, usuario=None, saida=print, pausar=False):
    if not WINDOWS:
        saida("O agendamento usa o Agendador de Tarefas do Windows.")
        return False
    usuario = usuario or usuario_atual()
    if not eh_admin():
        saida("Vou pedir permissão de administrador (o Windows exige para criar tarefas)...")
        if not _reabrir_como_admin(["agendar", "instalar", "--usuario", usuario, "--pausar"]):
            saida("Permissão negada. Nada foi criado.")
        return False

    criadas = 0
    for item in agendamentos:
        nome = f"{PASTA_AGENDADOR}\\{item['nome']}"
        if not item.get("ativo", True):
            _schtasks("/Delete", "/F", "/TN", nome)   # se existia, desativa
            continue
        try:
            xml = gerar_xml(item, usuario)
        except ValueError as erro:
            saida(f"  ! {erro}")
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-16") as f:
            f.write(xml)
        ok, msg = _schtasks("/Create", "/F", "/TN", nome, "/XML", f.name)
        os.unlink(f.name)
        saida(f"  {'✓' if ok else '!'} {item['nome']}" + ("" if ok else f": {msg}"))
        criadas += ok
    saida(f"\n{criadas} tarefa(s) ativas em Agendador de Tarefas > {PASTA_AGENDADOR}.")
    if pausar:
        input("\nPressione Enter para fechar...")
    return True


def listar(saida=print):
    if not WINDOWS:
        saida("Só no Windows.")
        return
    ok, texto = _schtasks("/Query", "/FO", "CSV", "/NH")
    tarefas = [l for l in texto.splitlines() if f"\\{PASTA_AGENDADOR}\\" in l]
    if not tarefas:
        saida("Nenhuma tarefa da AutomacaoPC instalada.")
    for linha in tarefas:
        nome, proxima, status = [c.strip('"') for c in linha.split('","')][:3]
        saida(f"  {nome.split(chr(92))[-1]:<32} próxima: {proxima:<22} {status}")


def remover(agendamentos, saida=print):
    if not WINDOWS:
        saida("Só no Windows.")
        return
    for item in agendamentos:
        ok, _ = _schtasks("/Delete", "/F", "/TN", f"{PASTA_AGENDADOR}\\{item['nome']}")
        if ok:
            saida(f"  removida: {item['nome']}")
