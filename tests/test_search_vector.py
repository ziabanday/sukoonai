# tests/test_search_vector.py
import json
from fastapi.testclient import TestClient

# Import the app and helpers
from app.api.main import app

client = TestClient(app)

def test_search_vector_basic(monkeypatch):
    # 1) Mock embeddings to a fixed vector (unit at index 1)
    async def fake_embed_text(q: str):
        v = [0.0] * 1536
        v[0] = 1.0
        return v

    # 2) Mock PostgREST RPC for /rpc/match_chunks
    async def fake_post_json(url: str, payload, headers):
        assert url.endswith("/rpc/match_chunks")
        # Simulate three rows, already scored (scores descending)
        return [
            {
                "score": 0.91,
                "content": "Good sleep habits improve mood and reduce anxiety.",
                "ord": 0,
                "title": "Sleep Hygiene Basics",
                "source_url": "https://example.org/sleep",
                "external_id": "ext-1",
            },
            {
                "score": 0.80,
                "content": "Avoid caffeine late; keep a regular bedtime routine.",
                "ord": 1,
                "title": "Sleep Hygiene Basics",
                "source_url": "https://example.org/sleep",
                "external_id": "ext-1",
            },
        ]

    # Wire monkeypatches
    monkeypatch.setattr("app.api.main._embed_text", fake_embed_text)
    monkeypatch.setattr("app.api.main._post_json", fake_post_json)

    # Call API
    r = client.get("/v1/search/vector", params={"q": "sleep anxiety", "k": 2})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2
    top = data[0]
    # Shape checks
    assert set(top.keys()) == {"score", "content", "ord", "document"}
    assert set(top["document"].keys()) == {"title", "source_url", "external_id"}
    # Ordering by score desc
    assert data[0]["score"] >= data[1]["score"]
    # Snippet length guard
    assert len(top["content"]) <= 520  # includes possible ellipses/bolding


def test_search_vector_params_and_min_score(monkeypatch):
    async def fake_embed_text(q: str):
        return [0.0] * 1536

    async def fake_post_json(url: str, payload, headers):
        # Ensure k is clamped to <= 20
        assert payload["match_count"] <= 20
        # Simulate results around the min_score threshold
        return [
            {"score": 0.72, "content": "alpha content", "ord": 0, "title": "T", "source_url": None, "external_id": None},
            {"score": 0.61, "content": "beta content", "ord": 1, "title": "T", "source_url": None, "external_id": None},
        ]

    monkeypatch.setattr("app.api.main._embed_text", fake_embed_text)
    monkeypatch.setattr("app.api.main._post_json", fake_post_json)

    # Large k should clamp; min_score is enforced in RPC, but we at least pass it
    r = client.get(
        "/v1/search/vector",
        params={
            "q": "sleep",
            "k": 99,
            "min_score": 0.65,
            "doc_filters": json.dumps({"title": "sleep", "external_id": "ext-1"}),
        },
    )
    assert r.status_code == 200
    data = r.json()
    # We simulated 2 rows from backend; min_score filtering happens server-side,
    # here we just ensure we didn't 404 and response shape is correct.
    assert isinstance(data, list)
    assert all({"score", "content", "ord", "document"} <= set(x.keys()) for x in data)
