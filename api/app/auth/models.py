"""SQLModel tables for wallet sign-in."""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel


class AuthNonce(SQLModel, table=True):
    """One-time sign-in challenge issued to a wallet.

    A nonce is single use (``used_at`` is set on the first verify attempt,
    successful or not) and expires at ``expires_at``.
    """

    __tablename__ = "auth_nonces"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wallet_type: str = Field(index=True)
    address: str = Field(index=True)
    nonce: str = Field(index=True, unique=True)
    message: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    used_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
