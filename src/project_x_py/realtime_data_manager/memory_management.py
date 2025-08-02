"""Memory management and cleanup functionality for real-time data."""

import asyncio
import gc
import logging
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_x_py.realtime_data_manager.types import RealtimeDataManagerProtocol

logger = logging.getLogger(__name__)


class MemoryManagementMixin:
    """Mixin for memory management and optimization."""

    def __init__(self) -> None:
        """Initialize memory management attributes."""
        super().__init__()
        self._cleanup_task: asyncio.Task[None] | None = None

    async def _cleanup_old_data(self: "RealtimeDataManagerProtocol") -> None:
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

    async def _periodic_cleanup(self: "RealtimeDataManagerProtocol") -> None:
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

    def get_memory_stats(self: "RealtimeDataManagerProtocol") -> dict[str, Any]:
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

    async def stop_cleanup_task(self: "RealtimeDataManagerProtocol") -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    def start_cleanup_task(self: "RealtimeDataManagerProtocol") -> None:
        """Start the background cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
