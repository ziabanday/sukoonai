from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_post_ask_ok_and_headers():
    payload = {"org_id": "demo", "user_id": "u1", "q": "What is sleep hygiene?"}
    headers = {"x-client-request-id": "test-123"}
    r = client.post("/v1/agent/ask", json=payload, headers=headers)
    assert r.status_code == 200

    body = r.json()
    # schema fields from Result
    assert isinstance(body["answer"], str) and body["answer"]
    assert isinstance(body["sources"], list)
    assert body["confidence"] in {"low", "med", "high"}
    assert isinstance(body["cost_ms"], int)
    assert isinstance(body["tokens"], int)

    # response headers
    assert "x-cost-ms" in r.headers
    assert r.headers.get("x-request-id") == "test-123"

def test_post_ask_determinism():
    payload = {"org_id": "demo", "user_id": "u1", "q": "What is sleep hygiene?"}
    r1 = client.post("/v1/agent/ask", json=payload)
    r2 = client.post("/v1/agent/ask", json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["answer"] == r2.json()["answer"]
    assert r1.json()["sources"] == r2.json()["sources"]

def test_post_ask_crisis_no_sources():
    payload = {"org_id": "demo", "user_id": "u1", "q": "I want to kill myself"}
    r = client.post("/v1/agent/ask", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["sources"], list) and len(body["sources"]) == 0
    assert body["confidence"] == "low"
