"""
Discos: relatório de espaço, maiores arquivos e redistribuição automática.

A redistribuição varre as pastas de origem (Área de Trabalho, Documentos,
Downloads...) e manda cada arquivo para o disco/pasta definido para o tipo
dele no config, ex.: vídeos para E:/Vídeos, fotos para D:/Fotos. Assim o SSD
do sistema fica só com o que precisa estar nele.

Segurança:
  - nunca toca em pastas de programas/sistema (só nas origens que você listar);
  - pula arquivos alterados recentemente (você pode estar usando);
  - não enche o disco de destino (respeita uma margem de espaço livre);
  - sem --executar só mostra o plano; com --executar tudo pode ser desfeito.
"""

import fnmatch
import heapq
import os
import shutil
import time
from collections import defaultdict
from pathlib import Path

from .duplicados import PASTAS_IGNORADAS
from .movimentos import Movimentos
from .util import WINDOWS, arquivo_intocavel, eh_link_ou_juncao, tamanho_legivel

TIPOS_UNIDADE = {2: "Removível", 3: "Interno", 4: "Rede", 6: "RAM"}


def unidades():
    """[(raiz, rótulo, tipo, total, livre)] de todos os discos com mídia."""
    if not WINDOWS:
        uso = shutil.disk_usage("/")
        return [("/", "", "Interno", uso.total, uso.free)]

    import ctypes
    k32 = ctypes.windll.kernel32
    lista = []
    mascara = k32.GetLogicalDrives()
    for i in range(26):
        if not mascara & (1 << i):
            continue
        raiz = f"{chr(65 + i)}:\\"
        tipo = k32.GetDriveTypeW(raiz)
        if tipo not in TIPOS_UNIDADE:
            continue
        nome = ctypes.create_unicode_buffer(261)
        k32.GetVolumeInformationW(raiz, nome, 261, None, None, None, None, 0)
        try:
            uso = shutil.disk_usage(raiz)
        except OSError:
            continue   # leitor de cartão vazio etc.
        lista.append((raiz, nome.value, TIPOS_UNIDADE[tipo], uso.total, uso.free))
    return lista


def relatorio(saida=print):
    for raiz, rotulo, tipo, total, livre in unidades():
        pct = (total - livre) / total if total else 0
        barra = "█" * round(pct * 24) + "░" * (24 - round(pct * 24))
        alerta = "  ⚠ quase cheio" if pct > 0.9 else ""
        saida(f"{raiz:<4} {rotulo[:14]:<14} {tipo:<9} [{barra}] {pct:4.0%}  "
              f"livre {tamanho_legivel(livre):>9} de {tamanho_legivel(total):>9}{alerta}")


def _varrer(raizes, ignorar=()):
    ignorar = PASTAS_IGNORADAS | {i.lower() for i in ignorar}
    for raiz in raizes:
        for pasta, subpastas, arquivos in os.walk(raiz):
            subpastas[:] = [d for d in subpastas
                            if d.lower() not in ignorar and not d.startswith("$")
                            and "onedrive" not in d.lower()
                            and not eh_link_ou_juncao(os.path.join(pasta, d))]
            for nome in arquivos:
                p = Path(pasta, nome)
                try:
                    st = p.stat(follow_symlinks=False)
                except OSError:
                    continue
                if not arquivo_intocavel(st):
                    yield p, st


def maiores(raizes, top=30, saida=print):
    """Os maiores arquivos — normalmente é onde está o espaço que sumiu."""
    lista = heapq.nlargest(top, ((st.st_size, str(p)) for p, st in _varrer(raizes)))
    for tamanho, p in lista:
        saida(f"{tamanho_legivel(tamanho):>10}  {p}")
    return lista


def _dentro(caminho, pasta):
    try:
        Path(caminho).relative_to(pasta)
        return True
    except ValueError:
        return False


def _disco(caminho):
    """"D:\\Fotos\\x.jpg" -> "D:\\" (a raiz do disco onde o caminho está)."""
    return Path(caminho).anchor.upper() or "/"


def planejar_redistribuicao(origens, destinos, mapa, manter=(), idade_minima_dias=7,
                            margem_livre_pct=10, agora=None, uso_disco=shutil.disk_usage):
    """Devolve (plano [(origem, destino, tamanho, categoria)], pulados {motivo: qtd})."""
    agora = time.time() if agora is None else agora
    destinos = {cat: Path(p) for cat, p in destinos.items()}
    origens = [Path(o) for o in origens if Path(o).is_dir()]
    reservado = defaultdict(int)       # bytes já planejados por disco de destino
    livre_cache = {}
    plano, pulados = [], defaultdict(int)

    def cabe(disco, tamanho):
        if disco not in livre_cache:
            try:
                uso = uso_disco(disco)
            except OSError:
                livre_cache[disco] = None
            else:
                livre_cache[disco] = uso.free - uso.total * margem_livre_pct / 100
        livre = livre_cache[disco]
        return livre is not None and reservado[disco] + tamanho <= livre

    for origem in origens:
        for arquivo, st in _varrer([origem]):
            categoria = mapa.get(arquivo.suffix.lower())
            if categoria not in destinos:
                continue
            raiz_destino = destinos[categoria]
            if _dentro(arquivo, raiz_destino):
                continue    # já está no lugar certo
            if any(fnmatch.fnmatch(arquivo.name.lower(), m.lower()) for m in manter):
                pulados["marcado para manter"] += 1
                continue
            if agora - st.st_mtime < idade_minima_dias * 86400:
                pulados["alterado recentemente"] += 1
                continue

            relativo = arquivo.relative_to(origem)
            if len(relativo.parts) > 1 and relativo.parts[0] == categoria:
                relativo = Path(*relativo.parts[1:])   # Downloads/Imagens/x.jpg -> Fotos/x.jpg
            disco = _disco(raiz_destino)
            mesmo_disco = _disco(arquivo) == disco
            if not mesmo_disco and not cabe(disco, st.st_size):
                pulados[f"sem espaço em {disco}"] += 1
                continue
            if not mesmo_disco:
                reservado[disco] += st.st_size
            plano.append((arquivo, raiz_destino / relativo, st.st_size, categoria))
    return plano, dict(pulados)


def redistribuir(cfg, mapa, aplicar=False, saida=print):
    from .util import caminho
    plano, pulados = planejar_redistribuicao(
        [caminho(o) for o in cfg.get("origens", [])],
        {cat: caminho(p) for cat, p in cfg.get("destinos", {}).items()},
        mapa,
        manter=cfg.get("manter", []),
        idade_minima_dias=cfg.get("idade_minima_dias", 7),
        margem_livre_pct=cfg.get("espaco_livre_minimo_pct", 10),
    )
    if not plano:
        saida("Tudo já está no lugar certo.")
    else:
        por_destino = defaultdict(lambda: [0, 0])
        for _, destino, tamanho, categoria in plano:
            por_destino[(categoria, cfg["destinos"][categoria])][0] += 1
            por_destino[(categoria, cfg["destinos"][categoria])][1] += tamanho
        saida("Plano de redistribuição:" if not aplicar else "Redistribuindo:")
        for (categoria, destino), (qtd, tamanho) in sorted(por_destino.items()):
            saida(f"  {categoria:<16} {qtd:>6} arquivo(s) {tamanho_legivel(tamanho):>10}  →  {destino}")
    for motivo, qtd in pulados.items():
        saida(f"  (pulados: {qtd} — {motivo})")
    if not plano:
        return plano
    if not aplicar:
        saida("\nNada foi movido ainda. Use --executar para aplicar.")
        return plano

    erros = 0
    with Movimentos("redistribuir") as mov:
        for i, (origem, destino, _, _) in enumerate(plano, 1):
            try:
                mov.mover(origem, destino)
            except OSError as erro:
                erros += 1
                saida(f"  ! {origem}: {erro}")
            if i % 200 == 0:
                saida(f"  ... {i}/{len(plano)}")
    saida(f"\n{len(plano) - erros} arquivo(s) movidos. Para desfazer: python pc.py desfazer")
    return plano
