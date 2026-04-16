"""
Integration tests for POST /api/v1/ai/similarity-search.

Requires Docker (testcontainers pulls pgvector/pgvector:pg16).
Run with:  pytest -m integration
Skipped by default via pytest.ini addopts: -m "not integration"

Strategy:
- Real pgvector DB (via testcontainers) with Alembic migrations applied.
- AIService is overridden so it uses the test DB session factory rather than
  the production one, while keeping the real service logic.
- Ollama embedding is mocked deterministically (no network call).
- Contract listings are mocked deterministically.

Isolation: each test gets a fresh db_session that rolls back on teardown.
"""

from contextlib import asynccontextmanager

import numpy as np
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app
from app.repositories.dataset_embedding_repo import DatasetEmbeddingRepository
from app.routers import ai_router
from app.schemas.ai_schema import ErrorResponse
from app.services.ai_service import AIService, EmbeddingError, get_ai_service
from app.config.settings import Settings

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

DIM = 768

# ---------------------------------------------------------------------------
# Test vector fixtures
# ---------------------------------------------------------------------------


def _unit_vec(hot_idx: int) -> list[float]:
    v = np.zeros(DIM, dtype=np.float32)
    v[hot_idx] = 1.0
    return v.tolist()


QUERY_VEC = _unit_vec(0)   # query is hot on dim 0
VEC_HIGH = _unit_vec(0)    # cosine ≈ 1.0 → "high" after clamping
VEC_MED = [0.5 if i == 0 else (0.5 if i == 1 else 0.0) for i in range(DIM)]  # ~0.7
VEC_LOW = _unit_vec(1)     # orthogonal to query → score ≈ 0.0

# ---------------------------------------------------------------------------
# Settings fixture (reuse service-level make_settings pattern)
# ---------------------------------------------------------------------------


def make_test_settings() -> Settings:
    return Settings(
        _env_file=None,
        APP_NAME="BridgeMart Test",
        APP_VERSION="0.1.0",
        ENVIRONMENT="test",
        HOST="localhost",
        PORT=8080,
        CORS_ORIGINS=["http://localhost"],
        EMBEDDING_MODEL="nomic-embed-text",
        MAX_FILE_SIZE_MB=50,
        MAX_DATASET_ROWS=50000,
        EMBEDDING_CHUNK_SIZE=2,
        TOP_K=10,
        K_ROWS=2,
        SIMILARITY_THRESHOLD=None,
        CACHE_MAXSIZE=100,
        PINATA_API_KEY="k",
        PINATA_SECRET_KEY="s",
        PINATA_GATEWAY_URL="https://gateway.pinata.cloud",
        CONTRACT_ADDRESS="0x" + "0" * 40,
        CONTRACT_ABI_PATH="/tmp/Marketplace.json",
        CHAIN_ID=31337,
        RPC_URL="http://127.0.0.1:8545",
        SERVER_PRIVATE_KEY="0x" + "11" * 32,
        POSTGRES_URL="postgresql://user:pass@localhost/test",
    )


# ---------------------------------------------------------------------------
# Contract items fixture (deterministic mock)
# ---------------------------------------------------------------------------

from types import SimpleNamespace


def make_contract_item(listing_id: str, title: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=listing_id,
        title=title,
        description=f"Description for {title}",
        seller="0x" + "ab" * 20,
        price_atomic="1000000",
    )


CONTRACT_ITEMS = [
    make_contract_item("listing-high", "High Match Dataset"),
    make_contract_item("listing-med", "Medium Match Dataset"),
    make_contract_item("listing-low", "Low Match Dataset"),
]


# ---------------------------------------------------------------------------
# AIService override factory (uses test DB session factory)
# ---------------------------------------------------------------------------


def make_ai_service_override(
    db_session: AsyncSession,
    embedding_vec: list[float] = None,
    embedding_raises: Exception = None,
):
    """Return a factory that produces an AIService wired to the test DB session."""
    embedding_repo = DatasetEmbeddingRepository()

    # Wrap the provided db_session in an asynccontextmanager-compatible factory
    @asynccontextmanager
    async def test_session_factory():
        yield db_session

    # Fake session maker class so `async with factory() as db:` works
    class FakeSessionMaker:
        def __call__(self):
            return test_session_factory()

    if embedding_raises is not None:
        def embedding_fn(text, settings):
            raise embedding_raises
    else:
        vec = embedding_vec or QUERY_VEC
        def embedding_fn(text, settings):
            return vec, len(vec)

    def contract_fetcher(settings):
        return CONTRACT_ITEMS

    settings = make_test_settings()

    return AIService(
        embedding_repo=embedding_repo,
        session_factory=FakeSessionMaker(),
        contract_listing_fetcher=contract_fetcher,
        embedding_fn=embedding_fn,
        settings=settings,
    )


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------


async def seed_embeddings(db_session: AsyncSession) -> None:
    repo = DatasetEmbeddingRepository()
    await repo.upsert(db_session, "listing-high", VEC_HIGH)
    await repo.upsert(db_session, "listing-med", VEC_MED)
    await repo.upsert(db_session, "listing-low", VEC_LOW)
    await db_session.flush()


# ---------------------------------------------------------------------------
# Tests — 200 happy path
# ---------------------------------------------------------------------------


async def test_similarity_search_200_returns_ordered_results(db_session: AsyncSession):
    await seed_embeddings(db_session)

    ai_svc = make_ai_service_override(db_session)
    app.dependency_overrides[get_ai_service] = lambda: ai_svc

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/ai/similarity-search",
                json={"query": "heart rate data", "limit": 20},
            )
    finally:
        app.dependency_overrides.pop(get_ai_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "heart rate data"
    assert body["count"] > 0

    results = body["results"]
    # Results must be ordered by descending score
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

    # Each result must have the flat schema fields
    for r in results:
        assert "listing_id" in r
        assert "title" in r
        assert "description" in r
        assert "seller" in r
        assert "price_atomic" in r
        assert "score" in r
        assert r["score_label"] in ("high", "moderate", "low")
        # Old nested fields must not be present
        assert "item" not in r
        assert "explanation" not in r

    # listing-high should be first (most similar to QUERY_VEC)
    assert results[0]["listing_id"] == "listing-high"


async def test_similarity_search_200_scores_clamped(db_session: AsyncSession):
    await seed_embeddings(db_session)

    ai_svc = make_ai_service_override(db_session)
    app.dependency_overrides[get_ai_service] = lambda: ai_svc

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/ai/similarity-search",
                json={"query": "test"},
            )
    finally:
        app.dependency_overrides.pop(get_ai_service, None)

    assert response.status_code == 200
    for r in response.json()["results"]:
        assert 0.0 <= r["score"] <= 1.0


async def test_similarity_search_200_score_label_correct(db_session: AsyncSession):
    await seed_embeddings(db_session)

    ai_svc = make_ai_service_override(db_session)
    app.dependency_overrides[get_ai_service] = lambda: ai_svc

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/ai/similarity-search",
                json={"query": "test"},
            )
    finally:
        app.dependency_overrides.pop(get_ai_service, None)

    assert response.status_code == 200
    for r in response.json()["results"]:
        score = r["score"]
        label = r["score_label"]
        if score > 0.66:
            assert label == "high", f"score={score} should be 'high'"
        elif score > 0.33:
            assert label == "moderate", f"score={score} should be 'moderate'"
        else:
            assert label == "low", f"score={score} should be 'low'"


# ---------------------------------------------------------------------------
# Tests — 422 validation
# ---------------------------------------------------------------------------


async def test_similarity_search_422_blank_query(db_session: AsyncSession):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/ai/similarity-search",
            json={"query": ""},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert "details" in body


async def test_similarity_search_422_missing_query(db_session: AsyncSession):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/ai/similarity-search", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"


async def test_similarity_search_422_limit_out_of_range(db_session: AsyncSession):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/ai/similarity-search",
            json={"query": "test", "limit": 99},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"


# ---------------------------------------------------------------------------
# Tests — 503 Ollama unavailable
# ---------------------------------------------------------------------------


async def test_similarity_search_503_when_embedding_fails(db_session: AsyncSession):
    from fastapi import HTTPException as FastAPIHTTPException

    ai_svc = make_ai_service_override(
        db_session,
        embedding_raises=FastAPIHTTPException(status_code=500, detail="Ollama down"),
    )
    app.dependency_overrides[get_ai_service] = lambda: ai_svc

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/ai/similarity-search",
                json={"query": "heart rate data"},
            )
    finally:
        app.dependency_overrides.pop(get_ai_service, None)

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error"] == "embedding_unavailable"
    assert "message" in detail
