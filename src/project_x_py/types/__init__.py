"""
Centralized type definitions for ProjectX Python SDK.

This package consolidates all type definitions, protocols, and type aliases
used throughout the ProjectX SDK to ensure consistency and reduce redundancy.

The types are organized into logical modules:
- base: Core types used across the SDK
- trading: Order and position related types
- market_data: Market data and real-time types
- protocols: Protocol definitions for type checking
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
