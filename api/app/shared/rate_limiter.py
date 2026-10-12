"""
In-memory sliding-window rate limiter for FastAPI endpoints.
"""

from collections import defaultdict, deque
import math
import threading
import time

from fastapi import HTTPException, Request


class RateLimiter:
    """Sliding-window in-memory rate limiter keyed by client IP.

    Args:
        max_calls: Maximum number of calls allowed within the time window
        period: Length of the sliding window in seconds
    """

    MAX_TRACKED_KEYS = 10_000

    def __init__(self, max_calls: int = 60, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self._calls: defaultdict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_eviction = 0.0

    def __call__(self, request: Request) -> None:
        """Check and record a request against the rate limit.

        Args:
            request: Incoming FastAPI Request object

        Raises:
            HTTPException: 429 if the rate limit has been exceeded
        """
        key = request.client.host if request.client else "unknown"
        self.hit(key)

    def hit(self, key: str) -> None:
        """Record one call for ``key`` or raise 429 with a Retry-After header.

        Thread-safe: sync FastAPI routes run in a threadpool.
        """
        with self._lock:
            now = time.time()
            if (
                len(self._calls) > self.MAX_TRACKED_KEYS
                and now - self._last_eviction >= self.period
            ):
                self._evict_idle(now)

            window = self._calls[key]

            # Remove timestamps outside the current sliding window
            while window and window[0] <= now - self.period:
                window.popleft()

            if len(window) >= self.max_calls:
                retry_after = max(1, math.ceil(window[0] + self.period - now))
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)},
                )

            window.append(now)

    def reset(self) -> None:
        """Forget all recorded calls."""
        with self._lock:
            self._calls.clear()
            self._last_eviction = 0.0

    def _evict_idle(self, now: float) -> None:
        """Drop keys whose whole window has expired (caller holds the lock).

        Runs at most once per period, so a full table does not cost O(n) per request.
        """
        self._last_eviction = now
        for key in [
            k for k, w in self._calls.items() if not w or w[-1] <= now - self.period
        ]:
            del self._calls[key]


agent_write_rate_limiter = RateLimiter(max_calls=60, period=60.0)
