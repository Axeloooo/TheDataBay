"""SQLModel for durable dataset preview metadata."""

from datetime import datetime
from typing import Any, Optional
import uuid

from sqlalchemy import Column, JSON, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field, SQLModel


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
