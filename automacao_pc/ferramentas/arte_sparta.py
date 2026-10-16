"""
Arte da SPARTA para as aberturas: o elmo espartano como uma "máscara"
(grade de intensidade 0..1) que vira arte em caracteres, e a palavra
SPARTA em letras grandes.

A máscara é geométrica (cúpula + protetores laterais + barra do nariz +
crista), então se adapta a qualquer tamanho. Cada célula vale de 0 (vazio)
a 1 (metal cheio); as bordas ficam perto de 1, o miolo um pouco menor,
para dar volume quando colorida em tons de vermelho.
"""

import math


def elmo(largura, altura):
    """Grade altura×largura com a intensidade do elmo em cada célula (0..1)."""
    g = [[0.0] * largura for _ in range(altura)]
    # células do terminal são ~2x mais altas que largas: corrige a proporção
    for ly in range(altura):
        y = ly / (altura - 1)                     # 0 topo .. 1 base
        for lx in range(largura):
            x = (lx / (largura - 1)) * 2 - 1       # -1 esquerda .. 1 direita
            g[ly][lx] = _intensidade(x, y)
    _realcar_bordas(g)
    return g


def _intensidade(x, y):
    ax = abs(x)

    # crista (plume) no topo, um leve arco para trás
    if y < 0.20:
        desloc = 0.12 * math.sin((0.20 - y) * 6)
        if abs(x - desloc) < 0.11 + y * 0.25:
            return 1.0

    # cúpula: meia-elipse superior
    dome = (x / 0.70) ** 2 + ((y - 0.46) / 0.42) ** 2
    na_cupula = dome <= 1.0 and 0.14 <= y <= 0.5

    # protetores laterais (bochechas): descem dos lados estreitando
    if 0.42 <= y <= 1.0:
        externo = 0.72 - 0.30 * (y - 0.42)
        interno = 0.34 - 0.06 * (y - 0.42)
        if interno <= ax <= externo:
            return 1.0

    # barra central do nariz
    if 0.44 <= y <= 0.96 and ax < 0.085:
        return 1.0

    # barra da testa (sobrancelha), ligando cúpula e nariz, acima dos olhos
    if 0.40 <= y <= 0.50 and ax < 0.52:
        return 1.0

    return 1.0 if na_cupula else 0.0


def _realcar_bordas(g):
    """Deixa o miolo um pouco mais fraco e as bordas fortes (dá volume)."""
    a, l = len(g), len(g[0])
    orig = [linha[:] for linha in g]
    for y in range(a):
        for x in range(l):
            if orig[y][x] <= 0:
                continue
            vizinhos_vazios = any(
                0 <= y + dy < a and 0 <= x + dx < l and orig[y + dy][x + dx] <= 0
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)))
            g[y][x] = 1.0 if vizinhos_vazios else 0.72


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
    letras = "SPARTA"
    return ["  ".join(_FONTE[c][i] for c in letras) for i in range(5)]
