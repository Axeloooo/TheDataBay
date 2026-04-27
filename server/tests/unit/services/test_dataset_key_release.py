import pytest
from fastapi import HTTPException

from app.routers.datasets_router import release_key
from app.schemas.dataset_schema import KeyReleaseRequest
from app.services import contract_service
from app.services import dataset_key_repo


class DummyRecord:
    def __init__(self, key_b64: str, nonce_b64: str):
        self.key_b64 = key_b64
        self.nonce_b64 = nonce_b64


def test_release_key_authorized(monkeypatch, settings):
    monkeypatch.setattr(
        contract_service, "wallet_id", lambda *args, **kwargs: b"1" * 32
    )
    monkeypatch.setattr(contract_service, "has_access", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        dataset_key_repo,
        "get_dataset_key",
        lambda session, listing_id: DummyRecord("key", "nonce"),
    )

    response = release_key(
        id="123e4567-e89b-12d3-a456-426614174000",
        request=KeyReleaseRequest(wallet_type="evm", address="0x1"),
        settings=settings,
        session=object(),
    )

    assert response.key_b64 == "key"
    assert response.nonce_b64 == "nonce"


def test_release_key_unauthorized(monkeypatch, settings):
    monkeypatch.setattr(
        contract_service, "wallet_id", lambda *args, **kwargs: b"1" * 32
    )
    monkeypatch.setattr(contract_service, "has_access", lambda *args, **kwargs: False)

    with pytest.raises(HTTPException) as exc:
        release_key(
            id="123e4567-e89b-12d3-a456-426614174000",
            request=KeyReleaseRequest(wallet_type="evm", address="0x1"),
            settings=settings,
            session=object(),
        )
    assert exc.value.status_code == 403
