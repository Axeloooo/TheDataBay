from collections.abc import Callable, Generator
from typing import Any

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.auth.models import AuthNonce
from app.config.settings import Settings

TEST_JWT_SECRET = "test-secret-" + "x" * 40


def make_settings(**overrides: Any) -> Settings:
    data = {
        "APP_NAME": "TheDataBay API",
        "APP_VERSION": "0.1.0",
        "ENVIRONMENT": "test",
        "HOST": "localhost",
        "PORT": 8080,
        "CORS_ORIGINS": ["http://localhost:5173"],
        "LLM_EMBEDDING_MODEL": "nomic-embed-text",
        "LLM_EMBEDDING_DIMENSION": 768,
        "MAX_FILE_SIZE_MB": 50,
        "MAX_DATASET_ROWS": 50000,
        "TOP_K": 10,
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
        "POSTGRES_URL": "sqlite://",
        "AUTH_JWT_SECRET": TEST_JWT_SECRET,
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


@pytest.fixture
def settings_factory() -> Callable[..., Settings]:
    return make_settings


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine, tables=[AuthNonce.__table__])
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


@pytest.fixture
def wallet():
    return Account.create()


def sign(account, message: str) -> str:
    signed = account.sign_message(encode_defunct(text=message))
    return "0x" + signed.signature.hex().removeprefix("0x")
