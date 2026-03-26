import asyncio
import uuid
from types import SimpleNamespace

from app.config.settings import Settings
from app.services import agent_service


def make_settings(**overrides) -> Settings:
    data = {
        "APP_NAME": "BridgeMart API",
        "APP_VERSION": "0.1.0",
        "ENVIRONMENT": "development",
        "HOST": "localhost",
        "PORT": 8080,
        "CORS_ORIGINS": ["http://localhost:5173"],
        "EMBEDDING_MODEL": "nomic-embed-text",
        "MAX_FILE_SIZE_MB": 50,
        "MAX_DATASET_ROWS": 50000,
        "EMBEDDING_CHUNK_SIZE": 2,
        "TOP_K": 10,
        "K_ROWS": 2,
        "SIMILARITY_THRESHOLD": None,
        "CACHE_MAXSIZE": 100,
        "PINATA_API_KEY": "k",
        "PINATA_SECRET_KEY": "s",
        "PINATA_GATEWAY_URL": "https://gateway.pinata.cloud",
        "CONTRACT_ADDRESS": "0x0000000000000000000000000000000000000000",
        "CONTRACT_ABI_PATH": "/tmp/Marketplace.json",
        "CHAIN_ID": 31337,
        "RPC_URL": "http://127.0.0.1:8545",
        "SERVER_PRIVATE_KEY": "0x" + "11" * 32,
        "POSTGRES_URL": "postgresql://user:password@localhost:5432/bridgemart",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


def test_generate_recommendation_success(monkeypatch):
    settings = make_settings()
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


def test_generate_recommendation_returns_none_when_no_results(monkeypatch):
    settings = make_settings()
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


def test_generate_recommendation_returns_none_below_threshold(monkeypatch):
    settings = make_settings()
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
