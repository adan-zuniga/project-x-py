"""Data manipulation and DataFrame utilities."""

from datetime import datetime
from typing import Any

import polars as pl


def get_polars_rows(df: pl.DataFrame) -> int:
    """Get number of rows from polars DataFrame safely."""
    return getattr(df, "n_rows", 0)


def get_polars_last_value(df: pl.DataFrame, column: str) -> Any:
    """Get the last value from a polars DataFrame column safely."""
    if df.is_empty():
        return None
    return df.select(pl.col(column)).tail(1).item()


def create_data_snapshot(data: pl.DataFrame, description: str = "") -> dict[str, Any]:
    """
    Create a comprehensive snapshot of DataFrame for debugging/analysis.

    Args:
        data: Polars DataFrame
        description: Optional description

    Returns:
        dict: Data snapshot with statistics

    Example:
        >>> snapshot = create_data_snapshot(ohlcv_data, "MGC 5min data")
        >>> print(f"Rows: {snapshot['row_count']}")
        >>> print(f"Timespan: {snapshot['timespan']}")
    """
    if data.is_empty():
        return {
            "description": description,
            "row_count": 0,
            "columns": [],
            "empty": True,
        }

    snapshot = {
        "description": description,
        "row_count": len(data),
        "columns": data.columns,
        "dtypes": {
            col: str(dtype)
            for col, dtype in zip(data.columns, data.dtypes, strict=False)
        },
        "empty": False,
        "created_at": datetime.now(),
    }

    # Add time range if timestamp column exists
    timestamp_cols = [col for col in data.columns if "time" in col.lower()]
    if timestamp_cols:
        ts_col = timestamp_cols[0]
        try:
            first_time = data.select(pl.col(ts_col)).head(1).item()
            last_time = data.select(pl.col(ts_col)).tail(1).item()
            if first_time and last_time:
                snapshot["time_range"] = {"start": first_time, "end": last_time}
                if hasattr(first_time, "timestamp") and hasattr(last_time, "timestamp"):
                    duration = last_time.timestamp() - first_time.timestamp()
                    snapshot["timespan"] = duration
        except Exception:
            pass

    # Add basic statistics for numeric columns
    numeric_cols = [
        col
        for col, dtype in zip(data.columns, data.dtypes, strict=False)
        if dtype in [pl.Float32, pl.Float64, pl.Int32, pl.Int64]
    ]

    if numeric_cols:
        stats: dict[str, dict[str, Any]] = {}
        for col in numeric_cols:
            try:

                def safe_float(val: Any) -> float | None:
                    if val is None:
                        return None
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        return None

                stats[col] = {
                    "min": safe_float(data[col].min()),
                    "max": safe_float(data[col].max()),
                    "mean": safe_float(data[col].mean()),
                    "std": safe_float(data[col].std()),
                }
            except Exception:
                stats[col] = {"error": "Failed to calculate statistics"}
        snapshot["statistics"] = stats

    return snapshot
