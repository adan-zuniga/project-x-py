"""
Core OrderManager class for comprehensive order operations.

This module provides the main OrderManager class that handles all order-related
operations including placement, modification, cancellation, and tracking.
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from project_x_py.exceptions import ProjectXOrderError
from project_x_py.models import Order, OrderPlaceResponse

from .bracket_orders import BracketOrderMixin
from .order_types import OrderTypesMixin
from .position_orders import PositionOrderMixin
from .tracking import OrderTrackingMixin
from .types import OrderStats
from .utils import align_price_to_tick_size, resolve_contract_id

if TYPE_CHECKING:
    from project_x_py.client import ProjectXBase
    from project_x_py.realtime import ProjectXRealtimeClient

logger = logging.getLogger(__name__)


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
    """

    def __init__(self, project_x_client: "ProjectXBase"):
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
        """
        # Initialize mixins
        OrderTrackingMixin.__init__(self)

        self.project_x = project_x_client
        self.logger = logging.getLogger(__name__)

        # Async lock for thread safety
        self.order_lock = asyncio.Lock()

        # Real-time integration (optional)
        self.realtime_client: ProjectXRealtimeClient | None = None
        self._realtime_enabled = False

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
            order_type: Order type integer value
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
        """
        result = None
        aligned_limit_price = None
        aligned_stop_price = None
        aligned_trail_price = None

        async with self.order_lock:
            try:
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
        try:
            if not self.project_x.account_info:
                raise ProjectXOrderError("No account selected")

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
        """
        try:
            # Get existing order details to determine contract_id for price alignment
            existing_order = await self.get_order_by_id(order_id)
            if not existing_order:
                self.logger.error(f"❌ Cannot modify order {order_id}: Order not found")
                return False

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

    async def get_order_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive order management statistics and system health information.

        Provides detailed metrics about order activity, real-time tracking status,
        position-order relationships, and system health for monitoring and debugging.

        Returns:
            Dict with complete statistics
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
