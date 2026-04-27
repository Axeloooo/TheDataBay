"""
Conftest for integration/routers tests.

Seeds required environment variables before any app module is imported so that
``app/main.py``'s module-level ``get_settings()`` call succeeds during pytest
collection.  This mirrors the pattern used in tests/unit/api/conftest.py.
"""

import os

_REQUIRED_DEFAULTS = {
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
    "POSTGRES_URL": "postgresql://user:password@localhost:5432/bridgemart",
}

for _key, _val in _REQUIRED_DEFAULTS.items():
    os.environ.setdefault(_key, _val)
