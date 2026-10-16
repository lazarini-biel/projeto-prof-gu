"""
Funções comuns: configuração, formatação de tamanhos e detalhes do Windows.
"""

import json
import os
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
