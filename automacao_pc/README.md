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

Dê dois cliques em **`SPARTA.bat`**. Ele abre em **tela cheia** no Windows Terminal, mostra uma abertura animada (painéis estilo tmux com dados reais do PC; qualquer tecla pula) e depois o menu numerado. Esse é o jeito mais fácil.
Para desligar a abertura: `"abertura": false` no `config.json`.
Na primeira vez ele cria o `config.json`. **Abra esse arquivo no Bloco de Notas e ajuste para o seu PC** (pastas, discos, programas).

> Tudo que mexe em arquivos mostra primeiro uma **prévia** e só aplica com `--executar` (ou quando você responde "s" no menu).
> Movimentações podem ser desfeitas com `py pc.py desfazer`.

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

Comandos: `/status`, `/desligar [min]`, `/reiniciar [min]`, `/cancelar`, `/hibernar`, `/bloquear`, `/limpar`, `/discos`.
Mensagens de qualquer ID fora da lista são ignoradas. Comandos enviados com o PC desligado são descartados, para um `/desligar` antigo não desligar o PC assim que ele ligar.

> **Ligar** o PC remotamente não dá por aqui: desligado, ele não recebe mensagens. Para isso existe o *Wake-on-LAN*, que depende da placa-mãe e do roteador.
> O token fica em texto no `config.json`. Não compartilhe esse arquivo. Ele já está fora do Git.

---

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
