"""
ProjectX Indicators - Fair Value Gap (FVG) Indicator

Author: TexasCoding
Date: August 2025

Fair Value Gap indicator identifies imbalance areas in price action where there is little
to no trading activity, which can act as support/resistance zones.
"""

from typing import Any

import polars as pl

from project_x_py.indicators.base import BaseIndicator


class FVG(BaseIndicator):
    """Fair Value Gap indicator for identifying price imbalances."""

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
        - Current candle's low > Previous candle's high
        - Previous candle's low > Two candles ago's high

        A bearish FVG occurs when:
        - Current candle's high < Previous candle's low
        - Previous candle's high < Two candles ago's low

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
            - fvg_gap_top: Top of the gap (resistance for bullish, support for bearish)
            - fvg_gap_bottom: Bottom of the gap (support for bullish, resistance for bearish)
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
        self.validate_data_length(data, 3)  # Need at least 3 candles

        # Get shifted values for comparison
        result = data.with_columns(
            [
                # Previous candle values
                pl.col(high_column).shift(1).alias("prev_high"),
                pl.col(low_column).shift(1).alias("prev_low"),
                # Two candles ago values
                pl.col(high_column).shift(2).alias("prev2_high"),
                pl.col(low_column).shift(2).alias("prev2_low"),
            ]
        )

        # Identify FVGs
        result = result.with_columns(
            [
                # Bullish FVG: current low > prev high AND prev low > prev2 high
                (
                    (pl.col(low_column) > pl.col("prev_high"))
                    & (pl.col("prev_low") > pl.col("prev2_high"))
                ).alias("fvg_bullish_raw"),
                # Bearish FVG: current high < prev low AND prev high < prev2 low
                (
                    (pl.col(high_column) < pl.col("prev_low"))
                    & (pl.col("prev_high") < pl.col("prev2_low"))
                ).alias("fvg_bearish_raw"),
            ]
        )

        # Calculate gap boundaries and size
        result = result.with_columns(
            [
                # Bullish gap: between prev high and current low
                pl.when(pl.col("fvg_bullish_raw"))
                .then(pl.col(low_column))
                .otherwise(None)
                .alias("bullish_gap_top"),
                pl.when(pl.col("fvg_bullish_raw"))
                .then(pl.col("prev_high"))
                .otherwise(None)
                .alias("bullish_gap_bottom"),
                # Bearish gap: between prev low and current high
                pl.when(pl.col("fvg_bearish_raw"))
                .then(pl.col("prev_low"))
                .otherwise(None)
                .alias("bearish_gap_top"),
                pl.when(pl.col("fvg_bearish_raw"))
                .then(pl.col(high_column))
                .otherwise(None)
                .alias("bearish_gap_bottom"),
            ]
        )

        # Combine gap boundaries
        result = result.with_columns(
            [
                pl.when(pl.col("fvg_bullish_raw"))
                .then(pl.col("bullish_gap_top"))
                .when(pl.col("fvg_bearish_raw"))
                .then(pl.col("bearish_gap_top"))
                .otherwise(None)
                .alias("fvg_gap_top"),
                pl.when(pl.col("fvg_bullish_raw"))
                .then(pl.col("bullish_gap_bottom"))
                .when(pl.col("fvg_bearish_raw"))
                .then(pl.col("bearish_gap_bottom"))
                .otherwise(None)
                .alias("fvg_gap_bottom"),
            ]
        )

        # Calculate gap size
        result = result.with_columns(
            [
                (pl.col("fvg_gap_top") - pl.col("fvg_gap_bottom"))
                .abs()
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
            ).select("_row_idx", "fvg_bullish", "fvg_gap_top", "fvg_gap_bottom")

            # Initialize mitigation column
            mitigated = pl.Series("fvg_mitigated", [False] * len(result))

            # Check each gap for mitigation
            for row in gap_indices.iter_rows(named=True):
                gap_idx = row["_row_idx"]
                is_bullish = row["fvg_bullish"]
                gap_top = row["fvg_gap_top"]
                gap_bottom = row["fvg_gap_bottom"]
                gap_size = gap_top - gap_bottom
                mitigation_amount = gap_size * mitigation_threshold

                # Look at subsequent candles for mitigation
                future_data = result.filter(pl.col("_row_idx") > gap_idx)

                if is_bullish:
                    # Bullish gap is mitigated when price goes below gap_top - mitigation_amount
                    mitigation_level = gap_top - mitigation_amount
                    mitigated_rows = future_data.filter(
                        pl.col(low_column) <= mitigation_level
                    )
                else:
                    # Bearish gap is mitigated when price goes above gap_bottom + mitigation_amount
                    mitigation_level = gap_bottom + mitigation_amount
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
            "prev2_high",
            "prev2_low",
            "fvg_bullish_raw",
            "fvg_bearish_raw",
            "bullish_gap_top",
            "bullish_gap_bottom",
            "bearish_gap_top",
            "bearish_gap_bottom",
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
