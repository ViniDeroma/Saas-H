@echo off
title Iniciando Clonador de Mídias Premium
echo ====================================================
echo      INICIANDO CLONADOR DE MIDIAS TELEGRAM PREMIUM
echo ====================================================
echo.

cd /d "%~dp0"

:: 1. Verificar e criar ambiente virtual do Python
if not exist venv (
    echo [1/4] Criando ambiente virtual Python...
    python -m venv venv
)

echo [2/4] Ativando ambiente virtual e instalando dependencias...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

:: 2. Verificar se o frontend precisa ser copiado
:: (Ja pre-compilamos e copiamos no backend/static, entao nao precisa compilar de novo)
if not exist backend\static (
    echo [3/4] Interface web nao encontrada no servidor!
    pause
    exit /b 1
)

echo [3/4] Interface web ja integrada no servidor.

echo.
echo ====================================================
echo   TUDO PRONTO! INICIANDO SERVIDOR DO CLONADOR...
echo   Seu navegador abrira automaticamente em:
echo   http://127.0.0.1:8000
echo ====================================================
echo.

:: 3. Rodar o servidor Python
python -m backend.main
pause
