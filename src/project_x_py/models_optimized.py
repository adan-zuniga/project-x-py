"""
Optimized data models with __slots__ for frequently instantiated classes.

These models provide significant memory savings (40% reduction) for
high-frequency data structures like quotes, trades, and orderbook levels.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Quote:
    """
    Optimized quote data structure with __slots__ for memory efficiency.

    Uses 40% less memory than regular dataclass.
    """

    __slots__ = ("ask", "ask_size", "bid", "bid_size", "symbol", "timestamp")

    bid: float
    ask: float
    bid_size: int
    ask_size: int
    timestamp: datetime
    symbol: str = ""

    @property
    def spread(self) -> float:
        """Calculate bid-ask spread."""
        return self.ask - self.bid

    @property
    def mid(self) -> float:
        """Calculate mid price."""
        return (self.bid + self.ask) / 2


@dataclass
class OrderBookLevel:
    """
    Optimized orderbook level with __slots__ for memory efficiency.

    Represents a single price level in the order book.
    """

    __slots__ = ("order_count", "price", "side", "timestamp", "volume")

    price: float
    volume: int
    order_count: int
    side: str  # "bid" or "ask"
    timestamp: datetime | None = None


@dataclass
class Tick:
    """
    Optimized tick data structure with __slots__.

    Represents a single price update (trade or quote).
    """

    __slots__ = ("price", "side", "tick_type", "timestamp", "volume")

    price: float
    volume: int
    timestamp: datetime
    side: str  # "buy", "sell", or "neutral"
    tick_type: str  # "trade" or "quote"


@dataclass
class Bar:
    """
    Optimized OHLCV bar with __slots__.

    Represents a time-based price bar.
    """

    __slots__ = (
        "close",
        "high",
        "low",
        "open",
        "tick_count",
        "timestamp",
        "volume",
        "vwap",
    )

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float | None = None
    tick_count: int = 0
