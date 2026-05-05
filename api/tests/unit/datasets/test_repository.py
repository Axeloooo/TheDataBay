from types import SimpleNamespace

import pytest

from app.datasets.repository import DatasetKeyRepository, get_vector_document_preview


class FakeResult:
    def __init__(self, row):
        self.row = row

    def scalar_one(self):
        return self.row


class FakeAsyncSession:
    def __init__(self):
        self.executed = []
        self.flushed = False
        self.row = SimpleNamespace(listing_id="listing-123")

    async def execute(self, statement):
        self.executed.append(statement)
        return FakeResult(self.row)

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_dataset_key_repository_upsert_flushes_and_returns_row():
    session = FakeAsyncSession()
    repo = DatasetKeyRepository()

    row = await repo.upsert(
        db=session,
        listing_id="listing-123",
        key_b64="a2V5",
        nonce_b64="bm9uY2U=",
        dataset_url="ipfs://QmData",
        dataset_hash="0xdata",
    )

    assert row.listing_id == "listing-123"
    assert len(session.executed) == 1
    assert session.flushed is True


def test_vector_document_preview_no_longer_queries_vector_tables():
    class QueryingSession:
        def execute(self, *args, **kwargs):
            raise AssertionError("Preview fallback must not touch vector tables")

    assert get_vector_document_preview(QueryingSession(), "listing-123") is None
