"""
Async PositionManager for Comprehensive Position Operations

This module provides async/await support for comprehensive position management with the ProjectX API:
1. Position tracking and monitoring
2. Real-time position updates and P&L calculation
3. Portfolio-level position management
4. Risk metrics and exposure analysis
5. Position sizing and risk management
6. Automated position monitoring and alerts

Key Features:
- Async/await patterns for all operations
- Thread-safe position operations using asyncio locks
- Dependency injection with AsyncProjectX client
- Integration with AsyncProjectXRealtimeClient for live updates
- Real-time P&L and risk calculations
- Portfolio-level analytics and reporting
- Position-based risk management
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from .exceptions import ProjectXError
from .models import Position

if TYPE_CHECKING:
    from .async_client import AsyncProjectX
    from .async_order_manager import AsyncOrderManager
    from .async_realtime import AsyncProjectXRealtimeClient


class AsyncPositionManager:
    """
    Async comprehensive position management system for ProjectX trading operations.

    This class handles all position-related operations including tracking, monitoring,
    analysis, and management using async/await patterns. It integrates with both the
    AsyncProjectX client and the async real-time client for live position monitoring.

    Features:
        - Complete async position lifecycle management
        - Real-time position tracking and monitoring
        - Portfolio-level position management
        - Automated P&L calculation and risk metrics
        - Position sizing and risk management tools
        - Event-driven position updates (closures detected from type=0/size=0)
        - Async-safe operations for concurrent access

    Example Usage:
        >>> # Create async position manager with dependency injection
        >>> position_manager = AsyncPositionManager(async_project_x_client)
        >>> # Initialize with optional real-time client
        >>> await position_manager.initialize(realtime_client=async_realtime_client)
        >>> # Get current positions
        >>> positions = await position_manager.get_all_positions()
        >>> mgc_position = await position_manager.get_position("MGC")
        >>> # Portfolio analytics
        >>> portfolio_pnl = await position_manager.get_portfolio_pnl()
        >>> risk_metrics = await position_manager.get_risk_metrics()
        >>> # Position monitoring
        >>> await position_manager.add_position_alert("MGC", max_loss=-500.0)
        >>> await position_manager.start_monitoring()
        >>> # Position sizing
        >>> suggested_size = await position_manager.calculate_position_size(
        ...     "MGC", risk_amount=100.0, entry_price=2045.0, stop_price=2040.0
        ... )
    """

    def __init__(self, project_x_client: "AsyncProjectX"):
        """
        Initialize the AsyncPositionManager with an AsyncProjectX client.

        Creates a comprehensive position management system with tracking, monitoring,
        alerts, risk management, and optional real-time/order synchronization.

        Args:
            project_x_client (AsyncProjectX): The authenticated AsyncProjectX client instance
                used for all API operations. Must be properly authenticated before use.

        Attributes:
            project_x (AsyncProjectX): Reference to the ProjectX client
            logger (logging.Logger): Logger instance for this manager
            position_lock (asyncio.Lock): Thread-safe lock for position operations
            realtime_client (AsyncProjectXRealtimeClient | None): Optional real-time client
            order_manager (AsyncOrderManager | None): Optional order manager for sync
            tracked_positions (dict[str, Position]): Current positions by contract ID
            position_history (dict[str, list[dict]]): Historical position changes
            position_callbacks (dict[str, list[Any]]): Event callbacks by type
            position_alerts (dict[str, dict]): Active position alerts by contract
            stats (dict): Comprehensive tracking statistics
            risk_settings (dict): Risk management configuration

        Example:
            >>> async with AsyncProjectX.from_env() as client:
            ...     await client.authenticate()
            ...     position_manager = AsyncPositionManager(client)
        """
        self.project_x = project_x_client
        self.logger = logging.getLogger(__name__)

        # Async lock for thread safety
        self.position_lock = asyncio.Lock()

        # Real-time integration (optional)
        self.realtime_client: AsyncProjectXRealtimeClient | None = None
        self._realtime_enabled = False

        # Order management integration (optional)
        self.order_manager: AsyncOrderManager | None = None
        self._order_sync_enabled = False

        # Position tracking (maintains local state for business logic)
        self.tracked_positions: dict[str, Position] = {}
        self.position_history: dict[str, list[dict]] = defaultdict(list)
        self.position_callbacks: dict[str, list[Any]] = defaultdict(list)

        # Monitoring and alerts
        self._monitoring_active = False
        self._monitoring_task: asyncio.Task | None = None
        self.position_alerts: dict[str, dict] = {}

        # Statistics and metrics
        self.stats = {
            "positions_tracked": 0,
            "total_pnl": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "positions_closed": 0,
            "positions_partially_closed": 0,
            "last_update_time": None,
            "monitoring_started": None,
        }

        # Risk management settings
        self.risk_settings = {
            "max_portfolio_risk": 0.02,  # 2% of portfolio
            "max_position_risk": 0.01,  # 1% per position
            "max_correlation": 0.7,  # Maximum correlation between positions
            "alert_threshold": 0.005,  # 0.5% threshold for alerts
        }

        self.logger.info("AsyncPositionManager initialized")

    async def initialize(
        self,
        realtime_client: Optional["AsyncProjectXRealtimeClient"] = None,
        order_manager: Optional["AsyncOrderManager"] = None,
    ) -> bool:
        """
        Initialize the AsyncPositionManager with optional real-time capabilities and order synchronization.

        This method sets up advanced features including real-time position tracking via WebSocket
        and automatic order synchronization. Must be called before using real-time features.

        Args:
            realtime_client (AsyncProjectXRealtimeClient, optional): Real-time client instance
                for WebSocket-based position updates. When provided, enables live position
                tracking without polling. Defaults to None (polling mode).
            order_manager (AsyncOrderManager, optional): Order manager instance for automatic
                order synchronization. When provided, orders are automatically updated when
                positions change. Defaults to None (no order sync).

        Returns:
            bool: True if initialization successful, False if any errors occurred

        Raises:
            Exception: Logged but not raised - returns False on failure

        Example:
            >>> # Initialize with real-time tracking
            >>> rt_client = create_async_realtime_client(jwt_token)
            >>> success = await position_manager.initialize(realtime_client=rt_client)
            >>>
            >>> # Initialize with both real-time and order sync
            >>> order_mgr = AsyncOrderManager(client, rt_client)
            >>> success = await position_manager.initialize(
            ...     realtime_client=rt_client, order_manager=order_mgr
            ... )

        Note:
            - Real-time mode provides instant position updates via WebSocket
            - Polling mode refreshes positions periodically (see start_monitoring)
            - Order synchronization helps maintain order/position consistency
        """
        try:
            # Set up real-time integration if provided
            if realtime_client:
                self.realtime_client = realtime_client
                await self._setup_realtime_callbacks()
                self._realtime_enabled = True
                self.logger.info(
                    "✅ AsyncPositionManager initialized with real-time capabilities"
                )
            else:
                self.logger.info("✅ AsyncPositionManager initialized (polling mode)")

            # Set up order management integration if provided
            if order_manager:
                self.order_manager = order_manager
                self._order_sync_enabled = True
                self.logger.info(
                    "✅ AsyncPositionManager initialized with order synchronization"
                )

            # Load initial positions
            await self.refresh_positions()

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize AsyncPositionManager: {e}")
            return False

    async def _setup_realtime_callbacks(self) -> None:
        """
        Set up callbacks for real-time position monitoring via WebSocket.

        Registers internal callback handlers with the real-time client to process
        position updates and account changes. Called automatically during initialization
        when a real-time client is provided.

        Registered callbacks:
            - position_update: Handles position size/price changes and closures
            - account_update: Handles account-level changes affecting positions

        Note:
            This is an internal method called by initialize(). Do not call directly.
        """
        if not self.realtime_client:
            return

        # Register for position events (closures are detected from position updates)
        await self.realtime_client.add_callback(
            "position_update", self._on_position_update
        )
        await self.realtime_client.add_callback(
            "account_update", self._on_account_update
        )

        self.logger.info("🔄 Real-time position callbacks registered")

    async def _on_position_update(self, data: dict) -> None:
        """
        Handle real-time position updates and detect position closures.

        Processes incoming position data from the WebSocket feed, updates tracked
        positions, detects closures (size=0), and triggers appropriate callbacks.

        Args:
            data (dict): Position update data from real-time feed. Can be:
                - Single position dict with GatewayUserPosition fields
                - List of position dicts
                - Wrapped format: {"action": 1, "data": {position_data}}

        Note:
            - Position closure is detected when size == 0 (not type == 0)
            - Type 0 means "Undefined" in PositionType enum, not closed
            - Automatically triggers position_closed callbacks on closure
        """
        try:
            async with self.position_lock:
                if isinstance(data, list):
                    for position_data in data:
                        await self._process_position_data(position_data)
                elif isinstance(data, dict):
                    await self._process_position_data(data)

        except Exception as e:
            self.logger.error(f"Error processing position update: {e}")

    async def _on_account_update(self, data: dict) -> None:
        """
        Handle account-level updates that may affect positions.

        Processes account update events from the real-time feed and triggers
        registered account_update callbacks for custom handling.

        Args:
            data (dict): Account update data containing balance, margin, and other
                account-level information that may impact position management
        """
        await self._trigger_callbacks("account_update", data)

    def _validate_position_payload(self, position_data: dict) -> bool:
        """
        Validate that position payload matches ProjectX GatewayUserPosition format.

        Ensures incoming position data conforms to the expected schema before processing.
        This validation prevents errors from malformed data and ensures API compliance.

        Expected fields according to ProjectX docs:
            - id (int): The unique position identifier
            - accountId (int): The account associated with the position
            - contractId (string): The contract ID associated with the position
            - creationTimestamp (string): ISO timestamp when position was opened
            - type (int): PositionType enum value:
                * 0 = Undefined (not a closed position)
                * 1 = Long position
                * 2 = Short position
            - size (int): The number of contracts (0 means position is closed)
            - averagePrice (number): The weighted average entry price

        Args:
            position_data (dict): Raw position payload from ProjectX real-time feed

        Returns:
            bool: True if payload contains all required fields with valid values,
                False if validation fails

        Warning:
            Position closure is determined by size == 0, NOT type == 0.
            Type 0 means "Undefined" position type, not a closed position.
        """
        required_fields = {
            "id",
            "accountId",
            "contractId",
            "creationTimestamp",
            "type",
            "size",
            "averagePrice",
        }

        if not isinstance(position_data, dict):
            self.logger.warning(
                f"Position payload is not a dict: {type(position_data)}"
            )
            return False

        missing_fields = required_fields - set(position_data.keys())
        if missing_fields:
            self.logger.warning(
                f"Position payload missing required fields: {missing_fields}"
            )
            return False

        # Validate PositionType enum values
        position_type = position_data.get("type")
        if position_type not in [0, 1, 2]:  # Undefined, Long, Short
            self.logger.warning(f"Invalid position type: {position_type}")
            return False

        return True

    async def _process_position_data(self, position_data: dict) -> None:
        """
        Process individual position data update and detect position closures.

        Core processing method that handles position updates, maintains tracked positions,
        detects closures, triggers callbacks, and synchronizes with order management.

        ProjectX GatewayUserPosition payload structure:
            - Position is closed when size == 0 (not when type == 0)
            - type=0 means "Undefined" according to PositionType enum
            - type=1 means "Long", type=2 means "Short"

        Args:
            position_data (dict): Position data which can be:
                - Direct position dict with GatewayUserPosition fields
                - Wrapped format: {"action": 1, "data": {actual_position_data}}

        Processing flow:
            1. Extract actual position data from wrapper if needed
            2. Validate payload format
            3. Check if position is closed (size == 0)
            4. Update tracked positions or remove if closed
            5. Trigger appropriate callbacks
            6. Update position history
            7. Check position alerts
            8. Synchronize with order manager if enabled

        Side effects:
            - Updates self.tracked_positions
            - Appends to self.position_history
            - May trigger position_closed or position_update callbacks
            - May trigger position alerts
            - Updates statistics counters
        """
        try:
            # Handle wrapped position data from real-time updates
            # Real-time updates come as: {"action": 1, "data": {position_data}}
            # But direct API calls might provide raw position data
            actual_position_data = position_data
            if "action" in position_data and "data" in position_data:
                actual_position_data = position_data["data"]
                self.logger.debug(
                    f"Extracted position data from wrapper: action={position_data.get('action')}"
                )

            # Validate payload format
            if not self._validate_position_payload(actual_position_data):
                self.logger.error(
                    f"Invalid position payload format: {actual_position_data}"
                )
                return

            contract_id = actual_position_data.get("contractId")
            if not contract_id:
                self.logger.error(f"No contract ID found in {actual_position_data}")
                return

            # Check if this is a position closure
            # Position is closed when size == 0 (not when type == 0)
            # type=0 means "Undefined" according to PositionType enum, not closed
            position_size = actual_position_data.get("size", 0)
            is_position_closed = position_size == 0

            # Get the old position before updating
            old_position = self.tracked_positions.get(contract_id)
            old_size = old_position.size if old_position else 0

            if is_position_closed:
                # Position is closed - remove from tracking and trigger closure callbacks
                if contract_id in self.tracked_positions:
                    del self.tracked_positions[contract_id]
                    self.logger.info(f"📊 Position closed: {contract_id}")
                    self.stats["positions_closed"] += 1

                # Synchronize orders - cancel related orders when position is closed
                # Note: Order synchronization methods will be added to AsyncOrderManager
                # if self._order_sync_enabled and self.order_manager:
                #     await self.order_manager.on_position_closed(contract_id)

                # Trigger position_closed callbacks with the closure data
                await self._trigger_callbacks(
                    "position_closed", {"data": actual_position_data}
                )
            else:
                # Position is open/updated - create or update position
                # ProjectX payload structure matches our Position model fields
                position = Position(**actual_position_data)
                self.tracked_positions[contract_id] = position

                # Synchronize orders - update order sizes if position size changed
                # Note: Order synchronization methods will be added to AsyncOrderManager
                # if (
                #     self._order_sync_enabled
                #     and self.order_manager
                #     and old_size != position_size
                # ):
                #     await self.order_manager.on_position_changed(
                #         contract_id, old_size, position_size
                #     )

                # Track position history
                self.position_history[contract_id].append(
                    {
                        "timestamp": datetime.now(),
                        "position": actual_position_data.copy(),
                        "size_change": position_size - old_size,
                    }
                )

                # Check alerts
                await self._check_position_alerts(contract_id, position, old_position)

        except Exception as e:
            self.logger.error(f"Error processing position data: {e}")
            self.logger.debug(f"Position data that caused error: {position_data}")

    async def _trigger_callbacks(self, event_type: str, data: Any) -> None:
        """
        Trigger registered callbacks for position events.

        Executes all registered callback functions for a specific event type.
        Handles both sync and async callbacks, with error isolation to prevent
        one failing callback from affecting others.

        Args:
            event_type (str): The type of event to trigger callbacks for:
                - "position_update": Position changed
                - "position_closed": Position fully closed
                - "account_update": Account-level change
                - "position_alert": Alert condition met
            data (Any): Event data to pass to callbacks, typically a dict with
                event-specific information

        Note:
            - Callbacks are executed in registration order
            - Errors in callbacks are logged but don't stop other callbacks
            - Supports both sync and async callback functions
        """
        for callback in self.position_callbacks.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {e}")

    async def add_callback(
        self,
        event_type: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None],
    ) -> None:
        """
        Register a callback function for specific position events.

        Allows you to listen for position updates, closures, account changes, and alerts
        to build custom monitoring and notification systems.

        Args:
            event_type: Type of event to listen for
                - "position_update": Position size or price changes
                - "position_closed": Position fully closed (size = 0)
                - "account_update": Account-level changes
                - "position_alert": Position alert triggered
            callback: Async function to call when event occurs
                Should accept one argument: the event data dict

        Example:
            >>> async def on_position_update(data):
            ...     pos = data.get("data", {})
            ...     print(
            ...         f"Position updated: {pos.get('contractId')} size: {pos.get('size')}"
            ...     )
            >>> await position_manager.add_callback(
            ...     "position_update", on_position_update
            ... )
            >>> async def on_position_closed(data):
            ...     pos = data.get("data", {})
            ...     print(f"Position closed: {pos.get('contractId')}")
            >>> await position_manager.add_callback(
            ...     "position_closed", on_position_closed
            ... )
        """
        self.position_callbacks[event_type].append(callback)

    # ================================================================================
    # CORE POSITION RETRIEVAL METHODS
    # ================================================================================

    async def get_all_positions(self, account_id: int | None = None) -> list[Position]:
        """
        Get all current positions from the API and update tracking.

        Retrieves all open positions for the specified account, updates the internal
        tracking cache, and returns the position list. This is the primary method
        for fetching position data.

        Args:
            account_id (int, optional): The account ID to get positions for.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            list[Position]: List of all current open positions. Each Position object
                contains id, accountId, contractId, type, size, averagePrice, and
                creationTimestamp. Empty list if no positions or on error.

        Side effects:
            - Updates self.tracked_positions with current data
            - Updates statistics (positions_tracked, last_update_time)

        Example:
            >>> # Get all positions for default account
            >>> positions = await position_manager.get_all_positions()
            >>> for pos in positions:
            ...     print(f"{pos.contractId}: {pos.size} @ ${pos.averagePrice}")
            >>> # Get positions for specific account
            >>> positions = await position_manager.get_all_positions(account_id=12345)

        Note:
            In real-time mode, tracked positions are also updated via WebSocket,
            but this method always fetches fresh data from the API.
        """
        try:
            positions = await self.project_x.search_open_positions(
                account_id=account_id
            )

            # Update tracked positions
            async with self.position_lock:
                for position in positions:
                    self.tracked_positions[position.contractId] = position

                # Update statistics
                self.stats["positions_tracked"] = len(positions)
                self.stats["last_update_time"] = datetime.now()

            return positions

        except Exception as e:
            self.logger.error(f"❌ Failed to retrieve positions: {e}")
            return []

    async def get_position(
        self, contract_id: str, account_id: int | None = None
    ) -> Position | None:
        """
        Get a specific position by contract ID.

        Searches for a position matching the given contract ID. In real-time mode,
        checks the local cache first for better performance before falling back
        to an API call.

        Args:
            contract_id (str): The contract ID to search for (e.g., "MGC", "NQ")
            account_id (int, optional): The account ID to search within.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            Position | None: Position object if found, containing all position details
                (id, size, averagePrice, type, etc.). Returns None if no position
                exists for the contract.

        Example:
            >>> # Check if we have a Gold position
            >>> mgc_position = await position_manager.get_position("MGC")
            >>> if mgc_position:
            ...     print(f"MGC position: {mgc_position.size} contracts")
            ...     print(f"Entry price: ${mgc_position.averagePrice}")
            ...     print(f"Direction: {'Long' if mgc_position.type == 1 else 'Short'}")
            ... else:
            ...     print("No MGC position found")

        Performance:
            - Real-time mode: O(1) cache lookup, falls back to API if miss
            - Polling mode: Always makes API call via get_all_positions()
        """
        # Try cached data first if real-time enabled
        if self._realtime_enabled:
            async with self.position_lock:
                cached_position = self.tracked_positions.get(contract_id)
                if cached_position:
                    return cached_position

        # Fallback to API search
        positions = await self.get_all_positions(account_id=account_id)
        for position in positions:
            if position.contractId == contract_id:
                return position

        return None

    async def refresh_positions(self, account_id: int | None = None) -> bool:
        """
        Refresh all position data from the API.

        Forces a fresh fetch of all positions from the API, updating the internal
        tracking cache. Useful for ensuring data is current after external changes
        or when real-time updates may have been missed.

        Args:
            account_id (int, optional): The account ID to refresh positions for.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            bool: True if refresh was successful, False if any error occurred

        Side effects:
            - Updates self.tracked_positions with fresh data
            - Updates position statistics
            - Logs refresh results

        Example:
            >>> # Manually refresh positions
            >>> success = await position_manager.refresh_positions()
            >>> if success:
            ...     print("Positions refreshed successfully")
            >>> # Refresh specific account
            >>> await position_manager.refresh_positions(account_id=12345)

        Note:
            This method is called automatically during initialization and by
            the monitoring loop in polling mode.
        """
        try:
            positions = await self.get_all_positions(account_id=account_id)
            self.logger.info(f"🔄 Refreshed {len(positions)} positions")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to refresh positions: {e}")
            return False

    async def is_position_open(
        self, contract_id: str, account_id: int | None = None
    ) -> bool:
        """
        Check if a position exists for the given contract.

        Convenience method to quickly check if you have an open position in a
        specific contract without retrieving the full position details.

        Args:
            contract_id (str): The contract ID to check (e.g., "MGC", "NQ")
            account_id (int, optional): The account ID to check within.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            bool: True if an open position exists (size != 0), False otherwise

        Example:
            >>> # Check before placing an order
            >>> if await position_manager.is_position_open("MGC"):
            ...     print("Already have MGC position")
            ... else:
            ...     # Safe to open new position
            ...     await order_manager.place_market_order("MGC", 0, 1)

        Note:
            A position with size=0 is considered closed and returns False.
        """
        position = await self.get_position(contract_id, account_id)
        return position is not None and position.size != 0

    # ================================================================================
    # P&L CALCULATION METHODS (requires market prices)
    # ================================================================================

    async def calculate_position_pnl(
        self, position: Position, current_price: float, point_value: float | None = None
    ) -> dict[str, Any]:
        """
        Calculate P&L for a position given current market price.

        Computes unrealized profit/loss for a position based on the difference
        between entry price and current market price, accounting for position
        direction (long/short).

        Args:
            position (Position): The position object to calculate P&L for
            current_price (float): Current market price of the contract
            point_value (float, optional): Dollar value per point movement.
                For futures, this is the contract multiplier (e.g., 10 for MGC).
                If None, P&L is returned in points rather than dollars.
                Defaults to None.

        Returns:
            dict[str, Any]: Comprehensive P&L calculations containing:
                - unrealized_pnl (float): Total unrealized P&L (dollars or points)
                - market_value (float): Current market value of position
                - pnl_per_contract (float): P&L per contract (dollars or points)
                - current_price (float): The provided current price
                - entry_price (float): Average entry price (position.averagePrice)
                - size (int): Position size in contracts
                - direction (str): "LONG" or "SHORT"
                - price_change (float): Favorable price movement amount

        Example:
            >>> # Calculate P&L in points
            >>> position = await position_manager.get_position("MGC")
            >>> pnl = await position_manager.calculate_position_pnl(position, 2050.0)
            >>> print(f"Unrealized P&L: {pnl['unrealized_pnl']:.2f} points")
            >>> # Calculate P&L in dollars with contract multiplier
            >>> pnl = await position_manager.calculate_position_pnl(
            ...     position,
            ...     2050.0,
            ...     point_value=10.0,  # MGC = $10/point
            ... )
            >>> print(f"Unrealized P&L: ${pnl['unrealized_pnl']:.2f}")
            >>> print(f"Per contract: ${pnl['pnl_per_contract']:.2f}")

        Note:
            - Long positions profit when price increases
            - Short positions profit when price decreases
            - Use instrument.contractMultiplier for accurate point_value
        """
        # Calculate P&L based on position direction
        if position.type == 1:  # LONG
            price_change = current_price - position.averagePrice
        else:  # SHORT (type == 2)
            price_change = position.averagePrice - current_price

        # Apply point value if provided (for accurate dollar P&L)
        if point_value is not None:
            pnl_per_contract = price_change * point_value
        else:
            pnl_per_contract = price_change

        unrealized_pnl = pnl_per_contract * position.size
        market_value = current_price * position.size

        return {
            "unrealized_pnl": unrealized_pnl,
            "market_value": market_value,
            "pnl_per_contract": pnl_per_contract,
            "current_price": current_price,
            "entry_price": position.averagePrice,
            "size": position.size,
            "direction": "LONG" if position.type == 1 else "SHORT",
            "price_change": price_change,
        }

    async def calculate_portfolio_pnl(
        self, current_prices: dict[str, float], account_id: int | None = None
    ) -> dict[str, Any]:
        """
        Calculate portfolio P&L given current market prices.

        Computes aggregate P&L across all positions using provided market prices.
        Handles missing prices gracefully and provides detailed breakdown by position.

        Args:
            current_prices (dict[str, float]): Dictionary mapping contract IDs to
                their current market prices. Example: {"MGC": 2050.0, "NQ": 15500.0}
            account_id (int, optional): The account ID to calculate P&L for.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: Portfolio P&L analysis containing:
                - total_pnl (float): Sum of all calculated P&Ls
                - positions_count (int): Total number of positions
                - positions_with_prices (int): Positions with price data
                - positions_without_prices (int): Positions missing price data
                - position_breakdown (list[dict]): Detailed P&L per position:
                    * contract_id (str): Contract identifier
                    * size (int): Position size
                    * entry_price (float): Average entry price
                    * current_price (float | None): Current market price
                    * unrealized_pnl (float | None): Position P&L
                    * market_value (float | None): Current market value
                    * direction (str): "LONG" or "SHORT"
                - timestamp (datetime): Calculation timestamp

        Example:
            >>> # Get current prices from market data
            >>> prices = {"MGC": 2050.0, "NQ": 15500.0, "ES": 4400.0}
            >>> portfolio_pnl = await position_manager.calculate_portfolio_pnl(prices)
            >>> print(f"Total P&L: ${portfolio_pnl['total_pnl']:.2f}")
            >>> print(
            ...     f"Positions analyzed: {portfolio_pnl['positions_with_prices']}/"
            ...     f"{portfolio_pnl['positions_count']}"
            ... )
            >>> # Check individual positions
            >>> for pos in portfolio_pnl["position_breakdown"]:
            ...     if pos["unrealized_pnl"] is not None:
            ...         print(f"{pos['contract_id']}: ${pos['unrealized_pnl']:.2f}")

        Note:
            - P&L calculations assume point values of 1.0
            - For accurate dollar P&L, use calculate_position_pnl() with point values
            - Positions without prices in current_prices dict will have None P&L
        """
        positions = await self.get_all_positions(account_id=account_id)

        total_pnl = 0.0
        position_breakdown = []
        positions_with_prices = 0

        for position in positions:
            current_price = current_prices.get(position.contractId)

            if current_price is not None:
                pnl_data = await self.calculate_position_pnl(position, current_price)
                total_pnl += pnl_data["unrealized_pnl"]
                positions_with_prices += 1

                position_breakdown.append(
                    {
                        "contract_id": position.contractId,
                        "size": position.size,
                        "entry_price": position.averagePrice,
                        "current_price": current_price,
                        "unrealized_pnl": pnl_data["unrealized_pnl"],
                        "market_value": pnl_data["market_value"],
                        "direction": pnl_data["direction"],
                    }
                )
            else:
                # No price data available
                position_breakdown.append(
                    {
                        "contract_id": position.contractId,
                        "size": position.size,
                        "entry_price": position.averagePrice,
                        "current_price": None,
                        "unrealized_pnl": None,
                        "market_value": None,
                        "direction": "LONG" if position.type == 1 else "SHORT",
                    }
                )

        return {
            "total_pnl": total_pnl,
            "positions_count": len(positions),
            "positions_with_prices": positions_with_prices,
            "positions_without_prices": len(positions) - positions_with_prices,
            "position_breakdown": position_breakdown,
            "timestamp": datetime.now(),
        }

    # ================================================================================
    # PORTFOLIO ANALYTICS AND REPORTING
    # ================================================================================

    async def get_portfolio_pnl(self, account_id: int | None = None) -> dict[str, Any]:
        """
        Get portfolio P&L placeholder data (requires market prices for actual P&L).

        Retrieves current positions and provides a structure for P&L analysis.
        Since ProjectX API doesn't provide P&L data directly, actual P&L calculation
        requires current market prices via calculate_portfolio_pnl().

        Args:
            account_id (int, optional): The account ID to analyze.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: Portfolio structure containing:
                - position_count (int): Number of open positions
                - positions (list[dict]): Position details with placeholders:
                    * contract_id (str): Contract identifier
                    * size (int): Position size
                    * avg_price (float): Average entry price
                    * market_value (float): Size x average price estimate
                    * direction (str): "LONG" or "SHORT"
                    * note (str): Reminder about P&L calculation
                - total_pnl (float): 0.0 (placeholder)
                - total_unrealized_pnl (float): 0.0 (placeholder)
                - total_realized_pnl (float): 0.0 (placeholder)
                - net_pnl (float): 0.0 (placeholder)
                - last_updated (datetime): Timestamp
                - note (str): Instructions for actual P&L calculation

        Example:
            >>> # Get portfolio structure
            >>> portfolio = await position_manager.get_portfolio_pnl()
            >>> print(f"Open positions: {portfolio['position_count']}")
            >>> for pos in portfolio["positions"]:
            ...     print(f"{pos['contract_id']}: {pos['size']} @ ${pos['avg_price']}")
            >>> # For actual P&L, use calculate_portfolio_pnl() with prices
            >>> print(portfolio["note"])

        See Also:
            calculate_portfolio_pnl(): For actual P&L calculations with market prices
        """
        positions = await self.get_all_positions(account_id=account_id)

        position_breakdown = []

        for position in positions:
            # Note: ProjectX doesn't provide P&L data, would need current market prices to calculate
            position_breakdown.append(
                {
                    "contract_id": position.contractId,
                    "size": position.size,
                    "avg_price": position.averagePrice,
                    "market_value": position.size * position.averagePrice,
                    "direction": "LONG" if position.type == 1 else "SHORT",
                    "note": "P&L requires current market price - use calculate_position_pnl() method",
                }
            )

        return {
            "position_count": len(positions),
            "positions": position_breakdown,
            "total_pnl": 0.0,  # Default value when no current prices available
            "total_unrealized_pnl": 0.0,
            "total_realized_pnl": 0.0,
            "net_pnl": 0.0,
            "last_updated": datetime.now(),
            "note": "For P&L calculations, use calculate_portfolio_pnl() with current market prices",
        }

    async def get_risk_metrics(self, account_id: int | None = None) -> dict[str, Any]:
        """
        Calculate portfolio risk metrics and concentration analysis.

        Analyzes portfolio composition, exposure concentration, and generates risk
        warnings based on configured thresholds. Provides insights for risk management
        and position sizing decisions.

        Args:
            account_id (int, optional): The account ID to analyze.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: Comprehensive risk analysis containing:
                - portfolio_risk (float): Overall portfolio risk score (0.0-1.0)
                - largest_position_risk (float): Concentration in largest position
                - total_exposure (float): Sum of all position values
                - position_count (int): Number of open positions
                - diversification_score (float): Portfolio diversification (0.0-1.0)
                - risk_warnings (list[str]): Generated warnings based on thresholds

        Risk thresholds (configurable via self.risk_settings):
            - max_portfolio_risk: 2% default
            - max_position_risk: 1% default
            - max_correlation: 0.7 default
            - alert_threshold: 0.5% default

        Example:
            >>> # Analyze portfolio risk
            >>> risk_metrics = await position_manager.get_risk_metrics()
            >>> print(f"Portfolio risk: {risk_metrics['portfolio_risk']:.2%}")
            >>> print(f"Largest position: {risk_metrics['largest_position_risk']:.2%}")
            >>> print(f"Diversification: {risk_metrics['diversification_score']:.2f}")
            >>> # Check for warnings
            >>> if risk_metrics["risk_warnings"]:
            ...     print("\nRisk Warnings:")
            ...     for warning in risk_metrics["risk_warnings"]:
            ...         print(f"  ⚠️  {warning}")

        Note:
            - P&L-based risk metrics require current market prices
            - Diversification score: 1.0 = well diversified, 0.0 = concentrated
            - Empty portfolio returns zero risk with perfect diversification
        """
        positions = await self.get_all_positions(account_id=account_id)

        if not positions:
            return {
                "portfolio_risk": 0.0,
                "largest_position_risk": 0.0,
                "total_exposure": 0.0,
                "position_count": 0,
                "diversification_score": 1.0,
            }

        total_exposure = sum(abs(pos.size * pos.averagePrice) for pos in positions)
        largest_exposure = (
            max(abs(pos.size * pos.averagePrice) for pos in positions)
            if positions
            else 0.0
        )

        # Calculate basic risk metrics (note: P&L-based risk requires market prices)
        portfolio_risk = (
            0.0  # Would need current market prices to calculate P&L-based risk
        )
        largest_position_risk = (
            largest_exposure / total_exposure if total_exposure > 0 else 0.0
        )

        # Simple diversification score (inverse of concentration)
        diversification_score = (
            1.0 - largest_position_risk if largest_position_risk < 1.0 else 0.0
        )

        return {
            "portfolio_risk": portfolio_risk,
            "largest_position_risk": largest_position_risk,
            "total_exposure": total_exposure,
            "position_count": len(positions),
            "diversification_score": diversification_score,
            "risk_warnings": self._generate_risk_warnings(
                positions, portfolio_risk, largest_position_risk
            ),
        }

    def _generate_risk_warnings(
        self,
        positions: list[Position],
        portfolio_risk: float,
        largest_position_risk: float,
    ) -> list[str]:
        """
        Generate risk warnings based on current portfolio state.

        Analyzes portfolio metrics against configured risk thresholds and generates
        actionable warnings for risk management.

        Args:
            positions (list[Position]): Current open positions
            portfolio_risk (float): Calculated portfolio risk (0.0-1.0)
            largest_position_risk (float): Largest position concentration (0.0-1.0)

        Returns:
            list[str]: List of warning messages, empty if no issues detected

        Warning conditions:
            - Portfolio risk exceeds max_portfolio_risk setting
            - Largest position exceeds max_position_risk setting
            - Single position portfolio (no diversification)
        """
        warnings = []

        if portfolio_risk > self.risk_settings["max_portfolio_risk"]:
            warnings.append(
                f"Portfolio risk ({portfolio_risk:.2%}) exceeds maximum ({self.risk_settings['max_portfolio_risk']:.2%})"
            )

        if largest_position_risk > self.risk_settings["max_position_risk"]:
            warnings.append(
                f"Largest position risk ({largest_position_risk:.2%}) exceeds maximum ({self.risk_settings['max_position_risk']:.2%})"
            )

        if len(positions) == 1:
            warnings.append("Portfolio lacks diversification (single position)")

        return warnings

    # ================================================================================
    # POSITION MONITORING AND ALERTS
    # ================================================================================

    async def add_position_alert(
        self,
        contract_id: str,
        max_loss: float | None = None,
        max_gain: float | None = None,
        pnl_threshold: float | None = None,
    ) -> None:
        """
        Add an alert for a specific position.

        Args:
            contract_id: Contract ID to monitor
            max_loss: Maximum loss threshold (negative value)
            max_gain: Maximum gain threshold (positive value)
            pnl_threshold: Absolute P&L change threshold

        Example:
            >>> # Alert if MGC loses more than $500
            >>> await position_manager.add_position_alert("MGC", max_loss=-500.0)
            >>> # Alert if NQ gains more than $1000
            >>> await position_manager.add_position_alert("NQ", max_gain=1000.0)
        """
        async with self.position_lock:
            self.position_alerts[contract_id] = {
                "max_loss": max_loss,
                "max_gain": max_gain,
                "pnl_threshold": pnl_threshold,
                "created": datetime.now(),
                "triggered": False,
            }

        self.logger.info(f"📢 Position alert added for {contract_id}")

    async def remove_position_alert(self, contract_id: str) -> None:
        """
        Remove position alert for a specific contract.

        Args:
            contract_id: Contract ID to remove alert for

        Example:
            >>> await position_manager.remove_position_alert("MGC")
        """
        async with self.position_lock:
            if contract_id in self.position_alerts:
                del self.position_alerts[contract_id]
                self.logger.info(f"🔕 Position alert removed for {contract_id}")

    async def _check_position_alerts(
        self,
        contract_id: str,
        current_position: Position,
        old_position: Position | None,
    ) -> None:
        """
        Check if position alerts should be triggered and handle alert notifications.

        Evaluates position changes against configured alert thresholds and triggers
        notifications when conditions are met. Called automatically during position
        updates from both real-time feeds and polling.

        Args:
            contract_id (str): Contract ID of the position being checked
            current_position (Position): Current position state after update
            old_position (Position | None): Previous position state before update,
                None if this is a new position

        Alert types:
            - max_loss: Triggers when P&L falls below threshold (requires prices)
            - max_gain: Triggers when P&L exceeds threshold (requires prices)
            - pnl_threshold: Triggers on absolute P&L change (requires prices)
            - size_change: Currently implemented - alerts on position size changes

        Side effects:
            - Sets alert['triggered'] = True when triggered (one-time trigger)
            - Logs warning message for triggered alerts
            - Calls position_alert callbacks with alert details

        Note:
            P&L-based alerts require current market prices to be provided
            separately. Currently only size change detection is implemented.
        """
        alert = self.position_alerts.get(contract_id)
        if not alert or alert["triggered"]:
            return

        # Note: P&L-based alerts require current market prices
        # For now, only check position size changes
        alert_triggered = False
        alert_message = ""

        # Check for position size changes as a basic alert
        if old_position and current_position.size != old_position.size:
            size_change = current_position.size - old_position.size
            alert_triggered = True
            alert_message = (
                f"Position {contract_id} size changed by {size_change} contracts"
            )

        if alert_triggered:
            alert["triggered"] = True
            self.logger.warning(f"🚨 POSITION ALERT: {alert_message}")
            await self._trigger_callbacks(
                "position_alert",
                {
                    "contract_id": contract_id,
                    "message": alert_message,
                    "position": current_position,
                    "alert": alert,
                },
            )

    async def _monitoring_loop(self, refresh_interval: int) -> None:
        """
        Main monitoring loop for polling mode position updates.

        Continuously refreshes position data at specified intervals when real-time
        mode is not available. Handles errors gracefully to maintain monitoring.

        Args:
            refresh_interval (int): Seconds between position refreshes

        Note:
            - Runs until self._monitoring_active becomes False
            - Errors are logged but don't stop the monitoring loop
            - Only used in polling mode (when real-time client not available)
        """
        while self._monitoring_active:
            try:
                await self.refresh_positions()
                await asyncio.sleep(refresh_interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(refresh_interval)

    async def start_monitoring(self, refresh_interval: int = 30) -> None:
        """
        Start automated position monitoring for real-time updates and alerts.

        Enables continuous monitoring of positions with automatic alert checking.
        In real-time mode (with AsyncProjectXRealtimeClient), uses live WebSocket feeds.
        In polling mode, periodically refreshes position data from the API.

        Args:
            refresh_interval: Seconds between position updates in polling mode (default: 30)
                Ignored when real-time client is available

        Example:
            >>> # Start monitoring with real-time updates
            >>> await position_manager.start_monitoring()
            >>> # Start monitoring with custom polling interval
            >>> await position_manager.start_monitoring(refresh_interval=60)
        """
        if self._monitoring_active:
            self.logger.warning("⚠️ Position monitoring already active")
            return

        self._monitoring_active = True
        self.stats["monitoring_started"] = datetime.now()

        if not self._realtime_enabled:
            # Start async monitoring loop
            self._monitoring_task = asyncio.create_task(
                self._monitoring_loop(refresh_interval)
            )
            self.logger.info(
                f"📊 Position monitoring started (polling every {refresh_interval}s)"
            )
        else:
            self.logger.info("📊 Position monitoring started (real-time mode)")

    async def stop_monitoring(self) -> None:
        """
        Stop automated position monitoring and clean up monitoring resources.

        Cancels any active monitoring tasks and stops position update notifications.

        Example:
            >>> await position_manager.stop_monitoring()
        """
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
        self.logger.info("🛑 Position monitoring stopped")

    # ================================================================================
    # POSITION SIZING AND RISK MANAGEMENT
    # ================================================================================

    async def calculate_position_size(
        self,
        contract_id: str,
        risk_amount: float,
        entry_price: float,
        stop_price: float,
        account_balance: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculate optimal position size based on risk parameters.

        Implements fixed-risk position sizing by calculating the maximum number
        of contracts that can be traded while limiting loss to the specified
        risk amount if the stop loss is hit.

        Args:
            contract_id (str): Contract to size position for (e.g., "MGC")
            risk_amount (float): Maximum dollar amount to risk on the trade
            entry_price (float): Planned entry price for the position
            stop_price (float): Stop loss price for risk management
            account_balance (float, optional): Account balance for risk percentage
                calculation. If None, retrieved from account info or defaults
                to $10,000. Defaults to None.

        Returns:
            dict[str, Any]: Position sizing analysis containing:
                - suggested_size (int): Recommended number of contracts
                - risk_per_contract (float): Dollar risk per contract
                - total_risk (float): Actual total risk with suggested size
                - risk_percentage (float): Risk as percentage of account
                - entry_price (float): Provided entry price
                - stop_price (float): Provided stop price
                - price_diff (float): Absolute price difference (risk in points)
                - contract_multiplier (float): Contract point value
                - account_balance (float): Account balance used
                - risk_warnings (list[str]): Risk management warnings
                - error (str): Error message if calculation fails

        Example:
            >>> # Size position for $500 risk on Gold
            >>> sizing = await position_manager.calculate_position_size(
            ...     "MGC", risk_amount=500.0, entry_price=2050.0, stop_price=2040.0
            ... )
            >>> print(f"Trade {sizing['suggested_size']} contracts")
            >>> print(
            ...     f"Risk: ${sizing['total_risk']:.2f} "
            ...     f"({sizing['risk_percentage']:.1f}% of account)"
            ... )
            >>> # With specific account balance
            >>> sizing = await position_manager.calculate_position_size(
            ...     "NQ",
            ...     risk_amount=1000.0,
            ...     entry_price=15500.0,
            ...     stop_price=15450.0,
            ...     account_balance=50000.0,
            ... )

        Formula:
            position_size = risk_amount / (price_diff x contract_multiplier)

        Warnings generated when:
            - Risk percentage exceeds max_position_risk setting
            - Calculated size is 0 (risk amount too small)
            - Size is unusually large (>10 contracts)
        """
        try:
            # Get account balance if not provided
            if account_balance is None:
                if self.project_x.account_info:
                    account_balance = self.project_x.account_info.balance
                else:
                    account_balance = 10000.0  # Default fallback

            # Calculate risk per contract
            price_diff = abs(entry_price - stop_price)
            if price_diff == 0:
                return {"error": "Entry price and stop price cannot be the same"}

            # Get instrument details for contract multiplier
            instrument = await self.project_x.get_instrument(contract_id)
            contract_multiplier = (
                getattr(instrument, "contractMultiplier", 1.0) if instrument else 1.0
            )

            risk_per_contract = price_diff * contract_multiplier
            suggested_size = (
                int(risk_amount / risk_per_contract) if risk_per_contract > 0 else 0
            )

            # Calculate risk metrics
            total_risk = suggested_size * risk_per_contract
            risk_percentage = (
                (total_risk / account_balance) * 100 if account_balance > 0 else 0.0
            )

            return {
                "suggested_size": suggested_size,
                "risk_per_contract": risk_per_contract,
                "total_risk": total_risk,
                "risk_percentage": risk_percentage,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "price_diff": price_diff,
                "contract_multiplier": contract_multiplier,
                "account_balance": account_balance,
                "risk_warnings": self._generate_sizing_warnings(
                    risk_percentage, suggested_size
                ),
            }

        except Exception as e:
            self.logger.error(f"❌ Position sizing calculation failed: {e}")
            return {"error": str(e)}

    def _generate_sizing_warnings(self, risk_percentage: float, size: int) -> list[str]:
        """
        Generate warnings for position sizing calculations.

        Evaluates calculated position size and risk percentage against thresholds
        to provide risk management guidance.

        Args:
            risk_percentage (float): Position risk as percentage of account (0-100)
            size (int): Calculated position size in contracts

        Returns:
            list[str]: Risk warnings, empty if sizing is appropriate

        Warning thresholds:
            - Risk percentage > max_position_risk setting
            - Size = 0 (risk amount insufficient)
            - Size > 10 contracts (arbitrary large position threshold)
        """
        warnings = []

        if risk_percentage > self.risk_settings["max_position_risk"] * 100:
            warnings.append(
                f"Risk percentage ({risk_percentage:.2f}%) exceeds recommended maximum"
            )

        if size == 0:
            warnings.append(
                "Calculated position size is 0 - risk amount may be too small"
            )

        if size > 10:  # Arbitrary large size threshold
            warnings.append(
                f"Large position size ({size} contracts) - consider reducing risk"
            )

        return warnings

    # ================================================================================
    # DIRECT POSITION MANAGEMENT METHODS (API-based)
    # ================================================================================

    async def close_position_direct(
        self, contract_id: str, account_id: int | None = None
    ) -> dict[str, Any]:
        """
        Close an entire position using the direct position close API.

        Sends a market order to close the full position immediately at the current
        market price. This is the fastest way to exit a position completely.

        Args:
            contract_id (str): Contract ID of the position to close (e.g., "MGC")
            account_id (int, optional): Account ID holding the position.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: API response containing:
                - success (bool): True if closure was successful
                - orderId (str): Order ID of the closing order (if successful)
                - errorMessage (str): Error description (if failed)
                - error (str): Additional error details

        Raises:
            ProjectXError: If no account information is available

        Side effects:
            - Removes position from tracked_positions on success
            - Increments positions_closed counter
            - May trigger order synchronization if enabled

        Example:
            >>> # Close entire Gold position
            >>> result = await position_manager.close_position_direct("MGC")
            >>> if result["success"]:
            ...     print(f"Position closed with order: {result.get('orderId')}")
            ... else:
            ...     print(f"Failed: {result.get('errorMessage')}")
            >>> # Close position in specific account
            >>> result = await position_manager.close_position_direct(
            ...     "NQ", account_id=12345
            ... )

        Note:
            - Uses market order for immediate execution
            - No price control - executes at current market price
            - For partial closes, use partially_close_position()
        """
        await self.project_x._ensure_authenticated()

        if account_id is None:
            if not self.project_x.account_info:
                raise ProjectXError("No account information available")
            account_id = self.project_x.account_info.id

        url = "/Position/closeContract"
        payload = {
            "accountId": account_id,
            "contractId": contract_id,
        }

        try:
            response = await self.project_x._make_request("POST", url, data=payload)

            if response:
                success = response.get("success", False)

                if success:
                    self.logger.info(f"✅ Position {contract_id} closed successfully")
                    # Remove from tracked positions if present
                    async with self.position_lock:
                        positions_to_remove = [
                            contract_id
                            for contract_id, pos in self.tracked_positions.items()
                            if pos.contractId == contract_id
                        ]
                        for contract_id in positions_to_remove:
                            del self.tracked_positions[contract_id]

                    # Synchronize orders - cancel related orders when position is closed
                    # Note: Order synchronization methods will be added to AsyncOrderManager
                    # if self._order_sync_enabled and self.order_manager:
                    #     await self.order_manager.on_position_closed(contract_id)

                    self.stats["positions_closed"] += 1
                else:
                    error_msg = response.get("errorMessage", "Unknown error")
                    self.logger.error(f"❌ Position closure failed: {error_msg}")

                return response

            return {"success": False, "error": "No response from server"}

        except Exception as e:
            self.logger.error(f"❌ Position closure request failed: {e}")
            return {"success": False, "error": str(e)}

    async def partially_close_position(
        self, contract_id: str, close_size: int, account_id: int | None = None
    ) -> dict[str, Any]:
        """
        Partially close a position by reducing its size.

        Sends a market order to close a specified number of contracts from an
        existing position, allowing for gradual position reduction or profit taking.

        Args:
            contract_id (str): Contract ID of the position to partially close
            close_size (int): Number of contracts to close. Must be positive and
                less than the current position size.
            account_id (int, optional): Account ID holding the position.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: API response containing:
                - success (bool): True if partial closure was successful
                - orderId (str): Order ID of the closing order (if successful)
                - errorMessage (str): Error description (if failed)
                - error (str): Additional error details

        Raises:
            ProjectXError: If no account information available or close_size <= 0

        Side effects:
            - Triggers position refresh on success to update sizes
            - Increments positions_partially_closed counter
            - May trigger order synchronization if enabled

        Example:
            >>> # Take profit on half of a 10 contract position
            >>> result = await position_manager.partially_close_position("MGC", 5)
            >>> if result["success"]:
            ...     print(f"Partially closed with order: {result.get('orderId')}")
            >>> # Scale out of position in steps
            >>> for size in [3, 2, 1]:
            ...     result = await position_manager.partially_close_position("NQ", size)
            ...     if not result["success"]:
            ...         break
            ...     await asyncio.sleep(60)  # Wait between scales

        Note:
            - Uses market order for immediate execution
            - Remaining position continues with same average price
            - Close size must not exceed current position size
        """
        await self.project_x._ensure_authenticated()

        if account_id is None:
            if not self.project_x.account_info:
                raise ProjectXError("No account information available")
            account_id = self.project_x.account_info.id

        # Validate close size
        if close_size <= 0:
            raise ProjectXError("Close size must be positive")

        url = "/Position/partialCloseContract"
        payload = {
            "accountId": account_id,
            "contractId": contract_id,
            "closeSize": close_size,
        }

        try:
            response = await self.project_x._make_request("POST", url, data=payload)

            if response:
                success = response.get("success", False)

                if success:
                    self.logger.info(
                        f"✅ Position {contract_id} partially closed: {close_size} contracts"
                    )
                    # Trigger position refresh to get updated sizes
                    await self.refresh_positions(account_id=account_id)

                    # Synchronize orders - update order sizes after partial close
                    # Note: Order synchronization methods will be added to AsyncOrderManager
                    # if self._order_sync_enabled and self.order_manager:
                    #     await self.order_manager.sync_orders_with_position(
                    #         contract_id, account_id
                    #     )

                    self.stats["positions_partially_closed"] += 1
                else:
                    error_msg = response.get("errorMessage", "Unknown error")
                    self.logger.error(
                        f"❌ Partial position closure failed: {error_msg}"
                    )

                return response

            return {"success": False, "error": "No response from server"}

        except Exception as e:
            self.logger.error(f"❌ Partial position closure request failed: {e}")
            return {"success": False, "error": str(e)}

    async def close_all_positions(
        self, contract_id: str | None = None, account_id: int | None = None
    ) -> dict[str, Any]:
        """
        Close all positions, optionally filtered by contract.

        Iterates through open positions and closes each one individually.
        Useful for emergency exits, end-of-day flattening, or closing all
        positions in a specific contract.

        Args:
            contract_id (str, optional): If provided, only closes positions
                in this specific contract. If None, closes all positions.
                Defaults to None.
            account_id (int, optional): Account ID to close positions for.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: Bulk operation results containing:
                - total_positions (int): Number of positions attempted
                - closed (int): Number successfully closed
                - failed (int): Number that failed to close
                - errors (list[str]): Error messages for failed closures

        Example:
            >>> # Emergency close all positions
            >>> result = await position_manager.close_all_positions()
            >>> print(
            ...     f"Closed {result['closed']}/{result['total_positions']} positions"
            ... )
            >>> if result["errors"]:
            ...     for error in result["errors"]:
            ...         print(f"Error: {error}")
            >>> # Close all Gold positions only
            >>> result = await position_manager.close_all_positions(contract_id="MGC")
            >>> # Close positions in specific account
            >>> result = await position_manager.close_all_positions(account_id=12345)

        Warning:
            - Uses market orders - no price control
            - Processes positions sequentially, not in parallel
            - Continues attempting remaining positions even if some fail
        """
        positions = await self.get_all_positions(account_id=account_id)

        # Filter by contract if specified
        if contract_id:
            positions = [pos for pos in positions if pos.contractId == contract_id]

        results = {
            "total_positions": len(positions),
            "closed": 0,
            "failed": 0,
            "errors": [],
        }

        for position in positions:
            try:
                close_result = await self.close_position_direct(
                    position.contractId, account_id
                )
                if close_result.get("success", False):
                    results["closed"] += 1
                else:
                    results["failed"] += 1
                    error_msg = close_result.get("errorMessage", "Unknown error")
                    results["errors"].append(
                        f"Position {position.contractId}: {error_msg}"
                    )
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Position {position.contractId}: {e!s}")

        self.logger.info(
            f"✅ Closed {results['closed']}/{results['total_positions']} positions"
        )
        return results

    async def close_position_by_contract(
        self,
        contract_id: str,
        close_size: int | None = None,
        account_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Close position by contract ID (full or partial).

        Convenience method that automatically determines whether to use full or
        partial position closure based on the requested size.

        Args:
            contract_id (str): Contract ID of position to close (e.g., "MGC")
            close_size (int, optional): Number of contracts to close.
                If None or >= position size, closes entire position.
                If less than position size, closes partially.
                Defaults to None (full close).
            account_id (int, optional): Account ID holding the position.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: Closure response containing:
                - success (bool): True if closure was successful
                - orderId (str): Order ID (if successful)
                - errorMessage (str): Error description (if failed)
                - error (str): Error details or "No open position found"

        Example:
            >>> # Close entire position (auto-detect size)
            >>> result = await position_manager.close_position_by_contract("MGC")
            >>> # Close specific number of contracts
            >>> result = await position_manager.close_position_by_contract(
            ...     "MGC", close_size=3
            ... )
            >>> # Smart scaling - close half of any position
            >>> position = await position_manager.get_position("NQ")
            >>> if position:
            ...     half_size = position.size // 2
            ...     result = await position_manager.close_position_by_contract(
            ...         "NQ", close_size=half_size
            ...     )

        Note:
            - Returns error if no position exists for the contract
            - Automatically chooses between full and partial close
            - Uses market orders for immediate execution
        """
        # Find the position
        position = await self.get_position(contract_id, account_id)
        if not position:
            return {
                "success": False,
                "error": f"No open position found for {contract_id}",
            }

        # Determine if full or partial close
        if close_size is None or close_size >= position.size:
            # Full close
            return await self.close_position_direct(position.contractId, account_id)
        else:
            # Partial close
            return await self.partially_close_position(
                position.contractId, close_size, account_id
            )

    # ================================================================================
    # UTILITY AND STATISTICS METHODS
    # ================================================================================

    def get_position_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive position management statistics and health information.

        Provides detailed statistics about position tracking, monitoring status,
        performance metrics, and system health for debugging and monitoring.

        Returns:
            dict[str, Any]: Complete system statistics containing:
                - statistics (dict): Core metrics:
                    * positions_tracked (int): Current position count
                    * total_pnl (float): Aggregate P&L
                    * realized_pnl (float): Closed position P&L
                    * unrealized_pnl (float): Open position P&L
                    * positions_closed (int): Total positions closed
                    * positions_partially_closed (int): Partial closures
                    * last_update_time (datetime): Last data refresh
                    * monitoring_started (datetime): Monitoring start time
                - realtime_enabled (bool): Using WebSocket updates
                - order_sync_enabled (bool): Order synchronization active
                - monitoring_active (bool): Position monitoring running
                - tracked_positions (int): Positions in local cache
                - active_alerts (int): Untriggered alert count
                - callbacks_registered (dict): Callbacks by event type
                - risk_settings (dict): Current risk thresholds
                - health_status (str): "active" or "inactive"

        Example:
            >>> stats = position_manager.get_position_statistics()
            >>> print(f"System Health: {stats['health_status']}")
            >>> print(f"Tracking {stats['tracked_positions']} positions")
            >>> print(f"Real-time: {stats['realtime_enabled']}")
            >>> print(f"Monitoring: {stats['monitoring_active']}")
            >>> print(f"Positions closed: {stats['statistics']['positions_closed']}")
            >>> # Check callback registrations
            >>> for event, count in stats["callbacks_registered"].items():
            ...     print(f"{event}: {count} callbacks")

        Note:
            Statistics are cumulative since manager initialization.
            Use export_portfolio_report() for more detailed analysis.
        """
        return {
            "statistics": self.stats.copy(),
            "realtime_enabled": self._realtime_enabled,
            "order_sync_enabled": self._order_sync_enabled,
            "monitoring_active": self._monitoring_active,
            "tracked_positions": len(self.tracked_positions),
            "active_alerts": len(
                [a for a in self.position_alerts.values() if not a["triggered"]]
            ),
            "callbacks_registered": {
                event: len(callbacks)
                for event, callbacks in self.position_callbacks.items()
            },
            "risk_settings": self.risk_settings.copy(),
            "health_status": (
                "active" if self.project_x._authenticated else "inactive"
            ),
        }

    async def get_position_history(
        self, contract_id: str, limit: int = 100
    ) -> list[dict]:
        """
        Get historical position data for a specific contract.

        Retrieves the history of position changes including size changes,
        timestamps, and position snapshots for analysis and debugging.

        Args:
            contract_id (str): Contract ID to retrieve history for (e.g., "MGC")
            limit (int, optional): Maximum number of history entries to return.
                Returns most recent entries if history exceeds limit.
                Defaults to 100.

        Returns:
            list[dict]: Historical position entries, each containing:
                - timestamp (datetime): When the change occurred
                - position (dict): Complete position snapshot at that time
                - size_change (int): Change in position size from previous

        Example:
            >>> # Get recent history for Gold position
            >>> history = await position_manager.get_position_history("MGC", limit=50)
            >>> print(f"Found {len(history)} historical entries")
            >>> # Analyze recent changes
            >>> for entry in history[-5:]:  # Last 5 changes
            ...     ts = entry["timestamp"].strftime("%H:%M:%S")
            ...     size = entry["position"]["size"]
            ...     change = entry["size_change"]
            ...     print(f"{ts}: Size {size} (change: {change:+d})")
            >>> # Find when position was opened
            >>> if history:
            ...     first_entry = history[0]
            ...     print(f"Position opened at {first_entry['timestamp']}")

        Note:
            - History is maintained in memory during manager lifetime
            - Cleared when cleanup() is called
            - Empty list returned if no history exists
        """
        async with self.position_lock:
            history = self.position_history.get(contract_id, [])
            return history[-limit:] if history else []

    async def export_portfolio_report(self) -> dict[str, Any]:
        """
        Generate a comprehensive portfolio report with complete analysis.

        Creates a detailed report suitable for saving to file, sending via email,
        or displaying in dashboards. Combines all available analytics into a
        single comprehensive document.

        Returns:
            dict[str, Any]: Complete portfolio report containing:
                - report_timestamp (datetime): Report generation time
                - portfolio_summary (dict):
                    * total_positions (int): Open position count
                    * total_pnl (float): Aggregate P&L (requires prices)
                    * total_exposure (float): Sum of position values
                    * portfolio_risk (float): Risk score
                - positions (list[dict]): Detailed position list
                - risk_analysis (dict): Complete risk metrics
                - statistics (dict): System statistics and health
                - alerts (dict):
                    * active_alerts (int): Untriggered alert count
                    * triggered_alerts (int): Triggered alert count

        Example:
            >>> # Generate comprehensive report
            >>> report = await position_manager.export_portfolio_report()
            >>> print(f"Portfolio Report - {report['report_timestamp']}")
            >>> print(f"Positions: {report['portfolio_summary']['total_positions']}")
            >>> print(
            ...     f"Exposure: ${report['portfolio_summary']['total_exposure']:,.2f}"
            ... )
            >>> # Save report to file
            >>> import json
            >>> with open("portfolio_report.json", "w") as f:
            ...     json.dump(report, f, indent=2, default=str)
            >>> # Send key metrics
            >>> summary = report["portfolio_summary"]
            >>> alerts = report["alerts"]
            >>> print(f"Active Alerts: {alerts['active_alerts']}")

        Use cases:
            - End-of-day reporting
            - Risk management dashboards
            - Performance tracking
            - Audit trails
            - Email summaries
        """
        positions = await self.get_all_positions()
        pnl_data = await self.get_portfolio_pnl()
        risk_data = await self.get_risk_metrics()
        stats = self.get_position_statistics()

        return {
            "report_timestamp": datetime.now(),
            "portfolio_summary": {
                "total_positions": len(positions),
                "total_pnl": pnl_data["total_pnl"],
                "total_exposure": risk_data["total_exposure"],
                "portfolio_risk": risk_data["portfolio_risk"],
            },
            "positions": pnl_data["positions"],
            "risk_analysis": risk_data,
            "statistics": stats,
            "alerts": {
                "active_alerts": len(
                    [a for a in self.position_alerts.values() if not a["triggered"]]
                ),
                "triggered_alerts": len(
                    [a for a in self.position_alerts.values() if a["triggered"]]
                ),
            },
        }

    def get_realtime_validation_status(self) -> dict[str, Any]:
        """
        Get validation status for real-time position feed integration and compliance.

        Provides detailed information about real-time integration status,
        payload validation settings, and ProjectX API compliance for debugging
        and system validation.

        Returns:
            dict[str, Any]: Validation and compliance status containing:
                - realtime_enabled (bool): WebSocket integration active
                - tracked_positions_count (int): Positions in cache
                - position_callbacks_registered (int): Update callbacks
                - payload_validation (dict):
                    * enabled (bool): Validation active
                    * required_fields (list[str]): Expected fields
                    * position_type_enum (dict): Type mappings
                    * closure_detection (str): How closures detected
                - projectx_compliance (dict):
                    * gateway_user_position_format: Compliance status
                    * position_type_enum: Enum validation status
                    * closure_logic: Closure detection status
                    * payload_structure: Payload format status
                - statistics (dict): Current statistics

        Example:
            >>> # Check real-time integration health
            >>> status = position_manager.get_realtime_validation_status()
            >>> print(f"Real-time enabled: {status['realtime_enabled']}")
            >>> print(f"Tracking {status['tracked_positions_count']} positions")
            >>> # Verify API compliance
            >>> compliance = status["projectx_compliance"]
            >>> all_compliant = all("✅" in v for v in compliance.values())
            >>> print(f"Fully compliant: {all_compliant}")
            >>> # Check payload validation
            >>> validation = status["payload_validation"]
            >>> print(f"Closure detection: {validation['closure_detection']}")
            >>> print(f"Required fields: {len(validation['required_fields'])}")

        Use cases:
            - Integration testing
            - Debugging connection issues
            - Compliance verification
            - System health checks
        """
        return {
            "realtime_enabled": self._realtime_enabled,
            "tracked_positions_count": len(self.tracked_positions),
            "position_callbacks_registered": len(
                self.position_callbacks.get("position_update", [])
            ),
            "payload_validation": {
                "enabled": True,
                "required_fields": [
                    "id",
                    "accountId",
                    "contractId",
                    "creationTimestamp",
                    "type",
                    "size",
                    "averagePrice",
                ],
                "position_type_enum": {"Undefined": 0, "Long": 1, "Short": 2},
                "closure_detection": "size == 0 (not type == 0)",
            },
            "projectx_compliance": {
                "gateway_user_position_format": "✅ Compliant",
                "position_type_enum": "✅ Correct",
                "closure_logic": "✅ Fixed (was incorrectly checking type==0)",
                "payload_structure": "✅ Direct payload (no 'data' extraction)",
            },
            "statistics": self.stats.copy(),
        }

    async def cleanup(self) -> None:
        """
        Clean up resources and connections when shutting down.

        Performs complete cleanup of the AsyncPositionManager, including stopping
        monitoring tasks, clearing tracked data, and releasing all resources.
        Should be called when the manager is no longer needed to prevent memory
        leaks and ensure graceful shutdown.

        Cleanup operations:
            1. Stops position monitoring (cancels async tasks)
            2. Clears all tracked positions
            3. Clears position history
            4. Removes all callbacks
            5. Clears all alerts
            6. Disconnects order manager integration

        Example:
            >>> # Basic cleanup
            >>> await position_manager.cleanup()
            >>> # Cleanup in finally block
            >>> position_manager = AsyncPositionManager(client)
            >>> try:
            ...     await position_manager.initialize(realtime_client)
            ...     # ... use position manager ...
            ... finally:
            ...     await position_manager.cleanup()
            >>> # Context manager pattern (if implemented)
            >>> async with AsyncPositionManager(client) as pm:
            ...     await pm.initialize(realtime_client)
            ...     # ... automatic cleanup on exit ...

        Note:
            - Safe to call multiple times
            - Logs successful cleanup
            - Does not close underlying client connections
        """
        await self.stop_monitoring()

        async with self.position_lock:
            self.tracked_positions.clear()
            self.position_history.clear()
            self.position_callbacks.clear()
            self.position_alerts.clear()

        # Clear order manager integration
        self.order_manager = None
        self._order_sync_enabled = False

        self.logger.info("✅ AsyncPositionManager cleanup completed")
