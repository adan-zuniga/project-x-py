"""
Volume profile and support/resistance analysis for the async orderbook.

This module implements sophisticated volume profile analysis, support/resistance level
detection, and spread analytics for market structure analysis. It focuses on identifying
key price levels and zones where significant trading activity has occurred or where
the market may find support or resistance in the future.

Key capabilities:
- Volume profile analysis: Creates histogram-based analysis of volume distribution across
  price levels, identifying high-volume nodes and areas of interest
- Point of Control (POC) identification: Locates the price level with highest traded volume
- Value Area calculation: Determines the price range containing 70% of volume around the POC
- Support and resistance level detection: Identifies price levels that have acted as
  barriers to price movement based on historical price action
- Spread pattern analysis: Studies bid-ask spread behavior to identify market regime changes
  and liquidity conditions
- Market structure analysis: Integrates volume and price information to understand underlying
  market structure and participant behavior

These analyses are particularly valuable for trading strategy development, trade planning,
and execution timing, as they provide insights into where market participants have been
active and where price may react in the future.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import polars as pl

from project_x_py.orderbook.base import OrderBookBase


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

        Args:
            time_window_minutes: Time window to analyze
            price_bins: Number of price bins for histogram

        Returns:
            Dict containing volume profile analysis
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

        Args:
            lookback_minutes: Time window to analyze
            min_touches: Minimum price touches to qualify as S/R
            price_tolerance: Price range to consider as same level

        Returns:
            Dict containing support and resistance levels
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

    async def get_spread_analysis(self, window_minutes: int = 30) -> dict[str, Any]:
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
                    return {
                        "current_spread": None,
                        "avg_spread": None,
                        "min_spread": None,
                        "max_spread": None,
                        "spread_volatility": None,
                        "spread_trend": "insufficient_data",
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
                    return {
                        "current_spread": None,
                        "avg_spread": None,
                        "min_spread": None,
                        "max_spread": None,
                        "spread_volatility": None,
                        "spread_trend": "insufficient_data",
                    }

                # Calculate statistics
                spread_values = [s["spread"] for s in recent_spreads]
                current_spread = spread_values[-1]
                avg_spread = sum(spread_values) / len(spread_values)
                min_spread = min(spread_values)
                max_spread = max(spread_values)

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
                        spread_trend = "widening"
                    elif second_half_avg < first_half_avg * 0.9:
                        spread_trend = "tightening"
                    else:
                        spread_trend = "stable"
                else:
                    spread_trend = "insufficient_data"

                # Calculate spread distribution
                spread_distribution = {
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

                return {
                    "current_spread": current_spread,
                    "avg_spread": avg_spread,
                    "min_spread": min_spread,
                    "max_spread": max_spread,
                    "spread_volatility": spread_volatility,
                    "spread_trend": spread_trend,
                    "spread_distribution": spread_distribution,
                    "sample_count": len(spread_values),
                    "window_minutes": window_minutes,
                }

            except Exception as e:
                self.logger.error(f"Error analyzing spread: {e}")
                return {"error": str(e)}
