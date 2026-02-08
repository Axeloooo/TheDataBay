"""
SQLModel for dataset encryption keys.
"""

from datetime import datetime, timezone
import uuid

from sqlmodel import SQLModel, Field


class DatasetKey(SQLModel, table=True):
    """Per-listing AES key storage."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    listing_id: str = Field(index=True, unique=True)
    key_b64: str
    nonce_b64: str
    dataset_url: str
    dataset_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
