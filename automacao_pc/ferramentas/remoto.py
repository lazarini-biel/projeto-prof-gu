"""
Controle remoto do PC pelo Telegram (de qualquer lugar, pelo celular).

O PC fica "perguntando" ao Telegram se chegou mensagem nova (não abre
nenhuma porta no seu roteador). Só obedece às contas cujos IDs estão em
"ids_autorizados"; mensagens de qualquer outra pessoa são ignoradas.

Configuração (uma vez):
  1. No Telegram, fale com @BotFather -> /newbot -> copie o token para
     config.json em "remoto" > "token".
  2. Rode `python pc.py remoto` e mande /start para o seu bot. Ele responde
     com o seu ID; coloque-o em "ids_autorizados" e rode de novo.
"""

import json
import platform
import socket
import time
import urllib.error
import urllib.request

from . import discos, energia, limpeza
from .util import tamanho_legivel, tempo_ligado

AJUDA = """Comandos:
/status — como está o PC
/desligar [min] — desliga (padrão: 1 min)
/reiniciar [min] — reinicia (padrão: 1 min)
/cancelar — cancela desligar/reiniciar
/hibernar — hiberna agora
/bloquear — bloqueia a tela
/limpar — limpa temporários e caches
/discos — espaço livre"""

MENU = [("status", "Como está o PC"), ("desligar", "Desliga (minutos opcional)"),
        ("reiniciar", "Reinicia (minutos opcional)"), ("cancelar", "Cancela desligar/reiniciar"),
        ("hibernar", "Hiberna agora"), ("bloquear", "Bloqueia a tela"),
        ("limpar", "Limpa temporários e caches"), ("discos", "Espaço livre nos discos")]


def _minutos(args, padrao=1):
    try:
        return max(0, float(args[0].replace(",", "."))) if args else padrao
    except ValueError:
        return padrao


class Bot:
    def __init__(self, token, ids_autorizados, cfg_limpeza=None, http=None, log=print):
        self.token = token
        self.autorizados = {int(i) for i in ids_autorizados}
        self.cfg_limpeza = cfg_limpeza or {}
        self.http = http or self._http
        self.log = log
        self.offset = 0
        self.conectado = False

    def _http(self, metodo, params, timeout):
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{self.token}/{metodo}",
            data=json.dumps(params).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def chamar(self, metodo, **params):
        # "timeout" do getUpdates é a espera do Telegram; a conexão espera um pouco mais.
        resposta = self.http(metodo, params, params.get("timeout", 0) + 20)
        if not resposta.get("ok"):
            raise RuntimeError(resposta.get("description", "erro do Telegram"))
        return resposta.get("result")

    def responder(self, chat_id, texto):
        self.chamar("sendMessage", chat_id=chat_id, text=texto)

    # ------------------------------------------------------------- comandos
    def comando(self, texto):
        partes = texto.strip().split()
        if not partes:
            return None
        nome = partes[0].lstrip("/").split("@")[0].lower()
        args = partes[1:]

        if nome in ("start", "ajuda", "help"):
            return f"🖥 {socket.gethostname()} às ordens.\n\n{AJUDA}"
        if nome == "status":
            livres = ", ".join(f"{r.rstrip(chr(92))} {tamanho_legivel(l)} livres"
                               for r, _, _, _, l in discos.unidades())
            return (f"🖥 {socket.gethostname()} ({platform.system()} {platform.release()})\n"
                    f"⏱ Ligado há {tempo_ligado()}\n💾 {livres}")
        if nome == "desligar":
            return energia.desligar(_minutos(args))[1] + " /cancelar para abortar."
        if nome == "reiniciar":
            return energia.reiniciar(_minutos(args))[1] + " /cancelar para abortar."
        if nome == "cancelar":
            return energia.cancelar()[1]
        if nome == "hibernar":
            return energia.hibernar()[1]
        if nome == "bloquear":
            return energia.bloquear()[1]
        if nome == "limpar":
            linhas = []
            limpeza.executar(aplicar=True, saida=linhas.append,
                             idade_horas=self.cfg_limpeza.get("idade_minima_horas", 24),
                             navegadores=self.cfg_limpeza.get("navegadores", True))
            return "🧹 " + "\n".join(linhas)
        if nome == "discos":
            linhas = []
            discos.relatorio(saida=linhas.append)
            return "\n".join(linhas)
        return f"Não conheço /{nome}.\n\n{AJUDA}"

    def tratar(self, update):
        msg = update.get("message") or {}
        texto = msg.get("text")
        if not texto:
            return
        chat_id = msg["chat"]["id"]
        remetente = msg.get("from", {}).get("id")
        if not self.autorizados:
            self.responder(chat_id, f"Seu ID é {remetente}.\nColoque-o em config.json > "
                                    "remoto > ids_autorizados e reinicie o bot.")
            self.log(f"Mensagem de ID {remetente} (nenhum ID autorizado ainda).")
            return
        if remetente not in self.autorizados:
            self.log(f"Ignorado: mensagem de ID não autorizado {remetente}.")
            return
        self.log(f"Comando de {remetente}: {texto}")
        try:
            resposta = self.comando(texto)
        except Exception as erro:   # um comando com erro não pode derrubar o bot
            resposta = f"Erro: {erro}"
        if resposta:
            self.responder(chat_id, resposta)

    # ----------------------------------------------------------------- loop
    def descartar_pendentes(self):
        """Ignora o que foi enviado com o PC desligado (um /desligar antigo
        desligaria o PC assim que ele ligasse)."""
        ultimos = self.chamar("getUpdates", offset=-1, timeout=0)
        if ultimos:
            self.offset = ultimos[-1]["update_id"] + 1

    def rodar(self):
        espera = 5
        while True:
            try:
                if not self.conectado:
                    self.descartar_pendentes()
                    self.chamar("setMyCommands", commands=[
                        {"command": c, "description": d} for c, d in MENU])
                    self.conectado = True
                    self.log("Bot conectado ao Telegram. Aguardando comandos...")
                for update in self.chamar("getUpdates", timeout=60, offset=self.offset,
                                          allowed_updates=["message"]) or []:
                    self.offset = update["update_id"] + 1
                    self.tratar(update)
                espera = 5
            except (urllib.error.URLError, OSError, RuntimeError, ValueError) as erro:
                if isinstance(erro, urllib.error.HTTPError) and erro.code == 401:
                    self.log("Token inválido. Confira config.json > remoto > token.")
                    return
                self.log(f"Sem conexão ({erro}). Tentando de novo em {espera}s...")
                time.sleep(espera)
                espera = min(espera * 2, 300)
