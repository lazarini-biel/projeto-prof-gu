"use strict";
/* SPARTA // MIXER — interface. O controle de áudio está no Python (pycaw + Equalizer APO). */

const $ = (s, r = document) => r.querySelector(s);
let api = null;
const estado = { eqapo: false, pycaw: false, boostMax: 400, arrastando: false };

function el(tag, props = {}, ...filhos) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) if (f != null) n.append(f);
  return n;
}
function aviso(t, tipo = "info") {
  const a = el("div", { class: `aviso ${tipo}`, text: t });
  $("#avisos").append(a);
  setTimeout(() => { a.classList.add("saindo"); setTimeout(() => a.remove(), 320); }, tipo === "erro" ? 5000 : 2600);
}
function corApp(nome) {
  let h = 0; for (const c of nome || "?") h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return `hsl(${h % 360} 75% 60%)`;
}

/* --------------------------------------------------- canal (strip) */
function canal({ id, nome, cor, volume, mudo, boost, master }) {
  const icone = el("div", { class: "icone", style: `background:${cor}`, text: (nome.trim()[0] || "?").toUpperCase() });
  const pct = el("div", { class: "pct", text: volume + "%" });
  const boostnum = el("div", { class: "boostnum", text: boost > 100 ? "boost " + boost + "%" : "" });

  const fader = el("input", { type: "range", class: "fader", min: 0, max: 100, value: volume });
  fader.addEventListener("input", () => { pct.textContent = fader.value + "%"; estado.arrastando = true; });
  fader.addEventListener("change", async () => {
    estado.arrastando = false;
    const r = master ? await api.set_master(+fader.value) : await api.set_volume(id, +fader.value);
    if (!r.ok) aviso(r.erro, "erro");
  });

  const btMute = el("button", { class: "mute" + (mudo ? " on" : ""), text: mudo ? "🔇" : "🔊",
    onclick: async () => {
      const novo = !btMute.classList.contains("on");
      const r = master ? await api.set_master_mudo(novo) : await api.set_mudo(id, novo);
      if (r.ok) { btMute.classList.toggle("on", novo); btMute.textContent = novo ? "🔇" : "🔊"; }
      else aviso(r.erro, "erro");
    } });

  // boost (Equalizer APO) — GERAL para o master, por app para os demais
  const alvoBoost = master ? "" : id;
  const valorBoost = el("span", { class: "pct", style: "font-size:13px;color:var(--ambar);min-width:46px;text-align:center",
    text: boost + "%" });
  const passo = async (d) => {
    let v = Math.max(100, Math.min(estado.boostMax, (boost || 100) + d));
    boost = v; valorBoost.textContent = v + "%"; boostnum.textContent = v > 100 ? "boost " + v + "%" : "";
    const r = await api.set_boost(alvoBoost, v);
    if (!r.ok) aviso(r.erro, "erro");
  };
  const menos = el("button", { text: "−", disabled: !estado.eqapo, onclick: () => passo(-10) });
  const mais = el("button", { text: "+", disabled: !estado.eqapo, onclick: () => passo(+10) });
  const boostBox = el("div", { class: "boost", title: estado.eqapo ? "Boost (passa de 100%)" : "Instale o Equalizer APO para passar de 100%" },
    el("span", { class: "rot", text: "BOOST" }), menos, valorBoost, mais);

  return el("div", { class: "canal" + (master ? " master" : "") },
    icone,
    el("div", { class: "nome", text: master ? "Geral (Windows)" : nome }),
    pct, boostnum,
    el("div", { class: "fader-area" }, fader),
    el("div", { class: "botoes-canal" }, btMute),
    boostBox);
}

/* ---------------------------------------------------- carregar */
async function atualizar() {
  if (estado.arrastando) return;        // não atropela o usuário mexendo no fader
  const r = await api.sessoes();
  const mesa = $("#mesa");
  if (r.erro === "pycaw") {
    mesa.innerHTML = "";
    mesa.append(el("div", { class: "vazio" },
      el("div", { text: "A biblioteca de áudio (pycaw) não está instalada." }),
      el("div", { style: "margin-top:10px;color:var(--neon2)", text: "Rode uma vez:  py -m pip install pycaw comtypes" })));
    return;
  }
  if (r.erro) { mesa.innerHTML = ""; mesa.append(el("div", { class: "vazio", text: r.erro })); return; }
  mesa.textContent = "";
  if (r.master) {
    const bg = estado.boostGeral || 100;
    mesa.append(canal({ id: "__master__", nome: "Geral", cor: "var(--neon)",
      volume: r.master.volume, mudo: r.master.mudo, boost: bg, master: true }));
  }
  if (!r.sessoes.length) {
    mesa.append(el("div", { class: "vazio", text: "Nenhum app tocando som agora.\nAbra um player/jogo/navegador com áudio." }));
  }
  for (const s of r.sessoes)
    mesa.append(canal({ id: s.exe || s.id, nome: s.nome, cor: corApp(s.nome),
      volume: s.volume, mudo: s.mudo, boost: s.boost || 100 }));
  $("#rodape").textContent = `${r.sessoes.length} app(s) com áudio`;
}

async function iniciar() {
  api = window.pywebview.api;
  const st = await api.estado();
  estado.eqapo = st.eqapo; estado.pycaw = st.pycaw;
  estado.boostGeral = (st.boost || {}).GERAL || 100;
  const ee = $("#estado-eqapo");
  ee.innerHTML = st.eqapo
    ? 'Boost além de 100%: <b class="on">Equalizer APO ativo</b>'
    : 'Boost além de 100%: <b class="off">Equalizer APO não instalado</b>';
  if (!st.eqapo && st.windows) {
    const banner = $("#banner");
    banner.classList.remove("escondido");
    banner.append(el("span", { text: "Para passar de 100% o volume, instale o Equalizer APO (gratuito). O volume 0–100%, geral e mudo já funcionam sem ele." }),
      el("button", { text: "Baixar Equalizer APO", onclick: () => api.abrir_eqapo() }));
  }
  $("#bt-atualizar").onclick = atualizar;
  $("#bt-tela-cheia").onclick = () => api.alternar_tela_cheia();
  $("#bt-sair").onclick = () => api.sair();
  document.addEventListener("keydown", (ev) => { if (ev.key === "F11") { ev.preventDefault(); api.alternar_tela_cheia(); } });
  atualizar();
  setInterval(atualizar, 1800);
}
if (window.pywebview && window.pywebview.api) iniciar();
else window.addEventListener("pywebviewready", iniciar);
