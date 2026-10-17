@echo off
rem Abre o Explorador. Na primeira vez instala o Pillow (icones reais).
cd /d "%~dp0"
py -c "import PIL" 1>nul 2>nul || (echo Instalando Pillow para os icones reais... ^& py -m pip install pillow)
start "" pyw explorador.py %*
