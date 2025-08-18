"""
Enhanced statistics tracking mixin with async support and performance metrics.

Author: SDK v3.2.1
Date: 2025-01-18

Overview:
    Provides comprehensive statistics tracking capabilities for all SDK components
    with async support, circular buffers for memory management, and configurable
    retention periods.

Key Features:
    - Async-safe operations with locks
    - Circular buffers to prevent memory leaks
    - Performance timing metrics
    - Configurable retention periods
    - Thread-safe aggregation
    - PII sanitization for exports
    - Graceful degradation on failures
"""

import asyncio
import sys
import time
import traceback
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from project_x_py.utils.logging_config import ProjectXLogger

logger = ProjectXLogger.get_logger(__name__)


class EnhancedStatsTrackingMixin:
    """
    Enhanced mixin for comprehensive statistics tracking across all components.

    Provides async-safe, memory-efficient statistics collection with configurable
    retention, performance metrics, and export capabilities.
    """

    def _init_enhanced_stats(
        self,
        max_errors: int = 100,
        max_timings: int = 1000,
        retention_hours: int = 24,
        enable_profiling: bool = False,
    ) -> None:
        """
        Initialize enhanced statistics tracking.

        Args:
            max_errors: Maximum error history entries
            max_timings: Maximum timing samples to retain
            retention_hours: Hours to retain detailed statistics
            enable_profiling: Enable detailed performance profiling
        """
        # Store max_timings for use in other methods
        self._max_timings = max_timings

        # Error tracking with circular buffer
        self._error_count = 0
        self._error_history: deque[dict[str, Any]] = deque(maxlen=max_errors)
        self._error_types: dict[str, int] = {}

        # Performance metrics with circular buffers
        self._api_timings: deque[float] = deque(maxlen=max_timings)
        self._operation_timings: dict[str, deque[float]] = {}
        self._last_activity = datetime.now()
        self._start_time = time.time()

        # Memory tracking
        self._memory_snapshots: deque[dict[str, Any]] = deque(maxlen=100)
        self._last_memory_check = time.time()

        # Network metrics
        self._network_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "avg_latency_ms": 0.0,
            "websocket_reconnects": 0,
            "websocket_messages": 0,
        }

        # Data quality metrics
        self._data_quality = {
            "total_data_points": 0,
            "invalid_data_points": 0,
            "missing_data_points": 0,
            "duplicate_data_points": 0,
            "data_gaps": [],
            "last_validation": None,
        }

        # Configuration
        self._retention_hours = retention_hours
        self._enable_profiling = enable_profiling
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

        # Async lock for thread safety
        self._stats_lock = asyncio.Lock()

        # Component-specific stats (to be overridden by each component)
        self._component_stats: dict[str, Any] = {}

        logger.debug(
            f"Enhanced stats initialized: retention={retention_hours}h, "
            f"profiling={enable_profiling}"
        )

    async def track_operation(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Track an operation with timing and success metrics.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            metadata: Optional metadata about the operation
        """
        async with self._stats_lock:
            # Update operation timings
            if operation not in self._operation_timings:
                self._operation_timings[operation] = deque(maxlen=self._max_timings)
            self._operation_timings[operation].append(duration_ms)

            # Update network stats if applicable
            if metadata and "bytes_sent" in metadata:
                self._network_stats["total_bytes_sent"] += metadata["bytes_sent"]
            if metadata and "bytes_received" in metadata:
                self._network_stats["total_bytes_received"] += metadata[
                    "bytes_received"
                ]

            # Update request counts
            self._network_stats["total_requests"] += 1
            if success:
                self._network_stats["successful_requests"] += 1
            else:
                self._network_stats["failed_requests"] += 1

            # Update activity timestamp
            self._last_activity = datetime.now()

            # Trigger cleanup if needed
            await self._cleanup_old_stats_if_needed()

    async def track_error(
        self,
        error: Exception,
        context: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Track an error occurrence with enhanced context.

        Args:
            error: The exception that occurred
            context: Context about where/why the error occurred
            details: Additional error details
        """
        async with self._stats_lock:
            self._error_count += 1

            # Update error type counts
            error_type = type(error).__name__
            self._error_types[error_type] = self._error_types.get(error_type, 0) + 1

            # Sanitize details to remove PII
            sanitized_details = self._sanitize_for_export(details) if details else None

            # Store error in history
            self._error_history.append(
                {
                    "timestamp": datetime.now(),
                    "error_type": error_type,
                    "message": str(error),
                    "context": context,
                    "details": sanitized_details,
                    "traceback": traceback.format_exc()
                    if self._enable_profiling
                    else None,
                }
            )

    async def track_data_quality(
        self,
        total_points: int,
        invalid_points: int = 0,
        missing_points: int = 0,
        duplicate_points: int = 0,
    ) -> None:
        """
        Track data quality metrics.

        Args:
            total_points: Total data points processed
            invalid_points: Number of invalid points
            missing_points: Number of missing points
            duplicate_points: Number of duplicate points
        """
        async with self._stats_lock:
            self._data_quality["total_data_points"] += total_points
            self._data_quality["invalid_data_points"] += invalid_points
            self._data_quality["missing_data_points"] += missing_points
            self._data_quality["duplicate_data_points"] += duplicate_points
            self._data_quality["last_validation"] = datetime.now()

    async def get_performance_metrics(self) -> dict[str, Any]:
        """
        Get detailed performance metrics.

        Returns:
            Dictionary with performance statistics
        """
        async with self._stats_lock:
            # Calculate averages for each operation
            operation_stats = {}
            for op_name, timings in self._operation_timings.items():
                if timings:
                    operation_stats[op_name] = {
                        "count": len(timings),
                        "avg_ms": sum(timings) / len(timings),
                        "min_ms": min(timings),
                        "max_ms": max(timings),
                        "p50_ms": self._calculate_percentile(timings, 50),
                        "p95_ms": self._calculate_percentile(timings, 95),
                        "p99_ms": self._calculate_percentile(timings, 99),
                    }

            # Calculate overall API timing stats
            api_stats = {}
            if self._api_timings:
                api_stats = {
                    "avg_response_time_ms": sum(self._api_timings)
                    / len(self._api_timings),
                    "min_response_time_ms": min(self._api_timings),
                    "max_response_time_ms": max(self._api_timings),
                    "p50_response_time_ms": self._calculate_percentile(
                        self._api_timings, 50
                    ),
                    "p95_response_time_ms": self._calculate_percentile(
                        self._api_timings, 95
                    ),
                }

            # Calculate network metrics
            success_rate = (
                self._network_stats["successful_requests"]
                / self._network_stats["total_requests"]
                if self._network_stats["total_requests"] > 0
                else 0.0
            )

            return {
                "operation_stats": operation_stats,
                "api_stats": api_stats,
                "network_stats": {
                    **self._network_stats,
                    "success_rate": success_rate,
                },
                "uptime_seconds": time.time() - self._start_time,
                "last_activity": self._last_activity.isoformat()
                if self._last_activity
                else None,
            }

    async def get_error_stats(self) -> dict[str, Any]:
        """
        Get enhanced error statistics.

        Returns:
            Dictionary with error statistics
        """
        async with self._stats_lock:
            recent_errors = list(self._error_history)[-10:]  # Last 10 errors

            # Calculate error rate over time windows
            now = datetime.now()
            errors_last_hour = sum(
                1
                for e in self._error_history
                if (now - e["timestamp"]).total_seconds() < 3600
            )
            errors_last_day = sum(
                1
                for e in self._error_history
                if (now - e["timestamp"]).total_seconds() < 86400
            )

            return {
                "total_errors": self._error_count,
                "errors_last_hour": errors_last_hour,
                "errors_last_day": errors_last_day,
                "error_types": dict(self._error_types),
                "recent_errors": recent_errors,
                "last_error": recent_errors[-1] if recent_errors else None,
            }

    async def get_data_quality_stats(self) -> dict[str, Any]:
        """
        Get data quality statistics.

        Returns:
            Dictionary with data quality metrics
        """
        async with self._stats_lock:
            total = self._data_quality["total_data_points"]
            invalid = self._data_quality["invalid_data_points"]

            quality_score = ((total - invalid) / total * 100) if total > 0 else 100.0

            return {
                **self._data_quality,
                "quality_score": quality_score,
                "invalid_rate": (invalid / total) if total > 0 else 0.0,
            }

    async def get_memory_stats(self) -> dict[str, Any]:
        """
        Get memory usage statistics with automatic sampling.

        Returns:
            Dictionary with memory statistics
        """
        async with self._stats_lock:
            # Sample memory if enough time has passed
            current_time = time.time()
            if current_time - self._last_memory_check > 60:  # Sample every minute
                self._last_memory_check = current_time

                # Calculate current memory usage
                memory_mb = self._calculate_memory_usage()

                # Store snapshot
                self._memory_snapshots.append(
                    {
                        "timestamp": datetime.now(),
                        "memory_mb": memory_mb,
                        "error_count": self._error_count,
                        "operation_count": sum(
                            len(t) for t in self._operation_timings.values()
                        ),
                    }
                )

            # Get latest stats
            current_memory = self._calculate_memory_usage()
            memory_trend = []
            if len(self._memory_snapshots) >= 2:
                memory_trend = [
                    s["memory_mb"] for s in list(self._memory_snapshots)[-10:]
                ]

            return {
                "current_memory_mb": current_memory,
                "memory_trend": memory_trend,
                "peak_memory_mb": max(s["memory_mb"] for s in self._memory_snapshots)
                if self._memory_snapshots
                else current_memory,
                "avg_memory_mb": sum(s["memory_mb"] for s in self._memory_snapshots)
                / len(self._memory_snapshots)
                if self._memory_snapshots
                else current_memory,
            }

    async def export_stats(self, format: str = "json") -> dict[str, Any] | str:
        """
        Export statistics in specified format.

        Args:
            format: Export format (json, prometheus, etc.)

        Returns:
            Exported statistics
        """
        async with self._stats_lock:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "component": self.__class__.__name__,
                "performance": await self.get_performance_metrics(),
                "errors": await self.get_error_stats(),
                "data_quality": await self.get_data_quality_stats(),
                "memory": await self.get_memory_stats(),
                "component_specific": self._sanitize_for_export(self._component_stats),
            }

            if format == "prometheus":
                return self._format_prometheus(stats)

            return stats

    async def cleanup_old_stats(self) -> None:
        """
        Clean up statistics older than retention period.
        """
        async with self._stats_lock:
            cutoff_time = datetime.now() - timedelta(hours=self._retention_hours)

            # Clean up error history
            while (
                self._error_history
                and self._error_history[0]["timestamp"] < cutoff_time
            ):
                self._error_history.popleft()

            # Clean up memory snapshots
            while (
                self._memory_snapshots
                and self._memory_snapshots[0]["timestamp"] < cutoff_time
            ):
                self._memory_snapshots.popleft()

            # Clean up data gaps
            if "data_gaps" in self._data_quality:
                self._data_quality["data_gaps"] = [
                    gap
                    for gap in self._data_quality["data_gaps"]
                    if gap.get("timestamp", datetime.min) >= cutoff_time
                ]

            logger.debug(f"Cleaned up stats older than {cutoff_time}")

    async def _cleanup_old_stats_if_needed(self) -> None:
        """
        Check if cleanup is needed and perform it.
        """
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._last_cleanup = current_time
            await self.cleanup_old_stats()

    def _calculate_memory_usage(self) -> float:
        """
        Calculate current memory usage of this component.

        Returns:
            Memory usage in MB
        """
        size = 0

        # Check common attributes
        attrs_to_check = [
            "_error_history",
            "_error_types",
            "_api_timings",
            "_operation_timings",
            "_memory_snapshots",
            "_network_stats",
            "_data_quality",
            "_component_stats",
            # Component-specific attributes
            "tracked_orders",
            "order_status_cache",
            "position_orders",
            "_orders",
            "_positions",
            "_trades",
            "_bars",
            "_ticks",
            "stats",
            "_data",
            "_order_history",
            "_position_history",
        ]

        for attr_name in attrs_to_check:
            if hasattr(self, attr_name):
                attr = getattr(self, attr_name)
                size += sys.getsizeof(attr)

                # For collections, also count items
                if isinstance(attr, (list, dict, set, deque)):
                    try:
                        for item in attr.values() if isinstance(attr, dict) else attr:
                            size += sys.getsizeof(item)
                    except (AttributeError, TypeError):
                        pass

        return size / (1024 * 1024)

    def _calculate_percentile(
        self, data: deque[float] | list[float], percentile: int
    ) -> float:
        """
        Calculate percentile value from data.

        Args:
            data: Data points
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value
        """
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        if index >= len(sorted_data):
            index = len(sorted_data) - 1

        return sorted_data[index]

    def _sanitize_for_export(self, data: Any) -> Any:
        """
        Sanitize data for export by removing PII.

        Args:
            data: Data to sanitize

        Returns:
            Sanitized data
        """
        if isinstance(data, dict):
            sanitized = {}
            sensitive_keys = {
                "password",
                "token",
                "key",
                "secret",
                "auth",
                "credential",
            }

            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = self._sanitize_for_export(value)

            return sanitized
        elif isinstance(data, (list, tuple)):
            return [self._sanitize_for_export(item) for item in data]
        else:
            return data

    def _format_prometheus(self, stats: dict[str, Any]) -> str:
        """
        Format statistics for Prometheus export.

        Args:
            stats: Statistics dictionary

        Returns:
            Prometheus-formatted string
        """
        lines = []
        component = stats["component"].lower()

        # Performance metrics
        if "performance" in stats:
            perf = stats["performance"]
            if "api_stats" in perf and perf["api_stats"]:
                lines.append(
                    f"# HELP {component}_api_response_time_ms API response time in milliseconds"
                )
                lines.append(f"# TYPE {component}_api_response_time_ms summary")
                lines.append(
                    f'{component}_api_response_time_ms{{quantile="0.5"}} {perf["api_stats"].get("p50_response_time_ms", 0)}'
                )
                lines.append(
                    f'{component}_api_response_time_ms{{quantile="0.95"}} {perf["api_stats"].get("p95_response_time_ms", 0)}'
                )
                lines.append(
                    f"{component}_api_response_time_ms_sum {perf['api_stats'].get('avg_response_time_ms', 0)}"
                )

            if "network_stats" in perf:
                net = perf["network_stats"]
                lines.append(
                    f"# HELP {component}_requests_total Total number of requests"
                )
                lines.append(f"# TYPE {component}_requests_total counter")
                lines.append(
                    f"{component}_requests_total {net.get('total_requests', 0)}"
                )

                lines.append(
                    f"# HELP {component}_request_success_rate Request success rate"
                )
                lines.append(f"# TYPE {component}_request_success_rate gauge")
                lines.append(
                    f"{component}_request_success_rate {net.get('success_rate', 0)}"
                )

        # Error metrics
        if "errors" in stats:
            err = stats["errors"]
            lines.append(f"# HELP {component}_errors_total Total number of errors")
            lines.append(f"# TYPE {component}_errors_total counter")
            lines.append(f"{component}_errors_total {err.get('total_errors', 0)}")

        # Memory metrics
        if "memory" in stats:
            mem = stats["memory"]
            lines.append(
                f"# HELP {component}_memory_usage_mb Memory usage in megabytes"
            )
            lines.append(f"# TYPE {component}_memory_usage_mb gauge")
            lines.append(
                f"{component}_memory_usage_mb {mem.get('current_memory_mb', 0)}"
            )

        return "\n".join(lines)
