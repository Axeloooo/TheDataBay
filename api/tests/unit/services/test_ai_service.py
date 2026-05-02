"""Unit tests for AIService semantic dataset search."""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.service import (
    AIService,
    EmbeddingError,
    _bytes32_hex_to_uuid,
    _clamp,
    _score_label,
)
from app.llm.schemas import EmbeddingResult


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


def make_doc(
    *,
    dataset_id: str,
    listing_id: str,
    page_content: str,
    dataset_filename: str = "dataset.csv",
    summary_kind: str = "overview",
    summary_index: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        page_content=page_content,
        metadata={
            "dataset_id": dataset_id,
            "listing_id": listing_id,
            "dataset_filename": dataset_filename,
            "summary_kind": summary_kind,
            "summary_index": summary_index,
        },
    )


def make_settings(**overrides) -> SimpleNamespace:
    data = {
        "top_k": 10,
        "llm_embedding_model": "nomic-embed-text",
        "dataset_summary_count": 5,
        "similarity_threshold": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_service(
    *,
    summary_hits: list[tuple[object, float]],
    contract_items: list,
    embedding_vector: list[float] | None = None,
    embedding_raises: Exception | None = None,
    settings: SimpleNamespace | None = None,
):
    llm_service = MagicMock()
    if embedding_raises is not None:
        llm_service.embed_text = AsyncMock(side_effect=embedding_raises)
    else:
        vector = embedding_vector or [0.1, 0.2, 0.3]
        llm_service.embed_text = AsyncMock(
            return_value=EmbeddingResult(
                vector=vector,
                model="test-embedding",
                dimension=len(vector),
            )
        )

    vector_repository = MagicMock()
    vector_repository.similarity_search_by_vector = AsyncMock(return_value=summary_hits)
    contract_listing_fetcher = MagicMock(return_value=contract_items)

    service = AIService(
        llm_service=llm_service,
        vector_repository=vector_repository,
        contract_listing_fetcher=contract_listing_fetcher,
        settings=settings or make_settings(),
    )
    return service, llm_service, vector_repository, contract_listing_fetcher


class TestBytes32HexToUuid:
    def test_converts_known_uuid_roundtrip(self):
        original = "a8b3f2c1-47b3-4d8e-9f3e-123456789abc"
        raw_bytes = uuid.UUID(original).bytes + b"\x00" * 16

        assert _bytes32_hex_to_uuid("0x" + raw_bytes.hex()) == original

    def test_passthrough_on_invalid_input(self):
        assert _bytes32_hex_to_uuid("notvalidhex") == "notvalidhex"


class TestClamp:
    def test_clamps_above_one(self):
        assert _clamp(1.5) == 1.0

    def test_clamps_below_zero(self):
        assert _clamp(-0.3) == 0.0

    def test_identity_within_range(self):
        assert _clamp(0.5) == 0.5


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (0.72, "high"),
        (0.719, "moderate"),
        (0.58, "moderate"),
        (0.579, "low"),
        (0.42, "low"),
        (0.419, "no_match"),
    ],
)
def test_score_label_uses_fixed_search_bands(score: float, label: str):
    assert _score_label(score) == label


def test_strong_match_embeds_query_searches_summaries_and_joins_listing():
    item = make_item("listing-1", title="Heart Cohort")
    service, llm_service, vector_repository, contract_fetcher = make_service(
        summary_hits=[
            (
                make_doc(
                    dataset_id="dataset-1",
                    listing_id="listing-1",
                    page_content="Summary: heart patients with age and cholesterol fields.",
                ),
                0.91,
            )
        ],
        contract_items=[item],
    )

    results = asyncio.run(service.rank_datasets("heart cholesterol", limit=5))

    llm_service.embed_text.assert_awaited_once_with("heart cholesterol")
    vector_repository.similarity_search_by_vector.assert_awaited_once_with(
        [0.1, 0.2, 0.3],
        k=25,
    )
    contract_fetcher.assert_called_once()
    assert len(results) == 1
    result = results[0]
    assert result.dataset_id == "dataset-1"
    assert result.listing_id == "listing-1"
    assert result.title == "Heart Cohort"
    assert result.score == 0.91
    assert result.score_label == "high"
    assert result.best_summary == "Summary: heart patients with age and cholesterol fields."


def test_weak_match_is_returned_with_low_label():
    service, _, _, _ = make_service(
        summary_hits=[
            (
                make_doc(
                    dataset_id="dataset-weak",
                    listing_id="listing-weak",
                    page_content="Some faintly related tabular metadata.",
                ),
                0.43,
            )
        ],
        contract_items=[make_item("listing-weak")],
    )

    results = asyncio.run(service.rank_datasets("weak signal", limit=5))

    assert len(results) == 1
    assert results[0].score == 0.43
    assert results[0].score_label == "low"


def test_off_domain_no_match_is_filtered():
    service, _, _, contract_fetcher = make_service(
        summary_hits=[
            (
                make_doc(
                    dataset_id="dataset-off",
                    listing_id="listing-off",
                    page_content="Retail inventory summary.",
                ),
                0.419,
            )
        ],
        contract_items=[make_item("listing-off")],
    )

    results = asyncio.run(service.rank_datasets("cardiology trial", limit=5))

    assert results == []
    contract_fetcher.assert_not_called()


def test_top_k_is_final_dataset_limit_and_not_row_overfetch():
    hits = [
        (
            make_doc(
                dataset_id=f"dataset-{index}",
                listing_id=f"listing-{index}",
                page_content=f"Useful summary {index}",
            ),
            0.9 - index * 0.01,
        )
        for index in range(5)
    ]
    service, _, vector_repository, _ = make_service(
        summary_hits=hits,
        contract_items=[make_item(f"listing-{index}") for index in range(5)],
        settings=make_settings(top_k=3),
    )

    results = asyncio.run(service.rank_datasets("useful data", limit=5))

    vector_repository.similarity_search_by_vector.assert_awaited_once_with(
        [0.1, 0.2, 0.3],
        k=15,
    )
    assert [result.dataset_id for result in results] == [
        "dataset-0",
        "dataset-1",
        "dataset-2",
    ]


def test_similarity_threshold_can_raise_minimum_score_above_low_band():
    service, _, _, _ = make_service(
        summary_hits=[
            (
                make_doc(
                    dataset_id="dataset-low",
                    listing_id="listing-low",
                    page_content="Low but normally matchable summary.",
                ),
                0.43,
            )
        ],
        contract_items=[make_item("listing-low")],
        settings=make_settings(similarity_threshold=0.5),
    )

    assert asyncio.run(service.rank_datasets("weak signal", limit=5)) == []


def test_dedupes_summary_hits_by_dataset_id_and_keeps_best_summary():
    service, _, _, _ = make_service(
        summary_hits=[
            (
                make_doc(
                    dataset_id="dataset-1",
                    listing_id="listing-1",
                    page_content="Weaker summary for the same dataset.",
                    summary_index=0,
                ),
                0.6,
            ),
            (
                make_doc(
                    dataset_id="dataset-1",
                    listing_id="listing-1",
                    page_content="Best summary with age, sex, and cholesterol.",
                    summary_index=1,
                ),
                0.88,
            ),
            (
                make_doc(
                    dataset_id="dataset-2",
                    listing_id="listing-2",
                    page_content="Another dataset summary.",
                ),
                0.7,
            ),
        ],
        contract_items=[make_item("listing-1"), make_item("listing-2")],
    )

    results = asyncio.run(service.rank_datasets("heart columns", limit=5))

    assert [result.dataset_id for result in results] == ["dataset-1", "dataset-2"]
    assert results[0].score == 0.88
    assert results[0].best_summary == "Best summary with age, sex, and cholesterol."


def test_response_schema_includes_dataset_and_summary_fields():
    service, _, _, _ = make_service(
        summary_hits=[
            (
                make_doc(
                    dataset_id="dataset-schema",
                    listing_id="listing-schema",
                    page_content="Schema coverage summary.",
                ),
                0.75,
            )
        ],
        contract_items=[make_item("listing-schema")],
    )

    result = asyncio.run(service.rank_datasets("schema", limit=1))[0]
    payload = result.model_dump()

    assert payload == {
        "dataset_id": "dataset-schema",
        "listing_id": "listing-schema",
        "title": "Test Dataset",
        "description": "A test dataset",
        "seller": "0xSeller",
        "payment_token": "0x0000000000000000000000000000000000000002",
        "price_atomic": 100,
        "settlement_currency": "USDC",
        "settlement_decimals": 6,
        "purchase_count": 0,
        "score": 0.75,
        "score_label": "high",
        "best_summary": "Schema coverage summary.",
    }


def test_bytes32_contract_listing_id_joins_to_uuid_metadata_listing_id():
    listing_uuid = "deadbeef-dead-beef-dead-beefdeadbeef"
    bytes32_hex = "0x" + (uuid.UUID(listing_uuid).bytes + b"\x00" * 16).hex()
    service, _, _, _ = make_service(
        summary_hits=[
            (
                make_doc(
                    dataset_id="dataset-uuid",
                    listing_id=listing_uuid,
                    page_content="UUID listing summary.",
                ),
                0.82,
            )
        ],
        contract_items=[make_item(bytes32_hex, "UUID Dataset")],
    )

    results = asyncio.run(service.rank_datasets("uuid", limit=5))

    assert len(results) == 1
    assert results[0].listing_id == listing_uuid
    assert results[0].title == "UUID Dataset"


def test_embedding_failure_raises_embedding_error():
    service, _, _, _ = make_service(
        summary_hits=[],
        contract_items=[],
        embedding_raises=RuntimeError("provider down"),
    )

    with pytest.raises(EmbeddingError):
        asyncio.run(service.rank_datasets("query"))


def test_ai_service_no_longer_imports_ollama_or_langchain_pgvector_boundaries():
    import app.ai.service as ai_service_module

    assert not hasattr(ai_service_module, "get_embeddings")
    assert not hasattr(ai_service_module, "vectorstore_for_settings")
