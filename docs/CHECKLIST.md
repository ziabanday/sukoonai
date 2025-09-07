# CHECKLIST.md (Starter Repo Checklist)

> Use this every time you spin up a new client repo. Delete sections that don’t apply.

## A. Initialize
- [ ] Create repo from template; set **private**
- [ ] Choose frontend: **Streamlit** or **Next.js** (delete the other)
- [ ] Pick host: **Render** or **Railway** (set as default)
- [ ] Create project board: *Backlog, In‑Progress, Review, Done*

## B. Secrets & Config
- [ ] Add **OPENAI_API_KEY** to repo secrets and host
- [ ] Add **LANGCHAIN_API_KEY**, set `LANGCHAIN_TRACING_V2=true`
- [ ] Add **SUPABASE_URL**, **SUPABASE_ANON_KEY**, **SUPABASE_SERVICE_ROLE_KEY** (host only)
- [ ] Set **JWT_SECRET**, **ORG_DEFAULT_RATE_LIMIT_PER_MIN**
- [ ] Commit `.env.example`; never commit real secrets

## C. Supabase Setup
- [ ] Create project; enable pgvector
- [ ] Run `infra/supabase/schema.sql` (tables: orgs, users, memberships, api_keys, docs, chunks, runs)
- [ ] Apply RLS policies (org‑scoped isolation)
- [ ] Create service role key (server only) & anon key (client)

## D. Local Dev
- [ ] `make bootstrap` (install uv/poetry, pre‑commit hooks)
- [ ] `make dev` → runs FastAPI at :8000 and chosen frontend
- [ ] Verify `/health` and `/metrics`

## E. Agent Graph
- [ ] Implement nodes: **plan → rag → guard → (hitl?) → compose**
- [ ] Add retries/backoff on external calls; timeouts ≤ 12s
- [ ] Enforce token/output caps; include cost + latency in response

## F. RAG Pipeline
- [ ] Implement chunker (600–900 chars, 100–150 overlap)
- [ ] Populate `docs/chunks` with metadata & md5 ids
- [ ] Retriever k=6 default; ensure `sources[]` are stable URLs
- [ ] Golden set (≥10 items) committed under `tests/golden/`

## G. Safety & Governance
- [ ] Add **crisis lexicon** and guard node behavior
- [ ] Compose node injects disclaimer + resources when needed
- [ ] HITL stub: email/webhook + admin note storage
- [ ] Unit tests for safety triggers

## H. Quality Gates (CI)
- [ ] GitHub Actions: lint (ruff), typecheck (mypy), tests (pytest), build image
- [ ] Golden tests must pass; block merge on fail
- [ ] Coverage badge (optional)

## I. Observability
- [ ] LangSmith project created; traces visible for `/v1/agent/ask`
- [ ] `/metrics` returns p95 latency, error rate, token spend

## J. Deployment
- [ ] Build & deploy container on chosen host
- [ ] Add health check; confirm cold‑start behavior is acceptable
- [ ] Set minimum instance (if client pays for uptime)

## K. Go‑Live Readiness
- [ ] Per‑org API key issued; RLS verified with two test orgs
- [ ] Rate limits applied; log redaction enabled
- [ ] Backup/export policy defined (docs & chunks)

## L. Client Onboarding
- [ ] Create org, admin user, and API key
- [ ] Upload 5–10 seed documents; run first golden eval
- [ ] Share usage guide and safety policy

## M. SukoonAI‑specific (mental health)
- [ ] Crisis flow tested end‑to‑end (trigger → resource → HITL)
- [ ] Bilingual disclaimer embedded in compose node
- [ ] Content sources restricted to approved MedlinePlus/WHO (for MVP)

---

## Makefile (starter targets)
```
bootstrap:  ## install toolchain & hooks
	uvenv || pip install uv || pip install poetry
	pre-commit install || true

lint:
	ruff check .
	ruff format --check

default: dev

dev:
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port $${PORT:-8000}

test:
	pytest -q

build:
	docker build -t agent:latest .

run:
	docker run -p 8000:8000 --env-file .env agent:latest
```

## CI (workflow sketch)
```yaml
name: ci
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv pip install -r requirements.txt || uv sync
      - run: ruff check . && mypy . && pytest -q
      - run: docker build -t ghcr.io/org/agent:${{ github.sha }} .
```
