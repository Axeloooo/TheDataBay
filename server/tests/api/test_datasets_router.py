from types import SimpleNamespace

from app.routers import datasets_router


def test_release_key_returns_encryption_material(client, monkeypatch):
    captured = {}

    def fake_wallet_id(wallet_type, address, settings):
        captured["wallet_args"] = (wallet_type, address, settings)
        return b"wallet-id"

    def fake_has_access(listing_id, wallet_id_bytes, settings):
        captured["access_args"] = (listing_id, wallet_id_bytes, settings)
        return True

    def fake_get_dataset_key(session, listing_id):
        captured["key_args"] = (session, listing_id)
        return SimpleNamespace(key_b64="a2V5", nonce_b64="bm9uY2U=")

    monkeypatch.setattr(datasets_router.contract_service, "wallet_id", fake_wallet_id)
    monkeypatch.setattr(datasets_router.contract_service, "has_access", fake_has_access)
    monkeypatch.setattr(
        datasets_router.dataset_key_repo,
        "get_dataset_key",
        fake_get_dataset_key,
    )

    response = client.post(
        "/api/v1/datasets/listing-123/key",
        json={
            "wallet_type": "evm",
            "address": "0x0000000000000000000000000000000000000001",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "listing-123",
        "key_b64": "a2V5",
        "nonce_b64": "bm9uY2U=",
        "algorithm": "AES-256-GCM",
    }
    assert captured["wallet_args"][:2] == (
        "evm",
        "0x0000000000000000000000000000000000000001",
    )
    assert captured["access_args"][:2] == ("listing-123", b"wallet-id")
    assert captured["key_args"][1] == "listing-123"


def test_release_key_returns_403_when_access_is_denied(client, monkeypatch):
    monkeypatch.setattr(
        datasets_router.contract_service,
        "wallet_id",
        lambda wallet_type, address, settings: b"wallet-id",
    )
    monkeypatch.setattr(
        datasets_router.contract_service,
        "has_access",
        lambda listing_id, wallet_id_bytes, settings: False,
    )
    monkeypatch.setattr(
        datasets_router.dataset_key_repo,
        "get_dataset_key",
        lambda session, listing_id: (_ for _ in ()).throw(
            AssertionError("get_dataset_key should not be called when unauthorized")
        ),
    )

    response = client.post(
        "/api/v1/datasets/listing-123/key",
        json={
            "wallet_type": "evm",
            "address": "0x0000000000000000000000000000000000000001",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access not authorized"}


def test_release_key_returns_404_when_key_is_missing(client, monkeypatch):
    monkeypatch.setattr(
        datasets_router.contract_service,
        "wallet_id",
        lambda wallet_type, address, settings: b"wallet-id",
    )
    monkeypatch.setattr(
        datasets_router.contract_service,
        "has_access",
        lambda listing_id, wallet_id_bytes, settings: True,
    )
    monkeypatch.setattr(
        datasets_router.dataset_key_repo,
        "get_dataset_key",
        lambda session, listing_id: None,
    )

    response = client.post(
        "/api/v1/datasets/listing-123/key",
        json={
            "wallet_type": "evm",
            "address": "0x0000000000000000000000000000000000000001",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Key not found for listing"}


def test_release_key_validates_wallet_type_before_router_logic(client, monkeypatch):
    monkeypatch.setattr(
        datasets_router.contract_service,
        "wallet_id",
        lambda wallet_type, address, settings: (_ for _ in ()).throw(
            AssertionError("wallet_id should not be called for invalid payloads")
        ),
    )

    response = client.post(
        "/api/v1/datasets/listing-123/key",
        json={
            "wallet_type": "bitcoin",
            "address": "wallet-address",
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(error["loc"][-1] == "wallet_type" for error in detail)
