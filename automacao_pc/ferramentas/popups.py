"""
Tempestade de "janelas de CMD" para as aberturas no terminal.

Dezenas de janelinhas aparecem em posições aleatórias, enchem-se de texto
em tons de vermelho (código, fluxos de caracteres, barras), vivem alguns
segundos e somem, enquanto outras surgem — enchendo a tela.

Ao mesmo tempo, um conjunto de janelas "de logo" vai se encaixando como um
quebra-cabeça numa área central: juntas, o texto delas desenha o elmo da
SPARTA. Essas não somem — ficam montando a logo.

Desenha tudo numa grade (o Quadro de intro.py), então não abre nenhuma
janela de verdade no Windows. Texto só com tema da SPARTA, nada de fora.
"""

import random

# Paleta vermelha (igual à de intro.py)
FUNDO = (8, 7, 9)
PRETO = (6, 6, 8)
CINZA = (120, 120, 128)
BRANCO = (250, 250, 250)
VERMELHOS = [(92, 22, 34), (128, 24, 44), (170, 28, 56), (205, 34, 66), (232, 52, 86),
             (245, 92, 122), (250, 140, 165), (252, 190, 205), (255, 228, 234)]
ESCURO, MEDIO, FORTE, VIVO, CLARO, ROSA = (VERMELHOS[1], VERMELHOS[2], VERMELHOS[3],
                                          VERMELHOS[4], VERMELHOS[6], VERMELHOS[5])

SIMBOLOS = "0123456789ABCDEFabcdef<>{}[]()=+-*/\\|:;.,#$%&@?!^~"
TITULOS = ["organizar.py", "duplicados.py", "discos.py", "limpeza.py", "inicio.py",
           "energia.py", "agendador.py", "remoto.py", "navegadores.py", "cofre.py",
           "nucleo.py", "autotipo.py", "util.py", "pc.py", "movimentos.py"]
LINHAS_CODIGO = [
    "def executar(cfg, aplicar=False):", "    with Movimentos('sparta') as mov:",
    "        plano = planejar(pasta, mapa)", "        for origem, destino in plano:",
    "            mov.mover(origem, destino)", "    return {'ok': True, 'total': n}",
    "chave = scrypt(senha, sal, N=2**17)", "dados = AESGCM(chave).encrypt(n, claro)",
    "for raiz, _, _, total, livre in discos:", "    pct = 1 - livre / total",
    "if agora - st.st_mtime > idade:", "    categoria = mapa.get(ext, 'Outros')",
    "hash = blake2b(bloco).digest()", "subprocess.run(['shutdown', '/s'])",
    "self.cpu = [medir(n) for n in nucleos]", "tarefas = carregar(config)['agendamentos']",
]


def _mistura(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _cor_fluxo(k):
    """Cor de uma linha do fluxo: a de cima branca, esmaecendo para o vermelho."""
    return BRANCO if k == 0 else _mistura(VIVO, ESCURO, k / 8)


class Popup:
    def __init__(self, x, y, w, h, titulo, tipo, nascimento, vida, rng, dados=None):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.titulo, self.tipo = titulo, tipo
        self.nascimento, self.vida = nascimento, vida
        self.rng = rng
        self.dados = dados or {}
        self.fixa = tipo == "logo"

    def alfa(self, t):
        """0..1: entra rápido, segura, e sai no fim da vida (janelas comuns)."""
        if self.fixa:
            return min(1.0, (t - self.nascimento) / 0.25)
        idade = t - self.nascimento
        if idade < 0.2:
            return idade / 0.2
        if idade > self.vida - 0.5:
            return max(0.0, (self.vida - idade) / 0.5)
        return 1.0

    def viva(self, t):
        return self.fixa or t - self.nascimento < self.vida

    def _moldura(self, q, a):
        cor_barra = _mistura(FUNDO, FORTE, a)
        cor_borda = _mistura(FUNDO, VIVO if self.fixa else MEDIO, a)
        q.pintar_fundo(self.x, self.y, self.w, self.h, _mistura(FUNDO, PRETO, a))
        # barra de título
        titulo = f" ■ C:\\SPARTA\\{self.titulo}"[: self.w - 4]
        q.escrever(self.x, self.y, titulo.ljust(self.w - 3), _mistura(FUNDO, BRANCO, a), cor_barra)
        q.escrever(self.x + self.w - 3, self.y, "_□x", _mistura(FUNDO, CLARO, a), cor_barra)
        # bordas
        q.escrever(self.x, self.y + self.h - 1, "└" + "─" * (self.w - 2) + "┘", cor_borda)
        for yy in range(self.y + 1, self.y + self.h - 1):
            q.escrever(self.x, yy, "│", cor_borda)
            q.escrever(self.x + self.w - 1, yy, "│", cor_borda)
        return a

    def desenhar(self, q, t, escala_alfa=1.0):
        a = self.alfa(t) * escala_alfa
        if a <= 0.01:
            return
        self._moldura(q, a)
        ix, iy = self.x + 1, self.y + 1
        iw, ih = self.w - 2, self.h - 2
        metodo = getattr(self, f"_conteudo_{self.tipo}", self._conteudo_fluxo)
        metodo(q, t, a, ix, iy, iw, ih)

    # ---- tipos de conteúdo ----------------------------------------------
    def _conteudo_fluxo(self, q, t, a, ix, iy, iw, ih):
        self.rng.seed(int((t - self.nascimento) * 12) * 7 + self.dados["semente"])
        for linha in range(ih):
            k = ih - 1 - linha                         # a de baixo é a "nova"
            texto = "".join(self.rng.choice(SIMBOLOS) for _ in range(iw))
            q.escrever(ix, iy + linha, texto, _mistura(FUNDO, _cor_fluxo(min(8, k)), a))

    def _conteudo_codigo(self, q, t, a, ix, iy, iw, ih):
        linhas = self.dados["linhas"]
        reveladas = int((t - self.nascimento) * 8)
        for i in range(ih):
            if i >= reveladas:
                break
            texto = linhas[i % len(linhas)][:iw]
            digitando = i == min(reveladas, ih) - 1
            cor = BRANCO if digitando else _cor_fluxo(1 + i % 3)
            q.escrever(ix, iy + i, texto + ("█" if digitando else ""), _mistura(FUNDO, cor, a))

    def _conteudo_barras(self, q, t, a, ix, iy, iw, ih):
        self.rng.seed(self.dados["semente"])
        for i in range(ih):
            nome = TITULOS[(self.dados["semente"] + i) % len(TITULOS)][:8]
            prog = min(1.0, (t - self.nascimento) / 2 + self.rng.random() * 0.5)
            larg = max(3, iw - 11)
            cheio = int(prog * larg)
            q.escrever(ix, iy + i, f"{nome:<8} ", _mistura(FUNDO, CINZA, a))
            q.escrever(ix + 9, iy + i, "█" * cheio, _mistura(FUNDO, VIVO, a))
            q.escrever(ix + 9 + cheio, iy + i, "░" * (larg - cheio), _mistura(FUNDO, ESCURO, a))

class Tempestade:
    """Tempestade de pop-ups (fake) enchendo a tela. Usada como alternativa
    quando não dá para abrir CMDs de verdade (fora do Windows ou desligado)."""

    def __init__(self, largura, altura, rng=None, duracao=12.0):
        self.l, self.a = largura, altura
        self.rng = rng or random.Random()
        self.dur_storm = duracao                   # enche a tela o tempo todo
        self.duracao = duracao
        self.comuns = []
        self.proximo = 0.0
        self.contador = 0

    def _nova_comum(self, t):
        self.contador += 1
        w = self.rng.randint(22, max(24, self.l // 3))
        h = self.rng.randint(6, max(8, self.a // 3))
        x = self.rng.randint(0, max(0, self.l - w))
        y = self.rng.randint(1, max(1, self.a - h))
        tipo = self.rng.choice(["fluxo", "fluxo", "codigo", "barras"])
        dados = {"semente": self.rng.randrange(9999)}
        if tipo == "codigo":
            inicio = self.rng.randrange(len(LINHAS_CODIGO))
            dados["linhas"] = LINHAS_CODIGO[inicio:] + LINHAS_CODIGO[:inicio]
        vida = self.rng.uniform(7.0, 9.5)          # cada pop-up vive >= 7s
        return Popup(x, y, w, h, self.rng.choice(TITULOS), tipo, t, vida, self.rng, dados)

    def desenhar(self, q, t):
        # some com as janelas mortas, nasce outra no lugar (tela sempre cheia)
        self.comuns = [p for p in self.comuns if p.viva(t)]
        if t < self.dur_storm and t >= self.proximo:
            self.comuns.append(self._nova_comum(t))
            self.proximo = t + self.rng.uniform(0.3, 0.7)
        for p in sorted(self.comuns, key=lambda p: p.nascimento):
            p.desenhar(q, t)
        # rodapé
        prog = min(1.0, t / self.duracao) if self.duracao else 1.0
        larg = max(10, self.l - 52)
        cheio = int(prog * larg)
        texto = (f" SPARTA // abrindo terminais  [{'█' * cheio}{'░' * (larg - cheio)}]"
                 f" {prog * 100:3.0f}%   qualquer tecla pula ")
        q.escrever(0, self.a - 1, texto.ljust(self.l), CLARO, PRETO)
