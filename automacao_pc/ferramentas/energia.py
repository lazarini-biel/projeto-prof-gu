"""
Desligar, reiniciar, hibernar, bloquear e cancelar — com aviso na tela.
Todas as funções devolvem (ok, mensagem).
"""

import subprocess

from .util import WINDOWS


def _shutdown(argumentos, minutos=None, mensagem=None):
    if not WINDOWS:
        return False, "Isso só funciona no Windows."
    cmd = ["shutdown", *argumentos]
    if minutos is not None:
        cmd += ["/t", str(max(0, int(float(minutos) * 60)))]
    if mensagem:
        cmd += ["/c", mensagem[:500]]
    r = subprocess.run(cmd, capture_output=True, encoding="oem", errors="replace",
                       creationflags=subprocess.CREATE_NO_WINDOW)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def desligar(minutos=1):
    ok, erro = _shutdown(["/s"], minutos, f"O PC vai desligar em {minutos} min (SPARTA).")
    return ok, f"Desligando em {minutos} min." if ok else erro


def reiniciar(minutos=1):
    ok, erro = _shutdown(["/r"], minutos, f"O PC vai reiniciar em {minutos} min (SPARTA).")
    return ok, f"Reiniciando em {minutos} min." if ok else erro


def hibernar():
    ok, erro = _shutdown(["/h"])
    return ok, "Hibernando." if ok else erro


def cancelar():
    ok, _ = _shutdown(["/a"])
    return ok, "Desligamento/reinício cancelado." if ok else "Não havia nada agendado."


def bloquear():
    if not WINDOWS:
        return False, "Isso só funciona no Windows."
    import ctypes
    ok = bool(ctypes.windll.user32.LockWorkStation())
    return ok, "Tela bloqueada." if ok else "Não consegui bloquear a tela."
