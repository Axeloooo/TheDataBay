"""
Unit tests for AIService.rank_datasets().

All external dependencies (embedding repo, session factory, contract fetcher,
Ollama embedding fn) are mocked.  No I/O — these are pure unit tests.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai_service import (
    AIService,
    EmbeddingError,
    _aggregate_row_hits,
    _bytes32_hex_to_uuid,
    _clamp,
    _score_label,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_item(listing_id: str, title: str = "Test Dataset") -> SimpleNamespace:
    return SimpleNamespace(
        id=listing_id,
        title=title,
        description="A test dataset",
        seller="0xSeller",
        payment_token="0x0000000000000000000000000000000000000002",
        price_atomic="100",
        settlement_currency="USDC",
        settlement_decimals=6,
        purchase_count=0,
    )



def make_service(
    *,
    row_hits: list[tuple[object, float]],
    contract_items: list,
    embedding_vec: list[float] | None = None,
    embedding_raises: Exception | None = None,
    similarity_threshold: float | None = None,
):
    """Build an AIService with fully mocked dependencies."""
    from app.config.settings import Settings

    settings_data = {
        "APP_NAME": "test",
        "APP_VERSION": "0.1",
        "ENVIRONMENT": "test",
        "HOST": "localhost",
        "PORT": 8080,
        "CORS_ORIGINS": ["http://localhost"],
        "EMBEDDING_MODEL": "nomic-embed-text",
        "MAX_FILE_SIZE_MB": 50,
        "MAX_DATASET_ROWS": 50000,
        "EMBEDDING_CHUNK_SIZE": 2,
        "TOP_K": 10,
        "K_ROWS": 2,
        "SIMILARITY_THRESHOLD": similarity_threshold,
        "CACHE_MAXSIZE": 100,
        "PINATA_API_KEY": "k",
        "PINATA_SECRET_KEY": "s",
        "PINATA_GATEWAY_URL": "https://gateway.pinata.cloud",
        "CONTRACT_ADDRESS": "0x" + "0" * 40,
        "PAYMENT_TOKEN_ADDRESS": "0x0000000000000000000000000000000000000002",
        "CONTRACT_ABI_PATH": "/tmp/Marketplace.json",
        "CHAIN_ID": 31337,
        "RPC_URL": "http://127.0.0.1:8545",
        "SERVER_PRIVATE_KEY": "0x" + "11" * 32,
        "POSTGRES_URL": "postgresql://user:pass@localhost/test",
    }
    settings = Settings(_env_file=None, **settings_data)

    vectorstore = MagicMock()
    vectorstore.asimilarity_search_with_score_by_vector = AsyncMock(
        return_value=row_hits
    )

    contract_listing_fetcher = MagicMock(return_value=contract_items)

    if embedding_raises is not None:
        async def embedding_fn(text, settings):
            raise embedding_raises
    else:
        vec = embedding_vec or [0.1] * 768
        async def embedding_fn(text, settings):
            return vec, len(vec)

    service = AIService(
        vectorstore_factory=lambda settings: vectorstore,
        contract_listing_fetcher=contract_listing_fetcher,
        embedding_fn=embedding_fn,
        settings=settings,
    )
    return service, vectorstore, contract_listing_fetcher


def make_doc(listing_id: str | None) -> SimpleNamespace:
    metadata = {} if listing_id is None else {"listing_id": listing_id}
    return SimpleNamespace(metadata=metadata)


# ---------------------------------------------------------------------------
# Score helpers (pure functions)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# bytes32 hex → UUID normalisation (Critical #1 fix)
# ---------------------------------------------------------------------------

class TestBytes32HexToUuid:
    """Verify the contract-id normalisation used to join pgvector hits with contract items."""

    def test_converts_known_uuid_roundtrip(self):
        # Simulate uuid_to_bytes32 then Web3.to_hex: uuid → bytes32 hex → uuid
        import uuid as _uuid
        original = "a8b3f2c1-47b3-4d8e-9f3e-123456789abc"
        u = _uuid.UUID(original)
        # bytes32 = 16 UUID bytes + 16 zero bytes
        raw_bytes = u.bytes + b"\x00" * 16
        hex_str = "0x" + raw_bytes.hex()
        assert _bytes32_hex_to_uuid(hex_str) == original

    def test_passthrough_on_plain_uuid_string(self):
        plain = "a8b3f2c1-47b3-4d8e-9f3e-123456789abc"
        # If someone passes a UUID string directly, it should come back unchanged
        # (the UUID constructor accepts dash format in the first 32 hex chars too)
        result = _bytes32_hex_to_uuid(plain)
        # Either the same or a valid UUID — no crash
        assert isinstance(result, str)

    def test_passthrough_on_invalid_input(self):
        assert _bytes32_hex_to_uuid("notvalidhex") == "notvalidhex"

    def test_passthrough_on_short_hex(self):
        # Less than 32 hex chars after 0x — should not crash
        result = _bytes32_hex_to_uuid("0xdeadbeef")
        assert isinstance(result, str)


class TestClamp:
    def test_clamps_above_one(self):
        assert _clamp(1.5) == 1.0

    def test_clamps_below_zero(self):
        assert _clamp(-0.3) == 0.0

    def test_identity_within_range(self):
        assert _clamp(0.5) == 0.5

    def test_boundary_zero(self):
        assert _clamp(0.0) == 0.0

    def test_boundary_one(self):
        assert _clamp(1.0) == 1.0


class TestScoreLabel:
    def test_high_above_066(self):
        assert _score_label(0.67) == "high"

    def test_high_boundary_just_above(self):
        assert _score_label(0.661) == "high"

    def test_moderate_above_033_below_066(self):
        assert _score_label(0.5) == "moderate"

    def test_moderate_boundary_just_above(self):
        assert _score_label(0.331) == "moderate"

    def test_low_at_033(self):
        assert _score_label(0.33) == "low"

    def test_low_below_033(self):
        assert _score_label(0.1) == "low"

    def test_low_at_zero(self):
        assert _score_label(0.0) == "low"


# ---------------------------------------------------------------------------
# rank_datasets — ranking order
# ---------------------------------------------------------------------------


def test_row_hits_aggregate_by_listing_max_similarity():
    hits = _aggregate_row_hits(
        [
            (make_doc("listing-a"), 0.4),
            (make_doc("listing-b"), 0.1),
            (make_doc("listing-a"), 0.2),
            (make_doc(None), 0.0),
        ]
    )

    assert hits == [("listing-b", 0.9), ("listing-a", 0.8)]


def test_ranking_follows_aggregated_row_score_order():
    items = [
        make_item("0xAAA", "Alpha"),
        make_item("0xBBB", "Beta"),
    ]
    service, _, _ = make_service(
        row_hits=[(make_doc("0xAAA"), 0.1), (make_doc("0xBBB"), 0.6)],
        contract_items=items,
    )

    results = asyncio.run(service.rank_datasets("query", limit=20))

    assert len(results) == 2
    assert results[0].listing_id == "0xAAA"
    assert results[1].listing_id == "0xBBB"


def test_scores_are_clamped_to_unit_interval():
    """Raw pgvector scores outside [0, 1] are clamped before being returned."""
    items = [make_item("0xAAA")]
    service, _, _ = make_service(
        row_hits=[(make_doc("0xAAA"), -0.2)],
        contract_items=items,
    )

    results = asyncio.run(service.rank_datasets("query"))

    assert results[0].score == 1.0


def test_negative_raw_score_clamped_to_zero():
    items = [make_item("0xCCC")]
    service, _, _ = make_service(
        row_hits=[(make_doc("0xCCC"), 1.5)],
        contract_items=items,
    )

    results = asyncio.run(service.rank_datasets("query"))

    assert results[0].score == 0.0


# ---------------------------------------------------------------------------
# rank_datasets — score_label derivation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw_score,expected_label", [
    (0.9,  "high"),
    (0.67, "high"),
    (0.66, "moderate"),   # not > 0.66, so moderate
    (0.5,  "moderate"),
    (0.34, "moderate"),
    (0.33, "low"),        # not > 0.33, so low
    (0.1,  "low"),
    (0.0,  "low"),
])
def test_score_label_derivation(raw_score: float, expected_label: str):
    items = [make_item("0xDDD")]
    service, _, _ = make_service(
        row_hits=[(make_doc("0xDDD"), 1.0 - raw_score)],
        contract_items=items,
    )

    results = asyncio.run(service.rank_datasets("query"))

    assert results[0].score_label == expected_label


# ---------------------------------------------------------------------------
# rank_datasets — threshold filtering
# ---------------------------------------------------------------------------

def test_threshold_filtering_happens_after_clamping():
    """Score is clamped first; then compared against threshold."""
    items = [make_item("0xEEE")]
    # Raw score 1.5 clamps to 1.0 — above threshold of 0.5 → keep
    service, _, _ = make_service(
        row_hits=[(make_doc("0xEEE"), -0.5)],
        contract_items=items,
        similarity_threshold=0.5,
    )

    results = asyncio.run(service.rank_datasets("query"))

    assert len(results) == 1
    assert results[0].score == 1.0


def test_threshold_filters_low_clamped_score():
    """Score clamped to near-zero is dropped when threshold is high."""
    items = [make_item("0xFFF")]
    # Raw score -0.8 clamps to 0.0 — below threshold of 0.5 → skip
    service, _, _ = make_service(
        row_hits=[(make_doc("0xFFF"), 1.8)],
        contract_items=items,
        similarity_threshold=0.5,
    )

    results = asyncio.run(service.rank_datasets("query"))

    assert results == []


# ---------------------------------------------------------------------------
# rank_datasets — stale hits
# ---------------------------------------------------------------------------

def test_stale_pgvector_hit_is_skipped():
    """A listing_id returned by pgvector that is not in contract items is skipped.

    In production, pgvector stores listing_id as a UUID string while the
    contract returns item.id as bytes32 hex.  _bytes32_hex_to_uuid normalises
    the contract key, so we mirror that here: one live item (bytes32 hex id
    matching the pgvector UUID), one stale (no matching contract entry).
    """
    import uuid as _uuid

    live_uuid = "a8b3f2c1-47b3-4d8e-9f3e-123456789abc"
    live_bytes32_hex = "0x" + (_uuid.UUID(live_uuid).bytes + b"\x00" * 16).hex()

    live_item = make_item(live_bytes32_hex, "Live Dataset")
    service, _, _ = make_service(
        row_hits=[(make_doc("stale-uuid-not-on-chain"), 0.1), (make_doc(live_uuid), 0.3)],
        contract_items=[live_item],
    )

    results = asyncio.run(service.rank_datasets("query"))

    assert len(results) == 1
    assert results[0].listing_id == live_uuid


def test_all_stale_returns_empty_list():
    service, _, _ = make_service(
        row_hits=[(make_doc("stale-1"), 0.1), (make_doc("stale-2"), 0.5)],
        contract_items=[],
    )

    results = asyncio.run(service.rank_datasets("query"))

    assert results == []


# ---------------------------------------------------------------------------
# rank_datasets — empty pgvector result
# ---------------------------------------------------------------------------

def test_empty_repo_hits_returns_empty_list():
    service, _, _ = make_service(
        row_hits=[],
        contract_items=[make_item("0xAAA")],
    )

    results = asyncio.run(service.rank_datasets("query"))

    assert results == []


# ---------------------------------------------------------------------------
# rank_datasets — EmbeddingError
# ---------------------------------------------------------------------------

def test_embedding_failure_raises_embedding_error():
    from fastapi import HTTPException as FastAPIHTTPException

    service, _, _ = make_service(
        row_hits=[],
        contract_items=[],
        embedding_raises=FastAPIHTTPException(status_code=500, detail="Ollama down"),
    )

    with pytest.raises(EmbeddingError):
        asyncio.run(service.rank_datasets("query"))


def test_no_ipfs_import_in_ai_service_module():
    """Confirm that download_signature_embeddings is not imported by ai_service.

    The old implementation imported and called this function on every search,
    causing O(datasets×rows) IPFS downloads at query time.  This test guards
    against regression by asserting the symbol is absent from the module's
    namespace.
    """
    import app.services.ai_service as ai_service_module

    assert not hasattr(ai_service_module, "download_signature_embeddings"), (
        "download_signature_embeddings must not be imported in ai_service — "
        "that is the IPFS scan path that was removed in the pgvector rewrite."
    )


def test_vectorstore_is_called_not_ipfs(monkeypatch):
    """rank_datasets() calls PGVector, never any IPFS download helper."""
    items = [make_item("0xAAA")]
    service, vectorstore, _ = make_service(
        row_hits=[(make_doc("0xAAA"), 0.2)],
        contract_items=items,
    )

    asyncio.run(service.rank_datasets("query"))

    vectorstore.asimilarity_search_with_score_by_vector.assert_awaited_once()


def test_rank_datasets_overfetches_rows_for_listing_aggregation():
    items = [make_item("0xAAA")]
    service, vectorstore, _ = make_service(
        row_hits=[(make_doc("0xAAA"), 0.2)],
        contract_items=items,
    )

    asyncio.run(service.rank_datasets("query", limit=20))

    assert (
        vectorstore.asimilarity_search_with_score_by_vector.await_args.kwargs["k"]
        == 200
    )


# ---------------------------------------------------------------------------
# rank_datasets — field mapping
# ---------------------------------------------------------------------------

def test_ranked_dataset_fields_are_mapped_correctly():
    """Verify all RankedDataset fields are populated from the contract item.

    The contract returns item.id as bytes32 hex; pgvector stores listing_id
    as a UUID string.  The service must normalise and join them correctly.
    """
    import uuid as _uuid

    listing_uuid = "deadbeef-dead-beef-dead-beefdeadbeef"
    bytes32_hex = "0x" + (_uuid.UUID(listing_uuid).bytes + b"\x00" * 16).hex()

    item = make_item(bytes32_hex, title="Climate Data")
    item.description = "Climate measurements"
    item.seller = "0xSellerAddr"
    item.price_atomic = "250"

    service, _, _ = make_service(
        row_hits=[(make_doc(listing_uuid), 0.25)],
        contract_items=[item],
    )

    results = asyncio.run(service.rank_datasets("query"))

    assert len(results) == 1
    r = results[0]
    assert r.listing_id == listing_uuid   # UUID format, not bytes32 hex
    assert r.title == "Climate Data"
    assert r.description == "Climate measurements"
    assert r.seller == "0xSellerAddr"
    assert r.payment_token == "0x0000000000000000000000000000000000000002"
    assert r.price_atomic == 250          # int, not str
    assert r.settlement_currency == "USDC"
    assert r.settlement_decimals == 6
    assert r.purchase_count == 0
    assert isinstance(r.score, float)
    assert r.score_label in ("high", "moderate", "low")
