"""
Async Level 2 Orderbook module for ProjectX.

This module provides comprehensive asynchronous orderbook analysis with real-time
capabilities for institutional-grade market microstructure analysis. It offers a
complete suite of tools for deep market understanding and strategy development.

Core Functionality:
- Real-time Level 2 market depth tracking with WebSocket integration
- Advanced iceberg order detection with confidence scoring
- Order clustering analysis for institutional activity detection
- Volume profile analysis with Point of Control and Value Area
- Dynamic support/resistance level identification
- Detailed trade flow analytics and execution classification
- Memory-efficient data management with configurable cleanup policies
- Complete market microstructure metrics with imbalance detection

Technical Features:
- Thread-safe concurrent access with asyncio locks
- Polars DataFrame-based data structures for performance
- Configurable memory management with automatic garbage collection
- Event-driven architecture with customizable callbacks
- Component-based design for maintainability and extensibility

Example:
    Basic usage with real-time data::

        >>> from project_x_py import ProjectX, create_orderbook
        >>> import asyncio
        >>>
        >>> async def main():
        ...     # Initialize client and connect
        ...     client = ProjectX()
        ...     await client.connect()
        ...
        ...     # Create orderbook with factory function
        ...     orderbook = create_orderbook(
        ...         instrument="MNQ",  # Micro Nasdaq futures
        ...         project_x=client,
        ...         timezone_str="America/Chicago"
        ...     )
        ...
        ...     # Initialize with real-time data feed
        ...     await orderbook.initialize(
        ...         realtime_client=client.realtime_client,
        ...         subscribe_to_depth=True,
        ...         subscribe_to_quotes=True
        ...     )
        ...
        ...     # Get current orderbook snapshot
        ...     snapshot = await orderbook.get_orderbook_snapshot(levels=10)
        ...     print(f"Best Bid: {snapshot['best_bid']}")
        ...     print(f"Best Ask: {snapshot['best_ask']}")
        ...     print(f"Spread: {snapshot['spread']}")
        ...     print(f"Bid/Ask Imbalance: {snapshot['imbalance']}")
        ...
        ...     # Detect iceberg orders
        ...     icebergs = await orderbook.detect_iceberg_orders(min_refreshes=5)
        ...     for iceberg in icebergs['iceberg_levels']:
        ...         print(f"Potential iceberg at {iceberg['price']} with "
        ...               f"{iceberg['confidence']:.1%} confidence")
        ...
        ...     # Analyze market imbalance
        ...     imbalance = await orderbook.get_market_imbalance(levels=10)
        ...     print(f"Market imbalance: {imbalance['imbalance_ratio']:.2f} "
        ...           f"({imbalance['analysis']})")
        ...
        ...     # Register a callback for order book updates
        ...     async def on_depth_update(data):
        ...         print(f"New depth update at {data['price']}, "
        ...               f"volume: {data['volume']}")
        ...
        ...     await orderbook.add_callback("depth_update", on_depth_update)
        ...
        ...     # Clean up resources when done
        ...     await orderbook.cleanup()
        >>>
        >>> asyncio.run(main())
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_x_py.client import ProjectXBase
    from project_x_py.realtime import ProjectXRealtimeClient

import logging

from project_x_py.orderbook.analytics import MarketAnalytics
from project_x_py.orderbook.base import OrderBookBase
from project_x_py.orderbook.detection import OrderDetection
from project_x_py.orderbook.memory import MemoryManager
from project_x_py.orderbook.profile import VolumeProfile
from project_x_py.orderbook.realtime import RealtimeHandler
from project_x_py.orderbook.types import (
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
    "CallbackType",
    "DomType",
    "IcebergConfig",
    "MarketDataDict",
    "MemoryConfig",
    "OrderBook",
    "OrderbookSide",
    "OrderbookSnapshot",
    "PriceLevelDict",
    "SyncCallback",
    "TradeDict",
    "create_orderbook",
]


class OrderBook(OrderBookBase):
    """
    Async Level 2 Orderbook with comprehensive market analysis.

    This class combines all orderbook functionality into a single interface,
    providing a unified API for accessing real-time market depth data, advanced
    analytics, detection algorithms, and volume profiling. It uses a component-based
    architecture where specialized functionality is delegated to dedicated components
    while maintaining a simple, cohesive interface for the client code.

    Key Components:
        - realtime_handler: Manages WebSocket connections and real-time data processing
        - analytics: Provides market analytics (imbalance, depth, delta, liquidity)
        - detection: Implements detection algorithms (iceberg, clusters)
        - profile: Handles volume profiling and support/resistance analysis
        - memory_manager: Manages memory usage and cleanup tasks

    Thread Safety:
        All methods are thread-safe and can be called concurrently from multiple
        asyncio tasks. Data consistency is maintained through internal locks.

    Memory Management:
        The orderbook implements automatic memory management through the MemoryManager
        component, which periodically cleans up historical data based on configurable
        parameters to prevent memory leaks during long-running sessions.

    Example:
        >>> orderbook = OrderBook("ES", project_x_client)
        >>> await orderbook.initialize(realtime_client)
        >>>
        >>> # Get basic orderbook data
        >>> snapshot = await orderbook.get_orderbook_snapshot()
        >>> print(f"Spread: {snapshot['spread']}")
        >>>
        >>> # Advanced analytics
        >>> imbalance = await orderbook.get_market_imbalance()
        >>> liquidity = await orderbook.get_liquidity_levels()
        >>>
        >>> # Detection algorithms
        >>> icebergs = await orderbook.detect_iceberg_orders()
        >>> clusters = await orderbook.detect_order_clusters()
        >>>
        >>> # Cleanup when done
        >>> await orderbook.cleanup()
    """

    def __init__(
        self,
        instrument: str,
        project_x: "ProjectXBase | None" = None,
        timezone_str: str = DEFAULT_TIMEZONE,
    ):
        """
        Initialize the orderbook.

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
        realtime_client: "ProjectXRealtimeClient | None" = None,
        subscribe_to_depth: bool = True,
        subscribe_to_quotes: bool = True,
    ) -> bool:
        """
        Initialize the orderbook with optional real-time data feed.

        This method configures the orderbook for operation, sets up the memory manager,
        and optionally connects to the real-time data feed. It must be called after
        creating an OrderBook instance and before using any other methods.

        The initialization process performs the following steps:
        1. Starts the memory manager for automatic cleanup
        2. If a realtime_client is provided:
           - Registers callbacks for market depth and quote updates
           - Subscribes to the specified data channels
           - Sets up WebSocket connection handlers

        Args:
            realtime_client: Async real-time client for WebSocket data. If provided,
                the orderbook will receive live market data updates. If None, the
                orderbook will function in historical/static mode only.
            subscribe_to_depth: Subscribe to market depth updates (Level 2 data).
                Set to False only if you don't need full order book data.
            subscribe_to_quotes: Subscribe to quote updates (top of book data).
                Set to False only if you don't need quote data.

        Returns:
            bool: True if initialization successful, False if any part of the
                initialization failed.

        Example:
            >>> orderbook = OrderBook("MNQ", client)
            >>> success = await orderbook.initialize(
            ...     realtime_client=client.realtime_client,
            ...     subscribe_to_depth=True,
            ...     subscribe_to_quotes=True,
            ... )
            >>> if success:
            ...     print("Orderbook initialized and receiving real-time data")
            ... else:
            ...     print("Failed to initialize orderbook")
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

            self.logger.info(f"OrderBook initialized for {self.instrument}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize OrderBook: {e}")
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


def create_orderbook(
    instrument: str,
    project_x: "ProjectXBase | None" = None,
    realtime_client: "ProjectXRealtimeClient | None" = None,
    timezone_str: str = DEFAULT_TIMEZONE,
) -> OrderBook:
    """
    Factory function to create an orderbook.

    This factory function creates and returns an OrderBook instance for the specified
    instrument. It simplifies the process of creating an orderbook by handling the initial
    configuration. Note that the returned orderbook is not yet initialized - you must call
    the initialize() method separately to start the orderbook's functionality.

    The factory approach provides several benefits:
    1. Ensures consistent orderbook creation across the application
    2. Allows for future extension with pre-configured orderbook variants
    3. Simplifies the API for common use cases

    Args:
        instrument: Trading instrument symbol (e.g., "ES", "NQ", "MES", "MNQ").
            This should be the base symbol without contract-specific extensions.
        project_x: Optional AsyncProjectX client for tick size lookup and API access.
            If provided, the orderbook will be able to look up tick sizes and other
            contract details automatically.
        realtime_client: Optional real-time client for WebSocket data. This is kept
            for compatibility but should be passed to initialize() instead.
        timezone_str: Timezone for timestamps (default: "America/Chicago").
            All timestamps in the orderbook will be converted to this timezone.

    Returns:
        OrderBook: Orderbook instance that must be initialized with a call
        to initialize() before use.

    Example:
        >>> # Create an orderbook for E-mini S&P 500 futures
        >>> orderbook = create_orderbook(
        ...     instrument="ES",  # E-mini S&P 500
        ...     project_x=client,
        ...     timezone_str="America/New_York",
        ... )
        >>>
        >>> # Initialize with real-time data
        >>> await orderbook.initialize(realtime_client=client.realtime_client)
        >>>
        >>> # Start using the orderbook
        >>> snapshot = await orderbook.get_orderbook_snapshot()
    """
    # Note: realtime_client is passed to initialize() separately to allow
    # for async initialization
    _ = realtime_client  # Mark as intentionally unused
    return OrderBook(instrument, project_x, timezone_str)
