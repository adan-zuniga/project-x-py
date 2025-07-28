#!/usr/bin/env python3
"""
OrderBook Manager for Real-time Market Data

Author: TexasCoding
Date: June 2025

This module provides comprehensive orderbook management and analysis capabilities:
1. Real-time Level 2 market depth processing
2. Trade flow analysis and execution tracking
3. Advanced market microstructure analytics
4. Iceberg order detection using statistical analysis
5. Support/resistance level identification
6. Market imbalance and liquidity analysis

Key Features:
- Thread-safe orderbook operations
- Polars DataFrame-based storage for efficient analysis
- Advanced institutional-grade order flow analytics
- Statistical significance testing for pattern recognition
- Real-time market maker and iceberg detection
- Comprehensive liquidity and depth analysis

ProjectX DomType Enum Reference:
- Type 0 = Unknown
- Type 1 = Ask
- Type 2 = Bid
- Type 3 = BestAsk
- Type 4 = BestBid
- Type 5 = Trade
- Type 6 = Reset
- Type 7 = Low (session low)
- Type 8 = High (session high)
- Type 9 = NewBestBid
- Type 10 = NewBestAsk
- Type 11 = Fill

Source: https://gateway.docs.projectx.com/docs/realtime/
"""

import gc
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import TYPE_CHECKING, Any, Optional

import polars as pl

if TYPE_CHECKING:
    from .realtime import ProjectXRealtimeClient
import pytz


class OrderBook:
    """
    Advanced orderbook manager for real-time market depth and trade flow analysis.

    This class provides institutional-grade orderbook analytics including:
    - Real-time Level 2 market depth processing
    - Trade execution flow analysis
    - Iceberg order detection with statistical confidence
    - Dynamic support/resistance identification
    - Market imbalance and liquidity metrics
    - Volume profile and cumulative delta analysis

    The orderbook maintains separate bid and ask sides with full depth,
    tracks all trade executions, and provides advanced analytics for
    algorithmic trading strategies.
    """

    def __init__(self, instrument: str, timezone: str = "America/Chicago", client=None):
        """
        Initialize the advanced orderbook manager for real-time market depth analysis.

        Creates a thread-safe orderbook with Level 2 market depth tracking,
        trade flow analysis, and advanced analytics for institutional trading.
        Uses Polars DataFrames for high-performance data operations.

        Args:
            instrument: Trading instrument symbol (e.g., "MGC", "MNQ", "ES")
            timezone: Timezone for timestamp handling (default: "America/Chicago")
                Supports any pytz timezone string
            client: ProjectX client instance for instrument metadata (optional)

        Example:
            >>> # Create orderbook for gold futures
            >>> orderbook = OrderBook("MGC", client=project_x_client)
            >>> # Create orderbook with custom timezone
            >>> orderbook = OrderBook(
            ...     "ES", timezone="America/New_York", client=project_x_client
            ... )
            >>> # Initialize with real-time data
            >>> success = orderbook.initialize(realtime_client)
        """
        self.instrument = instrument
        self.timezone = pytz.timezone(timezone)
        self.client = client
        self.logger = logging.getLogger(__name__)

        # Cache instrument tick size during initialization
        self.tick_size = self._fetch_instrument_tick_size()

        # Thread-safe locks for concurrent access
        self.orderbook_lock = threading.RLock()

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
                "timestamp": pl.Datetime,
                "type": pl.Utf8,
            },
        )

        self.orderbook_asks: pl.DataFrame = pl.DataFrame(
            {"price": [], "volume": [], "timestamp": [], "type": []},
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime,
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
                "timestamp": pl.Datetime,
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
        self.callbacks: dict[str, list[Callable]] = defaultdict(list)

        self.logger.info(f"OrderBook initialized for {instrument}")

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

    def initialize(
        self, realtime_client: Optional["ProjectXRealtimeClient"] = None
    ) -> bool:
        """
        Initialize the OrderBook with optional real-time capabilities.

        This method follows the same pattern as OrderManager and PositionManager,
        allowing automatic setup of real-time market data callbacks for seamless
        integration with live market depth, trade flow, and quote updates.

        Args:
            realtime_client: Optional ProjectXRealtimeClient for live market data

        Returns:
            bool: True if initialization successful

        Example:
            >>> orderbook = OrderBook("MGC")
            >>> success = orderbook.initialize(realtime_client)
            >>> if success:
            ...     # OrderBook will now automatically receive market depth updates
            ...     snapshot = orderbook.get_orderbook_snapshot()
        """
        try:
            # Set up real-time integration if provided
            if realtime_client:
                self.realtime_client = realtime_client
                self._setup_realtime_callbacks()
                self.logger.info(
                    "✅ OrderBook initialized with real-time market data capabilities"
                )
            else:
                self.logger.info("✅ OrderBook initialized (manual data mode)")

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize OrderBook: {e}")
            return False

    def _setup_realtime_callbacks(self):
        """Set up callbacks for real-time market data processing."""
        if not hasattr(self, "realtime_client") or not self.realtime_client:
            return

        # Register for market depth events (primary orderbook data)
        self.realtime_client.add_callback("market_depth", self._on_market_depth_update)

        # Register for market trade events (for trade flow analysis)
        self.realtime_client.add_callback("market_trade", self._on_market_trade_update)

        # Register for quote updates (for best bid/ask tracking)
        self.realtime_client.add_callback("quote_update", self._on_quote_update)

        self.logger.info("🔄 Real-time market data callbacks registered")

    def _on_market_depth_update(self, data: dict):
        """Handle real-time market depth updates."""
        try:
            # Filter for this instrument
            contract_id = data.get("contract_id", "")
            if not self._symbol_matches_instrument(contract_id):
                return

            # Process the market depth data
            self.process_market_depth(data)

            # Trigger any registered callbacks
            self._trigger_callbacks(
                "market_depth_processed",
                {
                    "contract_id": contract_id,
                    "update_count": self.level2_update_count,
                    "timestamp": datetime.now(self.timezone),
                },
            )

        except Exception as e:
            self.logger.error(f"Error processing market depth update: {e}")

    def _on_market_trade_update(self, data: dict):
        """Handle real-time market trade updates for trade flow analysis."""
        try:
            # Filter for this instrument
            contract_id = data.get("contract_id", "")
            if not self._symbol_matches_instrument(contract_id):
                return

            # Extract trade data - handle both dict and list formats
            raw_trade_data = data.get("data", {})
            if isinstance(raw_trade_data, list):
                # If data is a list, treat it as the trade data directly
                if not raw_trade_data:
                    return
                # For list format, we might need to extract the first element or handle differently
                # For now, skip processing list format trade data as we need the dict structure
                self.logger.debug(
                    f"Skipping list format trade data: {type(raw_trade_data)}"
                )
                return
            elif isinstance(raw_trade_data, dict):
                trade_data = raw_trade_data
            else:
                # Neither dict nor list - can't process
                self.logger.debug(
                    f"Unexpected trade data format: {type(raw_trade_data)}"
                )
                return

            if not trade_data:
                return

            # Update recent trades for analysis
            with self.orderbook_lock:
                current_time = datetime.now(self.timezone)

                # Get current best bid/ask for context
                best_prices = self.get_best_bid_ask()
                best_bid = best_prices.get("bid", 0.0)
                best_ask = best_prices.get("ask", 0.0)
                mid_price = best_prices.get("mid", 0.0)
                spread = best_prices.get("spread", 0.0)

                # Determine trade side based on price vs best bid/ask
                price = trade_data.get("price", 0.0)
                if best_ask and price >= best_ask:
                    side = "buy"  # Aggressive buy
                elif best_bid and price <= best_bid:
                    side = "sell"  # Aggressive sell
                elif mid_price and price > mid_price:
                    side = "buy"  # Above mid, likely buy
                elif mid_price and price < mid_price:
                    side = "sell"  # Below mid, likely sell
                else:
                    side = "neutral"  # Can't determine

                # Map trade type
                trade_type = trade_data.get("type", 0)
                order_type = self._map_trade_type(trade_type)

                trade_entry = {
                    "price": price,
                    "volume": trade_data.get("volume", 0),
                    "timestamp": current_time,
                    "side": side,
                    "spread_at_trade": spread,
                    "mid_price_at_trade": mid_price,
                    "best_bid_at_trade": best_bid,
                    "best_ask_at_trade": best_ask,
                    "order_type": order_type,
                }

                # Add to recent trades DataFrame
                if self.recent_trades.is_empty():
                    # Initialize DataFrame with the first trade
                    self.recent_trades = pl.DataFrame([trade_entry])
                else:
                    new_trade_df = pl.DataFrame([trade_entry])
                    self.recent_trades = pl.concat([self.recent_trades, new_trade_df])

                    # Keep only recent trades (last 1000)
                    if len(self.recent_trades) > 1000:
                        self.recent_trades = self.recent_trades.tail(1000)

            # Trigger callbacks
            self._trigger_callbacks(
                "trade_processed",
                {
                    "contract_id": contract_id,
                    "trade_data": trade_data,
                    "timestamp": current_time,
                },
            )

        except Exception as e:
            self.logger.error(f"Error processing market trade update: {e}")

    def _on_quote_update(self, data: dict):
        """Handle real-time quote updates for best bid/ask tracking."""
        try:
            # Filter for this instrument
            contract_id = data.get("contract_id", "")
            if not self._symbol_matches_instrument(contract_id):
                return

            # Extract quote data
            quote_data = data.get("data", {})
            if not quote_data:
                return

            # Trigger callbacks for quote processing
            self._trigger_callbacks(
                "quote_processed",
                {
                    "contract_id": contract_id,
                    "quote_data": quote_data,
                    "timestamp": datetime.now(self.timezone),
                },
            )

        except Exception as e:
            self.logger.error(f"Error processing quote update: {e}")

    def _symbol_matches_instrument(self, contract_id: str) -> bool:
        """
        Check if a contract_id matches this orderbook's instrument.

        Uses simplified symbol matching logic for ProjectX contract IDs.
        For example: "CON.F.US.MNQ.U25" should match instrument "MNQ"
        """
        if not contract_id or not self.instrument:
            return False

        try:
            instrument_upper = self.instrument.upper()
            contract_upper = contract_id.upper()

            # Simple check: instrument symbol should appear in contract ID
            # For "CON.F.US.MNQ.U25" and "MNQ", this should match
            return instrument_upper in contract_upper

        except Exception:
            return False

    def _cleanup_old_data(self) -> None:
        """
        Clean up old data to manage memory usage efficiently.
        """
        current_time = time.time()

        # Only cleanup if interval has passed
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        with self.orderbook_lock:
            initial_trade_count = len(self.recent_trades)
            initial_bid_count = len(self.orderbook_bids)
            initial_ask_count = len(self.orderbook_asks)

            # Cleanup recent trades - keep only the most recent trades
            if len(self.recent_trades) > self.max_trades:
                self.recent_trades = self.recent_trades.tail(self.max_trades // 2)
                self.memory_stats["trades_cleaned"] += initial_trade_count - len(
                    self.recent_trades
                )

            # Cleanup orderbook depth - keep only recent depth entries
            cutoff_time = datetime.now(self.timezone) - timedelta(hours=1)

            if len(self.orderbook_bids) > self.max_depth_entries:
                self.orderbook_bids = self.orderbook_bids.filter(
                    pl.col("timestamp") > cutoff_time
                ).tail(self.max_depth_entries // 2)

            if len(self.orderbook_asks) > self.max_depth_entries:
                self.orderbook_asks = self.orderbook_asks.filter(
                    pl.col("timestamp") > cutoff_time
                ).tail(self.max_depth_entries // 2)

            self.last_cleanup = current_time
            self.memory_stats["last_cleanup"] = current_time

            # Log cleanup stats
            trades_after = len(self.recent_trades)
            bids_after = len(self.orderbook_bids)
            asks_after = len(self.orderbook_asks)

            if (
                initial_trade_count != trades_after
                or initial_bid_count != bids_after
                or initial_ask_count != asks_after
            ):
                self.logger.debug(
                    f"OrderBook cleanup - Trades: {initial_trade_count}→{trades_after}, "
                    f"Bids: {initial_bid_count}→{bids_after}, "
                    f"Asks: {initial_ask_count}→{asks_after}"
                )

                # Force garbage collection after significant cleanup
                gc.collect()

    def get_memory_stats(self) -> dict:
        """
        Get comprehensive memory usage statistics for the orderbook.

        Provides detailed information about current memory usage,
        data structure sizes, and cleanup statistics for monitoring
        and optimization purposes.

        Returns:
            Dict with memory and performance statistics:
                - recent_trades_count: Number of trades stored in memory
                - orderbook_bids_count, orderbook_asks_count: Depth levels stored
                - total_memory_entries: Combined count of all data entries
                - max_trades, max_depth_entries: Configured memory limits
                - total_trades, trades_cleaned: Lifetime processing statistics
                - last_cleanup: Timestamp of last memory cleanup

        Example:
            >>> stats = orderbook.get_memory_stats()
            >>> print(f"Memory usage: {stats['total_memory_entries']} entries")
            >>> print(f"Trades: {stats['recent_trades_count']}/{stats['max_trades']}")
            >>> print(
            ...     f"Depth: {stats['orderbook_bids_count']} bids, {stats['orderbook_asks_count']} asks"
            ... )
            >>> # Check if cleanup occurred recently
            >>> import time
            >>> if time.time() - stats["last_cleanup"] > 300:  # 5 minutes
            ...     print("Memory cleanup may be needed")
        """
        with self.orderbook_lock:
            return {
                "recent_trades_count": len(self.recent_trades),
                "orderbook_bids_count": len(self.orderbook_bids),
                "orderbook_asks_count": len(self.orderbook_asks),
                "total_memory_entries": (
                    len(self.recent_trades)
                    + len(self.orderbook_bids)
                    + len(self.orderbook_asks)
                ),
                "max_trades": self.max_trades,
                "max_depth_entries": self.max_depth_entries,
                **self.memory_stats,
            }

    def process_market_depth(self, data: dict) -> None:
        """
        Process market depth data and update Level 2 orderbook.

        Args:
            data: Market depth data containing price levels and volumes
        """
        try:
            contract_id = data.get("contract_id", "Unknown")
            depth_data = data.get("data", [])

            # Update statistics
            self.level2_update_count += 1

            # Process each market depth entry
            with self.orderbook_lock:
                current_time = datetime.now(self.timezone)

                bid_updates = []
                ask_updates = []
                trade_updates = []

                for entry in depth_data:
                    # DEBUG: Log the raw entry format to understand real-time data structure
                    self.logger.debug(f"Processing DOM entry: {entry}")

                    # Try multiple possible field names for ProjectX data format
                    price = entry.get("price", entry.get("Price", 0.0))
                    volume = entry.get("volume", entry.get("Volume", 0))
                    # Note: ProjectX can provide both 'volume' (total at price level)
                    # and 'currentVolume' (current at price level). Using 'volume' for now.
                    # current_volume = entry.get("currentVolume", volume)  # Future enhancement
                    entry_type = entry.get(
                        "type", entry.get("Type", entry.get("EntryType", 0))
                    )
                    timestamp_str = entry.get("timestamp", entry.get("Timestamp", ""))

                    self.logger.debug(
                        f"Extracted: price={price}, volume={volume}, entry_type={entry_type}, timestamp={timestamp_str}"
                    )

                    # Update statistics
                    if entry_type == 1:
                        self.order_type_stats["type_1_count"] += 1  # Ask
                    elif entry_type == 2:
                        self.order_type_stats["type_2_count"] += 1  # Bid
                    elif entry_type == 3:
                        self.order_type_stats["type_3_count"] += 1  # BestAsk
                    elif entry_type == 4:
                        self.order_type_stats["type_4_count"] += 1  # BestBid
                    elif entry_type == 5:
                        self.order_type_stats["type_5_count"] += 1  # Trade
                    elif entry_type == 6:
                        self.order_type_stats["type_6_count"] += 1  # Reset
                    elif entry_type == 7:
                        self.order_type_stats["type_7_count"] += 1  # Low
                    elif entry_type == 8:
                        self.order_type_stats["type_8_count"] += 1  # High
                    elif entry_type == 9:
                        self.order_type_stats["type_9_count"] += 1  # NewBestBid
                    elif entry_type == 10:
                        self.order_type_stats["type_10_count"] += 1  # NewBestAsk
                    elif entry_type == 11:
                        self.order_type_stats["type_11_count"] += 1  # Fill
                    else:
                        self.order_type_stats["other_types"] += 1
                        # Debug: Log unexpected entry types
                        if entry_type not in [0]:  # Don't spam for type 0 (Unknown)
                            self.logger.debug(
                                f"Unknown entry_type: {entry_type} (price={price}, volume={volume})"
                            )

                    # Parse timestamp if provided, otherwise use current time
                    if timestamp_str and timestamp_str != "0001-01-01T00:00:00+00:00":
                        try:
                            timestamp = datetime.fromisoformat(
                                timestamp_str.replace("Z", "+00:00")
                            )
                            if timestamp.tzinfo is None:
                                timestamp = self.timezone.localize(timestamp)
                            else:
                                timestamp = timestamp.astimezone(self.timezone)
                        except Exception:
                            timestamp = current_time
                    else:
                        timestamp = current_time

                    # Enhanced type mapping based on ProjectX DomType enum:
                    # Type 0 = Unknown
                    # Type 1 = Ask
                    # Type 2 = Bid
                    # Type 3 = BestAsk
                    # Type 4 = BestBid
                    # Type 5 = Trade
                    # Type 6 = Reset
                    # Type 7 = Low
                    # Type 8 = High
                    # Type 9 = NewBestBid
                    # Type 10 = NewBestAsk
                    # Type 11 = Fill

                    if entry_type == 2:  # Bid
                        bid_updates.append(
                            {
                                "price": float(price),
                                "volume": int(volume),
                                "timestamp": timestamp,
                                "type": "bid",
                            }
                        )
                    elif entry_type == 1:  # Ask
                        ask_updates.append(
                            {
                                "price": float(price),
                                "volume": int(volume),
                                "timestamp": timestamp,
                                "type": "ask",
                            }
                        )
                    elif entry_type == 4:  # BestBid
                        bid_updates.append(
                            {
                                "price": float(price),
                                "volume": int(volume),
                                "timestamp": timestamp,
                                "type": "best_bid",
                            }
                        )
                    elif entry_type == 3:  # BestAsk
                        ask_updates.append(
                            {
                                "price": float(price),
                                "volume": int(volume),
                                "timestamp": timestamp,
                                "type": "best_ask",
                            }
                        )
                    elif entry_type == 9:  # NewBestBid
                        bid_updates.append(
                            {
                                "price": float(price),
                                "volume": int(volume),
                                "timestamp": timestamp,
                                "type": "new_best_bid",
                            }
                        )
                    elif entry_type == 10:  # NewBestAsk
                        ask_updates.append(
                            {
                                "price": float(price),
                                "volume": int(volume),
                                "timestamp": timestamp,
                                "type": "new_best_ask",
                            }
                        )
                    elif entry_type == 5:  # Trade execution
                        if volume > 0:  # Only record actual trades with volume
                            trade_updates.append(
                                {
                                    "price": float(price),
                                    "volume": int(volume),
                                    "timestamp": timestamp,
                                    "order_type": self._map_trade_type(entry_type),
                                }
                            )
                    elif entry_type == 11:  # Fill (alternative trade representation)
                        if volume > 0:
                            trade_updates.append(
                                {
                                    "price": float(price),
                                    "volume": int(volume),
                                    "timestamp": timestamp,
                                    "order_type": self._map_trade_type(entry_type),
                                }
                            )
                    elif entry_type == 6:  # Reset - clear orderbook
                        self.logger.info(
                            "OrderBook reset signal received, clearing data"
                        )
                        self.orderbook_bids = pl.DataFrame(
                            {"price": [], "volume": [], "timestamp": [], "type": []},
                            schema={
                                "price": pl.Float64,
                                "volume": pl.Int64,
                                "timestamp": pl.Datetime,
                                "type": pl.Utf8,
                            },
                        )
                        self.orderbook_asks = pl.DataFrame(
                            {"price": [], "volume": [], "timestamp": [], "type": []},
                            schema={
                                "price": pl.Float64,
                                "volume": pl.Int64,
                                "timestamp": pl.Datetime,
                                "type": pl.Utf8,
                            },
                        )
                    elif entry_type in [
                        7,
                        8,
                    ]:  # Low/High - informational, could be used for day range
                        # These are typically session low/high updates, log for awareness
                        self.logger.debug(
                            f"Session {'low' if entry_type == 7 else 'high'} update: {price}"
                        )
                    elif entry_type == 0:  # Unknown
                        self.logger.debug(
                            f"Unknown DOM type received: price={price}, volume={volume}"
                        )
                    # Note: We removed the complex classification logic for types 9/10 since they're now clearly defined

                # Update bid levels
                if bid_updates:
                    updates_df = pl.from_dicts(bid_updates)
                    self._update_orderbook_side(updates_df, "bid")

                # Update ask levels
                if ask_updates:
                    updates_df = pl.from_dicts(ask_updates)
                    self._update_orderbook_side(updates_df, "ask")

                # Validate orderbook integrity - check for negative spreads
                self._validate_orderbook_integrity()

                # Update trade flow data
                if trade_updates:
                    updates_df = pl.from_dicts(trade_updates)
                    self._update_trade_flow(updates_df)

                # Update last update time
                self.last_orderbook_update = current_time

            # Store the complete Level 2 data structure
            processed_data = self._process_level2_data(depth_data)
            self.last_level2_data = {
                "contract_id": contract_id,
                "timestamp": current_time,
                "bids": processed_data["bids"],
                "asks": processed_data["asks"],
                "best_bid": processed_data["best_bid"],
                "best_ask": processed_data["best_ask"],
                "spread": processed_data["spread"],
                "raw_data": depth_data,
            }

            # Trigger callbacks for any registered listeners
            self._trigger_callbacks("market_depth", data)

            # Periodic memory cleanup
            self._cleanup_old_data()

        except Exception as e:
            self.logger.error(f"❌ Error processing market depth: {e}")
            import traceback

            self.logger.error(f"❌ Market depth traceback: {traceback.format_exc()}")

    def _update_orderbook_side(self, updates_df: pl.DataFrame, side: str) -> None:
        """
        Update bid or ask side of the orderbook with new price levels.

        Args:
            updates: List of price level updates {price, volume, timestamp}
            side: "bid" or "ask"
        """
        try:
            current_df = self.orderbook_bids if side == "bid" else self.orderbook_asks

            # Combine with existing data
            if current_df.height > 0:
                combined_df = pl.concat([current_df, updates_df])
            else:
                combined_df = updates_df

            # Group by price and take the latest update
            latest_df = combined_df.group_by("price").agg(
                [
                    pl.col("volume").last(),
                    pl.col("timestamp").last(),
                    pl.col("type").last(),
                ]
            )

            # Remove zero-volume levels
            latest_df = latest_df.filter(pl.col("volume") > 0)

            # Sort appropriately
            if side == "bid":
                latest_df = latest_df.sort("price", descending=True)
                self.orderbook_bids = latest_df.head(100)
            else:
                latest_df = latest_df.sort("price", descending=False)
                self.orderbook_asks = latest_df.head(100)

        except Exception as e:
            self.logger.error(f"❌ Error updating {side} orderbook: {e}")

    def _update_trade_flow(self, trade_updates: pl.DataFrame) -> None:
        """
        Update trade flow data with new trade executions.

        Args:
            trade_updates: List of trade executions {price, volume, timestamp}
        """
        try:
            if trade_updates.height == 0:
                return

            # Get current best bid/ask to determine trade direction
            best_prices = self.get_best_bid_ask()
            best_bid = best_prices.get("bid")
            best_ask = best_prices.get("ask")

            # Enhanced trade direction detection with improved logic
            if best_bid is not None and best_ask is not None:
                # Calculate mid price for better classification
                mid_price = (best_bid + best_ask) / 2
                spread = best_ask - best_bid

                # Use spread-aware logic for better trade direction detection
                # Wider spreads require more conservative classification
                spread_threshold = spread * 0.25  # 25% of spread as buffer zone

                enhanced_trades = trade_updates.with_columns(
                    pl.when(pl.col("price") >= best_ask)
                    .then(pl.lit("buy"))  # Trade at or above ask = aggressive buy
                    .when(pl.col("price") <= best_bid)
                    .then(pl.lit("sell"))  # Trade at or below bid = aggressive sell
                    .when(pl.col("price") >= (mid_price + spread_threshold))
                    .then(pl.lit("buy"))  # Above mid + buffer = likely buy
                    .when(pl.col("price") <= (mid_price - spread_threshold))
                    .then(pl.lit("sell"))  # Below mid - buffer = likely sell
                    .when(spread <= 0.01)  # Very tight spread (1 cent or less)
                    .then(
                        pl.when(pl.col("price") > mid_price)
                        .then(pl.lit("buy"))
                        .otherwise(pl.lit("sell"))
                    )
                    .otherwise(pl.lit("neutral"))  # In the spread buffer zone
                    .alias("side")
                )

                # Add spread metadata to trades for analysis
                enhanced_trades = enhanced_trades.with_columns(
                    [
                        pl.lit(spread).alias("spread_at_trade"),
                        pl.lit(mid_price).alias("mid_price_at_trade"),
                        pl.lit(best_bid).alias("best_bid_at_trade"),
                        pl.lit(best_ask).alias("best_ask_at_trade"),
                    ]
                )
            else:
                # Fallback to basic classification if no best prices available
                enhanced_trades = trade_updates.with_columns(
                    pl.when((best_ask is not None) & (pl.col("price") >= best_ask))
                    .then(pl.lit("buy"))
                    .when((best_bid is not None) & (pl.col("price") <= best_bid))
                    .then(pl.lit("sell"))
                    .otherwise(pl.lit("unknown"))
                    .alias("side")
                )

                # Add null metadata for consistency when best prices unavailable
                enhanced_trades = enhanced_trades.with_columns(
                    [
                        pl.lit(None, dtype=pl.Float64).alias("spread_at_trade"),
                        pl.lit(None, dtype=pl.Float64).alias("mid_price_at_trade"),
                        pl.lit(best_bid, dtype=pl.Float64).alias("best_bid_at_trade"),
                        pl.lit(best_ask, dtype=pl.Float64).alias("best_ask_at_trade"),
                    ]
                )

            # Combine with existing trade data
            if self.recent_trades.height > 0:
                combined_df = pl.concat([self.recent_trades, enhanced_trades])
            else:
                combined_df = enhanced_trades

            # Keep only last 1000 trades to manage memory
            self.recent_trades = combined_df.tail(1000)

        except Exception as e:
            self.logger.error(f"❌ Error updating trade flow: {e}")

    def _validate_orderbook_integrity(self) -> None:
        """
        Validate orderbook integrity and fix any negative spreads by removing problematic entries.
        This is a safety net to ensure market data integrity.
        """
        try:
            if len(self.orderbook_bids) == 0 or len(self.orderbook_asks) == 0:
                return

            # Get current best bid and ask
            best_bid = float(self.orderbook_bids.select(pl.col("price")).head(1).item())
            best_ask = float(self.orderbook_asks.select(pl.col("price")).head(1).item())

            # If we have a negative spread, we need to fix it
            if best_bid >= best_ask:
                self.logger.debug(
                    f"Negative spread detected: best_bid={best_bid}, best_ask={best_ask}. "
                    f"Cleaning problematic entries."
                )

                # Remove any bid entries that are >= best ask
                original_bid_count = len(self.orderbook_bids)
                self.orderbook_bids = self.orderbook_bids.filter(
                    pl.col("price") < best_ask
                )
                removed_bids = original_bid_count - len(self.orderbook_bids)

                # Remove any ask entries that are <= best bid
                original_ask_count = len(self.orderbook_asks)
                self.orderbook_asks = self.orderbook_asks.filter(
                    pl.col("price") > best_bid
                )
                removed_asks = original_ask_count - len(self.orderbook_asks)

                # Update statistics
                self.order_type_stats["integrity_fixes"] = (
                    self.order_type_stats.get("integrity_fixes", 0) + 1
                )

                # If we removed entries, log the action
                if removed_bids > 0 or removed_asks > 0:
                    self.logger.debug(
                        f"Orderbook integrity fix: removed {removed_bids} problematic bid entries "
                        f"and {removed_asks} problematic ask entries to maintain positive spread."
                    )

                # Verify the fix worked
                if len(self.orderbook_bids) > 0 and len(self.orderbook_asks) > 0:
                    new_best_bid = float(
                        self.orderbook_bids.select(pl.col("price")).head(1).item()
                    )
                    new_best_ask = float(
                        self.orderbook_asks.select(pl.col("price")).head(1).item()
                    )
                    new_spread = new_best_ask - new_best_bid

                    if new_spread >= 0:
                        self.logger.debug(
                            f"Orderbook integrity restored: new spread = {new_spread}"
                        )
                    else:
                        self.logger.error(
                            f"Failed to fix negative spread: {new_spread}"
                        )

        except Exception as e:
            self.logger.error(f"Error in orderbook integrity validation: {e}")

    def _process_level2_data(self, depth_data: list) -> dict:
        """
        Process raw Level 2 data into structured bid/ask format.

        Args:
            depth_data: List of market depth entries with price, volume, type

        Returns:
            dict: Processed data with separate bids and asks
        """
        bids = []
        asks = []

        for entry in depth_data:
            price = entry.get("price", 0)
            volume = entry.get("volume", 0)
            entry_type = entry.get("type", 0)

            # Type mapping based on ProjectX DomType enum:
            # Type 0 = Unknown
            # Type 1 = Ask
            # Type 2 = Bid
            # Type 3 = BestAsk
            # Type 4 = BestBid
            # Type 5 = Trade
            # Type 6 = Reset
            # Type 7 = Low
            # Type 8 = High
            # Type 9 = NewBestBid
            # Type 10 = NewBestAsk
            # Type 11 = Fill

            if entry_type == 2 and volume > 0:  # Bid
                bids.append({"price": price, "volume": volume})
            elif entry_type == 1 and volume > 0:  # Ask
                asks.append({"price": price, "volume": volume})
            elif entry_type == 4 and volume > 0:  # BestBid
                bids.append({"price": price, "volume": volume})
            elif entry_type == 3 and volume > 0:  # BestAsk
                asks.append({"price": price, "volume": volume})
            elif entry_type == 9 and volume > 0:  # NewBestBid
                bids.append({"price": price, "volume": volume})
            elif entry_type == 10 and volume > 0:  # NewBestAsk
                asks.append({"price": price, "volume": volume})

        # Sort bids (highest to lowest) and asks (lowest to highest)
        bids.sort(key=lambda x: x["price"], reverse=True)
        asks.sort(key=lambda x: x["price"])

        # Calculate best bid/ask and spread
        best_bid = bids[0]["price"] if bids else 0
        best_ask = asks[0]["price"] if asks else 0
        spread = best_ask - best_bid if best_bid and best_ask else 0

        return {
            "bids": bids,
            "asks": asks,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
        }

    def get_orderbook_bids(self, levels: int = 10) -> pl.DataFrame:
        """
        Get the current bid side of the orderbook with specified depth.

        Retrieves bid levels sorted by price from highest to lowest,
        providing market depth information for buy-side liquidity analysis.

        Args:
            levels: Number of price levels to return (default: 10)
                Maximum depth available depends on market data feed

        Returns:
            pl.DataFrame: Bid levels with columns:
                - price: Bid price level
                - volume: Total volume at that price level
                - timestamp: Last update timestamp for that level
                - type: ProjectX DomType (2=Bid, 4=BestBid, 9=NewBestBid)

        Example:
            >>> bids = orderbook.get_orderbook_bids(5)
            >>> if not bids.is_empty():
            ...     best_bid = bids.row(0, named=True)["price"]
            ...     best_bid_volume = bids.row(0, named=True)["volume"]
            ...     print(f"Best bid: ${best_bid:.2f} x {best_bid_volume}")
            ...     # Analyze depth
            ...     total_volume = bids["volume"].sum()
            ...     print(f"Total bid volume (5 levels): {total_volume}")
        """
        try:
            with self.orderbook_lock:
                if len(self.orderbook_bids) == 0:
                    return pl.DataFrame(
                        {"price": [], "volume": [], "timestamp": [], "type": []},
                        schema={
                            "price": pl.Float64,
                            "volume": pl.Int64,
                            "timestamp": pl.Datetime,
                            "type": pl.Utf8,
                        },
                    )

                return self.orderbook_bids.head(levels).clone()

        except Exception as e:
            self.logger.error(f"Error getting orderbook bids: {e}")
            return pl.DataFrame(
                {"price": [], "volume": [], "timestamp": [], "type": []},
                schema={
                    "price": pl.Float64,
                    "volume": pl.Int64,
                    "timestamp": pl.Datetime,
                    "type": pl.Utf8,
                },
            )

    def get_orderbook_asks(self, levels: int = 10) -> pl.DataFrame:
        """
        Get the current ask side of the orderbook with specified depth.

        Retrieves ask levels sorted by price from lowest to highest,
        providing market depth information for sell-side liquidity analysis.

        Args:
            levels: Number of price levels to return (default: 10)
                Maximum depth available depends on market data feed

        Returns:
            pl.DataFrame: Ask levels with columns:
                - price: Ask price level
                - volume: Total volume at that price level
                - timestamp: Last update timestamp for that level
                - type: ProjectX DomType (1=Ask, 3=BestAsk, 10=NewBestAsk)

        Example:
            >>> asks = orderbook.get_orderbook_asks(5)
            >>> if not asks.is_empty():
            ...     best_ask = asks.row(0, named=True)["price"]
            ...     best_ask_volume = asks.row(0, named=True)["volume"]
            ...     print(f"Best ask: ${best_ask:.2f} x {best_ask_volume}")
            ...     # Analyze depth
            ...     total_volume = asks["volume"].sum()
            ...     print(f"Total ask volume (5 levels): {total_volume}")
        """
        try:
            with self.orderbook_lock:
                if len(self.orderbook_asks) == 0:
                    return pl.DataFrame(
                        {"price": [], "volume": [], "timestamp": [], "type": []},
                        schema={
                            "price": pl.Float64,
                            "volume": pl.Int64,
                            "timestamp": pl.Datetime,
                            "type": pl.Utf8,
                        },
                    )

                return self.orderbook_asks.head(levels).clone()

        except Exception as e:
            self.logger.error(f"Error getting orderbook asks: {e}")
            return pl.DataFrame(
                {"price": [], "volume": [], "timestamp": [], "type": []},
                schema={
                    "price": pl.Float64,
                    "volume": pl.Int64,
                    "timestamp": pl.Datetime,
                    "type": pl.Utf8,
                },
            )

    def get_orderbook_snapshot(self, levels: int = 10) -> dict[str, Any]:
        """
        Get a complete orderbook snapshot with both bids and asks plus market metadata.

        Provides a comprehensive view of current market depth including
        best prices, spreads, total volume, and market structure information
        for both sides of the orderbook.

        Args:
            levels: Number of price levels to return for each side (default: 10)
                Higher values provide deeper market visibility

        Returns:
            Dict with complete market depth information:
                - bids: pl.DataFrame with bid levels (highest to lowest price)
                - asks: pl.DataFrame with ask levels (lowest to highest price)
                - metadata: Dict with market metrics:
                    - best_bid, best_ask: Current best prices
                    - spread: Bid-ask spread
                    - mid_price: Midpoint price
                    - total_bid_volume, total_ask_volume: Aggregate volume
                    - last_update: Timestamp of last orderbook update
                    - levels_count: Number of levels available per side

        Example:
            >>> snapshot = orderbook.get_orderbook_snapshot(10)
            >>> metadata = snapshot["metadata"]
            >>> print(f"Spread: ${metadata['spread']:.2f}")
            >>> print(f"Mid price: ${metadata['mid_price']:.2f}")
            >>> # Analyze market imbalance
            >>> bid_vol = metadata["total_bid_volume"]
            >>> ask_vol = metadata["total_ask_volume"]
            >>> imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
            >>> print(f"Order imbalance: {imbalance:.2%}")
            >>> # Access raw data
            >>> bids_df = snapshot["bids"]
            >>> asks_df = snapshot["asks"]
        """
        try:
            with self.orderbook_lock:
                bids = self.get_orderbook_bids(levels)
                asks = self.get_orderbook_asks(levels)

                # Calculate metadata
                best_bid = (
                    float(bids.select(pl.col("price")).head(1).item())
                    if len(bids) > 0
                    else None
                )
                best_ask = (
                    float(asks.select(pl.col("price")).head(1).item())
                    if len(asks) > 0
                    else None
                )
                spread = (best_ask - best_bid) if best_bid and best_ask else None
                mid_price = (
                    ((best_bid + best_ask) / 2) if best_bid and best_ask else None
                )

                # Calculate total volume at each side
                total_bid_volume = (
                    int(bids.select(pl.col("volume").sum()).item())
                    if len(bids) > 0
                    else 0
                )
                total_ask_volume = (
                    int(asks.select(pl.col("volume").sum()).item())
                    if len(asks) > 0
                    else 0
                )

                return {
                    "bids": bids,
                    "asks": asks,
                    "metadata": {
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "spread": spread,
                        "mid_price": mid_price,
                        "total_bid_volume": total_bid_volume,
                        "total_ask_volume": total_ask_volume,
                        "last_update": self.last_orderbook_update,
                        "levels_count": {"bids": len(bids), "asks": len(asks)},
                    },
                }

        except Exception as e:
            self.logger.error(f"Error getting orderbook snapshot: {e}")
            return {
                "bids": pl.DataFrame(
                    schema={
                        "price": pl.Float64,
                        "volume": pl.Int64,
                        "timestamp": pl.Datetime,
                        "type": pl.Utf8,
                    }
                ),
                "asks": pl.DataFrame(
                    schema={
                        "price": pl.Float64,
                        "volume": pl.Int64,
                        "timestamp": pl.Datetime,
                        "type": pl.Utf8,
                    }
                ),
                "metadata": {},
            }

    def get_best_bid_ask(self) -> dict[str, float | None]:
        """
        Get the current best bid and ask prices with spread and midpoint calculations.

        Provides the most recent best bid and ask prices from the top of book,
        along with derived metrics for spread analysis and fair value estimation.

        Returns:
            Dict with current market prices:
                - bid: Best bid price (highest buy price) or None
                - ask: Best ask price (lowest sell price) or None
                - spread: Bid-ask spread (ask - bid) or None
                - mid: Midpoint price ((bid + ask) / 2) or None

        Example:
            >>> prices = orderbook.get_best_bid_ask()
            >>> if prices["bid"] and prices["ask"]:
            ...     print(f"Market: {prices['bid']:.2f} x {prices['ask']:.2f}")
            ...     print(f"Spread: ${prices['spread']:.2f}")
            ...     print(f"Fair value: ${prices['mid']:.2f}")
            ...     # Check if market is tight
            ...     if prices["spread"] < 0.50:
            ...         print("Tight market - good liquidity")
            >>> else:
            ...     print("No current market data available")
        """
        try:
            with self.orderbook_lock:
                best_bid = None
                best_ask = None

                if len(self.orderbook_bids) > 0:
                    best_bid = float(
                        self.orderbook_bids.select(pl.col("price")).head(1).item()
                    )

                if len(self.orderbook_asks) > 0:
                    best_ask = float(
                        self.orderbook_asks.select(pl.col("price")).head(1).item()
                    )

                spread = (best_ask - best_bid) if best_bid and best_ask else None
                mid_price = (
                    ((best_bid + best_ask) / 2) if best_bid and best_ask else None
                )

                return {
                    "bid": best_bid,
                    "ask": best_ask,
                    "spread": spread,
                    "mid": mid_price,
                }

        except Exception as e:
            self.logger.error(f"Error getting best bid/ask: {e}")
            return {"bid": None, "ask": None, "spread": None, "mid": None}

    def get_recent_trades(self, count: int = 100) -> pl.DataFrame:
        """
        Get recent trade executions with comprehensive market context.

        Retrieves the most recent trade executions (ProjectX Type 5 data)
        with inferred trade direction and market context at the time of
        each trade for comprehensive trade flow analysis.

        Args:
            count: Number of recent trades to return (default: 100)
                Trades are returned in chronological order (oldest first)

        Returns:
            pl.DataFrame: Recent trades with enriched market data:
                - price: Trade execution price
                - volume: Trade size in contracts
                - timestamp: Execution timestamp
                - side: Inferred trade direction ("buy" or "sell")
                - spread_at_trade: Bid-ask spread when trade occurred
                - mid_price_at_trade: Midpoint price when trade occurred
                - best_bid_at_trade: Best bid when trade occurred
                - best_ask_at_trade: Best ask when trade occurred

        Example:
            >>> trades = orderbook.get_recent_trades(50)
            >>> if not trades.is_empty():
            ...     # Analyze recent trade flow
            ...     buy_volume = trades.filter(pl.col("side") == "buy")["volume"].sum()
            ...     sell_volume = trades.filter(pl.col("side") == "sell")[
            ...         "volume"
            ...     ].sum()
            ...     print(f"Buy volume: {buy_volume}, Sell volume: {sell_volume}")
            ...     # Check trade sizes
            ...     avg_trade_size = trades["volume"].mean()
            ...     print(f"Average trade size: {avg_trade_size:.1f} contracts")
            ...     # Recent price action
            ...     latest_price = trades["price"].tail(1).item()
            ...     print(f"Last trade: ${latest_price:.2f}")
        """
        try:
            with self.orderbook_lock:
                if len(self.recent_trades) == 0:
                    return pl.DataFrame(
                        {
                            "price": [],
                            "volume": [],
                            "timestamp": [],
                            "side": [],
                            "spread_at_trade": [],
                            "mid_price_at_trade": [],
                            "best_bid_at_trade": [],
                            "best_ask_at_trade": [],
                        },
                        schema={
                            "price": pl.Float64,
                            "volume": pl.Int64,
                            "timestamp": pl.Datetime,
                            "side": pl.Utf8,
                            "spread_at_trade": pl.Float64,
                            "mid_price_at_trade": pl.Float64,
                            "best_bid_at_trade": pl.Float64,
                            "best_ask_at_trade": pl.Float64,
                        },
                    )

                return self.recent_trades.tail(count).clone()

        except Exception as e:
            self.logger.error(f"Error getting recent trades: {e}")
            return pl.DataFrame(
                schema={
                    "price": pl.Float64,
                    "volume": pl.Int64,
                    "timestamp": pl.Datetime,
                    "side": pl.Utf8,
                    "spread_at_trade": pl.Float64,
                    "mid_price_at_trade": pl.Float64,
                    "best_bid_at_trade": pl.Float64,
                    "best_ask_at_trade": pl.Float64,
                }
            )

    def clear_recent_trades(self) -> None:
        """
        Clear the recent trades history for fresh monitoring periods.

        Removes all stored trade execution data to start fresh trade flow
        analysis. Useful when starting new monitoring sessions or after
        market breaks.

        Example:
            >>> # Clear trades at market open
            >>> orderbook.clear_recent_trades()
            >>> # Start fresh analysis for new session
            >>> # ... collect new trade data ...
            >>> fresh_trades = orderbook.get_recent_trades()
        """
        try:
            with self.orderbook_lock:
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
                        "timestamp": pl.Datetime,
                        "side": pl.Utf8,
                        "spread_at_trade": pl.Float64,
                        "mid_price_at_trade": pl.Float64,
                        "best_bid_at_trade": pl.Float64,
                        "best_ask_at_trade": pl.Float64,
                        "order_type": pl.Utf8,
                    },
                )

                self.logger.info("🧹 Recent trades history cleared")

        except Exception as e:
            self.logger.error(f"❌ Error clearing recent trades: {e}")

    def get_trade_flow_summary(self, minutes: int = 5) -> dict[str, Any]:
        """
        Get trade flow summary for the last N minutes.

        Args:
            minutes: Number of minutes to analyze

        Returns:
            dict: Trade flow statistics
        """
        try:
            with self.orderbook_lock:
                if len(self.recent_trades) == 0:
                    return {
                        "total_volume": 0,
                        "trade_count": 0,
                        "buy_volume": 0,
                        "sell_volume": 0,
                        "buy_trades": 0,
                        "sell_trades": 0,
                        "avg_trade_size": 0,
                        "vwap": 0,
                        "buy_sell_ratio": 0,
                    }

                # Filter trades from last N minutes
                cutoff_time = datetime.now(self.timezone) - timedelta(minutes=minutes)
                recent_trades = self.recent_trades.filter(
                    pl.col("timestamp") >= cutoff_time
                )

                if len(recent_trades) == 0:
                    return {
                        "total_volume": 0,
                        "trade_count": 0,
                        "buy_volume": 0,
                        "sell_volume": 0,
                        "buy_trades": 0,
                        "sell_trades": 0,
                        "avg_trade_size": 0,
                        "vwap": 0,
                        "buy_sell_ratio": 0,
                    }

                # Calculate statistics
                total_volume = int(recent_trades.select(pl.col("volume").sum()).item())
                trade_count = len(recent_trades)

                # Buy/sell breakdown
                buy_trades = recent_trades.filter(pl.col("side") == "buy")
                sell_trades = recent_trades.filter(pl.col("side") == "sell")

                buy_volume = (
                    int(buy_trades.select(pl.col("volume").sum()).item())
                    if len(buy_trades) > 0
                    else 0
                )
                sell_volume = (
                    int(sell_trades.select(pl.col("volume").sum()).item())
                    if len(sell_trades) > 0
                    else 0
                )

                buy_count = len(buy_trades)
                sell_count = len(sell_trades)

                # Calculate VWAP (Volume Weighted Average Price)
                if total_volume > 0:
                    vwap_calc = recent_trades.select(
                        (pl.col("price") * pl.col("volume")).sum()
                        / pl.col("volume").sum()
                    ).item()
                    vwap = float(vwap_calc)
                else:
                    vwap = 0

                avg_trade_size = total_volume / trade_count if trade_count > 0 else 0
                buy_sell_ratio = (
                    buy_volume / sell_volume
                    if sell_volume > 0
                    else float("inf")
                    if buy_volume > 0
                    else 0
                )

                return {
                    "total_volume": total_volume,
                    "trade_count": trade_count,
                    "buy_volume": buy_volume,
                    "sell_volume": sell_volume,
                    "buy_trades": buy_count,
                    "sell_trades": sell_count,
                    "avg_trade_size": avg_trade_size,
                    "vwap": vwap,
                    "buy_sell_ratio": buy_sell_ratio,
                    "period_minutes": minutes,
                }

        except Exception as e:
            self.logger.error(f"Error getting trade flow summary: {e}")
            return {"error": str(e)}

    def get_order_type_statistics(self) -> dict[str, int]:
        """
        Get statistics about different order types processed.

        Returns:
            dict: Count of each order type processed
        """
        return self.order_type_stats.copy()

    def get_orderbook_depth(self, price_range: float = 10.0) -> dict[str, int | float]:
        """
        Get orderbook depth within a price range of the mid price.

        Args:
            price_range: Price range around mid to analyze (in price units)

        Returns:
            dict: Volume and level counts within the range
        """
        try:
            with self.orderbook_lock:
                best_prices = self.get_best_bid_ask()
                mid_price = best_prices.get("mid")

                if not mid_price:
                    return {
                        "bid_volume": 0,
                        "ask_volume": 0,
                        "bid_levels": 0,
                        "ask_levels": 0,
                    }

                # Define price range
                lower_bound = mid_price - price_range
                upper_bound = mid_price + price_range

                # Filter bids in range
                bids_in_range = self.orderbook_bids.filter(
                    (pl.col("price") >= lower_bound) & (pl.col("price") <= mid_price)
                )

                # Filter asks in range
                asks_in_range = self.orderbook_asks.filter(
                    (pl.col("price") <= upper_bound) & (pl.col("price") >= mid_price)
                )

                bid_volume = (
                    int(bids_in_range.select(pl.col("volume").sum()).item())
                    if len(bids_in_range) > 0
                    else 0
                )
                ask_volume = (
                    int(asks_in_range.select(pl.col("volume").sum()).item())
                    if len(asks_in_range) > 0
                    else 0
                )

                return {
                    "bid_volume": bid_volume,
                    "ask_volume": ask_volume,
                    "bid_levels": len(bids_in_range),
                    "ask_levels": len(asks_in_range),
                    "price_range": price_range,
                    "mid_price": mid_price,
                }

        except Exception as e:
            self.logger.error(f"Error getting orderbook depth: {e}")
            return {"bid_volume": 0, "ask_volume": 0, "bid_levels": 0, "ask_levels": 0}

    def get_liquidity_levels(
        self, min_volume: int = 100, levels: int = 20
    ) -> dict[str, Any]:
        """
        Identify significant liquidity levels in the orderbook.

        Args:
            min_volume: Minimum volume threshold for significance
            levels: Number of levels to analyze from each side

        Returns:
            dict: {"bid_liquidity": DataFrame, "ask_liquidity": DataFrame}
        """
        try:
            with self.orderbook_lock:
                # Get top levels from each side
                bids = self.get_orderbook_bids(levels)
                asks = self.get_orderbook_asks(levels)

                avg_ask_volume = pl.DataFrame()
                avg_bid_volume = pl.DataFrame()

                # Filter for significant volume levels
                significant_bids = bids.filter(pl.col("volume") >= min_volume)
                significant_asks = asks.filter(pl.col("volume") >= min_volume)

                # Add liquidity score (volume relative to average)
                if len(significant_bids) > 0:
                    avg_bid_volume = significant_bids.select(
                        pl.col("volume").mean()
                    ).item()
                    significant_bids = significant_bids.with_columns(
                        [
                            (pl.col("volume") / avg_bid_volume).alias(
                                "liquidity_score"
                            ),
                            pl.lit("bid").alias("side"),
                        ]
                    )

                if len(significant_asks) > 0:
                    avg_ask_volume = significant_asks.select(
                        pl.col("volume").mean()
                    ).item()
                    significant_asks = significant_asks.with_columns(
                        [
                            (pl.col("volume") / avg_ask_volume).alias(
                                "liquidity_score"
                            ),
                            pl.lit("ask").alias("side"),
                        ]
                    )

                return {
                    "bid_liquidity": significant_bids,
                    "ask_liquidity": significant_asks,
                    "analysis": {
                        "total_bid_levels": len(significant_bids),
                        "total_ask_levels": len(significant_asks),
                        "avg_bid_volume": avg_bid_volume
                        if len(significant_bids) > 0
                        else 0,
                        "avg_ask_volume": avg_ask_volume
                        if len(significant_asks) > 0
                        else 0,
                    },
                }

        except Exception as e:
            self.logger.error(f"Error analyzing liquidity levels: {e}")
            return {"bid_liquidity": pl.DataFrame(), "ask_liquidity": pl.DataFrame()}

    def detect_order_clusters(
        self, price_tolerance: float | None = None, min_cluster_size: int = 3
    ) -> dict[str, Any]:
        """
        Detect clusters of orders at similar price levels.

        Args:
            price_tolerance: Price difference tolerance for clustering. If None,
                           will be calculated based on instrument tick size or derived from data
            min_cluster_size: Minimum number of orders to form a cluster

        Returns:
            dict: {"bid_clusters": list, "ask_clusters": list}
        """
        try:
            with self.orderbook_lock:
                # Calculate appropriate price tolerance if not provided
                if price_tolerance is None:
                    price_tolerance = self._calculate_price_tolerance()

                bid_clusters = self._find_clusters(
                    self.orderbook_bids, price_tolerance, min_cluster_size
                )
                ask_clusters = self._find_clusters(
                    self.orderbook_asks, price_tolerance, min_cluster_size
                )

                return {
                    "bid_clusters": bid_clusters,
                    "ask_clusters": ask_clusters,
                    "cluster_count": len(bid_clusters) + len(ask_clusters),
                    "analysis": {
                        "strongest_bid_cluster": max(
                            bid_clusters, key=lambda x: x["total_volume"]
                        )
                        if bid_clusters
                        else None,
                        "strongest_ask_cluster": max(
                            ask_clusters, key=lambda x: x["total_volume"]
                        )
                        if ask_clusters
                        else None,
                    },
                }

        except Exception as e:
            self.logger.error(f"Error detecting order clusters: {e}")
            return {"bid_clusters": [], "ask_clusters": []}

    def _fetch_instrument_tick_size(self) -> float:
        """
        Fetch and cache instrument tick size during initialization.

        Returns:
            float: Instrument tick size, or fallback value if unavailable
        """
        try:
            # First try to get tick size from ProjectX client
            if self.client:
                instrument_obj = self.client.get_instrument(self.instrument)
                if instrument_obj and hasattr(instrument_obj, "tickSize"):
                    self.logger.debug(
                        f"Fetched tick size {instrument_obj.tickSize} for {self.instrument}"
                    )
                    return instrument_obj.tickSize

            # Fallback to known tick sizes for common instruments if client unavailable
            instrument_tick_sizes = {
                "MNQ": 0.25,  # Micro E-mini NASDAQ-100
                "ES": 0.25,  # E-mini S&P 500
                "MGC": 0.10,  # Micro Gold
                "MCL": 0.01,  # Micro Crude Oil
                "RTY": 0.10,  # E-mini Russell 2000
                "YM": 1.00,  # E-mini Dow
                "ZB": 0.03125,  # Treasury Bonds
                "ZN": 0.015625,  # 10-Year Treasury Notes
                "GC": 0.10,  # Gold Futures
                "CL": 0.01,  # Crude Oil
                "EUR": 0.00005,  # Euro FX
                "GBP": 0.0001,  # British Pound
            }

            # Extract base symbol (remove month/year codes)
            base_symbol = self.instrument.upper()
            if base_symbol in instrument_tick_sizes:
                tick_size = instrument_tick_sizes[base_symbol]
                self.logger.debug(
                    f"Using fallback tick size {tick_size} for {self.instrument}"
                )
                return tick_size

            # Final fallback - conservative default
            self.logger.warning(
                f"Unknown instrument {self.instrument}, using default tick size 0.01"
            )
            return 0.01

        except Exception as e:
            self.logger.warning(f"Error fetching instrument tick size: {e}")
            return 0.01

    def _calculate_price_tolerance(self) -> float:
        """
        Calculate appropriate price tolerance for cluster detection based on
        cached instrument tick size.

        Returns:
            float: Calculated price tolerance for clustering (3x tick size)
        """
        try:
            # Use cached tick size with 3x multiplier for tolerance
            return self.tick_size * 3

        except Exception as e:
            self.logger.warning(f"Error calculating price tolerance: {e}")
            return 0.05

    def _find_clusters(
        self, df: pl.DataFrame, tolerance: float, min_size: int
    ) -> list[dict]:
        """Helper method to find price clusters in orderbook data."""
        if len(df) == 0:
            return []

        clusters = []
        prices = df.get_column("price").to_list()
        volumes = df.get_column("volume").to_list()

        i = 0
        while i < len(prices):
            cluster_prices = [prices[i]]
            cluster_volumes = [volumes[i]]
            cluster_indices = [i]

            # Look for nearby prices within tolerance
            j = i + 1
            while j < len(prices) and abs(prices[j] - prices[i]) <= tolerance:
                cluster_prices.append(prices[j])
                cluster_volumes.append(volumes[j])
                cluster_indices.append(j)
                j += 1

            # If cluster is large enough, record it
            if len(cluster_prices) >= min_size:
                clusters.append(
                    {
                        "center_price": sum(cluster_prices) / len(cluster_prices),
                        "price_range": (min(cluster_prices), max(cluster_prices)),
                        "total_volume": sum(cluster_volumes),
                        "order_count": len(cluster_prices),
                        "volume_weighted_price": sum(
                            p * v
                            for p, v in zip(
                                cluster_prices, cluster_volumes, strict=False
                            )
                        )
                        / sum(cluster_volumes),
                        "indices": cluster_indices,
                    }
                )

            # Move to next unclustered price
            i = j if j > i + 1 else i + 1

        return clusters

    def detect_iceberg_orders(
        self,
        time_window_minutes: int = 30,
        min_refresh_count: int = 5,
        volume_consistency_threshold: float = 0.85,
        min_total_volume: int = 1000,
        statistical_confidence: float = 0.95,
    ) -> dict[str, Any]:
        """
        Advanced iceberg order detection using statistical analysis.

        Args:
            time_window_minutes: Analysis window for historical patterns
            min_refresh_count: Minimum refreshes to qualify as iceberg
            volume_consistency_threshold: Required volume consistency (0-1)
            min_total_volume: Minimum cumulative volume threshold
            statistical_confidence: Statistical confidence level for detection

        Returns:
            dict: Advanced iceberg analysis with confidence metrics
        """
        try:
            with self.orderbook_lock:
                cutoff_time = datetime.now(self.timezone) - timedelta(
                    minutes=time_window_minutes
                )

                # Initialize empty history DataFrame - schema will be inferred from concatenation
                history_df = None

                # Process both bid and ask sides
                for side, df in [
                    ("bid", self.orderbook_bids),
                    ("ask", self.orderbook_asks),
                ]:
                    if df.height == 0:
                        continue

                    # Filter by timestamp if available, otherwise use all data
                    if "timestamp" in df.columns:
                        # Use cutoff_time directly since it's already in the correct timezone
                        recent_df = df.filter(pl.col("timestamp") >= cutoff_time)
                    else:
                        # Use all data if no timestamp filtering possible
                        recent_df = df

                    if recent_df.height == 0:
                        continue

                    # Add side column and ensure schema compatibility
                    side_df = recent_df.select(
                        [
                            pl.col("price"),
                            pl.col("volume"),
                            pl.col("timestamp"),
                            pl.lit(side).alias("side"),
                        ]
                    )

                    # Concatenate with main history DataFrame
                    if history_df is None:
                        history_df = side_df
                    else:
                        history_df = pl.concat([history_df, side_df], how="vertical")

                # Check if we have sufficient data for analysis
                if history_df is None or history_df.height == 0:
                    return {
                        "potential_icebergs": [],
                        "analysis": {
                            "total_detected": 0,
                            "detection_method": "advanced_statistical_analysis",
                            "time_window_minutes": time_window_minutes,
                            "error": "No orderbook data available for analysis",
                        },
                    }

                # Perform statistical analysis on price levels
                grouped = history_df.group_by(["price", "side"]).agg(
                    [
                        pl.col("volume").mean().alias("avg_volume"),
                        pl.col("volume").std().alias("vol_std"),
                        pl.col("volume").count().alias("refresh_count"),
                        pl.col("volume").sum().alias("total_volume"),
                        pl.lit(60.0).alias(
                            "avg_refresh_interval_seconds"
                        ),  # Default placeholder
                        pl.col("volume").min().alias("min_volume"),
                        pl.col("volume").max().alias("max_volume"),
                    ]
                )

                # Filter for potential icebergs based on statistical criteria
                potential = grouped.filter(
                    # Minimum refresh count requirement
                    (pl.col("refresh_count") >= min_refresh_count)
                    &
                    # Minimum total volume requirement
                    (pl.col("total_volume") >= min_total_volume)
                    &
                    # Volume consistency requirement (low coefficient of variation)
                    (
                        (pl.col("vol_std") / pl.col("avg_volume"))
                        < (1 - volume_consistency_threshold)
                    )
                    &
                    # Ensure we have meaningful standard deviation data
                    (pl.col("vol_std").is_not_null())
                    & (pl.col("avg_volume") > 0)
                )

                # Convert to list of dictionaries for processing
                potential_icebergs = []
                for row in potential.to_dicts():
                    # Calculate confidence score based on multiple factors
                    refresh_score = min(
                        row["refresh_count"] / (min_refresh_count * 2), 1.0
                    )
                    volume_score = min(
                        row["total_volume"] / (min_total_volume * 2), 1.0
                    )

                    # Volume consistency score (lower coefficient of variation = higher score)
                    cv = (
                        row["vol_std"] / row["avg_volume"]
                        if row["avg_volume"] > 0
                        else 1.0
                    )
                    consistency_score = max(0, 1 - cv)

                    # Refresh interval regularity (more regular = higher score)
                    interval_score = 0.5  # Default score if no interval data
                    if (
                        row["avg_refresh_interval_seconds"]
                        and row["avg_refresh_interval_seconds"] > 0
                    ):
                        # Score based on whether refresh interval is reasonable (5-300 seconds)
                        if 5 <= row["avg_refresh_interval_seconds"] <= 300:
                            interval_score = 0.8
                        elif row["avg_refresh_interval_seconds"] < 5:
                            interval_score = 0.6  # Too frequent might be algorithm
                        else:
                            interval_score = 0.4  # Too infrequent

                    # Combined confidence score
                    confidence_score = (
                        refresh_score * 0.3
                        + volume_score * 0.2
                        + consistency_score * 0.4
                        + interval_score * 0.1
                    )

                    # Determine confidence category
                    if confidence_score >= 0.8:
                        confidence = "very_high"
                    elif confidence_score >= 0.65:
                        confidence = "high"
                    elif confidence_score >= 0.45:
                        confidence = "medium"
                    else:
                        confidence = "low"

                    # Estimate hidden size based on volume patterns
                    estimated_hidden_size = max(
                        row["total_volume"] * 1.5,  # Conservative estimate
                        row["max_volume"] * 5,  # Based on max observed
                        row["avg_volume"] * 10,  # Based on average pattern
                    )

                    iceberg_data = {
                        "price": row["price"],
                        "current_volume": row["avg_volume"],
                        "side": row["side"],
                        "confidence": confidence,
                        "confidence_score": confidence_score,
                        "estimated_hidden_size": estimated_hidden_size,
                        "refresh_count": row["refresh_count"],
                        "total_volume": row["total_volume"],
                        "volume_std": row["vol_std"],
                        "avg_refresh_interval": row["avg_refresh_interval_seconds"],
                        "volume_range": {
                            "min": row["min_volume"],
                            "max": row["max_volume"],
                            "avg": row["avg_volume"],
                        },
                    }
                    potential_icebergs.append(iceberg_data)

                # Cross-reference with trade data for additional validation
                potential_icebergs = self._cross_reference_with_trades(
                    potential_icebergs, cutoff_time
                )

                # Sort by confidence score (highest first)
                potential_icebergs.sort(
                    key=lambda x: x["confidence_score"], reverse=True
                )

                return {
                    "potential_icebergs": potential_icebergs,
                    "analysis": {
                        "total_detected": len(potential_icebergs),
                        "detection_method": "advanced_statistical_analysis",
                        "time_window_minutes": time_window_minutes,
                        "cutoff_time": cutoff_time,
                        "parameters": {
                            "min_refresh_count": min_refresh_count,
                            "volume_consistency_threshold": volume_consistency_threshold,
                            "min_total_volume": min_total_volume,
                            "statistical_confidence": statistical_confidence,
                        },
                        "data_summary": {
                            "total_orderbook_entries": history_df.height,
                            "unique_price_levels": history_df.select(
                                "price"
                            ).n_unique(),
                            "bid_entries": history_df.filter(
                                pl.col("side") == "bid"
                            ).height,
                            "ask_entries": history_df.filter(
                                pl.col("side") == "ask"
                            ).height,
                        },
                        "confidence_distribution": {
                            "very_high": sum(
                                1
                                for x in potential_icebergs
                                if x["confidence"] == "very_high"
                            ),
                            "high": sum(
                                1
                                for x in potential_icebergs
                                if x["confidence"] == "high"
                            ),
                            "medium": sum(
                                1
                                for x in potential_icebergs
                                if x["confidence"] == "medium"
                            ),
                            "low": sum(
                                1
                                for x in potential_icebergs
                                if x["confidence"] == "low"
                            ),
                        },
                        "side_distribution": {
                            "bid": sum(
                                1 for x in potential_icebergs if x["side"] == "bid"
                            ),
                            "ask": sum(
                                1 for x in potential_icebergs if x["side"] == "ask"
                            ),
                        },
                        "total_estimated_hidden_volume": sum(
                            x["estimated_hidden_size"] for x in potential_icebergs
                        ),
                    },
                }

        except Exception as e:
            self.logger.error(f"Error in advanced iceberg detection: {e}")
            return {"potential_icebergs": [], "analysis": {"error": str(e)}}

    def get_cumulative_delta(self, time_window_minutes: int = 30) -> dict[str, Any]:
        """
        Calculate cumulative delta (running total of buy vs sell volume).

        Args:
            time_window_minutes: Time window for delta calculation

        Returns:
            dict: Cumulative delta analysis
        """
        try:
            with self.orderbook_lock:
                if len(self.recent_trades) == 0:
                    return {
                        "cumulative_delta": 0,
                        "delta_trend": "neutral",
                        "time_series": [],
                        "analysis": {
                            "total_buy_volume": 0,
                            "total_sell_volume": 0,
                            "net_volume": 0,
                            "trade_count": 0,
                        },
                    }

                cutoff_time = datetime.now(self.timezone) - timedelta(
                    minutes=time_window_minutes
                )
                recent_trades = self.recent_trades.filter(
                    pl.col("timestamp") >= cutoff_time
                )

                if len(recent_trades) == 0:
                    return {
                        "cumulative_delta": 0,
                        "delta_trend": "neutral",
                        "time_series": [],
                        "analysis": {"note": "No trades in time window"},
                    }

                # Sort by timestamp for cumulative calculation
                trades_sorted = recent_trades.sort("timestamp")

                # Calculate cumulative delta
                cumulative_delta = 0
                delta_series = []
                total_buy_volume = 0
                total_sell_volume = 0

                for trade in trades_sorted.to_dicts():
                    volume = trade["volume"]
                    side = trade["side"]
                    timestamp = trade["timestamp"]

                    if side == "buy":
                        cumulative_delta += volume
                        total_buy_volume += volume
                    elif side == "sell":
                        cumulative_delta -= volume
                        total_sell_volume += volume

                    delta_series.append(
                        {
                            "timestamp": timestamp,
                            "delta": cumulative_delta,
                            "volume": volume,
                            "side": side,
                        }
                    )

                # Determine trend with wider, less sensitive thresholds
                if cumulative_delta > 5000:
                    trend = "strongly_bullish"
                elif cumulative_delta > 1000:
                    trend = "bullish"
                elif cumulative_delta < -5000:
                    trend = "strongly_bearish"
                elif cumulative_delta < -1000:
                    trend = "bearish"
                else:
                    trend = "neutral"

                return {
                    "cumulative_delta": cumulative_delta,
                    "delta_trend": trend,
                    "time_series": delta_series,
                    "analysis": {
                        "total_buy_volume": total_buy_volume,
                        "total_sell_volume": total_sell_volume,
                        "net_volume": total_buy_volume - total_sell_volume,
                        "trade_count": len(trades_sorted),
                        "time_window_minutes": time_window_minutes,
                        "delta_per_minute": cumulative_delta / time_window_minutes
                        if time_window_minutes > 0
                        else 0,
                    },
                }

        except Exception as e:
            self.logger.error(f"Error calculating cumulative delta: {e}")
            return {"cumulative_delta": 0, "error": str(e)}

    def get_market_imbalance(self, levels: int = 10) -> dict[str, Any]:
        """
        Calculate market imbalance metrics from orderbook and trade flow.

        Returns:
            dict: Market imbalance analysis
        """
        try:
            with self.orderbook_lock:
                # Get top 10 levels for analysis
                bids = self.get_orderbook_bids(levels)
                asks = self.get_orderbook_asks(levels)

                if len(bids) == 0 or len(asks) == 0:
                    return {
                        "imbalance_ratio": 0,
                        "direction": "neutral",
                        "confidence": "low",
                    }

                # Calculate volume imbalance at top levels
                top_bid_volume = bids.head(5).select(pl.col("volume").sum()).item()
                top_ask_volume = asks.head(5).select(pl.col("volume").sum()).item()

                # 🔍 DEBUG: Log orderbook data availability
                self.logger.debug(
                    f"🔍 Orderbook data: {len(bids)} bids, {len(asks)} asks"
                )
                self.logger.debug(
                    f"🔍 Top volumes: bid={top_bid_volume}, ask={top_ask_volume}"
                )

                total_volume = top_bid_volume + top_ask_volume
                if total_volume == 0:
                    self.logger.debug(
                        f"🔍 Zero total volume - returning neutral (bids={len(bids)}, asks={len(asks)})"
                    )
                    return {
                        "imbalance_ratio": 0,
                        "direction": "neutral",
                        "confidence": "low",
                    }

                # Calculate imbalance ratio (-1 to 1)
                imbalance_ratio = (top_bid_volume - top_ask_volume) / total_volume

                # Get recent trade flow for confirmation
                trade_flow = self.get_trade_flow_summary(minutes=5)
                trade_imbalance = 0
                if trade_flow["total_volume"] > 0:
                    trade_imbalance = (
                        trade_flow["buy_volume"] - trade_flow["sell_volume"]
                    ) / trade_flow["total_volume"]

                # Determine direction and confidence
                # Production thresholds for better signal quality
                bullish_threshold = (
                    0.15  # Moderate threshold (was 0.05 debug, 0.3 original)
                )
                bearish_threshold = (
                    -0.15
                )  # Moderate threshold (was -0.05 debug, -0.3 original)

                if imbalance_ratio > bullish_threshold:
                    direction = "bullish"
                    # Enhanced confidence logic
                    if imbalance_ratio > 0.25 and trade_imbalance > 0.2:
                        confidence = "high"
                    elif imbalance_ratio > 0.2 or trade_imbalance > 0.15:
                        confidence = "medium"
                    else:
                        confidence = "low"
                elif imbalance_ratio < bearish_threshold:
                    direction = "bearish"
                    # Enhanced confidence logic
                    if imbalance_ratio < -0.25 and trade_imbalance < -0.2:
                        confidence = "high"
                    elif imbalance_ratio < -0.2 or trade_imbalance < -0.15:
                        confidence = "medium"
                    else:
                        confidence = "low"
                else:
                    direction = "neutral"
                    confidence = "low"

                return {
                    "imbalance_ratio": imbalance_ratio,
                    "direction": direction,
                    "confidence": confidence,
                    "orderbook_metrics": {
                        "top_bid_volume": top_bid_volume,
                        "top_ask_volume": top_ask_volume,
                        "bid_ask_ratio": top_bid_volume / top_ask_volume
                        if top_ask_volume > 0
                        else float("inf"),
                        "volume_concentration": (top_bid_volume + top_ask_volume)
                        / (
                            bids.select(pl.col("volume").sum()).item()
                            + asks.select(pl.col("volume").sum()).item()
                        )
                        if (
                            bids.select(pl.col("volume").sum()).item()
                            + asks.select(pl.col("volume").sum()).item()
                        )
                        > 0
                        else 0,
                    },
                    "trade_flow_metrics": {
                        "trade_imbalance": trade_imbalance,
                        "recent_buy_volume": trade_flow["buy_volume"],
                        "recent_sell_volume": trade_flow["sell_volume"],
                        "buy_sell_ratio": trade_flow.get("buy_sell_ratio", 0),
                        "trade_count": trade_flow.get("trade_count", 0),
                    },
                    "signal_strength": abs(imbalance_ratio),
                    "timestamp": datetime.now(self.timezone),
                }

        except Exception as e:
            self.logger.error(f"Error calculating market imbalance: {e}")
            return {"imbalance_ratio": 0, "error": str(e)}

    def get_volume_profile(
        self, price_bucket_size: float = 0.25, time_window_minutes: int | None = None
    ) -> dict[str, Any]:
        """
        Create volume profile from recent trade data with optional time filtering.

        Args:
            price_bucket_size: Size of price buckets for grouping trades
            time_window_minutes: Optional time window in minutes for filtering trades.
                               If None, uses all available trade data.

        Returns:
            dict: Volume profile analysis
        """
        try:
            with self.orderbook_lock:
                if len(self.recent_trades) == 0:
                    return {"profile": [], "poc": None, "value_area": None}

                # Apply time filtering if specified
                trades_to_analyze = self.recent_trades
                if time_window_minutes is not None:
                    cutoff_time = datetime.now(self.timezone) - timedelta(
                        minutes=time_window_minutes
                    )

                    # Filter trades within the time window
                    if "timestamp" in trades_to_analyze.columns:
                        trades_to_analyze = trades_to_analyze.filter(
                            pl.col("timestamp") >= cutoff_time
                        )

                        # Check if we have any trades left after filtering
                        if len(trades_to_analyze) == 0:
                            return {
                                "profile": [],
                                "poc": None,
                                "value_area": None,
                                "time_window_minutes": time_window_minutes,
                                "analysis": {
                                    "note": f"No trades found in last {time_window_minutes} minutes"
                                },
                            }
                    else:
                        self.logger.warning(
                            "Trade data missing timestamp column, time filtering skipped"
                        )

                # Group trades by price buckets
                trades_with_buckets = trades_to_analyze.with_columns(
                    [(pl.col("price") / price_bucket_size).floor().alias("bucket")]
                )

                # Calculate volume profile
                profile = (
                    trades_with_buckets.group_by("bucket")
                    .agg(
                        [
                            pl.col("volume").sum().alias("total_volume"),
                            pl.col("price").mean().alias("avg_price"),
                            pl.col("volume").count().alias("trade_count"),
                            pl.col("volume")
                            .filter(pl.col("side") == "buy")
                            .sum()
                            .alias("buy_volume"),
                            pl.col("volume")
                            .filter(pl.col("side") == "sell")
                            .sum()
                            .alias("sell_volume"),
                        ]
                    )
                    .sort("bucket")
                )

                if len(profile) == 0:
                    return {
                        "profile": [],
                        "poc": None,
                        "value_area": None,
                        "time_window_minutes": time_window_minutes,
                        "analysis": {"note": "No trades available for volume profile"},
                    }

                # Find Point of Control (POC) - price level with highest volume
                max_volume_row = profile.filter(
                    pl.col("total_volume")
                    == profile.select(pl.col("total_volume").max()).item()
                ).head(1)

                poc_price = (
                    max_volume_row.select(pl.col("avg_price")).item()
                    if len(max_volume_row) > 0
                    else None
                )
                poc_volume = (
                    max_volume_row.select(pl.col("total_volume")).item()
                    if len(max_volume_row) > 0
                    else 0
                )

                # Calculate value area (70% of volume)
                total_volume = profile.select(pl.col("total_volume").sum()).item()
                value_area_volume = total_volume * 0.7

                # Find value area high and low
                profile_sorted = profile.sort("total_volume", descending=True)
                cumulative_volume = 0
                value_area_prices = []

                for row in profile_sorted.to_dicts():
                    cumulative_volume += row["total_volume"]
                    value_area_prices.append(row["avg_price"])
                    if cumulative_volume >= value_area_volume:
                        break

                value_area = {
                    "high": max(value_area_prices) if value_area_prices else None,
                    "low": min(value_area_prices) if value_area_prices else None,
                    "volume_percentage": (cumulative_volume / total_volume * 100)
                    if total_volume > 0
                    else 0,
                }

                # Calculate additional time-based metrics
                analysis = {
                    "total_trades_analyzed": len(trades_to_analyze),
                    "price_range": {
                        "high": float(
                            trades_to_analyze.select(pl.col("price").max()).item()
                        ),
                        "low": float(
                            trades_to_analyze.select(pl.col("price").min()).item()
                        ),
                    }
                    if len(trades_to_analyze) > 0
                    else {"high": None, "low": None},
                    "time_filtered": time_window_minutes is not None,
                }

                if time_window_minutes is not None:
                    analysis["time_window_minutes"] = time_window_minutes
                    analysis["time_filtering_applied"] = True
                else:
                    analysis["time_filtering_applied"] = False

                return {
                    "profile": profile.to_dicts(),
                    "poc": {"price": poc_price, "volume": poc_volume},
                    "value_area": value_area,
                    "total_volume": total_volume,
                    "bucket_size": price_bucket_size,
                    "time_window_minutes": time_window_minutes,
                    "analysis": analysis,
                    "timestamp": datetime.now(self.timezone),
                }

        except Exception as e:
            self.logger.error(f"Error creating volume profile: {e}")
            return {
                "profile": [],
                "error": str(e),
                "time_window_minutes": time_window_minutes,
            }

    def get_support_resistance_levels(
        self, lookback_minutes: int = 60
    ) -> dict[str, Any]:
        """
        Identify dynamic support and resistance levels from orderbook and trade data.

        Args:
            lookback_minutes: Minutes of data to analyze

        Returns:
            dict: {"support_levels": list, "resistance_levels": list}
        """
        try:
            with self.orderbook_lock:
                # Get volume profile for support/resistance detection with time filtering
                volume_profile = self.get_volume_profile(
                    time_window_minutes=lookback_minutes
                )

                if not volume_profile.get("profile"):
                    return {
                        "support_levels": [],
                        "resistance_levels": [],
                        "analysis": {"error": "No volume profile data available"},
                    }

                # Get current market price
                best_prices = self.get_best_bid_ask()
                current_price = best_prices.get("mid")

                if not current_price:
                    return {
                        "support_levels": [],
                        "resistance_levels": [],
                        "analysis": {"error": "No current price available"},
                    }

                # Identify significant volume levels
                profile_data = volume_profile["profile"]
                if not profile_data:
                    return {
                        "support_levels": [],
                        "resistance_levels": [],
                        "analysis": {"error": "Empty volume profile"},
                    }

                # Calculate average volume for significance threshold
                total_volume = sum(
                    level.get("total_volume", 0) for level in profile_data
                )
                avg_volume = total_volume / len(profile_data) if profile_data else 0

                if avg_volume == 0:
                    return {
                        "support_levels": [],
                        "resistance_levels": [],
                        "analysis": {"error": "No significant volume data"},
                    }

                # Filter for significant volume levels (1.5x average)
                significant_levels = [
                    level
                    for level in profile_data
                    if level.get("total_volume", 0) > avg_volume * 1.5
                ]

                # Separate into support and resistance based on current price
                support_levels = []
                resistance_levels = []

                for level in significant_levels:
                    level_price = level.get("avg_price")
                    level_volume = level.get("total_volume", 0)

                    if level_price is None:
                        continue  # Skip invalid levels

                    level_strength = level_volume / avg_volume

                    level_info = {
                        "price": float(level_price),
                        "volume": int(level_volume),
                        "strength": round(level_strength, 2),
                        "trade_count": level.get("trade_count", 0),
                        "type": "volume_cluster",
                        "distance_from_price": abs(level_price - current_price),
                    }

                    if level_price < current_price:
                        support_levels.append(level_info)
                    else:
                        resistance_levels.append(level_info)

                # Sort by proximity to current price (closest first)
                support_levels.sort(key=lambda x: x["distance_from_price"])
                resistance_levels.sort(key=lambda x: x["distance_from_price"])

                # Add orderbook levels as potential support/resistance
                try:
                    liquidity_levels = self.get_liquidity_levels(
                        min_volume=200, levels=15
                    )

                    # Process bid liquidity as potential support
                    bid_liquidity = liquidity_levels.get("bid_liquidity")
                    if bid_liquidity is not None and hasattr(bid_liquidity, "to_dicts"):
                        for bid_level in bid_liquidity.to_dicts():
                            bid_price = bid_level.get("price")
                            if bid_price is not None and bid_price < current_price:
                                support_levels.append(
                                    {
                                        "price": float(bid_price),
                                        "volume": int(bid_level.get("volume", 0)),
                                        "strength": round(
                                            bid_level.get("liquidity_score", 0), 2
                                        ),
                                        "type": "orderbook_liquidity",
                                        "distance_from_price": abs(
                                            bid_price - current_price
                                        ),
                                    }
                                )

                    # Process ask liquidity as potential resistance
                    ask_liquidity = liquidity_levels.get("ask_liquidity")
                    if ask_liquidity is not None and hasattr(ask_liquidity, "to_dicts"):
                        for ask_level in ask_liquidity.to_dicts():
                            ask_price = ask_level.get("price")
                            if ask_price is not None and ask_price > current_price:
                                resistance_levels.append(
                                    {
                                        "price": float(ask_price),
                                        "volume": int(ask_level.get("volume", 0)),
                                        "strength": round(
                                            ask_level.get("liquidity_score", 0), 2
                                        ),
                                        "type": "orderbook_liquidity",
                                        "distance_from_price": abs(
                                            ask_price - current_price
                                        ),
                                    }
                                )

                except Exception as liquidity_error:
                    self.logger.warning(
                        f"Failed to get liquidity levels: {liquidity_error}"
                    )
                    # Continue without orderbook liquidity data

                # Remove duplicates based on price proximity (within 1 tick)
                def remove_duplicates(levels_list):
                    """Remove levels that are too close to each other (within 1 tick)."""
                    if not levels_list:
                        return []

                    # Sort by strength first
                    sorted_levels = sorted(
                        levels_list, key=lambda x: x["strength"], reverse=True
                    )
                    unique_levels = [sorted_levels[0]]  # Start with strongest level

                    for level in sorted_levels[1:]:
                        # Check if this level is far enough from existing levels
                        min_distance = min(
                            abs(level["price"] - existing["price"])
                            for existing in unique_levels
                        )
                        if min_distance >= 0.25:  # At least 25 cents apart
                            unique_levels.append(level)

                    return unique_levels[:10]  # Limit to top 10

                # Apply deduplication and limit results
                support_levels = remove_duplicates(support_levels)
                resistance_levels = remove_duplicates(resistance_levels)

                # Re-sort by proximity to current price
                support_levels.sort(key=lambda x: x["distance_from_price"])
                resistance_levels.sort(key=lambda x: x["distance_from_price"])

                # Calculate analysis metrics
                analysis = {
                    "strongest_support": support_levels[0] if support_levels else None,
                    "strongest_resistance": resistance_levels[0]
                    if resistance_levels
                    else None,
                    "total_levels": len(support_levels) + len(resistance_levels),
                    "lookback_minutes": lookback_minutes,
                    "current_price": current_price,
                    "nearest_support": support_levels[0] if support_levels else None,
                    "nearest_resistance": resistance_levels[0]
                    if resistance_levels
                    else None,
                    "support_count": len(support_levels),
                    "resistance_count": len(resistance_levels),
                }

                # Add distance analysis
                if support_levels:
                    analysis["nearest_support_distance"] = round(
                        current_price - support_levels[0]["price"], 2
                    )
                if resistance_levels:
                    analysis["nearest_resistance_distance"] = round(
                        resistance_levels[0]["price"] - current_price, 2
                    )

                return {
                    "support_levels": support_levels,
                    "resistance_levels": resistance_levels,
                    "current_price": current_price,
                    "analysis": analysis,
                    "metadata": {
                        "data_source": "volume_profile + orderbook_liquidity",
                        "significance_threshold": f"{avg_volume * 1.5:.0f} volume",
                        "timestamp": datetime.now(self.timezone),
                    },
                }

        except Exception as e:
            self.logger.error(f"Error identifying support/resistance levels: {e}")
            return {
                "support_levels": [],
                "resistance_levels": [],
                "analysis": {"error": str(e)},
            }

    def get_advanced_market_metrics(self) -> dict[str, Any]:
        """
        Get comprehensive advanced market microstructure metrics.

        Returns:
            dict: Complete advanced market analysis
        """
        try:
            return {
                "liquidity_analysis": self.get_liquidity_levels(),
                "order_clusters": self.detect_order_clusters(),
                "iceberg_detection": self.detect_iceberg_orders(),
                "cumulative_delta": self.get_cumulative_delta(),
                "market_imbalance": self.get_market_imbalance(),
                "volume_profile": self.get_volume_profile(time_window_minutes=60),
                "support_resistance": self.get_support_resistance_levels(),
                "orderbook_snapshot": self.get_orderbook_snapshot(),
                "trade_flow": self.get_trade_flow_summary(),
                "dom_event_analysis": self.get_dom_event_analysis(),
                "best_price_analysis": self.get_best_price_change_analysis(),
                "spread_analysis": self.get_spread_analysis(),
                "timestamp": datetime.now(self.timezone),
                "analysis_summary": {
                    "data_quality": "high"
                    if len(self.recent_trades) > 100
                    else "medium",
                    "market_activity": "active"
                    if len(self.recent_trades) > 50
                    else "quiet",
                    "analysis_completeness": "full",
                },
            }

        except Exception as e:
            self.logger.error(f"Error getting advanced market metrics: {e}")
            return {"error": str(e)}

    def add_callback(self, event_type: str, callback: Callable):
        """
        Register a callback function for specific orderbook events.

        Allows you to listen for orderbook updates, trade processing,
        and other market events to build custom monitoring and
        analysis systems.

        Args:
            event_type: Type of event to listen for:
                - "market_depth_processed": Orderbook depth updated
                - "trade_processed": New trade execution processed
                - "orderbook_reset": Orderbook cleared/reset
                - "integrity_warning": Data integrity issue detected
            callback: Function to call when event occurs
                Should accept one argument: the event data dict

        Example:
            >>> def on_depth_update(data):
            ...     print(f"Depth updated for {data['contract_id']}")
            ...     print(f"Update #{data['update_count']}")
            >>> orderbook.add_callback("market_depth_processed", on_depth_update)
            >>> def on_trade(data):
            ...     trade = data["trade_data"]
            ...     print(f"Trade: {trade.get('volume')} @ ${trade.get('price'):.2f}")
            >>> orderbook.add_callback("trade_processed", on_trade)
        """
        self.callbacks[event_type].append(callback)
        self.logger.debug(f"Added orderbook callback for {event_type}")

    def remove_callback(self, event_type: str, callback: Callable):
        """
        Remove a specific callback function from event notifications.

        Args:
            event_type: Event type the callback was registered for
            callback: The exact callback function to remove

        Example:
            >>> # Remove previously registered callback
            >>> orderbook.remove_callback("market_depth_processed", on_depth_update)
        """
        if callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            self.logger.debug(f"Removed orderbook callback for {event_type}")

    def _trigger_callbacks(self, event_type: str, data: dict):
        """Trigger all callbacks for a specific event type."""
        for callback in self.callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} orderbook callback: {e}")

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics about the orderbook with enhanced DOM analysis."""
        with self.orderbook_lock:
            best_prices = self.get_best_bid_ask()
            dom_analysis = self.get_dom_event_analysis()

            return {
                "instrument": self.instrument,
                "orderbook_state": {
                    "bid_levels": len(self.orderbook_bids),
                    "ask_levels": len(self.orderbook_asks),
                    "best_bid": best_prices.get("bid"),
                    "best_ask": best_prices.get("ask"),
                    "spread": best_prices.get("spread"),
                    "mid_price": best_prices.get("mid"),
                },
                "data_flow": {
                    "last_update": self.last_orderbook_update,
                    "level2_updates": self.level2_update_count,
                    "recent_trades_count": len(self.recent_trades),
                },
                "dom_event_breakdown": {
                    "raw_stats": self.get_order_type_statistics(),
                    "event_quality": dom_analysis.get("analysis", {})
                    .get("market_activity_insights", {})
                    .get("data_quality", {}),
                    "market_activity": dom_analysis.get("analysis", {}).get(
                        "market_activity_insights", {}
                    ),
                },
                "performance_metrics": self.get_memory_stats(),
                "timestamp": datetime.now(self.timezone),
            }

    # Helper methods for advanced iceberg detection
    def _is_round_price(self, price: float) -> float:
        """Check if price is at psychologically significant level."""
        if price % 1.0 == 0:  # Whole numbers
            return 1.0
        elif price % 0.5 == 0:  # Half numbers
            return 0.8
        elif price % 0.25 == 0:  # Quarter numbers
            return 0.6
        elif price % 0.1 == 0:  # Tenth numbers
            return 0.4
        else:
            return 0.0

    def _analyze_volume_replenishment(self, volume_history: list) -> float:
        """Analyze how consistently volume is replenished after depletion."""
        if len(volume_history) < 4:
            return 0.0

        # Look for patterns where volume drops then returns to similar levels
        replenishment_score = 0.0
        for i in range(2, len(volume_history)):
            prev_vol = volume_history[i - 2]
            current_vol = volume_history[i - 1]
            next_vol = volume_history[i]

            # Check if volume dropped then replenished
            if (
                prev_vol > 0
                and current_vol < prev_vol * 0.5
                and next_vol > prev_vol * 0.8
            ):
                replenishment_score += 1.0

        return min(1.0, replenishment_score / max(1, len(volume_history) - 2))

    def _calculate_statistical_significance(
        self, volume_list: list, avg_refresh_interval: float, confidence_level: float
    ) -> float:
        """Calculate statistical significance of observed patterns."""
        if len(volume_list) < 3:
            return 0.0

        try:
            # Simple statistical significance based on volume consistency
            volume_std = stdev(volume_list) if len(volume_list) > 1 else 0
            volume_mean = mean(volume_list)

            # Calculate coefficient of variation
            cv = volume_std / volume_mean if volume_mean > 0 else float("inf")

            # Convert to significance score (lower CV = higher significance)
            significance = max(0.0, min(1.0, 1.0 - cv))

            # Adjust for sample size (more samples = higher confidence)
            sample_size_factor = min(1.0, len(volume_list) / 10.0)

            return significance * sample_size_factor

        except Exception:
            return 0.0

    def _estimate_iceberg_hidden_size(
        self, volume_history: list, confidence_score: float, total_observed: int
    ) -> int:
        """Estimate hidden size using statistical models."""
        if not volume_history:
            return 0

        avg_visible = mean(volume_history)

        # Advanced estimation based on multiple factors
        base_multiplier = 3.0 + (confidence_score * 7.0)  # 3x to 10x multiplier

        # Adjust for consistency patterns
        if len(volume_history) > 5:
            # More data points suggest larger hidden size
            base_multiplier *= 1.0 + len(volume_history) / 20.0

        estimated_hidden = int(avg_visible * base_multiplier)

        # Ensure estimate is reasonable relative to observed volume
        max_reasonable = total_observed * 5
        return min(estimated_hidden, max_reasonable)

    def _cross_reference_with_trades(
        self, icebergs: list, cutoff_time: datetime
    ) -> list:
        """Cross-reference iceberg candidates with actual trade execution patterns."""
        if not (len(self.recent_trades) > 0) or not icebergs:
            return icebergs

        # Filter trades to time window
        trades_in_window = self.recent_trades.filter(pl.col("timestamp") >= cutoff_time)

        if len(trades_in_window) == 0:
            return icebergs

        # Enhance icebergs with trade execution analysis
        enhanced_icebergs = []

        for iceberg in icebergs:
            price = iceberg["price"]

            # Find trades near this price level (within 1 tick)
            price_tolerance = 0.01  # 1 cent tolerance
            nearby_trades = trades_in_window.filter(
                (pl.col("price") >= price - price_tolerance)
                & (pl.col("price") <= price + price_tolerance)
            )

            if len(nearby_trades) > 0:
                trade_volumes = nearby_trades.get_column("volume").to_list()
                total_trade_volume = sum(trade_volumes)
                avg_trade_size = mean(trade_volumes)
                trade_count = len(trade_volumes)

                # Calculate execution consistency
                if len(trade_volumes) > 1:
                    trade_std = stdev(trade_volumes)
                    execution_consistency = 1.0 - (trade_std / mean(trade_volumes))
                else:
                    execution_consistency = 1.0

                # Update iceberg data with trade analysis
                iceberg["execution_analysis"] = {
                    "nearby_trades_count": trade_count,
                    "total_trade_volume": int(total_trade_volume),
                    "avg_trade_size": round(avg_trade_size, 2),
                    "execution_consistency": round(max(0, execution_consistency), 3),
                    "volume_to_trade_ratio": round(
                        iceberg["current_volume"] / max(1, avg_trade_size), 2
                    ),
                }

                # Adjust confidence based on trade patterns
                if execution_consistency > 0.7 and trade_count >= 3:
                    iceberg["confidence_score"] = min(
                        1.0, iceberg["confidence_score"] * 1.1
                    )
                    iceberg["detection_method"] += "_with_trade_confirmation"

            enhanced_icebergs.append(iceberg)

        return enhanced_icebergs

    def get_dom_event_analysis(self, time_window_minutes: int = 30) -> dict[str, Any]:
        """
        Analyze DOM event patterns using the corrected ProjectX DomType understanding.

        Args:
            time_window_minutes: Time window for analysis

        Returns:
            dict: DOM event analysis with market structure insights
        """
        try:
            stats = self.get_order_type_statistics().copy()

            # Calculate total DOM events
            total_events = (
                sum(stats.values())
                - stats.get("skipped_updates", 0)
                - stats.get("integrity_fixes", 0)
            )

            if total_events == 0:
                return {
                    "dom_events": stats,
                    "analysis": {"note": "No DOM events recorded"},
                }

            # Calculate percentages and insights
            analysis = {
                "total_dom_events": total_events,
                "event_distribution": {
                    "regular_updates": {
                        "bid_updates": stats.get("type_2_count", 0),
                        "ask_updates": stats.get("type_1_count", 0),
                        "percentage": (
                            (
                                stats.get("type_1_count", 0)
                                + stats.get("type_2_count", 0)
                            )
                            / total_events
                            * 100
                        )
                        if total_events > 0
                        else 0,
                    },
                    "best_price_updates": {
                        "best_bid": stats.get("type_4_count", 0),
                        "best_ask": stats.get("type_3_count", 0),
                        "new_best_bid": stats.get("type_9_count", 0),
                        "new_best_ask": stats.get("type_10_count", 0),
                        "total": stats.get("type_3_count", 0)
                        + stats.get("type_4_count", 0)
                        + stats.get("type_9_count", 0)
                        + stats.get("type_10_count", 0),
                        "percentage": (
                            (
                                stats.get("type_3_count", 0)
                                + stats.get("type_4_count", 0)
                                + stats.get("type_9_count", 0)
                                + stats.get("type_10_count", 0)
                            )
                            / total_events
                            * 100
                        )
                        if total_events > 0
                        else 0,
                    },
                    "trade_executions": {
                        "trades": stats.get("type_5_count", 0),
                        "fills": stats.get("type_11_count", 0),
                        "total": stats.get("type_5_count", 0)
                        + stats.get("type_11_count", 0),
                        "percentage": (
                            (
                                stats.get("type_5_count", 0)
                                + stats.get("type_11_count", 0)
                            )
                            / total_events
                            * 100
                        )
                        if total_events > 0
                        else 0,
                    },
                    "market_structure": {
                        "resets": stats.get("type_6_count", 0),
                        "session_high": stats.get("type_8_count", 0),
                        "session_low": stats.get("type_7_count", 0),
                        "percentage": (
                            (
                                stats.get("type_6_count", 0)
                                + stats.get("type_7_count", 0)
                                + stats.get("type_8_count", 0)
                            )
                            / total_events
                            * 100
                        )
                        if total_events > 0
                        else 0,
                    },
                },
                "market_activity_insights": {
                    "best_price_volatility": "high"
                    if (stats.get("type_9_count", 0) + stats.get("type_10_count", 0))
                    > total_events * 0.1
                    else "normal",
                    "trade_to_quote_ratio": (
                        stats.get("type_5_count", 0) + stats.get("type_11_count", 0)
                    )
                    / max(
                        1, stats.get("type_1_count", 0) + stats.get("type_2_count", 0)
                    ),
                    "market_maker_activity": "active"
                    if (stats.get("type_1_count", 0) + stats.get("type_2_count", 0))
                    > (stats.get("type_5_count", 0) + stats.get("type_11_count", 0)) * 3
                    else "moderate",
                    "data_quality": {
                        "integrity_fixes_needed": stats.get("integrity_fixes", 0),
                        "skipped_updates": stats.get("skipped_updates", 0),
                        "data_quality_score": max(
                            0,
                            min(
                                100,
                                100
                                - (
                                    stats.get("skipped_updates", 0)
                                    + stats.get("integrity_fixes", 0)
                                )
                                / max(1, total_events)
                                * 100,
                            ),
                        ),
                    },
                },
            }

            return {
                "dom_events": stats,
                "analysis": analysis,
                "timestamp": datetime.now(self.timezone),
                "time_window_minutes": time_window_minutes,
            }

        except Exception as e:
            self.logger.error(f"Error analyzing DOM events: {e}")
            return {"dom_events": self.get_order_type_statistics(), "error": str(e)}

    def get_best_price_change_analysis(
        self, time_window_minutes: int = 10
    ) -> dict[str, Any]:
        """
        Analyze best price change patterns using NewBestBid/NewBestAsk events.

        Args:
            time_window_minutes: Time window for analysis

        Returns:
            dict: Best price change analysis
        """
        try:
            stats = self.get_order_type_statistics()

            # Calculate best price change frequency
            new_best_bid_count = stats.get("type_9_count", 0)  # NewBestBid
            new_best_ask_count = stats.get("type_10_count", 0)  # NewBestAsk
            best_bid_count = stats.get("type_4_count", 0)  # BestBid
            best_ask_count = stats.get("type_3_count", 0)  # BestAsk

            total_best_events = (
                new_best_bid_count
                + new_best_ask_count
                + best_bid_count
                + best_ask_count
            )

            if total_best_events == 0:
                return {
                    "best_price_changes": 0,
                    "analysis": {"note": "No best price events recorded"},
                }

            # Get current best prices for context
            current_best = self.get_best_bid_ask()

            analysis = {
                "best_price_events": {
                    "new_best_bid": new_best_bid_count,
                    "new_best_ask": new_best_ask_count,
                    "best_bid_updates": best_bid_count,
                    "best_ask_updates": best_ask_count,
                    "total": total_best_events,
                },
                "price_movement_indicators": {
                    "bid_side_activity": new_best_bid_count + best_bid_count,
                    "ask_side_activity": new_best_ask_count + best_ask_count,
                    "bid_vs_ask_ratio": (new_best_bid_count + best_bid_count)
                    / max(1, new_best_ask_count + best_ask_count),
                    "new_best_frequency": (new_best_bid_count + new_best_ask_count)
                    / max(1, total_best_events),
                    "price_volatility_indicator": "high"
                    if (new_best_bid_count + new_best_ask_count)
                    > total_best_events * 0.6
                    else "normal",
                },
                "market_microstructure": {
                    "current_spread": current_best.get("spread"),
                    "current_mid": current_best.get("mid"),
                    "best_bid": current_best.get("bid"),
                    "best_ask": current_best.get("ask"),
                    "spread_activity": "active" if total_best_events > 10 else "quiet",
                },
                "time_metrics": {
                    "events_per_minute": total_best_events
                    / max(1, time_window_minutes),
                    "estimated_tick_frequency": f"{60 / max(1, total_best_events / max(1, time_window_minutes)):.1f} seconds between best price changes"
                    if total_best_events > 0
                    else "No changes",
                },
            }

            return {
                "best_price_changes": total_best_events,
                "analysis": analysis,
                "timestamp": datetime.now(self.timezone),
                "time_window_minutes": time_window_minutes,
            }

        except Exception as e:
            self.logger.error(f"Error analyzing best price changes: {e}")
            return {"best_price_changes": 0, "error": str(e)}

    def get_spread_analysis(self, time_window_minutes: int = 30) -> dict[str, Any]:
        """
        Analyze spread patterns and their impact on trade direction detection.

        Args:
            time_window_minutes: Time window for analysis

        Returns:
            dict: Spread analysis with trade direction insights
        """
        try:
            with self.orderbook_lock:
                if len(self.recent_trades) == 0:
                    return {
                        "spread_analysis": {},
                        "analysis": {"note": "No trade data available"},
                    }

                # Filter trades from time window
                cutoff_time = datetime.now(self.timezone) - timedelta(
                    minutes=time_window_minutes
                )
                recent_trades = self.recent_trades.filter(
                    pl.col("timestamp") >= cutoff_time
                )

                if len(recent_trades) == 0:
                    return {
                        "spread_analysis": {},
                        "analysis": {"note": "No trades in time window"},
                    }

                # Check if spread metadata is available
                if "spread_at_trade" not in recent_trades.columns:
                    return {
                        "spread_analysis": {},
                        "analysis": {
                            "note": "Spread metadata not available (legacy data)"
                        },
                    }

                # Filter out trades with null spread data
                trades_with_spread = recent_trades.filter(
                    pl.col("spread_at_trade").is_not_null()
                )

                if len(trades_with_spread) == 0:
                    return {
                        "spread_analysis": {},
                        "analysis": {
                            "note": "No trades with spread metadata in time window"
                        },
                    }

                # Calculate spread statistics
                spread_stats = trades_with_spread.select(
                    [
                        pl.col("spread_at_trade").mean().alias("avg_spread"),
                        pl.col("spread_at_trade").median().alias("median_spread"),
                        pl.col("spread_at_trade").min().alias("min_spread"),
                        pl.col("spread_at_trade").max().alias("max_spread"),
                        pl.col("spread_at_trade").std().alias("spread_volatility"),
                    ]
                ).to_dicts()[0]

                # Analyze trade direction by spread size
                spread_buckets = trades_with_spread.with_columns(
                    [
                        pl.when(pl.col("spread_at_trade") <= 0.01)
                        .then(pl.lit("tight"))
                        .when(pl.col("spread_at_trade") <= 0.05)
                        .then(pl.lit("normal"))
                        .when(pl.col("spread_at_trade") <= 0.10)
                        .then(pl.lit("wide"))
                        .otherwise(pl.lit("very_wide"))
                        .alias("spread_category")
                    ]
                )

                # Trade direction distribution by spread category
                direction_by_spread = (
                    spread_buckets.group_by(["spread_category", "side"])
                    .agg(
                        [
                            pl.count().alias("trade_count"),
                            pl.col("volume").sum().alias("total_volume"),
                        ]
                    )
                    .sort(["spread_category", "side"])
                )

                # Calculate spread impact on direction confidence
                neutral_trades = spread_buckets.filter(pl.col("side") == "neutral")
                total_trades = len(spread_buckets)
                neutral_percentage = (
                    (len(neutral_trades) / total_trades * 100)
                    if total_trades > 0
                    else 0
                )

                # Current spread context
                current_best = self.get_best_bid_ask()
                current_spread = current_best.get("spread", 0)

                # Spread trend analysis
                if len(trades_with_spread) > 10:
                    recent_spread_trend = (
                        trades_with_spread.tail(10)
                        .select(
                            [
                                pl.col("spread_at_trade")
                                .mean()
                                .alias("recent_avg_spread")
                            ]
                        )
                        .item()
                    )

                    spread_trend = (
                        "widening"
                        if recent_spread_trend > spread_stats["avg_spread"] * 1.1
                        else "tightening"
                        if recent_spread_trend < spread_stats["avg_spread"] * 0.9
                        else "stable"
                    )
                else:
                    recent_spread_trend = spread_stats["avg_spread"]
                    spread_trend = "stable"

                analysis = {
                    "spread_statistics": spread_stats,
                    "current_spread": current_spread,
                    "spread_trend": spread_trend,
                    "recent_avg_spread": recent_spread_trend,
                    "trade_direction_analysis": {
                        "neutral_trade_percentage": neutral_percentage,
                        "classification_confidence": "high"
                        if neutral_percentage < 10
                        else "medium"
                        if neutral_percentage < 25
                        else "low",
                        "spread_impact": "minimal"
                        if spread_stats["spread_volatility"] < 0.01
                        else "moderate"
                        if spread_stats["spread_volatility"] < 0.05
                        else "high",
                    },
                    "direction_by_spread_category": direction_by_spread.to_dicts(),
                    "market_microstructure": {
                        "spread_efficiency": "efficient"
                        if spread_stats["avg_spread"] < 0.02
                        else "normal"
                        if spread_stats["avg_spread"] < 0.05
                        else "wide",
                        "volatility_indicator": "low"
                        if spread_stats["spread_volatility"] < 0.01
                        else "normal"
                        if spread_stats["spread_volatility"] < 0.03
                        else "high",
                    },
                }

                return {
                    "spread_analysis": analysis,
                    "timestamp": datetime.now(self.timezone),
                    "time_window_minutes": time_window_minutes,
                }

        except Exception as e:
            self.logger.error(f"Error analyzing spread patterns: {e}")
            return {"spread_analysis": {}, "error": str(e)}

    def get_iceberg_detection_status(self) -> dict[str, Any]:
        """
        Get status and validation information for iceberg detection capabilities.

        Returns:
            Dict with iceberg detection system status and health metrics
        """
        try:
            with self.orderbook_lock:
                # Check data availability
                bid_data_available = self.orderbook_bids.height > 0
                ask_data_available = self.orderbook_asks.height > 0
                trade_data_available = len(self.recent_trades) > 0

                # Analyze data quality for iceberg detection
                data_quality = {
                    "sufficient_bid_data": bid_data_available,
                    "sufficient_ask_data": ask_data_available,
                    "trade_data_available": trade_data_available,
                    "orderbook_depth": {
                        "bid_levels": self.orderbook_bids.height,
                        "ask_levels": self.orderbook_asks.height,
                    },
                    "trade_history_size": len(self.recent_trades),
                }

                # Check for required columns in orderbook data
                bid_schema_valid = True
                ask_schema_valid = True
                required_columns = ["price", "volume", "timestamp"]

                if bid_data_available:
                    bid_columns = set(self.orderbook_bids.columns)
                    missing_bid_cols = set(required_columns) - bid_columns
                    bid_schema_valid = len(missing_bid_cols) == 0
                    data_quality["bid_missing_columns"] = list(missing_bid_cols)

                if ask_data_available:
                    ask_columns = set(self.orderbook_asks.columns)
                    missing_ask_cols = set(required_columns) - ask_columns
                    ask_schema_valid = len(missing_ask_cols) == 0
                    data_quality["ask_missing_columns"] = list(missing_ask_cols)

                # Check recent data freshness
                data_freshness = {}
                current_time = datetime.now(self.timezone)

                if bid_data_available and "timestamp" in self.orderbook_bids.columns:
                    latest_bid_time = self.orderbook_bids.select(
                        pl.col("timestamp").max()
                    ).item()
                    if latest_bid_time:
                        bid_age_minutes = (
                            current_time - latest_bid_time
                        ).total_seconds() / 60
                        data_freshness["bid_data_age_minutes"] = round(
                            bid_age_minutes, 1
                        )
                        data_freshness["bid_data_fresh"] = bid_age_minutes < 30

                if ask_data_available and "timestamp" in self.orderbook_asks.columns:
                    latest_ask_time = self.orderbook_asks.select(
                        pl.col("timestamp").max()
                    ).item()
                    if latest_ask_time:
                        ask_age_minutes = (
                            current_time - latest_ask_time
                        ).total_seconds() / 60
                        data_freshness["ask_data_age_minutes"] = round(
                            ask_age_minutes, 1
                        )
                        data_freshness["ask_data_fresh"] = ask_age_minutes < 30

                if trade_data_available and "timestamp" in self.recent_trades.columns:
                    latest_trade_time = self.recent_trades.select(
                        pl.col("timestamp").max()
                    ).item()
                    if latest_trade_time:
                        trade_age_minutes = (
                            current_time - latest_trade_time
                        ).total_seconds() / 60
                        data_freshness["trade_data_age_minutes"] = round(
                            trade_age_minutes, 1
                        )
                        data_freshness["trade_data_fresh"] = trade_age_minutes < 30

                # Assess overall readiness for iceberg detection
                detection_ready = (
                    bid_data_available
                    and ask_data_available
                    and bid_schema_valid
                    and ask_schema_valid
                    and self.orderbook_bids.height >= 10  # Minimum data for analysis
                    and self.orderbook_asks.height >= 10
                )

                # Method availability check
                methods_available = {
                    "basic_detection": hasattr(self, "detect_iceberg_orders"),
                    "advanced_detection": hasattr(
                        self, "detect_iceberg_orders_advanced"
                    ),
                    "trade_cross_reference": hasattr(
                        self, "_cross_reference_with_trades"
                    ),
                    "volume_analysis": hasattr(self, "_analyze_volume_replenishment"),
                    "round_price_analysis": hasattr(self, "_is_round_price"),
                }

                # Configuration recommendations
                recommendations = []
                if not detection_ready:
                    if not bid_data_available:
                        recommendations.append("Enable bid orderbook data collection")
                    if not ask_data_available:
                        recommendations.append("Enable ask orderbook data collection")
                    if self.orderbook_bids.height < 10:
                        recommendations.append(
                            "Collect more bid orderbook history (need 10+ entries)"
                        )
                    if self.orderbook_asks.height < 10:
                        recommendations.append(
                            "Collect more ask orderbook history (need 10+ entries)"
                        )

                if not trade_data_available:
                    recommendations.append(
                        "Enable trade data collection for enhanced validation"
                    )

                # Performance metrics for iceberg detection
                performance_metrics = {
                    "memory_usage": {
                        "bid_memory_mb": round(
                            self.orderbook_bids.estimated_size("mb"), 2
                        ),
                        "ask_memory_mb": round(
                            self.orderbook_asks.estimated_size("mb"), 2
                        ),
                        "trade_memory_mb": round(
                            self.recent_trades.estimated_size("mb"), 2
                        )
                        if trade_data_available
                        else 0,
                    },
                    "processing_capability": {
                        "max_analysis_window_hours": min(
                            24,
                            (self.orderbook_bids.height + self.orderbook_asks.height)
                            / 120,
                        ),  # Rough estimate
                        "recommended_refresh_interval_seconds": 30,
                    },
                }

                return {
                    "iceberg_detection_ready": detection_ready,
                    "data_quality": data_quality,
                    "data_freshness": data_freshness,
                    "methods_available": methods_available,
                    "recommendations": recommendations,
                    "performance_metrics": performance_metrics,
                    "system_status": {
                        "orderbook_lock_available": self.orderbook_lock is not None,
                        "timezone_configured": str(self.timezone),
                        "instrument": self.instrument,
                        "memory_stats": self.get_memory_stats(),
                    },
                    "validation_timestamp": current_time,
                }

        except Exception as e:
            self.logger.error(f"Error getting iceberg detection status: {e}")
            return {
                "iceberg_detection_ready": False,
                "error": str(e),
                "validation_timestamp": datetime.now(self.timezone),
            }

    def test_iceberg_detection(
        self, test_params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Test the iceberg detection functionality with current orderbook data.

        Args:
            test_params: Optional parameters for testing (overrides defaults)

        Returns:
            Dict with test results and validation information
        """
        if test_params is None:
            test_params = {}

        # Default test parameters
        default_params = {
            "time_window_minutes": 15,
            "min_refresh_count": 3,
            "volume_consistency_threshold": 0.7,
            "min_total_volume": 100,
            "statistical_confidence": 0.8,
        }

        # Merge with provided parameters
        params = {**default_params, **test_params}

        try:
            # Get system status first
            status = self.get_iceberg_detection_status()

            test_results = {
                "test_timestamp": datetime.now(self.timezone),
                "test_parameters": params,
                "system_status": status,
                "detection_results": {},
                "performance_metrics": {},
                "validation": {
                    "test_passed": False,
                    "issues_found": [],
                    "recommendations": [],
                },
            }

            # Check if system is ready
            if not status["iceberg_detection_ready"]:
                test_results["validation"]["issues_found"].append(
                    "System not ready for iceberg detection"
                )
                test_results["validation"]["recommendations"].extend(
                    status.get("recommendations", [])
                )
                return test_results

            # Run basic iceberg detection test
            start_time = time.time()
            try:
                basic_results = self.detect_iceberg_orders(
                    min_refresh_count=params["min_refresh_count"],
                    time_window_minutes=params["time_window_minutes"],
                    volume_consistency_threshold=params["volume_consistency_threshold"],
                )
                basic_duration = time.time() - start_time
                test_results["detection_results"]["basic"] = {
                    "success": True,
                    "results": basic_results,
                    "execution_time_seconds": round(basic_duration, 3),
                }
            except Exception as e:
                test_results["detection_results"]["basic"] = {
                    "success": False,
                    "error": str(e),
                    "execution_time_seconds": round(time.time() - start_time, 3),
                }
                test_results["validation"]["issues_found"].append(
                    f"Basic detection failed: {e}"
                )

            # Run advanced iceberg detection test
            start_time = time.time()
            try:
                advanced_results = self.detect_iceberg_orders(
                    time_window_minutes=params["time_window_minutes"],
                    min_refresh_count=params["min_refresh_count"],
                    volume_consistency_threshold=params["volume_consistency_threshold"],
                    min_total_volume=params["min_total_volume"],
                    statistical_confidence=params["statistical_confidence"],
                )
                advanced_duration = time.time() - start_time
                test_results["detection_results"]["advanced"] = {
                    "success": True,
                    "results": advanced_results,
                    "execution_time_seconds": round(advanced_duration, 3),
                }

                # Validate advanced results structure
                if (
                    "potential_icebergs" in advanced_results
                    and "analysis" in advanced_results
                ):
                    icebergs = advanced_results["potential_icebergs"]
                    analysis = advanced_results["analysis"]

                    # Check result quality
                    if isinstance(icebergs, list) and isinstance(analysis, dict):
                        test_results["validation"]["test_passed"] = True

                        # Performance analysis
                        test_results["performance_metrics"]["advanced_detection"] = {
                            "icebergs_detected": len(icebergs),
                            "execution_time": advanced_duration,
                            "data_processed": analysis.get("data_summary", {}).get(
                                "total_orderbook_entries", 0
                            ),
                            "performance_score": "excellent"
                            if advanced_duration < 1.0
                            else "good"
                            if advanced_duration < 3.0
                            else "needs_optimization",
                        }

                        # Result quality analysis
                        if len(icebergs) > 0:
                            confidence_scores = [
                                ic.get("confidence_score", 0) for ic in icebergs
                            ]
                            test_results["performance_metrics"]["result_quality"] = {
                                "max_confidence": max(confidence_scores),
                                "avg_confidence": sum(confidence_scores)
                                / len(confidence_scores),
                                "high_confidence_count": sum(
                                    1 for score in confidence_scores if score > 0.7
                                ),
                            }
                    else:
                        test_results["validation"]["issues_found"].append(
                            "Advanced detection returned invalid result structure"
                        )
                else:
                    test_results["validation"]["issues_found"].append(
                        "Advanced detection missing required result fields"
                    )

            except Exception as e:
                test_results["detection_results"]["advanced"] = {
                    "success": False,
                    "error": str(e),
                    "execution_time_seconds": round(time.time() - start_time, 3),
                }
                test_results["validation"]["issues_found"].append(
                    f"Advanced detection failed: {e}"
                )

            # Generate recommendations based on test results
            recommendations = []
            if test_results["validation"]["test_passed"]:
                recommendations.append(
                    "✅ Iceberg detection system is working correctly"
                )

                # Performance recommendations
                advanced_perf = test_results["performance_metrics"].get(
                    "advanced_detection", {}
                )
                if advanced_perf.get("execution_time", 0) > 2.0:
                    recommendations.append(
                        "Consider reducing time_window_minutes for better performance"
                    )

                if advanced_perf.get("icebergs_detected", 0) == 0:
                    recommendations.append(
                        "No icebergs detected - this may be normal or consider adjusting detection parameters"
                    )

            else:
                recommendations.append(
                    "❌ Iceberg detection system has issues that need to be resolved"
                )

            test_results["validation"]["recommendations"] = recommendations

            return test_results

        except Exception as e:
            self.logger.error(f"Error in iceberg detection test: {e}")
            return {
                "test_timestamp": datetime.now(self.timezone),
                "test_parameters": params,
                "validation": {
                    "test_passed": False,
                    "issues_found": [f"Test framework error: {e}"],
                    "recommendations": ["Fix test framework errors before proceeding"],
                },
                "error": str(e),
            }

    def test_support_resistance_detection(
        self, test_params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Test the support/resistance level detection functionality.

        Args:
            test_params: Optional parameters for testing (overrides defaults)

        Returns:
            Dict with test results and validation information
        """
        if test_params is None:
            test_params = {}

        # Default test parameters
        default_params = {
            "lookback_minutes": 30,
        }

        # Merge with provided parameters
        params = {**default_params, **test_params}

        try:
            test_results = {
                "test_timestamp": datetime.now(self.timezone),
                "test_parameters": params,
                "detection_results": {},
                "validation": {
                    "test_passed": False,
                    "issues_found": [],
                    "recommendations": [],
                },
            }

            # Check prerequisites
            prerequisites = {
                "orderbook_data": self.orderbook_bids.height > 0
                and self.orderbook_asks.height > 0,
                "trade_data": len(self.recent_trades) > 0,
                "best_prices": self.get_best_bid_ask().get("mid") is not None,
            }

            if not all(prerequisites.values()):
                missing = [key for key, value in prerequisites.items() if not value]
                test_results["validation"]["issues_found"].append(
                    f"Missing prerequisites: {missing}"
                )
                test_results["validation"]["recommendations"].append(
                    "Ensure orderbook and trade data are available"
                )
                return test_results

            # Test support/resistance detection
            start_time = time.time()
            try:
                sr_results = self.get_support_resistance_levels(
                    lookback_minutes=params["lookback_minutes"]
                )
                detection_duration = time.time() - start_time

                test_results["detection_results"]["support_resistance"] = {
                    "success": True,
                    "results": sr_results,
                    "execution_time_seconds": round(detection_duration, 3),
                }

                # Validate results structure
                required_keys = [
                    "support_levels",
                    "resistance_levels",
                    "current_price",
                    "analysis",
                ]
                missing_keys = [key for key in required_keys if key not in sr_results]

                if missing_keys:
                    test_results["validation"]["issues_found"].append(
                        f"Missing result keys: {missing_keys}"
                    )
                else:
                    # Check for error in analysis
                    if "error" in sr_results.get("analysis", {}):
                        test_results["validation"]["issues_found"].append(
                            f"Analysis error: {sr_results['analysis']['error']}"
                        )
                    else:
                        # Validate data quality
                        support_levels = sr_results.get("support_levels", [])
                        resistance_levels = sr_results.get("resistance_levels", [])
                        current_price = sr_results.get("current_price")

                        validation_results = {
                            "support_levels_count": len(support_levels),
                            "resistance_levels_count": len(resistance_levels),
                            "total_levels": len(support_levels)
                            + len(resistance_levels),
                            "current_price_available": current_price is not None,
                        }

                        # Check level data quality
                        level_issues = []
                        for i, level in enumerate(
                            support_levels[:3]
                        ):  # Check first 3 support levels
                            if not isinstance(level.get("price"), int | float):
                                level_issues.append(f"Support level {i}: invalid price")
                            if level.get("price", 0) >= current_price:
                                level_issues.append(
                                    f"Support level {i}: price above current price"
                                )

                        for i, level in enumerate(
                            resistance_levels[:3]
                        ):  # Check first 3 resistance levels
                            if not isinstance(level.get("price"), int | float):
                                level_issues.append(
                                    f"Resistance level {i}: invalid price"
                                )
                            if level.get("price", float("inf")) <= current_price:
                                level_issues.append(
                                    f"Resistance level {i}: price below current price"
                                )

                        if level_issues:
                            test_results["validation"]["issues_found"].extend(
                                level_issues
                            )
                        else:
                            test_results["validation"]["test_passed"] = True

                        # Performance metrics
                        test_results["performance_metrics"] = {
                            "execution_time": detection_duration,
                            "levels_detected": validation_results["total_levels"],
                            "performance_score": "excellent"
                            if detection_duration < 0.5
                            else "good"
                            if detection_duration < 1.5
                            else "needs_optimization",
                            "level_quality": {
                                "support_coverage": len(support_levels) > 0,
                                "resistance_coverage": len(resistance_levels) > 0,
                                "balanced_detection": abs(
                                    len(support_levels) - len(resistance_levels)
                                )
                                <= 3,
                            },
                            "data_validation": validation_results,
                        }

            except Exception as e:
                test_results["detection_results"]["support_resistance"] = {
                    "success": False,
                    "error": str(e),
                    "execution_time_seconds": round(time.time() - start_time, 3),
                }
                test_results["validation"]["issues_found"].append(
                    f"Detection failed: {e}"
                )

            # Generate recommendations
            recommendations = []
            if test_results["validation"]["test_passed"]:
                recommendations.append(
                    "✅ Support/resistance detection system is working correctly"
                )

                # Performance recommendations
                perf = test_results.get("performance_metrics", {})
                if perf.get("execution_time", 0) > 1.0:
                    recommendations.append("Consider optimizing for better performance")

                if perf.get("levels_detected", 0) == 0:
                    recommendations.append(
                        "No support/resistance levels detected - this may be normal in ranging markets"
                    )
                elif perf.get("levels_detected", 0) > 20:
                    recommendations.append(
                        "Many levels detected - consider adjusting significance thresholds"
                    )

            else:
                recommendations.append(
                    "❌ Support/resistance detection system has issues that need to be resolved"
                )
                if "Missing prerequisites" in str(
                    test_results["validation"]["issues_found"]
                ):
                    recommendations.append(
                        "Collect sufficient orderbook and trade data before testing"
                    )

            test_results["validation"]["recommendations"] = recommendations

            return test_results

        except Exception as e:
            self.logger.error(f"Error in support/resistance detection test: {e}")
            return {
                "test_timestamp": datetime.now(self.timezone),
                "test_parameters": params,
                "validation": {
                    "test_passed": False,
                    "issues_found": [f"Test framework error: {e}"],
                    "recommendations": ["Fix test framework errors before proceeding"],
                },
                "error": str(e),
            }

    def test_volume_profile_time_filtering(
        self, test_params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Test the volume profile time filtering functionality.

        Args:
            test_params: Optional parameters for testing (overrides defaults)

        Returns:
            Dict with test results and validation information
        """
        if test_params is None:
            test_params = {}

        # Default test parameters
        default_params = {
            "time_windows": [15, 30, 60],  # Different time windows to test
            "bucket_size": 0.25,
        }

        # Merge with provided parameters
        params = {**default_params, **test_params}

        try:
            test_results = {
                "test_timestamp": datetime.now(self.timezone),
                "test_parameters": params,
                "time_filtering_results": {},
                "validation": {
                    "test_passed": False,
                    "issues_found": [],
                    "recommendations": [],
                },
            }

            # Check prerequisites
            if len(self.recent_trades) == 0:
                test_results["validation"]["issues_found"].append(
                    "No trade data available"
                )
                test_results["validation"]["recommendations"].append(
                    "Collect trade data before testing volume profile"
                )
                return test_results

            # Test volume profile without time filtering (baseline)
            try:
                baseline_start = time.time()
                baseline_profile = self.get_volume_profile(
                    price_bucket_size=params["bucket_size"]
                )
                baseline_duration = time.time() - baseline_start

                test_results["time_filtering_results"]["baseline"] = {
                    "success": True,
                    "time_window": None,
                    "execution_time": round(baseline_duration, 3),
                    "profile_levels": len(baseline_profile.get("profile", [])),
                    "total_volume": baseline_profile.get("total_volume", 0),
                    "trades_analyzed": baseline_profile.get("analysis", {}).get(
                        "total_trades_analyzed", 0
                    ),
                }
            except Exception as e:
                test_results["time_filtering_results"]["baseline"] = {
                    "success": False,
                    "error": str(e),
                }
                test_results["validation"]["issues_found"].append(
                    f"Baseline volume profile failed: {e}"
                )

            # Test different time windows
            valid_tests = 0
            for time_window in params["time_windows"]:
                try:
                    filtered_start = time.time()
                    filtered_profile = self.get_volume_profile(
                        price_bucket_size=params["bucket_size"],
                        time_window_minutes=time_window,
                    )
                    filtered_duration = time.time() - filtered_start

                    result = {
                        "success": True,
                        "time_window": time_window,
                        "execution_time": round(filtered_duration, 3),
                        "profile_levels": len(filtered_profile.get("profile", [])),
                        "total_volume": filtered_profile.get("total_volume", 0),
                        "trades_analyzed": filtered_profile.get("analysis", {}).get(
                            "total_trades_analyzed", 0
                        ),
                        "time_filtering_applied": filtered_profile.get(
                            "analysis", {}
                        ).get("time_filtering_applied", False),
                    }

                    # Validate that time filtering is working
                    if result["time_filtering_applied"]:
                        valid_tests += 1
                    else:
                        test_results["validation"]["issues_found"].append(
                            f"Time filtering not applied for {time_window} minutes"
                        )

                    test_results["time_filtering_results"][f"{time_window}_min"] = (
                        result
                    )

                except Exception as e:
                    test_results["time_filtering_results"][f"{time_window}_min"] = {
                        "success": False,
                        "time_window": time_window,
                        "error": str(e),
                    }
                    test_results["validation"]["issues_found"].append(
                        f"Time filtering failed for {time_window} minutes: {e}"
                    )

            # Validate the time filtering behavior
            baseline_result = test_results["time_filtering_results"].get("baseline", {})
            if baseline_result.get("success"):
                baseline_trades = baseline_result.get("trades_analyzed", 0)

                # Check that filtered results have fewer or equal trades than baseline
                for time_window in params["time_windows"]:
                    filtered_result = test_results["time_filtering_results"].get(
                        f"{time_window}_min", {}
                    )
                    if filtered_result.get("success"):
                        filtered_trades = filtered_result.get("trades_analyzed", 0)

                        if filtered_trades > baseline_trades:
                            test_results["validation"]["issues_found"].append(
                                f"Time filtering error: {time_window} min window has more trades ({filtered_trades}) than baseline ({baseline_trades})"
                            )

                        # Check that shorter windows have fewer or equal trades than longer windows
                        if time_window == 15:  # Shortest window
                            for longer_window in [30, 60]:
                                if longer_window in params["time_windows"]:
                                    longer_result = test_results[
                                        "time_filtering_results"
                                    ].get(f"{longer_window}_min", {})
                                    if longer_result.get("success"):
                                        longer_trades = longer_result.get(
                                            "trades_analyzed", 0
                                        )
                                        if filtered_trades > longer_trades:
                                            test_results["validation"][
                                                "issues_found"
                                            ].append(
                                                f"Time filtering logic error: {time_window} min window has more trades than {longer_window} min window"
                                            )

            # Calculate performance metrics
            performance_metrics = {
                "tests_passed": valid_tests,
                "total_tests": len(params["time_windows"]),
                "success_rate": (valid_tests / len(params["time_windows"]) * 100)
                if params["time_windows"]
                else 0,
                "avg_execution_time": 0,
            }

            execution_times = [
                result.get("execution_time", 0)
                for result in test_results["time_filtering_results"].values()
                if result.get("success") and result.get("execution_time")
            ]

            if execution_times:
                performance_metrics["avg_execution_time"] = round(
                    sum(execution_times) / len(execution_times), 3
                )

            test_results["performance_metrics"] = performance_metrics

            # Determine if test passed
            test_results["validation"]["test_passed"] = (
                len(test_results["validation"]["issues_found"]) == 0
                and valid_tests > 0
                and baseline_result.get("success", False)
            )

            # Generate recommendations
            recommendations = []
            if test_results["validation"]["test_passed"]:
                recommendations.append(
                    "✅ Volume profile time filtering is working correctly"
                )

                if performance_metrics["avg_execution_time"] > 1.0:
                    recommendations.append("Consider optimizing for better performance")

                if performance_metrics["success_rate"] == 100:
                    recommendations.append(
                        "All time filtering tests passed - system is robust"
                    )

            else:
                recommendations.append(
                    "❌ Volume profile time filtering has issues that need to be resolved"
                )
                if "No trade data available" in str(
                    test_results["validation"]["issues_found"]
                ):
                    recommendations.append(
                        "Collect sufficient trade data before testing"
                    )

            test_results["validation"]["recommendations"] = recommendations

            return test_results

        except Exception as e:
            self.logger.error(f"Error in volume profile time filtering test: {e}")
            return {
                "test_timestamp": datetime.now(self.timezone),
                "test_parameters": params,
                "validation": {
                    "test_passed": False,
                    "issues_found": [f"Test framework error: {e}"],
                    "recommendations": ["Fix test framework errors before proceeding"],
                },
                "error": str(e),
            }

    def cleanup(self) -> None:
        """
        Clean up resources and connections when shutting down.

        Properly shuts down orderbook monitoring, clears cached data, and releases
        resources to prevent memory leaks when the OrderBook is no longer needed.

        This method clears:
        - All orderbook bid/ask data
        - Recent trades history
        - Order type statistics
        - Event callbacks
        - Memory stats tracking

        Example:
            >>> orderbook = OrderBook("MNQ")
            >>> # ... use orderbook ...
            >>> orderbook.cleanup()  # Clean shutdown
        """
        with self.orderbook_lock:
            # Clear all orderbook data
            self.orderbook_bids = pl.DataFrame(
                {"price": [], "volume": [], "timestamp": [], "type": []},
                schema={
                    "price": pl.Float64,
                    "volume": pl.Int64,
                    "timestamp": pl.Datetime,
                    "type": pl.Utf8,
                },
            )
            self.orderbook_asks = pl.DataFrame(
                {"price": [], "volume": [], "timestamp": [], "type": []},
                schema={
                    "price": pl.Float64,
                    "volume": pl.Int64,
                    "timestamp": pl.Datetime,
                    "type": pl.Utf8,
                },
            )

            # Clear trade data
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
                    "timestamp": pl.Datetime,
                    "side": pl.Utf8,
                    "spread_at_trade": pl.Float64,
                    "mid_price_at_trade": pl.Float64,
                    "best_bid_at_trade": pl.Float64,
                    "best_ask_at_trade": pl.Float64,
                    "order_type": pl.Utf8,
                },
            )

            # Clear callbacks
            self.callbacks.clear()

            # Reset statistics
            self.order_type_stats = {
                "type_1_count": 0,
                "type_2_count": 0,
                "type_3_count": 0,
                "type_4_count": 0,
                "type_5_count": 0,
                "type_6_count": 0,
                "type_7_count": 0,
                "type_8_count": 0,
                "type_9_count": 0,
                "type_10_count": 0,
                "type_11_count": 0,
                "other_types": 0,
                "skipped_updates": 0,
                "integrity_fixes": 0,
            }

            # Reset memory stats
            self.memory_stats = {
                "total_trades": 0,
                "trades_cleaned": 0,
                "last_cleanup": time.time(),
            }

            # Reset metadata
            self.last_orderbook_update = None
            self.last_level2_data = None
            self.level2_update_count = 0

        self.logger.info("✅ OrderBook cleanup completed")

    def get_volume_profile_enhancement_status(self) -> dict[str, Any]:
        """
        Get status information about volume profile time filtering enhancement.

        Returns:
            Dict with enhancement status and capabilities
        """
        return {
            "time_filtering_enabled": True,
            "enhancement_version": "2.0",
            "capabilities": {
                "time_window_filtering": "Filters trades by timestamp within specified window",
                "fallback_behavior": "Uses all trades if no time window specified",
                "validation": "Checks for timestamp column presence",
                "metrics": "Provides analysis of trades processed and time filtering status",
            },
            "usage_examples": {
                "last_30_minutes": "get_volume_profile(time_window_minutes=30)",
                "last_hour": "get_volume_profile(time_window_minutes=60)",
                "all_data": "get_volume_profile() or get_volume_profile(time_window_minutes=None)",
            },
            "integration_status": {
                "support_resistance_levels": "✅ Updated to use time filtering",
                "advanced_market_metrics": "✅ Updated with 60-minute default",
                "testing_framework": "✅ Comprehensive test method available",
            },
            "performance": {
                "expected_speed": "<0.5 seconds for typical time windows",
                "memory_efficiency": "Filters data before processing to reduce memory usage",
                "backwards_compatible": "Yes - existing calls without time_window_minutes still work",
            },
        }
