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


class DummyRecord:
    def __init__(self, key_b64: str, nonce_b64: str):
        self.key_b64 = key_b64
        self.nonce_b64 = nonce_b64


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
