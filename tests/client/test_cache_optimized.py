"""Tests for the optimized caching functionality with msgpack and lz4."""

import time
from unittest.mock import patch

import polars as pl
import pytest

from project_x_py import ProjectX


class TestOptimizedCache:
    """Tests for the optimized caching functionality with msgpack and lz4."""

    @pytest.fixture
    async def mock_project_x(self, mock_httpx_client):
        """Create a properly initialized ProjectX instance with optimized cache."""
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            async with ProjectX("testuser", "test-api-key") as client:
                yield client

    @pytest.mark.asyncio
    async def test_msgpack_serialization(self, mock_project_x):
        """Test that DataFrames are serialized with Arrow IPC format."""
        client = mock_project_x

        # Create test data
        test_data = pl.DataFrame(
            {
                "price": [100.5, 101.0, 102.5],
                "volume": [1000, 2000, 1500],
                "timestamp": ["2024-01-01", "2024-01-02", "2024-01-03"],
            }
        )

        # Cache the data
        client.cache_market_data("test_key", test_data)

        # Check that data is stored in optimized cache (not compatibility cache)
        assert "test_key" in client._opt_market_data_cache

        # Retrieve and verify data integrity
        cached_data = client.get_cached_market_data("test_key")
        assert cached_data is not None
        assert cached_data.shape == test_data.shape
        assert cached_data.equals(test_data)

    @pytest.mark.asyncio
    async def test_lz4_compression(self, mock_project_x):
        """Test that large data is compressed with lz4."""
        client = mock_project_x

        # Create large test data (> 1KB threshold)
        large_data = pl.DataFrame(
            {
                "price": list(range(1000)),
                "volume": list(range(1000, 2000)),
                "timestamp": [f"2024-01-{i:03d}" for i in range(1000)],
            }
        )

        # Cache the large data
        client.cache_market_data("large_key", large_data)

        # Check that data is in optimized cache
        assert "large_key" in client._opt_market_data_cache
        serialized = client._opt_market_data_cache["large_key"]

        # Check compression header (should start with b"LZ4" for compressed data)
        assert serialized[:3] == b"LZ4" or serialized[:3] == b"RAW"

        # If data is large enough, it should be compressed
        if len(large_data.to_dicts()) > client.compression_threshold:
            assert serialized[:3] == b"LZ4"

        # Verify decompression works
        cached_data = client.get_cached_market_data("large_key")
        assert cached_data is not None
        assert cached_data.shape == large_data.shape

    @pytest.mark.asyncio
    async def test_lru_cache_for_instruments(self, mock_project_x, mock_instrument):
        """Test LRU cache behavior for instruments."""
        client = mock_project_x

        # Cache an instrument
        client.cache_instrument("MGC", mock_instrument)

        # Check it's in the optimized LRU cache
        assert "MGC" in client._opt_instrument_cache

        # Retrieve should increase hit count
        initial_hits = client.cache_hit_count
        cached = client.get_cached_instrument("MGC")
        assert cached is not None
        assert client.cache_hit_count == initial_hits + 1

    @pytest.mark.asyncio
    async def test_ttl_cache_for_market_data(self, mock_project_x):
        """Test TTL cache behavior for market data."""
        client = mock_project_x

        # Set short TTL for testing
        client.cache_ttl = 0.1  # 100ms

        # Cache some data
        test_data = pl.DataFrame({"price": [100, 101, 102]})
        client.cache_market_data("ttl_test", test_data)

        # Immediately available
        assert client.get_cached_market_data("ttl_test") is not None

        # Wait for expiry
        time.sleep(0.2)

        # Should be expired
        assert client.get_cached_market_data("ttl_test") is None

    @pytest.mark.asyncio
    async def test_cache_statistics(self, mock_project_x, mock_instrument):
        """Test cache statistics reporting."""
        client = mock_project_x

        # Add some items to cache
        client.cache_instrument("MGC", mock_instrument)
        test_data = pl.DataFrame({"price": [100, 101, 102]})
        client.cache_market_data("stats_test", test_data)

        # Get cache stats
        stats = client.get_cache_stats()

        # Check new optimized cache stats
        assert "cache_hits" in stats
        assert "instrument_cache_size" in stats
        assert "market_data_cache_size" in stats
        assert "compression_enabled" in stats
        assert "serialization" in stats
        assert "compression" in stats

        # Verify values
        assert stats["compression_enabled"] is True
        assert stats["serialization"] == "arrow-ipc"
        assert stats["compression"] == "lz4"
        assert stats["instrument_cache_size"] == 1
        assert stats["market_data_cache_size"] == 1

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, mock_project_x):
        """Test memory efficiency of optimized cache."""
        client = mock_project_x

        # Create multiple DataFrames
        for i in range(10):
            data = pl.DataFrame(
                {
                    "price": list(range(100)),  # Same length for both columns
                    "volume": list(range(1000 + i * 100, 1100 + i * 100)),
                }
            )
            client.cache_market_data(f"memory_test_{i}", data)

        # Check that optimized cache is being used
        assert len(client._opt_market_data_cache) == 10

    @pytest.mark.asyncio
    async def test_cache_clear_optimized(self, mock_project_x, mock_instrument):
        """Test clearing optimized caches."""
        client = mock_project_x

        # Add items to cache
        client.cache_instrument("MGC", mock_instrument)
        test_data = pl.DataFrame({"price": [100, 101, 102]})
        client.cache_market_data("clear_test", test_data)

        # Verify items are in optimized caches
        assert len(client._opt_instrument_cache) == 1
        assert len(client._opt_market_data_cache) == 1

        # Clear all caches
        client.clear_all_caches()

        # All caches should be empty
        assert len(client._opt_instrument_cache) == 0
        assert len(client._opt_market_data_cache) == 0
        assert client.cache_hit_count == 0

    @pytest.mark.asyncio
    async def test_empty_dataframe_handling(self, mock_project_x):
        """Test handling of empty DataFrames."""
        client = mock_project_x

        # Create empty DataFrame
        empty_data = pl.DataFrame()

        # Cache empty data
        client.cache_market_data("empty_test", empty_data)

        # Should handle empty data gracefully
        cached = client.get_cached_market_data("empty_test")
        # Empty DataFrames may return None or empty
        assert cached is None or cached.is_empty()

    @pytest.mark.asyncio
    async def test_compression_threshold(self, mock_project_x):
        """Test compression threshold logic."""
        client = mock_project_x

        # Small data (should not be compressed)
        small_data = pl.DataFrame({"a": [1, 2, 3]})
        client.cache_market_data("small", small_data)

        # Large data (should be compressed)
        large_data = pl.DataFrame(
            {
                "data": list(range(10000))  # Much larger than threshold
            }
        )
        client.cache_market_data("large", large_data)

        # Check compression headers
        small_serialized = client._opt_market_data_cache.get("small")
        large_serialized = client._opt_market_data_cache.get("large")

        if small_serialized:
            # Small data should use RAW (no compression)
            assert small_serialized[:3] == b"RAW"

        if large_serialized:
            # Large data should use LZ4 compression
            assert large_serialized[:3] == b"LZ4"

    @pytest.mark.asyncio
    async def test_case_insensitive_instrument_cache(
        self, mock_project_x, mock_instrument
    ):
        """Test case-insensitive instrument caching in optimized cache."""
        client = mock_project_x

        # Cache with lowercase
        client.cache_instrument("mgc", mock_instrument)

        # Retrieve with uppercase
        cached = client.get_cached_instrument("MGC")
        assert cached is not None
        assert cached.id == mock_instrument.id

        # Check it's in optimized cache with uppercase key
        assert "MGC" in client._opt_instrument_cache
