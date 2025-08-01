"""
Async Level 2 Orderbook module for ProjectX.

This module provides comprehensive asynchronous orderbook analysis including:
- Real-time Level 2 market depth tracking
- Iceberg order detection
- Order clustering analysis
- Volume profile analysis
- Support/resistance identification
- Trade flow analytics
- Market microstructure metrics

Example:
    Basic usage with real-time data::

        >>> from project_x_py import AsyncProjectX, create_async_orderbook
        >>> import asyncio
        >>>
        >>> async def main():
        ...     client = AsyncProjectX()
        ...     await client.connect()
        ...
        ...     orderbook = await create_async_orderbook(
        ...         instrument="MNQ",
        ...         project_x=client,
        ...         realtime_client=client.realtime_client
        ...     )
        ...
        ...     # Get orderbook snapshot
        ...     snapshot = await orderbook.get_orderbook_snapshot()
        ...     print(f"Best Bid: {snapshot['best_bid']}")
        ...     print(f"Best Ask: {snapshot['best_ask']}")
        ...
        ...     # Detect iceberg orders
        ...     icebergs = await orderbook.detect_iceberg_orders()
        ...     for iceberg in icebergs:
        ...         print(f"Potential iceberg at {iceberg['price']}")
        >>>
        >>> asyncio.run(main())
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_x_py.async_client import AsyncProjectX
    from project_x_py.async_realtime import AsyncProjectXRealtimeClient

import logging

from .analytics import MarketAnalytics
from .base import AsyncOrderBookBase
from .detection import OrderDetection
from .memory import MemoryManager
from .profile import VolumeProfile
from .realtime import RealtimeHandler
from .types import (
    DEFAULT_TIMEZONE,
    AsyncCallback,
    CallbackType,
    DomType,
    IcebergConfig,
    MarketDataDict,
    MemoryConfig,
    OrderbookSide,
    OrderbookSnapshot,
    PriceLevelDict,
    SyncCallback,
    TradeDict,
)

__all__ = [
    # Types
    "AsyncCallback",
    "AsyncOrderBook",
    "CallbackType",
    "DomType",
    "IcebergConfig",
    "MarketDataDict",
    "MemoryConfig",
    "OrderbookSide",
    "OrderbookSnapshot",
    "PriceLevelDict",
    "SyncCallback",
    "TradeDict",
    "create_async_orderbook",
]


class AsyncOrderBook(AsyncOrderBookBase):
    """
    Async Level 2 Orderbook with comprehensive market analysis.

    This class combines all orderbook functionality into a single interface,
    including real-time data handling, analytics, detection algorithms,
    and volume profiling.
    """

    def __init__(
        self,
        instrument: str,
        project_x: "AsyncProjectX | None" = None,
        timezone_str: str = DEFAULT_TIMEZONE,
    ):
        """
        Initialize the async orderbook.

        Args:
            instrument: Trading instrument symbol
            project_x: Optional ProjectX client for tick size lookup
            timezone_str: Timezone for timestamps (default: America/Chicago)
        """
        super().__init__(instrument, project_x, timezone_str)

        # Initialize components
        self.realtime_handler = RealtimeHandler(self)
        self.analytics = MarketAnalytics(self)
        self.detection = OrderDetection(self)
        self.profile = VolumeProfile(self)

        self.logger = logging.getLogger(__name__)

    async def initialize(
        self,
        realtime_client: "AsyncProjectXRealtimeClient | None" = None,
        subscribe_to_depth: bool = True,
        subscribe_to_quotes: bool = True,
    ) -> bool:
        """
        Initialize the orderbook with optional real-time data feed.

        Args:
            realtime_client: Async real-time client for WebSocket data
            subscribe_to_depth: Subscribe to market depth updates
            subscribe_to_quotes: Subscribe to quote updates

        Returns:
            bool: True if initialization successful
        """
        try:
            # Start memory manager
            await self.memory_manager.start()

            # Initialize real-time connection if provided
            if realtime_client:
                success = await self.realtime_handler.initialize(
                    realtime_client, subscribe_to_depth, subscribe_to_quotes
                )
                if not success:
                    self.logger.error("Failed to initialize real-time connection")
                    return False

            self.logger.info(f"AsyncOrderBook initialized for {self.instrument}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize AsyncOrderBook: {e}")
            return False

    # Delegate analytics methods
    async def get_market_imbalance(self, levels: int = 10) -> dict[str, Any]:
        """Calculate order flow imbalance between bid and ask sides."""
        return await self.analytics.get_market_imbalance(levels)

    async def get_orderbook_depth(self, price_range: float) -> dict[str, Any]:
        """Analyze orderbook depth within a price range."""
        return await self.analytics.get_orderbook_depth(price_range)

    async def get_cumulative_delta(
        self, time_window_minutes: int = 60
    ) -> dict[str, Any]:
        """Get cumulative delta (buy volume - sell volume) over time window."""
        return await self.analytics.get_cumulative_delta(time_window_minutes)

    async def get_trade_flow_summary(self) -> dict[str, Any]:
        """Get comprehensive trade flow statistics."""
        return await self.analytics.get_trade_flow_summary()

    async def get_liquidity_levels(
        self, min_volume: int = 100, levels: int = 20
    ) -> dict[str, Any]:
        """Identify significant liquidity levels in the orderbook."""
        return await self.analytics.get_liquidity_levels(min_volume, levels)

    async def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive orderbook statistics."""
        return await self.analytics.get_statistics()

    # Delegate detection methods
    async def detect_iceberg_orders(
        self,
        min_refreshes: int | None = None,
        volume_threshold: int | None = None,
        time_window_minutes: int | None = None,
    ) -> dict[str, Any]:
        """Detect potential iceberg orders based on price level refresh patterns."""
        return await self.detection.detect_iceberg_orders(
            min_refreshes, volume_threshold, time_window_minutes
        )

    async def detect_order_clusters(
        self, min_cluster_size: int = 3, price_tolerance: float = 0.1
    ) -> list[dict[str, Any]]:
        """Detect clusters of orders at similar price levels."""
        return await self.detection.detect_order_clusters(
            min_cluster_size, price_tolerance
        )

    async def get_advanced_market_metrics(self) -> dict[str, Any]:
        """Calculate advanced market microstructure metrics."""
        return await self.detection.get_advanced_market_metrics()

    # Delegate profile methods
    async def get_volume_profile(
        self, time_window_minutes: int = 60, price_bins: int = 20
    ) -> dict[str, Any]:
        """Calculate volume profile showing volume distribution by price."""
        return await self.profile.get_volume_profile(time_window_minutes, price_bins)

    async def get_support_resistance_levels(
        self,
        lookback_minutes: int = 120,
        min_touches: int = 3,
        price_tolerance: float = 0.1,
    ) -> dict[str, Any]:
        """Identify support and resistance levels based on price history."""
        return await self.profile.get_support_resistance_levels(
            lookback_minutes, min_touches, price_tolerance
        )

    async def get_spread_analysis(self, window_minutes: int = 30) -> dict[str, Any]:
        """Analyze bid-ask spread patterns over time."""
        return await self.profile.get_spread_analysis(window_minutes)

    # Delegate memory methods
    async def get_memory_stats(self) -> dict[str, Any]:
        """Get comprehensive memory usage statistics."""
        return await self.memory_manager.get_memory_stats()

    async def cleanup(self) -> None:
        """Clean up resources and disconnect from real-time feeds."""
        # Disconnect real-time
        if self.realtime_handler.is_connected:
            await self.realtime_handler.disconnect()

        # Stop memory manager
        await self.memory_manager.stop()

        # Call parent cleanup
        await super().cleanup()


def create_async_orderbook(
    instrument: str,
    project_x: "AsyncProjectX | None" = None,
    realtime_client: "AsyncProjectXRealtimeClient | None" = None,
    timezone_str: str = DEFAULT_TIMEZONE,
) -> AsyncOrderBook:
    """
    Factory function to create an async orderbook.

    Args:
        instrument: Trading instrument symbol
        project_x: Optional ProjectX client for tick size lookup
        realtime_client: Optional real-time client for WebSocket data
        timezone_str: Timezone for timestamps

    Returns:
        AsyncOrderBook: Orderbook instance (call initialize() separately)

    Example:
        >>> orderbook = create_async_orderbook(
        ...     "MNQ", project_x=client, realtime_client=realtime_client
        ... )
        >>> await orderbook.initialize(realtime_client)
    """
    # Note: realtime_client is passed to initialize() separately to allow
    # for async initialization
    _ = realtime_client  # Mark as intentionally unused
    return AsyncOrderBook(instrument, project_x, timezone_str)
