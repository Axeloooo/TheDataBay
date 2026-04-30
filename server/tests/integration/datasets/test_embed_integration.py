"""Integration test for DatasetEmbedService against a real pgvector DB."""

import json
from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import Settings
from app.datasets.service import DatasetEmbedService

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

SAMPLE_CSV_PATH = Path(__file__).parents[1] / "services" / "sample.csv"
DIM = 768


def _make_settings() -> Settings:
    return Settings(
        _env_file=None,
        **{
            "APP_NAME": "Ulenor API",
            "APP_VERSION": "0.1.0",
            "ENVIRONMENT": "test",
            "HOST": "localhost",
            "PORT": 8080,
            "CORS_ORIGINS": ["http://localhost:5173"],
            "OLLAMA_HOST": "http://localhost:11434",
            "EMBEDDING_MODEL": "nomic-embed-text",
            "EMBEDDING_DIMENSION": DIM,
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
            "CADC_TOKEN_ADDRESS": "0x0000000000000000000000000000000000000003",
            "CONTRACT_ABI_PATH": "/tmp/Marketplace.json",
            "CHAIN_ID": 31337,
            "RPC_URL": "http://127.0.0.1:8545",
            "SERVER_PRIVATE_KEY": "0x" + "11" * 32,
            "POSTGRES_URL": "postgresql://user:password@localhost:5432/ulenor",
        },
    )


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


async def _delete_rows(factory, listing_id: str) -> None:
    async with factory() as session:
        async with session.begin():
            await session.execute(
                text("""
                    DELETE FROM langchain_pg_embedding e
                    USING langchain_pg_collection c
                    WHERE e.collection_id = c.uuid
                      AND c.name = 'dataset_rows'
                      AND e.cmetadata->>'listing_id' = :lid
                    """),
                {"lid": listing_id},
            )
            await session.execute(
                text("DELETE FROM dataset_keys WHERE listing_id = :lid"),
                {"lid": listing_id},
            )
            await session.execute(
                text("DELETE FROM dataset_previews WHERE listing_id = :lid"),
                {"lid": listing_id},
            )


async def test_embed_persists_rows_and_dataset_key(
    pg_container,
    run_alembic,
    committing_factory,
    settings,
) -> None:
    csv_file = SAMPLE_CSV_PATH.open("rb")

    class FakeVectorstore:
        async def acreate_collection(self):
            async with committing_factory() as session:
                async with session.begin():
                    await session.execute(text("""
                            INSERT INTO langchain_pg_collection (uuid, name, cmetadata)
                            VALUES ('00000000-0000-0000-0000-000000000001', 'dataset_rows', '{}')
                            ON CONFLICT (name) DO NOTHING
                            """))

        async def aadd_documents(self, documents, ids):
            async with committing_factory() as session:
                async with session.begin():
                    for doc, doc_id in zip(documents, ids):
                        await session.execute(
                            text("""
                                INSERT INTO langchain_pg_embedding
                                    (id, collection_id, embedding, document, cmetadata)
                                VALUES
                                    (:id, '00000000-0000-0000-0000-000000000001',
                                     CAST(:embedding AS vector(768)), :document,
                                     CAST(:metadata AS jsonb))
                                """),
                            {
                                "id": doc_id,
                                "embedding": str([0.1] * DIM),
                                "document": doc.page_content,
                                "metadata": json.dumps(doc.metadata),
                            },
                        )

    async def fake_upload(payload, filename, settings):
        return "ipfs://QmFakeData", "0xfakedata"

    service = DatasetEmbedService(
        settings,
        vectorstore_factory=lambda settings: FakeVectorstore(),
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

        async with committing_factory() as verify_session:
            emb_result = await verify_session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON c.uuid = e.collection_id
                    WHERE c.name = 'dataset_rows'
                      AND e.cmetadata->>'listing_id' = :lid
                    """),
                {"lid": response.listing_id},
            )
            assert emb_result.scalar_one() == 8

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
            assert preview_row.vector_spec["dimension"] == DIM
    finally:
        csv_file.close()
        if response is not None:
            await _delete_rows(committing_factory, response.listing_id)
