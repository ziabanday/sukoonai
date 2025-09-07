#!/usr/bin/env bash
# SukoonAI scaffold bootstrapper
# Usage (Windows Git Bash/macOS/Linux):
#   bash template.sh

set -euo pipefail

# Create folders
mkdir -p app/routers app/services app/utils app/models
mkdir -p data/raw/medlineplus data/raw/gem data/processed/chunks data/indices/faiss
mkdir -p scripts tests web/static notebooks infra docs packages sandbox

# Touch placeholder files (only if not exist)
[ -f .env.example ] || cat > .env.example <<'ENV'
# Copy this file to .env and fill in your secrets.
# Never commit .env to git.

# --- Required ---
SUPABASE_REST_URL=https://<your-project-ref>.supabase.co/rest/v1
SUPABASE_ANON_KEY=<YOUR_SUPABASE_ANON_KEY>
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>

# --- Optional overrides (sane defaults below) ---
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
OPENAI_TIMEOUT_SECS=15.0
LOG_LEVEL=INFO
PORT=8001
ENV

[ -f requirements.txt ] || cat > requirements.txt <<'REQ'
fastapi>=0.115
uvicorn[standard]>=0.30
httpx>=0.27
pydantic>=2.7
python-dotenv>=1.0
pyyaml>=6.0
langchain>=0.2
langchain-community>=0.2
# optional/light graph layer
langgraph>=0.1
tiktoken>=0.7
requests>=2.31
beautifulsoup4>=4.12
aiofiles>=23.2
REQ

# Starter URL list (example corpus)
[ -f data/raw/medlineplus_urls.txt ] || cat > data/raw/medlineplus_urls.txt <<'URLS'
https://medlineplus.gov/diabetes.html
https://medlineplus.gov/asthma.html
https://medlineplus.gov/hypertension.html
URLS

echo "SukoonAI skeleton ready. Next steps:"
echo "1) Create/activate a Python 3.11+ env (conda/mamba/venv)."
echo "2) pip install -r requirements.txt"
echo "3) cp .env.example .env  # then put your real keys (DO NOT COMMIT .env)"
echo "4) (optional) python scripts/ingest.py  # if you build a FAISS index locally"
echo "5) uvicorn app.api.main:app --reload --port \${PORT:-8001}"
