# SukoonAI Agent (Chat-3b)

Deterministic, safety-first scaffold: **plan → rag → guard → compose**.  
All nodes are **pure** (no network IO, no randomness). Crisis queries return a **safe escalation** message.

```
+-------+     +-----+     +------+     +---------+
| plan  | --> | rag | --> | guard| --> | compose |
+-------+     +-----+     +------+     +---------+
                               |
                               +--(crisis?)-->  safe escalation (no sources)
```

---

## Flow summary

- **plan**: build a tiny plan string from the user query (deterministic).
- **rag**: return a **stable-ordered** curated source list (MedlinePlus → WHO).
- **guard**: crisis screening using `notes["crisis_terms"]` (lowercased `set[str]`, injected by API).
- **compose**:
  - If **crisis** → output **bilingual escalation** (English → Roman-Urdu), **no sources**, `confidence="low"`.
  - Else → output **bilingual answer** (English → Roman-Urdu) with **numbered citations** `[1][2]` in the order of `sources`.
  - Token estimate: `tokens = max(1, len(answer)//4)`.
  - Confidence is `"low"` by default for this MVP.

Nodes are pure functions over a dict-like **AgentState**; the API layer is responsible for IO (loading crisis terms, headers, timing, etc.).

---

## Determinism & Safety

- **Determinism**: no randomness, no clocks/UUIDs inside nodes; RAG is a curated list with fixed ordering.
- **Safety**: crisis detection uses a simple term match against `packages/agent/crisis_terms.txt`.  
  When triggered, the **compose** node returns an escalation message (no coaching, no instructions for self-harm), **no sources**, and `confidence="low"`.

---

## Where real RAG plugs in (Chat-4)

Swap the current `rag_node` with your retriever (e.g., pgvector/FAISS). Keep output **order stable**:
1. Sort by score descending.
2. Tie-break by canonical URL (or title + URL) so the citation order remains deterministic.

---

## API contract

### POST `/v1/agent/ask`
Runs: **plan → rag → guard → compose** and returns a bilingual response.

**Headers**
- Optional request header: `x-client-request-id` → echoed back as `x-request-id`.
- Response header: `x-cost-ms` (integer milliseconds; API clamps to ≥ 1).

**Request body**
```json
{
  "org_id": "demo",
  "user_id": "u1",
  "q": "What is sleep hygiene?"
}
```

**Response body (`Result`)**
```json
{
  "answer": "English paragraph [1][2]\n\nRoman-Urdu paragraph [1][2]",
  "sources": [
    "https://medlineplus.gov/encyclopedia.html",
    "https://www.who.int/health-topics/sleep"
  ],
  "confidence": "low",
  "cost_ms": 12,
  "tokens": 85
}
```

**Crisis case**
- `answer`: bilingual **escalation** with “emergency/help” language.
- `sources`: `[]` (empty).
- `confidence`: `"low"`.

---

## Crisis terms

- File: `packages/agent/crisis_terms.txt` (one term per line, **lowercased**).  
- The API loads these once at startup and injects into the graph as `state.notes["crisis_terms"]`.

---

## Local run

```bash
uvicorn app.api.main:app --reload --port 8001
# Swagger UI:
# http://127.0.0.1:8001/docs
```

---

## Tests

```bash
pytest -q tests/graph/test_flow.py
pytest -q tests/api/test_ask_route.py
```

What the tests check:
- **Smoke**: bilingual answer (two paragraphs), ≥2 sources, confidence in {low,med,high}.
- **Crisis**: escalation language, **no sources**, `confidence=="low"`.
- **Determinism**: same input → same answer & source order.
- **API**: schema matches `Result`, headers include `x-cost-ms` and echo `x-request-id` when provided.

---

## Debug routes

Debug routes are **off by default**. Enable by setting `DEBUG_ROUTES=1` before launching.

- `GET /__routes__` (not included in OpenAPI schema)
- `POST /v1/agent/ask/min` (minimal call-through used for quick inspection)

---

## Environment & versions

- **Python 3.11**
- **FastAPI**
- **Pydantic v2** (`ConfigDict`, `model_dump()` semantics)

Nodes remain pure; any IO (loading terms, UUID trace IDs, timing) happens in the **API layer**.
