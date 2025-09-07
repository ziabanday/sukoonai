import os
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

# Paths
CLEAN_DIR = "data/clean"
INDEX_DIR = "data/index"
INDEX_PATH = os.path.join(INDEX_DIR, "index")

# Ensure index folder exists
os.makedirs(INDEX_DIR, exist_ok=True)

def load_cleaned_docs():
    docs = []
    for fname in os.listdir(CLEAN_DIR):
        if fname.endswith(".md"):
            with open(os.path.join(CLEAN_DIR, fname), "r", encoding="utf-8") as f:
                text = f.read()
                docs.append(Document(page_content=text, metadata={"source": fname}))
    return docs

def main():
    print("[INFO] Loading cleaned documents from:", CLEAN_DIR)
    documents = load_cleaned_docs()
    print(f"[INFO] Loaded {len(documents)} documents")

    if not documents:
        print("[ERROR] No cleaned documents found. Run clean.py first.")
        return

    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)
    print(f"[INFO] Split into {len(splits)} chunks")

    # Create embeddings
    embeddings = OpenAIEmbeddings()

    # Build FAISS index
    db = FAISS.from_documents(splits, embeddings)

    # Save index
    db.save_local(INDEX_PATH)
    print(f"[SUCCESS] Saved FAISS index with {len(splits)} chunks to {INDEX_PATH}")

if __name__ == "__main__":
    main()
