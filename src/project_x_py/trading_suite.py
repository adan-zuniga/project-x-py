"""
Unified TradingSuite class for simplified SDK initialization and management.

Author: @TexasCoding
Date: 2025-08-04

Overview:
    Provides a single, intuitive entry point for creating a complete trading
    environment with all components properly configured and connected. This
    replaces the complex factory functions with a clean, simple API.

Key Features:
    - Single-line initialization with sensible defaults
    - Automatic component wiring and dependency injection
    - Built-in connection management and error recovery
    - Feature flags for optional components
    - Configuration file and environment variable support

Example Usage:
    ```python
    # Simple one-liner with defaults
    suite = await TradingSuite.create("MNQ")

    # With specific configuration
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min", "15min"],
        features=["orderbook", "risk_manager"],
    )

    # From configuration file
    suite = await TradingSuite.from_config("config/trading.yaml")
    ```
"""

from contextlib import AbstractAsyncContextManager
from datetime import datetime
from enum import Enum
from pathlib import Path
from types import TracebackType
from typing import Any

import orjson
import yaml

from project_x_py.client import ProjectX
from project_x_py.client.base import ProjectXBase
from project_x_py.event_bus import EventBus, EventType
from project_x_py.models import Instrument
from project_x_py.order_manager import OrderManager
from project_x_py.order_tracker import OrderChainBuilder, OrderTracker
from project_x_py.orderbook import OrderBook
from project_x_py.position_manager import PositionManager
from project_x_py.realtime import ProjectXRealtimeClient
from project_x_py.realtime_data_manager import RealtimeDataManager
from project_x_py.risk_manager import ManagedTrade, RiskConfig, RiskManager
from project_x_py.types.config_types import (
    DataManagerConfig,
    OrderbookConfig,
    OrderManagerConfig,
    PositionManagerConfig,
)
from project_x_py.types.stats_types import ComponentStats, TradingSuiteStats
from project_x_py.utils import ProjectXLogger

logger = ProjectXLogger.get_logger(__name__)


class Features(str, Enum):
    """Available feature flags for TradingSuite."""

    ORDERBOOK = "orderbook"
    RISK_MANAGER = "risk_manager"
    TRADE_JOURNAL = "trade_journal"
    PERFORMANCE_ANALYTICS = "performance_analytics"
    AUTO_RECONNECT = "auto_reconnect"


class TradingSuiteConfig:
    """Configuration for TradingSuite initialization."""

    def __init__(
        self,
        instrument: str,
        timeframes: list[str] | None = None,
        features: list[Features] | None = None,
        initial_days: int = 5,
        auto_connect: bool = True,
        timezone: str = "America/Chicago",
    ):
        self.instrument = instrument
        self.timeframes = timeframes or ["5min"]
        self.features = features or []
        self.initial_days = initial_days
        self.auto_connect = auto_connect
        self.timezone = timezone

    def get_order_manager_config(self) -> OrderManagerConfig:
        """Get configuration for OrderManager."""
        return {
            "enable_bracket_orders": Features.RISK_MANAGER in self.features,
            "enable_trailing_stops": True,
            "auto_risk_management": Features.RISK_MANAGER in self.features,
            "enable_order_validation": True,
        }

    def get_position_manager_config(self) -> PositionManagerConfig:
        """Get configuration for PositionManager."""
        return {
            "enable_risk_monitoring": Features.RISK_MANAGER in self.features,
            "enable_correlation_analysis": Features.PERFORMANCE_ANALYTICS
            in self.features,
            "enable_portfolio_rebalancing": False,
        }

    def get_data_manager_config(self) -> DataManagerConfig:
        """Get configuration for RealtimeDataManager."""
        return {
            "max_bars_per_timeframe": 1000,
            "enable_tick_data": True,
            "enable_level2_data": Features.ORDERBOOK in self.features,
            "data_validation": True,
            "auto_cleanup": True,
        }

    def get_orderbook_config(self) -> OrderbookConfig:
        """Get configuration for OrderBook."""
        return {
            "max_depth_levels": 100,
            "max_trade_history": 1000,
            "enable_analytics": Features.PERFORMANCE_ANALYTICS in self.features,
            "enable_pattern_detection": True,
        }

    def get_risk_config(self) -> RiskConfig:
        """Get configuration for RiskManager."""
        return RiskConfig(
            max_risk_per_trade=0.01,  # 1% per trade
            max_daily_loss=0.03,  # 3% daily loss
            max_positions=3,
            use_stop_loss=True,
            use_take_profit=True,
            use_trailing_stops=True,
            default_risk_reward_ratio=2.0,
        )


class TradingSuite:
    """
    Unified trading suite providing simplified access to all SDK components.

    This class replaces the complex factory functions with a clean, intuitive
    API that handles all initialization, connection, and dependency management
    automatically.

    Attributes:
        instrument: Trading instrument symbol
        data: Real-time data manager for OHLCV data
        orders: Order management system
        positions: Position tracking system
        orderbook: Level 2 market depth (if enabled)
        risk_manager: Risk management system (if enabled)
        client: Underlying ProjectX API client
        realtime: WebSocket connection manager
        config: Suite configuration
        events: Unified event bus for all components
    """

    def __init__(
        self,
        client: ProjectXBase,
        realtime_client: ProjectXRealtimeClient,
        config: TradingSuiteConfig,
    ):
        """
        Initialize TradingSuite with core components.

        Note: Use the factory methods (create, from_config, from_env) instead
        of instantiating directly.
        """
        self.client = client
        self.realtime = realtime_client
        self.config = config
        self._symbol = config.instrument  # Store original symbol
        self.instrument: Instrument | None = None  # Will be set during initialization

        # Initialize unified event bus
        self.events = EventBus()

        # Initialize core components with typed configs and event bus
        self.data = RealtimeDataManager(
            instrument=config.instrument,
            project_x=client,
            realtime_client=realtime_client,
            timeframes=config.timeframes,
            timezone=config.timezone,
            config=config.get_data_manager_config(),
            event_bus=self.events,
        )

        self.orders = OrderManager(
            client, config=config.get_order_manager_config(), event_bus=self.events
        )
        self.positions = PositionManager(
            client, config=config.get_position_manager_config(), event_bus=self.events
        )

        # Optional components
        self.orderbook: OrderBook | None = None
        self.risk_manager: RiskManager | None = None
        self.journal = None  # TODO: Future enhancement
        self.analytics = None  # TODO: Future enhancement

        # Initialize risk manager if enabled
        if Features.RISK_MANAGER in config.features:
            self.risk_manager = RiskManager(
                project_x=client,
                order_manager=self.orders,
                position_manager=self.positions,
                event_bus=self.events,
                config=config.get_risk_config(),
            )

        # State tracking
        self._connected = False
        self._initialized = False
        self._created_at = datetime.now()
        self._client_context: AbstractAsyncContextManager[ProjectXBase] | None = (
            None  # Will be set by create() method
        )

        logger.info(
            f"TradingSuite created for {config.instrument} "
            f"with features: {config.features}"
        )

    @classmethod
    async def create(
        cls,
        instrument: str,
        timeframes: list[str] | None = None,
        features: list[str] | None = None,
        **kwargs: Any,
    ) -> "TradingSuite":
        """
        Create a fully initialized TradingSuite with sensible defaults.

        This is the primary way to create a trading environment. It handles:
        - Authentication with ProjectX
        - WebSocket connection setup
        - Component initialization
        - Historical data loading
        - Market data subscriptions

        Args:
            instrument: Trading symbol (e.g., "MNQ", "MGC", "ES")
            timeframes: Data timeframes (default: ["5min"])
            features: Optional features to enable
            **kwargs: Additional configuration options

        Returns:
            Fully initialized and connected TradingSuite

        Example:
            ```python
            # Simple usage with defaults (with proper cleanup)
            async with await TradingSuite.create("MNQ") as suite:
                # Use the suite for trading
                current_price = await suite.data.get_current_price()
                print(f"Current price: {current_price}")

            # Or manage lifecycle manually
            suite = await TradingSuite.create(
                "MNQ",
                timeframes=["1min", "5min", "15min"],
                features=["orderbook", "risk_manager"],
                initial_days=10,
            )
            try:
                # Use the suite
                pass
            finally:
                await suite.disconnect()
            ```
        """
        # Build configuration
        config = TradingSuiteConfig(
            instrument=instrument,
            timeframes=timeframes or ["5min"],
            features=[Features(f) for f in (features or [])],
            **kwargs,
        )

        # Create and authenticate client
        # Note: We need to manage the client lifecycle manually since we're
        # keeping it alive beyond the creation method
        client_context = ProjectX.from_env()
        client = await client_context.__aenter__()

        try:
            await client.authenticate()

            if not client.account_info:
                raise ValueError("Failed to authenticate with ProjectX")

            # Create realtime client
            realtime_client = ProjectXRealtimeClient(
                jwt_token=client.session_token,
                account_id=str(client.account_info.id),
                config=client.config,
            )

            # Create suite instance
            suite = cls(client, realtime_client, config)

            # Store the context for cleanup later
            suite._client_context = client_context

            # Initialize if auto_connect is enabled
            if config.auto_connect:
                await suite._initialize()

            return suite

        except Exception:
            # Clean up on error
            await client_context.__aexit__(None, None, None)
            raise

    @classmethod
    async def from_config(cls, config_path: str) -> "TradingSuite":
        """
        Create TradingSuite from a configuration file.

        Supports both YAML and JSON configuration files.

        Args:
            config_path: Path to configuration file

        Returns:
            Configured TradingSuite instance

        Example:
            ```yaml
            # config/trading.yaml
            instrument: MNQ
            timeframes:
              - 1min
              - 5min
              - 15min
            features:
              - orderbook
              - risk_manager
            initial_days: 30
            ```

            ```python
            # Note: Create the config file first with the above content
            suite = await TradingSuite.from_config("config/trading.yaml")
            ```
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Load configuration
        if path.suffix in [".yaml", ".yml"]:
            with open(path) as f:
                data = yaml.safe_load(f)
        elif path.suffix == ".json":
            with open(path, "rb") as f:
                data = orjson.loads(f.read())
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")

        # Create suite with loaded configuration
        return await cls.create(**data)

    @classmethod
    async def from_env(cls, instrument: str, **kwargs: Any) -> "TradingSuite":
        """
        Create TradingSuite using environment variables for configuration.

        This method automatically loads ProjectX credentials from environment
        variables and applies any additional configuration from kwargs.

        Required environment variables:
        - PROJECT_X_API_KEY
        - PROJECT_X_USERNAME

        Args:
            instrument: Trading instrument symbol
            **kwargs: Additional configuration options

        Returns:
            Configured TradingSuite instance

        Example:
            ```python
            # Uses PROJECT_X_API_KEY and PROJECT_X_USERNAME from environment
            suite = await TradingSuite.from_env("MNQ", timeframes=["1min", "5min"])
            ```
        """
        # Environment variables are automatically used by ProjectX.from_env()
        return await cls.create(instrument, **kwargs)

    async def _initialize(self) -> None:
        """Initialize all components and establish connections."""
        if self._initialized:
            return

        try:
            # Connect to realtime feeds
            logger.info("Connecting to real-time feeds...")
            await self.realtime.connect()
            await self.realtime.subscribe_user_updates()

            # Initialize position manager with order manager for cleanup
            await self.positions.initialize(
                realtime_client=self.realtime,
                order_manager=self.orders,
            )

            # Load historical data
            logger.info(
                f"Loading {self.config.initial_days} days of historical data..."
            )
            await self.data.initialize(initial_days=self.config.initial_days)

            # Get instrument info and subscribe to market data
            self.instrument = await self.client.get_instrument(self._symbol)
            if not self.instrument:
                raise ValueError(f"Failed to get instrument info for {self._symbol}")

            await self.realtime.subscribe_market_data([self.instrument.id])

            # Start realtime data feed
            await self.data.start_realtime_feed()

            # Initialize optional components
            if Features.ORDERBOOK in self.config.features:
                logger.info("Initializing orderbook...")
                # Use the actual contract ID for the orderbook to properly match WebSocket updates
                self.orderbook = OrderBook(
                    instrument=self.instrument.id,  # Use contract ID instead of symbol
                    timezone_str=self.config.timezone,
                    project_x=self.client,
                    config=self.config.get_orderbook_config(),
                    event_bus=self.events,
                )
                await self.orderbook.initialize(
                    realtime_client=self.realtime,
                    subscribe_to_depth=True,
                    subscribe_to_quotes=True,
                )

            self._connected = True
            self._initialized = True
            logger.info("TradingSuite initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize TradingSuite: {e}")
            await self.disconnect()
            raise

    async def connect(self) -> None:
        """
        Manually connect all components if auto_connect was disabled.

        Example:
            ```python
            suite = await TradingSuite.create("MNQ", auto_connect=False)
            # ... configure components ...
            await suite.connect()
            ```
        """
        if not self._initialized:
            await self._initialize()

    async def disconnect(self) -> None:
        """
        Gracefully disconnect all components and clean up resources.

        Example:
            ```python
            await suite.disconnect()
            ```
        """
        logger.info("Disconnecting TradingSuite...")

        # Stop data feeds
        if self.data:
            await self.data.stop_realtime_feed()
            await self.data.cleanup()

        # Disconnect realtime
        if self.realtime:
            await self.realtime.disconnect()

        # Clean up orderbook
        if self.orderbook:
            await self.orderbook.cleanup()

        # Clean up client context
        if hasattr(self, "_client_context") and self._client_context:
            try:
                await self._client_context.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error cleaning up client context: {e}")
                # Continue with cleanup even if there's an error

        self._connected = False
        self._initialized = False
        logger.info("TradingSuite disconnected")

    async def __aenter__(self) -> "TradingSuite":
        """Async context manager entry."""
        if not self._initialized and self.config.auto_connect:
            await self._initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit with cleanup."""
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if all components are connected and ready."""
        return self._connected and self.realtime.is_connected()

    @property
    def symbol(self) -> str:
        """Get the original symbol (e.g., 'MNQ') without contract details."""
        return self._symbol

    @property
    def instrument_id(self) -> str | None:
        """Get the full instrument/contract ID (e.g., 'CON.F.US.MNQ.U25')."""
        return self.instrument.id if self.instrument else None

    async def on(self, event: EventType | str, handler: Any) -> None:
        """
        Register event handler through unified event bus.

        This is the single interface for all event handling in the SDK,
        replacing the scattered callback systems across components.

        Args:
            event: Event type to listen for (EventType enum or string)
            handler: Async callable to handle events

        Example:
            ```python
            async def handle_new_bar(event):
                # event.data contains: {'timeframe': str, 'data': bar_dict}
                bar_data = event.data.get("data", {})
                timeframe = event.data.get("timeframe", "")
                print(f"New {timeframe} bar: ${bar_data.get('close', 0):.2f}")


            async def handle_position_closed(event):
                # event.data contains the position object
                position = event.data
                print(f"Position closed: P&L = {position.pnl}")


            async def handle_order_filled(event):
                # event.data contains the order object
                order = event.data
                print(f"Order filled at {order.filledPrice}")


            # Register handlers
            await suite.on(EventType.NEW_BAR, handle_new_bar)
            await suite.on(EventType.POSITION_CLOSED, handle_position_closed)
            await suite.on(EventType.ORDER_FILLED, handle_order_filled)
            ```
        """
        await self.events.on(event, handler)

    async def once(self, event: EventType | str, handler: Any) -> None:
        """
        Register one-time event handler.

        Handler will be automatically removed after first invocation.

        Args:
            event: Event type to listen for
            handler: Async callable to handle event once
        """
        await self.events.once(event, handler)

    async def off(
        self, event: EventType | str | None = None, handler: Any | None = None
    ) -> None:
        """
        Remove event handler(s).

        Args:
            event: Event type to remove handler from (None for all)
            handler: Specific handler to remove (None for all)
        """
        await self.events.off(event, handler)

    def track_order(self, order: Any = None) -> OrderTracker:
        """
        Create an OrderTracker for comprehensive order lifecycle management.

        This provides automatic order state tracking with async waiting capabilities,
        eliminating the need for manual order status polling.

        Args:
            order: Optional order to track immediately (Order, OrderPlaceResponse, or order ID)

        Returns:
            OrderTracker instance (use as context manager)

        Example:
            ```python
            from project_x_py.types.trading import OrderSide

            # Track a new order
            async with suite.track_order() as tracker:
                order = await suite.orders.place_limit_order(
                    contract_id=suite.instrument_id,
                    side=OrderSide.BUY,
                    size=1,
                    price=current_price - 10,
                )
                tracker.track(order)

                try:
                    filled = await tracker.wait_for_fill(timeout=60)
                    print(f"Order filled at {filled.filledPrice}")
                except TimeoutError:
                    await tracker.modify_or_cancel(new_price=current_price - 5)
            ```
        """
        tracker = OrderTracker(self, order)
        return tracker

    def order_chain(self) -> OrderChainBuilder:
        """
        Create an order chain builder for complex order structures.

        Provides a fluent API for building multi-part orders (entry + stops + targets)
        with clean, readable syntax.

        Returns:
            OrderChainBuilder instance

        Example:
            ```python
            # Build a bracket order with stops and targets
            # Note: side=0 for BUY, side=1 for SELL
            order_chain = (
                suite.order_chain()
                .market_order(size=2, side=0)  # BUY 2 contracts
                .with_stop_loss(offset=50)
                .with_take_profit(offset=100)
                .with_trail_stop(offset=25, trigger_offset=50)
            )

            result = await order_chain.execute()

            # Or use a limit entry
            order_chain = (
                suite.order_chain()
                .limit_order(size=1, price=16000, side=0)  # BUY limit
                .with_stop_loss(price=15950)
                .with_take_profit(price=16100)
            )
            ```
        """
        return OrderChainBuilder(self)

    def managed_trade(
        self,
        max_risk_percent: float | None = None,
        max_risk_amount: float | None = None,
    ) -> ManagedTrade:
        """
        Create a managed trade context manager with automatic risk management.

        This provides a high-level interface for executing trades with built-in:
        - Position sizing based on risk parameters
        - Trade validation against risk rules
        - Automatic stop-loss and take-profit attachment
        - Position monitoring and adjustment
        - Cleanup on exit

        Args:
            max_risk_percent: Override max risk percentage for this trade
            max_risk_amount: Override max risk dollar amount for this trade

        Returns:
            ManagedTrade context manager

        Raises:
            ValueError: If risk manager is not enabled

        Example:
            ```python
            # Enter a risk-managed long position
            async with suite.managed_trade(max_risk_percent=0.01) as trade:
                result = await trade.enter_long(
                    stop_loss=current_price - 50,
                    take_profit=current_price + 100,
                )

                # Optional: Scale in
                if market_conditions_favorable:
                    await trade.scale_in(additional_size=1)

                # Optional: Adjust stop
                if price_moved_favorably:
                    await trade.adjust_stop(new_stop_loss=entry_price)

            # Automatic cleanup on exit
            ```
        """
        if not self.risk_manager:
            raise ValueError(
                "Risk manager not enabled. Add 'risk_manager' to features list."
            )

        return ManagedTrade(
            risk_manager=self.risk_manager,
            order_manager=self.orders,
            position_manager=self.positions,
            instrument_id=self.instrument_id or self._symbol,
            max_risk_percent=max_risk_percent,
            max_risk_amount=max_risk_amount,
        )

    async def wait_for(
        self, event: EventType | str, timeout: float | None = None
    ) -> Any:
        """
        Wait for specific event to occur.

        Args:
            event: Event type to wait for
            timeout: Optional timeout in seconds

        Returns:
            Event object when received

        Raises:
            TimeoutError: If timeout expires
        """
        return await self.events.wait_for(event, timeout)

    def get_stats(self) -> TradingSuiteStats:
        """
        Get comprehensive statistics from all components.

        Returns:
            Structured statistics from all active components
        """
        from datetime import datetime

        # Calculate uptime
        uptime_seconds = (
            int((datetime.now() - self._created_at).total_seconds())
            if hasattr(self, "_created_at")
            else 0
        )

        # Build component stats
        components: dict[str, ComponentStats] = {}
        if self.orders:
            components["order_manager"] = ComponentStats(
                name="OrderManager",
                status="connected" if self.orders else "disconnected",
                uptime_seconds=uptime_seconds,
                last_activity=None,
                error_count=0,
                memory_usage_mb=0.0,
            )

        if self.positions:
            components["position_manager"] = ComponentStats(
                name="PositionManager",
                status="connected" if self.positions else "disconnected",
                uptime_seconds=uptime_seconds,
                last_activity=None,
                error_count=0,
                memory_usage_mb=0.0,
            )

        if self.data:
            components["data_manager"] = ComponentStats(
                name="RealtimeDataManager",
                status="connected" if self.data else "disconnected",
                uptime_seconds=uptime_seconds,
                last_activity=None,
                error_count=0,
                memory_usage_mb=0.0,
            )

        if self.orderbook:
            components["orderbook"] = ComponentStats(
                name="OrderBook",
                status="connected" if self.orderbook else "disconnected",
                uptime_seconds=uptime_seconds,
                last_activity=None,
                error_count=0,
                memory_usage_mb=0.0,
            )

        if self.risk_manager:
            components["risk_manager"] = ComponentStats(
                name="RiskManager",
                status="active" if self.risk_manager else "inactive",
                uptime_seconds=uptime_seconds,
                last_activity=None,
                error_count=0,
                memory_usage_mb=0.0,
            )

        return {
            "suite_id": getattr(self, "suite_id", "unknown"),
            "instrument": self.instrument_id or self._symbol,
            "created_at": getattr(self, "_created_at", datetime.now()).isoformat(),
            "uptime_seconds": uptime_seconds,
            "status": "active" if self.is_connected else "disconnected",
            "connected": self.is_connected,
            "components": components,
            "realtime_connected": self.realtime.is_connected()
            if self.realtime
            else False,
            "user_hub_connected": getattr(self.realtime, "user_connected", False)
            if self.realtime
            else False,
            "market_hub_connected": getattr(self.realtime, "market_connected", False)
            if self.realtime
            else False,
            "total_api_calls": 0,
            "successful_api_calls": 0,
            "failed_api_calls": 0,
            "avg_response_time_ms": 0.0,
            "cache_hit_rate": 0.0,
            "memory_usage_mb": 0.0,
            "active_subscriptions": 0,
            "message_queue_size": 0,
            "features_enabled": [f.value for f in self.config.features],
            "timeframes": self.config.timeframes,
        }
