"""Read path served from indexer tables, readiness lag, and lifespan wiring."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.contracts import router as contract_router
from app.indexer import runner as runner_module
from app.indexer.models import IndexedListing, IndexedPurchase, IndexerState
from app.indexer.service import STATE_NAME

USDC = "0x" + "0A" * 20
SELLER = "0x" + "5E" * 20
BUYER = "0x00000000000000000000000000000000000000b0"
BUYER_CHECKSUM = "0x00000000000000000000000000000000000000B0"
OTHER_BUYER = "0x00000000000000000000000000000000000000b2"
ID1 = "0x" + "01" * 16 + "00" * 16
ID2 = "0x" + "02" * 16 + "00" * 16
ID3 = "0x" + "03" * 16 + "00" * 16


def _indexer_settings(override_settings, **extra):
    return override_settings(
        INDEXER_ENABLED=True,
        INDEXER_CONFIRMATIONS=2,
        USDC_TOKEN_ADDRESS=USDC,
        **extra,
    )


def _listing(
    listing_id: str, block: int, price: int, title: str, log_index: int = 0
) -> IndexedListing:
    return IndexedListing(
        listing_id=listing_id,
        title=title,
        description=f"{title} description",
        seller=SELLER,
        payment_token=USDC,
        payment_token_decimals=6,
        price=Decimal(price),
        dataset_url=f"ipfs://{title}",
        dataset_hash="0x" + "11" * 32,
        signature_url="",
        signature_hash="0x" + "00" * 32,
        created_block=block,
        created_log_index=log_index,
        frozen=False,
        last_event_block=block,
        last_event_log_index=0,
    )


def _purchase(listing_id: str, buyer: str, block: int, n: int) -> IndexedPurchase:
    return IndexedPurchase(
        tx_hash="0x" + f"{n:064x}",
        log_index=0,
        listing_id=listing_id,
        buyer=buyer,
        payment_token=USDC,
        price_paid=Decimal(1_010_000),
        fee_paid=Decimal(10_000),
        seller_paid=Decimal(1_000_000),
        block_number=block,
        block_time=datetime(2026, 10, 11, tzinfo=timezone.utc),
    )


@pytest.fixture(autouse=True)
def no_background_indexer(monkeypatch):
    """These tests seed tables directly; keep the lifespan from starting a
    real runner thread against the shared single-connection SQLite DB."""

    async def idle(settings):
        await asyncio.Event().wait()

    monkeypatch.setattr(runner_module, "run_forever", idle)


@pytest.fixture
def seeded(db_session):
    db_session.add_all(
        [
            _listing(ID1, 101, 1_000_000, "first"),
            _listing(ID2, 102, 2_000_000, "second"),
            _listing(ID3, 103, 3_000_000, "third"),
            _purchase(ID1, BUYER_CHECKSUM, 110, 1),
            _purchase(ID2, BUYER_CHECKSUM, 120, 2),
            _purchase(ID1, OTHER_BUYER, 130, 3),
        ]
    )
    db_session.commit()
    return db_session


def _set_state(session, last: int, head: int, age_seconds: float = 0) -> None:
    session.merge(
        IndexerState(
            name=STATE_NAME,
            last_indexed_block=last,
            chain_head_block=head,
            updated_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
        )
    )
    session.commit()


def _forbid_contract(monkeypatch, *names: str) -> None:
    for name in names:
        def boom(*args, _name=name, **kwargs):
            raise AssertionError(f"contract read {_name} should not be called")

        monkeypatch.setattr(contract_router.contract_service, name, boom)


def _contract_items(monkeypatch) -> list[str]:
    calls: list[str] = []

    def fake_get_all_items(settings):
        calls.append("get_all_items")
        return []

    monkeypatch.setattr(contract_router.contract_service, "get_all_items", fake_get_all_items)
    return calls


# ---- browse -----------------------------------------------------------------


def test_browse_reads_listings_table_when_indexer_is_synced(
    client_factory, override_settings, seeded, monkeypatch
):
    settings = _indexer_settings(override_settings)
    _set_state(seeded, last=198, head=200)
    _forbid_contract(monkeypatch, "get_all_items")

    with client_factory(settings=settings) as client:
        response = client.get("/api/v1/contract/items/all")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [ID1, ID2, ID3]
    first = body[0]
    assert first["title"] == "first"
    assert first["description"] == "first description"
    assert first["seller"] == SELLER
    assert first["price_atomic"] == "1000000"
    assert first["settlement_currency"] == "USDC"
    assert first["settlement_decimals"] == 6
    assert first["exists"] is True
    assert [item["purchase_count"] for item in body] == [2, 1, 0]


def test_browse_falls_back_to_contract_when_indexer_state_is_missing(
    client_factory, override_settings, seeded, monkeypatch
):
    settings = _indexer_settings(override_settings)
    calls = _contract_items(monkeypatch)

    with client_factory(settings=settings) as client:
        response = client.get("/api/v1/contract/items/all")

    assert response.status_code == 200
    assert calls == ["get_all_items"]


def test_browse_falls_back_to_contract_while_indexer_is_catching_up(
    client_factory, override_settings, seeded, monkeypatch
):
    settings = _indexer_settings(override_settings)
    _set_state(seeded, last=150, head=200)
    calls = _contract_items(monkeypatch)

    with client_factory(settings=settings) as client:
        client.get("/api/v1/contract/items/all")

    assert calls == ["get_all_items"]


def test_browse_ignores_tables_when_indexer_is_disabled(
    client_factory, override_settings, seeded, monkeypatch
):
    settings = override_settings(INDEXER_ENABLED=False)
    _set_state(seeded, last=198, head=200)
    calls = _contract_items(monkeypatch)

    with client_factory(settings=settings) as client:
        client.get("/api/v1/contract/items/all")

    assert calls == ["get_all_items"]


def test_browse_falls_back_to_contract_when_indexer_state_is_stale(
    client_factory, override_settings, seeded, monkeypatch
):
    settings = _indexer_settings(override_settings, INDEXER_POLL_SECONDS=5)
    _set_state(seeded, last=198, head=200, age_seconds=120)
    calls = _contract_items(monkeypatch)

    with client_factory(settings=settings) as client:
        client.get("/api/v1/contract/items/all")

    assert calls == ["get_all_items"]


def test_browse_orders_same_block_listings_by_log_index(
    client_factory, override_settings, db_session, monkeypatch
):
    settings = _indexer_settings(override_settings)
    db_session.add_all(
        [
            _listing(ID1, 101, 1, "later-in-block", log_index=9),
            _listing(ID2, 101, 1, "earlier-in-block", log_index=2),
        ]
    )
    db_session.commit()
    _set_state(db_session, last=198, head=200)
    _forbid_contract(monkeypatch, "get_all_items")

    with client_factory(settings=settings) as client:
        body = client.get("/api/v1/contract/items/all").json()

    assert [item["id"] for item in body] == [ID2, ID1]


# ---- purchases by wallet ------------------------------------------------------


def test_purchases_by_wallet_rejects_inverted_block_range(
    client_factory, override_settings, seeded, monkeypatch
):
    settings = _indexer_settings(override_settings)
    _set_state(seeded, last=198, head=200)
    _forbid_contract(monkeypatch, "get_purchased_items_by_wallet")

    with client_factory(settings=settings) as client:
        response = client.post(
            "/api/v1/contract/purchases/by-wallet",
            json={"wallet_type": "evm", "address": BUYER, "start_block": 20, "end_block": 10},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "start_block cannot be greater than end_block"


def test_purchases_by_wallet_reads_purchases_table_newest_first(
    client_factory, override_settings, seeded, monkeypatch
):
    settings = _indexer_settings(override_settings)
    _set_state(seeded, last=198, head=200)
    _forbid_contract(monkeypatch, "get_purchased_items_by_wallet")

    with client_factory(settings=settings) as client:
        response = client.post(
            "/api/v1/contract/purchases/by-wallet",
            json={"wallet_type": "evm", "address": BUYER},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [item["id"] for item in body["items"]] == [ID2, ID1]
    assert body["wallet_id"].startswith("0x") and len(body["wallet_id"]) == 66


def test_purchases_by_wallet_applies_block_range_and_paging(
    client_factory, override_settings, seeded, monkeypatch
):
    settings = _indexer_settings(override_settings)
    _set_state(seeded, last=198, head=200)
    _forbid_contract(monkeypatch, "get_purchased_items_by_wallet")

    with client_factory(settings=settings) as client:
        in_range = client.post(
            "/api/v1/contract/purchases/by-wallet",
            json={"wallet_type": "evm", "address": BUYER, "start_block": 100, "end_block": 115},
        ).json()
        paged = client.post(
            "/api/v1/contract/purchases/by-wallet",
            json={"wallet_type": "evm", "address": BUYER, "limit": 1, "offset": 1},
        ).json()

    assert [item["id"] for item in in_range["items"]] == [ID1]
    assert [item["id"] for item in paged["items"]] == [ID1]


def test_purchases_by_wallet_with_no_purchases_returns_empty_list(
    client_factory, override_settings, seeded, monkeypatch
):
    settings = _indexer_settings(override_settings)
    _set_state(seeded, last=198, head=200)
    _forbid_contract(monkeypatch, "get_purchased_items_by_wallet")

    with client_factory(settings=settings) as client:
        response = client.post(
            "/api/v1/contract/purchases/by-wallet",
            json={"wallet_type": "evm", "address": "0x" + "99" * 20},
        )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["count"] == 0


def test_purchases_by_wallet_falls_back_to_contract_without_state(
    client_factory, override_settings, seeded, monkeypatch
):
    settings = _indexer_settings(override_settings)
    calls: list[str] = []

    def fake(**kwargs):
        calls.append(kwargs["address"])
        return ("0x" + "11" * 32, [])

    monkeypatch.setattr(contract_router.contract_service, "get_purchased_items_by_wallet", fake)

    with client_factory(settings=settings) as client:
        client.post(
            "/api/v1/contract/purchases/by-wallet",
            json={"wallet_type": "evm", "address": BUYER},
        )

    assert calls == [BUYER]


# ---- readiness ----------------------------------------------------------------


def test_readiness_reports_indexer_lag_in_blocks(client_factory, override_settings, db_session):
    settings = _indexer_settings(override_settings)
    _set_state(db_session, last=200, head=250)

    with client_factory(settings=settings) as client:
        body = client.get("/health/ready").json()

    assert body["ready"] is True
    assert body["indexer_lag_blocks"] == 50
    assert body["dependencies"]["indexer"] == "catching_up"


def test_readiness_reports_synced_indexer(client_factory, override_settings, db_session):
    settings = _indexer_settings(override_settings)
    _set_state(db_session, last=248, head=250)

    with client_factory(settings=settings) as client:
        body = client.get("/health/ready").json()

    assert body["indexer_lag_blocks"] == 2
    assert body["dependencies"]["indexer"] == "synced"


def test_readiness_reports_stale_indexer(client_factory, override_settings, db_session):
    settings = _indexer_settings(override_settings, INDEXER_POLL_SECONDS=5)
    _set_state(db_session, last=248, head=250, age_seconds=300)

    with client_factory(settings=settings) as client:
        body = client.get("/health/ready").json()

    assert body["indexer_lag_blocks"] == 2
    assert body["dependencies"]["indexer"] == "stale"


def test_readiness_before_first_indexer_run(client_factory, override_settings):
    settings = _indexer_settings(override_settings)

    with client_factory(settings=settings) as client:
        body = client.get("/health/ready").json()

    assert body["indexer_lag_blocks"] is None
    assert body["dependencies"]["indexer"] == "starting"


# ---- lifespan -----------------------------------------------------------------


def test_lifespan_starts_indexer_only_when_enabled(client_factory, monkeypatch):
    started: list[bool] = []
    cancelled: list[bool] = []

    async def fake_run_forever(settings):
        started.append(settings.indexer_enabled)
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    monkeypatch.setattr(runner_module, "run_forever", fake_run_forever)

    with client_factory(INDEXER_ENABLED=False):
        pass
    assert started == []

    with client_factory(INDEXER_ENABLED=True):
        pass
    assert started == [True]
    assert cancelled == [True]
