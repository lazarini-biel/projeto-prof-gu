"""
Encontra arquivos duplicados (conteúdo idêntico, mesmo com nomes diferentes)
e libera espaço.

Como funciona, do mais barato para o mais caro:
  1. agrupa por tamanho (arquivos de tamanhos diferentes nunca são iguais);
  2. dentro de cada grupo, compara o começo e o fim do arquivo;
  3. só os que continuam empatados têm o conteúdo inteiro comparado (hash).

Em cada grupo um arquivo é MANTIDO (o que está nas pastas preferidas, senão o
mais antigo) e os outros podem ir para a Lixeira ou ser excluídos.
"""

import csv
import hashlib
import os
import stat
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .util import (PASTA_LOGS, WINDOWS, arquivo_intocavel, eh_link_ou_juncao,
                   tamanho_legivel)

# Pastas nunca varridas (programas e sistema guardam cópias de propósito).
PASTAS_IGNORADAS = {
    "windows", "program files", "program files (x86)", "programdata", "appdata",
    "system volume information", "recovery", "msocache", "perflogs", "$recycle.bin",
    ".git", "node_modules", "__pycache__", ".venv", "venv", "steamapps",
}

_BLOCO = 64 * 1024


@dataclass
class Grupo:
    tamanho: int
    arquivos: list = field(default_factory=list)   # [(Path, mtime)]

    @property
    def desperdicio(self):
        return self.tamanho * (len(self.arquivos) - 1)


def listar_arquivos(raizes, tamanho_min=1, ignorar=()):
    ignorar = PASTAS_IGNORADAS | {i.lower() for i in ignorar}
    vistos = set()
    for raiz in raizes:
        for pasta, subpastas, arquivos in os.walk(raiz):
            subpastas[:] = [
                d for d in subpastas
                if d.lower() not in ignorar and not d.startswith("$")
                and not eh_link_ou_juncao(os.path.join(pasta, d))
            ]
            for nome in arquivos:
                p = os.path.join(pasta, nome)
                try:
                    st = os.stat(p, follow_symlinks=False)
                except OSError:
                    continue
                if (not stat.S_ISREG(st.st_mode) or st.st_size < tamanho_min
                        or arquivo_intocavel(st)):
                    continue
                chave = (st.st_dev, st.st_ino)
                if st.st_ino and chave in vistos:   # mesma pasta listada 2x / hardlink
                    continue
                vistos.add(chave)
                yield Path(p), st


def _hash(caminho, parcial):
    h = hashlib.blake2b(digest_size=20)
    with open(caminho, "rb") as f:
        if parcial:
            h.update(f.read(_BLOCO))
            f.seek(-min(_BLOCO, os.fstat(f.fileno()).st_size), os.SEEK_END)
            h.update(f.read(_BLOCO))
        else:
            for bloco in iter(lambda: f.read(1024 * 1024), b""):
                h.update(bloco)
    return h.digest()


def _separar_por_hash(itens, parcial):
    grupos = defaultdict(list)
    for caminho, st in itens:
        try:
            grupos[_hash(caminho, parcial)].append((caminho, st))
        except OSError:
            continue
    return [g for g in grupos.values() if len(g) > 1]


def encontrar(raizes, tamanho_min=1, ignorar=(), progresso=None):
    """Devolve (grupos de duplicados ordenados pelo espaço desperdiçado, total varrido)."""
    por_tamanho = defaultdict(list)
    total = 0
    for caminho, st in listar_arquivos(raizes, tamanho_min, ignorar):
        por_tamanho[st.st_size].append((caminho, st))
        total += 1
        if progresso and total % 2000 == 0:
            progresso(total)

    grupos = []
    for tamanho, itens in por_tamanho.items():
        if len(itens) < 2:
            continue
        for candidatos in _separar_por_hash(itens, parcial=True):
            # Até 2 blocos, o hash parcial já leu o arquivo inteiro.
            iguais = [candidatos] if tamanho <= 2 * _BLOCO else _separar_por_hash(candidatos, parcial=False)
            for g in iguais:
                grupos.append(Grupo(tamanho, [(c, st.st_mtime) for c, st in g]))

    grupos.sort(key=lambda g: g.desperdicio, reverse=True)
    return grupos, total


def escolher_original(grupo, preferir=()):
    """(arquivo mantido, [duplicados que podem sair])."""
    preferir = [os.path.join(str(Path(p)), "").lower() for p in preferir]   # com barra no fim

    def chave(item):
        caminho, mtime = item
        texto = str(caminho).lower()
        preferido = any(texto.startswith(p) for p in preferir)
        return (not preferido, mtime, len(texto))

    ordenados = sorted(grupo.arquivos, key=chave)
    return ordenados[0][0], [c for c, _ in ordenados[1:]]


def mandar_para_lixeira(caminhos):
    """Envia arquivos para a Lixeira do Windows. Devolve quantos foram."""
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                    ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]

    FO_DELETE = 3
    FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 0x4, 0x10, 0x40, 0x400
    enviados = 0
    for i in range(0, len(caminhos), 200):
        lote = [str(Path(c).resolve()) for c in caminhos[i:i + 200]]
        buffer = ctypes.create_unicode_buffer("\0".join(lote) + "\0")
        op = SHFILEOPSTRUCTW(wFunc=FO_DELETE,
                             pFrom=ctypes.cast(buffer, wintypes.LPCWSTR),
                             fFlags=FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI)
        if ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0:
            enviados += sum(1 for c in lote if not os.path.exists(c))
    return enviados


def _salvar_csv(grupos, preferir):
    PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    arquivo = PASTA_LOGS / f"duplicados_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    with open(arquivo, "w", newline="", encoding="utf-8-sig") as f:   # -sig: Excel abre com acentos
        w = csv.writer(f, delimiter=";")
        w.writerow(["grupo", "tamanho", "situacao", "caminho"])
        for n, grupo in enumerate(grupos, 1):
            original, extras = escolher_original(grupo, preferir)
            w.writerow([n, grupo.tamanho, "MANTER", original])
            for c in extras:
                w.writerow([n, grupo.tamanho, "duplicado", c])
    return arquivo


def executar(raizes, acao="relatorio", tamanho_min=1, ignorar=(), preferir=(),
             mostrar=15, confirmado=False, saida=print, entrada=input):
    raizes = [Path(r) for r in raizes if Path(r).is_dir()]
    if not raizes:
        saida("Nenhuma das pastas configuradas existe.")
        return []

    saida("Procurando duplicados em:\n  " + "\n  ".join(map(str, raizes)))
    interativo = sys.stdout is not None and sys.stdout.isatty()

    def progresso(n):
        if interativo:
            print(f"\r  {n} arquivos lidos...", end="", flush=True)

    grupos, total = encontrar(raizes, tamanho_min, ignorar, progresso)
    if interativo:
        print("\r" + " " * 40 + "\r", end="")
    if not grupos:
        saida(f"{total} arquivos verificados. Nenhum duplicado. 🎉")
        return []

    desperdicio = sum(g.desperdicio for g in grupos)
    extras_total = sum(len(g.arquivos) - 1 for g in grupos)
    saida(f"{total} arquivos verificados: {len(grupos)} grupos de duplicados, "
          f"{extras_total} cópias sobrando, {tamanho_legivel(desperdicio)} para liberar.\n")
    for grupo in grupos[:mostrar]:
        original, extras = escolher_original(grupo, preferir)
        saida(f"[{tamanho_legivel(grupo.tamanho)} × {len(grupo.arquivos)}]")
        saida(f"   MANTER   {original}")
        for c in extras:
            saida(f"   remover  {c}")
    if len(grupos) > mostrar:
        saida(f"... e mais {len(grupos) - mostrar} grupos.")
    saida(f"\nLista completa: {_salvar_csv(grupos, preferir)}")

    removiveis = [c for g in grupos for c in escolher_original(g, preferir)[1]]
    if acao == "relatorio":
        saida("Nada foi apagado. Use --acao lixeira (recuperável) ou --acao excluir.")
        return grupos

    if acao == "lixeira":
        if not WINDOWS:
            saida("A Lixeira só é suportada no Windows. Use --acao excluir.")
            return grupos
        enviados = mandar_para_lixeira(removiveis)
        saida(f"{enviados} cópia(s) foram para a Lixeira. Esvazie-a para liberar o espaço "
              "(em pendrives/HDs externos o Windows apaga direto, sem Lixeira).")
        return grupos

    if acao == "excluir":
        if not confirmado:
            resposta = entrada(f"Excluir DEFINITIVAMENTE {len(removiveis)} arquivo(s)? "
                               "Digite EXCLUIR para confirmar: ")
            if resposta.strip().upper() != "EXCLUIR":
                saida("Cancelado.")
                return grupos
        apagados = 0
        for c in removiveis:
            try:
                c.unlink()
                apagados += 1
            except OSError as erro:
                saida(f"  ! {c}: {erro}")
        saida(f"{apagados} cópia(s) excluídas.")
    return grupos
