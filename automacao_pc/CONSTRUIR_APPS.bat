@echo off
rem ============================================================
rem  SPARTA - CONSTRUIR_APPS
rem  Transforma tudo em aplicativos .exe de verdade (com o logo
rem  SPARTA) e cria os atalhos na Area de Trabalho.
rem
rem  Gera, dentro de dist\:
rem    SPARTA.exe       (a central / menu)
rem    Cofre.exe        (cofre de senhas)
rem    Explorador.exe   (explorador de arquivos)
rem    Mixer.exe        (mixer de volume)
rem
rem  E coloca 4 atalhos com o icone SPARTA na sua Area de Trabalho.
rem  Rode este arquivo uma vez (duplo clique). Pode demorar alguns
rem  minutos na primeira vez (ele baixa o empacotador).
rem ============================================================
setlocal
cd /d "%~dp0"
set "RAIZ=%~dp0"
if "%RAIZ:~-1%"=="\" set "RAIZ=%RAIZ:~0,-1%"
set "DIST=%RAIZ%\dist"
set "BUILD=%RAIZ%\build"

echo.
echo  ====== SPARTA // CONSTRUINDO OS APLICATIVOS ======
echo.

echo  [1/6] Instalando o empacotador e as bibliotecas...
py -m pip install --upgrade pyinstaller pywebview cryptography pycaw comtypes pillow || goto erro

echo.
echo  [2/6] Construindo a CENTRAL (SPARTA.exe)...
py -m PyInstaller --noconfirm --clean --onefile --name SPARTA ^
  --icon "%RAIZ%\assets\sparta.ico" --paths "%RAIZ%" ^
  --distpath "%DIST%" --workpath "%BUILD%\sparta" --specpath "%BUILD%" ^
  --add-data "%RAIZ%\config.exemplo.json;." ^
  "%RAIZ%\pc.py" || goto erro

echo.
echo  [3/6] Construindo o COFRE (Cofre.exe)...
py -m PyInstaller --noconfirm --clean --onefile --windowed --name Cofre ^
  --icon "%RAIZ%\assets\cofre.ico" --paths "%RAIZ%" ^
  --distpath "%DIST%" --workpath "%BUILD%\cofre" --specpath "%BUILD%" ^
  --add-data "%RAIZ%\cofre\ui;ui" ^
  --add-data "%RAIZ%\cofre\nucleo.py;." --add-data "%RAIZ%\cofre\autotipo.py;." --add-data "%RAIZ%\cofre\cofre.py;." ^
  "%RAIZ%\cofre\cofre.py" || goto erro

echo.
echo  [4/6] Construindo o EXPLORADOR (Explorador.exe)...
py -m PyInstaller --noconfirm --clean --onefile --windowed --name Explorador ^
  --icon "%RAIZ%\assets\explorador.ico" --paths "%RAIZ%" ^
  --distpath "%DIST%" --workpath "%BUILD%\explorador" --specpath "%BUILD%" ^
  --add-data "%RAIZ%\explorador\ui;ui" --add-data "%RAIZ%\explorador\icones.py;." ^
  "%RAIZ%\explorador\explorador.py" || goto erro

echo.
echo  [5/6] Construindo o MIXER (Mixer.exe)...
py -m PyInstaller --noconfirm --clean --onefile --windowed --name Mixer ^
  --icon "%RAIZ%\assets\mixer.ico" --paths "%RAIZ%" ^
  --distpath "%DIST%" --workpath "%BUILD%\mixer" --specpath "%BUILD%" ^
  --add-data "%RAIZ%\mixer\ui;ui" ^
  "%RAIZ%\mixer\mixer.py" || goto erro

echo.
echo  [6/6] Criando os atalhos na Area de Trabalho...
powershell -NoProfile -ExecutionPolicy Bypass -File "%RAIZ%\criar_atalhos.ps1" -Dist "%DIST%" || goto erro

echo.
echo  ================================================
echo   PRONTO! Seus aplicativos estao em:
echo     %DIST%
echo   E os atalhos ja estao na Area de Trabalho.
echo.
echo   Pode apagar a pasta build\ (sao so arquivos
echo   temporarios da construcao).
echo  ================================================
echo.
pause
exit /b 0

:erro
echo.
echo  !!! Algo deu errado. Veja a mensagem acima.
echo  Dica: confira se o Python esta instalado (digite  py --version ).
echo.
pause
exit /b 1
