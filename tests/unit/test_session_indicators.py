"""
Tests for session-aware technical indicators.

These tests define the EXPECTED behavior for indicators that respect
trading sessions (RTH vs ETH). Following strict TDD methodology.

Author: TDD Implementation
Date: 2025-08-28
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import polars as pl
import pytest

from project_x_py.indicators import EMA, MACD, RSI, SMA, VWAP
from project_x_py.sessions import SessionConfig, SessionFilterMixin, SessionType
from project_x_py.sessions.indicators import (
    aggregate_with_sessions,
    calculate_anchored_vwap,
    calculate_percent_from_open,
    calculate_relative_to_vwap,
    calculate_session_cumulative_volume,
    calculate_session_gap,
    calculate_session_levels,
    calculate_session_vwap,
    generate_session_alerts,
    get_session_performance_metrics,
    get_volume_profile,
    _create_minute_data,
    _create_single_session_data,
    _find_session_boundaries,
    _identify_sessions,
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
        session_boundaries = _find_session_boundaries(rth_with_rsi)
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
        session_data = _create_single_session_data()

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
        sessions = _identify_sessions(with_cum_volume)
        for session_start in sessions:
            # First bar of session should have volume equal to its own volume
            first_cum = float(with_cum_volume["session_cumulative_volume"][session_start])
            first_vol = float(with_cum_volume["volume"][session_start])
            assert abs(first_cum - first_vol) < 1.0

    @pytest.mark.asyncio
    async def test_session_relative_indicators(self):
        """Should calculate indicators relative to session metrics."""
        session_data = _create_single_session_data()

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
        minute_data = _create_minute_data()

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
        session_data = _create_single_session_data()

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


class TestSessionIndicatorsEdgeCases:
    """Test edge cases and uncovered lines in indicators.py."""

    @pytest.mark.asyncio
    async def test_calculate_session_vwap_empty_dataframe(self):
        """Test calculate_session_vwap with empty DataFrame."""
        empty_df = pl.DataFrame({
            "timestamp": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": []
        }, schema={
            "timestamp": pl.Datetime(time_zone="UTC"),
            "open": pl.Float64,
            "high": pl.Float64,
            "low": pl.Float64,
            "close": pl.Float64,
            "volume": pl.Int64
        })

        result = await calculate_session_vwap(empty_df, SessionType.RTH, "ES")

        assert len(result) == 0
        assert "session_vwap" in result.columns

    def test_find_session_boundaries_empty_data(self):
        """Test _find_session_boundaries with empty DataFrame."""
        empty_df = pl.DataFrame({
            "timestamp": []
        }, schema={"timestamp": pl.Datetime(time_zone="UTC")})

        boundaries = _find_session_boundaries(empty_df)
        assert boundaries == []

    def test_find_session_boundaries_multi_session(self):
        """Test _find_session_boundaries with multiple sessions."""
        multi_session = pl.DataFrame({
            "timestamp": [
                datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc),  # Day 1
                datetime(2024, 1, 15, 16, 0, tzinfo=timezone.utc),  # Day 1
                datetime(2024, 1, 16, 15, 0, tzinfo=timezone.utc),  # Day 2 - boundary
                datetime(2024, 1, 16, 16, 0, tzinfo=timezone.utc),  # Day 2
                datetime(2024, 1, 17, 15, 0, tzinfo=timezone.utc),  # Day 3 - boundary
            ]
        })

        boundaries = _find_session_boundaries(multi_session)
        # Should find boundaries at indices 2 and 4 (start of new days)
        assert boundaries == [2, 4]

    def test_create_single_session_data_structure(self):
        """Test _create_single_session_data returns correct structure."""
        data = _create_single_session_data()

        # Should have 390 rows (6.5 hours * 60 minutes)
        assert len(data) == 390

        # Should have all OHLCV columns
        expected_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        assert set(data.columns) == set(expected_columns)

        # Should have proper data types
        assert data["timestamp"].dtype == pl.Datetime(time_zone="UTC")

        # Prices should be ascending
        opens = data["open"].to_list()
        assert opens[0] < opens[-1]

    def test_identify_sessions_empty_data(self):
        """Test _identify_sessions with empty DataFrame."""
        empty_df = pl.DataFrame({
            "timestamp": []
        }, schema={"timestamp": pl.Datetime(time_zone="UTC")})

        sessions = _identify_sessions(empty_df)
        assert sessions == []

    def test_identify_sessions_single_row(self):
        """Test _identify_sessions with single row."""
        single_row = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)]
        })

        sessions = _identify_sessions(single_row)
        # First row is always a session start
        assert sessions == [0]

    @pytest.mark.asyncio
    async def test_calculate_anchored_vwap_empty_data(self):
        """Test calculate_anchored_vwap with empty DataFrame."""
        empty_df = pl.DataFrame({
            "timestamp": [],
            "close": [],
            "volume": []
        }, schema={
            "timestamp": pl.Datetime(time_zone="UTC"),
            "close": pl.Float64,
            "volume": pl.Int64
        })

        result = await calculate_anchored_vwap(empty_df, "session_open")

        assert len(result) == 0
        assert "anchored_vwap" in result.columns

    @pytest.mark.asyncio
    async def test_calculate_anchored_vwap_unknown_anchor(self):
        """Test calculate_anchored_vwap with unknown anchor point."""
        data = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)],
            "close": [100.0],
            "volume": [1000]
        })

        result = await calculate_anchored_vwap(data, "unknown_anchor")

        # Should return original data without anchored_vwap column
        assert result.equals(data)
        assert "anchored_vwap" not in result.columns

    @pytest.mark.asyncio
    async def test_generate_session_alerts_empty_data(self):
        """Test generate_session_alerts with empty DataFrame."""
        empty_df = pl.DataFrame({
            "close": [],
            "sma_10": [],
            "rsi_14": []
        }, schema={
            "close": pl.Float64,
            "sma_10": pl.Float64,
            "rsi_14": pl.Float64
        })

        conditions = {"breakout": "close > sma_10"}
        result = await generate_session_alerts(empty_df, conditions)

        assert len(result) == 0
        assert "alerts" in result.columns

    @pytest.mark.asyncio
    async def test_generate_session_alerts_no_conditions(self):
        """Test generate_session_alerts with no conditions."""
        data = pl.DataFrame({
            "close": [100.0, 101.0],
            "sma_10": [99.0, 100.0]
        })

        result = await generate_session_alerts(data, {})

        assert len(result) == 2
        assert "alerts" in result.columns
        # Should have None values for alerts when no conditions
        alerts = result["alerts"].to_list()
        assert all(alert is None for alert in alerts)

    def test_calculate_session_gap_empty_data(self):
        """Test calculate_session_gap with empty DataFrames."""
        empty_df = pl.DataFrame({
            "close": [],
            "open": []
        }, schema={"close": pl.Float64, "open": pl.Float64})

        # Both empty
        result = calculate_session_gap(empty_df, empty_df)
        assert result == {"gap_size": 0.0, "gap_percentage": 0.0}

    def test_calculate_session_gap_zero_friday_close(self):
        """Test calculate_session_gap with zero Friday close."""
        friday_data = pl.DataFrame({"close": [0.0]})
        monday_data = pl.DataFrame({"open": [100.0]})

        result = calculate_session_gap(friday_data, monday_data)

        assert result["gap_size"] == 100.0
        assert result["gap_percentage"] == 0.0  # Avoid division by zero

    def test_get_volume_profile_empty_data(self):
        """Test get_volume_profile with empty DataFrame."""
        empty_df = pl.DataFrame({
            "volume": []
        }, schema={"volume": pl.Int64})

        result = get_volume_profile(empty_df, SessionType.RTH)

        expected = {"open_volume": 0, "midday_volume": 0, "close_volume": 0}
        assert result == expected

    def test_get_volume_profile_insufficient_data(self):
        """Test get_volume_profile with insufficient data points."""
        # Test with 1 data point
        single_point = pl.DataFrame({"volume": [1000]})
        result = get_volume_profile(single_point, SessionType.RTH)

        assert result["open_volume"] == 1000
        assert result["midday_volume"] == 1000
        assert result["close_volume"] == 1000

    def test_get_session_performance_metrics_none_data(self):
        """Test get_session_performance_metrics with None data."""
        result = get_session_performance_metrics(None)

        expected_keys = ["rth_tick_rate", "eth_tick_rate", "rth_data_quality", "session_efficiency"]
        for key in expected_keys:
            assert key in result
            assert isinstance(result[key], float)

    def test_get_session_performance_metrics_single_point(self):
        """Test get_session_performance_metrics with single data point."""
        single_point = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)]
        })

        result = get_session_performance_metrics(single_point)

        # Should return default metrics (can't calculate rate with single point)
        assert result["rth_tick_rate"] == 0.0


class TestSessionIndicatorsConditionEvaluators:
    """Test condition evaluators and alert generation edge cases."""

    def test_evaluate_close_gt_sma_10_missing_fields(self):
        """Test _evaluate_close_gt_sma_10 with missing fields."""
        from project_x_py.sessions.indicators import _evaluate_close_gt_sma_10

        # Missing close
        row = {"sma_10": 100.0}
        assert _evaluate_close_gt_sma_10(row) is False

        # Missing sma_10
        row = {"close": 101.0}
        assert _evaluate_close_gt_sma_10(row) is False

        # None values
        row = {"close": None, "sma_10": 100.0}
        assert _evaluate_close_gt_sma_10(row) is False

    def test_evaluate_close_gt_sma_10_valid_conditions(self):
        """Test _evaluate_close_gt_sma_10 with valid conditions."""
        from project_x_py.sessions.indicators import _evaluate_close_gt_sma_10

        # True condition
        row = {"close": 101.0, "sma_10": 100.0}
        assert _evaluate_close_gt_sma_10(row) is True

        # False condition
        row = {"close": 99.0, "sma_10": 100.0}
        assert _evaluate_close_gt_sma_10(row) is False

    def test_has_valid_fields_edge_cases(self):
        """Test _has_valid_fields helper function."""
        from project_x_py.sessions.indicators import _has_valid_fields

        # Empty row
        assert _has_valid_fields({}, ["field1"]) is False

        # Missing field
        row = {"field1": 100}
        assert _has_valid_fields(row, ["field2"]) is False

        # None value
        row = {"field1": None}
        assert _has_valid_fields(row, ["field1"]) is False

        # Valid field
        row = {"field1": 100, "field2": 200}
        assert _has_valid_fields(row, ["field1", "field2"]) is True


class TestSessionIndicatorsConcurrentAccess:
    """Test concurrent access patterns for indicators."""

    @pytest.mark.asyncio
    async def test_concurrent_vwap_calculations(self):
        """Test concurrent VWAP calculations don't interfere."""
        import asyncio

        data = _create_single_session_data()

        async def calc_vwap():
            return await calculate_session_vwap(data, SessionType.RTH, "ES")

        # Run multiple concurrent calculations
        tasks = [calc_vwap() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.equals(first_result)
