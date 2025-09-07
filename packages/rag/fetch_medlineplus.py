"""
Fetch MedlinePlus pages from a URL list and save cleaned text files.
Usage:
    python scripts/fetch_medlineplus.py
"""
import pathlib
import time
import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
URL_LIST = ROOT / "data" / "raw" / "medlineplus_urls.txt"
OUT_DIR = ROOT / "data" / "raw" / "medlineplus"

HEADERS = {"User-Agent": "SukoonAI-MVP/0.1 (https://example.com)"}

def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["nav", "footer", "script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not URL_LIST.exists():
        print(f"URL list not found: {URL_LIST}")
        return

    for url in URL_LIST.read_text(encoding="utf-8").splitlines():
        url = url.strip()
        if not url or url.startswith("#"):
            continue
        print(f"Fetching {url} ...")
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        text = clean_text(r.text)
        fname = (url.split("/")[-1] or "index").split("?")[0]
        out_path = OUT_DIR / f"{fname}.txt"
        out_path.write_text(text, encoding="utf-8")
        time.sleep(1)  # be polite
    print(f"Saved cleaned pages to {OUT_DIR}")

if __name__ == "__main__":
    main()
