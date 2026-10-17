@echo off
rem Gera dist\Cofre.exe: um unico arquivo para levar no pendrive.
cd /d "%~dp0"
py -m pip install --upgrade pyinstaller pywebview cryptography || goto erro
py -m PyInstaller --noconfirm --clean --onefile --windowed --name Cofre --icon "..\assets\cofre.ico" --paths .. --add-data "ui;ui" --add-data "nucleo.py;." --add-data "autotipo.py;." --add-data "cofre.py;." cofre.py || goto erro
echo.
echo Pronto! Copie dist\Cofre.exe para o pendrive.
echo Na primeira vez ele cria o cofre.dat ao lado do .exe.
pause
exit /b 0
:erro
echo.
echo Algo deu errado. Veja a mensagem acima.
pause
exit /b 1
