"""
Rosa desabrochando.

Uma rosa rosa vai se abrindo camada por camada: primeiro as pétalas claras
do miolo, depois as mais escuras de fora. Tem caule e folhas verdes e alguns
"<3" flutuando em volta. Clique na janela para fechar.

Requer apenas a biblioteca padrão do Python (turtle). Rode com:
    python rosa.py
"""

import math
import random
import turtle

FUNDO = "#14000f"

# Camadas de pétalas, de dentro para fora:
# (quantidade, distância do centro, raio da pétala, cor)
CAMADAS = [
    (3, 8, 22, "#ffeef6"),
    (5, 24, 30, "#ffc2dd"),
    (7, 42, 38, "#ff8cc6"),
    (9, 62, 44, "#ff4fae"),
    (11, 84, 48, "#f0168f"),
    (13, 106, 50, "#c8007a"),
    (15, 126, 50, "#9a0063"),
]
ACHATAMENTO = 0.8       # "deita" a flor para dar sensação de profundidade
CENTRO = (0, 60)
VERDE = "#2fa860"


def misturar(cor, fator):
    """Clareia (fator > 0) ou escurece (fator < 0) uma cor #rrggbb."""
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    if fator >= 0:
        r, g, b = (int(c + (255 - c) * fator) for c in (r, g, b))
    else:
        r, g, b = (int(c * (1 + fator)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def anel(t, cx, cy, raio, cor, achatar=1.0, giro=0.0, espessura=7, passos=80):
    """Desenha uma pétala como um anel "pontilhado" (várias voltas lado a lado)."""
    for camada in range(espessura):
        r = raio - camada * 1.8
        tom = misturar(cor, 0.3 - camada * 0.08)
        for i in range(passos):
            a = 2 * math.pi * i / passos
            x = r * math.cos(a)
            y = r * math.sin(a) * achatar
            # gira o anel e aplica o achatamento da flor
            xr = x * math.cos(giro) - y * math.sin(giro)
            yr = x * math.sin(giro) + y * math.cos(giro)
            t.goto(cx + xr, cy + yr * ACHATAMENTO)
            t.dot(3, misturar(tom, random.uniform(-0.15, 0.1)))


def ponto_do_caule(s):
    """Curva de Bézier do miolo da flor até a parte de baixo da janela."""
    p0, p1, p2, p3 = (CENTRO[0], CENTRO[1] - 60), (10, -130), (40, -230), (130, -340)
    x = ((1 - s) ** 3 * p0[0] + 3 * (1 - s) ** 2 * s * p1[0]
         + 3 * (1 - s) * s ** 2 * p2[0] + s ** 3 * p3[0])
    y = ((1 - s) ** 3 * p0[1] + 3 * (1 - s) ** 2 * s * p1[1]
         + 3 * (1 - s) * s ** 2 * p2[1] + s ** 3 * p3[1])
    return x, y


def caule(t, tela):
    t.color(VERDE)
    t.pensize(3)
    t.penup()
    t.goto(ponto_do_caule(0))
    t.pendown()
    for i in range(61):
        t.goto(ponto_do_caule(i / 60))
        if i % 6 == 0:
            tela.update()
    t.penup()


def folhas(t, tela):
    # cada folha nasce num ponto do caule e se abre para um dos lados
    for s, lado, giro in ((0.42, -1, 0.2), (0.72, 1, -0.15)):
        x, y = ponto_do_caule(s)
        anel(t, x + lado * 34, y, 36, VERDE, achatar=0.4, giro=giro,
             espessura=4, passos=60)
        tela.update()


def coracoezinhos(t):
    t.color("#ff99cc")
    colocados = 0
    while colocados < 14:
        x, y = random.randint(-300, 300), random.randint(-260, 300)
        if math.hypot(x - CENTRO[0], y - CENTRO[1]) > 200:
            t.goto(x, y)
            t.write("<3", align="center", font=("Courier", 10, "bold"))
            colocados += 1


def main():
    tela = turtle.Screen()
    tela.title("Rose")
    tela.setup(800, 750)
    tela.bgcolor(FUNDO)
    tela.tracer(0)

    t = turtle.Turtle()
    t.hideturtle()
    t.penup()

    caule(t, tela)
    folhas(t, tela)

    # a flor desabrocha de dentro para fora
    cx, cy = CENTRO
    for qtd, distancia, raio, cor in CAMADAS:
        deslocamento = random.uniform(0, 2 * math.pi)
        for k in range(qtd):
            ang = deslocamento + 2 * math.pi * k / qtd
            px = cx + distancia * math.cos(ang)
            py = cy + distancia * math.sin(ang) * ACHATAMENTO
            anel(t, px, py, raio, cor, achatar=0.75, giro=ang)
            tela.update()

    coracoezinhos(t)
    t.goto(0, -340)
    t.color("white")
    t.write("Clique em qualquer lugar para fechar", align="center",
            font=("Arial", 10, "italic"))
    tela.update()
    tela.exitonclick()


if __name__ == "__main__":
    main()
