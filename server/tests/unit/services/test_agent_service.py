import asyncio
import uuid
from types import SimpleNamespace

from app.services import agent_service
from app.schemas.ai_schema import RankedDataset


def make_ranked(listing_id: str, title: str, score: float) -> RankedDataset:
    return RankedDataset(
        listing_id=listing_id,
        title=title,
        description="desc",
        seller="0xSeller",
        price_atomic=10,
        score=score,
        score_label="high" if score > 0.66 else ("moderate" if score > 0.33 else "low"),
    )


def test_generate_recommendation_success(monkeypatch):
    agent_id = uuid.uuid4()
    session = object()
    top_result = make_ranked("0x" + "01" * 32, "Climate Data", 0.72)
    captured = {}

    class FakeAIService:
        async def rank_datasets(self, query: str, limit: int = 20):
            assert query == "find climate datasets"
            return [top_result]

    def fake_create_recommendation(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(agent_service, "create_recommendation", fake_create_recommendation)

    recommendation = asyncio.run(
        agent_service.generate_recommendation(
            agent_id=agent_id,
            query="find climate datasets",
            session=session,
            ai_service=FakeAIService(),
        )
    )

    assert recommendation is not None
    assert captured["agent_id"] == agent_id
    assert captured["listing_id"] == "0x" + "01" * 32
    assert captured["confidence"] == 0.72
    assert captured["similarity_score"] == 0.72
    assert "find climate datasets" in captured["rationale"]
    assert captured["pros"] == [
        "High semantic similarity score: 0.720",
        "Dataset: Climate Data",
    ]
    assert captured["cons"] == [
        "Recommendation is based on semantic similarity only, not manual curation"
    ]
    assert captured["suggested_use_cases"] == ["find climate datasets"]


def test_generate_recommendation_returns_none_when_no_results(monkeypatch):
    agent_id = uuid.uuid4()
    session = object()

    class FakeAIService:
        async def rank_datasets(self, query: str, limit: int = 20):
            return []

    monkeypatch.setattr(agent_service, "create_recommendation", lambda **kwargs: None)

    recommendation = asyncio.run(
        agent_service.generate_recommendation(
            agent_id=agent_id,
            query="nothing",
            session=session,
            ai_service=FakeAIService(),
        )
    )

    assert recommendation is None


def test_generate_recommendation_returns_none_below_threshold(monkeypatch):
    agent_id = uuid.uuid4()
    session = object()
    top_result = make_ranked("0x" + "02" * 32, "Small Data", 0.05)
    create_called = {"value": False}

    class FakeAIService:
        async def rank_datasets(self, query: str, limit: int = 20):
            return [top_result]

    def fake_create_recommendation(**kwargs):
        create_called["value"] = True
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(agent_service, "create_recommendation", fake_create_recommendation)

    recommendation = asyncio.run(
        agent_service.generate_recommendation(
            agent_id=agent_id,
            query="small data",
            session=session,
            ai_service=FakeAIService(),
        )
    )

    assert recommendation is None
    assert create_called["value"] is False
