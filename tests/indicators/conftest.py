import polars as pl
import pytest


@pytest.fixture
def sample_ohlcv_df():
    """
    Returns a deterministic polars DataFrame with 120 rows and standard OHLCV columns.
    Values are monotonically increasing for easy/deterministic indicator output.
    """
    n = 120
    return pl.DataFrame(
        {
            "open": [float(i) for i in range(n)],
            "high": [float(i) + 1 for i in range(n)],
            "low": [float(i) - 1 for i in range(n)],
            "close": [float(i) + 0.5 for i in range(n)],
            "volume": [100 + i for i in range(n)],
        }
    )


@pytest.fixture
def small_ohlcv_df():
    """
    Returns a polars DataFrame with 5 rows to trigger insufficient data paths.
    """
    n = 5
    return pl.DataFrame(
        {
            "open": [float(i) for i in range(n)],
            "high": [float(i) + 1 for i in range(n)],
            "low": [float(i) - 1 for i in range(n)],
            "close": [float(i) + 0.5 for i in range(n)],
            "volume": [100 + i for i in range(n)],
        }
    )
