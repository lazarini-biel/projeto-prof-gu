"""
Arte da SPARTA para as aberturas: o elmo espartano como uma "máscara"
(grade de intensidade 0..1) que vira arte em caracteres, e a palavra SPARTA.

A máscara é geométrica (crista + cúpula + protetores laterais + nariz +
olhos inclinados), então se adapta a qualquer tamanho. `cartaz()` monta o
elmo já bem proporcionado (cada caractere é ~2x mais alto que largo) com a
palavra SPARTA embaixo, para as janelas das aberturas fatiarem.
"""

import math


def _intensidade(x, y):
    """Metal do elmo em (x em -1..1, y em 0..1): 1 cheio, 0 vazio."""
    ax = abs(x)
    # crista (plume): pente simétrico no topo
    if y < 0.30:
        w = 0.24 * math.sin(math.pi * (y / 0.30)) ** 0.65
        if ax < max(w, 0.028):
            return 1.0
    # base da crista, ligando ao casco
    if 0.22 <= y <= 0.32 and ax < 0.13:
        return 1.0
    # cúpula (elipse cheia)
    if ((x / 0.66) ** 2 + ((y - 0.52) / 0.30) ** 2) <= 1.0 and 0.26 <= y <= 0.56:
        return 1.0
    # faixa da testa
    if 0.50 <= y <= 0.575 and ax < 0.52:
        return 1.0
    # protetores laterais (bochechas), afinando até a ponta embaixo
    if 0.50 <= y <= 1.0:
        f = (y - 0.50) / 0.50
        externo = 0.62 - 0.46 * f
        interno = 0.46 - 0.30 * f
        if interno <= ax <= externo:
            return 1.0
    # nariz
    if 0.52 <= y <= 0.90 and ax < 0.055:
        return 1.0
    # sobrancelha "brava": cunha inclinada sobre os olhos
    if 0.56 <= y <= 0.70:
        t = (y - 0.56) / 0.14
        if 0.055 < ax < 0.055 + 0.30 * (1 - t):
            return 1.0
    return 0.0


def elmo(largura, altura):
    """Grade altura×largura com a intensidade do elmo (bordas realçadas)."""
    g = [[_intensidade((lx / (largura - 1)) * 2 - 1, ly / (altura - 1))
          for lx in range(largura)] for ly in range(altura)]
    _realcar_bordas(g)
    return g


def _realcar_bordas(g):
    """Miolo um pouco mais fraco, bordas fortes (dá volume quando colorido)."""
    a, l = len(g), len(g[0])
    orig = [linha[:] for linha in g]
    for y in range(a):
        for x in range(l):
            if orig[y][x] <= 0:
                continue
            borda = any(
                not (0 <= y + dy < a and 0 <= x + dx < l and orig[y + dy][x + dx] > 0)
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)))
            g[y][x] = 1.0 if borda else 0.72


# Letras grandes para "SPARTA" (5 linhas)
_FONTE = {
    "S": [" ███", "█   ", " ██ ", "   █", "███ "],
    "P": ["███ ", "█  █", "███ ", "█   ", "█   "],
    "A": [" ██ ", "█  █", "████", "█  █", "█  █"],
    "R": ["███ ", "█  █", "███ ", "█ █ ", "█  █"],
    "T": ["███", " █ ", " █ ", " █ ", " █ "],
}


def palavra_sparta():
    """A palavra SPARTA em 5 linhas de blocos."""
    return ["  ".join(_FONTE[c][i] for c in "SPARTA") for i in range(5)]


def cartaz(cols, rows):
    """Grade cols×rows com o elmo (proporção certa, centralizado) e SPARTA
    embaixo. O elmo é desenhado ~2:1 em caracteres para parecer quadrado na
    tela, com margens vazias ao redor (letterbox)."""
    g = [[0.0] * cols for _ in range(rows)]
    palavra = palavra_sparta()
    espaco_palavra = len(palavra) + 1
    # bloco do elmo: largura = 2× altura (caractere é ~2x mais alto que largo)
    hb = max(8, min(rows - espaco_palavra, cols // 2))
    wb = min(cols, hb * 2)
    hb = min(hb, wb // 2)
    if hb < 6:
        return g
    m = elmo(wb, hb)
    ox = (cols - wb) // 2
    oy = max(0, (rows - hb - espaco_palavra) // 2)
    for y in range(hb):
        for x in range(wb):
            if 0 <= oy + y < rows and 0 <= ox + x < cols:
                g[oy + y][ox + x] = m[y][x]
    # palavra SPARTA logo abaixo do elmo
    pl = len(palavra[0])
    px = (cols - pl) // 2
    py = oy + hb + 1
    for i, linha in enumerate(palavra):
        for j, c in enumerate(linha):
            if c != " " and 0 <= py + i < rows and 0 <= px + j < cols:
                g[py + i][px + j] = 1.5
    return g


# Fonte GRANDE e grossa para o título do menu (7 linhas, traço de 2).
_FONTE_GRANDE = {
    "S": ["██████", "██    ", "██    ", "██████", "    ██", "    ██", "██████"],
    "P": ["██████", "██  ██", "██  ██", "██████", "██    ", "██    ", "██    "],
    "A": [" ████ ", "██  ██", "██  ██", "██████", "██  ██", "██  ██", "██  ██"],
    "R": ["██████", "██  ██", "██  ██", "██████", "████  ", "██ ██ ", "██  ██"],
    "T": ["██████", "  ██  ", "  ██  ", "  ██  ", "  ██  ", "  ██  ", "  ██  "],
}


def palavra_sparta_grande(sep="  "):
    """SPARTA em 7 linhas, bem largo e grosso (para o título do menu)."""
    return [sep.join(_FONTE_GRANDE[c][i] for c in "SPARTA") for i in range(7)]
