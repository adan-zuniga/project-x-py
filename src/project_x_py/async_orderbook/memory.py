"""
Memory management for the async orderbook module.

Handles cleanup strategies, memory statistics, and resource optimization
for high-frequency orderbook data processing.
"""

import asyncio
import gc
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_x_py.async_orderbook.base import AsyncOrderBookBase

import contextlib
import logging

from project_x_py.async_orderbook.types import MemoryConfig


class MemoryManager:
    """Manages memory usage and cleanup for async orderbook."""

    def __init__(self, orderbook: "AsyncOrderBookBase", config: MemoryConfig):
        self.orderbook = orderbook
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Memory statistics
        self.memory_stats: dict[str, Any] = {
            "last_cleanup": datetime.now(UTC),
            "total_trades": 0,
            "trades_cleaned": 0,
            "depth_cleaned": 0,
            "history_cleaned": 0,
        }

        # Cleanup task
        self._cleanup_task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the periodic cleanup task."""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            self.logger.info("Memory manager started")

    async def stop(self) -> None:
        """Stop the periodic cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None
        self.logger.info("Memory manager stopped")

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old data to manage memory usage."""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self.cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")

    async def cleanup_old_data(self) -> None:
        """Clean up old data based on configured limits."""
        async with self.orderbook.orderbook_lock:
            try:
                current_time = datetime.now(self.orderbook.timezone)
                self.memory_stats["last_cleanup"] = current_time

                # Clean up old trades
                trades_before = self.orderbook.recent_trades.height
                if trades_before > self.config.max_trades:
                    self.orderbook.recent_trades = self.orderbook.recent_trades.tail(
                        self.config.max_trades
                    )
                    trades_cleaned = trades_before - self.orderbook.recent_trades.height
                    self.memory_stats["trades_cleaned"] += trades_cleaned
                    self.logger.debug(f"Cleaned {trades_cleaned} old trades")

                # Clean up excessive depth entries
                bids_before = self.orderbook.orderbook_bids.height
                asks_before = self.orderbook.orderbook_asks.height

                if bids_before > self.config.max_depth_entries:
                    # Keep only the best N bids
                    self.orderbook.orderbook_bids = self.orderbook.orderbook_bids.sort(
                        "price", descending=True
                    ).head(self.config.max_depth_entries)
                    self.memory_stats["depth_cleaned"] += (
                        bids_before - self.orderbook.orderbook_bids.height
                    )

                if asks_before > self.config.max_depth_entries:
                    # Keep only the best N asks
                    self.orderbook.orderbook_asks = self.orderbook.orderbook_asks.sort(
                        "price"
                    ).head(self.config.max_depth_entries)
                    self.memory_stats["depth_cleaned"] += (
                        asks_before - self.orderbook.orderbook_asks.height
                    )

                # Clean up price level history
                await self._cleanup_price_history(current_time)

                # Clean up best price and spread history
                await self._cleanup_market_history()

                # Run garbage collection after major cleanup
                if (
                    self.memory_stats["trades_cleaned"]
                    + self.memory_stats["depth_cleaned"]
                    + self.memory_stats["history_cleaned"]
                ) > 1000:
                    gc.collect()
                    self.logger.debug("Garbage collection completed")

            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")

    async def _cleanup_price_history(self, current_time: datetime) -> None:
        """Clean up old price level history."""
        cutoff_time = current_time - timedelta(
            minutes=self.config.price_history_window_minutes
        )

        for key in list(self.orderbook.price_level_history.keys()):
            history = self.orderbook.price_level_history[key]

            # Remove old entries
            history[:] = [
                h for h in history if h.get("timestamp", current_time) > cutoff_time
            ]

            # Limit to max history per level
            if len(history) > self.config.max_history_per_level:
                removed = len(history) - self.config.max_history_per_level
                history[:] = history[-self.config.max_history_per_level :]
                self.memory_stats["history_cleaned"] += removed

            # Remove empty histories
            if not history:
                del self.orderbook.price_level_history[key]

    async def _cleanup_market_history(self) -> None:
        """Clean up market data history (best prices, spreads, etc.)."""
        # Best bid/ask history
        if len(self.orderbook.best_bid_history) > self.config.max_best_price_history:
            removed = (
                len(self.orderbook.best_bid_history)
                - self.config.max_best_price_history
            )
            self.orderbook.best_bid_history = self.orderbook.best_bid_history[
                -self.config.max_best_price_history :
            ]
            self.memory_stats["history_cleaned"] += removed

        if len(self.orderbook.best_ask_history) > self.config.max_best_price_history:
            removed = (
                len(self.orderbook.best_ask_history)
                - self.config.max_best_price_history
            )
            self.orderbook.best_ask_history = self.orderbook.best_ask_history[
                -self.config.max_best_price_history :
            ]
            self.memory_stats["history_cleaned"] += removed

        # Spread history
        if len(self.orderbook.spread_history) > self.config.max_spread_history:
            removed = (
                len(self.orderbook.spread_history) - self.config.max_spread_history
            )
            self.orderbook.spread_history = self.orderbook.spread_history[
                -self.config.max_spread_history :
            ]
            self.memory_stats["history_cleaned"] += removed

        # Delta history
        if len(self.orderbook.delta_history) > self.config.max_delta_history:
            removed = len(self.orderbook.delta_history) - self.config.max_delta_history
            self.orderbook.delta_history = self.orderbook.delta_history[
                -self.config.max_delta_history :
            ]
            self.memory_stats["history_cleaned"] += removed

    async def get_memory_stats(self) -> dict[str, Any]:
        """Get comprehensive memory usage statistics."""
        async with self.orderbook.orderbook_lock:
            return {
                "orderbook_bids_count": self.orderbook.orderbook_bids.height,
                "orderbook_asks_count": self.orderbook.orderbook_asks.height,
                "recent_trades_count": self.orderbook.recent_trades.height,
                "price_level_history_count": len(self.orderbook.price_level_history),
                "best_bid_history_count": len(self.orderbook.best_bid_history),
                "best_ask_history_count": len(self.orderbook.best_ask_history),
                "spread_history_count": len(self.orderbook.spread_history),
                "delta_history_count": len(self.orderbook.delta_history),
                "support_levels_count": len(self.orderbook.support_levels),
                "resistance_levels_count": len(self.orderbook.resistance_levels),
                "last_cleanup": self.memory_stats["last_cleanup"].timestamp()
                if self.memory_stats["last_cleanup"]
                else 0,
                "total_trades_processed": self.memory_stats["total_trades"],
                "trades_cleaned": self.memory_stats["trades_cleaned"],
                "depth_cleaned": self.memory_stats["depth_cleaned"],
                "history_cleaned": self.memory_stats["history_cleaned"],
                "memory_config": {
                    "max_trades": self.config.max_trades,
                    "max_depth_entries": self.config.max_depth_entries,
                    "cleanup_interval": self.config.cleanup_interval,
                },
            }
