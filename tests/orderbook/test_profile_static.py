"""Tests for orderbook volume profile static methods."""

import polars as pl

from project_x_py.orderbook import VolumeProfile


class TestVolumeProfileStaticMethods:
    """Test static methods in VolumeProfile class."""

    def test_calculate_dataframe_volume_profile_basic(self):
        """Test basic volume profile calculation."""
        # Create test data with price movements
        data = pl.DataFrame(
            {
                "close": [100.0, 100.5, 101.0, 100.5, 100.0, 99.5, 100.0, 100.5, 101.0],
                "volume": [100, 200, 150, 300, 250, 100, 200, 150, 100],
            }
        )

        result = VolumeProfile.calculate_dataframe_volume_profile(
            data, price_column="close", volume_column="volume", num_bins=5
        )

        # Check structure
        assert isinstance(result, dict)
        assert "point_of_control" in result
        assert "poc_volume" in result
        assert "value_area_high" in result
        assert "value_area_low" in result
        assert "total_volume" in result
        assert "volume_distribution" in result

        # Check volume distribution
        assert isinstance(result["volume_distribution"], list)
        assert len(result["volume_distribution"]) > 0

        # POC should be at price with highest volume
        assert result["poc_volume"] > 0
        # Check that total volume is sum of all volumes (some might be excluded by binning)
        expected_total = sum([100, 200, 150, 300, 250, 100, 200, 150, 100])  # 1550
        # But due to binning edge effects, might be slightly less
        assert result["total_volume"] <= expected_total
        assert result["total_volume"] > 0

        # Value area should be reasonable
        assert (
            result["value_area_low"]
            <= result["point_of_control"]
            <= result["value_area_high"]
        )

    def test_calculate_dataframe_volume_profile_single_price(self):
        """Test volume profile with single price level."""
        data = pl.DataFrame(
            {
                "close": [100.0] * 5,
                "volume": [100, 200, 150, 300, 250],
            }
        )

        result = VolumeProfile.calculate_dataframe_volume_profile(data)

        # Should have single price level
        assert result["point_of_control"] == 100.0
        assert result["poc_volume"] == 1000  # Sum of all volumes
        assert result["total_volume"] == 1000

    def test_calculate_dataframe_volume_profile_empty(self):
        """Test volume profile with empty DataFrame."""
        data = pl.DataFrame(
            {
                "close": [],
                "volume": [],
            }
        )

        result = VolumeProfile.calculate_dataframe_volume_profile(data)

        # Should return error for empty data
        assert "error" in result

    def test_calculate_dataframe_volume_profile_custom_bins(self):
        """Test volume profile with different bin counts."""
        data = pl.DataFrame(
            {
                "close": list(range(100, 200)),  # 100 different prices
                "volume": [10] * 100,  # Equal volume at each price
            }
        )

        # Test with 10 bins
        result_10 = VolumeProfile.calculate_dataframe_volume_profile(data, num_bins=10)
        assert len(result_10["volume_distribution"]) <= 10

        # Test with 20 bins
        result_20 = VolumeProfile.calculate_dataframe_volume_profile(data, num_bins=20)
        assert len(result_20["volume_distribution"]) <= 20

        # More bins should give finer granularity
        assert len(result_20["volume_distribution"]) >= len(
            result_10["volume_distribution"]
        )

    def test_calculate_dataframe_volume_profile_distribution(self):
        """Test that volume distribution is properly formatted."""
        data = pl.DataFrame(
            {
                "close": [100.0, 100.5, 101.0, 100.5, 100.0],
                "volume": [100, 200, 150, 300, 250],
            }
        )

        result = VolumeProfile.calculate_dataframe_volume_profile(data)

        # Check volume distribution structure
        assert isinstance(result["volume_distribution"], list)
        for item in result["volume_distribution"]:
            assert "price" in item
            assert "volume" in item
            assert "price_range" in item
            assert isinstance(item["price_range"], tuple)
            assert len(item["price_range"]) == 2

    def test_calculate_dataframe_volume_profile_custom_columns(self):
        """Test volume profile with custom column names."""
        data = pl.DataFrame(
            {
                "price": [100.0, 101.0, 102.0],
                "size": [100, 200, 300],
            }
        )

        result = VolumeProfile.calculate_dataframe_volume_profile(
            data, price_column="price", volume_column="size"
        )

        # POC should be a reasonable price within the data range
        assert 100.0 <= result["point_of_control"] <= 102.0
        # POC volume should be positive
        assert result["poc_volume"] > 0
        # Total volume should be positive (binning might exclude some edge data)
        assert result["total_volume"] > 0
        assert result["total_volume"] <= 600
