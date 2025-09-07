#!/usr/bin/env bash
# SukoonAI scaffold bootstrapper
# Usage (Windows Git Bash/macOS/Linux):
#   bash template.sh

set -euo pipefail

# Create folders
mkdir -p app/routers app/services app/utils app/models
mkdir -p data/raw/medlineplus data/raw/gem data/processed/chunks data/indices/faiss
mkdir -p scripts tests web/static notebooks

# Touch placeholder files (only if not exist)
[ -f .env.example ] || cat > .env.example <<'ENV'
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-large
LOG_LEVEL=INFO
PORT=8000
ENV

[ -f requirements.txt ] || cat > requirements.txt <<'REQ'
fastapi>=0.115
uvicorn[standard]>=0.30
langchain>=0.2
langchain-community>=0.2
langchain-openai>=0.1
faiss-cpu>=1.8
python-dotenv>=1.0
pydantic>=2.7
tiktoken>=0.7
requests>=2.31
beautifulsoup4>=4.12
aiofiles>=23.2
httpx>=0.27
REQ

# Starter URL list
[ -f data/raw/medlineplus_urls.txt ] || cat > data/raw/medlineplus_urls.txt <<'URLS'
https://medlineplus.gov/diabetes.html
https://medlineplus.gov/asthma.html
https://medlineplus.gov/hypertension.html
URLS

echo "SukoonAI skeleton created. Next steps:"
echo "1) Create and activate a Python 3.11+ env (conda/mamba/venv)."
echo "2) pip install -r requirements.txt"
echo "3) cp .env.example .env  # then put your keys"
echo "4) python scripts/ingest.py  # builds the FAISS index"
echo "5) uvicorn app.main:app --reload"
