"""Tests for the caching functionality of ProjectX client."""

import time
from unittest.mock import patch

import polars as pl
import pytest

from project_x_py import ProjectX


class TestCache:
    """Tests for the caching functionality of the ProjectX client."""

    @pytest.fixture
    async def mock_project_x(self, mock_httpx_client):
        """Create a properly initialized ProjectX instance with cache attributes."""
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            async with ProjectX("testuser", "test-api-key") as client:
                # Client now has optimized cache initialized in __init__
                yield client

    @pytest.mark.asyncio
    async def test_instrument_cache(self, mock_project_x, mock_instrument):
        """Test instrument caching."""
        client = mock_project_x

        # Initially cache is empty
        cached_instrument = client.get_cached_instrument("MGC")
        assert cached_instrument is None

        # Add to cache
        client.cache_instrument("MGC", mock_instrument)

        # Should return from cache now
        cached_instrument = client.get_cached_instrument("MGC")
        assert cached_instrument is not None
        assert cached_instrument.id == mock_instrument.id
        assert cached_instrument.name == mock_instrument.name

    @pytest.mark.asyncio
    async def test_instrument_cache_case_insensitive(
        self, mock_project_x, mock_instrument
    ):
        """Test instrument cache is case insensitive."""
        client = mock_project_x

        # Add to cache with one case
        client.cache_instrument("mgc", mock_instrument)

        # Should return from cache with different case
        cached_instrument = client.get_cached_instrument("MGC")
        assert cached_instrument is not None
        assert cached_instrument.name == mock_instrument.name

    @pytest.mark.asyncio
    async def test_market_data_cache(self, mock_project_x):
        """Test market data caching."""
        client = mock_project_x

        # Create test data
        test_data = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        # Initially cache is empty
        cached_data = client.get_cached_market_data("test_key")
        assert cached_data is None

        # Add to cache
        client.cache_market_data("test_key", test_data)

        # Should return from cache now
        cached_data = client.get_cached_market_data("test_key")
        assert cached_data is not None
        assert cached_data.shape == test_data.shape
        assert cached_data.equals(test_data)

    @pytest.mark.asyncio
    async def test_cache_expiration(self, mock_project_x, mock_instrument):
        """Test cache expiration."""
        client = mock_project_x

        # Set a short TTL for testing
        client.cache_ttl = 0.1  # 100ms

        # Add to cache
        client.cache_instrument("MGC", mock_instrument)
        test_data = pl.DataFrame({"a": [1, 2, 3]})
        client.cache_market_data("test_key", test_data)

        # Immediately should be in cache
        assert client.get_cached_instrument("MGC") is not None
        assert client.get_cached_market_data("test_key") is not None

        # Wait for expiry
        time.sleep(0.2)

        # Should be expired now
        assert client.get_cached_instrument("MGC") is None
        assert client.get_cached_market_data("test_key") is None

    @pytest.mark.asyncio
    async def test_cache_cleanup(self, mock_project_x, mock_instrument):
        """Test cache cleanup logic."""
        client = mock_project_x

        # Set a short TTL for testing
        client.cache_ttl = 0.1  # 100ms

        # Add multiple items to cache
        client.cache_instrument("MGC", mock_instrument)
        client.cache_instrument("MNQ", mock_instrument)

        test_data = pl.DataFrame({"a": [1, 2, 3]})
        client.cache_market_data("key1", test_data)
        client.cache_market_data("key2", test_data)

        # Wait for expiry
        time.sleep(0.2)

        # TTLCache automatically expires items - no manual cleanup needed
        # Check that items have expired
        assert client.get_cached_instrument("MGC") is None
        assert client.get_cached_instrument("MNQ") is None
        assert client.get_cached_market_data("key1") is None
        assert client.get_cached_market_data("key2") is None

    @pytest.mark.asyncio
    async def test_clear_all_caches(self, mock_project_x, mock_instrument):
        """Test clearing all caches."""
        client = mock_project_x

        # Add items to cache
        client.cache_instrument("MGC", mock_instrument)
        test_data = pl.DataFrame({"a": [1, 2, 3]})
        client.cache_market_data("test_key", test_data)

        # Verify items are in cache
        assert len(client._opt_instrument_cache) == 1
        assert len(client._opt_market_data_cache) == 1

        # Clear all caches
        client.clear_all_caches()

        # Cache should be empty
        assert len(client._opt_instrument_cache) == 0
        assert len(client._opt_market_data_cache) == 0

    @pytest.mark.asyncio
    async def test_cache_hit_tracking(self, mock_project_x, mock_instrument):
        """Test cache hit tracking."""
        client = mock_project_x

        # Initial hit count
        initial_hits = client.cache_hit_count

        # Add to cache
        client.cache_instrument("MGC", mock_instrument)
        test_data = pl.DataFrame({"a": [1, 2, 3]})
        client.cache_market_data("test_key", test_data)

        # Get from cache multiple times
        client.get_cached_instrument("MGC")
        client.get_cached_instrument("MGC")
        client.get_cached_market_data("test_key")

        # Hit count should increase by 3
        assert client.cache_hit_count == initial_hits + 3

        # Miss shouldn't increment counter
        client.get_cached_instrument("UNKNOWN")
        assert client.cache_hit_count == initial_hits + 3
