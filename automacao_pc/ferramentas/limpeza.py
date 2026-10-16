"""
Limpa arquivos temporários e caches que só ocupam espaço.

Regras para não quebrar nada:
  - só apaga arquivos mais velhos que X horas (os recentes podem estar em uso);
  - cache de navegador só é limpo com o navegador fechado (senão é pulado);
  - pastas do sistema (C:\\Windows\\Temp etc.) só com --sistema e como administrador;
  - arquivos em uso são simplesmente ignorados.
"""

import os
import time
from pathlib import Path

from .util import WINDOWS, eh_admin, processos_ativos, tamanho_legivel

# (rótulo, pasta ou padrão glob, processo que precisa estar fechado, só admin)
_NAVEGADORES = [
    ("Chrome", r"%LOCALAPPDATA%\Google\Chrome\User Data\*", "chrome.exe"),
    ("Edge", r"%LOCALAPPDATA%\Microsoft\Edge\User Data\*", "msedge.exe"),
    ("Brave", r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\*", "brave.exe"),
    ("Vivaldi", r"%LOCALAPPDATA%\Vivaldi\User Data\*", "vivaldi.exe"),
    ("Opera", r"%LOCALAPPDATA%\Opera Software\Opera Stable", "opera.exe"),
    ("Opera GX", r"%LOCALAPPDATA%\Opera Software\Opera GX Stable", "opera.exe"),
]
_CACHES_CHROMIUM = ["Cache", "Code Cache", "GPUCache"]


def alvos(navegadores=True, sistema=False):
    lista = [
        ("Temporários do usuário", os.environ.get("TEMP", ""), None, False),
        ("Despejos de travamento", r"%LOCALAPPDATA%\CrashDumps", None, False),
    ]
    if navegadores:
        for nome, perfil, processo in _NAVEGADORES:
            for cache in _CACHES_CHROMIUM:
                lista.append((f"Cache {nome}", perfil + "\\" + cache, processo, False))
        lista.append(("Cache Firefox", r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\cache2",
                      "firefox.exe", False))
    if sistema:
        lista += [
            ("Temporários do Windows", r"%SystemRoot%\Temp", None, True),
            ("Relatórios de erro", r"%ProgramData%\Microsoft\Windows\WER\ReportArchive", None, True),
            ("Downloads do Windows Update", r"%SystemRoot%\SoftwareDistribution\Download", None, True),
        ]
    return lista


def _expandir(padrao):
    padrao = os.path.expandvars(padrao)
    if not padrao or "%" in padrao:
        return []
    if "*" not in padrao:
        return [Path(padrao)] if os.path.isdir(padrao) else []
    p = Path(padrao)
    return [x for x in Path(p.anchor).glob(str(p.relative_to(p.anchor))) if x.is_dir()]


def _arquivos_velhos(pasta, idade_horas, agora):
    limite = agora - idade_horas * 3600
    for raiz, _, arquivos in os.walk(pasta):
        for nome in arquivos:
            p = os.path.join(raiz, nome)
            try:
                st = os.stat(p, follow_symlinks=False)
            except OSError:
                continue
            if st.st_mtime < limite:
                yield p, st.st_size


def _remover_pastas_vazias(pasta):
    for raiz, _, _ in sorted(os.walk(pasta), key=lambda x: len(x[0]), reverse=True):
        if Path(raiz) != Path(pasta):
            try:
                os.rmdir(raiz)
            except OSError:
                pass


def tamanho_lixeira():
    if not WINDOWS:
        return 0, 0
    import ctypes

    class SHQUERYRBINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint32), ("i64Size", ctypes.c_int64),
                    ("i64NumItems", ctypes.c_int64)]
    info = SHQUERYRBINFO(cbSize=ctypes.sizeof(SHQUERYRBINFO))
    ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
    return info.i64Size, info.i64NumItems


def esvaziar_lixeira():
    import ctypes
    SEM_CONFIRMACAO, SEM_PROGRESSO, SEM_SOM = 0x1, 0x2, 0x4
    ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, SEM_CONFIRMACAO | SEM_PROGRESSO | SEM_SOM)


def executar(aplicar=False, idade_horas=24, navegadores=True, sistema=False,
             lixeira=False, saida=print, agora=None, lista_alvos=None):
    agora = time.time() if agora is None else agora
    abertos = processos_ativos()
    admin = eh_admin()
    total_geral = 0
    saida("Limpando:" if aplicar else "Prévia da limpeza:")

    resumo = {}
    for rotulo, padrao, processo, precisa_admin in (lista_alvos or alvos(navegadores, sistema)):
        pastas = _expandir(padrao)
        if not pastas:
            continue
        if precisa_admin and not admin:
            resumo.setdefault(rotulo, "pulado (rode como administrador)")
            continue
        if processo and processo in abertos:
            resumo[rotulo] = f"pulado (feche o {rotulo.replace('Cache ', '')})"
            continue
        liberado = 0
        for pasta in pastas:
            for arquivo, tamanho in _arquivos_velhos(pasta, idade_horas, agora):
                if aplicar:
                    try:
                        os.remove(arquivo)
                    except OSError:
                        continue   # em uso
                liberado += tamanho
            if aplicar:
                _remover_pastas_vazias(pasta)
        anterior = resumo.get(rotulo, 0)
        resumo[rotulo] = (anterior if isinstance(anterior, int) else 0) + liberado
        total_geral += liberado

    if lixeira and WINDOWS:
        tamanho, itens = tamanho_lixeira()
        if itens:
            if aplicar:
                esvaziar_lixeira()
            resumo["Lixeira"] = tamanho
            total_geral += tamanho

    for rotulo, valor in resumo.items():
        texto = tamanho_legivel(valor) if isinstance(valor, int) else valor
        saida(f"  {rotulo:<28} {texto}")
    saida(f"\n{'Liberado' if aplicar else 'Dá para liberar'}: {tamanho_legivel(total_geral)}"
          + ("" if aplicar else "  (use --executar para limpar)"))
    return total_geral
