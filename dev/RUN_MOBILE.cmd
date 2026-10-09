@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Se o Windows perguntar sobre o Firewall, clique em PERMITIR.
python mobile.py
endlocal
