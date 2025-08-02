"""Tick and OHLCV data processing functionality."""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import polars as pl

if TYPE_CHECKING:
    from project_x_py.realtime_data_manager.types import RealtimeDataManagerProtocol

logger = logging.getLogger(__name__)


class DataProcessingMixin:
    """Mixin for tick processing and OHLCV bar creation."""

    async def _on_quote_update(
        self: "RealtimeDataManagerProtocol", callback_data: dict[str, Any]
    ) -> None:
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

    async def _on_trade_update(
        self: "RealtimeDataManagerProtocol", callback_data: dict[str, Any]
    ) -> None:
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

    async def _process_tick_data(
        self: "RealtimeDataManagerProtocol", tick: dict[str, Any]
    ) -> None:
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
        self: "RealtimeDataManagerProtocol",
        tf_key: str,
        timestamp: datetime,
        price: float,
        volume: int,
    ) -> None:
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
        self: "RealtimeDataManagerProtocol",
        timestamp: datetime,
        interval: int,
        unit: int,
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
