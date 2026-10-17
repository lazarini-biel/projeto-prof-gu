"""
SPARTA // EXPLORADOR — explorador de arquivos no estilo SPARTA (vermelho),
com conexão direta ao Windows.

Navega como o Explorer, mas com extras: filtrar/colorir por categoria,
organizar a pasta por tipo num clique, renomear, mover, excluir (para a
Lixeira), criar pasta e buscar. A janela é pywebview (igual ao cofre);
a lógica de arquivos é Python puro.

Rode com:
    python explorador.py            abre na pasta do usuário
    python explorador.py D:/Fotos   abre numa pasta
    --janela                        abre em janela (padrão: tela cheia; F11 alterna)
"""

import os
import shutil
import sys
import time
from pathlib import Path

import webview

import icones   # ícones reais (mesma pasta)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # ferramentas/
from ferramentas import organizar as _org          # noqa: E402
from ferramentas.categorias import montar_mapa, OUTROS   # noqa: E402
from ferramentas.util import WINDOWS, tamanho_legivel, carregar_config, caminho as _caminho   # noqa: E402

TITULO = "SPARTA // EXPLORADOR"


def _recurso(rel):
    """Caminho de um recurso (ui/), funcionando empacotado (.exe) ou como script."""
    import os
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def _identidade_windows():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SPARTA.Explorador")
        except OSError:
            pass
_MAPA = montar_mapa()


def pasta_do_programa():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _categoria(p: Path):
    if p.is_dir():
        return "Pasta"
    return _MAPA.get(p.suffix.lower(), OUTROS)


def _lixeira(caminhos):
    """Manda para a Lixeira (Windows) ou apaga de vez (fora do Windows)."""
    if WINDOWS:
        from ferramentas.duplicados import mandar_para_lixeira
        return mandar_para_lixeira([Path(c) for c in caminhos])
    apagados = 0
    for c in caminhos:
        try:
            p = Path(c)
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            apagados += 1
        except OSError:
            pass
    return apagados


class Api:
    def __init__(self):
        self._janela = None
        self._inicio = None

    # ------------------------------------------------------------ base
    def estado(self):
        try:
            cfg = carregar_config()
        except Exception:
            cfg = {}
        inicio = self._inicio or cfg.get("explorador", {}).get("pasta_inicial", "~")
        return {"windows": WINDOWS, "inicio": str(_caminho(inicio))}

    def locais(self):
        """Atalhos: pastas do usuário + discos."""
        atalhos = []
        base = Path.home()
        for nome, sub in [("Início", ""), ("Área de Trabalho", "Desktop"),
                          ("Downloads", "Downloads"), ("Documentos", "Documents"),
                          ("Imagens", "Pictures"), ("Vídeos", "Videos"), ("Músicas", "Music")]:
            p = base / sub if sub else base
            if p.is_dir():
                atalhos.append({"nome": nome, "caminho": str(p), "tipo": "pasta"})
        discos = []
        try:
            from ferramentas.discos import unidades
            for raiz, rotulo, tipo, total, livre in unidades():
                uso = round((1 - livre / total) * 100) if total else 0
                discos.append({"nome": f"{raiz.rstrip(chr(92))} {rotulo}".strip(),
                               "caminho": raiz, "tipo": "disco", "uso": uso,
                               "livre": tamanho_legivel(livre), "total": tamanho_legivel(total)})
        except Exception:
            pass
        return {"atalhos": atalhos, "discos": discos}

    def listar(self, pasta):
        try:
            pasta = Path(pasta).resolve()
        except OSError:
            return {"erro": "Caminho inválido."}
        if not pasta.is_dir():
            return {"erro": f"Pasta não encontrada: {pasta}"}
        itens = []
        try:
            entradas = list(os.scandir(pasta))
        except PermissionError:
            return {"erro": "Sem permissão para abrir esta pasta."}
        except OSError as erro:
            return {"erro": str(erro)}
        for e in entradas:
            try:
                st = e.stat()
                ep = Path(e.path)
                pasta_bool = e.is_dir()
                oculto = e.name.startswith(".") or bool(getattr(st, "st_file_attributes", 0) & 0x2)
                itens.append({
                    "nome": e.name, "caminho": e.path, "pasta": pasta_bool,
                    "tamanho": 0 if pasta_bool else st.st_size,
                    "tamanho_fmt": "" if pasta_bool else tamanho_legivel(st.st_size),
                    "modificado": int(st.st_mtime),
                    "modificado_fmt": time.strftime("%d/%m/%Y %H:%M", time.localtime(st.st_mtime)),
                    "categoria": _categoria(ep), "ext": ep.suffix.lower().lstrip("."),
                    "oculto": oculto,
                })
            except OSError:
                continue
        pai = str(pasta.parent) if pasta.parent != pasta else None
        return {"pasta": str(pasta), "pai": pai, "nome": pasta.name or str(pasta),
                "itens": itens}

    # ------------------------------------------------------------ ações
    def abrir(self, caminho):
        """Abre um arquivo no programa padrão do Windows."""
        if not WINDOWS:
            return {"ok": False, "erro": "Abrir arquivos só funciona no Windows."}
        try:
            os.startfile(caminho)   # noqa: S606 (ação pedida pelo usuário)
            return {"ok": True}
        except OSError as erro:
            return {"ok": False, "erro": str(erro)}

    def abrir_no_windows(self, pasta):
        """Abre a pasta no Explorer do Windows."""
        if WINDOWS:
            try:
                os.startfile(pasta)
                return {"ok": True}
            except OSError as erro:
                return {"ok": False, "erro": str(erro)}
        return {"ok": False}

    def icone(self, caminho, tam=48):
        """data:image/png do ícone real do arquivo (ou miniatura de imagem)."""
        return {"img": icones.para_web(caminho, int(tam))}

    def nova_pasta(self, pasta, nome):
        nome = (nome or "").strip().strip(". ")
        if not nome or any(c in nome for c in '\\/:*?"<>|'):
            return {"ok": False, "erro": "Nome inválido."}
        destino = Path(pasta) / nome
        try:
            destino.mkdir(parents=False, exist_ok=False)
            return {"ok": True, "caminho": str(destino)}
        except FileExistsError:
            return {"ok": False, "erro": "Já existe uma pasta com esse nome."}
        except OSError as erro:
            return {"ok": False, "erro": str(erro)}

    def renomear(self, caminho, novo):
        novo = (novo or "").strip()
        if not novo or any(c in novo for c in '\\/:*?"<>|'):
            return {"ok": False, "erro": "Nome inválido."}
        origem = Path(caminho)
        destino = origem.with_name(novo)
        if destino.exists():
            return {"ok": False, "erro": "Já existe um item com esse nome."}
        try:
            origem.rename(destino)
            return {"ok": True, "caminho": str(destino)}
        except OSError as erro:
            return {"ok": False, "erro": str(erro)}

    def mover(self, caminhos, destino):
        destino = Path(destino)
        if not destino.is_dir():
            return {"ok": False, "erro": "Destino inválido."}
        from ferramentas.movimentos import nome_livre
        ok, erros = 0, []
        for c in caminhos:
            try:
                shutil.move(str(c), str(nome_livre(destino / Path(c).name)))
                ok += 1
            except OSError as erro:
                erros.append(f"{Path(c).name}: {erro}")
        return {"ok": True, "movidos": ok, "erros": erros}

    def excluir(self, caminhos):
        n = _lixeira(caminhos)
        return {"ok": True, "excluidos": n,
                "lixeira": WINDOWS}

    def organizar(self, pasta, aplicar=False):
        linhas = []
        plano = _org.executar(Path(pasta), _MAPA, aplicar=aplicar, saida=linhas.append,
                              idade_minima_min=0)
        return {"ok": True, "total": len(plano), "aplicado": aplicar}

    def buscar(self, pasta, termo, limite=400):
        termo = (termo or "").strip().lower()
        if not termo:
            return {"itens": []}
        achados = []
        for raiz, subpastas, arquivos in os.walk(pasta):
            for nome in list(subpastas) + arquivos:
                if termo in nome.lower():
                    p = Path(raiz) / nome
                    try:
                        st = p.stat()
                        pasta_bool = p.is_dir()
                        achados.append({
                            "nome": nome, "caminho": str(p), "pasta": pasta_bool,
                            "tamanho_fmt": "" if pasta_bool else tamanho_legivel(st.st_size),
                            "categoria": _categoria(p), "ext": p.suffix.lower().lstrip("."),
                            "modificado_fmt": time.strftime("%d/%m/%Y %H:%M", time.localtime(st.st_mtime)),
                        })
                    except OSError:
                        continue
                    if len(achados) >= limite:
                        return {"itens": achados, "parcial": True}
        return {"itens": achados}

    def escolher_pasta(self):
        r = self._janela.create_file_dialog(webview.FOLDER_DIALOG)
        return {"caminho": r[0]} if r else {"caminho": None}

    # ------------------------------------------------------- janela
    def alternar_tela_cheia(self):
        if self._janela:
            self._janela.toggle_fullscreen()

    def sair(self):
        if self._janela:
            self._janela.destroy()


def main():
    _identidade_windows()
    opcoes = [a for a in sys.argv[1:] if a.startswith("--")]
    caminhos = [a for a in sys.argv[1:] if not a.startswith("--")]
    inicio = caminhos[0] if caminhos else None
    api = Api()
    api._inicio = inicio
    janela = webview.create_window(TITULO, _recurso("ui/index.html"), js_api=api, width=1240, height=780,
                                   min_size=(900, 600), background_color="#070204",
                                   fullscreen="--janela" not in opcoes)
    api._janela = janela
    webview.start()


if __name__ == "__main__":
    main()
