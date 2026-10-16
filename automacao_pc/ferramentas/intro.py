"""
Abertura animada no terminal, antes do menu (estilo painel de filme).

Divide o terminal em painéis, como um tmux, e anima todos ao mesmo tempo:
logo, passos da inicialização com dados reais do PC, memória e discos,
grade de cores, módulos carregando, circuito se desenhando e chuva de
caracteres. Qualquer tecla pula.

Usa só códigos ANSI (o Windows Terminal entende), sem bibliotecas extras.
"""

import math
import os
import random
import shutil
import sys
import time

from .util import WINDOWS, info_sistema, tamanho_legivel

QPS = 20            # quadros por segundo
DURACAO = 5.5       # segundos até "SISTEMA PRONTO"

VERMELHOS = [(70, 8, 20), (110, 14, 34), (150, 20, 48), (195, 28, 62), (235, 40, 78),
             (255, 70, 105), (255, 120, 150), (255, 170, 190), (255, 215, 225)]
ESCURO, MEDIO, FORTE, VIVO, CLARO = VERMELHOS[1], VERMELHOS[3], VERMELHOS[4], VERMELHOS[5], VERMELHOS[7]
BRANCO = (245, 245, 245)
CINZA = (115, 115, 125)
FUNDO = (10, 10, 14)

MODULOS = ["organizar", "duplicados", "discos", "limpeza", "inicio",
           "energia", "agendador", "remoto", "cofre"]

FONTE = {
    "A": [" ███ ", "█   █", "█████", "█   █", "█   █"],
    "U": ["█   █", "█   █", "█   █", "█   █", " ███ "],
    "T": ["█████", "  █  ", "  █  ", "  █  ", "  █  "],
    "O": [" ███ ", "█   █", "█   █", "█   █", " ███ "],
    "M": ["█   █", "██ ██", "█ █ █", "█   █", "█   █"],
    "C": [" ████", "█    ", "█    ", "█    ", " ████"],
    "P": ["████ ", "█   █", "████ ", "█    ", "█    "],
    " ": ["  ", "  ", "  ", "  ", "  "],
}


def letreiro(texto):
    """Texto em letras grandes (5 linhas)."""
    return [" ".join(FONTE[c][i] for c in texto) for i in range(5)]


# ------------------------------------------------------------------ terminal
def _preparar_windows():
    """Liga as cores ANSI no console do Windows e maximiza a janela."""
    import ctypes
    k32 = ctypes.windll.kernel32
    saida = k32.GetStdHandle(-11)
    modo = ctypes.c_uint32()
    if k32.GetConsoleMode(saida, ctypes.byref(modo)):
        k32.SetConsoleMode(saida, modo.value | 0x0004)   # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    janela = k32.GetConsoleWindow()
    if janela:
        ctypes.windll.user32.ShowWindow(janela, 3)         # SW_MAXIMIZE
        time.sleep(0.25)


class Teclado:
    """Percebe "alguma tecla apertada" sem travar a animação."""

    def __enter__(self):
        self._antigo = None
        if not WINDOWS and sys.stdin.isatty():
            import termios
            import tty
            self._antigo = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        return self

    def apertou(self):
        if WINDOWS:
            import msvcrt
            if not msvcrt.kbhit():
                return False
            while msvcrt.kbhit():
                msvcrt.getwch()
            return True
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            os.read(sys.stdin.fileno(), 64)
            return True
        return False

    def __exit__(self, *_):
        if self._antigo:
            import termios
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._antigo)


# ------------------------------------------------------------------- desenho
class Quadro:
    """Grade de células: caractere, cor da letra e cor do fundo."""

    def __init__(self, largura, altura):
        self.l, self.a = largura, altura
        self.car = [[" "] * largura for _ in range(altura)]
        self.fg = [[CINZA] * largura for _ in range(altura)]
        self.bg = [[FUNDO] * largura for _ in range(altura)]

    def escrever(self, x, y, texto, fg=CINZA, bg=None):
        if not 0 <= y < self.a:
            return
        for i, c in enumerate(texto):
            if 0 <= x + i < self.l:
                self.car[y][x + i] = c
                self.fg[y][x + i] = fg
                if bg:
                    self.bg[y][x + i] = bg

    def ansi(self, anterior=None):
        """Códigos ANSI do quadro. Com o quadro anterior, só redesenha o que mudou."""
        partes = []
        cor_atual = None
        for y in range(self.a):
            proximo_x = None   # onde o cursor está, se estiver nesta linha
            for x in range(self.l):
                celula = (self.car[y][x], self.fg[y][x], self.bg[y][x])
                if anterior and celula == (anterior.car[y][x], anterior.fg[y][x], anterior.bg[y][x]):
                    continue
                if proximo_x != x:
                    partes.append(f"\x1b[{y + 1};{x + 1}H")
                cor = celula[1:]
                if cor != cor_atual:
                    (r1, g1, b1), (r2, g2, b2) = cor
                    partes.append(f"\x1b[38;2;{r1};{g1};{b1};48;2;{r2};{g2};{b2}m")
                    cor_atual = cor
                partes.append(celula[0])
                proximo_x = x + 1
        partes.append("\x1b[0m")
        return "".join(partes)


class Painel:
    def __init__(self, x, y, l, a, titulo):
        self.x, self.y, self.l, self.a, self.titulo = x, y, max(l, 4), max(a, 3), titulo

    @property
    def dentro(self):
        return self.x + 1, self.y + 1, self.l - 2, self.a - 2

    def moldura(self, q, destaque):
        q.escrever(self.x, self.y, "┌" + "─" * (self.l - 2) + "┐", ESCURO)
        for yy in range(self.y + 1, self.y + self.a - 1):
            q.escrever(self.x, yy, "│", ESCURO)
            q.escrever(self.x + self.l - 1, yy, "│", ESCURO)
        q.escrever(self.x, self.y + self.a - 1, "└" + "─" * (self.l - 2) + "┘", ESCURO)
        q.escrever(self.x + 2, self.y, f"[ {self.titulo} ]"[: self.l - 4], VIVO if destaque else FORTE)


def _misturar(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _barra(valor, largura):
    cheios = round(max(0.0, min(1.0, valor)) * largura)
    return "█" * cheios + "░" * (largura - cheios)


# ------------------------------------------------------------------ abertura
class Abertura:
    def __init__(self, largura, altura, info):
        self.l, self.a, self.info = largura, altura, info
        self.rng = random.Random()
        mem = info["memoria_usada"] / info["memoria_total"] if info["memoria_total"] else 0
        self.passos = [
            (0.3, f"usuário ...................... {info['usuario']}@{info['maquina']}"),
            (0.8, f"sistema ...................... {info['sistema']}"),
            (1.4, "configuração ................. carregada"),
            (2.0, f"discos encontrados ........... {len(info['discos'])}"),
            (2.6, f"memória em uso ............... {mem:.0%}"),
            (3.2, f"ligado há .................... {info['ligado']}"),
            (3.8, f"módulos prontos .............. {len(MODULOS)}"),
            (4.6, "bem-vindo."),
        ]
        self.gotas = []
        self.trilhas = {}
        self.pontas = []
        self.montar()

    def montar(self):
        l, a = self.l, self.a
        c1, c2 = int(l * 0.40), int(l * 0.68)
        meio = 1 + int((a - 2) * 0.55)
        self.p_logo = Painel(0, 1, c1, meio - 1, "AUTOMAÇÃO PC")
        self.p_sistema = Painel(0, meio, c1, a - 1 - meio, "SISTEMA")
        meio2 = 1 + (a - 2) // 2
        self.p_espectro = Painel(c1, 1, c2 - c1, meio2 - 1, "ESPECTRO")
        self.p_modulos = Painel(c1, meio2, c2 - c1, a - 1 - meio2, "MÓDULOS")
        self.p_circuito = Painel(c2, 1, l - c2, meio2 - 1, "CIRCUITO")
        self.p_matriz = Painel(c2, meio2, l - c2, a - 1 - meio2, "MATRIZ")
        self.paineis = [self.p_logo, self.p_sistema, self.p_espectro,
                        self.p_modulos, self.p_circuito, self.p_matriz]

    # ---- painéis ----------------------------------------------------------
    def logo(self, q, t):
        x, y, l, a = self.p_logo.dentro
        linhas = letreiro("AUTOMACAO") if l >= 56 else letreiro("PC")
        largura = len(linhas[0])
        x0 = x + max(0, (l - largura) // 2)
        for i, linha in enumerate(linhas):
            for j, c in enumerate(linha):
                if c != " ":
                    brilho = (math.sin(t * 4 - j * 0.15) + 1) / 2   # faixa de luz passando
                    q.escrever(x0 + j, y + 1 + i, c, _misturar(MEDIO, CLARO, brilho))
        base = y + 8
        for i, (inicio, texto) in enumerate(p for p in self.passos if p[0] <= t):
            if base + i >= y + a:
                break
            digitado = texto[: int((t - inicio) * 80)]
            q.escrever(x + 2, base + i, "> ", FORTE)
            q.escrever(x + 4, base + i, digitado[: l - 5], BRANCO if texto == "bem-vindo." else CLARO)

    def sistema(self, q, t):
        x, y, l, a = self.p_sistema.dentro
        info = self.info
        largura = max(8, min(36, l - 26))
        enchendo = min(1.0, t / 2.5)   # as barras sobem até o valor real
        linha = y
        if info["memoria_total"]:
            uso = info["memoria_usada"] / info["memoria_total"] * enchendo
            q.escrever(x + 1, linha, "MEM ", CINZA)
            q.escrever(x + 5, linha, _barra(uso, largura), VIVO)
            q.escrever(x + 6 + largura, linha,
                       f"{tamanho_legivel(info['memoria_usada'])} / {tamanho_legivel(info['memoria_total'])}", CINZA)
            linha += 2
        for d in info["discos"][: max(0, a - 6)]:
            uso = (1 - d["livre"] / d["total"]) * enchendo if d["total"] else 0
            q.escrever(x + 1, linha, f"{d['raiz'][:3]:<4}", CINZA)
            q.escrever(x + 5, linha, _barra(uso, largura), FORTE if uso < 0.9 else BRANCO)
            q.escrever(x + 6 + largura, linha, f"{tamanho_legivel(d['livre'])} livres", CINZA)
            linha += 1
        linha += 1
        q.escrever(x + 1, linha, f"{info['nucleos']} núcleos  ·  ligado há {info['ligado']}"[: l - 2], CLARO)
        onda = "".join("▁▂▃▄▅▆▇█"[int((math.sin(t * 6 + i * 0.5) + 1) * 3.5)] for i in range(max(0, l - 2)))
        q.escrever(x + 1, min(y + a - 1, linha + 2), onda, MEDIO)

    def espectro(self, q, t):
        x, y, l, a = self.p_espectro.dentro
        colunas = max(1, (l - 5) // 5)
        n = len(VERMELHOS)
        for linha in range(a):
            q.escrever(x, y + linha, f"{linha:>3}", CINZA)
            for c in range(colunas):
                i = (c + linha + int(t * 8)) % (2 * n)
                i = i if i < n else 2 * n - 1 - i
                q.escrever(x + 4 + c * 5, y + linha, " gYw ", FUNDO if i > 5 else BRANCO, VERMELHOS[i])

    def modulos(self, q, t):
        x, y, l, a = self.p_modulos.dentro
        progresso = min(1.0, t / (DURACAO - 0.8))
        prontos = int(progresso * len(MODULOS))
        for i, nome in enumerate(MODULOS[:a]):
            if i < prontos:
                estado, cor = "[  OK  ]", VIVO
            elif i == prontos:
                estado, cor = "[" + "|/-\\"[int(t * 10) % 4].center(6) + "]", BRANCO
            else:
                estado, cor = "[      ]", ESCURO
            pontos = "." * max(1, l - len(nome) - 14)
            q.escrever(x + 1, y + i, f"{i + 1:02} {nome} {pontos} ", CINZA if i > prontos else CLARO)
            q.escrever(x + l - 9, y + i, estado, cor)

    def circuito(self, q, t):
        x, y, l, a = self.p_circuito.dentro
        if not self.pontas:
            self.pontas = [[self.rng.randrange(l), self.rng.randrange(a), self.rng.randrange(4)]
                           for _ in range(6)]
        for p in self.pontas:
            for _ in range(2):
                if self.rng.random() < 0.25:
                    p[2] = (p[2] + self.rng.choice((1, 3))) % 4
                dx, dy = ((1, 0), (0, 1), (-1, 0), (0, -1))[p[2]]
                p[0], p[1] = (p[0] + dx) % l, (p[1] + dy) % a
                self.trilhas[(p[0], p[1])] = ("─" if dx else "│", t)
        self.trilhas = {k: v for k, v in self.trilhas.items() if t - v[1] < 3}   # rastro antigo some
        for (cx, cy), (c, quando) in self.trilhas.items():
            idade = t - quando
            q.escrever(x + cx, y + cy, c, BRANCO if idade < 0.15 else (VIVO if idade < 1 else MEDIO))
        for p in self.pontas:
            q.escrever(x + p[0], y + p[1], "■", BRANCO)

    def matriz(self, q, t):
        x, y, l, a = self.p_matriz.dentro
        simbolos = "0123456789ABCDEF<>{}[]=+*#$%&@/\\|:;"
        if self.rng.random() < 0.9:
            self.gotas.append([self.rng.randrange(l), 0.0, self.rng.uniform(0.4, 1.2)])
        vivas = []
        for g in self.gotas:
            g[1] += g[2]
            for k in range(8):
                gy = int(g[1]) - k
                if 0 <= gy < a:
                    cor = BRANCO if k == 0 else _misturar(VIVO, ESCURO, k / 8)
                    q.escrever(x + g[0], y + gy, self.rng.choice(simbolos), cor)
            if g[1] - 8 < a:
                vivas.append(g)
        self.gotas = vivas

    # ---- quadro completo -------------------------------------------------
    def quadro(self, t):
        q = Quadro(self.l, self.a)
        abas = [" automacao_pc ", " cofre ", " sistema "]
        x = 0
        for i, aba in enumerate(abas):
            q.escrever(x, 0, aba, FUNDO if i == 0 else CINZA, VIVO if i == 0 else ESCURO)
            x += len(aba) + 1
        relogio = time.strftime(" %d/%m/%Y  %H:%M:%S ")
        q.escrever(self.l - len(relogio), 0, relogio, BRANCO, ESCURO)

        destaque = int(t * 1.5) % len(self.paineis)
        for i, p in enumerate(self.paineis):
            p.moldura(q, i == destaque)
        self.logo(q, t)
        self.sistema(q, t)
        self.espectro(q, t)
        self.modulos(q, t)
        self.circuito(q, t)
        self.matriz(q, t)

        progresso = min(1.0, t / DURACAO)
        largura = max(10, self.l - 52)
        rodape = f" INICIANDO [{_barra(progresso, largura)}] {progresso:4.0%}   qualquer tecla pula "
        q.escrever(0, self.a - 1, rodape.ljust(self.l), CLARO, ESCURO)

        if t >= DURACAO:   # selo final
            texto = "  S I S T E M A   P R O N T O  "
            cx, cy = (self.l - len(texto)) // 2, self.a // 2
            cor = BRANCO if int(t * 6) % 2 else VIVO
            q.escrever(cx - 2, cy - 1, "╔" + "═" * (len(texto) + 2) + "╗", cor)
            q.escrever(cx - 2, cy, "║ " + texto + " ║", FUNDO, cor)
            q.escrever(cx - 2, cy + 1, "╚" + "═" * (len(texto) + 2) + "╝", cor)
        return q


def executar():
    """Mostra a abertura. Não faz nada se não houver um terminal de verdade."""
    if sys.stdout is None or not sys.stdout.isatty() or sys.stdin is None or not sys.stdin.isatty():
        return
    if WINDOWS:
        try:
            _preparar_windows()
        except OSError:
            pass
    colunas, linhas = shutil.get_terminal_size((120, 36))
    if colunas < 80 or linhas < 24:
        return   # janela pequena demais para o efeito
    abertura = Abertura(colunas - 1, linhas, info_sistema())

    sys.stdout.write("\x1b[?1049h\x1b[?25l")   # tela alternativa, sem cursor
    inicio = time.time()
    try:
        anterior = None
        with Teclado() as teclado:
            while True:
                t = time.time() - inicio
                quadro = abertura.quadro(t)
                sys.stdout.write(quadro.ansi(anterior))
                anterior = quadro
                sys.stdout.flush()
                if t > DURACAO + 0.9 or teclado.apertou():
                    break
                time.sleep(max(0.0, 1 / QPS - (time.time() - inicio - t)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
