"""
Abertura animada no terminal, antes do menu, no estilo "rice" de tmux:
várias telas de terminal lado a lado, todas se mexendo ao mesmo tempo.

  ┌ abas ─────────────────────────────────────────────────── data/hora ┐
  │ prompt + asas em ASCII  │ caixas + cadeado ASCII    │ fila de tarefas │
  │                         │ aviso                     │ canos           │
  │ monitor (htop) com      │ tabela de cores 40m..47m  │                 │
  │ processos reais         │ prompt + tanques em pixel │ chuva (cmatrix) │
  └────────────────────────────────────────────────────────────────────┘

Os números (memória, discos, processos, tempo ligado, tarefas) são reais.
Qualquer tecla pula. Usa só códigos ANSI, sem bibliotecas extras.
"""

import math
import os
import random
import shutil
import sys
import time

from .arte_sparta import elmo, palavra_sparta
from .popups import Tempestade
from .util import WINDOWS, info_sistema, processos_detalhados, tamanho_legivel

QPS = 20
DURACAO = 6.5

# Paleta: cinza de fundo como no tmux + vermelhos
FUNDO = (38, 38, 41)
FUNDO_ESCURO = (28, 28, 30)
TEXTO = (205, 205, 210)
CINZA = (120, 120, 128)
BRANCO = (250, 250, 250)
PRETO = (16, 16, 18)
VERMELHOS = [(92, 22, 34), (128, 24, 44), (170, 28, 56), (205, 34, 66), (232, 52, 86),
             (245, 92, 122), (250, 140, 165), (252, 190, 205), (255, 228, 234)]
ESCURO, MEDIO, FORTE, VIVO = VERMELHOS[0], VERMELHOS[2], VERMELHOS[3], VERMELHOS[4]
ROSA, CLARO = VERMELHOS[5], VERMELHOS[6]


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

    def ler_tecla(self):
        """Devolve 'up','down','enter','esc','space', um dígito/letra, ou None."""
        if WINDOWS:
            import msvcrt
            if not msvcrt.kbhit():
                return None
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):
                return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(msvcrt.getwch())
            if ch in ("\r", "\n"):
                return "enter"
            if ch == "\x1b":
                return "esc"
            if ch == " ":
                return "space"
            return ch
        import select
        if not select.select([sys.stdin], [], [], 0)[0]:
            return None
        dados = os.read(sys.stdin.fileno(), 6)
        if not dados:
            return None
        if dados[:1] == b"\x1b":
            if dados[1:2] == b"[" and len(dados) > 2:
                return {"A": "up", "B": "down", "C": "right", "D": "left"}.get(chr(dados[2]))
            return "esc"
        c = dados[:1].decode("latin-1", "ignore")
        if c in ("\r", "\n"):
            return "enter"
        if c == " ":
            return "space"
        return c

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
        self.fg = [[TEXTO] * largura for _ in range(altura)]
        self.bg = [[FUNDO] * largura for _ in range(altura)]

    def escrever(self, x, y, texto, fg=TEXTO, bg=None, ate=None):
        """Escreve na linha y a partir de x; `ate` corta o texto nessa coluna."""
        if not 0 <= y < self.a:
            return
        limite = min(self.l, self.l if ate is None else ate)
        for i, c in enumerate(texto):
            if 0 <= x + i < limite:
                self.car[y][x + i] = c
                self.fg[y][x + i] = fg
                if bg:
                    self.bg[y][x + i] = bg

    def pintar_fundo(self, x, y, largura, altura, cor):
        for yy in range(max(0, y), min(self.a, y + altura)):
            for xx in range(max(0, x), min(self.l, x + largura)):
                self.bg[yy][xx] = cor

    def ansi(self, anterior=None):
        """Códigos ANSI do quadro. Com o quadro anterior, só redesenha o que mudou."""
        partes = []
        cor_atual = None
        for y in range(self.a):
            proximo_x = None
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


def _misturar(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


# --------------------------------------------------------------- arte ASCII
def asas(largura, altura, texto):
    """Asas abertas no estilo figlet ("dXb", "9XP") com um texto no meio.
    Devolve (linhas, linha do texto, (coluna inicial do texto, largura))."""
    meio = largura // 2
    grade = [[" "] * largura for _ in range(altura)]
    faixa = max(2, altura // 3)            # até aqui: pontas das penas subindo

    def por(x, y, c):
        if 0 <= x < largura and 0 <= y < altura:
            grade[y][x] = c

    for r in range(altura):
        if r == 0:
            for frac in (0.95, 0.62, 0.3):
                d = int(meio * frac)
                por(meio - d, r, ".")
                por(meio + d - 1, r, ".")
        elif r < faixa:
            for frac in (0.92, 0.6, 0.3):
                d = int(meio * frac) - (faixa - r)
                por(meio - d, r, "d")
                por(meio - d + 1, r, "P")
                por(meio + d - 2, r, "9")
                por(meio + d - 1, r, "b")
        else:
            f = (r - faixa) / max(1, altura - faixa - 1)
            externo = int(meio * (1.0 - 0.78 * f))
            interno = 0 if r < faixa + 2 else int(meio * 0.06)
            for d in range(interno, externo):
                if (d + r * 3) % 11 == 0 and d < externo - 2:
                    continue                # vão entre as penas
                ponta = d == externo - 1
                direita = ("b" if f < 0.5 else "P") if ponta else "X"
                esquerda = ("d" if f < 0.5 else "9") if ponta else "X"
                por(meio - 1 - d, r, esquerda)
                por(meio + d, r, direita)

    linha_texto = min(altura - 1, faixa + 1)
    rotulo = f"  {texto}  "
    x0 = meio - len(rotulo) // 2
    for i, c in enumerate(rotulo):
        por(x0 + i, linha_texto, c)
    return ["".join(l) for l in grade], linha_texto, (x0, len(rotulo))


def cadeado(largura, altura):
    """Cadeado grande feito de "8", "d", "b", "Y", "P", com fundo pontilhado ":"."""
    grade = [[":" if (x + y) % 2 == 0 else " " for x in range(largura)] for y in range(altura)]
    cx = largura // 2
    alca = max(3, altura * 2 // 5)
    raio = max(4, min(largura // 4, alca * 2))
    for y in range(alca):
        dy = (alca - y) / alca
        for x in range(largura):
            dist = math.hypot((x - cx) / raio, dy * 1.05)
            if 0.62 <= dist <= 1.0:
                grade[y][x] = "8"
            elif 0.5 <= dist < 0.62 or 1.0 < dist <= 1.1:
                grade[y][x] = " "
    meia = int(raio * 1.35)
    for y in range(alca, altura):
        for x in range(max(0, cx - meia), min(largura, cx + meia + 1)):
            esq, dir_ = x == cx - meia, x == cx + meia
            c = "8"
            if y == alca:
                c = "d" if esq else "b" if dir_ else "8"
            elif y == altura - 1:
                c = "Y" if esq else "P" if dir_ else "8"
            grade[y][x] = c
    fy = alca + (altura - alca) // 2           # buraco da fechadura
    for y, desenho in ((fy - 1, " d8b "), (fy, " Y8P "), (fy + 1, "  8  ")):
        for i, c in enumerate(desenho):
            if 0 <= y < altura and 0 <= cx - 2 + i < largura:
                grade[y][cx - 2 + i] = " " if c in " 8" else c
    return ["".join(l) for l in grade]


TANQUE = ["   ▄██▄   ",
          " ▄██████▄ ",
          "██▀████▀██",
          "██ ▀▀▀▀ ██"]


# ------------------------------------------------------------------ abertura
class Abertura:
    def __init__(self, largura, altura, info, tarefas=(), processos=()):
        self.l, self.a = largura, altura
        self.info = info
        self.tarefas = list(tarefas)
        self.processos = list(processos)
        self.rng = random.Random()
        self.usuario = f"{info['usuario']}@{info['maquina']}"
        self.cpu = [self.rng.uniform(0.15, 0.5) for _ in range(min(info["nucleos"], 4))]
        self.canos = []
        self.ocupado = {}
        self.gotas = []
        self.c1 = int(largura * 0.345)
        self.c2 = int(largura * 0.70)
        self.meio = 1 + int((altura - 1) * 0.47)
        self.y_canos = self.meio - 1
        self.a_canos = max(4, int((altura - self.y_canos) * 0.45))

    def prompt(self, q, x, y, comando, t, inicio, ate):
        q.escrever(x, y, "[", ROSA, ate=ate)
        q.escrever(x + 1, y, self.usuario, BRANCO, ate=ate)
        q.escrever(x + 1 + len(self.usuario), y, "]", ROSA, ate=ate)
        q.escrever(x, y + 1, "[", ROSA, ate=ate)
        q.escrever(x + 1, y + 1, "~", BRANCO, ate=ate)
        q.escrever(x + 2, y + 1, "]> ", ROSA, ate=ate)
        digitado = comando[: max(0, int((t - inicio) * 30))]
        cursor = "█" if int(t * 3) % 2 or len(digitado) < len(comando) else " "
        q.escrever(x + 5, y + 1, digitado + cursor, BRANCO, ate=ate)

    # ---- coluna da esquerda ---------------------------------------------
    def esquerda_topo(self, q, t):
        l = self.c1
        self.prompt(q, 0, 1, "py pc.py --abertura", t, 0.1, l)
        altura = max(6, self.meio - 6)
        arte, linha_texto, (tx, tl) = asas(l - 2, altura, "S   P   A   R   T   A")
        revelado = min(len(arte), int(max(0, t - 0.8) * 14))   # a arte surge linha a linha
        for i, linha in enumerate(arte[:revelado]):
            for j, c in enumerate(linha):
                if c == " ":
                    continue
                if i == linha_texto and tx <= j < tx + tl:
                    q.escrever(1 + j, 3 + i, c, BRANCO)
                else:
                    brilho = (math.sin(t * 3 - j * 0.12 + i * 0.3) + 1) / 2
                    q.escrever(1 + j, 3 + i, c, _misturar(MEDIO, VIVO, brilho))
        if t > 2.0:
            texto = "Iniciando módulos..."[: int((t - 2.0) * 25)]
            q.escrever(0, self.meio - 2, texto + ("█" if int(t * 3) % 2 else " "), ROSA, ate=l)

    def esquerda_htop(self, q, t):
        l, y0 = self.c1, self.meio
        info = self.info
        metade = l // 2
        barra_l = max(6, metade - 14)
        for i, v in enumerate(self.cpu):
            self.cpu[i] = min(0.95, max(0.03, v + self.rng.uniform(-0.06, 0.06)))
            q.escrever(1, y0 + i, f"{i + 1:>2} [", TEXTO)
            q.escrever(5, y0 + i, "|" * int(self.cpu[i] * barra_l), ROSA if self.cpu[i] < 0.6 else VIVO)
            q.escrever(5 + barra_l, y0 + i, f"{self.cpu[i] * 100:5.1f}%]", TEXTO)
        linha = y0 + len(self.cpu)
        total, usada = info["memoria_total"], info["memoria_usada"]
        enchendo = min(1.0, t / 2)
        if total:
            q.escrever(1, linha, "Mem[", TEXTO)
            q.escrever(5, linha, "|" * int(usada / total * barra_l * enchendo), CLARO)
            q.escrever(5 + barra_l, linha, f" {usada // 2**20}/{total // 2**20}MB]", TEXTO, ate=metade + 1)
        if info["discos"]:
            d = info["discos"][0]
            uso = 1 - d["livre"] / d["total"] if d["total"] else 0
            q.escrever(1, linha + 1, "Dsc[", TEXTO)
            q.escrever(5, linha + 1, "|" * int(uso * barra_l * enchendo), MEDIO)
            q.escrever(5 + barra_l, linha + 1, f"{uso * 100:5.1f}%]", TEXTO)
        q.escrever(metade + 2, y0, f"Processos: {len(self.processos)}", TEXTO, ate=l)
        q.escrever(metade + 2, y0 + 1, f"Agendadas: {sum(1 for x in self.tarefas if x.get('ativo', True))}", TEXTO, ate=l)
        q.escrever(metade + 2, y0 + 2, f"Ligado há: {info['ligado']}", TEXTO, ate=l)

        cab = linha + 3
        q.escrever(0, cab, "  PID USUÁRIO   CPU%  MEM%   MEMÓRIA  Comando".ljust(l), PRETO, ROSA, ate=l)
        rodape_y = self.a - 1
        linhas = max(0, rodape_y - cab - 1)
        selecionado = int(t * 2.5) % max(1, min(len(self.processos), linhas))
        for i, (pid, nome, mem) in enumerate(self.processos[:linhas]):
            pct = mem / total * 100 if total else 0
            cpu = abs(math.sin(pid + t)) * 4
            texto = f"{pid:>5} {info['usuario'][:9]:<9} {cpu:4.1f}  {pct:4.1f} {tamanho_legivel(mem):>9}  {nome}"
            if i == selecionado:
                q.escrever(0, cab + 1 + i, texto.ljust(l), PRETO, CLARO, ate=l)
            else:
                q.escrever(0, cab + 1 + i, texto, ROSA if i == 0 else TEXTO, ate=l)
        x = 0
        for tecla, rotulo in (("F1", "Ajuda "), ("F2", "Setup "), ("F3", "Busca "), ("F4", "Filtro"),
                              ("F5", "Árvore"), ("F6", "Ordem "), ("F9", "Parar "), ("F10", "Sair  ")):
            q.escrever(x, rodape_y, tecla, BRANCO, PRETO, ate=l)
            q.escrever(x + len(tecla), rodape_y, rotulo, PRETO, ROSA, ate=l)
            x += len(tecla) + len(rotulo)

    # ---- coluna do meio ---------------------------------------------------
    def caixa(self, q, x, y, l, a, titulo, linhas, t):
        q.escrever(x, y, ".-" + "=" * (l - 4) + "-.", ROSA)
        for i in range(1, a - 1):
            q.escrever(x, y + i, ":", ROSA)
            q.escrever(x + l - 1, y + i, ":", ROSA)
        q.escrever(x, y + a - 1, "'-" + "=" * (l - 4) + "-'", ROSA)
        q.escrever(x + 1, y + 1, titulo.center(l - 2), BRANCO if int(t * 2) % 4 else VIVO)
        for i, linha in enumerate(linhas[: max(0, a - 3)]):
            q.escrever(x + 1, y + 2 + i, linha.center(l - 2)[: l - 2], FORTE)

    def meio_topo(self, q, t):
        x0, l = self.c1 + 1, self.c2 - self.c1 - 1
        q.escrever(x0, 1, ("- " * l)[:l], CINZA)
        alt = max(8, self.meio - 9)
        lado = max(12, l // 5)
        centro_l = l - 2 * lado - 2
        if centro_l >= 14:
            revelado = int(max(0, t - 0.4) * 10)
            for i, linha in enumerate(cadeado(centro_l, alt)[:revelado]):
                for j, c in enumerate(linha):
                    cor = CINZA if c == ":" else _misturar(MEDIO, CLARO, (math.sin(t * 2 + i * 0.4) + 1) / 2)
                    q.escrever(x0 + lado + 1 + j, 2 + i, c, cor)
        meia = alt // 2
        discos = [d["raiz"].rstrip("\\")[:3] for d in self.info["discos"][:3]]
        self.caixa(q, x0, 2, lado, meia, ":COFRE", ["AES-256", "GCM"], t)
        self.caixa(q, x0, 2 + meia, lado, alt - meia, ":DISCOS", discos, t)
        self.caixa(q, x0 + l - lado, 2, lado, meia, ":CHAVE", ["scrypt", "N=2^17"], t)
        self.caixa(q, x0 + l - lado, 2 + meia, lado, alt - meia, ":LOCAL", ["127 0 0 1"], t)

        y = 2 + alt
        q.escrever(x0, y, ("- " * l)[:l], CINZA)
        pisca = int(t * 3) % 2
        for i, (a, b, c) in enumerate([
            ("*AVISO* ", '"Painel de controle local do seu PC"', ""),
            ("==  ", "Você está no comando. Tudo pode ser desfeito", "  =="),
            ("Registros: ", "logs/", "  ·  desfazer: py pc.py desfazer"),
        ]):
            xx = x0 + max(0, (l - len(a + b + c)) // 2)
            q.escrever(xx, y + 1 + i, a, BRANCO if (pisca and i == 0) else VIVO, ate=x0 + l)
            q.escrever(xx + len(a), y + 1 + i, b, BRANCO if i == 1 else ROSA, ate=x0 + l)
            q.escrever(xx + len(a) + len(b), y + 1 + i, c, VIVO, ate=x0 + l)

    def meio_cores(self, q, t):
        """A clássica tabela de teste de cores do terminal, em vermelhos."""
        x0, l = self.c1 + 1, self.c2 - self.c1 - 1
        y0 = self.meio + 1
        rotulos = ["m", "1m"] + [r for n in range(30, 38) for r in (f"{n}m", f"1;{n}m")]
        fundos = [FUNDO_ESCURO, (60, 60, 64)] + VERMELHOS[1:]
        frente = [TEXTO, BRANCO, PRETO, CINZA, ESCURO, MEDIO, FORTE, VIVO, ROSA, CLARO]
        larg = max(5, min(7, (l - 7) // len(fundos)))
        nomes = [""] + [f"{40 + i}m" for i in range(len(fundos) - 1)]
        for c, nome in enumerate(nomes):
            q.escrever(x0 + 7 + c * larg, y0, nome.center(larg), VIVO, ate=x0 + l)
        disponivel = self.a - 1 - y0 - 8
        onda = int(t * 6)
        for r, rotulo in enumerate(rotulos[: max(0, disponivel)]):
            q.escrever(x0, y0 + 1 + r, f"{rotulo:>6}", TEXTO, ate=x0 + l)
            for c, fundo in enumerate(fundos):
                letra = frente[(r // 2 + c + onda) % len(frente)] if r > 1 else TEXTO
                q.escrever(x0 + 7 + c * larg, y0 + 1 + r, "gYw".center(larg), letra, fundo, ate=x0 + l)

    def meio_tanques(self, q, t):
        x0, l = self.c1 + 1, self.c2 - self.c1 - 1
        y0 = self.a - 8
        self.prompt(q, x0, y0 - 2, "./sprites.sh", t, 1.5, x0 + l)
        tons = VERMELHOS[2:8]
        passo = max(11, l // 6)
        aparece = int(max(0, t - 2.2) * 8)
        n = 0
        for linha in range(2):
            for coluna in range(min(6, l // passo)):
                if n >= aparece:
                    return
                cor = tons[(coluna + linha * 2 + int(t * 2)) % len(tons)]
                for i, parte in enumerate(TANQUE):
                    q.escrever(x0 + coluna * passo, y0 + linha * 4 + i, parte, cor, ate=x0 + l)
                n += 1

    # ---- coluna da direita ------------------------------------------------
    def direita_fila(self, q, t):
        x0, l = self.c2 + 1, self.l - self.c2 - 1
        itens = self.tarefas or [{"nome": "nenhuma tarefa agendada", "quando": "-"}]
        q.escrever(x0, 1, f"Fila de tarefas ({len(itens)} itens)", TEXTO, ate=self.l - 13)
        q.escrever(self.l - 12, 1, "Volume: 50%", BRANCO)
        q.escrever(x0, 2, "─" * l, CINZA)
        alt = max(3, self.y_canos - 6)
        for i, item in enumerate(itens[:alt]):
            ativo = item.get("ativo", True)
            q.escrever(x0, 3 + i, f"{i + 1:02} ", TEXTO)
            q.escrever(x0 + 3, 3 + i, "│ ", CINZA)
            q.escrever(x0 + 5, 3 + i, item["nome"], ROSA if ativo else CINZA, ate=x0 + int(l * 0.62))
            quando = f"[{item.get('quando', '')}{' ' + item['hora'] if item.get('hora') else ''}]"
            q.escrever(x0 + int(l * 0.64), 3 + i, quando, FORTE if ativo else CINZA, ate=self.l)
        y = self.y_canos - 3
        q.escrever(x0, y, "─" * l, CINZA)
        progresso = min(1.0, t / DURACAO)
        texto = f"Tocando: abertura // {time.strftime('%Y')} // SPARTA // [0:{int(t):02}/0:{int(DURACAO):02}]"
        q.escrever(x0, y + 1, texto, BRANCO, ate=self.l)
        cheio = int(progresso * l)
        q.escrever(x0, y + 2, "━" * cheio, VIVO)
        q.escrever(x0 + cheio, y + 2, "─" * (l - cheio), CINZA, ate=self.l)

    def direita_canos(self, q, t):
        """Protetor de tela "canos": canos coloridos crescendo e virando esquinas."""
        x0, l = self.c2 + 1, self.l - self.c2 - 1
        y0, a = self.y_canos, self.a_canos
        cores = [VIVO, FORTE, BRANCO, CINZA, ROSA, MEDIO]
        if len(self.ocupado) > l * a * 0.55:
            self.ocupado.clear()
            self.canos.clear()
        while len(self.canos) < 5:
            self.canos.append({"x": self.rng.randrange(l), "y": self.rng.randrange(a),
                               "dir": self.rng.randrange(4), "cor": self.rng.choice(cores)})
        retos = {0: "━", 2: "━", 1: "┃", 3: "┃"}
        curvas = {(0, 1): "┓", (0, 3): "┛", (2, 1): "┏", (2, 3): "┗",
                  (1, 0): "┗", (1, 2): "┛", (3, 0): "┏", (3, 2): "┓"}
        for cano in self.canos:
            for _ in range(2):
                antiga = cano["dir"]
                if self.rng.random() < 0.18:
                    cano["dir"] = (antiga + self.rng.choice((1, 3))) % 4
                dx, dy = ((1, 0), (0, 1), (-1, 0), (0, -1))[cano["dir"]]
                char = retos[cano["dir"]] if antiga == cano["dir"] else curvas[(antiga, cano["dir"])]
                self.ocupado[(cano["x"], cano["y"])] = (char, cano["cor"])
                cano["x"] += dx
                cano["y"] += dy
                if not (0 <= cano["x"] < l and 0 <= cano["y"] < a):   # saiu da área: nasce outro
                    cano.update(x=self.rng.randrange(l), y=self.rng.randrange(a),
                                dir=self.rng.randrange(4), cor=self.rng.choice(cores))
        for (cx, cy), (char, cor) in self.ocupado.items():
            q.escrever(x0 + cx, y0 + cy, char, cor)

    def direita_matriz(self, q, t):
        x0, l = self.c2 + 1, self.l - self.c2 - 1
        y0 = self.y_canos + self.a_canos + 1
        a = self.a - y0
        if a <= 0:
            return
        simbolos = "0123456789ABCDEFabcdef<>{}[]=+*#$%&@/\\|:;?!^~"
        if self.rng.random() < 0.95:
            self.gotas.append([self.rng.randrange(0, l, 2), 0.0, self.rng.uniform(0.3, 0.9)])
        vivas = []
        for g in self.gotas:
            g[1] += g[2]
            for k in range(10):
                gy = int(g[1]) - k
                if 0 <= gy < a:
                    cor = BRANCO if k == 0 else _misturar(VIVO, (70, 52, 58), k / 10)
                    q.escrever(x0 + g[0], y0 + gy, self.rng.choice(simbolos), cor)
            if g[1] - 10 < a:
                vivas.append(g)
        self.gotas = vivas

    # ---- tudo junto ------------------------------------------------------
    def quadro(self, t):
        q = Quadro(self.l, self.a)
        x = 0
        for i in range(5):                      # barra de abas do tmux
            aba = f" {self.usuario[:18]} "
            ativa = i == int(t / 1.3) % 5
            q.escrever(x, 0, aba, PRETO if ativa else CINZA, ROSA if ativa else FUNDO_ESCURO)
            x += len(aba)
        q.pintar_fundo(x, 0, self.l - x, 1, FUNDO_ESCURO)
        relogio = time.strftime(" %d/%m/%y %H:%M ")
        q.escrever(self.l - len(relogio), 0, relogio, BRANCO, FUNDO_ESCURO)
        for coluna in (self.c1, self.c2):       # divisões entre as colunas
            q.pintar_fundo(coluna, 1, 1, self.a - 1, FUNDO_ESCURO)

        self.esquerda_topo(q, t)
        self.esquerda_htop(q, t)
        self.meio_topo(q, t)
        self.meio_cores(q, t)
        self.meio_tanques(q, t)
        self.direita_fila(q, t)
        self.direita_canos(q, t)
        self.direita_matriz(q, t)

        if t >= DURACAO:
            texto = "  S I S T E M A   P R O N T O  "
            cx, cy = (self.l - len(texto)) // 2, self.a // 2
            cor = BRANCO if int(t * 6) % 2 else VIVO
            q.escrever(cx - 2, cy - 1, "╔" + "═" * (len(texto) + 2) + "╗", cor, PRETO)
            q.escrever(cx - 2, cy, "║ " + texto + " ║", PRETO, cor)
            q.escrever(cx - 2, cy + 1, "╚" + "═" * (len(texto) + 2) + "╝", cor, PRETO)
        return q


def _quadro_tempestade(tempestade, t):
    q = Quadro(tempestade.l, tempestade.a)
    q.pintar_fundo(0, 0, tempestade.l, tempestade.a, (8, 8, 11))   # quase preto
    tempestade.desenhar(q, t)
    return q


def executar(tarefas=(), popups=True):
    """Mostra a abertura. Não faz nada se não houver um terminal de verdade.

    Fases: tempestade de pop-ups que monta o elmo da SPARTA, depois o painel
    (dashboard) e o "SISTEMA PRONTO". Qualquer tecla pula tudo.
    """
    if sys.stdout is None or not sys.stdout.isatty() or sys.stdin is None or not sys.stdin.isatty():
        return
    if WINDOWS:
        try:
            _preparar_windows()
        except OSError:
            pass
    colunas, linhas = shutil.get_terminal_size((120, 36))
    if colunas < 120 or linhas < 34:
        return   # janela pequena demais para o efeito
    largura = colunas - 1
    tempestade = Tempestade(largura, linhas) if popups else None
    t_storm = tempestade.duracao if tempestade else 0.0
    abertura = Abertura(largura, linhas, info_sistema(), tarefas, processos_detalhados())

    sys.stdout.write("\x1b[?1049h\x1b[?25l")   # tela alternativa, sem cursor
    inicio = time.time()
    try:
        anterior = None
        with Teclado() as teclado:
            while True:
                t = time.time() - inicio
                if tempestade and t < t_storm:
                    quadro = _quadro_tempestade(tempestade, t)
                else:
                    quadro = abertura.quadro(t - t_storm)
                sys.stdout.write(quadro.ansi(anterior))
                sys.stdout.flush()
                anterior = quadro
                if t - t_storm > DURACAO + 0.9 or teclado.apertou():
                    break
                time.sleep(max(0.0, 1 / QPS - (time.time() - inicio - t)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()


# ======================================================================
#  MENU ANIMADO  (central, "desconstruído", com vermelho ao redor)
# ======================================================================
class _MenuArte:
    """Fundo animado e painel central do menu."""

    def __init__(self, largura, altura, opcoes):
        self.l, self.a = largura, altura
        self.opcoes = opcoes
        self.rng = random.Random()
        self.gotas = []
        # painel central
        self.pw = min(66, max(44, largura - 24))
        self.ph = len(opcoes) + 11
        self.px = (largura - self.pw) // 2
        self.py = max(1, (altura - self.ph) // 2)
        # marca-d'água do elmo, atrás do painel
        self.marca = elmo(self.pw + 8, self.ph + 2)

    def _chuva(self, q, t):
        simbolos = "0123456789ABCDEF<>{}[]=+*#$%&@/\\|:;"
        if self.rng.random() < 0.9:
            # só nas margens, fora do painel
            margem = self.px - 2
            if margem > 2:
                x = self.rng.randrange(0, margem) if self.rng.random() < 0.5 else \
                    self.rng.randrange(self.px + self.pw + 2, self.l)
                self.gotas.append([x, 1.0, self.rng.uniform(0.3, 0.9)])
        vivas = []
        for g in self.gotas:
            g[1] += g[2]
            for k in range(8):
                gy = int(g[1]) - k
                if 1 <= gy < self.a - 1:
                    cor = BRANCO if k == 0 else _misturar(VIVO, (46, 30, 36), k / 8)
                    q.escrever(g[0], gy, self.rng.choice(simbolos), cor)
            if g[1] - 8 < self.a:
                vivas.append(g)
        self.gotas = vivas

    def _marca_dagua(self, q, t):
        x0, y0 = self.px - 4, self.py - 1
        for ly, linha in enumerate(self.marca):
            for lx, v in enumerate(linha):
                if v > 0 and (lx + ly) % 2 == 0:
                    car = "▓" if v >= 0.9 else "▒"
                    q.escrever(x0 + lx, y0 + ly, car, _misturar(FUNDO, ESCURO, 0.5))

    def _widgets(self, q, t):
        # cantos com "atividade" em vermelho
        for i in range(4):
            v = (math.sin(t * 3 + i) + 1) / 2
            barra = "▁▂▃▄▅▆▇█"[int(v * 7)]
            q.escrever(2 + i, self.a - 2, barra, _misturar(ESCURO, VIVO, v))
            q.escrever(self.l - 3 - i, self.a - 2, barra, _misturar(ESCURO, VIVO, v))
        onda = "".join("▁▂▃▄▅▆▇█"[int((math.sin(t * 5 + i * 0.4) + 1) * 3.5)] for i in range(18))
        q.escrever(2, 1, onda, MEDIO)
        q.escrever(self.l - 20, 1, onda, MEDIO)

    def _painel(self, q, t, selecao):
        x, y, w, h = self.px, self.py, self.pw, self.ph
        q.pintar_fundo(x, y, w, h, (14, 9, 12))
        # borda com brilho correndo
        pulso = int(t * 8) % (2 * (w + h))
        for i in range(w):
            cor = CLARO if abs(pulso - i) < 3 or abs(pulso - (2 * w + h - 1 - i)) < 3 else FORTE
            q.escrever(x + i, y, "═" if 0 < i < w - 1 else ("╔" if i == 0 else "╗"), cor)
            q.escrever(x + i, y + h - 1, "═" if 0 < i < w - 1 else ("╚" if i == 0 else "╝"), FORTE)
        for j in range(1, h - 1):
            q.escrever(x, y + j, "║", FORTE)
            q.escrever(x + w - 1, y + j, "║", FORTE)
        # título SPARTA grande
        palavra = palavra_sparta()
        pl = len(palavra[0])
        tx = x + (w - pl) // 2
        for i, linha in enumerate(palavra):
            for j, c in enumerate(linha):
                if c != " ":
                    brilho = (math.sin(t * 3 - j * 0.1) + 1) / 2
                    q.escrever(tx + j, y + 1 + i, "█", _misturar(FORTE, CLARO, brilho))
        q.escrever(x + 2, y + 6, "─" * (w - 4), ESCURO)
        sub = "central de automações do PC"
        q.escrever(x + (w - len(sub)) // 2, y + 6, f" {sub} ", ROSA, (14, 9, 12))
        # opções
        base = y + 8
        for i, rotulo in enumerate(self.opcoes):
            yy = base + i
            if yy >= y + h - 2:
                break
            num = f"{i + 1:02}"
            if i == selecao:
                marca = "▶ "
                linha = (marca + f"{num}  {rotulo}").ljust(w - 4)
                q.escrever(x + 2, yy, linha, PRETO, CLARO)
            else:
                q.escrever(x + 2, yy, "  ", CINZA)
                q.escrever(x + 4, yy, num, VIVO)
                q.escrever(x + 7, yy, rotulo, TEXTO)
        # rodapé do painel
        dica = "↑↓ mover · Enter escolher · nº direto · 0/Esc sair"
        q.escrever(x + (w - len(dica)) // 2, y + h - 1, f" {dica} ", CINZA, FUNDO)

    def quadro(self, t, selecao):
        q = Quadro(self.l, self.a)
        q.pintar_fundo(0, 0, self.l, self.a, (8, 8, 11))
        relogio = time.strftime(" %d/%m/%y  %H:%M:%S ")
        q.escrever(self.l - len(relogio), 0, relogio, BRANCO, FUNDO_ESCURO)
        q.escrever(1, 0, " SPARTA // menu ", PRETO, VIVO)
        self._marca_dagua(q, t)
        self._chuva(q, t)
        self._widgets(q, t)
        self._painel(q, t, selecao)
        return q


def _menu_simples(opcoes):
    """Menu em texto puro (terminal pequeno ou sem tty)."""
    print("\n╔" + "═" * 38 + "╗")
    print("║" + "S  P  A  R  T  A".center(38) + "║")
    print("╚" + "═" * 38 + "╝")
    for i, rotulo in enumerate(opcoes, 1):
        print(f"  {i:>2}. {rotulo}")
    print("   0. Sair")
    escolha = input("\nEscolha: ").strip()
    if not escolha.isdigit() or not 0 <= int(escolha) <= len(opcoes):
        return None
    return None if int(escolha) == 0 else int(escolha) - 1


def menu_animado(opcoes, selecao=0):
    """Mostra o menu animado e devolve o índice escolhido (0-based) ou None (sair)."""
    tty = (sys.stdout is not None and sys.stdout.isatty()
           and sys.stdin is not None and sys.stdin.isatty())
    colunas, linhas = shutil.get_terminal_size((120, 36))
    if not tty or colunas < 90 or linhas < 24:
        return _menu_simples(opcoes)
    if WINDOWS:
        try:
            _preparar_windows()
        except OSError:
            pass
        colunas, linhas = shutil.get_terminal_size((120, 36))
    arte = _MenuArte(colunas - 1, linhas, opcoes)
    selecao = max(0, min(selecao, len(opcoes) - 1))

    sys.stdout.write("\x1b[?1049h\x1b[?25l")
    inicio = time.time()
    anterior = None
    escolhido = -1   # -1 = ainda escolhendo
    try:
        with Teclado() as teclado:
            while escolhido == -1:
                t = time.time() - inicio
                q = arte.quadro(t, selecao)
                sys.stdout.write(q.ansi(anterior))
                sys.stdout.flush()
                anterior = q
                tecla = teclado.ler_tecla()
                if tecla == "up" or tecla == "k":
                    selecao = (selecao - 1) % len(opcoes)
                elif tecla == "down" or tecla == "j":
                    selecao = (selecao + 1) % len(opcoes)
                elif tecla in ("enter", "space"):
                    escolhido = selecao
                elif tecla in ("esc", "q", "0"):
                    escolhido = None
                elif tecla and tecla.isdigit():
                    # número digitado: tenta 1..len (suporta 2 dígitos rápidos)
                    n = int(tecla)
                    if n == 0:
                        escolhido = None
                    else:
                        proxima = teclado.ler_tecla() if n <= (len(opcoes) // 10) else None
                        if proxima and proxima.isdigit():
                            n = n * 10 + int(proxima)
                        if 1 <= n <= len(opcoes):
                            escolhido = n - 1
                        else:
                            selecao = min(len(opcoes) - 1, n - 1)
                time.sleep(max(0.0, 1 / QPS - ((time.time() - inicio) - t)))
    except KeyboardInterrupt:
        escolhido = None
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
    return escolhido if escolhido != -1 else None
