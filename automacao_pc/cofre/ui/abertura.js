"use strict";
/*
 * Abertura do COFRE (estilo "rice" / filme): dezenas de janelas de CMD em
 * vermelho surgem por toda a tela digitando código e fluxos de caracteres,
 * vivem alguns segundos e somem, enquanto outras aparecem. Ao mesmo tempo,
 * um conjunto de janelas fixas vai montando, como um quebra-cabeça, o elmo
 * da SPARTA. No fim a tela "desliga" como um monitor antigo e aparece o
 * login. Qualquer tecla ou clique pula.
 *
 * Uso: await window.abertura(fontes)   // fontes = [{nome, texto}, ...]
 */
(function () {
  const DUR_STORM = 12000;     // tempestade de pop-ups enchendo a tela
  const DUR_LOGO = 2600;       // segura o elmo montado
  const TITULOS = ["organizar.py", "duplicados.py", "discos.py", "limpeza.py",
    "inicio.py", "energia.py", "agendador.py", "remoto.py", "navegadores.py",
    "cofre.py", "nucleo.py", "autotipo.py", "util.py", "pc.py"];
  const SIMBOLOS = "0123456789ABCDEFabcdef<>{}[]()=+-*/\\|:;.,#$%&@?!^~";

  /* -------------------------------------------------- máscara do elmo */
  const _FONTE = {
    S: [" ███", "█   ", " ██ ", "   █", "███ "], P: ["███ ", "█  █", "███ ", "█   ", "█   "],
    A: [" ██ ", "█  █", "████", "█  █", "█  █"], R: ["███ ", "█  █", "███ ", "█ █ ", "█  █"],
    T: ["███", " █ ", " █ ", " █ ", " █ "],
  };
  function intensidade(x, y) {
    const ax = Math.abs(x);
    if (y < 0.30) {                                   // crista
      const w = 0.24 * Math.sin(Math.PI * (y / 0.30)) ** 0.65;
      if (ax < Math.max(w, 0.028)) return 1.0;
    }
    if (y >= 0.22 && y <= 0.32 && ax < 0.13) return 1.0;
    if ((x / 0.66) ** 2 + ((y - 0.52) / 0.30) ** 2 <= 1.0 && y >= 0.26 && y <= 0.56) return 1.0;
    if (y >= 0.50 && y <= 0.575 && ax < 0.52) return 1.0;
    if (y >= 0.50 && y <= 1.0) {                       // bochechas
      const f = (y - 0.50) / 0.50;
      if (ax >= 0.46 - 0.30 * f && ax <= 0.62 - 0.46 * f) return 1.0;
    }
    if (y >= 0.52 && y <= 0.90 && ax < 0.055) return 1.0;   // nariz
    if (y >= 0.56 && y <= 0.70) {                      // sobrancelha brava
      const t = (y - 0.56) / 0.14;
      if (ax > 0.055 && ax < 0.055 + 0.30 * (1 - t)) return 1.0;
    }
    return 0.0;
  }
  function elmoMascara(w, h) {
    const g = [];
    for (let ly = 0; ly < h; ly++) {
      const row = [], y = ly / (h - 1);
      for (let lx = 0; lx < w; lx++) row.push(intensidade((lx / (w - 1)) * 2 - 1, y));
      g.push(row);
    }
    const orig = g.map((r) => r.slice());
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      if (orig[y][x] <= 0) continue;
      const borda = [[-1, 0], [1, 0], [0, -1], [0, 1]].some(
        ([dy, dx]) => !(orig[y + dy] && orig[y + dy][x + dx] > 0));
      g[y][x] = borda ? 1.0 : 0.72;
    }
    return g;
  }
  function palavraLinhas() {
    return [0, 1, 2, 3, 4].map((i) => "SPARTA".split("").map((c) => _FONTE[c][i]).join("  "));
  }
  function cartaz(cols, rows) {
    const g = Array.from({ length: rows }, () => new Array(cols).fill(0));
    const palavra = palavraLinhas(), espaco = palavra.length + 1;
    let hb = Math.max(8, Math.min(rows - espaco, Math.floor(cols / 2)));
    let wb = Math.min(cols, hb * 2);
    hb = Math.min(hb, Math.floor(wb / 2));
    if (hb < 6) return g;
    const m = elmoMascara(wb, hb);
    const ox = Math.floor((cols - wb) / 2), oy = Math.max(0, Math.floor((rows - hb - espaco) / 2));
    for (let y = 0; y < hb; y++) for (let x = 0; x < wb; x++)
      if (oy + y < rows && ox + x < cols) g[oy + y][ox + x] = m[y][x];
    const pl = palavra[0].length, px = Math.floor((cols - pl) / 2), py = oy + hb + 1;
    palavra.forEach((linha, i) => {
      for (let j = 0; j < linha.length; j++)
        if (linha[j] !== " " && g[py + i] && px + j < cols) g[py + i][px + j] = 1.5;
    });
    return g;
  }

  /* ------------------------------------------------------- janelas */
  function moldura(x, y, w, h, titulo, z, fixa) {
    const j = document.createElement("div");
    j.className = "janela-cmd" + (fixa ? " logo" : "");
    Object.assign(j.style, { left: x + "%", top: y + "%", width: w + "%", height: h + "%", zIndex: z });
    const barra = document.createElement("div");
    barra.className = "barra-titulo";
    const t = document.createElement("span");
    t.textContent = "■ C:\\SPARTA\\" + titulo;
    const b = document.createElement("span");
    b.className = "botoes-titulo";
    b.textContent = "_ □ ✕";
    barra.append(t, b);
    const pre = document.createElement("pre");
    j.append(barra, pre);
    return { el: j, pre };
  }

  function janelaFluxo(palco, pos, fonte, z) {
    const { el, pre } = moldura(pos.x, pos.y, pos.l, pos.a, fonte.nome, z, false);
    palco.append(el);
    let texto, pos0 = 0, modo;
    if (fonte.texto) {
      modo = "codigo";
      let ini = Math.floor(Math.random() * Math.max(1, fonte.texto.length - 4000));
      ini = fonte.texto.indexOf("\n", ini) + 1;
      texto = fonte.texto.slice(ini) + "\n" + fonte.texto;
    } else {
      modo = "fluxo";
    }
    let ultimoFluxo = 0;
    return {
      el, nascimento: performance.now(),
      tick(agora) {
        if (modo === "codigo") {
          pos0 = Math.min(texto.length, pos0 + 20 + ((Math.random() * 12) | 0));
          pre.textContent = texto.slice(Math.max(0, pos0 - 4000), pos0) + "█";
          pre.scrollTop = pre.scrollHeight;
        } else if (agora - ultimoFluxo > 70) {      // fluxo: ~14x/s, mais leve
          ultimoFluxo = agora;
          const linhas = [];
          for (let i = 0; i < 44; i++) {
            let s = "";
            for (let k = 0; k < 90; k++) s += SIMBOLOS[(Math.random() * SIMBOLOS.length) | 0];
            linhas.push(s);
          }
          pre.textContent = linhas.join("\n");
        }
      },
    };
  }

  function janelaLogo(palco, pos, slice, z) {
    const { el, pre } = moldura(pos.x, pos.y, pos.l, pos.a, pos.titulo, z, true);
    // font-size para a fatia caber na largura da janela
    const cols = slice[0].length;
    el.style.setProperty("--cols", cols);
    palco.append(el);
    let montado = false;
    return {
      el, logo: true, nascimento: performance.now(),
      tick(agora) {
        const vivo = (agora - this.nascimento) / 600;
        if (montado) return;
        const frag = [];
        for (let r = 0; r < slice.length; r++) {
          for (let c = 0; c < slice[r].length; c++) {
            const v = slice[r][c];
            if (v <= 0) { frag.push(Math.random() < 0.05 ? "·" : " "); continue; }
            if (Math.random() > Math.min(1, vivo)) { frag.push(" "); continue; }
            if (v >= 1.4) frag.push(`<b class="w">█</b>`);
            else if (v >= 0.9) frag.push(`<b class="e">${"██▓@#"[(Math.random() * 5) | 0]}</b>`);
            else frag.push(`<b class="f">${"▓▒#%&8B"[(Math.random() * 7) | 0]}</b>`);
          }
          frag.push("\n");
        }
        pre.innerHTML = frag.join("");
        if (vivo >= 1) montado = true;   // congela quando montado (barato)
      },
    };
  }

  /* ---------------------------------------------- posições aleatórias */
  function posStorm() {
    const l = 20 + Math.random() * 22, a = 24 + Math.random() * 26;
    return { x: Math.random() * (100 - l), y: 4 + Math.random() * (92 - a), l, a };
  }
  function gradeLogo() {
    const cols = 4, linhas = 4, areaL = 46, areaA = 80;
    const x0 = (100 - areaL) / 2, y0 = (100 - areaA) / 2;
    const cw = 15, ch = 8;                       // chars por janela (interior)
    const mascara = cartaz(cols * cw, linhas * ch);   // elmo proporcionado + SPARTA
    const janelas = [];
    const ordem = [];
    for (let r = 0; r < linhas; r++) for (let c = 0; c < cols; c++) ordem.push([c, r]);
    for (let i = ordem.length - 1; i > 0; i--) {   // embaralha a ordem de encaixe
      const j = (Math.random() * (i + 1)) | 0;[ordem[i], ordem[j]] = [ordem[j], ordem[i]];
    }
    ordem.forEach(([c, r], k) => {
      const slice = mascara.slice(r * ch, r * ch + ch).map((row) => row.slice(c * cw, c * cw + cw));
      janelas.push({
        pos: {
          x: x0 + (areaL / cols) * c, y: y0 + (areaA / linhas) * r,
          l: areaL / cols, a: areaA / linhas, titulo: TITULOS[k % TITULOS.length],
        },
        slice, nasce: 2600 + k * ((DUR_STORM - 3500) / (cols * linhas)),
      });
    });
    return janelas;
  }

  /* ------------------------------------------------------------ run */
  window.abertura = function (fontes) {
    return new Promise((resolver) => {
      const camada = document.createElement("div");
      camada.id = "abertura";
      const palco = document.createElement("div");
      palco.className = "palco";
      const rodape = document.createElement("div");
      rodape.className = "abertura-rodape";
      camada.append(palco, rodape);
      document.body.append(camada);

      fontes = fontes && fontes.length ? fontes : [{ nome: "sparta", texto: "" }];
      const logos = gradeLogo();
      const logosVivos = [];
      let comuns = [];
      let proximaComum = 0, z = 10, logoIdx = 0;
      const inicio = performance.now();
      let terminou = false, raf = 0;

      const finalizar = async () => {
        if (terminou) return;
        terminou = true;
        cancelAnimationFrame(raf);
        removeEventListener("keydown", pular, true);
        camada.removeEventListener("click", pular);
        camada.classList.add("tremendo");
        await new Promise((r) => setTimeout(r, 380));
        palco.classList.add("desligando");
        rodape.classList.add("escondido");
        await new Promise((r) => setTimeout(r, 520));
        camada.classList.add("sumindo");
        await new Promise((r) => setTimeout(r, 360));
        camada.remove();
        resolver();
      };
      const pular = (ev) => { ev.preventDefault(); ev.stopPropagation(); finalizar(); };
      addEventListener("keydown", pular, true);
      camada.addEventListener("click", pular);

      const quadro = (agora) => {
        if (terminou) return;
        const t = agora - inicio;
        // nasce uma janela comum com frequência, enchendo a tela
        if (t < DUR_STORM && t >= proximaComum) {
          const fonte = Math.random() < 0.4
            ? fontes[(Math.random() * fontes.length) | 0]
            : { nome: TITULOS[(Math.random() * TITULOS.length) | 0], texto: "" };
          const j = janelaFluxo(palco, posStorm(), fonte, z++);
          j.vida = 7000 + Math.random() * 2500;     // cada pop-up vive >= 7s
          comuns.push(j);
          proximaComum = t + 380 + Math.random() * 420;
        }
        // nascem as janelas de logo, uma a uma (quebra-cabeça)
        while (logoIdx < logos.length && t >= logos[logoIdx].nasce) {
          const spec = logos[logoIdx++];
          logosVivos.push(janelaLogo(palco, spec.pos, spec.slice, 500 + logoIdx));
        }
        // mortes das comuns + fade final
        const fade = t < DUR_STORM ? 1 : Math.max(0, 1 - (t - DUR_STORM) / 1000);
        comuns = comuns.filter((j) => {
          const vivo = agora - j.nascimento < j.vida;
          if (!vivo || fade <= 0) { j.el.remove(); return false; }
          j.el.style.opacity = fade;
          j.tick(agora);
          return true;
        });
        for (const j of logosVivos) j.tick(agora);

        const pct = Math.min(100, Math.round((t / (DUR_STORM + DUR_LOGO)) * 100));
        rodape.textContent = `SPARTA // montando cofre  [${"█".repeat(pct / 5)}${"░".repeat(20 - (pct / 5 | 0))}]  ${pct}%   ·   qualquer tecla pula`;
        if (t >= DUR_STORM + DUR_LOGO) finalizar();
        else raf = requestAnimationFrame(quadro);
      };
      raf = requestAnimationFrame(quadro);
    });
  };
})();
