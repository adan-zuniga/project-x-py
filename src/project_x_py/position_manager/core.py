"""
Core PositionManager class for comprehensive position operations.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides the main PositionManager class that handles all position-related
    operations including tracking, monitoring, analysis, and management.
    Integrates multiple mixins to provide comprehensive position lifecycle
    management with real-time capabilities and risk management.

Key Features:
    - Real-time position tracking via WebSocket integration
    - Portfolio-level position management and analytics
    - Automated P&L calculation and risk metrics
    - Position sizing and risk management tools
    - Event-driven position updates and closure detection
    - Async-safe operations for concurrent access
    - Comprehensive position operations (close, partial close)
    - Statistics, history, and report generation

Note:
    This class is the core implementation of the position manager. For most
    applications, it is recommended to interact with it through the `TradingSuite`
    (`suite.positions`), which handles its lifecycle and integration automatically.
    The example below demonstrates direct, low-level instantiation and usage.

Example Usage:
    ```python
    # V3: Initialize position manager with EventBus and real-time support
    import asyncio
    from project_x_py import ProjectX, create_realtime_client, EventBus
    from project_x_py.position_manager import PositionManager


    async def main():
        async with ProjectX.from_env() as client:
            await client.authenticate()

            # V3: Create dependencies
            event_bus = EventBus()
            realtime_client = await create_realtime_client(
                client.get_session_token(), str(client.get_account_info().id)
            )

            # V3: Initialize position manager
            pm = PositionManager(client, event_bus)
            await pm.initialize(realtime_client)

            # V3: Get current positions with detailed fields
            positions = await pm.get_all_positions()
            for pos in positions:
                print(f"{pos.contractId}: {pos.netPos} @ ${pos.buyAvgPrice}")

            # V3: Calculate P&L with market prices
            prices = {"MGC": 2050.0, "MNQ": 18500.0}
            pnl = await pm.calculate_portfolio_pnl(prices)
            print(f"Total P&L: ${pnl['total_pnl']:.2f}")

            # V3: Risk analysis
            risk = await pm.get_risk_metrics()
            print(f"Portfolio risk: {risk['portfolio_risk']:.2%}")

            # V3: Position operations
            await pm.close_position_direct("MGC")


    asyncio.run(main())
    ```

See Also:
    - `position_manager.analytics.PositionAnalyticsMixin`
    - `position_manager.risk.RiskManagementMixin`
    - `position_manager.monitoring.PositionMonitoringMixin`
    - `position_manager.operations.PositionOperationsMixin`
    - `position_manager.reporting.PositionReportingMixin`
    - `position_manager.tracking.PositionTrackingMixin`
"""

import asyncio
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
from project_x_py.types.config_types import PositionManagerConfig
from project_x_py.utils import (
    LogMessages,
    ProjectXLogger,
    handle_errors,
)

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
        - Real-time position tracking and monitoring via WebSocket
        - Portfolio-level position management and analytics
        - Automated P&L calculation and risk metrics
        - Position sizing and risk management tools
        - Event-driven position updates (closures detected from size=0)
        - Async-safe operations for concurrent access
        - Comprehensive position operations (close, partial close, bulk operations)
        - Statistics, history, and report generation

    Real-time Capabilities:
        - WebSocket-based position updates and closure detection
        - Immediate position change notifications
        - Event-driven callbacks for custom monitoring
        - Automatic position synchronization with order management

    Risk Management:
        - Portfolio risk assessment and concentration analysis
        - Position sizing calculations with configurable risk parameters
        - Risk warnings and threshold monitoring
        - Diversification scoring and portfolio health metrics

    Example Usage:
        >>> # V3: Create position manager with EventBus integration
        >>> event_bus = EventBus()
        >>> position_manager = PositionManager(project_x_client, event_bus)
        >>> # V3: Initialize with real-time client for WebSocket updates
        >>> realtime_client = await create_realtime_client(
        ...     client.get_session_token(), str(client.get_account_info().id)
        ... )
        >>> await position_manager.initialize(realtime_client=realtime_client)
        >>> # V3: Get current positions with actual field names
        >>> positions = await position_manager.get_all_positions()
        >>> mgc_position = await position_manager.get_position("MGC")
        >>> if mgc_position:
        >>>     print(f"Size: {mgc_position.netPos}")
        >>>     print(f"Avg Price: ${mgc_position.buyAvgPrice}")
        >>> # V3: Portfolio analytics with market prices
        >>> market_prices = {"MGC": 2050.0, "MNQ": 18500.0}
        >>> portfolio_pnl = await position_manager.calculate_portfolio_pnl(
        ...     market_prices
        ... )
        >>> risk_metrics = await position_manager.get_risk_metrics()
        >>> # V3: Position monitoring with alerts
        >>> await position_manager.add_position_alert("MGC", max_loss=-500.0)
        >>> await position_manager.start_monitoring(interval_seconds=5)
        >>> # V3: Position sizing with risk management
        >>> suggested_size = await position_manager.calculate_position_size(
        ...     "MGC", risk_amount=100.0, entry_price=2045.0, stop_price=2040.0
        ... )
    """

    def __init__(
        self,
        project_x_client: "ProjectXBase",
        event_bus: Any,
        config: PositionManagerConfig | None = None,
    ):
        """
        Initialize the PositionManager with an ProjectX client and optional configuration.

        Creates a comprehensive position management system with tracking, monitoring,
        alerts, risk management, and optional real-time/order synchronization.

        Args:
            project_x_client (ProjectX): The authenticated ProjectX client instance
                used for all API operations. Must be properly authenticated before use.
            event_bus: EventBus instance for unified event handling. Required for all
                event emissions including position updates, P&L changes, and risk alerts.
            config: Optional configuration for position management behavior. If not provided,
                default values will be used for all configuration options.

        Attributes:
            project_x (ProjectX): Reference to the ProjectX client
            logger (logging.Logger): Logger instance for this manager
            position_lock (asyncio.Lock): Thread-safe lock for position operations
            realtime_client (ProjectXRealtimeClient | None): Optional real-time client
            order_manager (OrderManager | None): Optional order manager for sync
            tracked_positions (dict[str, Position]): Current positions by contract ID
            position_history (dict[str, list[dict]]): Historical position changes
            event_bus (Any): EventBus instance for unified event handling
            position_alerts (dict[str, dict]): Active position alerts by contract
            stats (dict): Comprehensive tracking statistics
            risk_settings (dict): Risk management configuration

        Example:
            >>> # V3: Initialize with EventBus for unified event handling
            >>> async with ProjectX.from_env() as client:
            ...     await client.authenticate()
            ...     event_bus = EventBus()
            ...     position_manager = PositionManager(client, event_bus)
            ...
            ...     # V3: Optional - add order manager for synchronization
            ...     order_manager = OrderManager(client, event_bus)
            ...     await position_manager.initialize(
            ...         realtime_client=realtime_client, order_manager=order_manager
            ...     )
        """
        # Initialize all mixins
        PositionTrackingMixin.__init__(self)
        PositionMonitoringMixin.__init__(self)

        self.project_x = project_x_client
        self.event_bus = event_bus  # Store the event bus for emitting events
        self.logger = ProjectXLogger.get_logger(__name__)

        # Store configuration with defaults
        self.config = config or {}
        self._apply_config_defaults()

        # Async lock for thread safety
        self.position_lock = asyncio.Lock()

        # Real-time integration (optional)
        self.realtime_client: ProjectXRealtimeClient | None = None
        self._realtime_enabled = False

        # Order management integration (optional)
        self.order_manager: OrderManager | None = None
        self._order_sync_enabled = False

        # Comprehensive statistics tracking
        self.stats = {
            "open_positions": 0,
            "closed_positions": 0,
            "total_positions": 0,
            "total_pnl": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "best_position_pnl": 0.0,
            "worst_position_pnl": 0.0,
            "avg_position_size": 0.0,
            "largest_position": 0,
            "avg_hold_time_minutes": 0.0,
            "longest_hold_time_minutes": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_risk": 0.0,
            "max_position_risk": 0.0,
            "portfolio_correlation": 0.0,
            "var_95": 0.0,
            "position_updates": 0,
            "risk_calculations": 0,
            "last_position_update": None,
            # Legacy fields for backward compatibility in other methods
            "positions_tracked": 0,
            "positions_partially_closed": 0,
            "last_update_time": None,
            "monitoring_started": None,
        }

        self.logger.info(
            LogMessages.MANAGER_INITIALIZED, extra={"manager": "PositionManager"}
        )

    def _apply_config_defaults(self) -> None:
        """Apply default values for configuration options."""
        # Position management settings
        self.enable_risk_monitoring = self.config.get("enable_risk_monitoring", True)
        self.auto_stop_loss = self.config.get("auto_stop_loss", False)
        self.auto_take_profit = self.config.get("auto_take_profit", False)
        self.max_position_size = self.config.get("max_position_size", 100)
        self.max_portfolio_risk = self.config.get("max_portfolio_risk", 0.02)
        self.position_sizing_method = self.config.get("position_sizing_method", "fixed")
        self.enable_correlation_analysis = self.config.get(
            "enable_correlation_analysis", True
        )
        self.enable_portfolio_rebalancing = self.config.get(
            "enable_portfolio_rebalancing", False
        )
        self.rebalance_frequency_minutes = self.config.get(
            "rebalance_frequency_minutes", 60
        )
        self.risk_calculation_interval = self.config.get("risk_calculation_interval", 5)

        # Update risk settings from configuration
        self.risk_settings = {
            "max_portfolio_risk": self.max_portfolio_risk,
            "max_position_risk": self.config.get(
                "max_position_risk", 0.01
            ),  # 1% per position
            "max_correlation": self.config.get(
                "max_correlation", 0.7
            ),  # Maximum correlation between positions
            "alert_threshold": self.config.get(
                "alert_threshold", 0.005
            ),  # 0.5% threshold for alerts
        }

    @handle_errors("initialize position manager", reraise=False, default_return=False)
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
            >>> # V3: Initialize with real-time tracking
            >>> rt_client = await create_realtime_client(
            ...     client.get_session_token(), str(client.get_account_info().id)
            ... )
            >>> success = await position_manager.initialize(realtime_client=rt_client)
            >>>
            >>> # V3: Initialize with both real-time and order sync
            >>> event_bus = EventBus()
            >>> order_mgr = OrderManager(client, event_bus)
            >>> success = await position_manager.initialize(
            ...     realtime_client=rt_client, order_manager=order_mgr
            ... )

        Note:
            - Real-time mode provides instant position updates via WebSocket
            - Polling mode refreshes positions periodically (see start_monitoring)
            - Order synchronization helps maintain order/position consistency
        """
        # Set up real-time integration if provided
        if realtime_client:
            self.realtime_client = realtime_client
            await self._setup_realtime_callbacks()
            self._realtime_enabled = True
            self.logger.info(
                LogMessages.MANAGER_INITIALIZED,
                extra={"manager": "PositionManager", "mode": "realtime"},
            )
        else:
            self.logger.info(
                LogMessages.MANAGER_INITIALIZED,
                extra={"manager": "PositionManager", "mode": "polling"},
            )

        # Set up order management integration if provided
        if order_manager:
            self.order_manager = order_manager
            self._order_sync_enabled = True
            self.logger.info(
                LogMessages.MANAGER_INITIALIZED,
                extra={"feature": "order_synchronization", "enabled": True},
            )

        # Load initial positions
        await self.refresh_positions()

        return True

    # ================================================================================
    # CORE POSITION RETRIEVAL METHODS
    # ================================================================================

    @handle_errors("get all positions", reraise=False, default_return=[])
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
            >>> # V3: Get all positions with actual field names
            >>> positions = await position_manager.get_all_positions()
            >>> for pos in positions:
            ...     print(f"Contract: {pos.contractId}")
            ...     print(f"  Net Position: {pos.netPos}")
            ...     print(f"  Buy Avg Price: ${pos.buyAvgPrice:.2f}")
            ...     print(f"  Unrealized P&L: ${pos.unrealizedPnl:.2f}")
            >>> # V3: Get positions for specific account
            >>> positions = await position_manager.get_all_positions(account_id=12345)

        Note:
            In real-time mode, tracked positions are also updated via WebSocket,
            but this method always fetches fresh data from the API.
        """
        self.logger.info(LogMessages.POSITION_SEARCH, extra={"account_id": account_id})

        positions = await self.project_x.search_open_positions(account_id=account_id)

        # Update tracked positions
        async with self.position_lock:
            for position in positions:
                self.tracked_positions[position.contractId] = position

            # Update statistics
            self.stats["positions_tracked"] = len(positions)
            self.stats["last_update_time"] = datetime.now()

        self.logger.info(
            LogMessages.POSITION_UPDATE, extra={"position_count": len(positions)}
        )

        return positions

    @handle_errors("get position", reraise=False, default_return=None)
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
            >>> # V3: Check if we have a Gold position
            >>> mgc_position = await position_manager.get_position("MGC")
            >>> if mgc_position:
            ...     print(f"MGC position: {mgc_position.netPos} contracts")
            ...     print(f"Buy Avg Price: ${mgc_position.buyAvgPrice:.2f}")
            ...     print(f"Sell Avg Price: ${mgc_position.sellAvgPrice:.2f}")
            ...     print(f"Unrealized P&L: ${mgc_position.unrealizedPnl:.2f}")
            ...     print(f"Realized P&L: ${mgc_position.realizedPnl:.2f}")
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

    @handle_errors("refresh positions", reraise=False, default_return=False)
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
        self.logger.info(LogMessages.POSITION_REFRESH, extra={"account_id": account_id})

        positions = await self.get_all_positions(account_id=account_id)

        self.logger.info(
            LogMessages.POSITION_UPDATE, extra={"refreshed_count": len(positions)}
        )

        return True

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
            # EventBus handles all callbacks now
            self.position_alerts.clear()

        # Clear order manager integration
        self.order_manager = None
        self._order_sync_enabled = False

        self.logger.info("✅ AsyncPositionManager cleanup completed")
