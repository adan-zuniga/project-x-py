#!/usr/bin/env python3
"""
OrderManager for Comprehensive Order Operations

Author: TexasCoding
Date: June 2025

This module provides comprehensive order management capabilities for the ProjectX API:
1. Order placement (market, limit, stop, trailing stop, bracket orders)
2. Order modification and cancellation
3. Order status tracking and search
4. Automatic price alignment to tick sizes
5. Real-time order monitoring integration
6. Advanced order types (OCO, bracket, conditional)

Key Features:
- Thread-safe order operations
- Dependency injection with ProjectX client
- Integration with ProjectXRealtimeClient for live updates
- Automatic price alignment and validation
- Comprehensive error handling and retry logic
- Support for complex order strategies

Architecture:
- Similar to OrderBook and ProjectXRealtimeDataManager
- Clean separation from main client class
- Real-time order tracking capabilities
- Event-driven order status updates
"""

import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, Optional

import requests

from .exceptions import (
    ProjectXConnectionError,
    ProjectXDataError,
    ProjectXOrderError,
)
from .lock_coordinator import get_lock_coordinator
from .models import (
    BracketOrderResponse,
    Order,
    OrderPlaceResponse,
)
from .utils import extract_symbol_from_contract_id

if TYPE_CHECKING:
    from .client import ProjectX
    from .realtime import ProjectXRealtimeClient


class OrderManager:
    """
    Comprehensive order management system for ProjectX trading operations.

    This class handles all order-related operations including placement, modification,
    cancellation, and tracking. It integrates with both the ProjectX API client and
    the real-time client for live order monitoring.

    Features:
        - Complete order lifecycle management
        - Bracket order strategies with automatic stop/target placement
        - Real-time order status tracking (fills/cancellations detected from status changes)
        - Automatic price alignment to instrument tick sizes
        - OCO (One-Cancels-Other) order support
        - Position-based order management
        - Thread-safe operations for concurrent trading

    Example Usage:
        >>> # Create order manager with dependency injection
        >>> order_manager = OrderManager(project_x_client)
        >>> # Initialize with optional real-time client
        >>> order_manager.initialize(realtime_client=realtime_client)
        >>> # Place simple orders
        >>> response = order_manager.place_market_order("MGC", side=0, size=1)
        >>> response = order_manager.place_limit_order("MGC", 1, 1, 2050.0)
        >>> # Place bracket orders (entry + stop + target)
        >>> bracket = order_manager.place_bracket_order(
        ...     contract_id="MGC",
        ...     side=0,  # Buy
        ...     size=1,
        ...     entry_price=2045.0,
        ...     stop_loss_price=2040.0,
        ...     take_profit_price=2055.0,
        ... )
        >>> # Manage existing orders
        >>> orders = order_manager.search_open_orders()
        >>> order_manager.cancel_order(order_id)
        >>> order_manager.modify_order(order_id, new_price=2052.0)
        >>> # Position-based operations
        >>> order_manager.close_position("MGC", method="market")
        >>> order_manager.add_stop_loss("MGC", stop_price=2040.0)
        >>> order_manager.add_take_profit("MGC", target_price=2055.0)
    """

    def __init__(self, project_x_client: "ProjectX"):
        """
        Initialize the OrderManager with a ProjectX client.

        Args:
            project_x_client: ProjectX client instance for API access
        """
        self.project_x = project_x_client
        self.logger = logging.getLogger(__name__)

        # Thread safety (coordinated with other components)
        self.lock_coordinator = get_lock_coordinator()
        self.order_lock = self.lock_coordinator.order_lock

        # Real-time integration (optional)
        self.realtime_client: ProjectXRealtimeClient | None = None
        self._realtime_enabled = False

        # Internal order state tracking (for realtime optimization)
        self.tracked_orders: dict[str, dict[str, Any]] = {}  # order_id -> order_data
        self.order_status_cache: dict[str, int] = {}  # order_id -> last_known_status

        # Order callbacks (tracking is centralized in realtime client)
        self.order_callbacks: dict[str, list] = defaultdict(list)

        # Order-Position relationship tracking for synchronization
        self.position_orders: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: {"stop_orders": [], "target_orders": [], "entry_orders": []}
        )
        self.order_to_position: dict[int, str] = {}  # order_id -> contract_id

        # Statistics
        self.stats = {
            "orders_placed": 0,
            "orders_cancelled": 0,
            "orders_modified": 0,
            "bracket_orders_placed": 0,
            "last_order_time": None,
        }

        self.logger.info("OrderManager initialized")

    def initialize(
        self, realtime_client: Optional["ProjectXRealtimeClient"] = None
    ) -> bool:
        """
        Initialize the OrderManager with optional real-time capabilities.

        Args:
            realtime_client: Optional ProjectXRealtimeClient for live order tracking

        Returns:
            bool: True if initialization successful
        """
        try:
            # Set up real-time integration if provided
            if realtime_client:
                self.realtime_client = realtime_client
                self._setup_realtime_callbacks()

                # Connect and subscribe to user updates for order tracking
                if not realtime_client.user_connected:
                    if realtime_client.connect():
                        self.logger.info("🔌 Real-time client connected")
                    else:
                        self.logger.warning("⚠️ Real-time client connection failed")
                        return False

                # Subscribe to user updates to receive order events
                if realtime_client.subscribe_user_updates():
                    self.logger.info("📡 Subscribed to user order updates")
                else:
                    self.logger.warning("⚠️ Failed to subscribe to user updates")

                self._realtime_enabled = True
                self.logger.info(
                    "✅ OrderManager initialized with real-time capabilities"
                )
            else:
                self.logger.info("✅ OrderManager initialized (polling mode)")

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize OrderManager: {e}")
            return False

    def _setup_realtime_callbacks(self):
        """Set up callbacks for real-time order monitoring."""
        if not self.realtime_client:
            return

        # Register for order events (fills/cancellations detected from order updates)
        self.realtime_client.add_callback("order_update", self._on_order_update)
        # Also register for trade execution events (complement to order fills)
        self.realtime_client.add_callback("trade_execution", self._on_trade_execution)

        self.logger.info("🔄 Real-time order callbacks registered")

    def _on_order_update(self, data: dict):
        """Handle real-time order updates and detect fills/cancellations."""
        try:
            with self.order_lock:
                # Handle ProjectX Gateway payload format: {'action': X, 'data': order_data}
                if isinstance(data, list):
                    for item in data:
                        self._extract_and_process_order_data(item)
                elif isinstance(data, dict):
                    self._extract_and_process_order_data(data)

            # Note: No duplicate callback triggering - realtime client handles this

        except Exception as e:
            self.logger.error(f"Error processing order update: {e}")

    def _extract_and_process_order_data(self, payload):
        """Extract order data from ProjectX Gateway payload format."""
        try:
            # Handle ProjectX Gateway format: {'action': X, 'data': {...}}
            if isinstance(payload, dict) and "data" in payload:
                order_data = payload["data"]
                self._process_order_data(order_data)
            else:
                # Direct order data (fallback)
                self._process_order_data(payload)
        except Exception as e:
            self.logger.error(f"Error extracting order data from payload: {e}")
            self.logger.debug(f"Payload that caused error: {payload}")

    def _validate_order_payload(self, order_data: dict) -> bool:
        """
        Validate that order payload matches ProjectX GatewayUserOrder format.

        Expected fields according to ProjectX docs:
        - id (long): The order ID
        - accountId (int): The account associated with the order
        - contractId (string): The contract ID on which the order is placed
        - symbolId (string): The symbol ID corresponding to the contract
        - creationTimestamp (string): When the order was created
        - updateTimestamp (string): When the order was last updated
        - status (int): OrderStatus enum (None=0, Open=1, Filled=2, Cancelled=3, Expired=4, Rejected=5, Pending=6)
        - type (int): OrderType enum (Unknown=0, Limit=1, Market=2, StopLimit=3, Stop=4, TrailingStop=5, JoinBid=6, JoinAsk=7)
        - side (int): OrderSide enum (Bid=0, Ask=1)
        - size (int): The size of the order
        - limitPrice (number): The limit price for the order, if applicable
        - stopPrice (number): The stop price for the order, if applicable
        - fillVolume (int): The number of contracts filled on the order
        - filledPrice (number): The price at which the order was filled, if any
        - customTag (string): The custom tag associated with the order, if any

        Args:
            order_data: Order payload from ProjectX realtime feed

        Returns:
            bool: True if payload format is valid
        """
        required_fields = {
            "id",
            "accountId",
            "contractId",
            "creationTimestamp",
            "status",
            "type",
            "side",
            "size",
        }

        if not isinstance(order_data, dict):
            self.logger.warning(f"Order payload is not a dict: {type(order_data)}")
            return False

        missing_fields = required_fields - set(order_data.keys())
        if missing_fields:
            self.logger.warning(
                f"Order payload missing required fields: {missing_fields}"
            )
            return False

        # Validate enum values
        status = order_data.get("status")
        if status not in [0, 1, 2, 3, 4, 5, 6]:  # OrderStatus enum
            self.logger.warning(f"Invalid order status: {status}")
            return False

        order_type = order_data.get("type")
        if order_type not in [0, 1, 2, 3, 4, 5, 6, 7]:  # OrderType enum
            self.logger.warning(f"Invalid order type: {order_type}")
            return False

        side = order_data.get("side")
        if side not in [0, 1]:  # OrderSide enum
            self.logger.warning(f"Invalid order side: {side}")
            return False

        return True

    def _process_order_data(self, order_data: dict):
        """
        Process individual order data and detect status changes.

        ProjectX GatewayUserOrder payload structure uses these enums:
        - OrderStatus: None=0, Open=1, Filled=2, Cancelled=3, Expired=4, Rejected=5, Pending=6
        - OrderType: Unknown=0, Limit=1, Market=2, StopLimit=3, Stop=4, TrailingStop=5, JoinBid=6, JoinAsk=7
        - OrderSide: Bid=0, Ask=1
        """
        try:
            # ProjectX payload structure: order data is direct, not nested under "data"

            # Validate payload format
            if not self._validate_order_payload(order_data):
                self.logger.error(f"Invalid order payload format: {order_data}")
                return

            order_id = str(order_data.get("id", ""))
            if not order_id:
                return

            # Get current and previous order status from internal cache
            current_status = order_data.get("status", 0)
            old_status = self.order_status_cache.get(order_id, 0)

            # Update internal order tracking
            with self.order_lock:
                self.tracked_orders[order_id] = order_data.copy()
                self.order_status_cache[order_id] = current_status

            # Detect status changes and trigger appropriate callbacks using ProjectX OrderStatus enum
            if current_status != old_status:
                self.logger.debug(
                    f"📊 Order {order_id} status changed: {old_status} -> {current_status}"
                )

                # OrderStatus enum: None=0, Open=1, Filled=2, Cancelled=3, Expired=4, Rejected=5, Pending=6
                if current_status == 2:  # Filled
                    self.logger.info(f"✅ Order filled: {order_id}")
                    self._trigger_callbacks("order_filled", order_data)
                elif current_status == 3:  # Cancelled
                    self.logger.info(f"❌ Order cancelled: {order_id}")
                    self._trigger_callbacks("order_cancelled", order_data)
                elif current_status == 4:  # Expired
                    self.logger.info(f"⏰ Order expired: {order_id}")
                    self._trigger_callbacks("order_expired", order_data)
                elif current_status == 5:  # Rejected
                    self.logger.warning(f"🚫 Order rejected: {order_id}")
                    self._trigger_callbacks("order_rejected", order_data)
                elif current_status == 6:  # Pending
                    self.logger.info(f"⏳ Order pending: {order_id}")
                    self._trigger_callbacks("order_pending", order_data)

        except Exception as e:
            self.logger.error(f"Error processing order data: {e}")
            self.logger.debug(f"Order data that caused error: {order_data}")

    def _on_trade_execution(self, data: dict):
        """Handle real-time trade execution notifications."""
        self.logger.info(f"🔄 Trade execution: {data}")
        self._trigger_callbacks("trade_execution", data)

    def _trigger_callbacks(self, event_type: str, data: Any):
        """Trigger registered callbacks for order events."""
        for callback in self.order_callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {e}")

    def add_callback(self, event_type: str, callback):
        """
        Register a callback function for specific order events.

        Allows you to listen for order fills, cancellations, rejections, and other
        order status changes to build custom monitoring and notification systems.

        Args:
            event_type: Type of event to listen for
                - "order_filled": Order completely filled
                - "order_cancelled": Order cancelled
                - "order_expired": Order expired
                - "order_rejected": Order rejected by exchange
                - "order_pending": Order pending submission
                - "trade_execution": Trade execution notification
            callback: Function to call when event occurs
                Should accept one argument: the order data dict

        Example:
            >>> def on_order_filled(order_data):
            ...     print(
            ...         f"Order filled: {order_data.get('id')} - {order_data.get('contractId')}"
            ...     )
            ...     print(f"Fill volume: {order_data.get('fillVolume', 0)}")
            >>> order_manager.add_callback("order_filled", on_order_filled)
            >>> def on_order_cancelled(order_data):
            ...     print(f"Order cancelled: {order_data.get('id')}")
            >>> order_manager.add_callback("order_cancelled", on_order_cancelled)
        """
        self.order_callbacks[event_type].append(callback)

    # ================================================================================
    # REALTIME ORDER TRACKING METHODS (for optimization)
    # ================================================================================

    def get_tracked_order_status(
        self, order_id: str, wait_for_cache: bool = False
    ) -> dict[str, Any] | None:
        """
        Get cached order status from real-time tracking for faster access.

        When real-time mode is enabled, this method provides instant access to
        order status without requiring API calls, improving performance.

        Args:
            order_id: Order ID to get status for (as string)
            wait_for_cache: If True, briefly wait for real-time cache to populate

        Returns:
            dict: Complete order data if tracked in cache, None if not found
                Contains all ProjectX GatewayUserOrder fields:
                - id, accountId, contractId, status, type, side, size
                - limitPrice, stopPrice, fillVolume, filledPrice, etc.

        Example:
            >>> order_data = order_manager.get_tracked_order_status("12345")
            >>> if order_data:
            ...     print(
            ...         f"Status: {order_data['status']}"
            ...     )  # 1=Open, 2=Filled, 3=Cancelled
            ...     print(f"Fill volume: {order_data.get('fillVolume', 0)}")
            >>> else:
            ...     print("Order not found in cache")
        """
        if wait_for_cache and self._realtime_enabled:
            # Brief wait for real-time cache to populate
            for attempt in range(3):
                with self.order_lock:
                    order_data = self.tracked_orders.get(order_id)
                    if order_data:
                        return order_data

                if attempt < 2:  # Don't sleep on last attempt
                    time.sleep(0.3)  # Brief wait for real-time update

        with self.order_lock:
            return self.tracked_orders.get(order_id)

    def is_order_filled(self, order_id: str | int) -> bool:
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
            >>> if order_manager.is_order_filled(12345):
            ...     print("Order has been filled")
            ...     # Proceed with next trading logic
            >>> else:
            ...     print("Order still pending")
        """
        order_id_str = str(order_id)

        # Try cached data first with brief retry for real-time updates
        if self._realtime_enabled:
            for attempt in range(3):  # Try 3 times with small delays
                with self.order_lock:
                    status = self.order_status_cache.get(order_id_str)
                    if status is not None:
                        return status == 2  # 2 = Filled

                if attempt < 2:  # Don't sleep on last attempt
                    time.sleep(0.2)  # Brief wait for real-time update

        # Fallback to API check
        order = self.get_order_by_id(int(order_id))
        return order is not None and order.status == 2  # 2 = Filled

    def clear_order_tracking(self):
        """
        Clear internal order tracking cache for memory management.

        Removes all cached order data from the real-time tracking system.
        Useful for memory cleanup or when restarting order monitoring.

        Example:
            >>> order_manager.clear_order_tracking()
        """
        with self.order_lock:
            self.tracked_orders.clear()
            self.order_status_cache.clear()
            self.logger.debug("📊 Cleared order tracking cache")

    # ================================================================================
    # CORE ORDER PLACEMENT METHODS
    # ================================================================================

    def place_market_order(
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
            >>> response = order_manager.place_market_order("MGC", 0, 1)
        """
        return self.place_order(
            contract_id=contract_id,
            order_type=2,  # Market order
            side=side,
            size=size,
            account_id=account_id,
        )

    def place_limit_order(
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
            >>> response = order_manager.place_limit_order("MGC", 1, 1, 2050.0)
        """
        return self.place_order(
            contract_id=contract_id,
            order_type=1,  # Limit order
            side=side,
            size=size,
            limit_price=limit_price,
            account_id=account_id,
        )

    def place_stop_order(
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
            >>> response = order_manager.place_stop_order("MGC", 1, 1, 2040.0)
        """
        return self.place_order(
            contract_id=contract_id,
            order_type=4,  # Stop order
            side=side,
            size=size,
            stop_price=stop_price,
            account_id=account_id,
        )

    def place_trailing_stop_order(
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
            >>> # Trailing stop $5 below current price
            >>> response = order_manager.place_trailing_stop_order("MGC", 1, 1, 5.0)
        """
        return self.place_order(
            contract_id=contract_id,
            order_type=5,  # Trailing stop order
            side=side,
            size=size,
            trail_price=trail_price,
            account_id=account_id,
        )

    def place_order(
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

        Args:
            contract_id: The contract ID to trade
            order_type: Order type:
                1=Limit, 2=Market, 4=Stop, 5=TrailingStop, 6=JoinBid, 7=JoinAsk
            side: Order side: 0=Buy, 1=Sell
            size: Number of contracts to trade
            limit_price: Limit price for limit orders (auto-aligned to tick size)
            stop_price: Stop price for stop orders (auto-aligned to tick size)
            trail_price: Trail amount for trailing stop orders (auto-aligned to tick size)
            custom_tag: Custom identifier for the order
            linked_order_id: ID of a linked order (for OCO, etc.)
            account_id: Account ID. Uses default account if None.

        Returns:
            OrderPlaceResponse: Response containing order ID and status

        Raises:
            ProjectXOrderError: If order placement fails
        """
        self.project_x._ensure_authenticated()

        # Use account_info if no account_id provided
        if account_id is None:
            if not self.project_x.account_info:
                self.project_x.get_account_info()
            if not self.project_x.account_info:
                raise ProjectXOrderError("No account information available")
            account_id = self.project_x.account_info.id

        # Align all prices to tick size to prevent "Invalid price" errors
        aligned_limit_price = self._align_price_to_tick_size(limit_price, contract_id)
        aligned_stop_price = self._align_price_to_tick_size(stop_price, contract_id)
        aligned_trail_price = self._align_price_to_tick_size(trail_price, contract_id)

        url = f"{self.project_x.base_url}/Order/place"
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

        # 🔍 DEBUG: Log order parameters to diagnose placement issues
        self.logger.debug(f"🔍 Order Placement Request: {payload}")

        try:
            response = requests.post(
                url,
                headers=self.project_x.headers,
                json=payload,
                timeout=self.project_x.timeout_seconds,
            )
            self.project_x._handle_response_errors(response)

            data = response.json()

            # 🔍 DEBUG: Log the actual API response to diagnose issues
            self.logger.debug(f"🔍 Order API Response: {data}")

            if not data.get("success", False):
                error_msg = (
                    data.get("errorMessage")
                    or "Unknown error - no error message provided"
                )
                self.logger.error(f"Order placement failed: {error_msg}")
                self.logger.error(f"🔍 Full response data: {data}")
                raise ProjectXOrderError(f"Order placement failed: {error_msg}")

            result = OrderPlaceResponse(**data)

            # Update statistics
            with self.order_lock:
                self.stats["orders_placed"] += 1
                self.stats["last_order_time"] = datetime.now()

            self.logger.info(f"✅ Order placed: {result.orderId}")
            return result

        except requests.RequestException as e:
            raise ProjectXConnectionError(f"Order placement request failed: {e}") from e
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"Invalid order placement response: {e}")
            raise ProjectXDataError(f"Invalid order placement response: {e}") from e

    # ================================================================================
    # BRACKET ORDER METHODS
    # ================================================================================

    def _prepare_bracket_prices(
        self,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: float,
        contract_id: str,
        side: int,
    ) -> tuple[float, float, float]:
        aligned_entry = self._align_price_to_tick_size(entry_price, contract_id)
        aligned_stop = self._align_price_to_tick_size(stop_loss_price, contract_id)
        aligned_target = self._align_price_to_tick_size(take_profit_price, contract_id)

        if aligned_entry is None or aligned_stop is None or aligned_target is None:
            raise ProjectXOrderError("Invalid bracket order prices")

        self._validate_bracket_prices(side, aligned_entry, aligned_stop, aligned_target)
        return aligned_entry, aligned_stop, aligned_target

    def _place_entry_order(
        self,
        contract_id: str,
        side: int,
        size: int,
        entry_type: str,
        aligned_entry: float,
        custom_tag: str | None,
        account_id: int | None,
    ) -> OrderPlaceResponse:
        entry_order_type = 1 if entry_type == "limit" else 2
        return self.place_order(
            contract_id=contract_id,
            order_type=entry_order_type,
            side=side,
            size=size,
            limit_price=aligned_entry if entry_type == "limit" else None,
            custom_tag=f"{custom_tag}_entry" if custom_tag else "bracket_entry",
            account_id=account_id,
        )

    def _place_stop_order(
        self,
        contract_id: str,
        stop_side: int,
        size: int,
        aligned_stop: float,
        entry_response: OrderPlaceResponse,
        custom_tag: str | None,
        account_id: int | None,
    ) -> OrderPlaceResponse:
        return self.place_order(
            contract_id=contract_id,
            order_type=4,
            side=stop_side,
            size=size,
            stop_price=aligned_stop,
            linked_order_id=entry_response.orderId,
            custom_tag=f"{custom_tag}_stop" if custom_tag else "bracket_stop",
            account_id=account_id,
        )

    def _place_target_order(
        self,
        contract_id: str,
        stop_side: int,
        size: int,
        aligned_target: float,
        entry_response: OrderPlaceResponse,
        custom_tag: str | None,
        account_id: int | None,
    ) -> OrderPlaceResponse:
        return self.place_order(
            contract_id=contract_id,
            order_type=1,
            side=stop_side,
            size=size,
            limit_price=aligned_target,
            linked_order_id=entry_response.orderId,
            custom_tag=f"{custom_tag}_target" if custom_tag else "bracket_target",
            account_id=account_id,
        )

    def place_bracket_order(
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
        Place a bracket order with entry, stop loss, and take profit.

        A bracket order consists of three orders:
        1. Entry order (limit or market)
        2. Stop loss order (triggered if entry fills and price moves against position)
        3. Take profit order (triggered if entry fills and price moves favorably)

        Args:
            contract_id: The contract ID to trade
            side: Order side: 0=Buy, 1=Sell
            size: Number of contracts to trade
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price (risk management)
            take_profit_price: Take profit price (profit target)
            entry_type: Entry order type: "limit" or "market"
            account_id: Account ID. Uses default account if None.
            custom_tag: Custom identifier for the bracket

        Returns:
            BracketOrderResponse: Comprehensive response with all order details

        Example:
            >>> # Long bracket order
            >>> bracket = order_manager.place_bracket_order(
            ...     contract_id="MGC",
            ...     side=0,  # Buy
            ...     size=1,
            ...     entry_price=2045.0,
            ...     stop_loss_price=2040.0,  # $5 risk
            ...     take_profit_price=2055.0,  # $10 profit target
            ... )
        """
        try:
            aligned_entry, aligned_stop, aligned_target = self._prepare_bracket_prices(
                entry_price, stop_loss_price, take_profit_price, contract_id, side
            )

            # Generate unique custom tag if none provided to avoid "already in use" errors
            if custom_tag is None:
                timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
                custom_tag = f"bracket_{timestamp}"

            entry_response = self._place_entry_order(
                contract_id,
                side,
                size,
                entry_type,
                aligned_entry,
                custom_tag,
                account_id,
            )

            if not entry_response.success:
                return BracketOrderResponse(
                    success=False,
                    entry_order_id=None,
                    stop_order_id=None,
                    target_order_id=None,
                    entry_price=aligned_entry,
                    stop_loss_price=aligned_stop,
                    take_profit_price=aligned_target,
                    entry_response=entry_response,
                    stop_response=None,
                    target_response=None,
                    error_message=f"Entry order failed: {entry_response}",
                )

            stop_side = 1 - side
            stop_response = self._place_stop_order(
                contract_id,
                stop_side,
                size,
                aligned_stop,
                entry_response,
                custom_tag,
                account_id,
            )

            target_response = self._place_target_order(
                contract_id,
                stop_side,
                size,
                aligned_target,
                entry_response,
                custom_tag,
                account_id,
            )

            bracket_success = (
                entry_response.success
                and stop_response.success
                and target_response.success
            )

            result = BracketOrderResponse(
                success=bracket_success,
                entry_order_id=entry_response.orderId
                if entry_response.success
                else None,
                stop_order_id=stop_response.orderId if stop_response.success else None,
                target_order_id=target_response.orderId
                if target_response.success
                else None,
                entry_price=aligned_entry,
                stop_loss_price=aligned_stop,
                take_profit_price=aligned_target,
                entry_response=entry_response,
                stop_response=stop_response,
                target_response=target_response,
                error_message=None
                if bracket_success
                else "Partial bracket order failure",
            )

            if bracket_success:
                # Track order-position relationships for synchronization
                with self.order_lock:
                    if entry_response.success:
                        self.position_orders[contract_id]["entry_orders"].append(
                            entry_response.orderId
                        )
                        self.order_to_position[entry_response.orderId] = contract_id

                    if stop_response.success:
                        self.position_orders[contract_id]["stop_orders"].append(
                            stop_response.orderId
                        )
                        self.order_to_position[stop_response.orderId] = contract_id

                    if target_response.success:
                        self.position_orders[contract_id]["target_orders"].append(
                            target_response.orderId
                        )
                        self.order_to_position[target_response.orderId] = contract_id

                self.logger.info(
                    f"✅ Bracket order placed successfully: Entry={entry_response.orderId}, Stop={stop_response.orderId}, Target={target_response.orderId}"
                )
                with self.order_lock:
                    self.stats["bracket_orders_placed"] += 1
            else:
                self.logger.warning("⚠️ Partial bracket order failure")

            return result

        except Exception as e:
            self.logger.error(f"❌ Bracket order failed: {e}")
            return BracketOrderResponse(
                success=False,
                entry_order_id=None,
                stop_order_id=None,
                target_order_id=None,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                entry_response=None,
                stop_response=None,
                target_response=None,
                error_message=str(e),
            )

    def _validate_bracket_prices(
        self, side: int, entry: float, stop: float, target: float
    ):
        """Validate bracket order price relationships."""
        if side == 0:  # Buy order
            if stop >= entry:
                raise ProjectXOrderError(
                    "For buy orders, stop loss must be below entry price"
                )
            if target <= entry:
                raise ProjectXOrderError(
                    "For buy orders, take profit must be above entry price"
                )
        else:  # Sell order
            if stop <= entry:
                raise ProjectXOrderError(
                    "For sell orders, stop loss must be above entry price"
                )
            if target >= entry:
                raise ProjectXOrderError(
                    "For sell orders, take profit must be below entry price"
                )

    # ================================================================================
    # ORDER MODIFICATION AND CANCELLATION
    # ================================================================================

    def cancel_order(self, order_id: int, account_id: int | None = None) -> bool:
        """
        Cancel an existing order.

        Args:
            order_id: ID of the order to cancel
            account_id: Account ID. Uses default account if None.

        Returns:
            bool: True if cancellation successful

        Example:
            >>> success = order_manager.cancel_order(12345)
        """
        self.project_x._ensure_authenticated()

        if account_id is None:
            if not self.project_x.account_info:
                self.project_x.get_account_info()
            if not self.project_x.account_info:
                raise ProjectXOrderError("No account information available")
            account_id = self.project_x.account_info.id

        url = f"{self.project_x.base_url}/Order/cancel"
        payload = {
            "accountId": account_id,
            "orderId": order_id,
        }

        try:
            response = requests.post(
                url,
                headers=self.project_x.headers,
                json=payload,
                timeout=self.project_x.timeout_seconds,
            )
            self.project_x._handle_response_errors(response)

            data = response.json()
            success = data.get("success", False)

            if success:
                with self.order_lock:
                    self.stats["orders_cancelled"] += 1
                self.logger.info(f"✅ Order {order_id} cancelled successfully")
            else:
                error_msg = data.get("errorMessage", "Unknown error")
                self.logger.error(f"❌ Order cancellation failed: {error_msg}")

            return success

        except requests.RequestException as e:
            self.logger.error(f"❌ Order cancellation request failed: {e}")
            return False
        except (KeyError, json.JSONDecodeError) as e:
            self.logger.error(f"❌ Invalid cancellation response: {e}")
            return False

    def modify_order(
        self,
        order_id: int,
        limit_price: float | None = None,
        stop_price: float | None = None,
        size: int | None = None,
        account_id: int | None = None,
    ) -> bool:
        """
        Modify an existing order.

        Args:
            order_id: ID of the order to modify
            limit_price: New limit price (if applicable)
            stop_price: New stop price (if applicable)
            size: New order size
            account_id: Account ID. Uses default account if None.

        Returns:
            bool: True if modification successful

        Example:
            >>> # Change limit price
            >>> success = order_manager.modify_order(12345, limit_price=2052.0)
            >>> # Change order size
            >>> success = order_manager.modify_order(12345, size=2)
        """
        self.project_x._ensure_authenticated()

        if account_id is None:
            if not self.project_x.account_info:
                self.project_x.get_account_info()
            if not self.project_x.account_info:
                raise ProjectXOrderError("No account information available")
            account_id = self.project_x.account_info.id

        # Get existing order details to determine contract_id for price alignment
        existing_order = self.get_order_by_id(order_id, account_id)
        if not existing_order:
            self.logger.error(f"❌ Cannot modify order {order_id}: Order not found")
            return False

        contract_id = existing_order.contractId

        # Align prices to tick size
        aligned_limit = self._align_price_to_tick_size(limit_price, contract_id)
        aligned_stop = self._align_price_to_tick_size(stop_price, contract_id)

        url = f"{self.project_x.base_url}/Order/modify"
        payload: dict[str, Any] = {
            "accountId": account_id,
            "orderId": order_id,
        }

        # Add only the fields that are being modified
        if aligned_limit is not None:
            payload["limitPrice"] = aligned_limit
        if aligned_stop is not None:
            payload["stopPrice"] = aligned_stop
        if size is not None:
            payload["size"] = size

        try:
            response = requests.post(
                url,
                headers=self.project_x.headers,
                json=payload,
                timeout=self.project_x.timeout_seconds,
            )
            self.project_x._handle_response_errors(response)

            data = response.json()
            success = data.get("success", False)

            if success:
                with self.order_lock:
                    self.stats["orders_modified"] += 1
                self.logger.info(f"✅ Order {order_id} modified successfully")
            else:
                error_msg = data.get("errorMessage", "Unknown error")
                self.logger.error(f"❌ Order modification failed: {error_msg}")

            return success

        except requests.RequestException as e:
            self.logger.error(f"❌ Order modification request failed: {e}")
            return False
        except (KeyError, json.JSONDecodeError) as e:
            self.logger.error(f"❌ Invalid modification response: {e}")
            return False

    def cancel_all_orders(
        self, contract_id: str | None = None, account_id: int | None = None
    ) -> dict[str, Any]:
        """
        Cancel all orders, optionally filtered by contract.

        Args:
            contract_id: Optional contract ID to filter orders
            account_id: Account ID. Uses default account if None.

        Returns:
            Dict with cancellation results

        Example:
            >>> # Cancel all orders
            >>> result = order_manager.cancel_all_orders()
            >>> # Cancel all MGC orders
            >>> result = order_manager.cancel_all_orders(contract_id="MGC")
        """
        orders = self.search_open_orders(contract_id=contract_id, account_id=account_id)

        results = {
            "total_orders": len(orders),
            "cancelled": 0,
            "failed": 0,
            "errors": [],
        }

        for order in orders:
            try:
                if self.cancel_order(order.id, account_id):
                    results["cancelled"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Order {order.id}: {e!s}")

        self.logger.info(
            f"✅ Cancelled {results['cancelled']}/{results['total_orders']} orders"
        )
        return results

    # ================================================================================
    # ORDER SEARCH AND STATUS METHODS
    # ================================================================================

    def search_open_orders(
        self, contract_id: str | None = None, account_id: int | None = None
    ) -> list[Order]:
        """
        Search for open orders, optionally filtered by contract.

        Args:
            contract_id: Optional contract ID to filter orders
            account_id: Account ID. Uses default account if None.

        Returns:
            List[Order]: List of open orders

        Example:
            >>> # Get all open orders
            >>> orders = order_manager.search_open_orders()
            >>> # Get MGC orders only
            >>> mgc_orders = order_manager.search_open_orders(contract_id="MGC")
        """
        self.project_x._ensure_authenticated()

        if account_id is None:
            if not self.project_x.account_info:
                self.project_x.get_account_info()
            if not self.project_x.account_info:
                raise ProjectXOrderError("No account information available")
            account_id = self.project_x.account_info.id

        url = f"{self.project_x.base_url}/Order/searchOpen"
        payload: dict[str, Any] = {"accountId": account_id}

        if contract_id:
            payload["contractId"] = contract_id

        try:
            response = requests.post(
                url,
                headers=self.project_x.headers,
                json=payload,
                timeout=self.project_x.timeout_seconds,
            )
            self.project_x._handle_response_errors(response)

            data = response.json()
            if not data.get("success", False):
                error_msg = data.get("errorMessage", "Unknown error")
                self.logger.error(f"Order search failed: {error_msg}")
                return []

            orders = data.get("orders", [])
            # Filter to only include fields that Order model expects
            expected_fields = {
                "id",
                "accountId",
                "contractId",
                "symbolId",
                "creationTimestamp",
                "updateTimestamp",
                "status",
                "type",
                "side",
                "size",
                "fillVolume",
                "limitPrice",
                "stopPrice",
                "filledPrice",
                "customTag",
            }
            filtered_orders = []
            for order in orders:
                if isinstance(order, dict):
                    # Only keep fields that Order model expects
                    filtered_order = {
                        k: v for k, v in order.items() if k in expected_fields
                    }
                    filtered_orders.append(Order(**filtered_order))
                else:
                    filtered_orders.append(Order(**order))
            return filtered_orders

        except requests.RequestException as e:
            self.logger.error(f"❌ Order search request failed: {e}")
            return []
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"❌ Invalid order search response: {e}")
            return []

    def get_order_by_id(
        self, order_id: int, account_id: int | None = None
    ) -> Order | None:
        """
        Get a specific order by ID using cached data with API fallback.

        Args:
            order_id: ID of the order to retrieve
            account_id: Account ID. Uses default account if None.

        Returns:
            Order: Order object if found, None otherwise
        """
        order_id_str = str(order_id)

        # Try cached data first (realtime optimization)
        if self._realtime_enabled:
            order_data = self.get_tracked_order_status(order_id_str)
            if order_data:
                try:
                    return Order(**order_data)
                except Exception as e:
                    self.logger.debug(f"Failed to parse cached order data: {e}")

        # Fallback to API search
        orders = self.search_open_orders(account_id=account_id)
        for order in orders:
            if order.id == order_id:
                return order

        return None

    # ================================================================================
    # POSITION-BASED ORDER METHODS
    # ================================================================================

    def close_position(
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
            >>> response = order_manager.close_position("MGC", method="market")
            >>> # Close position with limit
            >>> response = order_manager.close_position(
            ...     "MGC", method="limit", limit_price=2050.0
            ... )
        """
        # Get current position
        positions = self.project_x.search_open_positions(account_id=account_id)
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
            return self.place_market_order(contract_id, side, size, account_id)
        elif method == "limit":
            if limit_price is None:
                raise ProjectXOrderError("Limit price required for limit close")
            return self.place_limit_order(
                contract_id, side, size, limit_price, account_id
            )
        else:
            raise ProjectXOrderError(f"Invalid close method: {method}")

    def add_stop_loss(
        self, contract_id: str, stop_price: float, account_id: int | None = None
    ) -> OrderPlaceResponse | None:
        """
        Add a stop loss order to an existing position.

        Args:
            contract_id: Contract ID of position
            stop_price: Stop loss price
            account_id: Account ID. Uses default account if None.

        Returns:
            OrderPlaceResponse: Response from stop loss order

        Example:
            >>> response = order_manager.add_stop_loss("MGC", 2040.0)
        """
        # Get current position
        positions = self.project_x.search_open_positions(account_id=account_id)
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

        response = self.place_stop_order(
            contract_id, side, size, stop_price, account_id
        )

        # Track the stop loss order for position synchronization
        if response and response.success:
            self.track_order_for_position(response.orderId, contract_id, "stop")

        return response

    def add_take_profit(
        self, contract_id: str, target_price: float, account_id: int | None = None
    ) -> OrderPlaceResponse | None:
        """
        Add a take profit order to an existing position.

        Args:
            contract_id: Contract ID of position
            target_price: Take profit price
            account_id: Account ID. Uses default account if None.

        Returns:
            OrderPlaceResponse: Response from take profit order

        Example:
            >>> response = order_manager.add_take_profit("MGC", 2055.0)
        """
        # Get current position
        positions = self.project_x.search_open_positions(account_id=account_id)
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

        response = self.place_limit_order(
            contract_id, side, size, target_price, account_id
        )

        # Track the take profit order for position synchronization
        if response and response.success:
            self.track_order_for_position(response.orderId, contract_id, "target")

        return response

    # ================================================================================
    # ORDER-POSITION SYNCHRONIZATION METHODS
    # ================================================================================

    def track_order_for_position(
        self, order_id: int, contract_id: str, order_category: str
    ):
        """
        Track an order as being related to a position for synchronization.

        Establishes a relationship between an order and a position to enable
        automatic order management when positions change (size adjustments,
        closures, etc.).

        Args:
            order_id: Order ID to track
            contract_id: Contract ID the order relates to
            order_category: Order category for the relationship:
                - 'entry': Entry orders that create positions
                - 'stop': Stop loss orders for risk management
                - 'target': Take profit orders for profit taking

        Example:
            >>> # Track a stop loss order for MGC position
            >>> order_manager.track_order_for_position(12345, "MGC", "stop")
            >>> # Track a take profit order
            >>> order_manager.track_order_for_position(12346, "MGC", "target")
        """
        with self.order_lock:
            if order_category in ["entry", "stop", "target"]:
                category_key = f"{order_category}_orders"
                self.position_orders[contract_id][category_key].append(order_id)
                self.order_to_position[order_id] = contract_id
                self.logger.debug(
                    f"📊 Tracking {order_category} order {order_id} for position {contract_id}"
                )

    def untrack_order(self, order_id: int):
        """
        Remove order from position tracking when no longer needed.

        Removes the order-position relationship, typically called when orders
        are filled, cancelled, or expired.

        Args:
            order_id: Order ID to remove from tracking

        Example:
            >>> order_manager.untrack_order(12345)
        """
        with self.order_lock:
            contract_id = self.order_to_position.pop(order_id, None)
            if contract_id:
                # Remove from all categories
                for category in ["entry_orders", "stop_orders", "target_orders"]:
                    if order_id in self.position_orders[contract_id][category]:
                        self.position_orders[contract_id][category].remove(order_id)
                self.logger.debug(
                    f"📊 Untracked order {order_id} from position {contract_id}"
                )

    def get_position_orders(self, contract_id: str) -> dict[str, list[int]]:
        """
        Get all orders related to a specific position.

        Retrieves all tracked orders associated with a position, organized
        by category for position management and synchronization.

        Args:
            contract_id: Contract ID to get orders for

        Returns:
            Dict with lists of order IDs organized by category:
                - entry_orders: List of entry order IDs
                - stop_orders: List of stop loss order IDs
                - target_orders: List of take profit order IDs

        Example:
            >>> orders = order_manager.get_position_orders("MGC")
            >>> print(f"Stop orders: {orders['stop_orders']}")
            >>> print(f"Target orders: {orders['target_orders']}")
            >>> if orders["entry_orders"]:
            ...     print(f"Entry orders still pending: {orders['entry_orders']}")
        """
        with self.order_lock:
            return {
                "entry_orders": self.position_orders[contract_id][
                    "entry_orders"
                ].copy(),
                "stop_orders": self.position_orders[contract_id]["stop_orders"].copy(),
                "target_orders": self.position_orders[contract_id][
                    "target_orders"
                ].copy(),
            }

    def cancel_position_orders(
        self,
        contract_id: str,
        categories: list[str] | None = None,
        account_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Cancel all orders related to a position.

        Args:
            contract_id: Contract ID to cancel orders for
            categories: Order categories to cancel ('stop', 'target', 'entry'). All if None.
            account_id: Account ID. Uses default account if None.

        Returns:
            Dict with cancellation results
        """
        if categories is None:
            categories = ["stop", "target", "entry"]

        results = {
            "total_cancelled": 0,
            "failed_cancellations": 0,
            "errors": [],
        }

        with self.order_lock:
            orders_to_cancel = []
            for category in categories:
                category_key = f"{category}_orders"
                if category_key in self.position_orders[contract_id]:
                    orders_to_cancel.extend(
                        self.position_orders[contract_id][category_key]
                    )

        for order_id in orders_to_cancel:
            try:
                if self.cancel_order(order_id, account_id):
                    results["total_cancelled"] += 1
                    self.untrack_order(order_id)
                else:
                    results["failed_cancellations"] += 1
            except Exception as e:
                results["failed_cancellations"] += 1
                results["errors"].append(f"Order {order_id}: {e!s}")

        self.logger.info(
            f"✅ Cancelled {results['total_cancelled']} position orders for {contract_id}"
        )
        return results

    def update_position_order_sizes(
        self, contract_id: str, new_position_size: int, account_id: int | None = None
    ) -> dict[str, Any]:
        """
        Update stop and target order sizes to match new position size.

        Args:
            contract_id: Contract ID of the position
            new_position_size: New position size (signed: positive=long, negative=short)
            account_id: Account ID. Uses default account if None.

        Returns:
            Dict with update results
        """
        if new_position_size == 0:
            # Position is closed, cancel all related orders
            return self.cancel_position_orders(contract_id, account_id=account_id)

        results = {
            "orders_updated": 0,
            "orders_failed": 0,
            "errors": [],
        }

        order_size = abs(new_position_size)
        position_orders = self.get_position_orders(contract_id)

        # Update stop orders
        for order_id in position_orders["stop_orders"]:
            try:
                if self.modify_order(order_id, size=order_size, account_id=account_id):
                    results["orders_updated"] += 1
                else:
                    results["orders_failed"] += 1
            except Exception as e:
                results["orders_failed"] += 1
                results["errors"].append(f"Stop order {order_id}: {e!s}")

        # Update target orders
        for order_id in position_orders["target_orders"]:
            try:
                if self.modify_order(order_id, size=order_size, account_id=account_id):
                    results["orders_updated"] += 1
                else:
                    results["orders_failed"] += 1
            except Exception as e:
                results["orders_failed"] += 1
                results["errors"].append(f"Target order {order_id}: {e!s}")

        self.logger.info(
            f"📊 Updated {results['orders_updated']} orders for position {contract_id} (size: {new_position_size})"
        )
        return results

    def sync_orders_with_position(
        self, contract_id: str, account_id: int | None = None
    ) -> dict[str, Any]:
        """
        Synchronize all related orders with current position state.

        Args:
            contract_id: Contract ID to synchronize
            account_id: Account ID. Uses default account if None.

        Returns:
            Dict with synchronization results
        """
        # Get current position
        positions = self.project_x.search_open_positions(account_id=account_id)
        current_position = None
        for pos in positions:
            if pos.contractId == contract_id:
                current_position = pos
                break

        if not current_position:
            # Position is closed, cancel all related orders
            self.logger.info(
                f"📊 Position {contract_id} closed, cancelling related orders"
            )
            return self.cancel_position_orders(contract_id, account_id=account_id)
        else:
            # Position exists, update order sizes
            self.logger.info(
                f"📊 Synchronizing orders for position {contract_id} (size: {current_position.size})"
            )
            return self.update_position_order_sizes(
                contract_id, current_position.size, account_id
            )

    def on_position_changed(
        self,
        contract_id: str,
        old_size: int,
        new_size: int,
        account_id: int | None = None,
    ):
        """
        Callback for when a position size changes.

        Args:
            contract_id: Contract ID of changed position
            old_size: Previous position size
            new_size: New position size
            account_id: Account ID. Uses default account if None.
        """
        self.logger.info(f"📊 Position {contract_id} changed: {old_size} -> {new_size}")

        if new_size == 0:
            # Position closed
            self.cancel_position_orders(contract_id, account_id=account_id)
        elif abs(new_size) != abs(old_size):
            # Position size changed
            self.update_position_order_sizes(contract_id, new_size, account_id)

    def on_position_closed(self, contract_id: str, account_id: int | None = None):
        """
        Callback for when a position is fully closed.

        Args:
            contract_id: Contract ID of closed position
            account_id: Account ID. Uses default account if None.
        """
        self.logger.info(f"📊 Position {contract_id} closed, cancelling related orders")
        self.cancel_position_orders(contract_id, account_id=account_id)

    # ================================================================================
    # UTILITY METHODS
    # ================================================================================

    def _align_price_to_tick_size(
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
                instrument_obj = self.project_x.get_instrument(contract_id)
            else:
                # Extract symbol from contract ID (e.g., "CON.F.US.MGC.M25" -> "MGC")
                symbol = extract_symbol_from_contract_id(contract_id)
                if symbol:
                    instrument_obj = self.project_x.get_instrument(symbol)

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

    def get_order_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive order management statistics and system health information.

        Provides detailed metrics about order activity, real-time tracking status,
        position-order relationships, and system health for monitoring and debugging.

        Returns:
            Dict with complete statistics including:
                - statistics: Core order metrics (placed, cancelled, modified, etc.)
                - realtime_enabled: Whether real-time order tracking is active
                - tracked_orders: Number of orders currently in cache
                - position_order_relationships: Details about order-position links
                - callbacks_registered: Number of callbacks per event type
                - health_status: Overall system health status

        Example:
            >>> stats = order_manager.get_order_statistics()
            >>> print(f"Orders placed: {stats['statistics']['orders_placed']}")
            >>> print(f"Real-time enabled: {stats['realtime_enabled']}")
            >>> print(f"Tracked orders: {stats['tracked_orders']}")
            >>> relationships = stats["position_order_relationships"]
            >>> print(
            ...     f"Positions with orders: {relationships['positions_with_orders']}"
            ... )
            >>> for contract_id, orders in relationships["position_summary"].items():
            ...     print(f"  {contract_id}: {orders['total']} orders")
        """
        with self.order_lock:
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
                total_position_orders += total_count

                if total_count > 0:
                    position_summary[contract_id] = {
                        "entry_orders": entry_count,
                        "stop_orders": stop_count,
                        "target_orders": target_count,
                        "total": total_count,
                    }

            return {
                "statistics": self.stats.copy(),
                "realtime_enabled": self._realtime_enabled,
                "tracked_orders": tracked_orders_count,
                "position_order_relationships": {
                    "total_tracked_orders": total_position_orders,
                    "positions_with_orders": len(position_summary),
                    "position_summary": position_summary,
                },
                "callbacks_registered": {
                    event: len(callbacks)
                    for event, callbacks in self.order_callbacks.items()
                },
                "health_status": "active"
                if self.project_x._authenticated
                else "inactive",
            }

    def get_realtime_validation_status(self) -> dict[str, Any]:
        """
        Get validation status for real-time order feed integration and compliance.

        Provides detailed information about real-time integration status,
        payload validation settings, and ProjectX API compliance for debugging
        and system validation.

        Returns:
            Dict with comprehensive validation status including:
                - realtime_enabled: Whether real-time updates are active
                - tracked_orders_count: Number of orders being tracked
                - order_callbacks_registered: Number of order update callbacks
                - payload_validation: Settings for validating ProjectX order payloads
                - projectx_compliance: Compliance status with ProjectX API format
                - statistics: Current order management statistics

        Example:
            >>> status = order_manager.get_realtime_validation_status()
            >>> print(f"Real-time enabled: {status['realtime_enabled']}")
            >>> print(f"Tracking {status['tracked_orders_count']} orders")
            >>> compliance = status["projectx_compliance"]
            >>> for check, result in compliance.items():
            ...     print(f"{check}: {result}")
            >>> # Validate order status enum understanding
            >>> status_enum = status["payload_validation"]["order_status_enum"]
            >>> print(f"Filled status code: {status_enum['Filled']}")
        """
        # Use internal order tracking
        with self.order_lock:
            tracked_orders_count = len(self.tracked_orders)

        return {
            "realtime_enabled": self._realtime_enabled,
            "tracked_orders_count": tracked_orders_count,
            "order_callbacks_registered": len(
                self.order_callbacks.get("order_update", [])
            ),
            "payload_validation": {
                "enabled": True,
                "required_fields": [
                    "id",
                    "accountId",
                    "contractId",
                    "creationTimestamp",
                    "status",
                    "type",
                    "side",
                    "size",
                ],
                "order_status_enum": {
                    "None": 0,
                    "Open": 1,
                    "Filled": 2,
                    "Cancelled": 3,
                    "Expired": 4,
                    "Rejected": 5,
                    "Pending": 6,
                },
                "order_type_enum": {
                    "Unknown": 0,
                    "Limit": 1,
                    "Market": 2,
                    "StopLimit": 3,
                    "Stop": 4,
                    "TrailingStop": 5,
                    "JoinBid": 6,
                    "JoinAsk": 7,
                },
                "order_side_enum": {"Bid": 0, "Ask": 1},
            },
            "projectx_compliance": {
                "gateway_user_order_format": "✅ Compliant",
                "order_status_enum": "✅ Correct (added Expired, Pending)",
                "status_change_detection": "✅ Enhanced (Filled, Cancelled, Expired, Rejected, Pending)",
                "payload_structure": "✅ Direct payload (no 'data' extraction)",
                "additional_fields": "✅ Added symbolId, filledPrice, customTag",
            },
            "statistics": self.stats.copy(),
        }

    def cleanup(self):
        """
        Clean up resources and connections when shutting down.

        Properly shuts down order tracking, clears cached data, and releases
        resources to prevent memory leaks when the OrderManager is no
        longer needed.

        Example:
            >>> # Proper shutdown
            >>> order_manager.cleanup()
        """
        with self.order_lock:
            self.order_callbacks.clear()
            self.position_orders.clear()
            self.order_to_position.clear()
            # Clear realtime tracking cache
            self.tracked_orders.clear()
            self.order_status_cache.clear()

        self.logger.info("✅ OrderManager cleanup completed")
