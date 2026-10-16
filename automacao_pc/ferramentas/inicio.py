"""
Abre de uma vez os programas, sites e pastas de um "perfil" (ex.: "padrao",
"trabalho", "jogos"). O perfil "padrao" pode rodar sozinho ao ligar o PC.
"""

import os
import subprocess
import time
from collections import defaultdict

from . import navegadores
from .util import WINDOWS, caminho, processos_ativos


def executar(perfis, nome="padrao", sem_atraso=False, saida=print):
    if nome not in perfis:
        saida(f"Perfil '{nome}' não existe no config. Perfis: {', '.join(perfis)}")
        return False
    perfil = perfis[nome]
    atraso = 0 if sem_atraso else perfil.get("atraso_segundos", 0)
    if atraso:
        saida(f"Aguardando {atraso}s para o Windows terminar de carregar...")
        time.sleep(atraso)

    abertos = processos_ativos()
    for prog in perfil.get("programas", []):
        if isinstance(prog, str):
            prog = {"caminho": prog}
        exe = caminho(prog["caminho"])
        if not exe.exists():
            saida(f"  ! não encontrei {exe}")
            continue
        if prog.get("pular_se_aberto", True) and exe.name.lower() in abertos:
            saida(f"  = {exe.name} já está aberto")
            continue
        saida(f"  > {exe.name}")
        try:
            argumentos = prog.get("argumentos", [])
            if argumentos or not WINDOWS:
                subprocess.Popen([str(exe), *argumentos], cwd=str(exe.parent), close_fds=True)
            else:
                os.startfile(str(exe))   # também abre atalhos .lnk e .url
        except OSError as erro:
            saida(f"  ! {exe.name}: {erro}")
        time.sleep(prog.get("esperar_segundos", 1))

    por_navegador = defaultdict(list)
    for site in perfil.get("sites", []):
        if isinstance(site, str):
            site = {"url": site}
        por_navegador[site.get("navegador")].append(site["url"])
    for nav, urls in por_navegador.items():
        saida(f"  > {len(urls)} site(s) no {nav or 'navegador padrão'}")
        navegadores.abrir(urls, nav)

    for pasta in perfil.get("pastas", []):
        p = caminho(pasta)
        if p.is_dir() and WINDOWS:
            os.startfile(str(p))
    saida("Pronto.")
    return True
