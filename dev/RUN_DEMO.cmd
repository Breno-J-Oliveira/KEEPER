@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start "KEEPER - MAQUINA" cmd /k "python machine.py"
start "KEEPER - ADM" cmd /k "python admin.py"
timeout /t 2 >nul
start "KEEPER - FUNCIONARIO" cmd /k "python employee.py"
endlocal
