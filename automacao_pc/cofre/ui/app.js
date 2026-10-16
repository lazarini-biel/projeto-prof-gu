"use strict";
/*
 * Tela do COFRE. Toda a criptografia acontece no Python (nucleo.py); aqui só
 * há interface e animação. Dados vindos do cofre são sempre inseridos com
 * textContent (nunca innerHTML) — um título malicioso importado de um CSV
 * não consegue executar código nesta janela.
 */

const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
let api = null;

const estado = {
  entradas: [],
  categoria: "Todas",
  selecionado: null,
  prefs: null,
  navegadores: [],
  criando: false,
  minimo: 10,
  kdf: {},
  ultimaAtividade: Date.now(),
  ultimoPing: 0,
  janelaAlvo: null,
  temporizadorRevelar: null,
};

/* ------------------------------------------------------------ utilidades */
function el(tag, props = {}, ...filhos) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) if (f !== null && f !== undefined) n.append(f);
  return n;
}

function aviso(texto, tipo = "info") {
  const a = el("div", { class: `aviso ${tipo}`, text: texto });
  $("#avisos").append(a);
  setTimeout(() => { a.classList.add("saindo"); setTimeout(() => a.remove(), 350); }, tipo === "erro" ? 6000 : 3800);
}

function corPara(texto) {
  let h = 0;
  for (const c of texto || "?") h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return `hsl(${h % 360} 80% 62%)`;
}

function icone(entrada, classe = "icone") {
  const base = entrada.titulo || entrada.dominio || "?";
  return el("div", { class: classe, style: `background:${corPara(entrada.dominio || base)}`, text: base.trim()[0]?.toUpperCase() || "?" });
}

const SIMBOLOS = "ABCDEF0123456789#$%&@<>/\\{}[]=+*";
const aleatorio = (n) => Array.from({ length: n }, () => SIMBOLOS[(Math.random() * SIMBOLOS.length) | 0]).join("");

/** Efeito "decifrando": caracteres aleatórios que vão se fixando da esquerda para a direita. */
function embaralhar(alvo, final, duracao = 700) {
  return new Promise((resolve) => {
    const inicio = performance.now();
    const passo = (agora) => {
      const t = Math.min(1, (agora - inicio) / duracao);
      const fixos = Math.floor(final.length * t);
      alvo.textContent = final.slice(0, fixos) + aleatorio(final.length - fixos);
      if (t < 1) requestAnimationFrame(passo);
      else { alvo.textContent = final; resolve(); }
    };
    requestAnimationFrame(passo);
  });
}

async function digitarLinhas(caixa, linhas, intervalo = 16) {
  caixa.textContent = "";
  for (const texto of linhas) {
    const linha = el("div", { class: "linha cursor" });
    caixa.append(linha);
    for (let i = 1; i <= texto.length; i++) {
      linha.textContent = texto.slice(0, i);
      await esperar(intervalo);
    }
    linha.classList.remove("cursor");
    await esperar(120);
  }
}

function pintarMedidor(barra, forca) {
  const cores = ["#ff3b5c", "#ff7a3b", "#ffb020", "#7dff6a", "#39ff9c"];
  barra.style.width = forca.bits ? `${(forca.nivel + 1) * 20}%` : "0";
  barra.style.background = cores[forca.nivel];
}

/* --------------------------------------------- chuva de caracteres (fundo) */
function iniciarChuva() {
  const tela = $("#chuva");
  const ctx = tela.getContext("2d");
  const chars = "アイウエオカキクケコサシスセソタチツテト0123456789ABCDEF<>{}[]#$%";
  const tam = 16;
  let colunas = [];
  const ajustar = () => {
    tela.width = innerWidth; tela.height = innerHeight;
    colunas = Array.from({ length: Math.ceil(innerWidth / tam) }, () => Math.random() * -60);
  };
  ajustar();
  addEventListener("resize", ajustar);
  let ultimo = 0;
  const desenhar = (agora) => {
    requestAnimationFrame(desenhar);
    if (agora - ultimo < 50) return;
    ultimo = agora;
    ctx.fillStyle = "rgba(7, 2, 4, 0.14)";
    ctx.fillRect(0, 0, tela.width, tela.height);
    ctx.font = `${tam - 2}px Consolas, monospace`;
    colunas.forEach((y, i) => {
      const c = chars[(Math.random() * chars.length) | 0];
      ctx.fillStyle = Math.random() > 0.975 ? "#ffe3e8" : "rgba(255, 51, 85, 0.75)";
      ctx.fillText(c, i * tam, y * tam);
      colunas[i] = y * tam > tela.height && Math.random() > 0.975 ? 0 : y + 1;
    });
  };
  requestAnimationFrame(desenhar);
}

/* ================================================================= LOGIN */
function relogio() {
  const r = $("#relogio");
  const tic = () => { r.textContent = new Date().toLocaleTimeString("pt-BR"); };
  tic(); setInterval(tic, 1000);
}

async function iniciar() {
  if (api) return;
  api = window.pywebview.api;
  iniciarChuva();
  relogio();
  const st = await api.estado();
  estado.minimo = st.minimo;
  estado.kdf = st.kdf;
  $("#caminho-cofre").textContent = "ARQUIVO: " + st.caminho;
  if (st.aberto) return entrarNoCofre();
  if (st.abertura) await window.abertura(await fontesDaAbertura());

  estado.criando = !st.existe;
  await digitarLinhas($("#boot"), [
    "INICIALIZANDO PROTOCOLO DE SEGURANÇA...",
    "CANAL CRIPTOGRAFADO: AES-256-GCM // CHAVE: SCRYPT",
    st.existe ? "COFRE LOCALIZADO. AGUARDANDO CREDENCIAL DO AGENTE."
              : "NENHUM COFRE ENCONTRADO. DEFINA SUA CREDENCIAL MESTRA.",
  ]);
  prepararFormulario();
  if (st.espera > 0) contagemBloqueio(st.espera);
}

async function fontesDaAbertura() {
  try {
    const fontes = await api.codigo_fonte();
    if (fontes && fontes.length) return fontes;
  } catch (e) { /* segue para o plano B */ }
  try {
    return [{ nome: "app.js", texto: await (await fetch("app.js")).text() }];
  } catch (e) {
    return [];
  }
}

function prepararFormulario() {
  const form = $("#form-login");
  form.classList.remove("escondido");
  $("#bloco-criar").classList.toggle("escondido", !estado.criando);
  $("#rotulo-senha").textContent = estado.criando ? "NOVA CREDENCIAL MESTRA" : "CREDENCIAL DO AGENTE";
  $("#botao-login").textContent = estado.criando ? "CRIAR COFRE" : "AUTENTICAR";
  $("#dica-criar").textContent = `Mínimo de ${estado.minimo} caracteres. Uma frase longa é ótima ` +
    `(ex.: "cafe-forte-na-varanda-1987"). Sem ela não há como recuperar nada.`;
  $("#senha").value = ""; $("#senha2").value = "";
  setTimeout(() => $("#senha").focus(), 50);
}

function statusLogin(texto, tipo = "") {
  const s = $("#status-login");
  s.textContent = texto;
  s.className = "status-login " + tipo;
}

function contagemBloqueio(segundos) {
  const botao = $("#botao-login");
  botao.disabled = true;
  const fim = Date.now() + segundos * 1000;
  const tic = () => {
    const resta = Math.ceil((fim - Date.now()) / 1000);
    if (resta <= 0) { botao.disabled = false; statusLogin("TENTE NOVAMENTE.", "alerta"); return; }
    statusLogin(`MUITAS TENTATIVAS. AGUARDE ${resta}s.`, "erro");
    setTimeout(tic, 250);
  };
  tic();
}

async function aoEnviarLogin(ev) {
  ev.preventDefault();
  const senha = $("#senha").value;
  if (!senha) return;
  if (estado.criando) {
    if (senha.length < estado.minimo) return statusLogin(`USE PELO MENOS ${estado.minimo} CARACTERES.`, "erro");
    if (senha !== $("#senha2").value) return statusLogin("AS CREDENCIAIS NÃO CONFEREM.", "erro");
  }
  $("#botao-login").disabled = true;
  statusLogin("");
  const chamada = estado.criando ? api.criar(senha, $("#senha2").value) : api.desbloquear(senha);
  $("#senha").value = ""; $("#senha2").value = "";
  const resultado = await animacaoDecifrar(chamada, estado.criando);
  $("#botao-login").disabled = false;
  if (resultado.ok) return entrarNoCofre();

  const hud = $("#hud");
  hud.classList.remove("negado"); void hud.offsetWidth; hud.classList.add("negado");
  if (resultado.espera > 0) contagemBloqueio(resultado.espera);
  else statusLogin(resultado.falhas ? `ACESSO NEGADO — TENTATIVA ${resultado.falhas}` : resultado.erro, "erro");
  $("#senha").focus();
}

async function animacaoDecifrar(chamada, criando) {
  const caixa = $("#decifrando");
  const matriz = $("#matriz-hex");
  const etapas = $("#etapas");
  const barra = $("#barra-progresso");
  const veredito = $("#veredito");
  veredito.className = ""; veredito.textContent = ""; etapas.textContent = ""; barra.style.width = "0";
  caixa.classList.add("ativa");

  const linhasHex = () => Array.from({ length: 9 }, () =>
    aleatorio(52).replace(/(.{4})/g, "$1 ").trim()).join("\n");
  const animarMatriz = setInterval(() => { matriz.textContent = linhasHex(); }, 55);

  const kdf = `scrypt N=2^${Math.log2(estado.kdf.n || 131072)} r=${estado.kdf.r || 8} p=${estado.kdf.p || 1}`;
  const roteiro = criando
    ? ["GERANDO SAL CRIPTOGRÁFICO (128 bits)", `DERIVANDO CHAVE MESTRA · ${kdf}`, "CIFRANDO COFRE · AES-256-GCM", "GRAVANDO EM DISCO"]
    : ["ESTABELECENDO CANAL SEGURO", `DERIVANDO CHAVE · ${kdf}`, "DESCRIPTOGRAFANDO · AES-256-GCM", "VERIFICANDO INTEGRIDADE"];
  const linhas = roteiro.map((t) => el("div", { text: t }));
  const etapa = async (i, ms) => {
    linhas[i].className = "rodando"; etapas.append(linhas[i]);
    await esperar(ms);
  };
  const feita = (i) => { linhas[i].className = "feito"; };

  await etapa(0, 380); feita(0); barra.style.width = "18%";
  await etapa(1, 0);
  let progresso = 18;
  const subir = setInterval(() => { progresso = Math.min(68, progresso + 2); barra.style.width = progresso + "%"; }, 60);
  const [resultado] = await Promise.all([chamada.catch((e) => ({ ok: false, erro: String(e) })), esperar(900)]);
  clearInterval(subir);

  if (resultado.ok) {
    feita(1); barra.style.width = "72%";
    await etapa(2, 300); feita(2); barra.style.width = "88%";
    await etapa(3, 260); feita(3); barra.style.width = "100%";
    clearInterval(animarMatriz);
    await embaralhar(matriz, linhasHex().replace(/[^\s]/g, "0"), 350);
    veredito.className = "concedido";
    await embaralhar(veredito, "ACESSO CONCEDIDO", 650);
    $("#hud").classList.add("aberto");
    caixa.classList.add("flash-verde");
    await esperar(850);
  } else {
    linhas[1].className = "";
    linhas[1].style.color = "var(--vermelho)";
    barra.style.background = "var(--vermelho)";
    clearInterval(animarMatriz);
    const texto = resultado.erro === "ACESSO NEGADO" || resultado.erro === "AGUARDE" ? "ACESSO NEGADO" : "FALHA";
    veredito.className = "negado";
    veredito.dataset.texto = texto;
    await embaralhar(veredito, texto, 450);
    await esperar(1100);
    barra.style.background = "";
  }
  caixa.classList.remove("ativa", "flash-verde");
  return resultado;
}

/* ================================================================= COFRE */
async function entrarNoCofre() {
  document.body.classList.add("desbloqueado");
  $("#tela-login").classList.remove("ativa");
  $("#tela-cofre").classList.add("ativa");
  const st = await api.estado();
  estado.prefs = st.preferencias;
  estado.ultimaAtividade = Date.now();
  const atalho = $("#estado-atalho");
  if (!st.windows) { atalho.textContent = "(disponível no Windows)"; atalho.classList.add("erro"); }
  else if (st.atalho && st.atalho !== "Ctrl+Alt+A") { atalho.textContent = st.atalho; atalho.classList.add("erro"); }
  else { atalho.textContent = "● atalho ativo"; atalho.classList.remove("erro"); }
  estado.navegadores = await api.navegadores();
  await carregar();
  $("#busca").focus();
}

async function carregar(manterSelecao = true) {
  estado.entradas = await api.entradas();
  $("#contagem").textContent = `${estado.entradas.length} registro${estado.entradas.length === 1 ? "" : "s"}`;
  desenharCategorias();
  desenharLista();
  if (manterSelecao && estado.selecionado && estado.entradas.some((e) => e.id === estado.selecionado)) {
    await selecionar(estado.selecionado);
  } else {
    limparDetalhe();
  }
}

function categorias() {
  const contagem = new Map();
  for (const e of estado.entradas) contagem.set(e.categoria || "Geral", (contagem.get(e.categoria || "Geral") || 0) + 1);
  return [...contagem.entries()].sort((a, b) => a[0].localeCompare(b[0], "pt-BR"));
}

function desenharCategorias() {
  const ul = $("#categorias");
  ul.textContent = "";
  const itens = [["Todas", estado.entradas.length], ["★ Favoritos", estado.entradas.filter((e) => e.favorito).length], ...categorias()];
  if (!itens.some(([n]) => n === estado.categoria)) estado.categoria = "Todas";
  for (const [nome, qtd] of itens) {
    ul.append(el("li", {
      class: nome === estado.categoria ? "ativa" : "",
      onclick: () => { estado.categoria = nome; desenharCategorias(); desenharLista(); },
    }, el("span", { text: nome }), el("span", { text: String(qtd) })));
  }
  const lista = $("#lista-categorias");
  lista.textContent = "";
  for (const [nome] of categorias()) lista.append(el("option", { value: nome }));
}

const semAcento = (t) => (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

function filtradas() {
  const termo = semAcento($("#busca").value.trim());
  return estado.entradas
    .filter((e) => estado.categoria === "Todas"
      || (estado.categoria === "★ Favoritos" ? e.favorito : (e.categoria || "Geral") === estado.categoria))
    .filter((e) => !termo || semAcento([e.titulo, e.usuario, e.dominio, e.categoria].join(" ")).includes(termo))
    .sort((a, b) => (b.favorito - a.favorito) || a.titulo.localeCompare(b.titulo, "pt-BR"));
}

function desenharLista() {
  const lista = $("#lista");
  lista.textContent = "";
  const itens = filtradas();
  if (!itens.length) {
    lista.append(el("div", { class: "lista-vazia",
      text: estado.entradas.length ? "NENHUM REGISTRO ENCONTRADO." : "COFRE VAZIO. CLIQUE EM ＋ NOVO OU IMPORTE AS SENHAS DO NAVEGADOR." }));
    return;
  }
  itens.forEach((e, i) => {
    lista.append(el("div", {
      class: "cartao" + (e.id === estado.selecionado ? " selecionado" : ""),
      style: `animation-delay:${Math.min(i, 20) * 25}ms`,
      tabindex: 0,
      onclick: () => selecionar(e.id),
      onkeydown: (ev) => { if (ev.key === "Enter") selecionar(e.id); },
      ondblclick: () => abrirEPreencher(e.id),
    }, icone(e), el("div", { class: "info" }, el("b", { text: e.titulo }), el("span", { text: e.usuario || e.dominio || "—" })),
    e.favorito ? el("span", { class: "estrela", text: "★" }) : null));
  });
}

function limparDetalhe() {
  estado.selecionado = null;
  const d = $("#detalhe");
  d.textContent = "";
  d.append(el("div", { class: "vazio" }, el("p", { text: "Selecione um registro" })));
}

async function selecionar(id) {
  estado.selecionado = id;
  $$(".cartao").forEach((c) => c.classList.remove("selecionado"));
  const e = await api.entrada(id);
  desenharLista();
  desenharDetalhe(e);
}

function campo(rotulo, conteudo, ...botoes) {
  return el("div", { class: "campo-detalhe" }, el("label", { text: rotulo }), el("div", { class: "valor" }, conteudo, ...botoes));
}

function desenharDetalhe(e) {
  const d = $("#detalhe");
  d.textContent = "";
  clearTimeout(estado.temporizadorRevelar);
  const dominio = e.url ? (e.url.includes("://") ? e.url : "https://" + e.url).replace(/^https?:\/\/(www\.)?/, "").split("/")[0] : "";
  d.append(el("div", { class: "cabeca-detalhe" }, icone({ ...e, dominio }),
    el("div", {}, el("h2", { text: e.titulo }), el("small", { text: `${e.categoria || "Geral"}${dominio ? " · " + dominio : ""}` }))));

  const saidaSenha = el("output", { class: "oculta", text: "••••••••••••" });
  let visivel = false;
  const revelar = el("button", { class: "mini", title: "Revelar", text: "◉", onclick: async () => {
    visivel = !visivel;
    clearTimeout(estado.temporizadorRevelar);
    if (visivel) {
      saidaSenha.classList.remove("oculta");
      await embaralhar(saidaSenha, e.senha || "", 550);
      estado.temporizadorRevelar = setTimeout(() => { if (visivel) revelar.click(); }, 15000);
    } else {
      saidaSenha.classList.add("oculta");
      saidaSenha.textContent = "••••••••••••";
    }
  } });

  d.append(
    campo("USUÁRIO", el("output", { text: e.usuario || "—" }), botaoCopiar(e.id, "usuario")),
    campo("SENHA", saidaSenha, revelar, botaoCopiar(e.id, "senha")),
  );
  if (e.url) {
    const nav = estado.navegadores.find((n) => n.chave === e.navegador);
    d.append(campo("SITE", el("output", { text: e.url }),
      el("button", { class: "mini", title: "Abrir", text: "↗", onclick: () => api.abrir_site(e.id) })));
    d.append(campo("NAVEGADOR", el("output", { text: nav ? nav.nome : "Padrão do Windows" })));
  }
  if (e.notas) d.append(campo("NOTAS", el("output", { class: "notas", text: e.notas })));
  if (e.palavras && e.palavras.length) d.append(campo("RECONHECE JANELAS COM", el("output", { text: e.palavras.join(", ") })));

  d.append(el("div", { class: "botoes-detalhe" },
    e.url ? el("button", { class: "botao destaque largo", text: "⚡ Abrir e preencher login", onclick: () => abrirEPreencher(e.id) }) : null,
    el("button", { class: "botao", text: "✎ Editar", onclick: () => abrirEditor(e) }),
    el("button", { class: "botao perigo", text: "🗑 Excluir", onclick: () => excluir(e) })));
  if (e.alterado) d.append(el("p", { class: "dica", text: "Atualizado em " + new Date(e.alterado * 1000).toLocaleString("pt-BR") }));
}

function botaoCopiar(id, campoNome) {
  return el("button", { class: "mini", title: "Copiar", text: "⧉", onclick: async () => {
    const r = await api.copiar(id, campoNome);
    if (r.ok) aviso(`${campoNome === "senha" ? "Senha" : "Usuário"} copiado. Some da área de transferência em ${r.segundos}s.`, "ok");
    else aviso(r.erro, "erro");
  } });
}

async function abrirEPreencher(id) {
  const r = await api.abrir_e_preencher(id);
  if (r.ok) aviso("Abrindo o site… o login será digitado quando a página aparecer.", "info");
  else aviso(r.erro, "erro");
}

async function confirmar(titulo, texto) {
  const m = $("#modal-confirmar");
  $("#confirmar-titulo").textContent = titulo;
  $("#confirmar-texto").textContent = texto;
  m.returnValue = "";
  m.showModal();
  return new Promise((r) => m.addEventListener("close", () => r(m.returnValue === "sim"), { once: true }));
}

async function excluir(e) {
  if (!(await confirmar("EXCLUIR REGISTRO", `Excluir "${e.titulo}" para sempre?`))) return;
  await api.excluir(e.id);
  estado.selecionado = null;
  await carregar(false);
  aviso("Registro excluído.", "ok");
}

/* ---------------------------------------------------------------- editor */
function abrirEditor(e = null) {
  const form = $("#form-editor");
  form.reset();
  form.dataset.id = e ? e.id : "";
  $("#titulo-editor").textContent = e ? "EDITAR REGISTRO" : "NOVO REGISTRO";
  const sel = $("#sel-navegador");
  sel.textContent = "";
  sel.append(el("option", { value: "", text: "Padrão do Windows" }));
  for (const n of estado.navegadores) sel.append(el("option", { value: n.chave, text: n.nome }));
  if (e) {
    for (const nome of ["titulo", "categoria", "url", "usuario", "senha", "notas", "sequencia"]) form.elements[nome].value = e[nome] || "";
    form.elements.navegador.value = e.navegador || "";
    form.elements.palavras.value = (e.palavras || []).join(", ");
    form.elements.favorito.checked = !!e.favorito;
  } else if (!["Todas", "★ Favoritos"].includes(estado.categoria)) {
    form.elements.categoria.value = estado.categoria;
  }
  form.elements.senha.type = "password";
  atualizarForcaEditor();
  $("#modal-editor").showModal();
  form.elements.titulo.focus();
}

async function atualizarForcaEditor() {
  const senha = $("#form-editor").elements.senha.value;
  const f = await api.forca(senha);
  pintarMedidor($("#medidor-editor"), f);
  $("#forca-editor").textContent = senha ? `${f.rotulo} · ~${f.bits} bits` : "";
}

async function salvarEditor() {
  const f = $("#form-editor").elements;
  const dados = {
    id: $("#form-editor").dataset.id || null,
    titulo: f.titulo.value, categoria: f.categoria.value, url: f.url.value, usuario: f.usuario.value,
    senha: f.senha.value, navegador: f.navegador.value, notas: f.notas.value, sequencia: f.sequencia.value,
    palavras: f.palavras.value.split(","), favorito: f.favorito.checked,
  };
  const r = await api.salvar(dados);
  estado.selecionado = r.id;
  await carregar();
  aviso("Registro salvo e cifrado.", "ok");
}

/* --------------------------------------------------------------- gerador */
async function gerarNoModal() {
  const opcoes = {
    tamanho: +$("#g-tamanho").value, maiusculas: $("#g-mai").checked, minusculas: $("#g-min").checked,
    numeros: $("#g-num").checked, simbolos: $("#g-sim").checked, evitar_ambiguos: $("#g-amb").checked,
  };
  $("#rotulo-tamanho").textContent = opcoes.tamanho;
  const senha = await api.gerar(opcoes);
  embaralhar($("#senha-gerada"), senha, 380);
  pintarMedidor($("#medidor-gerador"), await api.forca(senha));
  return senha;
}

/* ---------------------------------------------- Ctrl+Alt+A sem certeza */
function palavraDaJanela(titulo, navegador) {
  const partes = titulo.split(/\s+[-—–|]\s+/).map((p) => p.trim()).filter(Boolean);
  const semNavegador = partes.filter((p) => !navegador || !semAcento(p).includes(semAcento(navegador).split(" ").pop()));
  return (semNavegador.length ? semNavegador : partes).sort((a, b) => b.length - a.length)[0] || "";
}

function escolherParaJanela(dados) {
  estado.janelaAlvo = dados;
  $("#escolher-janela").textContent = `${dados.titulo}${dados.navegador ? " (" + dados.navegador + ")" : ""}`;
  $("#escolher-busca").value = "";
  desenharEscolhas();
  const m = $("#modal-escolher");
  if (!m.open) m.showModal();
  $("#escolher-busca").focus();
}

function desenharEscolhas() {
  const dados = estado.janelaAlvo;
  const termo = semAcento($("#escolher-busca").value);
  const prioridade = new Map(dados.ids.map((id, i) => [id, i]));
  const lista = estado.entradas
    .filter((e) => !termo || semAcento(`${e.titulo} ${e.usuario} ${e.dominio}`).includes(termo))
    .sort((a, b) => (prioridade.get(a.id) ?? 999) - (prioridade.get(b.id) ?? 999) || a.titulo.localeCompare(b.titulo));
  const ul = $("#escolher-lista");
  ul.textContent = "";
  for (const e of lista.slice(0, 50)) {
    ul.append(el("li", { tabindex: 0, onclick: () => usarNaJanela(e.id), onkeydown: (ev) => { if (ev.key === "Enter") usarNaJanela(e.id); } },
      icone(e), el("div", {}, el("b", { text: e.titulo }), el("div", { class: "dica", text: e.usuario || e.dominio || "" }))));
  }
}

async function usarNaJanela(id) {
  const dados = estado.janelaAlvo;
  $("#modal-escolher").close();
  if ($("#escolher-ensinar").checked && !dados.ids.includes(id)) {
    const palavra = palavraDaJanela(dados.titulo, dados.navegador);
    if (palavra) await api.ensinar_janela(id, palavra);
  }
  const r = await api.preencher_alvo(id);
  if (!r.ok) aviso(r.erro, "erro");
}

/* ------------------------------------------------------- bloqueio/ajustes */
async function voltarAoLogin(mensagem = "") {
  $$("dialog[open]").forEach((d) => d.close());
  document.body.classList.remove("desbloqueado");
  $("#tela-cofre").classList.remove("ativa");
  $("#tela-login").classList.add("ativa");
  $("#hud").classList.remove("aberto", "negado");
  estado.entradas = []; estado.selecionado = null;
  $("#lista").textContent = ""; limparDetalhe();
  estado.criando = false;
  $("#boot").textContent = "";
  await digitarLinhas($("#boot"), ["SESSÃO ENCERRADA. DADOS REMOVIDOS DA MEMÓRIA.", "AGUARDANDO CREDENCIAL DO AGENTE."], 10);
  prepararFormulario();
  if (mensagem) statusLogin(mensagem, "alerta");
}

async function bloquear(mensagem) {
  await api.bloquear();
  voltarAoLogin(mensagem);
}

function marcarAtividade() {
  estado.ultimaAtividade = Date.now();
  if (api && document.body.classList.contains("desbloqueado") && Date.now() - estado.ultimoPing > 5000) {
    estado.ultimoPing = Date.now();
    api.atividade();
  }
}

function relogioBloqueio() {
  setInterval(() => {
    if (!estado.prefs || !document.body.classList.contains("desbloqueado")) return;
    const resta = Math.max(0, estado.prefs.bloqueio_minutos * 60 - (Date.now() - estado.ultimaAtividade) / 1000);
    $("#timer-bloqueio").textContent = `${String(Math.floor(resta / 60)).padStart(2, "0")}:${String(Math.floor(resta % 60)).padStart(2, "0")}`;
  }, 1000);
}

async function abrirAjustes() {
  const st = await api.estado();
  const f = $("#form-ajustes");
  f.reset();
  f.elements.bloqueio_minutos.value = st.preferencias.bloqueio_minutos;
  f.elements.limpar_copia_segundos.value = st.preferencias.limpar_copia_segundos;
  $("#ajustes-caminho").textContent = st.caminho;
  $("#modal-ajustes").showModal();
}

/* -------------------------------------------------------------- ligações */
function ligarEventos() {
  $("#form-login").addEventListener("submit", aoEnviarLogin);
  $("#senha").addEventListener("input", async () => {
    if (!estado.criando || !api) return;
    pintarMedidor($("#medidor-login"), await api.forca($("#senha").value));
  });
  $$(".olho").forEach((b) => b.addEventListener("click", () => {
    const alvo = b.dataset.alvo ? $("#" + b.dataset.alvo) : b.closest("form").elements[b.dataset.alvoNome];
    alvo.type = alvo.type === "password" ? "text" : "password";
  }));

  $("#busca").addEventListener("input", desenharLista);
  $("#bt-novo").addEventListener("click", () => abrirEditor());
  $("#bt-bloquear").addEventListener("click", () => bloquear(""));
  $("#bt-gerador").addEventListener("click", () => { $("#modal-gerador").showModal(); gerarNoModal(); });
  $("#bt-regerar").addEventListener("click", gerarNoModal);
  $$("#modal-gerador input").forEach((i) => i.addEventListener("input", gerarNoModal));
  $("#bt-copiar-gerada").addEventListener("click", async () => {
    const r = await api.copiar_texto($("#senha-gerada").textContent);
    aviso(r.ok ? `Copiada. Some em ${r.segundos}s.` : r.erro, r.ok ? "ok" : "erro");
  });

  $("#bt-importar").addEventListener("click", async () => {
    const r = await api.importar();
    if (r.cancelado) return;
    if (!r.ok) return aviso(r.erro, "erro");
    await carregar();
    aviso(`${r.novos} senha(s) importadas${r.repetidos ? `, ${r.repetidos} repetidas ignoradas` : ""}. ` +
          `APAGUE o arquivo ${r.arquivo} — ele guarda suas senhas sem proteção!`, "alerta");
  });

  const formEditor = $("#form-editor");
  formEditor.elements.senha.addEventListener("input", atualizarForcaEditor);
  $("#bt-gerar-editor").addEventListener("click", async () => {
    formEditor.elements.senha.value = await api.gerar({});
    formEditor.elements.senha.type = "text";
    atualizarForcaEditor();
  });
  $("#modal-editor").addEventListener("close", () => {
    if ($("#modal-editor").returnValue === "salvar") salvarEditor();
  });

  $("#bt-ajustes").addEventListener("click", abrirAjustes);
  $("#modal-ajustes").addEventListener("close", async () => {
    if ($("#modal-ajustes").returnValue !== "salvar") return;
    const f = $("#form-ajustes").elements;
    estado.prefs = await api.salvar_preferencias({
      bloqueio_minutos: +f.bloqueio_minutos.value, limpar_copia_segundos: +f.limpar_copia_segundos.value });
    aviso("Ajustes salvos.", "ok");
  });
  $("#bt-trocar-senha").addEventListener("click", async () => {
    const f = $("#form-ajustes").elements;
    const r = await api.trocar_senha(f.atual.value, f.nova.value, f.confirmacao.value);
    f.atual.value = f.nova.value = f.confirmacao.value = "";
    aviso(r.ok ? "Senha mestra trocada. O cofre foi recifrado com uma chave nova." : r.erro, r.ok ? "ok" : "erro");
  });
  $("#bt-backup").addEventListener("click", async () => {
    const r = await api.backup();
    if (!r.cancelado) aviso(r.ok ? `Cópia salva em ${r.arquivo}` : r.erro, r.ok ? "ok" : "erro");
  });

  $("#escolher-busca").addEventListener("input", desenharEscolhas);
  $("#bt-tela-cheia").addEventListener("click", () => api && api.alternar_tela_cheia());
  $("#bt-sair").addEventListener("click", () => api && api.sair());
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "F11" && api) { ev.preventDefault(); api.alternar_tela_cheia(); }
  });

  for (const ev of ["mousemove", "keydown", "click", "wheel"]) document.addEventListener(ev, marcarAtividade, { passive: true });
  document.addEventListener("keydown", (ev) => {
    if (!document.body.classList.contains("desbloqueado") || $("dialog[open]")) return;
    const tecla = ev.key.toLowerCase();
    if (ev.ctrlKey && tecla === "f") { ev.preventDefault(); $("#busca").focus(); }
    else if (ev.ctrlKey && tecla === "n") { ev.preventDefault(); abrirEditor(); }
    else if (ev.ctrlKey && tecla === "l") { ev.preventDefault(); bloquear(""); }
  });
  relogioBloqueio();
}

/* Chamado pelo Python (cofre.py) */
window.app = {
  aviso,
  escolherParaJanela,
  bloqueadoPorInatividade: () => voltarAoLogin("BLOQUEADO POR INATIVIDADE."),
};

ligarEventos();
if (window.pywebview && window.pywebview.api) iniciar();
else window.addEventListener("pywebviewready", iniciar);
