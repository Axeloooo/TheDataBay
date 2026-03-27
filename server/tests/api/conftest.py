import os
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session

from app.config.settings import Settings, get_settings


def _seed_required_env() -> None:
    """Provide import-time settings for app.main during test collection."""

    defaults = {
        "APP_NAME": "BridgeMart API",
        "APP_VERSION": "0.1.0",
        "ENVIRONMENT": "test",
        "HOST": "localhost",
        "PORT": "8080",
        "CORS_ORIGINS": '["http://localhost:5173"]',
        "EMBEDDING_MODEL": "nomic-embed-text",
        "MAX_FILE_SIZE_MB": "50",
        "MAX_DATASET_ROWS": "50000",
        "EMBEDDING_CHUNK_SIZE": "2",
        "TOP_K": "10",
        "K_ROWS": "2",
        "SIMILARITY_THRESHOLD": "0.5",
        "CACHE_MAXSIZE": "100",
        "PINATA_API_KEY": "k",
        "PINATA_SECRET_KEY": "s",
        "PINATA_GATEWAY_URL": "https://gateway.pinata.cloud",
        "CONTRACT_ADDRESS": "0x0000000000000000000000000000000000000000",
        "CONTRACT_ABI_PATH": "/tmp/Marketplace.json",
        "CHAIN_ID": "31337",
        "RPC_URL": "http://127.0.0.1:8545",
        "SERVER_PRIVATE_KEY": "0x" + "11" * 32,
        "POSTGRES_URL": "sqlite:///./test.db",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


_seed_required_env()

from app.database import engine as db_engine_module
from app import main as main_module
from app.main import app
from app.models.agent import Agent, AgentPurchaseRequest, AgentRecommendation
from app.models.dataset_key import DatasetKey
from app.routers import health_router

_REGISTERED_MODELS = (
    Agent,
    AgentRecommendation,
    AgentPurchaseRequest,
    DatasetKey,
)


def make_settings(**overrides: Any) -> Settings:
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
        "POSTGRES_URL": "sqlite:///./test.db",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


@pytest.fixture
def settings_factory() -> Callable[..., Settings]:
    return make_settings


@pytest.fixture
def settings(settings_factory: Callable[..., Settings]) -> Settings:
    return settings_factory()


@pytest.fixture(autouse=True)
def dependency_overrides() -> Generator[None, None, None]:
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
        get_settings.cache_clear()


@pytest.fixture
def override_settings(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> Callable[..., Settings]:
    def _override(*, settings: Settings | None = None, **overrides: Any) -> Settings:
        resolved = settings if settings is not None else settings_factory(**overrides)
        app.dependency_overrides[get_settings] = lambda: resolved
        monkeypatch.setattr(health_router, "get_settings", lambda: resolved)
        monkeypatch.setattr(db_engine_module, "get_settings", lambda: resolved)
        monkeypatch.setattr(main_module, "settings", resolved, raising=False)
        return resolved

    return _override


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    original_get_engine = db_engine_module.get_engine
    db_engine_module.get_engine = lambda: engine  # type: ignore[assignment]
    try:
        yield engine
    finally:
        db_engine_module.get_engine = original_get_engine
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def client_factory(
    db_engine: Engine,
    override_settings: Callable[..., Settings],
) -> Callable[..., Iterator[TestClient]]:
    @contextmanager
    def _make_client(
        *, settings: Settings | None = None, **overrides: Any
    ) -> Iterator[TestClient]:
        override_settings(settings=settings, **overrides)
        with TestClient(app) as client:
            yield client

    return _make_client


@pytest.fixture
def client(
    client_factory: Callable[..., Iterator[TestClient]],
) -> Generator[TestClient, None, None]:
    with client_factory() as test_client:
        yield test_client
