"""Log handling and cursor tests for the marketplace indexer."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlmodel import Session, select

from app.indexer.models import IndexedListing, IndexedPurchase, IndexerState
from app.indexer.service import STATE_NAME, index_range, run_once

from .conftest import make_settings
from .fakes import (
    BLOCK_TIME_BASE,
    BUYER,
    BUYER_2,
    OTHER_CONTRACT,
    SELLER,
    USDC,
    FakeChain,
    contract_for,
    item_id,
)

ID1 = "0x" + item_id(1).hex()
ID2 = "0x" + item_id(2).hex()


def _purchases(session: Session) -> list[IndexedPurchase]:
    return list(session.exec(select(IndexedPurchase)).all())


def _listing(session: Session, listing_id: str) -> IndexedListing | None:
    session.expire_all()
    return session.get(IndexedListing, listing_id)


def _state(session: Session) -> IndexerState | None:
    session.expire_all()
    return session.get(IndexerState, STATE_NAME)


@pytest.fixture
def chain() -> FakeChain:
    c = FakeChain(head=200)
    iid1 = c.add_listing(1, block=101, price=1_000_000)
    c.add_listing(2, block=102, price=2_000_000)
    c.add_event("PriceUpdated", 103, 0, itemId=iid1, oldPrice=1_000_000, newPrice=1_500_000)
    c.add_event("PriceUpdated", 104, 0, itemId=iid1, oldPrice=1_500_000, newPrice=1_250_000)
    c.add_purchase(iid1, block=105, log_index=1, buyer=BUYER)
    c.add_purchase(iid1, block=106, log_index=0, buyer=BUYER_2)
    return c


# ---- index_range -------------------------------------------------------------


def test_index_range_writes_listings_purchases_and_applies_price_updates(session, chain):
    written = index_range(session, contract_for(chain), 100, 110)
    session.commit()

    assert written == 6
    l1 = _listing(session, ID1)
    assert l1.title == "Dataset 1"
    assert l1.description == "Description 1"
    assert l1.seller == SELLER
    assert l1.payment_token == USDC
    assert l1.payment_token_decimals == 6
    assert l1.price == Decimal(1_250_000)
    assert l1.dataset_url == "ipfs://dataset-1"
    assert l1.dataset_hash == "0x" + "11" * 32
    assert l1.created_block == 101
    assert l1.frozen is True
    l2 = _listing(session, ID2)
    assert l2.price == Decimal(2_000_000)
    assert l2.frozen is False

    rows = sorted(_purchases(session), key=lambda p: p.block_number)
    assert [(p.buyer, p.block_number) for p in rows] == [(BUYER, 105), (BUYER_2, 106)]
    first = rows[0]
    assert first.listing_id == ID1
    assert first.log_index == 1
    assert first.payment_token == USDC
    assert (first.price_paid, first.fee_paid, first.seller_paid) == (
        Decimal(1_010_000),
        Decimal(10_000),
        Decimal(1_000_000),
    )
    assert first.block_time.replace(tzinfo=timezone.utc) == datetime.fromtimestamp(
        BLOCK_TIME_BASE + 105, tz=timezone.utc
    )


def test_replaying_the_same_range_creates_no_duplicates(session, chain):
    contract = contract_for(chain)
    index_range(session, contract, 100, 110)
    session.commit()

    written_again = index_range(session, contract, 100, 110)
    session.commit()

    assert written_again == 0
    assert len(_purchases(session)) == 2
    assert len(session.exec(select(IndexedListing)).all()) == 2
    assert _listing(session, ID1).price == Decimal(1_250_000)


def test_replaying_an_older_price_update_does_not_roll_price_back(session, chain):
    contract = contract_for(chain)
    index_range(session, contract, 100, 110)
    session.commit()

    index_range(session, contract, 103, 103)
    session.commit()

    assert _listing(session, ID1).price == Decimal(1_250_000)


def test_logs_from_other_contracts_are_ignored(session, chain):
    chain.ignore_address_filter = True
    chain.add_purchase(item_id(1), block=107, log_index=0)
    chain.logs[-1]["address"] = OTHER_CONTRACT.lower()

    index_range(session, contract_for(chain), 100, 110)
    session.commit()

    assert len(_purchases(session)) == 2
    requested = chain.get_logs_calls[0]["address"]
    requested = [requested] if isinstance(requested, str) else requested
    assert [a.lower() for a in requested] == [contract_for(chain).address.lower()]


def test_dataset_url_updates_are_applied(session, chain):
    chain.add_event(
        "DatasetUrlUpdated", 107, 0, itemId=item_id(2), oldUrl="ipfs://dataset-2", newUrl="ipfs://v2"
    )
    chain.add_event(
        "SignatureUpdated",
        108,
        0,
        itemId=item_id(2),
        oldUrl="",
        newUrl="ipfs://sig",
        oldHash=b"\x00" * 32,
        newHash=b"\x22" * 32,
    )

    index_range(session, contract_for(chain), 100, 110)
    session.commit()

    l2 = _listing(session, ID2)
    assert l2.dataset_url == "ipfs://v2"
    assert l2.signature_url == "ipfs://sig"
    assert l2.signature_hash == "0x" + "22" * 32


# ---- run_once ----------------------------------------------------------------


def test_first_run_starts_at_start_block_and_stops_at_confirmed_head(session, chain):
    chain.head = 125
    settings = make_settings(INDEXER_START_BLOCK=100, INDEXER_BLOCK_CHUNK=10)

    written = run_once(session, settings, contract=contract_for(chain))

    assert written == 6
    ranges = [(int(c["fromBlock"], 16), int(c["toBlock"], 16)) for c in chain.get_logs_calls]
    assert ranges == [(100, 109), (110, 119), (120, 123)]
    state = _state(session)
    assert state.last_indexed_block == 123
    assert state.chain_head_block == 125


def test_events_inside_the_confirmation_window_are_not_indexed(session):
    chain = FakeChain(head=110)
    chain.add_listing(1, block=109)
    settings = make_settings(INDEXER_START_BLOCK=100, INDEXER_CONFIRMATIONS=2)

    run_once(session, settings, contract=contract_for(chain))

    assert _listing(session, ID1) is None
    assert _state(session).last_indexed_block == 108

    chain.head = 111
    run_once(session, settings, contract=contract_for(chain))

    assert _listing(session, ID1) is not None
    assert _state(session).last_indexed_block == 109


def test_next_run_resumes_after_the_cursor(session, chain):
    chain.head = 112
    contract = contract_for(chain)
    run_once(session, make_settings(), contract=contract)
    chain.get_logs_calls.clear()

    chain.head = 130
    run_once(session, make_settings(INDEXER_START_BLOCK=0), contract=contract)

    assert int(chain.get_logs_calls[0]["fromBlock"], 16) == 111


def test_nothing_happens_when_confirmed_head_is_behind_cursor(session, chain):
    session.add(IndexerState(name=STATE_NAME, last_indexed_block=123, chain_head_block=125))
    session.commit()
    chain.head = 124

    written = run_once(session, make_settings(), contract=contract_for(chain))

    assert written == 0
    assert chain.get_logs_calls == []
    state = _state(session)
    assert (state.last_indexed_block, state.chain_head_block) == (123, 125)


def test_cursor_does_not_advance_when_a_write_raises(session, chain):
    chain.fail_block_times = {105}
    settings = make_settings(INDEXER_START_BLOCK=100, INDEXER_BLOCK_CHUNK=50)

    with pytest.raises(ConnectionError):
        run_once(session, settings, contract=contract_for(chain))

    assert _state(session) is None
    assert _purchases(session) == []
    assert _listing(session, ID1) is None


def test_crash_mid_chunk_then_restart_creates_no_duplicate_purchases(session, chain):
    # Chunk 1 = 100..104, chunk 2 = 105..109. Purchase at 105 is written,
    # then block 106's timestamp lookup fails before the chunk commits.
    chain.head = 120
    chain.fail_block_times = {106}
    settings = make_settings(INDEXER_START_BLOCK=100, INDEXER_BLOCK_CHUNK=5)
    contract = contract_for(chain)

    with pytest.raises(ConnectionError):
        run_once(session, settings, contract=contract)

    assert _state(session).last_indexed_block == 104
    assert _purchases(session) == []

    chain.fail_block_times = set()
    run_once(session, settings, contract=contract)
    run_once(session, settings, contract=contract)

    rows = _purchases(session)
    assert sorted(p.block_number for p in rows) == [105, 106]
    assert _state(session).last_indexed_block == 118
