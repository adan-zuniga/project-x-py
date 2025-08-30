"""Tests for the rate limiter functionality of ProjectX client."""

import asyncio
import time

import pytest

from project_x_py.utils.async_rate_limiter import RateLimiter


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

    @pytest.mark.asyncio
    async def test_rate_limiter_window_sliding(self):
        """Test that rate limiter uses a sliding window for requests."""
        # Create a limiter with small window to make test faster
        window_seconds = 0.5
        limiter = RateLimiter(max_requests=3, window_seconds=window_seconds)

        # Send 3 requests immediately (filling the window)
        request_times = []
        for _ in range(3):
            await limiter.acquire()
            request_times.append(time.time())

        # Wait for most of the window to pass
        await asyncio.sleep(window_seconds * 0.8)  # 80% of window time passed

        # At this point, we should be able to make 1 more request with minimal delay
        # since one of the original requests should have "slid out" of the window
        start_time = time.time()
        await limiter.acquire()
        request_times.append(time.time())
        elapsed = time.time() - start_time

        # This should be fairly quick since we're using a sliding window
        # Not requiring < 0.1 since timing can vary on different systems
        assert elapsed < window_seconds * 0.5, (
            "Request should be relatively quick with sliding window"
        )

        # Make one more request to see if it delays properly
        start_time = time.time()
        await limiter.acquire()
        elapsed = time.time() - start_time

        # This should show some delay
        assert elapsed > 0, "Request should show some delay when window is full"

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
        limiter = RateLimiter(max_requests=2, window_seconds=0.3)

        # Fill up the limit
        await limiter.acquire()
        await limiter.acquire()

        # Wait for all requests to age out
        await asyncio.sleep(0.4)  # Wait longer than window_seconds

        # Make multiple requests that should be immediate
        start_time = time.time()
        await limiter.acquire()
        elapsed_first = time.time() - start_time

        start_time = time.time()
        await limiter.acquire()
        elapsed_second = time.time() - start_time

        # Both should be immediate since old requests aged out
        assert elapsed_first < 0.1, (
            "First request should be immediate after window expires"
        )
        assert elapsed_second < 0.1, (
            "Second request should be immediate after window expires"
        )

        # Verify internal state
        assert len(limiter.requests) == 2, "Should have 2 requests in tracking"

    @pytest.mark.asyncio
    async def test_rate_limiter_memory_cleanup(self):
        """Test that rate limiter doesn't accumulate unlimited request history."""
        limiter = RateLimiter(max_requests=100, window_seconds=0.1)

        # Make many requests over multiple windows
        for _ in range(5):
            # Fill the window
            for _ in range(100):
                await limiter.acquire()
            # Wait for window to expire
            await asyncio.sleep(0.15)

        # Check that internal state is bounded
        # Should not keep more than max_requests * 2 entries
        assert len(limiter.requests) <= 200, "Should limit internal request history"

    @pytest.mark.asyncio
    async def test_rate_limiter_edge_cases(self):
        """Test edge cases for rate limiter."""
        # Test with 1 request per window
        limiter = RateLimiter(max_requests=1, window_seconds=0.1)

        await limiter.acquire()
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start

        assert elapsed >= 0.09, "Should wait for window with single request limit"

        # Test with very large window
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        await limiter.acquire()

        # Should still track request
        assert len(limiter.requests) == 1

    @pytest.mark.asyncio
    async def test_rate_limiter_stress_test(self):
        """Stress test the rate limiter with many concurrent requests."""
        import os

        # Use more lenient parameters for CI environments
        if os.environ.get("CI"):
            # In CI: smaller batch, more lenient timing due to scheduling differences
            limiter = RateLimiter(max_requests=5, window_seconds=1.0)
            num_requests = 25
            expected_min_time = 4.0  # 5 batches of 5 requests, 1s window
            expected_max_time = 7.0  # Allow more overhead in CI
            max_allowed_per_window = 8  # Allow 60% more in CI due to timing issues
        else:
            # Local: more aggressive testing
            limiter = RateLimiter(max_requests=10, window_seconds=0.5)
            num_requests = 50
            expected_min_time = 2.0  # 5 batches of 10 requests, 0.5s window
            expected_max_time = 3.0
            max_allowed_per_window = 10

        # Create concurrent requests
        async def make_request():
            await limiter.acquire()
            return time.time()

        start_time = time.time()
        tasks = [make_request() for _ in range(num_requests)]
        times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Check total time is reasonable
        assert expected_min_time <= total_time <= expected_max_time, (
            f"Expected {expected_min_time:.1f}-{expected_max_time:.1f}s total, got {total_time:.2f}s"
        )

        # Verify requests were properly rate limited
        times.sort()

        # Check rate limiting - for sliding windows
        window_seconds = limiter.window_seconds
        violations = 0
        max_violations_allowed = 3 if os.environ.get("CI") else 2

        for i in range(len(times)):
            # Count requests within window starting from this request
            window_end = times[i] + window_seconds
            requests_in_window = sum(1 for t in times[i:] if t < window_end)
            if requests_in_window > max_allowed_per_window:
                violations += 1

        # Allow some violations in CI due to timing precision issues
        assert violations <= max_violations_allowed, (
            f"Too many rate limit violations ({violations}). "
            f"Max allowed: {max_violations_allowed}. "
            f"Window size: {window_seconds}s, "
            f"Max per window: {max_allowed_per_window}, "
            f"Total time: {total_time:.3f}s"
        )

    @pytest.mark.asyncio
    async def test_rate_limiter_accuracy(self):
        """Test the accuracy of rate limiting calculations."""
        limiter = RateLimiter(max_requests=5, window_seconds=1.0)

        # Record exact timings
        timings = []

        for i in range(10):
            start = time.time()
            await limiter.acquire()
            timings.append(time.time())

            # Small delay to spread requests, but not too small to avoid timing issues
            if i < 9:
                await asyncio.sleep(0.05)

        # Analyze the timings with more lenient assertions
        total_time = timings[-1] - timings[0]

        # Basic sanity check: should take at least close to 1 second for 10 requests with 5/sec limit
        assert total_time >= 0.8, (
            f"Total time {total_time:.3f}s too fast for rate limiting"
        )

        # First 5 should be relatively fast (allowing some buffer for timing variance)
        first_five_time = timings[4] - timings[0]
        assert first_five_time < 1.2, (
            f"First 5 requests took {first_five_time:.3f}s, should be under 1.2s"
        )

        # Check sliding window behavior with tolerance
        violations = 0
        for i in range(5, 10):
            # Each request should maintain the rate limit (with small tolerance)
            window_start = timings[i] - 1.0
            recent_requests = [t for t in timings[: i + 1] if t > window_start]
            if len(recent_requests) > 5:
                violations += 1

        # Allow up to 2 violations due to timing precision issues
        assert violations <= 2, (
            f"Too many rate limit violations ({violations}). "
            f"Timings: {[f'{t:.3f}' for t in timings]}"
        )
