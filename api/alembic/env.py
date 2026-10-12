"""
Alembic environment configuration — async online migrations + offline mode.

* target_metadata is SQLModel.metadata so autogenerate sees all table models.
* sqlalchemy.url is resolved in priority order: explicit override on the
  Alembic config object (e.g. set by the integration-test conftest or CI),
  then settings.async_database_url from the POSTGRES_URL env var.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# Import all feature-local models so their tables are registered on
# SQLModel.metadata before autogenerate inspects it.
import app.agents.models  # noqa: F401
import app.datasets.models  # noqa: F401

from app.config.settings import get_settings

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to alembic.ini values.
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging from the alembic.ini [loggers] section if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that autogenerate should reflect against.
target_metadata = SQLModel.metadata


def _resolve_url() -> str:
    """Return the async-compatible DB URL for migrations.

    Priority:
    1. ``sqlalchemy.url`` explicitly set on the Alembic config object
       (e.g. overridden by the integration-test conftest or CI).
       Any sync driver prefix is normalised to asyncpg automatically.
    2. ``settings.async_database_url`` — read from the POSTGRES_URL env var.
    """
    config_url = config.get_main_option("sqlalchemy.url")
    if config_url:
        return (
            config_url
            .replace("postgresql+psycopg2://", "postgresql+asyncpg://")
            .replace("postgresql://", "postgresql+asyncpg://")
            .replace("postgres://", "postgresql+asyncpg://")
        )
    return get_settings().async_database_url


# ---------------------------------------------------------------------------
# Offline mode — emit SQL to stdout without a live DB connection.
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL, not an Engine, so that
    Alembic can produce SQL without a live database connection.
    """
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — connect asynchronously and apply migrations.
# ---------------------------------------------------------------------------
async def run_migrations_online() -> None:
    """Run migrations against a live database using an async engine."""
    connectable = create_async_engine(_resolve_url(), echo=False)

    async with connectable.connect() as connection:
        await connection.run_sync(_run_sync_migrations)

    await connectable.dispose()


def _run_sync_migrations(sync_connection: object) -> None:
    """Configure and run migrations inside a synchronous connection context."""
    context.configure(
        connection=sync_connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point — called by the Alembic CLI.
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
