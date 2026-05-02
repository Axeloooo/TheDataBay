import io

import pytest
from fastapi import UploadFile

from app.config.settings import Settings


def make_settings(**overrides) -> Settings:
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
        "PAYMENT_TOKEN_ADDRESS": "0x0000000000000000000000000000000000000002",
        "CADC_TOKEN_ADDRESS": "0x0000000000000000000000000000000000000003",
        "CONTRACT_ABI_PATH": "/tmp/Marketplace.json",
        "CHAIN_ID": 31337,
        "RPC_URL": "http://127.0.0.1:8545",
        "SERVER_PRIVATE_KEY": "0x" + "11" * 32,
        "POSTGRES_URL": "postgresql://user:password@localhost:5432/thedatabay",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


def make_upload_file(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content))
