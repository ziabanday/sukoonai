# STACK.md

> **Purpose**: Freeze a lean, repeatable stack for SMB gigs and enterprise pilots. Default to **LangGraph‑first** orchestration, with LangChain components for RAG/tools. Host on a single free/low‑cost platform until a client pays for SLAs. Backend LLM: **GPT‑4o‑mini** (tokens are the only mandatory spend).

---

## 1) Architecture (at a glance)
```
Client (Streamlit or Next.js)
        │ REST/WS
        ▼
FastAPI (apps/api)
  ├─ Auth (JWT/API keys, org tenancy)
  ├─ Agent Orchestrator (LangGraph)
  │    ├─ Planner node
  │    ├─ Tool node(s) (Typed)
  │    ├─ RAG node (Supabase + pgvector)
  │    ├─ Safety/Policy guard
  │    ├─ HITL edge (escalation)
  │    └─ Finalize/format node
  ├─ Observability (LangSmith, JSON /metrics)
  └─ Budget/Latency gate

Supabase Postgres + pgvector
  ├─ docs, chunks, embeddings, sources
  ├─ orgs, users, roles, api_keys
  └─ RLS policies per org

CI/CD (GitHub Actions) → Render/Railway (one default host)
```

---

## 2) Standard Stack v1.0
- **Language/Runtime**: Python 3.11, FastAPI, Uvicorn, Pydantic v2, Poetry or uv
- **Orchestration**: **LangGraph** (typed state, error edges, retries); LangChain for tools/RAG wrappers
- **LLM**: OpenAI **gpt‑4o‑mini** (default); provider is pluggable via env
- **RAG**: Supabase Postgres + pgvector; hybrid retriever (BM25 + vector) optional
- **Embeddings**: Small/cheap embedding model; cache vectors in Supabase
- **Frontend**: **Pick one per project** → Streamlit (fast demos) **or** Next.js (prod UI)
- **Observability**: LangSmith tracing; `/health` and `/metrics` endpoints
- **Auth & Tenancy**: JWT (HS256) + per‑org API keys; Supabase RLS
- **CI/CD**: GitHub Actions (lint, tests, build, deploy)
- **Hosting**: Render **or** Railway (pick one default); Vercel only with Next.js
- **HITL**: Mandatory; start simple (email/webhook) and upgrade later (Ops UI)
- **Safety**: Domain guardrails + crisis/escalation rules (esp. mental health)

---

## 3) Repo Layout
```
repo/
├─ apps/
│  ├─ api/                # FastAPI service
│  │  ├─ main.py
│  │  ├─ settings.py
│  │  ├─ deps/
│  │  ├─ auth/
│  │  ├─ routes/
│  │  └─ graphs/          # LangGraph graphs & nodes
│  └─ web/                # Streamlit or Next.js (choose one, delete the other)
├─ packages/
│  ├─ rag/                # retrievers, chunkers, evaluators
│  ├─ tools/              # typed tool interfaces
│  └─ common/             # schemas, errors, utils
├─ infra/
│  ├─ supabase/           # SQL, RLS policies, seed
│  ├─ docker/             # Dockerfile(s), compose, entrypoints
│  └─ deploy/             # Render/Railway templates
├─ tests/
│  ├─ unit/
│  └─ e2e/
├─ .github/workflows/ci.yml
├─ pyproject.toml / uv.lock
├─ Makefile
├─ .env.example
├─ STACK.md               # this file (kept in repo)
└─ CHECKLIST.md           # starter repo checklist
```

---

## 4) Environment & Config
**.env.example**
```
APP_ENV=dev
APP_DEBUG=false
PORT=8000

# OpenAI / LLM
OPENAI_API_KEY=sk-...
MODEL_COMPLETIONS=gpt-4o-mini
MODEL_EMBEDDINGS=text-embedding-3-small
MAX_OUTPUT_TOKENS=800

# Supabase
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...   # server-only, never to client
SUPABASE_DB_SCHEMA=public

# Auth & tenancy
JWT_SECRET=change_me
JWT_ALG=HS256
ORG_DEFAULT_RATE_LIMIT_PER_MIN=60

# Observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=default

# Safety
CRISIS_TERMS_PATH=./packages/common/crisis_terms.txt
```

---

## 5) API Surface (minimal)
- **POST** `/v1/agent/ask` → `{org_id, user_id, query}` → `{answer, sources[], confidence, cost_ms, tokens}`
- **POST** `/v1/ingest` → `{org_id, source_url|file}` (auth required)
- **GET** `/health` → `{"status":"ok"}`
- **GET** `/metrics` → simple JSON: p95 latency, token spend (1h/24h), error rate

---

## 6) LangGraph Skeleton (pseudocode)
```python
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

class AgentState(BaseModel):
    org_id: str
    user_id: str
    query: str
    plan: str | None = None
    evidence: list[dict] = []
    draft: str | None = None
    final: str | None = None
    sources: list[str] = []
    confidence: float | None = None

sg = StateGraph(AgentState)

@sg.node("plan")
def plan_node(s: AgentState):
    # call LLM to create a short plan/tool calls; budget & retry guards here
    ...

@sg.node("rag")
def rag_node(s: AgentState):
    # hybrid retrieval from Supabase (BM25 + vector), attach sources & snippets
    ...

@sg.node("guard")
def guard_node(s: AgentState):
    # crisis terms, domain scope, PII red flags → return HITL route if needed
    ...

@sg.node("compose")
def compose_node(s: AgentState):
    # answer with citations, compute confidence (heuristic/logit via rerank)
    ...

@sg.node("hitl")
def hitl_node(s: AgentState):
    # enqueue/manual review (email/webhook); block or annotate response
    ...

sg.add_edge("plan", "rag")
sg.add_edge("rag", "guard")
sg.add_conditional_edges("guard", lambda s: "hitl" if need_human(s) else "compose")
sg.add_edge("compose", END)

graph = sg.compile()
```

---

## 7) RAG Defaults
- Chunk: 600–900 chars w/ 100–150 overlap; store md5(doc_id+span)
- Metadata: `org_id, doc_id, url, title, section, tokens, license`
- Retrieval: k=4–8; rerank optional; always return `sources[]` with stable URLs
- **Confidence**: simple heuristic (overlap + agreement) → `low|med|high`
- **Policy**: if `confidence == low`, return safe fallback and encourage follow‑up

---

## 8) Supabase: Minimal Schema & RLS
**tables**: `orgs, users, memberships, api_keys, docs, chunks, runs`

**RLS example (per‑org)**
```sql
alter table docs enable row level security;
create policy org_isolation_docs
on docs using ( org_id = (select org_id from memberships m where m.user_id = auth.uid()) );
```

**API keys** (server‑only table; never expose service role key to client).

---

## 9) Safety & HITL (Mental‑health baseline)
- Crisis lexicon (self‑harm, harm to others, emergency intents)
- If triggered: **do not** generate advice; return local helpline text + HITL route
- Disclaimer baked into compose node; not just UI copy
- Red‑team prompts and unit tests for safety flows

---

## 10) Performance & Cost Budgets
- p95 latency target: **< 1.8s** (MVP), **< 1.2s** (hardened)
- Cost caps: server enforces max output tokens + per‑org/minute rate limit
- Cache: request fingerprinting for identical queries within 5 min (per org)

---

## 11) Testing & Quality Gates
- **Unit**: tools pure functions, chunking, policy checks
- **Golden**: 10–20 Q&A per client/org with expected sources
- **Load**: `locust` or `k6` basic ramp; track p95 & error rate
- CI must pass: lint, typecheck, unit, golden; block merge on fail

---

## 12) Deployment
- One default host (Render/Railway). Containerized. Health checks enabled.
- Secrets via platform UI; never commit .env
- Blue/green or rolling if supported; otherwise simple redeploy with readiness

---

## 13) What we intentionally defer
- Kubernetes, multi‑cloud, advanced MLOps, SOC‑2; exotic vector DBs
