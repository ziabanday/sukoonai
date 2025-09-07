# ingest/fetch.py
import httpx, time, yaml
from pathlib import Path

# Make sure raw data folder exists
RAW = Path("data/raw")
RAW.mkdir(parents=True, exist_ok=True)

# Load curated sources from YAML
with open("data/sources.yml", "r", encoding="utf-8") as f:
    sources = yaml.safe_load(f)

def fetch(url, fname):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/114.0 Safari/537.36"
    }
    # follow_redirects=True lets us handle 301/302 automatically
    r = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
    r.raise_for_status()
    (RAW/fname).write_bytes(r.content)

for s in sources:
    fname = f"{s['name']}.html"
    if not (RAW/fname).exists():
        try:
            print("Fetching:", s["url"])
            fetch(s["url"], fname)
            time.sleep(1.0)  # polite delay
        except Exception as e:
            print("FAILED:", s["name"], e)
    else:
        print("Already exists:", fname)
