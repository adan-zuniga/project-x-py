"""
Async order tracking and real-time monitoring for ProjectX.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Implements mixin logic for tracking order status, maintaining local state and cache,
    and handling real-time updates from websocket events. Supports callback registration
    for fills/cancels, cache queries, and system health validation.

Key Features:
    - Real-time tracking via websocket/callbacks and local cache
    - Order-to-position relationship mapping
    - Async event/callback system for fills, cancels, rejections
    - Cache clearing, health/status reporting, and metrics
    - Integrates with OrderManager main class
    - WebSocket-based order status updates
    - Local caching for performance optimization
    - Comprehensive order lifecycle monitoring

Real-time Tracking Capabilities:
    - Immediate order status change detection
    - Fill and cancellation event processing
    - Order-to-position relationship tracking
    - Custom callback registration for events
    - Cache-based performance optimization
    - Health monitoring and validation

Example Usage:
    ```python
    # Assuming om is an instance of OrderManager
    await om.initialize(realtime_client)
    tracked = await om.get_tracked_order_status("12345")


    # Register callback for order events
    def on_order_fill(order_data):
        print(f"Order {order_data['id']} filled!")


    om.add_callback("order_fill", on_order_fill)
    ```

See Also:
    - `order_manager.core.OrderManager`
    - `order_manager.position_orders`
    - `order_manager.utils`
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_x_py.types import OrderManagerProtocol

logger = logging.getLogger(__name__)


class OrderTrackingMixin:
    """
    Mixin for order tracking and real-time monitoring functionality.

    Provides comprehensive order tracking capabilities including real-time status monitoring,
    local caching for performance optimization, callback registration for custom event
    handling, and order-to-position relationship management. This enables efficient
    order lifecycle monitoring and automated trading strategies.
    """

    # Type hints for mypy - these attributes are provided by the main class
    if TYPE_CHECKING:
        from asyncio import Lock
        from typing import Any

        from project_x_py.realtime import ProjectXRealtimeClient

        order_lock: Lock
        realtime_client: ProjectXRealtimeClient | None
        _realtime_enabled: bool
        event_bus: Any  # EventBus instance

    def __init__(self) -> None:
        """Initialize tracking attributes."""
        # Internal order state tracking (for realtime optimization)
        self.tracked_orders: dict[str, dict[str, Any]] = {}  # order_id -> order_data
        self.order_status_cache: dict[str, int] = {}  # order_id -> last_known_status

        # EventBus is now used for all event handling

        # Order-Position relationship tracking for synchronization
        self.position_orders: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: {"stop_orders": [], "target_orders": [], "entry_orders": []}
        )
        self.order_to_position: dict[int, str] = {}  # order_id -> contract_id

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

    async def _on_order_update(self, order_data: dict[str, Any] | list[Any]) -> None:
        """Handle real-time order update events."""
        try:
            logger.info(f"📨 Order update received: {type(order_data)}")

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
                        logger.warning(f"Unexpected order data format: {order_data}")
                        return
                else:
                    return

            if not isinstance(order_data, dict):
                logger.warning(f"Order data is not a dict: {type(order_data)}")
                return

            # Extract order data - handle nested structure from SignalR
            actual_order_data = order_data
            if "action" in order_data and "data" in order_data:
                # SignalR format: {'action': 1, 'data': {...}}
                actual_order_data = order_data["data"]

            order_id = actual_order_data.get("id")
            if not order_id:
                logger.warning(f"No order ID found in data: {order_data}")
                return

            logger.info(
                f"📨 Tracking order {order_id} (status: {actual_order_data.get('status')})"
            )

            # Update our cache with the actual order data
            async with self.order_lock:
                old_status = self.order_status_cache.get(str(order_id))
                new_status = actual_order_data.get("status", 0)

                self.tracked_orders[str(order_id)] = actual_order_data
                self.order_status_cache[str(order_id)] = new_status
                logger.info(
                    f"✅ Order {order_id} added to cache. Total tracked: {len(self.tracked_orders)}"
                )

            # Emit events based on status changes
            if old_status != new_status:
                # Map status values to event types
                status_events = {
                    2: "order_filled",  # Filled
                    3: "order_cancelled",  # Cancelled
                    4: "order_expired",  # Expired
                    5: "order_rejected",  # Rejected
                }

                if new_status in status_events:
                    await self._trigger_callbacks(
                        status_events[new_status],
                        {
                            "order_id": order_id,
                            "order_data": actual_order_data,
                            "old_status": old_status,
                            "new_status": new_status,
                        },
                    )

                # Check for partial fills
                fills = actual_order_data.get("fills", [])
                filled_size = sum(fill.get("size", 0) for fill in fills)
                total_size = actual_order_data.get("size", 0)

                if filled_size > 0 and filled_size < total_size:
                    await self._trigger_callbacks(
                        "order_partial_fill",
                        {
                            "order_id": order_id,
                            "order_data": actual_order_data,
                            "filled_size": filled_size,
                            "total_size": total_size,
                        },
                    )

            # Legacy callbacks have been removed - use EventBus

        except Exception as e:
            logger.error(f"Error handling order update: {e}")
            logger.debug(f"Order data received: {order_data}")

    # Back-compat helper for tests that directly call _process_order_update
    async def _process_order_update(self, order_data: dict[str, Any]) -> None:
        """Process a single order update (compat wrapper used by tests)."""
        await self._on_order_update(order_data)

    async def _on_trade_execution(self, trade_data: dict[str, Any] | list[Any]) -> None:
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
                        logger.warning(f"Unexpected trade data format: {trade_data}")
                        return
                else:
                    return

            if not isinstance(trade_data, dict):
                logger.warning(f"Trade data is not a dict: {type(trade_data)}")
                return

            order_id = trade_data.get("orderId")
            if order_id and str(order_id) in self.tracked_orders:
                # Update fill information
                async with self.order_lock:
                    if "fills" not in self.tracked_orders[str(order_id)]:
                        self.tracked_orders[str(order_id)]["fills"] = []
                    self.tracked_orders[str(order_id)]["fills"].append(trade_data)

        except Exception as e:
            logger.error(f"Error handling trade execution: {e}")
            logger.debug(f"Trade data received: {trade_data}")

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

    def add_callback(
        self,
        event_type: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """
        DEPRECATED: Use TradingSuite.on() with EventType enum instead.

        This method is provided for backward compatibility only and will be removed in v4.0.
        """
        logger.warning(
            "add_callback is deprecated. Use TradingSuite.on() with EventType enum instead."
        )

    async def _trigger_callbacks(self, event_type: str, data: Any) -> None:
        """
        Trigger all callbacks registered for a specific event type.

        Args:
            event_type: Type of event that occurred
            data: Event data to pass to callbacks
        """
        # Emit event through EventBus
        from project_x_py.event_bus import EventType

        # Map order event types to EventType enum
        event_mapping = {
            "order_placed": EventType.ORDER_PLACED,
            "order_filled": EventType.ORDER_FILLED,
            "order_partial_fill": EventType.ORDER_PARTIAL_FILL,
            "order_cancelled": EventType.ORDER_CANCELLED,
            "order_rejected": EventType.ORDER_REJECTED,
            "order_expired": EventType.ORDER_EXPIRED,
            "order_modified": EventType.ORDER_MODIFIED,
        }

        if event_type in event_mapping:
            await self.event_bus.emit(
                event_mapping[event_type], data, source="OrderManager"
            )

        # Legacy callbacks have been removed - use EventBus

    def clear_order_tracking(self: "OrderManagerProtocol") -> None:
        """
        Clear all cached order tracking data.

        Useful for resetting the order manager state, particularly after
        connectivity issues or when switching between accounts.
        """
        self.tracked_orders.clear()
        self.order_status_cache.clear()
        self.order_to_position.clear()
        self.position_orders.clear()
        logger.info("Cleared all order tracking data")

    def get_realtime_validation_status(self: "OrderManagerProtocol") -> dict[str, Any]:
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
        }
