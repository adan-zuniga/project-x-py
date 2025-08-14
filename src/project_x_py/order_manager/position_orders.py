"""
Async position-based order management for ProjectX.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides mixin logic for managing orders at the position level: closing open positions,
    adding stop losses/take profits, and synchronizing/canceling related orders as position
    size changes. Enables robust, risk-aware trading automations.

Key Features:
    - Async close, stop loss, and take profit for open positions
    - Automatic order/position tracking and synchronization
    - Bulk cancellation and modification of position-related orders
    - Integrates with order callbacks and bracket strategies
    - Position size change handling and order synchronization
    - Comprehensive position-order relationship management

Position Management Capabilities:
    - Close positions using market or limit orders
    - Add stop losses to protect existing positions
    - Add take profit orders for profit targets
    - Track orders associated with specific positions
    - Synchronize order sizes with position changes
    - Cancel all orders when positions are closed

Example Usage:
    ```python
    # V3.1: Position-based order management with TradingSuite
    import asyncio
    from project_x_py import TradingSuite


    async def main():
        # Initialize suite with integrated managers
        suite = await TradingSuite.create("MNQ")

        # Get current price for realistic order placement
        current_price = await suite.data.get_current_price()

        # V3.1: Close an existing position at market
        await suite.orders.close_position(suite.instrument_id, method="market")

        # V3.1: Close position with limit order
        await suite.orders.close_position(
            suite.instrument_id, method="limit", limit_price=current_price + 5.0
        )

        # V3.1: Add protective orders to existing position
        await suite.orders.add_stop_loss(
            suite.instrument_id, stop_price=current_price - 25.0
        )
        await suite.orders.add_take_profit(
            suite.instrument_id, limit_price=current_price + 25.0
        )

        # V3.1: Cancel specific order types for a position
        await suite.orders.cancel_position_orders(
            suite.instrument_id,
            ["stop"],  # Cancel stops only
        )
        await suite.orders.cancel_position_orders(suite.instrument_id)  # Cancel all

        # V3.1: Sync orders with position size after partial fill
        await suite.orders.sync_orders_with_position(
            suite.instrument_id, target_size=2, cancel_orphaned=True
        )

        await suite.disconnect()


    asyncio.run(main())
    ```

See Also:
    - `order_manager.core.OrderManager`
    - `order_manager.bracket_orders`
    - `order_manager.order_types`
"""

import logging
from typing import TYPE_CHECKING, Any

from project_x_py.exceptions import ProjectXOrderError
from project_x_py.models import OrderPlaceResponse
from project_x_py.types.trading import OrderSide, OrderStatus, PositionType

if TYPE_CHECKING:
    from project_x_py.types import OrderManagerProtocol

logger = logging.getLogger(__name__)


class PositionOrderMixin:
    """
    Mixin for position-related order management.

    Provides methods for managing orders in relation to existing positions, including
    closing positions, adding protective orders (stop losses, take profits), and
    synchronizing order sizes with position changes. This enables automated risk
    management and position-based trading strategies.
    """

    async def close_position(
        self: "OrderManagerProtocol",
        contract_id: str,
        method: str = "market",
        limit_price: float | None = None,
        account_id: int | None = None,
    ) -> OrderPlaceResponse | None:
        """
        Close an existing position using market or limit order.

        Args:
            contract_id: Contract ID of position to close
            method: "market" or "limit"
            limit_price: Limit price if using limit order
            account_id: Account ID. Uses default account if None.

        Returns:
            OrderPlaceResponse: Response from closing order

        Example:
            >>> # V3.1: Close position at market price
            >>> response = await suite.orders.close_position(
            ...     suite.instrument_id, method="market"
            ... )
            >>> print(
            ...     f"Closing order ID: {response.orderId if response else 'No position'}"
            ... )
            >>> # V3.1: Close position with limit order for better price
            >>> current_price = await suite.data.get_current_price()
            >>> response = await suite.orders.close_position(
            ...     suite.instrument_id, method="limit", limit_price=current_price + 5.0
            ... )
            >>> # V3.1: The method automatically determines the correct side
            >>> # For long position: sells to close
            >>> # For short position: buys to cover
        """
        # Get current position
        positions = await self.project_x.search_open_positions(account_id=account_id)
        position = None
        for pos in positions:
            if pos.contractId == contract_id:
                position = pos
                break

        if not position:
            logger.warning(f"⚠️ No open position found for {contract_id}")
            return None

        # Determine order side (opposite of position)
        # side = 1 if position.size > 0 else 0  # Sell long, Buy short
        side = OrderSide.SELL if position.type == PositionType.LONG else OrderSide.BUY
        size = abs(position.size)

        # Place closing order
        if method == "market":
            return await self.place_market_order(contract_id, side, size, account_id)
        elif method == "limit":
            if limit_price is None:
                raise ProjectXOrderError("Limit price required for limit close")
            return await self.place_limit_order(
                contract_id, side, size, limit_price, account_id
            )
        else:
            raise ProjectXOrderError(f"Invalid close method: {method}")

    async def add_stop_loss(
        self: "OrderManagerProtocol",
        contract_id: str,
        stop_price: float,
        size: int | None = None,
        account_id: int | None = None,
    ) -> OrderPlaceResponse | None:
        """
        Add a stop loss order to protect an existing position.

        Args:
            contract_id: Contract ID of the position
            stop_price: Stop loss trigger price
            size: Number of contracts (defaults to position size)
            account_id: Account ID. Uses default account if None.

        Returns:
            OrderPlaceResponse if successful, None if no position

        Example:
            >>> # V3.1: Add stop loss to protect existing position
            >>> current_price = await suite.data.get_current_price()
            >>> response = await suite.orders.add_stop_loss(
            ...     suite.instrument_id, stop_price=current_price - 20.0
            ... )
            >>> print(
            ...     f"Stop order ID: {response.orderId if response else 'No position'}"
            ... )
            >>> # V3.1: Add partial stop (protect only part of position)
            >>> response = await suite.orders.add_stop_loss(
            ...     suite.instrument_id, stop_price=current_price - 20.0, size=1
            ... )
            >>> # V3.1: Stop is automatically placed on opposite side of position
            >>> # Long position: stop sell order below current price
            >>> # Short position: stop buy order above current price
        """
        # Get current position
        positions = await self.project_x.search_open_positions(account_id=account_id)
        position = None
        for pos in positions:
            if pos.contractId == contract_id:
                position = pos
                break

        if not position:
            logger.warning(f"⚠️ No open position found for {contract_id}")
            return None

        # Determine order side (opposite of position)
        side = OrderSide.SELL if position.type == PositionType.LONG else OrderSide.BUY
        order_size = size if size else abs(position.size)

        # Place stop order
        response = await self.place_stop_order(
            contract_id, side, order_size, stop_price, account_id
        )

        # Track order for position
        if response and response.success:
            await self.track_order_for_position(
                contract_id, response.orderId, "stop", account_id
            )

        return response

    async def add_take_profit(
        self: "OrderManagerProtocol",
        contract_id: str,
        limit_price: float,
        size: int | None = None,
        account_id: int | None = None,
    ) -> OrderPlaceResponse | None:
        """
        Add a take profit (limit) order to an existing position.

        Args:
            contract_id: Contract ID of the position
            limit_price: Take profit price
            size: Number of contracts (defaults to position size)
            account_id: Account ID. Uses default account if None.

        Returns:
            OrderPlaceResponse if successful, None if no position

        Example:
            >>> # V3.1: Add take profit target to existing position
            >>> current_price = await suite.data.get_current_price()
            >>> response = await suite.orders.add_take_profit(
            ...     suite.instrument_id, limit_price=current_price + 25.0
            ... )
            >>> print(
            ...     f"Target order ID: {response.orderId if response else 'No position'}"
            ... )
            >>> # V3.1: Add partial take profit (scale out strategy)
            >>> response = await suite.orders.add_take_profit(
            ...     suite.instrument_id, limit_price=current_price + 25.0, size=1
            ... )
            >>> # V3.1: Target is automatically placed on opposite side of position
            >>> # Long position: limit sell order above current price
            >>> # Short position: limit buy order below current price
        """
        # Get current position
        positions = await self.project_x.search_open_positions(account_id=account_id)
        position = None
        for pos in positions:
            if pos.contractId == contract_id:
                position = pos
                break

        if not position:
            logger.warning(f"⚠️ No open position found for {contract_id}")
            return None

        # Determine order side (opposite of position)
        side = OrderSide.SELL if position.type == PositionType.LONG else OrderSide.BUY
        order_size = size if size else abs(position.size)

        # Place limit order
        response = await self.place_limit_order(
            contract_id, side, order_size, limit_price, account_id
        )

        # Track order for position
        if response and response.success:
            await self.track_order_for_position(
                contract_id, response.orderId, "target", account_id
            )

        return response

    async def track_order_for_position(
        self: "OrderManagerProtocol",
        contract_id: str,
        order_id: int,
        order_type: str = "entry",
        account_id: int | None = None,
    ) -> None:
        """
        Track an order as part of position management.

        Args:
            contract_id: Contract ID the order is for
            order_id: Order ID to track
            order_type: Type of order: "entry", "stop", or "target"
            account_id: Account ID for multi-account support
        """
        async with self.order_lock:
            if contract_id not in self.position_orders:
                self.position_orders[contract_id] = {
                    "entry_orders": [],
                    "stop_orders": [],
                    "target_orders": [],
                }

            if order_type == "entry":
                self.position_orders[contract_id]["entry_orders"].append(order_id)
            elif order_type == "stop":
                self.position_orders[contract_id]["stop_orders"].append(order_id)
            elif order_type == "target":
                self.position_orders[contract_id]["target_orders"].append(order_id)

            self.order_to_position[order_id] = contract_id
            logger.debug(
                f"Tracking {order_type} order {order_id} for position {contract_id}"
            )

    def untrack_order(self: "OrderManagerProtocol", order_id: int) -> None:
        """
        Remove an order from position tracking.

        Args:
            order_id: Order ID to untrack
        """
        if order_id in self.order_to_position:
            contract_id = self.order_to_position[order_id]
            del self.order_to_position[order_id]

            # Remove from position orders
            if contract_id in self.position_orders:
                for order_list in self.position_orders[contract_id].values():
                    if order_id in order_list:
                        order_list.remove(order_id)

            logger.debug(f"Untracked order {order_id}")

    def get_position_orders(
        self: "OrderManagerProtocol", contract_id: str
    ) -> dict[str, list[int]]:
        """
        Get all orders associated with a position.

        Args:
            contract_id: Contract ID to get orders for

        Returns:
            Dict with entry_orders, stop_orders, and target_orders lists
        """
        return self.position_orders.get(
            contract_id, {"entry_orders": [], "stop_orders": [], "target_orders": []}
        )

    async def cancel_position_orders(
        self: "OrderManagerProtocol",
        contract_id: str,
        order_types: list[str] | None = None,
        account_id: int | None = None,
    ) -> dict[str, int]:
        """
        Cancel all orders associated with a position.

        Args:
            contract_id: Contract ID of the position
            order_types: List of order types to cancel (e.g., ["stop", "target"])
                        If None, cancels all order types
            account_id: Account ID. Uses default account if None.

        Returns:
            Dict with counts of cancelled orders by type

        Example:
            >>> # V3.1: Cancel only stop orders for a position
            >>> results = await suite.orders.cancel_position_orders(
            ...     suite.instrument_id, ["stop"]
            ... )
            >>> print(f"Cancelled {results['stop']} stop orders")
            >>> # V3.1: Cancel all orders for position (stops, targets, entries)
            >>> results = await suite.orders.cancel_position_orders(suite.instrument_id)
            >>> print(
            ...     f"Cancelled: {results['stop']} stops, {results['target']} targets"
            ... )
            >>> # V3.1: Cancel specific order types
            >>> results = await suite.orders.cancel_position_orders(
            ...     suite.instrument_id, order_types=["stop", "target"]
            ... )
        """
        if order_types is None:
            order_types = ["entry", "stop", "target"]

        position_orders = self.get_position_orders(contract_id)
        results = {"entry": 0, "stop": 0, "target": 0}

        for order_type in order_types:
            order_key = f"{order_type}_orders"
            if order_key in position_orders:
                for order_id in position_orders[order_key][:]:  # Copy list
                    try:
                        if await self.cancel_order(order_id, account_id):
                            results[order_type] += 1
                            self.untrack_order(order_id)
                    except Exception as e:
                        logger.error(
                            f"Failed to cancel {order_type} order {order_id}: {e}"
                        )

        return results

    async def update_position_order_sizes(
        self: "OrderManagerProtocol",
        contract_id: str,
        new_size: int,
        account_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Update order sizes for a position (e.g., after partial fill).

        Args:
            contract_id: Contract ID of the position
            new_size: New position size to protect
            account_id: Account ID. Uses default account if None.

        Returns:
            Dict with update results
        """
        position_orders = self.get_position_orders(contract_id)
        results: dict[str, Any] = {"modified": 0, "failed": 0, "errors": []}

        # Update stop and target orders
        for order_type in ["stop", "target"]:
            order_key = f"{order_type}_orders"
            for order_id in position_orders.get(order_key, []):
                try:
                    # Get current order
                    order = await self.get_order_by_id(order_id)
                    if order and order.status == OrderStatus.OPEN:  # Open
                        # Modify order size
                        success = await self.modify_order(
                            order_id=order_id, size=new_size
                        )
                        if success:
                            results["modified"] += 1
                        else:
                            results["failed"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({"order_id": order_id, "error": str(e)})

        return results

    async def sync_orders_with_position(
        self: "OrderManagerProtocol",
        contract_id: str,
        target_size: int,
        cancel_orphaned: bool = True,
        account_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Synchronize orders with actual position size.

        Args:
            contract_id: Contract ID to sync
            target_size: Expected position size
            cancel_orphaned: Whether to cancel orders if no position exists
            account_id: Account ID. Uses default account if None.

        Returns:
            Dict with sync results
        """
        results: dict[str, Any] = {"actions_taken": [], "errors": []}

        if target_size == 0 and cancel_orphaned:
            # No position, cancel all orders
            cancel_results = await self.cancel_position_orders(
                contract_id, account_id=account_id
            )
            results["actions_taken"].append(
                {"action": "cancelled_all_orders", "details": cancel_results}
            )
        elif target_size > 0:
            # Update order sizes to match position
            update_results = await self.update_position_order_sizes(
                contract_id, target_size, account_id
            )
            results["actions_taken"].append(
                {"action": "updated_order_sizes", "details": update_results}
            )

        return results

    async def on_position_changed(
        self: "OrderManagerProtocol",
        contract_id: str,
        old_size: int,
        new_size: int,
        account_id: int | None = None,
    ) -> None:
        """
        Handle position size changes (e.g., partial fills).

        Args:
            contract_id: Contract ID of the position
            old_size: Previous position size
            new_size: New position size
            account_id: Account ID for multi-account support
        """
        logger.info(f"Position changed for {contract_id}: {old_size} -> {new_size}")

        if new_size == 0:
            # Position closed, cancel remaining orders
            await self.on_position_closed(contract_id, account_id)
        else:
            # Position partially filled, update order sizes
            await self.sync_orders_with_position(
                contract_id, abs(new_size), cancel_orphaned=True, account_id=account_id
            )

    async def on_position_closed(
        self: "OrderManagerProtocol", contract_id: str, account_id: int | None = None
    ) -> None:
        """
        Handle position closure by canceling all related orders.

        Args:
            contract_id: Contract ID of the closed position
            account_id: Account ID for multi-account support
        """
        logger.info(f"Position closed for {contract_id}, cancelling all orders")

        # Cancel all orders for this position
        cancel_results = await self.cancel_position_orders(
            contract_id, account_id=account_id
        )

        # Clean up tracking
        if contract_id in self.position_orders:
            del self.position_orders[contract_id]

        # Remove from order_to_position mapping
        orders_to_remove = [
            order_id
            for order_id, pos_id in self.order_to_position.items()
            if pos_id == contract_id
        ]
        for order_id in orders_to_remove:
            del self.order_to_position[order_id]

        logger.info(f"Cleaned up position {contract_id}: {cancel_results}")
