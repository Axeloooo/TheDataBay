"""SQLModel tables for dataset key and preview persistence."""

from datetime import datetime
from typing import Any, Optional
import uuid

from sqlalchemy import Column, JSON, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field, SQLModel


class DatasetKey(SQLModel, table=True):
    """Per-listing AES key storage."""

    __tablename__ = "dataset_keys"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    listing_id: str = Field(index=True, unique=True)
    key_b64: str
    nonce_b64: str
    dataset_url: str
    dataset_hash: str
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


class DatasetPreview(SQLModel, table=True):
    """Per-listing preview and upload metadata for public dataset rendering."""

    __tablename__ = "dataset_previews"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    listing_id: str = Field(index=True, unique=True)
    preview: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    stats: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    vector_spec: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
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
