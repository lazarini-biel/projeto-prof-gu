"""
Gera os ícones .ico do SPARTA a partir das artes em assets/arte/*.webp
(logos vermelhas estilo hacker). Recorta o emblema (sem o texto embaixo) e
salva em vários tamanhos.

Rode se trocar as artes:

    cd automacao_pc
    py assets\\converter_logos.py

Precisa do Pillow com suporte a webp (já vem no Pillow normal):
    py -m pip install pillow
"""
import os

from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
ARTE = os.path.join(AQUI, "arte")
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# arte de origem -> (arquivo .ico, caixa do emblema na imagem 1122x1402)
#   a caixa (esquerda, topo, direita, baixo) recorta só o emblema, fora o texto.
LOGOS = [
    ("sparta.webp",   "sparta.ico",     (17, 42, 1027, 1052)),
    ("cofre.webp",    "cofre.ico",      (110, 110, 1010, 1010)),
    ("arquivos.webp", "explorador.ico", (140, 175, 940, 975)),
    ("mixer.webp",    "mixer.ico",      (120, 115, 970, 965)),
]


def main():
    for origem, destino, box in LOGOS:
        caminho = os.path.join(ARTE, origem)
        emblema = Image.open(caminho).convert("RGBA").crop(box)
        # garante quadrado (caso a caixa não seja perfeita)
        lado = max(emblema.size)
        fundo = Image.new("RGBA", (lado, lado), (0, 0, 0, 255))
        fundo.paste(emblema, ((lado - emblema.width) // 2, (lado - emblema.height) // 2))
        fundo = fundo.resize((256, 256), Image.LANCZOS)
        fundo.convert("RGB").save(os.path.join(AQUI, destino), sizes=SIZES)
        print("gerado", destino)


if __name__ == "__main__":
    main()
