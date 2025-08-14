"""
ProjectX Indicators - Candlestick Pattern Recognition

Author: @TexasCoding
Date: 2025-08-03

Overview:
    Implements common candlestick pattern indicators with strength validation.
    Each pattern is implemented as a class that adds strength and validity columns
    to the DataFrame. Strength is calculated based on how well the pattern matches
    ideal conditions, allowing for validation of pattern quality.

Key Features:
    - Detection of common patterns like Doji, Hammer, Engulfing, etc.
    - Strength scoring from -100 (strong bearish) to 100 (strong bullish)
    - Configurable minimum strength for validity
    - Multi-candle pattern support
    - Convenience functions for easy use

Example Usage:
    ```python
    from project_x_py.indicators import calculate_hammer

    data_with_hammer = calculate_hammer(ohlcv_data, min_strength=60)
    strong_hammers = data_with_hammer.filter(pl.col("is_hammer"))
    ```

See Also:
    - `project_x_py.indicators.fvg`
    - `project_x_py.indicators.order_block`
    - `project_x_py.indicators.base.BaseIndicator`
"""

from typing import Any

import polars as pl

from project_x_py.indicators.base import BaseIndicator


class Doji(BaseIndicator):
    """
    Doji candlestick pattern indicator.

    A Doji occurs when open and close are virtually equal, indicating indecision.
    Strength is higher when body is smaller relative to the range.
    Positive strength for standard Doji (potential reversal in either direction).
    """

    def __init__(self) -> None:
        super().__init__(
            name="DOJI",
            description="Doji - indecision pattern with open and close nearly equal",
        )

    def calculate(
        self,
        data: pl.DataFrame,
        **kwargs: Any,
    ) -> pl.DataFrame:
        open_col = kwargs.get("open_column", "open")
        high_col = kwargs.get("high_column", "high")
        low_col = kwargs.get("low_column", "low")
        close_col = kwargs.get("close_column", "close")
        min_strength = kwargs.get("min_strength", 50)

        required = [open_col, high_col, low_col, close_col]
        self.validate_data(data, required)

        result = data.with_columns(
            [
                (pl.col(close_col) - pl.col(open_col)).abs().alias("body"),
                (pl.col(high_col) - pl.col(low_col)).alias("range"),
            ]
        )

        result = result.with_columns(
            pl.when(pl.col("range") > 0)
            .then(100 - (pl.col("body") / pl.col("range") * 100))
            .otherwise(0)
            .clip(0, 100)
            .alias("doji_strength")
        )

        result = result.with_columns(
            (pl.col("doji_strength") >= min_strength).alias("is_doji")
        )

        return result.drop(["body", "range"])


class Hammer(BaseIndicator):
    """
    Hammer candlestick pattern indicator (bullish).

    Hammer has small body, long lower shadow, small upper shadow.
    Strength based on lower shadow length relative to body and small upper shadow.
    """

    def __init__(self) -> None:
        super().__init__(
            name="HAMMER",
            description="Hammer - bullish reversal with long lower shadow",
        )

    def calculate(
        self,
        data: pl.DataFrame,
        **kwargs: Any,
    ) -> pl.DataFrame:
        open_col = kwargs.get("open_column", "open")
        high_col = kwargs.get("high_column", "high")
        low_col = kwargs.get("low_column", "low")
        close_col = kwargs.get("close_column", "close")
        min_strength = kwargs.get("min_strength", 50)

        required = [open_col, high_col, low_col, close_col]
        self.validate_data(data, required)

        result = data.with_columns(
            [
                (pl.col(close_col) - pl.col(open_col)).abs().alias("body"),
                (pl.col(high_col) - pl.max_horizontal([close_col, open_col])).alias(
                    "upper_shadow"
                ),
                (pl.min_horizontal([close_col, open_col]) - pl.col(low_col)).alias(
                    "lower_shadow"
                ),
                (pl.col(high_col) - pl.col(low_col)).alias("range"),
            ]
        )

        result = result.with_columns(
            pl.when(
                (pl.col("body") > 0)
                & (pl.col("lower_shadow") >= 2 * pl.col("body"))
                & (pl.col("upper_shadow") <= pl.col("body") * 0.3)
                & (
                    pl.min_horizontal([close_col, open_col])
                    > pl.col(low_col) + pl.col("lower_shadow") * 0.6
                )
            )
            .then(
                pl.min_horizontal(
                    pl.lit(100),
                    (pl.col("lower_shadow") / pl.col("body") * 20)
                    + (
                        100
                        - (pl.col("upper_shadow") / pl.col("body") * 100).clip(0, 50)
                    )
                    + (100 - (pl.col("body") / pl.col("range") * 100).clip(0, 50)),
                )
                / 3
            )
            .otherwise(0)
            .alias("hammer_strength")
        )

        result = result.with_columns(
            (pl.col("hammer_strength") >= min_strength).alias("is_hammer")
        )

        return result.drop(["body", "upper_shadow", "lower_shadow", "range"])


class ShootingStar(BaseIndicator):
    """
    Shooting Star candlestick pattern indicator (bearish).

    Shooting Star has small body, long upper shadow, small lower shadow.
    Strength is negative, magnitude based on upper shadow relative to body.
    """

    def __init__(self) -> None:
        super().__init__(
            name="SHOOTINGSTAR",
            description="Shooting Star - bearish reversal with long upper shadow",
        )

    def calculate(
        self,
        data: pl.DataFrame,
        **kwargs: Any,
    ) -> pl.DataFrame:
        open_col = kwargs.get("open_column", "open")
        high_col = kwargs.get("high_column", "high")
        low_col = kwargs.get("low_column", "low")
        close_col = kwargs.get("close_column", "close")
        min_strength = kwargs.get("min_strength", 50)

        required = [open_col, high_col, low_col, close_col]
        self.validate_data(data, required)

        result = data.with_columns(
            [
                (pl.col(close_col) - pl.col(open_col)).abs().alias("body"),
                (pl.col(high_col) - pl.max_horizontal([close_col, open_col])).alias(
                    "upper_shadow"
                ),
                (pl.min_horizontal([close_col, open_col]) - pl.col(low_col)).alias(
                    "lower_shadow"
                ),
                (pl.col(high_col) - pl.col(low_col)).alias("range"),
            ]
        )

        result = result.with_columns(
            pl.when(
                (pl.col("body") > 0)
                & (pl.col("upper_shadow") >= 2 * pl.col("body"))
                & (pl.col("lower_shadow") <= pl.col("body") * 0.3)
                & (
                    pl.max_horizontal([close_col, open_col])
                    < pl.col(high_col) - pl.col("upper_shadow") * 0.6
                )
            )
            .then(
                -1
                * pl.min_horizontal(
                    pl.lit(100),
                    (pl.col("upper_shadow") / pl.col("body") * 20)
                    + (
                        100
                        - (pl.col("lower_shadow") / pl.col("body") * 100).clip(0, 50)
                    )
                    + (100 - (pl.col("body") / pl.col("range") * 100).clip(0, 50)),
                )
                / 3
            )
            .otherwise(0)
            .alias("shootingstar_strength")
        )

        result = result.with_columns(
            (pl.col("shootingstar_strength").abs() >= min_strength).alias(
                "is_shootingstar"
            )
        )

        return result.drop(["body", "upper_shadow", "lower_shadow", "range"])


class BullishEngulfing(BaseIndicator):
    """
    Bullish Engulfing pattern indicator (2 candles).

    Bullish Engulfing occurs when a small bearish candle is followed by a large bullish candle that engulfs it.
    Strength based on how much it engulfs and body sizes.
    """

    def __init__(self) -> None:
        super().__init__(
            name="BULLISHENGULFING",
            description="Bullish Engulfing - bullish reversal pattern",
        )

    def calculate(
        self,
        data: pl.DataFrame,
        **kwargs: Any,
    ) -> pl.DataFrame:
        open_col = kwargs.get("open_column", "open")
        close_col = kwargs.get("close_column", "close")
        min_strength = kwargs.get("min_strength", 50)

        required = [open_col, close_col]
        self.validate_data(data, required)
        self.validate_data_length(data, 2)

        result = data.with_columns(
            [
                pl.col(open_col).shift(1).alias("prev_open"),
                pl.col(close_col).shift(1).alias("prev_close"),
            ]
        )

        result = result.with_columns(
            [
                (pl.col("prev_close") < pl.col("prev_open")).alias("prev_bearish"),
                (pl.col(close_col) > pl.col(open_col)).alias("current_bullish"),
                (pl.col(open_col) < pl.col("prev_close")).alias("engulfs_low"),
                (pl.col(close_col) > pl.col("prev_open")).alias("engulfs_high"),
            ]
        )

        result = result.with_columns(
            pl.when(
                pl.col("prev_bearish")
                & pl.col("current_bullish")
                & pl.col("engulfs_low")
                & pl.col("engulfs_high")
            )
            .then(100)  # Simple for now, can add more factors
            .otherwise(0)
            .alias("bullishengulfing_strength")
        )

        result = result.with_columns(
            (pl.col("bullishengulfing_strength") >= min_strength).alias(
                "is_bullishengulfing"
            )
        )

        return result.drop(
            [
                "prev_open",
                "prev_close",
                "prev_bearish",
                "current_bullish",
                "engulfs_low",
                "engulfs_high",
            ]
        )


# Convenience functions


def calculate_doji(data: pl.DataFrame, **kwargs: Any) -> pl.DataFrame:
    return Doji().calculate(data, **kwargs)


def calculate_hammer(data: pl.DataFrame, **kwargs: Any) -> pl.DataFrame:
    return Hammer().calculate(data, **kwargs)


def calculate_shootingstar(data: pl.DataFrame, **kwargs: Any) -> pl.DataFrame:
    return ShootingStar().calculate(data, **kwargs)


def calculate_bullishengulfing(data: pl.DataFrame, **kwargs: Any) -> pl.DataFrame:
    return BullishEngulfing().calculate(data, **kwargs)
