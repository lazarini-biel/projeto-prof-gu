# SPARTA

Duas coisas para o seu Windows 11:

| | O que faz |
|---|---|
| **`pc.py`** — central de automações | Organiza Downloads, acha duplicados, redistribui arquivos entre HDs/SSDs, limpa temporários, abre seus programas ao ligar, desliga/reinicia (até pelo celular) e agenda tudo isso sozinho. |
| **`cofre/`** — gerenciador de senhas | App com login estilo filme de espião. Senhas cifradas com AES-256, roda direto do pendrive e preenche o login no navegador com **Ctrl+Alt+A**. |

---

## 1. Instalação (uma vez)

1. Instale o **Python** em <https://www.python.org/downloads/>. Na primeira tela do instalador, marque **"Add python.exe to PATH"**.
   Use o instalador do site, não a versão da Microsoft Store: as tarefas automáticas não funcionam bem com a da Store.
2. Copie esta pasta `automacao_pc` para um lugar fixo, ex.: `C:\Ferramentas\automacao_pc`.
3. Só para o cofre: abra o Terminal nessa pasta e rode
   ```
   py -m pip install -r requirements.txt
   ```

## 2. A central (`pc.py`)

Dê dois cliques em **`SPARTA.bat`**. Ele abre em **tela cheia** no Windows Terminal, mostra uma abertura animada e depois o menu numerado. Esse é o jeito mais fácil.

**A abertura** tem duas partes: primeiro **várias janelas de CMD de verdade** abrem espalhadas pela tela, com texto vermelho correndo (estilo filme de hacker); depois elas **se fecham sozinhas** e aparece um **painel** com dados reais do PC. A quantidade de CMDs é limitada (no máximo 30), não é um "fork bomb". Qualquer tecla pula o painel. Controles no `config.json`:
- `"abertura": true/false` — liga/desliga a abertura inteira.
- `"cmds_reais": true/false` — abrir CMDs de verdade. Se `false` (ou fora do Windows), usa uma versão "desenhada" das janelas, sem abrir nada.
- `"cmds_qtd": 18` — quantas janelas de CMD abrir (teto de 30).
- `"cmds_segundos": 7` — quanto tempo os CMDs ficam na tela antes de fechar.
- `"abertura_segundos": 14` — quanto tempo o painel dura depois (pode pôr 20, 30...).
Na primeira vez ele cria o `config.json`. **Abra esse arquivo no Bloco de Notas e ajuste para o seu PC** (pastas, discos, programas).

> Tudo que mexe em arquivos mostra primeiro uma **prévia** e só aplica com `--executar` (ou quando você responde "s" no menu).
> Movimentações podem ser desfeitas com `py pc.py desfazer`.

### Temperaturas
```
py pc.py temp
```
Mostra CPU/GPU/placa quando o Windows informa. Para temperaturas detalhadas, deixe o **LibreHardwareMonitor** (gratuito) aberto.

### Programas que abrem com o Windows
```
py pc.py inicializar                 lista o que abre no logon
py pc.py inicializar desativar 3     desativa o item 3 (dá para reativar)
py pc.py inicializar ativar 1
```
Desativar guarda um backup, então nada é perdido. Itens "[HKLM]" (de todos os usuários) exigem rodar como administrador.

### Modos de foco
```
py pc.py foco            lista os modos
py pc.py foco estudo
py pc.py foco dormir
```
Cada modo fecha os programas que atrapalham (e pode abrir sites ou programar o desligamento). Crie os seus em `config.json` > `foco`. O modo "dormir" usa `"fechar": ["*"]` para fechar tudo em segundo plano (menos o essencial do Windows).

### Atualizar programas
```
py pc.py atualizar               mostra o que tem atualização
py pc.py atualizar --executar     atualiza tudo (winget)
```

### Limpar Downloads antigos
```
py pc.py downloads                prévia dos arquivos com mais de 30 dias
py pc.py downloads --executar     manda para a Lixeira
```
Ajuste os dias em `config.json` > `limpeza` > `downloads_antigos_dias`. Há uma tarefa agendada pronta (desligada por padrão) em `agendamentos`.

### Liberar memória / fechar programas
```
py pc.py fechar
```
Lista os programas que mais usam memória (sem os do Windows) e fecha os que você escolher. Os pesados de segundo plano ganham um aviso "⚠ dá para fechar".

### Testar internet
```
py pc.py internet
```
Mede ping e velocidade de download e guarda um histórico das últimas medições.

### Dispositivos na rede
```
py pc.py rede
```
Lista os aparelhos que seu PC enxergou na rede local (IP e MAC).

### Clima e notícias
```
py pc.py clima
```
Mostra a previsão de hoje (descobre a cidade pelo seu IP, ou fixe em `config.json` > `clima`) e as manchetes do dia. Uma linha curta (clima + 1 manchete) aparece na abertura do menu; desligue com `"na_abertura": false`.

### Lembretes / notas
```
py pc.py notas                 lista as notas
py pc.py notas add "comprar HD"
py pc.py notas rm 2
```
Notas rápidas salvas só no seu PC (notas.json).

### Painel do PC no navegador
```
py pc.py painel
```
Abre no navegador um **painel ao vivo** do PC (CPU, memória, discos, processos, bateria) no tema vermelho — bem mais bonito que o terminal. Roda um servidor só no seu PC (127.0.0.1); feche a aba e dê Ctrl+C para parar.

### Top processos
```
py pc.py top
```
Uso de CPU e RAM agora, e os programas que mais consomem memória.

### Espaço por pasta
```
py pc.py discos pastas            as pastas que mais enchem o disco
py pc.py discos pastas D:/ C:/Users
```
Mostra muitas pastas ordenadas por tamanho. Ajuste em `config.json` > `espaco_pastas` (onde procurar, quantas mostrar, tamanho mínimo).

### Ver informações do PC
```
py pc.py sistema
```
Mostra um painel em vermelho com: sistema, processador e núcleos, placa de vídeo, placa-mãe, memória (com barra), tempo ligado, IP local, bateria (em notebooks) e os discos. Só leitura.

### Organizar Downloads
```
py pc.py organizar              prévia
py pc.py organizar --executar   aplica
```
Separa os arquivos em `PDFs`, `Imagens`, `Instaladores`, `Planilhas`, `Vídeos`, `Compactados`…
Não mexe em downloads em andamento nem em arquivos baixados nos últimos 10 minutos.
Para criar suas próprias categorias, use `categorias_extras` no config.

### Duplicados (liberar espaço)
```
py pc.py duplicados                    lista o que está repetido (não apaga nada)
py pc.py duplicados --acao lixeira     manda as cópias para a Lixeira (dá para recuperar)
py pc.py duplicados --acao excluir     apaga de vez (pede confirmação)
py pc.py duplicados D:/ E:/Fotos       varre outras pastas/discos
```
- Compara o **conteúdo**, então acha cópias mesmo com nomes diferentes (`foto.jpg` e `foto (1).jpg`).
- Em cada grupo **mantém uma** cópia: a que está nas pastas de `preferir_manter_em`; se nenhuma estiver lá, a mais antiga.
- A lista completa vai para `logs/duplicados_*.csv`, que abre no Excel.
- Nunca varre pastas de sistema/programas (Windows, Program Files, AppData, Steam…).

### Discos: espaço e redistribuição
```
py pc.py discos                              espaço livre de cada disco
py pc.py discos maiores C:/Users --top 40    os maiores arquivos
py pc.py discos redistribuir                 plano: o que iria para onde
py pc.py discos redistribuir --executar      aplica
```
Em `redistribuir` > `destinos` você diz para onde vai cada tipo, ex.: vídeos → `E:/Vídeos`, fotos → `D:/Fotos`.
O que não estiver na lista fica onde está. Proteções:
- só mexe nas pastas de `origens` (Área de Trabalho, Documentos, Downloads…), nunca em programas;
- pula arquivos alterados nos últimos 7 dias;
- não enche o disco de destino: deixa 10% livre;
- pula pastas do OneDrive (mover tiraria os arquivos da nuvem).

💡 **Dica complementar:** para que *novos* arquivos já nasçam no outro disco, mova as pastas do Windows.
Clique com o botão direito em **Imagens** (ou Vídeos, Músicas) → **Propriedades** → aba **Local** → **Mover…** → escolha `D:\Imagens`.

### Limpeza
```
py pc.py limpar                   prévia de quanto dá para liberar
py pc.py limpar --executar        limpa
py pc.py limpar --executar --lixeira          também esvazia a Lixeira
py pc.py limpar --executar --sistema          + pastas do Windows (como administrador)
```
Limpa temporários e caches do Chrome, Edge, Firefox, Brave, Opera e Vivaldi. Só apaga arquivos com mais de 24 h.
Cache de navegador só é limpo com o navegador **fechado**. O Edge costuma ficar aberto em segundo plano; se ele for sempre pulado, desative em Edge → Configurações → Sistema → "Aumento de inicialização".

### Abrir programas e sites
No config, em `inicio`, cada **perfil** tem `programas`, `sites` (com o navegador de cada um) e `pastas`:
```
py pc.py iniciar              perfil "padrao"
py pc.py iniciar trabalho     outro perfil
```
Para descobrir o caminho de um programa: botão direito no atalho → **Abrir local do arquivo** → botão direito no `.exe` → **Copiar como caminho**. Troque `\` por `/` ao colar no config.

### Desligar / reiniciar
```
py pc.py energia desligar --em 30     desliga em 30 min (o Windows avisa)
py pc.py energia reiniciar --em 5
py pc.py energia cancelar
py pc.py energia hibernar | bloquear
```

### Tudo automático (Agendador de Tarefas)
Ajuste a lista `agendamentos` no config (`"ativo": true/false`) e rode:
```
py pc.py agendar instalar     cria/atualiza as tarefas (pede permissão de administrador)
py pc.py agendar listar
py pc.py agendar remover
```
`quando` pode ser `logon` (ao entrar no Windows), `diario` + `hora`, `semanal` + `dias` (`dom, seg, ter, qua, qui, sex, sab`) + `hora`, ou `a_cada_horas` + `horas`.
As tarefas rodam sem janela; o que elas fazem fica em `logs/sparta.log`.
Se o PC estiver desligado no horário, a tarefa roda quando ele ligar. A exceção é desligar/reiniciar, para o PC não desligar assim que você o liga.

### Controle remoto pelo celular (Telegram)
Desligue, reinicie, bloqueie ou veja o estado do PC de qualquer lugar. Não precisa abrir porta no roteador.

1. No Telegram, procure **@BotFather** → `/newbot` → escolha um nome. Ele te dá um **token** (algo como `123456:ABC-...`).
2. Cole o token em `config.json` → `remoto` → `token`.
3. Rode `py pc.py remoto` e mande `/start` para o seu bot. Ele responde com o **seu ID**.
4. Coloque esse número em `ids_autorizados` (ex.: `"ids_autorizados": [123456789]`) e rode de novo.
5. Para ficar sempre ligado: em `agendamentos`, ative `"Controle remoto Telegram"` e rode `py pc.py agendar instalar`.

Comandos: `/status`, `/desligar [min]`, `/reiniciar [min]`, `/cancelar`, `/hibernar`, `/bloquear`, `/limpar`, `/discos`, `/top`, `/ip`, `/sistema`.
Mensagens de qualquer ID fora da lista são ignoradas. Comandos enviados com o PC desligado são descartados, para um `/desligar` antigo não desligar o PC assim que ele ligar.

> **Ligar** o PC remotamente não dá por aqui: desligado, ele não recebe mensagens. Para isso existe o *Wake-on-LAN*, que depende da placa-mãe e do roteador.
> O token fica em texto no `config.json`. Não compartilhe esse arquivo. Ele já está fora do Git.

---

## O Explorador de arquivos
```
Dois cliques em explorador/Explorador.bat   (ou: py pc.py explorador)
```
Um explorador no estilo SPARTA (vermelho), ligado ao Windows: navegar pelos discos e pastas, **filtrar/colorir por categoria**, **organizar a pasta por tipo** num clique, **renomear**, **mover**, **excluir** (vai para a Lixeira), criar pasta e **buscar**. Clique duplo abre o arquivo no programa padrão. **F11** alterna tela cheia.

Para levar como atalho/.exe: `explorador/gerar_exe.bat`.

## O Mixer de volume
```
Dois cliques em mixer/Mixer.bat   (ou: py pc.py mixer)
```
Um mixer estilo mesa de som (vermelho): **volume por aplicativo**, **volume geral** e **mudo**, cada um no seu fader. Precisa das bibliotecas de áudio uma vez: `py -m pip install pycaw comtypes`.

**Passar de 100%** (boost): o Windows não deixa por software puro, então o SPARTA controla o **Equalizer APO** (gratuito). Instale-o uma vez (o botão no mixer abre a página) e o controle BOOST de cada canal passa a funcionar acima de 100%. Mudanças no boost podem exigir rodar o SPARTA como administrador (o Equalizer APO fica em Arquivos de Programas).

## 3. O COFRE (senhas)

```
Dois cliques em cofre/Cofre.bat        (ou: py cofre/cofre.py)
```
Abre em **tela cheia** com uma abertura animada: janelas de terminal digitando o próprio código do cofre. Qualquer tecla ou clique pula. Depois aparece o painel de login.
Na primeira vez ele pede para você **criar a senha mestra**, depois sempre pede para desbloquear.
**F11** alterna tela cheia/janela, e o **✕** no canto fecha. Opções: `py cofre/cofre.py --sem-abertura --janela`.

### Levar no pendrive
1. Dê dois cliques em **`cofre/gerar_exe.bat`**. Ele gera `cofre/dist/Cofre.exe`, um arquivo só.
2. Copie o `Cofre.exe` para o pendrive. O `cofre.dat` (suas senhas cifradas) é criado **ao lado do .exe**.
3. Em qualquer Windows 10/11, é só abrir o `Cofre.exe` do pendrive. Nada é instalado no PC.

Se você já tem um cofre, copie o `cofre.dat` para junto do `Cofre.exe`.

### Preenchimento automático (Ctrl+Alt+A)
Com o cofre desbloqueado:
1. Abra a página de login no navegador e **clique no campo de usuário**.
2. Aperte **Ctrl+Alt+A**.
3. O cofre vê qual janela/site está na frente (Chrome, Edge, Firefox, Brave, Opera… ou qualquer programa) e digita **usuário → Tab → senha → Enter**.

Se ele não tiver certeza de qual login usar, mostra uma lista. Escolha uma vez e marque "lembrar". Da próxima vez ele reconhece sozinho.

Também dá para clicar em **⚡ Abrir e preencher**: ele abre o site no navegador escolhido para aquele login e digita sozinho quando a página aparecer.

Sites com login em **duas telas** (usuário → Avançar → senha, como o Google e o gov.br): edite o registro e use a sequência
`{USUARIO}{ENTER}{ESPERA:2500}{SENHA}{ENTER}`.

Antes de cada tecla, o cofre confere se a janela ativa ainda é a mesma. Se você trocar de janela no meio, ele **para** e não digita a senha no lugar errado.

### Importar as senhas do navegador
- **Chrome / Edge / Brave / Opera:** Configurações → Senhas (Gerenciador de senhas) → Exportar senhas → `.csv`
- **Firefox:** Senhas → menu `⋯` → Exportar senhas

No cofre: **⇪ Importar** → escolha o `.csv`. Depois **apague o .csv**, porque ele guarda tudo sem proteção.

### Segurança: como funciona
- Senha mestra → **scrypt** (N=2¹⁷, r=8; ~0,5 s e 128 MB por tentativa) → chave de 256 bits → dados cifrados com **AES-256-GCM**. São algoritmos padrão, via biblioteca `cryptography`. Nada de criptografia "caseira".
- O `cofre.dat` é ilegível sem a senha mestra, e qualquer alteração no arquivo é detectada.
- Cada salvamento é atômico: arrancar o pendrive no meio não corrompe o cofre. A versão anterior fica em `cofre.dat.bak`.
- Bloqueia sozinho após 5 min sem uso (ajustável). Senha copiada some da área de transferência em 20 s e **não** vai para o histórico do Win+V nem para a nuvem.
- Errar a senha várias vezes gera espera crescente entre tentativas.

### ⚠️ Leia antes de confiar suas senhas
- **Esqueceu a senha mestra = perdeu tudo.** Não existe recuperação, por design. Use uma frase longa que você não esquece (ex.: `cafe-forte-na-varanda-1987`).
- **Faça backup do `cofre.dat`** (⚙ → "Salvar cópia de segurança em…") em outro lugar. Pendrive se perde e queima.
- **PC dos outros:** se a máquina tiver vírus/keylogger, ele pode capturar a senha mestra quando você digita. Use o cofre do pendrive só em computadores em que você confia.
- Este é um projeto pessoal, não auditado por especialistas. Se você quiser algo do mesmo tipo já auditado e com extensão de navegador, o **KeePassXC** (gratuito, tem versão portátil) é a referência. Dá para usar os dois.

---

## Testes (para quem for mexer no código)
```
py -m unittest discover -s testes
```

## Estrutura
```
automacao_pc/
├── pc.py                  central (menu e linha de comando)
├── SPARTA.bat             atalho de dois cliques
├── config.exemplo.json    modelo de configuração
├── ferramentas/           organizar, duplicados, discos, limpeza, início,
│                          energia, agendador, remoto (Telegram), navegadores
├── cofre/
│   ├── cofre.py           app (janela + ponte com a tela)
│   ├── nucleo.py          criptografia e dados
│   ├── autotipo.py        Ctrl+Alt+A, digitação e área de transferência
│   ├── ui/                tela (HTML/CSS/JS)
│   ├── Cofre.bat          abrir sem console
│   └── gerar_exe.bat      gera o Cofre.exe portátil
└── testes/
```
