@echo off
setlocal

:: Define o diretório do script como base
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Inicia o Streamlit para o rodar.py em modo silencioso (sem abrir o console)
start /MIN python -m streamlit run "%SCRIPT_DIR%rodar.py" --server.headless true

:: Aguarda 5 segundos para garantir que o Streamlit inicie
timeout /t 5 /nobreak >nul

:: Tenta abrir a URL no Brave Browser ou no navegador padrão
set "BRAVE_PATH="
for %%I in (Brave.exe) do set "BRAVE_PATH=%%~$PATH:I"
if defined BRAVE_PATH (
    start "" "%BRAVE_PATH%" "http://localhost:8501"
) else (
    start "" "http://localhost:8501"
)

:: Fecha o terminal imediatamente
exit