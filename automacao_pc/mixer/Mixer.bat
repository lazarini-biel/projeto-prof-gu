@echo off
rem Abre o Mixer. Na primeira vez instala o que falta (audio + icones).
cd /d "%~dp0"
py -c "import pycaw, comtypes" 1>nul 2>nul || (echo Instalando bibliotecas de audio... ^& py -m pip install pycaw comtypes)
py -c "import PIL" 1>nul 2>nul || (echo Instalando Pillow para os icones... ^& py -m pip install pillow)
start "" pyw mixer.py %*
