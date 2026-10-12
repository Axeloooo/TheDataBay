from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.shared.rate_limiter import RateLimiter


def test_rate_limiter_enforces_call_limit(monkeypatch):
    limiter = RateLimiter(max_calls=2, period=10.0)
    request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.10"))
    times = iter([100.0, 101.0, 102.0])
    monkeypatch.setattr("app.shared.rate_limiter.time.time", lambda: next(times))

    limiter(request)
    limiter(request)

    with pytest.raises(HTTPException, match="Rate limit exceeded"):
        limiter(request)


def test_rate_limiter_allows_request_after_period_expires(monkeypatch):
    limiter = RateLimiter(max_calls=1, period=5.0)
    request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.10"))
    times = iter([100.0, 106.0])
    monkeypatch.setattr("app.shared.rate_limiter.time.time", lambda: next(times))

    limiter(request)
    limiter(request)  # second call is allowed because the first expired after 6s


def test_rate_limiter_uses_fallback_ip_when_client_is_none(monkeypatch):
    limiter = RateLimiter(max_calls=2, period=10.0)
    request = SimpleNamespace(client=None)
    times = iter([100.0, 101.0])
    monkeypatch.setattr("app.shared.rate_limiter.time.time", lambda: next(times))

    limiter(request)
    limiter(request)  # should not raise; unknown client is tracked under fallback key


def test_rate_limiter_is_thread_safe_and_does_not_overshoot(monkeypatch):
    import threading

    limiter = RateLimiter(max_calls=50, period=60.0)
    limiter.MAX_TRACKED_KEYS = 5  # force eviction paths
    monkeypatch.setattr("app.shared.rate_limiter.time.time", lambda: 1000.0)
    allowed = []
    errors = []

    def worker(n):
        try:
            for i in range(200):
                try:
                    limiter.hit(f"other-{n}-{i}")  # churn many keys
                except HTTPException:
                    pass
                try:
                    limiter.hit("shared")
                    allowed.append(1)
                except HTTPException:
                    pass
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(allowed) == 50


def test_rate_limiter_evicts_idle_keys_at_most_once_per_period(monkeypatch):
    limiter = RateLimiter(max_calls=1, period=10.0)
    limiter.MAX_TRACKED_KEYS = 2
    now = {"t": 100.0}
    monkeypatch.setattr("app.shared.rate_limiter.time.time", lambda: now["t"])
    for i in range(5):
        limiter.hit(f"k{i}")
    now["t"] = 111.0
    limiter.hit("fresh")  # eviction runs: all old keys expired
    assert list(limiter._calls) == ["fresh"]
