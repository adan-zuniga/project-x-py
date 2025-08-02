import pytest
import polars as pl

from project_x_py.indicators.base import (
    BaseIndicator,
    validate_data,
    validate_data_length,
    validate_period,
    safe_division,
    IndicatorError,
)
from project_x_py.indicators.convenience import (
    calculate_sma,
    calculate_rsi,
    calculate_atr,
    calculate_obv,
)

def test_validate_data_missing_column(sample_ohlcv_df):
    df_missing = sample_ohlcv_df.drop("open")
    with pytest.raises(IndicatorError, match="Missing required columns?"):
        validate_data(df_missing, required_cols=["open", "close"])

def test_validate_data_length_too_short(small_ohlcv_df):
    with pytest.raises(IndicatorError, match="at least"):
        validate_data_length(small_ohlcv_df, min_length=10)

def test_validate_period_negative_or_zero():
    for val in [0, -1, -10]:
        with pytest.raises(IndicatorError, match="period"):
            validate_period(val)

def test_safe_division_behavior():
    df = pl.DataFrame({"numerator": [1, 2], "denominator": [0, 2]})
    result = safe_division(df["numerator"], df["denominator"], default_value=-1)
    # Should be Series [-1, 1]
    assert list(result) == [-1, 1], f"safe_division gave {list(result)}"

@pytest.mark.parametrize("func, kwargs, exp_col", [
    (calculate_sma, {"period": 5}, "sma_5"),
    (calculate_rsi, {"period": 14}, "rsi_14"),
    (calculate_atr, {"period": 14}, "atr_14"),
    (calculate_obv, {}, "obv"),
])
def test_convenience_functions_match_class(sample_ohlcv_df, func, kwargs, exp_col):
    """
    Convenience functions (calculate_sma etc) add expected columns and match direct class output.
    """
    # Call via function
    df_func = func(sample_ohlcv_df, **kwargs)
    assert exp_col in df_func.columns, f"{func.__name__} did not add expected column '{exp_col}'"
    assert df_func.height == sample_ohlcv_df.height

    # Find corresponding indicator class dynamically and compare output
    # E.g. for calculate_sma → SmaIndicator, etc.
    func_name = func.__name__
    if func_name.startswith("calculate_"):
        class_name = func_name.replace("calculate_", "").upper() + "Indicator"
    else:
        class_name = func_name.capitalize() + "Indicator"
    # Map to known class names for common indicators
    class_map = {
        "SMAIndicator": "SmaIndicator",
        "RSIIndicator": "RsiIndicator",
        "ATRIndicator": "AtrIndicator",
        "OBVIndicator": "ObvIndicator",
    }
    class_name = class_map.get(class_name, class_name)

    import project_x_py.indicators
    indicator_cls = getattr(project_x_py.indicators, class_name, None)
    assert indicator_cls is not None, (
        f"Could not find indicator class '{class_name}' for {func.__name__}"
    )
    # Instantiate and run
    ind = indicator_cls(**kwargs)
    df_class = ind(sample_ohlcv_df)
    # Compare the expected column
    assert df_func[exp_col].series_equal(df_class[exp_col]), (
        f"{func.__name__} and {class_name} produced different '{exp_col}' values"
    )