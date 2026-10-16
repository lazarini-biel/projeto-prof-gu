"""
Modos de foco: com um comando, fecha os programas que atrapalham, abre os
que ajudam e (opcional) programa o desligamento. Os modos ficam no config,
então dá para criar quantos quiser (jogos, estudo, foco, dormir...).

Exemplo de config:
  "foco": {
    "estudo":  {"fechar": ["discord.exe","steam.exe","epicgameslauncher.exe"],
                "abrir_sites": ["https://scholar.google.com"], "mensagem": "Bons estudos!"},
    "jogos":   {"fechar": ["chrome.exe","teams.exe","onedrive.exe"]},
    "foco":    {"fechar": ["discord.exe","spotify.exe","steam.exe"]},
    "dormir":  {"fechar": ["*"], "desligar_em_min": 30}
  }
"""

from . import navegadores, tema
from .util import processos_ativos, WINDOWS

MODOS_PADRAO = {
    "estudo": {"fechar": ["discord.exe", "steam.exe", "epicgameslauncher.exe", "spotify.exe"],
               "mensagem": "Modo estudo: foco total. 📚"},
    "jogos": {"fechar": ["chrome.exe", "msedge.exe", "teams.exe", "onedrive.exe", "slack.exe"],
              "mensagem": "Modo jogos: segundo plano fechado. 🎮"},
    "foco": {"fechar": ["discord.exe", "spotify.exe", "steam.exe", "whatsapp.exe", "telegram.exe"],
             "mensagem": "Modo foco ligado. 🎯"},
    "dormir": {"fechar": ["*"], "desligar_em_min": 30, "mensagem": "Boa noite. 🌙"},
}
# nunca fechar com o curinga "*" (quebraria o Windows ou o próprio SPARTA)
_POUPAR = {
    "explorer.exe", "dwm.exe", "svchost.exe", "csrss.exe", "winlogon.exe", "wininit.exe",
    "services.exe", "lsass.exe", "smss.exe", "fontdrvhost.exe", "ctfmon.exe", "python.exe",
    "pythonw.exe", "conhost.exe", "windowsterminal.exe", "openconsole.exe", "sihost.exe",
    "taskhostw.exe", "runtimebroker.exe", "systemsettings.exe",
}


def listar_modos(cfg):
    modos = {**MODOS_PADRAO, **cfg.get("foco", {})}
    tema.cabecalho("Modos de foco", "use: py pc.py foco <modo>")
    for nome, m in modos.items():
        alvo = "tudo em segundo plano" if "*" in m.get("fechar", []) else \
            ", ".join(m.get("fechar", [])) or "nada"
        extra = f"  · desliga em {m['desligar_em_min']}min" if m.get("desligar_em_min") else ""
        tema.saida(f"  {tema.cor('▸', tema.VIVO)} {tema.realce(nome):<10} "
                   f"{tema.cor('fecha: ' + alvo + extra, tema.CINZA)}")


def ativar(cfg, nome):
    from .sistema import _matar
    from .util import processos_detalhados
    modos = {**MODOS_PADRAO, **cfg.get("foco", {})}
    if nome not in modos:
        tema.saida(f"Modo '{nome}' não existe. Modos: {', '.join(modos)}")
        return
    m = modos[nome]
    tema.cabecalho(f"Modo de foco: {nome}", m.get("mensagem", ""))

    fechar = [f.lower() for f in m.get("fechar", [])]
    ativos = processos_ativos()
    if "*" in fechar:
        # fecha tudo que não está na lista de poupados
        alvos = {nome_proc for nome_proc in ativos if nome_proc not in _POUPAR}
    else:
        alvos = {f for f in fechar if f in ativos}

    fechados = 0
    if alvos:
        for pid, nm, _ in processos_detalhados(200):
            if nm.lower() in alvos and _matar(pid):
                fechados += 1
        tema.saida(tema.cor(f"  {fechados} programa(s) fechados.", tema.ROSA))
    else:
        tema.saida(tema.cor("  Nada para fechar.", tema.CINZA))

    for site in m.get("abrir_sites", []):
        navegadores.abrir(site)
    if m.get("abrir_sites"):
        tema.saida(tema.cor(f"  {len(m['abrir_sites'])} site(s) abertos.", tema.CINZA))

    minutos = m.get("desligar_em_min")
    if minutos:
        from . import energia
        ok, msg = energia.desligar(minutos)
        tema.saida(tema.cor(f"  {msg}", tema.VIVO if ok else tema.CINZA))

    if not WINDOWS:
        return
    tema.saida(tema.cor("  (dica: para silenciar notificações, ligue o Assistente de Foco "
                        "com Win + A → Assistente de Foco)", tema.CINZA))
