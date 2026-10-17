"""
Gera os icones .ico do SPARTA: um elmo coríntio (de frente) em vermelho sobre
fundo escuro, mais a letra de cada app (C/E/M) no cantinho. Rode quando quiser
mudar o logo:

    cd automacao_pc
    py assets\\gerar_icones.py

Precisa do Pillow:  py -m pip install pillow
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
N = 256                     # tamanho final
SS = 4                      # supersampling (desenha 4x maior e reduz)
W = N * SS
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

PROF = (120, 12, 28)        # vermelho profundo (base do gradiente)
CLARO = (255, 72, 100)      # vermelho claro (topo do gradiente)
RIM = (255, 172, 188)       # luz da borda
FUNDO = (24, 6, 10, 255)    # fundo do quadrado


def X(f):
    return f * W


def _grad_vert(topo, baixo):
    col = Image.new("RGB", (1, W))
    px = col.load()
    for y in range(W):
        t = y / (W - 1)
        px[0, y] = tuple(int(topo[i] + (baixo[i] - topo[i]) * t) for i in range(3))
    return col.resize((W, W))


def _bezier(p0, p1, p2, n=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / n for i in range(n + 1))]


def _poly(pts):
    m = Image.new("L", (W, W), 0)
    ImageDraw.Draw(m).polygon([(X(a), X(b)) for a, b in pts], fill=255)
    return m


def _elipse(a, b, c, d):
    m = Image.new("L", (W, W), 0)
    ImageDraw.Draw(m).ellipse([X(a), X(b), X(c), X(d)], fill=255)
    return m


def _amendoa(cx, cy, ww, hh, ang):
    """Buraco do olho: amendoa inclinada."""
    pts = []
    for a in range(0, 360, 10):
        r = math.radians(a)
        x = math.cos(r) * ww * (0.58 + 0.42 * abs(math.cos(r)))
        y = math.sin(r) * hh
        pts.append((cx + x, cy + y))
    m = Image.new("L", (W, W), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m.rotate(ang, center=(cx, cy))


def _uniao(*ms):
    o = ms[0]
    for m in ms[1:]:
        o = ImageChops.lighter(o, m)
    return o


def _crista():
    outer = _bezier((.455, .30), (.47, -.02), (.88, .20))
    inner = _bezier((.88, .20), (.60, .20), (.47, .345))
    m = Image.new("L", (W, W), 0)
    ImageDraw.Draw(m).polygon([(X(a), X(b)) for a, b in outer + inner], fill=255)
    # base de encaixe na cupula
    return _uniao(m, _poly([(.43, .30), (.57, .30), (.55, .40), (.45, .40)]))


def _sulcos_crista():
    m = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(m)
    for k in range(5):
        c = _bezier((.49, .26), (.52, .04 + 0.015 * k), (.84, .20 + 0.012 * k), n=30)
        d.line([(X(a), X(b)) for a, b in c], fill=255, width=max(1, W // 260))
    return m


def _fundo_quadrado():
    bg = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(bg)
    r = int(W * .22)
    d.rounded_rectangle([0, 0, W - 1, W - 1], radius=r, fill=FUNDO)
    d.rounded_rectangle([int(W * .03), int(W * .03), int(W * .97), int(W * .97)],
                        radius=int(r * .88), outline=(255, 51, 85, 110), width=max(2, W // 110))
    return bg


def elmo():
    """O icone base: elmo coríntio de frente, vermelho, no quadrado escuro."""
    dome = _elipse(.25, .13, .75, .65)
    face = _poly([(.26, .42), (.28, .64), (.34, .78), (.41, .85), (.44, .74), (.50, .72),
                  (.56, .74), (.59, .85), (.66, .78), (.72, .64), (.74, .42)])
    nariz = _poly([(.458, .46), (.542, .46), (.528, .80), (.50, .86), (.472, .80)])
    cr = _crista()
    shell = _uniao(dome, face, nariz, cr).filter(ImageFilter.GaussianBlur(W / 500))

    oe = _amendoa(X(.378), X(.50), X(.118), X(.05), -20)
    od = _amendoa(X(.622), X(.50), X(.118), X(.05), 20)
    ae = _elipse(.335, .60, .44, .80)
    ad = _elipse(.56, .60, .665, .80)
    cortes = _uniao(oe, od, ae, ad)
    shell = ImageChops.subtract(shell, cortes)

    corpo = _grad_vert(CLARO, PROF).convert("RGBA")
    corpo.putalpha(shell)

    # sulcos da crina (escurece levemente)
    sc = ImageChops.multiply(_sulcos_crista().filter(ImageFilter.GaussianBlur(W / 600)), cr)
    sombra_cr = Image.new("RGBA", (W, W), (90, 8, 20, 0))
    sombra_cr.putalpha(ImageChops.multiply(sc, shell))
    corpo.alpha_composite(sombra_cr)

    # brilho na cupula
    hl = Image.new("L", (W, W), 0)
    ImageDraw.Draw(hl).ellipse([X(.31), X(.18), X(.49), X(.40)], fill=85)
    hl = ImageChops.multiply(hl.filter(ImageFilter.GaussianBlur(W / 55)), shell)
    corpo.alpha_composite(Image.merge("RGBA", (Image.new("L", (W, W), 255),) * 3 + (hl,)))

    # luz da borda
    k = 2 * (W // 150) + 1
    borda = ImageChops.subtract(shell, shell.filter(ImageFilter.MinFilter(k)))
    rim = Image.new("RGBA", (W, W), RIM + (0,))
    rim.putalpha(borda)
    corpo.alpha_composite(rim)

    # sombra em volta dos recortes (profundidade)
    anel = ImageChops.multiply(ImageChops.subtract(cortes.filter(ImageFilter.MaxFilter(k)), cortes), shell)
    so = Image.new("RGBA", (W, W), (50, 3, 10, 0))
    so.putalpha(anel)
    corpo.alpha_composite(so)

    bg = _fundo_quadrado()
    bg.alpha_composite(corpo)
    return bg.resize((N, N), Image.LANCZOS)


def _fonte(px):
    for cand in ("arialbd.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(cand, px)
        except OSError:
            continue
    return ImageFont.load_default()


def com_badge(base, letra):
    """Mesmo elmo + um selo redondo com a letra (C/E/M) no canto."""
    im = base.copy().convert("RGBA")
    d = ImageDraw.Draw(im)
    s = int(N * 0.46)
    x0, y0 = N - s - int(N * 0.04), N - s - int(N * 0.04)
    d.ellipse([x0, y0, x0 + s, y0 + s], fill=(255, 51, 85, 255),
              outline=(26, 6, 10, 255), width=max(2, N // 64))
    f = _fonte(int(s * 0.62))
    tb = d.textbbox((0, 0), letra, font=f)
    tx = x0 + (s - (tb[2] - tb[0])) // 2 - tb[0]
    ty = y0 + (s - (tb[3] - tb[1])) // 2 - tb[1]
    d.text((tx, ty), letra, fill=(255, 255, 255, 255), font=f)
    return im


def main():
    base = elmo()
    base.save(os.path.join(AQUI, "sparta.ico"), sizes=SIZES)
    print("gerado assets/sparta.ico")
    for nome, letra in [("cofre", "C"), ("explorador", "E"), ("mixer", "M")]:
        com_badge(base, letra).save(os.path.join(AQUI, f"{nome}.ico"), sizes=SIZES)
    print("gerados cofre/explorador/mixer .ico")


if __name__ == "__main__":
    main()
