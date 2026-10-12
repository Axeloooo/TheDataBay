"""Rate limits for the wallet sign-in endpoints.

Each endpoint is limited twice: per client IP (stops one host flooding) and per
(client IP, wallet address) pair (stops one host hammering one wallet). The
address bucket is deliberately scoped to the IP: an address-only bucket would let
anyone lock a public wallet address out of sign-in. Rows created from many IPs
are bounded separately by MAX_OUTSTANDING_NONCES per address. Limits live in
process memory, so they apply per API replica.
"""

from fastapi import Request

from ..config.settings import Settings
from ..shared.errors import ApiError
from ..shared.rate_limiter import RateLimiter
from .service import normalize_evm_address

PERIOD_SECONDS = 60.0

# Limits are re-read from settings on every call (see ``_sync``).
_nonce_ip = RateLimiter(period=PERIOD_SECONDS)
_nonce_address = RateLimiter(period=PERIOD_SECONDS)
_verify_ip = RateLimiter(period=PERIOD_SECONDS)
_verify_address = RateLimiter(period=PERIOD_SECONDS)


def client_ip(request: Request, settings: Settings) -> str:
    """Best-effort client IP.

    X-Forwarded-For is only read when AUTH_TRUSTED_PROXY_HOPS > 0. With
    ingress-nginx defaults the header is overwritten with the real client IP
    (a single entry) and the value is 1. The Nth entry from the right is used
    because entries further left may be client-supplied. Change the value if
    ingress-nginx use-forwarded-headers or compute-full-forwarded-for is enabled,
    or if Front Door / Application Gateway is placed in front.
    """
    hops = settings.auth_trusted_proxy_hops
    if hops > 0:
        forwarded = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
    return request.client.host if request.client else "unknown"


def _address_key(ip: str, address: str) -> str:
    try:
        normalized = normalize_evm_address(address)
    except ApiError:
        # Not an EVM address (the service rejects it later); still bucket it.
        normalized = address.strip().lower()
    return f"{ip}|{normalized}"


def _sync(limiter: RateLimiter, max_calls: int) -> RateLimiter:
    limiter.max_calls = max_calls
    return limiter


def limit_nonce(request: Request, settings: Settings, address: str) -> None:
    """Raise 429 when /auth/nonce is called too often by this IP or for this address."""
    ip = client_ip(request, settings)
    _sync(_nonce_ip, settings.auth_nonce_rate_limit_per_minute).hit(ip)
    _sync(_nonce_address, settings.auth_nonce_address_rate_limit_per_minute).hit(
        _address_key(ip, address)
    )


def limit_verify(request: Request, settings: Settings, address: str) -> None:
    """Raise 429 when /auth/verify is called too often by this IP or for this address."""
    ip = client_ip(request, settings)
    _sync(_verify_ip, settings.auth_verify_rate_limit_per_minute).hit(ip)
    _sync(_verify_address, settings.auth_verify_address_rate_limit_per_minute).hit(
        _address_key(ip, address)
    )


def reset_all() -> None:
    """Clear every sign-in limiter (used by tests)."""
    for limiter in (_nonce_ip, _nonce_address, _verify_ip, _verify_address):
        limiter.reset()
