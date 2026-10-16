"""
Organiza uma pasta (normalmente Downloads) separando os arquivos por tipo:
PDFs, Imagens, Instaladores, Planilhas...

Só mexe nos arquivos soltos da pasta (subpastas ficam como estão) e pula
downloads em andamento e arquivos modificados há poucos minutos.
"""

import time
from collections import defaultdict
from pathlib import Path

from .categorias import IGNORAR_NOMES, INCOMPLETOS, OUTROS
from .movimentos import Movimentos
from .util import tamanho_legivel


def planejar(pasta, mapa, idade_minima_min=10, separar_por_ano=False,
             mover_desconhecidos=True, agora=None):
    """Lista de (origem, destino, tamanho, categoria). Não move nada."""
    pasta = Path(pasta)
    agora = time.time() if agora is None else agora
    itens = sorted(pasta.iterdir(), key=lambda p: p.name.lower())
    nomes = {p.name.lower() for p in itens}
    plano = []

    for item in itens:
        nome = item.name.lower()
        if (not item.is_file() or item.is_symlink() or nome in IGNORAR_NOMES
                or nome.startswith("~$") or item.suffix.lower() in INCOMPLETOS):
            continue
        # Firefox cria "video.mp4" vazio + "video.mp4.part" enquanto baixa.
        if any(nome + ext in nomes for ext in INCOMPLETOS):
            continue
        try:
            st = item.stat()
        except OSError:
            continue
        if agora - st.st_mtime < idade_minima_min * 60:
            continue

        categoria = mapa.get(item.suffix.lower())
        if categoria is None:
            if not mover_desconhecidos:
                continue
            categoria = OUTROS
        destino = pasta / categoria
        if separar_por_ano:
            destino = destino / time.strftime("%Y", time.localtime(st.st_mtime))
        plano.append((item, destino / item.name, st.st_size, categoria))
    return plano


def executar(pasta, mapa, aplicar=False, saida=print, **opcoes):
    pasta = Path(pasta)
    if not pasta.is_dir():
        saida(f"Pasta não encontrada: {pasta}")
        return []
    plano = planejar(pasta, mapa, **opcoes)
    if not plano:
        saida(f"Nada para organizar em {pasta}.")
        return []

    resumo = defaultdict(lambda: [0, 0])
    for _, _, tamanho, categoria in plano:
        resumo[categoria][0] += 1
        resumo[categoria][1] += tamanho
    saida(f"{'Organizando' if aplicar else 'Prévia —'} {pasta}")
    for categoria, (qtd, tamanho) in sorted(resumo.items()):
        saida(f"  {categoria:<18} {qtd:>5} arquivo(s) {tamanho_legivel(tamanho):>11}")

    if not aplicar:
        saida("\nNada foi movido ainda. Use --executar para aplicar.")
        return plano

    erros = 0
    with Movimentos("organizar") as mov:
        for origem, destino, _, _ in plano:
            try:
                mov.mover(origem, destino)
            except OSError as erro:
                erros += 1
                saida(f"  ! {origem.name}: {erro}")
    saida(f"\n{len(plano) - erros} arquivo(s) organizados."
          + (f" {erros} em uso/bloqueados ficaram onde estavam." if erros else "")
          + " Para desfazer: python pc.py desfazer")
    return plano
