"""
Núcleo do cofre: criptografia, arquivo do cofre e busca de logins.

Criptografia (nada inventado aqui — só algoritmos padrão e bibliotecas testadas):
  - a senha mestra vira uma chave de 256 bits com scrypt (N=2^17, r=8, p=1).
    O scrypt é lento e gasta ~128 MB de RAM de propósito: cada tentativa de
    adivinhar a senha custa caro, o que inviabiliza força bruta;
  - os dados são cifrados com AES-256-GCM, que também detecta qualquer
    alteração no arquivo (senha errada e arquivo adulterado dão o mesmo erro);
  - a cada salvamento é usado um nonce novo e aleatório;
  - o cabeçalho (versão e parâmetros) entra como "dado autenticado".

O arquivo é JSON:
  {"formato": "cofre-pc", "versao": 1, "kdf": {...}, "nonce": b64, "dados": b64}
A senha mestra nunca é gravada. Esqueceu = perdeu (não existe porta dos fundos).
"""

import base64
import csv
import hmac
import hashlib
import json
import math
import os
import secrets
import shutil
import string
import time
import unicodedata
import uuid
from pathlib import Path
from urllib.parse import urlparse

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMATO = "cofre-pc"
VERSAO = 1
KDF_PADRAO = {"nome": "scrypt", "n": 2 ** 17, "r": 8, "p": 1}
TAMANHO_MINIMO_SENHA = 10
SEQUENCIA_PADRAO = "{USUARIO}{TAB}{SENHA}{ENTER}"
PREFERENCIAS_PADRAO = {"bloqueio_minutos": 5, "limpar_copia_segundos": 20}


class SenhaIncorreta(Exception):
    pass


class CofreInvalido(Exception):
    pass


def _b64(dados):
    return base64.b64encode(dados).decode("ascii")


def _de_b64(texto):
    return base64.b64decode(texto.encode("ascii"))


def derivar_chave(senha, sal, kdf):
    if kdf.get("nome") != "scrypt":
        raise CofreInvalido(f"KDF desconhecido: {kdf.get('nome')}")
    n, r, p = int(kdf["n"]), int(kdf["r"]), int(kdf["p"])
    senha = unicodedata.normalize("NFC", senha).encode("utf-8")
    return hashlib.scrypt(senha, salt=sal, n=n, r=r, p=p, dklen=32,
                          maxmem=128 * r * n * p + 32 * 1024 * 1024)


def _aad(cabecalho):
    return json.dumps({k: cabecalho[k] for k in ("formato", "versao", "kdf")},
                      sort_keys=True, separators=(",", ":")).encode()


class Cofre:
    def __init__(self, caminho, kdf=None):
        self.caminho = Path(caminho)
        self._kdf_novo = dict(kdf or KDF_PADRAO)
        self._chave = None
        self._kdf = None
        self.dados = None

    # -------------------------------------------------------------- estado
    @property
    def existe(self):
        return self.caminho.exists()

    @property
    def aberto(self):
        return self._chave is not None

    def _exigir_aberto(self):
        if not self.aberto:
            raise PermissionError("O cofre está bloqueado.")

    # ----------------------------------------------------- abrir e salvar
    def criar(self, senha):
        if self.existe:
            raise FileExistsError(f"Já existe um cofre em {self.caminho}")
        if len(senha) < TAMANHO_MINIMO_SENHA:
            raise ValueError(f"A senha mestra precisa de pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")
        self._kdf = {**self._kdf_novo, "sal": _b64(secrets.token_bytes(16))}
        self._chave = derivar_chave(senha, _de_b64(self._kdf["sal"]), self._kdf)
        self.dados = {"entradas": [], "preferencias": dict(PREFERENCIAS_PADRAO)}
        self.salvar()

    def abrir(self, senha):
        try:
            with open(self.caminho, encoding="utf-8") as f:
                doc = json.load(f)
            if doc.get("formato") != FORMATO:
                raise CofreInvalido("Este arquivo não é um cofre.")
            if doc.get("versao") != VERSAO:
                raise CofreInvalido(f"Versão {doc.get('versao')} não suportada.")
            kdf = doc["kdf"]
            nonce, cifrado = _de_b64(doc["nonce"]), _de_b64(doc["dados"])
        except (KeyError, ValueError, TypeError) as erro:
            raise CofreInvalido(f"Arquivo do cofre danificado ({erro}).")

        chave = derivar_chave(senha, _de_b64(kdf["sal"]), kdf)
        try:
            claro = AESGCM(chave).decrypt(nonce, cifrado, _aad(doc))
        except InvalidTag:
            raise SenhaIncorreta()
        self._chave, self._kdf = chave, kdf
        self.dados = json.loads(claro)
        self.dados.setdefault("entradas", [])
        self.dados["preferencias"] = {**PREFERENCIAS_PADRAO, **self.dados.get("preferencias", {})}

    def salvar(self):
        self._exigir_aberto()
        cabecalho = {"formato": FORMATO, "versao": VERSAO, "kdf": self._kdf}
        nonce = secrets.token_bytes(12)
        claro = json.dumps(self.dados, ensure_ascii=False).encode("utf-8")
        cifrado = AESGCM(self._chave).encrypt(nonce, claro, _aad(cabecalho))
        doc = {**cabecalho, "nonce": _b64(nonce), "dados": _b64(cifrado)}

        # Grava num temporário e só então troca: queda de energia ou pendrive
        # arrancado no meio nunca deixa o cofre pela metade. A versão anterior
        # fica em .bak.
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_name(self.caminho.name + ".tmp")
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump(doc, f)
            f.flush()
            os.fsync(f.fileno())
        if self.existe:
            shutil.copy2(self.caminho, self.caminho.with_name(self.caminho.name + ".bak"))
        os.replace(temporario, self.caminho)

    def fechar(self):
        self._chave = None
        self._kdf = None
        self.dados = None

    def trocar_senha(self, atual, nova):
        self._exigir_aberto()
        if not hmac.compare_digest(derivar_chave(atual, _de_b64(self._kdf["sal"]), self._kdf),
                                   self._chave):
            raise SenhaIncorreta()
        if len(nova) < TAMANHO_MINIMO_SENHA:
            raise ValueError(f"A senha mestra precisa de pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")
        self._kdf = {**self._kdf_novo, "sal": _b64(secrets.token_bytes(16))}
        self._chave = derivar_chave(nova, _de_b64(self._kdf["sal"]), self._kdf)
        self.salvar()

    # ------------------------------------------------------------ entradas
    @property
    def preferencias(self):
        self._exigir_aberto()
        return self.dados["preferencias"]

    def entradas(self):
        """Lista resumida (sem senhas) para a tela."""
        self._exigir_aberto()
        campos = ("id", "titulo", "usuario", "url", "categoria", "favorito", "navegador", "alterado")
        return [{c: e.get(c) for c in campos} | {"dominio": dominio(e.get("url", ""))}
                for e in self.dados["entradas"]]

    def obter(self, id_):
        self._exigir_aberto()
        for e in self.dados["entradas"]:
            if e["id"] == id_:
                return e
        raise KeyError(id_)

    def salvar_entrada(self, entrada):
        self._exigir_aberto()
        agora = int(time.time())
        limpa = {
            "titulo": str(entrada.get("titulo", "")).strip() or dominio(entrada.get("url", "")) or "Sem título",
            "usuario": str(entrada.get("usuario", "")),
            "senha": str(entrada.get("senha", "")),
            "url": str(entrada.get("url", "")).strip(),
            "navegador": entrada.get("navegador") or "",
            "categoria": str(entrada.get("categoria", "")).strip() or "Geral",
            "palavras": [p.strip() for p in entrada.get("palavras", []) if p.strip()],
            "sequencia": str(entrada.get("sequencia", "")).strip() or SEQUENCIA_PADRAO,
            "notas": str(entrada.get("notas", "")),
            "favorito": bool(entrada.get("favorito")),
            "alterado": agora,
        }
        if entrada.get("id"):
            atual = self.obter(entrada["id"])
            if atual.get("senha") != limpa["senha"] and atual.get("senha"):
                historico = atual.get("historico", [])
                historico.insert(0, {"senha": atual["senha"], "ate": agora})
                limpa["historico"] = historico[:5]
            atual.update(limpa)
        else:
            atual = {"id": uuid.uuid4().hex, "criado": agora, **limpa}
            self.dados["entradas"].append(atual)
        self.salvar()
        return atual["id"]

    def excluir(self, id_):
        self._exigir_aberto()
        self.dados["entradas"] = [e for e in self.dados["entradas"] if e["id"] != id_]
        self.salvar()

    def importar_csv(self, arquivo):
        """Importa a exportação de senhas do Chrome, Edge, Firefox, Brave, Opera ou Bitwarden."""
        self._exigir_aberto()
        existentes = {(e["url"], e["usuario"], e["senha"]) for e in self.dados["entradas"]}
        novos = repetidos = 0
        with open(arquivo, encoding="utf-8-sig", newline="") as f:
            for linha in csv.DictReader(f):
                linha = {(k or "").strip().lower(): (v or "") for k, v in linha.items()}
                url = linha.get("url") or linha.get("login_uri") or ""
                usuario = linha.get("username") or linha.get("login_username") or ""
                senha = linha.get("password") or linha.get("login_password") or ""
                if not senha:
                    continue
                if (url, usuario, senha) in existentes:
                    repetidos += 1
                    continue
                existentes.add((url, usuario, senha))
                titulo = linha.get("name") or dominio(url) or url
                agora = int(time.time())
                self.dados["entradas"].append({
                    "id": uuid.uuid4().hex, "titulo": titulo, "usuario": usuario,
                    "senha": senha, "url": url, "navegador": "", "categoria": "Importados",
                    "palavras": [], "sequencia": SEQUENCIA_PADRAO,
                    "notas": linha.get("note") or linha.get("notes") or "",
                    "favorito": False, "criado": agora, "alterado": agora,
                })
                novos += 1
        if novos:
            self.salvar()
        return novos, repetidos


# ------------------------------------------------------------- senhas
AMBIGUOS = set("Il1O0o`'\"")
SIMBOLOS = "!@#$%&*-_=+?.:;"


def gerar_senha(tamanho=20, maiusculas=True, minusculas=True, numeros=True,
                simbolos=True, evitar_ambiguos=True):
    grupos = [g for g, usar in ((string.ascii_uppercase, maiusculas),
                                (string.ascii_lowercase, minusculas),
                                (string.digits, numeros), (SIMBOLOS, simbolos)) if usar]
    if not grupos:
        grupos = [string.ascii_letters + string.digits]
    if evitar_ambiguos:
        grupos = ["".join(c for c in g if c not in AMBIGUOS) for g in grupos]
    tamanho = max(int(tamanho), len(grupos), 4)
    todos = "".join(grupos)
    sorteio = secrets.SystemRandom()
    while True:
        senha = [secrets.choice(todos) for _ in range(tamanho)]
        if all(any(c in g for c in senha) for g in grupos):   # pelo menos 1 de cada tipo
            sorteio.shuffle(senha)
            return "".join(senha)


def forca(senha):
    """Estimativa simples em bits e um rótulo (0 = péssima ... 4 = excelente)."""
    if not senha:
        return {"bits": 0, "nivel": 0, "rotulo": "vazia"}
    alfabeto = 0
    alfabeto += 26 if any(c.islower() for c in senha) else 0
    alfabeto += 26 if any(c.isupper() for c in senha) else 0
    alfabeto += 10 if any(c.isdigit() for c in senha) else 0
    alfabeto += 33 if any(not c.isalnum() for c in senha) else 0
    unicos = len(set(senha))
    bits = round(min(len(senha), unicos * 1.5) * math.log2(max(alfabeto, 2)))
    nivel = 0 if bits < 36 else 1 if bits < 50 else 2 if bits < 65 else 3 if bits < 85 else 4
    rotulo = ["muito fraca", "fraca", "razoável", "forte", "excelente"][nivel]
    return {"bits": bits, "nivel": nivel, "rotulo": rotulo}


# ----------------------------------------------------- casar com janelas
_SUFIXOS = {"com", "br", "org", "net", "gov", "edu", "io", "co", "app", "dev", "me",
            "info", "biz", "tv", "uk", "us", "pt", "www", "m", "login", "accounts",
            "account", "auth", "conta", "contas", "secure", "id", "sso"}


def dominio(url):
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "").lower()
    return "".join(c for c in texto if not unicodedata.combining(c))


def nomes_do_dominio(url):
    """"accounts.google.com.br" -> ["google"]. São as palavras que costumam aparecer no título."""
    return [p for p in dominio(url).split(".") if p and p not in _SUFIXOS and len(p) > 2]


def pontuar(entrada, titulo_janela):
    titulo = _normalizar(titulo_janela)
    if not titulo:
        return 0
    pontos = 0
    for palavra in entrada.get("palavras", []):
        if _normalizar(palavra) and _normalizar(palavra) in titulo:
            pontos += 5
    dom = dominio(entrada.get("url", ""))
    if dom and dom in titulo:
        pontos += 4
    for nome in nomes_do_dominio(entrada.get("url", "")):
        if nome in titulo:
            pontos += 3
    nome_entrada = _normalizar(entrada.get("titulo", ""))
    if len(nome_entrada) > 2 and nome_entrada in titulo:
        pontos += 3
    return pontos


def melhores(entradas, titulo_janela):
    """Entradas que combinam com o título da janela, da melhor para a pior."""
    pontuadas = [(pontuar(e, titulo_janela), e) for e in entradas]
    return [e for p, e in sorted(pontuadas, key=lambda x: -x[0]) if p > 0]
