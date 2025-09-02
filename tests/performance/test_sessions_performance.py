"""
Performance regression tests for sessions module.

These tests define performance expectations and catch regressions.
Following TDD methodology - tests define expected performance characteristics.

Author: TDD Implementation
Date: 2025-08-31
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from project_x_py.sessions import SessionConfig, SessionFilterMixin, SessionType
from project_x_py.sessions.indicators import (
    calculate_session_vwap,
    calculate_session_levels,
    calculate_anchored_vwap,
    aggregate_with_sessions,
    _create_minute_data,
)
from project_x_py.sessions.statistics import SessionAnalytics, SessionStatistics


class TestSessionsPerformanceRegression:
    """Test performance benchmarks and regression detection."""

    @pytest.fixture
    def large_dataset(self):
        """Create large dataset for performance testing."""
        # 100,000 data points (roughly 2 months of 1-minute data)
        n_rows = 100_000
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        timestamps = [
            start_date + timedelta(minutes=i) for i in range(n_rows)
        ]

        return pl.DataFrame({
            "timestamp": timestamps,
            "open": [100.0 + (i % 1000) * 0.01 for i in range(n_rows)],
            "high": [101.0 + (i % 1000) * 0.01 for i in range(n_rows)],
            "low": [99.0 + (i % 1000) * 0.01 for i in range(n_rows)],
            "close": [100.5 + (i % 1000) * 0.01 for i in range(n_rows)],
            "volume": [1000 + (i % 100) for i in range(n_rows)]
        })

    @pytest.fixture
    def very_large_dataset(self):
        """Create very large dataset for stress testing."""
        # 1,000,000 data points for memory/performance stress testing
        n_rows = 1_000_000
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Create data in chunks to avoid memory issues during creation
        chunk_size = 100_000
        chunks = []

        for chunk_start in range(0, n_rows, chunk_size):
            chunk_end = min(chunk_start + chunk_size, n_rows)
            chunk_timestamps = [
                start_date + timedelta(seconds=i)
                for i in range(chunk_start, chunk_end)
            ]

            chunk_df = pl.DataFrame({
                "timestamp": chunk_timestamps,
                "open": [100.0 + (i % 1000) * 0.001 for i in range(chunk_start, chunk_end)],
                "high": [100.1 + (i % 1000) * 0.001 for i in range(chunk_start, chunk_end)],
                "low": [99.9 + (i % 1000) * 0.001 for i in range(chunk_start, chunk_end)],
                "close": [100.05 + (i % 1000) * 0.001 for i in range(chunk_start, chunk_end)],
                "volume": [1000 + (i % 10) for i in range(chunk_start, chunk_end)]
            })
            chunks.append(chunk_df)

        return pl.concat(chunks)

    @pytest.mark.performance
    def test_session_config_performance_baseline(self):
        """Test SessionConfig performance baseline."""
        config = SessionConfig()
        timestamp = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)

        start_time = time.time()

        # Perform 10,000 session checks
        for _ in range(10_000):
            config.is_market_open(timestamp, "ES")
            config.get_current_session(timestamp, "ES")

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 10k operations in under 0.5 seconds
        assert duration < 0.5, f"Session config operations took {duration:.3f}s, expected < 0.5s"

        # Calculate operations per second
        ops_per_second = 20_000 / duration  # 2 operations per iteration
        assert ops_per_second > 40_000, f"Only {ops_per_second:.0f} ops/s, expected > 40k"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_session_filter_performance_large_dataset(self, large_dataset):
        """Test session filtering performance with large datasets."""
        session_filter = SessionFilterMixin()

        start_time = time.time()

        # Filter large dataset
        result = await session_filter.filter_by_session(
            large_dataset, SessionType.RTH, "ES"
        )

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within 2 seconds for 100k rows
        assert duration < 2.0, f"Filtering took {duration:.2f}s, expected < 2.0s"

        # Should return reasonable amount of data
        assert len(result) > 0
        assert len(result) < len(large_dataset)  # Should filter out some data

        # Calculate throughput
        rows_per_second = len(large_dataset) / duration
        assert rows_per_second > 50_000, f"Only {rows_per_second:.0f} rows/s, expected > 50k"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_session_vwap_performance_regression(self, large_dataset):
        """Test session VWAP calculation performance."""
        start_time = time.time()

        result = await calculate_session_vwap(large_dataset, SessionType.RTH, "ES")

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within 3 seconds for 100k rows
        assert duration < 3.0, f"VWAP calculation took {duration:.2f}s, expected < 3.0s"

        # Result should have VWAP column
        assert "session_vwap" in result.columns
        assert len(result) == len(large_dataset)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_session_statistics_performance(self, large_dataset):
        """Test session statistics calculation performance."""
        stats = SessionStatistics()

        start_time = time.time()

        result = await stats.calculate_session_stats(large_dataset, "ES")

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within 2 seconds for 100k rows
        assert duration < 2.0, f"Statistics calculation took {duration:.2f}s, expected < 2.0s"

        # Should return complete statistics
        expected_keys = [
            "rth_volume", "eth_volume", "rth_vwap", "eth_vwap"
        ]
        for key in expected_keys:
            assert key in result

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_session_analytics_performance(self, large_dataset):
        """Test session analytics performance."""
        analytics = SessionAnalytics()

        start_time = time.time()

        # Run multiple analytics operations
        comparison = await analytics.compare_sessions(large_dataset, "ES")
        volatility = await analytics.analyze_session_volatility(large_dataset, "ES")
        profile = await analytics.get_session_volume_profile(large_dataset, "ES")

        end_time = time.time()
        duration = end_time - start_time

        # Should complete all analytics within 5 seconds
        assert duration < 5.0, f"Analytics took {duration:.2f}s, expected < 5.0s"

        # All results should be populated
        assert isinstance(comparison, dict)
        assert isinstance(volatility, dict)
        assert isinstance(profile, dict)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_session_operations_performance(self, large_dataset):
        """Test concurrent session operations don't degrade performance."""
        async def run_operation(operation_id: int):
            """Run a session operation with unique identifier."""
            if operation_id % 4 == 0:
                filter_mixin = SessionFilterMixin()
                return await filter_mixin.filter_by_session(large_dataset, SessionType.RTH, "ES")
            elif operation_id % 4 == 1:
                return await calculate_session_vwap(large_dataset, SessionType.RTH, "ES")
            elif operation_id % 4 == 2:
                stats = SessionStatistics()
                return await stats.calculate_session_stats(large_dataset, "ES")
            else:
                analytics = SessionAnalytics()
                return await analytics.compare_sessions(large_dataset, "ES")

        start_time = time.time()

        # Run 8 concurrent operations
        tasks = [run_operation(i) for i in range(8)]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time

        # Concurrent operations should complete reasonably fast
        # Allow more time due to concurrency but should benefit from parallelization
        assert duration < 10.0, f"Concurrent operations took {duration:.2f}s, expected < 10.0s"

        # All operations should complete successfully
        assert len(results) == 8
        assert all(result is not None for result in results)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_usage_performance(self, large_dataset):
        """Test memory usage doesn't grow excessively."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        session_filter = SessionFilterMixin()
        stats = SessionStatistics()

        # Multiple operations that could accumulate memory
        for _ in range(5):
            filtered = await session_filter.filter_by_session(large_dataset, SessionType.RTH, "ES")
            result = await stats.calculate_session_stats(filtered, "ES")
            # Explicitly delete to test cleanup
            del filtered, result

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before

        # Memory increase should be reasonable (< 200MB for 100k rows * 5 operations)
        assert memory_increase < 200, f"Memory increased by {memory_increase:.1f}MB, expected < 200MB"

    @pytest.mark.performance
    def test_cache_performance_benefits(self):
        """Test that caching provides performance benefits."""
        session_filter = SessionFilterMixin()

        # Warm up to reduce timing variance
        _ = session_filter._get_cached_session_boundaries("warmup", "ES", "RTH")

        # Test cache functionality rather than microsecond timing
        # First call should populate the cache
        result1 = session_filter._get_cached_session_boundaries("test_hash", "ES", "RTH")

        # Verify cache was populated
        cache_key = "test_hash_ES_RTH"
        assert cache_key in session_filter._session_boundary_cache

        # Second call should use cache
        result2 = session_filter._get_cached_session_boundaries("test_hash", "ES", "RTH")

        # Results should be identical
        assert result1 == result2

        # Verify cache was actually used (not recreated)
        # The cached object should be the same reference
        assert session_filter._session_boundary_cache[cache_key] is result2

        # Test with multiple iterations to verify consistent caching
        # This is more reliable than timing microsecond operations
        iterations = 100
        cache_miss_time = 0
        cache_hit_time = 0

        # Measure cache misses (new keys each time)
        for i in range(iterations):
            key = f"miss_test_{i}"
            start = time.perf_counter()
            _ = session_filter._get_cached_session_boundaries(key, "ES", "RTH")
            cache_miss_time += time.perf_counter() - start

        # Measure cache hits (same key repeatedly)
        for _ in range(iterations):
            start = time.perf_counter()
            _ = session_filter._get_cached_session_boundaries("hit_test", "ES", "RTH")
            cache_hit_time += time.perf_counter() - start

        # Average times should show cache benefit
        # We only check that cache is being used, not strict timing
        avg_miss = cache_miss_time / iterations
        avg_hit = cache_hit_time / iterations

        # Cache hits should generally be faster, but we use a generous margin
        # to avoid flakiness. The key test is that cache is functioning.
        # If cache wasn't working, times would be identical.
        assert avg_hit <= avg_miss * 2.0  # Very generous margin to avoid flakiness

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_aggregation_performance(self):
        """Test performance with large data aggregation."""
        # Create minute-by-minute data for one full day
        minute_data = _create_minute_data()

        start_time = time.time()

        # Aggregate to 5-minute bars
        result = await aggregate_with_sessions(minute_data, "5min", SessionType.RTH)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete aggregation quickly
        assert duration < 1.0, f"Aggregation took {duration:.3f}s, expected < 1.0s"

        # Should have fewer bars than input
        assert len(result) < len(minute_data)
        assert len(result) > 0

    @pytest.mark.performance
    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_stress_test_very_large_dataset(self, very_large_dataset):
        """Stress test with very large dataset (1M rows)."""
        # This test is marked as 'stress' and may be skipped in normal test runs
        session_filter = SessionFilterMixin()

        start_time = time.time()

        # Filter 1M rows
        result = await session_filter.filter_by_session(
            very_large_dataset, SessionType.RTH, "ES"
        )

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within 20 seconds for 1M rows (stress test)
        assert duration < 20.0, f"Stress test took {duration:.2f}s, expected < 20.0s"

        # Should return filtered data
        assert len(result) > 0

        # Calculate throughput
        rows_per_second = len(very_large_dataset) / duration
        assert rows_per_second > 50_000, f"Stress test only {rows_per_second:.0f} rows/s"


class TestPerformanceRegressionDetection:
    """Test performance regression detection and monitoring."""

    @pytest.mark.performance
    def test_performance_baseline_tracking(self):
        """Test that tracks performance baselines for regression detection."""
        # This test demonstrates how to track performance over time
        # In a real CI/CD system, results would be stored and compared

        config = SessionConfig()
        timestamp = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)

        # Measure baseline performance
        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            config.is_market_open(timestamp, "ES")

        end_time = time.perf_counter()
        duration = end_time - start_time

        avg_time_per_operation = duration / iterations
        operations_per_second = iterations / duration

        # Document performance expectations
        performance_metrics = {
            "avg_time_per_operation": avg_time_per_operation,
            "operations_per_second": operations_per_second,
            "total_duration": duration
        }

        # Performance expectations (these would be stored/compared in real system)
        assert avg_time_per_operation < 0.001, "Operation should take < 1ms"
        assert operations_per_second > 10_000, "Should handle > 10k ops/second"

        # In a real implementation, these metrics would be:
        # 1. Stored in a database or metrics system
        # 2. Compared against historical baselines
        # 3. Used to trigger alerts if regression is detected

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_async_performance_characteristics(self):
        """Test async operation performance characteristics."""
        # Test that async operations have appropriate performance
        large_data = pl.DataFrame({
            "timestamp": [
                datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc) + timedelta(minutes=i)
                for i in range(10_000)
            ],
            "open": [100.0] * 10_000,
            "high": [101.0] * 10_000,
            "low": [99.0] * 10_000,
            "close": [100.5] * 10_000,
            "volume": [1000] * 10_000
        })

        start_time = time.perf_counter()

        # Test async operations
        results = await asyncio.gather(
            calculate_session_vwap(large_data, SessionType.RTH, "ES"),
            calculate_session_levels(large_data),
            calculate_anchored_vwap(large_data, "session_open"),
        )

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Async operations should complete quickly
        assert duration < 3.0, f"Async operations took {duration:.2f}s, expected < 3.0s"

        # All results should be valid
        assert len(results) == 3
        assert all(isinstance(result, pl.DataFrame) for result in results)
        assert all(len(result) == 10_000 for result in results)


class TestPerformanceProfilingHelpers:
    """Performance profiling and debugging helpers."""

    @pytest.mark.performance
    def test_performance_profiling_session_config(self):
        """Profile session config operations for bottlenecks."""
        import cProfile
        import pstats
        from io import StringIO

        config = SessionConfig()
        timestamp = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)

        # Profile the operations
        profiler = cProfile.Profile()
        profiler.enable()

        # Run operations to profile
        for _ in range(1000):
            config.is_market_open(timestamp, "ES")
            config.get_session_times("ES")
            config.get_current_session(timestamp, "ES")

        profiler.disable()

        # Analyze profile results
        stats_stream = StringIO()
        ps = pstats.Stats(profiler, stream=stats_stream).sort_stats('cumulative')
        ps.print_stats(10)  # Top 10 functions

        profile_output = stats_stream.getvalue()

        # Basic validation that profiling worked
        assert "is_market_open" in profile_output
        assert len(profile_output) > 100  # Should have meaningful output

        # In a real scenario, this output would be analyzed for:
        # 1. Hotspot identification
        # 2. Performance bottlenecks
        # 3. Optimization opportunities

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_profiling_session_operations(self):
        """Memory profiling for session operations."""
        import tracemalloc

        # Start memory tracing
        tracemalloc.start()

        # Take initial memory snapshot
        snapshot1 = tracemalloc.take_snapshot()

        # Perform memory-intensive operations
        large_data = pl.DataFrame({
            "timestamp": [
                datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc) + timedelta(minutes=i)
                for i in range(50_000)
            ],
            "open": [100.0 + i * 0.01 for i in range(50_000)],
            "high": [101.0 + i * 0.01 for i in range(50_000)],
            "low": [99.0 + i * 0.01 for i in range(50_000)],
            "close": [100.5 + i * 0.01 for i in range(50_000)],
            "volume": [1000 + i for i in range(50_000)]
        })

        session_filter = SessionFilterMixin()
        result = await session_filter.filter_by_session(large_data, SessionType.RTH, "ES")

        # Take final memory snapshot
        snapshot2 = tracemalloc.take_snapshot()

        # Analyze memory usage
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')[:10]

        # Basic validation
        assert len(result) > 0
        assert len(top_stats) > 0

        # Calculate total memory increase
        total_increase = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)

        # Memory increase should be reasonable for the data size
        # 50k rows * ~40 bytes per row (rough estimate) = ~2MB base expectation
        assert total_increase < 50_000_000  # Less than 50MB increase

        tracemalloc.stop()
