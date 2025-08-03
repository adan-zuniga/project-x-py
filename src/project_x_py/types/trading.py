"""
Trading-related type definitions for orders and positions.

This module contains type definitions for trading operations including
order management, position tracking, and execution statistics.
"""

from datetime import datetime
from enum import IntEnum
from typing import TypedDict


class OrderSide(IntEnum):
    """Order side enumeration."""

    BUY = 0
    SELL = 1


class OrderType(IntEnum):
    """Order type enumeration."""

    MARKET = 0
    LIMIT = 1
    STOP = 2
    STOP_LIMIT = 3
    TRAILING_STOP = 4


class OrderStatus(IntEnum):
    """Order status enumeration."""

    PENDING = 0
    OPEN = 1
    FILLED = 2
    CANCELLED = 3
    REJECTED = 4
    EXPIRED = 5


class OrderStats(TypedDict):
    """Type definition for order statistics."""

    orders_placed: int
    orders_cancelled: int
    orders_modified: int
    bracket_orders_placed: int
    last_order_time: datetime | None


class PositionSide(IntEnum):
    """Position side enumeration."""

    LONG = 0
    SHORT = 1
    FLAT = 2


__all__ = [
    "OrderSide",
    "OrderStats",
    "OrderStatus",
    "OrderType",
    "PositionSide",
]
