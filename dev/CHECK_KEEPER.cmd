@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python smoke_test.py
pause
endlocal
