"""
Advanced detection algorithms for the async orderbook.

This module implements sophisticated algorithms for detecting hidden market microstructure
patterns that provide deeper insights into market participant behavior. It specializes in
identifying patterns that may indicate institutional activity, hidden liquidity, and
market manipulation attempts.

Key detection capabilities:
- Iceberg order detection: Identifies large hidden orders that only show a small portion
  of their total size at any given time
- Order clustering analysis: Detects clusters of orders at similar price levels that may
  indicate coordinated market participant activity
- Market microstructure metrics: Calculates advanced metrics that reveal hidden aspects
  of market behavior
- Confidence scoring: Assigns confidence levels to detections to distinguish between
  high and low probability signals

The detection algorithms use historical price level data, order refresh patterns, and
trade execution analysis to infer the presence of hidden orders and market structures
that are not directly visible in the raw orderbook data.

All detection methods are optimized for real-time performance while maintaining
accuracy, with configurable sensitivity parameters to adjust for different market
conditions and instrument characteristics.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import polars as pl

from project_x_py.orderbook.base import OrderBookBase
from project_x_py.orderbook.types import IcebergConfig


class OrderDetection:
    """
    Provides advanced order detection algorithms.

    This class implements sophisticated algorithms for detecting hidden patterns in
    orderbook data that may indicate specific trading behaviors, hidden liquidity,
    or other market microstructure phenomena. It is designed as a specialized component
    of the OrderBook that focuses solely on detection capabilities.

    Key features:
    1. Iceberg order detection - Identifies large orders that are deliberately split
       into smaller pieces to hide their true size
    2. Order clustering analysis - Detects groups of orders at similar price levels
       that may represent coordinated activity or key liquidity zones
    3. Advanced market metrics - Calculates metrics like book pressure and
       price concentration to reveal hidden market dynamics

    Each detection algorithm follows these principles:
    - Configurable sensitivity with reasonable defaults
    - Explicit confidence scoring to indicate detection reliability
    - Comprehensive metadata to explain the reasoning behind detections
    - Thread-safe implementation through orderbook lock usage
    - Proper error handling with graceful degradation

    The detection methods leverage the historical data accumulated by the orderbook
    to identify patterns over time rather than just analyzing the current state,
    allowing for more sophisticated and reliable detections.
    """

    def __init__(self, orderbook: OrderBookBase):
        self.orderbook = orderbook
        self.logger = logging.getLogger(__name__)
        self.iceberg_config = IcebergConfig()

    async def detect_iceberg_orders(
        self,
        min_refreshes: int | None = None,
        volume_threshold: int | None = None,
        time_window_minutes: int | None = None,
    ) -> dict[str, Any]:
        """
        Detect potential iceberg orders based on price level refresh patterns.

        Iceberg orders are detected by looking for price levels that:
        1. Refresh frequently with new volume
        2. Maintain consistent volume levels
        3. Show patterns of immediate replenishment after trades

        Args:
            min_refreshes: Minimum refreshes to consider iceberg (default: 5)
            volume_threshold: Minimum volume to consider (default: 50)
            time_window_minutes: Time window to analyze (default: 10)

        Returns:
            List of detected iceberg orders with analysis
        """
        min_refreshes = min_refreshes or self.iceberg_config.min_refreshes
        volume_threshold = volume_threshold or self.iceberg_config.volume_threshold
        time_window_minutes = (
            time_window_minutes or self.iceberg_config.time_window_minutes
        )

        async with self.orderbook.orderbook_lock:
            try:
                current_time = datetime.now(self.orderbook.timezone)
                cutoff_time = current_time - timedelta(minutes=time_window_minutes)

                detected_icebergs = []

                # Analyze price level history
                for (
                    price,
                    side,
                ), history in self.orderbook.price_level_history.items():
                    # Filter recent history
                    recent_history = [
                        h
                        for h in history
                        if h.get("timestamp", current_time) > cutoff_time
                    ]

                    if len(recent_history) < min_refreshes:
                        continue

                    # Analyze refresh patterns
                    volumes = [h["volume"] for h in recent_history]
                    avg_volume = sum(volumes) / len(volumes)

                    if avg_volume < volume_threshold:
                        continue

                    # Check for consistent replenishment
                    replenishments = self._analyze_volume_replenishment(recent_history)

                    if replenishments >= min_refreshes - 1:
                        # Calculate confidence score
                        confidence = self._calculate_iceberg_confidence(
                            recent_history, replenishments
                        )

                        if confidence >= self.iceberg_config.confidence_threshold:
                            detected_icebergs.append(
                                {
                                    "price": price,
                                    "side": side,
                                    "avg_volume": avg_volume,
                                    "refresh_count": len(recent_history),
                                    "replenishment_count": replenishments,
                                    "confidence": confidence,
                                    "estimated_hidden_size": self._estimate_iceberg_hidden_size(
                                        recent_history, avg_volume
                                    ),
                                    "last_update": recent_history[-1]["timestamp"],
                                }
                            )

                # Sort by confidence
                detected_icebergs.sort(key=lambda x: x["confidence"], reverse=True)

                # Update statistics
                self.orderbook.trade_flow_stats["iceberg_detected_count"] = len(
                    detected_icebergs
                )

                # Return as dictionary with metadata
                return {
                    "iceberg_levels": detected_icebergs,
                    "analysis_window_minutes": time_window_minutes,
                    "detection_parameters": {
                        "min_refreshes": min_refreshes,
                        "volume_threshold": volume_threshold,
                        "confidence_threshold": self.iceberg_config.confidence_threshold,
                    },
                    "timestamp": current_time,
                }

            except Exception as e:
                self.logger.error(f"Error detecting iceberg orders: {e}")
                return {
                    "iceberg_levels": [],
                    "analysis_window_minutes": time_window_minutes,
                    "detection_parameters": {
                        "min_refreshes": min_refreshes,
                        "volume_threshold": volume_threshold,
                        "confidence_threshold": self.iceberg_config.confidence_threshold,
                    },
                    "timestamp": datetime.now(self.orderbook.timezone),
                    "error": str(e),
                }

    def _analyze_volume_replenishment(self, history: list[dict[str, Any]]) -> int:
        """Count volume replenishment events in price level history."""
        if len(history) < 2:
            return 0

        replenishments = 0
        for i in range(1, len(history)):
            prev_volume = history[i - 1]["volume"]
            curr_volume = history[i]["volume"]

            # Check if volume increased after decrease
            if prev_volume < curr_volume:
                replenishments += 1

        return replenishments

    def _calculate_iceberg_confidence(
        self, history: list[dict[str, Any]], replenishments: int
    ) -> float:
        """Calculate confidence score for iceberg detection."""
        if not history:
            return 0.0

        # Base confidence from refresh frequency
        refresh_score = min(len(history) / 10, 1.0) * 0.4

        # Replenishment pattern score
        replenishment_score = min(replenishments / 5, 1.0) * 0.4

        # Volume consistency score
        volumes = [h["volume"] for h in history]
        avg_volume = sum(volumes) / len(volumes)
        volume_std = (sum((v - avg_volume) ** 2 for v in volumes) / len(volumes)) ** 0.5
        consistency_score = (
            max(0, 1 - (volume_std / avg_volume)) * 0.2 if avg_volume > 0 else 0
        )

        return refresh_score + replenishment_score + consistency_score

    def _estimate_iceberg_hidden_size(
        self, history: list[dict[str, Any]], avg_volume: float
    ) -> float:
        """Estimate the hidden size of an iceberg order."""
        # Simple estimation based on refresh frequency and volume
        refresh_rate = len(history) / 10  # Assume 10 minute window
        estimated_total = avg_volume * refresh_rate * 10  # Project over time
        return max(0, estimated_total - avg_volume)

    async def detect_order_clusters(
        self, min_cluster_size: int = 3, price_tolerance: float = 0.1
    ) -> list[dict[str, Any]]:
        """
        Detect clusters of orders at similar price levels.

        Args:
            min_cluster_size: Minimum orders to form a cluster
            price_tolerance: Price range to consider as cluster

        Returns:
            List of detected order clusters
        """
        async with self.orderbook.orderbook_lock:
            try:
                clusters = []

                # Analyze bid clusters
                if not self.orderbook.orderbook_bids.is_empty():
                    bid_clusters = await self._find_clusters(
                        self.orderbook.orderbook_bids,
                        "bid",
                        min_cluster_size,
                        price_tolerance,
                    )
                    clusters.extend(bid_clusters)

                # Analyze ask clusters
                if not self.orderbook.orderbook_asks.is_empty():
                    ask_clusters = await self._find_clusters(
                        self.orderbook.orderbook_asks,
                        "ask",
                        min_cluster_size,
                        price_tolerance,
                    )
                    clusters.extend(ask_clusters)

                return clusters

            except Exception as e:
                self.logger.error(f"Error detecting order clusters: {e}")
                return []

    async def _find_clusters(
        self,
        orderbook_df: pl.DataFrame,
        side: str,
        min_cluster_size: int,
        price_tolerance: float,
    ) -> list[dict[str, Any]]:
        """Find order clusters in orderbook data."""
        if orderbook_df.is_empty():
            return []

        # Sort by price
        sorted_df = orderbook_df.sort("price", descending=(side == "bid"))
        prices = sorted_df["price"].to_list()
        volumes = sorted_df["volume"].to_list()

        clusters = []
        i = 0

        while i < len(prices):
            # Start a new cluster
            cluster_prices = [prices[i]]
            cluster_volumes = [volumes[i]]
            j = i + 1

            # Find all prices within tolerance
            while j < len(prices) and abs(prices[j] - prices[i]) <= price_tolerance:
                cluster_prices.append(prices[j])
                cluster_volumes.append(volumes[j])
                j += 1

            # Check if cluster is large enough
            if len(cluster_prices) >= min_cluster_size:
                clusters.append(
                    {
                        "side": side,
                        "center_price": sum(cluster_prices) / len(cluster_prices),
                        "price_range": (min(cluster_prices), max(cluster_prices)),
                        "total_volume": sum(cluster_volumes),
                        "order_count": len(cluster_prices),
                        "avg_order_size": sum(cluster_volumes) / len(cluster_volumes),
                        "prices": cluster_prices,
                        "volumes": cluster_volumes,
                    }
                )

            i = j

        return clusters

    async def get_advanced_market_metrics(self) -> dict[str, Any]:
        """
        Calculate advanced market microstructure metrics.

        Returns:
            Dict containing various market metrics
        """
        async with self.orderbook.orderbook_lock:
            try:
                metrics = {}

                # Order book shape metrics
                if (
                    not self.orderbook.orderbook_bids.is_empty()
                    and not self.orderbook.orderbook_asks.is_empty()
                ):
                    # Calculate book pressure
                    top_5_bids = self.orderbook.orderbook_bids.sort(
                        "price", descending=True
                    ).head(5)
                    top_5_asks = self.orderbook.orderbook_asks.sort("price").head(5)

                    bid_pressure = (
                        top_5_bids["volume"].sum() if not top_5_bids.is_empty() else 0
                    )
                    ask_pressure = (
                        top_5_asks["volume"].sum() if not top_5_asks.is_empty() else 0
                    )

                    metrics["book_pressure"] = {
                        "bid_pressure": float(bid_pressure),
                        "ask_pressure": float(ask_pressure),
                        "pressure_ratio": float(bid_pressure / ask_pressure)
                        if ask_pressure > 0
                        else float("inf"),
                    }

                # Trade intensity metrics
                if not self.orderbook.recent_trades.is_empty():
                    recent_window = datetime.now(self.orderbook.timezone) - timedelta(
                        minutes=5
                    )
                    recent_trades = self.orderbook.recent_trades.filter(
                        pl.col("timestamp") >= recent_window
                    )

                    if not recent_trades.is_empty():
                        metrics["trade_intensity"] = {
                            "trades_per_minute": recent_trades.height / 5,
                            "volume_per_minute": float(
                                recent_trades["volume"].sum() / 5
                            ),
                            "avg_trade_size": float(
                                str(recent_trades["volume"].mean())
                            ),
                        }

                # Price level concentration
                metrics["price_concentration"] = {
                    "bid_levels": self.orderbook.orderbook_bids.height,
                    "ask_levels": self.orderbook.orderbook_asks.height,
                    "total_levels": self.orderbook.orderbook_bids.height
                    + self.orderbook.orderbook_asks.height,
                }

                # Iceberg detection summary
                iceberg_result = await self.detect_iceberg_orders()
                iceberg_levels = iceberg_result.get("iceberg_levels", [])
                metrics["iceberg_summary"] = {
                    "detected_count": len(iceberg_levels),
                    "bid_icebergs": len(
                        [i for i in iceberg_levels if i.get("side") == "bid"]
                    ),
                    "ask_icebergs": len(
                        [i for i in iceberg_levels if i.get("side") == "ask"]
                    ),
                    "total_hidden_volume": sum(
                        i.get("estimated_hidden_size", 0) for i in iceberg_levels
                    ),
                }

                return metrics

            except Exception as e:
                self.logger.error(f"Error calculating advanced metrics: {e}")
                return {"error": str(e)}
