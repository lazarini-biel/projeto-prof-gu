"""
Love Heart - "Eu te amo" em 20 idiomas formando um coração.

As frases vão aparecendo uma a uma até preencher um coração vermelho sobre
fundo preto. Quando o coração fica pronto, ele começa a "pulsar".

Requer apenas a biblioteca padrão do Python (tkinter). Rode com:
    python love_heart.py

Teclas: R = recomeçar | Esc = sair
"""

import math
import random
import tkinter as tk
from tkinter import font as tkfont

LARGURA, ALTURA = 900, 800
FUNDO = "#000000"

FRASES = {
    "Inglês": "I love you",
    "Português": "Eu te amo",
    "Espanhol": "Te amo",
    "Francês": "Je t'aime",
    "Alemão": "Ich liebe dich",
    "Italiano": "Ti amo",
    "Japonês": "愛してる",
    "Coreano": "사랑해",
    "Chinês": "我爱你",
    "Russo": "Я тебя люблю",
    "Grego": "Σ' αγαπώ",
    "Turco": "Seni seviyorum",
    "Indonésio": "Aku cinta kamu",
    "Tailandês": "ฉันรักเธอ",
    "Holandês": "Ik hou van jou",
    "Sueco": "Jag älskar dig",
    "Polonês": "Kocham cię",
    "Vietnamita": "Anh yêu em",
    "Filipino": "Mahal kita",
    "Ucraniano": "Я тебе кохаю",
}

# Tons de vermelho usados nas palavras
VERMELHOS = ["#ff1f3d", "#ff2e4d", "#e8102e", "#ff4d5e", "#d90429", "#ff3355"]

# Tamanhos de fonte: primeiro as palavras maiores, depois as menores
# preenchem os buracos que sobraram.
TAMANHOS = [13, 11, 10, 9, 8, 7]
PASSO_GRADE = 3            # distância (px) entre posições testadas
MARGEM = 1                 # espaço mínimo entre palavras (px)
PALAVRAS_POR_QUADRO = 1    # quantas palavras surgem a cada quadro
INTERVALO_MS = 12          # tempo entre quadros
CELULA = 32                # tamanho da célula do índice espacial


def contorno_coracao(cx, cy, escala, pontos=600):
    """Curva clássica do coração:
        x = 16·sen³(t)
        y = 13·cos(t) - 5·cos(2t) - 2·cos(3t) - cos(4t)
    """
    poligono = []
    for i in range(pontos):
        t = 2 * math.pi * i / pontos
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        poligono.append((cx + x * escala, cy - y * escala))  # y do canvas cresce para baixo
    return poligono


def intervalos_por_linha(poligono, y0, y1):
    """Para cada linha y, os trechos [xa, xb] que ficam dentro do coração."""
    linhas = {}
    n = len(poligono)
    for y in range(int(y0), int(y1) + 1):
        cruzamentos = []
        for i in range(n):
            xa, ya = poligono[i]
            xb, yb = poligono[(i + 1) % n]
            if (ya > y) != (yb > y):
                cruzamentos.append(xa + (y - ya) * (xb - xa) / (yb - ya))
        cruzamentos.sort()
        linhas[y] = list(zip(cruzamentos[::2], cruzamentos[1::2]))
    return linhas


class CoracaoDeAmor:
    def __init__(self, raiz):
        self.raiz = raiz
        raiz.title("Love Heart")
        raiz.configure(bg=FUNDO)
        raiz.resizable(False, False)

        self.canvas = tk.Canvas(raiz, width=LARGURA, height=ALTURA,
                                bg=FUNDO, highlightthickness=0)
        self.canvas.pack()

        # geometria do coração
        escala = min(LARGURA, ALTURA) / 36
        cx, cy = LARGURA / 2, ALTURA / 2 - 2.5 * escala
        poligono = contorno_coracao(cx, cy, escala)
        xs = [p[0] for p in poligono]
        ys = [p[1] for p in poligono]
        self.limites = (min(xs), min(ys), max(xs), max(ys))
        self.linhas = intervalos_por_linha(poligono, min(ys), max(ys))

        familia = self._escolher_fonte()
        self.fontes = {t: tkfont.Font(family=familia, size=t, weight="bold")
                       for t in TAMANHOS}
        # mede cada frase uma vez só. A altura vem do tamanho da fonte (e não
        # de "linespace"), que inclui muito espaço vazio em fontes asiáticas.
        self.medidas = {t: [(f, self.fontes[t].measure(f), round(t * 1.4))
                            for f in FRASES.values()]
                        for t in TAMANHOS}

        raiz.bind("<Escape>", lambda e: raiz.destroy())
        raiz.bind("<r>", lambda e: self.reiniciar())
        raiz.bind("<R>", lambda e: self.reiniciar())

        self._job = None
        self.reiniciar()

    @staticmethod
    def _escolher_fonte():
        """Escolhe uma fonte com boa cobertura de alfabetos."""
        disponiveis = set(tkfont.families())
        for nome in ("Segoe UI", "Arial Unicode MS", "Noto Sans",
                     "DejaVu Sans", "Helvetica"):
            if nome in disponiveis:
                return nome
        return "TkDefaultFont"

    def reiniciar(self):
        if self._job:
            self.raiz.after_cancel(self._job)
        self.canvas.delete("all")
        self.itens = []
        self.grade = {}  # índice espacial: célula -> caixas ocupadas
        self.gerador = self._posicoes()
        self._job = self.raiz.after(300, self.passo)

    # --- geometria -----------------------------------------------------
    def _linha_contem(self, y, x0, x1):
        """O trecho horizontal [x0, x1] na altura y está todo no coração?"""
        for a, b in self.linhas.get(int(y), ()):
            if a <= x0 and x1 <= b:
                return True
        return False

    def _cabe_no_coracao(self, x0, y0, x1, y1):
        return (self._linha_contem(y0, x0, x1)
                and self._linha_contem((y0 + y1) / 2, x0, x1)
                and self._linha_contem(y1, x0, x1))

    def _celulas(self, x0, y0, x1, y1):
        for gx in range(int(x0) // CELULA, int(x1) // CELULA + 1):
            for gy in range(int(y0) // CELULA, int(y1) // CELULA + 1):
                yield gx, gy

    def _livre(self, x0, y0, x1, y1):
        for c in self._celulas(x0, y0, x1, y1):
            for a0, b0, a1, b1 in self.grade.get(c, ()):
                if (x0 < a1 + MARGEM and x1 > a0 - MARGEM and
                        y0 < b1 + MARGEM and y1 > b0 - MARGEM):
                    return False
        return True

    def _ocupar(self, caixa):
        for c in self._celulas(*caixa):
            self.grade.setdefault(c, []).append(caixa)

    # --- preenchimento -------------------------------------------------
    def _posicoes(self):
        """Gera (texto, x, y, tamanho) para cada palavra que cabe; (x, y) é o centro."""
        esq, topo, dir_, base = self.limites
        pontos = [(x, y)
                  for y in range(int(topo), int(base), PASSO_GRADE)
                  for x in range(int(esq), int(dir_), PASSO_GRADE)]
        for tamanho in TAMANHOS:
            random.shuffle(pontos)
            opcoes = self.medidas[tamanho]
            for x, y in pontos:
                # sorteia a ordem das frases e usa a primeira que couber
                for texto, larg, alt in random.sample(opcoes, len(opcoes)):
                    caixa = (x - larg / 2, y - alt / 2, x + larg / 2, y + alt / 2)
                    if self._cabe_no_coracao(*caixa) and self._livre(*caixa):
                        self._ocupar(caixa)
                        yield texto, x, y, tamanho
                        break

    def passo(self):
        for _ in range(PALAVRAS_POR_QUADRO):
            try:
                texto, x, y, tamanho = next(self.gerador)
            except StopIteration:
                self.batida(0)
                return
            self.itens.append(self.canvas.create_text(
                x, y, text=texto, anchor="center", font=self.fontes[tamanho],
                fill=random.choice(VERMELHOS)))
        self._job = self.raiz.after(INTERVALO_MS, self.passo)

    # --- batimento -----------------------------------------------------
    def batida(self, quadro):
        """Faz o coração 'pulsar' (tum-tum ... tum-tum) mudando o brilho."""
        t = quadro / 50 * 2 * math.pi
        pulso = max(0.0, math.sin(t)) ** 8 + 0.6 * max(0.0, math.sin(t - 0.9)) ** 8
        pulso = min(1.0, pulso)
        r = 190 + int(65 * pulso)
        g = 10 + int(70 * pulso)
        cor = f"#{r:02x}{g:02x}{g + 15:02x}"
        for item in self.itens[quadro % 2::2]:
            self.canvas.itemconfigure(item, fill=cor)
        self._job = self.raiz.after(30, self.batida, quadro + 1)


def main():
    raiz = tk.Tk()
    CoracaoDeAmor(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
