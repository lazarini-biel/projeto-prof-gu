"""
Rede: testar a internet (ping + velocidade, com histórico) e listar os
dispositivos que aparecem na sua rede local.
"""

import json
import re
import subprocess
import time
import urllib.error
import urllib.request

from . import tema
from .util import PASTA_BASE, WINDOWS, tamanho_legivel

HISTORICO = PASTA_BASE / "rede_historico.json"
_SW_OCULTO = {"creationflags": 0x08000000} if WINDOWS else {}


def _run(cmd, timeout=15):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              **_SW_OCULTO).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def ping(host="1.1.1.1"):
    """Latência média em ms (ou None se não respondeu)."""
    cmd = ["ping", "-n", "4", host] if WINDOWS else ["ping", "-c", "4", host]
    saida = _run(cmd, timeout=12)
    # pega todos os "tempo=12ms" / "time=12.3 ms"
    tempos = [float(x) for x in re.findall(r"(?:time|tempo)[=<]\s*([\d.,]+)\s*ms",
                                           saida, re.IGNORECASE)]
    tempos = [float(str(t).replace(",", ".")) for t in tempos]
    return round(sum(tempos) / len(tempos), 1) if tempos else None


def velocidade(bytes_baixar=8_000_000):
    """Velocidade de download aproximada em Mbps (ou None se falhar)."""
    url = f"https://speed.cloudflare.com/__down?bytes={bytes_baixar}"
    try:
        inicio = time.time()
        baixado = 0
        req = urllib.request.Request(url, headers={"User-Agent": "SPARTA"})
        with urllib.request.urlopen(req, timeout=20) as r:
            while True:
                pedaco = r.read(65536)
                if not pedaco:
                    break
                baixado += len(pedaco)
        dur = time.time() - inicio
        if dur <= 0 or baixado < bytes_baixar * 0.5:
            return None, baixado
        return round(baixado * 8 / dur / 1_000_000, 1), baixado
    except (urllib.error.URLError, OSError, ValueError):
        return None, 0


def _registrar(ping_ms, down):
    try:
        hist = json.loads(HISTORICO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        hist = []
    hist.append({"quando": int(time.time()), "ping": ping_ms, "download": down})
    hist = hist[-50:]
    try:
        HISTORICO.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return hist


def testar(saida=None):
    tema.cabecalho("Teste de internet", "ping + velocidade de download")
    tema.saida(tema.cor("Medindo ping...", tema.CINZA))
    p = ping()
    if p is None:
        tema.saida(tema.cor("Sem resposta ao ping — você está sem internet?", tema.VIVO))
    else:
        nivel = "ótimo" if p < 20 else "bom" if p < 60 else "alto"
        tema.saida(f"  {tema.cor('Ping   :', tema.CINZA)} {tema.realce(f'{p} ms')} "
                   f"{tema.cor('(' + nivel + ')', tema.CINZA)}")
    tema.saida(tema.cor("Medindo velocidade de download...", tema.CINZA))
    mbps, baixado = velocidade()
    if mbps is None:
        tema.saida(tema.cor("Não consegui medir a velocidade agora.", tema.VIVO))
    else:
        larg = min(1.0, mbps / 300)
        tema.saida(f"  {tema.cor('Download:', tema.CINZA)} {tema.barra(larg, 24)} "
                   f"{tema.realce(f'{mbps} Mbps')} {tema.cor(f'({tamanho_legivel(baixado)})', tema.CINZA)}")
    hist = _registrar(p, mbps)
    anteriores = [h for h in hist[:-1] if h.get("download")]
    if anteriores:
        media = sum(h["download"] for h in anteriores) / len(anteriores)
        tema.saida(tema.cor(f"\n  Média das últimas {len(anteriores)} medições: {media:.0f} Mbps", tema.CINZA))


def dispositivos(saida=None):
    """Lista os dispositivos vistos na rede local (pela tabela ARP)."""
    tema.cabecalho("Dispositivos na rede", "aparelhos que seu PC 'enxergou' na rede local")
    saida_arp = _run(["arp", "-a"], timeout=10)
    # IPs e MACs em qualquer formato (aa-bb-.. ou aa:bb:..)
    pares = re.findall(r"(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})",
                       saida_arp)
    vistos = {}
    for ip, mac in pares:
        vistos[ip] = mac.lower().replace("-", ":")
    if not vistos:
        tema.saida(tema.cor("Nenhum dispositivo encontrado (tente abrir sites antes, ou "
                            "rode como administrador).", tema.CINZA))
        return
    tema.saida(f"  {tema.cor(f'{len(vistos)} dispositivo(s):', tema.VIVO)}\n")
    for ip in sorted(vistos, key=lambda x: tuple(int(p) for p in x.split("."))):
        fab = _fabricante(vistos[ip])
        tema.saida(f"  {tema.realce(f'{ip:<16}')} {tema.cor(vistos[ip], tema.CINZA)}  "
                   f"{tema.cor(fab, tema.CINZA)}")


# início de MAC (OUI) → fabricante, só os mais comuns (identifica alguns aparelhos)
_OUI = {
    "fc:fb:fb": "Apple", "a4:83:e7": "Apple", "3c:5a:b4": "Google", "44:07:0b": "Google",
    "b8:27:eb": "Raspberry Pi", "dc:a6:32": "Raspberry Pi", "00:1a:11": "Google",
    "ec:fa:bc": "Tuya/Smart", "50:02:91": "Espressif/IoT", "d8:bb:c1": "Samsung",
}


def _fabricante(mac):
    return _OUI.get(mac[:8], "")
