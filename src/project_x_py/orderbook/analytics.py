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

import logging
from datetime import datetime, timedelta
from typing import Any

import polars as pl

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
        self.logger = logging.getLogger(__name__)

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
                self.logger.error(f"Error calculating market imbalance: {e}")
                return {"error": str(e)}

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
                self.logger.error(f"Error analyzing orderbook depth: {e}")
                return {"error": str(e)}

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
                self.logger.error(f"Error calculating cumulative delta: {e}")
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
                self.logger.error(f"Error getting trade flow summary: {e}")
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
                self.logger.error(f"Error analyzing liquidity levels: {e}")
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
                self.logger.error(f"Error getting statistics: {e}")
                return {"error": str(e)}
