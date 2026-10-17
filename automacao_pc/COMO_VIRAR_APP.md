# SPARTA — virar aplicativo de verdade (.exe com logo, na Área de Trabalho)

Isso transforma a central e os três apps em **executáveis `.exe`** com o **logo
SPARTA** (os logos vermelhos), e coloca os **atalhos na sua Área de Trabalho**.
Some o visual de "Arquivo em Lotes" (.bat) e o ícone da cobrinha do Python.

## Como fazer (uma vez)

1. Tenha o **Python** instalado (abra o `cmd` e digite `py --version` para conferir).
2. Dê **duplo clique** em **`CONSTRUIR_APPS.bat`**.
3. Espere. Na primeira vez demora alguns minutos (ele baixa o empacotador).
4. No fim, aparecem na Área de Trabalho:
   - **SPARTA** (a central / menu)
   - **SPARTA - Cofre**
   - **SPARTA - Explorador**
   - **SPARTA - Mixer**

Os `.exe` ficam na pasta **`dist\`**. A pasta **`build\`** é só lixo temporário
da construção — pode apagar.

## Detalhes úteis

- **Pode mover/copiar a pasta `dist\`** para onde quiser (ex.: `C:\SPARTA`). Se
  mover, rode de novo os atalhos com:
  `powershell -ExecutionPolicy Bypass -File criar_atalhos.ps1 -Dist "C:\SPARTA\dist"`
- O **`config.json`** (suas configurações) é criado **ao lado do `SPARTA.exe`**,
  na primeira vez que a central abre. Edite esse arquivo para ajustar pastas,
  agendamentos, etc.
- **Fixar na barra de tarefas / menu Iniciar:** clique com o botão direito no
  `.exe` (ou no atalho) → *Fixar*. O ícone do SPARTA aparece certinho.
- **Cada app é independente.** A central (`SPARTA.exe`) chama o `Explorador.exe`
  e o `Mixer.exe` que estão **na mesma pasta `dist\`** — por isso mantenha os
  quatro juntos.

## Trocar o logo depois

Os ícones vêm das artes em `assets\arte\` (sparta / cofre / arquivos / mixer).
Para trocar: substitua a arte correspondente e regenere os ícones:

```
cd automacao_pc
py assets\converter_logos.py
```

Isso reescreve `assets\sparta.ico`, `cofre.ico`, `explorador.ico`, `mixer.ico`
(recortando o emblema, sem o texto). Se a arte nova tiver outro tamanho ou
enquadramento, ajuste as caixas de recorte no topo do `converter_logos.py`.
Depois é só rodar o `CONSTRUIR_APPS.bat` de novo.

## Gerar um app só

Dentro de `cofre\`, `explorador\` ou `mixer\` há um `gerar_exe.bat` que cria só
aquele app (com o ícone certo), caso você não queira reconstruir tudo.

## Observações honestas

- Tudo isso é feito **para Windows** e só dá para testar de verdade no seu PC —
  me avise se algum `.exe` não abrir ou reclamar de alguma biblioteca, que eu
  ajusto.
- O **boost de volume acima de 100%** (no Mixer) continua precisando do
  **Equalizer APO** instalado; o resto do volume funciona sem ele.
- A tempestade de CMDs da abertura: quando você roda pelo `.exe`, se o Windows
  achar um Python instalado, abre os CMDs de verdade; se não achar, cai no
  efeito feito dentro do próprio terminal (sem erro).
