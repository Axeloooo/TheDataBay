"""
In-memory sliding-window rate limiter for FastAPI endpoints.
"""

from collections import defaultdict, deque
import time

from fastapi import HTTPException, Request


class RateLimiter:
    """Sliding-window in-memory rate limiter keyed by client IP.

    Args:
        max_calls: Maximum number of calls allowed within the time window
        period: Length of the sliding window in seconds
    """

    def __init__(self, max_calls: int = 60, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self._calls: defaultdict[str, deque] = defaultdict(deque)

    def __call__(self, request: Request) -> None:
        """Check and record a request against the rate limit.

        Args:
            request: Incoming FastAPI Request object

        Raises:
            HTTPException: 429 if the rate limit has been exceeded
        """
        key = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._calls[key]

        # Remove timestamps outside the current sliding window
        while window and window[0] < now - self.period:
            window.popleft()

        if len(window) >= self.max_calls:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        window.append(now)


agent_write_rate_limiter = RateLimiter(max_calls=60, period=60.0)
