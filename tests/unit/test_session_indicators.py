"""
Tests for session-aware technical indicators.

These tests define the EXPECTED behavior for indicators that respect
trading sessions (RTH vs ETH). Following strict TDD methodology.

Author: TDD Implementation
Date: 2025-08-28
"""

import pytest
import polars as pl
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from project_x_py.sessions import SessionConfig, SessionType, SessionFilterMixin
from project_x_py.indicators import SMA, EMA, VWAP, RSI, MACD
from project_x_py.sessions.indicators import (
    calculate_session_vwap,
    find_session_boundaries,
    create_single_session_data,
    calculate_anchored_vwap,
    calculate_session_levels,
    calculate_session_cumulative_volume,
    identify_sessions,
    calculate_relative_to_vwap,
    calculate_percent_from_open,
    create_minute_data,
    aggregate_with_sessions,
    generate_session_alerts
)


@pytest.fixture
def mixed_session_data():
    """Create data spanning RTH and ETH sessions."""
    timestamps = []
    prices = []
    volumes = []

    # Generate 2 days of mixed session data
    base_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

    for day in range(2):
        day_offset = timedelta(days=day)

        # ETH morning (3 AM - 9:30 AM ET)
        for hour in range(8, 14):  # 8-14 UTC = 3-9 AM ET
            for minute in range(0, 60, 30):
                ts = base_date + day_offset + timedelta(hours=hour, minutes=minute)
                timestamps.append(ts)
                prices.append(100.0 + hour * 0.1 + minute * 0.001)
                volumes.append(100)

        # RTH (9:30 AM - 4 PM ET)
        for hour in range(14, 21):  # 14-21 UTC = 9:30 AM - 4 PM ET
            for minute in range(0, 60, 30):
                ts = base_date + day_offset + timedelta(hours=hour, minutes=minute)
                timestamps.append(ts)
                prices.append(101.0 + hour * 0.2 + minute * 0.002)
                volumes.append(500)  # Higher RTH volume

        # ETH evening (4 PM - 11 PM ET)
        for hour in range(21, 24):  # 21-24 UTC = 4-7 PM ET
            for minute in range(0, 60, 30):
                ts = base_date + day_offset + timedelta(hours=hour, minutes=minute)
                timestamps.append(ts)
                prices.append(102.0 + hour * 0.05 + minute * 0.001)
                volumes.append(150)

    return pl.DataFrame({
        "timestamp": timestamps,
        "open": prices,
        "high": [p + 0.1 for p in prices],
        "low": [p - 0.1 for p in prices],
        "close": prices,
        "volume": volumes
    })


class TestSessionAwareIndicators:
    """Test indicators with session filtering."""

    @pytest.mark.asyncio
    async def test_session_filtered_sma(self, mixed_session_data):
        """SMA should calculate only from session-filtered data."""
        # Create session filter
        session_filter = SessionFilterMixin(
            config=SessionConfig(session_type=SessionType.RTH)
        )

        # Filter to RTH only
        rth_data = await session_filter.filter_by_session(
            mixed_session_data, SessionType.RTH, "ES"
        )

        # Calculate SMA on filtered data
        rth_with_sma = rth_data.pipe(SMA, period=10)

        # SMA should only use RTH prices
        assert "sma_10" in rth_with_sma.columns

        # Compare with full data SMA
        full_with_sma = mixed_session_data.pipe(SMA, period=10)

        # Values should differ due to different input data
        rth_sma_mean = float(rth_with_sma["sma_10"].mean())
        full_sma_mean = float(full_with_sma["sma_10"].mean())
        assert abs(rth_sma_mean - full_sma_mean) > 0.01

    @pytest.mark.asyncio
    async def test_session_aware_vwap(self, mixed_session_data):
        """VWAP should reset at session boundaries."""
        # VWAP with session reset
        session_vwap = await calculate_session_vwap(
            mixed_session_data,
            session_type=SessionType.RTH,
            product="ES"
        )

        assert "session_vwap" in session_vwap.columns

        # VWAP should reset each RTH session
        # Check that VWAP resets between days
        day1_vwap = session_vwap.filter(
            pl.col("timestamp").dt.date() == datetime(2024, 1, 15).date()
        )["session_vwap"]

        day2_vwap = session_vwap.filter(
            pl.col("timestamp").dt.date() == datetime(2024, 1, 16).date()
        )["session_vwap"]

        # First values of each day should be close to the open price
        day1_data = session_vwap.filter(
            pl.col("timestamp").dt.date() == datetime(2024, 1, 15).date()
        )
        day2_data = session_vwap.filter(
            pl.col("timestamp").dt.date() == datetime(2024, 1, 16).date()
        )

        if not day1_data.is_empty():
            day1_first_vwap = day1_data["session_vwap"].head(1)[0]
            day1_first_open = day1_data["open"].head(1)[0]
            if day1_first_vwap is not None:
                assert abs(float(day1_first_vwap) - float(day1_first_open)) < 1.0

        if not day2_data.is_empty():
            day2_first_vwap = day2_data["session_vwap"].head(1)[0]
            day2_first_open = day2_data["open"].head(1)[0]
            if day2_first_vwap is not None:
                assert abs(float(day2_first_vwap) - float(day2_first_open)) < 1.0

    @pytest.mark.asyncio
    async def test_session_rsi_calculation(self, mixed_session_data):
        """RSI should handle session gaps correctly."""
        session_filter = SessionFilterMixin()

        # Calculate RSI for RTH only
        rth_data = await session_filter.filter_by_session(
            mixed_session_data, SessionType.RTH, "ES"
        )

        rth_with_rsi = rth_data.pipe(RSI, period=14)

        assert "rsi_14" in rth_with_rsi.columns

        # RSI values should be between 0 and 100
        rsi_values = rth_with_rsi["rsi_14"].drop_nulls()
        assert all(0 <= val <= 100 for val in rsi_values)

        # Should handle overnight gaps without distortion
        # Check RSI continuity across session boundaries
        session_boundaries = find_session_boundaries(rth_with_rsi)
        for boundary in session_boundaries:
            # RSI shouldn't spike at boundaries
            before = float(rth_with_rsi["rsi_14"][boundary - 1])
            after = float(rth_with_rsi["rsi_14"][boundary + 1])
            assert abs(before - after) < 30  # No extreme jumps

    @pytest.mark.asyncio
    async def test_session_macd_signals(self, mixed_session_data):
        """MACD should generate signals based on session data."""
        session_filter = SessionFilterMixin()

        # RTH-only MACD
        rth_data = await session_filter.filter_by_session(
            mixed_session_data, SessionType.RTH, "ES"
        )

        rth_with_macd = rth_data.pipe(MACD, fast_period=12, slow_period=26, signal_period=9)

        assert "macd" in rth_with_macd.columns
        assert "macd_signal" in rth_with_macd.columns
        assert "macd_histogram" in rth_with_macd.columns

        # Signals should be based only on RTH data
        histogram = rth_with_macd["macd_histogram"].drop_nulls()
        assert len(histogram) > 0

    @pytest.mark.asyncio
    async def test_session_anchored_vwap(self):
        """Should support session-anchored VWAP."""
        # Create session data
        session_data = create_single_session_data()

        # Anchored VWAP from session open
        anchored_vwap = await calculate_anchored_vwap(
            session_data,
            anchor_point="session_open"
        )

        assert "anchored_vwap" in anchored_vwap.columns

        # First value should equal first price
        first_vwap = float(anchored_vwap["anchored_vwap"][0])
        first_price = float(session_data["close"][0])
        assert abs(first_vwap - first_price) < 0.01

        # VWAP should incorporate volume weighting
        last_vwap = float(anchored_vwap["anchored_vwap"][-1])
        simple_avg = float(session_data["close"].mean())
        assert abs(last_vwap - simple_avg) > 0.01  # Should differ due to volume weighting

    @pytest.mark.asyncio
    async def test_session_high_low_indicators(self, mixed_session_data):
        """Should track session highs and lows."""
        session_filter = SessionFilterMixin()

        # Get RTH data
        rth_data = await session_filter.filter_by_session(
            mixed_session_data, SessionType.RTH, "ES"
        )

        # Calculate session high/low
        with_session_levels = await calculate_session_levels(rth_data)

        assert "session_high" in with_session_levels.columns
        assert "session_low" in with_session_levels.columns
        assert "session_range" in with_session_levels.columns

        # Session high should be cumulative maximum within each session
        # Group by date to check within sessions
        dates = with_session_levels.with_columns(
            pl.col("timestamp").dt.date().alias("date")
        ).partition_by("date")

        for date_data in dates:
            if len(date_data) > 1:
                # Within a session, high should be cumulative maximum
                for i in range(1, len(date_data)):
                    current_high = float(date_data["session_high"][i])
                    prev_high = float(date_data["session_high"][i-1])
                    assert current_high >= prev_high

    @pytest.mark.asyncio
    async def test_session_volume_indicators(self, mixed_session_data):
        """Volume indicators should respect session boundaries."""
        session_filter = SessionFilterMixin()

        # RTH data only
        rth_data = await session_filter.filter_by_session(
            mixed_session_data, SessionType.RTH, "ES"
        )

        # Calculate cumulative volume by session
        with_cum_volume = await calculate_session_cumulative_volume(rth_data)

        assert "session_cumulative_volume" in with_cum_volume.columns

        # Should reset at session boundaries
        sessions = identify_sessions(with_cum_volume)
        for session_start in sessions:
            # First bar of session should have volume equal to its own volume
            first_cum = float(with_cum_volume["session_cumulative_volume"][session_start])
            first_vol = float(with_cum_volume["volume"][session_start])
            assert abs(first_cum - first_vol) < 1.0

    @pytest.mark.asyncio
    async def test_session_relative_indicators(self):
        """Should calculate indicators relative to session metrics."""
        session_data = create_single_session_data()

        # Calculate price relative to session VWAP
        relative_data = await calculate_relative_to_vwap(session_data)

        assert "price_vs_vwap" in relative_data.columns
        assert "vwap_deviation" in relative_data.columns

        # Calculate percentage from session open
        with_pct_change = await calculate_percent_from_open(session_data)

        assert "percent_from_open" in with_pct_change.columns

        # First bar should be 0% from open
        assert float(with_pct_change["percent_from_open"][0]) == 0.0


class TestSessionIndicatorIntegration:
    """Test integration of session indicators with data manager."""

    @pytest.mark.asyncio
    async def test_indicator_chain_with_sessions(self, mixed_session_data):
        """Should chain indicators on session-filtered data."""
        session_filter = SessionFilterMixin()

        # Filter to RTH
        rth_data = await session_filter.filter_by_session(
            mixed_session_data, SessionType.RTH, "ES"
        )

        # Chain multiple indicators
        with_indicators = (rth_data
            .pipe(SMA, period=20)
            .pipe(EMA, period=12)
            .pipe(RSI, period=14)
            .pipe(VWAP)
        )

        # All indicators should be present
        assert "sma_20" in with_indicators.columns
        assert "ema_12" in with_indicators.columns
        assert "rsi_14" in with_indicators.columns
        assert "vwap" in with_indicators.columns

        # No NaN values after warmup period
        after_warmup = with_indicators.tail(len(with_indicators) - 20)
        assert not after_warmup["sma_20"].has_nulls()

    @pytest.mark.asyncio
    async def test_multi_timeframe_session_indicators(self):
        """Should calculate indicators across multiple timeframes."""
        # Create 1-minute data
        minute_data = create_minute_data()

        # Aggregate to 5-minute maintaining session awareness
        five_min_data = await aggregate_with_sessions(
            minute_data,
            timeframe="5min",
            session_type=SessionType.RTH
        )

        # Calculate indicators on both timeframes
        minute_with_sma = minute_data.pipe(SMA, period=20)
        five_min_with_sma = five_min_data.pipe(SMA, period=20)

        # Both should have indicators
        assert "sma_20" in minute_with_sma.columns
        assert "sma_20" in five_min_with_sma.columns

        # 5-minute should have fewer bars
        assert len(five_min_data) < len(minute_data)

    @pytest.mark.asyncio
    async def test_session_indicator_alerts(self):
        """Should generate alerts based on session indicators."""
        session_data = create_single_session_data()

        # Calculate indicators
        with_indicators = session_data.pipe(SMA, period=10).pipe(RSI, period=14)

        # Generate alerts for session-specific conditions
        alerts = await generate_session_alerts(
            with_indicators,
            conditions={
                "above_sma": "close > sma_10",
                "overbought": "rsi_14 > 70",
                "session_high": "high == session_high"
            }
        )

        assert "alerts" in alerts.columns
        # Check if we have any alerts (handle None values)
        alerts_series = alerts["alerts"].drop_nulls()
        assert not alerts_series.is_empty()  # Should have some alerts


# Helper functions are imported from the actual implementation above
# No stub implementations needed - using real functions from sessions.indicators module
