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
