from eth_account import Account
from eth_account.messages import encode_defunct


def _sign(account, message: str) -> str:
    return "0x" + account.sign_message(
        encode_defunct(text=message)
    ).signature.hex().removeprefix("0x")


def test_nonce_then_verify_returns_bearer_token(client):
    account = Account.create()

    nonce_response = client.post(
        "/api/v1/auth/nonce",
        json={"wallet_type": "evm", "address": account.address},
    )
    assert nonce_response.status_code == 200
    challenge = nonce_response.json()

    verify_response = client.post(
        "/api/v1/auth/verify",
        json={
            "wallet_type": "evm",
            "address": account.address,
            "nonce": challenge["nonce"],
            "signature": _sign(account, challenge["message"]),
        },
    )

    assert verify_response.status_code == 200
    body = verify_response.json()
    assert body["token_type"] == "bearer"
    assert body["address"] == account.address
    assert body["access_token"]


def test_verify_replayed_nonce_returns_401(client):
    account = Account.create()
    challenge = client.post(
        "/api/v1/auth/nonce",
        json={"wallet_type": "evm", "address": account.address},
    ).json()
    payload = {
        "wallet_type": "evm",
        "address": account.address,
        "nonce": challenge["nonce"],
        "signature": _sign(account, challenge["message"]),
    }

    assert client.post("/api/v1/auth/verify", json=payload).status_code == 200
    replay = client.post("/api/v1/auth/verify", json=payload)

    assert replay.status_code == 401
    assert replay.json()["error"] == "unauthorized"


def test_solana_nonce_returns_501(client):
    response = client.post(
        "/api/v1/auth/nonce",
        json={"wallet_type": "solana", "address": "So11111111111111111111111111111111111111112"},
    )

    assert response.status_code == 501


def test_admin_scope_sign_in_returns_admin_token(client):
    account = Account.create()
    challenge = client.post(
        "/api/v1/auth/nonce",
        json={"wallet_type": "evm", "address": account.address, "scope": "admin"},
    ).json()
    assert "administrative" in challenge["message"].lower()

    response = client.post(
        "/api/v1/auth/verify",
        json={
            "wallet_type": "evm",
            "address": account.address,
            "nonce": challenge["nonce"],
            "signature": _sign(account, challenge["message"]),
            "scope": "admin",
        },
    )

    assert response.status_code == 200
    assert response.json()["scope"] == "admin"


def test_unknown_scope_is_rejected(client):
    response = client.post(
        "/api/v1/auth/nonce",
        json={"wallet_type": "evm", "address": Account.create().address, "scope": "root"},
    )

    assert response.status_code == 422
