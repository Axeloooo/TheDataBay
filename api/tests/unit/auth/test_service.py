from datetime import datetime, timedelta, timezone

import jwt
import pytest
from eth_account import Account
from sqlmodel import select

from app.auth import service as auth_service
from app.auth.models import AuthNonce
from app.shared.errors import ApiError

from .conftest import TEST_JWT_SECRET, make_settings, sign


def _sign_in(session, settings, account):
    issued = auth_service.create_nonce(session, "evm", account.address, settings)
    signature = sign(account, issued.message)
    return issued, signature


def test_create_nonce_returns_message_binding_address_nonce_and_chain(
    session, settings, wallet
):
    issued = auth_service.create_nonce(
        session, "evm", wallet.address.lower(), settings
    )

    assert len(issued.nonce) >= 32
    assert wallet.address in issued.message  # checksummed address
    assert f"Nonce: {issued.nonce}" in issued.message
    assert f"Chain ID: {settings.chain_id}" in issued.message
    assert settings.auth_domain in issued.message
    row = session.exec(select(AuthNonce).where(AuthNonce.nonce == issued.nonce)).one()
    assert row.address == wallet.address
    assert row.used_at is None


def test_create_nonce_issues_unique_nonces(session, settings, wallet):
    first = auth_service.create_nonce(session, "evm", wallet.address, settings)
    second = auth_service.create_nonce(session, "evm", wallet.address, settings)

    assert first.nonce != second.nonce


def test_create_nonce_rejects_invalid_evm_address(session, settings):
    with pytest.raises(ApiError) as exc:
        auth_service.create_nonce(session, "evm", "not-an-address", settings)

    assert exc.value.status_code == 400


def test_valid_evm_personal_sign_returns_hs256_token(session, settings, wallet):
    issued, signature = _sign_in(session, settings, wallet)

    result = auth_service.verify_signature(
        session, "evm", wallet.address, issued.nonce, signature, settings
    )

    assert result.token_type == "bearer"
    assert jwt.get_unverified_header(result.access_token)["alg"] == "HS256"
    claims = jwt.decode(
        result.access_token,
        TEST_JWT_SECRET,
        algorithms=["HS256"],
        audience=auth_service.TOKEN_AUDIENCE,
        issuer=auth_service.TOKEN_ISSUER,
    )
    assert claims["sub"] == wallet.address
    assert claims["wallet_type"] == "evm"
    assert claims["exp"] - claims["iat"] == settings.auth_token_ttl_seconds
    assert result.address == wallet.address


def test_verify_accepts_lowercase_address(session, settings, wallet):
    issued, signature = _sign_in(session, settings, wallet)

    result = auth_service.verify_signature(
        session, "evm", wallet.address.lower(), issued.nonce, signature, settings
    )

    assert result.address == wallet.address


def test_reused_nonce_raises_401(session, settings, wallet):
    issued, signature = _sign_in(session, settings, wallet)
    auth_service.verify_signature(
        session, "evm", wallet.address, issued.nonce, signature, settings
    )

    with pytest.raises(ApiError) as exc:
        auth_service.verify_signature(
            session, "evm", wallet.address, issued.nonce, signature, settings
        )

    assert exc.value.status_code == 401


def test_expired_nonce_raises_401(session, settings, wallet, monkeypatch):
    issued, signature = _sign_in(session, settings, wallet)
    later = datetime.now(timezone.utc) + timedelta(
        seconds=settings.auth_nonce_ttl_seconds + 1
    )
    monkeypatch.setattr(auth_service, "_utcnow", lambda: later)

    with pytest.raises(ApiError) as exc:
        auth_service.verify_signature(
            session, "evm", wallet.address, issued.nonce, signature, settings
        )

    assert exc.value.status_code == 401


def test_signature_from_different_key_raises_401(session, settings, wallet):
    issued = auth_service.create_nonce(session, "evm", wallet.address, settings)
    attacker = Account.create()
    signature = sign(attacker, issued.message)

    with pytest.raises(ApiError) as exc:
        auth_service.verify_signature(
            session, "evm", wallet.address, issued.nonce, signature, settings
        )

    assert exc.value.status_code == 401


def test_failed_attempt_burns_nonce(session, settings, wallet):
    issued = auth_service.create_nonce(session, "evm", wallet.address, settings)
    bad = sign(Account.create(), issued.message)
    with pytest.raises(ApiError):
        auth_service.verify_signature(
            session, "evm", wallet.address, issued.nonce, bad, settings
        )

    good = sign(wallet, issued.message)
    with pytest.raises(ApiError) as exc:
        auth_service.verify_signature(
            session, "evm", wallet.address, issued.nonce, good, settings
        )

    assert exc.value.status_code == 401


def test_nonce_issued_for_other_address_raises_401(session, settings, wallet):
    attacker = Account.create()
    issued = auth_service.create_nonce(session, "evm", wallet.address, settings)
    signature = sign(attacker, issued.message)

    with pytest.raises(ApiError) as exc:
        auth_service.verify_signature(
            session, "evm", attacker.address, issued.nonce, signature, settings
        )

    assert exc.value.status_code == 401


def test_unknown_nonce_raises_401(session, settings, wallet):
    with pytest.raises(ApiError) as exc:
        auth_service.verify_signature(
            session, "evm", wallet.address, "deadbeef", "0x" + "00" * 65, settings
        )

    assert exc.value.status_code == 401


def test_malformed_signature_raises_401(session, settings, wallet):
    issued = auth_service.create_nonce(session, "evm", wallet.address, settings)

    with pytest.raises(ApiError) as exc:
        auth_service.verify_signature(
            session, "evm", wallet.address, issued.nonce, "0xnothex", settings
        )

    assert exc.value.status_code == 401


@pytest.mark.parametrize("step", ["nonce", "verify"])
def test_solana_sign_in_returns_501(session, settings, step):
    address = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
    with pytest.raises(ApiError) as exc:
        if step == "nonce":
            auth_service.create_nonce(session, "solana", address, settings)
        else:
            auth_service.verify_signature(
                session, "solana", address, "abc", "sig", settings
            )

    assert exc.value.status_code == 501


def test_create_nonce_prunes_long_expired_nonces(
    session, settings, wallet, monkeypatch
):
    old = auth_service.create_nonce(session, "evm", wallet.address, settings)
    later = datetime.now(timezone.utc) + timedelta(days=2)
    monkeypatch.setattr(auth_service, "_utcnow", lambda: later)

    auth_service.create_nonce(session, "evm", wallet.address, settings)

    remaining = session.exec(select(AuthNonce.nonce)).all()
    assert old.nonce not in remaining
    assert len(remaining) == 1


@pytest.mark.parametrize("secret", [None, "too-short"])
def test_missing_or_weak_jwt_secret_fails_closed(session, wallet, secret):
    good_settings = make_settings()
    issued, signature = _sign_in(session, good_settings, wallet)
    settings = make_settings(AUTH_JWT_SECRET=secret)

    with pytest.raises(ApiError) as nonce_exc:
        auth_service.create_nonce(session, "evm", wallet.address, settings)
    with pytest.raises(ApiError) as verify_exc:
        auth_service.verify_signature(
            session, "evm", wallet.address, issued.nonce, signature, settings
        )

    assert nonce_exc.value.status_code == 503
    assert verify_exc.value.status_code == 503
