import asyncio
import uuid
from types import SimpleNamespace

from app.services import agent_service


def test_generate_recommendation_success(monkeypatch, settings):
    agent_id = uuid.uuid4()
    session = object()
    datasets = [SimpleNamespace(id="0x" + "01" * 32, title="Climate Data")]
    top_result = SimpleNamespace(
        score=0.72,
        item=SimpleNamespace(id=datasets[0].id, title=datasets[0].title),
    )
    captured = {}

    monkeypatch.setattr(agent_service, "get_all_items", lambda settings: datasets)

    class FakeAIService:
        async def rank_datasets(self, query, ranked_datasets):
            assert query == "find climate datasets"
            assert ranked_datasets == datasets
            return [top_result]

    def fake_create_recommendation(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(
        agent_service, "create_recommendation", fake_create_recommendation
    )

    recommendation = asyncio.run(
        agent_service.generate_recommendation(
            agent_id=agent_id,
            query="find climate datasets",
            session=session,
            ai_service=FakeAIService(),
            settings=settings,
        )
    )

    assert recommendation is not None
    assert captured["agent_id"] == agent_id
    assert captured["listing_id"] == datasets[0].id
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


def test_generate_recommendation_returns_none_when_no_results(monkeypatch, settings):
    agent_id = uuid.uuid4()
    session = object()

    monkeypatch.setattr(agent_service, "get_all_items", lambda settings: [])

    class FakeAIService:
        async def rank_datasets(self, query, ranked_datasets):
            assert query == "nothing"
            assert ranked_datasets == []
            return []

    monkeypatch.setattr(agent_service, "create_recommendation", lambda **kwargs: None)

    recommendation = asyncio.run(
        agent_service.generate_recommendation(
            agent_id=agent_id,
            query="nothing",
            session=session,
            ai_service=FakeAIService(),
            settings=settings,
        )
    )

    assert recommendation is None


def test_generate_recommendation_returns_none_below_threshold(monkeypatch, settings):
    agent_id = uuid.uuid4()
    session = object()
    datasets = [SimpleNamespace(id="0x" + "02" * 32, title="Small Data")]
    top_result = SimpleNamespace(
        score=0.05,
        item=SimpleNamespace(id=datasets[0].id, title=datasets[0].title),
    )
    create_called = {"value": False}

    monkeypatch.setattr(agent_service, "get_all_items", lambda settings: datasets)

    class FakeAIService:
        async def rank_datasets(self, query, ranked_datasets):
            return [top_result]

    def fake_create_recommendation(**kwargs):
        create_called["value"] = True
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(
        agent_service, "create_recommendation", fake_create_recommendation
    )

    recommendation = asyncio.run(
        agent_service.generate_recommendation(
            agent_id=agent_id,
            query="small data",
            session=session,
            ai_service=FakeAIService(),
            settings=settings,
        )
    )

    assert recommendation is None
    assert create_called["value"] is False
