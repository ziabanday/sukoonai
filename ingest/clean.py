# ingest/clean.py
from pathlib import Path
from bs4 import BeautifulSoup
import re
import csv
from datetime import datetime

RAW = Path("data/raw")
CLEAN = Path("data/clean")
CLEAN.mkdir(parents=True, exist_ok=True)
REPORT = Path("data/clean_report.csv")

# Phrases & patterns to strip explicitly
NOISE_PATTERNS = [
    r"On this page.*",        # MedlinePlus menu
    r"Skip to main content",  # WHO pages
    r"Regions.*",             # WHO region links
    r"Select language.*",     # WHO language selector
    r"Basics", r"Summary", r"Start Here",  # MedlinePlus page menus
]

def clean_html(html: str) -> str:
    """Clean HTML content and return plain text."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove common noisy sections
    for tag in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()

    # Remove elements with nav-like classes or ids
    for noisy in soup.find_all(attrs={"class": re.compile(r"(nav|menu|breadcrumb)", re.I)}):
        noisy.decompose()
    for noisy in soup.find_all(attrs={"id": re.compile(r"(nav|menu|breadcrumb)", re.I)}):
        noisy.decompose()

    text = soup.get_text("\n", strip=True)

    # Remove noisy patterns
    for pat in NOISE_PATTERNS:
        text = re.sub(pat, "", text, flags=re.I)

    # Collapse multiple newlines
    text = re.sub(r"\n{2,}", "\n\n", text)

    return text.strip()

def process_file(path: Path, writer, timestamp):
    """Clean one HTML file, save as Markdown, and log word counts."""
    raw_html = path.read_text(encoding="utf-8", errors="ignore")

    # Word count before cleaning
    raw_text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)
    raw_words = len(raw_text.split())

    # Cleaned text
    cleaned = clean_html(raw_html)
    cleaned_words = len(cleaned.split())

    out_path = CLEAN / (path.stem + ".md")
    out_path.write_text(cleaned, encoding="utf-8")

    removed = raw_words - cleaned_words
    print(f"✅ Cleaned {path.name} → {out_path.name}")
    print(f"   Words kept: {cleaned_words}, removed: {removed} (from {raw_words})")

    # Append row to CSV
    writer.writerow({
        "timestamp": timestamp,
        "file": path.name,
        "output_file": out_path.name,
        "raw_words": raw_words,
        "cleaned_words": cleaned_words,
        "removed_words": removed
    })

if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    file_exists = REPORT.exists()
    with REPORT.open("a", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["timestamp", "file", "output_file", "raw_words", "cleaned_words", "removed_words"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header if file is new
        if not file_exists:
            writer.writeheader()

        # Write a blank row as run-separator
        if file_exists:
            csvfile.write("\n")

        for html_file in RAW.glob("*.html"):
            process_file(html_file, writer, timestamp)
