"""
Integration test fixtures using testcontainers with the pgvector/pgvector:pg16
Docker image.  All fixtures are session-scoped except `db_session` which is
function-scoped and rolls back after each test.

NullPool is used on the async engine so that asyncpg connections are never
cached across event-loop boundaries.  Each db_session call gets a fresh
connection that lives entirely within that test's loop context.

Imports of testcontainers are deferred inside fixture bodies so that pytest
collection succeeds even when Docker is unavailable (integration tests are
excluded by default via pytest.ini: -m "not integration").
"""

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

PGVECTOR_IMAGE = "pgvector/pgvector:pg16"

# ---------------------------------------------------------------------------
# Container (session-scoped — started once per test session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def pg_container():
    """Start a pgvector-enabled PostgreSQL container for the test session."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(PGVECTOR_IMAGE) as container:
        yield container


# ---------------------------------------------------------------------------
# Alembic migration (session-scoped — runs once after container is ready)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def run_alembic(pg_container):
    """Run Alembic migrations against the test container (sync connection).

    Alembic's command.upgrade() is synchronous, so we use the psycopg2 URL
    from the container and override sqlalchemy.url at runtime.
    """
    from alembic import command
    from alembic.config import Config

    sync_url: str = pg_container.get_connection_url()

    server_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    alembic_cfg = Config(os.path.join(server_root, "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    alembic_cfg.set_main_option(
        "script_location", os.path.join(server_root, "alembic")
    )

    command.upgrade(alembic_cfg, "head")


# ---------------------------------------------------------------------------
# Per-test async session (rolls back after each test for isolation)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def db_session(pg_container, run_alembic) -> AsyncSession:
    """Yield a fresh AsyncSession for each test.

    NullPool ensures each session opens its own asyncpg connection.  Tests
    must NOT call db_session.commit() — writes are flushed within the open
    transaction and the PostgreSQL server rolls back automatically when the
    connection is discarded by NullPool on teardown.  Cleanup errors are
    suppressed: the session-scoped container resets all state at the end of
    the test session regardless.
    """
    sync_url: str = pg_container.get_connection_url()
    async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

    engine = create_async_engine(async_url, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    session = factory()
    try:
        yield session
    finally:
        for coro in (session.rollback, session.close, engine.dispose):
            try:
                await coro()
            except Exception:
                pass
