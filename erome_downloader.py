"""
Erome Downloader
----------------
Baixa albuns publicos do Erome. Aceita:
  - Link de um album:      https://www.erome.com/a/XXXXXX
  - Link de uma busca:     https://www.erome.com/search?q=amador
  - Termo de busca direto: --search "amador"
  - Arquivo .txt com varias URLs (uma por linha)

Exemplos:
    python erome_downloader.py https://www.erome.com/a/XXXXXX
    python erome_downloader.py --search "amador" --pages 5
    python erome_downloader.py "https://www.erome.com/search?q=amador" --pages 3
    python erome_downloader.py https://www.erome.com/a/XXXXXX --skip-images
    python erome_downloader.py urls.txt -o "C:/Downloads"

Dependencias: requests, beautifulsoup4
"""

import argparse
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, quote

import requests
from bs4 import BeautifulSoup
import shutil

try:
    from telegram_helper import TelegramUploader
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

HOST = "https://www.erome.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
}

# Reconhece links de album: /a/CODIGO
ALBUM_RE = re.compile(r"/a/([A-Za-z0-9]+)")


def sanitize(name: str) -> str:
    """Remove caracteres invalidos para nome de pasta/arquivo."""
    name = re.sub(r'[<>:"/\\|?*\n\r\t]', "_", name).strip()
    return name[:120] or "erome_album"


def is_album_url(url: str) -> bool:
    return "/a/" in url


def is_search_or_listing(url: str) -> bool:
    return ("/search" in url) or ("?q=" in url) or ("/tag/" in url) or url.rstrip("/") == HOST


def get_album_links(listing_url: str, pages_str: str, session: requests.Session):
    """Coleta todos os links de album de uma pagina de busca/listagem (varias paginas)."""
    found = []
    seen = set()
    base = listing_url.split("#")[0]
    sep = "&" if "?" in base else "?"

    if "-" in str(pages_str):
        start_p, end_p = map(int, str(pages_str).split("-"))
    else:
        start_p = end_p = int(pages_str)

    for page in range(start_p, end_p + 1):
        page_url = base if page == 1 else f"{base}{sep}page={page}"
        print(f"  Lendo pagina {page} (limite {end_p}): {page_url}")
        try:
            resp = session.get(page_url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"    [ERRO] {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        page_links = []
        for a in soup.find_all("a", href=True):
            m = ALBUM_RE.search(a["href"])
            if m:
                full = HOST + "/a/" + m.group(1)
                if full not in seen:
                    seen.add(full)
                    page_links.append(full)

        if not page_links:
            print("    (nenhum album novo nesta pagina; encerrando)")
            break

        found.extend(page_links)
        print(f"    +{len(page_links)} albuns (total {len(found)})")
        time.sleep(1)  # pausa educada entre paginas

    return found


def get_album_media(album_url: str, session: requests.Session):
    """Retorna (titulo, [videos], [imagens]) de um album."""
    resp = session.get(album_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title_tag = soup.find("meta", attrs={"property": "og:title"})
    title = title_tag["content"] if title_tag and title_tag.get("content") else album_url.rstrip("/").split("/")[-1]

    videos = [s.get("src") for s in soup.select("video source") if s.get("src")]
    images = [(i.get("data-src") or i.get("src")) for i in soup.select("img.img-back") if (i.get("data-src") or i.get("src"))]

    videos = list(dict.fromkeys(videos))
    images = list(dict.fromkeys(images))
    return title, videos, images


def download_file(url: str, dest_path: str, referer: str, session: requests.Session, retries: int = 4):
    """Baixa um arquivo com o Referer correto. Tenta de novo em caso de falha."""
    name = os.path.basename(dest_path)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        print(f"    [pulado] ja existe: {name}")
        return True

    headers = dict(HEADERS)
    headers["Referer"] = referer

    for attempt in range(1, retries + 1):
        try:
            with session.get(url, headers=headers, stream=True, timeout=(10, 15)) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                last_print = 0
                tmp = dest_path + ".part"
                print(f"    [iniciando] {name} ({total_size//(1024*1024)}MB)") if total_size else print(f"    [iniciando] {name}")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 512):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                if percent - last_print >= 10:
                                    print(f"    -> {name}: {percent:.0f}%")
                                    last_print = percent
                os.replace(tmp, dest_path)
            print(f"    [ok] {name}")
            return True
        except Exception as e:
            if os.path.exists(dest_path + ".part"):
                os.remove(dest_path + ".part")
            if attempt < retries:
                wait = 2 * attempt
                print(f"    [tentativa {attempt}/{retries} falhou] {name} - retentando em {wait}s")
                time.sleep(wait)
            else:
                print(f"    [ERRO apos {retries} tentativas] {name}: {e}")
    return False


def process_album(album_url: str, out_root: str, skip_images: bool, session: requests.Session, workers: int = 4):
    album_url = album_url.strip()
    if not album_url:
        return None, None, []
    print(f"\n=== Album: {album_url} ===")
    try:
        title, videos, images = get_album_media(album_url, session)
    except Exception as e:
        print(f"  [ERRO] nao foi possivel ler o album: {e}")
        return None, None, []

    folder = os.path.join(out_root, sanitize(title))
    os.makedirs(folder, exist_ok=True)
    print(f"  Titulo: {title} | Videos: {len(videos)} | Imagens: {len(images)}")
    print(f"  Salvando em: {folder}")

    items = list(videos)
    if not skip_images:
        items += images

    tasks = []
    for i, media_url in enumerate(items, 1):
        ext = os.path.splitext(urlparse(media_url).path)[1] or ".bin"
        dest = os.path.join(folder, f"{i:03d}{ext}")
        tasks.append((media_url, dest))

    ok = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(download_file, m, d, album_url, session) for m, d in tasks]
        for fut in as_completed(futures):
            if fut.result():
                ok += 1
    print(f"  Concluido: {ok}/{len(items)} arquivos.")
    
    downloaded_files = [d for m, d in tasks if os.path.exists(d)]
    return title, folder, downloaded_files


def expand_targets(target: str, pages: str, session: requests.Session):
    """Transforma o alvo (album, busca, listagem ou .txt) numa lista de URLs de album."""
    # Arquivo .txt com varias URLs
    if os.path.isfile(target):
        with open(target, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        albums = []
        for line in lines:
            albums.extend(expand_targets(line, pages, session))
        return albums

    if not target.startswith("http"):
        target = HOST + ("" if target.startswith("/") else "/") + target

    # Pagina de busca/listagem -> coletar varios albuns
    if is_search_or_listing(target):
        if str(pages) == "ask":
            print(f"\nBuscando informacoes sobre os resultados...")
            try:
                resp = session.get(target, headers=HEADERS, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                max_p = 1
                for a in soup.select('ul.pagination li a'):
                    if a.text.isdigit():
                        max_p = max(max_p, int(a.text))
                
                print(f"-> Foram encontradas {max_p} paginas no total para essa busca!")
                pages = input("Qual pagina voce quer baixar? (ex: 3, ou 1-5) [padrao=1]: ").strip()
                if not pages:
                    pages = "1"
            except Exception as e:
                pages = "1"

        print(f"\n### Coletando albuns de: {target}")
        albums = get_album_links(target, pages, session)
        print(f"### Total de albuns encontrados: {len(albums)}")
        return albums

    # Link de album unico
    if is_album_url(target):
        return [target]

    print(f"  [AVISO] nao reconheci o tipo de link: {target}")
    return []


def main():
    parser = argparse.ArgumentParser(description="Baixa midias de albuns publicos do Erome.")
    parser.add_argument("target", nargs="?", help="URL de album, URL de busca, ou caminho de um .txt")
    parser.add_argument("--search", help="Termo de busca (ex: --search amador)")
    parser.add_argument("--pages", type=str, default="1", help="Pagina especifica (ex: 3) ou intervalo (ex: 1-5). Padrao=1")
    parser.add_argument("-o", "--output", default="erome_downloads", help="Pasta de destino")
    parser.add_argument("--skip-images", action="store_true", help="Baixar somente videos")
    parser.add_argument("--workers", type=int, default=4, help="Downloads simultaneos (padrao 4)")
    parser.add_argument("--telegram", action="store_true", help="Ativar integracao interativa com Telegram")
    parser.add_argument("--clean-local", action="store_true", help="Apagar arquivos locais apos enviar pro Telegram")
    parser.add_argument("--setup-telegram", action="store_true", help="Configurar o Telegram e sair")
    args = parser.parse_args()

    session = requests.Session()

    if getattr(args, 'setup_telegram', False):
        if not TELEGRAM_AVAILABLE:
            print("\n[!] O modulo do Telegram (Telethon) nao esta instalado.")
            print("Instale com: pip install telethon cryptg")
            return
        uploader = TelegramUploader()
        uploader.connect()
        print("\nConfiguracao do Telegram concluida com sucesso!")
        return

    # Monta o alvo a partir de --search, se usado
    if args.search:
        target = f"{HOST}/search?q={quote(args.search)}"
    elif args.target:
        target = args.target
    else:
        parser.error("informe um link/arquivo OU use --search \"termo\"")

    albums = expand_targets(target, args.pages, session)
    if not albums:
        print("Nenhum album encontrado/valido.")
        return

    HISTORY_FILE = "erome_history.txt"
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = set(line.strip() for line in f if line.strip())
    else:
        history = set()

    filtered_albums = []
    for album in albums:
        if album in history:
            print(f"  [historico] Pulando album ja processado: {album}")
        else:
            filtered_albums.append(album)
            
    albums = filtered_albums
    if not albums:
        print("\nTodos os albuns desta busca ja foram baixados/processados anteriormente!")
        return

    os.makedirs(args.output, exist_ok=True)
    print(f"\n>>> Vou baixar {len(albums)} album(ns).")
    
    uploader = None
    use_telegram = False
    
    if getattr(args, 'telegram', False):
        if not TELEGRAM_AVAILABLE:
            print("\n[!] O modulo do Telegram (Telethon) nao esta instalado.")
            print("Instale com: pip install telethon cryptg")
            return
        uploader = TelegramUploader()
        uploader.connect()
        use_telegram = uploader.setup_target_group()

    # Se Telegram ativo, mapeia todas as respostas ANTES de baixar
    album_decisions = []
    if use_telegram:
        print(f"\n--- PREPARANDO {len(albums)} ALBUNS ---")
        print("Buscando os nomes dos albuns na nuvem (aguarde uns segundinhos)...")
        
        album_titles = {}
        def _fetch_title(album_url):
            try:
                t, _, _ = get_album_media(album_url, session)
                return album_url, t
            except:
                return album_url, album_url.split('/')[-1]
                
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(_fetch_title, url) for url in albums]
            for fut in as_completed(futures):
                u, t = fut.result()
                album_titles[u] = t

        for n, album in enumerate(albums, 1):
            title = album_titles[album]
            topic_id, topico_nome = uploader.ask_topic_for_album(title, n, len(albums))
            album_decisions.append((album, title, topic_id, topico_nome))
        
        print("\n" + "="*50)
        print("  INICIANDO DOWNLOADS E UPLOADS AUTOMATICOS")
        print("="*50)
        
        for n, (album, title, topic_id, topico_nome) in enumerate(album_decisions, 1):
            if topic_id == "skip":
                print(f"\n[{n}/{len(albums)}] Pulando album: {title}")
                with open(HISTORY_FILE, "a", encoding="utf-8") as f: f.write(album + "\n")
                continue
            
            print(f"\n[{n}/{len(albums)}] Baixando: {title}")
            _, folder, files = process_album(album, args.output, args.skip_images, session, workers=args.workers)
            
            if topic_id != "local" and files:
                print(f"  -> Enviando para o Telegram (Destino: {topico_nome})...")
                ok = uploader.upload_files(topic_id, files, caption=title)
                
                if ok:
                    with open(HISTORY_FILE, "a", encoding="utf-8") as f: f.write(album + "\n")
                    if getattr(args, 'clean_local', False):
                        print(f"  -> Apagando arquivos locais (--clean-local ativado)...")
                        try:
                            import shutil
                            shutil.rmtree(folder)
                        except Exception as e:
                            print(f"  [AVISO] Nao foi possivel apagar {folder}: {e}")
            else:
                with open(HISTORY_FILE, "a", encoding="utf-8") as f: f.write(album + "\n")
    else:
        for n, album in enumerate(albums, 1):
            print(f"\n[{n}/{len(albums)}]")
            process_album(album, args.output, args.skip_images, session, workers=args.workers)
            with open(HISTORY_FILE, "a", encoding="utf-8") as f: f.write(album + "\n")

    print("\nFinalizado.")

if __name__ == "__main__":
    main()
