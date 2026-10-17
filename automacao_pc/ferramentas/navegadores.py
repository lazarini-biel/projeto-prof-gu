"""
Encontra os navegadores instalados e abre sites em um navegador específico.
Usado pela central (abrir sites ao ligar o PC) e pelo cofre de senhas.
"""

import os
import subprocess
import webbrowser
from pathlib import Path

from .util import WINDOWS

# chave: (nome, processo, caminhos comuns de instalação)
NAVEGADORES = {
    "chrome": ("Google Chrome", "chrome.exe", [
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"]),
    "edge": ("Microsoft Edge", "msedge.exe", [
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"]),
    "firefox": ("Firefox", "firefox.exe", [
        r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
        r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"]),
    "brave": ("Brave", "brave.exe", [
        r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"]),
    "opera": ("Opera", "opera.exe", [r"%LOCALAPPDATA%\Programs\Opera\launcher.exe"]),
    "operagx": ("Opera GX", "opera.exe", [r"%LOCALAPPDATA%\Programs\Opera GX\launcher.exe"]),
    "vivaldi": ("Vivaldi", "vivaldi.exe", [r"%LOCALAPPDATA%\Vivaldi\Application\vivaldi.exe"]),
}


def _pelo_registro(executavel):
    """Procura em "App Paths" do registro (onde instaladores registram o .exe)."""
    import winreg
    chave = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{executavel}"
    for raiz in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(raiz, chave) as k:
                valor = winreg.QueryValue(k, None)
                if valor and os.path.isfile(valor.strip('"')):
                    return Path(valor.strip('"'))
        except OSError:
            continue
    return None


def localizar(chave):
    if not WINDOWS or chave not in NAVEGADORES:
        return None
    _, processo, caminhos = NAVEGADORES[chave]
    for c in caminhos:
        c = os.path.expandvars(c)
        if os.path.isfile(c):
            return Path(c)
    return _pelo_registro(processo) if not chave.startswith("opera") else None


def instalados():
    """[{"chave": "chrome", "nome": "Google Chrome"}, ...]"""
    return [{"chave": k, "nome": v[0]} for k, v in NAVEGADORES.items() if localizar(k)]


def nome_pelo_processo(processo):
    processo = (processo or "").lower()
    for nome, exe, _ in NAVEGADORES.values():
        if exe == processo:
            return nome
    return None


def abrir(urls, navegador=None):
    """Abre uma ou várias URLs. Sem navegador (ou não encontrado), usa o padrão do sistema."""
    if isinstance(urls, str):
        urls = [urls]
    urls = [u if "://" in u else "https://" + u for u in urls if u]
    if not urls:
        return
    exe = localizar(navegador) if navegador else None
    if exe:
        subprocess.Popen([str(exe), *urls], close_fds=True)
    else:
        for u in urls:
            webbrowser.open(u)
