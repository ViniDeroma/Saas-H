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
if not exist telegram_config.json (
    echo  [!] O Telegram ainda nao foi configurado.
    echo.
)
echo  O que voce quer fazer?
echo.
echo   [1] Baixar UM album (colar o link)
echo   [2] Baixar VARIOS de uma BUSCA (ex: amador)
echo   [3] Sair
echo   [4] Configurar/Reconfigurar Telegram
echo.

set "opcao="
set /p "opcao=Escolha (1/2/3/4): "

if "%opcao%"=="4" goto configtg
if "%opcao%"=="3" goto fim
if "%opcao%"=="2" goto busca
if "%opcao%"=="1" goto album
goto menu

:configtg
cls
echo ----------------------------------------------------
echo  CONFIGURACAO DO TELEGRAM
echo ----------------------------------------------------
python erome_downloader.py --setup-telegram
pause
goto menu

:album
cls
echo ----------------------------------------------------
echo  Cole o link do album (ex: https://www.erome.com/a/XXXXXX)
echo  Deixe em branco para voltar.
echo ----------------------------------------------------
echo.
set "link="
set /p "link=Link do album: "
if "%link%"=="" goto menu

set "soimg="
set /p "soimg=Baixar SO videos (sem imagens)? (s/N): "
set "usetg="
set /p "usetg=Enviar downloads para o Telegram? (s/N): "
echo.
echo ----------------------------------------------------

set "ARGS=--workers 16"
if /i "%soimg%"=="s" set "ARGS=%ARGS% --skip-images"
if /i "%usetg%"=="s" set "ARGS=%ARGS% --telegram --clean-local"

python erome_downloader.py "%link%" %ARGS%
goto fimrodada

:busca
cls
echo ----------------------------------------------------
echo  Digite o termo que quer pesquisar (ex: amador)
echo  Deixe em branco para voltar.
echo ----------------------------------------------------
echo.
set "termo="
set /p "termo=Pesquisar por: "
if "%termo%"=="" goto menu

set "paginas="
set /p "paginas=Quantas paginas baixar? (cada pagina ~36 albuns) [1]: "
if "%paginas%"=="" set "paginas=1"

set "soimg="
set /p "soimg=Baixar SO videos (sem imagens)? (s/N): "
set "usetg="
set /p "usetg=Enviar downloads para o Telegram? (s/N): "
echo.
echo ----------------------------------------------------
echo  ATENCAO: varias paginas = muitos albuns e muitos GB!
echo ----------------------------------------------------

set "ARGS=--search "%termo%" --pages %paginas% --workers 16"
if /i "%soimg%"=="s" set "ARGS=%ARGS% --skip-images"
if /i "%usetg%"=="s" set "ARGS=%ARGS% --telegram --clean-local"

python erome_downloader.py %ARGS%
goto fimrodada

:fimrodada
echo ----------------------------------------------------
if errorlevel 1 (
    echo.
    echo [!] Algo deu errado. Se for "python nao reconhecido",
    echo     instale o Python ou troque "python" por "py".
)
echo.
set "denovo="
set /p "denovo=Aperte ENTER para voltar ao menu, ou N para sair: "
if /i "%denovo%"=="n" goto fim
goto menu

:fim
echo.
echo Ate mais!
timeout /t 2 >nul
