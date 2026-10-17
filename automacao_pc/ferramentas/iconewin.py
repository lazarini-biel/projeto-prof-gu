"""
Ícones de verdade para o explorador: pega o ícone que o Windows usa para cada
tipo de arquivo (WinRAR, Word, PDF, pasta...) e gera a MINIATURA das imagens.

Devolve um "data:image/png;base64,..." para a página usar como <img>. Precisa
do Pillow (py -m pip install pillow). Sem Pillow ou fora do Windows, devolve
None e o explorador mostra a letrinha colorida de sempre.
"""

import base64
import ctypes
import sys
from io import BytesIO
from pathlib import Path

WINDOWS = sys.platform == "win32"
_CACHE_TIPO = {}                        # ext -> data uri (ícone do tipo)
IMAGENS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".ico"}
_SEM_CACHE = {".exe", ".lnk", ".ico", ".url"}   # ícone próprio de cada arquivo


def _pil():
    import importlib.util
    return importlib.util.find_spec("PIL") is not None


def disponivel():
    """(ok, motivo) — se os ícones reais funcionam aqui e, se não, por quê."""
    if not WINDOWS:
        return False, "Ícones reais do Windows só aparecem no Windows."
    if not _pil():
        return False, "Instale o Pillow para ver os ícones reais:  py -m pip install pillow"
    return True, ""


def _png_base64(img):
    buf = BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# ----------------------------------------------------- miniatura de imagem
def _miniatura(caminho, tam):
    from PIL import Image, ImageOps
    try:
        with Image.open(caminho) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((tam, tam))
            return _png_base64(img.convert("RGBA"))
    except Exception:
        return None


# ----------------------------------------------------- ícone do tipo (Windows)
if WINDOWS:
    from ctypes import wintypes

    class SHFILEINFOW(ctypes.Structure):
        _fields_ = [("hIcon", wintypes.HICON), ("iIcon", ctypes.c_int),
                    ("dwAttributes", wintypes.DWORD),
                    ("szDisplayName", wintypes.WCHAR * 260),
                    ("szTypeName", wintypes.WCHAR * 80)]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def _hicon(caminho, p: Path):
    """HICON do arquivo: o ícone real (apps) ou genérico pela extensão."""
    shell32 = ctypes.windll.shell32
    sfi = SHFILEINFOW()
    SHGFI_ICON, SHGFI_LARGEICON, SHGFI_USEFILEATTRIBUTES = 0x100, 0x0, 0x10
    if p.is_dir():
        attr, flags, nome = 0x10, SHGFI_ICON | SHGFI_LARGEICON | SHGFI_USEFILEATTRIBUTES, "pasta"
    elif p.suffix.lower() in _SEM_CACHE and p.exists():
        attr, flags, nome = 0, SHGFI_ICON | SHGFI_LARGEICON, caminho       # ícone próprio
    else:
        attr, flags, nome = 0x80, SHGFI_ICON | SHGFI_LARGEICON | SHGFI_USEFILEATTRIBUTES, \
            "x" + (p.suffix.lower() or ".dat")                              # genérico por extensão
    r = shell32.SHGetFileInfoW(nome, attr, ctypes.byref(sfi), ctypes.sizeof(sfi), flags)
    return sfi.hIcon if r else None


def _icone_para_img(hicon, tam):
    from PIL import Image
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    lado = 32
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = lado
    bmi.bmiHeader.biHeight = -lado        # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    hdc = gdi32.CreateCompatibleDC(None)
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    try:
        antigo = gdi32.SelectObject(hdc, hbmp)
        user32.DrawIconEx(hdc, 0, 0, hicon, lado, lado, 0, None, 0x0003)   # DI_NORMAL
        buf = ctypes.string_at(bits, lado * lado * 4)
        gdi32.SelectObject(hdc, antigo)
    finally:
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc)
    img = Image.frombuffer("RGBA", (lado, lado), buf, "raw", "BGRA", 0, 1)
    if not img.getextrema()[3][1]:         # alpha todo zero (ícone antigo): torna opaco
        r, g, b, _ = img.split()
        from PIL import Image as _I
        a = _I.eval(r.point(lambda v: v).convert("L"), lambda v: 255)
        img = _I.merge("RGBA", (r, g, b, a))
    if tam != lado:
        img = img.resize((tam, tam), Image.LANCZOS)
    return _png_base64(img)


def _icone_tipo(caminho, p, tam):
    hicon = _hicon(caminho, p)
    if not hicon:
        return None
    try:
        return _icone_para_img(hicon, tam)
    finally:
        ctypes.windll.user32.DestroyIcon(hicon)


# --------------------------------------------------------------- API
def para_web(caminho, tam=48):
    """data:image/png;base64,... do ícone/miniatura, ou None."""
    if not WINDOWS or not _pil():
        return None
    try:
        p = Path(caminho)
        if p.is_file() and p.suffix.lower() in IMAGENS:
            mini = _miniatura(caminho, tam)
            if mini:
                return mini
        base = "DIR" if p.is_dir() else p.suffix.lower()
        chave = (base, int(tam))                 # mesmo tipo em tamanhos diferentes (zoom)
        if base and base not in _SEM_CACHE and chave in _CACHE_TIPO:
            return _CACHE_TIPO[chave]
        dado = _icone_tipo(caminho, p, tam)
        if base and base not in _SEM_CACHE:
            _CACHE_TIPO[chave] = dado
        return dado
    except Exception:
        return None
