"""Async rate limiting for API calls.

This module provides a thread-safe, async rate limiter using a sliding window
algorithm. It ensures that no more than a specified number of requests are
made within a given time window.

Example:
    >>> limiter = RateLimiter(
    ...     max_requests=60, window_seconds=60
    ... )  # 60 requests per minute
    >>> async def make_api_call():
    ...     await limiter.acquire()
    ...     # Make your API call here
    ...     response = await client.get("/api/endpoint")
    ...     return response

The rate limiter is particularly useful for:
- Respecting API rate limits
- Preventing server overload
- Implementing fair usage policies
- Testing rate-limited scenarios
"""

import asyncio
import time


class RateLimiter:
    """Async rate limiter using sliding window algorithm.

    This rate limiter implements a sliding window algorithm that tracks
    the exact timestamp of each request. It ensures that at any point in
    time, no more than `max_requests` have been made in the past
    `window_seconds`.

    Features:
        - Thread-safe using asyncio locks
        - Accurate sliding window implementation
        - Automatic cleanup of old request timestamps
        - Memory-efficient with bounded history
        - Zero CPU usage while waiting

    Args:
        max_requests: Maximum number of requests allowed in the window
        window_seconds: Size of the sliding window in seconds

    Example:
        >>> # Create a rate limiter for 10 requests per second
        >>> limiter = RateLimiter(max_requests=10, window_seconds=1)
        >>>
        >>> # Use in an async function
        >>> async def rate_limited_operation():
        ...     await limiter.acquire()
        ...     # Perform operation here
        ...     return "Success"
        >>>
        >>> # The limiter will automatically delay if needed
        >>> async def bulk_operations():
        ...     tasks = [rate_limited_operation() for _ in range(50)]
        ...     results = await asyncio.gather(*tasks)
        ...     # This will take ~5 seconds (50 requests / 10 per second)
    """

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

        # Sort the requests to ensure we're using the oldest first
        self.requests.sort()

        if len(self.requests) >= self.max_requests:
            # Calculate wait time based on the oldest request that would make room for a new one
            # Oldest request would be at index: len(self.requests) - self.max_requests
            if len(self.requests) > self.max_requests:
                oldest_relevant = self.requests[len(self.requests) - self.max_requests]
            else:
                oldest_relevant = self.requests[0]

            wait_time = (oldest_relevant + self.window_seconds) - now
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

            # Ensure we don't keep more requests than needed
            if len(self.requests) > self.max_requests * 2:
                self.requests = self.requests[-self.max_requests :]
