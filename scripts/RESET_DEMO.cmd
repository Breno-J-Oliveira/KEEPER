@echo off
setlocal
cd /d "%~dp0.."
echo ATENCAO: isto apaga o banco keeper.db e cria um banco novo de demonstracao.
pause
if exist keeper.db del /q keeper.db
if exist data\faces\*.jpg del /q data\faces\*.jpg
call .venv\Scripts\activate.bat
python -c "import db; print('Banco recriado com sucesso.')"
pause
endlocal
