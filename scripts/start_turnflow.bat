@echo off
setlocal

REM Carpeta donde está este .bat (...\TurnFlow\scripts\)
set SCRIPT_DIR=%~dp0

REM Subimos un nivel => ...\TurnFlow\
for %%I in ("%SCRIPT_DIR%..") do set APP_DIR=%%~fI

cd /d "%APP_DIR%"

REM Validaciones (para no arrancar “a ciegas”)
if not exist "%APP_DIR%\.venv\Scripts\python.exe" (
  echo ERROR: No existe el venv en "%APP_DIR%\.venv"
  echo Crea el entorno con:
  echo   py -3.11 -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

REM Levantar con el python del venv (sin depender de activate)
"%APP_DIR%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

endlocal
