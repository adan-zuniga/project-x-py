"""
In-memory caching for instrument and market data with TTL and performance tracking.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides efficient, per-symbol in-memory caching for instrument metadata and historical
    market data. Uses time-based TTL (time-to-live) for automatic expiry and memory cleanup,
    reducing API load and improving performance for frequently accessed symbols. Includes
    cache hit counters and periodic cleanup for resource optimization within async clients.

Key Features:
    - Fast cache for instrument lookups (symbol → instrument)
    - Market data caching for historical bar queries (string key → Polars DataFrame)
    - Configurable TTL (default 5 minutes) to automatically expire stale data
    - Performance metrics: cache hit count and cleanup timing
    - Async cache cleanup and garbage collection for large workloads
    - Manual cache clearing utilities

Example Usage:
    ```python
    # Used internally by ProjectX; typical use is transparent:
    instrument = await client.get_instrument("MNQ")
    # On repeated calls, instrument is served from cache if not expired.
    cached = client.get_cached_instrument("MNQ")
    client.clear_all_caches()
    ```

See Also:
    - `project_x_py.client.market_data.MarketDataMixin`
    - `project_x_py.client.base.ProjectXBase`
    - `project_x_py.client.http.HttpMixin`
"""

import gc
import logging
import time
from typing import TYPE_CHECKING

import polars as pl

from project_x_py.models import Instrument

if TYPE_CHECKING:
    from project_x_py.types import ProjectXClientProtocol

logger = logging.getLogger(__name__)


class CacheMixin:
    """Mixin class providing caching functionality."""

    def __init__(self) -> None:
        """Initialize cache attributes."""
        super().__init__()
        # Cache for instrument data (symbol -> instrument)
        self._instrument_cache: dict[str, Instrument] = {}
        self._instrument_cache_time: dict[str, float] = {}

        # Cache for market data
        self._market_data_cache: dict[str, pl.DataFrame] = {}
        self._market_data_cache_time: dict[str, float] = {}

        # Cache cleanup tracking
        self.cache_ttl = 300  # 5 minutes default
        self.last_cache_cleanup = time.time()

        # Performance monitoring
        self.cache_hit_count = 0

    async def _cleanup_cache(self: "ProjectXClientProtocol") -> None:
        """
        Clean up expired cache entries to manage memory usage.

        This method removes expired entries from both instrument and market data caches
        based on the configured TTL (time-to-live). It helps prevent unbounded memory
        growth during long-running sessions by:

        1. Removing instrument cache entries that have exceeded their TTL
        2. Removing market data cache entries that have exceeded their TTL
        3. Triggering garbage collection when a significant number of entries are removed

        The method is called periodically during normal API operations and updates
        the last_cache_cleanup timestamp to track when cleanup was last performed.
        """
        current_time = time.time()

        # Clean instrument cache
        expired_instruments = [
            symbol
            for symbol, cache_time in self._instrument_cache_time.items()
            if current_time - cache_time > self.cache_ttl
        ]
        for symbol in expired_instruments:
            del self._instrument_cache[symbol]
            del self._instrument_cache_time[symbol]

        # Clean market data cache
        expired_data = [
            key
            for key, cache_time in self._market_data_cache_time.items()
            if current_time - cache_time > self.cache_ttl
        ]
        for key in expired_data:
            del self._market_data_cache[key]
            del self._market_data_cache_time[key]

        self.last_cache_cleanup = current_time

        # Force garbage collection if caches were large
        if len(expired_instruments) > 10 or len(expired_data) > 10:
            gc.collect()

    def get_cached_instrument(self, symbol: str) -> Instrument | None:
        """
        Get cached instrument data if available and not expired.

        Args:
            symbol: Trading symbol

        Returns:
            Cached instrument or None if not found/expired
        """
        cache_key = symbol.upper()
        if cache_key in self._instrument_cache:
            cache_age = time.time() - self._instrument_cache_time.get(cache_key, 0)
            if cache_age < self.cache_ttl:
                self.cache_hit_count += 1
                return self._instrument_cache[cache_key]
        return None

    def cache_instrument(self, symbol: str, instrument: Instrument) -> None:
        """
        Cache instrument data.

        Args:
            symbol: Trading symbol
            instrument: Instrument object to cache
        """
        cache_key = symbol.upper()
        self._instrument_cache[cache_key] = instrument
        self._instrument_cache_time[cache_key] = time.time()

    def get_cached_market_data(self, cache_key: str) -> pl.DataFrame | None:
        """
        Get cached market data if available and not expired.

        Args:
            cache_key: Unique key for the cached data

        Returns:
            Cached DataFrame or None if not found/expired
        """
        if cache_key in self._market_data_cache:
            cache_age = time.time() - self._market_data_cache_time.get(cache_key, 0)
            if cache_age < self.cache_ttl:
                self.cache_hit_count += 1
                return self._market_data_cache[cache_key]
        return None

    def cache_market_data(self, cache_key: str, data: pl.DataFrame) -> None:
        """
        Cache market data.

        Args:
            cache_key: Unique key for the data
            data: DataFrame to cache
        """
        self._market_data_cache[cache_key] = data
        self._market_data_cache_time[cache_key] = time.time()

    def clear_all_caches(self) -> None:
        """Clear all cached data."""
        self._instrument_cache.clear()
        self._instrument_cache_time.clear()
        self._market_data_cache.clear()
        self._market_data_cache_time.clear()
        gc.collect()
