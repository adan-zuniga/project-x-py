"""
Type definitions for callback data structures.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides TypedDict definitions for all callback data structures used
    throughout the SDK. These types ensure type safety when handling
    events and callbacks from real-time feeds and manager updates.

Key Features:
    - Complete TypedDict definitions for all callback data
    - Event-specific data structures
    - Optional fields for partial updates
    - Type-safe callback handling
    - Comprehensive documentation

Callback Categories:
    - Order Events: Order updates, fills, cancellations
    - Position Events: Position changes, closures, alerts
    - Market Data: Quotes, trades, depth updates
    - Account Events: Balance changes, margin updates
    - System Events: Connection status, errors

Example Usage:
    ```python
    from project_x_py.types.callback_types import (
        OrderUpdateData,
        PositionUpdateData,
        QuoteUpdateData,
    )


    async def handle_order_update(data: OrderUpdateData) -> None:
        print(f"Order {data['order_id']} status: {data['status']}")


    async def handle_quote(data: QuoteUpdateData) -> None:
        print(f"New quote: Bid {data['bid']}, Ask {data['ask']}")
    ```

See Also:
    - `types.api_responses`: API response structures
    - `types.protocols`: Protocol definitions
    - `events`: Event system implementation
"""

from typing import NotRequired, TypedDict

from project_x_py.models import Order, Position


class OrderUpdateData(TypedDict):
    """Data for order update callbacks."""

    order_id: int
    order: NotRequired[Order]
    status: int
    fill_volume: NotRequired[int]
    filled_price: NotRequired[float]
    timestamp: str
    account_id: NotRequired[int]
    contract_id: NotRequired[str]


class OrderFilledData(TypedDict):
    """Data for order filled callbacks."""

    order_id: int
    order: Order
    filled_price: float
    filled_volume: int
    timestamp: str


class PositionUpdateData(TypedDict):
    """Data for position update callbacks."""

    position_id: int
    position: Position
    old_position: NotRequired[Position]
    contract_id: str
    size: int
    average_price: float
    type: int  # 1=LONG, 2=SHORT
    timestamp: str


class PositionClosedData(TypedDict):
    """Data for position closed callbacks."""

    contract_id: str
    position: Position
    pnl: NotRequired[float]
    timestamp: str


class PositionAlertData(TypedDict):
    """Data for position alert callbacks."""

    contract_id: str
    message: str
    position: Position
    alert: dict[str, float | bool | str]


class QuoteUpdateData(TypedDict):
    """Data for quote update callbacks."""

    contract_id: str
    bid: NotRequired[float]
    bid_size: NotRequired[int]
    ask: NotRequired[float]
    ask_size: NotRequired[int]
    last: NotRequired[float]
    last_size: NotRequired[int]
    timestamp: str


class MarketTradeData(TypedDict):
    """Data for market trade callbacks."""

    contract_id: str
    price: float
    size: int
    side: int  # 0=Buy, 1=Sell
    timestamp: str
    trade_id: NotRequired[str]


class MarketDepthData(TypedDict):
    """Data for market depth callbacks."""

    contract_id: str
    bids: list[tuple[float, int]]  # [(price, size), ...]
    asks: list[tuple[float, int]]  # [(price, size), ...]
    timestamp: str


class NewBarData(TypedDict):
    """Data for new bar creation callbacks."""

    timeframe: str
    data: dict[str, float | int | str]  # OHLCV bar data
    timestamp: str


class AccountUpdateData(TypedDict):
    """Data for account update callbacks."""

    account_id: int
    balance: float
    equity: NotRequired[float]
    margin: NotRequired[float]
    timestamp: str


class TradeExecutionData(TypedDict):
    """Data for trade execution callbacks."""

    trade_id: int
    order_id: int
    contract_id: str
    price: float
    size: int
    side: int  # 0=Buy, 1=Sell
    pnl: NotRequired[float]
    fees: float
    timestamp: str


class ConnectionStatusData(TypedDict):
    """Data for connection status callbacks."""

    hub: str  # 'user' or 'market'
    connected: bool
    timestamp: str
    error: NotRequired[str]


class ErrorData(TypedDict):
    """Data for error callbacks."""

    error_type: str
    message: str
    details: NotRequired[dict[str, str]]
    timestamp: str


class SystemStatusData(TypedDict):
    """Data for system status callbacks."""

    status: str  # 'connected', 'disconnected', 'error'
    message: NotRequired[str]
    timestamp: str


__all__ = [
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
]
