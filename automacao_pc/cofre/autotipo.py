"""
Integração com o Windows: descobrir a janela ativa (navegador e site),
"digitar" usuário e senha nela, atalho global Ctrl+Alt+A e área de
transferência que se apaga sozinha.

A digitação é feita com SendInput em modo Unicode (como se fosse o teclado),
então funciona em qualquer navegador ou programa, sem extensão. Antes de cada
tecla o cofre confere se a janela ativa ainda é a mesma — se você trocar de
janela no meio, ele para e não digita a senha no lugar errado.
"""

import ctypes
import re
import sys
import threading
import time
from dataclasses import dataclass

WINDOWS = sys.platform == "win32"
VK = {"TAB": 0x09, "ENTER": 0x0D, "ESC": 0x1B, "ESPACO": 0x20}


class JanelaMudou(Exception):
    pass


# ------------------------------------------------------ sequência de teclas
def interpretar(sequencia):
    """"{USUARIO}{TAB}{SENHA}{ENTER}" -> [("campo","usuario"), ("tecla",9), ...]

    Tokens: {USUARIO} {SENHA} {TAB} {ENTER} {ESC} {ESPACO} {ESPERA:ms}.
    Qualquer outro texto é digitado como está.
    """
    tokens = []
    pos = 0
    for m in re.finditer(r"\{([^{}]+)\}", sequencia):
        if m.start() > pos:
            tokens.append(("texto", sequencia[pos:m.start()]))
        nome = m.group(1).strip().upper()
        if nome in ("USUARIO", "USUÁRIO", "USERNAME", "USER"):
            tokens.append(("campo", "usuario"))
        elif nome in ("SENHA", "PASSWORD"):
            tokens.append(("campo", "senha"))
        elif nome in VK:
            tokens.append(("tecla", VK[nome]))
        elif re.fullmatch(r"(ESPERA|DELAY):\d+", nome):
            tokens.append(("espera", int(nome.split(":")[1])))
        else:
            tokens.append(("texto", m.group(0)))
        pos = m.end()
    if pos < len(sequencia):
        tokens.append(("texto", sequencia[pos:]))
    return tokens


@dataclass
class Janela:
    hwnd: int
    titulo: str
    processo: str
    pid: int


if WINDOWS:
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ULONG_PTR = ctypes.c_size_t

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

    class _UNIAO(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _UNIAO)]

    INPUT_KEYBOARD, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 1, 0x2, 0x4

    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
    user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.IsIconic.argtypes = (wintypes.HWND,)
    user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
    user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
    user32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    user32.OpenClipboard.argtypes = (wintypes.HWND,)
    user32.SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.GetClipboardData.argtypes = (wintypes.UINT,)
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.RegisterClipboardFormatW.argtypes = (wintypes.LPCWSTR,)
    user32.RegisterClipboardFormatW.restype = wintypes.UINT
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                    ctypes.POINTER(wintypes.DWORD))
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.GlobalAlloc.argtypes = (wintypes.UINT, ctypes.c_size_t)
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD


def _exigir_windows():
    if not WINDOWS:
        raise OSError("Recurso disponível só no Windows.")


# ------------------------------------------------------------- janelas
def janela_ativa():
    _exigir_windows()
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    tamanho = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(tamanho + 1)
    user32.GetWindowTextW(hwnd, buffer, tamanho + 1)

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    processo = ""
    handle = kernel32.OpenProcess(0x1000, False, pid.value)   # QUERY_LIMITED_INFORMATION
    if handle:
        caminho = ctypes.create_unicode_buffer(1024)
        n = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, caminho, ctypes.byref(n)):
            processo = caminho.value.rsplit("\\", 1)[-1].lower()
        kernel32.CloseHandle(handle)
    return Janela(hwnd, buffer.value, processo, pid.value)


def focar(hwnd, espera=1.5):
    _exigir_windows()
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)   # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    limite = time.time() + espera
    while time.time() < limite:
        if user32.GetForegroundWindow() == hwnd:
            time.sleep(0.15)
            return True
        time.sleep(0.05)
    return False


# ------------------------------------------------------------ digitação
def _enviar(*entradas):
    arr = (INPUT * len(entradas))(*entradas)
    if user32.SendInput(len(entradas), arr, ctypes.sizeof(INPUT)) != len(entradas):
        raise OSError(ctypes.get_last_error(), "O Windows bloqueou a digitação (janela de administrador?)")


def _tecla(vk):
    _enviar(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk, dwFlags=KEYEVENTF_KEYUP)))


def _texto(texto, intervalo):
    dados = texto.encode("utf-16-le")
    for i in range(0, len(dados), 2):   # emojis e acentos viram pares UTF-16
        unidade = int.from_bytes(dados[i:i + 2], "little")
        _enviar(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wScan=unidade, dwFlags=KEYEVENTF_UNICODE)),
                INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wScan=unidade,
                                                         dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)))
        time.sleep(intervalo)


def esperar_modificadores(limite=3.0):
    """Quem apertou Ctrl+Alt+A ainda pode estar segurando Ctrl/Alt: digitar
    agora viraria atalhos. Espera soltar."""
    fim = time.time() + limite
    while time.time() < fim:
        if not any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C)):
            return True
        time.sleep(0.03)
    return False


def digitar(sequencia, usuario, senha, hwnd_alvo, intervalo=0.012):
    _exigir_windows()
    esperar_modificadores()
    for tipo, valor in interpretar(sequencia):
        if user32.GetForegroundWindow() != hwnd_alvo:
            raise JanelaMudou()
        if tipo == "campo":
            _texto(usuario if valor == "usuario" else senha, intervalo)
        elif tipo == "texto":
            _texto(valor, intervalo)
        elif tipo == "tecla":
            _tecla(valor)
            time.sleep(0.05)
        elif tipo == "espera":
            time.sleep(valor / 1000)


# ------------------------------------------------- área de transferência
def _abrir_area():
    for _ in range(20):   # outro programa pode estar com ela aberta
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.05)
    return False


def _global(dados):
    h = kernel32.GlobalAlloc(0x0002, len(dados))   # GMEM_MOVEABLE
    p = kernel32.GlobalLock(h)
    ctypes.memmove(p, dados, len(dados))
    kernel32.GlobalUnlock(h)
    return h


def copiar(texto):
    """Copia sem entrar no histórico do Win+V nem na nuvem da Microsoft."""
    _exigir_windows()
    if not _abrir_area():
        raise OSError("A área de transferência está ocupada por outro programa.")
    try:
        user32.EmptyClipboard()
        user32.SetClipboardData(13, _global((texto + "\0").encode("utf-16-le")))   # CF_UNICODETEXT
        zero = (0).to_bytes(4, "little")
        for formato in ("ExcludeClipboardContentFromMonitorProcessing",
                        "CanIncludeInClipboardHistory", "CanUploadToCloudClipboard"):
            user32.SetClipboardData(user32.RegisterClipboardFormatW(formato), _global(zero))
    finally:
        user32.CloseClipboard()


def texto_copiado():
    _exigir_windows()
    if not _abrir_area():
        return None
    try:
        h = user32.GetClipboardData(13)
        if not h:
            return None
        p = kernel32.GlobalLock(h)
        try:
            return ctypes.wstring_at(p)
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()


def limpar_area():
    _exigir_windows()
    if _abrir_area():
        user32.EmptyClipboard()
        user32.CloseClipboard()


# ---------------------------------------------------------- atalho global
class AtalhoGlobal(threading.Thread):
    """Chama `ao_apertar()` quando Ctrl+Alt+<tecla> é pressionado em qualquer lugar."""

    MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x1, 0x2, 0x4000

    def __init__(self, ao_apertar, tecla="A"):
        super().__init__(daemon=True)
        self.ao_apertar = ao_apertar
        self.tecla = tecla
        self._thread_id = None
        self.registrado = threading.Event()
        self.erro = None

    def run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, 1, self.MOD_CONTROL | self.MOD_ALT | self.MOD_NOREPEAT,
                                     ord(self.tecla.upper())):
            self.erro = f"Ctrl+Alt+{self.tecla} já é usado por outro programa."
            self.registrado.set()
            return
        self.registrado.set()
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:   # WM_HOTKEY
                    try:
                        self.ao_apertar()
                    except Exception as erro:   # nunca derrubar o atalho
                        print("Erro no atalho:", erro, file=sys.stderr)
        finally:
            user32.UnregisterHotKey(None, 1)

    def parar(self):
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)   # WM_QUIT
