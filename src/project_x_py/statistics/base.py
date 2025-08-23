"""
Base statistics tracking infrastructure with 100% async architecture.

Author: @TexasCoding
Date: 2025-08-21

Overview:
    Provides foundational async statistics tracking capabilities for all ProjectX SDK
    components. Features efficient memory tracking with caching, error history with
    circular buffers, performance timing tracking, and health scoring algorithms.
    All operations are thread-safe using asyncio.Lock and support TTL caching for
    expensive operations.

Key Features:
    - 100% async architecture with asyncio.Lock for thread safety
    - Efficient memory tracking with caching and TTL support
    - Error history with circular buffer (deque with maxlen)
    - Performance timing tracking for all operations
    - Health scoring algorithm (0-100 scale)
    - Protocol-based design for type safety
    - Single read-write lock per component for deadlock prevention
    - Cache with TTL for expensive operations

Components:
    - StatisticsProvider: Protocol for type contracts
    - BaseStatisticsTracker: Core async statistics tracking implementation
    - ErrorInfo: Type-safe error tracking structure
    - PerformanceMetrics: Timing and performance data

Example Usage:
    ```python
    from project_x_py.statistics.base import BaseStatisticsTracker


    class OrderManagerStats(BaseStatisticsTracker):
        def __init__(self):
            super().__init__("order_manager")

        async def track_order_placed(self):
            await self.increment("orders_placed", 1)

        async def track_fill_time(self, duration_ms: float):
            await self.record_timing("fill_time", duration_ms)

        async def get_health(self) -> float:
            return await self.get_health_score()
    ```

See Also:
    - `project_x_py.types.stats_types`: TypedDict definitions for statistics
    - `project_x_py.statistics.collector`: Component-specific statistics collection
    - `project_x_py.statistics.aggregator`: Cross-component statistics aggregation
"""

import asyncio
import time
from collections import defaultdict, deque
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from project_x_py.types.stats_types import ComponentStats


class ErrorInfo:
    """Type-safe error tracking information."""

    def __init__(
        self,
        error: Exception | str,
        context: str,
        details: dict[str, Any] | None = None,
        timestamp: float | None = None,
    ):
        self.error = str(error)
        self.error_type = (
            type(error).__name__ if isinstance(error, Exception) else "Unknown"
        )
        self.context = context
        self.details = details or {}
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error": self.error,
            "error_type": self.error_type,
            "context": self.context,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class PerformanceMetrics:
    """Performance timing and metrics tracking."""

    def __init__(self) -> None:
        self.operation_times: dict[str, list[float]] = defaultdict(list)
        self.operation_counts: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def record_timing(self, operation: str, duration_ms: float) -> None:
        """Record timing for an operation."""
        async with self._lock:
            self.operation_times[operation].append(duration_ms)
            self.operation_counts[operation] += 1

            # Keep only last 1000 timings per operation to prevent memory growth
            if len(self.operation_times[operation]) > 1000:
                self.operation_times[operation] = self.operation_times[operation][
                    -1000:
                ]

    async def get_avg_timing(self, operation: str) -> float:
        """Get average timing for an operation."""
        async with self._lock:
            timings = self.operation_times.get(operation, [])
            return sum(timings) / len(timings) if timings else 0.0

    async def get_operation_count(self, operation: str) -> int:
        """Get count of operations performed."""
        async with self._lock:
            return self.operation_counts.get(operation, 0)

    async def get_all_metrics(self) -> dict[str, dict[str, float]]:
        """Get all performance metrics."""
        async with self._lock:
            metrics = {}
            for operation in self.operation_times:
                timings = self.operation_times[operation]
                metrics[operation] = {
                    "count": self.operation_counts[operation],
                    "avg_ms": sum(timings) / len(timings) if timings else 0.0,
                    "min_ms": min(timings) if timings else 0.0,
                    "max_ms": max(timings) if timings else 0.0,
                }
            return metrics


@runtime_checkable
class StatisticsProvider(Protocol):
    """
    Protocol defining the interface for statistics tracking components.

    All ProjectX SDK components that provide statistics should implement this protocol
    to ensure consistent statistics collection and health monitoring capabilities.
    """

    async def increment(self, metric: str, value: int | float = 1) -> None:
        """
        Increment a counter metric by the specified value.

        Args:
            metric: Name of the metric to increment
            value: Value to increment by (default: 1)
        """
        ...

    async def set_gauge(self, metric: str, value: int | float | Decimal) -> None:
        """
        Set a gauge metric to the specified value.

        Args:
            metric: Name of the gauge metric
            value: Value to set the gauge to
        """
        ...

    async def record_timing(self, operation: str, duration_ms: float) -> None:
        """
        Record timing information for an operation.

        Args:
            operation: Name of the operation being timed
            duration_ms: Duration in milliseconds
        """
        ...

    async def track_error(
        self,
        error: Exception | str,
        context: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Track an error occurrence with context and details.

        Args:
            error: The error that occurred
            context: Context in which the error occurred
            details: Additional error details
        """
        ...

    async def get_stats(self) -> ComponentStats:
        """
        Get current statistics for this component.

        Returns:
            ComponentStats with current metrics and status
        """
        ...

    async def get_health_score(self) -> float:
        """
        Calculate and return health score for this component.

        Returns:
            Health score between 0-100 (100 = perfect health)
        """
        ...


class BaseStatisticsTracker:
    """
    Base class for async statistics tracking with thread safety and caching.

    Provides foundational statistics tracking capabilities including counters,
    gauges, timing data, error tracking, and health scoring. All operations
    are async-safe using asyncio.Lock and include TTL caching for expensive
    operations.

    Features:
        - Async-safe counters and gauges using asyncio.Lock
        - Efficient memory tracking with caching
        - Error history with circular buffer (maxlen=100)
        - Performance timing tracking
        - Health scoring algorithm (0-100 scale)
        - TTL cache for expensive operations (5-second default)
        - Single lock per component to prevent deadlocks
    """

    def __init__(
        self, component_name: str, max_errors: int = 100, cache_ttl: float = 5.0
    ):
        """
        Initialize the statistics tracker.

        Args:
            component_name: Name of the component being tracked
            max_errors: Maximum number of errors to keep in history
            cache_ttl: Cache TTL in seconds for expensive operations
        """
        self.component_name = component_name
        self.created_at = time.time()
        self.last_activity: float | None = None

        # Async-safe data structures
        self._counters: dict[str, int | float] = defaultdict(float)
        self._gauges: dict[str, int | float | Decimal] = {}
        self._error_history: deque[ErrorInfo] = deque(maxlen=max_errors)
        self._performance = PerformanceMetrics()

        # Single lock to prevent deadlocks
        self._lock = asyncio.Lock()

        # Cache for expensive operations
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl = cache_ttl

        # Status tracking
        self._status = "initializing"

    async def increment(self, metric: str, value: int | float = 1) -> None:
        """
        Increment a counter metric by the specified value.

        Args:
            metric: Name of the metric to increment
            value: Value to increment by (default: 1)
        """
        async with self._lock:
            self._counters[metric] += value
            self.last_activity = time.time()

    async def set_gauge(self, metric: str, value: int | float | Decimal) -> None:
        """
        Set a gauge metric to the specified value.

        Args:
            metric: Name of the gauge metric
            value: Value to set the gauge to
        """
        async with self._lock:
            self._gauges[metric] = value
            self.last_activity = time.time()

    async def record_timing(self, operation: str, duration_ms: float) -> None:
        """
        Record timing information for an operation.

        Args:
            operation: Name of the operation being timed
            duration_ms: Duration in milliseconds
        """
        await self._performance.record_timing(operation, duration_ms)
        self.last_activity = time.time()

    async def track_error(
        self,
        error: Exception | str,
        context: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Track an error occurrence with context and details.

        Args:
            error: The error that occurred
            context: Context in which the error occurred
            details: Additional error details
        """
        error_info = ErrorInfo(error, context, details)

        async with self._lock:
            self._error_history.append(error_info)
            self._counters["total_errors"] += 1
            self.last_activity = time.time()

    async def get_error_count(self) -> int:
        """Get total number of errors tracked."""
        async with self._lock:
            return int(self._counters.get("total_errors", 0))

    async def get_recent_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent errors.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of recent error dictionaries
        """
        async with self._lock:
            recent = list(self._error_history)[-limit:]
            return [error.to_dict() for error in recent]

    async def set_status(self, status: str) -> None:
        """
        Set the component status.

        Args:
            status: New status ("connected", "disconnected", "error", "initializing")
        """
        async with self._lock:
            self._status = status
            self.last_activity = time.time()

    async def get_status(self) -> str:
        """Get current component status."""
        async with self._lock:
            return self._status

    async def get_uptime(self) -> int:
        """Get component uptime in seconds."""
        return int(time.time() - self.created_at)

    async def get_memory_usage(self) -> float:
        """
        Get estimated memory usage in MB.

        Override in subclasses for component-specific memory calculations.
        """
        # Basic estimation based on tracked data structures
        base_size = 0.1  # Base overhead in MB

        async with self._lock:
            # Estimate counter/gauge memory
            data_points = len(self._counters) + len(self._gauges)
            data_size = data_points * 0.001  # ~1KB per data point

            # Estimate error history memory
            error_size = len(self._error_history) * 0.002  # ~2KB per error

        # Get performance metrics memory
        perf_metrics = await self._performance.get_all_metrics()
        perf_size = len(perf_metrics) * 0.005  # ~5KB per operation type

        return base_size + data_size + error_size + perf_size

    async def _get_cached_value(self, cache_key: str) -> Any | None:
        """Get cached value if not expired."""
        if cache_key in self._cache:
            value, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return value
        return None

    async def _set_cached_value(self, cache_key: str, value: Any) -> None:
        """Set cached value with current timestamp."""
        self._cache[cache_key] = (value, time.time())

    async def get_health_score(self) -> float:
        """
        Calculate health score for this component (0-100 scale).

        Health scoring factors:
        - Error rate (40% weight): Lower error rate = higher score
        - Uptime (20% weight): Longer uptime = higher score
        - Activity (20% weight): Recent activity = higher score
        - Status (20% weight): Connected status = higher score

        Returns:
            Health score between 0-100 (100 = perfect health)
        """
        # Check cache first
        cached_score = await self._get_cached_value("health_score")
        if cached_score is not None:
            return float(cached_score)

        # Get uptime outside of lock to avoid deadlock
        uptime = await self.get_uptime()
        current_time = time.time()

        async with self._lock:
            # Error rate score (40% weight)
            total_operations = sum(self._counters.values()) - self._counters.get(
                "total_errors", 0
            )
            error_count = self._counters.get("total_errors", 0)

            if total_operations > 0:
                error_rate = error_count / total_operations
                error_score = max(0, 100 - (error_rate * 1000))  # Scale error rate
            else:
                error_score = 100 if error_count == 0 else 0

            # Uptime score (20% weight)
            uptime_score = min(100, (uptime / 3600) * 10)  # 100% after 10 hours

            # Activity score (20% weight)
            if self.last_activity:
                time_since_activity = current_time - self.last_activity
                activity_score = max(
                    0, 100 - (time_since_activity / 60) * 10
                )  # Decay over 10 min
            else:
                activity_score = 0

            # Status score (20% weight)
            status_scores = {
                "connected": 100,
                "active": 100,
                "initializing": 70,
                "disconnected": 30,
                "error": 0,
            }
            status_score = status_scores.get(self._status, 50)

        # Calculate weighted average
        health_score = (
            error_score * 0.4
            + uptime_score * 0.2
            + activity_score * 0.2
            + status_score * 0.2
        )

        # Cache the result
        await self._set_cached_value("health_score", health_score)

        return round(health_score, 1)

    async def get_stats(self) -> ComponentStats:
        """
        Get current statistics for this component.

        Returns:
            ComponentStats with current metrics and status
        """
        # Check cache first
        cached_stats = await self._get_cached_value("component_stats")
        if cached_stats is not None:
            return cached_stats

        # Get metrics that don't require lock first
        uptime = await self.get_uptime()
        performance_metrics = await self._performance.get_all_metrics()

        async with self._lock:
            # Get basic metrics under lock
            error_count = int(self._counters.get("total_errors", 0))

            # Estimate counter/gauge memory inside lock
            data_points = len(self._counters) + len(self._gauges)
            data_size = data_points * 0.001  # ~1KB per data point
            error_size = len(self._error_history) * 0.002  # ~2KB per error

            stats: ComponentStats = {
                "name": self.component_name,
                "status": self._status,
                "uptime_seconds": uptime,
                "last_activity": str(self.last_activity)
                if self.last_activity
                else None,
                "error_count": error_count,
                "memory_usage_mb": 0.1
                + data_size
                + error_size
                + len(performance_metrics) * 0.005,
                "performance_metrics": performance_metrics,
            }

        # Cache the result
        await self._set_cached_value("component_stats", stats)

        return stats

    async def cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]

        for key in expired_keys:
            del self._cache[key]

    async def reset_metrics(self) -> None:
        """Reset all metrics and statistics."""
        async with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._error_history.clear()
            self._cache.clear()
            self.last_activity = None
            self._status = "initializing"

        # Reset performance metrics
        self._performance = PerformanceMetrics()


__all__ = [
    "StatisticsProvider",
    "BaseStatisticsTracker",
    "ErrorInfo",
    "PerformanceMetrics",
]
