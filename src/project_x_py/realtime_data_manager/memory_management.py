"""
Memory management and cleanup functionality for real-time data.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides memory management and cleanup functionality for real-time data processing.
    Implements efficient memory management with sliding window storage, automatic cleanup,
    and comprehensive statistics tracking to prevent memory leaks and optimize performance.

Key Features:
    - Automatic memory cleanup with configurable intervals
    - Sliding window storage for efficient memory usage
    - Background cleanup tasks with proper error handling
    - Comprehensive memory statistics and monitoring
    - Garbage collection optimization
    - Thread-safe memory operations

Memory Management Capabilities:
    - Automatic cleanup of old OHLCV data with sliding windows
    - Tick buffer management with size limits
    - Background periodic cleanup tasks
    - Memory statistics tracking and monitoring
    - Garbage collection optimization after cleanup
    - Error handling and recovery for memory issues

Example Usage:
    ```python
    # V3: Memory management with async patterns
    async with ProjectX.from_env() as client:
        await client.authenticate()

        # V3: Create manager with memory configuration
        manager = RealtimeDataManager(
            instrument="MNQ",
            project_x=client,
            realtime_client=realtime_client,
            timeframes=["1min", "5min"],
            max_bars_per_timeframe=500,  # V3: Configurable limits
            tick_buffer_size=100,
        )

        # V3: Access memory statistics asynchronously
        stats = await manager.get_memory_stats()
        print(f"Total bars in memory: {stats['total_bars']}")
        print(f"Total data points: {stats['total_data_points']}")
        print(f"Ticks processed: {stats['ticks_processed']}")
        print(f"Bars cleaned: {stats['bars_cleaned']}")

        # V3: Check timeframe-specific statistics
        for tf, count in stats["timeframe_bar_counts"].items():
            print(f"{tf}: {count} bars")

        # V3: Monitor memory health
        if stats["total_data_points"] > 10000:
            print("Warning: High memory usage detected")
            await manager.cleanup()  # Force cleanup

        # V3: Memory management happens automatically
        # Background cleanup task runs periodically
    ```

Memory Management Strategy:
    - Sliding window: Keep only recent data (configurable limits)
    - Automatic cleanup: Periodic cleanup of old data
    - Tick buffering: Limited tick data storage for current price access
    - Garbage collection: Force GC after significant cleanup operations
    - Statistics tracking: Comprehensive monitoring of memory usage

Performance Characteristics:
    - Minimal memory footprint with sliding window storage
    - Automatic cleanup prevents memory leaks
    - Background tasks with proper error handling
    - Efficient garbage collection optimization
    - Thread-safe operations with proper locking

Configuration:
    - max_bars_per_timeframe: Maximum bars to keep per timeframe (default: 1000)
    - tick_buffer_size: Maximum tick data to buffer (default: 1000)
    - cleanup_interval: Time between cleanup operations (default: 300 seconds)

See Also:
    - `realtime_data_manager.core.RealtimeDataManager`
    - `realtime_data_manager.callbacks.CallbackMixin`
    - `realtime_data_manager.data_access.DataAccessMixin`
    - `realtime_data_manager.data_processing.DataProcessingMixin`
    - `realtime_data_manager.validation.ValidationMixin`
"""

import asyncio
import gc
import logging
import time
from collections import deque
from contextlib import suppress
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_x_py.types.stats_types import RealtimeDataManagerStats

if TYPE_CHECKING:
    from asyncio import Lock

    import polars as pl

logger = logging.getLogger(__name__)


class MemoryManagementMixin:
    """Mixin for memory management and optimization."""

    # Type hints for mypy - these attributes are provided by the main class
    if TYPE_CHECKING:
        logger: logging.Logger
        last_cleanup: float
        cleanup_interval: float
        data_lock: Lock
        timeframes: dict[str, dict[str, Any]]
        data: dict[str, pl.DataFrame]
        max_bars_per_timeframe: int
        current_tick_data: list[dict[str, Any]] | deque[dict[str, Any]]
        tick_buffer_size: int
        memory_stats: dict[str, Any]
        is_running: bool

        # Optional methods from overflow mixin
        async def _check_overflow_needed(self, timeframe: str) -> bool: ...
        async def _overflow_to_disk(self, timeframe: str) -> None: ...
        def get_overflow_stats(self) -> dict[str, Any]: ...

    def __init__(self) -> None:
        """Initialize memory management attributes."""
        super().__init__()
        self._cleanup_task: asyncio.Task[None] | None = None

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

                    # Check if overflow is needed (if mixin is available)
                    if hasattr(
                        self, "_check_overflow_needed"
                    ) and await self._check_overflow_needed(tf_key):
                        await self._overflow_to_disk(tf_key)
                        # Data has been overflowed, update count
                        total_bars_after += len(self.data[tf_key])
                        continue

                    # Keep only the most recent bars (sliding window)
                    if initial_count > self.max_bars_per_timeframe:
                        self.data[tf_key] = self.data[tf_key].tail(
                            self.max_bars_per_timeframe // 2
                        )

                    total_bars_after += len(self.data[tf_key])

            # Cleanup tick buffer - deque handles its own cleanup with maxlen
            # No manual cleanup needed for deque with maxlen

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
            except asyncio.CancelledError:
                # Task cancellation is expected during shutdown
                self.logger.debug("Periodic cleanup task cancelled")
                raise
            except MemoryError as e:
                self.logger.error(f"Memory error during cleanup: {e}")
                # Force immediate garbage collection
                import gc

                gc.collect()
            except RuntimeError as e:
                self.logger.error(f"Runtime error in periodic cleanup: {e}")
                # Don't re-raise runtime errors to keep the cleanup task running

    def get_memory_stats(self) -> "RealtimeDataManagerStats":
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

        # Update current statistics
        self.memory_stats["total_bars_stored"] = total_bars
        self.memory_stats["buffer_utilization"] = (
            len(self.current_tick_data) / self.tick_buffer_size
            if self.tick_buffer_size > 0
            else 0.0
        )

        # Calculate memory usage estimate (rough approximation)
        estimated_memory_mb = (total_bars * 0.001) + (
            len(self.current_tick_data) * 0.0001
        )  # Very rough estimate
        self.memory_stats["memory_usage_mb"] = estimated_memory_mb

        # Add overflow stats if available
        overflow_stats = {}
        if hasattr(self, "get_overflow_stats"):
            overflow_stats = self.get_overflow_stats()

        return {
            "bars_processed": self.memory_stats["bars_processed"],
            "ticks_processed": self.memory_stats["ticks_processed"],
            "quotes_processed": self.memory_stats["quotes_processed"],
            "trades_processed": self.memory_stats["trades_processed"],
            "timeframe_stats": self.memory_stats["timeframe_stats"],
            "avg_processing_time_ms": self.memory_stats["avg_processing_time_ms"],
            "data_latency_ms": self.memory_stats["data_latency_ms"],
            "buffer_utilization": self.memory_stats["buffer_utilization"],
            "total_bars_stored": self.memory_stats["total_bars_stored"],
            "memory_usage_mb": self.memory_stats["memory_usage_mb"],
            "compression_ratio": self.memory_stats["compression_ratio"],
            "updates_per_minute": self.memory_stats["updates_per_minute"],
            "last_update": (
                self.memory_stats["last_update"].isoformat()
                if self.memory_stats["last_update"]
                else None
            ),
            "data_freshness_seconds": self.memory_stats["data_freshness_seconds"],
            "data_validation_errors": self.memory_stats["data_validation_errors"],
            "connection_interruptions": self.memory_stats["connection_interruptions"],
            "recovery_attempts": self.memory_stats["recovery_attempts"],
            "overflow_stats": overflow_stats,
        }

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
