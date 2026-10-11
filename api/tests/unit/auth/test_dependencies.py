import base64
import json
import time

import jwt
import pytest
from eth_account import Account

from app.auth import dependencies as auth_deps
from app.auth import service as auth_service
from app.contracts import service as contract_service
from app.shared.errors import ApiError

from .conftest import TEST_JWT_SECRET, make_settings


def _claims(settings, address, **overrides):
    now = int(time.time())
    claims = {
        "iss": auth_service.TOKEN_ISSUER,
        "aud": auth_service.TOKEN_AUDIENCE,
        "sub": address,
        "wallet_type": "evm",
        "wallet_id": "0x"
        + contract_service.wallet_id("evm", address, settings).hex(),
        "iat": now,
        "exp": now + 600,
    }
    claims.update(overrides)
    return {k: v for k, v in claims.items() if v is not None}


def _token(claims, secret=TEST_JWT_SECRET, algorithm="HS256"):
    return jwt.encode(claims, secret, algorithm=algorithm)


def _expect_status(status, authorization, settings):
    with pytest.raises(ApiError) as exc:
        auth_deps.current_wallet(authorization=authorization, settings=settings)
    assert exc.value.status_code == status


def test_valid_issued_token_returns_authed_wallet(settings):
    account = Account.create()
    issued = auth_service.issue_token("evm", account.address, settings)

    wallet = auth_deps.current_wallet(
        authorization=f"Bearer {issued.access_token}", settings=settings
    )

    assert wallet.address == account.address
    assert wallet.wallet_type.value == "evm"
    assert wallet.wallet_id == contract_service.wallet_id(
        "evm", account.address, settings
    )


def test_missing_header_raises_401(settings):
    _expect_status(401, None, settings)


@pytest.mark.parametrize(
    "authorization",
    ["", "Bearer", "Bearer ", "Token abc", "Basic dXNlcjpwYXNz", "Bearer a b", "Bearer not.a.jwt"],
)
def test_malformed_header_raises_401(settings, authorization):
    _expect_status(401, authorization, settings)


def test_expired_token_raises_401(settings):
    address = Account.create().address
    now = int(time.time())
    token = _token(_claims(settings, address, iat=now - 7200, exp=now - 3600))

    _expect_status(401, f"Bearer {token}", settings)


def test_token_without_exp_raises_401(settings):
    address = Account.create().address
    token = _token(_claims(settings, address, exp=None))

    _expect_status(401, f"Bearer {token}", settings)


def test_token_signed_with_other_secret_raises_401(settings):
    address = Account.create().address
    token = _token(_claims(settings, address), secret="other-" + "y" * 40)

    _expect_status(401, f"Bearer {token}", settings)


def test_tampered_payload_raises_401(settings):
    victim = Account.create().address
    attacker = Account.create().address
    header, _payload, signature = _token(_claims(settings, attacker)).split(".")
    forged_payload = (
        base64.urlsafe_b64encode(json.dumps(_claims(settings, victim)).encode())
        .rstrip(b"=")
        .decode()
    )

    _expect_status(401, f"Bearer {header}.{forged_payload}.{signature}", settings)


def test_alg_none_token_raises_401(settings):
    address = Account.create().address
    token = jwt.encode(_claims(settings, address), key=None, algorithm="none")

    _expect_status(401, f"Bearer {token}", settings)


def test_non_hs256_algorithm_raises_401(settings):
    address = Account.create().address
    token = _token(_claims(settings, address), algorithm="HS512")

    _expect_status(401, f"Bearer {token}", settings)


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "someone-else"},
        {"iss": "someone-else"},
        {"wallet_type": "solana"},
        {"sub": "not-an-address"},
        {"wallet_id": "0x" + "00" * 32},
    ],
)
def test_invalid_claims_raise_401(settings, overrides):
    address = Account.create().address
    token = _token(_claims(settings, address, **overrides))

    _expect_status(401, f"Bearer {token}", settings)


def test_token_from_other_chain_raises_401(settings):
    address = Account.create().address
    other_chain = make_settings(CHAIN_ID=8453)
    token = auth_service.issue_token("evm", address, other_chain).access_token

    _expect_status(401, f"Bearer {token}", settings)


def test_unconfigured_secret_raises_503(settings):
    address = Account.create().address
    token = auth_service.issue_token("evm", address, settings).access_token

    _expect_status(503, f"Bearer {token}", make_settings(AUTH_JWT_SECRET=None))


def _wallet(settings, address):
    return auth_deps.AuthedWallet(
        wallet_type=auth_deps.WalletType.EVM,
        address=address,
        wallet_id=contract_service.wallet_id("evm", address, settings),
    )


def test_require_owner_allows_owner_case_insensitively(settings, monkeypatch):
    owner = Account.create().address
    monkeypatch.setattr(contract_service, "owner", lambda s: owner.lower())
    wallet = _wallet(settings, owner)

    assert auth_deps.require_owner(wallet=wallet, settings=settings) is wallet


def test_require_owner_rejects_non_owner_with_403(settings, monkeypatch):
    owner = Account.create().address
    monkeypatch.setattr(contract_service, "owner", lambda s: owner)
    wallet = _wallet(settings, Account.create().address)

    with pytest.raises(ApiError) as exc:
        auth_deps.require_owner(wallet=wallet, settings=settings)

    assert exc.value.status_code == 403
