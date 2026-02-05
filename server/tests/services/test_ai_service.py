import asyncio

from app.services import ai_service
from app.schemas.marketplace_schema import MarketplaceDataItem


def make_item(item_id: int, sig_url: str, sig_hash: str):
    return MarketplaceDataItem(
        id=item_id,
        title=f"Dataset {item_id}",
        description="desc",
        seller="0xSeller",
        price=10,
        dataset_url="ipfs://dataset",
        dataset_hash="0xhash",
        signature_url=sig_url,
        signature_hash=sig_hash,
        exists=True,
    )


def test_rank_datasets_sorted_and_cached(monkeypatch, settings):
    def fake_generate_single_embedding(query, settings):
        return [1.0, 0.0], 2

    call_count = {"count": 0}

    async def fake_download_signature_embeddings(
        signature_url, settings, expected_signature_hash=None, compressed=True
    ):
        call_count["count"] += 1
        if signature_url.endswith("a"):
            return [[1.0, 0.0], [1.0, 0.0]]
        return [[0.5, 0.5]]

    monkeypatch.setattr(
        ai_service, "generate_single_embedding", fake_generate_single_embedding
    )
    monkeypatch.setattr(
        ai_service, "download_signature_embeddings", fake_download_signature_embeddings
    )

    service = ai_service.AIService(settings)
    datasets = [
        make_item(1, "ipfs://a", "0xhash"),
        make_item(2, "ipfs://b", "0xhash"),
    ]

    results = asyncio.run(service.rank_datasets("query", datasets))

    assert len(results) == 2
    assert results[0].item.id == 1
    assert call_count["count"] == 1


def test_similarity_threshold_filters(monkeypatch, settings):
    def fake_generate_single_embedding(query, settings):
        return [1.0, 0.0], 2

    async def fake_download_signature_embeddings(
        signature_url, settings, expected_signature_hash=None, compressed=True
    ):
        return [[0.1, 0.9]]

    monkeypatch.setattr(
        ai_service, "generate_single_embedding", fake_generate_single_embedding
    )
    monkeypatch.setattr(
        ai_service, "download_signature_embeddings", fake_download_signature_embeddings
    )

    strict_settings = settings.model_copy(update={"similarity_threshold": 0.99})
    service = ai_service.AIService(strict_settings)
    datasets = [make_item(1, "ipfs://a", "0xhash")]

    results = asyncio.run(service.rank_datasets("query", datasets))

    assert results == []
