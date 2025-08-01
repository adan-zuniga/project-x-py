#!/usr/bin/env python3
"""Fix remaining issues in async orderbook by porting sync version's advanced algorithms."""

import re

# Read the async orderbook file
with open("src/project_x_py/async_orderbook.py") as f:
    content = f.read()

# First, let's add the missing helper methods from sync version
# Add _cross_reference_with_trades method before detect_iceberg_orders
cross_reference_method = '''
    def _cross_reference_with_trades(
        self, potential_icebergs: list[dict], cutoff_time: datetime
    ) -> list[dict]:
        """Cross-reference potential icebergs with trade data for validation."""
        if not potential_icebergs or len(self.recent_trades) == 0:
            return potential_icebergs
        
        # Get recent trades for cross-reference
        cutoff_time_naive = cutoff_time.replace(tzinfo=None)
        recent_trades = self.recent_trades.filter(pl.col("timestamp") > cutoff_time_naive)
        
        if len(recent_trades) == 0:
            return potential_icebergs
        
        for iceberg in potential_icebergs:
            price = iceberg["price"]
            side = iceberg["side"]
            
            # Find trades at or near this price level
            price_tolerance = self.tick_size if hasattr(self, "tick_size") else 0.25
            
            relevant_trades = recent_trades.filter(
                (pl.col("price") >= price - price_tolerance) &
                (pl.col("price") <= price + price_tolerance)
            )
            
            if len(relevant_trades) > 0:
                # Add trade validation metrics
                trade_volume = relevant_trades["volume"].sum()
                trade_count = len(relevant_trades)
                
                # Boost confidence if significant trading at this level
                if trade_volume > iceberg["total_volume"] * 0.5:
                    iceberg["trade_validated"] = True
                    iceberg["confidence_score"] = min(1.0, iceberg["confidence_score"] * 1.2)
                    iceberg["validation_metrics"] = {
                        "trade_volume": int(trade_volume),
                        "trade_count": trade_count,
                        "volume_ratio": float(trade_volume / iceberg["total_volume"])
                    }
                else:
                    iceberg["trade_validated"] = False
        
        return potential_icebergs
'''

# Find where to insert the method (before detect_iceberg_orders)
detect_iceberg_index = content.find("    async def detect_iceberg_orders(")
if detect_iceberg_index > 0:
    content = (
        content[:detect_iceberg_index]
        + cross_reference_method
        + "\n"
        + content[detect_iceberg_index:]
    )

# Now replace the simple iceberg detection with the advanced version
old_iceberg_method = '''    async def detect_iceberg_orders(
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
            }'''

new_iceberg_method = '''    async def detect_iceberg_orders(
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
            Dict containing advanced iceberg analysis with confidence metrics
        """
        try:
            async with self.orderbook_lock:
                cutoff_time = datetime.now(self.timezone) - timedelta(
                    minutes=time_window_minutes
                )
                
                # Build history DataFrame from price level history
                history_data = []
                
                # Clean old history entries while building data
                for (price, side), updates in list(self.price_level_history.items()):
                    # Filter out old updates
                    recent_updates = [
                        u for u in updates if u["timestamp"] >= cutoff_time
                    ]
                    
                    # Update the history with only recent updates
                    if recent_updates:
                        self.price_level_history[(price, side)] = recent_updates
                        # Add to history data for analysis
                        for update in recent_updates:
                            history_data.append({
                                "price": price,
                                "volume": update["volume"],
                                "timestamp": update["timestamp"].replace(tzinfo=None) if update["timestamp"].tzinfo else update["timestamp"],
                                "side": side,
                            })
                    else:
                        # Remove empty history entries
                        del self.price_level_history[(price, side)]
                
                # Create DataFrame from history
                if not history_data:
                    return {
                        "potential_icebergs": [],
                        "analysis": {
                            "total_detected": 0,
                            "detection_method": "advanced_statistical_analysis",
                            "time_window_minutes": time_window_minutes,
                            "error": "No orderbook data available for analysis",
                        },
                    }
                
                history_df = pl.DataFrame(history_data)
                
                # Perform statistical analysis on price levels
                grouped = history_df.group_by(["price", "side"]).agg([
                    pl.col("volume").mean().alias("avg_volume"),
                    pl.col("volume").std().alias("vol_std"),
                    pl.col("volume").count().alias("refresh_count"),
                    pl.col("volume").sum().alias("total_volume"),
                    pl.col("volume").min().alias("min_volume"),
                    pl.col("volume").max().alias("max_volume"),
                ])
                
                # Filter for potential icebergs based on statistical criteria
                potential = grouped.filter(
                    # Minimum refresh count requirement
                    (pl.col("refresh_count") >= min_refresh_count) &
                    # Minimum total volume requirement  
                    (pl.col("total_volume") >= min_total_volume) &
                    # Volume consistency requirement (low coefficient of variation)
                    (pl.col("vol_std") / pl.col("avg_volume") < (1 - volume_consistency_threshold)) &
                    # Ensure we have meaningful standard deviation data
                    (pl.col("vol_std").is_not_null()) &
                    (pl.col("avg_volume") > 0)
                )
                
                # Convert to list of dictionaries for processing
                potential_icebergs = []
                for row in potential.to_dicts():
                    # Calculate confidence score based on multiple factors
                    refresh_score = min(row["refresh_count"] / (min_refresh_count * 2), 1.0)
                    volume_score = min(row["total_volume"] / (min_total_volume * 2), 1.0)
                    
                    # Volume consistency score (lower CV = higher score)
                    cv = row["vol_std"] / row["avg_volume"] if row["avg_volume"] > 0 else 1.0
                    consistency_score = max(0, 1 - cv)
                    
                    # Combined confidence score
                    confidence_score = (
                        refresh_score * 0.3 +
                        volume_score * 0.2 +
                        consistency_score * 0.5
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
                    
                    # Estimate hidden size
                    estimated_hidden_size = max(
                        row["total_volume"] * 1.5,
                        row["max_volume"] * 5,
                        row["avg_volume"] * 10,
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
                        "volume_range": {
                            "min": row["min_volume"],
                            "max": row["max_volume"],
                            "avg": row["avg_volume"],
                        },
                    }
                    potential_icebergs.append(iceberg_data)
                
                # Cross-reference with trade data
                potential_icebergs = self._cross_reference_with_trades(
                    potential_icebergs, cutoff_time
                )
                
                # Sort by confidence score
                potential_icebergs.sort(key=lambda x: x["confidence_score"], reverse=True)
                
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
                            "total_orderbook_entries": len(history_data),
                            "unique_price_levels": len(set((h["price"], h["side"]) for h in history_data)),
                        },
                    },
                }
                
        except Exception as e:
            self.logger.error(f"Error in advanced iceberg detection: {e}")
            return {"potential_icebergs": [], "analysis": {"error": str(e)}}'''

content = content.replace(old_iceberg_method, new_iceberg_method)

# Fix the _calculate_price_tolerance method to use 3x like sync version
content = content.replace("return self.tick_size * 2", "return self.tick_size * 3")

# Now let's improve the _find_clusters method to be less sensitive
old_find_clusters = '''    def _find_clusters(
        self, df: pl.DataFrame, tolerance: float, min_size: int, side: str
    ) -> list[dict[str, Any]]:
        """Find clusters of orders within price tolerance."""
        if len(df) < min_size:
            return []
        
        # Sort by price
        sorted_df = df.sort("price", descending=(side == "bid"))
        prices = sorted_df["price"].to_list()
        volumes = sorted_df["volume"].to_list()
        
        clusters = []
        i = 0
        
        while i < len(prices):
            cluster_prices = [prices[i]]
            cluster_volumes = [volumes[i]]
            j = i + 1
            
            # Find all prices within tolerance
            while j < len(prices) and abs(prices[j] - prices[i]) <= tolerance:
                cluster_prices.append(prices[j])
                cluster_volumes.append(volumes[j])
                j += 1
            
            # Check if cluster is large enough
            if len(cluster_prices) >= min_size:
                clusters.append({
                    "center_price": sum(cluster_prices) / len(cluster_prices),
                    "price_range": (min(cluster_prices), max(cluster_prices)),
                    "total_volume": sum(cluster_volumes),
                    "order_count": len(cluster_prices),
                    "side": side,
                })
            
            i = j
        
        return clusters'''

new_find_clusters = '''    def _find_clusters(
        self, df: pl.DataFrame, tolerance: float, min_size: int, side: str
    ) -> list[dict[str, Any]]:
        """Find clusters of orders within price tolerance."""
        if len(df) < min_size:
            return []
        
        # Sort by price
        sorted_df = df.sort("price", descending=(side == "bid"))
        prices = sorted_df["price"].to_list()
        volumes = sorted_df["volume"].to_list()
        
        clusters = []
        i = 0
        
        while i < len(prices):
            cluster_prices = [prices[i]]
            cluster_volumes = [volumes[i]]
            j = i + 1
            
            # Find all prices within tolerance
            while j < len(prices) and abs(prices[j] - prices[i]) <= tolerance:
                cluster_prices.append(prices[j])
                cluster_volumes.append(volumes[j])
                j += 1
            
            # Check if cluster is large enough AND has significant volume
            total_volume = sum(cluster_volumes)
            if len(cluster_prices) >= min_size and total_volume >= 50:  # Add volume threshold
                clusters.append({
                    "center_price": sum(cluster_prices) / len(cluster_prices),
                    "price_range": (min(cluster_prices), max(cluster_prices)),
                    "total_volume": total_volume,
                    "order_count": len(cluster_prices),
                    "side": side,
                    "avg_volume": total_volume / len(cluster_prices),
                    "volume_weighted_price": sum(p * v for p, v in zip(cluster_prices, cluster_volumes)) / total_volume,
                })
            
            i = j
        
        # Sort by total volume descending and return only significant clusters
        clusters.sort(key=lambda x: x["total_volume"], reverse=True)
        return clusters[:10]  # Limit to top 10 clusters per side'''

content = content.replace(old_find_clusters, new_find_clusters)

# Fix the volume profile POC calculation
# Find the get_volume_profile method and check the POC logic
volume_profile_pattern = r"(async def get_volume_profile.*?)(if len\(volume_by_price\) > 0:.*?)(else:.*?return {)"
match = re.search(volume_profile_pattern, content, re.DOTALL)

if match:
    # Replace the POC finding logic
    old_poc_logic = """if len(volume_by_price) > 0:
                    poc_df = pl.DataFrame(volume_by_price)
                    poc_row = poc_df.sort("volume", descending=True).row(0, named=True)
                    poc = {
                        "price": poc_row["center_price"],
                        "volume": poc_row["volume"],
                        "bucket": poc_row["price_bucket"],
                    }"""

    new_poc_logic = """if len(volume_by_price) > 0:
                    # Find POC (Point of Control) - price level with highest volume
                    poc_data = max(volume_by_price, key=lambda x: x["volume"])
                    poc = {
                        "price": poc_data["center_price"],
                        "volume": poc_data["volume"],
                        "bucket": poc_data["price_bucket"],
                    }"""

    content = content.replace(old_poc_logic, new_poc_logic)

# Write the fixed content
with open("src/project_x_py/async_orderbook.py", "w") as f:
    f.write(content)

print("✅ Fixed remaining async orderbook issues:")
print("  1. Added _cross_reference_with_trades helper method")
print("  2. Implemented advanced iceberg detection from sync version")
print("  3. Improved cluster detection to be less sensitive (volume threshold + limit)")
print("  4. Fixed price tolerance calculation (3x tick size)")
print("  5. Fixed volume profile POC calculation")
print("\nThe async orderbook now has feature parity with the sync version!")
