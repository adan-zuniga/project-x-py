"""
Central statistics aggregation for TradingSuite.

Author: SDK v3.2.1
Date: 2025-01-18

Overview:
    Provides centralized aggregation of statistics from all TradingSuite components
    with async-safe operations and intelligent caching.

Key Features:
    - Aggregates stats from all components
    - Caches results with TTL for performance
    - Async-safe with proper locking
    - Calculates cross-component metrics
    - Supports multiple export formats
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Optional

from project_x_py.types.stats_types import (
    ComponentStats,
    TradingSuiteStats,
)
from project_x_py.utils.logging_config import ProjectXLogger

logger = ProjectXLogger.get_logger(__name__)


class StatisticsAggregator:
    """
    Central aggregator for all TradingSuite component statistics.

    Collects, caches, and aggregates statistics from all components
    with intelligent caching and cross-component metric calculation.
    """

    def __init__(
        self,
        cache_ttl_seconds: int = 5,
        enable_caching: bool = True,
    ):
        """
        Initialize the statistics aggregator.

        Args:
            cache_ttl_seconds: Cache time-to-live in seconds
            enable_caching: Enable result caching
        """
        self._cache_ttl = cache_ttl_seconds
        self._enable_caching = enable_caching
        self._cache: dict[str, Any] = {}
        self._cache_timestamps: dict[str, float] = {}
        self._aggregation_lock = asyncio.Lock()

        # Component references (set by TradingSuite)
        self.trading_suite: Any = None
        self.order_manager: Any = None
        self.position_manager: Any = None
        self.data_manager: Any = None
        self.orderbook: Any = None
        self.risk_manager: Any = None
        self.client: Any = None
        self.realtime_client: Any = None

        logger.debug(
            f"StatisticsAggregator initialized: cache_ttl={cache_ttl_seconds}s"
        )

    async def aggregate_stats(self, force_refresh: bool = False) -> TradingSuiteStats:
        """
        Aggregate statistics from all components.

        Args:
            force_refresh: Force refresh bypassing cache

        Returns:
            Aggregated statistics from all components
        """
        async with self._aggregation_lock:
            # Check cache if enabled
            if self._enable_caching and not force_refresh:
                cached = self._get_cached("aggregate_stats")
                if cached is not None:
                    return cached

            # Collect stats from all components
            stats = await self._collect_all_stats()

            # Calculate cross-component metrics
            stats = await self._calculate_cross_metrics(stats)

            # Cache the result
            if self._enable_caching:
                self._set_cache("aggregate_stats", stats)

            return stats

    async def _collect_all_stats(self) -> TradingSuiteStats:
        """
        Collect statistics from all components.

        Returns:
            Raw statistics from all components
        """
        suite = self.trading_suite
        if not suite:
            return self._get_empty_stats()

        # Get basic suite info
        uptime_seconds = (
            int((datetime.now() - suite._created_at).total_seconds())
            if hasattr(suite, "_created_at")
            else 0
        )

        # Initialize components dictionary
        components: dict[str, ComponentStats] = {}

        # Collect OrderManager stats
        if self.order_manager:
            components["order_manager"] = await self._get_order_manager_stats(
                uptime_seconds
            )

        # Collect PositionManager stats
        if self.position_manager:
            components["position_manager"] = await self._get_position_manager_stats(
                uptime_seconds
            )

        # Collect RealtimeDataManager stats
        if self.data_manager:
            components["data_manager"] = await self._get_data_manager_stats(
                uptime_seconds
            )

        # Collect OrderBook stats
        if self.orderbook:
            components["orderbook"] = await self._get_orderbook_stats(uptime_seconds)

        # Collect RiskManager stats
        if self.risk_manager:
            components["risk_manager"] = await self._get_risk_manager_stats(
                uptime_seconds
            )

        # Get client performance stats
        client_stats = await self._get_client_stats()

        # Get realtime connection stats
        realtime_stats = await self._get_realtime_stats()

        return {
            "suite_id": getattr(suite, "suite_id", "unknown"),
            "instrument": suite.instrument_id or suite._symbol if suite else "unknown",
            "created_at": getattr(suite, "_created_at", datetime.now()).isoformat(),
            "uptime_seconds": uptime_seconds,
            "status": "active" if suite and suite.is_connected else "disconnected",
            "connected": suite.is_connected if suite else False,
            "components": components,
            **client_stats,
            **realtime_stats,
            "features_enabled": [f.value for f in suite.config.features]
            if suite
            else [],
            "timeframes": suite.config.timeframes if suite else [],
        }

    async def _get_order_manager_stats(self, uptime_seconds: int) -> ComponentStats:
        """Get OrderManager statistics."""
        om = self.order_manager
        if not om:
            return self._get_empty_component_stats("OrderManager", uptime_seconds)

        # Get enhanced stats if available
        if hasattr(om, "get_performance_metrics"):
            perf_metrics = await om.get_performance_metrics()
        else:
            perf_metrics = {}

        # Get error stats
        if hasattr(om, "get_error_stats"):
            error_stats = await om.get_error_stats()
            error_count = error_stats.get("total_errors", 0)
        else:
            error_count = 0

        # Get memory usage
        if hasattr(om, "get_memory_stats"):
            memory_stats = await om.get_memory_stats()
            memory_mb = memory_stats.get("current_memory_mb", 0.0)
        elif hasattr(om, "get_memory_usage_mb"):
            memory_mb = om.get_memory_usage_mb()
        else:
            memory_mb = 0.0

        # Get last activity
        last_activity_obj = (
            om.stats.get("last_order_time") if hasattr(om, "stats") else None
        )

        return ComponentStats(
            name="OrderManager",
            status="connected",
            uptime_seconds=uptime_seconds,
            last_activity=last_activity_obj.isoformat() if last_activity_obj else None,
            error_count=error_count,
            memory_usage_mb=memory_mb,
            performance_metrics=perf_metrics,
        )

    async def _get_position_manager_stats(self, uptime_seconds: int) -> ComponentStats:
        """Get PositionManager statistics."""
        pm = self.position_manager
        if not pm:
            return self._get_empty_component_stats("PositionManager", uptime_seconds)

        # Get enhanced stats if available
        if hasattr(pm, "get_performance_metrics"):
            perf_metrics = await pm.get_performance_metrics()
        else:
            perf_metrics = {}

        # Get error stats
        if hasattr(pm, "get_error_stats"):
            error_stats = await pm.get_error_stats()
            error_count = error_stats.get("total_errors", 0)
        else:
            error_count = 0

        # Get memory usage
        if hasattr(pm, "get_memory_stats"):
            memory_stats = await pm.get_memory_stats()
            memory_mb = memory_stats.get("current_memory_mb", 0.0)
        elif hasattr(pm, "get_memory_usage_mb"):
            memory_mb = pm.get_memory_usage_mb()
        else:
            memory_mb = 0.0

        # Get last activity
        last_activity_obj = (
            pm.stats.get("last_position_update") if hasattr(pm, "stats") else None
        )

        return ComponentStats(
            name="PositionManager",
            status="connected",
            uptime_seconds=uptime_seconds,
            last_activity=last_activity_obj.isoformat() if last_activity_obj else None,
            error_count=error_count,
            memory_usage_mb=memory_mb,
            performance_metrics=perf_metrics,
        )

    async def _get_data_manager_stats(self, uptime_seconds: int) -> ComponentStats:
        """Get RealtimeDataManager statistics."""
        dm = self.data_manager
        if not dm:
            return self._get_empty_component_stats(
                "RealtimeDataManager", uptime_seconds
            )

        # Get memory stats which include performance metrics
        if hasattr(dm, "get_memory_stats"):
            memory_stats = dm.get_memory_stats()
            memory_mb = memory_stats.get("memory_usage_mb", 0.0)
            error_count = memory_stats.get("data_validation_errors", 0)
            last_activity_obj = memory_stats.get("last_update")

            # Extract performance metrics
            perf_metrics = {
                "ticks_processed": memory_stats.get("ticks_processed", 0),
                "quotes_processed": memory_stats.get("quotes_processed", 0),
                "trades_processed": memory_stats.get("trades_processed", 0),
                "total_bars": memory_stats.get("total_bars", 0),
                "websocket_messages": memory_stats.get("websocket_messages", 0),
            }
        else:
            memory_mb = 0.0
            error_count = 0
            last_activity_obj = None
            perf_metrics = {}

        return ComponentStats(
            name="RealtimeDataManager",
            status="connected" if dm.is_running else "disconnected",
            uptime_seconds=uptime_seconds,
            last_activity=last_activity_obj.isoformat() if last_activity_obj else None,
            error_count=error_count,
            memory_usage_mb=memory_mb,
            performance_metrics=perf_metrics,
        )

    async def _get_orderbook_stats(self, uptime_seconds: int) -> ComponentStats:
        """Get OrderBook statistics."""
        ob = self.orderbook
        if not ob:
            return self._get_empty_component_stats("OrderBook", uptime_seconds)

        # Get enhanced stats if available
        if hasattr(ob, "get_performance_metrics"):
            perf_metrics = await ob.get_performance_metrics()
        else:
            perf_metrics = {}

        # Get error stats
        if hasattr(ob, "get_error_stats"):
            error_stats = await ob.get_error_stats()
            error_count = error_stats.get("total_errors", 0)
        else:
            error_count = 0

        # Get memory usage
        if hasattr(ob, "get_memory_stats"):
            memory_stats = await ob.get_memory_stats()
            memory_mb = memory_stats.get("current_memory_mb", 0.0)
        elif hasattr(ob, "get_memory_usage_mb"):
            memory_mb = ob.get_memory_usage_mb()
        else:
            memory_mb = 0.0

        # Get last activity
        last_activity_obj = (
            ob.last_orderbook_update if hasattr(ob, "last_orderbook_update") else None
        )

        return ComponentStats(
            name="OrderBook",
            status="connected",
            uptime_seconds=uptime_seconds,
            last_activity=last_activity_obj.isoformat() if last_activity_obj else None,
            error_count=error_count,
            memory_usage_mb=memory_mb,
            performance_metrics=perf_metrics,
        )

    async def _get_risk_manager_stats(self, uptime_seconds: int) -> ComponentStats:
        """Get RiskManager statistics."""
        rm = self.risk_manager
        if not rm:
            return self._get_empty_component_stats("RiskManager", uptime_seconds)

        # Get enhanced stats if available
        if hasattr(rm, "get_performance_metrics"):
            perf_metrics = await rm.get_performance_metrics()
        else:
            perf_metrics = {}

        # Get error stats
        if hasattr(rm, "get_error_stats"):
            error_stats = await rm.get_error_stats()
            error_count = error_stats.get("total_errors", 0)
        else:
            error_count = 0

        # Get memory usage
        if hasattr(rm, "get_memory_stats"):
            memory_stats = await rm.get_memory_stats()
            memory_mb = memory_stats.get("current_memory_mb", 0.0)
        elif hasattr(rm, "get_memory_usage_mb"):
            memory_mb = rm.get_memory_usage_mb()
        else:
            memory_mb = 0.0

        # Get last activity
        if hasattr(rm, "get_activity_stats"):
            activity_stats = await rm.get_activity_stats()
            last_activity = activity_stats.get("last_activity")
        else:
            last_activity = None

        return ComponentStats(
            name="RiskManager",
            status="active",
            uptime_seconds=uptime_seconds,
            last_activity=last_activity,
            error_count=error_count,
            memory_usage_mb=memory_mb,
            performance_metrics=perf_metrics,
        )

    async def _get_client_stats(self) -> dict[str, Any]:
        """Get ProjectX client statistics."""
        client = self.client
        if not client:
            return {
                "total_api_calls": 0,
                "successful_api_calls": 0,
                "failed_api_calls": 0,
                "avg_response_time_ms": 0.0,
                "cache_hit_rate": 0.0,
                "memory_usage_mb": 0.0,
            }

        # Get performance stats from client
        if hasattr(client, "get_performance_stats"):
            perf_stats = await client.get_performance_stats()

            return {
                "total_api_calls": perf_stats.get("api_calls", 0),
                "successful_api_calls": perf_stats.get("successful_calls", 0),
                "failed_api_calls": perf_stats.get("failed_calls", 0),
                "avg_response_time_ms": perf_stats.get("avg_response_time_ms", 0.0),
                "cache_hit_rate": perf_stats.get("cache_hit_ratio", 0.0),
                "memory_usage_mb": perf_stats.get("memory_usage_mb", 0.0),
            }

        # Fallback to basic stats
        api_calls = getattr(client, "api_call_count", 0)
        cache_hits = getattr(client, "cache_hit_count", 0)
        total_requests = api_calls + cache_hits

        return {
            "total_api_calls": api_calls,
            "successful_api_calls": api_calls,  # Assume successful if we have the count
            "failed_api_calls": 0,
            "avg_response_time_ms": 0.0,
            "cache_hit_rate": (cache_hits / total_requests)
            if total_requests > 0
            else 0.0,
            "memory_usage_mb": 0.0,
        }

    async def _get_realtime_stats(self) -> dict[str, Any]:
        """Get realtime client statistics."""
        rt = self.realtime_client
        if not rt:
            return {
                "realtime_connected": False,
                "user_hub_connected": False,
                "market_hub_connected": False,
                "active_subscriptions": 0,
                "message_queue_size": 0,
            }

        return {
            "realtime_connected": rt.is_connected()
            if hasattr(rt, "is_connected")
            else False,
            "user_hub_connected": getattr(rt, "user_connected", False),
            "market_hub_connected": getattr(rt, "market_connected", False),
            "active_subscriptions": len(getattr(rt, "_subscriptions", [])),
            "message_queue_size": len(getattr(rt, "_message_queue", [])),
        }

    async def _calculate_cross_metrics(
        self, stats: TradingSuiteStats
    ) -> TradingSuiteStats:
        """
        Calculate cross-component metrics.

        Args:
            stats: Raw statistics

        Returns:
            Statistics with cross-component metrics added
        """
        # Calculate total memory usage across all components
        total_memory = sum(
            comp.get("memory_usage_mb", 0)
            for comp in stats.get("components", {}).values()
        )
        stats["memory_usage_mb"] = total_memory

        # Calculate total error count
        total_errors = sum(
            comp.get("error_count", 0) for comp in stats.get("components", {}).values()
        )
        stats["total_errors"] = total_errors

        # Calculate overall health score (0-100)
        health_score = 100.0

        # Deduct for errors
        if total_errors > 0:
            health_score -= min(20, total_errors * 2)

        # Deduct for disconnected components
        disconnected = sum(
            1
            for comp in stats.get("components", {}).values()
            if comp.get("status") != "connected" and comp.get("status") != "active"
        )
        if disconnected > 0:
            health_score -= disconnected * 10

        # Deduct for high memory usage (>500MB total)
        if total_memory > 500:
            health_score -= min(20, (total_memory - 500) / 50)

        # Deduct for poor cache performance
        cache_hit_rate = stats.get("cache_hit_rate", 0)
        if cache_hit_rate < 0.5:
            health_score -= (0.5 - cache_hit_rate) * 20

        stats["health_score"] = max(0, health_score)

        return stats

    def _get_cached(self, key: str) -> Any | None:
        """
        Get cached value if still valid.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing
        """
        if key not in self._cache:
            return None

        timestamp = self._cache_timestamps.get(key, 0)
        if time.time() - timestamp > self._cache_ttl:
            return None

        return self._cache[key]

    def _set_cache(self, key: str, value: Any) -> None:
        """
        Set cache value with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()

    def _get_empty_stats(self) -> TradingSuiteStats:
        """Get empty statistics structure."""
        return {
            "suite_id": "unknown",
            "instrument": "unknown",
            "created_at": datetime.now().isoformat(),
            "uptime_seconds": 0,
            "status": "disconnected",
            "connected": False,
            "components": {},
            "realtime_connected": False,
            "user_hub_connected": False,
            "market_hub_connected": False,
            "total_api_calls": 0,
            "successful_api_calls": 0,
            "failed_api_calls": 0,
            "avg_response_time_ms": 0.0,
            "cache_hit_rate": 0.0,
            "memory_usage_mb": 0.0,
            "active_subscriptions": 0,
            "message_queue_size": 0,
            "features_enabled": [],
            "timeframes": [],
        }

    def _get_empty_component_stats(
        self, name: str, uptime_seconds: int
    ) -> ComponentStats:
        """Get empty component statistics."""
        return ComponentStats(
            name=name,
            status="disconnected",
            uptime_seconds=uptime_seconds,
            last_activity=None,
            error_count=0,
            memory_usage_mb=0.0,
            performance_metrics={},
        )
