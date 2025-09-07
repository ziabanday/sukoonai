# SukoonAI — Medical Evidence Navigator (MVP)

A hands‑on, minimal, **FastAPI + LangChain + FAISS** chatbot that answers basic medical questions by retrieving from a small, curated corpus (starting with **MedlinePlus** and any Gale EoM content you have rights to use).

> **Why this MVP?**  
> - Keep **LLM cost low** by doing retrieval locally with **FAISS**.  
> - Use **transparent, trustworthy sources** to **reduce hallucinations**.  
> - Ship a simple **FastAPI** app you can demo to HSA partners and iterate quickly.

## Architecture (bird’s‑eye view)

```
User → FastAPI (/chat) → RAG Service
                         ├─ Retriever (FAISS, local)
                         │   └─ Docs (MedlinePlus + GEM you provide)
                         └─ LLM (OpenAI gpt-4o-mini)
```

- **Retriever:** FAISS vector store built from chunked pages.  
- **LLM:** `gpt-4o-mini` for balance of quality & cost.  
- **Data:** Start with public MedlinePlus pages. For **Gale Encyclopedia of Medicine (GEM)**, only ingest content you are licensed to use.

## Quickstart (10–15 min)

### 0) Prereqs

- Python **3.11+** (Miniforge/Conda or venv)
- Git Bash (on Windows) or any Bash shell (macOS/Linux)
- An **OpenAI API key**

### 1) Make the project

```bash
# (optional) create a new folder for repos
# mkdir -p ~/Projects && cd ~/Projects

# Unzip the scaffold if you downloaded it, otherwise init manually:
bash template.sh
```

### 2) Create & activate environment

**Conda/Miniforge (recommended):**
```bash
conda create -n SukoonAI python=3.11 -y
conda activate SukoonAI
```

**OR venv:**
```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# OR on Windows PowerShell: .venv\\Scripts\\Activate.ps1
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

> **Windows FAISS tip:** If `faiss-cpu` fails via pip, try:  
> `conda install -c pytorch faiss-cpu`

### 4) Configure secrets
```bash
cp .env.example .env
# edit .env and paste your OPENAI_API_KEY
```

### 5) Build the local index
```bash
# Seed URLs already in data/raw/medlineplus_urls.txt
python scripts/ingest.py
```
This fetches a few MedlinePlus pages, chunks the text, then writes the FAISS index to `data/indices/faiss/`.

### 6) Run the app
```bash
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000 in your browser to use the simple chat UI.

---

## Repository layout

```
app/
  main.py                 # FastAPI app & static hosting
  routers/chat.py         # /chat endpoint
  services/rag.py         # Retrieval + generation logic
  utils/env.py            # .env loader & validations
  models/schemas.py       # Pydantic request/response models
data/
  raw/                    # Source HTML/TXT
  processed/chunks/       # Chunked text (for debugging)
  indices/faiss/          # Saved FAISS store
scripts/
  fetch_medlineplus.py    # Pulls pages listed in data/raw/medlineplus_urls.txt
  fetch_gem_placeholder.md# Licensing note for GEM
  ingest.py               # Orchestrates fetch → chunk → embed → index
  verify_env.py           # Checks .env and API connectivity
web/
  index.html              # Minimal chat UI
  static/styles.css
  static/script.js
```

## Strengths & Limitations (investor/partner‑friendly)

**Strengths**
- **Trustworthy sources** (MedlinePlus today; extensible to HSA materials)
- **Lower cost** with local FAISS retrieval (fewer tokens to LLM)
- **Explainable**: returns citations for retrieved chunks

**Limitations (MVP)**
- **Small corpus** → may say “I don’t know” for out‑of‑scope queries
- **No images/voice** yet (text‑only Q&A)
- **GEM ingestion requires proper licensing**
- **RAG gaps**: if a fact isn’t in the chunks/index, the model won’t know it

## Common errors & fixes

- **`faiss` install fails on Windows:** use `conda install -c pytorch faiss-cpu`  
- **`OPENAI_API_KEY not set`:** copy `.env.example` to `.env` and fill in key  
- **`RateLimitError`**: slow down; add retry/backoff; upgrade plan if needed  
- **`404 /chat`**: start server with `uvicorn app.main:app --reload`  
- **Blank answers**: ensure you ran `python scripts/ingest.py` and the index files exist

## Roadmap (next 2–6 weeks)

- Add **HSA course PDFs/notes** (with permission) to the corpus
- Add **admin CLI**: re‑ingest with one command
- Add **guardrails** (moderation + safety disclaimers in prompt and UI)
- Add **basic analytics** (queries/day, top topics)
- Optional: **Urdu interface** (UI toggle + transliteration helper)

---

## Chat-2 backend retrieval note

In Chat-2 we introduced **Supabase Postgres + pgvector** for server-side retrieval while keeping FAISS available for local experiments. The API below uses a PostgREST **RPC** (`public.match_chunks`) to perform cosine search over `chunk_embeddings` and return short highlighted snippets.

## Vector Retrieval API — `/v1/search/vector`

This endpoint performs a pgvector cosine search over `chunk_embeddings`, joins to `chunks` and `documents`, then returns short highlighted snippets.

**Route**
```
GET /v1/search/vector
```

**Query params**

| Name | Type | Default | Notes |
|---|---:|---:|---|
| `q` | string | — | Required. User query to embed. |
| `k` | int | 6 | Effective range 1–20 (clamped). |
| `org_id` | string | `"demo"` | Tenant scope; anon reads limited to `org_id='demo'` by RLS. |
| `doc_filters` | JSON string | — | Optional: `{"title":"substring","source_url":"...","external_id":"..."}` |
| `min_score` | float | — | Optional minimum cosine similarity (0..1). |

**Response shape (array)**
```json
[
  {
    "score": 0.78,
    "content": "…snippet with **bold** keyword matches…",
    "ord": 3,
    "document": {
      "title": "Sleep Hygiene Basics",
      "source_url": "https://example.org/sleep",
      "external_id": "ext-1"
    }
  }
]
```

**Behavior**
- Embeds `q` with **`text-embedding-3-small`** (1536-dim).
- Cosine similarity via PostgREST RPC `public.match_chunks`.
- Snippets are ≤ ~500 chars with light `**bold**` highlighting of query terms.
- Sorted by score desc; `k` clamped to ≤20; `min_score` applied in RPC.
- **No results** → `[]` (never 404).
- Upstream embedding errors → HTTP **502** with message.

**Prereqs (.env)**
```
SUPABASE_REST_URL=https://<your-project-ref>.supabase.co/rest/v1
SUPABASE_ANON_KEY=<YOUR_SUPABASE_ANON_KEY>   # never commit real keys
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>            # required for live embedding calls
# optional overrides:
# EMBEDDING_MODEL=text-embedding-3-small
# EMBEDDING_DIM=1536
# OPENAI_TIMEOUT_SECS=15.0
```

**Run the API locally**
```bash
uvicorn app.api.main:app --reload --port 8001
# Health checks
curl -s http://127.0.0.1:8001/health
curl -s http://127.0.0.1:8001/debug/sb
```

**Quick test calls**

_PowerShell (`irm`):_
```powershell
# Basic
irm "http://127.0.0.1:8001/v1/search/vector?q=sleep%20anxiety&k=5"

# With filters & min_score
$filters = '{"title":"sleep","external_id":"ext-1"}'
$u = "http://127.0.0.1:8001/v1/search/vector?q=breathing%20for%20sleep&k=6&min_score=0.65&doc_filters=$([uri]::EscapeDataString($filters))"
irm $u
```

_curl (bash):_
```bash
curl -s "http://127.0.0.1:8001/v1/search/vector?q=sleep%20anxiety&k=5" | jq .

FILTERS='{"title":"sleep","external_id":"ext-1"}'
curl -s "http://127.0.0.1:8001/v1/search/vector?q=breathing%20for%20sleep&k=6&min_score=0.65&doc_filters=$(python - <<'PY'
import urllib.parse,sys,json
print(urllib.parse.quote(sys.stdin.read()))
PY
<<<"$FILTERS")" | jq .
```

**Security (RLS)**
- `conditions`, `symptoms`, `topic_links`: anon read allowed (MVP).
- `documents`, `chunks`, `chunk_embeddings`: anon reads are **restricted to `org_id='demo'`**. The ingest service uses `service_role` and bypasses RLS.

**Troubleshooting**
- **401/403/empty results:** Ensure rows in `documents/chunks/chunk_embeddings` have `org_id='demo'` (for anon access) and policies exist.  
- **502 OpenAI error:** Check `OPENAI_API_KEY` in `.env` and network access.  
- **Slow search:** after bulk ingest, run `ANALYZE` and ensure IVFFlat index exists; tune `ivfflat.probes` (e.g., 10).

---

## License & Content Rights

This code is MIT‑licensed. You are responsible for ensuring you have legal rights to ingest and serve any **content** (e.g., GEM). MedlinePlus pages are public, but still respect their terms of use.
