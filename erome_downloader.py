"""
Erome Downloader
----------------
Baixa todos os videos (e opcionalmente imagens) de um album publico do Erome.

Uso:
    python erome_downloader.py https://www.erome.com/a/XXXXXX
    python erome_downloader.py https://www.erome.com/a/XXXXXX -o "C:/Downloads"
    python erome_downloader.py urls.txt              (arquivo com 1 URL por linha)
    python erome_downloader.py https://www.erome.com/a/XXXXXX --skip-images

Dependencias: requests, beautifulsoup4  (veja requirements_erome.txt)
"""

import argparse
import os
import re
import sys
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HOST = "https://www.erome.com"

# User-Agent de navegador real ajuda a evitar bloqueios
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
}


def sanitize(name: str) -> str:
    """Remove caracteres invalidos para nome de pasta/arquivo no Windows."""
    name = re.sub(r'[<>:"/\\|?*\n\r\t]', "_", name).strip()
    return name[:120] or "erome_album"


def get_album_media(album_url: str, session: requests.Session):
    """Retorna (titulo, [urls_de_video], [urls_de_imagem]) de um album."""
    resp = session.get(album_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Titulo do album
    title_tag = soup.find("meta", attrs={"property": "og:title"})
    title = title_tag["content"] if title_tag and title_tag.get("content") else album_url.rstrip("/").split("/")[-1]

    videos, images = [], []

    # Videos: <video><source src="..."></video>
    for source in soup.select("video source"):
        src = source.get("src")
        if src:
            videos.append(src)

    # Imagens: <img class="img-back" data-src="...">
    for img in soup.select("img.img-back"):
        src = img.get("data-src") or img.get("src")
        if src:
            images.append(src)

    # Remove duplicatas preservando ordem
    videos = list(dict.fromkeys(videos))
    images = list(dict.fromkeys(images))
    return title, videos, images


def download_file(url: str, dest_path: str, referer: str, session: requests.Session):
    """Baixa um arquivo com o Referer correto (obrigatorio no Erome)."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        print(f"    [pulado] ja existe: {os.path.basename(dest_path)}")
        return True

    headers = dict(HEADERS)
    headers["Referer"] = referer  # <- sem isso o Erome devolve 403

    try:
        with session.get(url, headers=headers, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            done = 0
            tmp = dest_path + ".part"
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = done * 100 // total
                        print(f"\r    baixando {os.path.basename(dest_path)} {pct}%", end="")
            print()
            os.replace(tmp, dest_path)
        return True
    except Exception as e:
        print(f"\n    [ERRO] {url} -> {e}")
        if os.path.exists(dest_path + ".part"):
            os.remove(dest_path + ".part")
        return False


def process_album(album_url: str, out_root: str, skip_images: bool, session: requests.Session):
    album_url = album_url.strip()
    if not album_url:
        return
    if not album_url.startswith("http"):
        album_url = HOST + ("/" if not album_url.startswith("/") else "") + album_url

    print(f"\n=== Album: {album_url} ===")
    try:
        title, videos, images = get_album_media(album_url, session)
    except Exception as e:
        print(f"  [ERRO] nao foi possivel ler o album: {e}")
        return

    folder = os.path.join(out_root, sanitize(title))
    os.makedirs(folder, exist_ok=True)
    print(f"  Titulo: {title}")
    print(f"  Videos: {len(videos)} | Imagens: {len(images)}")
    print(f"  Salvando em: {folder}")

    items = list(videos)
    if not skip_images:
        items += images

    ok = 0
    for i, media_url in enumerate(items, 1):
        ext = os.path.splitext(urlparse(media_url).path)[1] or ".bin"
        dest = os.path.join(folder, f"{i:03d}{ext}")
        print(f"  [{i}/{len(items)}]")
        if download_file(media_url, dest, referer=album_url, session=session):
            ok += 1
    print(f"  Concluido: {ok}/{len(items)} arquivos.")


def main():
    parser = argparse.ArgumentParser(description="Baixa midias de albuns publicos do Erome.")
    parser.add_argument("target", help="URL do album OU caminho de um .txt com varias URLs")
    parser.add_argument("-o", "--output", default="erome_downloads", help="Pasta de destino")
    parser.add_argument("--skip-images", action="store_true", help="Baixar somente videos")
    args = parser.parse_args()

    # Lista de albuns: arquivo .txt ou URL unica
    if os.path.isfile(args.target):
        with open(args.target, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        urls = [args.target]

    os.makedirs(args.output, exist_ok=True)
    session = requests.Session()

    for url in urls:
        process_album(url, args.output, args.skip_images, session)

    print("\nFinalizado.")


if __name__ == "__main__":
    main()
