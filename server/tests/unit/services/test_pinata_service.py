import asyncio
import gzip
import hashlib
import json

import pytest
from fastapi import HTTPException

from app.config.settings import Settings
from app.services import pinata_service


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
        "POSTGRES_URL": "mysql+pymysql://user:password@localhost:3306/bridgemart?charset=utf8mb4",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


class FakeResponse:
    def __init__(self, status_code, text="", json_data=None, content=b""):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data or {}
        self.content = content

    def json(self):
        return self._json_data


def make_async_client(post_response=None, get_response=None):
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self._post_response = post_response
            self._get_response = get_response

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return self._post_response

        async def get(self, *args, **kwargs):
            return self._get_response

    return FakeAsyncClient


def test_upload_signature_success(monkeypatch, settings):
    response = FakeResponse(status_code=200, json_data={"IpfsHash": "QmHash"})
    monkeypatch.setattr(
        pinata_service.httpx,
        "AsyncClient",
        make_async_client(post_response=response),
    )

    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    filename = "data.csv"

    ipfs_url, signature_hash = asyncio.run(
        pinata_service.upload_signature(embeddings, filename, settings, compress=True)
    )

    expected_bytes = json.dumps(
        {"embeddings": embeddings, "filename": filename}
    ).encode("utf-8")
    expected_bytes = gzip.compress(expected_bytes)
    expected_hash = "0x" + hashlib.sha256(expected_bytes).hexdigest()

    assert ipfs_url == "ipfs://QmHash"
    assert signature_hash == expected_hash


def test_upload_signature_without_compression(monkeypatch, settings):
    response = FakeResponse(status_code=200, json_data={"IpfsHash": "QmHash"})
    monkeypatch.setattr(
        pinata_service.httpx,
        "AsyncClient",
        make_async_client(post_response=response),
    )

    embeddings = [[0.1, 0.2]]
    filename = "data.csv"

    ipfs_url, signature_hash = asyncio.run(
        pinata_service.upload_signature(embeddings, filename, settings, compress=False)
    )

    expected_bytes = json.dumps(
        {"embeddings": embeddings, "filename": filename}
    ).encode("utf-8")
    expected_hash = "0x" + hashlib.sha256(expected_bytes).hexdigest()

    assert ipfs_url == "ipfs://QmHash"
    assert signature_hash == expected_hash


def test_upload_bytes_success(monkeypatch, settings):
    response = FakeResponse(status_code=200, json_data={"IpfsHash": "QmHash"})
    monkeypatch.setattr(
        pinata_service.httpx,
        "AsyncClient",
        make_async_client(post_response=response),
    )

    payload = b"ciphertext"
    ipfs_url, file_hash = asyncio.run(
        pinata_service.upload_bytes(payload, "data.csv", settings)
    )

    assert ipfs_url == "ipfs://QmHash"
    assert file_hash.startswith("0x")


def test_upload_signature_missing_credentials():
    settings = make_settings(PINATA_API_KEY="", PINATA_SECRET_KEY="")

    with pytest.raises(HTTPException):
        asyncio.run(
            pinata_service.upload_signature(
                [[0.1]], "file.csv", settings, compress=True
            )
        )


def test_test_connection_success(monkeypatch, settings):
    response = FakeResponse(status_code=200)
    monkeypatch.setattr(
        pinata_service.httpx,
        "AsyncClient",
        make_async_client(get_response=response),
    )

    assert asyncio.run(pinata_service.test_connection(settings)) is True


def test_test_connection_missing_credentials():
    settings = make_settings(PINATA_API_KEY="", PINATA_SECRET_KEY="")
    assert asyncio.run(pinata_service.test_connection(settings)) is False


def test_download_signature_embeddings_success(monkeypatch, settings):
    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    payload = json.dumps({"embeddings": embeddings, "filename": "data.csv"}).encode(
        "utf-8"
    )
    compressed = gzip.compress(payload)
    expected_hash = "0x" + hashlib.sha256(compressed).hexdigest()

    response = FakeResponse(status_code=200, content=compressed)
    monkeypatch.setattr(
        pinata_service.httpx,
        "AsyncClient",
        make_async_client(get_response=response),
    )

    result = asyncio.run(
        pinata_service.download_signature_embeddings(
            signature_url="ipfs://QmHash",
            settings=settings,
            expected_signature_hash=expected_hash,
            compressed=True,
        )
    )

    assert result == embeddings


def test_download_signature_embeddings_hash_mismatch(monkeypatch, settings):
    embeddings = [[0.1, 0.2]]
    payload = json.dumps({"embeddings": embeddings, "filename": "data.csv"}).encode(
        "utf-8"
    )
    compressed = gzip.compress(payload)

    response = FakeResponse(status_code=200, content=compressed)
    monkeypatch.setattr(
        pinata_service.httpx,
        "AsyncClient",
        make_async_client(get_response=response),
    )

    with pytest.raises(HTTPException):
        asyncio.run(
            pinata_service.download_signature_embeddings(
                signature_url="ipfs://QmHash",
                settings=settings,
                expected_signature_hash="0xdeadbeef",
                compressed=True,
            )
        )


def test_download_signature_embeddings_invalid_ipfs_url(settings):
    with pytest.raises(HTTPException):
        asyncio.run(
            pinata_service.download_signature_embeddings(
                signature_url="http://bad",
                settings=settings,
                expected_signature_hash=None,
                compressed=True,
            )
        )
