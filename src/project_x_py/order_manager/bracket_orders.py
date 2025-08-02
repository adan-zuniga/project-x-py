"""Bracket order functionality for complex order strategies."""

import logging
from typing import TYPE_CHECKING

from project_x_py.exceptions import ProjectXOrderError
from project_x_py.models import BracketOrderResponse

if TYPE_CHECKING:
    from project_x_py.order_manager.protocols import OrderManagerProtocol

logger = logging.getLogger(__name__)


class BracketOrderMixin:
    """Mixin for bracket order functionality."""

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
                raise ProjectXOrderError("Failed to place entry order")

            # Place stop loss (opposite side)
            stop_side = 1 if side == 0 else 0
            stop_response = await self.place_stop_order(
                contract_id, stop_side, size, stop_loss_price, account_id
            )

            # Place take profit (opposite side)
            target_response = await self.place_limit_order(
                contract_id, stop_side, size, take_profit_price, account_id
            )

            # Create bracket response
            bracket_response = BracketOrderResponse(
                success=True,
                entry_order_id=entry_response.orderId,
                stop_order_id=stop_response.orderId if stop_response else None,
                target_order_id=target_response.orderId if target_response else None,
                entry_price=entry_price if entry_price else 0.0,
                stop_loss_price=stop_loss_price if stop_loss_price else 0.0,
                take_profit_price=take_profit_price if take_profit_price else 0.0,
                entry_response=entry_response,
                stop_response=stop_response,
                target_response=target_response,
                error_message=None,
            )

            # Track bracket relationship
            self.position_orders[contract_id]["entry_orders"].append(
                entry_response.orderId
            )
            if stop_response:
                self.position_orders[contract_id]["stop_orders"].append(
                    stop_response.orderId
                )
            if target_response:
                self.position_orders[contract_id]["target_orders"].append(
                    target_response.orderId
                )

            self.stats["bracket_orders_placed"] = (
                self.stats["bracket_orders_placed"] + 1
            )
            logger.info(
                f"✅ Bracket order placed: Entry={entry_response.orderId}, "
                f"Stop={stop_response.orderId if stop_response else 'None'}, "
                f"Target={target_response.orderId if target_response else 'None'}"
            )

            return bracket_response

        except Exception as e:
            logger.error(f"Failed to place bracket order: {e}")
            raise ProjectXOrderError(f"Failed to place bracket order: {e}") from e
