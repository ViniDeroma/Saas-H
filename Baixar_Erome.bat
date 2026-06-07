@echo off
chcp 65001 >nul
title Baixar Videos do Erome
cd /d "%~dp0"

:menu
cls
echo ====================================================
echo            BAIXADOR DE ALBUNS DO EROME
echo ====================================================
echo.
echo  Cole o link do album (ex: https://www.erome.com/a/XXXXXX)
echo  Para sair, deixe em branco e aperte ENTER.
echo.

set "link="
set /p "link=Link do album: "

if "%link%"=="" goto fim

echo.
set "soimagens="
set /p "soimagens=Baixar SO videos (sem imagens)? (s/N): "

echo.
echo ----------------------------------------------------
if /i "%soimagens%"=="s" (
    python erome_downloader.py "%link%" --skip-images
) else (
    python erome_downloader.py "%link%"
)
echo ----------------------------------------------------

if errorlevel 1 (
    echo.
    echo [!] Algo deu errado. Se for "python nao reconhecido",
    echo     instale o Python ou tente trocar "python" por "py".
)

echo.
echo Baixar outro album?
set "denovo="
set /p "denovo=Aperte ENTER para baixar outro, ou digite N para sair: "
if /i "%denovo%"=="n" goto fim
goto menu

:fim
echo.
echo Ate mais!
timeout /t 2 >nul
