# app/api/main.py

import os
import re
import json
import math
import urllib.parse
from typing import Any, Dict, List, Optional
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Ensure .env is loaded early (before reading env vars)
from dotenv import load_dotenv
load_dotenv()

# Optional: file-based YAML assessments (PHQ-9 / GAD-7, etc.)
try:
    import yaml  # pip install pyyaml
except Exception:
    yaml = None

app = FastAPI(title="SukoonAI API")

# --- ENV & Supabase helpers ---------------------------------------------------
SUPABASE_REST_URL = os.getenv("SUPABASE_REST_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
OPENAI_TIMEOUT_SECS = float(os.getenv("OPENAI_TIMEOUT_SECS", "15.0"))

# Path to your agent config pack (defaults to repo-relative packages/agent)
AGENT_DIR = Path(os.getenv("AGENT_DIR", "packages/agent")).resolve()


def _sb_headers_anon() -> Dict[str, str]:
    if not SUPABASE_ANON_KEY:
        raise RuntimeError("SUPABASE_ANON_KEY missing")
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _sb_headers_service() -> Dict[str, str]:
    # For server-side writes only (e.g., ingest). Never expose to clients.
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing")
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }


async def _get_json(url: str, headers: Dict[str, str]) -> Any:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()


async def _post_json(url: str, payload: Any, headers: Dict[str, str]) -> Any:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            # fixed minor bug here (detail=r.text)
            raise HTTPException(status_code=r.status_code, detail=r.text)
        # PostgREST upsert returns inserted rows if "return=representation" is used.
        # Here we don't strictly need them; you can add "?return=representation".
        return r.json() if r.text else {}


# --- Agent config loader (profile, policies, assessments, interventions) -------
class AgentConfigCache:
    def __init__(self, root: Path):
        self.root = root
        self.sig: Optional[str] = None
        self.cache: Dict[str, Any] = {}

    def _signature(self) -> str:
        """Create an mtime-based signature across key files to know when to reload."""
        files = [
            self.root / "agent_profile.json",
            self.root / "policies.json",
            self.root / "interventions" / "catalog.json",
        ]
        files += list((self.root / "assessments").glob("*.yaml"))
        mtimes: List[str] = []
        for f in files:
            if f.exists():
                mtimes.append(str(int(f.stat().st_mtime)))
        return "|".join(sorted(mtimes))

    def _load_json(self, p: Path) -> Any:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def _load_yaml(self, p: Path) -> Any:
        if not p.exists():
            return None
        if yaml is None:
            raise RuntimeError("PyYAML not installed. Please add 'pyyaml' to requirements.txt.")
        return yaml.safe_load(p.read_text(encoding="utf-8"))

    def load(self, force: bool = False) -> Dict[str, Any]:
        sig = self._signature()
        if (not force) and self.sig == sig and self.cache:
            return self.cache

        profile = self._load_json(self.root / "agent_profile.json") or {}
        policies = self._load_json(self.root / "policies.json") or {}
        interventions = self._load_json(self.root / "interventions" / "catalog.json") or {}

        assessments_dir = self.root / "assessments"
        assessments: Dict[str, Any] = {}
        if assessments_dir.exists():
            for y in assessments_dir.glob("*.yaml"):
                obj = self._load_yaml(y)
                if obj and isinstance(obj, dict) and obj.get("id"):
                    assessments[obj["id"]] = obj

        self.cache = {
            "profile": profile,
            "policies": policies,
            "assessments": assessments,
            "interventions": interventions,
        }
        self.sig = sig
        return self.cache


AGENT = AgentConfigCache(AGENT_DIR)

# --- Health -------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "supabase_env": bool(SUPABASE_REST_URL and SUPABASE_ANON_KEY),
        "openai_env": bool(os.getenv("OPENAI_API_KEY")),
        "agent_dir": str(AGENT_DIR),
    }

# --- DEBUG: show what env the server actually loaded --------------------------
@app.get("/debug/sb")
def debug_sb():
    anon = os.getenv("SUPABASE_ANON_KEY", "")
    srv  = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    return {
        "rest_url": os.getenv("SUPABASE_REST_URL", ""),
        "anon_len": len(anon), "anon_prefix": anon[:12],
        "srv_len": len(srv),  "srv_prefix": srv[:12],
    }


# --- Agent config (read-only) --------------------------------------------------
# Example: GET /agent/config
#          GET /agent/config?reload=1  -> force reload from disk
@app.get("/agent/config")
async def agent_config(reload: int = 0):
    try:
        cfg = AGENT.load(force=bool(reload))
        summary = {
            "name": cfg.get("profile", {}).get("name"),
            "languages": cfg.get("profile", {}).get("languages", []),
            "assessments": sorted(list(cfg.get("assessments", {}).keys())),
            "interventions": sorted(list(cfg.get("interventions", {}).keys()))
            if isinstance(cfg.get("interventions"), dict)
            else [],
        }
        return {"summary": summary, "config": cfg}
    except Exception as e:
        raise HTTPException(500, f"Agent config error: {e}")


# --- Existing: Conditions search (kept for parity) ----------------------------
# Example: GET /db/conditions/search?q=dep&limit=5
@app.get("/db/conditions/search")
async def search_conditions(q: str = Query(""), limit: int = Query(10, ge=1, le=50)):
    """
    Case-insensitive 'contains' search on conditions.name.
    Requires a table `public.conditions(name text, ... )`.
    """
    if not SUPABASE_REST_URL:
        raise HTTPException(500, "SUPABASE_REST_URL not configured")
    params = {
        "select": "id,name,slug,short_def",
        "name": f"ilike.*{q}*",
        "limit": str(limit),
        "order": "name.asc",
    }
    url = f"{SUPABASE_REST_URL}/conditions?{urllib.parse.urlencode(params)}"
    return await _get_json(url, _sb_headers_anon())


# --- NEW: Symptoms search (mirrors conditions) --------------------------------
# Example: GET /db/symptoms/search?q=sleep&limit=5
@app.get("/db/symptoms/search")
async def search_symptoms(q: str = Query(""), limit: int = Query(10, ge=1, le=50)):
    """
    Case-insensitive 'contains' search on symptoms.name.
    Requires `public.symptoms(name text, ... )` (from CKG-lite).
    """
    if not SUPABASE_REST_URL:
        raise HTTPException(500, "SUPABASE_REST_URL not configured")
    params = {
        "select": "id,name,slug",
        "name": f"ilike.*{q}*",
        "limit": str(limit),
        "order": "name.asc",
    }
    url = f"{SUPABASE_REST_URL}/symptoms?{urllib.parse.urlencode(params)}"
    return await _get_json(url, _sb_headers_anon())


# --- NEW: Topic links lookup ---------------------------------------------------
# Example: GET /db/topic-links?entity_type=condition&entity_id=depression
# Optional: &system=medlineplus
@app.get("/db/topic-links")
async def get_topic_links(
    entity_type: str = Query(..., description="e.g., 'condition' | 'symptom'"),
    entity_id: str = Query(..., description="stable id/slug of the entity"),
    system: Optional[str] = Query(None, description="link provider/system label"),
):
    """
    Returns rows from public.topic_links filtered by entity_type, entity_id (and optional system).
    Chat-1 created `topic_links` with UNIQUE(entity_type, entity_id, system) so we can safely upsert.
    """
    if not SUPABASE_REST_URL:
        raise HTTPException(500, "SUPABASE_REST_URL not configured")
    base = f"{SUPABASE_REST_URL}/topic_links"
    params = {
        "select": "entity_type,entity_id,system,url,label,meta",
        "entity_type": f"eq.{entity_type}",
        "entity_id": f"eq.{entity_id}",
        "order": "system.asc,label.asc",
    }
    if system:
        params["system"] = f"eq.{system}"
    url = f"{base}?{urllib.parse.urlencode(params)}"
    return await _get_json(url, _sb_headers_anon())


# --- NEW: Ingest route for chunks + embeddings (server-only) ------------------
# This route expects SERVICE_ROLE on server; do NOT call from untrusted clients.
class IngestChunk(BaseModel):
    # Document-level (idempotency via source_url or external_id)
    source_url: Optional[str] = None
    external_id: Optional[str] = None
    title: Optional[str] = None
    lang: Optional[str] = None
    org_id: Optional[str] = "demo"
    # Chunk-level
    content: str
    ord: int
    token_count: Optional[int] = None
    # Embedding (vector as Python list[float]; must match table dimension)
    embedding: Optional[List[float]] = None


class IngestPayload(BaseModel):
    items: List[IngestChunk]
    # If true, skip inserting embeddings even if provided (useful for dry runs)
    skip_embeddings: bool = False


@app.post("/v1/ingest")
async def ingest_chunks(payload: IngestPayload):
    """
    Upserts into:
      - documents (unique by source_url or external_id)
      - chunks (unique by doc_id + ord)
      - chunk_embeddings (1:1 with chunk_id)
    Uses Supabase PostgREST with `Prefer: resolution=merge-duplicates` and on_conflict params.
    """
    if not SUPABASE_REST_URL:
        raise HTTPException(500, "SUPABASE_REST_URL not configured")
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(500, "SERVICE_ROLE key not configured")

    svc_headers = _sb_headers_service()

    # Helper: upsert a single document and return its id
    async def upsert_document(item: IngestChunk) -> str:
        doc_body = {
            "source_url": item.source_url,
            "external_id": item.external_id,
            "title": item.title,
            "lang": item.lang,
            "org_id": item.org_id,
        }
        # Remove Nones (PostgREST handles nulls, but we keep it tidy)
        doc_body = {k: v for k, v in doc_body.items() if v is not None}

        # Choose unique column for on_conflict based on what we have
        if "external_id" in doc_body:
            on_conflict = "external_id"
        elif "source_url" in doc_body:
            on_conflict = "source_url"
        else:
            # Fall back to creating a new doc row each time (not ideal)
            on_conflict = "id"

        url = f"{SUPABASE_REST_URL}/documents?on_conflict={on_conflict}&return=representation"
        out = await _post_json(url, [doc_body], svc_headers)
        # Return inserted/merged id
        return out[0]["id"]

    # Helper: upsert chunk and (optionally) its embedding
    async def upsert_chunk_and_embedding(doc_id: str, item: IngestChunk):
        chunk_body = {
            "doc_id": doc_id,
            "ord": item.ord,
            "content": item.content,
            "token_count": item.token_count,
            "org_id": item.org_id,
        }
        chunk_body = {k: v for k, v in chunk_body.items() if v is not None}
        chunk_url = f"{SUPABASE_REST_URL}/chunks?on_conflict=doc_id,ord&return=representation"
        chunk_out = await _post_json(chunk_url, [chunk_body], svc_headers)
        chunk_id = chunk_out[0]["id"]

        if not payload.skip_embeddings and item.embedding is not None:
            emb_body = {"chunk_id": chunk_id, "embedding": item.embedding, "org_id": item.org_id}
            emb_url = f"{SUPABASE_REST_URL}/chunk_embeddings?on_conflict=chunk_id&return=representation"
            await _post_json(emb_url, [emb_body], svc_headers)
        return {"chunk_id": chunk_id}

    results: List[Dict[str, Any]] = []
    # Simple pass: upsert doc per item; PostgREST merge keeps it idempotent.
    for item in payload.items:
        doc_id = await upsert_document(item)
        res = await upsert_chunk_and_embedding(doc_id, item)
        results.append(res)
    return {"status": "ok", "inserted": results}


# ================================ Chat-2 ======================================
# A) Retrieval API (Vector Search)
# ------------------------------------------------------------------------------
class DocumentInfo(BaseModel):
    title: Optional[str] = None
    source_url: Optional[str] = None
    external_id: Optional[str] = None


class VectorHit(BaseModel):
    score: float
    content: str
    ord: int
    document: DocumentInfo


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _bold_keywords(text: str, query: str) -> str:
    """
    Very simple keyword highlighter: bold exact (case-insensitive) words from q.
    We keep it intentionally dumb/safe for MVP.
    """
    if not text or not query:
        return text
    out = text
    # Tokenize q into alphanumeric terms (min length 3 to reduce noise)
    terms = [t for t in re.findall(r"[A-Za-z0-9]+", query) if len(t) >= 3]
    if not terms:
        return out
    # Replace each term with **term** (case-insensitive)
    for t in sorted(set(terms), key=len, reverse=True):
        pattern = re.compile(re.escape(t), re.IGNORECASE)
        out = pattern.sub(lambda m: f"**{m.group(0)}**", out)
    return out


def _make_snippet(content: str, query: str, max_len: int = 480) -> str:
    """
    Truncate to ~max_len characters around the first occurrence of any query term.
    """
    text = _normalize_ws(content)
    if len(text) <= max_len:
        return _bold_keywords(text, query)

    # Find a window around the first occurrence
    terms = [t for t in re.findall(r"[A-Za-z0-9]+", query) if len(t) >= 3]
    idx = -1
    for t in terms:
        i = text.lower().find(t.lower())
        if i != -1:
            idx = i
            break
    if idx == -1:
        # No term found, just head slice
        snippet = text[:max_len]
        return _bold_keywords(snippet + "…", query)

    half = max_len // 2
    start = max(0, idx - half)
    end = min(len(text), start + max_len)
    snippet = text[start:end]
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return _bold_keywords(prefix + snippet + suffix, query)


async def _embed_text(q: str) -> List[float]:
    """
    Calls OpenAI embeddings endpoint (text-embedding-3-small, 1536 dims by default).
    Separated for easy monkeypatching in tests.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(502, "OpenAI embedding key not configured")
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": EMBEDDING_MODEL, "input": q}
    try:
        async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT_SECS) as client:
            r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            # Bubble up as 502 because upstream failed
            raise HTTPException(502, f"OpenAI error: {r.text}")
        data = r.json()
        vec = data["data"][0]["embedding"]
        if not isinstance(vec, list) or len(vec) != EMBEDDING_DIM:
            raise HTTPException(502, "Embedding dimension mismatch")
        return vec
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"OpenAI error: {e}")


def _parse_doc_filters(raw: Optional[str]) -> Dict[str, Optional[str]]:
    """
    doc_filters JSON supports: source_url, external_id, title (substring)
    Example: {"source_url":"https://…","title":"depression"}
    """
    if not raw:
        return {"source_url": None, "external_id": None, "title": None}
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return {"source_url": None, "external_id": None, "title": None}
        return {
            "source_url": obj.get("source_url"),
            "external_id": obj.get("external_id"),
            "title": obj.get("title") or obj.get("title_substring"),
        }
    except Exception:
        # Ignore parse errors; treat as no filters
        return {"source_url": None, "external_id": None, "title": None}


@app.get("/v1/search/vector")
async def search_vector(
    q: str = Query(..., description="Query string to embed and search"),
    k: int = Query(6, ge=1, le=1000, description="Top-k (1–20 effective; clamped server-side)"),
    org_id: str = Query("demo"),
    doc_filters: Optional[str] = Query(None, description='JSON: {"source_url": "...", "external_id": "...", "title": "substring"}'),
    min_score: Optional[float] = Query(None, description="Min similarity score (0..1)"),
) -> List[VectorHit]:
    """
    Vector search over chunk_embeddings via Supabase PostgREST RPC.
    Returns list of hits in stable shape:
    [{"score":0.78,"content":"...","ord":3,"document":{"title":"...","source_url":"...","external_id":"..."}}]
    """
    if not SUPABASE_REST_URL:
        raise HTTPException(500, "SUPABASE_REST_URL not configured")
    # Clamp k to 1..20 for MVP
    k_eff = max(1, min(20, int(k)))

    # 1) Embed the query
    embedding = await _embed_text(q)

    # 2) Parse doc filters
    filters = _parse_doc_filters(doc_filters)

    # 3) Call RPC function match_chunks (defined in SQL block)
    rpc_url = f"{SUPABASE_REST_URL}/rpc/match_chunks"
    payload = {
        "query_embedding": embedding,
        "match_count": k_eff,
        "org": org_id,
        "min_score": min_score,
        "source_url": filters["source_url"],
        "external_id": filters["external_id"],
        "title_substring": filters["title"],
    }
    try:
        rows = await _post_json(rpc_url, payload, _sb_headers_anon())
    except HTTPException:
        # Propagate PostgREST errors as-is
        raise
    except Exception as e:
        raise HTTPException(502, f"Search backend error: {e}")

    # 4) Transform/format
    hits: List[VectorHit] = []
    for r in rows or []:
        # r keys: score, content, ord, title, source_url, external_id
        snippet = _make_snippet(r.get("content", ""), q, max_len=480)
        hit = VectorHit(
            score=float(r.get("score", 0.0)),
            content=snippet,
            ord=int(r.get("ord", 0)),
            document=DocumentInfo(
                title=r.get("title"),
                source_url=r.get("source_url"),
                external_id=r.get("external_id"),
            ),
        )
        hits.append(hit)

    # Sort by score desc just in case RPC ties/ordering vary slightly
    hits.sort(key=lambda h: h.score, reverse=True)
    return [h.model_dump() for h in hits]
