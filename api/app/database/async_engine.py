"""
Async database engine and session factory for pgvector / asyncpg.

The synchronous engine in engine.py is left untouched; this module provides
a parallel async stack for the semantic-search layer.
"""

from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..config.settings import Settings, get_settings


@lru_cache(maxsize=1)
def get_async_engine() -> AsyncEngine:
    """Return a lazily-created, cached async SQLAlchemy engine.

    Returns:
        AsyncEngine: The async database engine.
    """
    settings: Settings = get_settings()
    return create_async_engine(
        url=settings.async_database_url,
        echo=settings.environment == "development",
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return a cached async session factory.

    Returns:
        async_sessionmaker[AsyncSession]: Session factory bound to the async engine.
    """
    engine = get_async_engine()
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    The caller (router / service) is responsible for committing; this
    generator only closes the session on exit.

    Yields:
        AsyncSession: An open async database session.
    """
    factory = get_async_session_factory()
    async with factory() as session:
        yield session
