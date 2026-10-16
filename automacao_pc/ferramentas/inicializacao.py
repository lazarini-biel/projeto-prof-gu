"""
Programas que abrem junto com o Windows (startup): listar e desativar os que
você não quer. Mexe no registro (chaves "Run") e nas pastas de Inicialização.

Desativar guarda um backup (inicio_backup.json), então dá para reativar.
Desativar itens do HKLM (para todos os usuários) exige rodar como administrador.
Só funciona no Windows.
"""

import json
import os
from pathlib import Path

from . import tema
from .util import PASTA_BASE, WINDOWS

BACKUP = PASTA_BASE / "inicio_backup.json"


def _chaves():
    import winreg
    return [
        ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        ("HKLM32", winreg.HKEY_LOCAL_MACHINE,
         r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
    ]


def _pastas_startup():
    appdata = os.environ.get("APPDATA", "")
    programdata = os.environ.get("ProgramData", "")
    p = []
    if appdata:
        p.append(("Usuário", Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup"))
    if programdata:
        p.append(("Todos", Path(programdata) / r"Microsoft\Windows\Start Menu\Programs\Startup"))
    return p


def listar_itens():
    """[(origem, nome, alvo, tipo)] de tudo que abre no logon."""
    if not WINDOWS:
        return []
    import winreg
    itens = []
    for rotulo, raiz, caminho in _chaves():
        try:
            with winreg.OpenKey(raiz, caminho) as k:
                i = 0
                while True:
                    try:
                        nome, valor, _ = winreg.EnumValue(k, i)
                        itens.append((rotulo, nome, valor, "registro"))
                        i += 1
                    except OSError:
                        break
        except OSError:
            continue
    for rotulo, pasta in _pastas_startup():
        if pasta.is_dir():
            for arq in pasta.iterdir():
                if arq.is_file() and arq.suffix.lower() in (".lnk", ".url", ".bat", ".exe"):
                    itens.append((f"Pasta/{rotulo}", arq.stem, str(arq), "pasta"))
    return itens


def _backup():
    try:
        return json.loads(BACKUP.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _salvar_backup(lista):
    BACKUP.write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")


def listar(saida=print):
    tema.cabecalho("Inicialização do Windows", "programas que abrem quando você liga o PC")
    if not WINDOWS:
        tema.saida(tema.cor("Só funciona no Windows.", tema.CINZA))
        return []
    itens = listar_itens()
    if not itens:
        tema.saida(tema.cor("Nenhum programa de inicialização encontrado.", tema.CINZA))
        return itens
    for i, (origem, nome, alvo, _) in enumerate(itens, 1):
        curto = alvo if len(alvo) <= 54 else "…" + alvo[-53:]
        tema.saida(f"  {tema.cor(f'{i:>2}', tema.VIVO)}  {tema.cor(f'[{origem}]', tema.CINZA):<22} "
                   f"{tema.realce(nome)}")
        tema.saida(f"      {tema.cor(curto, tema.CINZA)}")
    desativados = _backup()
    if desativados:
        tema.saida(tema.cor(f"\n  {len(desativados)} item(ns) desativado(s) por você "
                            f"(reative com: py pc.py inicializar ativar N).", tema.CINZA))
        for j, d in enumerate(desativados, 1):
            tema.saida(f"   {tema.cor(f'd{j}', tema.ROSA)} {tema.cor(d['nome'] + ' [' + d['origem'] + ']', tema.CINZA)}")
    tema.saida(tema.cor("\n  Desativar: py pc.py inicializar desativar N", tema.ROSA))
    return itens


def desativar(numero, saida=print):
    import winreg
    itens = listar_itens()
    if not 1 <= numero <= len(itens):
        tema.saida("Número inválido.")
        return
    origem, nome, alvo, tipo = itens[numero - 1]
    try:
        if tipo == "registro":
            rotulo_para = {r[0]: r for r in _chaves()}
            _, raiz, caminho = rotulo_para[origem]
            with winreg.OpenKey(raiz, caminho, 0, winreg.KEY_SET_VALUE | winreg.KEY_READ) as k:
                valor, t = winreg.QueryValueEx(k, nome)
                winreg.DeleteValue(k, nome)
            backup = _backup()
            backup.append({"origem": origem, "nome": nome, "valor": valor, "tipo": t, "modo": "registro"})
            _salvar_backup(backup)
        else:
            arq = Path(alvo)
            destino = arq.parent / "Desativados (SPARTA)"
            destino.mkdir(exist_ok=True)
            novo = destino / arq.name
            arq.rename(novo)
            backup = _backup()
            backup.append({"origem": origem, "nome": nome, "valor": str(novo),
                           "original": alvo, "modo": "pasta"})
            _salvar_backup(backup)
        tema.saida(tema.bom(f"Desativado: {nome}"))
    except OSError as erro:
        tema.saida(tema.cor(f"Não consegui (tente como administrador para itens [HKLM]): {erro}", tema.VIVO))


def ativar(numero, saida=print):
    import winreg
    backup = _backup()
    if not 1 <= numero <= len(backup):
        tema.saida("Número inválido (veja os 'd1, d2...' na lista).")
        return
    d = backup[numero - 1]
    try:
        if d["modo"] == "registro":
            rotulo_para = {r[0]: r for r in _chaves()}
            _, raiz, caminho = rotulo_para[d["origem"]]
            with winreg.OpenKey(raiz, caminho, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, d["nome"], 0, d.get("tipo", winreg.REG_SZ), d["valor"])
        else:
            Path(d["valor"]).rename(d["original"])
        backup.pop(numero - 1)
        _salvar_backup(backup)
        tema.saida(tema.bom(f"Reativado: {d['nome']}"))
    except OSError as erro:
        tema.saida(tema.cor(f"Não consegui reativar: {erro}", tema.VIVO))
