"use strict";
/*
 * Abertura do COFRE: janelas de terminal surgem uma sobre a outra digitando
 * código (o próprio código-fonte do cofre), tremem e a tela "desliga" como um
 * monitor antigo, revelando a tela de login. Qualquer tecla ou clique pula.
 *
 * Uso: await window.abertura(fontes)   // fontes = [{nome, texto}, ...]
 */
(function () {
  const ROTEIRO = [   // quando surge (ms), posição/tamanho em % da tela
    { t: 0, x: 3, y: 4, l: 52, a: 56 },
    { t: 650, x: 55, y: 10, l: 40, a: 44 },
    { t: 1300, x: 22, y: 46, l: 46, a: 50 },
    { t: 1900, x: 64, y: 52, l: 33, a: 42 },
    { t: 2450, x: 8, y: 60, l: 30, a: 36 },
    { t: 2900, x: 40, y: 24, l: 30, a: 34 },
  ];
  const DURACAO = 4300;
  const CARACTERES_POR_QUADRO = 22;

  function criarJanela(palco, posicao, fonte, indice) {
    const janela = document.createElement("div");
    janela.className = "janela-cmd";
    Object.assign(janela.style, {
      left: posicao.x + "%", top: posicao.y + "%", width: posicao.l + "%", height: posicao.a + "%",
      zIndex: String(10 + indice),
    });
    const barra = document.createElement("div");
    barra.className = "barra-titulo";
    const titulo = document.createElement("span");
    titulo.textContent = `C:\\COFRE\\${fonte.nome} — cmd.exe`;
    const botoes = document.createElement("span");
    botoes.className = "botoes-titulo";
    for (const b of ["_", "□", "×"]) {
      const s = document.createElement("i");
      s.textContent = b;
      botoes.append(s);
    }
    barra.append(titulo, botoes);
    const tela = document.createElement("pre");
    janela.append(barra, tela);
    palco.append(janela);

    // Começa num ponto aleatório do arquivo, no início de uma linha.
    const texto = fonte.texto;
    let inicio = Math.floor(Math.random() * Math.max(1, texto.length - 4000));
    inicio = texto.indexOf("\n", inicio) + 1;
    return { tela, texto: texto.slice(inicio) + "\n" + texto, pos: 0 };
  }

  window.abertura = function (fontes) {
    return new Promise((resolver) => {
      if (!fontes || !fontes.length) return resolver();
      const camada = document.createElement("div");
      camada.id = "abertura";
      const palco = document.createElement("div");
      palco.className = "palco";
      const rodape = document.createElement("div");
      rodape.className = "abertura-rodape";
      camada.append(palco, rodape);
      document.body.append(camada);

      const janelas = [];
      const inicio = performance.now();
      let terminou = false;

      const finalizar = async () => {
        if (terminou) return;
        terminou = true;
        removeEventListener("keydown", pular, true);
        camada.removeEventListener("click", pular);
        camada.classList.add("tremendo");
        await new Promise((r) => setTimeout(r, 380));
        palco.classList.add("desligando");          // efeito de monitor de tubo apagando
        rodape.classList.add("escondido");
        await new Promise((r) => setTimeout(r, 520));
        camada.classList.add("sumindo");
        await new Promise((r) => setTimeout(r, 380));
        camada.remove();
        resolver();
      };
      const pular = (ev) => { ev.preventDefault(); ev.stopPropagation(); finalizar(); };
      addEventListener("keydown", pular, true);
      camada.addEventListener("click", pular);

      const quadro = (agora) => {
        if (terminou) return;
        const t = agora - inicio;
        while (janelas.length < ROTEIRO.length && ROTEIRO[janelas.length].t <= t) {
          const i = janelas.length;
          janelas.push(criarJanela(palco, ROTEIRO[i], fontes[i % fontes.length], i));
        }
        for (const j of janelas) {
          const fim = j.pos + CARACTERES_POR_QUADRO + Math.floor(Math.random() * 14);
          j.pos = Math.min(fim, j.texto.length);
          // Só as últimas ~120 linhas ficam no DOM; o texto "rola" sozinho.
          const visivel = j.texto.slice(Math.max(0, j.pos - 6000), j.pos);
          j.tela.textContent = visivel + "█";
          j.tela.scrollTop = j.tela.scrollHeight;
        }
        const pct = Math.min(100, Math.round((t / DURACAO) * 100));
        rodape.textContent = `CARREGANDO MÓDULOS DO COFRE  [${"█".repeat(pct / 5)}${"░".repeat(20 - pct / 5)}]  ${pct}%   ·   qualquer tecla pula`;
        if (t >= DURACAO) finalizar();
        else requestAnimationFrame(quadro);
      };
      requestAnimationFrame(quadro);
    });
  };
})();
