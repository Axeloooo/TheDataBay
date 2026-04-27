from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.rate_limiter import RateLimiter


def test_rate_limiter_enforces_call_limit(monkeypatch):
    limiter = RateLimiter(max_calls=2, period=10.0)
    request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.10"))
    times = iter([100.0, 101.0, 102.0])
    monkeypatch.setattr("app.services.rate_limiter.time.time", lambda: next(times))

    limiter(request)
    limiter(request)

    with pytest.raises(HTTPException, match="Rate limit exceeded"):
        limiter(request)


def test_rate_limiter_allows_request_after_period_expires(monkeypatch):
    limiter = RateLimiter(max_calls=1, period=5.0)
    request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.10"))
    times = iter([100.0, 106.0])
    monkeypatch.setattr("app.services.rate_limiter.time.time", lambda: next(times))

    limiter(request)
    limiter(request)  # second call is allowed because the first expired after 6s


def test_rate_limiter_uses_fallback_ip_when_client_is_none(monkeypatch):
    limiter = RateLimiter(max_calls=2, period=10.0)
    request = SimpleNamespace(client=None)
    times = iter([100.0, 101.0])
    monkeypatch.setattr("app.services.rate_limiter.time.time", lambda: next(times))

    limiter(request)
    limiter(request)  # should not raise; unknown client is tracked under fallback key
