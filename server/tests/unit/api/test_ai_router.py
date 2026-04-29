"""
Unit tests for the /api/v1/ai/similarity-search endpoint.

Uses FastAPI TestClient with dependency overrides.  All external I/O
(pgvector, Ollama, contract) is handled inside AIService — the router
tests stub AIService entirely.
"""

from app.ai import router as ai_router
from app.ai.schemas import ErrorResponse, RankedDataset
from app.ai.service import EmbeddingError


def make_ranked_dataset(listing_id: str, score: float = 0.85) -> RankedDataset:
    return RankedDataset(
        listing_id=listing_id,
        title=f"Dataset {listing_id[-4:]}",
        description="Sample dataset",
        seller="0x0000000000000000000000000000000000000001",
        payment_token="0x0000000000000000000000000000000000000002",
        price_atomic=100,
        settlement_currency="USDC",
        settlement_decimals=6,
        purchase_count=0,
        score=score,
        score_label="high",
    )


class StubAIService:
    def __init__(self, ranked_results):
        self.ranked_results = ranked_results
        self.calls: list = []

    async def rank_datasets(self, query: str, limit: int = 20):
        self.calls.append((query, limit))
        return self.ranked_results


class RaisingAIService:
    def __init__(self, exc: Exception):
        self._exc = exc

    async def rank_datasets(self, query: str, limit: int = 20):
        raise self._exc


# ---------------------------------------------------------------------------
# Happy-path
# ---------------------------------------------------------------------------


def test_similarity_search_returns_ranked_results(client):
    ranked = [make_ranked_dataset("0x" + "01" * 32)]
    stub = StubAIService(ranked)
    client.app.dependency_overrides[ai_router.get_ai_service] = lambda: stub

    response = client.post(
        "/api/v1/ai/similarity-search",
        json={"query": "customer churn"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "customer churn"
    assert body["count"] == 1
    result = body["results"][0]
    assert result["listing_id"] == "0x" + "01" * 32
    assert result["score"] == 0.85
    assert result["score_label"] == "high"
    assert result["price_atomic"] == 100
    assert result["payment_token"] == "0x0000000000000000000000000000000000000002"
    assert result["settlement_currency"] == "USDC"
    assert result["settlement_decimals"] == 6
    assert result["purchase_count"] == 0
    # Old nested shape must not be present
    assert "item" not in result
    assert "explanation" not in result


def test_similarity_search_returns_empty_results(client):
    stub = StubAIService([])
    client.app.dependency_overrides[ai_router.get_ai_service] = lambda: stub

    response = client.post(
        "/api/v1/ai/similarity-search",
        json={"query": "no results"},
    )

    assert response.status_code == 200
    assert response.json() == {"query": "no results", "results": [], "count": 0}


def test_similarity_search_passes_limit_to_service(client):
    stub = StubAIService([])
    client.app.dependency_overrides[ai_router.get_ai_service] = lambda: stub

    client.post(
        "/api/v1/ai/similarity-search",
        json={"query": "test", "limit": 5},
    )

    assert stub.calls == [("test", 5)]


def test_similarity_search_defaults_limit_to_20(client):
    stub = StubAIService([])
    client.app.dependency_overrides[ai_router.get_ai_service] = lambda: stub

    client.post("/api/v1/ai/similarity-search", json={"query": "test"})

    assert stub.calls == [("test", 20)]


# ---------------------------------------------------------------------------
# 503 — Ollama unavailable
# ---------------------------------------------------------------------------


def test_similarity_search_returns_503_when_embedding_fails(client):
    raiser = RaisingAIService(EmbeddingError("Ollama connection refused"))
    client.app.dependency_overrides[ai_router.get_ai_service] = lambda: raiser

    response = client.post(
        "/api/v1/ai/similarity-search",
        json={"query": "heart rate data"},
    )

    assert response.status_code == 503
    body = response.json()
    # JSONResponse returns ErrorResponse directly at the top level
    assert body["error"] == "embedding_unavailable"
    assert "message" in body


# ---------------------------------------------------------------------------
# 422 — validation
# ---------------------------------------------------------------------------


def test_similarity_search_rejects_missing_query(client):
    response = client.post("/api/v1/ai/similarity-search", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    errors = body["details"]["errors"]
    assert any(e["loc"][-1] == "query" for e in errors)


def test_similarity_search_rejects_empty_query(client):
    response = client.post(
        "/api/v1/ai/similarity-search",
        json={"query": ""},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"


def test_similarity_search_rejects_limit_zero(client):
    response = client.post(
        "/api/v1/ai/similarity-search",
        json={"query": "test", "limit": 0},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"


def test_similarity_search_rejects_limit_above_max(client):
    response = client.post(
        "/api/v1/ai/similarity-search",
        json={"query": "test", "limit": 21},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"


def test_embed_query_returns_vector_payload(client, monkeypatch, settings):
    async def fake_embed_query(query, resolved_settings):
        return [0.25, 0.75], 2

    monkeypatch.setattr(ai_router, "embed_query", fake_embed_query)

    response = client.post(
        "/api/v1/ai/embed/query",
        json={"query": "weekly revenue"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "original_query": "weekly revenue",
        "query_embedding": [0.25, 0.75],
        "vector_spec": {
            "model": settings.embedding_model,
            "dimension": 2,
        },
    }


def test_embed_query_validates_non_empty_query(client, monkeypatch):
    async def fail_embed_query(query, settings):
        raise AssertionError("embed_query should not be called")

    monkeypatch.setattr(ai_router, "embed_query", fail_embed_query)

    response = client.post("/api/v1/ai/embed/query", json={"query": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    errors = body["details"]["errors"]
    assert any(error["loc"][-1] == "query" for error in errors)
