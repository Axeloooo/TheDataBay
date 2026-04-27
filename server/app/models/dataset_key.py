"""
SQLModel for dataset encryption keys.
"""

from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import SQLModel, Field


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
