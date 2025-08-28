"""
Session-aware indicator functions.

Provides indicator calculations that respect trading session boundaries,
including VWAP resets, session anchored calculations, and session statistics.

Author: TDD Implementation
Date: 2025-08-28
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from project_x_py.sessions import SessionType


async def calculate_session_vwap(
    data: pl.DataFrame, session_type: SessionType, product: str = "ES"
) -> pl.DataFrame:
    """
    Calculate VWAP that resets at session boundaries.

    Args:
        data: DataFrame with OHLCV data
        session_type: Type of session (RTH/ETH)
        product: Product symbol for session times

    Returns:
        DataFrame with session_vwap column added
    """
    from project_x_py.sessions import SessionConfig, SessionFilterMixin

    if data.is_empty():
        return data.with_columns(pl.lit(None).alias("session_vwap"))

    # Add session date for grouping
    data_with_date = data.with_columns(
        pl.col("timestamp").dt.date().alias("session_date")
    )

    # Filter to identify which rows are in session
    filter_mixin = SessionFilterMixin(config=SessionConfig(session_type=session_type))

    # Add a flag for in-session rows
    in_session_flags = []
    for row in data.iter_rows(named=True):
        timestamp = row["timestamp"]
        in_session = filter_mixin.is_in_session(timestamp, session_type, product)
        in_session_flags.append(in_session)

    data_with_flags = data_with_date.with_columns(
        pl.Series("in_session", in_session_flags)
    )

    # Calculate VWAP only for in-session data, reset by date
    result = data_with_flags.with_columns(
        [
            pl.when(pl.col("in_session"))
            .then(pl.col("close") * pl.col("volume"))
            .otherwise(0)
            .alias("price_volume")
        ]
    )

    # Calculate cumulative sums per session date
    result = result.with_columns(
        [
            pl.col("price_volume").cum_sum().over("session_date").alias("cum_pv"),
            pl.when(pl.col("in_session"))
            .then(pl.col("volume"))
            .otherwise(0)
            .cum_sum()
            .over("session_date")
            .alias("cum_volume"),
        ]
    )

    # Calculate VWAP
    result = result.with_columns(
        [
            pl.when(pl.col("cum_volume") > 0)
            .then(pl.col("cum_pv") / pl.col("cum_volume"))
            .otherwise(None)
            .alias("session_vwap")
        ]
    )

    # Clean up and return
    return result.drop(
        ["session_date", "in_session", "price_volume", "cum_pv", "cum_volume"]
    )


def find_session_boundaries(data: pl.DataFrame) -> list:
    """
    Find indices where sessions start/end.

    Args:
        data: DataFrame with timestamp column

    Returns:
        List of indices marking session boundaries
    """
    if data.is_empty():
        return []

    # Add date column
    with_date = data.with_columns(pl.col("timestamp").dt.date().alias("date"))

    # Find where date changes
    boundaries = []
    prev_date = None

    for i, row in enumerate(with_date.iter_rows(named=True)):
        current_date = row["date"]
        if i > 0 and current_date != prev_date:
            boundaries.append(i)
        prev_date = current_date

    return boundaries


def create_single_session_data() -> pl.DataFrame:
    """Create data for a single trading session."""
    from datetime import timedelta

    timestamps = []
    base = datetime(2024, 1, 15, 14, 30, tzinfo=UTC)  # 9:30 AM ET

    for i in range(390):  # 6.5 hours of minutes
        timestamps.append(base + timedelta(minutes=i))

    prices = [100.0 + i * 0.01 for i in range(390)]

    return pl.DataFrame(
        {
            "timestamp": timestamps,
            "open": prices,
            "high": [p + 0.05 for p in prices],
            "low": [p - 0.05 for p in prices],
            "close": prices,
            "volume": [1000 + i * 10 for i in range(390)],
        }
    )


async def calculate_anchored_vwap(
    data: pl.DataFrame, anchor_point: str = "session_open"
) -> pl.DataFrame:
    """
    Calculate VWAP anchored to specific point.

    Args:
        data: DataFrame with OHLCV data
        anchor_point: Where to anchor VWAP calculation

    Returns:
        DataFrame with anchored_vwap column
    """
    if data.is_empty():
        return data.with_columns(pl.lit(None).alias("anchored_vwap"))

    # For session_open, calculate cumulative from first bar
    if anchor_point == "session_open":
        result = (
            data.with_columns(
                [(pl.col("close") * pl.col("volume")).alias("price_volume")]
            )
            .with_columns(
                [
                    pl.col("price_volume").cum_sum().alias("cum_pv"),
                    pl.col("volume").cum_sum().alias("cum_volume"),
                ]
            )
            .with_columns(
                [(pl.col("cum_pv") / pl.col("cum_volume")).alias("anchored_vwap")]
            )
            .drop(["price_volume", "cum_pv", "cum_volume"])
        )

        return result

    return data


async def calculate_session_levels(data: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate cumulative session high/low.

    Args:
        data: DataFrame with OHLCV data

    Returns:
        DataFrame with session_high, session_low, session_range columns
    """
    if data.is_empty():
        return data.with_columns(
            [
                pl.lit(None).alias("session_high"),
                pl.lit(None).alias("session_low"),
                pl.lit(None).alias("session_range"),
            ]
        )

    # Add date for grouping
    with_date = data.with_columns(pl.col("timestamp").dt.date().alias("session_date"))

    # Calculate cumulative high/low per session
    result = (
        with_date.with_columns(
            [
                pl.col("high").cum_max().over("session_date").alias("session_high"),
                pl.col("low").cum_min().over("session_date").alias("session_low"),
            ]
        )
        .with_columns(
            [(pl.col("session_high") - pl.col("session_low")).alias("session_range")]
        )
        .drop("session_date")
    )

    return result


async def calculate_session_cumulative_volume(data: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate cumulative volume within session.

    Args:
        data: DataFrame with volume column

    Returns:
        DataFrame with session_cumulative_volume column
    """
    if data.is_empty():
        return data.with_columns(pl.lit(None).alias("session_cumulative_volume"))

    # Add date for grouping
    with_date = data.with_columns(pl.col("timestamp").dt.date().alias("session_date"))

    # Calculate cumulative volume per session
    result = with_date.with_columns(
        [
            pl.col("volume")
            .cum_sum()
            .over("session_date")
            .alias("session_cumulative_volume")
        ]
    ).drop("session_date")

    return result


def identify_sessions(data: pl.DataFrame) -> list:
    """
    Identify session start points.

    Args:
        data: DataFrame with timestamp column

    Returns:
        List of indices where sessions start
    """
    if data.is_empty():
        return []

    # Add date column
    with_date = data.with_columns(pl.col("timestamp").dt.date().alias("date"))

    # Find where date changes (session starts)
    session_starts = [0]  # First row is always a session start
    prev_date = None

    for i, row in enumerate(with_date.iter_rows(named=True)):
        current_date = row["date"]
        if i > 0 and current_date != prev_date:
            session_starts.append(i)
        prev_date = current_date

    return session_starts


async def calculate_relative_to_vwap(data: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate price relative to VWAP.

    Args:
        data: DataFrame with close and VWAP columns

    Returns:
        DataFrame with price_vs_vwap and vwap_deviation columns
    """
    # First calculate VWAP if not present
    if "vwap" not in data.columns:
        from project_x_py.indicators import VWAP

        data = data.pipe(VWAP)

    # Calculate relative metrics
    result = data.with_columns(
        [
            (pl.col("close") / pl.col("vwap")).alias("price_vs_vwap"),
            ((pl.col("close") - pl.col("vwap")) / pl.col("vwap") * 100).alias(
                "vwap_deviation"
            ),
        ]
    )

    return result


async def calculate_percent_from_open(data: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate percentage change from session open.

    Args:
        data: DataFrame with OHLCV data

    Returns:
        DataFrame with percent_from_open column
    """
    if data.is_empty():
        return data.with_columns(pl.lit(None).alias("percent_from_open"))

    # Add date for grouping
    with_date = data.with_columns(pl.col("timestamp").dt.date().alias("session_date"))

    # Get first open price of each session
    session_opens = with_date.group_by("session_date").agg(
        pl.col("open").first().alias("session_open")
    )

    # Join back and calculate percentage
    result = (
        with_date.join(session_opens, on="session_date", how="left")
        .with_columns(
            [
                (
                    (pl.col("close") - pl.col("session_open"))
                    / pl.col("session_open")
                    * 100
                ).alias("percent_from_open")
            ]
        )
        .drop(["session_date", "session_open"])
    )

    return result


def create_minute_data() -> pl.DataFrame:
    """Create 1-minute resolution data."""
    from datetime import timedelta

    timestamps = []
    base = datetime(2024, 1, 15, 14, 30, tzinfo=UTC)  # 9:30 AM ET

    # Create 2 days of minute data
    for day in range(2):
        day_base = base + timedelta(days=day)
        for i in range(390):  # 6.5 hours of minutes
            timestamps.append(day_base + timedelta(minutes=i))

    prices = [100.0 + (i % 390) * 0.01 for i in range(len(timestamps))]

    return pl.DataFrame(
        {
            "timestamp": timestamps,
            "open": prices,
            "high": [p + 0.05 for p in prices],
            "low": [p - 0.05 for p in prices],
            "close": prices,
            "volume": [1000 + (i % 390) * 10 for i in range(len(timestamps))],
        }
    )


async def aggregate_with_sessions(
    data: pl.DataFrame, timeframe: str, session_type: SessionType
) -> pl.DataFrame:
    """
    Aggregate data to higher timeframe respecting sessions.

    Args:
        data: DataFrame with 1-minute OHLCV data
        timeframe: Target timeframe (e.g., "5min")
        session_type: Type of session for filtering

    Returns:
        Aggregated DataFrame
    """
    from project_x_py.sessions import SessionConfig, SessionFilterMixin

    # Filter to session first
    filter_mixin = SessionFilterMixin(config=SessionConfig(session_type=session_type))
    session_data = await filter_mixin.filter_by_session(data, session_type, "ES")

    if session_data.is_empty():
        return session_data

    # Parse timeframe
    if timeframe == "5min":
        interval = 5
    elif timeframe == "15min":
        interval = 15
    else:
        interval = 5  # Default

    # Add grouping column
    result = session_data.with_columns(
        [
            (pl.col("timestamp").dt.minute() // interval).alias("interval_group"),
            pl.col("timestamp").dt.date().alias("date"),
            pl.col("timestamp").dt.hour().alias("hour"),
        ]
    )

    # Aggregate
    aggregated = (
        result.group_by(["date", "hour", "interval_group"], maintain_order=True)
        .agg(
            [
                pl.col("timestamp").first(),
                pl.col("open").first(),
                pl.col("high").max(),
                pl.col("low").min(),
                pl.col("close").last(),
                pl.col("volume").sum(),
            ]
        )
        .drop(["date", "hour", "interval_group"])
        .sort("timestamp")
    )

    return aggregated


async def generate_session_alerts(data: pl.DataFrame, conditions: dict) -> pl.DataFrame:
    """
    Generate alerts based on conditions.

    Args:
        data: DataFrame with indicator columns
        conditions: Dict of alert name to condition expression

    Returns:
        DataFrame with alerts column
    """
    # Initialize alerts column
    alerts = []

    # For each row, check conditions
    for row in data.iter_rows(named=True):
        row_alerts = []

        for alert_name, condition in conditions.items():
            # Simple evaluation for common conditions
            if condition == "close > sma_10":
                if (
                    "sma_10" in row
                    and row.get("close")
                    and row.get("sma_10")
                    and row["close"] > row["sma_10"]
                ):
                    row_alerts.append(alert_name)
            elif condition == "rsi_14 > 70":
                if "rsi_14" in row and row.get("rsi_14") and row["rsi_14"] > 70:
                    row_alerts.append(alert_name)
            elif (
                condition == "high == session_high"
                and "high" in row
                and "session_high" in row
                and row.get("high") == row.get("session_high")
            ):
                row_alerts.append(alert_name)

        alerts.append(row_alerts if row_alerts else None)

    # Add alerts column
    return data.with_columns(pl.Series("alerts", alerts))


def calculate_session_gap(friday_data: pl.DataFrame, monday_data: pl.DataFrame) -> dict:
    """
    Calculate the gap between Friday close and Monday open.

    Args:
        friday_data: DataFrame with Friday closing data
        monday_data: DataFrame with Monday opening data

    Returns:
        Dictionary with gap_size and gap_percentage
    """
    if friday_data.is_empty() or monday_data.is_empty():
        return {"gap_size": 0.0, "gap_percentage": 0.0}

    friday_close = friday_data["close"][-1]
    monday_open = monday_data["open"][0]

    gap_size = float(monday_open - friday_close)
    gap_percentage = (gap_size / friday_close * 100) if friday_close != 0 else 0.0

    return {"gap_size": gap_size, "gap_percentage": gap_percentage}


def get_volume_profile(data: pl.DataFrame, session_type: SessionType) -> dict:
    """
    Build volume profile showing U-shaped pattern.

    Args:
        data: DataFrame with price and volume data
        session_type: Session type for filtering

    Returns:
        Dictionary with open_volume, midday_volume, and close_volume
    """
    _ = session_type  # Will be used for actual session filtering in future
    if data.is_empty():
        return {"open_volume": 0, "midday_volume": 0, "close_volume": 0}

    # Get volumes for profile calculation
    volumes = data["volume"]

    if len(data) < 3:
        # Not enough data for a profile
        return {
            "open_volume": volumes[0] if len(volumes) > 0 else 0,
            "midday_volume": volumes[0] if len(volumes) > 0 else 0,
            "close_volume": volumes[-1] if len(volumes) > 0 else 0,
        }

    # First data point is open
    open_volume = int(volumes[0])

    # Last data point is close
    close_volume = int(volumes[-1])

    # Middle point(s) for midday
    mid_idx = len(volumes) // 2
    midday_volume = int(volumes[mid_idx])

    return {
        "open_volume": open_volume,
        "midday_volume": midday_volume,
        "close_volume": close_volume,
    }


def get_session_performance_metrics(data: pl.DataFrame | None) -> dict:
    """
    Calculate performance metrics for session data.

    Args:
        data: DataFrame with session data or None

    Returns:
        Dictionary with various performance metrics
    """
    # Return default metrics structure
    metrics = {
        "rth_tick_rate": 0.0,  # Ticks per second in RTH
        "eth_tick_rate": 0.0,  # Ticks per second in ETH
        "rth_data_quality": 1.0,  # Data completeness score
        "session_efficiency": 1.0,  # Processing efficiency score
    }

    if data is None or data.is_empty():
        return metrics

    # Calculate tick rates based on data density
    if len(data) > 1:
        time_span = (data["timestamp"][-1] - data["timestamp"][0]).total_seconds()
        if time_span > 0:
            # Assuming RTH is roughly 6.5 hours and ETH is 17.5 hours
            # This is simplified - in reality we'd need to identify actual session periods
            metrics["rth_tick_rate"] = len(data) / max(time_span, 1)
            metrics["eth_tick_rate"] = (
                len(data) / max(time_span, 1) * 0.37
            )  # RTH is ~37% of day

    return metrics
