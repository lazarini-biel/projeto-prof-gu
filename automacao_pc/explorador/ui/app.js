"use strict";
/* SPARTA // EXPLORADOR — interface. A lógica de arquivos está no Python. */

const $ = (s, r = document) => r.querySelector(s);
let api = null;
const estado = {
  pasta: null, itens: [], filtro: null, selecao: new Set(),
  historico: [], grade: false, ocultos: false, buscando: false,
};

const CORES = {
  Pasta: "#ffb020", PDFs: "#ff4d4d", Imagens: "#ff3d7f", Vídeos: "#c850ff",
  Músicas: "#50b0ff", Planilhas: "#2fd46b", Documentos: "#6a9bff", "Apresentações": "#ff7a3d",
  Instaladores: "#ff2d55", Compactados: "#d4a017", "Imagens de disco": "#9a6cff",
  Código: "#39ff9c", Fontes: "#c0c0c0", Outros: "#8a6f77",
};
const cor = (c) => CORES[c] || "#8a6f77";
const inicial = (nome, pasta) => pasta ? "▸" : (nome.split(".").pop()[0] || "?").toUpperCase();

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
  setTimeout(() => { a.classList.add("saindo"); setTimeout(() => a.remove(), 320); }, tipo === "erro" ? 5000 : 3200);
}

/* ------------------------------------------------------- navegação */
async function ir(pasta, semHistorico) {
  const r = await api.listar(pasta);
  if (r.erro) { aviso(r.erro, "erro"); return; }
  if (!semHistorico && estado.pasta) estado.historico.push(estado.pasta);
  estado.pasta = r.pasta;
  estado.itens = r.itens;
  estado.pai = r.pai;
  estado.filtro = null;
  estado.selecao.clear();
  estado.buscando = false;
  $("#busca").value = "";
  desenharCaminho();
  desenharFiltros();
  desenharLista();
  marcarAtalhoAtivo();
  $("#bt-voltar").disabled = estado.historico.length === 0;
  $("#bt-acima").disabled = !estado.pai;
}

function voltar() {
  const p = estado.historico.pop();
  if (p) ir(p, true);
}

function desenharCaminho() {
  const c = $("#caminho");
  c.textContent = "";
  const partes = estado.pasta.split(/[\\/]/).filter(Boolean);
  const sep = estado.pasta.includes("\\") ? "\\" : "/";
  let acc = estado.pasta.startsWith("/") ? "" : "";
  partes.forEach((parte, i) => {
    acc = i === 0 ? (estado.pasta.startsWith("/") ? "/" + parte : parte + (parte.endsWith(":") ? sep : "")) : acc + sep + parte;
    const alvo = acc;
    c.append(el("span", { class: "crumb", text: parte, onclick: () => ir(alvo) }));
    if (i < partes.length - 1) c.append(el("span", { class: "sepc", text: " › " }));
  });
}

/* --------------------------------------------------------- lista */
function filtradas() {
  let itens = estado.itens.slice();
  if (!estado.ocultos) itens = itens.filter((x) => !x.oculto);
  if (estado.filtro) itens = itens.filter((x) => x.categoria === estado.filtro);
  itens.sort((a, b) => (b.pasta - a.pasta) || a.nome.localeCompare(b.nome, "pt-BR"));
  return itens;
}

function desenharFiltros() {
  const cont = $("#filtros");
  cont.textContent = "";
  const cats = [...new Set(estado.itens.map((x) => x.categoria))];
  if (cats.length <= 1) return;
  const chip = (nome, label) => el("span", {
    class: "chip" + (estado.filtro === nome ? " ativo" : ""),
    onclick: () => { estado.filtro = estado.filtro === nome ? null : nome; desenharFiltros(); desenharLista(); },
  }, nome ? el("span", { class: "ponto", style: `background:${cor(nome)}` }) : null, label);
  cont.append(chip(null, "Tudo"));
  for (const cat of cats.sort()) cont.append(chip(cat, cat));
}

function desenharLista() {
  const lista = $("#lista");
  lista.textContent = "";
  lista.classList.toggle("grade", estado.grade);
  $("#cab-lista").classList.toggle("escondido", estado.grade || estado.buscando);
  const itens = estado.buscando ? estado.itens : filtradas();
  if (!itens.length) {
    lista.append(el("div", { class: "vazio", text: estado.buscando ? "NADA ENCONTRADO." : "PASTA VAZIA." }));
    atualizarStatus();
    return;
  }
  for (const it of itens) {
    const linha = el("div", {
      class: "item" + (estado.selecao.has(it.caminho) ? " sel" : "") + (it.oculto ? " oculto" : ""),
      onclick: (ev) => selecionar(it, ev),
      ondblclick: () => abrir(it),
      oncontextmenu: (ev) => { ev.preventDefault(); if (!estado.selecao.has(it.caminho)) selecionar(it, {}); menuContexto(ev, it); },
    },
      el("div", { class: "nome" },
        el("div", { class: "ic", style: `background:${cor(it.categoria)}`, text: inicial(it.nome, it.pasta) }),
        el("b", { text: it.nome })),
      el("span", { class: "cat", text: it.categoria }),
      el("span", { class: "tam", text: it.tamanho_fmt || "" }),
      el("span", { class: "data", text: it.modificado_fmt || "" }));
    lista.append(linha);
  }
  atualizarStatus();
}

function selecionar(it, ev) {
  if (ev.ctrlKey) {
    estado.selecao.has(it.caminho) ? estado.selecao.delete(it.caminho) : estado.selecao.add(it.caminho);
  } else {
    estado.selecao.clear();
    estado.selecao.add(it.caminho);
  }
  estado.ultimo = it;
  desenharLista();
}

function abrir(it) {
  if (it.pasta) ir(it.caminho);
  else api.abrir(it.caminho).then((r) => { if (!r.ok) aviso(r.erro, "erro"); });
}

function atualizarStatus() {
  const n = (estado.buscando ? estado.itens : filtradas()).length;
  const s = estado.selecao.size;
  $("#status").textContent = `${n} item(ns)` + (s ? ` · ${s} selecionado(s)` : "");
  const temSel = s > 0;
  $("#bt-excluir").disabled = !temSel;
  $("#bt-mover").disabled = !temSel;
  $("#bt-renomear").disabled = s !== 1;
}

/* ------------------------------------------------------- lateral */
async function desenharLateral() {
  const { atalhos, discos } = await api.locais();
  const ua = $("#atalhos"); ua.textContent = "";
  for (const a of atalhos)
    ua.append(el("li", { "data-caminho": a.caminho, onclick: () => ir(a.caminho), text: a.nome }));
  const ud = $("#discos"); ud.textContent = "";
  for (const d of discos)
    ud.append(el("li", { "data-caminho": d.caminho, onclick: () => ir(d.caminho) },
      el("span", { text: d.nome }),
      el("div", { class: "barra" }, el("i", { style: `width:${d.uso}%` })),
      el("span", { class: "sub" }, el("span", { text: `${d.livre} livres` }), el("span", { text: `${d.uso}%` }))));
}
function marcarAtalhoAtivo() {
  document.querySelectorAll(".lateral li").forEach((li) =>
    li.classList.toggle("ativa", li.getAttribute("data-caminho") === estado.pasta));
}

/* ------------------------------------------------- menu de contexto */
function menuContexto(ev, it) {
  const m = $("#menu-contexto");
  m.textContent = "";
  const n = estado.selecao.size;
  const add = (texto, fn, perigo) => m.append(el("li", { class: perigo ? "perigo" : "", text: texto,
    onclick: () => { fecharMenu(); fn(); } }));
  if (n === 1) {
    add(it.pasta ? "Abrir" : "Abrir no programa padrão", () => abrir(it));
    add("Renomear", renomearSelecao);
  }
  add(`Mover ${n > 1 ? `(${n})` : ""} para…`, moverSelecao);
  add(`Excluir ${n > 1 ? `(${n})` : ""}`, excluirSelecao, true);
  m.append(el("hr"));
  add("Copiar caminho", () => { navigator.clipboard?.writeText(it.caminho); aviso("Caminho copiado.", "ok"); });
  if (it.pasta) add("Abrir no Explorer do Windows", () => api.abrir_no_windows(it.caminho));
  m.style.left = Math.min(ev.clientX, innerWidth - 190) + "px";
  m.style.top = Math.min(ev.clientY, innerHeight - m.children.length * 38 - 20) + "px";
  m.classList.add("aberto");
}
function fecharMenu() { $("#menu-contexto").classList.remove("aberto"); }

/* ----------------------------------------------------- diálogos */
function pedirTexto(titulo, valor = "") {
  return new Promise((r) => {
    const m = $("#modal-texto");
    $("#mt-titulo").textContent = titulo;
    const inp = $("#mt-input");
    inp.value = valor;
    m.returnValue = "";
    m.showModal();
    const ponto = valor.lastIndexOf(".");
    setTimeout(() => { inp.focus(); inp.setSelectionRange(0, ponto > 0 ? ponto : valor.length); }, 30);
    m.addEventListener("close", () => r(m.returnValue === "ok" ? inp.value.trim() : null), { once: true });
  });
}
function confirmar(titulo, texto) {
  return new Promise((r) => {
    const m = $("#modal-confirmar");
    $("#mc-titulo").textContent = titulo;
    $("#mc-texto").textContent = texto;
    m.returnValue = "";
    m.showModal();
    m.addEventListener("close", () => r(m.returnValue === "sim"), { once: true });
  });
}

/* -------------------------------------------------------- ações */
function selecionados() { return [...estado.selecao]; }

async function novaPasta() {
  const nome = await pedirTexto("Nova pasta", "Nova pasta");
  if (!nome) return;
  const r = await api.nova_pasta(estado.pasta, nome);
  if (r.ok) { aviso("Pasta criada.", "ok"); ir(estado.pasta, true); }
  else aviso(r.erro, "erro");
}
async function renomearSelecao() {
  const alvo = estado.itens.find((x) => x.caminho === selecionados()[0]) || estado.ultimo;
  if (!alvo) return;
  const nome = await pedirTexto("Renomear", alvo.nome);
  if (!nome || nome === alvo.nome) return;
  const r = await api.renomear(alvo.caminho, nome);
  if (r.ok) { aviso("Renomeado.", "ok"); ir(estado.pasta, true); }
  else aviso(r.erro, "erro");
}
async function moverSelecao() {
  const r0 = await api.escolher_pasta();
  if (!r0.caminho) return;
  const r = await api.mover(selecionados(), r0.caminho);
  if (r.ok) { aviso(`${r.movidos} item(ns) movidos.`, "ok"); r.erros?.forEach((e) => aviso(e, "erro")); ir(estado.pasta, true); }
  else aviso(r.erro, "erro");
}
async function excluirSelecao() {
  const sel = selecionados();
  const ok = await confirmar("Excluir", `Mandar ${sel.length} item(ns) para a Lixeira?`);
  if (!ok) return;
  const r = await api.excluir(sel);
  aviso(`${r.excluidos} item(ns) ${r.lixeira ? "foram para a Lixeira" : "excluídos"}.`, "ok");
  ir(estado.pasta, true);
}
async function organizar() {
  const prev = await api.organizar(estado.pasta, false);
  if (!prev.total) { aviso("Nada para organizar aqui.", "info"); return; }
  const ok = await confirmar("Organizar por tipo",
    `Separar ${prev.total} arquivo(s) em pastas por tipo (PDFs, Imagens, Instaladores…)?`);
  if (!ok) return;
  const r = await api.organizar(estado.pasta, true);
  aviso(`${r.total} arquivo(s) organizados.`, "ok");
  ir(estado.pasta, true);
}

let buscaTimer = null;
function aoBuscar() {
  clearTimeout(buscaTimer);
  const termo = $("#busca").value.trim();
  if (!termo) { estado.buscando = false; desenharLista(); return; }
  buscaTimer = setTimeout(async () => {
    const r = await api.buscar(estado.pasta, termo);
    estado.buscando = true;
    estado.itens2 = estado.itens;
    estado.itens = r.itens;
    estado.selecao.clear();
    desenharLista();
    if (r.parcial) aviso("Mostrando os primeiros 400 resultados.", "info");
  }, 300);
}

/* -------------------------------------------------------- init */
function ligar() {
  $("#bt-voltar").onclick = voltar;
  $("#bt-acima").onclick = () => estado.pai && ir(estado.pai);
  $("#bt-atualizar").onclick = () => ir(estado.pasta, true);
  $("#bt-nova").onclick = novaPasta;
  $("#bt-organizar").onclick = organizar;
  $("#bt-renomear").onclick = renomearSelecao;
  $("#bt-mover").onclick = moverSelecao;
  $("#bt-excluir").onclick = excluirSelecao;
  $("#bt-visao").onclick = () => { estado.grade = !estado.grade; desenharLista(); };
  $("#mostrar-ocultos").onchange = (e) => { estado.ocultos = e.target.checked; desenharLista(); };
  $("#busca").oninput = aoBuscar;
  $("#bt-tela-cheia").onclick = () => api?.alternar_tela_cheia();
  $("#bt-sair").onclick = () => api?.sair();
  document.addEventListener("click", fecharMenu);
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "F11") { ev.preventDefault(); api?.alternar_tela_cheia(); }
    else if (ev.key === "F5") { ev.preventDefault(); ir(estado.pasta, true); }
    else if (ev.ctrlKey && ev.key === "f") { ev.preventDefault(); $("#busca").focus(); }
    else if (ev.key === "Delete" && estado.selecao.size) excluirSelecao();
    else if (ev.key === "F2" && estado.selecao.size === 1) renomearSelecao();
    else if (ev.altKey && ev.key === "ArrowLeft") voltar();
    else if (ev.altKey && ev.key === "ArrowUp" && estado.pai) ir(estado.pai);
  });
}

async function iniciar() {
  api = window.pywebview.api;
  ligar();
  await desenharLateral();
  const st = await api.estado();
  ir(st.inicio);
}
if (window.pywebview && window.pywebview.api) iniciar();
else window.addEventListener("pywebviewready", iniciar);
