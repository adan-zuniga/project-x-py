"""Tests for orderbook analytics static methods."""

import polars as pl
import pytest

from project_x_py.orderbook import MarketAnalytics


class TestMarketAnalyticsStaticMethods:
    """Test static methods in MarketAnalytics class."""

    def test_analyze_dataframe_spread_basic(self):
        """Test basic spread analysis functionality."""
        # Create test data
        data = pl.DataFrame(
            {
                "bid": [100.0, 100.1, 100.2, 100.3],
                "ask": [100.2, 100.3, 100.4, 100.5],
            }
        )

        result = MarketAnalytics.analyze_dataframe_spread(data)

        # Check structure
        assert isinstance(result, dict)
        assert "avg_spread" in result
        assert "median_spread" in result
        assert "min_spread" in result
        assert "max_spread" in result
        assert "spread_volatility" in result
        assert "avg_relative_spread" in result

        # Check values
        assert pytest.approx(result["avg_spread"], 0.001) == 0.2
        assert pytest.approx(result["min_spread"], 0.001) == 0.2
        assert pytest.approx(result["max_spread"], 0.001) == 0.2
        assert result["spread_volatility"] == 0.0

    def test_analyze_dataframe_spread_with_mid(self):
        """Test spread analysis with automatic mid price calculation."""
        data = pl.DataFrame(
            {
                "bid": [100.0, 100.1, 100.2],
                "ask": [100.2, 100.3, 100.4],
            }
        )

        result = MarketAnalytics.analyze_dataframe_spread(
            data,
            bid_column="bid",
            ask_column="ask",
            mid_column=None,  # Let it calculate mid price
        )

        # Should calculate spread correctly
        assert pytest.approx(result["avg_spread"], 0.001) == 0.2
        # Average mid price is (100.1 + 100.2 + 100.3) / 3 = 100.2
        assert pytest.approx(result["avg_relative_spread"], 0.0001) == 0.2 / 100.2

    def test_analyze_dataframe_spread_empty(self):
        """Test spread analysis with empty DataFrame."""
        data = pl.DataFrame(
            {
                "bid": [],
                "ask": [],
            }
        )

        result = MarketAnalytics.analyze_dataframe_spread(data)

        # Should return error for empty data
        assert "error" in result
        assert result["error"] == "No data provided"

    def test_analyze_dataframe_spread_custom_columns(self):
        """Test spread analysis with custom column names."""
        data = pl.DataFrame(
            {
                "best_bid": [100.0, 100.1],
                "best_ask": [100.2, 100.3],
            }
        )

        result = MarketAnalytics.analyze_dataframe_spread(
            data, bid_column="best_bid", ask_column="best_ask"
        )

        assert pytest.approx(result["avg_spread"], 0.001) == 0.2

    def test_analyze_dataframe_spread_missing_columns(self):
        """Test spread analysis with missing columns."""
        data = pl.DataFrame(
            {
                "price": [100.0, 100.1],
            }
        )

        with pytest.raises(ValueError):  # Should raise when columns don't exist
            MarketAnalytics.analyze_dataframe_spread(data)
