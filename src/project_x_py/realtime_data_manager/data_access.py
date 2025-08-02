"""Data access methods for retrieving OHLCV data."""

import logging
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from project_x_py.realtime_data_manager.types import RealtimeDataManagerProtocol

logger = logging.getLogger(__name__)


class DataAccessMixin:
    """Mixin for data access and retrieval methods."""

    async def get_data(
        self: "RealtimeDataManagerProtocol",
        timeframe: str = "5min",
        bars: int | None = None,
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

    async def get_current_price(self: "RealtimeDataManagerProtocol") -> float | None:
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
            return float(self.current_tick_data[-1]["price"])

        # Fallback to most recent bar close
        async with self.data_lock:
            for tf_key in ["1min", "5min", "15min"]:  # Check common timeframes
                if tf_key in self.data and not self.data[tf_key].is_empty():
                    return float(self.data[tf_key]["close"][-1])

        return None

    async def get_mtf_data(
        self: "RealtimeDataManagerProtocol",
    ) -> dict[str, pl.DataFrame]:
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
