from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

import app.indexer.models  # noqa: F401  (register tables)
from app.config.settings import Settings

from .fakes import MARKETPLACE, USDC


def make_settings(**overrides: Any) -> Settings:
    data: dict[str, Any] = {
        "APP_NAME": "TheDataBay API",
        "APP_VERSION": "0.1.0",
        "ENVIRONMENT": "test",
        "HOST": "localhost",
        "PORT": 8080,
        "CORS_ORIGINS": ["http://localhost:5173"],
        "MAX_FILE_SIZE_MB": 50,
        "MAX_DATASET_ROWS": 50000,
        "TOP_K": 10,
        "SIMILARITY_THRESHOLD": None,
        "CACHE_MAXSIZE": 100,
        "PINATA_API_KEY": "k",
        "PINATA_SECRET_KEY": "s",
        "PINATA_GATEWAY_URL": "https://gateway.pinata.cloud",
        "CONTRACT_ADDRESS": MARKETPLACE,
        "USDC_TOKEN_ADDRESS": USDC,
        "CONTRACT_ABI_PATH": "/nonexistent/Marketplace.json",
        "CHAIN_ID": 31337,
        "RPC_URL": "http://127.0.0.1:8545",
        "SERVER_PRIVATE_KEY": "0x" + "11" * 32,
        "POSTGRES_URL": "sqlite://",
        "INDEXER_ENABLED": True,
        "INDEXER_START_BLOCK": 100,
        "INDEXER_BLOCK_CHUNK": 10,
        "INDEXER_CONFIRMATIONS": 2,
        "INDEXER_POLL_SECONDS": 1,
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    with Session(engine) as s:
        yield s
