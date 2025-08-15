"""
Async bracket order strategies for ProjectX.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides mixin logic for placing and managing bracket orders—sophisticated, three-legged
    order strategies consisting of entry, stop loss, and take profit orders. Ensures risk
    controls are established atomically and linked to positions for robust trade automation.

Key Features:
    - Place async bracket orders (entry, stop, target) as a single operation
    - Price/side validation and position link management
    - Automatic risk management: stops and targets managed with entry
    - Integrates with core OrderManager and position tracking
    - Comprehensive error handling and validation
    - Real-time tracking of all bracket components

Bracket Order Components:
    - Entry Order: Primary order to establish position (limit or market)
    - Stop Loss Order: Risk management order triggered if price moves against position
    - Take Profit Order: Profit target order triggered if price moves favorably

The bracket order ensures that risk management is in place immediately when the entry
order fills, providing consistent trade management without manual intervention.

Example Usage:
    ```python
    # V3.1: Place bracket orders with TradingSuite
    import asyncio
    from project_x_py import TradingSuite


    async def main():
        # Initialize suite with integrated order manager
        suite = await TradingSuite.create("MNQ")

        # Get current market price for realistic order placement
        current_price = await suite.data.get_current_price()

        # V3.1: Place a bullish bracket order (buy with stop below, target above)
        bracket = await suite.orders.place_bracket_order(
            contract_id=suite.instrument_id,
            side=0,  # Buy
            size=1,
            entry_price=current_price - 10.0,  # Enter below market
            stop_loss_price=current_price - 30.0,  # Risk: $30 per contract
            take_profit_price=current_price + 20.0,  # Reward: $30 per contract
            entry_type="limit",  # Can also use "market"
        )

        print(f"Bracket order placed successfully:")
        print(f"  Entry Order ID: {bracket.entry_order_id}")
        print(f"  Stop Loss ID: {bracket.stop_order_id}")
        print(f"  Take Profit ID: {bracket.target_order_id}")

        # V3.1: Place a bearish bracket order (sell with stop above, target below)
        short_bracket = await suite.orders.place_bracket_order(
            contract_id=suite.instrument_id,
            side=1,  # Sell
            size=2,
            entry_price=current_price + 10.0,  # Enter above market for short
            stop_loss_price=current_price + 30.0,  # Stop above for short
            take_profit_price=current_price - 20.0,  # Target below for short
        )

        await suite.disconnect()


    asyncio.run(main())
    ```

See Also:
    - `order_manager.core.OrderManager`
    - `order_manager.position_orders`
    - `order_manager.order_types`
"""

import logging
from typing import TYPE_CHECKING

from project_x_py.exceptions import ProjectXOrderError
from project_x_py.models import BracketOrderResponse

if TYPE_CHECKING:
    from project_x_py.types import OrderManagerProtocol

logger = logging.getLogger(__name__)


class BracketOrderMixin:
    """
    Mixin for bracket order functionality.

    Provides methods for placing and managing bracket orders, which are sophisticated
    three-legged order strategies that combine entry, stop loss, and take profit orders
    into a single atomic operation. This ensures consistent risk management and trade
    automation.
    """

    async def place_bracket_order(
        self: "OrderManagerProtocol",
        contract_id: str,
        side: int,
        size: int,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: float,
        entry_type: str = "limit",
        account_id: int | None = None,
        custom_tag: str | None = None,
    ) -> BracketOrderResponse:
        """
        Place a bracket order with entry, stop loss, and take profit orders.

        A bracket order is a sophisticated order strategy that consists of three linked orders:
        1. Entry order (limit or market) - The primary order to establish a position
        2. Stop loss order - Risk management order that's triggered if price moves against position
        3. Take profit order - Profit target order that's triggered if price moves favorably

        The advantage of bracket orders is automatic risk management - the stop loss and
        take profit orders are placed immediately when the entry fills, ensuring consistent
        trade management. Each order is tracked and associated with the position.

        This method performs comprehensive validation to ensure:
        - Stop loss is properly positioned relative to entry price
        - Take profit is properly positioned relative to entry price
        - All prices are aligned to instrument tick sizes
        - Order sizes are valid and positive

        Args:
            contract_id: The contract ID to trade (e.g., "MGC", "MES", "F.US.EP")
            side: Order side: 0=Buy, 1=Sell
            size: Number of contracts to trade (positive integer)
            entry_price: Entry price for the position (ignored for market entries)
            stop_loss_price: Stop loss price for risk management
                For buy orders: must be below entry price
                For sell orders: must be above entry price
            take_profit_price: Take profit price (profit target)
                For buy orders: must be above entry price
                For sell orders: must be below entry price
            entry_type: Entry order type: "limit" (default) or "market"
            account_id: Account ID. Uses default account if None.
            custom_tag: Custom identifier for the bracket orders (not used in current implementation)

        Returns:
            BracketOrderResponse with comprehensive information including:
                - success: Whether the bracket order was placed successfully
                - entry_order_id: ID of the entry order
                - stop_order_id: ID of the stop loss order
                - target_order_id: ID of the take profit order
                - entry_response: Complete response from entry order placement
                - stop_response: Complete response from stop order placement
                - target_response: Complete response from take profit order placement
                - error_message: Error message if placement failed

        Raises:
            ProjectXOrderError: If bracket order validation or placement fails

        Example:
            >>> # V3: Place a bullish bracket order with 1:2 risk/reward
            >>> bracket = await om.place_bracket_order(
            ...     contract_id="MGC",
            ...     side=0,  # Buy
            ...     size=1,
            ...     entry_price=2050.0,
            ...     stop_loss_price=2040.0,  # $10 risk
            ...     take_profit_price=2070.0,  # $20 reward (2:1 R/R)
            ...     entry_type="limit",  # Use "market" for immediate entry
            ... )
            >>> print(f"Entry: {bracket.entry_order_id}")
            >>> print(f"Stop: {bracket.stop_order_id}")
            >>> print(f"Target: {bracket.target_order_id}")
            >>> print(f"Success: {bracket.success}")
            >>> # V3: Place a bearish bracket order (short position)
            >>> short_bracket = await om.place_bracket_order(
            ...     contract_id="ES",
            ...     side=1,  # Sell/Short
            ...     size=1,
            ...     entry_price=5000.0,
            ...     stop_loss_price=5020.0,  # Stop above for short
            ...     take_profit_price=4960.0,  # Target below for short
            ... )
        """
        try:
            # Validate prices
            if side == 0:  # Buy
                if stop_loss_price >= entry_price:
                    raise ProjectXOrderError(
                        f"Buy order stop loss ({stop_loss_price}) must be below entry ({entry_price})"
                    )
                if take_profit_price <= entry_price:
                    raise ProjectXOrderError(
                        f"Buy order take profit ({take_profit_price}) must be above entry ({entry_price})"
                    )
            else:  # Sell
                if stop_loss_price <= entry_price:
                    raise ProjectXOrderError(
                        f"Sell order stop loss ({stop_loss_price}) must be above entry ({entry_price})"
                    )
                if take_profit_price >= entry_price:
                    raise ProjectXOrderError(
                        f"Sell order take profit ({take_profit_price}) must be below entry ({entry_price})"
                    )

            # Place entry order
            if entry_type.lower() == "market":
                entry_response = await self.place_market_order(
                    contract_id, side, size, account_id
                )
            else:  # limit
                entry_response = await self.place_limit_order(
                    contract_id, side, size, entry_price, account_id
                )

            if not entry_response or not entry_response.success:
                raise ProjectXOrderError("Failed to place entry order for bracket.")

            entry_order_id = entry_response.orderId
            logger.info(
                f"Bracket entry order {entry_order_id} placed. Waiting for fill..."
            )

            # Wait for the entry order to fill
            is_filled = await self._wait_for_order_fill(
                entry_order_id, timeout_seconds=60
            )

            if not is_filled:
                logger.warning(
                    f"Bracket entry order {entry_order_id} did not fill. Cancelling."
                )
                try:
                    await self.cancel_order(entry_order_id, account_id)
                except ProjectXOrderError as e:
                    logger.error(
                        f"Failed to cancel unfilled bracket entry order {entry_order_id}: {e}"
                    )
                raise ProjectXOrderError(
                    f"Bracket entry order {entry_order_id} did not fill."
                )

            logger.info(
                f"Bracket entry order {entry_order_id} filled. Placing protective orders."
            )

            stop_response = None
            target_response = None
            try:
                # Place stop loss (opposite side)
                stop_side = 1 if side == 0 else 0
                stop_response = await self.place_stop_order(
                    contract_id, stop_side, size, stop_loss_price, account_id
                )

                # Place take profit (opposite side)
                target_response = await self.place_limit_order(
                    contract_id, stop_side, size, take_profit_price, account_id
                )

                if (
                    not stop_response
                    or not stop_response.success
                    or not target_response
                    or not target_response.success
                ):
                    raise ProjectXOrderError(
                        "Failed to place one or both protective orders."
                    )

                # Link the two protective orders for OCO
                stop_order_id = stop_response.orderId
                target_order_id = target_response.orderId
                self._link_oco_orders(stop_order_id, target_order_id)

                # Track all orders for the position
                await self.track_order_for_position(
                    contract_id, entry_order_id, "entry"
                )
                await self.track_order_for_position(contract_id, stop_order_id, "stop")
                await self.track_order_for_position(
                    contract_id, target_order_id, "target"
                )

                self.stats["bracket_orders"] += 1
                logger.info(
                    f"✅ Bracket order completed: Entry={entry_order_id}, Stop={stop_order_id}, Target={target_order_id}"
                )

                return BracketOrderResponse(
                    success=True,
                    entry_order_id=entry_order_id,
                    stop_order_id=stop_order_id,
                    target_order_id=target_order_id,
                    entry_price=entry_price,
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price,
                    entry_response=entry_response,
                    stop_response=stop_response,
                    target_response=target_response,
                    error_message=None,
                )
            except Exception as e:
                logger.error(
                    f"Failed to place protective orders for filled entry {entry_order_id}: {e}. Closing position."
                )
                await self.close_position(contract_id, account_id=account_id)
                if stop_response and stop_response.success:
                    await self.cancel_order(stop_response.orderId)
                if target_response and target_response.success:
                    await self.cancel_order(target_response.orderId)
                raise ProjectXOrderError(
                    f"Failed to place protective orders: {e}"
                ) from e

        except Exception as e:
            logger.error(f"Failed to place bracket order: {e}")
            raise ProjectXOrderError(f"Failed to place bracket order: {e}") from e
