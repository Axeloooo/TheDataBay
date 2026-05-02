"""
Database configuration and session management.
"""

import importlib
from functools import lru_cache
from typing import Any, Generator
from sqlalchemy import Engine, create_engine
from sqlmodel import Session
from ..config.settings import Settings, get_settings
from sqlmodel import SQLModel

MODEL_MODULES = (
    "app.agents.models",
    "app.datasets.models",
)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Get the database engine.

    Returns:
        Engine: The database engine.
    """
    settings: Settings = get_settings()
    return create_engine(
        url=settings.database_url.get_secret_value(),
        echo=settings.environment == "development",
    )


def create_db_and_tables() -> None:
    """Create the database and tables."""

    for module in MODEL_MODULES:
        importlib.import_module(module)
    engine: Engine = get_engine()
    SQLModel.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, Any, None]:
    """Get a database session.

    Returns:
        Generator[Session, Any, None]: Database session
    """
    engine: Engine = get_engine()
    with Session(bind=engine) as session:
        yield session
