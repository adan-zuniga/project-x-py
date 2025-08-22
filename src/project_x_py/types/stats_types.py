"""
Statistics and metrics type definitions for ProjectX components.

Author: @TexasCoding
Date: 2025-08-04

Overview:
    Contains TypedDict definitions for statistics and metrics returned by
    various SDK components. Replaces generic dict[str, Any] usage with
    structured, type-safe statistics definitions.

Key Features:
    - TradingSuite statistics with component status and performance metrics
    - Component-specific statistics for detailed analysis
    - Connection and performance metrics
    - Memory usage and resource tracking
    - Type safety for all statistics operations

Type Categories:
    - Suite Statistics: TradingSuiteStats for overall suite metrics
    - Component Statistics: OrderManagerStats, PositionManagerStats, etc.
    - Connection Statistics: RealtimeStats, WebSocketStats
    - Performance Statistics: MemoryStats, CacheStats

Example Usage:
    ```python
    from project_x_py.types.stats_types import (
        TradingSuiteStats,
        OrderManagerStats,
        ConnectionStats,
    )


    # Use in TradingSuite
    def get_stats(self) -> TradingSuiteStats:
        return {
            "suite_id": self.suite_id,
            "connected": self.is_connected(),
            "uptime_seconds": self._calculate_uptime(),
            "components": self._get_component_stats(),
        }


    # Use in OrderManager
    async def get_statistics(self) -> OrderManagerStats:
        return {
            "orders_placed": self._orders_placed,
            "orders_filled": self._orders_filled,
            "fill_rate": self._calculate_fill_rate(),
        }
    ```

Benefits:
    - Type safety for all statistics and metrics
    - Clear documentation of available statistics fields
    - Consistent statistics structure across components
    - Better IDE support with autocomplete
    - Compile-time validation of statistics access

See Also:
    - `types.response_types`: API response type definitions
    - `types.config_types`: Configuration type definitions
    - `types.base`: Core type definitions and constants
"""

from typing import Any, NotRequired, TypedDict


# TradingSuite Statistics Types
class ComponentStats(TypedDict):
    """Statistics for individual components within TradingSuite."""

    name: str
    status: str  # "connected", "disconnected", "error", "initializing"
    uptime_seconds: int
    last_activity: str | None
    error_count: int
    memory_usage_mb: float
    performance_metrics: NotRequired[dict[str, Any]]  # Optional performance data


class TradingSuiteStats(TypedDict):
    """Comprehensive statistics for TradingSuite instance."""

    suite_id: str
    instrument: str
    created_at: str
    uptime_seconds: int
    status: str  # "active", "connecting", "disconnected", "error"
    connected: bool

    # Component statistics
    components: dict[str, ComponentStats]

    # Connection statistics
    realtime_connected: bool
    user_hub_connected: bool
    market_hub_connected: bool

    # Performance metrics
    total_api_calls: int
    successful_api_calls: int
    failed_api_calls: int
    avg_response_time_ms: float
    cache_hit_rate: float

    # Resource usage
    memory_usage_mb: float
    active_subscriptions: int
    message_queue_size: int

    # Feature flags
    features_enabled: list[str]
    timeframes: list[str]

    # Calculated cross-component metrics
    total_errors: NotRequired[int]  # Total error count across all components
    health_score: NotRequired[float]  # Overall health score (0-100)


# Component-Specific Statistics Types
class OrderManagerStats(TypedDict):
    """Statistics for OrderManager component."""

    orders_placed: int
    orders_filled: int
    orders_cancelled: int
    orders_rejected: int
    orders_modified: int

    # Performance metrics
    fill_rate: float  # orders_filled / orders_placed
    avg_fill_time_ms: float
    rejection_rate: float

    # Order types
    market_orders: int
    limit_orders: int
    stop_orders: int
    bracket_orders: int

    # Timing statistics
    last_order_time: str | None
    avg_order_response_time_ms: float
    fastest_fill_ms: float
    slowest_fill_ms: float

    # Volume and value
    total_volume: int
    total_value: float
    avg_order_size: float
    largest_order: int

    # Risk metrics
    risk_violations: int
    order_validation_failures: int


class PositionManagerStats(TypedDict):
    """Statistics for PositionManager component."""

    open_positions: int
    closed_positions: int
    total_positions: int

    # P&L metrics
    total_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    best_position_pnl: float
    worst_position_pnl: float

    # Position metrics
    avg_position_size: float
    largest_position: int
    avg_hold_time_minutes: float
    longest_hold_time_minutes: float

    # Performance metrics
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float

    # Risk metrics
    total_risk: float
    max_position_risk: float
    portfolio_correlation: float
    var_95: float  # Value at Risk 95%

    # Activity metrics
    position_updates: int
    risk_calculations: int
    last_position_update: str | None


class RealtimeDataManagerStats(TypedDict):
    """Statistics for RealtimeDataManager component."""

    # Data metrics
    bars_processed: int
    ticks_processed: int
    quotes_processed: int
    trades_processed: int

    # Per timeframe statistics
    timeframe_stats: dict[str, dict[str, int]]  # timeframe -> {bars, updates, etc.}

    # Performance metrics
    avg_processing_time_ms: float
    data_latency_ms: float
    buffer_utilization: float

    # Storage metrics
    total_bars_stored: int
    memory_usage_mb: float
    compression_ratio: float

    # Update frequency
    updates_per_minute: float
    last_update: str | None
    data_freshness_seconds: float

    # Error handling
    data_validation_errors: int
    connection_interruptions: int
    recovery_attempts: int

    # Overflow handling
    overflow_stats: dict[str, Any]
    buffer_overflow_stats: dict[str, Any]
    # Lock optimization
    lock_optimization_stats: dict[str, Any]


class OrderbookStats(TypedDict):
    """Statistics for OrderBook component."""

    # Depth statistics
    avg_bid_depth: int
    avg_ask_depth: int
    max_bid_depth: int
    max_ask_depth: int

    # Trade statistics
    trades_processed: int
    avg_trade_size: float
    largest_trade: int
    total_volume: int

    # Market microstructure
    avg_spread: float
    spread_volatility: float
    price_levels: int
    order_clustering: float

    # Pattern detection
    icebergs_detected: int
    spoofing_alerts: int
    unusual_patterns: int

    # Performance metrics
    update_frequency_per_second: float
    processing_latency_ms: float
    memory_usage_mb: float

    # Data quality
    data_gaps: int
    invalid_updates: int
    duplicate_updates: int


class RiskManagerStats(TypedDict):
    """Statistics for RiskManager component."""

    # Risk rule statistics
    rules_evaluated: int
    rule_violations: int
    rule_warnings: int
    rules_passed: int

    # Position risk metrics
    total_risk_exposure: float
    max_position_risk: float
    portfolio_risk: float
    var_95: float  # Value at Risk 95%

    # Risk limits
    max_loss_limit: float
    daily_loss_limit: float
    position_size_limit: int
    leverage_limit: float

    # Risk events
    stop_losses_triggered: int
    margin_calls: int
    risk_alerts: int
    emergency_stops: int

    # Performance metrics
    risk_calculations_per_second: float
    avg_calculation_time_ms: float
    memory_usage_mb: float

    # Managed trades
    managed_trades_active: int
    managed_trades_completed: int
    managed_trades_stopped: int
    avg_trade_duration_minutes: float

    # Risk-adjusted performance
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    risk_adjusted_return: float


# Connection Statistics Types
class RealtimeConnectionStats(TypedDict):
    """Statistics for real-time WebSocket connections."""

    # Connection status
    user_hub_connected: bool
    market_hub_connected: bool
    connection_uptime_seconds: int

    # Connection quality
    reconnection_attempts: int
    last_reconnection: str | None
    connection_stability_score: float  # 0-1 scale

    # Message statistics
    messages_sent: int
    messages_received: int
    message_queue_size: int
    avg_message_latency_ms: float

    # Data flow
    subscriptions_active: int
    data_rate_per_second: float
    bandwidth_usage_kbps: float

    # Error handling
    connection_errors: int
    message_errors: int
    timeout_errors: int
    last_error: str | None


class HTTPClientStats(TypedDict):
    """Statistics for HTTP client operations."""

    # Request statistics
    total_requests: int
    successful_requests: int
    failed_requests: int

    # Performance metrics
    avg_response_time_ms: float
    fastest_request_ms: float
    slowest_request_ms: float

    # Response codes
    response_codes: dict[str, int]  # HTTP status code -> count

    # Rate limiting
    rate_limit_hits: int
    retry_attempts: int
    backoff_delays_ms: list[float]

    # Caching
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float

    # Connection pooling
    active_connections: int
    connection_reuse_rate: float


# Performance Statistics Types
class CacheStats(TypedDict):
    """Statistics for caching operations."""

    cache_hits: int
    cache_misses: int
    cache_hit_rate: float

    # Storage metrics
    items_cached: int
    total_size_mb: float
    avg_item_size_kb: float

    # Performance metrics
    avg_lookup_time_ms: float
    evictions: int
    ttl_expirations: int

    # Memory management
    memory_limit_mb: float
    memory_usage_mb: float
    memory_pressure: float  # 0-1 scale


class MemoryUsageStats(TypedDict):
    """Statistics for memory usage across components."""

    # Overall memory
    total_memory_mb: float
    used_memory_mb: float
    available_memory_mb: float
    memory_usage_percent: float

    # Component breakdown
    component_memory: dict[str, float]  # component name -> memory MB

    # Garbage collection
    gc_collections: int
    gc_time_ms: float
    objects_tracked: int

    # Performance impact
    memory_alerts: int
    out_of_memory_errors: int
    cleanup_operations: int
    last_cleanup: str | None


# Top-Level Statistics Categories
class HealthStats(TypedDict):
    """System-wide health statistics."""

    overall_score: float  # 0-100 health score
    component_scores: dict[str, float]  # component name -> health score
    issues: list[str]  # List of current health issues


class PerformanceStats(TypedDict):
    """System-wide performance statistics."""

    api_calls_total: int
    cache_hit_rate: float  # 0-1 ratio
    avg_response_time: float  # seconds
    requests_per_second: float


class ErrorInfo(TypedDict):
    """Individual error information."""

    timestamp: str | None
    component: str
    error_type: str
    message: str
    severity: str


class ErrorStats(TypedDict):
    """System-wide error statistics."""

    total_errors: int
    error_rate: float  # 0-1 ratio
    errors_by_component: dict[str, int]  # component name -> error count
    recent_errors: list[ErrorInfo]


class ConnectionStats(TypedDict):
    """System-wide connection statistics."""

    active_connections: int
    connection_status: dict[str, str]  # connection type -> status
    connection_uptime: dict[str, float]  # connection type -> uptime seconds


class TradingStats(TypedDict):
    """System-wide trading statistics."""

    orders_today: int
    fills_today: int
    active_positions: int
    pnl_today: float | None


# Combined Statistics Type
class ComprehensiveStats(TypedDict):
    """Combined statistics from all components and connections."""

    # Suite-level statistics
    suite: TradingSuiteStats

    # Top-level aggregated statistics
    health: NotRequired[HealthStats]
    performance: NotRequired[PerformanceStats]
    errors: NotRequired[ErrorStats]
    connections: NotRequired[ConnectionStats]
    trading: NotRequired[TradingStats]

    # Component statistics
    order_manager: NotRequired[OrderManagerStats]
    position_manager: NotRequired[PositionManagerStats]
    data_manager: NotRequired[RealtimeDataManagerStats]
    orderbook: NotRequired[OrderbookStats]
    risk_manager: NotRequired[RiskManagerStats]

    # Connection statistics
    realtime: NotRequired[RealtimeConnectionStats]
    http_client: NotRequired[HTTPClientStats]

    # Performance statistics
    cache: NotRequired[CacheStats]
    memory: NotRequired[MemoryUsageStats]

    # Metadata
    generated_at: str
    collection_time_ms: float


__all__ = [
    # Suite Statistics
    "ComponentStats",
    "TradingSuiteStats",
    # Top-Level Statistics
    "HealthStats",
    "PerformanceStats",
    "ErrorInfo",
    "ErrorStats",
    "ConnectionStats",
    "TradingStats",
    # Component Statistics
    "OrderManagerStats",
    "PositionManagerStats",
    "RealtimeDataManagerStats",
    "OrderbookStats",
    "RiskManagerStats",
    # Connection Statistics
    "RealtimeConnectionStats",
    "HTTPClientStats",
    # Performance Statistics
    "CacheStats",
    "MemoryUsageStats",
    # Combined Statistics
    "ComprehensiveStats",
]
