"""
ProjectX Indicators - Fair Value Gap (FVG) Indicator

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Implements the Fair Value Gap (FVG) indicator for identifying price imbalances
    and potential support/resistance zones. Detects gaps in price action with
    optional mitigation logic, helping traders spot areas likely to be revisited.

Key Features:
    - Identifies bullish/bearish fair value gaps from OHLC data
    - Supports configurable gap size, mitigation threshold, and custom columns
    - Returns gap boundary, size, and mitigation status for each bar
    - Callable as a class or via TA-Lib-style convenience function

Example Usage:
    ```python
    from project_x_py.indicators import FVG

    fvg = FVG()
    data_with_fvg = fvg.calculate(ohlcv_data, min_gap_size=0.001)
    gaps = data_with_fvg.filter(pl.col("fvg_bullish"))
    ```

See Also:
    - `project_x_py.indicators.order_block`
    - `project_x_py.indicators.base.BaseIndicator`
"""

from typing import Any

import polars as pl

from project_x_py.indicators.base import BaseIndicator


class FVG(BaseIndicator):
    """
    Fair Value Gap (FVG) indicator for identifying price imbalances.

    Fair Value Gaps are areas in price action where the market has moved so quickly
    that it has left a "gap" or imbalance. These areas often act as support/resistance
    zones as price tends to return to fill these gaps.

    The indicator identifies both bullish and bearish FVGs based on specific price
    action patterns and can optionally track whether gaps have been mitigated (filled).
    """

    def __init__(self) -> None:
        super().__init__(
            name="FVG",
            description="Fair Value Gap - identifies price imbalance areas that may act as support/resistance",
        )

    def calculate(
        self,
        data: pl.DataFrame,
        **kwargs: Any,
    ) -> pl.DataFrame:
        """
        Calculate Fair Value Gaps (FVG).

        A bullish FVG occurs when:
        - Current candle's low > Previous candle's high (gap up)

        A bearish FVG occurs when:
        - Current candle's high < Previous candle's low (gap down)

        Args:
            data: DataFrame with OHLC data
            **kwargs: Additional parameters:
                high_column: High price column (default: "high")
                low_column: Low price column (default: "low")
                close_column: Close price column (default: "close")
                min_gap_size: Minimum gap size (in price units) to consider valid (default: 0.0)
                check_mitigation: Whether to check if gaps have been mitigated (default: False)
                mitigation_threshold: Percentage of gap that needs to be filled to consider it mitigated (default: 0.5)

        Returns:
            DataFrame with FVG columns added:
            - fvg_bullish: Boolean indicating bullish FVG
            - fvg_bearish: Boolean indicating bearish FVG
            - fvg_bullish_start: Start of bullish gap (previous high)
            - fvg_bullish_end: End of bullish gap (current low)
            - fvg_bearish_start: Start of bearish gap (previous low)
            - fvg_bearish_end: End of bearish gap (current high)
            - fvg_gap_size: Size of the gap
            - fvg_mitigated: Boolean indicating if gap has been mitigated (if check_mitigation=True)

        Example:
            >>> fvg = FVG()
            >>> data_with_fvg = fvg.calculate(ohlcv_data, min_gap_size=0.001)
            >>> bullish_gaps = data_with_fvg.filter(pl.col("fvg_bullish"))
        """
        # Extract parameters from kwargs with defaults
        high_column = kwargs.get("high_column", "high")
        low_column = kwargs.get("low_column", "low")
        close_column = kwargs.get("close_column", "close")
        min_gap_size = kwargs.get("min_gap_size", 0.0)
        check_mitigation = kwargs.get("check_mitigation", False)
        mitigation_threshold = kwargs.get("mitigation_threshold", 0.5)

        required_cols: list[str] = [high_column, low_column, close_column]
        self.validate_data(data, required_cols)
        self.validate_data_length(data, 2)  # Need at least 2 candles

        # Get shifted values for comparison
        result = data.with_columns(
            [
                # Previous candle values
                pl.col(high_column).shift(1).alias("prev_high"),
                pl.col(low_column).shift(1).alias("prev_low"),
            ]
        )

        # Identify FVGs (gaps between consecutive bars)
        result = result.with_columns(
            [
                # Bullish FVG: current low > prev high (gap up)
                (pl.col(low_column) > pl.col("prev_high")).alias("fvg_bullish_raw"),
                # Bearish FVG: current high < prev low (gap down)
                (pl.col(high_column) < pl.col("prev_low")).alias("fvg_bearish_raw"),
            ]
        )

        # Calculate gap boundaries and size
        result = result.with_columns(
            [
                # Bullish gap: from prev high to current low
                pl.when(pl.col("fvg_bullish_raw"))
                .then(pl.col("prev_high"))
                .otherwise(None)
                .alias("fvg_bullish_start"),
                pl.when(pl.col("fvg_bullish_raw"))
                .then(pl.col(low_column))
                .otherwise(None)
                .alias("fvg_bullish_end"),
                # Bearish gap: from prev low to current high
                pl.when(pl.col("fvg_bearish_raw"))
                .then(pl.col("prev_low"))
                .otherwise(None)
                .alias("fvg_bearish_start"),
                pl.when(pl.col("fvg_bearish_raw"))
                .then(pl.col(high_column))
                .otherwise(None)
                .alias("fvg_bearish_end"),
            ]
        )

        # Calculate gap size
        result = result.with_columns(
            [
                pl.when(pl.col("fvg_bullish_raw"))
                .then((pl.col("fvg_bullish_end") - pl.col("fvg_bullish_start")).abs())
                .when(pl.col("fvg_bearish_raw"))
                .then((pl.col("fvg_bearish_start") - pl.col("fvg_bearish_end")).abs())
                .otherwise(None)
                .alias("fvg_gap_size")
            ]
        )

        # Apply minimum gap size filter
        result = result.with_columns(
            [
                (
                    pl.col("fvg_bullish_raw") & (pl.col("fvg_gap_size") >= min_gap_size)
                ).alias("fvg_bullish"),
                (
                    pl.col("fvg_bearish_raw") & (pl.col("fvg_gap_size") >= min_gap_size)
                ).alias("fvg_bearish"),
            ]
        )

        # Check for mitigation if requested
        if check_mitigation:
            # Add row index for tracking
            result = result.with_row_index("_row_idx")

            # Find gap indices
            gap_indices = result.filter(
                pl.col("fvg_bullish") | pl.col("fvg_bearish")
            ).select(
                "_row_idx",
                "fvg_bullish",
                "fvg_bullish_start",
                "fvg_bullish_end",
                "fvg_bearish_start",
                "fvg_bearish_end",
            )

            # Initialize mitigation column
            mitigated = pl.Series("fvg_mitigated", [False] * len(result))

            # Check each gap for mitigation
            for row in gap_indices.iter_rows(named=True):
                gap_idx = row["_row_idx"]
                is_bullish = row["fvg_bullish"]

                # Look at subsequent candles for mitigation
                future_data = result.filter(pl.col("_row_idx") > gap_idx)

                if is_bullish:
                    gap_start = row["fvg_bullish_start"]
                    gap_end = row["fvg_bullish_end"]
                    gap_size = gap_end - gap_start
                    mitigation_amount = gap_size * mitigation_threshold
                    # Bullish gap is mitigated when price goes back below gap_end - mitigation_amount
                    mitigation_level = gap_end - mitigation_amount
                    mitigated_rows = future_data.filter(
                        pl.col(low_column) <= mitigation_level
                    )
                else:
                    gap_start = row["fvg_bearish_start"]
                    gap_end = row["fvg_bearish_end"]
                    gap_size = gap_start - gap_end
                    mitigation_amount = gap_size * mitigation_threshold
                    # Bearish gap is mitigated when price goes back above gap_end + mitigation_amount
                    mitigation_level = gap_end + mitigation_amount
                    mitigated_rows = future_data.filter(
                        pl.col(high_column) >= mitigation_level
                    )

                if len(mitigated_rows) > 0:
                    mitigated[gap_idx] = True

            result = result.with_columns(mitigated)
            result = result.drop("_row_idx")

            # Update gap columns to exclude mitigated gaps if requested
            result = result.with_columns(
                [
                    (pl.col("fvg_bullish") & ~pl.col("fvg_mitigated")).alias(
                        "fvg_bullish"
                    ),
                    (pl.col("fvg_bearish") & ~pl.col("fvg_mitigated")).alias(
                        "fvg_bearish"
                    ),
                ]
            )

        # Clean up intermediate columns
        columns_to_drop: list[str] = [
            "prev_high",
            "prev_low",
            "fvg_bullish_raw",
            "fvg_bearish_raw",
        ]

        result = result.drop(columns_to_drop)

        return result


def calculate_fvg(
    data: pl.DataFrame,
    high_column: str = "high",
    low_column: str = "low",
    close_column: str = "close",
    min_gap_size: float = 0.0,
    check_mitigation: bool = False,
    mitigation_threshold: float = 0.5,
) -> pl.DataFrame:
    """
    Calculate Fair Value Gaps (convenience function).

    See FVG.calculate() for detailed documentation.

    Args:
        data: DataFrame with OHLC data
        high_column: High price column
        low_column: Low price column
        close_column: Close price column
        min_gap_size: Minimum gap size to consider valid
        check_mitigation: Whether to check if gaps have been mitigated
        mitigation_threshold: Percentage of gap that needs to be filled to consider it mitigated

    Returns:
        DataFrame with FVG columns added
    """
    indicator = FVG()
    return indicator.calculate(
        data,
        high_column=high_column,
        low_column=low_column,
        close_column=close_column,
        min_gap_size=min_gap_size,
        check_mitigation=check_mitigation,
        mitigation_threshold=mitigation_threshold,
    )
