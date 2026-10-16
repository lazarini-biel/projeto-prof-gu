"""
"Central de Sistemas": um resumo bonito (vermelho) do seu PC — processador,
memória, discos, placa de vídeo, rede, bateria, tempo ligado etc.

Tudo é leitura (não muda nada). No Windows usa chamadas da API e, quando
precisa, comandos do próprio Windows (wmic/PowerShell), sempre com reserva
caso não existam.
"""

import os
import platform
import socket
import subprocess

from . import tema
from .util import WINDOWS, memoria, tempo_ligado, tamanho_legivel
from .discos import unidades

_SW_OCULTO = {"creationflags": 0x08000000} if WINDOWS else {}   # CREATE_NO_WINDOW


def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=6, **_SW_OCULTO)
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _powershell(expr):
    return _run(["powershell", "-NoProfile", "-Command", expr])


def processador():
    if WINDOWS:
        nome = os.environ.get("PROCESSOR_IDENTIFIER", "")
        marca = _run(["wmic", "cpu", "get", "name"])
        if marca:
            linhas = [l.strip() for l in marca.splitlines() if l.strip() and "Name" not in l]
            if linhas:
                return linhas[0]
        return nome or platform.processor() or "desconhecido"
    return platform.processor() or platform.machine()


def placa_video():
    if WINDOWS:
        saida = _run(["wmic", "path", "win32_VideoController", "get", "name"])
        linhas = [l.strip() for l in saida.splitlines() if l.strip() and "Name" not in l]
        if linhas:
            return ", ".join(linhas)
        ps = _powershell("(Get-CimInstance Win32_VideoController).Name -join ', '")
        if ps:
            return ps
    return "desconhecida"


def placa_mae():
    if WINDOWS:
        saida = _run(["wmic", "baseboard", "get", "Manufacturer,Product"])
        linhas = [l.strip() for l in saida.splitlines() if l.strip() and "Manufacturer" not in l]
        if linhas:
            return " ".join(linhas[0].split())
    return ""


def ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3)
        s.connect(("8.8.8.8", 80))   # não envia nada; só descobre a interface de saída
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "—"


def bateria():
    """(porcentagem, carregando) ou None se não houver bateria (desktop)."""
    if not WINDOWS:
        return None
    try:
        import ctypes

        class SPS(ctypes.Structure):
            _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                        ("BatteryLifePercent", ctypes.c_ubyte), ("Reserved1", ctypes.c_ubyte),
                        ("BatteryLifeTime", ctypes.c_uint32), ("BatteryFullLifeTime", ctypes.c_uint32)]
        s = SPS()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
            return None
        if s.BatteryFlag & 128 or s.BatteryLifePercent == 255:   # sem bateria
            return None
        return s.BatteryLifePercent, bool(s.ACLineStatus == 1)
    except OSError:
        return None


def coletar():
    total, usada = memoria()
    try:
        ligado = tempo_ligado()
    except OSError:
        ligado = "—"
    return {
        "usuario": os.environ.get("USERNAME") or os.environ.get("USER") or "—",
        "maquina": socket.gethostname(),
        "so": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": processador(),
        "nucleos": os.cpu_count() or 0,
        "gpu": placa_video(),
        "placa_mae": placa_mae(),
        "mem_total": total,
        "mem_usada": usada,
        "ligado": ligado,
        "ip": ip_local(),
        "bateria": bateria(),
        "discos": [(r, n, t, l) for r, n, _, t, l in unidades()],
    }


def _linha(rotulo, valor):
    tema.saida(f"  {tema.cor(rotulo + ':', tema.CINZA)} {tema.realce(valor)}")


def relatorio(saida=None):
    """Imprime o painel de informações do PC."""
    info = coletar()
    tema.cabecalho("Informações do PC", f"{info['usuario']}@{info['maquina']}")
    _linha("Sistema      ", info["so"])
    _linha("Processador  ", f"{info['cpu']}  ·  {info['nucleos']} núcleos")
    _linha("Placa de vídeo", info["gpu"])
    if info["placa_mae"]:
        _linha("Placa-mãe    ", info["placa_mae"])
    if info["mem_total"]:
        frac = info["mem_usada"] / info["mem_total"]
        tema.saida(f"  {tema.cor('Memória      :', tema.CINZA)} "
                   f"{tema.barra(frac, 24, aviso=frac > 0.9)} "
                   f"{tema.realce(f'{tamanho_legivel(info["mem_usada"])} / {tamanho_legivel(info["mem_total"])}')}"
                   f" {tema.cor(f'({frac:.0%})', tema.CINZA)}")
    _linha("Ligado há    ", info["ligado"])
    _linha("IP local     ", info["ip"])
    if info["bateria"]:
        pct, carregando = info["bateria"]
        estado = "carregando ⚡" if carregando else "na bateria"
        tema.saida(f"  {tema.cor('Bateria      :', tema.CINZA)} "
                   f"{tema.barra(pct / 100, 24, aviso=pct < 20)} "
                   f"{tema.realce(f'{pct}%')} {tema.cor(estado, tema.CINZA)}")

    tema.saida()
    tema.saida(tema.cor("  DISCOS", tema.VIVO))
    for raiz, nome, total, livre in info["discos"]:
        if not total:
            continue
        uso = 1 - livre / total
        rotulo = f"{raiz.rstrip(chr(92)):<4} {nome[:14]:<14}"
        tema.saida(f"  {tema.cor(rotulo, tema.CINZA)} {tema.barra(uso, 22, aviso=uso > 0.9)} "
                   f"{tema.realce(f'{uso:5.0%}')}  "
                   f"{tema.cor('livre', tema.CINZA)} {tema.realce(tamanho_legivel(livre))} "
                   f"{tema.cor('de ' + tamanho_legivel(total), tema.CINZA)}")


def top(saida=None, n=15):
    """Mini-htop: uso de CPU/RAM e os processos que mais consomem memória."""
    from .util import cpu_percent, processos_detalhados
    cpu = cpu_percent(0.2)
    total, usada = memoria()
    mem_frac = usada / total if total else 0
    tema.cabecalho("Top processos", "uso do PC agora")
    tema.saida(f"  {tema.cor('CPU', tema.CINZA)}  {tema.barra(cpu / 100, 30, aviso=cpu > 90)} "
               f"{tema.realce(f'{cpu:4.1f}%')}")
    tema.saida(f"  {tema.cor('RAM', tema.CINZA)}  {tema.barra(mem_frac, 30, aviso=mem_frac > 0.9)} "
               f"{tema.realce(f'{mem_frac*100:4.1f}%')}  "
               f"{tema.cor(f'{tamanho_legivel(usada)} / {tamanho_legivel(total)}', tema.CINZA)}")
    tema.saida()
    tema.saida(tema.cor(f"  {'PID':>7}  {'MEM%':>5}  {'MEMÓRIA':>9}  PROGRAMA", tema.VIVO))
    for pid, nome, mem in processos_detalhados(n):
        pct = mem / total * 100 if total else 0
        tema.saida(f"  {tema.cor(f'{pid:>7}', tema.CINZA)}  {tema.realce(f'{pct:4.1f}%')}  "
                   f"{tema.realce(f'{tamanho_legivel(mem):>9}')}  {nome}")


# Processos do sistema que NUNCA são oferecidos para fechar (quebraria o Windows).
_CRITICOS = {
    "system", "system idle process", "registry", "memory compression", "idle",
    "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe",
    "smss.exe", "svchost.exe", "dwm.exe", "fontdrvhost.exe", "explorer.exe",
    "ctfmon.exe", "python.exe", "pythonw.exe", "conhost.exe", "sihost.exe",
    "taskhostw.exe", "runtimebroker.exe", "shellexperiencehost.exe",
    "systemd", "init", "kthreadd", "bash", "sh",
}
# Apps de segundo plano que costumam ser "fecháveis" sem dó (sugestão).
_DESNECESSARIOS = {
    "googleupdate.exe", "onedrive.exe", "spotify.exe", "discord.exe", "teams.exe",
    "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe", "skype.exe",
    "cortana.exe", "yourphone.exe", "gameoverlayui.exe", "msedge.exe",
    "widgets.exe", "searchapp.exe", "spotifywebhelper.exe", "razer central.exe",
    "nvidia web helper.exe", "adobe desktop service.exe", "acrotray.exe",
}


def _matar(pid):
    try:
        if WINDOWS:
            r = subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"],
                               capture_output=True, **_SW_OCULTO)
            return r.returncode == 0
        os.kill(pid, 15)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def fechar(saida=None, entrada=input, n=22):
    """Lista processos (poupando os do sistema) e fecha os que você escolher."""
    from .util import processos_detalhados, memoria
    total, _ = memoria()
    candidatos = [(pid, nome, mem) for pid, nome, mem in processos_detalhados(60)
                  if nome.lower() not in _CRITICOS][:n]
    tema.cabecalho("Liberar memória / fechar processos",
                   "escolha o que encerrar — os processos do Windows ficam de fora")
    if not candidatos:
        tema.saida("Nada para mostrar.")
        return
    tema.saida(tema.cor(f"  {'#':>2}  {'PID':>7}  {'MEMÓRIA':>9}  PROGRAMA", tema.VIVO))
    for i, (pid, nome, mem) in enumerate(candidatos, 1):
        dica = tema.cor("  ⚠ dá para fechar", tema.ROSA) if nome.lower() in _DESNECESSARIOS else ""
        pct = mem / total * 100 if total else 0
        tema.saida(f"  {tema.cor(f'{i:>2}', tema.VIVO)}  {tema.cor(f'{pid:>7}', tema.CINZA)}  "
                   f"{tema.realce(f'{tamanho_legivel(mem):>9}')}  {nome}{dica} "
                   f"{tema.cor(f'({pct:.1f}%)', tema.CINZA)}")
    resp = entrada("\nQuais fechar? (números separados por espaço, Enter cancela): ").strip()
    if not resp:
        tema.saida("Cancelado.")
        return
    escolhidos = []
    for parte in resp.replace(",", " ").split():
        if parte.isdigit() and 1 <= int(parte) <= len(candidatos):
            escolhidos.append(candidatos[int(parte) - 1])
    if not escolhidos:
        tema.saida("Nenhum número válido.")
        return
    nomes = ", ".join(nome for _, nome, _ in escolhidos)
    if entrada(f"Fechar {len(escolhidos)} ({nomes})? (s/n) ").strip().lower() not in ("s", "sim"):
        tema.saida("Cancelado.")
        return
    ok = 0
    for pid, nome, _ in escolhidos:
        if _matar(pid):
            ok += 1
            tema.saida(tema.cor(f"  ✓ fechado: {nome} (PID {pid})", tema.ROSA))
        else:
            tema.saida(tema.cor(f"  ! não consegui fechar {nome} (PID {pid}) — tente como administrador", tema.VIVO))
    tema.saida(tema.bom(f"\n{ok} processo(s) encerrados."))


def atualizar(aplicar=False, saida=None):
    """Atualiza todos os programas via winget (gerenciador do Windows)."""
    tema.cabecalho("Atualizar programas", "usa o winget (gerenciador do Windows)")
    if not WINDOWS:
        tema.saida(tema.cor("O winget é do Windows.", tema.CINZA))
        return
    if not _run(["where", "winget"]):
        tema.saida(tema.cor("winget não encontrado. Ele vem no Windows 10/11 atuais; "
                            "se faltar, instale o 'Instalador de Aplicativo' pela Microsoft Store.", tema.VIVO))
        return
    if not aplicar:
        tema.saida(tema.cor("Programas com atualização disponível:\n", tema.CINZA))
        lista = _run(["winget", "upgrade", "--include-unknown"]) or "(nada a mostrar)"
        for linha in lista.splitlines():
            tema.saida("  " + linha)
        tema.saida(tema.cor("\nPara atualizar tudo: py pc.py atualizar --executar", tema.ROSA))
        return
    tema.saida(tema.cor("Atualizando tudo... (pode demorar; acompanhe abaixo)\n", tema.CINZA))
    try:
        subprocess.run(["winget", "upgrade", "--all", "--silent",
                        "--accept-source-agreements", "--accept-package-agreements"],
                       **_SW_OCULTO)
    except (OSError, subprocess.SubprocessError) as erro:
        tema.saida(tema.cor(f"Erro ao rodar o winget: {erro}", tema.VIVO))
        return
    tema.saida(tema.bom("\nPronto."))


def temperaturas():
    """Lista de (sensor, °C). Vazia se o PC não expõe temperatura ao Windows."""
    if not WINDOWS:
        return []
    temps = []
    # 1) termozona ACPI (quase sempre existe, mas costuma ser só a placa)
    out = _powershell("(Get-CimInstance -Namespace root/WMI "
                      "-ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue)."
                      "CurrentTemperature")
    for linha in out.splitlines():
        linha = linha.strip()
        if linha.isdigit():
            c = int(linha) / 10 - 273.15
            if 10 < c < 120:
                temps.append(("Placa/ACPI", round(c, 1)))
    # 2) LibreHardwareMonitor / OpenHardwareMonitor (se estiver aberto): CPU/GPU reais
    for ns in ("root/LibreHardwareMonitor", "root/OpenHardwareMonitor"):
        out = _powershell(f"Get-CimInstance -Namespace {ns} -ClassName Sensor "
                          "-ErrorAction SilentlyContinue | Where-Object {{$_.SensorType -eq 'Temperature'}} "
                          "| ForEach-Object {{ \"$($_.Name)=$($_.Value)\" }}")
        for linha in out.splitlines():
            if "=" in linha:
                nome, _, val = linha.partition("=")
                try:
                    temps.append((nome.strip(), round(float(val), 1)))
                except ValueError:
                    continue
        if temps:
            break
    return temps


def temperatura_cmd():
    tema.cabecalho("Temperaturas", "CPU/GPU/placa (quando o PC informa)")
    temps = temperaturas()
    if not temps:
        tema.saida(tema.cor("O Windows não está informando temperaturas detalhadas.", tema.CINZA))
        tema.saida(tema.cor("Para ver CPU/GPU com precisão, abra o LibreHardwareMonitor "
                            "(gratuito) e rode este comando de novo.", tema.CINZA))
        return
    for sensor, c in temps:
        tema.saida(f"  {tema.cor(f'{sensor[:26]:<26}', tema.CINZA)} "
                   f"{tema.barra(min(1.0, c / 100), 20, aviso=c >= 80)} {tema.realce(f'{c:.0f}°C')}")
