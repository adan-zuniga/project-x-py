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

import json
from contextlib import AbstractAsyncContextManager
from enum import Enum
from pathlib import Path
from types import TracebackType
from typing import Any

import yaml

from project_x_py.client import ProjectX
from project_x_py.client.base import ProjectXBase
from project_x_py.order_manager import OrderManager
from project_x_py.orderbook import OrderBook
from project_x_py.position_manager import PositionManager
from project_x_py.realtime import ProjectXRealtimeClient
from project_x_py.realtime_data_manager import RealtimeDataManager
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
        client: Underlying ProjectX API client
        realtime: WebSocket connection manager
        config: Suite configuration
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
        self.instrument = config.instrument

        # Initialize core components
        self.data = RealtimeDataManager(
            instrument=config.instrument,
            project_x=client,
            realtime_client=realtime_client,
            timeframes=config.timeframes,
            timezone=config.timezone,
        )

        self.orders = OrderManager(client)
        self.positions = PositionManager(client)

        # Optional components
        self.orderbook: OrderBook | None = None
        self.risk_manager = None  # TODO: Implement in Week 5
        self.journal = None  # TODO: Future enhancement
        self.analytics = None  # TODO: Future enhancement

        # State tracking
        self._connected = False
        self._initialized = False
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
            # Simple usage with defaults
            suite = await TradingSuite.create("MNQ")

            # With custom configuration
            suite = await TradingSuite.create(
                "MNQ",
                timeframes=["1min", "5min", "15min"],
                features=["orderbook", "risk_manager"],
                initial_days=10,
            )
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
            suite = await TradingSuite.from_config("config/trading.yaml")
            ```
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Load configuration
        with open(path) as f:
            if path.suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            elif path.suffix == ".json":
                data = json.load(f)
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
            instrument_info = await self.client.get_instrument(self.instrument)
            await self.realtime.subscribe_market_data([instrument_info.id])

            # Start realtime data feed
            await self.data.start_realtime_feed()

            # Initialize optional components
            if Features.ORDERBOOK in self.config.features:
                logger.info("Initializing orderbook...")
                self.orderbook = OrderBook(
                    instrument=self.instrument,
                    timezone_str=self.config.timezone,
                    project_x=self.client,
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

    def get_stats(self) -> dict[str, Any]:
        """
        Get comprehensive statistics from all components.

        Returns:
            Dictionary containing stats from all active components
        """
        stats = {
            "connected": self.is_connected,
            "instrument": self.instrument,
            "features": [f.value for f in self.config.features],
        }

        if self.realtime:
            stats["realtime"] = self.realtime.get_stats()

        if self.data:
            stats["data_manager"] = self.data.get_memory_stats()

        if self.orderbook:
            stats["orderbook"] = {
                "bid_depth": len(self.orderbook.orderbook_bids),
                "ask_depth": len(self.orderbook.orderbook_asks),
                "trade_count": len(self.orderbook.recent_trades),
            }

        return stats
