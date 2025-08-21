"""
Statistics export module for ProjectX SDK.

Provides export functionality for statistics in multiple formats:
- JSON (human-readable, pretty-printed)
- Prometheus (metrics format for monitoring)
- CSV (tabular data export)
- Datadog (optional, for Datadog metrics)
"""

import asyncio
import csv
import json
import re
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional, Union

from project_x_py.types.stats_types import ComprehensiveStats


class StatsExporter:
    """Export statistics in multiple formats for monitoring and analysis."""

    # Sensitive fields to sanitize
    SENSITIVE_FIELDS = {
        "account_id",
        "account_number",
        "token",
        "api_key",
        "password",
        "secret",
        "auth_token",
        "session_token",
        "jwt_token",
        "bearer_token",
    }

    def __init__(self, sanitize_sensitive: bool = True):
        """
        Initialize the stats exporter.

        Args:
            sanitize_sensitive: Whether to sanitize sensitive data fields
        """
        self.sanitize_sensitive = sanitize_sensitive

    async def to_json(
        self,
        stats: ComprehensiveStats,
        pretty: bool = False,
        include_timestamp: bool = True,
    ) -> str:
        """
        Export statistics as JSON.

        Args:
            stats: Statistics to export
            pretty: Whether to pretty-print the JSON
            include_timestamp: Whether to include export timestamp

        Returns:
            JSON string representation of stats
        """
        data = self._stats_to_dict(stats)

        if include_timestamp:
            data["export_timestamp"] = datetime.utcnow().isoformat() + "Z"

        if self.sanitize_sensitive:
            data = self._sanitize_data(data)

        if pretty:
            return json.dumps(data, indent=2, sort_keys=True, default=str)
        else:
            return json.dumps(data, separators=(",", ":"), default=str)

    async def to_prometheus(
        self, stats: ComprehensiveStats, prefix: str = "projectx"
    ) -> str:
        """
        Export statistics in Prometheus format.

        Args:
            stats: Statistics to export
            prefix: Metric name prefix

        Returns:
            Prometheus format string
        """
        lines = []
        timestamp = int(datetime.utcnow().timestamp() * 1000)

        # Health metrics
        if stats.health:
            metric_name = f"{prefix}_health_score"
            lines.append(f"# HELP {metric_name} Overall system health score (0-100)")
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{metric_name} {stats.health.overall_score} {timestamp}")

            # Component health
            for component, score in stats.health.component_scores.items():
                component_clean = self._sanitize_prometheus_label(component)
                lines.append(
                    f'{prefix}_component_health{{component="{component_clean}"}} {score} {timestamp}'
                )

        # Performance metrics
        if stats.performance:
            # API calls
            if stats.performance.api_calls_total:
                metric_name = f"{prefix}_api_calls_total"
                lines.append(f"# HELP {metric_name} Total number of API calls")
                lines.append(f"# TYPE {metric_name} counter")
                lines.append(
                    f"{metric_name} {stats.performance.api_calls_total} {timestamp}"
                )

            # Cache metrics
            if stats.performance.cache_hit_rate is not None:
                metric_name = f"{prefix}_cache_hit_rate"
                lines.append(f"# HELP {metric_name} Cache hit rate (0-1)")
                lines.append(f"# TYPE {metric_name} gauge")
                lines.append(
                    f"{metric_name} {stats.performance.cache_hit_rate} {timestamp}"
                )

            # Response time
            if stats.performance.avg_response_time is not None:
                metric_name = f"{prefix}_response_time_seconds"
                lines.append(f"# HELP {metric_name} Average response time in seconds")
                lines.append(f"# TYPE {metric_name} gauge")
                lines.append(
                    f"{metric_name} {stats.performance.avg_response_time} {timestamp}"
                )

        # Memory metrics
        if stats.memory:
            # Total memory
            if stats.memory.total_memory_mb:
                metric_name = f"{prefix}_memory_total_mb"
                lines.append(f"# HELP {metric_name} Total memory usage in MB")
                lines.append(f"# TYPE {metric_name} gauge")
                lines.append(
                    f"{metric_name} {stats.memory.total_memory_mb} {timestamp}"
                )

            # Component memory
            for component, memory_mb in stats.memory.component_memory.items():
                component_clean = self._sanitize_prometheus_label(component)
                lines.append(
                    f'{prefix}_component_memory_mb{{component="{component_clean}"}} {memory_mb} {timestamp}'
                )

        # Error metrics
        if stats.errors:
            # Total errors
            if stats.errors.total_errors:
                metric_name = f"{prefix}_errors_total"
                lines.append(f"# HELP {metric_name} Total number of errors")
                lines.append(f"# TYPE {metric_name} counter")
                lines.append(f"{metric_name} {stats.errors.total_errors} {timestamp}")

            # Error rate
            if stats.errors.error_rate is not None:
                metric_name = f"{prefix}_error_rate"
                lines.append(f"# HELP {metric_name} Error rate (0-1)")
                lines.append(f"# TYPE {metric_name} gauge")
                lines.append(f"{metric_name} {stats.errors.error_rate} {timestamp}")

            # Errors by component
            for component, count in stats.errors.errors_by_component.items():
                component_clean = self._sanitize_prometheus_label(component)
                lines.append(
                    f'{prefix}_component_errors_total{{component="{component_clean}"}} {count} {timestamp}'
                )

        # Connection metrics
        if stats.connections:
            # Active connections
            if stats.connections.active_connections:
                metric_name = f"{prefix}_connections_active"
                lines.append(f"# HELP {metric_name} Number of active connections")
                lines.append(f"# TYPE {metric_name} gauge")
                lines.append(
                    f"{metric_name} {stats.connections.active_connections} {timestamp}"
                )

            # Connection status by type
            for conn_type, status in stats.connections.connection_status.items():
                conn_type_clean = self._sanitize_prometheus_label(conn_type)
                status_value = 1 if status == "connected" else 0
                lines.append(
                    f'{prefix}_connection_status{{type="{conn_type_clean}"}} {status_value} {timestamp}'
                )

        return "\n".join(lines) + "\n"

    async def to_csv(
        self, stats: ComprehensiveStats, include_timestamp: bool = True
    ) -> str:
        """
        Export statistics as CSV.

        Args:
            stats: Statistics to export
            include_timestamp: Whether to include export timestamp

        Returns:
            CSV string representation of stats
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        headers = ["metric_category", "metric_name", "value", "component"]
        if include_timestamp:
            headers.append("timestamp")

        writer.writerow(headers)

        timestamp = datetime.utcnow().isoformat() + "Z" if include_timestamp else None

        # Flatten stats into rows
        rows = []

        # Health metrics
        if stats.health:
            rows.append(
                ["health", "overall_score", stats.health.overall_score, "system"]
            )
            for component, score in stats.health.component_scores.items():
                rows.append(["health", "component_score", score, component])

        # Performance metrics
        if stats.performance:
            if stats.performance.api_calls_total:
                rows.append(
                    [
                        "performance",
                        "api_calls_total",
                        stats.performance.api_calls_total,
                        "system",
                    ]
                )
            if stats.performance.cache_hit_rate is not None:
                rows.append(
                    [
                        "performance",
                        "cache_hit_rate",
                        stats.performance.cache_hit_rate,
                        "system",
                    ]
                )
            if stats.performance.avg_response_time is not None:
                rows.append(
                    [
                        "performance",
                        "avg_response_time",
                        stats.performance.avg_response_time,
                        "system",
                    ]
                )

        # Memory metrics
        if stats.memory:
            if stats.memory.total_memory_mb:
                rows.append(
                    [
                        "memory",
                        "total_memory_mb",
                        stats.memory.total_memory_mb,
                        "system",
                    ]
                )
            for component, memory_mb in stats.memory.component_memory.items():
                rows.append(["memory", "component_memory_mb", memory_mb, component])

        # Error metrics
        if stats.errors:
            if stats.errors.total_errors:
                rows.append(
                    ["errors", "total_errors", stats.errors.total_errors, "system"]
                )
            if stats.errors.error_rate is not None:
                rows.append(["errors", "error_rate", stats.errors.error_rate, "system"])
            for component, count in stats.errors.errors_by_component.items():
                rows.append(["errors", "component_errors", count, component])

        # Connection metrics
        if stats.connections:
            if stats.connections.active_connections:
                rows.append(
                    [
                        "connections",
                        "active_connections",
                        stats.connections.active_connections,
                        "system",
                    ]
                )
            for conn_type, status in stats.connections.connection_status.items():
                rows.append(["connections", "connection_status", status, conn_type])

        # Write rows
        for row in rows:
            if include_timestamp:
                row.append(timestamp)
            writer.writerow(row)

        return output.getvalue()

    async def to_datadog(
        self, stats: ComprehensiveStats, prefix: str = "projectx"
    ) -> Dict[str, Any]:
        """
        Export statistics for Datadog.

        Args:
            stats: Statistics to export
            prefix: Metric name prefix

        Returns:
            Dictionary formatted for Datadog API
        """
        metrics = []
        timestamp = int(datetime.utcnow().timestamp())

        # Health metrics
        if stats.health:
            metrics.append(
                {
                    "metric": f"{prefix}.health.overall_score",
                    "points": [[timestamp, stats.health.overall_score]],
                    "type": "gauge",
                    "tags": ["service:projectx"],
                }
            )

            for component, score in stats.health.component_scores.items():
                metrics.append(
                    {
                        "metric": f"{prefix}.health.component_score",
                        "points": [[timestamp, score]],
                        "type": "gauge",
                        "tags": [f"service:projectx", f"component:{component}"],
                    }
                )

        # Performance metrics
        if stats.performance:
            if stats.performance.api_calls_total:
                metrics.append(
                    {
                        "metric": f"{prefix}.performance.api_calls_total",
                        "points": [[timestamp, stats.performance.api_calls_total]],
                        "type": "count",
                        "tags": ["service:projectx"],
                    }
                )

            if stats.performance.cache_hit_rate is not None:
                metrics.append(
                    {
                        "metric": f"{prefix}.performance.cache_hit_rate",
                        "points": [[timestamp, stats.performance.cache_hit_rate]],
                        "type": "gauge",
                        "tags": ["service:projectx"],
                    }
                )

            if stats.performance.avg_response_time is not None:
                metrics.append(
                    {
                        "metric": f"{prefix}.performance.avg_response_time",
                        "points": [[timestamp, stats.performance.avg_response_time]],
                        "type": "gauge",
                        "tags": ["service:projectx"],
                    }
                )

        # Memory metrics
        if stats.memory:
            if stats.memory.total_memory_mb:
                metrics.append(
                    {
                        "metric": f"{prefix}.memory.total_mb",
                        "points": [[timestamp, stats.memory.total_memory_mb]],
                        "type": "gauge",
                        "tags": ["service:projectx"],
                    }
                )

            for component, memory_mb in stats.memory.component_memory.items():
                metrics.append(
                    {
                        "metric": f"{prefix}.memory.component_mb",
                        "points": [[timestamp, memory_mb]],
                        "type": "gauge",
                        "tags": [f"service:projectx", f"component:{component}"],
                    }
                )

        # Error metrics
        if stats.errors:
            if stats.errors.total_errors:
                metrics.append(
                    {
                        "metric": f"{prefix}.errors.total",
                        "points": [[timestamp, stats.errors.total_errors]],
                        "type": "count",
                        "tags": ["service:projectx"],
                    }
                )

            if stats.errors.error_rate is not None:
                metrics.append(
                    {
                        "metric": f"{prefix}.errors.rate",
                        "points": [[timestamp, stats.errors.error_rate]],
                        "type": "gauge",
                        "tags": ["service:projectx"],
                    }
                )

            for component, count in stats.errors.errors_by_component.items():
                metrics.append(
                    {
                        "metric": f"{prefix}.errors.component_total",
                        "points": [[timestamp, count]],
                        "type": "count",
                        "tags": [f"service:projectx", f"component:{component}"],
                    }
                )

        # Connection metrics
        if stats.connections:
            if stats.connections.active_connections:
                metrics.append(
                    {
                        "metric": f"{prefix}.connections.active",
                        "points": [[timestamp, stats.connections.active_connections]],
                        "type": "gauge",
                        "tags": ["service:projectx"],
                    }
                )

            for conn_type, status in stats.connections.connection_status.items():
                status_value = 1 if status == "connected" else 0
                metrics.append(
                    {
                        "metric": f"{prefix}.connections.status",
                        "points": [[timestamp, status_value]],
                        "type": "gauge",
                        "tags": [f"service:projectx", f"type:{conn_type}"],
                    }
                )

        return {"series": metrics}

    async def export(
        self, stats: ComprehensiveStats, format: str = "json", **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """
        Generic export method.

        Args:
            stats: Statistics to export
            format: Export format ('json', 'prometheus', 'csv', 'datadog')
            **kwargs: Format-specific options

        Returns:
            Exported data as string or dict

        Raises:
            ValueError: If format is not supported
        """
        format = format.lower()

        if format == "json":
            return await self.to_json(stats, **kwargs)
        elif format == "prometheus":
            return await self.to_prometheus(stats, **kwargs)
        elif format == "csv":
            return await self.to_csv(stats, **kwargs)
        elif format == "datadog":
            return await self.to_datadog(stats, **kwargs)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _stats_to_dict(self, stats: ComprehensiveStats) -> Dict[str, Any]:
        """Convert ComprehensiveStats to dictionary."""
        result = {}

        if stats.health:
            result["health"] = {
                "overall_score": stats.health.overall_score,
                "component_scores": dict(stats.health.component_scores),
                "issues": list(stats.health.issues),
            }

        if stats.performance:
            result["performance"] = {
                "api_calls_total": stats.performance.api_calls_total,
                "cache_hit_rate": stats.performance.cache_hit_rate,
                "avg_response_time": stats.performance.avg_response_time,
                "requests_per_second": stats.performance.requests_per_second,
            }

        if stats.memory:
            result["memory"] = {
                "total_memory_mb": stats.memory.total_memory_mb,
                "component_memory": dict(stats.memory.component_memory),
                "peak_memory_mb": stats.memory.peak_memory_mb,
            }

        if stats.errors:
            result["errors"] = {
                "total_errors": stats.errors.total_errors,
                "error_rate": stats.errors.error_rate,
                "errors_by_component": dict(stats.errors.errors_by_component),
                "recent_errors": [
                    {
                        "timestamp": error.timestamp.isoformat()
                        if error.timestamp
                        else None,
                        "component": error.component,
                        "error_type": error.error_type,
                        "message": error.message,
                        "severity": error.severity,
                    }
                    for error in stats.errors.recent_errors
                ],
            }

        if stats.connections:
            result["connections"] = {
                "active_connections": stats.connections.active_connections,
                "connection_status": dict(stats.connections.connection_status),
                "connection_uptime": dict(stats.connections.connection_uptime),
            }

        if stats.trading:
            result["trading"] = {
                "orders_today": stats.trading.orders_today,
                "fills_today": stats.trading.fills_today,
                "active_positions": stats.trading.active_positions,
                "pnl_today": float(stats.trading.pnl_today)
                if stats.trading.pnl_today
                else None,
            }

        return result

    def _sanitize_data(self, data: Any) -> Any:
        """Recursively sanitize sensitive data."""
        if isinstance(data, dict):
            return {
                key: "***REDACTED***"
                if key.lower() in self.SENSITIVE_FIELDS
                else self._sanitize_data(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data

    def _sanitize_prometheus_label(self, label: str) -> str:
        """Sanitize label for Prometheus format."""
        # Replace invalid characters with underscores
        return re.sub(r"[^a-zA-Z0-9_]", "_", label)
