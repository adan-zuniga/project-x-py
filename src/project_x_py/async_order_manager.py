"""
Async OrderManager for Comprehensive Order Operations

This module provides async/await support for comprehensive order management with the ProjectX API:
1. Order placement (market, limit, stop, trailing stop, bracket orders)
2. Order modification and cancellation
3. Order status tracking and search
4. Automatic price alignment to tick sizes
5. Real-time order monitoring integration
6. Advanced order types (OCO, bracket, conditional)

Key Features:
- Async/await patterns for all operations
- Thread-safe order operations using asyncio locks
- Dependency injection with AsyncProjectX client
- Integration with AsyncProjectXRealtimeClient for live updates
- Automatic price alignment and validation
- Comprehensive error handling and retry logic
- Support for complex order strategies
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, Optional

from .exceptions import (
    ProjectXOrderError,
)
from .models import (
    BracketOrderResponse,
    Order,
    OrderPlaceResponse,
)

if TYPE_CHECKING:
    from .async_client import AsyncProjectX
    from .async_realtime import AsyncProjectXRealtimeClient


class AsyncOrderManager:
    """
    Async comprehensive order management system for ProjectX trading operations.

    This class handles all order-related operations including placement, modification,
    cancellation, and tracking using async/await patterns. It integrates with both the
    AsyncProjectX client and the async real-time client for live order monitoring.

    Features:
        - Complete async order lifecycle management
        - Bracket order strategies with automatic stop/target placement
        - Real-time order status tracking (fills/cancellations detected from status changes)
        - Automatic price alignment to instrument tick sizes
        - OCO (One-Cancels-Other) order support
        - Position-based order management
        - Async-safe operations for concurrent trading

    Example Usage:
        >>> # Create async order manager with dependency injection
        >>> order_manager = AsyncOrderManager(async_project_x_client)
        >>> # Initialize with optional real-time client
        >>> await order_manager.initialize(realtime_client=async_realtime_client)
        >>> # Place simple orders
        >>> response = await order_manager.place_market_order("MGC", side=0, size=1)
        >>> response = await order_manager.place_limit_order("MGC", 1, 1, 2050.0)
        >>> # Place bracket orders (entry + stop + target)
        >>> bracket = await order_manager.place_bracket_order(
        ...     contract_id="MGC",
        ...     side=0,  # Buy
        ...     size=1,
        ...     entry_price=2045.0,
        ...     stop_loss_price=2040.0,
        ...     take_profit_price=2055.0,
        ... )
        >>> # Manage existing orders
        >>> orders = await order_manager.search_open_orders()
        >>> await order_manager.cancel_order(order_id)
        >>> await order_manager.modify_order(order_id, new_price=2052.0)
        >>> # Position-based operations
        >>> await order_manager.close_position("MGC", method="market")
        >>> await order_manager.add_stop_loss("MGC", stop_price=2040.0)
        >>> await order_manager.add_take_profit("MGC", target_price=2055.0)
    """

    def __init__(self, project_x_client: "AsyncProjectX"):
        """
        Initialize the AsyncOrderManager with an AsyncProjectX client.

        Args:
            project_x_client: AsyncProjectX client instance for API access
        """
        self.project_x = project_x_client
        self.logger = logging.getLogger(__name__)

        # Async lock for thread safety
        self.order_lock = asyncio.Lock()

        # Real-time integration (optional)
        self.realtime_client: AsyncProjectXRealtimeClient | None = None
        self._realtime_enabled = False

        # Internal order state tracking (for realtime optimization)
        self.tracked_orders: dict[str, dict[str, Any]] = {}  # order_id -> order_data
        self.order_status_cache: dict[str, int] = {}  # order_id -> last_known_status

        # Order callbacks (tracking is centralized in realtime client)
        self.order_callbacks: dict[str, list[Any]] = defaultdict(list)

        # Order-Position relationship tracking for synchronization
        self.position_orders: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: {"stop_orders": [], "target_orders": [], "entry_orders": []}
        )
        self.order_to_position: dict[int, str] = {}  # order_id -> contract_id

        # Statistics
        self.stats: dict[str, Any] = {
            "orders_placed": 0,
            "orders_cancelled": 0,
            "orders_modified": 0,
            "bracket_orders_placed": 0,
            "last_order_time": None,
        }

        self.logger.info("AsyncOrderManager initialized")

    async def initialize(
        self, realtime_client: Optional["AsyncProjectXRealtimeClient"] = None
    ) -> bool:
        """
        Initialize the AsyncOrderManager with optional real-time capabilities.

        Args:
            realtime_client: Optional AsyncProjectXRealtimeClient for live order tracking

        Returns:
            bool: True if initialization successful
        """
        try:
            # Set up real-time integration if provided
            if realtime_client:
                self.realtime_client = realtime_client
                await self._setup_realtime_callbacks()

                # Connect and subscribe to user updates for order tracking
                if not realtime_client.user_connected:
                    if await realtime_client.connect():
                        self.logger.info("🔌 Real-time client connected")
                    else:
                        self.logger.warning("⚠️ Real-time client connection failed")
                        return False

                # Subscribe to user updates to receive order events
                if await realtime_client.subscribe_user_updates():
                    self.logger.info("📡 Subscribed to user order updates")
                else:
                    self.logger.warning("⚠️ Failed to subscribe to user updates")

                self._realtime_enabled = True
                self.logger.info(
                    "✅ AsyncOrderManager initialized with real-time capabilities"
                )
            else:
                self.logger.info("✅ AsyncOrderManager initialized (polling mode)")

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize AsyncOrderManager: {e}")
            return False

    async def _setup_realtime_callbacks(self) -> None:
        """Set up callbacks for real-time order monitoring."""
        if not self.realtime_client:
            return

        # Register for order events (fills/cancellations detected from order updates)
        await self.realtime_client.add_callback("order_update", self._on_order_update)
        # Also register for trade execution events (complement to order fills)
        await self.realtime_client.add_callback(
            "trade_execution", self._on_trade_execution
        )

    async def _on_order_update(self, order_data: dict[str, Any]) -> None:
        """Handle real-time order update events."""
        try:
            order_id = order_data.get("id")
            if not order_id:
                return

            # Update our cache
            async with self.order_lock:
                self.tracked_orders[str(order_id)] = order_data
                self.order_status_cache[str(order_id)] = order_data.get("status", 0)

            # Call any registered callbacks
            if str(order_id) in self.order_callbacks:
                for callback in self.order_callbacks[str(order_id)]:
                    await callback(order_data)

        except Exception as e:
            self.logger.error(f"Error handling order update: {e}")

    async def _on_trade_execution(self, trade_data: dict[str, Any]) -> None:
        """Handle real-time trade execution events."""
        try:
            order_id = trade_data.get("orderId")
            if order_id and str(order_id) in self.tracked_orders:
                # Update fill information
                async with self.order_lock:
                    if "fills" not in self.tracked_orders[str(order_id)]:
                        self.tracked_orders[str(order_id)]["fills"] = []
                    self.tracked_orders[str(order_id)]["fills"].append(trade_data)

        except Exception as e:
            self.logger.error(f"Error handling trade execution: {e}")

    async def place_order(
        self,
        contract_id: str,
        side: int,
        size: int,
        order_type: int,
        price: float | None = None,
        stop_price: float | None = None,
        trailing_offset: float | None = None,
        time_in_force: int = 2,
        reduce_only: bool = False,
        auto_align_price: bool = True,
    ) -> OrderPlaceResponse | None:
        """
        Place a new order with automatic price alignment.

        Args:
            contract_id: Instrument to trade (e.g., "MGC", "MNQ")
            side: 0=Buy, 1=Sell
            size: Number of contracts
            order_type: 1=Market, 2=Limit, 3=Stop, 4=StopLimit, 5=TrailingStop
            price: Limit price (required for limit orders)
            stop_price: Stop trigger price (required for stop orders)
            trailing_offset: Offset for trailing stop orders
            time_in_force: 1=IOC, 2=GTC, 3=GTD, 4=DAY, 5=FOK
            reduce_only: If True, order can only reduce position
            auto_align_price: Automatically align price to tick size

        Returns:
            OrderPlaceResponse with order details or None on failure

        Example:
            >>> # Market order
            >>> response = await order_manager.place_order("MGC", 0, 1, 1)
            >>> # Limit order with auto price alignment
            >>> response = await order_manager.place_order("MGC", 0, 1, 2, price=2045.5)
        """
        async with self.order_lock:
            try:
                # Resolve contract ID
                resolved_contract = await self._resolve_contract_id(contract_id)
                if not resolved_contract:
                    raise ProjectXOrderError(f"Cannot resolve contract: {contract_id}")

                resolved_id = resolved_contract.get("id")
                if not resolved_id:
                    raise ProjectXOrderError(f"Invalid contract data: {contract_id}")
                contract_id = resolved_id
                tick_size = resolved_contract.get("tickSize", 0.1)

                # Price alignment
                if auto_align_price:
                    if price is not None:
                        price = self._align_price_to_tick(price, tick_size)
                    if stop_price is not None:
                        stop_price = self._align_price_to_tick(stop_price, tick_size)

                # Build order request
                if not self.project_x.account_info:
                    raise ProjectXOrderError("No account selected")

                order_data = {
                    "accountId": self.project_x.account_info.id,
                    "contractId": contract_id,
                    "side": side,
                    "size": size,
                    "orderType": order_type,
                    "timeInForce": time_in_force,
                    "reduceOnly": reduce_only,
                }

                # Add price fields based on order type
                if order_type == 2:  # Limit
                    if price is None:
                        raise ProjectXOrderError("Limit order requires price")
                    order_data["price"] = float(price)
                elif order_type == 3:  # Stop
                    if stop_price is None:
                        raise ProjectXOrderError("Stop order requires stop_price")
                    order_data["stopPrice"] = float(stop_price)
                elif order_type == 4:  # StopLimit
                    if price is None or stop_price is None:
                        raise ProjectXOrderError(
                            "StopLimit order requires both price and stop_price"
                        )
                    order_data["price"] = float(price)
                    order_data["stopPrice"] = float(stop_price)
                elif order_type == 5:  # TrailingStop
                    if trailing_offset is None:
                        raise ProjectXOrderError(
                            "TrailingStop order requires trailing_offset"
                        )
                    order_data["trailingOffset"] = float(trailing_offset)

                # Place the order
                response = await self.project_x._make_request(
                    "POST", "/orders", data=order_data
                )

                if response:
                    order_response = OrderPlaceResponse(**response)

                    # Track order internally
                    self.tracked_orders[str(order_response.orderId)] = response
                    self.order_to_position[order_response.orderId] = contract_id

                    # Update stats
                    self.stats["orders_placed"] = self.stats["orders_placed"] + 1
                    self.stats["last_order_time"] = datetime.now()

                    self.logger.info(
                        f"✅ Order placed: {order_response.orderId} - "
                        f"{'BUY' if side == 0 else 'SELL'} {size} {contract_id}"
                    )

                    return order_response

                return None

            except Exception as e:
                self.logger.error(f"❌ Failed to place order: {e}")
                raise ProjectXOrderError(f"Order placement failed: {e}") from e

    async def place_market_order(
        self, contract_id: str, side: int, size: int, reduce_only: bool = False
    ) -> OrderPlaceResponse | None:
        """
        Place a market order.

        Args:
            contract_id: Instrument to trade
            side: 0=Buy, 1=Sell
            size: Number of contracts
            reduce_only: If True, order can only reduce position

        Returns:
            OrderPlaceResponse or None

        Example:
            >>> response = await order_manager.place_market_order("MGC", 0, 1)
        """
        return await self.place_order(
            contract_id=contract_id,
            side=side,
            size=size,
            order_type=1,  # Market
            reduce_only=reduce_only,
        )

    async def place_limit_order(
        self,
        contract_id: str,
        side: int,
        size: int,
        price: float,
        time_in_force: int = 2,
        reduce_only: bool = False,
        auto_align_price: bool = True,
    ) -> OrderPlaceResponse | None:
        """
        Place a limit order with automatic price alignment.

        Args:
            contract_id: Instrument to trade
            side: 0=Buy, 1=Sell
            size: Number of contracts
            price: Limit price
            time_in_force: 1=IOC, 2=GTC, 3=GTD, 4=DAY, 5=FOK
            reduce_only: If True, order can only reduce position
            auto_align_price: Automatically align price to tick size

        Returns:
            OrderPlaceResponse or None

        Example:
            >>> response = await order_manager.place_limit_order("MGC", 0, 1, 2045.5)
        """
        return await self.place_order(
            contract_id=contract_id,
            side=side,
            size=size,
            order_type=2,  # Limit
            price=price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
            auto_align_price=auto_align_price,
        )

    async def place_stop_order(
        self,
        contract_id: str,
        side: int,
        size: int,
        stop_price: float,
        time_in_force: int = 2,
        reduce_only: bool = False,
        auto_align_price: bool = True,
    ) -> OrderPlaceResponse | None:
        """
        Place a stop order.

        Args:
            contract_id: Instrument to trade
            side: 0=Buy, 1=Sell
            size: Number of contracts
            stop_price: Stop trigger price
            time_in_force: 1=IOC, 2=GTC, 3=GTD, 4=DAY, 5=FOK
            reduce_only: If True, order can only reduce position
            auto_align_price: Automatically align price to tick size

        Returns:
            OrderPlaceResponse or None
        """
        return await self.place_order(
            contract_id=contract_id,
            side=side,
            size=size,
            order_type=3,  # Stop
            stop_price=stop_price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
            auto_align_price=auto_align_price,
        )

    async def search_open_orders(
        self, contract_id: str | None = None, side: int | None = None
    ) -> list[Order]:
        """
        Search for open orders with optional filters.

        Args:
            contract_id: Filter by instrument (optional)
            side: Filter by side 0=Buy, 1=Sell (optional)

        Returns:
            List of Order objects

        Example:
            >>> # Get all open orders
            >>> orders = await order_manager.search_open_orders()
            >>> # Get open buy orders for MGC
            >>> buy_orders = await order_manager.search_open_orders("MGC", side=0)
        """
        try:
            if not self.project_x.account_info:
                raise ProjectXOrderError("No account selected")

            params = {"accountId": self.project_x.account_info.id}

            if contract_id:
                # Resolve contract
                resolved = await self._resolve_contract_id(contract_id)
                if resolved:
                    params["contractId"] = resolved.get("id")

            if side is not None:
                params["side"] = side

            response = await self.project_x._make_request(
                "GET", "/orders/search", params=params
            )

            if response and isinstance(response, list):
                # Filter for open orders (status < 100)
                open_orders = [
                    Order(**order) for order in response if order.get("status", 0) < 100
                ]

                # Update our cache
                async with self.order_lock:
                    for order in open_orders:
                        # Convert dataclass to dict
                        self.tracked_orders[str(order.id)] = {
                            "id": order.id,
                            "accountId": order.accountId,
                            "contractId": order.contractId,
                            "status": order.status,
                            "side": order.side,
                            "size": order.size,
                            "limitPrice": order.limitPrice,
                            "stopPrice": order.stopPrice,
                        }
                        self.order_status_cache[str(order.id)] = order.status

                return open_orders

            return []

        except Exception as e:
            self.logger.error(f"Failed to search orders: {e}")
            return []

    async def cancel_order(self, order_id: int) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancellation successful

        Example:
            >>> success = await order_manager.cancel_order(12345)
        """
        async with self.order_lock:
            try:
                response = await self.project_x._make_request(
                    "POST", f"/orders/{order_id}/cancel"
                )

                if response:
                    # Update cache
                    if str(order_id) in self.tracked_orders:
                        self.tracked_orders[str(order_id)]["status"] = 200  # Cancelled
                        self.order_status_cache[str(order_id)] = 200

                    self.stats["orders_cancelled"] = self.stats["orders_cancelled"] + 1
                    self.logger.info(f"✅ Order cancelled: {order_id}")
                    return True

                return False

            except Exception as e:
                self.logger.error(f"Failed to cancel order {order_id}: {e}")
                return False

    async def modify_order(
        self,
        order_id: int,
        new_price: float | None = None,
        new_stop_price: float | None = None,
        new_size: int | None = None,
        auto_align_price: bool = True,
    ) -> bool:
        """
        Modify an existing order.

        Args:
            order_id: Order ID to modify
            new_price: New limit price (optional)
            new_stop_price: New stop price (optional)
            new_size: New order size (optional)
            auto_align_price: Automatically align price to tick size

        Returns:
            True if modification successful

        Example:
            >>> success = await order_manager.modify_order(12345, new_price=2046.0)
        """
        async with self.order_lock:
            try:
                # Get current order details
                order_data = self.tracked_orders.get(str(order_id))
                if not order_data:
                    # Fetch from API if not cached
                    response = await self.project_x._make_request(
                        "GET", f"/orders/{order_id}"
                    )
                    if not response:
                        raise ProjectXOrderError(f"Order {order_id} not found")
                    order_data = response

                # Get tick size for price alignment
                contract_id = order_data.get("contractId")
                tick_size = 0.1  # Default

                if auto_align_price and contract_id:
                    resolved = await self._resolve_contract_id(contract_id)
                    if resolved:
                        tick_size = resolved.get("tickSize", 0.1)

                    if new_price is not None:
                        new_price = self._align_price_to_tick(new_price, tick_size)
                    if new_stop_price is not None:
                        new_stop_price = self._align_price_to_tick(
                            new_stop_price, tick_size
                        )

                # Build modification request
                modify_data = {}
                if new_price is not None:
                    modify_data["price"] = float(new_price)
                if new_stop_price is not None:
                    modify_data["stopPrice"] = float(new_stop_price)
                if new_size is not None:
                    modify_data["size"] = new_size

                if not modify_data:
                    return True  # Nothing to modify

                # Send modification request
                response = await self.project_x._make_request(
                    "PUT", f"/orders/{order_id}", data=modify_data
                )

                if response:
                    # Update cache
                    self.tracked_orders[str(order_id)].update(modify_data)
                    self.stats["orders_modified"] = self.stats["orders_modified"] + 1
                    self.logger.info(f"✅ Order modified: {order_id}")
                    return True

                return False

            except Exception as e:
                self.logger.error(f"Failed to modify order {order_id}: {e}")
                return False

    async def place_bracket_order(
        self,
        contract_id: str,
        side: int,
        size: int,
        entry_type: int = 1,
        entry_price: float | None = None,
        stop_loss_price: float | None = None,
        take_profit_price: float | None = None,
        stop_loss_offset: float | None = None,
        take_profit_offset: float | None = None,
        auto_align_price: bool = True,
    ) -> BracketOrderResponse | None:
        """
        Place a bracket order (entry + stop loss + take profit).

        Args:
            contract_id: Instrument to trade
            side: 0=Buy, 1=Sell
            size: Number of contracts
            entry_type: 1=Market, 2=Limit
            entry_price: Entry limit price (required if entry_type=2)
            stop_loss_price: Stop loss price (optional, can use offset)
            take_profit_price: Take profit price (optional, can use offset)
            stop_loss_offset: Points from entry for stop loss
            take_profit_offset: Points from entry for take profit
            auto_align_price: Automatically align prices to tick size

        Returns:
            BracketOrderResponse with all three order IDs

        Example:
            >>> # Market entry with fixed stop/target
            >>> bracket = await order_manager.place_bracket_order(
            ...     "MGC", 0, 1, stop_loss_price=2040.0, take_profit_price=2055.0
            ... )
            >>> # Limit entry with offset stop/target
            >>> bracket = await order_manager.place_bracket_order(
            ...     "MGC",
            ...     0,
            ...     1,
            ...     entry_type=2,
            ...     entry_price=2045.0,
            ...     stop_loss_offset=5.0,
            ...     take_profit_offset=10.0,
            ... )
        """
        # No lock here - individual order methods handle their own locking
        try:
            # Resolve contract
            resolved = await self._resolve_contract_id(contract_id)
            if not resolved:
                raise ProjectXOrderError(f"Cannot resolve contract: {contract_id}")

            resolved_id = resolved.get("id")
            if not resolved_id:
                raise ProjectXOrderError(f"Invalid contract data: {contract_id}")
            contract_id = resolved_id

            # Place entry order
            if entry_type == 1:  # Market
                entry_response = await self.place_market_order(contract_id, side, size)
            else:  # Limit
                if entry_price is None:
                    raise ProjectXOrderError("Limit entry requires entry_price")
                entry_response = await self.place_limit_order(
                    contract_id,
                    side,
                    size,
                    entry_price,
                    auto_align_price=auto_align_price,
                )

            if not entry_response:
                raise ProjectXOrderError("Failed to place entry order")

            # Calculate stop and target prices if using offsets
            # For market orders, we might need to wait for fill or use current market price
            current_price = entry_price or 0 if entry_type == 1 else entry_price

            if stop_loss_offset and current_price:
                if side == 0:  # Buy
                    stop_loss_price = current_price - stop_loss_offset
                else:  # Sell
                    stop_loss_price = current_price + stop_loss_offset

            if take_profit_offset and current_price:
                if side == 0:  # Buy
                    take_profit_price = current_price + take_profit_offset
                else:  # Sell
                    take_profit_price = current_price - take_profit_offset

            # Place stop loss order
            stop_response = None
            if stop_loss_price:
                stop_side = 1 if side == 0 else 0  # Opposite side
                stop_response = await self.place_stop_order(
                    contract_id,
                    stop_side,
                    size,
                    stop_loss_price,
                    reduce_only=True,
                    auto_align_price=auto_align_price,
                )

            # Place take profit order
            target_response = None
            if take_profit_price:
                target_side = 1 if side == 0 else 0  # Opposite side
                target_response = await self.place_limit_order(
                    contract_id,
                    target_side,
                    size,
                    take_profit_price,
                    reduce_only=True,
                    auto_align_price=auto_align_price,
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
            self.logger.info(
                f"✅ Bracket order placed: Entry={entry_response.orderId}, "
                f"Stop={stop_response.orderId if stop_response else 'None'}, "
                f"Target={target_response.orderId if target_response else 'None'}"
            )

            return bracket_response

        except Exception as e:
            self.logger.error(f"Failed to place bracket order: {e}")
            return None

    async def _resolve_contract_id(self, contract_id: str) -> dict[str, Any] | None:
        """Resolve a contract ID to its full contract details."""
        try:
            # Try to get from instrument cache first
            instrument = await self.project_x.get_instrument(contract_id)
            if instrument:
                # Return dict representation of instrument
                return {
                    "id": instrument.id,
                    "name": instrument.name,
                    "tickSize": instrument.tickSize,
                    "tickValue": instrument.tickValue,
                    "activeContract": instrument.activeContract,
                }
            return None
        except Exception:
            return None

    def _align_price_to_tick(self, price: float, tick_size: float) -> float:
        """Align price to the nearest valid tick."""
        if tick_size <= 0:
            return price

        decimal_price = Decimal(str(price))
        decimal_tick = Decimal(str(tick_size))

        # Round to nearest tick
        aligned = (decimal_price / decimal_tick).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        ) * decimal_tick

        return float(aligned)

    def get_stats(self) -> dict[str, Any]:
        """Get order manager statistics."""
        return self.stats.copy()
