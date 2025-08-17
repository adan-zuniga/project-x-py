"""
Centralized type definitions for ProjectX Python SDK.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Consolidates all type definitions, protocols, and type aliases used throughout
    the ProjectX SDK to ensure consistency and reduce redundancy. Provides comprehensive
    type safety and interface definitions for all SDK components.

Key Features:
    - Centralized type definitions for consistent usage across modules
    - Protocol definitions for type checking and interface validation
    - Enum types for ProjectX-specific constants and states
    - TypedDict definitions for structured data validation
    - Type aliases for common patterns and callbacks
    - Comprehensive type safety for async/await patterns

Type Categories:
    - Core Types: Basic type aliases and constants used throughout the SDK
    - Trading Types: Order and position management types and enums
    - Market Data Types: Real-time data structures and orderbook types
    - Protocol Types: Interface definitions for type checking and validation

Module Organization:
    - base: Core types used across the SDK (callbacks, IDs, constants)
    - trading: Order and position related types (enums, statistics)
    - market_data: Market data and real-time types (orderbook, trades, configs)
    - protocols: Protocol definitions for type checking (interfaces, contracts)

Example Usage:
    ```python
    from project_x_py.types import (
        # Core types
        AccountId,
        ContractId,
        OrderId,
        PositionId,
        AsyncCallback,
        SyncCallback,
        CallbackType,
        # Trading types
        OrderSide,
        OrderType,
        OrderStatus,
        PositionType,
        # Market data types
        DomType,
        OrderbookSide,
        TradeDict,
        OrderbookSnapshot,
        # Protocol types
        ProjectXClientProtocol,
        OrderManagerProtocol,
        PositionManagerProtocol,
        RealtimeDataManagerProtocol,
    )


    # Use in function signatures
    async def process_order(
        order_id: OrderId, side: OrderSide, status: OrderStatus
    ) -> None:
        pass


    # Use in callback definitions
    def on_trade_update(data: TradeDict) -> None:
        pass


    # Use in protocol implementations
    class MyOrderManager:
        def place_order(self, contract_id: ContractId) -> None:
            pass
    ```

Type Safety Benefits:
    - Compile-time type checking for all SDK operations
    - Interface validation for component interactions
    - Consistent data structures across modules
    - Reduced runtime errors through type validation
    - Better IDE support and autocomplete

See Also:
    - `types.base`: Core type definitions and constants
    - `types.trading`: Trading operation types and enums
    - `types.market_data`: Market data structures and configurations
    - `types.protocols`: Protocol definitions for type checking
"""

# Import all types for convenient access
from project_x_py.types.api_responses import (
    AccountListResponse,
    AccountResponse,
    AccountUpdatePayload,
    AuthLoginResponse,
    BarData,
    BarDataResponse,
    ErrorResponse as APIErrorResponse,
    InstrumentResponse,
    InstrumentSearchResponse,
    MarketDepthLevel,
    MarketDepthResponse,
    MarketDepthUpdatePayload,
    MarketTradePayload,
    OrderPlacementResponse,
    OrderResponse,
    OrderSearchResponse,
    OrderUpdatePayload,
    PositionResponse,
    PositionSearchResponse,
    PositionUpdatePayload,
    QuoteData,
    QuoteUpdatePayload,
    TradeExecutionPayload,
    TradeResponse,
    TradeSearchResponse,
)
from project_x_py.types.base import (
    DEFAULT_TIMEZONE,
    TICK_SIZE_PRECISION,
    AccountId,
    AsyncCallback,
    CallbackType,
    ContractId,
    OrderId,
    PositionId,
    SyncCallback,
)
from project_x_py.types.callback_types import (
    AccountUpdateData,
    ConnectionStatusData,
    ErrorData,
    MarketDepthData,
    MarketTradeData,
    NewBarData,
    OrderFilledData,
    OrderUpdateData,
    PositionAlertData,
    PositionClosedData,
    PositionUpdateData,
    QuoteUpdateData,
    SystemStatusData,
    TradeExecutionData,
)
from project_x_py.types.config_types import (
    CacheConfig,
    DataManagerConfig,
    EnvironmentConfig,
    FeatureConfig,
    HTTPConfig,
    IndicatorConfig,
    LoggingConfig,
    MemoryManagementConfig,
    OrderbookConfig,
    OrderManagerConfig,
    PositionManagerConfig,
    ProjectXSDKConfig,
    RateLimitConfig,
    RealtimeConfig,
    RiskConfig,
    TradingSuiteConfig,
    WebSocketConfig,
)
from project_x_py.types.market_data import (
    DomType,
    IcebergConfig,
    MarketDataDict,
    MemoryConfig,
    OrderbookSide,
    OrderbookSnapshot,
    PriceLevelDict,
    TradeDict,
)
from project_x_py.types.protocols import (
    OrderManagerProtocol,
    PositionManagerProtocol,
    ProjectXClientProtocol,
    ProjectXRealtimeClientProtocol,
    RealtimeDataManagerProtocol,
)
from project_x_py.types.response_types import (
    ComprehensiveAnalysisResponse,
    ConnectionStatsResponse,
    ErrorResponse,
    HealthStatusResponse,
    IcebergDetectionResponse,
    LiquidityAnalysisResponse,
    MarketImpactResponse,
    MemoryStatsResponse,
    OrderbookAnalysisResponse,
    OrderStatsResponse,
    PerformanceStatsResponse,
    PortfolioMetricsResponse,
    PositionAnalysisResponse,
    PositionSizingResponse,
    RiskAnalysisResponse,
    RiskValidationResponse,
    SpoofingDetectionResponse,
    TradeAnalysisResponse,
    VolumeProfileListResponse,
    VolumeProfileResponse,
)
from project_x_py.types.stats_types import (
    CacheStats,
    ComponentStats,
    ComprehensiveStats,
    HTTPClientStats,
    MemoryUsageStats,
    OrderbookStats,
    OrderManagerStats,
    PositionManagerStats,
    RealtimeConnectionStats,
    RealtimeDataManagerStats,
    TradingSuiteStats,
)
from project_x_py.types.trading import (
    OrderSide,
    OrderStatus,
    OrderType,
    PositionType,
    TradeLogType,
)

__all__ = [
    # From api_responses.py
    "AccountListResponse",
    "AccountResponse",
    "AccountUpdatePayload",
    "AuthLoginResponse",
    "APIErrorResponse",
    "BarData",
    "BarDataResponse",
    "InstrumentResponse",
    "InstrumentSearchResponse",
    "MarketDepthLevel",
    "MarketDepthResponse",
    "MarketDepthUpdatePayload",
    "MarketTradePayload",
    "OrderPlacementResponse",
    "OrderResponse",
    "OrderSearchResponse",
    "OrderUpdatePayload",
    "PositionResponse",
    "PositionSearchResponse",
    "PositionUpdatePayload",
    "QuoteData",
    "QuoteUpdatePayload",
    "TradeExecutionPayload",
    "TradeResponse",
    "TradeSearchResponse",
    # From base.py
    "DEFAULT_TIMEZONE",
    "TICK_SIZE_PRECISION",
    "AccountId",
    "AsyncCallback",
    "CallbackType",
    "ContractId",
    "OrderId",
    "PositionId",
    "SyncCallback",
    # From callback_types.py
    "AccountUpdateData",
    "ConnectionStatusData",
    "ErrorData",
    "MarketDepthData",
    "MarketTradeData",
    "NewBarData",
    "OrderFilledData",
    "OrderUpdateData",
    "PositionAlertData",
    "PositionClosedData",
    "PositionUpdateData",
    "QuoteUpdateData",
    "SystemStatusData",
    "TradeExecutionData",
    # From config_types.py
    "CacheConfig",
    "DataManagerConfig",
    "EnvironmentConfig",
    "FeatureConfig",
    "HTTPConfig",
    "IndicatorConfig",
    "LoggingConfig",
    "MemoryManagementConfig",
    "OrderManagerConfig",
    "OrderbookConfig",
    "PositionManagerConfig",
    "ProjectXSDKConfig",
    "RateLimitConfig",
    "RealtimeConfig",
    "RiskConfig",
    "TradingSuiteConfig",
    "WebSocketConfig",
    # From market_data.py
    "DomType",
    "IcebergConfig",
    "MarketDataDict",
    "MemoryConfig",
    "OrderbookSide",
    "OrderbookSnapshot",
    "PriceLevelDict",
    "TradeDict",
    # From protocols.py
    "OrderManagerProtocol",
    "PositionManagerProtocol",
    "ProjectXClientProtocol",
    "ProjectXRealtimeClientProtocol",
    "RealtimeDataManagerProtocol",
    # From response_types.py
    "ComprehensiveAnalysisResponse",
    "ConnectionStatsResponse",
    "ErrorResponse",
    "HealthStatusResponse",
    "IcebergDetectionResponse",
    "LiquidityAnalysisResponse",
    "MarketImpactResponse",
    "MemoryStatsResponse",
    "OrderStatsResponse",
    "OrderbookAnalysisResponse",
    "PerformanceStatsResponse",
    "PortfolioMetricsResponse",
    "PositionAnalysisResponse",
    "PositionSizingResponse",
    "RiskAnalysisResponse",
    "RiskValidationResponse",
    "SpoofingDetectionResponse",
    "TradeAnalysisResponse",
    "VolumeProfileListResponse",
    "VolumeProfileResponse",
    # From stats_types.py
    "CacheStats",
    "ComponentStats",
    "ComprehensiveStats",
    "HTTPClientStats",
    "MemoryUsageStats",
    "OrderManagerStats",
    "OrderbookStats",
    "PositionManagerStats",
    "RealtimeConnectionStats",
    "RealtimeDataManagerStats",
    "TradingSuiteStats",
    # From trading.py
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "PositionType",
    "TradeLogType",
]
