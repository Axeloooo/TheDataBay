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
        audience=auth_service.token_audience(settings, "user"),
        issuer=auth_service.TOKEN_ISSUER,
    )
    assert claims["sub"] == wallet.address
    assert claims["wallet_type"] == "evm"
    assert claims["scope"] == "user"
    assert settings.auth_domain in claims["aud"]
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


def test_user_nonce_message_does_not_mention_admin(session, settings, wallet):
    issued = auth_service.create_nonce(session, "evm", wallet.address, settings)

    assert "admin" not in issued.message.lower()


def test_admin_nonce_message_states_administrative_contract_actions(
    session, settings, wallet
):
    issued = auth_service.create_nonce(
        session, "evm", wallet.address, settings, scope="admin"
    )

    message = issued.message.lower()
    assert "administrative" in message
    for action in ("fee", "access", "price", "url"):
        assert action in message
    assert wallet.address in issued.message
    assert f"Nonce: {issued.nonce}" in issued.message


def test_admin_sign_in_issues_short_lived_admin_token(session, settings, wallet):
    issued = auth_service.create_nonce(
        session, "evm", wallet.address, settings, scope="admin"
    )

    result = auth_service.verify_signature(
        session,
        "evm",
        wallet.address,
        issued.nonce,
        sign(wallet, issued.message),
        settings,
        scope="admin",
    )

    claims = jwt.decode(
        result.access_token,
        TEST_JWT_SECRET,
        algorithms=["HS256"],
        audience=auth_service.token_audience(settings, "admin"),
        issuer=auth_service.TOKEN_ISSUER,
    )
    assert claims["scope"] == "admin"
    assert claims["exp"] - claims["iat"] == 300
    assert result.scope.value == "admin"
    assert auth_service.token_audience(settings, "admin") != (
        auth_service.token_audience(settings, "user")
    )


@pytest.mark.parametrize(
    ("nonce_scope", "verify_scope"), [("user", "admin"), ("admin", "user")]
)
def test_verify_with_scope_other_than_nonce_scope_raises_401(
    session, settings, wallet, nonce_scope, verify_scope
):
    issued = auth_service.create_nonce(
        session, "evm", wallet.address, settings, scope=nonce_scope
    )

    with pytest.raises(ApiError) as exc:
        auth_service.verify_signature(
            session,
            "evm",
            wallet.address,
            issued.nonce,
            sign(wallet, issued.message),
            settings,
            scope=verify_scope,
        )

    assert exc.value.status_code == 401


def test_token_audience_is_bound_to_auth_domain():
    staging = make_settings(AUTH_DOMAIN="staging.thedatabay.com")
    production = make_settings(AUTH_DOMAIN="thedatabay.com")

    for scope in ("user", "admin"):
        assert auth_service.token_audience(staging, scope) != (
            auth_service.token_audience(production, scope)
        )


def test_outstanding_nonces_are_capped_per_address(session, settings, wallet):
    issued = [
        auth_service.create_nonce(session, "evm", wallet.address, settings)
        for _ in range(auth_service.MAX_OUTSTANDING_NONCES + 2)
    ]

    rows = session.exec(
        select(AuthNonce).where(AuthNonce.address == wallet.address)
    ).all()
    assert len(rows) == auth_service.MAX_OUTSTANDING_NONCES
    kept = {row.nonce for row in rows}
    assert kept == {n.nonce for n in issued[-auth_service.MAX_OUTSTANDING_NONCES :]}

    oldest = issued[0]
    with pytest.raises(ApiError) as exc:
        auth_service.verify_signature(
            session, "evm", wallet.address, oldest.nonce,
            sign(wallet, oldest.message), settings,
        )
    assert exc.value.status_code == 401


def test_nonce_cap_is_per_address(session, settings, wallet):
    other = Account.create()
    for _ in range(auth_service.MAX_OUTSTANDING_NONCES):
        auth_service.create_nonce(session, "evm", other.address, settings)

    mine = auth_service.create_nonce(session, "evm", wallet.address, settings)

    result = auth_service.verify_signature(
        session, "evm", wallet.address, mine.nonce, sign(wallet, mine.message), settings
    )
    assert result.address == wallet.address
    assert len(session.exec(select(AuthNonce)).all()) == (
        auth_service.MAX_OUTSTANDING_NONCES + 1
    )


def test_prune_keeps_recently_expired_and_is_bounded(
    session, settings, wallet, monkeypatch
):
    old = [
        auth_service.create_nonce(session, "evm", Account.create().address, settings)
        for _ in range(3)
    ]
    monkeypatch.setattr(auth_service, "PRUNE_BATCH_SIZE", 2)
    past_grace = datetime.now(timezone.utc) + timedelta(
        seconds=settings.auth_nonce_ttl_seconds
    ) + auth_service.NONCE_RETENTION + timedelta(seconds=1)
    monkeypatch.setattr(auth_service, "_utcnow", lambda: past_grace)

    auth_service.create_nonce(session, "evm", wallet.address, settings)

    remaining = set(session.exec(select(AuthNonce.nonce)).all())
    assert len(remaining & {n.nonce for n in old}) == 1
    assert auth_service.NONCE_RETENTION <= timedelta(minutes=15)


def test_expires_at_is_indexed():
    indexed = {
        tuple(col.name for col in index.columns)
        for index in AuthNonce.__table__.indexes
    }
    assert ("expires_at",) in indexed


def test_same_evm_address_ignores_case():
    address = Account.create().address

    assert auth_service.same_evm_address(address, address.lower())
    assert auth_service.same_evm_address(address.lower(), address)
    assert auth_service.same_evm_address("0x" + address[2:].upper(), address)


@pytest.mark.parametrize(
    "a, b",
    [
        (
            "0x0000000000000000000000000000000000000001",
            "0x0000000000000000000000000000000000000002",
        ),
        ("not-an-address", "not-an-address"),
        ("", ""),
        (None, None),
        ("0x0000000000000000000000000000000000000001", None),
    ],
)
def test_same_evm_address_rejects_mismatch_and_invalid(a, b):
    assert not auth_service.same_evm_address(a, b)
