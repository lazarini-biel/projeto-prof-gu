"""
Abre VÁRIAS janelas de CMD de verdade no Windows, espalhadas pela tela,
com texto vermelho correndo — o efeito "filme de hacker" do gif.

Segurança (isto NÃO é um fork bomb):
  - a quantidade é limitada (no máximo MAX_JANELAS);
  - cada janela roda uma pequena animação em Python e FECHA SOZINHA depois
    de alguns segundos, mesmo que o programa principal morra;
  - o programa guarda as janelas e fecha todas quando a abertura termina ou
    quando você aperta uma tecla.

Só funciona no Windows (usa consoles e a API de janelas). Fora do Windows,
`abrir()` devolve None e a abertura usa a tempestade "fake" (popups.py).
"""

import ctypes
import random
import subprocess
import sys
import time

MAX_JANELAS = 30

# Animação que roda DENTRO de cada janelinha (recebe título e duração por argv).
_ANIMACAO = r'''
import sys, time, random, ctypes
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
w = out = sys.stdout.write
out("\x1b[2J")
fim = time.time() + dur
while time.time() < fim:
    out("\x1b[H")
    for _ in range(42):
        if random.random() < 0.28:
            out("\x1b[38;2;255;120;150m" + random.choice(L)[:72] + "\x1b[0m\x1b[K\n")
        else:
            n = random.randint(12, 72)
            out("\x1b[38;2;230;40;70m" + "".join(random.choice(S) for _ in range(n)) + "\x1b[K\n")
    out("\x1b[0m"); sys.stdout.flush()
    time.sleep(0.11)
'''


def _api():
    u = ctypes.windll.user32
    from ctypes import wintypes
    u.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
    u.FindWindowW.restype = wintypes.HWND
    u.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int, wintypes.UINT)
    u.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    u.GetSystemMetrics.argtypes = (ctypes.c_int,)
    return u


class Flood:
    def __init__(self, janelas):
        self._janelas = janelas          # [(Popen, hwnd|None)]
        self._fechado = False

    def fechar(self):
        if self._fechado:
            return
        self._fechado = True
        u = ctypes.windll.user32
        for proc, hwnd in self._janelas:
            try:
                if hwnd:
                    u.PostMessageW(hwnd, 0x0010, 0, 0)     # WM_CLOSE
            except Exception:
                pass
        time.sleep(0.15)
        for proc, _ in self._janelas:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass


def abrir(quantidade, duracao_total, rng=None):
    """Abre as janelas e devolve um Flood (ou None se não for Windows/der erro)."""
    if sys.platform != "win32":
        return None
    rng = rng or random.Random()
    quantidade = max(1, min(int(quantidade), MAX_JANELAS))
    try:
        u = _api()
        larg_tela = u.GetSystemMetrics(0) or 1920
        alt_tela = u.GetSystemMetrics(1) or 1080
    except Exception:
        return None

    janelas = []
    exe = sys.executable or "python"
    for i in range(quantidade):
        titulo = f"C:\\SPARTA\\{rng.choice(_TITULOS)}  —  {i:02d}"
        # cada janela vive de 45% a 100% do tempo (fecham escalonadas no fim)
        vida = duracao_total * rng.uniform(0.45, 1.0)
        try:
            proc = subprocess.Popen(
                [exe, "-c", _ANIMACAO, titulo, f"{vida:.1f}"],
                creationflags=0x00000010)          # CREATE_NEW_CONSOLE
        except OSError:
            continue
        hwnd = _posicionar(u, titulo, larg_tela, alt_tela, rng)
        janelas.append((proc, hwnd))
        time.sleep(rng.uniform(0.05, 0.18))        # escalona a abertura
    return Flood(janelas) if janelas else None


_TITULOS = ["organizar.py", "duplicados.py", "discos.py", "limpeza.py", "inicio.py",
            "energia.py", "agendador.py", "remoto.py", "nucleo.py", "autotipo.py",
            "cofre.py", "util.py", "pc.py", "navegadores.py"]


def _posicionar(u, titulo, larg_tela, alt_tela, rng):
    """Acha a janela recém-criada pelo título e a põe num lugar aleatório."""
    hwnd = None
    fim = time.time() + 0.6
    while time.time() < fim:
        hwnd = u.FindWindowW(None, titulo)
        if hwnd:
            break
        time.sleep(0.02)
    if not hwnd:
        return None
    w = rng.randint(int(larg_tela * 0.18), int(larg_tela * 0.30))
    h = rng.randint(int(alt_tela * 0.22), int(alt_tela * 0.36))
    x = rng.randint(0, max(0, larg_tela - w))
    y = rng.randint(0, max(0, alt_tela - h))
    try:
        u.SetWindowPos(hwnd, 0, x, y, w, h, 0x0040)   # SWP_SHOWWINDOW
    except Exception:
        pass
    return hwnd
