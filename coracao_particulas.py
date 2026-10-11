"""
Coração de partículas.

Centenas de partículas roxas começam espalhadas pela tela e, aos poucos,
se juntam até formar o contorno de um coração. No final elas ficam
"cintilando" no lugar.

Requer apenas a biblioteca padrão do Python (tkinter). Rode com:
    python coracao_particulas.py

Teclas: R = recomeçar | Esc = sair
"""

import math
import random
import tkinter as tk

LARGURA, ALTURA = 800, 800
FUNDO = "#000000"
CORES = ["#9b5cff", "#a66bff", "#8f4dff", "#b07cff", "#9966ff"]

N_PARTICULAS = 700
ESPALHAMENTO = 9       # quão "grosso" fica o contorno (desvio em px)
VELOCIDADE = 0.012     # fração do caminho percorrida a cada quadro
QUADRO_MS = 16         # ~60 quadros por segundo


def ponto_do_coracao(t, escala, cx, cy):
    """Curva do coração: x = 16·sen³(t), y = 13cos(t) - 5cos(2t) - 2cos(3t) - cos(4t)."""
    x = 16 * math.sin(t) ** 3
    y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
    return cx + x * escala, cy - y * escala


class Particula:
    def __init__(self, canvas, alvo):
        self.canvas = canvas
        self.alvo = alvo
        self.x = random.uniform(0, LARGURA)
        self.y = random.uniform(0, ALTURA)
        self.fase = random.uniform(0, 2 * math.pi)
        tamanho = random.choice((7, 8, 9, 10))
        self.item = canvas.create_text(self.x, self.y, text="✱",
                                       fill=random.choice(CORES),
                                       font=("Arial", tamanho, "bold"))

    def mover(self, quadro, velocidade):
        ax, ay = self.alvo
        # vai em direção ao alvo, com um leve balanço que diminui com o tempo
        balanco = max(0.0, 1.5 - quadro / 400)
        self.x += (ax - self.x) * velocidade + random.uniform(-balanco, balanco)
        self.y += (ay - self.y) * velocidade + random.uniform(-balanco, balanco)
        # depois de chegar, fica cintilando em volta do alvo
        brilho = 0.6 * math.sin(quadro / 10 + self.fase)
        self.canvas.coords(self.item, self.x + brilho, self.y + brilho)


class CoracaoDeParticulas:
    def __init__(self, raiz):
        self.raiz = raiz
        raiz.title("Heart")
        raiz.configure(bg=FUNDO)
        self.canvas = tk.Canvas(raiz, width=LARGURA, height=ALTURA,
                                bg=FUNDO, highlightthickness=0)
        self.canvas.pack()
        raiz.bind("<Escape>", lambda e: raiz.destroy())
        raiz.bind("<r>", lambda e: self.reiniciar())
        raiz.bind("<R>", lambda e: self.reiniciar())
        self._job = None
        self.reiniciar()

    def _alvos(self):
        escala = min(LARGURA, ALTURA) / 40
        cx, cy = LARGURA / 2, ALTURA / 2 - escala * 2
        alvos = []
        for _ in range(N_PARTICULAS):
            t = random.uniform(0, 2 * math.pi)
            x, y = ponto_do_coracao(t, escala, cx, cy)
            alvos.append((x + random.gauss(0, ESPALHAMENTO),
                          y + random.gauss(0, ESPALHAMENTO)))
        return alvos

    def reiniciar(self):
        if self._job:
            self.raiz.after_cancel(self._job)
        self.canvas.delete("all")
        self.particulas = [Particula(self.canvas, alvo) for alvo in self._alvos()]
        self.quadro = 0
        self._job = self.raiz.after(500, self.animar)

    def animar(self):
        self.quadro += 1
        # começa devagar e vai acelerando, como no vídeo
        velocidade = VELOCIDADE * min(1.0, self.quadro / 600) ** 2 + 0.001
        for p in self.particulas:
            p.mover(self.quadro, velocidade)
        self._job = self.raiz.after(QUADRO_MS, self.animar)


def main():
    raiz = tk.Tk()
    CoracaoDeParticulas(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
