"""
Core RealtimeDataManager class for efficient real-time OHLCV data management.

This module provides the main RealtimeDataManager class that handles real-time
market data processing across multiple timeframes.
"""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any

import polars as pl
import pytz

from project_x_py.client.base import ProjectXBase
from project_x_py.exceptions import (
    ProjectXDataError,
    ProjectXError,
    ProjectXInstrumentError,
)
from project_x_py.models import Instrument
from project_x_py.realtime_data_manager.callbacks import CallbackMixin
from project_x_py.realtime_data_manager.data_access import DataAccessMixin
from project_x_py.realtime_data_manager.data_processing import DataProcessingMixin
from project_x_py.realtime_data_manager.memory_management import MemoryManagementMixin
from project_x_py.realtime_data_manager.validation import ValidationMixin

if TYPE_CHECKING:
    from project_x_py.client import ProjectXBase
    from project_x_py.realtime import ProjectXRealtimeClient


class RealtimeDataManager(
    DataProcessingMixin,
    MemoryManagementMixin,
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
        timeframes: list[str] | None = None,
        timezone: str = "America/Chicago",
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

            timeframes: List of timeframes to track (default: ["5min"] if None provided).
                Available timeframes include:
                - Seconds: "1sec", "5sec", "10sec", "15sec", "30sec"
                - Minutes: "1min", "5min", "15min", "30min"
                - Hours: "1hr", "4hr"
                - Days/Weeks/Months: "1day", "1week", "1month"

            timezone: Timezone for timestamp handling (default: "America/Chicago").
                This timezone is used for all bar calculations and should typically be set to
                the exchange timezone for the instrument (e.g., "America/Chicago" for CME).

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

        self.instrument: str = instrument
        self.project_x: ProjectXBase = project_x
        self.realtime_client: ProjectXRealtimeClient = realtime_client

        self.logger = logging.getLogger(__name__)

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

        # Initialize timeframes as dict mapping timeframe names to configs
        self.timeframes: dict[str, dict[str, Any]] = {}
        for tf in timeframes:
            if tf not in timeframes_dict:
                raise ValueError(
                    f"Invalid timeframe: {tf}, valid timeframes are: {list(timeframes_dict.keys())}"
                )
            self.timeframes[tf] = timeframes_dict[tf]

        # OHLCV data storage for each timeframe
        self.data: dict[str, pl.DataFrame] = {}

        # Real-time data components
        self.current_tick_data: list[dict[str, Any]] = []
        self.last_bar_times: dict[str, datetime] = {}

        # Async synchronization
        self.data_lock: asyncio.Lock = asyncio.Lock()
        self.is_running: bool = False
        self.callbacks: dict[str, list[Any]] = defaultdict(list)
        self.indicator_cache: defaultdict[str, dict[str, Any]] = defaultdict(dict)

        # Contract ID for real-time subscriptions
        self.contract_id: str | None = None

        # Memory management settings
        self.max_bars_per_timeframe: int = 1000  # Keep last 1000 bars per timeframe
        self.tick_buffer_size: int = 1000  # Max tick data to buffer
        self.cleanup_interval: float = 300.0  # 5 minutes between cleanups
        self.last_cleanup: float = time.time()

        # Performance monitoring
        self.memory_stats: dict[str, Any] = {
            "total_bars": 0,
            "bars_cleaned": 0,
            "ticks_processed": 0,
            "last_cleanup": time.time(),
        }

        # Background cleanup task
        self._cleanup_task: asyncio.Task[None] | None = None

        self.logger.info(f"RealtimeDataManager initialized for {instrument}")

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
        try:
            self.logger.info(
                f"Initializing RealtimeDataManager for {self.instrument}..."
            )

            # Get the contract ID for the instrument
            instrument_info: Instrument | None = await self.project_x.get_instrument(
                self.instrument
            )
            if instrument_info is None:
                self.logger.error(f"❌ Instrument {self.instrument} not found")
                return False

            # Store the exact contract ID for real-time subscriptions
            self.contract_id = instrument_info.id

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
                        self.logger.info(
                            f"✅ Loaded {len(bars)} bars for {tf_key} timeframe"
                        )
                    else:
                        self.logger.warning(f"⚠️ No data loaded for {tf_key} timeframe")

            self.logger.info(
                f"✅ RealtimeDataManager initialized for {self.instrument}"
            )
            return True

        except ProjectXInstrumentError as e:
            self.logger.error(f"❌ Failed to initialize - instrument error: {e}")
            return False
        except ProjectXDataError as e:
            self.logger.error(f"❌ Failed to initialize - data error: {e}")
            return False
        except ProjectXError as e:
            self.logger.error(f"❌ Failed to initialize - ProjectX error: {e}")
            return False

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
        try:
            if self.is_running:
                self.logger.warning("⚠️ Real-time feed already running")
                return True

            if not self.contract_id:
                self.logger.error("❌ Contract ID not set - call initialize() first")
                return False

            # Register callbacks first
            await self.realtime_client.add_callback(
                "quote_update", self._on_quote_update
            )
            await self.realtime_client.add_callback(
                "market_trade",
                self._on_trade_update,  # Use market_trade event name
            )

            # Subscribe to market data using the contract ID
            self.logger.info(f"📡 Subscribing to market data for {self.contract_id}")
            subscription_success = await self.realtime_client.subscribe_market_data(
                [self.contract_id]
            )

            if not subscription_success:
                self.logger.error("❌ Failed to subscribe to market data")
                return False

            self.logger.info(
                f"✅ Successfully subscribed to market data for {self.contract_id}"
            )

            self.is_running = True

            # Start cleanup task
            self.start_cleanup_task()

            self.logger.info(f"✅ Real-time OHLCV feed started for {self.instrument}")
            return True

        except RuntimeError as e:
            self.logger.error(f"❌ Failed to start real-time feed - runtime error: {e}")
            return False
        except TimeoutError as e:
            self.logger.error(f"❌ Failed to start real-time feed - timeout: {e}")
            return False

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
            self.callbacks.clear()
            self.indicator_cache.clear()

        self.logger.info("✅ RealtimeDataManager cleanup completed")
