#!/usr/bin/env python3
"""Fix the iceberg detection method body."""

# Read the file
with open("src/project_x_py/async_orderbook.py") as f:
    lines = f.readlines()

# Find the start of detect_iceberg_orders method
in_method = False
method_start = None
method_end = None
indent_level = None

for i, line in enumerate(lines):
    if "async def detect_iceberg_orders(" in line:
        method_start = i
        in_method = True
        indent_level = len(line) - len(line.lstrip())
    elif in_method and line.strip() and len(line) - len(line.lstrip()) <= indent_level:
        # We've found the next method at the same or lower indent level
        method_end = i
        break

# Replace the method body
if method_start is not None:
    # Keep the method signature and docstring
    docstring_end = method_start
    for i in range(method_start + 1, len(lines)):
        if '"""' in lines[i] and i > method_start + 1:
            docstring_end = i + 1
            break

    # New method implementation
    new_implementation = """        try:
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
            return {"potential_icebergs": [], "analysis": {"error": str(e)}}
"""

    # Find the end of the current method implementation
    if method_end is None:
        method_end = len(lines)

    # Replace the implementation
    new_lines = lines[:docstring_end] + [new_implementation + "\n"] + lines[method_end:]

    # Write back
    with open("src/project_x_py/async_orderbook.py", "w") as f:
        f.writelines(new_lines)

    print("✅ Fixed iceberg detection method implementation")

# Also need to fix duplicate get_price_level_history method
with open("src/project_x_py/async_orderbook.py") as f:
    content = f.read()

# Find and remove the duplicate method (keep the first one)
import re

pattern = r"(\n    async def get_price_level_history.*?\n            return \[\]\n)"
matches = list(re.finditer(pattern, content, re.DOTALL))

if len(matches) > 1:
    # Remove the second occurrence
    content = content[: matches[1].start()] + content[matches[1].end() :]

    with open("src/project_x_py/async_orderbook.py", "w") as f:
        f.write(content)

    print("✅ Removed duplicate get_price_level_history method")
