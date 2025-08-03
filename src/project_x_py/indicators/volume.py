"""
ProjectX Indicators - Volume Indicators

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Implements volume-based indicators for ProjectX, allowing traders to confirm
    trends, spot reversals, and analyze money flow. Includes both cumulative
    and oscillator-style volume indicators operating on Polars DataFrames.

Key Features:
    - OBV, VWAP, Accumulation/Distribution (AD), AD Oscillator (ADOSC)
    - Rolling, cumulative, and EMA-based volume analytics
    - TA-Lib-style function interface for direct scripting
    - Compatible with all other indicator modules

Example Usage:
    ```python
    from project_x_py.indicators import calculate_vwap

    data_with_vwap = calculate_vwap(ohlcv_data, period=20)
    ```

See Also:
    - `project_x_py.indicators.base.VolumeIndicator`
    - `project_x_py.indicators.momentum`
    - `project_x_py.indicators.overlap`
"""

from typing import Any

import polars as pl

from project_x_py.indicators.base import VolumeIndicator, ema_alpha


class OBV(VolumeIndicator):
    """
    On-Balance Volume (OBV) indicator.

    OBV is a cumulative volume indicator that relates volume to price change. It
    adds volume on days when the price closes higher and subtracts volume on days
    when the price closes lower. The cumulative total shows whether volume is
    flowing into or out of a security.

    OBV is used to confirm price trends and identify potential reversals. When
    OBV and price are moving in the same direction, it confirms the trend. When
    they diverge, it may signal a potential reversal.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OBV",
            description="On-Balance Volume - cumulative indicator relating volume to price change",
        )

    def calculate(
        self,
        data: pl.DataFrame,
        **kwargs: Any,
    ) -> pl.DataFrame:
        """
        Calculate On-Balance Volume.

        Args:
            data: DataFrame with OHLCV data
            **kwargs: Additional parameters:
                close_column: Close price column (default: "close")
                volume_column: Volume column (default: "volume")

        Returns:
            DataFrame with OBV column added

        Example:
            >>> obv = OBV()
            >>> data_with_obv = obv.calculate(ohlcv_data)
            >>> print(data_with_obv.columns)  # Now includes 'obv'
        """
        close_column: str = kwargs.get("close_column", "close")
        volume_column: str = kwargs.get("volume_column", "volume")
        required_cols: list[str] = [close_column, volume_column]
        self.validate_data(data, required_cols)
        self.validate_data_length(data, 2)

        # Calculate price change direction
        result = (
            data.with_columns(
                [
                    pl.col(close_column).diff().alias("price_change"),
                ]
            )
            .with_columns(
                [
                    # Add volume if price went up, subtract if down, 0 if unchanged
                    pl.when(pl.col("price_change") > 0)
                    .then(pl.col(volume_column))
                    .when(pl.col("price_change") < 0)
                    .then(-pl.col(volume_column))
                    .otherwise(0)
                    .alias("volume_change")
                ]
            )
            .with_columns(
                # Calculate cumulative sum for OBV
                pl.col("volume_change").cum_sum().alias("obv")
            )
        )

        # Remove intermediate columns
        return result.drop(["price_change", "volume_change"])


class VWAP(VolumeIndicator):
    """
    Volume Weighted Average Price (VWAP) indicator.

    VWAP is the average price weighted by volume. It provides a benchmark price
    that represents the average price at which a security has traded throughout
    the day, taking into account both price and volume.

    VWAP is commonly used by institutional traders to assess whether they are
    buying or selling at favorable prices relative to the market average. It can
    also be used to identify potential support and resistance levels.
    """

    def __init__(self) -> None:
        super().__init__(
            name="VWAP",
            description="Volume Weighted Average Price - average price weighted by volume",
        )

    def calculate(
        self,
        data: pl.DataFrame,
        **kwargs: Any,
    ) -> pl.DataFrame:
        """
        Calculate Volume Weighted Average Price.

        Args:
            data: DataFrame with OHLCV data
            **kwargs: Additional parameters:
                high_column: High price column (default: "high")
                low_column: Low price column (default: "low")
                close_column: Close price column (default: "close")
                volume_column: Volume column (default: "volume")
                period: Optional period for rolling VWAP (None for cumulative)

        Returns:
            DataFrame with VWAP column added

        Example:
            >>> vwap = VWAP()
            >>> data_with_vwap = vwap.calculate(ohlcv_data, period=20)
            >>> print(data_with_vwap.columns)  # Now includes 'vwap_20' or 'vwap'
        """
        high_column: str = kwargs.get("high_column", "high")
        low_column: str = kwargs.get("low_column", "low")
        close_column: str = kwargs.get("close_column", "close")
        volume_column: str = kwargs.get("volume_column", "volume")
        period: int | None = kwargs.get("period")

        required_cols: list[str] = [
            high_column,
            low_column,
            close_column,
            volume_column,
        ]
        self.validate_data(data, required_cols)

        if period is not None:
            self.validate_period(period, min_period=1)
            self.validate_data_length(data, period)

        # Calculate typical price
        result = data.with_columns(
            (
                (pl.col(high_column) + pl.col(low_column) + pl.col(close_column)) / 3
            ).alias("typical_price")
        )

        # Calculate price * volume
        result = result.with_columns(
            (pl.col("typical_price") * pl.col(volume_column)).alias("price_volume")
        )

        if period is None:
            # Cumulative VWAP
            result = result.with_columns(
                [
                    pl.col("price_volume").cum_sum().alias("cumulative_pv"),
                    pl.col(volume_column).cum_sum().alias("cumulative_volume"),
                ]
            ).with_columns(
                (pl.col("cumulative_pv") / pl.col("cumulative_volume")).alias("vwap")
            )

            # Remove intermediate columns
            return result.drop(
                ["typical_price", "price_volume", "cumulative_pv", "cumulative_volume"]
            )
        else:
            # Rolling VWAP
            result = result.with_columns(
                [
                    pl.col("price_volume")
                    .rolling_sum(window_size=period)
                    .alias("rolling_pv"),
                    pl.col(volume_column)
                    .rolling_sum(window_size=period)
                    .alias("rolling_volume"),
                ]
            ).with_columns(
                (pl.col("rolling_pv") / pl.col("rolling_volume")).alias(
                    f"vwap_{period}"
                )
            )

            # Remove intermediate columns
            return result.drop(
                ["typical_price", "price_volume", "rolling_pv", "rolling_volume"]
            )


class AD(VolumeIndicator):
    """Accumulation/Distribution Line indicator."""

    def __init__(self) -> None:
        super().__init__(
            name="AD",
            description="Accumulation/Distribution Line - volume-based indicator showing money flow",
        )

    def calculate(
        self,
        data: pl.DataFrame,
        **kwargs: Any,
    ) -> pl.DataFrame:
        """
        Calculate Accumulation/Distribution Line.

        Args:
            data: DataFrame with OHLCV data
            **kwargs: Additional parameters:
                high_column: High price column (default: "high")
                low_column: Low price column (default: "low")
                close_column: Close price column (default: "close")
                volume_column: Volume column (default: "volume")

        Returns:
            DataFrame with A/D Line column added
        """
        high_column: str = kwargs.get("high_column", "high")
        low_column: str = kwargs.get("low_column", "low")
        close_column: str = kwargs.get("close_column", "close")
        volume_column: str = kwargs.get("volume_column", "volume")

        required_cols: list[str] = [
            high_column,
            low_column,
            close_column,
            volume_column,
        ]
        self.validate_data(data, required_cols)

        # Calculate Money Flow Multiplier
        result = (
            data.with_columns(
                [
                    # CLV = ((Close - Low) - (High - Close)) / (High - Low)
                    (
                        (
                            (pl.col(close_column) - pl.col(low_column))
                            - (pl.col(high_column) - pl.col(close_column))
                        )
                        / (pl.col(high_column) - pl.col(low_column))
                    ).alias("clv")
                ]
            )
            .with_columns(
                # Money Flow Volume = CLV * Volume
                (pl.col("clv") * pl.col(volume_column)).alias("money_flow_volume")
            )
            .with_columns(
                # A/D Line = cumulative sum of Money Flow Volume
                pl.col("money_flow_volume").cum_sum().alias("ad")
            )
        )

        # Remove intermediate columns
        return result.drop(["clv", "money_flow_volume"])


class ADOSC(VolumeIndicator):
    """Accumulation/Distribution Oscillator indicator."""

    def __init__(self) -> None:
        super().__init__(
            name="ADOSC",
            description="Accumulation/Distribution Oscillator - difference between fast and slow A/D Line EMAs",
        )

    def calculate(
        self,
        data: pl.DataFrame,
        **kwargs: Any,
    ) -> pl.DataFrame:
        """
        Calculate Accumulation/Distribution Oscillator.

        Args:
            data: DataFrame with OHLCV data
            **kwargs: Additional parameters:
                high_column: High price column (default: "high")
                low_column: Low price column (default: "low")
                close_column: Close price column (default: "close")
                volume_column: Volume column (default: "volume")
                fast_period: Fast EMA period (default: 3)
                slow_period: Slow EMA period (default: 10)

        Returns:
            DataFrame with A/D Oscillator column added
        """
        high_column: str = kwargs.get("high_column", "high")
        low_column: str = kwargs.get("low_column", "low")
        close_column: str = kwargs.get("close_column", "close")
        volume_column: str = kwargs.get("volume_column", "volume")
        fast_period: int = kwargs.get("fast_period", 3)
        slow_period: int = kwargs.get("slow_period", 10)

        required_cols: list[str] = [
            high_column,
            low_column,
            close_column,
            volume_column,
        ]
        self.validate_data(data, required_cols)
        self.validate_period(fast_period, min_period=1)
        self.validate_period(slow_period, min_period=1)

        if fast_period >= slow_period:
            raise ValueError("Fast period must be less than slow period")

        # First calculate A/D Line
        ad_indicator = AD()
        result = ad_indicator.calculate(
            data=data,
            high_column=high_column,
            low_column=low_column,
            close_column=close_column,
            volume_column=volume_column,
        )

        # Calculate fast and slow EMAs of A/D Line
        fast_alpha = ema_alpha(fast_period)
        slow_alpha = ema_alpha(slow_period)

        result = result.with_columns(
            [
                pl.col("ad").ewm_mean(alpha=fast_alpha).alias("ad_fast"),
                pl.col("ad").ewm_mean(alpha=slow_alpha).alias("ad_slow"),
            ]
        ).with_columns(
            # A/D Oscillator = Fast EMA - Slow EMA
            (pl.col("ad_fast") - pl.col("ad_slow")).alias(
                f"adosc_{fast_period}_{slow_period}"
            )
        )

        # Remove intermediate columns
        return result.drop(["ad", "ad_fast", "ad_slow"])


# Convenience functions for backwards compatibility and TA-Lib style usage
def calculate_obv(
    data: pl.DataFrame,
    close_column: str = "close",
    volume_column: str = "volume",
) -> pl.DataFrame:
    """Calculate OBV (convenience function)."""
    return OBV().calculate(data, close_column=close_column, volume_column=volume_column)


def calculate_vwap(
    data: pl.DataFrame,
    high_column: str = "high",
    low_column: str = "low",
    close_column: str = "close",
    volume_column: str = "volume",
    period: int | None = None,
) -> pl.DataFrame:
    """Calculate VWAP (convenience function)."""
    return VWAP().calculate(
        data,
        high_column=high_column,
        low_column=low_column,
        close_column=close_column,
        volume_column=volume_column,
        period=period,
    )
