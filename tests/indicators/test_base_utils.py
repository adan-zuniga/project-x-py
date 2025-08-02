import pytest
import polars as pl

from project_x_py.indicators.base import (
    BaseIndicator,
    safe_division,
    IndicatorError,
)
from project_x_py.indicators.overlap import calculate_sma, SMA
from project_x_py.indicators.momentum import calculate_rsi
from project_x_py.indicators.volatility import calculate_atr
from project_x_py.indicators.volume import calculate_obv

def test_validate_data_missing_column(sample_ohlcv_df):
    df_missing = sample_ohlcv_df.drop("open")
    sma = SMA()
    with pytest.raises(IndicatorError, match="Missing required columns?"):
        sma.validate_data(df_missing, required_cols=["open", "close"])

def test_validate_data_length_too_short(small_ohlcv_df):
    sma = SMA()
    with pytest.raises(IndicatorError, match="at least"):
        sma.validate_data_length(small_ohlcv_df, min_length=10)

def test_validate_period_negative_or_zero():
    sma = SMA()
    for val in [0, -1, -10]:
        with pytest.raises(IndicatorError, match="period"):
            sma.validate_period(val)

def test_safe_division_behavior():
    df = pl.DataFrame({"numerator": [1, 2], "denominator": [0, 2]})
    out = df.with_columns(
        result=safe_division(pl.col("numerator"), pl.col("denominator"), default_value=-1)
    )
    # Should be Series [-1, 1]
    assert out["result"].to_list() == [-1, 1], f"safe_division gave {out['result'].to_list()}"

@pytest.mark.parametrize("func, kwargs, exp_col", [
    (calculate_sma, {"period": 5}, "sma_5"),
    (calculate_rsi, {"period": 14}, "rsi_14"),
    (calculate_atr, {"period": 14}, "atr_14"),
    (calculate_obv, {}, "obv"),
])
def test_convenience_functions_expected_column_and_shape(sample_ohlcv_df, func, kwargs, exp_col):
    """
    Convenience functions (calculate_sma etc) add expected columns and preserve row count.
    """
    df_func = func(sample_ohlcv_df, **kwargs)
    assert exp_col in df_func.columns, f"{func.__name__} did not add expected column '{exp_col}'"
    assert df_func.height == sample_ohlcv_df.height