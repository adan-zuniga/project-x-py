"""Type definitions for order management."""

from datetime import datetime
from typing import TypedDict


class OrderStats(TypedDict):
    """Type definition for order statistics."""

    orders_placed: int
    orders_cancelled: int
    orders_modified: int
    bracket_orders_placed: int
    last_order_time: datetime | None
