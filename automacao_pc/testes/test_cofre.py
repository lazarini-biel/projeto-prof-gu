"""Testes do núcleo do cofre. Rode: python -m unittest discover testes"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cofre"))
import autotipo  # noqa: E402
import nucleo  # noqa: E402

KDF_RAPIDO = {"nome": "scrypt", "n": 2 ** 10, "r": 8, "p": 1}   # só para os testes serem rápidos
SENHA = "cavalo-bateria-grampo-correto"


class TestCofre(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.pasta.name) / "cofre.dat"
        self.cofre = nucleo.Cofre(self.arquivo, kdf=KDF_RAPIDO)
        self.cofre.criar(SENHA)

    def tearDown(self):
        self.pasta.cleanup()

    def reabrir(self, senha=SENHA):
        c = nucleo.Cofre(self.arquivo, kdf=KDF_RAPIDO)
        c.abrir(senha)
        return c

    def test_ida_e_volta(self):
        id_ = self.cofre.salvar_entrada({"titulo": "Gmail", "usuario": "eu@gmail.com",
                                         "senha": "s3nh@-çã-🔐", "url": "https://mail.google.com"})
        c = self.reabrir()
        e = c.obter(id_)
        self.assertEqual(e["senha"], "s3nh@-çã-🔐")
        self.assertEqual(e["usuario"], "eu@gmail.com")

    def test_arquivo_nao_tem_nada_legivel(self):
        self.cofre.salvar_entrada({"titulo": "Banco", "usuario": "fulano", "senha": "segredo-123"})
        bruto = self.arquivo.read_text()
        for texto in ("Banco", "fulano", "segredo-123", SENHA):
            self.assertNotIn(texto, bruto)

    def test_senha_errada(self):
        with self.assertRaises(nucleo.SenhaIncorreta):
            self.reabrir("senha-errada-mesmo")

    def test_senha_mestra_curta(self):
        with self.assertRaises(ValueError):
            nucleo.Cofre(Path(self.pasta.name) / "outro.dat", kdf=KDF_RAPIDO).criar("curta")

    def test_adulteracao_detectada(self):
        doc = json.loads(self.arquivo.read_text())
        dados = bytearray(nucleo._de_b64(doc["dados"]))
        dados[5] ^= 1
        doc["dados"] = nucleo._b64(bytes(dados))
        self.arquivo.write_text(json.dumps(doc))
        with self.assertRaises(nucleo.SenhaIncorreta):
            self.reabrir()

    def test_cabecalho_autenticado(self):
        doc = json.loads(self.arquivo.read_text())
        doc["kdf"]["p"] = 2   # alguém troca os parâmetros: a chave muda e a abertura falha
        self.arquivo.write_text(json.dumps(doc))
        with self.assertRaises(nucleo.SenhaIncorreta):
            self.reabrir()

    def test_nonce_novo_a_cada_salvamento(self):
        n1 = json.loads(self.arquivo.read_text())["nonce"]
        self.cofre.salvar()
        n2 = json.loads(self.arquivo.read_text())["nonce"]
        self.assertNotEqual(n1, n2)
        self.assertTrue(self.arquivo.with_name("cofre.dat.bak").exists())

    def test_trocar_senha(self):
        self.cofre.salvar_entrada({"titulo": "X", "senha": "1"})
        with self.assertRaises(nucleo.SenhaIncorreta):
            self.cofre.trocar_senha("errada-errada", "nova-senha-longa")
        self.cofre.trocar_senha(SENHA, "nova-senha-longa")
        with self.assertRaises(nucleo.SenhaIncorreta):
            self.reabrir()
        self.assertEqual(len(self.reabrir("nova-senha-longa").entradas()), 1)

    def test_historico_de_senhas(self):
        id_ = self.cofre.salvar_entrada({"titulo": "X", "senha": "antiga"})
        self.cofre.salvar_entrada({"id": id_, "titulo": "X", "senha": "nova"})
        self.assertEqual(self.cofre.obter(id_)["historico"][0]["senha"], "antiga")

    def test_lista_resumida_sem_senha(self):
        self.cofre.salvar_entrada({"titulo": "X", "senha": "segredo"})
        self.assertNotIn("senha", self.cofre.entradas()[0])

    def test_bloqueado_nao_le(self):
        self.cofre.fechar()
        with self.assertRaises(PermissionError):
            self.cofre.entradas()

    def test_importar_chrome_e_firefox(self):
        chrome = Path(self.pasta.name) / "chrome.csv"
        chrome.write_text("name,url,username,password,note\n"
                          "google.com,https://accounts.google.com/,eu@gmail.com,abc123,\n"
                          "gov.br,https://sso.acesso.gov.br/,12345678900,xyz,nota\n", encoding="utf-8")
        firefox = Path(self.pasta.name) / "firefox.csv"
        firefox.write_text('"url","username","password","httpRealm"\n'
                           '"https://accounts.google.com/","eu@gmail.com","abc123",""\n'
                           '"https://github.com","dev","p4ss",""\n', encoding="utf-8")
        self.assertEqual(self.cofre.importar_csv(chrome), (2, 0))
        self.assertEqual(self.cofre.importar_csv(firefox), (1, 1))
        titulos = sorted(e["titulo"] for e in self.reabrir().entradas())
        self.assertEqual(titulos, ["github.com", "google.com", "gov.br"])


class TestSenhas(unittest.TestCase):
    def test_gerador_respeita_opcoes(self):
        for _ in range(50):
            s = nucleo.gerar_senha(16, simbolos=False)
            self.assertEqual(len(s), 16)
            self.assertTrue(s.isalnum())
            self.assertTrue(any(c.isupper() for c in s) and any(c.isdigit() for c in s))
            self.assertFalse(set(s) & nucleo.AMBIGUOS)

    def test_forca(self):
        self.assertLess(nucleo.forca("123456")["nivel"], 2)
        self.assertGreaterEqual(nucleo.forca(nucleo.gerar_senha(24))["nivel"], 4)


class TestReconhecerJanela(unittest.TestCase):
    ENTRADAS = [
        {"id": "g", "titulo": "Gmail", "url": "https://accounts.google.com", "palavras": []},
        {"id": "gov", "titulo": "Gov.br", "url": "https://sso.acesso.gov.br", "palavras": ["gov.br"]},
        {"id": "nb", "titulo": "Nubank", "url": "https://app.nubank.com.br", "palavras": []},
    ]

    def test_dominio(self):
        self.assertEqual(nucleo.dominio("https://www.Exemplo.com.br/login?x=1"), "exemplo.com.br")
        self.assertEqual(nucleo.nomes_do_dominio("https://accounts.google.com.br"), ["google"])

    def test_titulos_de_navegador(self):
        casos = {
            "Fazer login nas Contas do Google - Google Chrome": "g",
            "Acesso gov.br - Mozilla Firefox": "gov",
            "Nubank — Entrar - Pessoal — Microsoft Edge": "nb",
        }
        for titulo, esperado in casos.items():
            self.assertEqual(nucleo.melhores(self.ENTRADAS, titulo)[0]["id"], esperado, titulo)

    def test_sem_correspondencia(self):
        self.assertEqual(nucleo.melhores(self.ENTRADAS, "Bloco de Notas"), [])


class TestSequencia(unittest.TestCase):
    def test_interpretar(self):
        self.assertEqual(autotipo.interpretar("{USUARIO}{TAB}{SENHA}{ENTER}"),
                         [("campo", "usuario"), ("tecla", 0x09), ("campo", "senha"), ("tecla", 0x0D)])
        self.assertEqual(autotipo.interpretar("{usuario}{ENTER}{ESPERA:1500}{SENHA}x{OUTRO}"),
                         [("campo", "usuario"), ("tecla", 0x0D), ("espera", 1500),
                          ("campo", "senha"), ("texto", "x"), ("texto", "{OUTRO}")])


if __name__ == "__main__":
    unittest.main()
