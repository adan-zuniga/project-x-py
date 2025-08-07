"""Managed trade context manager for risk-controlled trading."""

import logging
from typing import TYPE_CHECKING, Any

from project_x_py.types import OrderSide, OrderType
from project_x_py.types.protocols import OrderManagerProtocol, PositionManagerProtocol

if TYPE_CHECKING:
    from project_x_py.models import Order, Position

    from .core import RiskManager

logger = logging.getLogger(__name__)


class ManagedTrade:
    """Context manager for risk-managed trade execution.

    Automatically handles:
    - Position sizing based on risk parameters
    - Trade validation against risk rules
    - Stop-loss and take-profit attachment
    - Position monitoring and adjustment
    - Cleanup on exit
    """

    def __init__(
        self,
        risk_manager: "RiskManager",
        order_manager: OrderManagerProtocol,
        position_manager: PositionManagerProtocol,
        instrument_id: str,
        max_risk_percent: float | None = None,
        max_risk_amount: float | None = None,
    ):
        """Initialize managed trade.

        Args:
            risk_manager: Risk manager instance
            order_manager: Order manager instance
            position_manager: Position manager instance
            instrument_id: Instrument/contract ID to trade
            max_risk_percent: Override max risk percentage
            max_risk_amount: Override max risk dollar amount
        """
        self.risk = risk_manager
        self.orders = order_manager
        self.positions = position_manager
        self.instrument_id = instrument_id
        self.max_risk_percent = max_risk_percent
        self.max_risk_amount = max_risk_amount

        # Track orders and positions created
        self._orders: list[Order] = []
        self._positions: list[Position] = []
        self._entry_order: Order | None = None
        self._stop_order: Order | None = None
        self._target_order: Order | None = None

    async def __aenter__(self) -> "ManagedTrade":
        """Enter managed trade context."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit managed trade context with cleanup."""
        try:
            # Cancel any unfilled orders
            for order in self._orders:
                if order.is_working:
                    try:
                        await self.orders.cancel_order(order.id)
                        logger.info(f"Cancelled unfilled order {order.id}")
                    except Exception as e:
                        logger.error(f"Error cancelling order {order.id}: {e}")

            # Log trade summary
            if self._entry_order:
                logger.info(
                    f"Managed trade completed for {self.instrument_id}: "
                    f"Entry: {self._entry_order.status_str}, "
                    f"Positions: {len(self._positions)}"
                )

        except Exception as e:
            logger.error(f"Error in managed trade cleanup: {e}")

        # Don't suppress exceptions
        return False

    async def enter_long(
        self,
        entry_price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        size: int | None = None,
        order_type: OrderType = OrderType.MARKET,
    ) -> dict[str, Any]:
        """Enter a long position with risk management.

        Args:
            entry_price: Limit order price (None for market)
            stop_loss: Stop loss price (required)
            take_profit: Take profit price (calculated if not provided)
            size: Position size (calculated if not provided)
            order_type: Order type (default: MARKET)

        Returns:
            Dictionary with order details and risk metrics
        """
        if stop_loss is None:
            raise ValueError("Stop loss is required for risk management")

        # Use market price if no entry price
        if entry_price is None and order_type != OrderType.MARKET:
            raise ValueError("Entry price required for limit orders")

        # Calculate position size if not provided
        if size is None:
            if entry_price is None:
                # Get current market price
                # TODO: Get from data manager
                entry_price = await self._get_market_price()

            sizing = await self.risk.calculate_position_size(
                entry_price=entry_price,
                stop_loss=stop_loss,
                risk_percent=self.max_risk_percent,
                risk_amount=self.max_risk_amount,
            )
            size = sizing["position_size"]

        # Validate trade
        mock_order = self._create_mock_order(
            side=OrderSide.BUY,
            size=size,
            price=entry_price,
            order_type=order_type,
        )

        validation = await self.risk.validate_trade(mock_order)
        if not validation["is_valid"]:
            raise ValueError(f"Trade validation failed: {validation['reasons']}")

        # Place entry order
        if order_type == OrderType.MARKET:
            order_result = await self.orders.place_market_order(
                contract_id=self.instrument_id,
                side=OrderSide.BUY,
                size=size,
            )
        else:
            if entry_price is None:
                raise ValueError("Entry price is required for limit orders")
            order_result = await self.orders.place_limit_order(
                contract_id=self.instrument_id,
                side=OrderSide.BUY,
                size=size,
                limit_price=entry_price,
            )

        if order_result.success:
            # Get the actual order object
            orders = await self.orders.search_open_orders()
            self._entry_order = next(
                (o for o in orders if o.id == order_result.orderId), None
            )
            if self._entry_order:
                self._orders.append(self._entry_order)

        # Wait for fill if market order
        if order_type == OrderType.MARKET:
            # Market orders should fill immediately
            # TODO: Add proper fill waiting logic
            pass

        # Get position and attach risk orders
        positions = await self.positions.get_all_positions()
        position = next(
            (p for p in positions if p.contractId == self.instrument_id), None
        )

        if position:
            self._positions.append(position)

            # Attach risk orders
            risk_orders = await self.risk.attach_risk_orders(
                position=position,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

            if "bracket_order" in risk_orders:
                bracket = risk_orders["bracket_order"]
                if "stop_order" in bracket:
                    self._stop_order = bracket["stop_order"]
                    if self._stop_order:
                        self._orders.append(self._stop_order)
                if "limit_order" in bracket:
                    self._target_order = bracket["limit_order"]
                    if self._target_order:
                        self._orders.append(self._target_order)

        return {
            "entry_order": self._entry_order,
            "stop_order": self._stop_order,
            "target_order": self._target_order,
            "position": position,
            "size": size,
            "risk_amount": size * abs(entry_price - stop_loss) if entry_price else None,
            "validation": validation,
        }

    async def enter_short(
        self,
        entry_price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        size: int | None = None,
        order_type: OrderType = OrderType.MARKET,
    ) -> dict[str, Any]:
        """Enter a short position with risk management.

        Args:
            entry_price: Limit order price (None for market)
            stop_loss: Stop loss price (required)
            take_profit: Take profit price (calculated if not provided)
            size: Position size (calculated if not provided)
            order_type: Order type (default: MARKET)

        Returns:
            Dictionary with order details and risk metrics
        """
        if stop_loss is None:
            raise ValueError("Stop loss is required for risk management")

        # Use market price if no entry price
        if entry_price is None and order_type != OrderType.MARKET:
            raise ValueError("Entry price required for limit orders")

        # Calculate position size if not provided
        if size is None:
            if entry_price is None:
                # Get current market price
                entry_price = await self._get_market_price()

            sizing = await self.risk.calculate_position_size(
                entry_price=entry_price,
                stop_loss=stop_loss,
                risk_percent=self.max_risk_percent,
                risk_amount=self.max_risk_amount,
            )
            size = sizing["position_size"]

        # Validate trade
        mock_order = self._create_mock_order(
            side=OrderSide.SELL,
            size=size,
            price=entry_price,
            order_type=order_type,
        )

        validation = await self.risk.validate_trade(mock_order)
        if not validation["is_valid"]:
            raise ValueError(f"Trade validation failed: {validation['reasons']}")

        # Place entry order
        if order_type == OrderType.MARKET:
            order_result = await self.orders.place_market_order(
                contract_id=self.instrument_id,
                side=OrderSide.SELL,
                size=size,
            )
        else:
            if entry_price is None:
                raise ValueError("Entry price is required for limit orders")
            order_result = await self.orders.place_limit_order(
                contract_id=self.instrument_id,
                side=OrderSide.SELL,
                size=size,
                limit_price=entry_price,
            )

        if order_result.success:
            # Get the actual order object
            orders = await self.orders.search_open_orders()
            self._entry_order = next(
                (o for o in orders if o.id == order_result.orderId), None
            )
            if self._entry_order:
                self._orders.append(self._entry_order)

        # Get position and attach risk orders
        positions = await self.positions.get_all_positions()
        position = next(
            (p for p in positions if p.contractId == self.instrument_id), None
        )

        if position:
            self._positions.append(position)

            # Attach risk orders
            risk_orders = await self.risk.attach_risk_orders(
                position=position,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

            if "bracket_order" in risk_orders:
                bracket = risk_orders["bracket_order"]
                if "stop_order" in bracket:
                    self._stop_order = bracket["stop_order"]
                    if self._stop_order:
                        self._orders.append(self._stop_order)
                if "limit_order" in bracket:
                    self._target_order = bracket["limit_order"]
                    if self._target_order:
                        self._orders.append(self._target_order)

        return {
            "entry_order": self._entry_order,
            "stop_order": self._stop_order,
            "target_order": self._target_order,
            "position": position,
            "size": size,
            "risk_amount": size * abs(entry_price - stop_loss) if entry_price else None,
            "validation": validation,
        }

    async def scale_in(
        self,
        additional_size: int,
        new_stop_loss: float | None = None,
    ) -> dict[str, Any]:
        """Scale into existing position with risk checks.

        Args:
            additional_size: Additional contracts to add
            new_stop_loss: New stop loss for entire position

        Returns:
            Dictionary with scale-in details
        """
        if not self.risk.config.scale_in_enabled:
            raise ValueError("Scale-in is disabled in risk configuration")

        if not self._positions:
            raise ValueError("No existing position to scale into")

        # Validate additional size
        position = self._positions[0]
        is_long = position.is_long

        # Place scale-in order
        order_result = await self.orders.place_market_order(
            contract_id=self.instrument_id,
            side=OrderSide.BUY if is_long else OrderSide.SELL,
            size=additional_size,
        )

        if order_result.success:
            # Get the actual order object
            orders = await self.orders.search_open_orders()
            scale_order = next(
                (o for o in orders if o.id == order_result.orderId), None
            )
            if scale_order:
                self._orders.append(scale_order)

        # Adjust stop loss if provided
        if new_stop_loss and self._stop_order:
            await self.risk.adjust_stops(
                position=position,
                new_stop=new_stop_loss,
                order_id=str(self._stop_order.id),
            )

        return {
            "scale_order": scale_order if "scale_order" in locals() else None,
            "new_position_size": position.size + additional_size,
            "stop_adjusted": new_stop_loss is not None,
        }

    async def scale_out(
        self,
        exit_size: int,
        limit_price: float | None = None,
    ) -> dict[str, Any]:
        """Scale out of position with partial exit.

        Args:
            exit_size: Number of contracts to exit
            limit_price: Limit price for exit (market if None)

        Returns:
            Dictionary with scale-out details
        """
        if not self.risk.config.scale_out_enabled:
            raise ValueError("Scale-out is disabled in risk configuration")

        if not self._positions:
            raise ValueError("No position to scale out of")

        position = self._positions[0]
        is_long = position.is_long

        if exit_size > position.size:
            raise ValueError("Exit size exceeds position size")

        # Place scale-out order
        if limit_price:
            order_result = await self.orders.place_limit_order(
                contract_id=self.instrument_id,
                side=OrderSide.SELL if is_long else OrderSide.BUY,
                size=exit_size,
                limit_price=limit_price,
            )
        else:
            order_result = await self.orders.place_market_order(
                contract_id=self.instrument_id,
                side=OrderSide.SELL if is_long else OrderSide.BUY,
                size=exit_size,
            )

        if order_result.success:
            # Get the actual order object
            orders = await self.orders.search_open_orders()
            scale_order = next(
                (o for o in orders if o.id == order_result.orderId), None
            )
            if scale_order:
                self._orders.append(scale_order)

        return {
            "exit_order": order_result,
            "remaining_size": position.size - exit_size,
            "exit_type": "limit" if limit_price else "market",
        }

    async def adjust_stop(self, new_stop_loss: float) -> bool:
        """Adjust stop loss for current position.

        Args:
            new_stop_loss: New stop loss price

        Returns:
            True if adjustment successful
        """
        if not self._positions or not self._stop_order:
            logger.warning("No position or stop order to adjust")
            return False

        return await self.risk.adjust_stops(
            position=self._positions[0],
            new_stop=new_stop_loss,
            order_id=str(self._stop_order.id),
        )

    async def close_position(self) -> dict[str, Any]:
        """Close entire position at market.

        Returns:
            Dictionary with close details
        """
        if not self._positions:
            raise ValueError("No position to close")

        position = self._positions[0]
        is_long = position.is_long

        # Cancel existing stop/target orders
        for order in [self._stop_order, self._target_order]:
            if order and order.is_working:
                try:
                    await self.orders.cancel_order(order.id)
                except Exception as e:
                    logger.error(f"Error cancelling order: {e}")

        # Place market order to close
        close_result = await self.orders.place_market_order(
            contract_id=self.instrument_id,
            side=OrderSide.SELL if is_long else OrderSide.BUY,
            size=position.size,
        )

        if close_result.success:
            # Get the actual order object
            orders = await self.orders.search_open_orders()
            close_order = next(
                (o for o in orders if o.id == close_result.orderId), None
            )
            if close_order:
                self._orders.append(close_order)

        return {
            "close_order": close_order if "close_order" in locals() else None,
            "closed_size": position.size,
            "orders_cancelled": [
                o.id
                for o in [self._stop_order, self._target_order]
                if o and o.is_working
            ],
        }

    def _create_mock_order(
        self,
        side: OrderSide,
        size: int,
        price: float | None,
        order_type: OrderType,
    ) -> "Order":
        """Create mock order for validation."""
        # This is a simplified mock - adjust based on actual Order model
        from datetime import datetime

        from project_x_py.models import Order

        # Create a proper Order instance
        return Order(
            id=0,  # Mock ID
            accountId=0,  # Mock account ID
            contractId=self.instrument_id,
            creationTimestamp=datetime.now().isoformat(),
            updateTimestamp=None,
            status=6,  # Pending
            type=order_type.value if hasattr(order_type, "value") else order_type,
            side=side.value if hasattr(side, "value") else side,
            size=size,
            limitPrice=price,
            stopPrice=None,
            fillVolume=None,
            filledPrice=None,
            customTag=None,
        )

    async def _get_market_price(self) -> float:
        """Get current market price for instrument."""
        # TODO: Implement actual market price fetching
        # This would typically come from data manager
        raise NotImplementedError("Market price fetching not yet implemented")
