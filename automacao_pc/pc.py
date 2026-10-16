"""
SPARTA — central de automações do seu Windows.

Sem argumentos abre um menu. Com argumentos, roda direto (é assim que o
Agendador de Tarefas usa). Exemplos:

    python pc.py                          menu interativo
    python pc.py organizar --executar     organiza a pasta Downloads
    python pc.py duplicados               lista duplicados (não apaga nada)
    python pc.py duplicados --acao lixeira
    python pc.py discos                   espaço de cada disco
    python pc.py discos maiores C:/Users  maiores arquivos
    python pc.py discos redistribuir      plano de redistribuição entre discos
    python pc.py limpar --executar        limpa temporários e caches
    python pc.py iniciar trabalho         abre programas/sites do perfil
    python pc.py energia desligar --em 30
    python pc.py agendar instalar         cria as tarefas automáticas
    python pc.py remoto                   liga o controle pelo Telegram
    python pc.py desfazer                 desfaz a última organização

Sem --executar, os comandos que mexem em arquivos só mostram uma prévia.
"""

import argparse
import subprocess
import sys
import time

from ferramentas import (agendador, discos, duplicados, energia, inicio, intro, limpeza,
                         movimentos, organizar, painel_web, remoto, sistema, tema)
from ferramentas.categorias import montar_mapa
from ferramentas.util import PASTA_LOGS, caminho, carregar_config


def _log_sem_console():
    """Rodando pelo Agendador (pythonw) não há console: a saída vai para logs/."""
    if sys.stdout is None:
        PASTA_LOGS.mkdir(parents=True, exist_ok=True)
        arquivo = open(PASTA_LOGS / "sparta.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = arquivo
        print(f"\n=== {time.strftime('%d/%m/%Y %H:%M:%S')} — {' '.join(sys.argv[1:])}")


class _ns:
    """Namespace simples para reusar cmd_discos a partir de outro subcomando."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


def cmd_organizar(cfg, args):
    c = cfg.get("organizar", {})
    return organizar.executar(
        caminho(args.pasta or c.get("pasta", "~/Downloads")),
        montar_mapa(cfg.get("categorias_extras")),
        aplicar=args.executar,
        idade_minima_min=c.get("idade_minima_minutos", 10),
        separar_por_ano=c.get("separar_por_ano", False),
        mover_desconhecidos=c.get("mover_desconhecidos", True),
        saida=tema.saida,
    )


def cmd_duplicados(cfg, args):
    c = cfg.get("duplicados", {})
    pastas = args.pastas or c.get("pastas", ["~"])
    return duplicados.executar(
        [caminho(p) for p in pastas],
        acao=args.acao,
        tamanho_min=int(c.get("tamanho_minimo_kb", 100) * 1024),
        ignorar=c.get("ignorar_pastas", []),
        preferir=[caminho(p) for p in c.get("preferir_manter_em", [])],
        confirmado=args.sim,
        saida=tema.saida,
    )


def cmd_discos(cfg, args):
    if args.acao == "maiores":
        alvo = args.pastas or ["~"]
        discos.maiores([caminho(p) for p in alvo], top=args.top, saida=tema.saida)
    elif args.acao == "redistribuir":
        return discos.redistribuir(cfg.get("redistribuir", {}),
                                   montar_mapa(cfg.get("categorias_extras")),
                                   aplicar=args.executar, saida=tema.saida)
    elif args.acao == "pastas":
        c = cfg.get("espaco_pastas", {})
        alvo = args.pastas or c.get("onde", ["~"])
        discos.maiores_pastas([caminho(p) for p in alvo], top=c.get("quantidade", 80),
                              tamanho_min_mb=c.get("minimo_mb", 20), saida=tema.saida)
    else:
        discos.relatorio(saida=tema.saida)


def cmd_limpar(cfg, args):
    c = cfg.get("limpeza", {})
    return limpeza.executar(
        aplicar=args.executar,
        idade_horas=c.get("idade_minima_horas", 24),
        navegadores=c.get("navegadores", True),
        sistema=args.sistema or c.get("sistema", False),
        lixeira=args.lixeira or c.get("esvaziar_lixeira", False),
        saida=tema.saida,
    )


def cmd_iniciar(cfg, args):
    inicio.executar(cfg.get("inicio", {}), args.perfil, sem_atraso=args.agora, saida=tema.saida)


def cmd_energia(cfg, args):
    acoes = {
        "desligar": lambda: energia.desligar(args.em),
        "reiniciar": lambda: energia.reiniciar(args.em),
        "hibernar": energia.hibernar,
        "bloquear": energia.bloquear,
        "cancelar": energia.cancelar,
    }
    tema.saida(acoes[args.acao]()[1])


def cmd_agendar(cfg, args):
    itens = cfg.get("agendamentos", [])
    if args.acao == "instalar":
        agendador.instalar(itens, usuario=args.usuario, pausar=args.pausar, saida=tema.saida)
    elif args.acao == "remover":
        agendador.remover(itens, saida=tema.saida)
    else:
        agendador.listar(saida=tema.saida)


def cmd_remoto(cfg, args):
    c = cfg.get("remoto", {})
    if not c.get("token"):
        print("Falta o token do bot em config.json > remoto > token (veja o README).")
        return
    remoto.Bot(c["token"], c.get("ids_autorizados", []),
               cfg_limpeza=cfg.get("limpeza", {})).rodar()


def cmd_desfazer(cfg, args):
    registros = movimentos.registros_disponiveis()
    if not registros:
        tema.saida("Nada para desfazer.")
        return
    alvo = registros[0]
    tema.saida(f"Desfazendo {alvo.name}...")
    movimentos.desfazer(alvo, saida=tema.saida)


def cmd_sistema(cfg, args):
    sistema.relatorio()


def cmd_top(cfg, args):
    sistema.top()


def cmd_painel(cfg, args):
    painel_web.iniciar(porta=cfg.get("painel_web", {}).get("porta", 0))


def montar_parser():
    p = argparse.ArgumentParser(prog="pc.py", description="Central de automações do PC.")
    sub = p.add_subparsers(dest="comando")

    s = sub.add_parser("organizar", help="separa a pasta Downloads por tipo")
    s.add_argument("pasta", nargs="?", help="outra pasta (padrão: a do config)")
    s.add_argument("--executar", action="store_true", help="aplica (sem isso é só prévia)")
    s.set_defaults(func=cmd_organizar)

    s = sub.add_parser("duplicados", help="encontra arquivos repetidos")
    s.add_argument("pastas", nargs="*", help="pastas a varrer (padrão: as do config)")
    s.add_argument("--acao", choices=["relatorio", "lixeira", "excluir"], default="relatorio")
    s.add_argument("--sim", action="store_true", help="não pede confirmação ao excluir")
    s.set_defaults(func=cmd_duplicados)

    s = sub.add_parser("discos", help="espaço, maiores arquivos e redistribuição")
    s.add_argument("acao", nargs="?", choices=["relatorio", "maiores", "redistribuir", "pastas"],
                   default="relatorio")
    s.add_argument("pastas", nargs="*")
    s.add_argument("--top", type=int, default=30)
    s.add_argument("--executar", action="store_true")
    s.set_defaults(func=cmd_discos)

    s = sub.add_parser("limpar", help="temporários, caches e lixeira")
    s.add_argument("--executar", action="store_true")
    s.add_argument("--sistema", action="store_true", help="inclui pastas do Windows (admin)")
    s.add_argument("--lixeira", action="store_true", help="também esvazia a Lixeira")
    s.set_defaults(func=cmd_limpar)

    s = sub.add_parser("iniciar", help="abre programas e sites de um perfil")
    s.add_argument("perfil", nargs="?", default="padrao")
    s.add_argument("--agora", action="store_true", help="ignora o atraso inicial")
    s.set_defaults(func=cmd_iniciar)

    s = sub.add_parser("energia", help="desligar, reiniciar, hibernar, bloquear")
    s.add_argument("acao", choices=["desligar", "reiniciar", "hibernar", "bloquear", "cancelar"])
    s.add_argument("--em", type=float, default=1, help="minutos até desligar/reiniciar")
    s.set_defaults(func=cmd_energia)

    s = sub.add_parser("agendar", help="tarefas automáticas do Windows")
    s.add_argument("acao", nargs="?", choices=["instalar", "listar", "remover"], default="listar")
    s.add_argument("--usuario", help=argparse.SUPPRESS)
    s.add_argument("--pausar", action="store_true", help=argparse.SUPPRESS)
    s.set_defaults(func=cmd_agendar)

    s = sub.add_parser("remoto", help="controle pelo Telegram")
    s.set_defaults(func=cmd_remoto)

    s = sub.add_parser("desfazer", help="desfaz a última movimentação de arquivos")
    s.set_defaults(func=cmd_desfazer)

    s = sub.add_parser("sistema", help="mostra informações do PC (CPU, memória, discos...)")
    s.set_defaults(func=cmd_sistema)

    s = sub.add_parser("top", help="processos que mais usam CPU/memória agora")
    s.set_defaults(func=cmd_top)

    s = sub.add_parser("pastas", help="as pastas que mais ocupam espaço")
    s.add_argument("pastas", nargs="*")
    s.set_defaults(func=lambda cfg, a: cmd_discos(cfg, _ns(acao="pastas", pastas=a.pastas)))

    s = sub.add_parser("painel", help="abre o painel do PC no navegador")
    s.set_defaults(func=cmd_painel)
    return p


def _como_aplicar(argv):
    """Depois de uma prévia: (argumentos que aplicam, pergunta) ou None."""
    if "--executar" in argv or "--acao" in argv:
        return None
    if argv[0] in ("organizar", "limpar") or argv[:2] == ["discos", "redistribuir"]:
        return argv + ["--executar"], "Aplicar agora?"
    if argv[0] == "duplicados":
        return argv + ["--acao", "lixeira"], "Mandar as cópias para a Lixeira?"
    return None


_TITULOS_CMD = {
    "organizar": "Organizar Downloads", "duplicados": "Arquivos duplicados",
    "discos": "Discos", "limpar": "Limpeza", "iniciar": "Abrir programas e sites",
    "energia": "Energia", "agendar": "Tarefas automáticas", "desfazer": "Desfazer",
    "remoto": "Controle remoto", "sistema": "Informações do PC",
    "top": "Top processos", "painel": "Painel no navegador", "pastas": "Espaço por pasta",
}


def rodar(cfg, parser, argv, perguntar, topo=True):
    """Roda um comando. Se foi só uma prévia com algo a fazer, pergunta se aplica
    (ou, sem ninguém no teclado, mostra o comando completo para aplicar)."""
    if topo and argv and argv[0] not in ("sistema", "top"):   # têm cabeçalho próprio
        tema.cabecalho(_TITULOS_CMD.get(argv[0], argv[0]))
        print()
    args = parser.parse_args(argv)
    resultado = args.func(cfg, args)
    proximo = _como_aplicar(argv) if resultado else None
    if not proximo:
        return
    argv_aplicar, pergunta = proximo
    if perguntar:
        if input(f"\n{pergunta} (s/n) ").strip().lower() in ("s", "sim"):
            print()
            rodar(cfg, parser, argv_aplicar, perguntar=False, topo=False)
    else:
        print(f"\nPara aplicar: py pc.py {subprocess.list2cmdline(argv_aplicar)}")


def _tem_teclado():
    return all(f is not None and f.isatty() for f in (sys.stdin, sys.stdout))


MENU = [
    ("Ver informações do PC", ["sistema"]),
    ("Top processos (quem usa CPU/RAM)", ["top"]),
    ("Painel do PC no navegador", ["painel"]),
    ("Organizar a pasta Downloads", ["organizar"]),
    ("Procurar arquivos duplicados", ["duplicados"]),
    ("Ver espaço dos discos", ["discos"]),
    ("Ver os maiores arquivos", ["discos", "maiores"]),
    ("Espaço por pasta (o que enche o disco)", ["discos", "pastas"]),
    ("Redistribuir arquivos entre os discos", ["discos", "redistribuir"]),
    ("Limpar temporários e caches", ["limpar"]),
    ("Abrir meus programas e sites", ["iniciar", "padrao", "--agora"]),
    ("Desligar o PC em X minutos", None),
    ("Instalar/atualizar tarefas automáticas", ["agendar", "instalar"]),
    ("Ver tarefas automáticas", ["agendar", "listar"]),
    ("Desfazer a última movimentação", ["desfazer"]),
]
def menu(cfg, parser):
    if cfg.get("abertura", True):
        intro.executar(cfg.get("agendamentos", []), cfg=cfg)
    rotulos = [rotulo for rotulo, _ in MENU]
    selecao = 0
    while True:
        selecao = intro.menu_animado(rotulos, selecao)
        if selecao is None:
            return
        rotulo, argv = MENU[selecao]
        if argv is None:
            minutos = input("Em quantos minutos? ").strip() or "1"
            argv = ["energia", "desligar", "--em", minutos.replace(",", ".")]
        print()
        rodar(cfg, parser, argv, perguntar=True)
        input("\nEnter para voltar ao menu...")


def main(argv=None):
    _log_sem_console()
    tema.ativar()
    argv = sys.argv[1:] if argv is None else argv
    parser = montar_parser()
    args = parser.parse_args(argv)
    cfg = carregar_config()
    if not args.comando:
        menu(cfg, parser)
    else:
        rodar(cfg, parser, argv, perguntar=_tem_teclado())


if __name__ == "__main__":
    main()
