@echo off
rem Gera dist\Explorador.exe (para levar/atalhar).
cd /d "%~dp0"
py -m pip install --upgrade pyinstaller pywebview || goto erro
py -m PyInstaller --noconfirm --clean --onefile --windowed --name Explorador --icon "..\assets\explorador.ico" --paths .. --add-data "ui;ui" --add-data "icones.py;." explorador.py || goto erro
echo.
echo Pronto! Veja dist\Explorador.exe
pause
exit /b 0
:erro
echo Algo deu errado.
pause
