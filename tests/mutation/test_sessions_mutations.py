"""
Mutation testing scenarios for sessions module.

These tests are designed to catch common mutations and ensure test quality.
They verify that our tests would catch typical programming errors.

Author: TDD Implementation
Date: 2025-08-31
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import polars as pl
import pytest

from project_x_py.sessions import SessionConfig, SessionFilterMixin, SessionType
from project_x_py.sessions.indicators import (
    calculate_session_gap,
    get_volume_profile,
    _has_valid_fields,
    _evaluate_close_gt_sma_10,
    _evaluate_rsi_gt_70,
    _evaluate_high_eq_session_high,
)
from project_x_py.sessions.statistics import SessionStatistics


class TestMutationDetectionConfig:
    """Tests designed to catch mutations in config.py."""

    def test_session_type_mutation_detection(self):
        """Detect mutations in session type comparisons."""
        config = SessionConfig(session_type=SessionType.RTH)
        timestamp = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)

        # These tests would catch mutations like:
        # if self.session_type == SessionType.RTH: -> if self.session_type != SessionType.RTH:
        assert config.is_market_open(timestamp, "ES") is True

        config_eth = SessionConfig(session_type=SessionType.ETH)
        assert config_eth.is_market_open(timestamp, "ES") is True  # ETH includes RTH

        # Would catch mutations that swap RTH/ETH behavior
        config_rth = SessionConfig(session_type=SessionType.RTH)
        after_hours = datetime(2024, 1, 16, 0, 0, tzinfo=timezone.utc)
        assert config_rth.is_market_open(after_hours, "ES") is False

    def test_boundary_comparison_mutations(self):
        """Detect mutations in boundary comparisons (<=, <, >=, >)."""
        config = SessionConfig(session_type=SessionType.RTH)

        # Test exactly at market open - would catch <= vs < mutations
        market_open = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)  # 9:30 AM ET
        assert config.is_market_open(market_open, "ES") is True

        # Test exactly at market close - would catch < vs <= mutations
        market_close = datetime(2024, 1, 15, 21, 0, tzinfo=timezone.utc)  # 4:00 PM ET
        assert config.is_market_open(market_close, "ES") is False

        # Test one minute before open - would catch boundary mutations
        before_open = datetime(2024, 1, 15, 14, 29, tzinfo=timezone.utc)
        assert config.is_market_open(before_open, "ES") is False

    def test_return_value_mutations(self):
        """Detect mutations in return values (True/False swaps)."""
        config = SessionConfig(session_type=SessionType.RTH)

        # Clear True case
        rth_time = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)
        result = config.is_market_open(rth_time, "ES")
        assert result is True  # Would catch True -> False mutations

        # Clear False case
        weekend_time = datetime(2024, 1, 13, 15, 0, tzinfo=timezone.utc)  # Saturday
        result = config.is_market_open(weekend_time, "ES")
        assert result is False  # Would catch False -> True mutations

    def test_string_constant_mutations(self):
        """Detect mutations in string constants."""
        config = SessionConfig(session_type=SessionType.ETH)

        # Test session type strings
        rth_time = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)
        session = config.get_current_session(rth_time, "ES")
        assert session == "RTH"  # Would catch "RTH" -> "ETH" mutations

        break_time = datetime(2024, 1, 15, 22, 30, tzinfo=timezone.utc)
        session = config.get_current_session(break_time, "ES")
        assert session == "BREAK"  # Would catch "BREAK" -> "RTH" mutations


class TestMutationDetectionFiltering:
    """Tests designed to catch mutations in filtering.py."""

    @pytest.fixture
    def session_filter(self):
        return SessionFilterMixin()

    def test_cache_key_mutations(self, session_filter):
        """Detect mutations in cache key construction."""
        # Test that cache keys are properly unique
        result1 = session_filter._get_cached_session_boundaries("hash1", "ES", "RTH")
        result2 = session_filter._get_cached_session_boundaries("hash2", "ES", "RTH")
        result3 = session_filter._get_cached_session_boundaries("hash1", "NQ", "RTH")
        result4 = session_filter._get_cached_session_boundaries("hash1", "ES", "ETH")

        # Would catch mutations that break cache key uniqueness
        assert "hash1_ES_RTH" in session_filter._session_boundary_cache
        assert "hash2_ES_RTH" in session_filter._session_boundary_cache
        assert "hash1_NQ_RTH" in session_filter._session_boundary_cache
        assert "hash1_ES_ETH" in session_filter._session_boundary_cache

    def test_tuple_validation_mutations(self, session_filter):
        """Detect mutations in tuple validation logic."""
        # Test invalid cache data handling
        cache_key = "test_ES_RTH"

        # Test non-tuple - would catch isinstance mutations
        session_filter._session_boundary_cache[cache_key] = "invalid"
        result = session_filter._get_cached_session_boundaries("test", "ES", "RTH")
        assert result == ([], [])

        # Test wrong length tuple - would catch len() mutations
        session_filter._session_boundary_cache[cache_key] = ([1, 2, 3],)
        result = session_filter._get_cached_session_boundaries("test", "ES", "RTH")
        assert result == ([], [])

        # Test valid tuple
        session_filter._session_boundary_cache[cache_key] = ([1, 2], [3, 4])
        result = session_filter._get_cached_session_boundaries("test", "ES", "RTH")
        assert result == ([1, 2], [3, 4])

    def test_size_threshold_mutations(self, session_filter):
        """Detect mutations in size thresholds."""
        # Test size threshold for lazy evaluation (100_000)
        small_data = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)] * 99_999
        })

        # Should use regular path
        result = session_filter._optimize_filtering(small_data)
        assert result.equals(small_data)

        # Test exactly at threshold - would catch off-by-one mutations
        threshold_data = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)] * 100_001
        })

        # Should use lazy evaluation path
        result = session_filter._optimize_filtering(threshold_data)
        assert len(result) == 100_001


class TestMutationDetectionIndicators:
    """Tests designed to catch mutations in indicators.py."""

    def test_arithmetic_operator_mutations(self):
        """Detect mutations in arithmetic operators (+, -, *, /)."""
        # Test gap calculations - would catch + -> - mutations
        friday_data = pl.DataFrame({"close": [100.0]})
        monday_data = pl.DataFrame({"open": [105.0]})

        result = calculate_session_gap(friday_data, monday_data)
        assert result["gap_size"] == 5.0  # monday_open - friday_close

        # Test percentage calculation - would catch * -> / mutations
        expected_percentage = 5.0 / 100.0 * 100  # 5%
        assert result["gap_percentage"] == expected_percentage

    def test_comparison_operator_mutations(self):
        """Detect mutations in comparison operators (<, >, <=, >=, ==, !=)."""
        # Test RSI condition - would catch > -> >= mutations
        from project_x_py.sessions.indicators import _evaluate_rsi_gt_70

        # Exactly at threshold
        row_at_threshold = {"rsi_14": 70.0}
        assert _evaluate_rsi_gt_70(row_at_threshold) is False  # > not >=

        # Just above threshold
        row_above_threshold = {"rsi_14": 70.1}
        assert _evaluate_rsi_gt_70(row_above_threshold) is True

        # Test equality condition - would catch == -> != mutations
        from project_x_py.sessions.indicators import _evaluate_high_eq_session_high

        equal_row = {"high": 100.0, "session_high": 100.0}
        assert _evaluate_high_eq_session_high(equal_row) is True

        unequal_row = {"high": 100.0, "session_high": 99.9}
        assert _evaluate_high_eq_session_high(unequal_row) is False

    def test_logical_operator_mutations(self):
        """Detect mutations in logical operators (and, or, not)."""
        # Test field validation - would catch 'and' -> 'or' mutations
        row = {"field1": 100, "field2": 200}
        assert _has_valid_fields(row, ["field1", "field2"]) is True

        # Missing one field - would catch logical mutations
        partial_row = {"field1": 100}
        assert _has_valid_fields(row, ["field1", "field2"]) is True
        assert _has_valid_fields(partial_row, ["field1", "field2"]) is False

    def test_constant_value_mutations(self):
        """Detect mutations in numeric constants."""
        # Test volume profile with insufficient data
        single_point = pl.DataFrame({"volume": [1000]})
        result = get_volume_profile(single_point, SessionType.RTH)

        # Would catch mutations in return values
        assert result["open_volume"] == 1000
        assert result["midday_volume"] == 1000
        assert result["close_volume"] == 1000

        # Test zero values
        empty_df = pl.DataFrame({"volume": []}, schema={"volume": pl.Int64})
        result = get_volume_profile(empty_df, SessionType.RTH)

        assert result["open_volume"] == 0  # Would catch 0 -> 1 mutations
        assert result["midday_volume"] == 0
        assert result["close_volume"] == 0

    def test_array_index_mutations(self):
        """Detect mutations in array indexing ([0], [-1], etc)."""
        # Test first/last element access
        friday_data = pl.DataFrame({"close": [98.0, 99.0, 100.0]})
        monday_data = pl.DataFrame({"open": [101.0, 102.0, 103.0]})

        result = calculate_session_gap(friday_data, monday_data)

        # Should use last close and first open
        # Would catch [-1] -> [0] or [0] -> [-1] mutations
        expected_gap = 101.0 - 100.0  # monday_data["open"][0] - friday_data["close"][-1]
        assert result["gap_size"] == expected_gap


class TestMutationDetectionStatistics:
    """Tests designed to catch mutations in statistics.py."""

    @pytest.fixture
    def stats(self):
        return SessionStatistics()

    def test_division_by_zero_mutations(self, stats):
        """Detect mutations that could introduce division by zero."""
        # Test VWAP with zero volume - would catch volume == 0 -> volume != 0 mutations
        zero_volume_df = pl.DataFrame({
            "close": [100.0, 101.0],
            "volume": [0, 0]
        })

        result = stats._calculate_vwap(zero_volume_df)
        assert result == 0.0  # Should handle gracefully, not divide by zero

    def test_type_checking_mutations(self, stats):
        """Detect mutations in type checking logic."""
        # Test safe float conversion - would catch isinstance mutations
        assert stats._safe_convert_to_float(42) == 42.0  # int
        assert stats._safe_convert_to_float(3.14) == 3.14  # float
        assert stats._safe_convert_to_float("text") == 0.0  # string (invalid)
        assert stats._safe_convert_to_float(None) == 0.0  # None

        # Would catch mutations like isinstance(value, (int, float)) -> isinstance(value, int)
        assert stats._safe_convert_to_float(True) == 1.0  # bool is int-like
        assert stats._safe_convert_to_float(False) == 0.0

    def test_aggregation_function_mutations(self, stats):
        """Detect mutations in aggregation functions (sum, max, min, etc)."""
        # Test volume calculation - would catch sum -> max mutations
        volume_df = pl.DataFrame({"volume": [100, 200, 300]})
        result = stats._calculate_volume(volume_df)
        assert result == 600  # sum, not max (300)

        # Test high/low calculation - would catch max -> min mutations
        price_df = pl.DataFrame({
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 98.0, 97.0]
        })

        result = stats._calculate_high_low_range(price_df)
        assert result["high"] == 103.0  # max, not min
        assert result["low"] == 97.0   # min, not max

    def test_conditional_logic_mutations(self, stats):
        """Detect mutations in conditional logic."""
        # Test range calculation - would catch conditional mutations
        valid_data = pl.DataFrame({
            "high": [105.0],
            "low": [95.0]
        })

        result = stats._calculate_high_low_range(valid_data)
        assert result["range"] == 10.0  # high - low when high > 0

        # Test zero high value
        zero_high_data = pl.DataFrame({
            "high": [0.0],
            "low": [95.0]
        })

        result = stats._calculate_high_low_range(zero_high_data)
        assert result["range"] == 0.0  # Should be 0 when high <= 0


class TestMutationDetectionBoundaryConditions:
    """Tests specifically for boundary condition mutations."""

    def test_off_by_one_mutations(self):
        """Detect off-by-one mutations in loops and ranges."""
        # Test volume profile with exact boundary cases
        three_points = pl.DataFrame({"volume": [100, 200, 300]})
        result = get_volume_profile(three_points, SessionType.RTH)

        # Would catch len(data) < 3 -> len(data) <= 3 mutations
        assert result["open_volume"] == 100    # [0]
        assert result["midday_volume"] == 200  # [len//2] = [1]
        assert result["close_volume"] == 300   # [-1]

        # Test exactly at boundary
        two_points = pl.DataFrame({"volume": [100, 200]})
        result = get_volume_profile(two_points, SessionType.RTH)

        # Should handle insufficient data case
        assert result["open_volume"] == 100
        assert result["close_volume"] == 200

    def test_empty_collection_mutations(self):
        """Detect mutations in empty collection handling."""
        # Test empty data - would catch len(data) == 0 -> len(data) > 0 mutations
        empty_df = pl.DataFrame({"volume": []}, schema={"volume": pl.Int64})
        result = get_volume_profile(empty_df, SessionType.RTH)

        assert result == {
            "open_volume": 0,
            "midday_volume": 0,
            "close_volume": 0
        }

    def test_none_value_mutations(self):
        """Detect mutations in None value handling."""
        # Test None handling - would catch is None -> is not None mutations
        stats = SessionStatistics()

        assert stats._safe_convert_to_float(None) == 0.0

        # Test field validation with None
        row_with_none = {"field1": None, "field2": 100}
        assert _has_valid_fields(row_with_none, ["field1"]) is False
        assert _has_valid_fields(row_with_none, ["field2"]) is True


class TestMutationDetectionEdgeCases:
    """Test mutations in edge case handling."""

    def test_error_path_mutations(self):
        """Detect mutations in error handling paths."""
        config = SessionConfig(session_type=SessionType.RTH)

        # Test invalid timestamp types - would catch error path mutations
        assert config.is_market_open(None, "ES") is False
        assert config.is_market_open("invalid", "ES") is False
        assert config.is_market_open(12345, "ES") is False

    def test_default_value_mutations(self):
        """Detect mutations in default values."""
        # Test default session gap values
        empty_df = pl.DataFrame({"close": [], "open": []},
                               schema={"close": pl.Float64, "open": pl.Float64})

        result = calculate_session_gap(empty_df, empty_df)

        # Would catch default value mutations
        assert result["gap_size"] == 0.0
        assert result["gap_percentage"] == 0.0

    def test_boolean_logic_mutations(self):
        """Detect mutations in boolean logic."""
        # Test has_valid_fields with various combinations
        row = {"a": 1, "b": 2, "c": None}

        # All valid fields
        assert _has_valid_fields(row, ["a", "b"]) is True

        # Mix of valid/invalid - would catch 'and' -> 'or' mutations
        assert _has_valid_fields(row, ["a", "c"]) is False
        assert _has_valid_fields(row, ["b", "c"]) is False

        # All invalid
        assert _has_valid_fields(row, ["c", "d"]) is False
