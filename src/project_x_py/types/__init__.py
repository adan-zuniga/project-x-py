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
        PositionSide,
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
from project_x_py.types.trading import (
    OrderSide,
    OrderStats,
    OrderStatus,
    OrderType,
    PositionSide,
)

__all__ = [
    "DEFAULT_TIMEZONE",
    "TICK_SIZE_PRECISION",
    "AccountId",
    # From base.py
    "AsyncCallback",
    "CallbackType",
    "ContractId",
    # From market_data.py
    "DomType",
    "IcebergConfig",
    "MarketDataDict",
    "MemoryConfig",
    "OrderId",
    "OrderManagerProtocol",
    # From trading.py
    "OrderSide",
    "OrderStats",
    "OrderStatus",
    "OrderType",
    "OrderbookSide",
    "OrderbookSnapshot",
    "PositionId",
    "PositionManagerProtocol",
    "PositionSide",
    "PriceLevelDict",
    # From protocols.py
    "ProjectXClientProtocol",
    "ProjectXRealtimeClientProtocol",
    "RealtimeDataManagerProtocol",
    "SyncCallback",
    "TradeDict",
]
