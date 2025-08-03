"""
Async order type placement mixin for ProjectX.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Implements mixin methods for placing specific order types (market, limit,
    stop, trailing stop) in the async OrderManager system. Encapsulates order-type
    validation, parameter handling, and delegates to the unified underlying API.

Key Features:
    - Async placement of market, limit, stop, and trailing stop orders
    - Standardized argument validation and contract handling
    - Integrates with bracket and position order mixins
    - Returns model-typed responses for downstream logic
    - Automatic price alignment to instrument tick sizes
    - Comprehensive error handling and validation

Order Types Supported:
    - Market Orders: Immediate execution at current market price
    - Limit Orders: Execution at specified price or better
    - Stop Orders: Market orders triggered at stop price
    - Trailing Stop Orders: Dynamic stops that follow price movement

Each order type method provides a simplified interface for common order placement
scenarios while maintaining full compatibility with the underlying order system.

Example Usage:
    ```python
    # Assuming om is an instance of OrderManager
    await om.place_limit_order("MES", 1, 2, 5000.0)
    await om.place_market_order("MGC", 0, 1)
    await om.place_stop_order("MGC", 1, 1, 2040.0)
    await om.place_trailing_stop_order("MGC", 1, 1, 5.0)
    ```

See Also:
    - `order_manager.core.OrderManager`
    - `order_manager.bracket_orders`
    - `order_manager.position_orders`
"""

import logging
from typing import TYPE_CHECKING

from project_x_py.models import OrderPlaceResponse

if TYPE_CHECKING:
    from project_x_py.types import OrderManagerProtocol

logger = logging.getLogger(__name__)


class OrderTypesMixin:
    """
    Mixin for different order type placement methods.

    Provides simplified methods for placing specific order types (market, limit, stop,
    trailing stop) that delegate to the core place_order method. Each method handles
    the specific parameters and validation required for that order type while maintaining
    consistency with the overall order management system.
    """

    async def place_market_order(
        self: "OrderManagerProtocol",
        contract_id: str,
        side: int,
        size: int,
        account_id: int | None = None,
    ) -> OrderPlaceResponse:
        """
        Place a market order (immediate execution at current market price).

        Args:
            contract_id: The contract ID to trade
            side: Order side: 0=Buy, 1=Sell
            size: Number of contracts to trade
            account_id: Account ID. Uses default account if None.

        Returns:
            OrderPlaceResponse: Response containing order ID and status

        Example:
            >>> response = await order_manager.place_market_order("MGC", 0, 1)
        """
        return await self.place_order(
            contract_id=contract_id,
            side=side,
            size=size,
            order_type=2,  # Market
            account_id=account_id,
        )

    async def place_limit_order(
        self: "OrderManagerProtocol",
        contract_id: str,
        side: int,
        size: int,
        limit_price: float,
        account_id: int | None = None,
    ) -> OrderPlaceResponse:
        """
        Place a limit order (execute only at specified price or better).

        Args:
            contract_id: The contract ID to trade
            side: Order side: 0=Buy, 1=Sell
            size: Number of contracts to trade
            limit_price: Maximum price for buy orders, minimum price for sell orders
            account_id: Account ID. Uses default account if None.

        Returns:
            OrderPlaceResponse: Response containing order ID and status

        Example:
            >>> response = await order_manager.place_limit_order("MGC", 1, 1, 2050.0)
        """
        return await self.place_order(
            contract_id=contract_id,
            side=side,
            size=size,
            order_type=1,  # Limit
            limit_price=limit_price,
            account_id=account_id,
        )

    async def place_stop_order(
        self: "OrderManagerProtocol",
        contract_id: str,
        side: int,
        size: int,
        stop_price: float,
        account_id: int | None = None,
    ) -> OrderPlaceResponse:
        """
        Place a stop order (market order triggered at stop price).

        Args:
            contract_id: The contract ID to trade
            side: Order side: 0=Buy, 1=Sell
            size: Number of contracts to trade
            stop_price: Price level that triggers the market order
            account_id: Account ID. Uses default account if None.

        Returns:
            OrderPlaceResponse: Response containing order ID and status

        Example:
            >>> # Stop loss for long position
            >>> response = await order_manager.place_stop_order("MGC", 1, 1, 2040.0)
        """
        return await self.place_order(
            contract_id=contract_id,
            side=side,
            size=size,
            order_type=4,  # Stop
            stop_price=stop_price,
            account_id=account_id,
        )

    async def place_trailing_stop_order(
        self: "OrderManagerProtocol",
        contract_id: str,
        side: int,
        size: int,
        trail_price: float,
        account_id: int | None = None,
    ) -> OrderPlaceResponse:
        """
        Place a trailing stop order (stop that follows price by trail amount).

        Args:
            contract_id: The contract ID to trade
            side: Order side: 0=Buy, 1=Sell
            size: Number of contracts to trade
            trail_price: Trail amount (distance from current price)
            account_id: Account ID. Uses default account if None.

        Returns:
            OrderPlaceResponse: Response containing order ID and status

        Example:
            >>> response = await order_manager.place_trailing_stop_order(
            ...     "MGC", 1, 1, 5.0
            ... )
        """
        return await self.place_order(
            contract_id=contract_id,
            order_type=5,  # Trailing stop order
            side=side,
            size=size,
            trail_price=trail_price,
            account_id=account_id,
        )
