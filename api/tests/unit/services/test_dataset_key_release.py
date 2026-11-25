import pytest
from fastapi import HTTPException

from app.auth.dependencies import AuthedWallet
from app.datasets.router import release_key
from app.datasets.schemas import WalletType
from app.contracts import service as contract_service
from app.datasets import repository as dataset_key_repo

LISTING_ID = "123e4567-e89b-12d3-a456-426614174000"
WALLET = AuthedWallet(
    wallet_type=WalletType.EVM,
    address="0x0000000000000000000000000000000000000001",
    wallet_id=b"1" * 32,
)


UPLOADER = "0x00000000000000000000000000000000000000Aa"
SQUATTER = "0x00000000000000000000000000000000000000bB"


class DummyRecord:
    def __init__(self, key_b64: str, nonce_b64: str, seller_address: str | None = None):
        self.key_b64 = key_b64
        self.nonce_b64 = nonce_b64
        self.seller_address = seller_address


class DummyItem:
    def __init__(self, seller: str):
        self.seller = seller


def _grant_access(monkeypatch, record):
    monkeypatch.setattr(contract_service, "has_access", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        dataset_key_repo, "get_dataset_key", lambda session, listing_id: record
    )


def test_release_key_authorized_checks_token_wallet_id(monkeypatch, settings):
    checked = []
    monkeypatch.setattr(
        contract_service,
        "has_access",
        lambda listing_id, wallet_id_bytes, settings: checked.append(wallet_id_bytes)
        or True,
    )
    monkeypatch.setattr(
        dataset_key_repo,
        "get_dataset_key",
        lambda session, listing_id: DummyRecord("key", "nonce"),
    )

    response = release_key(
        id=LISTING_ID, wallet=WALLET, settings=settings, session=object()
    )

    assert response.key_b64 == "key"
    assert response.nonce_b64 == "nonce"
    assert checked == [WALLET.wallet_id]


def test_release_key_unauthorized(monkeypatch, settings):
    monkeypatch.setattr(contract_service, "has_access", lambda *args, **kwargs: False)

    with pytest.raises(HTTPException) as exc:
        release_key(id=LISTING_ID, wallet=WALLET, settings=settings, session=object())
    assert exc.value.status_code == 403


def test_release_key_when_onchain_seller_is_the_uploader(monkeypatch, settings):
    # Stored checksummed, chain returns lowercase: still the same wallet.
    _grant_access(monkeypatch, DummyRecord("key", "nonce", seller_address=UPLOADER))
    looked_up = []
    monkeypatch.setattr(
        contract_service,
        "get_item_view",
        lambda listing_id, settings: looked_up.append(listing_id)
        or DummyItem(UPLOADER.lower()),
    )

    response = release_key(
        id=LISTING_ID, wallet=WALLET, settings=settings, session=object()
    )

    assert response.key_b64 == "key"
    assert looked_up == [LISTING_ID]


def test_release_key_refuses_squatted_listing(monkeypatch, settings):
    """Someone else created the on-chain item under the uploader's listing ID."""
    _grant_access(monkeypatch, DummyRecord("key", "nonce", seller_address=UPLOADER))
    monkeypatch.setattr(
        contract_service, "get_item_view", lambda listing_id, settings: DummyItem(SQUATTER)
    )

    with pytest.raises(HTTPException) as exc:
        release_key(id=LISTING_ID, wallet=WALLET, settings=settings, session=object())

    assert exc.value.status_code == 403
    assert "seller" in exc.value.detail.lower()


def test_release_key_for_legacy_row_skips_seller_check(monkeypatch, settings):
    _grant_access(monkeypatch, DummyRecord("key", "nonce", seller_address=None))
    monkeypatch.setattr(
        contract_service,
        "get_item_view",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("legacy rows have no seller to compare")
        ),
    )

    response = release_key(
        id=LISTING_ID, wallet=WALLET, settings=settings, session=object()
    )

    assert response.key_b64 == "key"
