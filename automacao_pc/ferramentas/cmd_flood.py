"""
Abre VÁRIAS janelas de CMD de verdade no Windows, espalhadas pela tela,
com texto vermelho correndo — o efeito "filme de hacker" (estilo o gif).

Segurança (isto NÃO é um fork bomb):
  - a quantidade é limitada (no máximo MAX_JANELAS);
  - cada janela roda uma pequena animação em Python e FECHA SOZINHA depois
    de alguns segundos, mesmo que o programa principal morra;
  - ao fim da abertura, o programa MATA todas as janelas na hora.

Só funciona no Windows. Fora do Windows, `abrir()` devolve None e a
abertura usa a tempestade "fake" (popups.py).
"""

import ctypes
import os
import random
import subprocess
import sys
import time

MAX_JANELAS = 30

# Animação dentro de cada janelinha (recebe título e duração por argv). Só vermelho.
_ANIMACAO = r'''
import sys, time, random, ctypes
if sys.stdout is None:          # pythonw sem console: nada a fazer
    raise SystemExit
titulo = sys.argv[1]; dur = float(sys.argv[2])
k = ctypes.windll.kernel32
try: k.SetConsoleTitleW(titulo)
except Exception: pass
h = k.GetStdHandle(-11); m = ctypes.c_uint32()
if k.GetConsoleMode(h, ctypes.byref(m)): k.SetConsoleMode(h, m.value | 4)
S = "0123456789ABCDEFabcdef<>{}[]()=+-*/\\|:;.,#$%&@?!^~"
L = ["def executar(cfg):", "  mov.mover(origem, destino)", "chave = scrypt(senha, sal)",
     "AESGCM(chave).encrypt(nonce, d)", "for raiz,_,_,tot,liv in discos:",
     "hash = blake2b(bloco).digest()", "categoria = mapa.get(ext)",
     "organizando Downloads ...", "[ OK ] modulo carregado", "SPARTA // systems control"]
CLARO = "\x1b[38;2;255;90;120m"; MEDIO = "\x1b[38;2;210;40;70m"; ESCURO = "\x1b[38;2;150;24;48m"
out = sys.stdout.write
out("\x1b[2J")
fim = time.time() + dur
while time.time() < fim:
    out("\x1b[H")
    for _ in range(42):
        if random.random() < 0.28:
            out(CLARO + random.choice(L)[:72] + "\x1b[K\n")
        else:
            n = random.randint(12, 72)
            cor = MEDIO if random.random() < 0.7 else ESCURO
            out(cor + "".join(random.choice(S) for _ in range(n)) + "\x1b[K\n")
    out("\x1b[0m"); sys.stdout.flush()
    time.sleep(0.10)
'''

_TITULOS = ["organizar.py", "duplicados.py", "discos.py", "limpeza.py", "inicio.py",
            "energia.py", "agendador.py", "remoto.py", "nucleo.py", "autotipo.py",
            "cofre.py", "util.py", "pc.py", "navegadores.py"]


def _api():
    u = ctypes.windll.user32
    from ctypes import wintypes
    u.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
    u.FindWindowW.restype = wintypes.HWND
    u.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int, wintypes.UINT)
    u.GetSystemMetrics.argtypes = (ctypes.c_int,)
    return u


class Flood:
    def __init__(self, procs):
        self._procs = procs              # [Popen]
        self._fechado = False

    def fechar(self):
        """Mata todas as janelas na hora (TerminateProcess é instantâneo)."""
        if self._fechado:
            return
        self._fechado = True
        for proc in self._procs:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass


def abrir(quantidade, duracao, rng=None):
    """Abre as janelas em cascata rápida e as posiciona. Devolve um Flood
    (ou None fora do Windows / se der erro). `duracao` = vida de cada janela."""
    if sys.platform != "win32":
        return None
    rng = rng or random.Random()
    quantidade = max(1, min(int(quantidade), MAX_JANELAS))
    try:
        u = _api()
        larg = u.GetSystemMetrics(0) or 1920
        alt = u.GetSystemMetrics(1) or 1080
    except Exception:
        return None

    exe = sys.executable or "python"
    # usa python.exe (com console), nunca pythonw.exe (sem stdout → janela preta)
    if exe.lower().endswith("pythonw.exe"):
        cand = exe[:-len("pythonw.exe")] + "python.exe"
        if os.path.exists(cand):
            exe = cand
    pendentes = []     # (titulo, proc) ainda sem posição
    procs = []
    for i in range(quantidade):
        titulo = f"C:\\SPARTA\\{rng.choice(_TITULOS)}  —  {i:02d}"
        vida = duracao + rng.uniform(0.0, 1.5)        # fecham quase juntas no fim
        try:
            proc = subprocess.Popen([exe, "-c", _ANIMACAO, titulo, f"{vida:.1f}"],
                                    creationflags=0x00000010)   # CREATE_NEW_CONSOLE
        except OSError:
            continue
        procs.append(proc)
        pendentes.append((titulo, proc))
        time.sleep(0.07)                              # cascata rápida de aberturas

    # posiciona em algumas passadas rápidas (FindWindowW é instantâneo)
    for _ in range(6):
        if not pendentes:
            break
        time.sleep(0.12)
        ainda = []
        for titulo, proc in pendentes:
            hwnd = u.FindWindowW(None, titulo)
            if hwnd:
                w = rng.randint(int(larg * 0.17), int(larg * 0.30))
                h = rng.randint(int(alt * 0.20), int(alt * 0.34))
                x = rng.randint(0, max(0, larg - w))
                y = rng.randint(0, max(0, alt - h))
                try:
                    u.SetWindowPos(hwnd, 0, x, y, w, h, 0x0040)   # SWP_SHOWWINDOW
                except Exception:
                    pass
            else:
                ainda.append((titulo, proc))
        pendentes = ainda
    return Flood(procs) if procs else None
