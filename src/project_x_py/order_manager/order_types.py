"""Order placement methods for different order types."""

import logging
from typing import TYPE_CHECKING

from project_x_py.models import OrderPlaceResponse

if TYPE_CHECKING:
    from project_x_py.order_manager.protocols import OrderManagerProtocol

logger = logging.getLogger(__name__)


class OrderTypesMixin:
    """Mixin for different order type placement methods."""

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
