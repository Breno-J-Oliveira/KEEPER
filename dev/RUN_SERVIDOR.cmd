
@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

title KEEPER - Inicializador Completo

REM ============================================================
REM CONFIGURACAO
REM ============================================================

set "PYTHON=%CD%\.venv\Scripts\python.exe"
set "CLOUDFLARED="
set "LOG_DIR=%TEMP%\KEEPER_TUNNELS"
set "LOG_FUNC=%LOG_DIR%\funcionario.log"
set "LOG_ADMIN=%LOG_DIR%\administrador.log"

REM ============================================================
REM CABECALHO
REM ============================================================

cls
echo.
echo ============================================================
echo                  KEEPER - INICIALIZADOR
echo ============================================================
echo.
echo Preparando o ambiente...
echo.

REM ============================================================
REM VALIDACOES
REM ============================================================

if not exist "%PYTHON%" (
    echo [ERRO] Python do ambiente virtual nao encontrado.
    echo.
    echo Caminho esperado:
    echo %PYTHON%
    echo.
    echo Verifique se a pasta .venv existe.
    pause
    exit /b 1
)

if not exist "%CD%\machine.py" (
    echo [ERRO] machine.py nao encontrado.
    pause
    exit /b 1
)

if not exist "%CD%\mobile.py" (
    echo [ERRO] mobile.py nao encontrado.
    pause
    exit /b 1
)

if not exist "%CD%\web_admin.py" (
    echo [ERRO] web_admin.py nao encontrado.
    pause
    exit /b 1
)

REM ============================================================
REM LOCALIZAR CLOUDFLARED
REM ============================================================

for /f "delims=" %%I in ('where cloudflared 2^>nul') do (
    if not defined CLOUDFLARED set "CLOUDFLARED=%%I"
)

if not defined CLOUDFLARED (
    echo [ERRO] Cloudflare Tunnel nao encontrado.
    echo.
    echo Instale com:
    echo winget install --id Cloudflare.cloudflared -e
    echo.
    echo Depois feche e abra novamente este arquivo.
    pause
    exit /b 1
)

REM ============================================================
REM PREPARAR LOGS
REM ============================================================

if not exist "%LOG_DIR%" md "%LOG_DIR%"

del /q "%LOG_FUNC%" "%LOG_ADMIN%" >nul 2>&1

REM ============================================================
REM INICIAR A PORTARIA
REM ============================================================

echo [1/4] Iniciando a portaria e a camera...
echo.

start "KEEPER - Portaria e Camera" "%ComSpec%" /k ""%PYTHON%" "%CD%\machine.py""

REM ============================================================
REM INICIAR APLICACAO DO FUNCIONARIO
REM ============================================================

echo [2/4] Iniciando o sistema do funcionario...
echo.

start "KEEPER - Funcionario 8550" "%ComSpec%" /k ""%PYTHON%" "%CD%\mobile.py""

REM ============================================================
REM INICIAR PAINEL ADMINISTRATIVO
REM ============================================================

echo Iniciando o painel administrativo...
echo.

start "KEEPER - Administrador 8551" "%ComSpec%" /k ""%PYTHON%" "%CD%\web_admin.py""

REM ============================================================
REM AGUARDAR OS SERVICOS
REM ============================================================

echo Aguardando os aplicativos iniciarem...
timeout /t 10 /nobreak >nul

REM ============================================================
REM INICIAR TUNEIS CLOUDFLARE
REM ============================================================

echo.
echo [3/4] Criando os tuneis publicos...
echo.

start "KEEPER Tunnel Funcionario" /min "%ComSpec%" /d /c ""%CLOUDFLARED%" tunnel --url http://127.0.0.1:8550 > "%LOG_FUNC%" 2>&1"

start "KEEPER Tunnel Administrador" /min "%ComSpec%" /d /c ""%CLOUDFLARED%" tunnel --url http://127.0.0.1:8551 > "%LOG_ADMIN%" 2>&1"

REM ============================================================
REM AGUARDAR E LER AS URLS
REM ============================================================

echo Aguardando a geracao das URLs do Cloudflare.
echo Isso pode levar alguns segundos...
echo.

set /a TENTATIVAS=0

:AGUARDAR_URLS

set "URL_FUNC="
set "URL_ADMIN="

for /f "tokens=2 delims=|" %%U in ('findstr /i "trycloudflare.com" "%LOG_FUNC%" 2^>nul') do (
    set "URL_FUNC=%%U"
    set "URL_FUNC=!URL_FUNC: =!"
)

for /f "tokens=2 delims=|" %%U in ('findstr /i "trycloudflare.com" "%LOG_ADMIN%" 2^>nul') do (
    set "URL_ADMIN=%%U"
    set "URL_ADMIN=!URL_ADMIN: =!"
)

if defined URL_FUNC if defined URL_ADMIN goto MOSTRAR_URLS

set /a TENTATIVAS+=1

if !TENTATIVAS! geq 45 goto MOSTRAR_URLS

timeout /t 1 /nobreak >nul
goto AGUARDAR_URLS

REM ============================================================
REM EXIBIR RESULTADO
REM ============================================================

:MOSTRAR_URLS

cls
echo.
echo ============================================================
echo                    KEEPER - STATUS
echo ============================================================
echo.

echo [FUNCIONARIO - PORTA 8550]
if defined URL_FUNC (
    echo !URL_FUNC!
) else (
    echo URL ainda nao identificada.
    echo Consulte o log:
    echo %LOG_FUNC%
)

echo.
echo ------------------------------------------------------------
echo.

echo [ADMINISTRADOR - PORTA 8551]
if defined URL_ADMIN (
    echo !URL_ADMIN!
) else (
    echo URL ainda nao identificada.
    echo Consulte o log:
    echo %LOG_ADMIN%
)

echo.
echo ------------------------------------------------------------
echo.
echo [PORTARIA]
echo Executando localmente neste computador.
echo A camera precisa estar conectada ao computador da portaria.
echo.
echo [ENDERECOS LOCAIS]
echo Funcionario: http://localhost:8550
echo Administrador: http://localhost:8551
echo.
echo ============================================================
echo INSTRUCOES IMPORTANTES
echo ============================================================
echo.
echo 1. Mantenha este inicializador aberto.
echo 2. Nao feche as janelas dos aplicativos.
echo 3. Nao feche os processos do Cloudflare.
echo 4. O computador deve permanecer ligado e conectado.
echo 5. As URLs gratuitas podem mudar ao reiniciar os tuneis.
echo.
echo Logs:
echo %LOG_DIR%
echo.
echo Para encerrar, feche os aplicativos e os tuneis.
echo ============================================================
echo.

pause