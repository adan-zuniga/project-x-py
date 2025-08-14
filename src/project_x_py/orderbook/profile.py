"""
Async volume profile and support/resistance analytics for ProjectX.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Implements volume profile, POC, value area, support/resistance, and spread
    analysis for the ProjectX async orderbook. Enables market structure research,
    trade planning, and execution optimization based on historical and real-time data.

Key Features:
    - Volume profile histogram and Point of Control (POC) calculation
    - Value area identification and support/resistance detection
    - Spread analytics and regime change/trend detection
    - Market structure mapping for trading and research

Example Usage:
    ```python
    # V3.1: Volume profiling with TradingSuite's orderbook
    from project_x_py import TradingSuite

    suite = await TradingSuite.create("MNQ", features=["orderbook"])

    # V3.1: Get volume profile with POC and value areas
    vp = await suite.orderbook.get_volume_profile(time_window_minutes=60)
    print(f"POC: {vp['poc']:.2f}")
    print(f"Value Area: {vp['value_area_low']:.2f} - {vp['value_area_high']:.2f}")
    print(f"Volume at POC: {vp['poc_volume']} contracts")

    # V3.1: Support/resistance levels
    levels = await suite.orderbook.get_support_resistance_levels()
    for support in levels["support_levels"]:
        print(f"Support at {support['price']:.2f}: {support['strength']} touches")

    await suite.disconnect()
    ```

See Also:
    - `orderbook.base.OrderBookBase`
    - `orderbook.analytics.MarketAnalytics`
    - `orderbook.detection.OrderDetection`
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import polars as pl

from project_x_py.orderbook.base import OrderBookBase
from project_x_py.types.response_types import (
    LiquidityAnalysisResponse,
)


class VolumeProfile:
    """
    Provides volume profile and price level analysis.

    This class implements advanced market structure analysis methods focusing on volume
    distribution and key price level identification. It is designed as a specialized
    component of the OrderBook that reveals deeper insights into market structure
    and participant behavior patterns.

    Key functionalities:
    1. Volume profile generation - Creates histogram-style analysis of volume distribution
       across price levels, identifying high-volume nodes and areas of interest
    2. Support/resistance detection - Identifies price levels that have shown significant
       reaction in the past based on price history and order flow
    3. Spread analysis - Studies bid-ask spread patterns over time to identify market
       regime changes and liquidity conditions

    These analyses are particularly useful for:
    - Identifying key price levels for trade entry and exit
    - Understanding where significant market participant activity has occurred
    - Recognizing market structure patterns and regime changes
    - Planning trade executions around areas of expected support/resistance

    The class implements thread-safe methods that operate on the historical data
    accumulated by the orderbook, with configurable time window parameters to
    focus analysis on the most relevant recent market activity.
    """

    def __init__(self, orderbook: OrderBookBase):
        self.orderbook = orderbook
        self.logger = logging.getLogger(__name__)

    async def get_volume_profile(
        self, time_window_minutes: int = 60, price_bins: int = 20
    ) -> dict[str, Any]:
        """
        Calculate volume profile showing volume distribution by price.

        Volume profile analysis reveals where the most trading activity has occurred
        by creating a histogram of volume distribution across price levels. This is
        a fundamental tool for identifying key areas of market interest, support/
        resistance levels, and understanding market structure.

        Key Metrics Calculated:
        1. Point of Control (POC): The price level with the highest volume
        2. Value Area: The range containing 70% of the total volume around the POC
        3. Price bins: Histogram bins showing volume at each price level
        4. Volume distribution: Complete breakdown of trading activity

        The analysis works by:
        - Filtering trades within the specified time window
        - Dividing the price range into equal-sized bins
        - Calculating total volume for each price bin
        - Identifying the POC as the bin with maximum volume
        - Expanding around the POC to find the value area (70% of volume)

        Args:
            time_window_minutes: Time window to analyze in minutes (default: 60).
                Larger windows provide more data but may include less relevant
                historical information.
            price_bins: Number of price bins for the histogram (default: 20).
                More bins provide finer granularity but may fragment the data;
                fewer bins provide smoother distribution but less detail.

        Returns:
            Dict containing comprehensive volume profile analysis:
                price_bins: List of price bin centers
                volumes: List of volumes corresponding to each price bin
                poc: Point of Control price (highest volume price)
                value_area_high: Upper boundary of the value area
                value_area_low: Lower boundary of the value area
                total_volume: Total volume analyzed
                time_window_minutes: Time window used for analysis

        Example:
            >>> # Get 1-hour volume profile with 30 price bins
            >>> profile = await orderbook.get_volume_profile(
            ...     time_window_minutes=60, price_bins=30
            ... )
            >>> print(f"POC at {profile['poc']}")
            >>> print(
            ...     f"Value area: {profile['value_area_low']} - {profile['value_area_high']}"
            ... )
            >>> print(f"Total volume: {profile['total_volume']}")
            >>>
            >>> # Find bins with highest activity
            >>> max_vol_idx = profile["volumes"].index(max(profile["volumes"]))
            >>> print(
            ...     f"Highest volume: {profile['volumes'][max_vol_idx]} at {profile['price_bins'][max_vol_idx]}"
            ... )
        """
        async with self.orderbook.orderbook_lock:
            try:
                if self.orderbook.recent_trades.is_empty():
                    return {
                        "price_bins": [],
                        "volumes": [],
                        "poc": None,  # Point of Control
                        "value_area_high": None,
                        "value_area_low": None,
                        "total_volume": 0,
                    }

                # Filter trades within time window
                cutoff_time = datetime.now(self.orderbook.timezone) - timedelta(
                    minutes=time_window_minutes
                )
                recent_trades = self.orderbook.recent_trades.filter(
                    pl.col("timestamp") >= cutoff_time
                )

                if recent_trades.is_empty():
                    return {
                        "price_bins": [],
                        "volumes": [],
                        "poc": None,
                        "value_area_high": None,
                        "value_area_low": None,
                        "total_volume": 0,
                    }
                price_min = recent_trades["price"].min()
                price_max = recent_trades["price"].max()

                # Calculate price range
                min_price = float(str(price_min))
                max_price = float(str(price_max))
                price_range = max_price - min_price

                if price_range == 0:
                    # All trades at same price
                    return {
                        "price_bins": [min_price],
                        "volumes": [int(recent_trades["volume"].sum())],
                        "poc": min_price,
                        "value_area_high": min_price,
                        "value_area_low": min_price,
                        "total_volume": int(recent_trades["volume"].sum()),
                    }

                # Create price bins
                bin_size = price_range / price_bins
                bins = [min_price + i * bin_size for i in range(price_bins + 1)]

                # Calculate volume for each bin
                volume_by_bin = []
                bin_centers = []

                for i in range(len(bins) - 1):
                    bin_low = bins[i]
                    bin_high = bins[i + 1]
                    bin_center = (bin_low + bin_high) / 2

                    # Filter trades in this bin
                    bin_trades = recent_trades.filter(
                        (pl.col("price") >= bin_low) & (pl.col("price") < bin_high)
                    )

                    bin_volume = (
                        int(bin_trades["volume"].sum())
                        if not bin_trades.is_empty()
                        else 0
                    )
                    volume_by_bin.append(bin_volume)
                    bin_centers.append(bin_center)

                # Find Point of Control (POC) - price with highest volume
                max_volume_idx = volume_by_bin.index(max(volume_by_bin))
                poc = bin_centers[max_volume_idx]

                # Calculate Value Area (70% of volume around POC)
                total_volume = sum(volume_by_bin)
                value_area_volume = total_volume * 0.7

                # Expand from POC to find value area
                value_area_low_idx = max_volume_idx
                value_area_high_idx = max_volume_idx
                accumulated_volume = volume_by_bin[max_volume_idx]

                while accumulated_volume < value_area_volume:
                    # Check which side to expand
                    expand_low = value_area_low_idx > 0
                    expand_high = value_area_high_idx < len(volume_by_bin) - 1

                    if expand_low and expand_high:
                        # Choose side with more volume
                        low_volume = volume_by_bin[value_area_low_idx - 1]
                        high_volume = volume_by_bin[value_area_high_idx + 1]

                        if low_volume >= high_volume:
                            value_area_low_idx -= 1
                            accumulated_volume += low_volume
                        else:
                            value_area_high_idx += 1
                            accumulated_volume += high_volume
                    elif expand_low:
                        value_area_low_idx -= 1
                        accumulated_volume += volume_by_bin[value_area_low_idx]
                    elif expand_high:
                        value_area_high_idx += 1
                        accumulated_volume += volume_by_bin[value_area_high_idx]
                    else:
                        break

                return {
                    "price_bins": bin_centers,
                    "volumes": volume_by_bin,
                    "poc": poc,
                    "value_area_high": bin_centers[value_area_high_idx],
                    "value_area_low": bin_centers[value_area_low_idx],
                    "total_volume": total_volume,
                    "time_window_minutes": time_window_minutes,
                }

            except Exception as e:
                self.logger.error(f"Error calculating volume profile: {e}")
                return {"error": str(e)}

    async def get_support_resistance_levels(
        self,
        lookback_minutes: int = 120,
        min_touches: int = 3,
        price_tolerance: float = 0.1,
    ) -> dict[str, Any]:
        """
        Identify support and resistance levels based on price history.

        This method analyzes historical price action to identify significant support
        and resistance levels where price has repeatedly reacted. These levels are
        critical for trading decisions as they often represent areas where price
        may reverse or consolidate.

        Algorithm Overview:
        1. Collects price points from recent trades and orderbook levels
        2. Groups nearby prices within the tolerance range
        3. Counts how many times each price cluster was "touched"
        4. Identifies clusters with sufficient touches as support/resistance
        5. Classifies levels as support (below current price) or resistance (above)

        A "touch" is counted when:
        - A trade occurs at or near the price level
        - The orderbook shows significant volume at the level
        - Price approaches but doesn't significantly break through the level

        Strength Assessment:
        - More touches indicate stronger levels
        - Recent touches are weighted more heavily
        - Volume at the level increases its significance

        Args:
            lookback_minutes: Time window to analyze in minutes (default: 120).
                Longer periods capture more historical levels but may include
                outdated information. Shorter periods focus on recent structure.
            min_touches: Minimum number of price touches required for a level
                to qualify as support/resistance (default: 3). Higher values
                identify only the strongest levels.
            price_tolerance: Price range to group similar levels (default: 0.1).
                This should be adjusted based on the instrument's tick size and
                typical price movement.

        Returns:
            Dict containing support and resistance analysis:
                support_levels: List of identified support levels, each containing:
                    - price: The support price level
                    - touches: Number of times price touched this level
                    - strength: Relative strength score (0.0 to 1.0)
                    - last_touch: Timestamp of most recent touch
                    - volume_at_level: Average volume when price was at this level
                resistance_levels: List of identified resistance levels (same format)
                strongest_support: The support level with highest strength score
                strongest_resistance: The resistance level with highest strength score
                current_price: Current market price for reference
                analysis_window: Time window used for the analysis

        Example:
            >>> # Find strong support/resistance over 4 hours
            >>> levels = await orderbook.get_support_resistance_levels(
            ...     lookback_minutes=240, min_touches=5, price_tolerance=0.25
            ... )
            >>> print(f"Found {len(levels['support_levels'])} support levels")
            >>> for level in levels["support_levels"]:
            ...     print(
            ...         f"Support at {level['price']}: {level['touches']} touches, strength {level['strength']:.2f}"
            ...     )
            >>>
            >>> if levels["strongest_resistance"]:
            ...     print(f"Key resistance: {levels['strongest_resistance']['price']}")
        """
        async with self.orderbook.orderbook_lock:
            try:
                if self.orderbook.recent_trades.is_empty():
                    return {
                        "support_levels": [],
                        "resistance_levels": [],
                        "strongest_support": None,
                        "strongest_resistance": None,
                    }

                # Get historical price data
                cutoff_time = datetime.now(self.orderbook.timezone) - timedelta(
                    minutes=lookback_minutes
                )

                # Combine trade prices with orderbook levels
                price_points = []

                # Add recent trade prices
                recent_trades = self.orderbook.recent_trades.filter(
                    pl.col("timestamp") >= cutoff_time
                )
                if not recent_trades.is_empty():
                    trade_prices = recent_trades["price"].to_list()
                    price_points.extend(trade_prices)

                # Add historical best bid/ask
                for bid_data in self.orderbook.best_bid_history[-100:]:
                    if bid_data["timestamp"] >= cutoff_time:
                        price_points.append(bid_data["price"])

                for ask_data in self.orderbook.best_ask_history[-100:]:
                    if ask_data["timestamp"] >= cutoff_time:
                        price_points.append(ask_data["price"])

                if not price_points:
                    return {
                        "support_levels": [],
                        "resistance_levels": [],
                        "strongest_support": None,
                        "strongest_resistance": None,
                    }

                # Find price levels with multiple touches
                current_price = price_points[-1] if price_points else 0
                support_levels: list[dict[str, Any]] = []
                resistance_levels: list[dict[str, Any]] = []

                # Group prices into levels
                price_levels: dict[float, list[float]] = {}
                for price in price_points:
                    # Find existing level within tolerance
                    found = False
                    for level in price_levels:
                        if abs(price - level) <= price_tolerance:
                            price_levels[level].append(price)
                            found = True
                            break

                    if not found:
                        price_levels[price] = [price]

                # Classify levels as support or resistance
                for _level, touches in price_levels.items():
                    if len(touches) >= min_touches:
                        avg_price = sum(touches) / len(touches)

                        level_data = {
                            "price": avg_price,
                            "touches": len(touches),
                            "strength": len(touches) / min_touches,
                            "last_touch": datetime.now(self.orderbook.timezone),
                        }

                        if avg_price < current_price:
                            support_levels.append(level_data)
                        else:
                            resistance_levels.append(level_data)

                # Sort by strength
                support_levels.sort(key=lambda x: x.get("strength", 0), reverse=True)
                resistance_levels.sort(key=lambda x: x.get("strength", 0), reverse=True)

                # Update orderbook tracking
                self.orderbook.support_levels = support_levels[:10]
                self.orderbook.resistance_levels = resistance_levels[:10]

                return {
                    "support_levels": support_levels,
                    "resistance_levels": resistance_levels,
                    "strongest_support": support_levels[0] if support_levels else None,
                    "strongest_resistance": resistance_levels[0]
                    if resistance_levels
                    else None,
                    "current_price": current_price,
                }

            except Exception as e:
                self.logger.error(f"Error identifying support/resistance: {e}")
                return {"error": str(e)}

    async def get_spread_analysis(
        self, window_minutes: int = 30
    ) -> LiquidityAnalysisResponse:
        """
        Analyze bid-ask spread patterns over time.

        Args:
            window_minutes: Time window for analysis

        Returns:
            Dict containing spread statistics and patterns
        """
        async with self.orderbook.orderbook_lock:
            try:
                if not self.orderbook.spread_history:
                    current_time = datetime.now(self.orderbook.timezone)
                    return {
                        "bid_liquidity": 0.0,
                        "ask_liquidity": 0.0,
                        "total_liquidity": 0.0,
                        "avg_spread": 0.0,
                        "spread_volatility": 0.0,
                        "liquidity_score": 0.0,
                        "market_depth_score": 0.0,
                        "resilience_score": 0.0,
                        "tightness_score": 0.0,
                        "immediacy_score": 0.0,
                        "depth_imbalance": 0.0,
                        "effective_spread": 0.0,
                        "realized_spread": 0.0,
                        "price_impact": 0.0,
                        "timestamp": current_time.isoformat(),
                    }

                # Filter spreads within window
                cutoff_time = datetime.now(self.orderbook.timezone) - timedelta(
                    minutes=window_minutes
                )

                recent_spreads = [
                    s
                    for s in self.orderbook.spread_history
                    if s["timestamp"] >= cutoff_time
                ]

                if not recent_spreads:
                    recent_spreads = self.orderbook.spread_history[-100:]

                if not recent_spreads:
                    current_time = datetime.now(self.orderbook.timezone)
                    return {
                        "bid_liquidity": 0.0,
                        "ask_liquidity": 0.0,
                        "total_liquidity": 0.0,
                        "avg_spread": 0.0,
                        "spread_volatility": 0.0,
                        "liquidity_score": 0.0,
                        "market_depth_score": 0.0,
                        "resilience_score": 0.0,
                        "tightness_score": 0.0,
                        "immediacy_score": 0.0,
                        "depth_imbalance": 0.0,
                        "effective_spread": 0.0,
                        "realized_spread": 0.0,
                        "price_impact": 0.0,
                        "timestamp": current_time.isoformat(),
                    }

                # Calculate statistics
                spread_values = [s["spread"] for s in recent_spreads]
                current_spread = spread_values[-1]
                avg_spread = sum(spread_values) / len(spread_values)
                _min_spread = min(spread_values)
                _max_spread = max(spread_values)

                # Calculate volatility
                variance = sum((s - avg_spread) ** 2 for s in spread_values) / len(
                    spread_values
                )
                spread_volatility = variance**0.5

                # Determine trend
                if len(spread_values) >= 10:
                    first_half_avg = sum(spread_values[: len(spread_values) // 2]) / (
                        len(spread_values) // 2
                    )
                    second_half_avg = sum(spread_values[len(spread_values) // 2 :]) / (
                        len(spread_values) - len(spread_values) // 2
                    )

                    if second_half_avg > first_half_avg * 1.1:
                        _spread_trend = "widening"
                    elif second_half_avg < first_half_avg * 0.9:
                        _spread_trend = "tightening"
                    else:
                        _spread_trend = "stable"
                else:
                    _spread_trend = "insufficient_data"

                # Calculate spread distribution
                _spread_distribution = {
                    "tight": len([s for s in spread_values if s <= avg_spread * 0.8]),
                    "normal": len(
                        [
                            s
                            for s in spread_values
                            if avg_spread * 0.8 < s <= avg_spread * 1.2
                        ]
                    ),
                    "wide": len([s for s in spread_values if s > avg_spread * 1.2]),
                }

                # Map to LiquidityAnalysisResponse structure
                current_time = datetime.now(self.orderbook.timezone)

                # Get current orderbook state for liquidity metrics
                _best_prices = self.orderbook._get_best_bid_ask_unlocked()
                bid_liquidity = 0.0
                ask_liquidity = 0.0
                total_liquidity = 0.0
                depth_imbalance = 0.0

                if (
                    not self.orderbook.orderbook_bids.is_empty()
                    and not self.orderbook.orderbook_asks.is_empty()
                ):
                    bid_volume = int(self.orderbook.orderbook_bids["volume"].sum())
                    ask_volume = int(self.orderbook.orderbook_asks["volume"].sum())
                    bid_liquidity = float(bid_volume)
                    ask_liquidity = float(ask_volume)
                    total_liquidity = float(bid_volume + ask_volume)
                    depth_imbalance = (
                        (bid_volume - ask_volume) / (bid_volume + ask_volume)
                        if (bid_volume + ask_volume) > 0
                        else 0.0
                    )

                # Calculate scores based on spread analysis
                liquidity_score = max(
                    0.0, 10.0 - (avg_spread * 100)
                )  # Lower spreads = higher liquidity
                tightness_score = max(
                    0.0, 10.0 - (current_spread * 100)
                )  # Current spread tightness
                market_depth_score = min(
                    10.0, total_liquidity / 1000
                )  # Volume-based depth
                resilience_score = max(
                    0.0, 10.0 - spread_volatility * 1000
                )  # Lower volatility = higher resilience
                immediacy_score = tightness_score  # Approximation

                # Price impact estimates
                effective_spread = current_spread
                realized_spread = current_spread * 0.5  # Approximation
                price_impact = abs(depth_imbalance) * current_spread

                return {
                    "bid_liquidity": bid_liquidity,
                    "ask_liquidity": ask_liquidity,
                    "total_liquidity": total_liquidity,
                    "avg_spread": avg_spread,
                    "spread_volatility": spread_volatility,
                    "liquidity_score": liquidity_score,
                    "market_depth_score": market_depth_score,
                    "resilience_score": resilience_score,
                    "tightness_score": tightness_score,
                    "immediacy_score": immediacy_score,
                    "depth_imbalance": depth_imbalance,
                    "effective_spread": effective_spread,
                    "realized_spread": realized_spread,
                    "price_impact": price_impact,
                    "timestamp": current_time.isoformat(),
                }

            except Exception as e:
                self.logger.error(f"Error analyzing spread: {e}")
                current_time = datetime.now(self.orderbook.timezone)
                return {
                    "bid_liquidity": 0.0,
                    "ask_liquidity": 0.0,
                    "total_liquidity": 0.0,
                    "avg_spread": 0.0,
                    "spread_volatility": 0.0,
                    "liquidity_score": 0.0,
                    "market_depth_score": 0.0,
                    "resilience_score": 0.0,
                    "tightness_score": 0.0,
                    "immediacy_score": 0.0,
                    "depth_imbalance": 0.0,
                    "effective_spread": 0.0,
                    "realized_spread": 0.0,
                    "price_impact": 0.0,
                    "timestamp": current_time.isoformat(),
                }

    @staticmethod
    def calculate_dataframe_volume_profile(
        data: pl.DataFrame,
        price_column: str = "close",
        volume_column: str = "volume",
        num_bins: int = 50,
    ) -> dict[str, Any]:
        """
        Calculate volume profile from a DataFrame with price and volume data.

        This static method provides volume profile analysis for any DataFrame,
        useful for historical analysis or when working with data outside of
        the orderbook context. It creates a histogram of volume distribution
        across price levels and identifies key areas of market interest.

        Args:
            data: DataFrame with price and volume data
            price_column: Name of the price column (default: "close")
            volume_column: Name of the volume column (default: "volume")
            num_bins: Number of price bins for the histogram (default: 50)

        Returns:
            Dict containing volume profile analysis:
                - point_of_control: Price level with highest volume
                - poc_volume: Volume at the point of control
                - value_area_high: Upper bound of 70% volume area
                - value_area_low: Lower bound of 70% volume area
                - total_volume: Total volume analyzed
                - volume_distribution: Top 10 high-volume price levels

        Example:
            >>> # Analyze volume distribution in historical data
            >>> profile = VolumeProfile.calculate_dataframe_volume_profile(ohlcv_data)
            >>> print(f"POC Price: ${profile['point_of_control']:.2f}")
            >>> print(
            ...     f"Value Area: ${profile['value_area_low']:.2f} - ${profile['value_area_high']:.2f}"
            ... )
        """
        required_cols = [price_column, volume_column]
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Column '{col}' not found in data")

        if data.is_empty():
            return {"error": "No data provided"}

        try:
            # Get price range
            min_price = data.select(pl.col(price_column).min()).item()
            max_price = data.select(pl.col(price_column).max()).item()

            if min_price is None or max_price is None:
                return {"error": "Invalid price data"}

            price_range = max_price - min_price
            if price_range == 0:
                # All prices are the same
                total_vol = data.select(pl.col(volume_column).sum()).item() or 0
                return {
                    "point_of_control": min_price,
                    "poc_volume": total_vol,
                    "value_area_high": min_price,
                    "value_area_low": min_price,
                    "total_volume": total_vol,
                    "volume_distribution": [{"price": min_price, "volume": total_vol}],
                }

            # Create price bins
            bin_size = price_range / num_bins
            bins = [min_price + i * bin_size for i in range(num_bins + 1)]

            # Calculate volume per price level
            volume_by_price = []
            for i in range(len(bins) - 1):
                bin_data = data.filter(
                    (pl.col(price_column) >= bins[i])
                    & (pl.col(price_column) < bins[i + 1])
                )

                if not bin_data.is_empty():
                    total_volume = (
                        bin_data.select(pl.col(volume_column).sum()).item() or 0
                    )
                    avg_price = (bins[i] + bins[i + 1]) / 2
                    volume_by_price.append(
                        {
                            "price": avg_price,
                            "volume": total_volume,
                            "price_range": (bins[i], bins[i + 1]),
                        }
                    )

            if not volume_by_price:
                return {"error": "No volume data in bins"}

            # Sort by volume to find key levels
            volume_by_price.sort(key=lambda x: x["volume"], reverse=True)

            # Point of Control (POC) - price level with highest volume
            poc = volume_by_price[0]

            # Value Area (70% of volume)
            total_volume = sum(vp["volume"] for vp in volume_by_price)
            value_area_volume = total_volume * 0.7
            cumulative_volume = 0
            value_area_prices = []

            for vp in volume_by_price:
                cumulative_volume += vp["volume"]
                value_area_prices.append(vp["price"])
                if cumulative_volume >= value_area_volume:
                    break

            return {
                "point_of_control": poc["price"],
                "poc_volume": poc["volume"],
                "value_area_high": max(value_area_prices),
                "value_area_low": min(value_area_prices),
                "total_volume": total_volume,
                "volume_distribution": volume_by_price[:10],  # Top 10 volume levels
            }

        except Exception as e:
            return {"error": str(e)}
