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
- Position-aware order management
- Real-time order status tracking and caching
- Bracket order management with stop-loss and take-profit

Usage Example:
```python
import asyncio
from project_x_py import AsyncProjectX, AsyncOrderManager, AsyncProjectXRealtimeClient


async def main():
    # Create client instances
    client = AsyncProjectX()
    await client.authenticate()

    # Create and initialize order manager
    order_manager = AsyncOrderManager(client)
    realtime_client = ProjectXRealtimeClient(client.config)
    await order_manager.initialize(realtime_client=realtime_client)

    # Place a simple market order
    response = await order_manager.place_market_order(
        "MGC", side=0, size=1
    )  # Buy 1 contract
    print(f"Order placed with ID: {response.orderId}")

    # Place a bracket order (entry + stop-loss + take-profit)
    bracket = await order_manager.place_bracket_order(
        contract_id="MGC",
        side=0,  # Buy
        size=1,
        entry_price=2045.0,
        stop_loss_price=2040.0,
        take_profit_price=2055.0,
    )
    print(
        f"Bracket order placed: Entry={bracket.entry_order_id}, Stop={bracket.stop_order_id}, Target={bracket.target_order_id}"
    )


asyncio.run(main())
```
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, Optional, TypedDict

from .exceptions import (
    ProjectXOrderError,
)
from .models import (
    BracketOrderResponse,
    Order,
    OrderPlaceResponse,
)

if TYPE_CHECKING:
    from .client import ProjectX
    from .realtime import ProjectXRealtimeClient


class OrderStats(TypedDict):
    """Type definition for order statistics."""

    orders_placed: int
    orders_cancelled: int
    orders_modified: int
    bracket_orders_placed: int
    last_order_time: datetime | None


class OrderManager:
    """
    Async comprehensive order management system for ProjectX trading operations.

    This class handles all order-related operations including placement, modification,
    cancellation, and tracking using async/await patterns. It integrates with both the
    AsyncProjectX client and the AsyncProjectXRealtimeClient for live order monitoring.

    Features:
        - Complete async order lifecycle management
        - Bracket order strategies with automatic stop/target placement
        - Real-time order status tracking (fills/cancellations detected from status changes)
        - Automatic price alignment to instrument tick sizes
        - OCO (One-Cancels-Other) order support
        - Position-based order management
        - Async-safe operations for concurrent trading
        - Order callback registration for custom event handling
        - Performance optimization with local order caching

    Order Status Enum Values:
        - 0: None (undefined)
        - 1: Open (active order)
        - 2: Filled (completely executed)
        - 3: Cancelled (cancelled by user or system)
        - 4: Expired (timed out)
        - 5: Rejected (rejected by exchange)
        - 6: Pending (awaiting submission)

    Order Side Enum Values:
        - 0: Buy (bid)
        - 1: Sell (ask)

    Order Type Enum Values:
        - 1: Limit
        - 2: Market
        - 4: Stop
        - 5: TrailingStop
        - 6: JoinBid
        - 7: JoinAsk

    Example Usage:
        ```python
        # Create async order manager with dependency injection
        order_manager = OrderManager(async_project_x_client)

        # Initialize with optional real-time client
        await order_manager.initialize(realtime_client=async_realtime_client)

        # Place simple orders
        response = await order_manager.place_market_order(
            "MGC", side=0, size=1
        )  # Buy 1 contract
        response = await order_manager.place_limit_order(
            "MGC", 1, 1, 2050.0
        )  # Sell 1 contract at 2050.0

        # Place bracket orders (entry + stop + target)
        bracket = await order_manager.place_bracket_order(
            contract_id="MGC",
            side=0,  # Buy
            size=1,
            entry_price=2045.0,
            stop_loss_price=2040.0,
            take_profit_price=2055.0,
        )

        # Manage existing orders
        orders = await order_manager.search_open_orders()  # Get all open orders
        orders = await order_manager.search_open_orders("MGC")  # Get MGC open orders

        # Cancel and modify orders
        await order_manager.cancel_order(order_id)
        await order_manager.modify_order(order_id, limit_price=2052.0)

        # Position-based operations
        await order_manager.close_position("MGC", method="market")
        await order_manager.add_stop_loss("MGC", stop_price=2040.0)
        await order_manager.add_take_profit("MGC", limit_price=2055.0)

        # Check order status efficiently (uses cache when available)
        if await order_manager.is_order_filled(order_id):
            print("Order has been filled!")


        # Register callbacks for order events
        async def on_order_filled(order_data):
            print(
                f"Order {order_data.get('id')} filled at {order_data.get('filledPrice')}"
            )


        order_manager.add_callback("order_filled", on_order_filled)
        ```
    """

    def __init__(self, project_x_client: "ProjectX"):
        """
        Initialize the OrderManager with an ProjectX client.

        Creates a new instance of the OrderManager that uses the provided ProjectX client
        for API access. This establishes the foundation for order operations but does not
        set up real-time capabilities. To enable real-time order tracking, call the `initialize`
        method with a real-time client after initialization.

        Args:
            project_x_client: ProjectX client instance for API access. This client
                should already be authenticated or authentication should be handled
                separately before attempting order operations.

        Example:
            ```python
            # Create the AsyncProjectX client first
            client = ProjectX()
            await client.authenticate()

            # Then create the order manager
            order_manager = OrderManager(client)
            ```
        """
        self.project_x = project_x_client
        self.logger = logging.getLogger(__name__)

        # Async lock for thread safety
        self.order_lock = asyncio.Lock()

        # Real-time integration (optional)
        self.realtime_client: ProjectXRealtimeClient | None = None
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
        self.stats: OrderStats = {
            "orders_placed": 0,
            "orders_cancelled": 0,
            "orders_modified": 0,
            "bracket_orders_placed": 0,
            "last_order_time": None,
        }

        self.logger.info("AsyncOrderManager initialized")

    async def initialize(
        self, realtime_client: Optional["ProjectXRealtimeClient"] = None
    ) -> bool:
        """
        Initialize the AsyncOrderManager with optional real-time capabilities.

        This method configures the AsyncOrderManager for operation, optionally enabling
        real-time order status tracking if a realtime client is provided. Real-time
        tracking significantly improves performance by minimizing API calls and
        providing immediate order status updates through websocket connections.

        When real-time tracking is enabled:
        1. Order status changes are detected immediately
        2. Fills, cancellations and rejections are processed in real-time
        3. The order_manager caches order data to reduce API calls
        4. Callbacks can be triggered for custom event handling

        Args:
            realtime_client: Optional AsyncProjectXRealtimeClient for live order tracking.
                If provided, the order manager will connect to the real-time API
                and subscribe to user updates for order status tracking.

        Returns:
            bool: True if initialization successful, False otherwise.

        Example:
            ```python
            # Create and set up the required components
            px_client = ProjectX()
            await px_client.authenticate()

            # Create the realtime client
            realtime = ProjectXRealtimeClient(px_client.config)

            # Initialize order manager with realtime capabilities
            order_manager = AsyncOrderManager(px_client)
            success = await order_manager.initialize(realtime_client=realtime)

            if success:
                print("Order manager initialized with realtime tracking")
            else:
                print("Using order manager in polling mode")
            ```
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

    async def _on_order_update(self, order_data: dict[str, Any] | list) -> None:
        """Handle real-time order update events."""
        try:
            self.logger.info(f"📨 Order update received: {type(order_data)}")

            # Handle different data formats from SignalR
            if isinstance(order_data, list):
                # SignalR sometimes sends data as a list
                if len(order_data) > 0:
                    # Try to extract the actual order data
                    if len(order_data) == 1:
                        order_data = order_data[0]
                    elif len(order_data) >= 2 and isinstance(order_data[1], dict):
                        # Format: [id, data_dict]
                        order_data = order_data[1]
                    else:
                        self.logger.warning(
                            f"Unexpected order data format: {order_data}"
                        )
                        return
                else:
                    return

            if not isinstance(order_data, dict):
                self.logger.warning(f"Order data is not a dict: {type(order_data)}")
                return

            # Extract order data - handle nested structure from SignalR
            actual_order_data = order_data
            if "action" in order_data and "data" in order_data:
                # SignalR format: {'action': 1, 'data': {...}}
                actual_order_data = order_data["data"]

            order_id = actual_order_data.get("id")
            if not order_id:
                self.logger.warning(f"No order ID found in data: {order_data}")
                return

            self.logger.info(
                f"📨 Tracking order {order_id} (status: {actual_order_data.get('status')})"
            )

            # Update our cache with the actual order data
            async with self.order_lock:
                self.tracked_orders[str(order_id)] = actual_order_data
                self.order_status_cache[str(order_id)] = actual_order_data.get(
                    "status", 0
                )
                self.logger.info(
                    f"✅ Order {order_id} added to cache. Total tracked: {len(self.tracked_orders)}"
                )

            # Call any registered callbacks
            if str(order_id) in self.order_callbacks:
                for callback in self.order_callbacks[str(order_id)]:
                    await callback(order_data)

        except Exception as e:
            self.logger.error(f"Error handling order update: {e}")
            self.logger.debug(f"Order data received: {order_data}")

    async def _on_trade_execution(self, trade_data: dict[str, Any] | list) -> None:
        """Handle real-time trade execution events."""
        try:
            # Handle different data formats from SignalR
            if isinstance(trade_data, list):
                # SignalR sometimes sends data as a list
                if len(trade_data) > 0:
                    # Try to extract the actual trade data
                    if len(trade_data) == 1:
                        trade_data = trade_data[0]
                    elif len(trade_data) >= 2 and isinstance(trade_data[1], dict):
                        # Format: [id, data_dict]
                        trade_data = trade_data[1]
                    else:
                        self.logger.warning(
                            f"Unexpected trade data format: {trade_data}"
                        )
                        return
                else:
                    return

            if not isinstance(trade_data, dict):
                self.logger.warning(f"Trade data is not a dict: {type(trade_data)}")
                return

            order_id = trade_data.get("orderId")
            if order_id and str(order_id) in self.tracked_orders:
                # Update fill information
                async with self.order_lock:
                    if "fills" not in self.tracked_orders[str(order_id)]:
                        self.tracked_orders[str(order_id)]["fills"] = []
                    self.tracked_orders[str(order_id)]["fills"].append(trade_data)

        except Exception as e:
            self.logger.error(f"Error handling trade execution: {e}")
            self.logger.debug(f"Trade data received: {trade_data}")

    async def place_order(
        self,
        contract_id: str,
        order_type: int,
        side: int,
        size: int,
        limit_price: float | None = None,
        stop_price: float | None = None,
        trail_price: float | None = None,
        custom_tag: str | None = None,
        linked_order_id: int | None = None,
        account_id: int | None = None,
    ) -> OrderPlaceResponse:
        """
        Place an order with comprehensive parameter support and automatic price alignment.

        This is the core order placement method that all specific order type methods use internally.
        It provides complete control over all order parameters and handles automatic price alignment
        to prevent "Invalid price" errors from the exchange. The method is thread-safe and can be
        called concurrently from multiple tasks.

        Args:
            contract_id: The contract ID to trade (e.g., "MGC", "MES", "F.US.EP")
            order_type: Order type integer value:
                1=Limit (executes at specified price or better)
                2=Market (executes immediately at best available price)
                4=Stop (market order triggered at stop price)
                5=TrailingStop (stop that follows price movements)
                6=JoinBid (joins the bid price automatically)
                7=JoinAsk (joins the ask price automatically)
            side: Order side integer value:
                0=Buy (bid)
                1=Sell (ask)
            size: Number of contracts to trade (positive integer)
            limit_price: Limit price for limit orders, automatically aligned to tick size.
                Required for order types 1 (Limit) and 6/7 (JoinBid/JoinAsk).
            stop_price: Stop price for stop orders, automatically aligned to tick size.
                Required for order type 4 (Stop).
            trail_price: Trail amount for trailing stop orders, automatically aligned to tick size.
                Required for order type 5 (TrailingStop).
            custom_tag: Custom identifier for the order (for your reference)
            linked_order_id: ID of a linked order for OCO (One-Cancels-Other) relationships
            account_id: Account ID. Uses default account from authenticated client if None.

        Returns:
            OrderPlaceResponse: Response containing order ID and status information including:
                - orderId: The unique ID of the placed order (int)
                - success: Whether the order was successfully placed (bool)
                - errorMessage: Error message if placement failed (str, None if successful)

        Raises:
            ProjectXOrderError: If order placement fails due to invalid parameters or API errors

        Example:
            ```python
            # Place a limit order to buy 1 contract
            response = await order_manager.place_order(
                contract_id="MGC",
                order_type=1,  # Limit
                side=0,  # Buy
                size=1,
                limit_price=2040.50,
                account_id=12345,  # Optional, uses default if None
            )

            if response.success:
                print(f"Order placed with ID: {response.orderId}")
            else:
                print(f"Order failed: {response.errorMessage}")

            # Place a stop order to sell 2 contracts
            stop_response = await order_manager.place_order(
                contract_id="MGC",
                order_type=4,  # Stop
                side=1,  # Sell
                size=2,
                stop_price=2030.00,
                custom_tag="stop_loss",
            )
            ```

        Note:
            - Prices are automatically aligned to the instrument's tick size
            - For market orders, limit_price, stop_price, and trail_price are ignored
            - For limit orders, only limit_price is used
            - For stop orders, only stop_price is used
            - For trailing stop orders, only trail_price is used
        """
        result = None
        aligned_limit_price = None
        aligned_stop_price = None
        aligned_trail_price = None

        async with self.order_lock:
            try:
                # Align all prices to tick size to prevent "Invalid price" errors
                aligned_limit_price = await self._align_price_to_tick_size(
                    limit_price, contract_id
                )
                aligned_stop_price = await self._align_price_to_tick_size(
                    stop_price, contract_id
                )
                aligned_trail_price = await self._align_price_to_tick_size(
                    trail_price, contract_id
                )

                # Use account_info if no account_id provided
                if account_id is None:
                    if not self.project_x.account_info:
                        raise ProjectXOrderError("No account information available")
                    account_id = self.project_x.account_info.id

                # Build order request payload
                payload = {
                    "accountId": account_id,
                    "contractId": contract_id,
                    "type": order_type,
                    "side": side,
                    "size": size,
                    "limitPrice": aligned_limit_price,
                    "stopPrice": aligned_stop_price,
                    "trailPrice": aligned_trail_price,
                    "linkedOrderId": linked_order_id,
                }

                # Only include customTag if it's provided and not None/empty
                if custom_tag:
                    payload["customTag"] = custom_tag

                # Log order parameters for debugging
                self.logger.debug(f"🔍 Order Placement Request: {payload}")

                # Place the order
                response = await self.project_x._make_request(
                    "POST", "/Order/place", data=payload
                )

                # Log the actual API response for debugging
                self.logger.debug(f"🔍 Order API Response: {response}")

                if not response.get("success", False):
                    error_msg = (
                        response.get("errorMessage")
                        or "Unknown error - no error message provided"
                    )
                    self.logger.error(f"Order placement failed: {error_msg}")
                    self.logger.error(f"🔍 Full response data: {response}")
                    raise ProjectXOrderError(f"Order placement failed: {error_msg}")

                result = OrderPlaceResponse(**response)

                # Update statistics
                self.stats["orders_placed"] += 1
                self.stats["last_order_time"] = datetime.now()

                self.logger.info(f"✅ Order placed: {result.orderId}")

            except Exception as e:
                self.logger.error(f"❌ Failed to place order: {e}")
                raise ProjectXOrderError(f"Order placement failed: {e}") from e

        return result

    async def place_market_order(
        self, contract_id: str, side: int, size: int, account_id: int | None = None
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
        self,
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
        self,
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
                if resolved and resolved.get("id"):
                    params["contractId"] = resolved["id"]

            if side is not None:
                params["side"] = side

            response = await self.project_x._make_request(
                "POST", "/Order/searchOpen", data=params
            )

            if not response.get("success", False):
                error_msg = response.get("errorMessage", "Unknown error")
                self.logger.error(f"Order search failed: {error_msg}")
                return []

            orders = response.get("orders", [])
            # Filter to only include fields that Order model expects
            open_orders = []
            for order_data in orders:
                try:
                    order = Order(**order_data)
                    open_orders.append(order)

                    # Update our cache
                    async with self.order_lock:
                        self.tracked_orders[str(order.id)] = order_data
                        self.order_status_cache[str(order.id)] = order.status
                except Exception as e:
                    self.logger.warning(f"Failed to parse order: {e}")
                    continue

            return open_orders

        except Exception as e:
            self.logger.error(f"Failed to search orders: {e}")
            return []

    async def get_tracked_order_status(
        self, order_id: str, wait_for_cache: bool = False
    ) -> dict[str, Any] | None:
        """
        Get cached order status from real-time tracking for faster access.

        When real-time mode is enabled, this method provides instant access to
        order status without requiring API calls, significantly improving performance
        and reducing API rate limit consumption. The method can optionally wait
        briefly for the cache to populate if a very recent order is being checked.

        Args:
            order_id: Order ID to get status for (as string)
            wait_for_cache: If True, briefly wait for real-time cache to populate
                (useful when checking status immediately after placing an order)

        Returns:
            dict: Complete order data dictionary if tracked in cache, None if not found.
                Contains all ProjectX GatewayUserOrder fields including:
                - id: Order ID (int)
                - accountId: Account ID (int)
                - contractId: Contract ID (str)
                - status: Order status (int - see enum values in class docstring)
                - type: Order type (int)
                - side: Order side (0=Buy, 1=Sell)
                - size: Order size (int)
                - limitPrice: Limit price if applicable (float)
                - stopPrice: Stop price if applicable (float)
                - fillVolume: Total filled quantity (int)
                - filledPrice: Average fill price (float)
                - fills: List of individual fill objects if available
                - lastModified: Timestamp of last order update

        Example:
            ```python
            # Check order status with cache lookup
            order_data = await order_manager.get_tracked_order_status("12345")

            if order_data:
                # Get order status (1=Open, 2=Filled, 3=Cancelled, etc.)
                status = order_data["status"]

                if status == 2:  # Filled
                    # Access fill information
                    filled_qty = order_data.get("fillVolume", 0)
                    avg_price = order_data.get("filledPrice", 0)
                    print(f"Order filled: {filled_qty} @ {avg_price}")

                    # Access detailed fills if available
                    if "fills" in order_data:
                        for fill in order_data["fills"]:
                            print(
                                f"Partial fill: {fill.get('volume')} @ {fill.get('price')}"
                            )

                elif status == 3:  # Cancelled
                    print("Order was cancelled")

                else:
                    print(f"Order status: {status}, Size: {order_data.get('size')}")
            else:
                print("Order not found in cache")

            # Wait for cache to populate for a new order
            new_order_data = await order_manager.get_tracked_order_status(
                "54321", wait_for_cache=True
            )
            ```

        Note:
            If real-time tracking is disabled, this method will always return None,
            and you should use get_order_by_id() instead. The is_order_filled() method
            automatically falls back to API calls when cache data is unavailable.
        """
        if wait_for_cache and self._realtime_enabled:
            # Brief wait for real-time cache to populate
            for attempt in range(3):
                async with self.order_lock:
                    order_data = self.tracked_orders.get(order_id)
                    if order_data:
                        return order_data

                if attempt < 2:  # Don't sleep on last attempt
                    await asyncio.sleep(0.3)  # Brief wait for real-time update

        async with self.order_lock:
            return self.tracked_orders.get(order_id)

    async def is_order_filled(self, order_id: str | int) -> bool:
        """
        Check if an order has been filled using cached data with API fallback.

        Efficiently checks order fill status by first consulting the real-time
        cache (if available) before falling back to API queries for maximum
        performance.

        Args:
            order_id: Order ID to check (accepts both string and integer)

        Returns:
            bool: True if order status is 2 (Filled), False otherwise

        Example:
            >>> if await order_manager.is_order_filled(12345):
            ...     print("Order has been filled")
            ...     # Proceed with next trading logic
            >>> else:
            ...     print("Order still pending")
        """
        order_id_str = str(order_id)

        # Try cached data first with brief retry for real-time updates
        if self._realtime_enabled:
            for attempt in range(3):  # Try 3 times with small delays
                async with self.order_lock:
                    status = self.order_status_cache.get(order_id_str)
                    if status is not None:
                        return status == 2  # 2 = Filled

                if attempt < 2:  # Don't sleep on last attempt
                    await asyncio.sleep(0.2)  # Brief wait for real-time update

        # Fallback to API check
        order = await self.get_order_by_id(int(order_id))
        return order is not None and order.status == 2  # 2 = Filled

    async def get_order_by_id(self, order_id: int) -> Order | None:
        """
        Get detailed order information by ID using cached data with API fallback.

        Args:
            order_id: Order ID to retrieve

        Returns:
            Order object with full details or None if not found
        """
        order_id_str = str(order_id)

        # Try cached data first (realtime optimization)
        if self._realtime_enabled:
            order_data = await self.get_tracked_order_status(order_id_str)
            if order_data:
                try:
                    return Order(**order_data)
                except Exception as e:
                    self.logger.debug(f"Failed to parse cached order data: {e}")

        # Fallback to API search
        try:
            orders = await self.search_open_orders()
            for order in orders:
                if order.id == order_id:
                    return order
            return None
        except Exception as e:
            self.logger.error(f"Failed to get order {order_id}: {e}")
            return None

    async def cancel_order(self, order_id: int, account_id: int | None = None) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Order ID to cancel
            account_id: Account ID. Uses default account if None.

        Returns:
            True if cancellation successful

        Example:
            >>> success = await order_manager.cancel_order(12345)
        """
        async with self.order_lock:
            try:
                # Get account ID if not provided
                if account_id is None:
                    if not self.project_x.account_info:
                        await self.project_x.authenticate()
                    if not self.project_x.account_info:
                        raise ProjectXOrderError("No account information available")
                    account_id = self.project_x.account_info.id

                # Use correct endpoint and payload structure
                payload = {
                    "accountId": account_id,
                    "orderId": order_id,
                }

                response = await self.project_x._make_request(
                    "POST", "/Order/cancel", data=payload
                )

                success = response.get("success", False) if response else False

                if success:
                    # Update cache
                    if str(order_id) in self.tracked_orders:
                        self.tracked_orders[str(order_id)]["status"] = (
                            3  # Cancelled = 3
                        )
                        self.order_status_cache[str(order_id)] = 3

                    self.stats["orders_cancelled"] = (
                        self.stats.get("orders_cancelled", 0) + 1
                    )
                    self.logger.info(f"✅ Order cancelled: {order_id}")
                    return True
                else:
                    error_msg = (
                        response.get("errorMessage", "Unknown error")
                        if response
                        else "No response"
                    )
                    self.logger.error(
                        f"❌ Failed to cancel order {order_id}: {error_msg}"
                    )
                    return False

            except Exception as e:
                self.logger.error(f"Failed to cancel order {order_id}: {e}")
                return False

    async def modify_order(
        self,
        order_id: int,
        limit_price: float | None = None,
        stop_price: float | None = None,
        size: int | None = None,
    ) -> bool:
        """
        Modify an existing order.

        Args:
            order_id: Order ID to modify
            limit_price: New limit price (optional)
            stop_price: New stop price (optional)
            size: New order size (optional)

        Returns:
            True if modification successful

        Example:
            >>> success = await order_manager.modify_order(12345, limit_price=2046.0)
        """
        try:
            # Get existing order details to determine contract_id for price alignment
            existing_order = await self.get_order_by_id(order_id)
            if not existing_order:
                self.logger.error(f"❌ Cannot modify order {order_id}: Order not found")
                return False

            contract_id = existing_order.contractId

            # Align prices to tick size
            aligned_limit = await self._align_price_to_tick_size(
                limit_price, contract_id
            )
            aligned_stop = await self._align_price_to_tick_size(stop_price, contract_id)

            # Build modification request
            payload: dict[str, Any] = {
                "accountId": self.project_x.account_info.id
                if self.project_x.account_info
                else None,
                "orderId": order_id,
            }

            # Add only the fields that are being modified
            if aligned_limit is not None:
                payload["limitPrice"] = aligned_limit
            if aligned_stop is not None:
                payload["stopPrice"] = aligned_stop
            if size is not None:
                payload["size"] = size

            if len(payload) <= 2:  # Only accountId and orderId
                return True  # Nothing to modify

            # Modify order
            response = await self.project_x._make_request(
                "POST", "/Order/modify", data=payload
            )

            if response and response.get("success", False):
                # Update statistics
                async with self.order_lock:
                    self.stats["orders_modified"] = (
                        self.stats.get("orders_modified", 0) + 1
                    )

                self.logger.info(f"✅ Order modified: {order_id}")
                return True
            else:
                error_msg = (
                    response.get("errorMessage", "Unknown error")
                    if response
                    else "No response"
                )
                self.logger.error(f"❌ Order modification failed: {error_msg}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to modify order {order_id}: {e}")
            return False

    async def place_bracket_order(
        self,
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
            custom_tag: Custom identifier for the bracket orders

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
            ```python
            # Place a buy bracket order with limit entry
            bracket = await order_manager.place_bracket_order(
                contract_id="MGC",  # Gold mini
                side=0,  # Buy
                size=1,  # 1 contract
                entry_price=2045.0,  # Entry at 2045
                stop_loss_price=2040.0,  # Stop loss at 2040 (-$50/contract risk)
                take_profit_price=2055.0,  # Take profit at 2055 (+$100/contract target)
                custom_tag="gold_breakout",  # Optional tracking tag
            )

            if bracket.success:
                print(f"Bracket order placed successfully")
                print(f"Entry ID: {bracket.entry_order_id}")
                print(f"Stop ID: {bracket.stop_order_id}")
                print(f"Target ID: {bracket.target_order_id}")

                # You can track the bracket orders as a group
                entry_status = await order_manager.is_order_filled(
                    bracket.entry_order_id
                )
                if entry_status:
                    print("Entry order has been filled")

            # Place a sell bracket order with market entry
            sell_bracket = await order_manager.place_bracket_order(
                contract_id="MES",  # E-mini S&P
                side=1,  # Sell
                size=2,  # 2 contracts
                entry_price=0,  # Ignored for market orders
                stop_loss_price=4205.0,  # Stop loss above entry
                take_profit_price=4180.0,  # Take profit below entry
                entry_type="market",  # Market order entry
            )
            ```

        Note:
            - For market entries, the entry_price is ignored
            - Stop loss orders must be below entry for buys and above for sells
            - Take profit orders must be above entry for buys and below for sells
            - All orders use automatic price alignment to respect instrument tick sizes
            - The orders are linked in tracking but not at the exchange level
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
            self.logger.info(
                f"✅ Bracket order placed: Entry={entry_response.orderId}, "
                f"Stop={stop_response.orderId if stop_response else 'None'}, "
                f"Target={target_response.orderId if target_response else 'None'}"
            )

            return bracket_response

        except Exception as e:
            self.logger.error(f"Failed to place bracket order: {e}")
            raise ProjectXOrderError(f"Failed to place bracket order: {e}") from e

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

    async def _align_price_to_tick_size(
        self, price: float | None, contract_id: str
    ) -> float | None:
        """
        Align a price to the instrument's tick size.

        Args:
            price: The price to align
            contract_id: Contract ID to get tick size from

        Returns:
            float: Price aligned to tick size
            None: If price is None
        """
        try:
            if price is None:
                return None

            instrument_obj = None

            # Try to get instrument by simple symbol first (e.g., "MNQ")
            if "." not in contract_id:
                instrument_obj = await self.project_x.get_instrument(contract_id)
            else:
                # Extract symbol from contract ID (e.g., "CON.F.US.MGC.M25" -> "MGC")
                from .utils import extract_symbol_from_contract_id

                symbol = extract_symbol_from_contract_id(contract_id)
                if symbol:
                    instrument_obj = await self.project_x.get_instrument(symbol)

            if not instrument_obj or not hasattr(instrument_obj, "tickSize"):
                self.logger.warning(
                    f"No tick size available for contract {contract_id}, using original price: {price}"
                )
                return price

            tick_size = instrument_obj.tickSize
            if tick_size is None or tick_size <= 0:
                self.logger.warning(
                    f"Invalid tick size {tick_size} for {contract_id}, using original price: {price}"
                )
                return price

            self.logger.debug(
                f"Aligning price {price} with tick size {tick_size} for {contract_id}"
            )

            # Convert to Decimal for precise calculation
            price_decimal = Decimal(str(price))
            tick_decimal = Decimal(str(tick_size))

            # Round to nearest tick using precise decimal arithmetic
            ticks = (price_decimal / tick_decimal).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
            aligned_decimal = ticks * tick_decimal

            # Determine the number of decimal places needed for the tick size
            tick_str = str(tick_size)
            decimal_places = len(tick_str.split(".")[1]) if "." in tick_str else 0

            # Create the quantization pattern
            if decimal_places == 0:
                quantize_pattern = Decimal("1")
            else:
                quantize_pattern = Decimal("0." + "0" * (decimal_places - 1) + "1")

            result = float(aligned_decimal.quantize(quantize_pattern))

            if result != price:
                self.logger.info(
                    f"Price alignment: {price} -> {result} (tick size: {tick_size})"
                )

            return result

        except Exception as e:
            self.logger.error(f"Error aligning price {price} to tick size: {e}")
            return price  # Return original price if alignment fails

    async def get_order_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive order management statistics and system health information.

        Provides detailed metrics about order activity, real-time tracking status,
        position-order relationships, and system health for monitoring and debugging.
        This method is useful for system monitoring, performance analysis, and
        diagnosing potential issues with order tracking.

        Returns:
            Dict with complete statistics including:
                - statistics: Core order metrics (placed, cancelled, modified, etc.)
                - realtime_enabled: Whether real-time order tracking is active
                - tracked_orders: Number of orders currently in cache
                - position_order_relationships: Details about order-position links
                - callbacks_registered: Number of callbacks per event type
                - health_status: Overall system health status ("healthy" or "degraded")

        Example:
            ```python
            # Get comprehensive order statistics
            stats = await order_manager.get_order_statistics()

            # Access basic statistics
            orders_placed = stats["statistics"]["orders_placed"]
            orders_cancelled = stats["statistics"]["orders_cancelled"]
            bracket_orders = stats["statistics"]["bracket_orders_placed"]
            last_order_time = stats["statistics"]["last_order_time"]

            print(
                f"Session statistics: {orders_placed} orders placed, "
                f"{orders_cancelled} cancelled, {bracket_orders} bracket orders"
            )

            if last_order_time:
                print(f"Last order placed at: {last_order_time}")

            # Check realtime system status
            realtime_status = "ENABLED" if stats["realtime_enabled"] else "DISABLED"
            cached_orders = stats["tracked_orders"]
            print(
                f"Realtime tracking: {realtime_status}, {cached_orders} orders in cache"
            )

            # Examine position-order relationships
            relationships = stats["position_order_relationships"]
            positions_count = relationships["positions_with_orders"]
            print(f"Tracking {positions_count} positions with active orders")

            # Detailed position order summary
            for contract_id, orders in relationships["position_summary"].items():
                print(
                    f"  {contract_id}: {orders['entry']} entry, "
                    f"{orders['stop']} stop, {orders['target']} target orders"
                )

            # Assess system health
            health = stats["health_status"]
            print(f"System health status: {health}")
            ```

        Note:
            - This method acquires the order_lock to ensure thread safety
            - The health_status is "healthy" if real-time tracking is enabled or orders are tracked
            - Position summary only includes positions with at least one active order
        """
        async with self.order_lock:
            # Use internal order tracking
            tracked_orders_count = len(self.tracked_orders)

            # Count position-order relationships
            total_position_orders = 0
            position_summary = {}
            for contract_id, orders in self.position_orders.items():
                entry_count = len(orders["entry_orders"])
                stop_count = len(orders["stop_orders"])
                target_count = len(orders["target_orders"])
                total_count = entry_count + stop_count + target_count

                if total_count > 0:
                    total_position_orders += total_count
                    position_summary[contract_id] = {
                        "entry": entry_count,
                        "stop": stop_count,
                        "target": target_count,
                        "total": total_count,
                    }

            # Count callbacks
            callback_counts = {
                event_type: len(callbacks)
                for event_type, callbacks in self.order_callbacks.items()
            }

            return {
                "statistics": self.stats,
                "realtime_enabled": self._realtime_enabled,
                "tracked_orders": tracked_orders_count,
                "position_order_relationships": {
                    "total_order_position_links": len(self.order_to_position),
                    "positions_with_orders": len(position_summary),
                    "total_position_orders": total_position_orders,
                    "position_summary": position_summary,
                },
                "callbacks_registered": callback_counts,
                "health_status": "healthy"
                if self._realtime_enabled or tracked_orders_count > 0
                else "degraded",
            }

    async def close_position(
        self,
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
            >>> # Close position at market
            >>> response = await order_manager.close_position("MGC", method="market")
            >>> # Close position with limit
            >>> response = await order_manager.close_position(
            ...     "MGC", method="limit", limit_price=2050.0
            ... )
        """
        # Get current position
        positions = await self.project_x.search_open_positions(account_id=account_id)
        position = None
        for pos in positions:
            if pos.contractId == contract_id:
                position = pos
                break

        if not position:
            self.logger.warning(f"⚠️ No open position found for {contract_id}")
            return None

        # Determine order side (opposite of position)
        side = 1 if position.size > 0 else 0  # Sell long, Buy short
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

    async def place_trailing_stop_order(
        self,
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

    async def cancel_all_orders(
        self, contract_id: str | None = None, account_id: int | None = None
    ) -> dict[str, Any]:
        """
        Cancel all open orders, optionally filtered by contract.

        Args:
            contract_id: Optional contract ID to filter orders
            account_id: Account ID. Uses default account if None.

        Returns:
            Dict with cancellation results

        Example:
            >>> results = await order_manager.cancel_all_orders()
            >>> print(f"Cancelled {results['cancelled']} orders")
        """
        orders = await self.search_open_orders(contract_id, account_id)

        results: dict[str, Any] = {
            "total": len(orders),
            "cancelled": 0,
            "failed": 0,
            "errors": [],
        }

        for order in orders:
            try:
                if await self.cancel_order(order.id, account_id):
                    results["cancelled"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"order_id": order.id, "error": str(e)})

        return results

    async def add_stop_loss(
        self,
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
            >>> response = await order_manager.add_stop_loss("MGC", 2040.0)
        """
        # Get current position
        positions = await self.project_x.search_open_positions(account_id=account_id)
        position = None
        for pos in positions:
            if pos.contractId == contract_id:
                position = pos
                break

        if not position:
            self.logger.warning(f"⚠️ No open position found for {contract_id}")
            return None

        # Determine order side (opposite of position)
        side = 1 if position.size > 0 else 0  # Sell long, Buy short
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
        self,
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
            >>> response = await order_manager.add_take_profit("MGC", 2060.0)
        """
        # Get current position
        positions = await self.project_x.search_open_positions(account_id=account_id)
        position = None
        for pos in positions:
            if pos.contractId == contract_id:
                position = pos
                break

        if not position:
            self.logger.warning(f"⚠️ No open position found for {contract_id}")
            return None

        # Determine order side (opposite of position)
        side = 1 if position.size > 0 else 0  # Sell long, Buy short
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
        self,
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
            self.logger.debug(
                f"Tracking {order_type} order {order_id} for position {contract_id}"
            )

    def untrack_order(self, order_id: int) -> None:
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

            self.logger.debug(f"Untracked order {order_id}")

    def get_position_orders(self, contract_id: str) -> dict[str, list[int]]:
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
        self,
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
            >>> # Cancel only stop orders
            >>> results = await order_manager.cancel_position_orders("MGC", ["stop"])
            >>> # Cancel all orders for position
            >>> results = await order_manager.cancel_position_orders("MGC")
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
                        self.logger.error(
                            f"Failed to cancel {order_type} order {order_id}: {e}"
                        )

        return results

    async def update_position_order_sizes(
        self, contract_id: str, new_size: int, account_id: int | None = None
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
                    if order and order.status == 1:  # Open
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
        self,
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
        self,
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
        self.logger.info(
            f"Position changed for {contract_id}: {old_size} -> {new_size}"
        )

        if new_size == 0:
            # Position closed, cancel remaining orders
            await self.on_position_closed(contract_id, account_id)
        else:
            # Position partially filled, update order sizes
            await self.sync_orders_with_position(
                contract_id, abs(new_size), cancel_orphaned=True, account_id=account_id
            )

    async def on_position_closed(
        self, contract_id: str, account_id: int | None = None
    ) -> None:
        """
        Handle position closure by canceling all related orders.

        Args:
            contract_id: Contract ID of the closed position
            account_id: Account ID for multi-account support
        """
        self.logger.info(f"Position closed for {contract_id}, cancelling all orders")

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

        self.logger.info(f"Cleaned up position {contract_id}: {cancel_results}")

    def get_realtime_validation_status(self) -> dict[str, Any]:
        """
        Get real-time validation and health status.

        Returns:
            Dict with validation status and metrics
        """
        return {
            "realtime_enabled": self._realtime_enabled,
            "tracked_orders": len(self.tracked_orders),
            "order_cache_size": len(self.order_status_cache),
            "position_links": len(self.order_to_position),
            "monitored_positions": len(self.position_orders),
            "callbacks_registered": {
                event_type: len(callbacks)
                for event_type, callbacks in self.order_callbacks.items()
            },
        }

    def add_callback(
        self, event_type: str, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """
        Register a callback function for specific order events.

        Allows you to listen for order fills, cancellations, rejections, and other
        order status changes to build custom monitoring and notification systems.
        Callbacks can be synchronous functions or asynchronous coroutines.

        Args:
            event_type: Type of event to listen for
                - "order_filled": Order completely filled (status changed to 2)
                - "order_cancelled": Order cancelled (status changed to 3)
                - "order_expired": Order expired (status changed to 4)
                - "order_rejected": Order rejected by exchange (status changed to 5)
                - "order_pending": Order pending submission (status changed to 6)
                - "order_update": Any order status update (with new order data)
                - "trade_execution": Individual trade execution notification
                - "position_update": Position changes (size or average price)
                - "{order_id}": Specific order ID to monitor (string ID)
            callback: Function or coroutine to call when event occurs.
                Will be called with a dictionary of order/trade data.

        Example:
            ```python
            # Regular function callback for order fills
            def on_order_filled(data):
                print(f"Order {data.get('id')} filled at {data.get('filledPrice')}")


            order_manager.add_callback("order_filled", on_order_filled)


            # Async coroutine callback for specific order
            async def on_specific_order_update(data):
                print(f"Order {data.get('id')} updated: status={data.get('status')}")
                # Perform async operations like database updates
                await database.update_order_status(data.get("id"), data.get("status"))


            # Monitor a specific order by ID
            order_manager.add_callback("12345", on_specific_order_update)


            # Monitor all trade executions
            async def on_trade(trade_data):
                print(
                    f"Trade executed: {trade_data.get('volume')} @ {trade_data.get('price')}"
                )


            order_manager.add_callback("trade_execution", on_trade)
            ```

        Note:
            - Both synchronous functions and async coroutines are supported as callbacks
            - For order-specific callbacks, use the string order ID as the event_type
            - Callbacks are executed sequentially for each event
            - Exceptions in callbacks are caught and logged but don't affect other callbacks
            - Real-time client must be enabled for callbacks to work effectively
        """
        if event_type not in self.order_callbacks:
            self.order_callbacks[event_type] = []
        self.order_callbacks[event_type].append(callback)
        self.logger.debug(f"Registered callback for {event_type}")

    async def _trigger_callbacks(self, event_type: str, data: Any) -> None:
        """
        Trigger all callbacks registered for a specific event type.

        Args:
            event_type: Type of event that occurred
            data: Event data to pass to callbacks
        """
        if event_type in self.order_callbacks:
            for callback in self.order_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    self.logger.error(f"Error in {event_type} callback: {e}")

    def clear_order_tracking(self) -> None:
        """
        Clear all cached order tracking data.

        Useful for resetting the order manager state, particularly after
        connectivity issues or when switching between accounts.
        """
        self.tracked_orders.clear()
        self.order_status_cache.clear()
        self.order_to_position.clear()
        self.position_orders.clear()
        self.logger.info("Cleared all order tracking data")

    async def cleanup(self) -> None:
        """Clean up resources and connections."""
        self.logger.info("Cleaning up AsyncOrderManager resources")

        # Clear all tracking data
        async with self.order_lock:
            self.tracked_orders.clear()
            self.order_status_cache.clear()
            self.order_to_position.clear()
            self.position_orders.clear()
            self.order_callbacks.clear()

        # Clean up realtime client if it exists
        if self.realtime_client:
            try:
                await self.realtime_client.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting realtime client: {e}")

        self.logger.info("AsyncOrderManager cleanup complete")
