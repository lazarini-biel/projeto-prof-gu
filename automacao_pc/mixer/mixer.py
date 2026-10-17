"""
SPARTA // MIXER — mixer de volume no estilo SPARTA, ligado ao Windows.

- Volume por aplicativo (0–100%), volume geral e mudo: pela API de áudio do
  Windows (biblioteca pycaw).
- Boost acima de 100%: o Windows não deixa por software puro, então o SPARTA
  controla o ganho do Equalizer APO (gratuito, open-source). Com ele instalado,
  dá para passar de 100% de verdade.

Rode com:
    python mixer.py            abre o mixer
    --janela                   em janela (padrão: tela cheia; F11 alterna)

Instale as dependências do áudio uma vez:  py -m pip install pycaw comtypes
"""

import math
import sys
from pathlib import Path

import webview

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # ferramentas/
from ferramentas.util import WINDOWS   # noqa: E402

TITULO = "SPARTA // MIXER"


def _recurso(rel):
    """Caminho de um recurso (ui/), funcionando empacotado (.exe) ou como script."""
    import os
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def _identidade_windows():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SPARTA.Mixer")
        except OSError:
            pass

# ----------------------------------------------------------- Equalizer APO
_EQAPO_CANDIDATOS = [
    r"C:\Program Files\EqualizerAPO\config\config.txt",
    r"C:\Program Files (x86)\EqualizerAPO\config\config.txt",
]
_MARCA_INI = "# SPARTA-BOOST-START"
_MARCA_FIM = "# SPARTA-BOOST-END"


def _eqapo_config():
    import os
    try:
        import winreg
        for raiz in (winreg.HKEY_LOCAL_MACHINE,):
            try:
                with winreg.OpenKey(raiz, r"SOFTWARE\EqualizerAPO") as k:
                    base = winreg.QueryValueEx(k, "InstallPath")[0]
                    cand = os.path.join(base, "config", "config.txt")
                    if os.path.exists(cand):
                        return cand
            except OSError:
                pass
    except ImportError:
        pass
    for c in _EQAPO_CANDIDATOS:
        if os.path.exists(c):
            return c
    return None


def _db_do_boost(pct):
    """pct 100..400 -> ganho em dB (100% = 0 dB)."""
    pct = max(100, min(int(pct), 600))
    return 20 * math.log10(pct / 100)


class Api:
    def __init__(self):
        self._janela = None
        self._eqapo = _eqapo_config() if WINDOWS else None

    # ------------------------------------------------------------ estado
    def estado(self):
        return {"windows": WINDOWS, "eqapo": bool(self._eqapo),
                "pycaw": self._tem_pycaw(), "boost": self._boost_atual()}

    def _tem_pycaw(self):
        if not WINDOWS:
            return False
        import importlib.util
        return importlib.util.find_spec("pycaw") is not None

    # ------------------------------------------------------- sessões
    def _endpoint(self):
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        alto = AudioUtilities.GetSpeakers()
        iface = alto.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(iface, POINTER(IAudioEndpointVolume))

    def master(self):
        if not self._tem_pycaw():
            return None
        try:
            e = self._endpoint()
            return {"volume": round(e.GetMasterVolumeLevelScalar() * 100),
                    "mudo": bool(e.GetMute())}
        except Exception:
            return None

    def sessoes(self):
        """Lista de apps com volume/mudo + o volume geral."""
        if not WINDOWS:
            return {"erro": "O mixer funciona no Windows.", "sessoes": []}
        if not self._tem_pycaw():
            return {"erro": "pycaw", "sessoes": []}
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        itens = []
        try:
            for s in AudioUtilities.GetAllSessions():
                ctl = s._ctl.QueryInterface(ISimpleAudioVolume)
                proc = getattr(s, "Process", None)
                nome = (proc.name() if proc else None) or s.DisplayName or "Sistema"
                exe = proc.name() if proc else ""
                itens.append({
                    "id": exe or nome,
                    "exe": exe,
                    "nome": nome.replace(".exe", "").title() if exe else nome,
                    "pid": proc.pid if proc else 0,
                    "volume": round(ctl.GetMasterVolume() * 100),
                    "mudo": bool(ctl.GetMute()),
                    "boost": self._boost_de(exe),
                })
        except Exception as erro:
            return {"erro": str(erro), "sessoes": []}
        # junta apps repetidos (vários processos do mesmo exe) pelo nome
        unicos = {}
        for it in itens:
            k = it["exe"] or it["nome"]
            if k not in unicos:
                unicos[k] = it
        return {"master": self.master(), "sessoes": sorted(unicos.values(), key=lambda x: x["nome"].lower())}

    def _por_exe(self, exe):
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        achados = []
        for s in AudioUtilities.GetAllSessions():
            proc = getattr(s, "Process", None)
            if proc and proc.name().lower() == exe.lower():
                achados.append(s._ctl.QueryInterface(ISimpleAudioVolume))
        return achados

    def set_volume(self, sid, pct):
        try:
            for ctl in self._por_exe(sid):
                ctl.SetMasterVolume(max(0, min(int(pct), 100)) / 100, None)
            return {"ok": True}
        except Exception as erro:
            return {"ok": False, "erro": str(erro)}

    def set_mudo(self, sid, mudo):
        try:
            for ctl in self._por_exe(sid):
                ctl.SetMute(1 if mudo else 0, None)
            return {"ok": True}
        except Exception as erro:
            return {"ok": False, "erro": str(erro)}

    def set_master(self, pct):
        try:
            self._endpoint().SetMasterVolumeLevelScalar(max(0, min(int(pct), 100)) / 100, None)
            return {"ok": True}
        except Exception as erro:
            return {"ok": False, "erro": str(erro)}

    def set_master_mudo(self, mudo):
        try:
            self._endpoint().SetMute(1 if mudo else 0, None)
            return {"ok": True}
        except Exception as erro:
            return {"ok": False, "erro": str(erro)}

    # ---------------------------------------------------- boost (EqualizerAPO)
    def _ler_config(self):
        try:
            return Path(self._eqapo).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _boost_blocos(self, texto):
        """{exe_ou_'GERAL': pct} lidos do bloco gerenciado pelo SPARTA."""
        import re
        m = re.search(re.escape(_MARCA_INI) + r"(.*?)" + re.escape(_MARCA_FIM), texto, re.DOTALL)
        blocos = {}
        if not m:
            return blocos
        corpo = m.group(1)
        # GERAL: linha "Preamp: +X dB" fora de If
        atual_app = "GERAL"
        for linha in corpo.splitlines():
            linha = linha.strip()
            cond = re.match(r'If:\s*appIncludes\("([^"]+)"\)', linha)
            if cond:
                atual_app = cond.group(1)
            elif linha.startswith("EndIf"):
                atual_app = "GERAL"
            else:
                g = re.match(r"Preamp:\s*([+-]?[\d.]+)\s*dB", linha)
                if g:
                    pct = round(10 ** (float(g.group(1)) / 20) * 100)
                    blocos[atual_app] = pct
        return blocos

    def _boost_atual(self):
        if not self._eqapo:
            return {}
        return self._boost_blocos(self._ler_config())

    def _boost_de(self, exe):
        return self._boost_atual().get(exe, 100)

    def set_boost(self, exe, pct):
        """Define o boost (>100%) de um app (ou 'GERAL') via Equalizer APO."""
        if not self._eqapo:
            return {"ok": False, "erro": "Equalizer APO não está instalado."}
        import re
        alvo = exe or "GERAL"
        blocos = self._boost_atual()
        if int(pct) <= 100:
            blocos.pop(alvo, None)
        else:
            blocos[alvo] = int(pct)
        # remonta o bloco gerenciado
        linhas = [_MARCA_INI, "# Controlado pelo SPARTA Mixer — nao edite a mao"]
        if "GERAL" in blocos:
            linhas.append(f"Preamp: {_db_do_boost(blocos['GERAL']):+.1f} dB")
        for app, p in blocos.items():
            if app == "GERAL":
                continue
            linhas.append(f'If: appIncludes("{app}")')
            linhas.append(f"Preamp: {_db_do_boost(p):+.1f} dB")
            linhas.append("EndIf:")
        linhas.append(_MARCA_FIM)
        novo_bloco = "\n".join(linhas)

        texto = self._ler_config()
        if _MARCA_INI in texto:
            texto = re.sub(re.escape(_MARCA_INI) + r".*?" + re.escape(_MARCA_FIM),
                           novo_bloco, texto, flags=re.DOTALL)
        else:
            texto = texto.rstrip() + "\n\n" + novo_bloco + "\n"
        try:
            Path(self._eqapo).write_text(texto, encoding="utf-8")
            return {"ok": True}
        except OSError as erro:
            return {"ok": False, "erro": f"Não consegui escrever (rode como administrador?): {erro}"}

    def abrir_eqapo(self):
        import webbrowser
        webbrowser.open("https://sourceforge.net/projects/equalizerapo/")
        return {"ok": True}

    # ----------------------------------------------------------- janela
    def alternar_tela_cheia(self):
        if self._janela:
            self._janela.toggle_fullscreen()

    def sair(self):
        if self._janela:
            self._janela.destroy()


def main():
    _identidade_windows()
    opcoes = [a for a in sys.argv[1:] if a.startswith("--")]
    api = Api()
    janela = webview.create_window(TITULO, _recurso("ui/index.html"), js_api=api, width=1100, height=720,
                                   min_size=(820, 560), background_color="#070204",
                                   fullscreen="--janela" not in opcoes)
    api._janela = janela
    webview.start()


if __name__ == "__main__":
    main()
