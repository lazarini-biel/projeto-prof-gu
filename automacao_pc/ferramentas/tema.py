"""
Tema visual (vermelho "hacker") para as saídas dos comandos no terminal.

Dá cor vermelha ao texto, cabeçalhos em caixa, barras coloridas e realces.
Usa cores ANSI de 24 bits (o Windows Terminal entende). `ativar()` liga as
cores no console clássico do Windows.
"""

import os
import sys

RESET = "\x1b[0m"
_COR = os.environ.get("SPARTA_SEM_COR") is None   # permite desligar via variável


def _rgb(r, g, b):
    return f"\x1b[38;2;{r};{g};{b}m" if _COR else ""


def _bg(r, g, b):
    return f"\x1b[48;2;{r};{g};{b}m" if _COR else ""


# paleta (igual à das aberturas)
VIVO = _rgb(255, 70, 105)
FORTE = _rgb(205, 34, 66)
MEDIO = _rgb(170, 28, 56)
ESCURO = _rgb(120, 24, 48)
CLARO = _rgb(255, 150, 170)
ROSA = _rgb(245, 92, 122)
CINZA = _rgb(120, 118, 126)
BRANCO = _rgb(255, 205, 212)
BG_FORTE = _bg(150, 20, 44)
_R = RESET if _COR else ""


def ativar():
    """Liga as cores ANSI no console clássico do Windows (no-op nos outros)."""
    if sys.platform != "win32" or not _COR:
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        for cod in (-11, -12):   # STDOUT e STDERR
            h = k.GetStdHandle(cod)
            m = ctypes.c_uint32()
            if k.GetConsoleMode(h, ctypes.byref(m)):
                k.SetConsoleMode(h, m.value | 0x0004)   # VIRTUAL_TERMINAL_PROCESSING
    except OSError:
        pass


def cor(texto, c):
    return f"{c}{texto}{_R}"


def saida(texto=""):
    """print() do tema: cada linha sai em vermelho claro (realces internos
    com códigos ANSI continuam valendo)."""
    print(f"{CLARO}{texto}{_R}" if _COR else texto)


def cabecalho(titulo, sub=""):
    """Imprime um cabeçalho em caixa vermelha."""
    larg = 56
    t = f"  ◢ SPARTA ▸ {titulo}"[:larg]
    print(VIVO + "╔" + "═" * larg + "╗" + _R)
    print(VIVO + "║" + _R + BG_FORTE + BRANCO + t.ljust(larg) + _R + VIVO + "║" + _R)
    if sub:
        print(VIVO + "║ " + _R + CINZA + sub[:larg - 2].ljust(larg - 2) + _R + VIVO + "║" + _R)
    print(VIVO + "╚" + "═" * larg + "╝" + _R)


def barra(fracao, larg=26, aviso=False):
    """Barra colorida: vermelho vivo (ou claro se aviso) + trilho escuro."""
    fracao = max(0.0, min(1.0, fracao))
    cheio = round(fracao * larg)
    c = BRANCO if aviso else VIVO
    return c + "█" * cheio + _R + ESCURO + "░" * (larg - cheio) + _R


def realce(texto):
    return cor(texto, BRANCO)


def bom(texto):
    return cor(texto, ROSA)
