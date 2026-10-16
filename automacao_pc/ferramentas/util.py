"""
Funções comuns: configuração, formatação de tamanhos e detalhes do Windows.
"""

import getpass
import json
import os
import platform
import socket
import shutil
import subprocess
import sys
from pathlib import Path

PASTA_BASE = Path(__file__).resolve().parent.parent
ARQUIVO_CONFIG = PASTA_BASE / "config.json"
EXEMPLO_CONFIG = PASTA_BASE / "config.exemplo.json"
PASTA_LOGS = PASTA_BASE / "logs"
WINDOWS = sys.platform == "win32"


def carregar_config(arquivo=ARQUIVO_CONFIG):
    """Lê o config.json. Na primeira vez, cria a partir do exemplo."""
    arquivo = Path(arquivo)
    if not arquivo.exists():
        shutil.copyfile(EXEMPLO_CONFIG, arquivo)
        print(f"Criei {arquivo} a partir do exemplo. Abra e ajuste para o seu PC.\n")
    with open(arquivo, encoding="utf-8") as f:
        return json.load(f)


def caminho(texto):
    """Converte "%USERPROFILE%/Downloads" ou "~/Downloads" em um Path."""
    return Path(os.path.expandvars(os.path.expanduser(str(texto))))


def tamanho_legivel(n):
    for unidade in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.0f} {unidade}" if unidade == "B" else f"{n:.1f} {unidade}"
        n /= 1024
    return f"{n:.1f} TB"


def processos_ativos():
    """Nomes (em minúsculas) dos executáveis em execução, ex.: {"chrome.exe"}."""
    try:
        if WINDOWS:
            saida = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"], capture_output=True,
                encoding="oem", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).stdout
            return {linha.split('","')[0].strip('"').lower()
                    for linha in saida.splitlines() if linha}
        saida = subprocess.run(["ps", "-A", "-o", "comm="],
                               capture_output=True, text=True).stdout
        return {os.path.basename(l.strip()).lower() for l in saida.splitlines() if l.strip()}
    except OSError:
        return set()


def eh_admin():
    if WINDOWS:
        import ctypes
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except OSError:
            return False
    return os.geteuid() == 0


def eh_link_ou_juncao(caminho_pasta):
    """Atalhos de pasta (symlink/junction) são pulados para não varrer a mesma coisa duas vezes."""
    if os.path.islink(caminho_pasta):
        return True
    isjunction = getattr(os.path, "isjunction", None)
    return bool(isjunction and isjunction(caminho_pasta))


# Atributos de arquivo do Windows que indicam "não mexa" ou "está só na nuvem".
_ATRIBUTO_SISTEMA = 0x4
_ATRIBUTO_OFFLINE = 0x1000
_ATRIBUTO_SO_NA_NUVEM = 0x400000   # OneDrive "arquivos sob demanda"


def arquivo_intocavel(st):
    """True para arquivos de sistema ou que só existem na nuvem (ler baixaria tudo)."""
    atributos = getattr(st, "st_file_attributes", 0)
    return bool(atributos & (_ATRIBUTO_SISTEMA | _ATRIBUTO_OFFLINE | _ATRIBUTO_SO_NA_NUVEM))


def tempo_ligado():
    """Há quanto tempo o PC está ligado, ex.: "2d 3h 15min"."""
    if WINDOWS:
        import ctypes
        ctypes.windll.kernel32.GetTickCount64.restype = ctypes.c_uint64
        segundos = ctypes.windll.kernel32.GetTickCount64() // 1000
    else:
        with open("/proc/uptime") as f:
            segundos = int(float(f.read().split()[0]))
    h, m = divmod(segundos // 60, 60)
    return f"{h // 24}d {h % 24}h {m}min" if h >= 24 else f"{h}h {m}min"


def memoria():
    """(total, usada) em bytes."""
    try:
        if WINDOWS:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_uint32), ("dwMemoryLoad", ctypes.c_uint32)] + [
                    (n, ctypes.c_uint64) for n in ("total", "livre", "a", "b", "c", "d", "e")]
            m = MEMORYSTATUSEX(dwLength=ctypes.sizeof(MEMORYSTATUSEX))
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.total, m.total - m.livre
        with open("/proc/meminfo") as f:
            info = {l.split(":")[0]: int(l.split()[1]) * 1024 for l in f}
        return info["MemTotal"], info["MemTotal"] - info["MemAvailable"]
    except (OSError, KeyError, ValueError):
        return 0, 0


def info_sistema():
    """Dados reais do PC para as telas de abertura."""
    from .discos import unidades
    total, usada = memoria()
    try:
        ligado = tempo_ligado()
    except OSError:
        ligado = "?"
    return {
        "usuario": getpass.getuser(),
        "maquina": socket.gethostname(),
        "sistema": f"{platform.system()} {platform.release()}",
        "nucleos": os.cpu_count() or 4,
        "memoria_total": total,
        "memoria_usada": usada,
        "ligado": ligado,
        "discos": [{"raiz": r, "nome": n, "total": t, "livre": l} for r, n, _, t, l in unidades()],
    }
