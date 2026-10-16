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
    if (y < 0.20) {
      const d = 0.12 * Math.sin((0.20 - y) * 6);
      if (Math.abs(x - d) < 0.11 + y * 0.25) return 1.0;
    }
    const dome = (x / 0.70) ** 2 + ((y - 0.46) / 0.42) ** 2;
    const naCupula = dome <= 1.0 && y >= 0.14 && y <= 0.5;
    if (y >= 0.42 && y <= 1.0) {
      const ext = 0.72 - 0.30 * (y - 0.42), intr = 0.34 - 0.06 * (y - 0.42);
      if (ax >= intr && ax <= ext) return 1.0;
    }
    if (y >= 0.44 && y <= 0.96 && ax < 0.085) return 1.0;
    if (y >= 0.40 && y <= 0.50 && ax < 0.52) return 1.0;
    return naCupula ? 1.0 : 0.0;
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
    const palavra = "SPARTA".split("").map((c) => _FONTE[c]);
    const linhas = 5, largura = palavra.reduce((s, l) => s + l[0].length + 2, -2);
    const px = Math.floor((w - largura) / 2), py = h - linhas - 1;
    palavra.forEach((letra, li) => {
      let off = 0;
      for (let k = 0; k < li; k++) off += palavra[k][0].length + 2;
      for (let r = 0; r < 5; r++) for (let c = 0; c < letra[r].length; c++)
        if (letra[r][c] !== " " && g[py + r] && px + off + c < w) g[py + r][px + off + c] = 1.5;
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
    const cols = 5, linhas = 3, areaL = 60, areaA = 66;
    const x0 = (100 - areaL) / 2, y0 = (100 - areaA) / 2;
    const cw = 16, ch = 9;                       // chars por janela (interior)
    const mascara = elmoMascara(cols * cw, linhas * ch);
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
