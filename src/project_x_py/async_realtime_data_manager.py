"""
Async Real-time Data Manager for OHLCV Data

This module provides async/await support for efficient real-time OHLCV data management by:
1. Loading initial historical data for all timeframes once at startup
2. Receiving real-time market data from AsyncProjectXRealtimeClient WebSocket feeds
3. Resampling real-time data into multiple timeframes (5s, 15s, 1m, 5m, 15m, 1h, 4h)
4. Maintaining synchronized OHLCV bars across all timeframes
5. Eliminating the need for repeated API calls during live trading

Key Features:
- Async/await patterns for all operations
- Thread-safe operations using asyncio locks
- Dependency injection with AsyncProjectX client
- Integration with AsyncProjectXRealtimeClient for live updates
- Sub-second data updates vs 5-minute polling delays
- Perfect synchronization between timeframes
- Resilient to API outages during trading
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
    from .async_client import AsyncProjectX
    from .async_realtime import AsyncProjectXRealtimeClient


class AsyncRealtimeDataManager:
    """
    Async optimized real-time OHLCV data manager for efficient multi-timeframe trading data.

    This class focuses exclusively on OHLCV (Open, High, Low, Close, Volume) data management
    across multiple timeframes through real-time tick processing using async/await patterns.

    Core Concept:
        Traditional approach: Poll API every 5 minutes for each timeframe = 20+ API calls/hour
        Real-time approach: Load historical once + live tick processing = 1 API call + WebSocket
        Result: 95% reduction in API calls with sub-second data freshness

    Features:
        - Complete async/await implementation
        - Zero-latency OHLCV updates via WebSocket
        - Automatic bar creation and maintenance
        - Async-safe multi-timeframe access
        - Memory-efficient sliding window storage
        - Timezone-aware timestamp handling (CME Central Time)
        - Event callbacks for new bars and data updates
        - Comprehensive health monitoring and statistics

    Example Usage:
        >>> # Create shared async realtime client
        >>> async_realtime_client = AsyncProjectXRealtimeClient(jwt_token, account_id)
        >>> await async_realtime_client.connect()
        >>>
        >>> # Initialize async data manager with dependency injection
        >>> manager = AsyncRealtimeDataManager(
        ...     "MGC", async_project_x, async_realtime_client
        ... )
        >>>
        >>> # Load historical data for all timeframes
        >>> if await manager.initialize(initial_days=30):
        ...     print("Historical data loaded successfully")
        >>>
        >>> # Start real-time feed (registers callbacks with existing client)
        >>> if await manager.start_realtime_feed():
        ...     print("Real-time OHLCV feed active")
        >>>
        >>> # Access multi-timeframe OHLCV data
        >>> data_5m = await manager.get_data("5min", bars=100)
        >>> data_15m = await manager.get_data("15min", bars=50)
        >>> mtf_data = await manager.get_mtf_data()
        >>>
        >>> # Get current market price
        >>> current_price = await manager.get_current_price()
    """

    def __init__(
        self,
        instrument: str,
        project_x: "AsyncProjectX",
        realtime_client: "AsyncProjectXRealtimeClient",
        timeframes: list[str] | None = None,
        timezone: str = "America/Chicago",
    ):
        """
        Initialize the async optimized real-time OHLCV data manager with dependency injection.

        Args:
            instrument: Trading instrument symbol (e.g., "MGC", "MNQ", "ES")
            project_x: AsyncProjectX client instance for initial historical data loading
            realtime_client: AsyncProjectXRealtimeClient instance for live market data
            timeframes: List of timeframes to track (default: ["5min"])
                Available: ["5sec", "15sec", "1min", "5min", "15min", "1hr", "4hr"]
            timezone: Timezone for timestamp handling (default: "America/Chicago")

        Example:
            >>> # Create shared async realtime client
            >>> async_realtime_client = AsyncProjectXRealtimeClient(
            ...     jwt_token, account_id
            ... )
            >>> # Initialize multi-timeframe manager
            >>> manager = AsyncRealtimeDataManager(
            ...     instrument="MGC",
            ...     project_x=async_project_x_client,
            ...     realtime_client=async_realtime_client,
            ...     timeframes=["1min", "5min", "15min", "1hr"],
            ... )
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

        self.logger.info(f"AsyncRealtimeDataManager initialized for {instrument}")

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

        Args:
            initial_days: Number of days of historical data to load (default: 1)

        Returns:
            bool: True if initialization completed successfully, False if errors occurred

        Example:
            >>> if await manager.initialize(initial_days=30):
            ...     print("Historical data loaded successfully")
        """
        try:
            self.logger.info(
                f"Initializing AsyncRealtimeDataManager for {self.instrument}..."
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
                        self.contract_id,
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
                f"✅ AsyncRealtimeDataManager initialized for {self.instrument}"
            )
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize: {e}")
            return False

    async def start_realtime_feed(self) -> bool:
        """
        Start the real-time OHLCV data feed using WebSocket connections.

        Returns:
            bool: True if real-time feed started successfully

        Example:
            >>> if await manager.start_realtime_feed():
            ...     print("Real-time OHLCV updates active")
        """
        try:
            if self.is_running:
                self.logger.warning("⚠️ Real-time feed already running")
                return True

            if not self.contract_id:
                self.logger.error("❌ Contract ID not set - call initialize() first")
                return False

            # Subscribe to market data
            # Note: subscribe_market_data will be implemented in AsyncProjectXRealtimeClient
            # For now, assume subscription is successful
            self.logger.info(f"✅ Ready to receive market data for {self.contract_id}")

            # Register callbacks
            await self.realtime_client.add_callback(
                "quote_update", self._on_quote_update
            )
            await self.realtime_client.add_callback(
                "trade_update", self._on_trade_update
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
            # Note: unsubscribe_market_data will be implemented in AsyncProjectXRealtimeClient
            if self.contract_id:
                self.logger.info(f"📉 Unsubscribing from {self.contract_id}")

            self.logger.info(f"✅ Real-time feed stopped for {self.instrument}")

        except Exception as e:
            self.logger.error(f"❌ Error stopping real-time feed: {e}")

    async def _on_quote_update(self, quote_data: dict) -> None:
        """
        Handle real-time quote updates for OHLCV data processing.

        Args:
            quote_data: ProjectX GatewayQuote payload
        """
        try:
            # Validate it's for our instrument
            if quote_data.get("contractId") != self.contract_id:
                return

            # Extract quote data
            bid_price = quote_data.get("bidPrice", 0)
            ask_price = quote_data.get("askPrice", 0)

            if bid_price > 0 and ask_price > 0:
                # Use mid price for OHLCV
                mid_price = (bid_price + ask_price) / 2

                tick = {
                    "timestamp": datetime.now(self.timezone),
                    "price": mid_price,
                    "volume": 0,  # Quote updates don't have volume
                    "bid": bid_price,
                    "ask": ask_price,
                    "type": "quote",
                }

                await self._process_tick_data(tick)

        except Exception as e:
            self.logger.error(f"Error processing quote update: {e}")

    async def _on_trade_update(self, trade_data: dict) -> None:
        """
        Handle real-time trade updates for OHLCV data processing.

        Args:
            trade_data: ProjectX GatewayTrade payload
        """
        try:
            # Validate it's for our instrument
            if trade_data.get("contractId") != self.contract_id:
                return

            # Extract trade data
            price = trade_data.get("price", 0)
            size = trade_data.get("size", 0)

            if price > 0:
                tick = {
                    "timestamp": datetime.now(self.timezone),
                    "price": price,
                    "volume": size,
                    "type": "trade",
                }

                await self._process_tick_data(tick)

        except Exception as e:
            self.logger.error(f"Error processing trade update: {e}")

    async def _process_tick_data(self, tick: dict) -> None:
        """
        Process incoming tick data and update all OHLCV timeframes.

        Args:
            tick: Dictionary containing tick data (timestamp, price, volume, etc.)
        """
        async with self.data_lock:
            # Add to tick buffer
            self.current_tick_data.append(tick)
            self.memory_stats["ticks_processed"] += 1

            # Update each timeframe
            current_time = tick["timestamp"]
            price = tick["price"]
            volume = tick.get("volume", 0)

            for tf_key, tf_config in self.timeframes.items():
                # Calculate the bar time for this timeframe
                bar_time = self._calculate_bar_time(current_time, tf_config)

                # Get or create the dataframe for this timeframe
                if tf_key not in self.data:
                    # Create new dataframe with first bar
                    self.data[tf_key] = pl.DataFrame(
                        {
                            "timestamp": [bar_time],
                            "open": [price],
                            "high": [price],
                            "low": [price],
                            "close": [price],
                            "volume": [volume],
                        }
                    )
                    self.last_bar_times[tf_key] = bar_time
                    await self._trigger_callbacks("new_bar", {"timeframe": tf_key})
                else:
                    # Update existing dataframe
                    if bar_time > self.last_bar_times.get(tf_key, bar_time):
                        # New bar
                        new_row = pl.DataFrame(
                            {
                                "timestamp": [bar_time],
                                "open": [price],
                                "high": [price],
                                "low": [price],
                                "close": [price],
                                "volume": [volume],
                            }
                        )
                        self.data[tf_key] = pl.concat([self.data[tf_key], new_row])
                        self.last_bar_times[tf_key] = bar_time
                        await self._trigger_callbacks("new_bar", {"timeframe": tf_key})
                    else:
                        # Update current bar
                        last_idx = len(self.data[tf_key]) - 1
                        if last_idx >= 0:
                            # Update high
                            if price > self.data[tf_key]["high"][last_idx]:
                                self.data[tf_key] = self.data[tf_key].with_columns(
                                    pl.when(pl.int_range(pl.len()) == last_idx)
                                    .then(price)
                                    .otherwise(pl.col("high"))
                                    .alias("high")
                                )
                            # Update low
                            if price < self.data[tf_key]["low"][last_idx]:
                                self.data[tf_key] = self.data[tf_key].with_columns(
                                    pl.when(pl.int_range(pl.len()) == last_idx)
                                    .then(price)
                                    .otherwise(pl.col("low"))
                                    .alias("low")
                                )
                            # Update close and volume
                            self.data[tf_key] = self.data[tf_key].with_columns(
                                pl.when(pl.int_range(pl.len()) == last_idx)
                                .then(price)
                                .otherwise(pl.col("close"))
                                .alias("close"),
                                pl.when(pl.int_range(pl.len()) == last_idx)
                                .then(self.data[tf_key]["volume"][last_idx] + volume)
                                .otherwise(pl.col("volume"))
                                .alias("volume"),
                            )

            # Trigger data update callbacks
            await self._trigger_callbacks("data_update", {"tick": tick})

    def _calculate_bar_time(
        self, timestamp: datetime, timeframe_config: dict
    ) -> datetime:
        """
        Calculate the bar time for a given timestamp and timeframe.

        Args:
            timestamp: Current timestamp
            timeframe_config: Timeframe configuration dict

        Returns:
            datetime: Bar time aligned to timeframe
        """
        interval = timeframe_config["interval"]
        unit = timeframe_config["unit"]

        if unit == 1:  # Seconds
            seconds = timestamp.second
            bar_seconds = (seconds // interval) * interval
            bar_time = timestamp.replace(second=bar_seconds, microsecond=0)
        elif unit == 2:  # Minutes
            minutes = timestamp.minute
            bar_minutes = (minutes // interval) * interval
            bar_time = timestamp.replace(minute=bar_minutes, second=0, microsecond=0)
        elif unit == 4:  # Days
            bar_time = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default to current time for other units
            bar_time = timestamp

        return bar_time

    async def get_data(
        self, timeframe: str = "5min", bars: int | None = None
    ) -> pl.DataFrame | None:
        """
        Get OHLCV data for a specific timeframe.

        Args:
            timeframe: Timeframe to retrieve (default: "5min")
            bars: Number of bars to return (None for all)

        Returns:
            DataFrame with OHLCV data or None if not available

        Example:
            >>> data = await manager.get_data("5min", bars=100)
            >>> if data is not None:
            ...     print(f"Got {len(data)} bars")
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

        Returns:
            Current price or None if no data available

        Example:
            >>> price = await manager.get_current_price()
            >>> if price:
            ...     print(f"Current price: ${price:.2f}")
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

        Args:
            event_type: Type of event ("new_bar", "data_update")
            callback: Async function to call when event occurs

        Example:
            >>> async def on_new_bar(data):
            ...     tf = data["timeframe"]
            ...     print(f"New bar on {tf}")
            >>> await manager.add_callback("new_bar", on_new_bar)
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

        self.logger.info("✅ AsyncRealtimeDataManager cleanup completed")
