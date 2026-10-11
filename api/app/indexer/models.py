"""SQLModel tables written by the marketplace event indexer.

Amounts are uint256 on-chain, so they are stored as NUMERIC(78, 0) (78 digits
holds 2**256 - 1). Block numbers are BIGINT. Addresses and hashes are TEXT:
addresses in EIP-55 checksum form, hashes as lowercase 0x-prefixed hex.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Column, Index, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel


class Uint256(TypeDecorator):
    """NUMERIC(78, 0) on Postgres. SQLite (unit tests) has no exact wide
    numeric type, so values are stored there as decimal text instead."""

    impl = Numeric(78, 0)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(Text())
        return dialect.type_descriptor(Numeric(78, 0))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            return str(int(value))
        return Decimal(int(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Decimal(value)


def _uint256_column() -> Column:
    return Column(Uint256(), nullable=False)


def _updated_at_column() -> Column:
    return Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )


class IndexedListing(SQLModel, table=True):
    """Current state of one marketplace listing, built from contract events."""

    __tablename__ = "listings"

    listing_id: str = Field(sa_column=Column(Text, primary_key=True))
    title: str = Field(sa_column=Column(Text, nullable=False))
    description: str = Field(sa_column=Column(Text, nullable=False))
    seller: str = Field(sa_column=Column(Text, nullable=False, index=True))
    payment_token: str = Field(sa_column=Column(Text, nullable=False))
    payment_token_decimals: int = Field(sa_column=Column(Integer, nullable=False))
    price: Decimal = Field(sa_column=_uint256_column())
    dataset_url: str = Field(sa_column=Column(Text, nullable=False))
    dataset_hash: str = Field(sa_column=Column(Text, nullable=False))
    signature_url: str = Field(sa_column=Column(Text, nullable=False))
    signature_hash: str = Field(sa_column=Column(Text, nullable=False))
    created_block: int = Field(sa_column=Column(BigInteger, nullable=False))
    frozen: bool = Field(default=False, nullable=False)
    # Position of the last event applied to this row. Updates from events at
    # or before this position are ignored, so replays never roll state back.
    last_event_block: int = Field(sa_column=Column(BigInteger, nullable=False))
    last_event_log_index: int = Field(sa_column=Column(Integer, nullable=False))
    updated_at: Optional[datetime] = Field(default=None, sa_column=_updated_at_column())


class IndexedPurchase(SQLModel, table=True):
    """One ItemPurchased event. The natural key (tx_hash, log_index) makes
    inserts idempotent: replaying a block range cannot create duplicates."""

    __tablename__ = "purchases"
    __table_args__ = (
        Index("ix_purchases_buyer_block", "buyer", "block_number"),
        Index("ix_purchases_listing_id", "listing_id"),
    )

    tx_hash: str = Field(sa_column=Column(Text, primary_key=True))
    log_index: int = Field(sa_column=Column(Integer, primary_key=True))
    listing_id: str = Field(sa_column=Column(Text, nullable=False))
    buyer: str = Field(sa_column=Column(Text, nullable=False))
    payment_token: str = Field(sa_column=Column(Text, nullable=False))
    price_paid: Decimal = Field(sa_column=_uint256_column())
    fee_paid: Decimal = Field(sa_column=_uint256_column())
    seller_paid: Decimal = Field(sa_column=_uint256_column())
    block_number: int = Field(sa_column=Column(BigInteger, nullable=False))
    block_time: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )


class IndexerState(SQLModel, table=True):
    """Cursor for one indexer. last_indexed_block is the highest block whose
    events are fully written; chain_head_block is the chain head seen on the
    run that wrote it (used to report lag without an RPC call)."""

    __tablename__ = "indexer_state"

    name: str = Field(sa_column=Column(Text, primary_key=True))
    last_indexed_block: int = Field(sa_column=Column(BigInteger, nullable=False))
    chain_head_block: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=_updated_at_column())
