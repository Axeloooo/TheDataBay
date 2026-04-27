import pytest

from app.config.settings import Settings
from app.services.job_manager import JobManager


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
        "PAYMENT_TOKEN_ADDRESS": "0x0000000000000000000000000000000000000002",
        "CONTRACT_ABI_PATH": "/tmp/Marketplace.json",
        "CHAIN_ID": 31337,
        "RPC_URL": "http://127.0.0.1:8545",
        "SERVER_PRIVATE_KEY": "0x" + "11" * 32,
        "POSTGRES_URL": "postgresql://user:password@localhost:5432/bridgemart",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def job_manager() -> JobManager:
    return JobManager()
