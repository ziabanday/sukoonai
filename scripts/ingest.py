"""
Ingest pipeline:
- Fetch MedlinePlus pages listed in data/raw/medlineplus_urls.txt
- Read TXT files from data/raw/{medlineplus, gem}
- Chunk, embed, and build FAISS index at data/indices/faiss/
"""
import pathlib
import os

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from scripts.fetch_medlineplus import main as fetch_medlineplus  # reuse
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_DIRS = [ROOT / "data" / "raw" / "medlineplus", ROOT / "data" / "raw" / "gem"]
CHUNK_OUT = ROOT / "data" / "processed" / "chunks"
INDEX_DIR = ROOT / "data" / "indices" / "faiss"

def read_all_txt():
    records = []
    for d in RAW_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        for path in d.glob("*.txt"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            records.append((text, str(path)))
    return records

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing. Create .env from .env.example")

    # Step 1: fetch MedlinePlus (safe & public)
    fetch_medlineplus()

    # Step 2: load raw text files
    records = read_all_txt()
    if not records:
        raise RuntimeError("No raw .txt files found under data/raw/.")

    # Step 3: chunk
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks, metas = [], []
    CHUNK_OUT.mkdir(parents=True, exist_ok=True)

    for text, source in records:
        docs = splitter.create_documents([text], metadatas=[{"source": source}])
        for i, d in enumerate(docs):
            chunks.append(d.page_content)
            metas.append({"source": source, "chunk": i})

    # Optional: save chunks for debugging
    with open(CHUNK_OUT / "chunks_preview.txt", "w", encoding="utf-8") as f:
        for c, m in zip(chunks[:20], metas[:20]):
            f.write(f"### {m}\\n{c}\\n\\n")

    # Step 4: embeddings & FAISS
    embeddings = OpenAIEmbeddings(api_key=api_key, model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"))
    vs = FAISS.from_texts(chunks, embedding=embeddings, metadatas=metas)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vs.save_local(INDEX_DIR.as_posix())
    print(f"Saved FAISS index to {INDEX_DIR}")

if __name__ == "__main__":
    main()
