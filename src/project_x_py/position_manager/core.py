"""
Core PositionManager class for comprehensive position operations.

This module provides the main PositionManager class that handles all position-related
operations including tracking, monitoring, analysis, and management.
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from project_x_py.client.base import ProjectXBase
from project_x_py.models import Position
from project_x_py.position_manager.analytics import PositionAnalyticsMixin
from project_x_py.position_manager.monitoring import PositionMonitoringMixin
from project_x_py.position_manager.operations import PositionOperationsMixin
from project_x_py.position_manager.reporting import PositionReportingMixin
from project_x_py.position_manager.risk import RiskManagementMixin
from project_x_py.position_manager.tracking import PositionTrackingMixin

if TYPE_CHECKING:
    from project_x_py.client import ProjectXBase
    from project_x_py.order_manager import OrderManager
    from project_x_py.realtime import ProjectXRealtimeClient


class PositionManager(
    PositionTrackingMixin,
    PositionAnalyticsMixin,
    RiskManagementMixin,
    PositionMonitoringMixin,
    PositionOperationsMixin,
    PositionReportingMixin,
):
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
        >>> position_manager = PositionManager(async_project_x_client)
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

    def __init__(self, project_x_client: "ProjectXBase"):
        """
        Initialize the PositionManager with an ProjectX client.

        Creates a comprehensive position management system with tracking, monitoring,
        alerts, risk management, and optional real-time/order synchronization.

        Args:
            project_x_client (ProjectX): The authenticated ProjectX client instance
                used for all API operations. Must be properly authenticated before use.

        Attributes:
            project_x (ProjectX): Reference to the ProjectX client
            logger (logging.Logger): Logger instance for this manager
            position_lock (asyncio.Lock): Thread-safe lock for position operations
            realtime_client (ProjectXRealtimeClient | None): Optional real-time client
            order_manager (OrderManager | None): Optional order manager for sync
            tracked_positions (dict[str, Position]): Current positions by contract ID
            position_history (dict[str, list[dict]]): Historical position changes
            position_callbacks (dict[str, list[Any]]): Event callbacks by type
            position_alerts (dict[str, dict]): Active position alerts by contract
            stats (dict): Comprehensive tracking statistics
            risk_settings (dict): Risk management configuration

        Example:
            >>> async with ProjectX.from_env() as client:
            ...     await client.authenticate()
            ...     position_manager = PositionManager(client)
        """
        # Initialize all mixins
        PositionTrackingMixin.__init__(self)
        PositionMonitoringMixin.__init__(self)

        self.project_x = project_x_client
        self.logger = logging.getLogger(__name__)

        # Async lock for thread safety
        self.position_lock = asyncio.Lock()

        # Real-time integration (optional)
        self.realtime_client: ProjectXRealtimeClient | None = None
        self._realtime_enabled = False

        # Order management integration (optional)
        self.order_manager: OrderManager | None = None
        self._order_sync_enabled = False

        # Statistics and metrics
        self.stats: dict[str, Any] = {
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

        self.logger.info("PositionManager initialized")

    async def initialize(
        self,
        realtime_client: Optional["ProjectXRealtimeClient"] = None,
        order_manager: Optional["OrderManager"] = None,
    ) -> bool:
        """
        Initialize the PositionManager with optional real-time capabilities and order synchronization.

        This method sets up advanced features including real-time position tracking via WebSocket
        and automatic order synchronization. Must be called before using real-time features.

        Args:
            realtime_client (ProjectXRealtimeClient, optional): Real-time client instance
                for WebSocket-based position updates. When provided, enables live position
                tracking without polling. Defaults to None (polling mode).
            order_manager (OrderManager, optional): Order manager instance for automatic
                order synchronization. When provided, orders are automatically updated when
                positions change. Defaults to None (no order sync).

        Returns:
            bool: True if initialization successful, False if any errors occurred

        Raises:
            Exception: Logged but not raised - returns False on failure

        Example:
            >>> # Initialize with real-time tracking
            >>> rt_client = create_realtime_client(jwt_token)
            >>> success = await position_manager.initialize(realtime_client=rt_client)
            >>>
            >>> # Initialize with both real-time and order sync
            >>> order_mgr = OrderManager(client, rt_client)
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
                    "✅ PositionManager initialized with real-time capabilities"
                )
            else:
                self.logger.info("✅ PositionManager initialized (polling mode)")

            # Set up order management integration if provided
            if order_manager:
                self.order_manager = order_manager
                self._order_sync_enabled = True
                self.logger.info(
                    "✅ PositionManager initialized with order synchronization"
                )

            # Load initial positions
            await self.refresh_positions()

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize PositionManager: {e}")
            return False

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
