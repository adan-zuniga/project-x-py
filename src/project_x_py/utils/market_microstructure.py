"""Market microstructure analysis including bid-ask spread and volume profile."""

from typing import Any

import polars as pl


def analyze_bid_ask_spread(
    data: pl.DataFrame,
    bid_column: str = "bid",
    ask_column: str = "ask",
    mid_column: str | None = None,
) -> dict[str, Any]:
    """
    Analyze bid-ask spread characteristics.

    Args:
        data: DataFrame with bid/ask data
        bid_column: Bid price column
        ask_column: Ask price column
        mid_column: Mid price column (optional, will calculate if not provided)

    Returns:
        Dict with spread analysis

    Example:
        >>> spread_analysis = analyze_bid_ask_spread(market_data)
        >>> print(f"Average spread: ${spread_analysis['avg_spread']:.4f}")
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
                        (pl.col(ask_column) - pl.col(bid_column)) / pl.col(mid_column)
                    ).alias("relative_spread"),
                ]
            )
            .select(["spread", "relative_spread"])
            .drop_nulls()
        )

        if analysis_data.is_empty():
            return {"error": "No valid spread data"}

        return {
            "avg_spread": analysis_data.select(pl.col("spread").mean()).item() or 0.0,
            "median_spread": analysis_data.select(pl.col("spread").median()).item()
            or 0.0,
            "min_spread": analysis_data.select(pl.col("spread").min()).item() or 0.0,
            "max_spread": analysis_data.select(pl.col("spread").max()).item() or 0.0,
            "avg_relative_spread": analysis_data.select(
                pl.col("relative_spread").mean()
            ).item()
            or 0.0,
            "spread_volatility": analysis_data.select(pl.col("spread").std()).item()
            or 0.0,
        }

    except Exception as e:
        return {"error": str(e)}


def calculate_volume_profile(
    data: pl.DataFrame,
    price_column: str = "close",
    volume_column: str = "volume",
    num_bins: int = 50,
) -> dict[str, Any]:
    """
    Calculate volume profile analysis.

    Args:
        data: DataFrame with price and volume data
        price_column: Price column for binning
        volume_column: Volume column for aggregation
        num_bins: Number of price bins

    Returns:
        Dict with volume profile analysis

    Example:
        >>> vol_profile = calculate_volume_profile(ohlcv_data)
        >>> print(f"POC Price: ${vol_profile['point_of_control']:.2f}")
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

        # Create price bins
        bin_size = (max_price - min_price) / num_bins
        bins = [min_price + i * bin_size for i in range(num_bins + 1)]

        # Calculate volume per price level
        volume_by_price = []
        for i in range(len(bins) - 1):
            bin_data = data.filter(
                (pl.col(price_column) >= bins[i]) & (pl.col(price_column) < bins[i + 1])
            )

            if not bin_data.is_empty():
                total_volume = bin_data.select(pl.col(volume_column).sum()).item() or 0
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
