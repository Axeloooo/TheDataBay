from types import SimpleNamespace

import pytest
from web3 import Web3

from app.contracts import service as contract_service
from app.datasets import router as datasets_router

WALLET_A = Web3.to_checksum_address("0x" + "aa" * 20)
WALLET_B = Web3.to_checksum_address("0x" + "bb" * 20)
KEY_PATH = "/api/v1/datasets/listing-123/key"


@pytest.fixture
def only_b_has_access(settings, monkeypatch):
    """has_access is true only for wallet B's real wallet id."""
    calls = []
    b_wallet_id = contract_service.wallet_id("evm", WALLET_B, settings)

    def fake_has_access(listing_id, wallet_id_bytes, resolved_settings):
        calls.append((listing_id, wallet_id_bytes))
        return wallet_id_bytes == b_wallet_id

    monkeypatch.setattr(datasets_router.contract_service, "has_access", fake_has_access)
    monkeypatch.setattr(
        datasets_router.dataset_key_repo,
        "get_dataset_key",
        lambda session, listing_id: SimpleNamespace(
            key_b64="a2V5", nonce_b64="bm9uY2U="
        ),
    )
    return SimpleNamespace(calls=calls, b_wallet_id=b_wallet_id)


def test_release_key_without_token_returns_401(client, only_b_has_access):
    response = client.post(KEY_PATH)

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert only_b_has_access.calls == []


def test_release_key_ignores_address_in_body(client, only_b_has_access):
    response = client.post(
        KEY_PATH, json={"wallet_type": "evm", "address": WALLET_B}
    )

    assert response.status_code == 401
    assert only_b_has_access.calls == []


def test_token_for_wallet_a_cannot_fetch_key_bought_by_wallet_b(
    client, auth_headers, only_b_has_access
):
    response = client.post(
        KEY_PATH,
        headers=auth_headers(WALLET_A),
        json={"wallet_type": "evm", "address": WALLET_B},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access not authorized"}


def test_wallet_with_access_gets_key(client, auth_headers, only_b_has_access):
    response = client.post(KEY_PATH, headers=auth_headers(WALLET_B))

    assert response.status_code == 200
    assert response.json() == {
        "id": "listing-123",
        "key_b64": "a2V5",
        "nonce_b64": "bm9uY2U=",
        "algorithm": "AES-256-GCM",
    }
    assert only_b_has_access.calls == [("listing-123", only_b_has_access.b_wallet_id)]


def test_release_key_returns_404_when_key_is_missing(
    client, auth_headers, monkeypatch
):
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

    response = client.post(KEY_PATH, headers=auth_headers(WALLET_B))

    assert response.status_code == 404
    assert response.json() == {"detail": "Key not found for listing"}


def test_admin_scope_token_cannot_fetch_key(client, auth_headers, only_b_has_access):
    response = client.post(KEY_PATH, headers=auth_headers(WALLET_B, scope="admin"))

    assert response.status_code == 401
    assert only_b_has_access.calls == []
