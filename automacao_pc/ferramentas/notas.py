"""
Lembretes / notas rápidas, salvos localmente num arquivo JSON (notas.json
ao lado do config). Nada vai para a internet.
"""

import json
import time

from . import tema
from .util import PASTA_BASE

ARQUIVO = PASTA_BASE / "notas.json"


def _carregar():
    try:
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _salvar(lista):
    ARQUIVO.write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")


def adicionar(texto):
    texto = texto.strip()
    if not texto:
        tema.saida("Nota vazia, nada feito.")
        return
    lista = _carregar()
    lista.append({"texto": texto, "quando": int(time.time())})
    _salvar(lista)
    tema.saida(tema.bom(f"Anotado: {texto}"))


def remover(numero):
    lista = _carregar()
    if not 1 <= numero <= len(lista):
        tema.saida("Número inválido.")
        return
    nota = lista.pop(numero - 1)
    _salvar(lista)
    tema.saida(tema.cor(f"Removida: {nota['texto']}", tema.CINZA))


def limpar():
    _salvar([])
    tema.saida(tema.cor("Todas as notas foram apagadas.", tema.CINZA))


def listar():
    tema.cabecalho("Lembretes / notas", str(ARQUIVO))
    lista = _carregar()
    if not lista:
        tema.saida(tema.cor("Nenhuma nota. Adicione com: py pc.py notas add \"sua nota\"", tema.CINZA))
        return
    for i, nota in enumerate(lista, 1):
        data = time.strftime("%d/%m %H:%M", time.localtime(nota["quando"]))
        tema.saida(f"  {tema.cor(f'{i:>2}.', tema.VIVO)} {tema.realce(nota['texto'])}  "
                   f"{tema.cor('(' + data + ')', tema.CINZA)}")
