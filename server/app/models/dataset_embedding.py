"""
SQLModel for dataset embedding vectors (pgvector).
"""

from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import SQLModel, Field


class DatasetEmbedding(SQLModel, table=True):
    """Persisted embedding vector for a marketplace dataset listing."""

    __tablename__ = "dataset_embeddings"

    listing_id: str = Field(primary_key=True)
    embedding: list[float] = Field(sa_column=Column(Vector(768), nullable=False))
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
