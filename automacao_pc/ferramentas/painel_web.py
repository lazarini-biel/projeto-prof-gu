"""
Painel web local: abre no navegador um dashboard do PC (mais bonito que o
terminal), em tempo real e no tema vermelho da SPARTA.

Sobe um servidor só em 127.0.0.1 (ninguém da rede acessa), serve a página e
um /dados em JSON que a página consulta a cada 2s. Para parar: Ctrl+C no
terminal, ou feche a aba e o terminal.
"""

import json
import socket
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import sistema
from .util import cpu_percent, memoria, processos_detalhados, tamanho_legivel, tempo_ligado
from .discos import unidades

_ESTATICO = None


def _estatico():
    global _ESTATICO
    if _ESTATICO is None:
        info = sistema.coletar()
        _ESTATICO = {
            "usuario": info["usuario"], "maquina": info["maquina"], "so": info["so"],
            "cpu": info["cpu"], "nucleos": info["nucleos"], "gpu": info["gpu"],
            "placa_mae": info["placa_mae"], "ip": info["ip"],
        }
    return _ESTATICO


def _dinamico():
    total, usada = memoria()
    try:
        ligado = tempo_ligado()
    except OSError:
        ligado = "—"
    procs = processos_detalhados(12)
    processos = [{"pid": p, "nome": n,
                  "mem": tamanho_legivel(m),
                  "mem_pct": round(m / total * 100, 1) if total else 0} for p, n, m in procs]
    discos = [{"raiz": r.rstrip("\\"), "nome": n, "uso": round((1 - l / t) * 100) if t else 0,
               "livre": tamanho_legivel(l), "total": tamanho_legivel(t)}
              for r, n, _, t, l in unidades() if t]
    return {
        "cpu": round(cpu_percent(0.12), 1),
        "mem_pct": round(usada / total * 100, 1) if total else 0,
        "mem_usada": tamanho_legivel(usada), "mem_total": tamanho_legivel(total),
        "ligado": ligado, "processos": processos, "discos": discos,
        "bateria": _bateria(), "hora": time.strftime("%H:%M:%S"),
    }


def _bateria():
    b = sistema.bateria()
    if not b:
        return None
    return {"pct": b[0], "carregando": b[1]}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass                                   # silencioso

    def _responder(self, corpo, tipo):
        dados = corpo.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path.startswith("/dados"):
            try:
                corpo = json.dumps({**_estatico(), **_dinamico()}, ensure_ascii=False)
            except Exception as erro:
                corpo = json.dumps({"erro": str(erro)})
            self._responder(corpo, "application/json; charset=utf-8")
        else:
            self._responder(_PAGINA, "text/html; charset=utf-8")


def iniciar(porta=0, abrir=True, saida=print):
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", porta), _Handler)
    except OSError as erro:
        saida(f"Não consegui abrir o servidor: {erro}")
        return
    porta = servidor.server_address[1]
    url = f"http://127.0.0.1:{porta}/"
    saida(f"Painel no ar: {url}")
    saida("Abra no navegador (deve abrir sozinho). Para parar: Ctrl+C aqui.")
    threading.Thread(target=_estatico, daemon=True).start()   # pré-carrega specs
    if abrir:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        saida("\nPainel encerrado.")
    finally:
        servidor.shutdown()


def porta_livre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


_PAGINA = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>SPARTA // Painel</title>
<style>
:root{--neon:#ff3355;--neon2:#ff6a85;--forte:#cd2242;--escuro:#4a1019;--fundo:#070204;--painel:#14060a;--texto:#f2d9de;--apagado:#946f77}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top,#1c0508,var(--fundo) 70%);color:var(--texto);
font:14px/1.5 "Segoe UI",system-ui,sans-serif;min-height:100vh}
.topo{display:flex;align-items:center;gap:16px;padding:16px 22px;border-bottom:1px solid rgba(255,51,85,.25)}
.logo{font:800 22px "Cascadia Mono",Consolas,monospace;letter-spacing:.3em;color:var(--neon);text-shadow:0 0 14px rgba(255,51,85,.6)}
.topo small{color:var(--apagado)}.relogio{margin-left:auto;font:700 20px "Cascadia Mono",monospace;color:#fff}
.grade{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;padding:18px 22px;max-width:1400px;margin:0 auto}
.card{background:var(--painel);border:1px solid rgba(255,51,85,.22);border-radius:12px;padding:16px 18px;
box-shadow:0 0 30px -12px rgba(255,51,85,.5)}
.card h2{margin:0 0 12px;font:600 12px "Cascadia Mono",monospace;letter-spacing:.25em;color:var(--neon2);text-transform:uppercase}
.medidor{display:flex;align-items:center;gap:14px;margin:10px 0}
.rosca{--v:0;width:92px;height:92px;border-radius:50%;flex:none;
background:conic-gradient(var(--neon) calc(var(--v)*1%),rgba(255,255,255,.06) 0);display:grid;place-items:center;position:relative}
.rosca::before{content:"";position:absolute;inset:9px;border-radius:50%;background:var(--painel)}
.rosca b{position:relative;font:700 20px "Cascadia Mono",monospace;color:#fff}
.medidor .lado{flex:1}.medidor .lado div{color:var(--apagado);font-size:12px}
.barra{height:10px;border-radius:6px;background:rgba(255,255,255,.06);overflow:hidden;margin:4px 0}
.barra i{display:block;height:100%;background:linear-gradient(90deg,var(--forte),var(--neon));width:0;transition:width .4s}
.linha{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.linha b{color:#fff;font-weight:600}.linha span{color:var(--apagado)}
table{width:100%;border-collapse:collapse;font:13px "Cascadia Mono",monospace}
th{text-align:left;color:var(--apagado);font-weight:500;padding:4px 6px;border-bottom:1px solid rgba(255,51,85,.2)}
td{padding:4px 6px;border-bottom:1px solid rgba(255,255,255,.04);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
td.n{color:var(--neon2)}.mini{height:7px;border-radius:4px;background:rgba(255,255,255,.06);overflow:hidden}
.mini i{display:block;height:100%;background:var(--neon)}
.disco{margin:12px 0}.disco .cab{display:flex;justify-content:space-between;font-size:13px}.disco b{color:#fff}
.alerta i{background:linear-gradient(90deg,#ff2d2d,#ff6a85)!important}
.rodape{text-align:center;color:var(--apagado);font-size:12px;padding:10px}
.scan{position:fixed;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(0,0,0,.14) 0 1px,transparent 1px 3px);mix-blend-mode:multiply}
</style></head><body><div class="scan"></div>
<div class="topo"><span class="logo">◈ SPARTA</span><small id="host">—</small><span class="relogio" id="hora">--:--:--</span></div>
<div class="grade">
  <div class="card"><h2>Processador</h2>
    <div class="medidor"><div class="rosca" id="rcpu"><b id="cpu">0%</b></div>
      <div class="lado"><div id="cpu-nome">—</div><div id="cpu-nucleos">—</div></div></div></div>
  <div class="card"><h2>Memória</h2>
    <div class="medidor"><div class="rosca" id="rmem"><b id="mem">0%</b></div>
      <div class="lado"><div id="mem-uso">—</div><div>em uso</div></div></div></div>
  <div class="card" id="card-bat" style="display:none"><h2>Bateria</h2>
    <div class="medidor"><div class="rosca" id="rbat"><b id="bat">—</b></div>
      <div class="lado"><div id="bat-estado">—</div></div></div></div>
  <div class="card"><h2>Sistema</h2>
    <div class="linha"><span>Sistema</span><b id="so">—</b></div>
    <div class="linha"><span>Placa de vídeo</span><b id="gpu">—</b></div>
    <div class="linha"><span>Placa-mãe</span><b id="mae">—</b></div>
    <div class="linha"><span>IP local</span><b id="ip">—</b></div>
    <div class="linha"><span>Ligado há</span><b id="ligado">—</b></div></div>
  <div class="card" style="grid-column:1/-1"><h2>Discos</h2><div id="discos"></div></div>
  <div class="card" style="grid-column:1/-1"><h2>Processos que mais usam memória</h2>
    <table><thead><tr><th>PID</th><th>Programa</th><th>Memória</th><th style="width:30%">%</th></tr></thead>
    <tbody id="procs"></tbody></table></div>
</div>
<div class="rodape">SPARTA // painel local · atualiza a cada 2s · feche a aba para sair</div>
<script>
const $=s=>document.querySelector(s);
function rosca(el,v,alerta){el.style.setProperty("--v",v);
 el.style.background=`conic-gradient(${alerta?"#ff2d2d":"var(--neon)"} calc(var(--v)*1%),rgba(255,255,255,.06) 0)`;}
async function tick(){
 let d;try{d=await (await fetch("/dados")).json();}catch(e){return;}
 if(d.erro)return;
 $("#host").textContent=d.usuario+"@"+d.maquina;
 $("#hora").textContent=d.hora;
 $("#cpu").textContent=d.cpu+"%";rosca($("#rcpu"),d.cpu,d.cpu>90);
 $("#cpu-nome").textContent=d.cpu_nome||d.cpu;$("#cpu-nucleos").textContent=d.nucleos+" núcleos";
 $("#mem").textContent=d.mem_pct+"%";rosca($("#rmem"),d.mem_pct,d.mem_pct>90);
 $("#mem-uso").textContent=d.mem_usada+" / "+d.mem_total;
 $("#so").textContent=d.so;$("#gpu").textContent=d.gpu;$("#mae").textContent=d.placa_mae||"—";
 $("#ip").textContent=d.ip;$("#ligado").textContent=d.ligado;
 if(d.bateria){$("#card-bat").style.display="";$("#bat").textContent=d.bateria.pct+"%";
  rosca($("#rbat"),d.bateria.pct,d.bateria.pct<20);
  $("#bat-estado").textContent=d.bateria.carregando?"carregando ⚡":"na bateria";}
 $("#discos").innerHTML=d.discos.map(x=>`<div class="disco"><div class="cab"><b>${x.raiz} ${x.nome||""}</b>
  <span>${x.livre} livres de ${x.total} · ${x.uso}%</span></div>
  <div class="barra ${x.uso>90?"alerta":""}"><i style="width:${x.uso}%"></i></div></div>`).join("");
 $("#procs").innerHTML=d.processos.map(p=>`<tr><td class="n">${p.pid}</td><td>${p.nome}</td>
  <td>${p.mem}</td><td><div class="mini"><i style="width:${Math.min(100,p.mem_pct*3)}%"></i></div>${p.mem_pct}%</td></tr>`).join("");
}
tick();setInterval(tick,2000);
</script></body></html>"""
