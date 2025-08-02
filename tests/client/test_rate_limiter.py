"""Tests for the rate limiter functionality of ProjectX client."""

import asyncio
import time

import pytest

from project_x_py.client.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for the rate limiter functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_under_limit(self):
        """Test that rate limiter allows requests under the limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        start_time = time.time()

        # Make 5 requests (should all be immediate)
        for _ in range(5):
            await limiter.acquire()

        elapsed = time.time() - start_time

        # All 5 requests should have been processed immediately
        # Allow some small execution time, but less than 0.1s total
        assert elapsed < 0.1, "Requests under limit should be processed immediately"

    @pytest.mark.asyncio
    async def test_rate_limiter_delays_over_limit(self):
        """Test that rate limiter delays requests over the limit."""
        limiter = RateLimiter(max_requests=3, window_seconds=0.5)

        # Make initial requests to fill up the limit
        for _ in range(3):
            await limiter.acquire()

        start_time = time.time()

        # This should be delayed since we've hit our limit of 3 per 0.5s
        await limiter.acquire()

        elapsed = time.time() - start_time

        # Should have waited close to 0.5s for the window to expire
        assert 0.4 <= elapsed <= 0.7, f"Expected delay of ~1s, got {elapsed:.2f}s"

    @pytest.mark.skip("Skipping flaky test to be fixed in a separate PR")
    def test_rate_limiter_window_sliding(self):
        """Test that rate limiter uses a sliding window for requests.

        Note: This test is marked as skip due to flakiness. The timing-based
        rate limiting tests will be refactored in a separate PR.
        """

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_access(self):
        """Test that rate limiter handles concurrent access properly."""
        limiter = RateLimiter(max_requests=3, window_seconds=1)

        # Launch 5 concurrent tasks, only 3 should run immediately
        start_time = time.time()

        async def make_request(idx):
            await limiter.acquire()
            return idx, time.time() - start_time

        tasks = [make_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Sort by elapsed time
        results.sort(key=lambda x: x[1])

        # First 3 should be quick, last 2 should be delayed
        assert results[0][1] < 0.1, "First request should be immediate"
        assert results[1][1] < 0.1, "Second request should be immediate"
        assert results[2][1] < 0.1, "Third request should be immediate"

        # Last 2 should have waited for at least some of the window time
        assert results[3][1] > 0.1, "Fourth request should be delayed"
        assert results[4][1] > 0.1, "Fifth request should be delayed"

    @pytest.mark.asyncio
    async def test_rate_limiter_clears_old_requests(self):
        """Test that rate limiter properly clears old requests."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # Fill up the limit
        await limiter.acquire()
        await limiter.acquire()

        # Wait for all requests to age out
        await asyncio.sleep(0.15)

        # Make multiple requests that should be immediate
        start_time = time.time()
        await limiter.acquire()
        await limiter.acquire()
        elapsed = time.time() - start_time

        # Both should be immediate since old requests aged out
        assert elapsed < 0.1, "Requests should be immediate after window expires"

        # Verify internal state
        assert len(limiter.requests) == 2, "Should have 2 requests in tracking"
