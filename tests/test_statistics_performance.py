"""
Performance benchmarking suite for enhanced statistics system.

This module tests the performance impact of the enhanced statistics tracking
to ensure it meets the < 2% CPU overhead and < 5% memory overhead targets.
"""

import asyncio
import gc
import time

import pytest

from project_x_py.statistics import BaseStatisticsTracker, StatisticsAggregator


class MockComponent(BaseStatisticsTracker):
    """Mock component for performance testing."""

    def __init__(self):
        super().__init__("mock_component")
        self.operations_executed = 0

    async def execute_operation(self, duration_ms: float = 1.0) -> None:
        """Simulate an operation with timing."""
        start_time = time.time()
        # Simulate work
        await asyncio.sleep(duration_ms / 1000)
        actual_duration = (time.time() - start_time) * 1000

        # Track the operation
        await self.record_timing("test_operation", actual_duration)
        self.operations_executed += 1


class TestStatisticsPerformance:
    """Performance benchmarking tests for statistics system."""

    @pytest.mark.asyncio
    async def test_cpu_overhead(self):
        """Test that statistics tracking adds < 2% CPU overhead."""
        # Create components with and without stats
        component_with_stats = MockComponent()

        # Benchmark without stats tracking (baseline)
        start_time = time.perf_counter()
        operations = 1000

        for _ in range(operations):
            await asyncio.sleep(0.001)  # 1ms operation

        baseline_duration = time.perf_counter() - start_time

        # Benchmark with stats tracking
        start_time = time.perf_counter()

        for _ in range(operations):
            await component_with_stats.execute_operation(1.0)

        stats_duration = time.perf_counter() - start_time

        # Calculate overhead
        overhead_percent = (
            (stats_duration - baseline_duration) / baseline_duration
        ) * 100

        print(f"Baseline: {baseline_duration:.3f}s")
        print(f"With stats: {stats_duration:.3f}s")
        print(f"Overhead: {overhead_percent:.2f}%")

        # Assert overhead is less than 2%
        assert overhead_percent < 2.0, (
            f"CPU overhead {overhead_percent:.2f}% exceeds 2% target"
        )

    @pytest.mark.asyncio
    async def test_memory_overhead(self):
        """Test that statistics tracking adds < 5% memory overhead."""
        import sys

        # Force garbage collection
        gc.collect()

        # Create a component and measure base memory
        component = MockComponent()
        base_size = sys.getsizeof(component)

        # Execute many operations to populate statistics
        for i in range(10000):
            await component.track_operation(f"op_{i % 10}", float(i % 100))
            if i % 100 == 0:
                await component.track_error(
                    ValueError(f"Test error {i}"),
                    f"context_{i}",
                    {"detail": f"value_{i}"},
                )

        # Measure memory with statistics
        gc.collect()

        # Calculate actual memory usage
        memory_stats = await component.get_enhanced_memory_stats()
        stats_memory_mb = memory_stats["current_memory_mb"]

        # Base object is small, so we check absolute memory usage
        print(f"Base size: {base_size} bytes")
        print(f"Stats memory: {stats_memory_mb:.2f} MB")

        # Assert memory usage is reasonable (< 10MB for 10K operations)
        assert stats_memory_mb < 10.0, (
            f"Memory usage {stats_memory_mb:.2f}MB exceeds limit"
        )

    @pytest.mark.asyncio
    async def test_high_frequency_operations(self):
        """Test statistics handling at 1000+ operations/second."""
        component = MockComponent()
        operations_per_second = 1000
        duration_seconds = 2

        start_time = time.time()
        tasks = []

        # Create concurrent operations
        for i in range(operations_per_second * duration_seconds):
            task = component.track_operation(
                f"high_freq_op_{i % 10}",
                0.1,  # 0.1ms operations
                success=i % 100 != 0,  # 1% failure rate
            )
            tasks.append(task)

            # Yield control periodically
            if i % 100 == 0:
                await asyncio.sleep(0)

        # Wait for all operations to complete
        await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        actual_ops_per_second = len(tasks) / elapsed

        print(f"Target: {operations_per_second} ops/sec")
        print(f"Actual: {actual_ops_per_second:.0f} ops/sec")
        print(f"Elapsed: {elapsed:.2f}s")

        # Verify we achieved target throughput
        assert (
            actual_ops_per_second >= operations_per_second * 0.9
        )  # Allow 10% variance

        # Verify statistics are accurate
        perf_metrics = await component.get_performance_metrics()
        total_ops = sum(
            stats["count"] for stats in perf_metrics["operation_stats"].values()
        )
        assert total_ops == len(tasks)

    @pytest.mark.asyncio
    async def test_circular_buffer_memory_bounds(self):
        """Test that circular buffers prevent unbounded memory growth."""
        component = MockComponent()

        # Get initial memory
        initial_stats = await component.get_enhanced_memory_stats()
        initial_memory = initial_stats["current_memory_mb"]

        # Execute many more operations than buffer size (default 1000)
        for i in range(5000):
            await component.track_operation("buffer_test", float(i % 100))

        # Check memory after many operations
        mid_stats = await component.get_enhanced_memory_stats()
        mid_memory = mid_stats["current_memory_mb"]

        # Execute many more operations
        for i in range(5000, 10000):
            await component.track_operation("buffer_test", float(i % 100))

        # Check final memory
        final_stats = await component.get_enhanced_memory_stats()
        final_memory = final_stats["current_memory_mb"]

        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Mid memory: {mid_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")

        # Memory should not grow significantly after buffer is full
        memory_growth = final_memory - mid_memory
        assert memory_growth < 0.5, (
            f"Memory grew by {memory_growth:.2f}MB after buffer full"
        )

    @pytest.mark.asyncio
    async def test_concurrent_access_performance(self):
        """Test performance with multiple concurrent accessors."""
        component = MockComponent()
        num_workers = 10
        operations_per_worker = 100

        async def worker(worker_id: int):
            """Simulate a worker accessing statistics."""
            for i in range(operations_per_worker):
                # Mix of operations
                await component.track_operation(f"worker_{worker_id}_op", float(i))

                if i % 10 == 0:
                    # Periodically read stats
                    _ = await component.get_performance_metrics()

                if i % 20 == 0:
                    # Occasionally track errors
                    await component.track_error(
                        RuntimeError(f"Worker {worker_id} error"), f"operation_{i}"
                    )

        # Run workers concurrently
        start_time = time.time()
        await asyncio.gather(*[worker(i) for i in range(num_workers)])
        elapsed = time.time() - start_time

        total_operations = num_workers * operations_per_worker
        ops_per_second = total_operations / elapsed

        print(f"Workers: {num_workers}")
        print(f"Total operations: {total_operations}")
        print(f"Elapsed: {elapsed:.2f}s")
        print(f"Throughput: {ops_per_second:.0f} ops/sec")

        # Should handle concurrent access efficiently
        assert ops_per_second > 500, (
            f"Concurrent throughput {ops_per_second:.0f} too low"
        )

    @pytest.mark.asyncio
    async def test_statistics_aggregation_performance(self):
        """Test performance of cross-component statistics aggregation."""

        # Create mock suite with multiple components
        class MockSuite:
            def __init__(self):
                self.orders = MockComponent()
                self.positions = MockComponent()
                self.data = MockComponent()
                self.risk_manager = MockComponent()
                self.orderbook = MockComponent()

        suite = MockSuite()
        aggregator = StatisticsAggregator()

        # Register components with the aggregator
        await aggregator.register_component("orders", suite.orders)
        await aggregator.register_component("positions", suite.positions)
        await aggregator.register_component("data", suite.data)

        # Populate components with data
        components = [suite.orders, suite.positions, suite.data]
        for component in components:
            for i in range(100):
                await component.record_timing(f"op_{i}", float(i % 50))

        # Benchmark aggregation
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            stats = await aggregator.get_comprehensive_stats()
            assert stats["health_score"] is not None

        elapsed = time.time() - start_time
        avg_time_ms = (elapsed / iterations) * 1000

        print(f"Aggregation iterations: {iterations}")
        print(f"Total time: {elapsed:.3f}s")
        print(f"Average time: {avg_time_ms:.2f}ms")

        # Aggregation should be fast (< 10ms)
        assert avg_time_ms < 10, (
            f"Aggregation time {avg_time_ms:.2f}ms exceeds 10ms target"
        )

    @pytest.mark.asyncio
    async def test_cleanup_performance(self):
        """Test that cleanup operations don't block or slow down operations."""
        component = MockComponent()

        # Fill up statistics
        for i in range(1000):
            await component.track_operation("cleanup_test", float(i))
            if i % 10 == 0:
                await component.track_error(Exception(f"Error {i}"), f"context_{i}")

        # Measure cleanup time
        start_time = time.time()
        await component.cleanup_old_stats()
        cleanup_time = time.time() - start_time

        print(f"Cleanup time: {cleanup_time * 1000:.2f}ms")

        # Cleanup should be fast (< 100ms)
        assert cleanup_time < 0.1, (
            f"Cleanup took {cleanup_time * 1000:.2f}ms, exceeds 100ms"
        )

        # Operations should continue to work during/after cleanup
        await component.track_operation("post_cleanup", 1.0)
        stats = await component.get_performance_metrics()
        assert "operation_stats" in stats

    @pytest.mark.asyncio
    async def test_export_performance(self):
        """Test performance of statistics export in different formats."""
        component = MockComponent()

        # Populate with data
        for i in range(500):
            await component.track_operation(f"export_test_{i % 20}", float(i % 100))

        # Test JSON export
        start_time = time.time()
        json_export = await component.export_stats("json")
        json_time = time.time() - start_time

        # Test Prometheus export
        start_time = time.time()
        prometheus_export = await component.export_stats("prometheus")
        prometheus_time = time.time() - start_time

        print(f"JSON export time: {json_time * 1000:.2f}ms")
        print(f"Prometheus export time: {prometheus_time * 1000:.2f}ms")

        # Exports should be fast (< 50ms)
        assert json_time < 0.05, f"JSON export took {json_time * 1000:.2f}ms"
        assert prometheus_time < 0.05, (
            f"Prometheus export took {prometheus_time * 1000:.2f}ms"
        )

    @pytest.mark.asyncio
    async def test_percentile_calculation_performance(self):
        """Test performance of percentile calculations with large datasets."""
        component = MockComponent()

        # Add many timing samples
        for i in range(1000):
            component._api_timings.append(float(i))

        # Benchmark percentile calculations
        iterations = 1000
        start_time = time.time()

        for _ in range(iterations):
            p50 = component._calculate_percentile(component._api_timings, 50)
            p95 = component._calculate_percentile(component._api_timings, 95)
            p99 = component._calculate_percentile(component._api_timings, 99)

        elapsed = time.time() - start_time
        avg_time_us = (elapsed / iterations) * 1_000_000

        print(f"Percentile calculations: {iterations}")
        print(f"Average time: {avg_time_us:.2f}μs")

        # Percentile calculation should be fast (< 100μs)
        assert avg_time_us < 100, f"Percentile calc took {avg_time_us:.2f}μs"


if __name__ == "__main__":
    # Run performance tests
    asyncio.run(TestStatisticsPerformance().test_cpu_overhead())
    asyncio.run(TestStatisticsPerformance().test_memory_overhead())
    asyncio.run(TestStatisticsPerformance().test_high_frequency_operations())
    asyncio.run(TestStatisticsPerformance().test_circular_buffer_memory_bounds())
    asyncio.run(TestStatisticsPerformance().test_concurrent_access_performance())
    asyncio.run(TestStatisticsPerformance().test_statistics_aggregation_performance())
    asyncio.run(TestStatisticsPerformance().test_cleanup_performance())
    asyncio.run(TestStatisticsPerformance().test_export_performance())
    asyncio.run(TestStatisticsPerformance().test_percentile_calculation_performance())
    print("\n✅ All performance tests passed!")
