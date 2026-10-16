"""
Clima e manchetes do dia. Busca a previsão (open-meteo, sem chave) e os
títulos de notícias (Google Notícias RSS). Usado na abertura e no comando
`py pc.py clima`.

Tudo com tempo-limite curto e à prova de falha: sem internet, simplesmente
não mostra nada.
"""

import json
import re
import urllib.error
import urllib.request

from . import tema

_TEMPO = {0: "céu limpo", 1: "quase limpo", 2: "parcialmente nublado", 3: "nublado",
          45: "névoa", 48: "névoa com geada", 51: "garoa fraca", 53: "garoa",
          55: "garoa forte", 61: "chuva fraca", 63: "chuva", 65: "chuva forte",
          71: "neve fraca", 73: "neve", 75: "neve forte", 80: "pancadas de chuva",
          81: "pancadas fortes", 82: "temporal", 95: "trovoada", 96: "trovoada com granizo"}


def _get(url, timeout=6):
    req = urllib.request.Request(url, headers={"User-Agent": "SPARTA/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _local(cfg):
    """(lat, lon, cidade) do config ou descoberto pelo IP."""
    c = cfg.get("clima", {})
    if c.get("lat") is not None and c.get("lon") is not None:
        return c["lat"], c["lon"], c.get("cidade", "")
    for url, campos in (("https://ipwho.is/", ("latitude", "longitude", "city")),
                        ("https://ipapi.co/json/", ("latitude", "longitude", "city")),
                        ("http://ip-api.com/json/", ("lat", "lon", "city"))):
        try:
            d = json.loads(_get(url, timeout=5))
            la, lo = d.get(campos[0]), d.get(campos[1])
            if la is not None and lo is not None:
                return la, lo, d.get(campos[2], "")
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            continue
    return None, None, ""


def previsao(cfg):
    """{'cidade','temp','sensacao','desc','min','max'} ou None."""
    lat, lon, cidade = _local(cfg)
    if lat is None:
        return None
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               "&current=temperature_2m,apparent_temperature,weather_code"
               "&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=1")
        d = json.loads(_get(url))
        atual = d["current"]
        diario = d.get("daily", {})
        return {
            "cidade": cidade,
            "temp": round(atual["temperature_2m"]),
            "sensacao": round(atual["apparent_temperature"]),
            "desc": _TEMPO.get(atual["weather_code"], "—"),
            "min": round(diario["temperature_2m_min"][0]) if diario.get("temperature_2m_min") else None,
            "max": round(diario["temperature_2m_max"][0]) if diario.get("temperature_2m_max") else None,
        }
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError):
        return None


def manchetes(cfg, quantas=6):
    """Lista de títulos de notícias (ou vazia)."""
    fonte = cfg.get("clima", {}).get("noticias_rss",
                                     "https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419")
    try:
        xml = _get(fonte, timeout=6)
    except (urllib.error.URLError, OSError):
        return []
    titulos = re.findall(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", xml, re.DOTALL)
    titulos = [re.sub(r"\s+", " ", t).strip() for t in titulos[1:]]   # pula o título do feed
    ruins = {"Google Notícias", "Google News"}
    return [t for t in titulos if t and t not in ruins][:quantas]


def resumo_curto(cfg):
    """Uma linha "☀ 24° céu limpo · <manchete>" para a abertura (ou '')."""
    p = previsao(cfg)
    partes = []
    if p:
        local = f" em {p['cidade']}" if p["cidade"] else ""
        partes.append(f"{p['temp']}°{local} · {p['desc']}")
    m = manchetes(cfg, 1)
    if m:
        partes.append(m[0][:70])
    return "  ·  ".join(partes)


def mostrar(cfg, saida=None):
    tema.cabecalho("Clima e notícias", "previsão de hoje e manchetes")
    p = previsao(cfg)
    if p:
        local = f" — {p['cidade']}" if p["cidade"] else ""
        temp = tema.realce(f"{p['temp']}°C")
        sens = tema.cor(f"(sensação {p['sensacao']}°)", tema.CINZA)
        tema.saida(f"  {temp} {sens}  {tema.realce(p['desc'])}{tema.cor(local, tema.CINZA)}")
        if p["min"] is not None:
            faixa = f"mínima {p['min']}°  ·  máxima {p['max']}°"
            tema.saida(f"  {tema.cor(faixa, tema.CINZA)}")
    else:
        tema.saida(tema.cor("  Não consegui pegar a previsão (sem internet?).", tema.CINZA))
    tema.saida()
    ms = manchetes(cfg, 7)
    if ms:
        tema.saida(tema.cor("  MANCHETES", tema.VIVO))
        for t in ms:
            tema.saida(f"  {tema.cor('▸', tema.VIVO)} {tema.realce(t[:78])}")
    else:
        tema.saida(tema.cor("  Sem manchetes agora.", tema.CINZA))
