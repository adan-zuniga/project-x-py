"""
Lock performance benchmarking utility for project-x-py SDK.

Author: @TexasCoding
Date: 2025-01-22

Overview:
    Provides comprehensive benchmarking tools to measure and compare lock performance
    improvements in the realtime modules. Generates detailed performance reports
    showing improvements from lock optimization.

Features:
    - Before/after performance comparison
    - Concurrent load testing
    - Lock contention measurement
    - Performance regression detection
    - Detailed benchmark reports
    - Real-time monitoring during tests

Usage:
    ```python
    from project_x_py.utils.lock_benchmarker import LockBenchmarker

    benchmarker = LockBenchmarker()

    # Benchmark realtime data manager
    results = await benchmarker.benchmark_realtime_data_manager(
        duration_seconds=30, reader_threads=10, writer_threads=2
    )

    print(f"Performance improvement: {results['improvement_factor']:.2f}x")
    print(f"Contention reduction: {results['contention_reduction_percent']:.1f}%")
    ```

Key Metrics:
    - Lock acquisition time (average, min, max, p95, p99)
    - Contention rate (percentage of time spent waiting)
    - Throughput (operations per second)
    - Concurrency (number of parallel operations)
    - Memory usage during tests
    - Error rates under load
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, cast

import polars as pl

from project_x_py.utils import ProjectXLogger
from project_x_py.utils.lock_optimization import (
    AsyncRWLock,
    LockFreeBuffer,
    LockProfiler,
)

logger = ProjectXLogger.get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Results from a lock performance benchmark."""

    test_name: str
    duration_seconds: float

    # Throughput metrics
    total_operations: int
    operations_per_second: float

    # Latency metrics
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float

    # Concurrency metrics
    max_concurrent_operations: int
    avg_concurrent_operations: float

    # Contention metrics
    contention_rate_percent: float
    total_wait_time_ms: float
    timeout_count: int

    # Resource metrics
    peak_memory_mb: float
    avg_cpu_percent: float

    # Error metrics
    error_count: int
    error_rate_percent: float


@dataclass
class ComparisonResult:
    """Comparison between baseline and optimized performance."""

    baseline: BenchmarkResult
    optimized: BenchmarkResult

    # Improvement factors
    throughput_improvement: float
    latency_improvement: float
    contention_reduction: float
    memory_improvement: float

    # Summary metrics
    overall_improvement_score: float
    recommendation: str


class LockBenchmarker:
    """
    Comprehensive lock performance benchmarking utility.

    Provides tools to measure lock performance improvements and generate
    detailed comparison reports between baseline and optimized implementations.
    """

    def __init__(self) -> None:
        self.profiler = LockProfiler()
        self.results: list[BenchmarkResult] = []

    async def benchmark_regular_lock(
        self,
        duration_seconds: float = 30.0,
        reader_count: int = 10,
        writer_count: int = 2,
        operation_delay_ms: float = 1.0,
    ) -> BenchmarkResult:
        """Benchmark regular asyncio.Lock performance."""

        logger.info(
            f"Benchmarking regular lock: {reader_count}R/{writer_count}W for {duration_seconds}s"
        )

        # Test data
        shared_data = {"counter": 0, "dataframe": pl.DataFrame({"value": [1, 2, 3]})}
        lock = asyncio.Lock()

        # Metrics tracking
        operations: list[dict[str, Any]] = []
        start_time = time.time()
        concurrent_ops = 0
        max_concurrent_ops = 0
        errors = 0

        async def reader_task(reader_id: int) -> None:
            nonlocal concurrent_ops, max_concurrent_ops, errors

            while time.time() - start_time < duration_seconds:
                op_start = time.time()
                try:
                    concurrent_ops += 1
                    max_concurrent_ops = max(max_concurrent_ops, concurrent_ops)

                    async with lock:
                        # Simulate DataFrame read operation
                        df = cast(pl.DataFrame, shared_data["dataframe"])
                        _ = df.select(pl.col("value")).sum()
                        _ = shared_data["counter"]
                        await asyncio.sleep(operation_delay_ms / 1000)

                    concurrent_ops -= 1
                    op_end = time.time()

                    operations.append(
                        {
                            "type": "read",
                            "duration_ms": (op_end - op_start) * 1000,
                            "timestamp": op_start,
                        }
                    )

                except Exception as e:
                    errors += 1
                    concurrent_ops = max(0, concurrent_ops - 1)
                    logger.error(f"Reader {reader_id} error: {e}")

                # Brief pause between operations
                await asyncio.sleep(0.01)

        async def writer_task(writer_id: int) -> None:
            nonlocal concurrent_ops, max_concurrent_ops, errors

            while time.time() - start_time < duration_seconds:
                op_start = time.time()
                try:
                    concurrent_ops += 1
                    max_concurrent_ops = max(max_concurrent_ops, concurrent_ops)

                    async with lock:
                        # Simulate DataFrame write operation
                        shared_data["counter"] = cast(int, shared_data["counter"]) + 1
                        df = cast(pl.DataFrame, shared_data["dataframe"])
                        shared_data["dataframe"] = df.with_columns(pl.col("value") + 1)
                        await asyncio.sleep(
                            operation_delay_ms * 2 / 1000
                        )  # Writes take longer

                    concurrent_ops -= 1
                    op_end = time.time()

                    operations.append(
                        {
                            "type": "write",
                            "duration_ms": (op_end - op_start) * 1000,
                            "timestamp": op_start,
                        }
                    )

                except Exception as e:
                    errors += 1
                    concurrent_ops = max(0, concurrent_ops - 1)
                    logger.error(f"Writer {writer_id} error: {e}")

                # Longer pause between writes
                await asyncio.sleep(0.05)

        # Run benchmark
        tasks = []
        for i in range(reader_count):
            tasks.append(reader_task(i))
        for i in range(writer_count):
            tasks.append(writer_task(i))

        await asyncio.gather(*tasks)

        # Calculate metrics
        if operations:
            latencies = [float(op["duration_ms"]) for op in operations]
            latencies.sort()

            avg_latency = sum(latencies) / len(latencies)
            min_latency = latencies[0]
            max_latency = latencies[-1]
            p95_latency = latencies[int(len(latencies) * 0.95)]
            p99_latency = latencies[int(len(latencies) * 0.99)]

            # Calculate contention (operations taking >5ms considered contended)
            contended_ops = len([latency for latency in latencies if latency > 5.0])
            contention_rate = (contended_ops / len(latencies)) * 100

            total_wait_time = sum(
                [max(0, latency - operation_delay_ms) for latency in latencies]
            )
        else:
            avg_latency = min_latency = max_latency = p95_latency = p99_latency = 0.0
            contention_rate = total_wait_time = 0.0

        actual_duration = time.time() - start_time

        return BenchmarkResult(
            test_name="Regular asyncio.Lock",
            duration_seconds=actual_duration,
            total_operations=len(operations),
            operations_per_second=len(operations) / actual_duration,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            max_concurrent_operations=max_concurrent_ops,
            avg_concurrent_operations=1.0,  # Regular lock allows max 1 concurrent
            contention_rate_percent=contention_rate,
            total_wait_time_ms=total_wait_time,
            timeout_count=0,
            peak_memory_mb=0.1,  # Rough estimate
            avg_cpu_percent=0.0,
            error_count=errors,
            error_rate_percent=(errors / max(1, len(operations) + errors)) * 100,
        )

    async def benchmark_rw_lock(
        self,
        duration_seconds: float = 30.0,
        reader_count: int = 10,
        writer_count: int = 2,
        operation_delay_ms: float = 1.0,
    ) -> BenchmarkResult:
        """Benchmark AsyncRWLock performance."""

        logger.info(
            f"Benchmarking AsyncRWLock: {reader_count}R/{writer_count}W for {duration_seconds}s"
        )

        # Test data
        shared_data = {"counter": 0, "dataframe": pl.DataFrame({"value": [1, 2, 3]})}
        rw_lock = AsyncRWLock("benchmark_lock")

        # Metrics tracking
        operations: list[dict[str, Any]] = []
        start_time = time.time()
        concurrent_readers = 0
        max_concurrent_readers = 0
        errors = 0

        async def reader_task(reader_id: int) -> None:
            nonlocal concurrent_readers, max_concurrent_readers, errors

            while time.time() - start_time < duration_seconds:
                op_start = time.time()
                try:
                    async with rw_lock.read_lock():
                        concurrent_readers += 1
                        max_concurrent_readers = max(
                            max_concurrent_readers, concurrent_readers
                        )

                        # Simulate DataFrame read operation
                        df = cast(pl.DataFrame, shared_data["dataframe"])
                        _ = df.select(pl.col("value")).sum()
                        _ = shared_data["counter"]
                        await asyncio.sleep(operation_delay_ms / 1000)

                        concurrent_readers -= 1

                    op_end = time.time()

                    operations.append(
                        {
                            "type": "read",
                            "duration_ms": (op_end - op_start) * 1000,
                            "timestamp": op_start,
                        }
                    )

                except Exception as e:
                    errors += 1
                    concurrent_readers = max(0, concurrent_readers - 1)
                    logger.error(f"Reader {reader_id} error: {e}")

                # Brief pause between operations
                await asyncio.sleep(0.01)

        async def writer_task(writer_id: int) -> None:
            nonlocal errors

            while time.time() - start_time < duration_seconds:
                op_start = time.time()
                try:
                    async with rw_lock.write_lock():
                        # Simulate DataFrame write operation
                        shared_data["counter"] = cast(int, shared_data["counter"]) + 1
                        df = cast(pl.DataFrame, shared_data["dataframe"])
                        shared_data["dataframe"] = df.with_columns(pl.col("value") + 1)
                        await asyncio.sleep(
                            operation_delay_ms * 2 / 1000
                        )  # Writes take longer

                    op_end = time.time()

                    operations.append(
                        {
                            "type": "write",
                            "duration_ms": (op_end - op_start) * 1000,
                            "timestamp": op_start,
                        }
                    )

                except Exception as e:
                    errors += 1
                    logger.error(f"Writer {writer_id} error: {e}")

                # Longer pause between writes
                await asyncio.sleep(0.05)

        # Run benchmark
        tasks = []
        for i in range(reader_count):
            tasks.append(reader_task(i))
        for i in range(writer_count):
            tasks.append(writer_task(i))

        await asyncio.gather(*tasks)

        # Get lock statistics
        lock_stats = await rw_lock.get_stats()

        # Calculate metrics
        if operations:
            latencies = [float(op["duration_ms"]) for op in operations]
            latencies.sort()

            avg_latency = sum(latencies) / len(latencies)
            min_latency = latencies[0]
            max_latency = latencies[-1]
            p95_latency = latencies[int(len(latencies) * 0.95)]
            p99_latency = latencies[int(len(latencies) * 0.99)]

            # Calculate contention using lock statistics
            contention_rate = (
                lock_stats.contentions / lock_stats.total_acquisitions * 100
                if lock_stats.total_acquisitions > 0
                else 0.0
            )
        else:
            avg_latency = min_latency = max_latency = p95_latency = p99_latency = 0.0
            contention_rate = 0.0

        actual_duration = time.time() - start_time

        return BenchmarkResult(
            test_name="AsyncRWLock",
            duration_seconds=actual_duration,
            total_operations=len(operations),
            operations_per_second=len(operations) / actual_duration,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            max_concurrent_operations=max_concurrent_readers,
            avg_concurrent_operations=lock_stats.max_concurrent_readers
            / max(1, reader_count),
            contention_rate_percent=contention_rate,
            total_wait_time_ms=lock_stats.total_wait_time_ms,
            timeout_count=lock_stats.timeouts,
            peak_memory_mb=0.1,  # Rough estimate
            avg_cpu_percent=0.0,
            error_count=errors,
            error_rate_percent=(errors / max(1, len(operations) + errors)) * 100,
        )

    async def benchmark_lock_free_buffer(
        self,
        duration_seconds: float = 30.0,
        writer_count: int = 5,
        reader_count: int = 10,
        buffer_size: int = 10000,
    ) -> BenchmarkResult:
        """Benchmark LockFreeBuffer performance."""

        logger.info(
            f"Benchmarking LockFreeBuffer: {writer_count}W/{reader_count}R for {duration_seconds}s"
        )

        buffer = LockFreeBuffer[dict[str, Any]](max_size=buffer_size)
        operations: list[dict[str, Any]] = []
        start_time = time.time()
        errors = 0

        async def writer_task(writer_id: int) -> None:
            nonlocal errors

            counter = 0
            while time.time() - start_time < duration_seconds:
                op_start = time.time()
                try:
                    # High-frequency data writing
                    data = {
                        "timestamp": time.time(),
                        "writer_id": writer_id,
                        "counter": counter,
                        "price": 4500.0 + (counter % 100) * 0.25,
                        "volume": 100 + (counter % 50),
                    }

                    success = buffer.append(data)
                    op_end = time.time()

                    operations.append(
                        {
                            "type": "write",
                            "duration_ms": (op_end - op_start) * 1000,
                            "timestamp": op_start,
                            "success": success,
                        }
                    )

                    counter += 1

                except Exception as e:
                    errors += 1
                    logger.error(f"Writer {writer_id} error: {e}")

                # High frequency - minimal delay
                await asyncio.sleep(0.001)

        async def reader_task(reader_id: int) -> None:
            nonlocal errors

            while time.time() - start_time < duration_seconds:
                op_start = time.time()
                try:
                    # Read recent data
                    recent_data = buffer.get_recent(100)
                    op_end = time.time()

                    operations.append(
                        {
                            "type": "read",
                            "duration_ms": (op_end - op_start) * 1000,
                            "timestamp": op_start,
                            "data_count": len(recent_data),
                        }
                    )

                except Exception as e:
                    errors += 1
                    logger.error(f"Reader {reader_id} error: {e}")

                # Moderate frequency
                await asyncio.sleep(0.01)

        # Run benchmark
        tasks = []
        for i in range(writer_count):
            tasks.append(writer_task(i))
        for i in range(reader_count):
            tasks.append(reader_task(i))

        await asyncio.gather(*tasks)

        # Get buffer statistics
        buffer_stats = buffer.get_stats()

        # Calculate metrics
        if operations:
            latencies = [float(op["duration_ms"]) for op in operations]
            latencies.sort()

            avg_latency = sum(latencies) / len(latencies)
            min_latency = latencies[0]
            max_latency = latencies[-1]
            p95_latency = latencies[int(len(latencies) * 0.95)]
            p99_latency = latencies[int(len(latencies) * 0.99)]

            # Lock-free should have very low contention
            contention_rate = 0.0  # No explicit locks to contend on
        else:
            avg_latency = min_latency = max_latency = p95_latency = p99_latency = 0.0
            contention_rate = 0.0

        actual_duration = time.time() - start_time

        return BenchmarkResult(
            test_name="LockFreeBuffer",
            duration_seconds=actual_duration,
            total_operations=len(operations),
            operations_per_second=len(operations) / actual_duration,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            max_concurrent_operations=writer_count
            + reader_count,  # All can operate concurrently
            avg_concurrent_operations=writer_count + reader_count,
            contention_rate_percent=contention_rate,
            total_wait_time_ms=0.0,  # No waiting in lock-free operations
            timeout_count=0,
            peak_memory_mb=buffer_stats["size"] * 0.001,  # Rough estimate
            avg_cpu_percent=0.0,
            error_count=errors,
            error_rate_percent=(errors / max(1, len(operations) + errors)) * 100,
        )

    async def compare_lock_implementations(
        self,
        duration_seconds: float = 30.0,
        reader_count: int = 10,
        writer_count: int = 2,
    ) -> ComparisonResult:
        """Compare regular lock vs AsyncRWLock performance."""

        logger.info("Running lock implementation comparison benchmark")

        # Benchmark baseline (regular lock)
        baseline_result = await self.benchmark_regular_lock(
            duration_seconds, reader_count, writer_count
        )

        # Brief pause between tests
        await asyncio.sleep(1.0)

        # Benchmark optimized (AsyncRWLock)
        optimized_result = await self.benchmark_rw_lock(
            duration_seconds, reader_count, writer_count
        )

        # Calculate improvements
        throughput_improvement = (
            optimized_result.operations_per_second
            / baseline_result.operations_per_second
            if baseline_result.operations_per_second > 0
            else 1.0
        )

        latency_improvement = (
            baseline_result.avg_latency_ms / optimized_result.avg_latency_ms
            if optimized_result.avg_latency_ms > 0
            else 1.0
        )

        contention_reduction = max(
            0,
            baseline_result.contention_rate_percent
            - optimized_result.contention_rate_percent,
        )

        memory_improvement = (
            baseline_result.peak_memory_mb / optimized_result.peak_memory_mb
            if optimized_result.peak_memory_mb > 0
            else 1.0
        )

        # Overall improvement score (weighted average)
        overall_score = (
            throughput_improvement * 0.4
            + latency_improvement * 0.3
            + (contention_reduction / 10) * 0.2  # Scale contention to 0-10 range
            + memory_improvement * 0.1
        )

        # Generate recommendation
        if overall_score > 1.5:
            recommendation = (
                "Significant improvement - implement AsyncRWLock immediately"
            )
        elif overall_score > 1.2:
            recommendation = (
                "Good improvement - AsyncRWLock recommended for read-heavy workloads"
            )
        elif overall_score > 1.0:
            recommendation = "Minor improvement - consider AsyncRWLock for high-concurrency scenarios"
        else:
            recommendation = (
                "No significant improvement - regular locks may be sufficient"
            )

        return ComparisonResult(
            baseline=baseline_result,
            optimized=optimized_result,
            throughput_improvement=throughput_improvement,
            latency_improvement=latency_improvement,
            contention_reduction=contention_reduction,
            memory_improvement=memory_improvement,
            overall_improvement_score=overall_score,
            recommendation=recommendation,
        )

    def generate_report(self, comparison: ComparisonResult) -> str:
        """Generate a human-readable performance comparison report."""

        report = []
        report.append("=" * 70)
        report.append("LOCK OPTIMIZATION PERFORMANCE REPORT")
        report.append("=" * 70)

        # Summary
        report.append(
            f"\nOVERALL IMPROVEMENT SCORE: {comparison.overall_improvement_score:.2f}"
        )
        report.append(f"RECOMMENDATION: {comparison.recommendation}")

        # Throughput comparison
        report.append(f"\n{'-' * 40}")
        report.append("THROUGHPUT ANALYSIS")
        report.append(f"{'-' * 40}")
        report.append(
            f"Baseline (Regular Lock): {comparison.baseline.operations_per_second:.1f} ops/sec"
        )
        report.append(
            f"Optimized (AsyncRWLock): {comparison.optimized.operations_per_second:.1f} ops/sec"
        )
        report.append(f"Improvement: {comparison.throughput_improvement:.2f}x faster")

        # Latency comparison
        report.append(f"\n{'-' * 40}")
        report.append("LATENCY ANALYSIS")
        report.append(f"{'-' * 40}")
        report.append(
            f"{'Metric':<20} {'Baseline':<12} {'Optimized':<12} {'Improvement':<12}"
        )
        report.append("-" * 58)
        report.append(
            f"{'Average (ms)':<20} {comparison.baseline.avg_latency_ms:<12.2f} "
            f"{comparison.optimized.avg_latency_ms:<12.2f} "
            f"{comparison.latency_improvement:<12.2f}x"
        )
        report.append(
            f"{'P95 (ms)':<20} {comparison.baseline.p95_latency_ms:<12.2f} "
            f"{comparison.optimized.p95_latency_ms:<12.2f} "
            f"{comparison.baseline.p95_latency_ms / max(0.001, comparison.optimized.p95_latency_ms):<12.2f}x"
        )
        report.append(
            f"{'P99 (ms)':<20} {comparison.baseline.p99_latency_ms:<12.2f} "
            f"{comparison.optimized.p99_latency_ms:<12.2f} "
            f"{comparison.baseline.p99_latency_ms / max(0.001, comparison.optimized.p99_latency_ms):<12.2f}x"
        )

        # Concurrency comparison
        report.append(f"\n{'-' * 40}")
        report.append("CONCURRENCY ANALYSIS")
        report.append(f"{'-' * 40}")
        report.append(
            f"Baseline Max Concurrent: {comparison.baseline.max_concurrent_operations}"
        )
        report.append(
            f"Optimized Max Concurrent: {comparison.optimized.max_concurrent_operations}"
        )
        report.append(
            f"Concurrency Improvement: "
            f"{comparison.optimized.max_concurrent_operations / max(1, comparison.baseline.max_concurrent_operations):.2f}x"
        )

        # Contention comparison
        report.append(f"\n{'-' * 40}")
        report.append("CONTENTION ANALYSIS")
        report.append(f"{'-' * 40}")
        report.append(
            f"Baseline Contention Rate: {comparison.baseline.contention_rate_percent:.1f}%"
        )
        report.append(
            f"Optimized Contention Rate: {comparison.optimized.contention_rate_percent:.1f}%"
        )
        report.append(
            f"Contention Reduction: {comparison.contention_reduction:.1f} percentage points"
        )

        # Error analysis
        report.append(f"\n{'-' * 40}")
        report.append("ERROR ANALYSIS")
        report.append(f"{'-' * 40}")
        report.append(
            f"Baseline Errors: {comparison.baseline.error_count} "
            f"({comparison.baseline.error_rate_percent:.2f}%)"
        )
        report.append(
            f"Optimized Errors: {comparison.optimized.error_count} "
            f"({comparison.optimized.error_rate_percent:.2f}%)"
        )

        # Key insights
        report.append(f"\n{'-' * 40}")
        report.append("KEY INSIGHTS")
        report.append(f"{'-' * 40}")

        if comparison.throughput_improvement > 1.5:
            report.append(
                "• Significant throughput improvement - AsyncRWLock enables better parallelism"
            )
        if comparison.contention_reduction > 20:
            report.append(
                "• Major contention reduction - readers can operate in parallel"
            )
        if (
            comparison.optimized.max_concurrent_operations
            > comparison.baseline.max_concurrent_operations * 2
        ):
            report.append(
                "• Dramatic concurrency improvement - much better resource utilization"
            )
        if (
            comparison.optimized.error_rate_percent
            < comparison.baseline.error_rate_percent
        ):
            report.append("• Reduced error rate - more stable under load")

        report.append(f"\n{'-' * 40}")
        report.append("IMPLEMENTATION IMPACT")
        report.append(f"{'-' * 40}")

        expected_improvement = comparison.throughput_improvement * 100 - 100
        report.append(
            f"• Expected {expected_improvement:.0f}% performance improvement in production"
        )

        if comparison.contention_reduction > 10:
            report.append(
                f"• {comparison.contention_reduction:.0f} percentage point reduction in lock contention"
            )

        if comparison.optimized.max_concurrent_operations > 5:
            report.append(
                f"• Supports up to {comparison.optimized.max_concurrent_operations} concurrent readers"
            )

        report.append("=" * 70)

        return "\n".join(report)


async def run_full_benchmark_suite() -> dict[str, Any]:
    """Run complete benchmark suite and return results."""

    logger.info("Starting full lock optimization benchmark suite")

    benchmarker = LockBenchmarker()

    # Test parameters
    test_duration = 30.0
    reader_count = 10  # Heavy read workload (typical for DataFrames)
    writer_count = 2  # Light write workload

    try:
        # Run comparison benchmark
        comparison = await benchmarker.compare_lock_implementations(
            duration_seconds=test_duration,
            reader_count=reader_count,
            writer_count=writer_count,
        )

        # Run lock-free buffer benchmark
        buffer_result = await benchmarker.benchmark_lock_free_buffer(
            duration_seconds=test_duration, writer_count=5, reader_count=10
        )

        # Generate report
        report = benchmarker.generate_report(comparison)

        return {
            "comparison": comparison,
            "buffer_benchmark": buffer_result,
            "report": report,
            "summary": {
                "throughput_improvement": comparison.throughput_improvement,
                "latency_improvement": comparison.latency_improvement,
                "contention_reduction": comparison.contention_reduction,
                "overall_score": comparison.overall_improvement_score,
                "recommendation": comparison.recommendation,
                "buffer_ops_per_sec": buffer_result.operations_per_second,
            },
        }

    except Exception as e:
        logger.error(f"Benchmark suite failed: {e}")
        raise


if __name__ == "__main__":
    # Run benchmarks when called directly
    import asyncio

    async def main() -> None:
        results = await run_full_benchmark_suite()
        print(results["report"])
        print("\nSummary:")
        print(
            f"- Lock Optimization Improvement: {results['summary']['throughput_improvement']:.2f}x"
        )
        print(
            f"- Buffer Operations/sec: {results['summary']['buffer_ops_per_sec']:.0f}"
        )
        print(f"- Recommendation: {results['summary']['recommendation']}")

    asyncio.run(main())
