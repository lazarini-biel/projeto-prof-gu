"""Testes das ferramentas da central. Rode: python -m unittest discover testes"""

import os
import sys
import tempfile
import time
import unittest
from collections import namedtuple
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ferramentas import (agendador, discos, duplicados, limpeza, movimentos,  # noqa: E402
                         organizar, remoto)
from ferramentas.categorias import montar_mapa  # noqa: E402

VELHO = time.time() - 30 * 86400


def criar(caminho, conteudo=b"x", idade=VELHO):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)
    os.utime(caminho, (idade, idade))
    return caminho


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.logs = self.raiz / "_logs"
        p = mock.patch.object(movimentos, "PASTA_LOGS", self.logs)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self._tmp.cleanup)
        # Movimentos usa PASTA_LOGS como padrão no __init__, então trocamos o default.
        original = movimentos.Movimentos.__init__
        logs = self.logs

        def init(obj, operacao, pasta_logs=None):
            original(obj, operacao, pasta_logs or logs)
        p2 = mock.patch.object(movimentos.Movimentos, "__init__", init)
        p2.start()
        self.addCleanup(p2.stop)


class TestOrganizar(Base):
    def test_separa_por_tipo_e_desfaz(self):
        dl = self.raiz / "Downloads"
        criar(dl / "nota.pdf")
        criar(dl / "foto.JPG")
        criar(dl / "setup.exe")
        criar(dl / "planilha.xlsx")
        criar(dl / "estranho.xyz")
        criar(dl / "baixando.zip.crdownload")
        criar(dl / "video.mp4", b"")
        criar(dl / "video.mp4.part")             # Firefox ainda baixando
        criar(dl / "recente.pdf", idade=time.time())
        (dl / "MinhaPasta").mkdir()

        organizar.executar(dl, montar_mapa(), aplicar=True, saida=lambda *_: None)
        self.assertTrue((dl / "PDFs/nota.pdf").exists())
        self.assertTrue((dl / "Imagens/foto.JPG").exists())
        self.assertTrue((dl / "Instaladores/setup.exe").exists())
        self.assertTrue((dl / "Planilhas/planilha.xlsx").exists())
        self.assertTrue((dl / "Outros/estranho.xyz").exists())
        for fica in ("baixando.zip.crdownload", "video.mp4", "video.mp4.part", "recente.pdf"):
            self.assertTrue((dl / fica).exists(), fica)

        movimentos.desfazer(movimentos.registros_disponiveis(self.logs)[0], saida=lambda *_: None)
        self.assertTrue((dl / "nota.pdf").exists())
        self.assertFalse((dl / "PDFs").exists())

    def test_nome_repetido_nao_sobrescreve(self):
        dl = self.raiz / "Downloads"
        criar(dl / "PDFs/nota.pdf", b"antigo")
        criar(dl / "nota.pdf", b"novo")
        organizar.executar(dl, montar_mapa(), aplicar=True, saida=lambda *_: None)
        self.assertEqual((dl / "PDFs/nota.pdf").read_bytes(), b"antigo")
        self.assertEqual((dl / "PDFs/nota (2).pdf").read_bytes(), b"novo")


class TestDuplicados(Base):
    def test_encontra_e_escolhe_original(self):
        grande = os.urandom(300 * 1024)
        a = criar(self.raiz / "Fotos/ferias.jpg", grande, idade=VELHO - 100)
        b = criar(self.raiz / "Downloads/ferias (1).jpg", grande)
        c = criar(self.raiz / "Desktop/copia.jpg", grande)
        criar(self.raiz / "Downloads/quase.jpg", grande[:-1] + b"!")      # mesmo tamanho, outro conteúdo
        criar(self.raiz / "x/pequeno1.txt", b"oi")
        criar(self.raiz / "y/pequeno2.txt", b"oi")
        criar(self.raiz / "AppData/ignorado.jpg", grande)

        grupos, _ = duplicados.encontrar([self.raiz], tamanho_min=1)
        self.assertEqual(len(grupos), 2)
        maior = grupos[0]
        self.assertEqual({p for p, _ in maior.arquivos}, {a, b, c})
        original, extras = duplicados.escolher_original(maior)
        self.assertEqual(original, a)                               # o mais antigo
        original, _ = duplicados.escolher_original(maior, preferir=[self.raiz / "Desktop"])
        self.assertEqual(original, c)                               # pasta preferida ganha

    def test_excluir(self):
        conteudo = os.urandom(5000)
        criar(self.raiz / "a/1.bin", conteudo, idade=VELHO - 10)
        criar(self.raiz / "b/2.bin", conteudo)
        with mock.patch.object(duplicados, "PASTA_LOGS", self.logs):
            duplicados.executar([self.raiz], acao="excluir", confirmado=True, saida=lambda *_: None)
        self.assertTrue((self.raiz / "a/1.bin").exists())
        self.assertFalse((self.raiz / "b/2.bin").exists())


Uso = namedtuple("Uso", "total used free")


class TestRedistribuir(Base):
    def test_plano(self):
        origem = self.raiz / "Usuario/Downloads"
        criar(origem / "Imagens/praia.jpg", b"1" * 100)
        criar(origem / "filme.mkv", b"2" * 100)
        criar(origem / "doc.pdf", b"3")
        criar(origem / "atalho.lnk")
        criar(origem / "novo.jpg", idade=time.time())
        destinos = {"Imagens": self.raiz / "D/Fotos", "Vídeos": self.raiz / "E/Videos"}
        plano, pulados = discos.planejar_redistribuicao(
            [origem], destinos, montar_mapa(), idade_minima_dias=7,
            uso_disco=lambda _: Uso(10_000, 0, 10_000))
        mapa = {o.name: d for o, d, _, _ in plano}
        self.assertEqual(mapa["praia.jpg"], self.raiz / "D/Fotos/praia.jpg")
        self.assertEqual(mapa["filme.mkv"], self.raiz / "E/Videos/filme.mkv")
        self.assertNotIn("doc.pdf", mapa)                   # PDF não tem destino: fica
        self.assertEqual(pulados, {"alterado recentemente": 1})

    def test_nao_enche_o_disco(self):
        origem = self.raiz / "Origem"
        for i in range(5):
            criar(origem / f"v{i}.mp4", b"x" * 300)
        destino = self.raiz / "X/Videos"
        outro_disco = lambda p: "X:\\" if str(p).startswith(str(self.raiz / "X")) else "C:\\"
        with mock.patch.object(discos, "_disco", outro_disco):
            plano, pulados = discos.planejar_redistribuicao(
                [origem], {"Vídeos": destino}, montar_mapa(), margem_livre_pct=10,
                uso_disco=lambda _: Uso(10_000, 0, 2_000))
        # livre útil = 2000 - 10% de 10000 = 1000 -> cabem 3 de 300
        self.assertEqual(len(plano), 3)
        self.assertEqual(sum(pulados.values()), 2)


class TestLimpeza(Base):
    def test_apaga_so_os_velhos(self):
        temp = self.raiz / "Temp"
        criar(temp / "velho.tmp", b"x" * 1000)
        criar(temp / "sub/velho2.tmp", b"x" * 500)
        criar(temp / "novo.tmp", idade=time.time())
        alvos = [("Temporários", str(temp), None, False),
                 ("Cache Chrome", str(self.raiz / "chrome"), "chrome.exe", False)]
        criar(self.raiz / "chrome/cache.bin", b"x" * 99)
        with mock.patch.object(limpeza, "processos_ativos", return_value={"chrome.exe"}):
            liberado = limpeza.executar(aplicar=True, lista_alvos=alvos, saida=lambda *_: None)
        self.assertEqual(liberado, 1500)
        self.assertFalse((temp / "velho.tmp").exists())
        self.assertFalse((temp / "sub").exists())
        self.assertTrue((temp / "novo.tmp").exists())
        self.assertTrue((self.raiz / "chrome/cache.bin").exists())   # Chrome aberto: não mexe


class TestAgendador(unittest.TestCase):
    def test_xml(self):
        xml = agendador.gerar_xml({"nome": "Limpeza", "comando": "limpar --executar", "quando": "semanal",
                                   "dias": ["dom", "qua"], "hora": "12:00"},
                                  "PC\\fulano", pythonw="C:/Python/pythonw.exe", script="C:/a/pc.py")
        self.assertIn("<Sunday />", xml)
        self.assertIn("<Wednesday />", xml)
        self.assertIn("<StartWhenAvailable>true</StartWhenAvailable>", xml)
        self.assertIn("<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>", xml)
        self.assertIn('<Arguments>"C:/a/pc.py" limpar --executar</Arguments>', xml)

    def test_desligar_nao_recupera_execucao_perdida(self):
        xml = agendador.gerar_xml({"nome": "D", "comando": "energia desligar", "quando": "diario"}, "u",
                                  pythonw="p", script="s")
        self.assertIn("<StartWhenAvailable>false</StartWhenAvailable>", xml)

    def test_logon_e_horas(self):
        xml = agendador.gerar_xml({"nome": "I", "comando": "iniciar", "quando": "logon"}, "PC\\eu",
                                  pythonw="p", script="s")
        self.assertIn("<LogonTrigger>", xml)
        self.assertIn("<UserId>PC\\eu</UserId>", xml)
        xml = agendador.gerar_xml({"nome": "O", "comando": "organizar", "quando": "a_cada_horas", "horas": 2},
                                  "u", pythonw="p", script="s")
        self.assertIn("<Interval>PT2H</Interval>", xml)
        with self.assertRaises(ValueError):
            agendador.gerar_xml({"nome": "Z", "comando": "x", "quando": "semanal", "dias": ["xyz"]}, "u",
                                pythonw="p", script="s")


class TestRemoto(unittest.TestCase):
    def setUp(self):
        self.enviadas = []

        def http(metodo, params, timeout):
            if metodo == "sendMessage":
                self.enviadas.append((params["chat_id"], params["text"]))
            return {"ok": True, "result": []}
        self.http = http

    def msg(self, remetente, texto):
        return {"update_id": 1, "message": {"chat": {"id": remetente}, "from": {"id": remetente}, "text": texto}}

    def test_ignora_desconhecidos(self):
        bot = remoto.Bot("t", [111], http=self.http, log=lambda *_: None)
        with mock.patch.object(remoto.energia, "desligar") as desligar:
            bot.tratar(self.msg(999, "/desligar"))
            desligar.assert_not_called()
        self.assertEqual(self.enviadas, [])

    def test_autorizado_desliga(self):
        bot = remoto.Bot("t", [111], http=self.http, log=lambda *_: None)
        with mock.patch.object(remoto.energia, "desligar", return_value=(True, "Desligando em 5.0 min.")) as d:
            bot.tratar(self.msg(111, "/desligar@MeuBot 5"))
            d.assert_called_once_with(5.0)
        self.assertIn("Desligando", self.enviadas[0][1])

    def test_sem_ids_informa_o_id(self):
        bot = remoto.Bot("t", [], http=self.http, log=lambda *_: None)
        bot.tratar(self.msg(4242, "/start"))
        self.assertIn("4242", self.enviadas[0][1])

    def test_descarta_mensagens_antigas(self):
        chamadas = []

        def http(metodo, params, timeout):
            chamadas.append((metodo, params))
            return {"ok": True, "result": [{"update_id": 77}]}
        bot = remoto.Bot("t", [1], http=http, log=lambda *_: None)
        bot.descartar_pendentes()
        self.assertEqual(bot.offset, 78)
        self.assertEqual(chamadas[0][1]["offset"], -1)


if __name__ == "__main__":
    unittest.main()
