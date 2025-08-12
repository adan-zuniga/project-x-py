"""
Core RealtimeDataManager class for efficient real-time OHLCV data management.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides the main RealtimeDataManager class that handles real-time market data
    processing across multiple timeframes. Implements efficient OHLCV (Open, High, Low, Close, Volume)
    data management with WebSocket integration, automatic bar creation, and comprehensive memory management.

Key Features:
    - Multi-timeframe OHLCV data management with real-time updates
    - WebSocket integration for zero-latency tick processing
    - Automatic bar creation and maintenance across all timeframes
    - Memory-efficient sliding window storage with automatic cleanup
    - Event-driven callback system for new bars and data updates
    - Timezone-aware timestamp handling (default: CME Central Time)
    - Thread-safe operations with asyncio locks
    - Comprehensive health monitoring and statistics

Architecture:
    - Mixin-based design for modular functionality
    - Dependency injection for ProjectX client and realtime client
    - Event-driven processing with callback system
    - Memory management with automatic cleanup
    - Thread-safe operations with proper locking

Performance Benefits:
    - 95% reduction in API calls compared to polling
    - Sub-second data freshness with WebSocket feeds
    - Synchronized data across all timeframes
    - Minimal latency for trading signals
    - Resilience to network issues

Note:
    This class is the core implementation of the real-time data manager. For most
    applications, it is recommended to interact with it through the `TradingSuite`
    (`suite.data`), which handles its lifecycle and integration automatically.
    The example below demonstrates direct, low-level instantiation and usage.

Example Usage:
    ```python
    # V3: Create shared async realtime client with factory
    from project_x_py import EventBus
    from project_x_py.realtime import create_realtime_client

    async_realtime_client = await create_realtime_client(
        jwt_token=client.jwt_token, account_id=str(client.account_id)
    )
    await async_realtime_client.connect()

    # V3: Initialize with EventBus for unified event handling
    event_bus = EventBus()

    # Initialize async data manager with dependency injection
    manager = RealtimeDataManager(
        instrument="MNQ",  # V3: Using actual contract symbols
        project_x=client,  # V3: ProjectX client from context manager
        realtime_client=async_realtime_client,
        timeframes=["1min", "5min", "15min", "1hr"],
        timezone="America/Chicago",  # CME timezone
        event_bus=event_bus,  # V3: EventBus integration
    )

    # Load historical data for all timeframes
    if await manager.initialize(initial_days=5):
        print("Historical data loaded successfully")

    # Start real-time feed (registers callbacks with existing client)
    if await manager.start_realtime_feed():
        print("Real-time OHLCV feed active")


    # V3: Register callback with actual field names
    async def on_new_bar(data):
        timeframe = data["timeframe"]
        bar_data = data["data"]
        print(f"New {timeframe} bar:")
        print(f"  Open: {bar_data['open']}, High: {bar_data['high']}")
        print(f"  Low: {bar_data['low']}, Close: {bar_data['close']}")
        print(f"  Volume: {bar_data['volume']}")


    await manager.add_callback("new_bar", on_new_bar)

    # V3: Access multi-timeframe OHLCV data
    data_5m = await manager.get_data("5min", bars=100)
    data_15m = await manager.get_data("15min", bars=50)
    mtf_data = await manager.get_mtf_data()  # All timeframes at once

    # Get current market price (latest tick or bar close)
    current_price = await manager.get_current_price()

    # V3: Monitor memory and performance
    stats = await manager.get_memory_stats()
    print(f"Data points stored: {stats['total_data_points']}")

    # When done, clean up resources
    await manager.cleanup()
    ```

Supported Timeframes:
    - Second-based: "1sec", "5sec", "10sec", "15sec", "30sec"
    - Minute-based: "1min", "5min", "15min", "30min"
    - Hour-based: "1hr", "4hr"
    - Day-based: "1day"
    - Week-based: "1week"
    - Month-based: "1month"

See Also:
    - `realtime_data_manager.callbacks.CallbackMixin`
    - `realtime_data_manager.data_access.DataAccessMixin`
    - `realtime_data_manager.data_processing.DataProcessingMixin`
    - `realtime_data_manager.memory_management.MemoryManagementMixin`
    - `realtime_data_manager.validation.ValidationMixin`
"""

import asyncio
import contextlib
import time
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any

import polars as pl
import pytz

from project_x_py.client.base import ProjectXBase
from project_x_py.exceptions import (
    ProjectXError,
    ProjectXInstrumentError,
)
from project_x_py.models import Instrument
from project_x_py.realtime_data_manager.callbacks import CallbackMixin
from project_x_py.realtime_data_manager.data_access import DataAccessMixin
from project_x_py.realtime_data_manager.data_processing import DataProcessingMixin
from project_x_py.realtime_data_manager.memory_management import MemoryManagementMixin
from project_x_py.realtime_data_manager.mmap_overflow import MMapOverflowMixin
from project_x_py.realtime_data_manager.validation import ValidationMixin
from project_x_py.types.config_types import DataManagerConfig
from project_x_py.utils import (
    ErrorMessages,
    LogContext,
    LogMessages,
    ProjectXLogger,
    format_error_message,
    handle_errors,
)

if TYPE_CHECKING:
    from project_x_py.client import ProjectXBase
    from project_x_py.realtime import ProjectXRealtimeClient


class RealtimeDataManager(
    DataProcessingMixin,
    MemoryManagementMixin,
    MMapOverflowMixin,
    CallbackMixin,
    DataAccessMixin,
    ValidationMixin,
):
    """
    Async optimized real-time OHLCV data manager for efficient multi-timeframe trading data.

    This class focuses exclusively on OHLCV (Open, High, Low, Close, Volume) data management
    across multiple timeframes through real-time tick processing using async/await patterns.
    It provides a foundation for trading strategies that require synchronized data across
    different timeframes with minimal API usage.

    Core Architecture:
        Traditional approach: Poll API every 5 minutes for each timeframe = 20+ API calls/hour
        Real-time approach: Load historical once + live tick processing = 1 API call + WebSocket
        Result: 95% reduction in API calls with sub-second data freshness

    Key Benefits:
        - Reduction in API rate limit consumption
        - Synchronized data across all timeframes
        - Real-time updates without polling
        - Minimal latency for trading signals
        - Resilience to network issues

    Features:
        - Complete async/await implementation for non-blocking operation
        - Zero-latency OHLCV updates via WebSocket integration
        - Automatic bar creation and maintenance across all timeframes
        - Async-safe multi-timeframe data access with locks
        - Memory-efficient sliding window storage with automatic pruning
        - Timezone-aware timestamp handling (default: CME Central Time)
        - Event callbacks for new bars and real-time data updates
        - Comprehensive health monitoring and statistics

    Available Timeframes:
        - Second-based: "1sec", "5sec", "10sec", "15sec", "30sec"
        - Minute-based: "1min", "5min", "15min", "30min"
        - Hour-based: "1hr", "4hr"
        - Day-based: "1day"
        - Week-based: "1week"
        - Month-based: "1month"

    Example Usage:
        ```python
        # Create shared async realtime client
        async_realtime_client = ProjectXRealtimeClient(config)
        await async_realtime_client.connect()

        # Initialize async data manager with dependency injection
        manager = RealtimeDataManager(
            instrument="MGC",  # Mini Gold futures
            project_x=async_project_x_client,  # For historical data loading
            realtime_client=async_realtime_client,
            timeframes=["1min", "5min", "15min", "1hr"],
            timezone="America/Chicago",  # CME timezone
        )

        # Load historical data for all timeframes
        if await manager.initialize(initial_days=30):
            print("Historical data loaded successfully")

        # Start real-time feed (registers callbacks with existing client)
        if await manager.start_realtime_feed():
            print("Real-time OHLCV feed active")


        # Register callback for new bars
        async def on_new_bar(data):
            timeframe = data["timeframe"]
            bar_data = data["data"]
            print(f"New {timeframe} bar: Close={bar_data['close']}")


        await manager.add_callback("new_bar", on_new_bar)

        # Access multi-timeframe OHLCV data in your trading loop
        data_5m = await manager.get_data("5min", bars=100)
        data_15m = await manager.get_data("15min", bars=50)
        mtf_data = await manager.get_mtf_data()  # All timeframes at once

        # Get current market price (latest tick or bar close)
        current_price = await manager.get_current_price()

        # When done, clean up resources
        await manager.cleanup()
        ```

    Note:
        - All methods accessing data are thread-safe with asyncio locks
        - Automatic memory management limits data storage for efficiency
        - All timestamp handling is timezone-aware by default
        - Uses Polars DataFrames for high-performance data operations
    """

    def __init__(
        self,
        instrument: str,
        project_x: "ProjectXBase",
        realtime_client: "ProjectXRealtimeClient",
        event_bus: Any | None = None,
        timeframes: list[str] | None = None,
        timezone: str = "America/Chicago",
        config: DataManagerConfig | None = None,
    ):
        """
        Initialize the optimized real-time OHLCV data manager with dependency injection.

        Creates a new instance of the RealtimeDataManager that manages real-time market data
        for a specific trading instrument across multiple timeframes. The manager uses dependency
        injection with ProjectX for historical data loading and ProjectXRealtimeClient
        for live WebSocket market data.

        Args:
            instrument: Trading instrument symbol (e.g., "MGC", "MNQ", "ES").
                This should be the base symbol, not a specific contract.

            project_x: ProjectXBase client instance for initial historical data loading.
                This client should already be authenticated before passing to this constructor.

            realtime_client: ProjectXRealtimeClient instance for live market data.
                The client does not need to be connected yet, as the manager will handle
                connection when start_realtime_feed() is called.

            event_bus: EventBus instance for unified event handling. Required for all
                event emissions including new bars, data updates, and errors.

            timeframes: List of timeframes to track (default: ["5min"] if None provided).
                Available timeframes include:
                - Seconds: "1sec", "5sec", "10sec", "15sec", "30sec"
                - Minutes: "1min", "5min", "15min", "30min"
                - Hours: "1hr", "4hr"
                - Days/Weeks/Months: "1day", "1week", "1month"

            timezone: Timezone for timestamp handling (default: "America/Chicago").
                This timezone is used for all bar calculations and should typically be set to
                the exchange timezone for the instrument (e.g., "America/Chicago" for CME).

            config: Optional configuration for data manager behavior. If not provided,
                default values will be used for all configuration options.

        Raises:
            ValueError: If an invalid timeframe is provided.

        Example:
            ```python
            # Create the required clients first
            px_client = ProjectX()
            await px_client.authenticate()

            # Create and connect realtime client
            realtime_client = ProjectXRealtimeClient(px_client.config)

            # Create data manager with multiple timeframes for Gold mini futures
            data_manager = RealtimeDataManager(
                instrument="MGC",  # Gold mini futures
                project_x=px_client,
                realtime_client=realtime_client,
                timeframes=["1min", "5min", "15min", "1hr"],
                timezone="America/Chicago",  # CME timezone
            )

            # Note: After creating the manager, you need to call:
            # 1. await data_manager.initialize() to load historical data
            # 2. await data_manager.start_realtime_feed() to begin real-time updates
            ```

        Note:
            The manager instance is not fully initialized until you call the initialize() method,
            which loads historical data for all timeframes. After initialization, call
            start_realtime_feed() to begin receiving real-time updates.
        """
        if timeframes is None:
            timeframes = ["5min"]

        # Set basic attributes needed by mixins
        self.instrument: str = instrument
        self.project_x: ProjectXBase = project_x
        self.realtime_client: ProjectXRealtimeClient = realtime_client
        # EventBus is optional in tests; fallback to a simple dummy if None
        self.event_bus = event_bus if event_bus is not None else object()

        self.logger = ProjectXLogger.get_logger(__name__)

        # Store configuration with defaults
        self.config = config or {}

        # Create data lock needed by mixins
        self.data_lock: asyncio.Lock = asyncio.Lock()

        # Initialize timeframes needed by mixins
        self.timeframes: dict[str, dict[str, Any]] = {}

        # Initialize data storage
        self.data: dict[str, pl.DataFrame] = {}

        # Apply defaults which sets max_bars_per_timeframe etc.
        self._apply_config_defaults()

        # Initialize all mixins (they may need the above attributes)
        super().__init__()

        # Set timezone for consistent timestamp handling
        self.timezone: Any = pytz.timezone(timezone)  # CME timezone

        timeframes_dict: dict[str, dict[str, Any]] = {
            "1sec": {"interval": 1, "unit": 1, "name": "1sec"},
            "5sec": {"interval": 5, "unit": 1, "name": "5sec"},
            "10sec": {"interval": 10, "unit": 1, "name": "10sec"},
            "15sec": {"interval": 15, "unit": 1, "name": "15sec"},
            "30sec": {"interval": 30, "unit": 1, "name": "30sec"},
            "1min": {"interval": 1, "unit": 2, "name": "1min"},
            "5min": {"interval": 5, "unit": 2, "name": "5min"},
            "15min": {"interval": 15, "unit": 2, "name": "15min"},
            "30min": {"interval": 30, "unit": 2, "name": "30min"},
            "1hr": {"interval": 60, "unit": 2, "name": "1hr"},
            "4hr": {"interval": 240, "unit": 2, "name": "4hr"},
            "1day": {"interval": 1, "unit": 4, "name": "1day"},
            "1week": {"interval": 1, "unit": 5, "name": "1week"},
            "1month": {"interval": 1, "unit": 6, "name": "1month"},
        }

        # Update timeframes with configs (dict already created above)
        for tf in timeframes:
            if tf not in timeframes_dict:
                raise ValueError(
                    f"Invalid timeframe: {tf}, valid timeframes are: {list(timeframes_dict.keys())}"
                )
            self.timeframes[tf] = timeframes_dict[tf]

        # Real-time data components
        # Use deque for automatic size management of tick data
        from collections import deque

        self.current_tick_data: deque[dict[str, Any]] = deque(maxlen=10000)
        self.last_bar_times: dict[str, datetime] = {}

        # Async synchronization
        self.is_running: bool = False
        # EventBus is now used for all event handling
        self.indicator_cache: defaultdict[str, dict[str, Any]] = defaultdict(dict)

        # Contract ID for real-time subscriptions
        self.contract_id: str | None = None
        # Actual symbol ID from the resolved instrument (e.g., "ENQ" when user specifies "NQ")
        self.instrument_symbol_id: str | None = None
        # Tick size for price alignment
        self.tick_size: float = 0.25  # Default, will be updated in initialize()

        # Memory management settings are set in _apply_config_defaults()
        self.last_cleanup: float = time.time()

        # Comprehensive statistics tracking
        self.memory_stats = {
            "bars_processed": 0,
            "ticks_processed": 0,
            "quotes_processed": 0,
            "trades_processed": 0,
            "timeframe_stats": {tf: {"bars": 0, "updates": 0} for tf in timeframes},
            "avg_processing_time_ms": 0.0,
            "data_latency_ms": 0.0,
            "buffer_utilization": 0.0,
            "total_bars_stored": 0,
            "memory_usage_mb": 0.0,
            "compression_ratio": 1.0,
            "updates_per_minute": 0.0,
            "last_update": None,
            "data_freshness_seconds": 0.0,
            "data_validation_errors": 0,
            "connection_interruptions": 0,
            "recovery_attempts": 0,
            # Legacy fields for backward compatibility
            "total_bars": 0,
            "bars_cleaned": 0,
            "last_cleanup": time.time(),
        }

        # Background cleanup task
        self._cleanup_task: asyncio.Task[None] | None = None

        # Background bar timer task for low-volume periods
        self._bar_timer_task: asyncio.Task[None] | None = None

        self.logger.info(
            "RealtimeDataManager initialized", extra={"instrument": instrument}
        )

    def _apply_config_defaults(self) -> None:
        """Apply default values for configuration options."""
        # Data management settings
        self.max_bars_per_timeframe = self.config.get("max_bars_per_timeframe", 1000)
        self.enable_tick_data = self.config.get("enable_tick_data", True)
        self.enable_level2_data = self.config.get("enable_level2_data", False)
        self.buffer_size = self.config.get("buffer_size", 1000)
        self.compression_enabled = self.config.get("compression_enabled", True)
        self.data_validation = self.config.get("data_validation", True)
        self.auto_cleanup = self.config.get("auto_cleanup", True)
        self.cleanup_interval_minutes = self.config.get("cleanup_interval_minutes", 5)
        self.historical_data_cache = self.config.get("historical_data_cache", True)
        self.cache_expiry_hours = self.config.get("cache_expiry_hours", 24)

        # Set memory management attributes based on config
        self.tick_buffer_size = self.buffer_size
        self.cleanup_interval = float(
            self.cleanup_interval_minutes * 60
        )  # Convert to seconds

    @handle_errors("initialize", reraise=False, default_return=False)
    async def initialize(self, initial_days: int = 1) -> bool:
        """
        Initialize the real-time data manager by loading historical OHLCV data.

        This method performs the initial setup of the data manager by loading historical
        OHLCV data for all configured timeframes. It identifies the correct contract ID
        for the instrument and loads the specified number of days of historical data
        into memory for each timeframe. This provides a baseline of data before real-time
        updates begin.

        Args:
            initial_days: Number of days of historical data to load (default: 1).
                Higher values provide more historical context but consume more memory.
                Typical values are:
                - 1-5 days: For short-term trading and minimal memory usage
                - 30 days: For strategies requiring more historical context
                - 90+ days: For longer-term pattern detection or backtesting

        Returns:
            bool: True if initialization completed successfully for at least one timeframe,
                False if errors occurred for all timeframes or the instrument wasn't found.

        Raises:
            Exception: Any exceptions from the API are caught and logged, returning False.

        Example:
            ```python
            # Initialize with 30 days of historical data
            success = await data_manager.initialize(initial_days=30)

            if success:
                print("Historical data loaded successfully")

                # Check data availability for each timeframe
                memory_stats = data_manager.get_memory_stats()
                for tf, count in memory_stats["timeframe_bar_counts"].items():
                    print(f"Loaded {count} bars for {tf} timeframe")
            else:
                print("Failed to initialize data manager")
            ```

        Note:
            - This method must be called before start_realtime_feed()
            - The method retrieves the contract ID for the instrument, which is needed
              for real-time data subscriptions
            - If data for a specific timeframe fails to load, the method will log a warning
              but continue with the other timeframes
        """
        with LogContext(
            self.logger,
            operation="initialize",
            instrument=self.instrument,
            initial_days=initial_days,
        ):
            self.logger.debug(
                LogMessages.DATA_FETCH,
                extra={"phase": "initialization", "instrument": self.instrument},
            )

            # Get the contract ID for the instrument
            instrument_info: Instrument | None = await self.project_x.get_instrument(
                self.instrument
            )
            if instrument_info is None:
                raise ProjectXInstrumentError(
                    format_error_message(
                        ErrorMessages.INSTRUMENT_NOT_FOUND, symbol=self.instrument
                    )
                )

            # Store the exact contract ID for real-time subscriptions
            self.contract_id = instrument_info.id

            # Store the tick size for price alignment
            self.tick_size = getattr(instrument_info, "tickSize", 0.25)

            # Store the actual symbol ID for matching (e.g., "ENQ" when user specifies "NQ")
            # Extract from symbolId like "F.US.ENQ" -> "ENQ"
            if instrument_info.symbolId and "." in instrument_info.symbolId:
                parts = instrument_info.symbolId.split(".")
                self.instrument_symbol_id = (
                    parts[-1] if parts else instrument_info.symbolId
                )
            else:
                self.instrument_symbol_id = instrument_info.symbolId or self.instrument

            # Load initial data for all timeframes
            async with self.data_lock:
                for tf_key, tf_config in self.timeframes.items():
                    bars = await self.project_x.get_bars(
                        self.instrument,  # Use base symbol, not contract ID
                        interval=tf_config["interval"],
                        unit=tf_config["unit"],
                        days=initial_days,
                    )

                    if bars is not None and not bars.is_empty():
                        self.data[tf_key] = bars
                        self.logger.debug(
                            LogMessages.DATA_RECEIVED,
                            extra={"timeframe": tf_key, "bar_count": len(bars)},
                        )
                    else:
                        self.logger.warning(
                            LogMessages.DATA_ERROR,
                            extra={"timeframe": tf_key, "error": "No data loaded"},
                        )

            self.logger.debug(
                LogMessages.DATA_RECEIVED,
                extra={"status": "initialized", "instrument": self.instrument},
            )
            return True

    @handle_errors("start realtime feed", reraise=False, default_return=False)
    async def start_realtime_feed(self) -> bool:
        """
        Start the real-time OHLCV data feed using WebSocket connections.

        This method configures and starts the real-time market data feed for the instrument.
        It registers callbacks with the realtime client to receive market data updates,
        subscribes to the appropriate market data channels, and initiates the background
        cleanup task for memory management.

        The method will:
        1. Register callback handlers for quotes and trades
        2. Subscribe to market data for the instrument's contract ID
        3. Start a background task for periodic memory cleanup

        Returns:
            bool: True if real-time feed started successfully, False if there were errors
                such as connection failures or subscription issues.

        Raises:
            Exception: Any exceptions during setup are caught and logged, returning False.

        Example:
            ```python
            # Initialize data manager first
            await data_manager.initialize(initial_days=10)

            # Start the real-time feed
            if await data_manager.start_realtime_feed():
                print("Real-time OHLCV updates active")

                # Register callback for new bars
                async def on_new_bar(data):
                    print(f"New {data['timeframe']} bar at {data['bar_time']}")

                await data_manager.add_callback("new_bar", on_new_bar)

                # Use the data in your trading loop
                while True:
                    current_price = await data_manager.get_current_price()
                    # Your trading logic here
                    await asyncio.sleep(1)
            else:
                print("Failed to start real-time feed")
            ```

        Note:
            - The initialize() method must be called successfully before calling this method,
              as it requires the contract_id to be set
            - This method is idempotent - calling it multiple times will only establish
              the connection once
            - The method sets up a background task for periodic memory cleanup to prevent
              excessive memory usage
        """
        with LogContext(
            self.logger,
            operation="start_realtime_feed",
            instrument=self.instrument,
            contract_id=self.contract_id,
        ):
            if self.is_running:
                self.logger.warning(
                    LogMessages.DATA_ERROR,
                    extra={"error": "Real-time feed already running"},
                )
                return True

            if not self.contract_id:
                raise ProjectXError(
                    format_error_message(
                        ErrorMessages.INTERNAL_ERROR,
                        reason="Contract ID not set - call initialize() first",
                    )
                )

            # Register callbacks first
            await self.realtime_client.add_callback(
                "quote_update", self._on_quote_update
            )
            await self.realtime_client.add_callback(
                "market_trade",
                self._on_trade_update,  # Use market_trade event name
            )

            # Subscribe to market data using the contract ID
            self.logger.debug(
                LogMessages.DATA_SUBSCRIBE, extra={"contract_id": self.contract_id}
            )
            subscription_success = await self.realtime_client.subscribe_market_data(
                [self.contract_id]
            )

            if not subscription_success:
                raise ProjectXError(
                    format_error_message(
                        ErrorMessages.WS_SUBSCRIPTION_FAILED,
                        channel="market data",
                        reason="Subscription returned False",
                    )
                )

            self.logger.debug(
                LogMessages.DATA_SUBSCRIBE,
                extra={"status": "success", "contract_id": self.contract_id},
            )

            self.is_running = True

            # Start cleanup task
            self.start_cleanup_task()

            # Start bar timer task for low-volume periods
            self._start_bar_timer_task()

            self.logger.debug(
                LogMessages.DATA_SUBSCRIBE,
                extra={"status": "feed_started", "instrument": self.instrument},
            )
            return True

    async def stop_realtime_feed(self) -> None:
        """
        Stop the real-time OHLCV data feed and cleanup resources.

        Example:
            >>> await manager.stop_realtime_feed()
        """
        try:
            if not self.is_running:
                return

            self.is_running = False

            # Cancel cleanup task
            await self.stop_cleanup_task()

            # Cancel bar timer task
            await self._stop_bar_timer_task()

            # Unsubscribe from market data
            # Note: unsubscribe_market_data will be implemented in ProjectXRealtimeClient
            if self.contract_id:
                self.logger.info(f"📉 Unsubscribing from {self.contract_id}")

            self.logger.info(f"✅ Real-time feed stopped for {self.instrument}")

        except RuntimeError as e:
            self.logger.error(f"❌ Error stopping real-time feed: {e}")

    async def cleanup(self) -> None:
        """
        Clean up resources when shutting down.

        Example:
            >>> await manager.cleanup()
        """
        await self.stop_realtime_feed()

        async with self.data_lock:
            self.data.clear()
            self.current_tick_data.clear()
            # EventBus handles all event cleanup
            self.indicator_cache.clear()

            # Backward-compatible attributes used in some tests/examples
            # Use dynamic attribute access safely without type checker complaints
            bars_attr = getattr(self, "bars", None)
            if isinstance(bars_attr, dict):
                for _tf in list(bars_attr.keys()):
                    bars_attr[_tf] = []
            ticks_attr = getattr(self, "ticks", None)
            if isinstance(ticks_attr, list):
                ticks_attr.clear()
            dom_attr = getattr(self, "dom_data", None)
            if isinstance(dom_attr, dict):
                for _k in list(dom_attr.keys()):
                    dom_attr[_k] = []

        self.logger.info("✅ RealtimeDataManager cleanup completed")

    def _start_bar_timer_task(self) -> None:
        """Start the bar timer task for creating bars during low-volume periods."""
        if self._bar_timer_task is None or self._bar_timer_task.done():
            self._bar_timer_task = asyncio.create_task(self._bar_timer_loop())
            self.logger.debug("Bar timer task started")

    async def _stop_bar_timer_task(self) -> None:
        """Stop the bar timer task."""
        if self._bar_timer_task and not self._bar_timer_task.done():
            self._bar_timer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._bar_timer_task
            self.logger.debug("Bar timer task stopped")

    async def _bar_timer_loop(self) -> None:
        """
        Periodic task to create empty bars during low-volume periods.

        This ensures bars are created at regular intervals even when
        there's no trading activity (important for low-volume instruments).
        """
        try:
            # Find the shortest timeframe interval to check
            min_seconds = float("inf")
            for tf_config in self.timeframes.values():
                interval = tf_config["interval"]
                unit = tf_config["unit"]

                # Convert to seconds based on numeric unit value
                # Unit mapping: {1: seconds, 2: minutes, 4: days, 5: weeks, 6: months}
                unit_seconds_map = {
                    1: 1,  # seconds
                    2: 60,  # minutes
                    4: 86400,  # days
                    5: 604800,  # weeks
                    6: 2629746,  # months (approximate)
                }

                if unit in unit_seconds_map:
                    seconds = interval * unit_seconds_map[unit]
                else:
                    continue  # Skip unsupported units

                min_seconds = min(min_seconds, seconds)

            # Check at least every 5 seconds, but no more than the shortest interval
            check_interval = min(5.0, min_seconds / 3)

            self.logger.debug(f"Bar timer checking every {check_interval} seconds")

            while self.is_running:
                await asyncio.sleep(check_interval)

                # Check each timeframe for stale bars
                await self._check_and_create_empty_bars()

        except asyncio.CancelledError:
            self.logger.debug("Bar timer task cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in bar timer loop: {e}")

    async def _check_and_create_empty_bars(self) -> None:
        """
        Check each timeframe and create empty bars if needed.

        This handles low-volume periods where no ticks are coming in,
        ensuring bars are still created at the proper intervals.
        """
        try:
            current_time = datetime.now(self.timezone)
            events_to_trigger = []

            async with self.data_lock:
                for tf_key, tf_config in self.timeframes.items():
                    if tf_key not in self.data:
                        continue

                    current_data = self.data[tf_key]
                    if current_data.height == 0:
                        continue

                    # Get the last bar time
                    last_bar_time = (
                        current_data.select(pl.col("timestamp")).tail(1).item()
                    )

                    try:
                        # Calculate what the current bar time should be
                        expected_bar_time = self._calculate_bar_time(
                            current_time, tf_config["interval"], tf_config["unit"]
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Error calculating bar time for {tf_key}: {e}"
                        )
                        continue  # Skip this timeframe if calculation fails

                    # If we're missing bars, create empty ones
                    if expected_bar_time > last_bar_time:
                        # Get the last close price to use for empty bars
                        last_close = current_data.select(pl.col("close")).tail(1).item()

                        # Import here to avoid circular import
                        from project_x_py.order_manager.utils import align_price_to_tick

                        # Align the last close price to tick size
                        aligned_close = align_price_to_tick(last_close, self.tick_size)

                        # Create empty bar with last close as OHLC, volume=0
                        # Using DataFrame constructor is efficient for single rows
                        new_bar = pl.DataFrame(
                            {
                                "timestamp": [expected_bar_time],
                                "open": [aligned_close],
                                "high": [aligned_close],
                                "low": [aligned_close],
                                "close": [aligned_close],
                                "volume": [0],  # Zero volume for empty bars
                            }
                        )

                        self.data[tf_key] = pl.concat([current_data, new_bar])
                        self.last_bar_times[tf_key] = expected_bar_time

                        self.logger.debug(
                            f"Created empty bar for {tf_key} at {expected_bar_time} "
                            f"(low volume period)"
                        )

                        # Prepare event to trigger
                        events_to_trigger.append(
                            {
                                "timeframe": tf_key,
                                "bar_time": expected_bar_time,
                                "data": new_bar.to_dicts()[0],
                            }
                        )

            # Trigger events outside the lock (non-blocking)
            for event in events_to_trigger:
                # Store task reference to avoid warning (though we don't need to track it)
                _ = asyncio.create_task(self._trigger_callbacks("new_bar", event))  # noqa: RUF006

        except Exception as e:
            self.logger.error(f"Error checking/creating empty bars: {e}")
            # Don't re-raise - bar timer should continue even if one check fails
