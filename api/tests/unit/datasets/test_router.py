import os

import pytest
from fastapi.testclient import TestClient

DEFAULT_ENV = {
    "APP_NAME": "TheDataBay API",
    "APP_VERSION": "0.1.0",
    "ENVIRONMENT": "test",
    "HOST": "localhost",
    "PORT": "8080",
    "CORS_ORIGINS": '["http://localhost:5173"]',
    "LLM_EMBEDDING_MODEL": "nomic-embed-text",
    "LLM_EMBEDDING_DIMENSION": "768",
    "MAX_FILE_SIZE_MB": "50",
    "MAX_DATASET_ROWS": "50000",
    "TOP_K": "10",
    "SIMILARITY_THRESHOLD": "0.5",
    "CACHE_MAXSIZE": "100",
    "PINATA_API_KEY": "k",
    "PINATA_SECRET_KEY": "s",
    "PINATA_GATEWAY_URL": "https://gateway.pinata.cloud",
    "CONTRACT_ADDRESS": "0x0000000000000000000000000000000000000000",
    "PAYMENT_TOKEN_ADDRESS": "0x0000000000000000000000000000000000000002",
    "CADC_TOKEN_ADDRESS": "0x0000000000000000000000000000000000000003",
    "CONTRACT_ABI_PATH": "/tmp/Marketplace.json",
    "CHAIN_ID": "31337",
    "RPC_URL": "http://127.0.0.1:8545",
    "SERVER_PRIVATE_KEY": "0x" + "11" * 32,
    "POSTGRES_URL": "sqlite:///./test.db",
}
for key, value in DEFAULT_ENV.items():
    os.environ.setdefault(key, value)

from app.datasets.schemas import (
    DatasetEmbedResponse,
    DatasetPreviewResponse,
    DatasetStats,
    VectorSpec,
)
from app.datasets.service import get_dataset_embed_service
from app import main as main_module
from app.main import app
from app.database.engine import get_session
from app.shared.errors import ApiError
from app.datasets import router as datasets_router


class FakeDatasetEmbedService:
    def __init__(self, *, error: ApiError | None = None) -> None:
        self.error = error
        self.calls = []

    async def embed(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return DatasetEmbedResponse(
            listing_id="123e4567-e89b-12d3-a456-426614174000",
            dataset_url="ipfs://QmData",
            dataset_hash="0xdata",
            preview=DatasetPreviewResponse(
                column_names=["age", "cp"],
                rows=[["63", "3"]],
            ),
            stats=DatasetStats(
                total_rows=1,
                total_columns=2,
                has_header=True,
                empty_rows_skipped=0,
            ),
            vector_spec=VectorSpec(model="nomic-embed-text", dimension=768),
        )


@pytest.fixture(autouse=True)
def clear_overrides(monkeypatch):
    original = dict(app.dependency_overrides)
    monkeypatch.setattr(main_module, "create_db_and_tables", lambda: None)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


def test_embed_dataset_returns_completed_payload():
    fake_service = FakeDatasetEmbedService()
    app.dependency_overrides[get_dataset_embed_service] = lambda: fake_service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/datasets/embed",
            data={
                "title": "Retail Data",
                "description": "Point of sale records",
                "seller": "0x0000000000000000000000000000000000000001",
                "price_atomic": "250",
            },
            files={"file": ("retail.csv", b"age,cp\n63,3\n", "text/csv")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "listing_id": "123e4567-e89b-12d3-a456-426614174000",
        "dataset_url": "ipfs://QmData",
        "dataset_hash": "0xdata",
        "preview": {"column_names": ["age", "cp"], "rows": [["63", "3"]]},
        "stats": {
            "total_rows": 1,
            "total_columns": 2,
            "has_header": True,
            "empty_rows_skipped": 0,
        },
        "vector_spec": {"model": "nomic-embed-text", "dimension": 768},
    }
    assert fake_service.calls[0]["file"].filename == "retail.csv"
    assert fake_service.calls[0]["price_atomic"] == 250
    assert fake_service.calls[0]["settlement_currency"] == "USDC"
    assert fake_service.calls[0]["seller_wallet_type"] == "evm"


def test_embed_dataset_maps_api_error_to_error_response():
    fake_service = FakeDatasetEmbedService(
        error=ApiError(
            status_code=413,
            error="too_many_rows",
            message="CSV has too many rows.",
            details={"max_dataset_rows": 1},
        )
    )
    app.dependency_overrides[get_dataset_embed_service] = lambda: fake_service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/datasets/embed",
            data={
                "title": "Retail Data",
                "description": "Point of sale records",
                "seller": "0x0000000000000000000000000000000000000001",
                "price_atomic": "250",
            },
            files={"file": ("retail.csv", b"age,cp\n63,3\n", "text/csv")},
        )

    assert response.status_code == 413
    assert response.json() == {
        "error": "too_many_rows",
        "message": "CSV has too many rows.",
        "details": {"max_dataset_rows": 1},
    }


def test_get_dataset_preview_returns_persisted_preview(monkeypatch):
    class FakeRecord:
        preview = {"column_names": ["age", "cp"], "rows": [["63", "3"]]}

    monkeypatch.setattr(
        datasets_router.dataset_key_repo,
        "get_dataset_preview",
        lambda session, listing_id: FakeRecord(),
        raising=False,
    )
    app.dependency_overrides[get_session] = lambda: object()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/datasets/123e4567-e89b-12d3-a456-426614174000/preview"
        )

    assert response.status_code == 200
    assert response.json() == {
        "column_names": ["age", "cp"],
        "rows": [["63", "3"]],
    }


def test_get_dataset_preview_falls_back_to_vector_documents(monkeypatch):
    monkeypatch.setattr(
        datasets_router.dataset_key_repo,
        "get_dataset_preview",
        lambda session, listing_id: None,
    )
    monkeypatch.setattr(
        datasets_router.dataset_key_repo,
        "get_vector_document_preview",
        lambda session, listing_id: {
            "column_names": ["age", "cp"],
            "rows": [["63", "3"], ["37", "2"]],
        },
        raising=False,
    )
    app.dependency_overrides[get_session] = lambda: object()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/datasets/123e4567-e89b-12d3-a456-426614174000/preview"
        )

    assert response.status_code == 200
    assert response.json() == {
        "column_names": ["age", "cp"],
        "rows": [["63", "3"], ["37", "2"]],
    }


def test_get_dataset_preview_returns_preview_unavailable(monkeypatch):
    monkeypatch.setattr(
        datasets_router.dataset_key_repo,
        "get_dataset_preview",
        lambda session, listing_id: None,
        raising=False,
    )
    monkeypatch.setattr(
        datasets_router.dataset_key_repo,
        "get_vector_document_preview",
        lambda session, listing_id: None,
        raising=False,
    )
    app.dependency_overrides[get_session] = lambda: object()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/datasets/123e4567-e89b-12d3-a456-426614174000/preview"
        )

    assert response.status_code == 404
    assert response.json() == {
        "error": "preview_unavailable",
        "message": "Dataset preview is not available for this listing.",
        "details": {"listing_id": "123e4567-e89b-12d3-a456-426614174000"},
    }
