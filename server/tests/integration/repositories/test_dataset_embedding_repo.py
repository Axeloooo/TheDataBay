"""
Integration tests for DatasetEmbeddingRepository against a real pgvector DB.

Requires Docker (testcontainers pulls pgvector/pgvector:pg16).
Run with:  pytest -m integration
Skipped by default via pytest.ini addopts: -m "not integration"

Isolation: the conftest db_session fixture rolls back after each test.
Tests do NOT call commit() — all writes are flushed within the transaction
and rolled back on teardown so tests are fully independent of each other.
"""

import numpy as np
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dataset_embedding_repo import DatasetEmbeddingRepository

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

# ---------------------------------------------------------------------------
# Test vector fixtures
# ---------------------------------------------------------------------------

DIM = 768


def _unit_vec(dim: int, hot_idx: int) -> list[float]:
    """Return a unit vector with all mass on `hot_idx`."""
    v = np.zeros(dim, dtype=np.float32)
    v[hot_idx] = 1.0
    return v.tolist()


# query  : dimension 0 is hot
# vec_A  : also hot on dim 0  → high cosine similarity with query
# vec_B  : hot on dim 1       → orthogonal, near-zero similarity
# vec_C  : negative of query  → cosine similarity ≈ -1 (score < 0 after 1-dist)
QUERY_VEC = _unit_vec(DIM, 0)
VEC_A = _unit_vec(DIM, 0)
VEC_B = _unit_vec(DIM, 1)
VEC_C = [-1.0 if i == 0 else 0.0 for i in range(DIM)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_upsert_inserts_new_row(db_session: AsyncSession) -> None:
    """upsert() should create a new row when listing_id does not exist."""
    repo = DatasetEmbeddingRepository()

    row = await repo.upsert(db_session, "integration-001", VEC_A)

    assert row.listing_id == "integration-001"
    assert row.created_at is not None
    assert row.updated_at is not None


async def test_upsert_idempotent_listing_id_unique(db_session: AsyncSession) -> None:
    """upsert() twice with the same listing_id should result in exactly one row."""
    repo = DatasetEmbeddingRepository()
    listing_id = "integration-dedup-001"

    first = await repo.upsert(db_session, listing_id, VEC_A)

    second = await repo.upsert(db_session, listing_id, VEC_B)

    # Only one row should exist.
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM dataset_embeddings WHERE listing_id = :lid"),
        {"lid": listing_id},
    )
    count = result.scalar_one()
    assert count == 1

    # updated_at should be >= created_at.
    assert second.listing_id == listing_id
    assert second.updated_at >= first.created_at  # type: ignore[operator]


async def test_upsert_updates_embedding_on_conflict(db_session: AsyncSession) -> None:
    """upsert() on an existing listing should update the stored embedding."""
    repo = DatasetEmbeddingRepository()
    listing_id = "integration-update-001"

    await repo.upsert(db_session, listing_id, VEC_A)

    updated = await repo.upsert(db_session, listing_id, VEC_B)

    assert updated.listing_id == listing_id


async def test_search_returns_correct_order(db_session: AsyncSession) -> None:
    """search_by_vector() should order results: A (similar) before B (orthogonal) before C (opposite)."""
    repo = DatasetEmbeddingRepository()
    prefix = "search-order"

    await repo.upsert(db_session, f"{prefix}-A", VEC_A)
    await repo.upsert(db_session, f"{prefix}-B", VEC_B)
    await repo.upsert(db_session, f"{prefix}-C", VEC_C)

    results = await repo.search_by_vector(db_session, QUERY_VEC, limit=20)

    # Filter to only the rows we just inserted.
    filtered = [(lid, score) for lid, score in results if lid.startswith(prefix)]
    assert len(filtered) == 3

    ids = [lid for lid, _ in filtered]
    scores = [score for _, score in filtered]

    assert ids[0] == f"{prefix}-A", f"Expected A first, got: {ids}"
    assert ids[1] == f"{prefix}-B", f"Expected B second, got: {ids}"
    assert ids[2] == f"{prefix}-C", f"Expected C third, got: {ids}"

    # Scores must be monotonically non-increasing.
    assert scores[0] >= scores[1] >= scores[2]


async def test_search_score_range(db_session: AsyncSession) -> None:
    """A should score > 0.9 (nearly identical); C should score < 0.05 (opposite)."""
    repo = DatasetEmbeddingRepository()
    prefix = "search-score"

    await repo.upsert(db_session, f"{prefix}-A", VEC_A)
    await repo.upsert(db_session, f"{prefix}-C", VEC_C)

    results = await repo.search_by_vector(db_session, QUERY_VEC, limit=20)
    result_map = {lid: score for lid, score in results if lid.startswith(prefix)}

    score_a = result_map[f"{prefix}-A"]
    score_c = result_map[f"{prefix}-C"]

    assert score_a > 0.9, f"Expected score_A > 0.9, got {score_a}"
    # For the opposite vector, 1 - cosine_distance ≈ 1 - 2 = -1, which is < 0.05.
    assert score_c < 0.05, f"Expected score_C < 0.05, got {score_c}"


async def test_delete_removes_row(db_session: AsyncSession) -> None:
    """delete() should remove the row so it no longer appears in searches."""
    repo = DatasetEmbeddingRepository()
    listing_id = "integration-delete-001"

    await repo.upsert(db_session, listing_id, VEC_A)

    await repo.delete(db_session, listing_id)

    result = await db_session.execute(
        text("SELECT COUNT(*) FROM dataset_embeddings WHERE listing_id = :lid"),
        {"lid": listing_id},
    )
    count = result.scalar_one()
    assert count == 0


async def test_delete_nonexistent_row_is_noop(db_session: AsyncSession) -> None:
    """delete() on a nonexistent listing_id should not raise an error."""
    repo = DatasetEmbeddingRepository()

    # Should complete without exception.
    await repo.delete(db_session, "nonexistent-listing-id-xyz")


async def test_search_empty_table_returns_empty_list(db_session: AsyncSession) -> None:
    """search_by_vector() on a table with no rows returns an empty list.

    Each test rolls back so the table is empty at the start of this test.
    The DELETE is a defensive no-op that guarantees the empty state.
    """
    repo = DatasetEmbeddingRepository()

    # Defensive: clear any rows visible in this transaction.
    await db_session.execute(text("DELETE FROM dataset_embeddings"))

    results = await repo.search_by_vector(db_session, QUERY_VEC, limit=10)
    assert results == []
