"""Rate limiting for API calls."""

import asyncio
import time


class RateLimiter:
    """Simple async rate limiter using sliding window."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: list[float] = []
        self._lock = asyncio.Lock()

    def _calculate_delay(self) -> float:
        """Calculate the delay needed to stay within rate limits.

        Returns:
            float: Time to wait in seconds, or 0 if no wait is needed
        """
        now = time.time()
        # Remove old requests outside the window
        self.requests = [t for t in self.requests if t > now - self.window_seconds]

        if len(self.requests) >= self.max_requests:
            # Calculate wait time
            oldest_request = self.requests[0]
            wait_time = (oldest_request + self.window_seconds) - now
            return max(0.0, wait_time)

        return 0.0

    async def acquire(self) -> None:
        """Wait if necessary to stay within rate limits."""
        async with self._lock:
            # Calculate any needed delay
            wait_time = self._calculate_delay()

            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # Clean up again after waiting
                now = time.time()
                self.requests = [
                    t for t in self.requests if t > now - self.window_seconds
                ]
            else:
                now = time.time()

            # Record this request
            self.requests.append(now)
