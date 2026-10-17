@echo off
rem Gera dist\Mixer.exe.
cd /d "%~dp0"
py -m pip install --upgrade pyinstaller pywebview pycaw comtypes || goto erro
py -m PyInstaller --noconfirm --clean --onefile --windowed --name Mixer --icon "..\assets\mixer.ico" --paths .. --add-data "ui;ui" mixer.py || goto erro
echo Pronto! Veja dist\Mixer.exe
pause
exit /b 0
:erro
echo Algo deu errado.
pause
