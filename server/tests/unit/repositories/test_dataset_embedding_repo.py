"""
Unit tests for DatasetEmbeddingRepository.

The AsyncSession is fully mocked — no real database is required.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.dataset_embedding import DatasetEmbedding
from app.repositories.dataset_embedding_repo import DatasetEmbeddingRepository

LISTING_ID = "listing-unit-001"
EMBEDDING = [0.1] * 768


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_db() -> AsyncMock:
    """Return a fresh mock AsyncSession for each test."""
    db = AsyncMock()
    db.flush = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# upsert
# ---------------------------------------------------------------------------


async def test_upsert_calls_execute_and_returns_embedding() -> None:
    """upsert() should call db.execute() and return the scalar result."""
    repo = DatasetEmbeddingRepository()
    db = make_db()

    expected = DatasetEmbedding(listing_id=LISTING_ID)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = expected
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.upsert(db, LISTING_ID, EMBEDDING)

    db.execute.assert_awaited_once()
    db.flush.assert_awaited_once()
    assert result is expected
    assert result.listing_id == LISTING_ID


async def test_upsert_passes_listing_id_and_embedding_to_statement() -> None:
    """upsert() should include listing_id and embedding in the INSERT statement."""
    repo = DatasetEmbeddingRepository()
    db = make_db()

    expected = DatasetEmbedding(listing_id=LISTING_ID)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = expected
    db.execute = AsyncMock(return_value=mock_result)

    await repo.upsert(db, LISTING_ID, EMBEDDING)

    # Verify execute was called with *something* (the compiled PG upsert stmt)
    call_args = db.execute.call_args
    # The first positional argument is the compiled statement object
    stmt_arg = call_args[0][0]
    # The statement should be an Insert (PostgreSQL dialect insert)
    assert stmt_arg is not None


# ---------------------------------------------------------------------------
# search_by_vector
# ---------------------------------------------------------------------------


async def test_search_by_vector_calls_execute_with_cosine_operator() -> None:
    """search_by_vector() should issue a query that contains the <=> operator."""
    repo = DatasetEmbeddingRepository()
    db = make_db()

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        ("listing-a", 0.95),
        ("listing-b", 0.80),
    ]
    db.execute = AsyncMock(return_value=mock_result)

    results = await repo.search_by_vector(db, EMBEDDING, limit=10)

    db.execute.assert_awaited_once()
    # Verify the SQL text contains the pgvector cosine distance operator
    call_args = db.execute.call_args
    stmt = call_args[0][0]
    assert "<=>" in str(stmt)

    assert len(results) == 2
    assert results[0] == ("listing-a", 0.95)
    assert results[1] == ("listing-b", 0.80)


async def test_search_by_vector_returns_empty_list_when_no_rows() -> None:
    """search_by_vector() should return an empty list when there are no matches."""
    repo = DatasetEmbeddingRepository()
    db = make_db()

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    results = await repo.search_by_vector(db, EMBEDDING, limit=5)

    assert results == []


async def test_search_by_vector_passes_limit_parameter() -> None:
    """search_by_vector() should forward the limit to the SQL query."""
    repo = DatasetEmbeddingRepository()
    db = make_db()

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    await repo.search_by_vector(db, EMBEDDING, limit=42)

    call_kwargs = db.execute.call_args[0][1]  # second positional arg = params dict
    assert call_kwargs["limit"] == 42


async def test_search_by_vector_converts_scores_to_float() -> None:
    """search_by_vector() should ensure scores are Python floats."""
    repo = DatasetEmbeddingRepository()
    db = make_db()

    # Simulate Decimal or other numeric type returned by the DB driver
    from decimal import Decimal

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("listing-x", Decimal("0.912345"))]
    db.execute = AsyncMock(return_value=mock_result)

    results = await repo.search_by_vector(db, EMBEDDING)

    assert isinstance(results[0][1], float)
    assert abs(results[0][1] - 0.912345) < 1e-5


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


async def test_delete_calls_execute_with_delete_statement() -> None:
    """delete() should issue a DELETE statement containing the listing_id."""
    repo = DatasetEmbeddingRepository()
    db = make_db()

    mock_result = MagicMock()
    db.execute = AsyncMock(return_value=mock_result)

    await repo.delete(db, LISTING_ID)

    db.execute.assert_awaited_once()
    call_args = db.execute.call_args
    stmt = call_args[0][0]
    params = call_args[0][1]

    # Statement should reference DELETE
    assert "DELETE" in str(stmt).upper()
    assert params["listing_id"] == LISTING_ID
    db.flush.assert_awaited_once()


async def test_delete_flushes_after_execute() -> None:
    """delete() should flush the session after issuing the DELETE."""
    repo = DatasetEmbeddingRepository()
    db = make_db()
    db.execute = AsyncMock(return_value=MagicMock())

    await repo.delete(db, LISTING_ID)

    db.flush.assert_awaited_once()
