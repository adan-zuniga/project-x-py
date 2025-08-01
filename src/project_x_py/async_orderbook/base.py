"""
Base async orderbook functionality.

This module contains the core orderbook data structures and basic operations
like maintaining bid/ask levels, best prices, and spread calculations.
"""

import asyncio
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import polars as pl
import pytz  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from project_x_py.async_client import AsyncProjectX

import logging

from project_x_py.async_orderbook.memory import MemoryManager
from project_x_py.async_orderbook.types import (
    DEFAULT_TIMEZONE,
    CallbackType,
    DomType,
    MemoryConfig,
)
from project_x_py.exceptions import ProjectXError


class AsyncOrderBookBase:
    """Base class for async orderbook with core functionality."""

    def __init__(
        self,
        instrument: str,
        project_x: "AsyncProjectX | None" = None,
        timezone_str: str = DEFAULT_TIMEZONE,
    ):
        """
        Initialize the async orderbook base.

        Args:
            instrument: Trading instrument symbol
            project_x: Optional ProjectX client for tick size lookup
            timezone_str: Timezone for timestamps (default: America/Chicago)
        """
        self.instrument = instrument
        self.project_x = project_x
        self.timezone = pytz.timezone(timezone_str)
        self.logger = logging.getLogger(__name__)

        # Cache instrument tick size during initialization
        self._tick_size: Decimal | None = None

        # Async locks for thread-safe operations
        self.orderbook_lock = asyncio.Lock()
        self._callback_lock = asyncio.Lock()

        # Memory configuration
        self.memory_config = MemoryConfig()
        self.memory_manager = MemoryManager(self, self.memory_config)

        # Level 2 orderbook storage with Polars DataFrames
        self.orderbook_bids = pl.DataFrame(
            {
                "price": [],
                "volume": [],
                "timestamp": [],
            },
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime(time_zone=timezone_str),
            },
        )

        self.orderbook_asks = pl.DataFrame(
            {
                "price": [],
                "volume": [],
                "timestamp": [],
            },
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime(time_zone=timezone_str),
            },
        )

        # Trade flow storage (Type 5 - actual executions)
        self.recent_trades = pl.DataFrame(
            {
                "price": [],
                "volume": [],
                "timestamp": [],
                "side": [],  # "buy" or "sell" inferred from price movement
                "spread_at_trade": [],
                "mid_price_at_trade": [],
                "best_bid_at_trade": [],
                "best_ask_at_trade": [],
                "order_type": [],
            },
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime(time_zone=timezone_str),
                "side": pl.Utf8,
                "spread_at_trade": pl.Float64,
                "mid_price_at_trade": pl.Float64,
                "best_bid_at_trade": pl.Float64,
                "best_ask_at_trade": pl.Float64,
                "order_type": pl.Utf8,
            },
        )

        # Orderbook metadata
        self.last_orderbook_update: datetime | None = None
        self.last_level2_data: dict[str, Any] | None = None
        self.level2_update_count = 0

        # Order type statistics
        self.order_type_stats: dict[str, int] = defaultdict(int)

        # Callbacks for orderbook events
        self.callbacks: dict[str, list[CallbackType]] = defaultdict(list)

        # Price level refresh history for advanced analytics
        self.price_level_history: dict[tuple[float, str], list[dict[str, Any]]] = (
            defaultdict(list)
        )

        # Best bid/ask tracking
        self.best_bid_history: list[dict[str, Any]] = []
        self.best_ask_history: list[dict[str, Any]] = []
        self.spread_history: list[dict[str, Any]] = []

        # Support/resistance level tracking
        self.support_levels: list[dict[str, Any]] = []
        self.resistance_levels: list[dict[str, Any]] = []

        # Cumulative delta tracking
        self.cumulative_delta = 0
        self.delta_history: list[dict[str, Any]] = []

        # VWAP tracking
        self.vwap_numerator = 0.0
        self.vwap_denominator = 0
        self.session_start_time = datetime.now(self.timezone).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Market microstructure analytics
        self.trade_flow_stats: dict[str, int] = defaultdict(int)

    def _map_trade_type(self, type_code: int) -> str:
        """Map ProjectX DomType codes to human-readable trade types."""
        try:
            return DomType(type_code).name
        except ValueError:
            return f"Unknown_{type_code}"

    async def get_tick_size(self) -> Decimal:
        """Get the tick size for the instrument."""
        if self._tick_size is None and self.project_x:
            try:
                contract_details = await self.project_x.get_instrument(self.instrument)
                if contract_details and hasattr(contract_details, "tickSize"):
                    self._tick_size = Decimal(str(contract_details.tickSize))
                else:
                    self._tick_size = Decimal("0.01")  # Default fallback
            except Exception as e:
                self.logger.warning(f"Failed to get tick size: {e}, using default 0.01")
                self._tick_size = Decimal("0.01")
        return self._tick_size or Decimal("0.01")

    def _get_best_bid_ask_unlocked(self) -> dict[str, Any]:
        """
        Internal method to get best bid/ask without acquiring lock.
        Must be called with orderbook_lock already held.
        """
        try:
            best_bid = None
            best_ask = None

            # Get best bid (highest price)
            if self.orderbook_bids.height > 0:
                bid_with_volume = self.orderbook_bids.filter(pl.col("volume") > 0).sort(
                    "price", descending=True
                )
                if bid_with_volume.height > 0:
                    best_bid = float(bid_with_volume.row(0)[0])

            # Get best ask (lowest price)
            if self.orderbook_asks.height > 0:
                ask_with_volume = self.orderbook_asks.filter(pl.col("volume") > 0).sort(
                    "price", descending=False
                )
                if ask_with_volume.height > 0:
                    best_ask = float(ask_with_volume.row(0)[0])

            # Calculate spread
            spread = None
            if best_bid is not None and best_ask is not None:
                spread = best_ask - best_bid

            # Update history
            current_time = datetime.now(self.timezone)
            if best_bid is not None:
                self.best_bid_history.append(
                    {
                        "price": best_bid,
                        "timestamp": current_time,
                    }
                )

            if best_ask is not None:
                self.best_ask_history.append(
                    {
                        "price": best_ask,
                        "timestamp": current_time,
                    }
                )

            if spread is not None:
                self.spread_history.append(
                    {
                        "spread": spread,
                        "timestamp": current_time,
                    }
                )

            return {
                "bid": best_bid,
                "ask": best_ask,
                "spread": spread,
                "timestamp": current_time,
            }

        except Exception as e:
            self.logger.error(f"Error getting best bid/ask: {e}")
            return {"bid": None, "ask": None, "spread": None, "timestamp": None}

    async def get_best_bid_ask(self) -> dict[str, Any]:
        """
        Get current best bid and ask prices with spread calculation.

        Returns:
            Dict containing bid, ask, spread, and timestamp
        """
        async with self.orderbook_lock:
            return self._get_best_bid_ask_unlocked()

    async def get_bid_ask_spread(self) -> float | None:
        """Get the current bid-ask spread."""
        best_prices = await self.get_best_bid_ask()
        return best_prices.get("spread")

    def _get_orderbook_bids_unlocked(self, levels: int = 10) -> pl.DataFrame:
        """Internal method to get orderbook bids without acquiring lock."""
        try:
            if self.orderbook_bids.height == 0:
                return pl.DataFrame(
                    {"price": [], "volume": [], "timestamp": []},
                    schema={
                        "price": pl.Float64,
                        "volume": pl.Int64,
                        "timestamp": pl.Datetime(time_zone=self.timezone.zone),
                    },
                )

            # Get top N bid levels by price
            return (
                self.orderbook_bids.filter(pl.col("volume") > 0)
                .sort("price", descending=True)
                .head(levels)
            )
        except Exception as e:
            self.logger.error(f"Error getting orderbook bids: {e}")
            return pl.DataFrame()

    async def get_orderbook_bids(self, levels: int = 10) -> pl.DataFrame:
        """Get orderbook bids up to specified levels."""
        async with self.orderbook_lock:
            return self._get_orderbook_bids_unlocked(levels)

    def _get_orderbook_asks_unlocked(self, levels: int = 10) -> pl.DataFrame:
        """Internal method to get orderbook asks without acquiring lock."""
        try:
            if self.orderbook_asks.height == 0:
                return pl.DataFrame(
                    {"price": [], "volume": [], "timestamp": []},
                    schema={
                        "price": pl.Float64,
                        "volume": pl.Int64,
                        "timestamp": pl.Datetime(time_zone=self.timezone.zone),
                    },
                )

            # Get top N ask levels by price
            return (
                self.orderbook_asks.filter(pl.col("volume") > 0)
                .sort("price", descending=False)
                .head(levels)
            )
        except Exception as e:
            self.logger.error(f"Error getting orderbook asks: {e}")
            return pl.DataFrame()

    async def get_orderbook_asks(self, levels: int = 10) -> pl.DataFrame:
        """Get orderbook asks up to specified levels."""
        async with self.orderbook_lock:
            return self._get_orderbook_asks_unlocked(levels)

    async def get_orderbook_snapshot(self, levels: int = 10) -> dict[str, Any]:
        """Get a complete snapshot of the current orderbook state."""
        async with self.orderbook_lock:
            try:
                # Get best prices - use unlocked version since we already hold the lock
                best_prices = self._get_best_bid_ask_unlocked()

                # Get bid and ask levels - use unlocked versions
                bids = self._get_orderbook_bids_unlocked(levels)
                asks = self._get_orderbook_asks_unlocked(levels)

                # Convert to lists of dicts
                bid_levels = bids.to_dicts() if not bids.is_empty() else []
                ask_levels = asks.to_dicts() if not asks.is_empty() else []

                # Calculate totals
                total_bid_volume = bids["volume"].sum() if not bids.is_empty() else 0
                total_ask_volume = asks["volume"].sum() if not asks.is_empty() else 0

                # Calculate imbalance
                imbalance = None
                if total_bid_volume > 0 or total_ask_volume > 0:
                    imbalance = (total_bid_volume - total_ask_volume) / (
                        total_bid_volume + total_ask_volume
                    )

                return {
                    "instrument": self.instrument,
                    "timestamp": datetime.now(self.timezone),
                    "best_bid": best_prices["bid"],
                    "best_ask": best_prices["ask"],
                    "spread": best_prices["spread"],
                    "mid_price": (
                        (best_prices["bid"] + best_prices["ask"]) / 2
                        if best_prices["bid"] and best_prices["ask"]
                        else None
                    ),
                    "bids": bid_levels,
                    "asks": ask_levels,
                    "total_bid_volume": int(total_bid_volume),
                    "total_ask_volume": int(total_ask_volume),
                    "bid_count": len(bid_levels),
                    "ask_count": len(ask_levels),
                    "imbalance": imbalance,
                    "update_count": self.level2_update_count,
                    "last_update": self.last_orderbook_update,
                }

            except Exception as e:
                self.logger.error(f"Error getting orderbook snapshot: {e}")
                raise ProjectXError(f"Failed to get orderbook snapshot: {e}") from e

    async def get_recent_trades(self, count: int = 100) -> list[dict[str, Any]]:
        """Get recent trades from the orderbook."""
        async with self.orderbook_lock:
            try:
                if self.recent_trades.height == 0:
                    return []

                # Get most recent trades
                recent = self.recent_trades.tail(count)
                return recent.to_dicts()

            except Exception as e:
                self.logger.error(f"Error getting recent trades: {e}")
                return []

    async def get_order_type_statistics(self) -> dict[str, int]:
        """Get statistics about different order types processed."""
        async with self.orderbook_lock:
            return self.order_type_stats.copy()

    async def add_callback(self, event_type: str, callback: CallbackType) -> None:
        """Register a callback for orderbook events."""
        async with self._callback_lock:
            self.callbacks[event_type].append(callback)
            self.logger.debug(f"Added orderbook callback for {event_type}")

    async def remove_callback(self, event_type: str, callback: CallbackType) -> None:
        """Remove a registered callback."""
        async with self._callback_lock:
            if event_type in self.callbacks and callback in self.callbacks[event_type]:
                self.callbacks[event_type].remove(callback)
                self.logger.debug(f"Removed orderbook callback for {event_type}")

    async def _trigger_callbacks(self, event_type: str, data: dict[str, Any]) -> None:
        """Trigger all callbacks for a specific event type."""
        callbacks = self.callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {e}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.memory_manager.stop()
        async with self._callback_lock:
            self.callbacks.clear()
        self.logger.info("AsyncOrderBook cleanup completed")
