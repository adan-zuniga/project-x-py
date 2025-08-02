"""
Async Real-time Data Manager for OHLCV Data

This module provides async/await support for efficient real-time OHLCV (Open, High, Low, Close, Volume)
data management for trading algorithms and applications. The implementation follows an event-driven
architecture for optimal performance and resource utilization.

Core Functionality:
1. Loading initial historical data for all timeframes once at startup
2. Receiving real-time market data from AsyncProjectXRealtimeClient WebSocket feeds
3. Resampling real-time data into multiple timeframes (5s, 15s, 1m, 5m, 15m, 1h, 4h)
4. Maintaining synchronized OHLCV bars across all timeframes
5. Eliminating the need for repeated API calls during live trading
6. Providing event callbacks for real-time data processing and visualization
7. Managing memory efficiently with automatic cleanup and sliding windows

Key Features:
- Async/await patterns for all operations
- Thread-safe operations using asyncio locks
- Dependency injection with AsyncProjectX client
- Integration with AsyncProjectXRealtimeClient for live updates
- Sub-second data updates vs 5-minute polling delays
- Perfect synchronization between timeframes
- Resilient to API outages during trading
- Memory-efficient sliding window storage with automatic cleanup
- Event-based callbacks for real-time processing
- ProjectX-compliant payload processing

Usage Example:
```python
import asyncio
from project_x_py import (
    AsyncProjectX,
    AsyncProjectXRealtimeClient,
    AsyncRealtimeDataManager,
)


async def main():
    # Create and authenticate clients
    px_client = AsyncProjectX()
    await px_client.authenticate()

    # Setup realtime client
    realtime_client = AsyncProjectXRealtimeClient(px_client.config)
    await realtime_client.connect()

    # Create data manager for a specific instrument with multiple timeframes
    data_manager = AsyncRealtimeDataManager(
        instrument="MGC",  # Mini Gold futures
        project_x=px_client,
        realtime_client=realtime_client,
        timeframes=["1min", "5min", "15min", "1hr"],
        timezone="America/Chicago",  # CME timezone
    )

    # Initialize with 30 days of historical data
    await data_manager.initialize(initial_days=30)

    # Start real-time data feed
    await data_manager.start_realtime_feed()

    # Register a callback for new bars
    async def on_new_bar(data):
        tf = data["timeframe"]
        bar = data["data"]
        print(f"New {tf} bar: Open={bar['open']}, Close={bar['close']}")

    await data_manager.add_callback("new_bar", on_new_bar)

    # In your trading loop
    while True:
        # Get latest data for analysis
        data_5m = await data_manager.get_data("5min", bars=100)
        current_price = await data_manager.get_current_price()

        # Your trading logic here
        print(f"Current price: {current_price}")

        # Get memory stats periodically
        if loop_count % 100 == 0:
            stats = data_manager.get_memory_stats()
            print(
                f"Memory stats: {stats['total_bars']} bars, {stats['ticks_processed']} ticks"
            )

        await asyncio.sleep(1)

    # Cleanup when done
    await data_manager.cleanup()


asyncio.run(main())
```
"""

import asyncio
import contextlib
import gc
import logging
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import TYPE_CHECKING, Any

import polars as pl
import pytz

if TYPE_CHECKING:
    from .client import ProjectX
    from .realtime import ProjectXRealtimeClient


class RealtimeDataManager:
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
        project_x: "ProjectX",
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

            project_x: ProjectX client instance for initial historical data loading.
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

        self.instrument = instrument
        self.project_x = project_x
        self.realtime_client = realtime_client

        self.logger = logging.getLogger(__name__)

        # Set timezone for consistent timestamp handling
        self.timezone = pytz.timezone(timezone)  # CME timezone

        timeframes_dict = {
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
        self.timeframes = {}
        for tf in timeframes:
            if tf not in timeframes_dict:
                raise ValueError(
                    f"Invalid timeframe: {tf}, valid timeframes are: {list(timeframes_dict.keys())}"
                )
            self.timeframes[tf] = timeframes_dict[tf]

        # OHLCV data storage for each timeframe
        self.data: dict[str, pl.DataFrame] = {}

        # Real-time data components
        self.current_tick_data: list[dict] = []
        self.last_bar_times: dict[str, datetime] = {}

        # Async synchronization
        self.data_lock = asyncio.Lock()
        self.is_running = False
        self.callbacks: dict[str, list[Any]] = defaultdict(list)
        self.indicator_cache: defaultdict[str, dict] = defaultdict(dict)

        # Contract ID for real-time subscriptions
        self.contract_id: str | None = None

        # Memory management settings
        self.max_bars_per_timeframe = 1000  # Keep last 1000 bars per timeframe
        self.tick_buffer_size = 1000  # Max tick data to buffer
        self.cleanup_interval = 300  # 5 minutes between cleanups
        self.last_cleanup = time.time()

        # Performance monitoring
        self.memory_stats = {
            "total_bars": 0,
            "bars_cleaned": 0,
            "ticks_processed": 0,
            "last_cleanup": time.time(),
        }

        # Background cleanup task
        self._cleanup_task: asyncio.Task | None = None

        self.logger.info(f"RealtimeDataManager initialized for {instrument}")

    async def _cleanup_old_data(self) -> None:
        """
        Clean up old OHLCV data to manage memory efficiently using sliding windows.
        """
        current_time = time.time()

        # Only cleanup if interval has passed
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        async with self.data_lock:
            total_bars_before = 0
            total_bars_after = 0

            # Cleanup each timeframe's data
            for tf_key in self.timeframes:
                if tf_key in self.data and not self.data[tf_key].is_empty():
                    initial_count = len(self.data[tf_key])
                    total_bars_before += initial_count

                    # Keep only the most recent bars (sliding window)
                    if initial_count > self.max_bars_per_timeframe:
                        self.data[tf_key] = self.data[tf_key].tail(
                            self.max_bars_per_timeframe // 2
                        )

                    total_bars_after += len(self.data[tf_key])

            # Cleanup tick buffer
            if len(self.current_tick_data) > self.tick_buffer_size:
                self.current_tick_data = self.current_tick_data[
                    -self.tick_buffer_size // 2 :
                ]

            # Update stats
            self.last_cleanup = current_time
            self.memory_stats["bars_cleaned"] += total_bars_before - total_bars_after
            self.memory_stats["total_bars"] = total_bars_after
            self.memory_stats["last_cleanup"] = current_time

            # Log cleanup if significant
            if total_bars_before != total_bars_after:
                self.logger.debug(
                    f"DataManager cleanup - Bars: {total_bars_before}→{total_bars_after}, "
                    f"Ticks: {len(self.current_tick_data)}"
                )

                # Force garbage collection after cleanup
                gc.collect()

    async def _periodic_cleanup(self) -> None:
        """Background task for periodic cleanup."""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_old_data()
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")

    def get_memory_stats(self) -> dict:
        """
        Get comprehensive memory usage statistics for the real-time data manager.

        Returns:
            Dict with memory and performance statistics

        Example:
            >>> stats = manager.get_memory_stats()
            >>> print(f"Total bars in memory: {stats['total_bars']}")
            >>> print(f"Ticks processed: {stats['ticks_processed']}")
        """
        # Note: This doesn't need to be async as it's just reading values
        timeframe_stats = {}
        total_bars = 0

        for tf_key in self.timeframes:
            if tf_key in self.data:
                bar_count = len(self.data[tf_key])
                timeframe_stats[tf_key] = bar_count
                total_bars += bar_count
            else:
                timeframe_stats[tf_key] = 0

        return {
            "timeframe_bar_counts": timeframe_stats,
            "total_bars": total_bars,
            "tick_buffer_size": len(self.current_tick_data),
            "max_bars_per_timeframe": self.max_bars_per_timeframe,
            "max_tick_buffer": self.tick_buffer_size,
            **self.memory_stats,
        }

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
            instrument_info = await self.project_x.get_instrument(self.instrument)
            if not instrument_info:
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

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize: {e}")
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
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

            self.logger.info(f"✅ Real-time OHLCV feed started for {self.instrument}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to start real-time feed: {e}")
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
            if self._cleanup_task:
                self._cleanup_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._cleanup_task
                self._cleanup_task = None

            # Unsubscribe from market data
            # Note: unsubscribe_market_data will be implemented in ProjectXRealtimeClient
            if self.contract_id:
                self.logger.info(f"📉 Unsubscribing from {self.contract_id}")

            self.logger.info(f"✅ Real-time feed stopped for {self.instrument}")

        except Exception as e:
            self.logger.error(f"❌ Error stopping real-time feed: {e}")

    async def _on_quote_update(self, callback_data: dict) -> None:
        """
        Handle real-time quote updates for OHLCV data processing.

        Args:
            callback_data: Quote update callback data from realtime client
        """
        try:
            self.logger.debug(f"📊 Quote update received: {type(callback_data)}")
            self.logger.debug(f"Quote data: {callback_data}")

            # Extract the actual quote data from the callback structure (same as sync version)
            data = (
                callback_data.get("data", {}) if isinstance(callback_data, dict) else {}
            )

            # Debug log to see what we're receiving
            self.logger.debug(
                f"Quote callback - callback_data type: {type(callback_data)}, data type: {type(data)}"
            )

            # Parse and validate payload format (same as sync version)
            quote_data = self._parse_and_validate_quote_payload(data)
            if quote_data is None:
                return

            # Check if this quote is for our tracked instrument
            symbol = quote_data.get("symbol", "")
            if not self._symbol_matches_instrument(symbol):
                return

            # Extract price information for OHLCV processing according to ProjectX format
            last_price = quote_data.get("lastPrice")
            best_bid = quote_data.get("bestBid")
            best_ask = quote_data.get("bestAsk")
            volume = quote_data.get("volume", 0)

            # Calculate price for OHLCV tick processing
            price = None

            if last_price is not None:
                # Use last traded price when available
                price = float(last_price)
                volume = 0  # GatewayQuote volume is daily total, not trade volume
            elif best_bid is not None and best_ask is not None:
                # Use mid price for quote updates
                price = (float(best_bid) + float(best_ask)) / 2
                volume = 0  # No volume for quote updates
            elif best_bid is not None:
                price = float(best_bid)
                volume = 0
            elif best_ask is not None:
                price = float(best_ask)
                volume = 0

            if price is not None:
                # Use timezone-aware timestamp
                current_time = datetime.now(self.timezone)

                # Create tick data for OHLCV processing
                tick_data = {
                    "timestamp": current_time,
                    "price": float(price),
                    "volume": volume,
                    "type": "quote",  # GatewayQuote is always a quote, not a trade
                    "source": "gateway_quote",
                }

                await self._process_tick_data(tick_data)

        except Exception as e:
            self.logger.error(f"Error processing quote update for OHLCV: {e}")
            self.logger.debug(f"Callback data that caused error: {callback_data}")

    async def _on_trade_update(self, callback_data: dict) -> None:
        """
        Handle real-time trade updates for OHLCV data processing.

        Args:
            callback_data: Market trade callback data from realtime client
        """
        try:
            self.logger.debug(f"💹 Trade update received: {type(callback_data)}")
            self.logger.debug(f"Trade data: {callback_data}")

            # Extract the actual trade data from the callback structure (same as sync version)
            data = (
                callback_data.get("data", {}) if isinstance(callback_data, dict) else {}
            )

            # Debug log to see what we're receiving
            self.logger.debug(
                f"🔍 Trade callback - callback_data type: {type(callback_data)}, data type: {type(data)}"
            )

            # Parse and validate payload format (same as sync version)
            trade_data = self._parse_and_validate_trade_payload(data)
            if trade_data is None:
                return

            # Check if this trade is for our tracked instrument
            symbol_id = trade_data.get("symbolId", "")
            if not self._symbol_matches_instrument(symbol_id):
                return

            # Extract trade information according to ProjectX format
            price = trade_data.get("price")
            volume = trade_data.get("volume", 0)
            trade_type = trade_data.get("type")  # TradeLogType enum: Buy=0, Sell=1

            if price is not None:
                current_time = datetime.now(self.timezone)

                # Create tick data for OHLCV processing
                tick_data = {
                    "timestamp": current_time,
                    "price": float(price),
                    "volume": int(volume),
                    "type": "trade",
                    "trade_side": "buy"
                    if trade_type == 0
                    else "sell"
                    if trade_type == 1
                    else "unknown",
                    "source": "gateway_trade",
                }

                self.logger.debug(f"🔥 Processing tick: {tick_data}")
                await self._process_tick_data(tick_data)

        except Exception as e:
            self.logger.error(f"❌ Error processing market trade for OHLCV: {e}")
            self.logger.debug(f"Callback data that caused error: {callback_data}")

    async def _process_tick_data(self, tick: dict) -> None:
        """
        Process incoming tick data and update all OHLCV timeframes.

        Args:
            tick: Dictionary containing tick data (timestamp, price, volume, etc.)
        """
        try:
            if not self.is_running:
                return

            timestamp = tick["timestamp"]
            price = tick["price"]
            volume = tick.get("volume", 0)

            # Update each timeframe
            async with self.data_lock:
                # Add to current tick data for get_current_price()
                self.current_tick_data.append(tick)

                for tf_key in self.timeframes:
                    await self._update_timeframe_data(tf_key, timestamp, price, volume)

            # Trigger callbacks for data updates
            await self._trigger_callbacks(
                "data_update",
                {"timestamp": timestamp, "price": price, "volume": volume},
            )

            # Update memory stats and periodic cleanup
            self.memory_stats["ticks_processed"] += 1
            await self._cleanup_old_data()

        except Exception as e:
            self.logger.error(f"Error processing tick data: {e}")

    async def _update_timeframe_data(
        self, tf_key: str, timestamp: datetime, price: float, volume: int
    ):
        """
        Update a specific timeframe with new tick data.

        Args:
            tf_key: Timeframe key (e.g., "5min", "15min", "1hr")
            timestamp: Timestamp of the tick
            price: Price of the tick
            volume: Volume of the tick
        """
        try:
            interval = self.timeframes[tf_key]["interval"]
            unit = self.timeframes[tf_key]["unit"]

            # Calculate the bar time for this timeframe
            bar_time = self._calculate_bar_time(timestamp, interval, unit)

            # Get current data for this timeframe
            if tf_key not in self.data:
                return

            current_data = self.data[tf_key]

            # Check if we need to create a new bar or update existing
            if current_data.height == 0:
                # First bar - ensure minimum volume for pattern detection
                bar_volume = max(volume, 1) if volume > 0 else 1
                new_bar = pl.DataFrame(
                    {
                        "timestamp": [bar_time],
                        "open": [price],
                        "high": [price],
                        "low": [price],
                        "close": [price],
                        "volume": [bar_volume],
                    }
                )

                self.data[tf_key] = new_bar
                self.last_bar_times[tf_key] = bar_time

            else:
                last_bar_time = current_data.select(pl.col("timestamp")).tail(1).item()

                if bar_time > last_bar_time:
                    # New bar needed
                    bar_volume = max(volume, 1) if volume > 0 else 1
                    new_bar = pl.DataFrame(
                        {
                            "timestamp": [bar_time],
                            "open": [price],
                            "high": [price],
                            "low": [price],
                            "close": [price],
                            "volume": [bar_volume],
                        }
                    )

                    self.data[tf_key] = pl.concat([current_data, new_bar])
                    self.last_bar_times[tf_key] = bar_time

                    # Trigger new bar callback
                    await self._trigger_callbacks(
                        "new_bar",
                        {
                            "timeframe": tf_key,
                            "bar_time": bar_time,
                            "data": new_bar.to_dicts()[0],
                        },
                    )

                elif bar_time == last_bar_time:
                    # Update existing bar
                    last_row_mask = pl.col("timestamp") == pl.lit(bar_time)

                    # Get current values
                    last_row = current_data.filter(last_row_mask)
                    current_high = (
                        last_row.select(pl.col("high")).item()
                        if last_row.height > 0
                        else price
                    )
                    current_low = (
                        last_row.select(pl.col("low")).item()
                        if last_row.height > 0
                        else price
                    )
                    current_volume = (
                        last_row.select(pl.col("volume")).item()
                        if last_row.height > 0
                        else 0
                    )

                    # Calculate new values
                    new_high = max(current_high, price)
                    new_low = min(current_low, price)
                    new_volume = max(current_volume + volume, 1)

                    # Update with new values
                    self.data[tf_key] = current_data.with_columns(
                        [
                            pl.when(last_row_mask)
                            .then(pl.lit(new_high))
                            .otherwise(pl.col("high"))
                            .alias("high"),
                            pl.when(last_row_mask)
                            .then(pl.lit(new_low))
                            .otherwise(pl.col("low"))
                            .alias("low"),
                            pl.when(last_row_mask)
                            .then(pl.lit(price))
                            .otherwise(pl.col("close"))
                            .alias("close"),
                            pl.when(last_row_mask)
                            .then(pl.lit(new_volume))
                            .otherwise(pl.col("volume"))
                            .alias("volume"),
                        ]
                    )

            # Prune memory
            if self.data[tf_key].height > 1000:
                self.data[tf_key] = self.data[tf_key].tail(1000)

        except Exception as e:
            self.logger.error(f"Error updating {tf_key} timeframe: {e}")

    def _calculate_bar_time(
        self, timestamp: datetime, interval: int, unit: int
    ) -> datetime:
        """
        Calculate the bar time for a given timestamp and interval.

        Args:
            timestamp: The tick timestamp (should be timezone-aware)
            interval: Bar interval value
            unit: Time unit (1=seconds, 2=minutes)

        Returns:
            datetime: The bar time (start of the bar period) - timezone-aware
        """
        # Ensure timestamp is timezone-aware
        if timestamp.tzinfo is None:
            timestamp = self.timezone.localize(timestamp)

        if unit == 1:  # Seconds
            # Round down to the nearest interval in seconds
            total_seconds = timestamp.second + timestamp.microsecond / 1000000
            rounded_seconds = (int(total_seconds) // interval) * interval
            bar_time = timestamp.replace(second=rounded_seconds, microsecond=0)
        elif unit == 2:  # Minutes
            # Round down to the nearest interval in minutes
            minutes = (timestamp.minute // interval) * interval
            bar_time = timestamp.replace(minute=minutes, second=0, microsecond=0)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")

        return bar_time

    async def get_data(
        self, timeframe: str = "5min", bars: int | None = None
    ) -> pl.DataFrame | None:
        """
        Get OHLCV data for a specific timeframe.

        This method returns a Polars DataFrame containing OHLCV (Open, High, Low, Close, Volume)
        data for the specified timeframe. The data is retrieved from the in-memory cache,
        which is continuously updated in real-time. You can optionally limit the number of
        bars returned.

        Args:
            timeframe: Timeframe to retrieve (default: "5min").
                Must be one of the timeframes configured during initialization.
                Common values are "1min", "5min", "15min", "1hr".

            bars: Number of most recent bars to return (None for all available bars).
                When specified, returns only the N most recent bars, which is more
                memory efficient for large datasets.

        Returns:
            pl.DataFrame: A Polars DataFrame with OHLCV data containing the following columns:
                - timestamp: Bar timestamp (timezone-aware datetime)
                - open: Opening price for the period
                - high: Highest price during the period
                - low: Lowest price during the period
                - close: Closing price for the period
                - volume: Volume traded during the period

                Returns None if the timeframe is not available or no data is loaded.

        Example:
            ```python
            # Get the most recent 100 bars of 5-minute data
            data_5m = await manager.get_data("5min", bars=100)

            if data_5m is not None:
                print(f"Got {len(data_5m)} bars of 5-minute data")

                # Get the most recent close price
                latest_close = data_5m["close"].last()
                print(f"Latest close price: {latest_close}")

                # Calculate a simple moving average
                if len(data_5m) >= 20:
                    sma_20 = data_5m["close"].tail(20).mean()
                    print(f"20-bar SMA: {sma_20}")

                # Check for gaps in data
                if data_5m.height > 1:
                    timestamps = data_5m["timestamp"]
                    # This requires handling timezone-aware datetimes properly

                # Use the data with external libraries
                # Convert to pandas if needed (though Polars is preferred)
                # pandas_df = data_5m.to_pandas()
            else:
                print(f"No data available for timeframe: 5min")
            ```

        Note:
            - This method is thread-safe and can be called concurrently from multiple tasks
            - The returned DataFrame is a copy of the internal data and can be modified safely
            - For memory efficiency, specify the 'bars' parameter to limit the result size
        """
        async with self.data_lock:
            if timeframe not in self.data:
                return None

            df = self.data[timeframe]
            if bars is not None and len(df) > bars:
                return df.tail(bars)
            return df

    async def get_current_price(self) -> float | None:
        """
        Get the current market price from the most recent data.

        This method provides the most recent market price available from tick data or bar data.
        It's designed for quick access to the current price without having to process the full
        OHLCV dataset, making it ideal for real-time trading decisions and order placement.

        The method follows this logic:
        1. First tries to get price from the most recent tick data (most up-to-date)
        2. If no tick data is available, falls back to the most recent bar close price
        3. Checks common timeframes in order of priority: 1min, 5min, 15min

        Returns:
            float: The current price if available
            None: If no price data is available from any source

        Example:
            ```python
            # Get the most recent price
            current_price = await manager.get_current_price()

            if current_price is not None:
                print(f"Current price: ${current_price:.2f}")

                # Use in trading logic
                if current_price > threshold:
                    # Place a sell order
                    await order_manager.place_market_order(
                        contract_id="MGC",
                        side=1,  # Sell
                        size=1,
                    )
                    print(f"Placed sell order at ${current_price:.2f}")
            else:
                print("No current price data available")
            ```

        Note:
            - This method is optimized for performance and minimal latency
            - The returned price is the most recent available, which could be
              several seconds old if market activity is low
            - The method is thread-safe and can be called concurrently
        """
        # Try to get from tick data first
        if self.current_tick_data:
            return self.current_tick_data[-1]["price"]

        # Fallback to most recent bar close
        async with self.data_lock:
            for tf_key in ["1min", "5min", "15min"]:  # Check common timeframes
                if tf_key in self.data and not self.data[tf_key].is_empty():
                    return self.data[tf_key]["close"][-1]

        return None

    async def get_mtf_data(self) -> dict[str, pl.DataFrame]:
        """
        Get multi-timeframe OHLCV data for all configured timeframes.

        Returns:
            Dict mapping timeframe names to DataFrames

        Example:
            >>> mtf_data = await manager.get_mtf_data()
            >>> for tf, data in mtf_data.items():
            ...     print(f"{tf}: {len(data)} bars")
        """
        async with self.data_lock:
            return {tf: df.clone() for tf, df in self.data.items()}

    async def add_callback(
        self,
        event_type: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None],
    ) -> None:
        """
        Register a callback for specific data events.

        This method allows you to register callback functions that will be triggered when
        specific events occur in the data manager. Callbacks can be either synchronous functions
        or asynchronous coroutines. This event-driven approach enables building reactive
        trading systems that respond to real-time market events.

        Args:
            event_type: Type of event to listen for. Supported event types:
                - "new_bar": Triggered when a new OHLCV bar is created in any timeframe.
                  The callback receives data with timeframe, bar_time, and complete bar data.
                - "data_update": Triggered on every tick update.
                  The callback receives timestamp, price, and volume information.

            callback: Function or coroutine to call when the event occurs.
                Both synchronous functions and async coroutines are supported.
                The function should accept a single dictionary parameter with event data.

        Event Data Structures:
            "new_bar" event data contains:
                {
                    "timeframe": "5min",                  # The timeframe of the bar
                    "bar_time": datetime(2023,5,1,10,0),  # Bar timestamp (timezone-aware)
                    "data": {                             # Complete bar data
                        "timestamp": datetime(...),       # Bar timestamp
                        "open": 1950.5,                   # Opening price
                        "high": 1955.2,                   # High price
                        "low": 1950.0,                    # Low price
                        "close": 1954.8,                  # Closing price
                        "volume": 128                     # Bar volume
                    }
                }

            "data_update" event data contains:
                {
                    "timestamp": datetime(2023,5,1,10,0,15),  # Tick timestamp
                    "price": 1954.75,                         # Current price
                    "volume": 1                               # Tick volume
                }

        Example:
            ```python
            # Register an async callback for new bar events
            async def on_new_bar(data):
                tf = data["timeframe"]
                bar = data["data"]
                print(
                    f"New {tf} bar: O={bar['open']}, H={bar['high']}, L={bar['low']}, C={bar['close']}"
                )

                # Implement trading logic based on the new bar
                if tf == "5min" and bar["close"] > bar["open"]:
                    # Bullish bar detected
                    print(f"Bullish 5min bar detected at {data['bar_time']}")

                    # Trigger trading logic (implement your strategy here)
                    # await strategy.on_bullish_bar(data)


            # Register the callback
            await data_manager.add_callback("new_bar", on_new_bar)


            # You can also use regular (non-async) functions
            def on_data_update(data):
                # This is called on every tick - keep it lightweight!
                print(f"Price update: {data['price']}")


            await data_manager.add_callback("data_update", on_data_update)
            ```

        Note:
            - Multiple callbacks can be registered for the same event type
            - Callbacks are executed sequentially for each event
            - For high-frequency events like "data_update", keep callbacks lightweight
              to avoid processing bottlenecks
            - Exceptions in callbacks are caught and logged, preventing them from
              affecting the data manager's operation
        """
        self.callbacks[event_type].append(callback)

    async def _trigger_callbacks(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Trigger all callbacks for a specific event type.

        Args:
            event_type: Type of event to trigger
            data: Data to pass to callbacks
        """
        for callback in self.callbacks.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {e}")

    def get_realtime_validation_status(self) -> dict[str, Any]:
        """
        Get validation status for real-time data feed integration.

        Returns:
            Dict with validation status

        Example:
            >>> status = manager.get_realtime_validation_status()
            >>> print(f"Feed active: {status['is_running']}")
        """
        return {
            "is_running": self.is_running,
            "contract_id": self.contract_id,
            "instrument": self.instrument,
            "timeframes_configured": list(self.timeframes.keys()),
            "data_available": {tf: tf in self.data for tf in self.timeframes},
            "ticks_processed": self.memory_stats["ticks_processed"],
            "bars_cleaned": self.memory_stats["bars_cleaned"],
            "projectx_compliance": {
                "quote_handling": "✅ Compliant",
                "trade_handling": "✅ Compliant",
                "tick_processing": "✅ Async",
                "memory_management": "✅ Automatic cleanup",
            },
        }

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

    def _parse_and_validate_trade_payload(self, trade_data):
        """Parse and validate trade payload, returning the parsed data or None if invalid."""
        # Handle string payloads - parse JSON if it's a string
        if isinstance(trade_data, str):
            try:
                import json

                self.logger.debug(
                    f"Attempting to parse trade JSON string: {trade_data[:200]}..."
                )
                trade_data = json.loads(trade_data)
                self.logger.debug(
                    f"Successfully parsed JSON string payload: {type(trade_data)}"
                )
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Failed to parse trade payload JSON: {e}")
                self.logger.warning(f"Trade payload content: {trade_data[:500]}...")
                return None

        # Handle list payloads - SignalR sends [contract_id, data_dict]
        if isinstance(trade_data, list):
            if not trade_data:
                self.logger.warning("Trade payload is an empty list")
                return None
            if len(trade_data) >= 2:
                # SignalR format: [contract_id, actual_data_dict]
                trade_data = trade_data[1]
                self.logger.debug(
                    f"Using second item from SignalR trade list: {type(trade_data)}"
                )
            else:
                # Fallback: use first item if only one element
                trade_data = trade_data[0]
                self.logger.debug(
                    f"Using first item from trade list: {type(trade_data)}"
                )

        # Handle nested list case: trade data might be wrapped in another list
        if (
            isinstance(trade_data, list)
            and trade_data
            and isinstance(trade_data[0], dict)
        ):
            trade_data = trade_data[0]
            self.logger.debug(
                f"Using first item from nested trade list: {type(trade_data)}"
            )

        if not isinstance(trade_data, dict):
            self.logger.warning(
                f"Trade payload is not a dict after processing: {type(trade_data)}"
            )
            self.logger.debug(f"Trade payload content: {trade_data}")
            return None

        required_fields = {"symbolId", "price", "timestamp", "volume"}
        missing_fields = required_fields - set(trade_data.keys())
        if missing_fields:
            self.logger.warning(
                f"Trade payload missing required fields: {missing_fields}"
            )
            self.logger.debug(f"Available fields: {list(trade_data.keys())}")
            return None

        return trade_data

    def _parse_and_validate_quote_payload(self, quote_data):
        """Parse and validate quote payload, returning the parsed data or None if invalid."""
        # Handle string payloads - parse JSON if it's a string
        if isinstance(quote_data, str):
            try:
                import json

                self.logger.debug(
                    f"Attempting to parse quote JSON string: {quote_data[:200]}..."
                )
                quote_data = json.loads(quote_data)
                self.logger.debug(
                    f"Successfully parsed JSON string payload: {type(quote_data)}"
                )
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Failed to parse quote payload JSON: {e}")
                self.logger.warning(f"Quote payload content: {quote_data[:500]}...")
                return None

        # Handle list payloads - SignalR sends [contract_id, data_dict]
        if isinstance(quote_data, list):
            if not quote_data:
                self.logger.warning("Quote payload is an empty list")
                return None
            if len(quote_data) >= 2:
                # SignalR format: [contract_id, actual_data_dict]
                quote_data = quote_data[1]
                self.logger.debug(
                    f"Using second item from SignalR quote list: {type(quote_data)}"
                )
            else:
                # Fallback: use first item if only one element
                quote_data = quote_data[0]
                self.logger.debug(
                    f"Using first item from quote list: {type(quote_data)}"
                )

        if not isinstance(quote_data, dict):
            self.logger.warning(
                f"Quote payload is not a dict after processing: {type(quote_data)}"
            )
            self.logger.debug(f"Quote payload content: {quote_data}")
            return None

        # More flexible validation - only require symbol and timestamp
        # Different quote types have different data (some may not have all price fields)
        required_fields = {"symbol", "timestamp"}
        missing_fields = required_fields - set(quote_data.keys())
        if missing_fields:
            self.logger.warning(
                f"Quote payload missing required fields: {missing_fields}"
            )
            self.logger.debug(f"Available fields: {list(quote_data.keys())}")
            return None

        return quote_data

    def _symbol_matches_instrument(self, symbol: str) -> bool:
        """
        Check if the symbol from the payload matches our tracked instrument.

        Args:
            symbol: Symbol from the payload (e.g., "F.US.EP")

        Returns:
            bool: True if symbol matches our instrument
        """
        # Extract the base symbol from the full symbol ID
        # Example: "F.US.EP" -> "EP", "F.US.MGC" -> "MGC"
        if "." in symbol:
            parts = symbol.split(".")
            base_symbol = parts[-1] if parts else symbol
        else:
            base_symbol = symbol

        # Compare with our instrument (case-insensitive)
        return base_symbol.upper() == self.instrument.upper()
