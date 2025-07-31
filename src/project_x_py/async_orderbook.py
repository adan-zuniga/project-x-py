#!/usr/bin/env python3
"""
Async OrderBook Manager for Real-time Market Data

This module provides async/await support for comprehensive orderbook management and analysis:
1. Real-time Level 2 market depth processing with async callbacks
2. Trade flow analysis and execution tracking
3. Advanced market microstructure analytics
4. Iceberg order detection using statistical analysis
5. Support/resistance level identification
6. Market imbalance and liquidity analysis

Key Features:
- Async/await patterns for all operations
- Thread-safe operations using asyncio locks
- Polars DataFrame-based storage for efficient analysis
- Advanced institutional-grade order flow analytics
- Statistical significance testing for pattern recognition
- Real-time market maker and iceberg detection
- Comprehensive liquidity and depth analysis

Based on the synchronous OrderBook implementation but with full async support.
"""

import asyncio
import gc
import logging
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import TYPE_CHECKING, Any, Optional

import polars as pl
import pytz

if TYPE_CHECKING:
    from .async_client import AsyncProjectX
    from .async_realtime import AsyncProjectXRealtimeClient


class AsyncOrderBook:
    """
    Async advanced orderbook manager for real-time market depth and trade flow analysis.

    This class provides institutional-grade orderbook analytics with async/await support:
    - Real-time Level 2 market depth processing
    - Trade execution flow analysis
    - Iceberg order detection with statistical confidence
    - Dynamic support/resistance identification
    - Market imbalance and liquidity metrics
    - Volume profile and cumulative delta analysis

    The orderbook maintains separate bid and ask sides with full depth,
    tracks all trade executions, and provides advanced analytics for
    algorithmic trading strategies - all with async patterns.
    """

    def __init__(
        self,
        instrument: str,
        timezone: str = "America/Chicago",
        client: Optional["AsyncProjectX"] = None,
    ):
        """
        Initialize the async advanced orderbook manager for real-time market depth analysis.

        Creates an async-safe orderbook with Level 2 market depth tracking,
        trade flow analysis, and advanced analytics for institutional trading.
        Uses Polars DataFrames for high-performance data operations.

        Args:
            instrument: Trading instrument symbol (e.g., "MGC", "MNQ", "ES")
            timezone: Timezone for timestamp handling (default: "America/Chicago")
                Supports any pytz timezone string
            client: AsyncProjectX client instance for instrument metadata (optional)

        Example:
            >>> # Create async orderbook for gold futures
            >>> orderbook = AsyncOrderBook("MGC", client=async_project_x_client)
            >>> # Create orderbook with custom timezone
            >>> orderbook = AsyncOrderBook(
            ...     "ES", timezone="America/New_York", client=async_project_x_client
            ... )
            >>> # Initialize with real-time data
            >>> success = await orderbook.initialize(async_realtime_client)
        """
        self.instrument = instrument
        self.timezone = pytz.timezone(timezone)
        self.client = client
        self.logger = logging.getLogger(__name__)

        # Cache instrument tick size during initialization
        self.tick_size = None  # Will be fetched asynchronously

        # Async-safe locks for concurrent access
        self.orderbook_lock = asyncio.Lock()

        # Memory management settings
        self.max_trades = 10000  # Maximum trades to keep in memory
        self.max_depth_entries = 1000  # Maximum depth entries per side
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()

        # Performance monitoring
        self.memory_stats = {
            "total_trades": 0,
            "trades_cleaned": 0,
            "last_cleanup": time.time(),
        }

        # Level 2 orderbook storage with Polars DataFrames
        self.orderbook_bids: pl.DataFrame = pl.DataFrame(
            {"price": [], "volume": [], "timestamp": [], "type": []},
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime("us"),
                "type": pl.Utf8,
            },
        )

        self.orderbook_asks: pl.DataFrame = pl.DataFrame(
            {"price": [], "volume": [], "timestamp": [], "type": []},
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime("us"),
                "type": pl.Utf8,
            },
        )

        # Trade flow storage (Type 5 - actual executions)
        self.recent_trades: pl.DataFrame = pl.DataFrame(
            {
                "price": [],
                "volume": [],
                "timestamp": [],
                "side": [],  # "buy" or "sell" inferred from price movement
                "spread_at_trade": [],  # Spread when trade occurred
                "mid_price_at_trade": [],  # Mid price when trade occurred
                "best_bid_at_trade": [],  # Best bid when trade occurred
                "best_ask_at_trade": [],  # Best ask when trade occurred
                "order_type": [],  # Mapped trade type name
            },
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime("us"),
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
        self.last_level2_data: dict | None = None
        self.level2_update_count = 0

        # Statistics for different order types
        self.order_type_stats = {
            "type_1_count": 0,  # Ask
            "type_2_count": 0,  # Bid
            "type_3_count": 0,  # BestAsk
            "type_4_count": 0,  # BestBid
            "type_5_count": 0,  # Trade
            "type_6_count": 0,  # Reset
            "type_7_count": 0,  # Low
            "type_8_count": 0,  # High
            "type_9_count": 0,  # NewBestBid
            "type_10_count": 0,  # NewBestAsk
            "type_11_count": 0,  # Fill
            "other_types": 0,  # Unknown/other types
            "skipped_updates": 0,  # Skipped updates
            "integrity_fixes": 0,  # Orderbook integrity fixes
        }

        # Callbacks for orderbook events
        self.callbacks: dict[str, list[Any]] = defaultdict(list)

        # Price level refresh history for iceberg detection
        # Key: (price, side), Value: list of volume updates with timestamps
        self.price_level_history: dict[tuple[float, str], list[dict]] = defaultdict(
            list
        )
        self.max_history_per_level = 50  # Keep last 50 updates per price level
        self.price_history_window_minutes = 30  # Keep history for 30 minutes

        self.logger.info(f"AsyncOrderBook initialized for {instrument}")

    def _map_trade_type(self, type_code: int) -> str:
        """Map ProjectX trade type codes to readable names."""
        type_mapping = {
            0: "Unknown",
            1: "Ask Order",
            2: "Bid Order",
            3: "Best Ask",
            4: "Best Bid",
            5: "Trade",
            6: "Reset",
            7: "Session Low",
            8: "Session High",
            9: "New Best Bid",
            10: "New Best Ask",
            11: "Fill",
        }
        return type_mapping.get(type_code, f"Type {type_code}")

    async def initialize(
        self, realtime_client: Optional["AsyncProjectXRealtimeClient"] = None
    ) -> bool:
        """
        Initialize the AsyncOrderBook with optional real-time capabilities.

        This method follows the same pattern as AsyncOrderManager and AsyncPositionManager,
        allowing automatic setup of real-time market data callbacks for seamless
        integration with live market depth, trade flow, and quote updates.

        Args:
            realtime_client: Optional AsyncProjectXRealtimeClient for live market data

        Returns:
            bool: True if initialization successful

        Example:
            >>> orderbook = AsyncOrderBook("MGC")
            >>> success = await orderbook.initialize(async_realtime_client)
            >>> if success:
            ...     # OrderBook will now automatically receive market depth updates
            ...     snapshot = await orderbook.get_orderbook_snapshot()
        """
        try:
            # Fetch instrument tick size if client is available
            if self.client:
                self.tick_size = await self._fetch_instrument_tick_size()

            # Set up real-time integration if provided
            if realtime_client:
                self.realtime_client = realtime_client
                await self._setup_realtime_callbacks()
                self.logger.info(
                    "✅ AsyncOrderBook initialized with real-time market data capabilities"
                )
            else:
                self.logger.info("✅ AsyncOrderBook initialized (manual data mode)")

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize AsyncOrderBook: {e}")
            return False

    async def _fetch_instrument_tick_size(self) -> float:
        """
        Fetch the instrument tick size from the client.

        Returns the tick size for the instrument, or a default of 0.25
        if the instrument info is not available.
        """
        if not self.client:
            return 0.25  # Default tick size

        try:
            instrument_info = await self.client.get_instrument(self.instrument)
            if instrument_info and hasattr(instrument_info, "tickSize"):
                return float(instrument_info.tickSize)
        except Exception as e:
            self.logger.warning(f"Could not fetch tick size: {e}")

        return 0.25  # Default tick size

    async def _setup_realtime_callbacks(self):
        """Set up callbacks for real-time market data processing."""
        if not hasattr(self, "realtime_client") or not self.realtime_client:
            return

        # Register for market depth events (primary orderbook data)
        # This includes trades as type 5 entries in the depth data
        await self.realtime_client.add_callback(
            "market_depth", self._on_market_depth_update
        )

        # NOTE: We do NOT register for market_trade events separately anymore
        # because trades are already included in market_depth as type 5 entries.
        # Registering for both would cause double-counting of trade volumes.

        # Register for quote updates (for best bid/ask tracking)
        await self.realtime_client.add_callback("quote_update", self._on_quote_update)

        self.logger.info("🔄 Real-time market data callbacks registered")

    async def _on_market_depth_update(self, data: dict):
        """Handle real-time market depth updates."""
        try:
            # Filter for this instrument
            contract_id = data.get("contract_id", "")
            if not self._symbol_matches_instrument(contract_id):
                return

            # Process the market depth data
            await self.process_market_depth(data)

            # Trigger any registered callbacks
            await self._trigger_callbacks(
                "market_depth_processed",
                {
                    "contract_id": contract_id,
                    "update_count": self.level2_update_count,
                    "timestamp": datetime.now(self.timezone),
                },
            )

        except Exception as e:
            self.logger.error(f"Error processing market depth update: {e}")

    async def _on_quote_update(self, data: dict):
        """Handle real-time quote updates."""
        try:
            # Filter for this instrument
            contract_id = data.get("contractId", "")
            if not self._symbol_matches_instrument(contract_id):
                return

            # Extract quote data
            bid_price = data.get("bidPrice", 0)
            ask_price = data.get("askPrice", 0)
            bid_volume = data.get("bidVolume", 0)
            ask_volume = data.get("askVolume", 0)

            if bid_price > 0 and ask_price > 0:
                # Update best bid/ask in orderbook
                async with self.orderbook_lock:
                    timestamp = datetime.now(self.timezone).replace(tzinfo=None)

                    # Update bid side
                    if bid_volume > 0:
                        self.orderbook_bids = self._update_price_level(
                            self.orderbook_bids, bid_price, bid_volume, timestamp, "bid"
                        )

                    # Update ask side
                    if ask_volume > 0:
                        self.orderbook_asks = self._update_price_level(
                            self.orderbook_asks, ask_price, ask_volume, timestamp, "ask"
                        )

        except Exception as e:
            self.logger.error(f"Error processing quote update: {e}")

    def _symbol_matches_instrument(self, contract_id: str) -> bool:
        """Check if a contract ID matches this orderbook's instrument."""
        if not contract_id:
            return False
        # Extract base symbol from contract ID (e.g., "MGC-H25" -> "MGC")
        base_symbol = contract_id.split("-")[0]
        return base_symbol.upper() == self.instrument.upper()

    def _update_price_level(
        self,
        orderbook_side: pl.DataFrame,
        price: float,
        volume: int,
        timestamp: datetime,
        side: str,
    ) -> pl.DataFrame:
        """Update a price level in the orderbook."""
        # This is a helper method that doesn't need to be async
        # It's called within locked sections, so it's safe

        # Ensure timestamp is timezone-naive for Polars compatibility
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)

        if volume == 0:
            # Remove price level
            return orderbook_side.filter(pl.col("price") != price)
        else:
            # Update or add price level
            if len(orderbook_side) > 0:
                mask = orderbook_side["price"] == price
                if mask.any():
                    # Update existing level
                    return orderbook_side.with_columns(
                        [
                            pl.when(mask)
                            .then(volume)
                            .otherwise(pl.col("volume"))
                            .alias("volume"),
                            pl.when(mask)
                            .then(timestamp)
                            .otherwise(pl.col("timestamp"))
                            .alias("timestamp"),
                        ]
                    )

            # Add new level
            new_row = pl.DataFrame(
                {
                    "price": [price],
                    "volume": [volume],
                    "timestamp": [timestamp],
                    "type": [side],
                },
                schema={
                    "price": pl.Float64,
                    "volume": pl.Int64,
                    "timestamp": pl.Datetime("us"),
                    "type": pl.Utf8,
                },
            )
            if len(orderbook_side) == 0:
                return new_row
            return pl.concat([orderbook_side, new_row])

    async def process_market_depth(self, data: dict) -> None:
        """
        Process incoming market depth data to update the orderbook.

        This method handles Level 2 market depth updates, including:
        - Bid and ask side updates
        - Trade executions (type 5)
        - Best bid/ask changes
        - Orderbook resets
        - Session highs/lows

        Args:
            data: Market depth data from ProjectX containing:
                - contract_id: Contract identifier
                - data: List of DOM entries with price, volume, type
                - timestamp: Update timestamp

        Example:
            >>> depth_data = {
            ...     "contract_id": "MGC-H25",
            ...     "data": [
            ...         {"price": 2045.0, "volume": 10, "type": 2},  # Bid
            ...         {"price": 2046.0, "volume": 15, "type": 1},  # Ask
            ...         {"price": 2045.5, "volume": 5, "type": 5},  # Trade
            ...     ],
            ... }
            >>> await orderbook.process_market_depth(depth_data)
        """
        try:
            # Process each market depth entry
            async with self.orderbook_lock:
                current_time = datetime.now(self.timezone).replace(tzinfo=None)
                entries = data.get("data", [])

                for entry in entries:
                    price = float(entry.get("price", 0))
                    volume = int(entry.get("volume", 0))
                    entry_type = int(entry.get("type", 0))

                    # Skip invalid entries
                    if price <= 0:
                        continue

                    # Update statistics
                    type_key = f"type_{entry_type}_count"
                    if type_key in self.order_type_stats:
                        self.order_type_stats[type_key] += 1
                    else:
                        self.order_type_stats["other_types"] += 1

                    # Process based on type
                    if entry_type == 1:  # Ask
                        self.orderbook_asks = self._update_price_level(
                            self.orderbook_asks, price, volume, current_time, "ask"
                        )
                    elif entry_type == 2:  # Bid
                        self.orderbook_bids = self._update_price_level(
                            self.orderbook_bids, price, volume, current_time, "bid"
                        )
                    elif entry_type == 5:  # Trade
                        await self._process_trade(price, volume, current_time)
                    elif entry_type == 6:  # Reset
                        self.orderbook_bids = pl.DataFrame()
                        self.orderbook_asks = pl.DataFrame()
                        self.logger.info("Orderbook reset")

                self.level2_update_count += 1
                self.last_orderbook_update = current_time
                self.last_level2_data = data

                # Cleanup old data periodically
                if current_time.timestamp() - self.last_cleanup > self.cleanup_interval:
                    await self._cleanup_old_data()

        except Exception as e:
            self.logger.error(f"Error processing market depth: {e}")

    async def _process_trade(
        self, price: float, volume: int, timestamp: datetime
    ) -> None:
        """Process a trade execution."""
        # Get current best bid/ask for context
        best_bid, best_ask = await self.get_best_bid_ask()
        spread = best_ask - best_bid if best_bid and best_ask else 0
        mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else price

        # Determine trade side based on price relative to mid
        side = "buy" if price >= mid_price else "sell"

        # Create trade record
        trade_record = pl.DataFrame(
            {
                "price": [price],
                "volume": [volume],
                "timestamp": [timestamp],
                "side": [side],
                "spread_at_trade": [spread],
                "mid_price_at_trade": [mid_price],
                "best_bid_at_trade": [best_bid if best_bid else 0],
                "best_ask_at_trade": [best_ask if best_ask else 0],
                "order_type": ["Trade"],
            },
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime("us"),
                "side": pl.Utf8,
                "spread_at_trade": pl.Float64,
                "mid_price_at_trade": pl.Float64,
                "best_bid_at_trade": pl.Float64,
                "best_ask_at_trade": pl.Float64,
                "order_type": pl.Utf8,
            },
        )

        # Add to recent trades
        self.recent_trades = pl.concat([self.recent_trades, trade_record])
        self.memory_stats["total_trades"] += 1

        # Trim if needed
        if len(self.recent_trades) > self.max_trades:
            self.recent_trades = self.recent_trades.tail(self.max_trades // 2)

    async def _cleanup_old_data(self) -> None:
        """Clean up old data to manage memory."""
        current_time = time.time()

        # Cleanup old price level history
        cutoff_time = datetime.now(self.timezone) - timedelta(
            minutes=self.price_history_window_minutes
        )
        keys_to_remove = []
        for key, history in self.price_level_history.items():
            # Filter out old entries
            filtered_history = [h for h in history if h["timestamp"] > cutoff_time]
            if filtered_history:
                self.price_level_history[key] = filtered_history[
                    -self.max_history_per_level :
                ]
            else:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.price_level_history[key]

        # Trim orderbook depth if needed
        if len(self.orderbook_bids) > self.max_depth_entries:
            self.orderbook_bids = self.orderbook_bids.sort(
                "price", descending=True
            ).head(self.max_depth_entries)
        if len(self.orderbook_asks) > self.max_depth_entries:
            self.orderbook_asks = self.orderbook_asks.sort("price").head(
                self.max_depth_entries
            )

        self.last_cleanup = current_time
        self.memory_stats["last_cleanup"] = current_time

        # Force garbage collection
        gc.collect()

    async def get_orderbook_snapshot(self, levels: int = 10) -> dict[str, Any]:
        """
        Get a snapshot of the current orderbook state.

        Args:
            levels: Number of price levels to include (default: 10)

        Returns:
            Dict containing bid/ask levels, spread, and metadata

        Example:
            >>> snapshot = await orderbook.get_orderbook_snapshot(levels=5)
            >>> print(f"Best bid: {snapshot['best_bid']}")
            >>> print(f"Best ask: {snapshot['best_ask']}")
            >>> print(f"Spread: {snapshot['spread']}")
        """
        try:
            async with self.orderbook_lock:
                bids = await self.get_orderbook_bids(levels)
                asks = await self.get_orderbook_asks(levels)
                best_bid, best_ask = await self.get_best_bid_ask()

                return {
                    "timestamp": datetime.now(self.timezone),
                    "instrument": self.instrument,
                    "bids": bids,
                    "asks": asks,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "spread": best_ask - best_bid if best_bid and best_ask else None,
                    "mid_price": (best_bid + best_ask) / 2
                    if best_bid and best_ask
                    else None,
                    "update_count": self.level2_update_count,
                    "last_update": self.last_orderbook_update,
                }

        except Exception as e:
            self.logger.error(f"Error getting orderbook snapshot: {e}")
            return {
                "timestamp": datetime.now(self.timezone),
                "instrument": self.instrument,
                "bids": [],
                "asks": [],
                "best_bid": None,
                "best_ask": None,
                "spread": None,
                "mid_price": None,
                "error": str(e),
            }

    async def get_orderbook_bids(self, levels: int = 10) -> list[dict[str, Any]]:
        """Get top bid levels from the orderbook."""
        try:
            async with self.orderbook_lock:
                if len(self.orderbook_bids) == 0:
                    return []

                # Sort by price descending and get top levels
                top_bids = (
                    self.orderbook_bids.sort("price", descending=True)
                    .head(levels)
                    .to_dicts()
                )

                return [
                    {
                        "price": bid["price"],
                        "volume": bid["volume"],
                        "timestamp": bid["timestamp"],
                    }
                    for bid in top_bids
                ]

        except Exception as e:
            self.logger.error(f"Error getting orderbook bids: {e}")
            return []

    async def get_orderbook_asks(self, levels: int = 10) -> list[dict[str, Any]]:
        """Get top ask levels from the orderbook."""
        try:
            async with self.orderbook_lock:
                if len(self.orderbook_asks) == 0:
                    return []

                # Sort by price ascending and get top levels
                top_asks = self.orderbook_asks.sort("price").head(levels).to_dicts()

                return [
                    {
                        "price": ask["price"],
                        "volume": ask["volume"],
                        "timestamp": ask["timestamp"],
                    }
                    for ask in top_asks
                ]

        except Exception as e:
            self.logger.error(f"Error getting orderbook asks: {e}")
            return []

    async def get_best_bid_ask(self) -> tuple[float | None, float | None]:
        """Get the best bid and ask prices."""
        try:
            async with self.orderbook_lock:
                best_bid = None
                best_ask = None

                if len(self.orderbook_bids) > 0:
                    best_bid = self.orderbook_bids["price"].max()

                if len(self.orderbook_asks) > 0:
                    best_ask = self.orderbook_asks["price"].min()

                return best_bid, best_ask

        except Exception as e:
            self.logger.error(f"Error getting best bid/ask: {e}")
            return None, None

    async def get_bid_ask_spread(self) -> float | None:
        """Get the current bid-ask spread."""
        best_bid, best_ask = await self.get_best_bid_ask()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None

    async def detect_iceberg_orders(
        self,
        min_refreshes: int = 5,
        volume_threshold: float = 100,
        time_window_minutes: int = 30,
        consistency_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """
        Detect potential iceberg orders using statistical analysis.

        Iceberg orders are large orders that are partially hidden, showing
        only a small portion at any price level. This method identifies them
        by analyzing price level refresh patterns.

        Args:
            min_refreshes: Minimum refreshes to consider (default: 5)
            volume_threshold: Minimum volume to track (default: 100)
            time_window_minutes: Analysis window (default: 30)
            consistency_threshold: Refresh consistency threshold (default: 0.7)

        Returns:
            Dict containing detected iceberg orders and confidence scores

        Example:
            >>> icebergs = await orderbook.detect_iceberg_orders(
            ...     min_refreshes=10, volume_threshold=50
            ... )
            >>> for level in icebergs["iceberg_levels"]:
            ...     print(
            ...         f"Price: {level['price']}, Confidence: {level['confidence']:.2%}"
            ...     )
        """
        try:
            async with self.orderbook_lock:
                cutoff_time = datetime.now(self.timezone) - timedelta(
                    minutes=time_window_minutes
                )
                iceberg_candidates = []

                # Analyze each price level's history
                for (price, side), history in self.price_level_history.items():
                    # Filter recent history
                    recent_history = [
                        h for h in history if h["timestamp"] > cutoff_time
                    ]

                    if len(recent_history) < min_refreshes:
                        continue

                    # Analyze refresh patterns
                    volumes = [h["volume"] for h in recent_history]
                    avg_volume = mean(volumes)

                    if avg_volume < volume_threshold:
                        continue

                    # Check consistency of volume refreshes
                    if len(volumes) > 1:
                        volume_std = stdev(volumes)
                        cv = volume_std / avg_volume if avg_volume > 0 else 0

                        # Low coefficient of variation indicates consistent refreshes
                        if cv < (1 - consistency_threshold):
                            # Calculate refresh rate
                            time_span = (
                                recent_history[-1]["timestamp"]
                                - recent_history[0]["timestamp"]
                            ).total_seconds() / 60
                            refresh_rate = len(recent_history) / max(time_span, 1)

                            # Calculate confidence score
                            confidence = min(
                                0.95,
                                (1 - cv)
                                * min(refresh_rate / 2, 1)
                                * min(len(recent_history) / 20, 1),
                            )

                            iceberg_candidates.append(
                                {
                                    "price": price,
                                    "side": side,
                                    "avg_volume": avg_volume,
                                    "refresh_count": len(recent_history),
                                    "refresh_rate_per_min": refresh_rate,
                                    "volume_consistency": 1 - cv,
                                    "confidence": confidence,
                                    "last_seen": recent_history[-1]["timestamp"],
                                }
                            )

                # Sort by confidence
                iceberg_candidates.sort(key=lambda x: x["confidence"], reverse=True)

                return {
                    "timestamp": datetime.now(self.timezone),
                    "analysis_window_minutes": time_window_minutes,
                    "iceberg_levels": iceberg_candidates[:10],  # Top 10
                    "detection_parameters": {
                        "min_refreshes": min_refreshes,
                        "volume_threshold": volume_threshold,
                        "consistency_threshold": consistency_threshold,
                    },
                }

        except Exception as e:
            self.logger.error(f"Error detecting iceberg orders: {e}")
            return {
                "timestamp": datetime.now(self.timezone),
                "iceberg_levels": [],
                "error": str(e),
            }

    async def add_callback(
        self,
        event_type: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None],
    ) -> None:
        """
        Register a callback for orderbook events.

        Args:
            event_type: Type of event to listen for
            callback: Async function to call when event occurs

        Example:
            >>> async def on_depth_update(data):
            ...     print(f"Orderbook updated: {data['update_count']}")
            >>> await orderbook.add_callback("market_depth_processed", on_depth_update)
        """
        self.callbacks[event_type].append(callback)

    async def _trigger_callbacks(self, event_type: str, data: dict[str, Any]) -> None:
        """Trigger all callbacks for a specific event type."""
        for callback in self.callbacks.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {e}")

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory usage statistics."""
        return {
            "total_bid_levels": len(self.orderbook_bids),
            "total_ask_levels": len(self.orderbook_asks),
            "total_trades": len(self.recent_trades),
            "price_history_levels": len(self.price_level_history),
            "update_count": self.level2_update_count,
            **self.memory_stats,
        }

    async def clear_orderbook(self) -> None:
        """Clear all orderbook data."""
        async with self.orderbook_lock:
            # Clear all orderbook data with proper schemas
            self.orderbook_bids = pl.DataFrame(
                {"price": [], "volume": [], "timestamp": [], "type": []},
                schema={
                    "price": pl.Float64,
                    "volume": pl.Int64,
                    "timestamp": pl.Datetime("us"),
                    "type": pl.Utf8,
                },
            )
            self.orderbook_asks = pl.DataFrame(
                {"price": [], "volume": [], "timestamp": [], "type": []},
                schema={
                    "price": pl.Float64,
                    "volume": pl.Int64,
                    "timestamp": pl.Datetime("us"),
                    "type": pl.Utf8,
                },
            )
            self.recent_trades = pl.DataFrame(
                {
                    "price": [],
                    "volume": [],
                    "timestamp": [],
                    "side": [],
                    "spread_at_trade": [],
                    "mid_price_at_trade": [],
                    "best_bid_at_trade": [],
                    "best_ask_at_trade": [],
                    "order_type": [],
                },
                schema={
                    "price": pl.Float64,
                    "volume": pl.Int64,
                    "timestamp": pl.Datetime("us"),
                    "side": pl.Utf8,
                    "spread_at_trade": pl.Float64,
                    "mid_price_at_trade": pl.Float64,
                    "best_bid_at_trade": pl.Float64,
                    "best_ask_at_trade": pl.Float64,
                    "order_type": pl.Utf8,
                },
            )
            self.price_level_history.clear()

            # Reset counters
            self.level2_update_count = 0
            self.last_orderbook_update = None
            self.order_type_stats = dict.fromkeys(self.order_type_stats, 0)

            self.logger.info("Orderbook data cleared")

    async def cleanup(self) -> None:
        """Clean up resources when shutting down."""
        await self.clear_orderbook()
        self.callbacks.clear()
        self.logger.info("✅ AsyncOrderBook cleanup completed")
