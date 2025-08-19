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
from typing import Any

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
        self._data_quality: dict[str, Any] = {
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

        # Fine-grained locks for different stat categories
        # This prevents deadlocks by allowing concurrent access to different stat types
        self._error_lock = asyncio.Lock()  # For error tracking
        self._timing_lock = asyncio.Lock()  # For performance timings
        self._network_lock = asyncio.Lock()  # For network stats
        self._data_quality_lock = asyncio.Lock()  # For data quality metrics
        self._memory_lock = asyncio.Lock()  # For memory snapshots
        self._component_lock = asyncio.Lock()  # For component-specific stats

        # Legacy lock for backward compatibility (will be phased out)
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
        # Use timing lock for operation timings
        async with self._timing_lock:
            # Update operation timings
            if operation not in self._operation_timings:
                self._operation_timings[operation] = deque(maxlen=self._max_timings)
            self._operation_timings[operation].append(duration_ms)

            # Update activity timestamp
            self._last_activity = datetime.now()

        # Use network lock for network stats
        if metadata and ("bytes_sent" in metadata or "bytes_received" in metadata):
            async with self._network_lock:
                if "bytes_sent" in metadata:
                    self._network_stats["total_bytes_sent"] += metadata["bytes_sent"]
                if "bytes_received" in metadata:
                    self._network_stats["total_bytes_received"] += metadata[
                        "bytes_received"
                    ]

        # Update request counts with network lock
        async with self._network_lock:
            self._network_stats["total_requests"] += 1
            if success:
                self._network_stats["successful_requests"] += 1
            else:
                self._network_stats["failed_requests"] += 1

        # Trigger cleanup if needed (no lock needed for time check)
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
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
        # Sanitize details outside of lock to minimize lock time
        sanitized_details = self._sanitize_for_export(details) if details else None
        error_type = type(error).__name__

        async with self._error_lock:
            self._error_count += 1

            # Update error type counts
            self._error_types[error_type] = self._error_types.get(error_type, 0) + 1

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
        async with self._data_quality_lock:
            # Type-safe integer updates with validation
            def safe_int(value: Any, default: int = 0) -> int:
                """Safely convert value to int with validation."""
                if value is None:
                    return default
                if isinstance(value, int | float):
                    return int(value)
                if isinstance(value, str) and value.isdigit():
                    return int(value)
                logger.warning(f"Invalid numeric value for data quality: {value}")
                return default

            current_total = safe_int(self._data_quality.get("total_data_points", 0))
            current_invalid = safe_int(self._data_quality.get("invalid_data_points", 0))
            current_missing = safe_int(self._data_quality.get("missing_data_points", 0))
            current_duplicate = safe_int(
                self._data_quality.get("duplicate_data_points", 0)
            )

            self._data_quality["total_data_points"] = current_total + total_points
            self._data_quality["invalid_data_points"] = current_invalid + invalid_points
            self._data_quality["missing_data_points"] = current_missing + missing_points
            self._data_quality["duplicate_data_points"] = (
                current_duplicate + duplicate_points
            )
            self._data_quality["last_validation"] = datetime.now()

    def get_performance_metrics(self) -> dict[str, Any]:
        """
        Get detailed performance metrics.

        Returns:
            Dictionary with performance statistics
        """
        # Note: This is now synchronous but thread-safe
        # We make quick copies to minimize time under locks

        # Make copies of timing data
        operation_timings_copy = {
            op_name: list(timings)
            for op_name, timings in self._operation_timings.items()
        }
        api_timings_copy = list(self._api_timings)
        last_activity_copy = self._last_activity

        # Copy network stats
        network_stats_copy = dict(self._network_stats)

        # Now calculate metrics without holding any locks
        operation_stats = {}
        for op_name, timings in operation_timings_copy.items():
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
        if api_timings_copy:
            api_stats = {
                "avg_response_time_ms": sum(api_timings_copy) / len(api_timings_copy),
                "min_response_time_ms": min(api_timings_copy),
                "max_response_time_ms": max(api_timings_copy),
                "p50_response_time_ms": self._calculate_percentile(
                    api_timings_copy, 50
                ),
                "p95_response_time_ms": self._calculate_percentile(
                    api_timings_copy, 95
                ),
            }

        # Calculate network metrics
        success_rate = (
            network_stats_copy["successful_requests"]
            / network_stats_copy["total_requests"]
            if network_stats_copy["total_requests"] > 0
            else 0.0
        )

        return {
            "operation_stats": operation_stats,
            "api_stats": api_stats,
            "network_stats": {
                **network_stats_copy,
                "success_rate": success_rate,
            },
            "uptime_seconds": time.time() - self._start_time,
            "last_activity": last_activity_copy.isoformat()
            if last_activity_copy
            else None,
        }

    def get_error_stats(self) -> dict[str, Any]:
        """
        Get enhanced error statistics.

        Returns:
            Dictionary with error statistics
        """
        # Note: This is now synchronous but thread-safe
        # We make quick copies to minimize time accessing shared data

        error_count_copy = self._error_count
        error_history_copy = list(self._error_history)
        error_types_copy = dict(self._error_types)

        # Now calculate metrics without holding lock
        recent_errors = error_history_copy[-10:]  # Last 10 errors

        # Calculate error rate over time windows
        now = datetime.now()
        errors_last_hour = sum(
            1
            for e in error_history_copy
            if (now - e["timestamp"]).total_seconds() < 3600
        )
        errors_last_day = sum(
            1
            for e in error_history_copy
            if (now - e["timestamp"]).total_seconds() < 86400
        )

        return {
            "total_errors": error_count_copy,
            "errors_last_hour": errors_last_hour,
            "errors_last_day": errors_last_day,
            "error_types": error_types_copy,
            "recent_errors": recent_errors,
            "last_error": recent_errors[-1] if recent_errors else None,
        }

    def get_data_quality_stats(self) -> dict[str, Any]:
        """
        Get data quality statistics.

        Returns:
            Dictionary with data quality metrics
        """
        # Note: This is now synchronous but thread-safe
        # We make quick copies to minimize time accessing shared data

        data_quality_copy = dict(self._data_quality)

        # Now calculate metrics without holding lock
        # Safe integer conversion with validation
        def safe_int(value: Any, default: int = 0) -> int:
            """Safely convert value to int with validation."""
            if value is None:
                return default
            if isinstance(value, int | float):
                return int(value)
            if isinstance(value, str) and value.isdigit():
                return int(value)
            return default

        total = safe_int(data_quality_copy.get("total_data_points", 0))
        invalid = safe_int(data_quality_copy.get("invalid_data_points", 0))

        quality_score = ((total - invalid) / total * 100) if total > 0 else 100.0

        return {
            **data_quality_copy,
            "quality_score": quality_score,
            "invalid_rate": (invalid / total) if total > 0 else 0.0,
        }

    def get_enhanced_memory_stats(self) -> dict[str, Any]:
        """
        Get enhanced memory usage statistics with automatic sampling.

        Returns:
            Dictionary with memory statistics
        """
        # Sample memory if enough time has passed
        current_time = time.time()
        should_sample = current_time - self._last_memory_check > 60

        if should_sample:
            # Calculate current memory usage
            memory_mb = self._calculate_memory_usage()

            # Get error count for snapshot
            error_count = self._error_count

            # Get operation count for snapshot
            operation_count = sum(len(t) for t in self._operation_timings.values())

            # Store snapshot
            self._last_memory_check = current_time
            self._memory_snapshots.append(
                {
                    "timestamp": datetime.now(),
                    "memory_mb": memory_mb,
                    "error_count": error_count,
                    "operation_count": operation_count,
                }
            )

        # Get latest stats and copy snapshots
        current_memory = self._calculate_memory_usage()

        snapshots_copy = list(self._memory_snapshots)

        # Calculate trends without lock
        memory_trend = []
        if len(snapshots_copy) >= 2:
            memory_trend = [s["memory_mb"] for s in snapshots_copy[-10:]]

        return {
            "current_memory_mb": current_memory,
            "memory_trend": memory_trend,
            "peak_memory_mb": max(s["memory_mb"] for s in snapshots_copy)
            if snapshots_copy
            else current_memory,
            "avg_memory_mb": sum(s["memory_mb"] for s in snapshots_copy)
            / len(snapshots_copy)
            if snapshots_copy
            else current_memory,
        }

    def export_stats(self, format: str = "json") -> dict[str, Any] | str:
        """
        Export statistics in specified format.

        Args:
            format: Export format (json, prometheus, etc.)

        Returns:
            Exported statistics
        """
        # Get all stats (now all synchronous)
        performance = self.get_performance_metrics()
        errors = self.get_error_stats()
        data_quality = self.get_data_quality_stats()
        memory = self.get_enhanced_memory_stats()

        # Get component stats
        component_stats_copy = dict(self._component_stats)

        stats = {
            "timestamp": datetime.now().isoformat(),
            "component": self.__class__.__name__,
            "performance": performance,
            "errors": errors,
            "data_quality": data_quality,
            "memory": memory,
            "component_specific": self._sanitize_for_export(component_stats_copy),
        }

        if format == "prometheus":
            return self._format_prometheus(stats)

        return stats

    async def cleanup_old_stats(self) -> None:
        """
        Clean up statistics older than retention period.
        """
        cutoff_time = datetime.now() - timedelta(hours=self._retention_hours)

        # Clean up error history with error lock
        async with self._error_lock:
            while (
                self._error_history
                and self._error_history[0]["timestamp"] < cutoff_time
            ):
                self._error_history.popleft()

        # Clean up memory snapshots with memory lock
        async with self._memory_lock:
            while (
                self._memory_snapshots
                and self._memory_snapshots[0]["timestamp"] < cutoff_time
            ):
                self._memory_snapshots.popleft()

        # Clean up data gaps with data quality lock
        async with self._data_quality_lock:
            if "data_gaps" in self._data_quality:
                gaps = self._data_quality.get("data_gaps", [])
                if isinstance(gaps, list):
                    self._data_quality["data_gaps"] = [
                        gap
                        for gap in gaps
                        if isinstance(gap, dict)
                        and gap.get("timestamp", datetime.min) >= cutoff_time
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

        Thread-safe memory calculation.

        Returns:
            Memory usage in MB
        """
        size = 0
        max_items_to_sample = 100  # Sample limit for large collections

        # Priority attributes to check
        priority_attrs = [
            "_error_history",
            "_error_types",
            "_api_timings",
            "_operation_timings",
            "_memory_snapshots",
            "_network_stats",
            "_data_quality",
            "_component_stats",
        ]

        # Calculate size for each attribute (synchronous access)
        for attr_name in priority_attrs:
            if hasattr(self, attr_name):
                attr = getattr(self, attr_name)
                size += sys.getsizeof(attr)

                # For small collections, count all items
                if isinstance(attr, list | dict | set | deque):
                    try:
                        items = attr.values() if isinstance(attr, dict) else attr
                        item_count = len(items) if hasattr(items, "__len__") else 0

                        if item_count <= max_items_to_sample:
                            # Count all items for small collections
                            for item in items:
                                size += sys.getsizeof(item)
                        else:
                            # Sample for large collections
                            sample_size = 0
                            for i, item in enumerate(items):
                                if i >= max_items_to_sample:
                                    break
                                sample_size += sys.getsizeof(item)
                            # Estimate total size based on sample
                            if max_items_to_sample > 0:
                                avg_item_size = sample_size / max_items_to_sample
                                size += int(avg_item_size * item_count)
                    except (AttributeError, TypeError):
                        pass

        # Component-specific attributes (check without locks as they're component-owned)
        component_attrs = [
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

        for attr_name in component_attrs:
            if hasattr(self, attr_name):
                attr = getattr(self, attr_name)
                size += sys.getsizeof(attr)

                # Only sample large component collections
                if isinstance(attr, dict) and len(attr) > max_items_to_sample:
                    # Sample a subset
                    sample_size = 0
                    for i, (k, v) in enumerate(attr.items()):
                        if i >= 10:  # Small sample for component attrs
                            break
                        sample_size += sys.getsizeof(k) + sys.getsizeof(v)
                    # Rough estimate
                    if 10 > 0:
                        size += (sample_size // 10) * len(attr)

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
        # Proper percentile calculation with bounds checking
        index = max(
            0, min(len(sorted_data) - 1, int((len(sorted_data) - 1) * percentile / 100))
        )
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
            # Extended list of sensitive keys for trading data
            sensitive_keys = {
                "password",
                "token",
                "key",
                "secret",
                "auth",
                "credential",
                "account_id",
                "accountid",
                "account_name",
                "accountname",
                "balance",
                "equity",
                "pnl",
                "profit",
                "loss",
                "position_size",
                "positionsize",
                "order_size",
                "ordersize",
                "api_key",
                "apikey",
                "session",
                "cookie",
                "username",
                "email",
                "phone",
                "ssn",
                "tax_id",
                "bank",
                "routing",
            }

            for key, value in data.items():
                key_lower = key.lower()
                # Check if key contains any sensitive patterns
                if any(sensitive in key_lower for sensitive in sensitive_keys):
                    # Special handling for certain fields to show partial info
                    if (
                        "account" in key_lower
                        and isinstance(value, str)
                        and len(value) > 4
                    ):
                        # Show last 4 chars of account ID/name
                        sanitized[key] = f"***{value[-4:]}"
                    elif any(
                        x in key_lower
                        for x in ["pnl", "profit", "loss", "balance", "equity"]
                    ):
                        # Show if positive/negative but not actual value
                        if isinstance(value, int | float):
                            sanitized[key] = (
                                "positive"
                                if value > 0
                                else "negative"
                                if value < 0
                                else "zero"
                            )
                        else:
                            sanitized[key] = "***REDACTED***"
                    else:
                        sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = self._sanitize_for_export(value)

            return sanitized
        elif isinstance(data, list | tuple):
            return [self._sanitize_for_export(item) for item in data]
        elif isinstance(data, str):
            # Check for patterns that look like sensitive data
            if len(data) > 20 and any(c in data for c in ["=", "Bearer", "Basic"]):
                # Might be a token or auth header
                return "***REDACTED***"
            return data
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
            if perf.get("api_stats"):
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
