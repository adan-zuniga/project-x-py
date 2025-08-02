"""Caching functionality for ProjectX client."""

import gc
import logging
import time
from typing import TYPE_CHECKING

import polars as pl

from project_x_py.models import Instrument

if TYPE_CHECKING:
    from project_x_py.client.protocols import ProjectXClientProtocol

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
        """Clean up expired cache entries."""
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
