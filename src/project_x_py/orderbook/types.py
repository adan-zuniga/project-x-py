"""
Type definitions and constants for the async orderbook module.

This module contains shared types, enums, and constants used across
the async orderbook implementation.
"""

from collections.abc import Callable, Coroutine
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


# Type aliases for async callbacks
AsyncCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
SyncCallback = Callable[[dict[str, Any]], None]
CallbackType = AsyncCallback | SyncCallback


# Constants
DEFAULT_TIMEZONE = "America/Chicago"
TICK_SIZE_PRECISION = 8  # Decimal places for tick size rounding
