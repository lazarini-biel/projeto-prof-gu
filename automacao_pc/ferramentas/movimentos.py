"""
Move arquivos guardando um registro de tudo, para poder desfazer depois.

Cada operação gera um logs/movimentos_<data>_<operacao>.jsonl com uma linha
{"de": ..., "para": ...} por arquivo. `desfazer` lê esse arquivo de trás
para frente e devolve cada arquivo ao lugar original.
"""

import json
import shutil
import time
from pathlib import Path

from .util import PASTA_LOGS


def nome_livre(destino):
    """Se já existe "foto.jpg" no destino, devolve "foto (2).jpg", "foto (3).jpg"..."""
    destino = Path(destino)
    if not destino.exists():
        return destino
    i = 2
    while True:
        candidato = destino.with_name(f"{destino.stem} ({i}){destino.suffix}")
        if not candidato.exists():
            return candidato
        i += 1


class Movimentos:
    def __init__(self, operacao, pasta_logs=PASTA_LOGS):
        carimbo = time.strftime("%Y%m%d_%H%M%S")
        self.arquivo = Path(pasta_logs) / f"movimentos_{carimbo}_{operacao}.jsonl"
        self._f = None
        self.total = 0

    def mover(self, origem, destino):
        origem = Path(origem)
        destino = nome_livre(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(origem), str(destino))
        except OSError:
            # Entre discos o move é "copia e apaga": se apagar falhou (arquivo
            # aberto em outro programa), remove a cópia para não duplicar.
            if origem.exists() and destino.exists():
                destino.unlink()
            raise
        self._registrar(origem, destino)
        return destino

    def _registrar(self, origem, destino):
        if self._f is None:
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            self._f = open(self.arquivo, "a", encoding="utf-8")
        self._f.write(json.dumps({"de": str(origem), "para": str(destino)},
                                 ensure_ascii=False) + "\n")
        self._f.flush()
        self.total += 1

    def fechar(self):
        if self._f:
            self._f.close()
            self._f = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.fechar()


def registros_disponiveis(pasta_logs=PASTA_LOGS):
    """Registros que ainda podem ser desfeitos, do mais recente para o mais antigo."""
    return sorted(Path(pasta_logs).glob("movimentos_*.jsonl"), reverse=True)


def desfazer(arquivo, saida=print):
    arquivo = Path(arquivo)
    with open(arquivo, encoding="utf-8") as f:
        linhas = [json.loads(l) for l in f if l.strip()]

    voltaram, pulados = 0, 0
    for item in reversed(linhas):
        de, para = Path(item["de"]), Path(item["para"])
        if not para.exists() or de.exists():
            pulados += 1
            continue
        try:
            de.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(para), str(de))
            voltaram += 1
        except OSError as erro:
            pulados += 1
            saida(f"  ! {para}: {erro}")
            continue
        try:
            para.parent.rmdir()   # só remove se ficou vazia
        except OSError:
            pass

    arquivo.rename(arquivo.with_suffix(".desfeito"))
    saida(f"{voltaram} arquivo(s) voltaram ao lugar original"
          + (f", {pulados} pulado(s) (já movidos ou apagados)." if pulados else "."))
    return voltaram
