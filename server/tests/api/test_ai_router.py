from app.routers import ai_router
from app.schemas.ai_schema import RankedDataset, ScoreExplanation
from app.schemas.marketplace_schema import MarketplaceDataItem


def make_item(item_id: str) -> MarketplaceDataItem:
    return MarketplaceDataItem(
        id=item_id,
        title=f"Dataset {item_id[-4:]}",
        description="Sample dataset",
        seller="0x0000000000000000000000000000000000000001",
        price_atomic="100",
        settlement_currency="USDC",
        settlement_decimals=6,
        dataset_url="ipfs://dataset",
        dataset_hash="0xdataset",
        signature_url="ipfs://signature",
        signature_hash="0xsignature",
        exists=True,
        purchase_count=1,
    )


class StubAIService:
    def __init__(self, ranked_results):
        self.ranked_results = ranked_results
        self.calls = []

    async def rank_datasets(self, query, datasets):
        self.calls.append((query, datasets))
        return self.ranked_results


def test_similarity_search_returns_ranked_results(client, monkeypatch):
    dataset = make_item("0x" + "01" * 32)
    ranked = [
        RankedDataset(
            item=dataset,
            score=0.97,
            explanation=ScoreExplanation(
                k_rows=2,
                rows_in_dataset=5,
                dimension=3,
            ),
        )
    ]
    ai_service = StubAIService(ranked)

    monkeypatch.setattr(ai_router, "get_all_items", lambda settings: [dataset])
    client.app.dependency_overrides[ai_router.get_ai_service] = lambda: ai_service

    response = client.post(
        "/api/v1/ai/similarity-search",
        json={"query": "customer churn"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "customer churn",
        "results": [
            {
                "item": dataset.model_dump(),
                "score": 0.97,
                "explanation": {
                    "method": "topk_mean_cosine",
                    "k_rows": 2,
                    "rows_in_dataset": 5,
                    "dimension": 3,
                    "normalized": True,
                },
            }
        ],
        "count": 1,
    }
    assert ai_service.calls == [("customer churn", [dataset])]


def test_similarity_search_returns_empty_results_when_no_items(
    client, monkeypatch
):
    class FailingAIService:
        async def rank_datasets(self, query, datasets):
            raise AssertionError("rank_datasets should not be called when no items exist")

    monkeypatch.setattr(ai_router, "get_all_items", lambda settings: [])
    client.app.dependency_overrides[ai_router.get_ai_service] = lambda: FailingAIService()

    response = client.post(
        "/api/v1/ai/similarity-search",
        json={"query": "no results"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "no results",
        "results": [],
        "count": 0,
    }


def test_similarity_search_validates_required_query(client, monkeypatch):
    def fail_get_all_items(settings):
        raise AssertionError("get_all_items should not be called for invalid payloads")

    monkeypatch.setattr(ai_router, "get_all_items", fail_get_all_items)

    response = client.post("/api/v1/ai/similarity-search", json={})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(error["loc"][-1] == "query" for error in detail)
