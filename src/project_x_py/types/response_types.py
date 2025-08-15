"""
Response type definitions for ProjectX API operations.

Author: @TexasCoding
Date: 2025-08-04

Overview:
    Contains comprehensive TypedDict definitions for all API response types,
    replacing generic dict[str, Any] usage with structured, type-safe definitions.
    Provides complete type safety for all client responses and data structures.

Key Features:
    - Complete API response type definitions for all endpoints
    - Health check and system status response types
    - Performance statistics and metrics response types
    - Risk analysis and portfolio analytics response types
    - Orderbook analysis and market microstructure response types
    - Error response structures with comprehensive error information

Type Categories:
    - Health & Status: HealthStatusResponse, PerformanceStatsResponse
    - Risk & Analytics: RiskAnalysisResponse, PositionSizingResponse, PortfolioMetrics
    - Market Data: OrderbookAnalysisResponse, LiquidityAnalysisResponse, MarketImpactResponse
    - Trading: OrderStatsResponse, PositionAnalysisResponse, TradeAnalysisResponse
    - System: MemoryStatsResponse, ConnectionStatsResponse, ErrorResponse

Example Usage:
    ```python
    from project_x_py.types.response_types import (
        HealthStatusResponse,
        PerformanceStatsResponse,
        RiskAnalysisResponse,
        OrderbookAnalysisResponse,
        MemoryStatsResponse,
    )


    # Use in client methods
    async def get_health_status(self) -> HealthStatusResponse:
        response = await self._make_request("GET", "/health")
        return cast(HealthStatusResponse, response)


    # Use in manager methods
    async def analyze_risk(self) -> RiskAnalysisResponse:
        analysis = await self._calculate_risk_metrics()
        return cast(RiskAnalysisResponse, analysis)


    # Use in orderbook methods
    async def analyze_liquidity(self) -> LiquidityAnalysisResponse:
        liquidity = await self._analyze_market_liquidity()
        return cast(LiquidityAnalysisResponse, liquidity)
    ```

Benefits:
    - Type safety for all API responses and internal data structures
    - Better IDE support with autocomplete and type checking
    - Compile-time error detection for incorrect field access
    - Clear documentation of expected response structure
    - Consistent data structures across all components

See Also:
    - `types.base`: Core type definitions and constants
    - `types.trading`: Trading operation types and enums
    - `types.market_data`: Market data structures and configurations
    - `types.protocols`: Protocol definitions for type checking
"""

from typing import Any, NotRequired, TypedDict


# Health and Status Response Types
class HealthStatusResponse(TypedDict):
    """Response type for health status checks."""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    uptime_seconds: int
    api_version: str
    connection_status: str
    database_status: str
    cache_status: str
    websocket_status: str
    last_heartbeat: str
    response_time_ms: float


class PerformanceStatsResponse(TypedDict):
    """Response type for performance statistics."""

    api_calls: int
    cache_hits: int
    cache_misses: int
    cache_hit_ratio: float
    total_requests: int
    active_connections: int


# Risk and Analytics Response Types
class RiskAnalysisResponse(TypedDict):
    """Response type for comprehensive risk analysis."""

    current_risk: float
    max_risk: float
    daily_loss: float
    daily_loss_limit: float
    position_count: int
    position_limit: int
    daily_trades: int
    daily_trade_limit: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    position_risks: list[dict[str, Any]]
    risk_per_trade: float
    account_balance: float
    margin_used: float
    margin_available: float


class PositionSizingResponse(TypedDict):
    """Response type for position sizing analysis."""

    position_size: int
    risk_amount: float
    risk_percent: float
    entry_price: float
    stop_loss: float
    tick_size: float
    account_balance: float
    kelly_fraction: float | None
    max_position_size: int
    sizing_method: str  # "fixed_risk", "kelly", "atr_based"


class RiskValidationResponse(TypedDict):
    """Response type for trade risk validation."""

    is_valid: bool
    reasons: list[str]  # Reasons for rejection
    warnings: list[str]  # Warnings but still valid
    current_risk: float
    daily_loss: float
    daily_trades: int
    position_count: int
    portfolio_risk: float


class PortfolioMetricsResponse(TypedDict):
    """Response type for portfolio analytics."""

    total_value: float
    total_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    ytd_pnl: float
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    largest_win: float
    largest_loss: float
    avg_trade_duration_minutes: float
    last_updated: str


# Market Data Response Types
class OrderbookAnalysisResponse(TypedDict):
    """Response type for orderbook microstructure analysis."""

    bid_depth: int
    ask_depth: int
    total_bid_size: int
    total_ask_size: int
    avg_bid_size: float
    avg_ask_size: float
    price_levels: int
    order_clustering: float
    imbalance: float
    spread: float
    mid_price: float
    weighted_mid_price: float
    volume_weighted_avg_price: float
    time_weighted_avg_price: float
    timestamp: str


class LiquidityAnalysisResponse(TypedDict):
    """Response type for liquidity analysis."""

    bid_liquidity: float
    ask_liquidity: float
    total_liquidity: float
    avg_spread: float
    spread_volatility: float
    liquidity_score: float  # 0-10 scale
    market_depth_score: float
    resilience_score: float
    tightness_score: float
    immediacy_score: float
    depth_imbalance: float
    effective_spread: float
    realized_spread: float
    price_impact: float
    timestamp: str


class MarketImpactResponse(TypedDict):
    """Response type for market impact estimation."""

    estimated_fill_price: float
    price_impact_pct: float
    spread_cost: float
    market_impact_cost: float
    total_transaction_cost: float
    levels_consumed: int
    remaining_liquidity: float
    confidence_level: float
    slippage_estimate: float
    timing_risk: float
    liquidity_premium: float
    implementation_shortfall: float
    timestamp: str


class IcebergDetectionResponse(TypedDict):
    """Response type for iceberg order detection."""

    price: float
    side: str  # "bid" or "ask"
    visible_size: int
    total_volume: int
    refill_count: int
    avg_refill_size: float
    time_active_minutes: float
    confidence: float  # 0-1 scale
    pattern: str
    first_detected: str
    last_refresh: str


class SpoofingDetectionResponse(TypedDict):
    """Response type for spoofing detection."""

    price: float
    side: str  # "bid" or "ask"
    order_size: int
    placement_frequency: float
    cancellation_rate: float
    time_to_cancel_avg_seconds: float
    distance_from_market: float  # ticks
    confidence: float  # 0-1 scale
    pattern: str  # e.g., "layering", "quote_stuffing", "momentum_ignition"
    first_detected: str
    last_detected: str
    total_instances: int


# Trading Response Types
class OrderStatsResponse(TypedDict):
    """Response type for order execution statistics."""

    orders_placed: int
    orders_filled: int
    orders_cancelled: int
    orders_rejected: int
    orders_modified: int
    bracket_orders: int
    fill_rate: float  # orders_filled / orders_placed
    cancellation_rate: float
    rejection_rate: float
    avg_fill_time_seconds: float
    avg_fill_price: float
    total_volume: int
    total_fees: float
    slippage_avg_ticks: float
    last_order_time: str | None
    performance_score: float  # 0-100


class PositionAnalysisResponse(TypedDict):
    """Response type for individual position analysis."""

    position_id: int
    contract_id: str
    entry_price: float
    current_price: float
    unrealized_pnl: float
    position_size: int
    position_value: float
    margin_used: float
    duration_minutes: int
    high_water_mark: float
    low_water_mark: float
    max_unrealized_pnl: float
    min_unrealized_pnl: float
    volatility: float
    beta: float
    delta_exposure: float
    gamma_exposure: float
    theta_decay: float
    risk_contribution: float
    analysis_timestamp: str
    # Optional error information used by some analytics fallbacks/tests
    error: NotRequired[str]


class TradeAnalysisResponse(TypedDict):
    """Response type for trade execution analysis."""

    trade_id: int
    execution_price: float
    market_price_at_execution: float
    slippage_ticks: float
    slippage_dollars: float
    timing_cost: float
    market_impact: float
    fill_quality_score: float  # 0-100
    venue_liquidity: float
    spread_at_execution: float
    volume_participation_rate: float
    price_improvement: float
    execution_shortfall: float
    benchmark_comparison: str
    execution_timestamp: str


# System Response Types
class MemoryStatsResponse(TypedDict):
    """Response type for memory usage statistics."""

    total_memory_mb: float
    used_memory_mb: float
    available_memory_mb: float
    memory_usage_percent: float
    cache_size_mb: float
    buffer_size_mb: float
    gc_collections: int
    gc_time_ms: float
    objects_tracked: int
    memory_leaks_detected: int
    last_cleanup: str
    next_cleanup: str


class ConnectionStatsResponse(TypedDict):
    """Response type for connection statistics."""

    active_connections: int
    total_connections: int
    failed_connections: int
    connection_success_rate: float
    avg_connection_time_ms: float
    websocket_connections: int
    http_connections: int
    reconnection_attempts: int
    last_reconnection: str | None
    uptime_seconds: int
    data_sent_bytes: int
    data_received_bytes: int
    messages_sent: int
    messages_received: int


class ErrorResponse(TypedDict):
    """Response type for error information."""

    error_code: int
    error_message: str
    error_type: str
    error_category: (
        str  # "validation", "authentication", "authorization", "system", "network"
    )
    timestamp: str
    request_id: str
    endpoint: str
    method: str
    user_message: str  # User-friendly error message
    technical_details: NotRequired[dict[str, Any]]
    suggested_action: NotRequired[str]
    retry_after_seconds: NotRequired[int]


# Volume Profile Response Types
class VolumeProfileResponse(TypedDict):
    """Response type for volume profile analysis."""

    price_min: float
    price_max: float
    volume: int
    percentage: float
    value_area_high: float
    value_area_low: float
    point_of_control: float  # Price level with highest volume
    profile_type: str  # "session", "day", "week", "custom"
    total_volume: int
    session_info: dict[str, Any]


class VolumeProfileListResponse(TypedDict):
    """Response type for list of volume profile levels."""

    levels: list[VolumeProfileResponse]
    total_volume: int
    price_range: float
    value_area_volume_percent: float
    session_start: str
    session_end: str
    analysis_timestamp: str


# Combined Analysis Response Types
class ComprehensiveAnalysisResponse(TypedDict):
    """Response type for comprehensive market analysis combining multiple metrics."""

    market_structure: OrderbookAnalysisResponse
    liquidity_analysis: LiquidityAnalysisResponse
    risk_metrics: RiskAnalysisResponse
    performance_stats: PerformanceStatsResponse
    volume_profile: VolumeProfileListResponse
    detected_patterns: list[str]
    market_regime: str  # "trending", "ranging", "volatile", "quiet"
    confidence_score: float
    analysis_timestamp: str
    recommendations: list[str]


__all__ = [
    # Health & Status
    "HealthStatusResponse",
    "PerformanceStatsResponse",
    # Risk & Analytics
    "RiskAnalysisResponse",
    "PositionSizingResponse",
    "RiskValidationResponse",
    "PortfolioMetricsResponse",
    # Market Data
    "OrderbookAnalysisResponse",
    "LiquidityAnalysisResponse",
    "MarketImpactResponse",
    "IcebergDetectionResponse",
    "SpoofingDetectionResponse",
    # Trading
    "OrderStatsResponse",
    "PositionAnalysisResponse",
    "TradeAnalysisResponse",
    # System
    "MemoryStatsResponse",
    "ConnectionStatsResponse",
    "ErrorResponse",
    # Volume Profile
    "VolumeProfileResponse",
    "VolumeProfileListResponse",
    # Combined
    "ComprehensiveAnalysisResponse",
]
