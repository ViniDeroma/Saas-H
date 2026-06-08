#!/data/data/com.termux/files/usr/bin/bash
# Baixador de albuns do Erome - Termux (com busca e downloads paralelos)

DL=~/erome_downloader.py
OUT=~/storage/downloads/erome_downloads
PC=http://192.168.1.9:8000   # endereco do PC na rede (servidor de atualizacao)

# --- Auto-atualizacao (se o PC estiver ligado na mesma WiFi) ---
echo "Procurando atualizacoes no PC..."
if wget -q -T 4 -O ~/.erome_dl.new "$PC/erome_downloader.py" 2>/dev/null && [ -s ~/.erome_dl.new ]; then
    mv ~/.erome_dl.new "$DL"
    echo "  programa atualizado!"
else
    rm -f ~/.erome_dl.new
    echo "  (sem atualizacao - usando versao atual)"
fi
if wget -q -T 4 -O ~/.erome_sh.new "$PC/baixar_erome.sh" 2>/dev/null && [ -s ~/.erome_sh.new ]; then
    mv ~/.erome_sh.new ~/baixar_erome.sh
    echo "  menu atualizado (vale na proxima vez que rodar)"
else
    rm -f ~/.erome_sh.new
fi
if wget -q -T 4 -O ~/.telegram_helper.new "$PC/telegram_helper.py" 2>/dev/null && [ -s ~/.telegram_helper.new ]; then
    mv ~/.telegram_helper.new ~/telegram_helper.py
    echo "  modulo telegram atualizado!"
else
    rm -f ~/.telegram_helper.new
fi
sleep 1

while true; do
    clear
    echo "===================================================="
    echo "           BAIXADOR DE ALBUNS DO EROME"
    echo "===================================================="
    echo ""
    if [ ! -f "telegram_config.json" ]; then
        echo "  [!] O Telegram ainda nao foi configurado."
        echo ""
    fi
    echo "  [1] Baixar UM album (colar o link)"
    echo "  [2] Baixar VARIOS de uma BUSCA (ex: amador)"
    echo "  [3] Sair"
    echo "  [4] Configurar/Reconfigurar Telegram"
    echo ""
    printf "Escolha (1/2/3/4): "
    read opcao

    if [ "$opcao" = "3" ]; then
        break
    fi

    if [ "$opcao" = "4" ]; then
        echo "----------------------------------------------------"
        echo "  CONFIGURACAO DO TELEGRAM"
        echo "----------------------------------------------------"
        python "$DL" --setup-telegram
        echo "Pressione ENTER para voltar..."
        read dummy
        continue
    fi

    if [ "$opcao" = "1" ]; then
        echo ""
        printf "Cole o link do album: "
        read link
        [ -z "$link" ] && continue
        printf "Baixar SO videos (sem imagens)? (s/N): "
        read soimg
        printf "Enviar downloads para o Telegram? (s/N): "
        read usetg
        echo "----------------------------------------------------"
        ARGS="--workers 8 -o \"$OUT\""
        if [ "$soimg" = "s" ] || [ "$soimg" = "S" ]; then ARGS="$ARGS --skip-images"; fi
        if [ "$usetg" = "s" ] || [ "$usetg" = "S" ]; then ARGS="$ARGS --telegram --clean-local"; fi
        
        eval python \"$DL\" \"$link\" $ARGS

    elif [ "$opcao" = "2" ]; then
        echo ""
        printf "Pesquisar por: "
        read termo
        [ -z "$termo" ] && continue
        paginas="ask"
        printf "Baixar SO videos (sem imagens)? (s/N): "
        read soimg
        printf "Enviar downloads para o Telegram? (s/N): "
        read usetg
        echo "----------------------------------------------------"
        echo "ATENCAO: varias paginas = muitos albuns e muitos MB/GB!"
        echo "----------------------------------------------------"
        
        ARGS="--search \"$termo\" --pages \"$paginas\" --workers 8 -o \"$OUT\""
        if [ "$soimg" = "s" ] || [ "$soimg" = "S" ]; then ARGS="$ARGS --skip-images"; fi
        if [ "$usetg" = "s" ] || [ "$usetg" = "S" ]; then ARGS="$ARGS --telegram --clean-local"; fi
        
        eval python \"$DL\" $ARGS
    else
        continue
    fi

    echo "----------------------------------------------------"
    echo ""
    printf "ENTER para voltar ao menu, ou N para sair: "
    read denovo
    { [ "$denovo" = "n" ] || [ "$denovo" = "N" ]; } && break
done

echo ""
echo "Ate mais!"
