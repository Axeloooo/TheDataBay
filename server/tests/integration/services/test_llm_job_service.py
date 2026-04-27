"""
Integration tests for _process_embedding_job against a real pgvector DB.

Requires Docker (testcontainers pulls pgvector/pgvector:pg16).
Run with:  pytest -m integration tests/integration/services/test_llm_job_service.py

Isolation strategy
------------------
The job creates its own internal async session via get_async_session_factory().
We monkeypatch that factory to point at the test container DB.  The factory
DOES commit (unlike the conftest db_session which rolls back) so we can query
rows after the job completes.  A separate verify session is opened just to
read back the rows, and all writes are cleaned up in the test fixture teardown
via explicit DELETE statements.
"""

import base64
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.schemas.job_schema import JobStatus
from app.services import llm_job_service
from app.services.job_manager import JobManager
from app.config.settings import Settings

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CSV_PATH = Path(__file__).parent / "sample.csv"
DIM = 768

def _make_settings() -> Settings:
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
        "POSTGRES_URL": "postgresql://user:password@localhost:5432/bridgemart",
    }
    return Settings(_env_file=None, **data)


@pytest.fixture(scope="module")
def settings() -> Settings:
    return _make_settings()


@pytest.fixture(scope="module")
def job_manager() -> JobManager:
    return JobManager()


@pytest.fixture(scope="module")
def committing_factory(pg_container):
    """Return an async_sessionmaker that COMMITs against the test container.

    Unlike the conftest db_session (which rolls back for isolation), this
    factory lets the job's own session.begin() complete normally so that
    rows are visible afterwards for assertion.
    """
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
    # Dispose the engine using a fresh event loop to avoid "no current event loop" error
    import asyncio

    async def _dispose():
        await engine.dispose()

    asyncio.run(_dispose())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _delete_rows(factory, listing_id: str) -> None:
    """Remove test rows written by the job for cleanup."""
    async with factory() as session:
        async with session.begin():
            await session.execute(
                text(
                    """
                    DELETE FROM langchain_pg_embedding e
                    USING langchain_pg_collection c
                    WHERE e.collection_id = c.uuid
                      AND c.name = 'dataset_rows'
                      AND e.cmetadata->>'listing_id' = :lid
                    """
                ),
                {"lid": listing_id},
            )
            await session.execute(
                text("DELETE FROM dataset_keys WHERE listing_id = :lid"),
                {"lid": listing_id},
            )


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


async def test_process_embedding_job_persists_rows(
    monkeypatch,
    pg_container,
    run_alembic,
    committing_factory,
    settings,
    job_manager,
) -> None:
    """_process_embedding_job should persist row documents and a DatasetKey row."""

    listing_id = "integ-llm-job-001"
    job_id = job_manager.create_job(
        filename="sample.csv",
        metadata={"listing_id": listing_id},
    )

    csv_bytes = SAMPLE_CSV_PATH.read_bytes()

    # -- Monkeypatches -------------------------------------------------------

    def fake_generate_key():
        return b"\xab" * 32

    def fake_encrypt_bytes(content_bytes, key, aad):
        return b"ciphertext", b"\x00" * 12

    async def fake_upload_bytes(payload, filename, settings):
        return "ipfs://QmFakeData", "0xfakedata"

    class FakeVectorstore:
        async def aadd_documents(self, documents, ids):
            async with committing_factory() as session:
                collection_id = "00000000-0000-0000-0000-000000000001"
                async with session.begin():
                    await session.execute(
                        text(
                            """
                            INSERT INTO langchain_pg_collection (uuid, name, cmetadata)
                            VALUES (:uuid, 'dataset_rows', '{}')
                            ON CONFLICT (name) DO NOTHING
                            """
                        ),
                        {"uuid": collection_id},
                    )
                    for doc, doc_id in zip(documents, ids):
                        await session.execute(
                            text(
                                """
                                INSERT INTO langchain_pg_embedding
                                    (id, collection_id, embedding, document, cmetadata)
                                VALUES
                                    (:id, :collection_id, CAST(:embedding AS vector(768)),
                                     :document, CAST(:metadata AS jsonb))
                                """
                            ),
                            {
                                "id": doc_id,
                                "collection_id": collection_id,
                                "embedding": str([0.1] * DIM),
                                "document": doc.page_content,
                                "metadata": (
                                    '{"listing_id": "%s", "row_index": %s}'
                                    % (
                                        doc.metadata["listing_id"],
                                        doc.metadata["row_index"],
                                    )
                                ),
                            },
                        )

    monkeypatch.setattr(llm_job_service, "generate_key", fake_generate_key)
    monkeypatch.setattr(llm_job_service, "encrypt_bytes", fake_encrypt_bytes)
    monkeypatch.setattr(llm_job_service, "upload_bytes", fake_upload_bytes)
    monkeypatch.setattr(
        llm_job_service, "vectorstore_for_settings", lambda settings: FakeVectorstore()
    )

    # Point the job's internal session factory at the test container DB
    monkeypatch.setattr(
        llm_job_service, "get_async_session_factory", lambda: committing_factory
    )

    # -- Run the job ---------------------------------------------------------

    try:
        await llm_job_service._process_embedding_job(
            job_id=job_id,
            content_bytes=csv_bytes,
            filename="sample.csv",
            settings=settings,
            job_manager=job_manager,
            listing_id=listing_id,
            title="Integration Test Dataset",
            description="Test dataset for integration testing",
            seller="0x0000000000000000000000000000000000000001",
            price=100,
        )

        # -- Assertions ------------------------------------------------------

        job = job_manager.get_job(job_id)
        assert job.status == JobStatus.COMPLETED, f"Job ended with status {job.status}, error: {job.error}"

        async with committing_factory() as verify_session:
            emb_result = await verify_session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON c.uuid = e.collection_id
                    WHERE c.name = 'dataset_rows'
                      AND e.cmetadata->>'listing_id' = :lid
                    """
                ),
                {"lid": listing_id},
            )
            assert emb_result.scalar_one() == 5

            # Verify DatasetKey row
            key_result = await verify_session.execute(
                text(
                    "SELECT listing_id, key_b64, nonce_b64, dataset_url, dataset_hash "
                    "FROM dataset_keys WHERE listing_id = :lid"
                ),
                {"lid": listing_id},
            )
            key_row = key_result.fetchone()
            assert key_row is not None, "Expected DatasetKey row to exist"
            assert key_row[0] == listing_id
            assert key_row[1] == base64.b64encode(b"\xab" * 32).decode("utf-8")
            assert key_row[3] == "ipfs://QmFakeData"
            assert key_row[4] == "0xfakedata"

    finally:
        # Cleanup: remove test rows so subsequent runs are not affected
        await _delete_rows(committing_factory, listing_id)
