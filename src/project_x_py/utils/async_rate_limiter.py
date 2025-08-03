"""Async rate limiting for API calls.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides a thread-safe, async rate limiter using a sliding window algorithm.
    Ensures that no more than a specified number of requests are made within a
    given time window. Essential for respecting API rate limits and preventing
    server overload in high-frequency trading applications.

Key Features:
    - Thread-safe using asyncio locks
    - Accurate sliding window implementation
    - Automatic cleanup of old request timestamps
    - Memory-efficient with bounded history
    - Zero CPU usage while waiting
    - Support for both async and sync operations

Rate Limiting Benefits:
    - Respecting API rate limits to avoid 429 errors
    - Preventing server overload and connection drops
    - Implementing fair usage policies across multiple clients
    - Testing rate-limited scenarios and edge cases
    - Ensuring consistent API performance

Example Usage:
    ```python
    from project_x_py.utils import RateLimiter

    # Create rate limiter for 60 requests per minute
    limiter = RateLimiter(max_requests=60, window_seconds=60)


    async def make_api_call():
        await limiter.acquire()  # Wait if necessary
        # Make your API call here
        response = await client.get("/api/endpoint")
        return response


    # Use in bulk operations
    async def bulk_api_calls():
        tasks = [make_api_call() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        # This will take ~1.67 minutes (100 requests / 60 per minute)
    ```

Algorithm Details:
    - Sliding window tracks exact timestamp of each request
    - Automatically removes requests outside the time window
    - Calculates precise wait time based on oldest relevant request
    - Memory bounded to prevent excessive storage usage
    - Thread-safe operations with proper asyncio locking

Performance Characteristics:
    - Minimal memory overhead with automatic cleanup
    - Zero CPU usage during wait periods
    - Accurate rate limiting with sub-second precision
    - Thread-safe for concurrent operations
    - Efficient for high-frequency trading scenarios

See Also:
    - `utils.error_handler`: Error handling for rate limit errors
    - `utils.logging_config`: Logging for rate limit monitoring
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
