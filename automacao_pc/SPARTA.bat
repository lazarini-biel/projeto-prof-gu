@echo off
cd /d "%~dp0"
rem Sem argumentos: abre o menu em tela cheia no Windows Terminal (se existir).
if "%~1"=="" (
  where wt >nul 2>nul && (
    start "" wt -F --title "SPARTA" -d "%~dp0." py pc.py
    exit /b
  )
)
py pc.py %*
echo.
pause
