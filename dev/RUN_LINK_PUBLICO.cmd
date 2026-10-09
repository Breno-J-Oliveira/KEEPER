@echo off
echo Instale uma vez: winget install Cloudflare.cloudflared
echo.
echo Link PUBLICO do app do FUNCIONARIO (copie o endereco https://....trycloudflare.com):
cloudflared tunnel --url http://localhost:8550
