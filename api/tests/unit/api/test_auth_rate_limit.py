from eth_account import Account
import pytest
from sqlmodel import select

from app.auth import rate_limit
from app.auth import service as auth_service
from app.auth.models import AuthNonce

NONCE = "/api/v1/auth/nonce"
VERIFY = "/api/v1/auth/verify"


def _nonce(client, address=None, **kwargs):
    address = address or Account.create().address
    return client.post(NONCE, json={"wallet_type": "evm", "address": address}, **kwargs)


def _verify(client, address):
    return client.post(
        VERIFY,
        json={
            "wallet_type": "evm",
            "address": address,
            "nonce": "0" * 32,
            "signature": "0x" + "00" * 65,
        },
    )


@pytest.fixture
def clock(monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr("app.shared.rate_limiter.time.time", lambda: now["t"])
    return now


def test_nonce_per_ip_limit_returns_429_with_retry_after(client_factory, clock):
    with client_factory(AUTH_NONCE_RATE_LIMIT_PER_MINUTE=3) as client:
        for _ in range(3):
            assert _nonce(client).status_code == 200

        blocked = _nonce(client)

    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"


def test_nonce_limit_resets_after_window(client_factory, clock):
    with client_factory(AUTH_NONCE_RATE_LIMIT_PER_MINUTE=2) as client:
        assert _nonce(client).status_code == 200
        clock["t"] += 10
        assert _nonce(client).status_code == 200
        assert _nonce(client).status_code == 429

        clock["t"] += 50  # first call is now 60s old
        assert _nonce(client).status_code == 200
        blocked = _nonce(client)

    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "10"


def test_one_ip_cannot_exhaust_another_ips_bucket_for_same_address(
    client_factory, clock
):
    address = Account.create().address
    with client_factory(
        AUTH_NONCE_RATE_LIMIT_PER_MINUTE=100,
        AUTH_NONCE_ADDRESS_RATE_LIMIT_PER_MINUTE=1,
        AUTH_TRUSTED_PROXY_HOPS=1,
    ) as client:
        attacker = {"X-Forwarded-For": "6.6.6.6"}
        victim = {"X-Forwarded-For": "7.7.7.7"}
        assert _nonce(client, address, headers=attacker).status_code == 200
        assert _nonce(client, address, headers=attacker).status_code == 429
        assert _nonce(client, address, headers=victim).status_code == 200


def test_nonce_per_address_limit_is_independent_of_other_addresses(
    client_factory, clock
):
    address = Account.create().address
    with client_factory(
        AUTH_NONCE_RATE_LIMIT_PER_MINUTE=100,
        AUTH_NONCE_ADDRESS_RATE_LIMIT_PER_MINUTE=2,
    ) as client:
        assert _nonce(client, address).status_code == 200
        assert _nonce(client, address).status_code == 200
        assert _nonce(client, address).status_code == 429
        # Same address in lower case is the same bucket.
        assert _nonce(client, address.lower()).status_code == 429
        assert _nonce(client).status_code == 200


def test_verify_limits_per_address(client_factory, clock):
    address = Account.create().address
    with client_factory(
        AUTH_VERIFY_RATE_LIMIT_PER_MINUTE=100,
        AUTH_VERIFY_ADDRESS_RATE_LIMIT_PER_MINUTE=2,
    ) as client:
        assert _verify(client, address).status_code == 401
        assert _verify(client, address).status_code == 401
        blocked = _verify(client, address)

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_verify_limits_per_ip(client_factory, clock):
    with client_factory(AUTH_VERIFY_RATE_LIMIT_PER_MINUTE=1) as client:
        assert _verify(client, Account.create().address).status_code == 401
        assert _verify(client, Account.create().address).status_code == 429


def test_forwarded_for_ignored_without_trusted_proxy(client_factory, clock):
    with client_factory(AUTH_NONCE_RATE_LIMIT_PER_MINUTE=1) as client:
        assert _nonce(client, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
        # Spoofing a different header value does not get a fresh bucket.
        assert _nonce(client, headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 429


def test_forwarded_for_uses_proxy_appended_entry_when_trusted(client_factory, clock):
    with client_factory(
        AUTH_NONCE_RATE_LIMIT_PER_MINUTE=1, AUTH_TRUSTED_PROXY_HOPS=1
    ) as client:
        # Left entries are client-supplied; only the proxy-appended last one counts.
        first = _nonce(client, headers={"X-Forwarded-For": "9.9.9.9, 10.0.0.1"})
        spoofed = _nonce(client, headers={"X-Forwarded-For": "8.8.8.8, 10.0.0.1"})
        other_client = _nonce(client, headers={"X-Forwarded-For": "9.9.9.9, 10.0.0.2"})

    assert first.status_code == 200
    assert spoofed.status_code == 429
    assert other_client.status_code == 200


def test_unused_nonces_per_address_stay_capped_across_requests(
    client_factory, db_session, clock
):
    address = Account.create().address
    with client_factory(
        AUTH_NONCE_RATE_LIMIT_PER_MINUTE=1000,
        AUTH_NONCE_ADDRESS_RATE_LIMIT_PER_MINUTE=1000,
    ) as client:
        for _ in range(auth_service.MAX_OUTSTANDING_NONCES + 4):
            assert _nonce(client, address).status_code == 200

    rows = db_session.exec(select(AuthNonce).where(AuthNonce.address == address)).all()
    assert len(rows) == auth_service.MAX_OUTSTANDING_NONCES


def test_reset_all_clears_limiters(client_factory, clock):
    with client_factory(AUTH_NONCE_RATE_LIMIT_PER_MINUTE=1) as client:
        assert _nonce(client).status_code == 200
        assert _nonce(client).status_code == 429
        rate_limit.reset_all()
        assert _nonce(client).status_code == 200
