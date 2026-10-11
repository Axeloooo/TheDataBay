"""/api/v1/me endpoints: wallet comes only from the token."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.contracts.marketplace_schemas import MarketplaceDataItem
from app.indexer import runner as runner_module
from app.indexer.models import IndexedListing, IndexedPurchase, IndexerState
from app.indexer.service import STATE_NAME
from app.me import service as me_service

USDC = "0x" + "0A" * 20
ALICE = "0x00000000000000000000000000000000000000A1"
BOB = "0x00000000000000000000000000000000000000B2"
CAROL = "0x00000000000000000000000000000000000000C3"
DAVE = "0x00000000000000000000000000000000000000D4"
ID1 = "0x" + "01" * 16 + "00" * 16
ID2 = "0x" + "02" * 16 + "00" * 16
ID3 = "0x" + "03" * 16 + "00" * 16


def _listing(listing_id, seller, block, price=1_000_000, title=None, frozen=False):
    return IndexedListing(
        listing_id=listing_id,
        title=title or f"title-{block}",
        description=f"desc-{block}",
        seller=seller,
        payment_token=USDC,
        payment_token_decimals=6,
        price=Decimal(price),
        dataset_url="ipfs://x",
        dataset_hash="0x" + "11" * 32,
        signature_url="",
        signature_hash="0x" + "00" * 32,
        created_block=block,
        created_log_index=0,
        frozen=frozen,
        last_event_block=block,
        last_event_log_index=0,
    )


def _purchase(listing_id, buyer, n, seller_paid=1_000_000):
    return IndexedPurchase(
        tx_hash="0x" + f"{n:064x}",
        log_index=0,
        listing_id=listing_id,
        buyer=buyer,
        payment_token=USDC,
        price_paid=Decimal(seller_paid + 10_000),
        fee_paid=Decimal(10_000),
        seller_paid=Decimal(seller_paid),
        block_number=100 + n,
        block_time=datetime(2026, 10, 11, tzinfo=timezone.utc),
    )


def _state(session, age_seconds=0):
    session.merge(
        IndexerState(
            name=STATE_NAME,
            last_indexed_block=198,
            chain_head_block=200,
            updated_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
        )
    )
    session.commit()


@pytest.fixture(autouse=True)
def no_background_indexer(monkeypatch):
    """Seed tables directly; keep the lifespan from starting a real runner."""

    async def idle(settings):
        await asyncio.Event().wait()

    monkeypatch.setattr(runner_module, "run_forever", idle)


@pytest.fixture
def indexed(db_session, override_settings):
    settings = override_settings(
        INDEXER_ENABLED=True, INDEXER_CONFIRMATIONS=2, USDC_TOKEN_ADDRESS=USDC
    )
    db_session.add_all(
        [
            _listing(ID1, ALICE, 10, title="alice-one"),
            _listing(ID2, ALICE, 11, title="alice-two"),
            _listing(ID3, BOB, 12, title="bob-one"),
            _purchase(ID1, BOB, 1),
            _purchase(ID1, CAROL, 2),
            _purchase(ID3, ALICE, 3),
        ]
    )
    db_session.commit()
    _state(db_session)
    return settings


def test_requires_token(client_factory, indexed):
    with client_factory(settings=indexed) as client:
        assert client.get("/api/v1/me/purchases").status_code == 401
        assert client.get("/api/v1/me/listings").status_code == 401


def test_admin_scope_token_is_rejected(client_factory, indexed, auth_headers):
    with client_factory(settings=indexed) as client:
        r = client.get(
            "/api/v1/me/listings", headers=auth_headers(ALICE, indexed, "admin")
        )
    assert r.status_code == 401


def test_purchases_returns_only_callers_rows(client_factory, indexed, auth_headers):
    with client_factory(settings=indexed) as client:
        r = client.get("/api/v1/me/purchases", headers=auth_headers(ALICE, indexed))
    assert r.status_code == 200
    body = r.json()
    assert [p["listing_id"] for p in body] == [ID3]
    assert body[0]["title"] == "bob-one"
    assert body[0]["price_paid"] == "1010000"
    assert body[0]["token_symbol"] == "USDC"
    assert body[0]["token_decimals"] == 6
    assert body[0]["source"] == "indexer"
    assert body[0]["purchased_at"].startswith("2026-10-11")


def test_purchases_empty_for_wallet_with_none(client_factory, indexed, auth_headers):
    with client_factory(settings=indexed) as client:
        r = client.get("/api/v1/me/purchases", headers=auth_headers(DAVE, indexed))
    assert r.status_code == 200
    assert r.json() == []


def test_listings_returns_only_callers_rows_with_earnings(
    client_factory, indexed, auth_headers
):
    with client_factory(settings=indexed) as client:
        r = client.get("/api/v1/me/listings", headers=auth_headers(ALICE, indexed))
    assert r.status_code == 200
    by_id = {row["listing_id"]: row for row in r.json()}
    assert set(by_id) == {ID1, ID2}
    sold, unsold = by_id[ID1], by_id[ID2]
    assert sold["sales_count"] == 2
    assert sold["earnings_by_token"] == {USDC: "2000000"}
    assert sold["price_editable"] is False
    assert sold["token_symbol"] == "USDC"
    assert unsold["sales_count"] == 0
    assert unsold["earnings_by_token"] == {}
    assert unsold["price_editable"] is True
    assert unsold["source"] == "indexer"


def test_listings_empty_for_non_seller(client_factory, indexed, auth_headers):
    with client_factory(settings=indexed) as client:
        r = client.get("/api/v1/me/listings", headers=auth_headers(CAROL, indexed))
    assert r.status_code == 200
    assert r.json() == []


def test_frozen_listing_is_not_editable(
    client_factory, db_session, override_settings, auth_headers
):
    settings = override_settings(INDEXER_ENABLED=True, USDC_TOKEN_ADDRESS=USDC)
    db_session.add(_listing(ID1, ALICE, 10, frozen=True))
    db_session.commit()
    _state(db_session)
    with client_factory(settings=settings) as client:
        r = client.get("/api/v1/me/listings", headers=auth_headers(ALICE, settings))
    assert r.json()[0]["price_editable"] is False


def _item(item_id, seller, count, title="t"):
    return MarketplaceDataItem(
        id=item_id,
        title=title,
        description="d",
        seller=seller,
        payment_token=USDC,
        price_atomic="5000000",
        settlement_currency="USDC",
        settlement_decimals=6,
        dataset_url="ipfs://x",
        dataset_hash="0x" + "11" * 32,
        signature_url="",
        signature_hash="0x" + "00" * 32,
        exists=True,
        purchase_count=count,
    )


def test_falls_back_to_contract_when_indexer_disabled(
    client_factory, override_settings, auth_headers, monkeypatch
):
    settings = override_settings(INDEXER_ENABLED=False)
    monkeypatch.setattr(
        me_service.contract_service,
        "get_all_items",
        lambda s: [_item(ID1, ALICE, 0), _item(ID2, ALICE, 3), _item(ID3, BOB, 0)],
    )
    monkeypatch.setattr(
        me_service.contract_service,
        "get_purchased_items_by_wallet",
        lambda *a, **k: ("0xwallet", [_item(ID3, BOB, 1, title="bought")]),
    )
    with client_factory(settings=settings) as client:
        listings = client.get(
            "/api/v1/me/listings", headers=auth_headers(ALICE, settings)
        )
        purchases = client.get(
            "/api/v1/me/purchases", headers=auth_headers(ALICE, settings)
        )
    rows = {r["listing_id"]: r for r in listings.json()}
    assert set(rows) == {ID1, ID2}
    assert rows[ID1]["price_editable"] is True
    assert rows[ID2]["price_editable"] is False
    assert rows[ID2]["sales_count"] == 3
    assert rows[ID2]["earnings_by_token"] == {}
    assert rows[ID2]["source"] == "contract"
    p = purchases.json()
    assert [x["title"] for x in p] == ["bought"]
    assert p[0]["source"] == "contract"
    assert p[0]["purchased_at"] is None


def test_falls_back_when_indexer_state_is_stale(
    client_factory, db_session, override_settings, auth_headers, monkeypatch
):
    settings = override_settings(
        INDEXER_ENABLED=True, INDEXER_POLL_SECONDS=5, USDC_TOKEN_ADDRESS=USDC
    )
    db_session.add(_listing(ID1, ALICE, 10))
    db_session.commit()
    _state(db_session, age_seconds=600)
    monkeypatch.setattr(me_service.contract_service, "get_all_items", lambda s: [])
    with client_factory(settings=settings) as client:
        r = client.get("/api/v1/me/listings", headers=auth_headers(ALICE, settings))
    assert r.json() == []
