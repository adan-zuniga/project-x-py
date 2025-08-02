"""Rate limiting utility for API calls."""

import time
from typing import Any


class RateLimiter:
    """
    Simple rate limiter for API calls.

    Example:
        >>> limiter = RateLimiter(requests_per_minute=60)
        >>> with limiter:
        ...     # Make API call
        ...     response = api_call()
    """

    def __init__(self, requests_per_minute: int = 60):
        """Initialize rate limiter."""
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0.0

    def __enter__(self) -> "RateLimiter":
        """Context manager entry - enforce rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""

    def wait_if_needed(self) -> None:
        """Wait if needed to respect rate limit."""
        with self:
            pass
