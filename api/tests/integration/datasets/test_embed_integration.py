"""Integration test for DatasetEmbedService key persistence with mocked RAG I/O."""

from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import Settings
from app.datasets.service import DatasetEmbedService
from app.llm.schemas import ColumnExpansionResult

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

SAMPLE_CSV_PATH = Path(__file__).parents[1] / "services" / "sample.csv"


def _make_settings() -> Settings:
    return Settings(
        _env_file=None,
        **{
            "APP_NAME": "TheDataBay API",
            "APP_VERSION": "0.1.0",
            "ENVIRONMENT": "test",
            "HOST": "localhost",
            "PORT": 8080,
            "CORS_ORIGINS": ["http://localhost:5173"],
            "LLM_BASE_URL": "http://localhost:11434",
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
            "USDC_TOKEN_ADDRESS": "0x0000000000000000000000000000000000000002",
            "CADC_TOKEN_ADDRESS": "0x0000000000000000000000000000000000000003",
            "CONTRACT_ABI_PATH": "/tmp/Marketplace.json",
            "CHAIN_ID": 31337,
            "RPC_URL": "http://127.0.0.1:8545",
            "SERVER_PRIVATE_KEY": "0x" + "11" * 32,
            "POSTGRES_URL": "postgresql://user:password@localhost:5432/thedatabay",
        },
    )


class FakeLLMService:
    embeddings_client = object()

    def __init__(self) -> None:
        self.expand_calls: list[tuple[list[str], list[list[str]]]] = []

    async def expand_column_names(
        self, column_names: list[str], sample_rows: list[list[str]]
    ) -> ColumnExpansionResult:
        self.expand_calls.append((column_names, sample_rows))
        return ColumnExpansionResult(
            columns={col: f"{col} (expanded)" for col in column_names}
        )

    async def embed_text(self, text: str):
        raise AssertionError("DatasetEmbedService must not embed directly")

    async def embed_texts(self, texts: list[str]):
        raise AssertionError("DatasetEmbedService must not embed rows directly")


class FakeVectorRepository:
    def __init__(self) -> None:
        self.created = False
        self.docs = []
        self.ids: list[str] = []
        self.deleted_listing_id: str | None = None
        self.deleted_ids: list[str] = []

    async def create_collection(self):
        self.created = True

    async def add_documents(self, docs, ids):
        self.docs = list(docs)
        self.ids = list(ids)

    async def delete_stale_documents(self, listing_id: str, ids: list[str]):
        self.deleted_listing_id = listing_id
        self.deleted_ids = list(ids)


@pytest.fixture(scope="module")
def settings() -> Settings:
    return _make_settings()


@pytest.fixture(scope="module")
def committing_factory(pg_container):
    sync_url: str = pg_container.get_connection_url()
    async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    yield factory

    import asyncio

    asyncio.run(engine.dispose())


async def _delete_dataset_records(factory, listing_id: str) -> None:
    async with factory() as session:
        async with session.begin():
            await session.execute(
                text("DELETE FROM dataset_keys WHERE listing_id = :lid"),
                {"lid": listing_id},
            )
            await session.execute(
                text("DELETE FROM dataset_previews WHERE listing_id = :lid"),
                {"lid": listing_id},
            )


async def test_embed_persists_row_documents_and_dataset_key(
    pg_container,
    run_alembic,
    committing_factory,
    settings,
) -> None:
    csv_file = SAMPLE_CSV_PATH.open("rb")
    llm_service = FakeLLMService()
    vector_repository = FakeVectorRepository()

    async def fake_upload(payload, filename, settings):
        return "ipfs://QmFakeData", "0xfakedata"

    service = DatasetEmbedService(
        settings,
        llm_service=llm_service,
        vector_repository=vector_repository,
        session_factory=committing_factory,
        key_generator=lambda: b"\xab" * 32,
        encryptor=lambda content, key, aad: (b"ciphertext", b"\x00" * 12),
        uploader=fake_upload,
    )

    response = None
    try:
        response = await service.embed(
            file=UploadFile(filename="sample.csv", file=csv_file),
            title="Integration Test Dataset",
            description="Test dataset for integration testing",
            seller="0x0000000000000000000000000000000000000001",
            price_atomic=100,
            settlement_currency="USDC",
            settlement_decimals=6,
        )

        assert response.dataset_url == "ipfs://QmFakeData"
        assert response.dataset_hash == "0xfakedata"
        assert response.stats.total_rows == 5
        assert vector_repository.created is True
        assert len(vector_repository.docs) == 5
        assert len(llm_service.expand_calls) == 1
        assert vector_repository.deleted_listing_id == response.listing_id
        assert vector_repository.deleted_ids == vector_repository.ids
        assert vector_repository.docs[0].metadata == {
            "listing_id": response.listing_id,
            "row_index": 0,
        }
        assert "(expanded)" in vector_repository.docs[0].page_content

        async with committing_factory() as verify_session:
            key_result = await verify_session.execute(
                text(
                    "SELECT key_b64, nonce_b64, dataset_url, dataset_hash "
                    "FROM dataset_keys WHERE listing_id = :lid"
                ),
                {"lid": response.listing_id},
            )
            row = key_result.one()
            assert row.key_b64
            assert row.nonce_b64
            assert row.dataset_url == "ipfs://QmFakeData"
            assert row.dataset_hash == "0xfakedata"

            preview_result = await verify_session.execute(
                text(
                    "SELECT preview, stats, vector_spec "
                    "FROM dataset_previews WHERE listing_id = :lid"
                ),
                {"lid": response.listing_id},
            )
            preview_row = preview_result.one()
            assert preview_row.preview["column_names"]
            assert len(preview_row.preview["rows"]) == 5
            assert preview_row.stats["total_rows"] == 5
            assert (
                preview_row.vector_spec["dimension"] == settings.llm_embedding_dimension
            )
    finally:
        csv_file.close()
        if response is not None:
            await _delete_dataset_records(committing_factory, response.listing_id)
