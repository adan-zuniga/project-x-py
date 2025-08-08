"""
Async OrderManager core for ProjectX trading.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Contains the main OrderManager class, orchestrating all async order operations
    (placement, modification, cancellation, tracking) and integrating mixins for
    bracket, position, and order type strategies. Provides thread-safe, eventful,
    and real-time capable order workflows for automated and manual trading.

Key Features:
    - Unified async API for order lifecycle (market, limit, stop, trailing, OCO)
    - Bracket and position-based order strategies
    - Real-time tracking, event-driven callbacks, and statistics
    - Price alignment, concurrent safety, and health metrics
    - Extensible for custom bots and strategy engines

Example Usage:
    ```python
    # V3: Initialize order manager with event bus and real-time support
    import asyncio
    from project_x_py import ProjectX, create_realtime_client, EventBus
    from project_x_py.order_manager import OrderManager


    async def main():
        async with ProjectX.from_env() as client:
            await client.authenticate()

            # V3: Create dependencies
            event_bus = EventBus()
            realtime_client = await create_realtime_client(
                client.get_session_token(), str(client.get_account_info().id)
            )

            # V3: Initialize order manager
            om = OrderManager(client, event_bus)
            await om.initialize(realtime_client)

            # V3: Place orders with automatic price alignment
            await om.place_limit_order("ES", side=0, size=1, limit_price=5000.0)

            # V3: Monitor order statistics
            stats = await om.get_order_statistics()
            print(f"Fill rate: {stats['fill_rate']:.1%}")


    asyncio.run(main())
    ```

See Also:
    - `order_manager.bracket_orders`
    - `order_manager.position_orders`
    - `order_manager.order_types`
    - `order_manager.tracking`
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from project_x_py.exceptions import ProjectXOrderError
from project_x_py.models import Order, OrderPlaceResponse
from project_x_py.types.config_types import OrderManagerConfig
from project_x_py.types.stats_types import OrderManagerStats
from project_x_py.types.trading import OrderStatus
from project_x_py.utils import (
    ErrorMessages,
    LogContext,
    LogMessages,
    ProjectXLogger,
    format_error_message,
    handle_errors,
    validate_response,
)

from .bracket_orders import BracketOrderMixin
from .order_types import OrderTypesMixin
from .position_orders import PositionOrderMixin
from .tracking import OrderTrackingMixin
from .utils import align_price_to_tick_size, resolve_contract_id

if TYPE_CHECKING:
    from project_x_py.client import ProjectXBase
    from project_x_py.realtime import ProjectXRealtimeClient

logger = ProjectXLogger.get_logger(__name__)


class OrderManager(
    OrderTrackingMixin, OrderTypesMixin, BracketOrderMixin, PositionOrderMixin
):
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
        - Comprehensive error handling and validation
        - Thread-safe operations with async locks

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
        - 3: StopLimit
        - 4: Stop
        - 5: TrailingStop
        - 6: JoinBid (places limit buy at current best bid)
        - 7: JoinAsk (places limit sell at current best ask)

    The OrderManager combines multiple mixins to provide a unified interface for all
    order-related operations, ensuring consistent behavior and comprehensive functionality
    across different order types and strategies.
    """

    def __init__(
        self,
        project_x_client: "ProjectXBase",
        event_bus: Any,
        config: OrderManagerConfig | None = None,
    ):
        """
        Initialize the OrderManager with an ProjectX client and optional configuration.

        Creates a new instance of the OrderManager that uses the provided ProjectX client
        for API access. This establishes the foundation for order operations but does not
        set up real-time capabilities. To enable real-time order tracking, call the `initialize`
        method with a real-time client after initialization.

        Args:
            project_x_client: ProjectX client instance for API access. This client
                should already be authenticated or authentication should be handled
                separately before attempting order operations.
            event_bus: EventBus instance for unified event handling. Required for all
                event emissions including order placements, fills, and cancellations.
            config: Optional configuration for order management behavior. If not provided,
                default values will be used for all configuration options.
        """
        # Initialize mixins
        OrderTrackingMixin.__init__(self)

        self.project_x = project_x_client
        self.event_bus = event_bus  # Store the event bus for emitting events
        self.logger = ProjectXLogger.get_logger(__name__)

        # Store configuration with defaults
        self.config = config or {}
        self._apply_config_defaults()

        # Async lock for thread safety
        self.order_lock = asyncio.Lock()

        # Real-time integration (optional)
        self.realtime_client: ProjectXRealtimeClient | None = None
        self._realtime_enabled = False

        # Comprehensive statistics tracking
        self.stats: dict[str, Any] = {
            "orders_placed": 0,
            "orders_filled": 0,
            "orders_cancelled": 0,
            "orders_rejected": 0,
            "orders_modified": 0,
            "market_orders": 0,
            "limit_orders": 0,
            "stop_orders": 0,
            "bracket_orders": 0,
            "total_volume": 0,
            "total_value": 0.0,
            "largest_order": 0,
            "risk_violations": 0,
            "order_validation_failures": 0,
            "last_order_time": None,
            "fill_times_ms": [],
            "order_response_times_ms": [],
        }

        self.logger.info("AsyncOrderManager initialized")

    def _apply_config_defaults(self) -> None:
        """Apply default values for configuration options."""
        # Set default configuration values
        self.enable_bracket_orders = self.config.get("enable_bracket_orders", True)
        self.enable_trailing_stops = self.config.get("enable_trailing_stops", True)
        self.auto_risk_management = self.config.get("auto_risk_management", False)
        self.max_order_size = self.config.get("max_order_size", 1000)
        self.max_orders_per_minute = self.config.get("max_orders_per_minute", 120)
        self.default_order_type = self.config.get("default_order_type", "limit")
        self.enable_order_validation = self.config.get("enable_order_validation", True)
        self.require_confirmation = self.config.get("require_confirmation", False)
        self.auto_cancel_on_close = self.config.get("auto_cancel_on_close", False)
        self.order_timeout_minutes = self.config.get("order_timeout_minutes", 60)

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
        5. WebSocket connections are established for live updates
        6. Order tracking is optimized for minimal latency

        Args:
            realtime_client: Optional AsyncProjectXRealtimeClient for live order tracking.
                If provided, the order manager will connect to the real-time API
                and subscribe to user updates for order status tracking.

        Returns:
            bool: True if initialization successful, False otherwise.

        Note:
            Real-time tracking is highly recommended for production trading as it
            provides immediate order status updates and significantly reduces API
            rate limit consumption.
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

    @handle_errors("place order")
    @validate_response(required_fields=["success", "orderId"])
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

        The method performs several important operations:
        1. Validates all input parameters (size, prices, etc.)
        2. Aligns all prices to the instrument's tick size
        3. Ensures proper account authentication
        4. Places the order via the ProjectX API
        5. Updates internal statistics and tracking
        6. Logs the operation for debugging

        Args:
            contract_id: The contract ID to trade (e.g., "MGC", "MES", "F.US.EP")
            order_type: Order type integer value (1=Limit, 2=Market, 4=Stop, 5=TrailingStop)
            side: Order side integer value: 0=Buy, 1=Sell
            size: Number of contracts to trade (positive integer)
            limit_price: Limit price for limit orders, automatically aligned to tick size.
            stop_price: Stop price for stop orders, automatically aligned to tick size.
            trail_price: Trail amount for trailing stop orders, automatically aligned to tick size.
            custom_tag: Custom identifier for the order (for your reference)
            linked_order_id: ID of a linked order for OCO (One-Cancels-Other) relationships
            account_id: Account ID. Uses default account from authenticated client if None.

        Returns:
            OrderPlaceResponse: Response containing order ID and status information

        Raises:
            ProjectXOrderError: If order placement fails due to invalid parameters or API errors

        Example:
            >>> # V3: Place a limit buy order with automatic price alignment
            >>> response = await om.place_order(
            ...     contract_id="MGC",
            ...     order_type=1,  # Limit order
            ...     side=0,  # Buy
            ...     size=1,
            ...     limit_price=2050.0,  # Automatically aligned to tick size
            ...     custom_tag="my_strategy_001",  # Optional tag for tracking
            ... )
            >>> print(f"Order placed: {response.orderId}")
            >>> print(f"Success: {response.success}")
            >>> # V3: Place a stop loss order
            >>> stop_response = await om.place_order(
            ...     contract_id="MGC",
            ...     order_type=4,  # Stop order
            ...     side=1,  # Sell
            ...     size=1,
            ...     stop_price=2040.0,  # Automatically aligned to tick size
            ... )
        """
        # Add logging context
        with LogContext(
            self.logger,
            operation="place_order",
            contract_id=contract_id,
            order_type=order_type,
            side=side,
            size=size,
            custom_tag=custom_tag,
        ):
            # Validate inputs
            if not isinstance(contract_id, str) or not contract_id:
                raise ProjectXOrderError(
                    format_error_message(
                        ErrorMessages.INSTRUMENT_INVALID_SYMBOL, symbol=contract_id
                    )
                )

            if size <= 0:
                raise ProjectXOrderError(
                    format_error_message(ErrorMessages.ORDER_INVALID_SIZE, size=size)
                )

            # Validate order side and type against expected enums
            if side not in (0, 1):
                raise ProjectXOrderError(
                    format_error_message(ErrorMessages.ORDER_INVALID_SIDE, side=side)
                )

            if order_type not in {1, 2, 3, 4, 5, 6, 7}:
                raise ProjectXOrderError(
                    format_error_message(
                        ErrorMessages.ORDER_INVALID_TYPE, order_type=order_type
                    )
                )

            self.logger.info(
                LogMessages.ORDER_PLACE,
                extra={
                    "contract_id": contract_id,
                    "order_type": order_type,
                    "side": side,
                    "size": size,
                    "limit_price": limit_price,
                    "stop_price": stop_price,
                },
            )

            async with self.order_lock:
                # Align all prices to tick size to prevent "Invalid price" errors
                aligned_limit_price = await align_price_to_tick_size(
                    limit_price, contract_id, self.project_x
                )
                aligned_stop_price = await align_price_to_tick_size(
                    stop_price, contract_id, self.project_x
                )
                aligned_trail_price = await align_price_to_tick_size(
                    trail_price, contract_id, self.project_x
                )

                # Use account_info if no account_id provided
                if account_id is None:
                    if not self.project_x.account_info:
                        raise ProjectXOrderError(ErrorMessages.ORDER_NO_ACCOUNT)
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

                # Place the order
                response = await self.project_x._make_request(
                    "POST", "/Order/place", data=payload
                )

                if not response.get("success", False):
                    error_msg = response.get("errorMessage", ErrorMessages.ORDER_FAILED)
                    raise ProjectXOrderError(error_msg)

                result = OrderPlaceResponse(**response)

                # Update statistics
                self.stats["orders_placed"] += 1
                self.stats["last_order_time"] = datetime.now()
                self.stats["total_volume"] += size
                if size > self.stats["largest_order"]:
                    self.stats["largest_order"] = size

                self.logger.info(
                    LogMessages.ORDER_PLACED,
                    extra={
                        "order_id": result.orderId,
                        "contract_id": contract_id,
                        "side": side,
                        "size": size,
                    },
                )

                # Emit order placed event
                await self._trigger_callbacks(
                    "order_placed",
                    {
                        "order_id": result.orderId,
                        "contract_id": contract_id,
                        "order_type": order_type,
                        "side": side,
                        "size": size,
                        "limit_price": aligned_limit_price,
                        "stop_price": aligned_stop_price,
                        "trail_price": aligned_trail_price,
                        "custom_tag": custom_tag,
                        "response": result,
                    },
                )

                return result

    @handle_errors("search open orders")
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
        """
        if not self.project_x.account_info:
            raise ProjectXOrderError(ErrorMessages.ORDER_NO_ACCOUNT)

        params = {"accountId": self.project_x.account_info.id}

        if contract_id:
            # Resolve contract
            resolved = await resolve_contract_id(contract_id, self.project_x)
            if resolved and resolved.get("id"):
                params["contractId"] = resolved["id"]

        if side is not None:
            params["side"] = side

        response = await self.project_x._make_request(
            "POST", "/Order/searchOpen", data=params
        )

        if not response.get("success", False):
            error_msg = response.get("errorMessage", ErrorMessages.ORDER_SEARCH_FAILED)
            raise ProjectXOrderError(error_msg)

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
                self.logger.warning(
                    "Failed to parse order",
                    extra={"error": str(e), "order_data": order_data},
                )
                continue

        return open_orders

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
        """
        order_id_str = str(order_id)

        # Try cached data first with brief retry for real-time updates
        if self._realtime_enabled:
            for attempt in range(3):  # Try 3 times with small delays
                async with self.order_lock:
                    status = self.order_status_cache.get(order_id_str)
                    if status is not None:
                        return status == OrderStatus.FILLED

                if attempt < 2:  # Don't sleep on last attempt
                    await asyncio.sleep(0.2)  # Brief wait for real-time update

        # Fallback to API check
        order = await self.get_order_by_id(int(order_id))
        return order is not None and order.status == OrderStatus.FILLED

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

    @handle_errors("cancel order")
    async def cancel_order(self, order_id: int, account_id: int | None = None) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Order ID to cancel
            account_id: Account ID. Uses default account if None.

        Returns:
            True if cancellation successful
        """
        self.logger.info(LogMessages.ORDER_CANCEL, extra={"order_id": order_id})

        async with self.order_lock:
            # Get account ID if not provided
            if account_id is None:
                if not self.project_x.account_info:
                    await self.project_x.authenticate()
                if not self.project_x.account_info:
                    raise ProjectXOrderError(ErrorMessages.ORDER_NO_ACCOUNT)
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
                    self.tracked_orders[str(order_id)]["status"] = OrderStatus.CANCELLED
                    self.order_status_cache[str(order_id)] = OrderStatus.CANCELLED

                self.stats["orders_cancelled"] += 1
                self.logger.info(
                    LogMessages.ORDER_CANCELLED, extra={"order_id": order_id}
                )
                return True
            else:
                error_msg = response.get(
                    "errorMessage", ErrorMessages.ORDER_CANCEL_FAILED
                )
                raise ProjectXOrderError(
                    format_error_message(
                        ErrorMessages.ORDER_CANCEL_FAILED,
                        order_id=order_id,
                        reason=error_msg,
                    )
                )

    @handle_errors("modify order")
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
        """
        with LogContext(
            self.logger,
            operation="modify_order",
            order_id=order_id,
            has_limit=limit_price is not None,
            has_stop=stop_price is not None,
            has_size=size is not None,
        ):
            self.logger.info(LogMessages.ORDER_MODIFY, extra={"order_id": order_id})

            # Get existing order details to determine contract_id for price alignment
            existing_order = await self.get_order_by_id(order_id)
            if not existing_order:
                raise ProjectXOrderError(
                    format_error_message(
                        ErrorMessages.ORDER_NOT_FOUND, order_id=order_id
                    )
                )

            contract_id = existing_order.contractId

            # Align prices to tick size
            aligned_limit = await align_price_to_tick_size(
                limit_price, contract_id, self.project_x
            )
            aligned_stop = await align_price_to_tick_size(
                stop_price, contract_id, self.project_x
            )

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
                    self.stats["orders_modified"] += 1

                self.logger.info(
                    LogMessages.ORDER_MODIFIED, extra={"order_id": order_id}
                )

                # Emit order modified event
                await self._trigger_callbacks(
                    "order_modified",
                    {
                        "order_id": order_id,
                        "modifications": {
                            "limit_price": aligned_limit,
                            "stop_price": aligned_stop,
                            "size": size,
                        },
                    },
                )

                return True
            else:
                error_msg = (
                    response.get("errorMessage", ErrorMessages.ORDER_MODIFY_FAILED)
                    if response
                    else ErrorMessages.ORDER_MODIFY_FAILED
                )
                raise ProjectXOrderError(
                    format_error_message(
                        ErrorMessages.ORDER_MODIFY_FAILED,
                        order_id=order_id,
                        reason=error_msg,
                    )
                )

    @handle_errors("cancel all orders")
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
        """
        with LogContext(
            self.logger,
            operation="cancel_all_orders",
            contract_id=contract_id,
            account_id=account_id,
        ):
            self.logger.info(
                LogMessages.ORDER_CANCEL_ALL, extra={"contract_id": contract_id}
            )

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

            self.logger.info(
                LogMessages.ORDER_CANCEL_ALL_COMPLETE,
                extra={
                    "total": results["total"],
                    "cancelled": results["cancelled"],
                    "failed": results["failed"],
                },
            )

            return results

    async def get_order_statistics(self) -> OrderManagerStats:
        """
        Get comprehensive order management statistics and system health information.

        Provides detailed metrics about order activity, real-time tracking status,
        position-order relationships, and system health for monitoring and debugging.

        Returns:
            Dict with complete statistics
        """
        async with self.order_lock:
            # Use internal order tracking
            _tracked_orders_count = len(self.tracked_orders)

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

            # Callbacks now handled through EventBus
            _callback_counts: dict[str, int] = {}

            # Calculate performance metrics
            fill_rate = (
                self.stats["orders_filled"] / self.stats["orders_placed"]
                if self.stats["orders_placed"] > 0
                else 0.0
            )

            rejection_rate = (
                self.stats["orders_rejected"] / self.stats["orders_placed"]
                if self.stats["orders_placed"] > 0
                else 0.0
            )

            avg_fill_time_ms = (
                sum(self.stats["fill_times_ms"]) / len(self.stats["fill_times_ms"])
                if self.stats["fill_times_ms"]
                else 0.0
            )

            avg_order_response_time_ms = (
                sum(self.stats["order_response_times_ms"])
                / len(self.stats["order_response_times_ms"])
                if self.stats["order_response_times_ms"]
                else 0.0
            )

            avg_order_size = (
                self.stats["total_volume"] / self.stats["orders_placed"]
                if self.stats["orders_placed"] > 0
                else 0.0
            )

            fastest_fill_ms = (
                min(self.stats["fill_times_ms"]) if self.stats["fill_times_ms"] else 0.0
            )
            slowest_fill_ms = (
                max(self.stats["fill_times_ms"]) if self.stats["fill_times_ms"] else 0.0
            )

            return {
                "orders_placed": self.stats["orders_placed"],
                "orders_filled": self.stats["orders_filled"],
                "orders_cancelled": self.stats["orders_cancelled"],
                "orders_rejected": self.stats["orders_rejected"],
                "orders_modified": self.stats["orders_modified"],
                # Performance metrics
                "fill_rate": fill_rate,
                "avg_fill_time_ms": avg_fill_time_ms,
                "rejection_rate": rejection_rate,
                # Order types
                "market_orders": self.stats["market_orders"],
                "limit_orders": self.stats["limit_orders"],
                "stop_orders": self.stats["stop_orders"],
                "bracket_orders": self.stats["bracket_orders"],
                # Timing statistics
                "last_order_time": self.stats["last_order_time"].isoformat()
                if self.stats["last_order_time"]
                else None,
                "avg_order_response_time_ms": avg_order_response_time_ms,
                "fastest_fill_ms": fastest_fill_ms,
                "slowest_fill_ms": slowest_fill_ms,
                # Volume and value
                "total_volume": self.stats["total_volume"],
                "total_value": self.stats["total_value"],
                "avg_order_size": avg_order_size,
                "largest_order": self.stats["largest_order"],
                # Risk metrics
                "risk_violations": self.stats["risk_violations"],
                "order_validation_failures": self.stats["order_validation_failures"],
            }

    async def cleanup(self) -> None:
        """Clean up resources and connections."""
        self.logger.info("Cleaning up AsyncOrderManager resources")

        # Clear all tracking data
        async with self.order_lock:
            self.tracked_orders.clear()
            self.order_status_cache.clear()
            self.order_to_position.clear()
            self.position_orders.clear()
            # EventBus handles all callbacks now

        # Clean up realtime client if it exists
        if self.realtime_client:
            try:
                await self.realtime_client.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting realtime client: {e}")

        self.logger.info("AsyncOrderManager cleanup complete")
