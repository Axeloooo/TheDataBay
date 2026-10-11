"""Schema-level tests for the event indexer tables."""

from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.database import engine as engine_module
from app.indexer.models import IndexedListing, IndexedPurchase, IndexerState

UINT256_MAX = 2**256 - 1


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    try:
        yield eng
    finally:
        eng.dispose()


def _purchase(**overrides) -> IndexedPurchase:
    data = {
        "tx_hash": "0x" + "ab" * 32,
        "log_index": 3,
        "listing_id": "0x" + "01" * 32,
        "buyer": "0x0000000000000000000000000000000000000001",
        "payment_token": "0x0000000000000000000000000000000000000002",
        "price_paid": Decimal(1_010_000),
        "fee_paid": Decimal(10_000),
        "seller_paid": Decimal(1_000_000),
        "block_number": 120,
        "block_time": datetime(2026, 10, 11, tzinfo=timezone.utc),
    }
    data.update(overrides)
    return IndexedPurchase(**data)


def test_same_tx_hash_and_log_index_cannot_be_inserted_twice(engine):
    with Session(engine) as session:
        session.add(_purchase())
        session.commit()

    with Session(engine) as session:
        session.add(_purchase(buyer="0x0000000000000000000000000000000000000009"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_same_tx_hash_with_different_log_index_is_a_separate_purchase(engine):
    with Session(engine) as session:
        session.add(_purchase(log_index=3))
        session.add(_purchase(log_index=4))
        session.commit()

    with Session(engine) as session:
        assert session.get(IndexedPurchase, ("0x" + "ab" * 32, 4)) is not None


def test_listing_id_is_unique(engine):
    def listing() -> IndexedListing:
        return IndexedListing(
            listing_id="0x" + "01" * 32,
            title="t",
            description="d",
            seller="0x0000000000000000000000000000000000000001",
            payment_token="0x0000000000000000000000000000000000000002",
            payment_token_decimals=6,
            price=Decimal(5),
            dataset_url="ipfs://x",
            dataset_hash="0x" + "00" * 32,
            signature_url="",
            signature_hash="0x" + "00" * 32,
            created_block=10,
            last_event_block=10,
            last_event_log_index=0,
        )

    with Session(engine) as session:
        session.add(listing())
        session.commit()
    with Session(engine) as session:
        session.add(listing())
        with pytest.raises(IntegrityError):
            session.commit()


def test_uint256_amounts_round_trip_without_overflow(engine):
    with Session(engine) as session:
        session.add(_purchase(price_paid=Decimal(UINT256_MAX)))
        session.commit()

    with Session(engine) as session:
        row = session.get(IndexedPurchase, ("0x" + "ab" * 32, 3))
        assert int(row.price_paid) == UINT256_MAX


def test_indexer_state_is_keyed_by_name(engine):
    with Session(engine) as session:
        session.add(IndexerState(name="marketplace", last_indexed_block=41))
        session.commit()

    with Session(engine) as session:
        state = session.get(IndexerState, "marketplace")
        assert state.last_indexed_block == 41
        assert state.chain_head_block is None


def test_indexer_models_are_created_on_startup():
    assert "app.indexer.models" in engine_module.MODEL_MODULES


def test_indexer_settings_have_safe_defaults():
    from app.config.settings import Settings

    fields = Settings.model_fields
    assert fields["indexer_enabled"].default is False
    assert fields["indexer_start_block"].default == 0
    assert fields["indexer_block_chunk"].default == 2000
    assert fields["indexer_confirmations"].default == 2
    assert fields["indexer_poll_seconds"].default == 5
