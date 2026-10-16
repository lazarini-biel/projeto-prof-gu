"""
COFRE — gerenciador de senhas portátil.

Rode com:
    python cofre.py                 usa/cria "cofre.dat" ao lado do programa
    python cofre.py E:/meu.dat      usa outro arquivo

Empacotado como Cofre.exe (veja gerar_exe.bat) ele roda direto do pendrive:
o executável e o cofre.dat ficam juntos, nada é instalado no PC.

A tela é HTML/CSS/JS (pasta ui/) exibida pelo pywebview, que no Windows 11
usa o WebView2 (o motor do Edge, que já vem no sistema).
"""

import json
import os
import shutil
import sys
import threading
import time
from pathlib import Path

import webview

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # ferramentas/
from ferramentas import navegadores   # noqa: E402

import autotipo   # noqa: E402
import nucleo   # noqa: E402

TITULO = "COFRE // acesso restrito"


def pasta_do_programa():
    """Ao lado do .exe (pendrive) ou ao lado deste script."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class Api:
    """Métodos chamados pela tela via window.pywebview.api.<nome>(...).

    O pywebview expõe todo atributo público ao JavaScript, por isso o estado
    interno fica em atributos com "_".
    """

    def __init__(self, cofre):
        self._cofre = cofre
        self._janela = None
        self._trava = threading.RLock()
        self._ultimo_uso = time.time()
        self._falhas = 0
        self._espera_ate = 0
        self._atalho = None
        self._alvo = None            # janela que pediu Ctrl+Alt+A
        self._copia = None           # (texto, timer) da área de transferência

    # ------------------------------------------------------------ util
    def _uso(self):
        self._ultimo_uso = time.time()

    def _js(self, codigo):
        if self._janela:
            try:
                self._janela.evaluate_js(codigo)
            except Exception:
                pass

    def _trazer_para_frente(self):
        if self._janela:
            self._janela.restore()
            self._janela.show()
            self._janela.on_top = True
            self._janela.on_top = False

    # ----------------------------------------------------------- estado
    def estado(self):
        with self._trava:
            return {
                "existe": self._cofre.existe,
                "aberto": self._cofre.aberto,
                "caminho": str(self._cofre.caminho),
                "windows": autotipo.WINDOWS,
                "espera": max(0, round(self._espera_ate - time.time())),
                "falhas": self._falhas,
                "kdf": nucleo.KDF_PADRAO,
                "minimo": nucleo.TAMANHO_MINIMO_SENHA,
                "preferencias": self._cofre.preferencias if self._cofre.aberto else None,
                "atalho": None if not self._atalho else (self._atalho.erro or "Ctrl+Alt+A"),
            }

    def atividade(self):
        self._uso()

    # ------------------------------------------------------- abrir/fechar
    def criar(self, senha, confirmacao):
        with self._trava:
            if senha != confirmacao:
                return {"ok": False, "erro": "As senhas não conferem."}
            try:
                inicio = time.time()
                self._cofre.criar(senha)
            except (ValueError, FileExistsError) as erro:
                return {"ok": False, "erro": str(erro)}
            self._ao_abrir()
            return {"ok": True, "ms": round((time.time() - inicio) * 1000)}

    def desbloquear(self, senha):
        with self._trava:
            espera = self._espera_ate - time.time()
            if espera > 0:
                return {"ok": False, "erro": "AGUARDE", "espera": round(espera)}
            inicio = time.time()
            try:
                self._cofre.abrir(senha)
            except nucleo.SenhaIncorreta:
                self._falhas += 1
                # A partir da 3ª falha: 2s, 4s, 8s... até 5 min entre tentativas.
                atraso = 0 if self._falhas < 3 else min(2 ** (self._falhas - 2), 300)
                self._espera_ate = time.time() + atraso
                return {"ok": False, "erro": "ACESSO NEGADO", "falhas": self._falhas, "espera": atraso}
            except (nucleo.CofreInvalido, OSError) as erro:
                return {"ok": False, "erro": str(erro)}
            self._falhas = 0
            self._ao_abrir()
            return {"ok": True, "ms": round((time.time() - inicio) * 1000)}

    def _ao_abrir(self):
        self._uso()
        if autotipo.WINDOWS and not self._atalho:
            self._atalho = autotipo.AtalhoGlobal(self._ao_atalho)
            self._atalho.start()
            self._atalho.registrado.wait(2)

    def bloquear(self):
        with self._trava:
            self._cofre.fechar()
            self._alvo = None
            self._limpar_copia(forcar=True)
        return True

    # -------------------------------------------------------- entradas
    def entradas(self):
        with self._trava:
            self._uso()
            return self._cofre.entradas()

    def entrada(self, id_):
        with self._trava:
            self._uso()
            return dict(self._cofre.obter(id_))

    def salvar(self, dados):
        with self._trava:
            self._uso()
            return {"ok": True, "id": self._cofre.salvar_entrada(dados)}

    def excluir(self, id_):
        with self._trava:
            self._uso()
            self._cofre.excluir(id_)
            return True

    def gerar(self, opcoes=None):
        return nucleo.gerar_senha(**(opcoes or {}))

    def forca(self, senha):
        return nucleo.forca(senha)

    def navegadores(self):
        return navegadores.instalados()

    def salvar_preferencias(self, prefs):
        with self._trava:
            atuais = self._cofre.preferencias
            for chave in nucleo.PREFERENCIAS_PADRAO:
                if chave in prefs:
                    atuais[chave] = max(1, int(prefs[chave]))
            self._cofre.salvar()
            return atuais

    def trocar_senha(self, atual, nova, confirmacao):
        with self._trava:
            if nova != confirmacao:
                return {"ok": False, "erro": "A nova senha e a confirmação não conferem."}
            try:
                self._cofre.trocar_senha(atual, nova)
            except nucleo.SenhaIncorreta:
                return {"ok": False, "erro": "Senha atual incorreta."}
            except ValueError as erro:
                return {"ok": False, "erro": str(erro)}
            return {"ok": True}

    # ------------------------------------------- área de transferência
    def copiar(self, id_, campo):
        with self._trava:
            self._uso()
            texto = self._cofre.obter(id_).get(campo, "")
        return self.copiar_texto(texto)

    def copiar_texto(self, texto):
        """Copia e apaga sozinho depois de alguns segundos."""
        if not autotipo.WINDOWS:
            return {"ok": False, "erro": "Copiar só funciona no Windows."}
        self._limpar_copia(forcar=False)
        autotipo.copiar(texto)
        segundos = self._cofre.preferencias["limpar_copia_segundos"]
        timer = threading.Timer(segundos, self._limpar_copia)
        timer.daemon = True
        self._copia = (texto, timer)
        timer.start()
        return {"ok": True, "segundos": segundos}

    def _limpar_copia(self, forcar=False):
        if not self._copia:
            return
        texto, timer = self._copia
        timer.cancel()
        self._copia = None
        try:
            if forcar or autotipo.texto_copiado() == texto:   # só apaga se ainda é a senha
                autotipo.limpar_area()
        except OSError:
            pass

    # --------------------------------------------------- navegador/sites
    def abrir_site(self, id_):
        with self._trava:
            e = self._cofre.obter(id_)
        if not e.get("url"):
            return {"ok": False, "erro": "Esta entrada não tem endereço."}
        navegadores.abrir(e["url"], e.get("navegador") or None)
        return {"ok": True}

    def abrir_e_preencher(self, id_):
        """Abre o site e, quando a página aparecer, digita o login."""
        if not autotipo.WINDOWS:
            return {"ok": False, "erro": "Preenchimento automático só no Windows."}
        resposta = self.abrir_site(id_)
        if not resposta["ok"]:
            return resposta
        threading.Thread(target=self._esperar_e_preencher, args=(id_,), daemon=True).start()
        return {"ok": True}

    def _esperar_e_preencher(self, id_):
        with self._trava:
            e = dict(self._cofre.obter(id_))
        fim = time.time() + 20
        while time.time() < fim:
            time.sleep(0.5)
            jan = autotipo.janela_ativa()
            if (jan and navegadores.nome_pelo_processo(jan.processo)
                    and nucleo.pontuar(e, jan.titulo) > 0):
                time.sleep(1.5)   # tempo para a página terminar de montar o formulário
                self._digitar(e, jan)
                return
        self._js("app.aviso('Não reconheci a página de login. Clique no campo e use Ctrl+Alt+A.', 'alerta')")

    def _digitar(self, entrada, jan):
        try:
            autotipo.digitar(entrada.get("sequencia") or nucleo.SEQUENCIA_PADRAO,
                             entrada.get("usuario", ""), entrada.get("senha", ""), jan.hwnd)
            self._js(f"app.aviso({json.dumps('Login preenchido: ' + entrada['titulo'])}, 'ok')")
        except autotipo.JanelaMudou:
            self._js("app.aviso('A janela mudou no meio — preenchimento cancelado por segurança.', 'erro')")
        except OSError as erro:
            self._js(f"app.aviso({json.dumps(str(erro))}, 'erro')")

    # ------------------------------------------------ atalho Ctrl+Alt+A
    def _ao_atalho(self):
        jan = autotipo.janela_ativa()
        if not jan or jan.pid == os.getpid():
            return
        with self._trava:
            if not self._cofre.aberto:
                self._alvo = None
                self._trazer_para_frente()
                self._js("app.aviso('Desbloqueie o cofre e aperte Ctrl+Alt+A de novo.', 'alerta')")
                return
            self._uso()
            candidatos = nucleo.melhores(self._cofre.dados["entradas"], jan.titulo)
        pontos = [nucleo.pontuar(c, jan.titulo) for c in candidatos[:2]]
        if len(candidatos) == 1 or (len(candidatos) > 1 and pontos[0] >= pontos[1] + 3):
            self._digitar(candidatos[0], jan)
            return
        # Nenhum ou vários: pergunta na tela qual usar.
        self._alvo = jan
        dados = {"titulo": jan.titulo,
                 "navegador": navegadores.nome_pelo_processo(jan.processo) or jan.processo,
                 "ids": [c["id"] for c in candidatos]}
        self._trazer_para_frente()
        self._js(f"app.escolherParaJanela({json.dumps(dados)})")

    def preencher_alvo(self, id_):
        """Chamado pela tela depois de escolher qual login usar."""
        jan, self._alvo = self._alvo, None
        if not jan:
            return {"ok": False, "erro": "A janela de destino não existe mais."}
        with self._trava:
            e = dict(self._cofre.obter(id_))
        if self._janela:
            self._janela.minimize()
        if not autotipo.focar(jan.hwnd):
            return {"ok": False, "erro": "Não consegui voltar para a janela do site."}
        threading.Thread(target=self._digitar, args=(e, jan), daemon=True).start()
        return {"ok": True}

    def ensinar_janela(self, id_, palavra):
        """Guarda uma palavra do título da janela para reconhecer o site da próxima vez."""
        with self._trava:
            e = self._cofre.obter(id_)
            palavras = e.setdefault("palavras", [])
            if palavra and palavra not in palavras:
                palavras.append(palavra)
                self._cofre.salvar()
        return True

    # ------------------------------------------------ importar/backup
    def importar(self):
        arquivos = self._janela.create_file_dialog(
            webview.OPEN_DIALOG, file_types=("Senhas exportadas (*.csv)", "Todos (*.*)"))
        if not arquivos:
            return {"ok": False, "cancelado": True}
        with self._trava:
            try:
                novos, repetidos = self._cofre.importar_csv(arquivos[0])
            except (OSError, UnicodeDecodeError, ValueError) as erro:
                return {"ok": False, "erro": f"Não consegui ler o arquivo: {erro}"}
        return {"ok": True, "novos": novos, "repetidos": repetidos, "arquivo": arquivos[0]}

    def backup(self):
        destino = self._janela.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=f"cofre-backup-{time.strftime('%Y%m%d')}.dat")
        if not destino:
            return {"ok": False, "cancelado": True}
        destino = destino if isinstance(destino, str) else destino[0]
        shutil.copy2(self._cofre.caminho, destino)
        return {"ok": True, "arquivo": destino}

    # ------------------------------------------------------- serviços
    def _vigiar_inatividade(self):
        while True:
            time.sleep(5)
            with self._trava:
                if not self._cofre.aberto:
                    continue
                limite = self._cofre.preferencias["bloqueio_minutos"] * 60
                if time.time() - self._ultimo_uso > limite:
                    self.bloquear()
                    self._js("app.bloqueadoPorInatividade()")

    def _ao_fechar(self):
        self.bloquear()
        if self._atalho:
            self._atalho.parar()


def main():
    arquivo = Path(sys.argv[1]) if len(sys.argv) > 1 else pasta_do_programa() / "cofre.dat"
    api = Api(nucleo.Cofre(arquivo))
    janela = webview.create_window(TITULO, "ui/index.html", js_api=api, width=1180, height=760,
                                   min_size=(900, 620), background_color="#03070b")
    api._janela = janela
    janela.events.closed += api._ao_fechar
    threading.Thread(target=api._vigiar_inatividade, daemon=True).start()
    webview.start(private_mode=True)


if __name__ == "__main__":
    main()
