"""
Market analytics for the async orderbook.

This module provides advanced market analytics for the async orderbook implementation,
focusing on quantitative analysis of market structure, liquidity, and order flow.
It extracts actionable insights from the raw orderbook data through a variety of
analytical methods.

Key capabilities:
- Market imbalance analysis: Detects and quantifies buy/sell pressure
- Orderbook depth analysis: Evaluates liquidity distribution across price ranges
- Cumulative delta calculations: Tracks aggressive buying vs. selling over time
- Trade flow analytics: Analyzes market maker vs. taker behavior patterns
- Liquidity level identification: Locates significant support/resistance zones
- Comprehensive statistical analysis: Provides full orderbook metrics

The analytics are designed to support trading strategy development, market
microstructure analysis, and real-time trading decision support by extracting
higher-level insights from the raw order book data.
"""

from datetime import datetime, timedelta
from typing import Any

import polars as pl

from project_x_py.utils import (
    LogMessages,
    ProjectXLogger,
    handle_errors,
)

from .base import OrderBookBase


class MarketAnalytics:
    """
    Provides market analytics for the orderbook.

    This class implements advanced analytics methods for the OrderBook, focusing on
    extracting actionable market insights from the raw orderbook data. It is designed as
    a component that is injected into the main OrderBook to provide specialized
    analytical capabilities while maintaining a clean separation of concerns.

    The analytics methods focus on several key areas:
    1. Market imbalance analysis - Detecting buy/sell pressure
    2. Liquidity distribution analysis - Understanding depth across price levels
    3. Trade flow analysis - Classifying aggressive vs. passive executions
    4. Cumulative delta tracking - Measuring net buying/selling pressure over time
    5. Significant liquidity levels - Identifying potential support/resistance

    Each method follows a consistent pattern:
    - Thread-safe execution through the orderbook lock
    - Comprehensive error handling and logging
    - Return of structured analysis results with multiple metrics
    - Optional time filtering when appropriate

    These analytics are designed to be used by trading strategies, market analysis tools,
    and visualization components that need deeper insights beyond raw orderbook data.
    """

    def __init__(self, orderbook: OrderBookBase):
        self.orderbook = orderbook
        self.logger = ProjectXLogger.get_logger(__name__)

    @handle_errors(
        "get market imbalance",
        reraise=False,
        default_return={
            "imbalance_ratio": 0.0,
            "bid_volume": 0,
            "ask_volume": 0,
            "analysis": "Error occurred",
        },
    )
    async def get_market_imbalance(self, levels: int = 10) -> dict[str, Any]:
        """
        Calculate order flow imbalance between bid and ask sides.

        This method quantifies the imbalance between buying and selling pressure in the
        orderbook by comparing the total volume on the bid side versus the ask side.
        A positive imbalance ratio indicates stronger buying pressure, while a negative
        ratio indicates stronger selling pressure.

        The analysis includes:
        - Imbalance ratio: (bid_volume - ask_volume) / total_volume
        - Raw bid and ask volumes
        - Number of populated price levels on each side
        - Text analysis of market conditions based on the imbalance ratio
        - Timestamp of the analysis

        The method is thread-safe and acquires the orderbook lock during execution.

        Args:
            levels: Number of price levels to analyze on each side of the book (default: 10).
                Higher values analyze deeper into the orderbook but may include less
                relevant levels.

        Returns:
            Dict containing:
                imbalance_ratio: Float between -1.0 and 1.0 where:
                    - Positive values indicate buying pressure
                    - Negative values indicate selling pressure
                    - Values near 0 indicate a balanced orderbook
                bid_volume: Total volume on the bid side
                ask_volume: Total volume on the ask side
                bid_levels: Number of populated bid price levels analyzed
                ask_levels: Number of populated ask price levels analyzed
                analysis: Text description of market conditions
                timestamp: Time of analysis

        Example:
            >>> imbalance = await orderbook.get_market_imbalance(levels=5)
            >>> print(f"Imbalance ratio: {imbalance['imbalance_ratio']:.2f}")
            >>> print(f"Analysis: {imbalance['analysis']}")
            >>> print(
            ...     f"Bid volume: {imbalance['bid_volume']}, "
            ...     f"Ask volume: {imbalance['ask_volume']}"
            ... )
        """
        async with self.orderbook.orderbook_lock:
            try:
                # Get orderbook levels
                bids = self.orderbook._get_orderbook_bids_unlocked(levels)
                asks = self.orderbook._get_orderbook_asks_unlocked(levels)

                if bids.is_empty() or asks.is_empty():
                    return {
                        "imbalance_ratio": 0.0,
                        "bid_volume": 0,
                        "ask_volume": 0,
                        "analysis": "Insufficient data",
                    }

                # Calculate volumes
                bid_volume = int(bids["volume"].sum())
                ask_volume = int(asks["volume"].sum())
                total_volume = bid_volume + ask_volume

                if total_volume == 0:
                    return {
                        "imbalance_ratio": 0.0,
                        "bid_volume": 0,
                        "ask_volume": 0,
                        "analysis": "No volume",
                    }

                # Calculate imbalance ratio
                imbalance_ratio = (bid_volume - ask_volume) / total_volume

                # Analyze imbalance
                if imbalance_ratio > 0.3:
                    analysis = "Strong buying pressure"
                elif imbalance_ratio > 0.1:
                    analysis = "Moderate buying pressure"
                elif imbalance_ratio < -0.3:
                    analysis = "Strong selling pressure"
                elif imbalance_ratio < -0.1:
                    analysis = "Moderate selling pressure"
                else:
                    analysis = "Balanced orderbook"

                return {
                    "imbalance_ratio": imbalance_ratio,
                    "bid_volume": bid_volume,
                    "ask_volume": ask_volume,
                    "bid_levels": bids.height,
                    "ask_levels": asks.height,
                    "analysis": analysis,
                    "timestamp": datetime.now(self.orderbook.timezone),
                }

            except Exception as e:
                self.logger.error(
                    LogMessages.DATA_ERROR,
                    extra={"operation": "market_imbalance", "error": str(e)},
                )
                return {"error": str(e)}

    @handle_errors(
        "get orderbook depth",
        reraise=False,
        default_return={"error": "Analysis failed"},
    )
    async def get_orderbook_depth(self, price_range: float) -> dict[str, Any]:
        """
        Analyze orderbook depth within a price range.

        Args:
            price_range: Price range from best bid/ask to analyze

        Returns:
            Dict containing depth analysis
        """
        async with self.orderbook.orderbook_lock:
            try:
                best_prices = self.orderbook._get_best_bid_ask_unlocked()
                best_bid = best_prices.get("bid")
                best_ask = best_prices.get("ask")

                if best_bid is None or best_ask is None:
                    return {"error": "No best bid/ask available"}

                # Filter bids within range
                bid_depth = self.orderbook.orderbook_bids.filter(
                    (pl.col("price") >= best_bid - price_range) & (pl.col("volume") > 0)
                )

                # Filter asks within range
                ask_depth = self.orderbook.orderbook_asks.filter(
                    (pl.col("price") <= best_ask + price_range) & (pl.col("volume") > 0)
                )

                return {
                    "price_range": price_range,
                    "bid_depth": {
                        "levels": bid_depth.height,
                        "total_volume": int(bid_depth["volume"].sum())
                        if not bid_depth.is_empty()
                        else 0,
                        "avg_volume": (
                            float(str(bid_depth["volume"].mean()))
                            if not bid_depth.is_empty()
                            else 0.0
                        ),
                    },
                    "ask_depth": {
                        "levels": ask_depth.height,
                        "total_volume": int(ask_depth["volume"].sum())
                        if not ask_depth.is_empty()
                        else 0,
                        "avg_volume": (
                            float(str(ask_depth["volume"].mean()))
                            if not ask_depth.is_empty()
                            else 0.0
                        ),
                    },
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                }

            except Exception as e:
                self.logger.error(
                    LogMessages.DATA_ERROR,
                    extra={"operation": "orderbook_depth", "error": str(e)},
                )
                return {"error": str(e)}

    @handle_errors(
        "get cumulative delta",
        reraise=False,
        default_return={
            "cumulative_delta": 0,
            "buy_volume": 0,
            "sell_volume": 0,
            "error": "Analysis failed",
        },
    )
    async def get_cumulative_delta(
        self, time_window_minutes: int = 60
    ) -> dict[str, Any]:
        """
        Get cumulative delta (buy volume - sell volume) over time window.

        Args:
            time_window_minutes: Time window to analyze

        Returns:
            Dict containing cumulative delta analysis
        """
        async with self.orderbook.orderbook_lock:
            try:
                if self.orderbook.recent_trades.is_empty():
                    return {
                        "cumulative_delta": 0,
                        "buy_volume": 0,
                        "sell_volume": 0,
                        "neutral_volume": 0,
                        "period_minutes": time_window_minutes,
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
                        "cumulative_delta": 0,
                        "buy_volume": 0,
                        "sell_volume": 0,
                        "neutral_volume": 0,
                        "period_minutes": time_window_minutes,
                    }

                # Calculate volumes by side
                buy_trades = recent_trades.filter(pl.col("side") == "buy")
                sell_trades = recent_trades.filter(pl.col("side") == "sell")
                neutral_trades = recent_trades.filter(pl.col("side") == "neutral")

                buy_volume = (
                    int(buy_trades["volume"].sum()) if not buy_trades.is_empty() else 0
                )
                sell_volume = (
                    int(sell_trades["volume"].sum())
                    if not sell_trades.is_empty()
                    else 0
                )
                neutral_volume = (
                    int(neutral_trades["volume"].sum())
                    if not neutral_trades.is_empty()
                    else 0
                )

                cumulative_delta = buy_volume - sell_volume

                return {
                    "cumulative_delta": cumulative_delta,
                    "buy_volume": buy_volume,
                    "sell_volume": sell_volume,
                    "neutral_volume": neutral_volume,
                    "total_volume": buy_volume + sell_volume + neutral_volume,
                    "period_minutes": time_window_minutes,
                    "trade_count": recent_trades.height,
                    "delta_per_trade": cumulative_delta / recent_trades.height
                    if recent_trades.height > 0
                    else 0,
                }

            except Exception as e:
                self.logger.error(
                    LogMessages.DATA_ERROR,
                    extra={"operation": "cumulative_delta", "error": str(e)},
                )
                return {"error": str(e)}

    async def get_trade_flow_summary(self) -> dict[str, Any]:
        """Get comprehensive trade flow statistics."""
        async with self.orderbook.orderbook_lock:
            try:
                # Calculate VWAP
                vwap = None
                if self.orderbook.vwap_denominator > 0:
                    vwap = (
                        self.orderbook.vwap_numerator / self.orderbook.vwap_denominator
                    )

                # Get recent trade statistics
                recent_trades_stats = {}
                if not self.orderbook.recent_trades.is_empty():
                    recent_trades_stats = {
                        "total_trades": self.orderbook.recent_trades.height,
                        "avg_trade_size": float(
                            str(self.orderbook.recent_trades["volume"].mean())
                        ),
                        "max_trade_size": int(
                            str(self.orderbook.recent_trades["volume"].max())
                        ),
                        "min_trade_size": int(
                            str(self.orderbook.recent_trades["volume"].min())
                        ),
                    }

                return {
                    "aggressive_buy_volume": self.orderbook.trade_flow_stats[
                        "aggressive_buy_volume"
                    ],
                    "aggressive_sell_volume": self.orderbook.trade_flow_stats[
                        "aggressive_sell_volume"
                    ],
                    "passive_buy_volume": self.orderbook.trade_flow_stats[
                        "passive_buy_volume"
                    ],
                    "passive_sell_volume": self.orderbook.trade_flow_stats[
                        "passive_sell_volume"
                    ],
                    "market_maker_trades": self.orderbook.trade_flow_stats[
                        "market_maker_trades"
                    ],
                    "cumulative_delta": self.orderbook.cumulative_delta,
                    "vwap": vwap,
                    "session_start": self.orderbook.session_start_time,
                    **recent_trades_stats,
                }

            except Exception as e:
                self.logger.error(
                    LogMessages.DATA_ERROR,
                    extra={"operation": "trade_flow_summary", "error": str(e)},
                )
                return {"error": str(e)}

    async def get_liquidity_levels(
        self, min_volume: int = 100, levels: int = 20
    ) -> dict[str, Any]:
        """
        Identify significant liquidity levels in the orderbook.

        Args:
            min_volume: Minimum volume to consider significant
            levels: Number of levels to check on each side

        Returns:
            Dict containing liquidity analysis
        """
        async with self.orderbook.orderbook_lock:
            try:
                # Get orderbook levels
                bids = self.orderbook._get_orderbook_bids_unlocked(levels)
                asks = self.orderbook._get_orderbook_asks_unlocked(levels)

                # Find significant bid levels
                significant_bids = []
                if not bids.is_empty():
                    sig_bids = bids.filter(pl.col("volume") >= min_volume)
                    if not sig_bids.is_empty():
                        significant_bids = sig_bids.to_dicts()

                # Find significant ask levels
                significant_asks = []
                if not asks.is_empty():
                    sig_asks = asks.filter(pl.col("volume") >= min_volume)
                    if not sig_asks.is_empty():
                        significant_asks = sig_asks.to_dicts()

                # Calculate liquidity concentration
                total_bid_liquidity = sum(b["volume"] for b in significant_bids)
                total_ask_liquidity = sum(a["volume"] for a in significant_asks)

                return {
                    "significant_bid_levels": significant_bids,
                    "significant_ask_levels": significant_asks,
                    "total_bid_liquidity": total_bid_liquidity,
                    "total_ask_liquidity": total_ask_liquidity,
                    "liquidity_imbalance": (
                        (total_bid_liquidity - total_ask_liquidity)
                        / (total_bid_liquidity + total_ask_liquidity)
                        if (total_bid_liquidity + total_ask_liquidity) > 0
                        else 0
                    ),
                    "min_volume_threshold": min_volume,
                }

            except Exception as e:
                self.logger.error(
                    LogMessages.DATA_ERROR,
                    extra={"operation": "liquidity_levels", "error": str(e)},
                )
                return {"error": str(e)}

    async def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive orderbook statistics."""
        async with self.orderbook.orderbook_lock:
            try:
                # Get best prices
                best_prices = self.orderbook._get_best_bid_ask_unlocked()

                # Calculate basic stats
                stats = {
                    "instrument": self.orderbook.instrument,
                    "update_count": self.orderbook.level2_update_count,
                    "last_update": self.orderbook.last_orderbook_update,
                    "best_bid": best_prices.get("bid"),
                    "best_ask": best_prices.get("ask"),
                    "spread": best_prices.get("spread"),
                    "bid_levels": self.orderbook.orderbook_bids.height,
                    "ask_levels": self.orderbook.orderbook_asks.height,
                    "total_trades": self.orderbook.recent_trades.height,
                    "order_type_breakdown": dict(self.orderbook.order_type_stats),
                }

                # Add spread statistics if available
                if self.orderbook.spread_history:
                    spreads = [
                        s["spread"] for s in self.orderbook.spread_history[-100:]
                    ]
                    stats["spread_stats"] = {
                        "current": best_prices.get("spread"),
                        "average": sum(spreads) / len(spreads),
                        "min": min(spreads),
                        "max": max(spreads),
                        "samples": len(spreads),
                    }

                return stats

            except Exception as e:
                self.logger.error(
                    LogMessages.DATA_ERROR,
                    extra={"operation": "get_statistics", "error": str(e)},
                )
                return {"error": str(e)}

    @staticmethod
    def analyze_dataframe_spread(
        data: pl.DataFrame,
        bid_column: str = "bid",
        ask_column: str = "ask",
        mid_column: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze bid-ask spread characteristics from a DataFrame.

        This is a static method that can analyze spread data from any DataFrame,
        useful for historical analysis or backtesting scenarios where you have
        bid/ask data but not a live orderbook.

        Args:
            data: DataFrame with bid/ask price columns
            bid_column: Name of the bid price column (default: "bid")
            ask_column: Name of the ask price column (default: "ask")
            mid_column: Name of the mid price column (optional, will calculate if not provided)

        Returns:
            Dict containing spread analysis:
                - avg_spread: Average absolute spread
                - median_spread: Median absolute spread
                - min_spread: Minimum spread observed
                - max_spread: Maximum spread observed
                - avg_relative_spread: Average spread as percentage of mid price
                - spread_volatility: Standard deviation of spread

        Example:
            >>> # Analyze historical bid/ask data
            >>> spread_stats = MarketAnalytics.analyze_dataframe_spread(historical_data)
            >>> print(f"Average spread: ${spread_stats['avg_spread']:.4f}")
            >>> print(f"Relative spread: {spread_stats['avg_relative_spread']:.4%}")
        """
        required_cols = [bid_column, ask_column]
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Column '{col}' not found in data")

        if data.is_empty():
            return {"error": "No data provided"}

        try:
            # Calculate mid price if not provided
            if mid_column is None:
                data = data.with_columns(
                    ((pl.col(bid_column) + pl.col(ask_column)) / 2).alias("mid_price")
                )
                mid_column = "mid_price"

            # Calculate spread metrics
            analysis_data = (
                data.with_columns(
                    [
                        (pl.col(ask_column) - pl.col(bid_column)).alias("spread"),
                        (
                            (pl.col(ask_column) - pl.col(bid_column))
                            / pl.col(mid_column)
                        ).alias("relative_spread"),
                    ]
                )
                .select(["spread", "relative_spread"])
                .drop_nulls()
            )

            if analysis_data.is_empty():
                return {"error": "No valid spread data"}

            return {
                "avg_spread": analysis_data.select(pl.col("spread").mean()).item()
                or 0.0,
                "median_spread": analysis_data.select(pl.col("spread").median()).item()
                or 0.0,
                "min_spread": analysis_data.select(pl.col("spread").min()).item()
                or 0.0,
                "max_spread": analysis_data.select(pl.col("spread").max()).item()
                or 0.0,
                "avg_relative_spread": analysis_data.select(
                    pl.col("relative_spread").mean()
                ).item()
                or 0.0,
                "spread_volatility": analysis_data.select(pl.col("spread").std()).item()
                or 0.0,
            }

        except Exception as e:
            return {"error": str(e)}
