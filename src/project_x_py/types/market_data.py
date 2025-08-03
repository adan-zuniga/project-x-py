"""
Market data type definitions.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Contains type definitions for market data structures including orderbook data,
    trades, quotes, and real-time data updates. Provides comprehensive type safety
    for market data processing and analysis.

Key Features:
    - DOM (Depth of Market) type enumerations for ProjectX Gateway
    - Orderbook data structures and side enumerations
    - Trade data structures with comprehensive market information
    - Memory management configuration types
    - Iceberg detection configuration types
    - Type safety for real-time data processing

Type Categories:
    - Enums: DomType, OrderbookSide for market data classification
    - Data Structures: MarketDataDict, TradeDict, PriceLevelDict, OrderbookSnapshot
    - Configurations: MemoryConfig, IcebergConfig for system configuration

Example Usage:
    ```python
    from project_x_py.types.market_data import (
        DomType,
        OrderbookSide,
        TradeDict,
        OrderbookSnapshot,
        PriceLevelDict,
        MarketDataDict,
        MemoryConfig,
        IcebergConfig,
    )


    # Use DOM types for market data classification
    def process_dom_update(dom_type: DomType, data: dict[str, Any]) -> None:
        if dom_type == DomType.TRADE:
            print("Processing trade update")
        elif dom_type == DomType.BEST_BID:
            print("Processing best bid update")


    # Use orderbook side enumeration
    def process_orderbook_side(side: OrderbookSide, price: float) -> None:
        if side == OrderbookSide.BID:
            print(f"Bid price: {price}")
        else:
            print(f"Ask price: {price}")


    # Use trade data structure
    def process_trade(trade: TradeDict) -> None:
        print(f"Trade: {trade['price']} x {trade['volume']}")
        print(f"Side: {trade['side']}")
        print(f"Spread: {trade['spread_at_trade']}")


    # Use configuration types
    memory_config = MemoryConfig(
        max_trades=10000, max_depth_entries=1000, cleanup_interval=300
    )

    iceberg_config = IcebergConfig(
        min_refreshes=5, volume_threshold=50, time_window_minutes=10
    )
    ```

DOM Types (ProjectX Gateway):
    - UNKNOWN=0: Unknown or undefined DOM type
    - ASK=1: Ask side update
    - BID=2: Bid side update
    - BEST_ASK=3: Best ask price update
    - BEST_BID=4: Best bid price update
    - TRADE=5: Trade execution
    - RESET=6: Orderbook reset
    - SESSION_LOW=7: Session low price
    - SESSION_HIGH=8: Session high price
    - NEW_BEST_BID=9: New best bid price
    - NEW_BEST_ASK=10: New best ask price
    - FILL=11: Order fill

Data Structures:
    - MarketDataDict: Contract ID and data list for market updates
    - TradeDict: Comprehensive trade information with market context
    - PriceLevelDict: Price level data for orderbook entries
    - OrderbookSnapshot: Complete orderbook state with statistics

Configuration Types:
    - MemoryConfig: Memory management settings for data retention
    - IcebergConfig: Iceberg detection algorithm configuration

See Also:
    - `types.base`: Core type definitions and constants
    - `types.trading`: Trading operation types and enums
    - `types.protocols`: Protocol definitions for type checking
"""

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Any, TypedDict


class DomType(IntEnum):
    """ProjectX DOM (Depth of Market) type codes."""

    UNKNOWN = 0
    ASK = 1
    BID = 2
    BEST_ASK = 3
    BEST_BID = 4
    TRADE = 5
    RESET = 6
    SESSION_LOW = 7
    SESSION_HIGH = 8
    NEW_BEST_BID = 9
    NEW_BEST_ASK = 10
    FILL = 11


class OrderbookSide(IntEnum):
    """Orderbook side enumeration."""

    BID = 0
    ASK = 1


class MarketDataDict(TypedDict):
    """Type definition for market data updates."""

    contractId: str
    data: list[dict[str, Any]]


class TradeDict(TypedDict):
    """Type definition for trade data."""

    price: float
    volume: int
    timestamp: datetime
    side: str
    spread_at_trade: float | None
    mid_price_at_trade: float | None
    best_bid_at_trade: float | None
    best_ask_at_trade: float | None
    order_type: str


class PriceLevelDict(TypedDict):
    """Type definition for price level data."""

    price: float
    volume: int
    timestamp: datetime


class OrderbookSnapshot(TypedDict):
    """Type definition for orderbook snapshot."""

    instrument: str
    timestamp: datetime
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    mid_price: float | None
    bids: list[PriceLevelDict]
    asks: list[PriceLevelDict]
    total_bid_volume: int
    total_ask_volume: int
    bid_count: int
    ask_count: int
    imbalance: float | None


@dataclass
class MemoryConfig:
    """Configuration for memory management."""

    max_trades: int = 10000
    max_depth_entries: int = 1000
    cleanup_interval: int = 300  # seconds
    max_history_per_level: int = 50
    price_history_window_minutes: int = 30
    max_best_price_history: int = 1000
    max_spread_history: int = 1000
    max_delta_history: int = 1000


@dataclass
class IcebergConfig:
    """Configuration for iceberg detection."""

    min_refreshes: int = 5
    volume_threshold: int = 50
    time_window_minutes: int = 10
    confidence_threshold: float = 0.7


__all__ = [
    "DomType",
    "IcebergConfig",
    "MarketDataDict",
    "MemoryConfig",
    "OrderbookSide",
    "OrderbookSnapshot",
    "PriceLevelDict",
    "TradeDict",
]
