"use strict";
/*
 * Abertura do COFRE (estilo "rice" / filme): dezenas de janelas de CMD em
 * vermelho surgem por toda a tela digitando código e fluxos de caracteres,
 * vivem alguns segundos e somem, enquanto outras aparecem — enchendo a tela.
 * No fim a tela "desliga" como um monitor antigo e aparece o login.
 * Qualquer tecla ou clique pula.
 *
 * (O cofre é uma única janela, então não abre CMDs de verdade como a abertura
 *  do terminal; aqui as janelas são desenhadas na própria tela.)
 *
 * Uso: await window.abertura(fontes)   // fontes = [{nome, texto}, ...]
 */
(function () {
  const DUR_STORM = 10000;     // tempestade de pop-ups enchendo a tela
  const TITULOS = ["organizar.py", "duplicados.py", "discos.py", "limpeza.py",
    "inicio.py", "energia.py", "agendador.py", "remoto.py", "navegadores.py",
    "cofre.py", "nucleo.py", "autotipo.py", "util.py", "pc.py"];
  const SIMBOLOS = "0123456789ABCDEFabcdef<>{}[]()=+-*/\\|:;.,#$%&@?!^~";

  function moldura(x, y, w, h, titulo, z) {
    const j = document.createElement("div");
    j.className = "janela-cmd";
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
    const { el, pre } = moldura(pos.x, pos.y, pos.l, pos.a, fonte.nome, z);
    palco.append(el);
    let texto, pos0 = 0, modo, ultimoFluxo = 0;
    if (fonte.texto) {
      modo = "codigo";
      let ini = Math.floor(Math.random() * Math.max(1, fonte.texto.length - 4000));
      ini = fonte.texto.indexOf("\n", ini) + 1;
      texto = fonte.texto.slice(ini) + "\n" + fonte.texto;
    } else {
      modo = "fluxo";
    }
    return {
      el, nascimento: performance.now(),
      tick(agora) {
        if (modo === "codigo") {
          pos0 = Math.min(texto.length, pos0 + 20 + ((Math.random() * 12) | 0));
          pre.textContent = texto.slice(Math.max(0, pos0 - 4000), pos0) + "█";
          pre.scrollTop = pre.scrollHeight;
        } else if (agora - ultimoFluxo > 70) {
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

  function posStorm() {
    const l = 20 + Math.random() * 22, a = 24 + Math.random() * 26;
    return { x: Math.random() * (100 - l), y: 4 + Math.random() * (92 - a), l, a };
  }

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
      let comuns = [];
      let proximaComum = 0, z = 10;
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
        if (t < DUR_STORM && t >= proximaComum) {
          const fonte = Math.random() < 0.4
            ? fontes[(Math.random() * fontes.length) | 0]
            : { nome: TITULOS[(Math.random() * TITULOS.length) | 0], texto: "" };
          const j = janelaFluxo(palco, posStorm(), fonte, z++);
          j.vida = 7000 + Math.random() * 2500;     // cada pop-up vive >= 7s
          comuns.push(j);
          proximaComum = t + 320 + Math.random() * 380;
        }
        comuns = comuns.filter((j) => {
          if (agora - j.nascimento >= j.vida) { j.el.remove(); return false; }
          j.tick(agora);
          return true;
        });

        const pct = Math.min(100, Math.round((t / DUR_STORM) * 100));
        rodape.textContent = `SPARTA // abrindo terminais  [${"█".repeat(pct / 5)}${"░".repeat(20 - (pct / 5 | 0))}]  ${pct}%   ·   qualquer tecla pula`;
        if (t >= DUR_STORM) finalizar();
        else raf = requestAnimationFrame(quadro);
      };
      raf = requestAnimationFrame(quadro);
    });
  };
})();
