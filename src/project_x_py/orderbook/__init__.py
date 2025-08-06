"""
Async Level 2 orderbook toolkit for ProjectX.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides a complete async suite for Level 2 orderbook analysis, real-time market
    microstructure, and market depth analytics. Integrates with ProjectX for
    institutional-grade trading, strategy development, and execution research.

Key Features:
    - Real-time Level 2 market depth tracking (WebSocket)
    - Iceberg/cluster detection, volume profile, and POC analytics
    - Market imbalance, support/resistance, and trade flow stats
    - Memory-efficient, thread-safe, event-driven architecture
    - Component-based design for extensibility
    - Advanced market microstructure analysis
    - Comprehensive trade flow classification
    - Automatic memory management and cleanup

Orderbook Components:
    - Base OrderBook: Core data structures and thread-safe operations
    - Market Analytics: Imbalance, depth, delta, and liquidity analysis
    - Order Detection: Iceberg orders, clusters, and hidden liquidity detection
    - Volume Profile: Support/resistance levels and volume distribution
    - Memory Manager: Automatic cleanup and memory optimization
    - Realtime Handler: WebSocket integration and real-time data processing

Real-time Capabilities:
    - WebSocket-based Level 2 market depth updates
    - Immediate trade execution detection and classification
    - Real-time spread and price level monitoring
    - Event-driven callback system for custom logic
    - Automatic data validation and error handling

Example Usage:
    ```python
    # V3: Uses EventBus and factory functions
    from project_x_py import ProjectX, create_orderbook, create_realtime_client
    from project_x_py.events import EventBus, EventType
    import asyncio


    async def main():
        # V3: ProjectX client with context manager
        async with ProjectX.from_env() as client:
            await client.authenticate()

            # V3: Create realtime client with factory function
            realtime_client = await create_realtime_client(
                jwt_token=client.jwt_token, account_id=str(client.account_id)
            )

            # V3: EventBus for unified event handling
            event_bus = EventBus()

            # V3: Create orderbook with EventBus
            orderbook = create_orderbook(
                "MNQ",  # V3: Using actual contract symbols
                event_bus=event_bus,
                project_x=client,
            )
            await orderbook.initialize(realtime_client=realtime_client)

            # V3: Register event handlers
            @event_bus.on(EventType.MARKET_DEPTH_UPDATE)
            async def on_depth_update(data):
                print(f"Depth update: {data['timestamp']}")

            # Get basic orderbook snapshot
            snapshot = await orderbook.get_orderbook_snapshot(levels=10)
            print(f"Best bid: {snapshot['best_bid']}, Spread: {snapshot['spread']}")

            # Advanced analytics
            imbalance = await orderbook.get_market_imbalance(levels=5)
            print(f"Market imbalance: {imbalance['imbalance_ratio']:.2f}")

            # Detection algorithms
            icebergs = await orderbook.detect_iceberg_orders()
            print(f"Detected {len(icebergs['iceberg_levels'])} iceberg orders")

            await orderbook.cleanup()


    asyncio.run(main())
    ```

See Also:
    - `orderbook.base.OrderBookBase`
    - `orderbook.analytics.MarketAnalytics`
    - `orderbook.detection.OrderDetection`
    - `orderbook.profile.VolumeProfile`
    - `orderbook.memory.MemoryManager`
    - `orderbook.realtime.RealtimeHandler`
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
from project_x_py.types import (
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
from project_x_py.types.config_types import OrderbookConfig
from project_x_py.types.response_types import (
    LiquidityAnalysisResponse,
    MarketImpactResponse,
    OrderbookAnalysisResponse,
)
from project_x_py.types.stats_types import OrderbookStats

__all__ = [
    # Types
    "AsyncCallback",
    "CallbackType",
    "DomType",
    "IcebergConfig",
    # Analytics components
    "MarketAnalytics",
    "MarketDataDict",
    "MemoryConfig",
    "OrderBook",
    "OrderbookSide",
    "OrderbookSnapshot",
    "PriceLevelDict",
    "SyncCallback",
    "TradeDict",
    # Profile components
    "VolumeProfile",
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

    Real-time Features:
        - WebSocket-based Level 2 market depth updates
        - Immediate trade execution detection and classification
        - Real-time spread and price level monitoring
        - Event-driven callback system for custom logic
        - Automatic data validation and error handling

    Analytics Capabilities:
        - Market imbalance analysis and ratio calculations
        - Orderbook depth analysis within price ranges
        - Cumulative delta tracking and trade flow statistics
        - Liquidity level identification and concentration analysis
        - Comprehensive orderbook statistics and health metrics

    Detection Algorithms:
        - Iceberg order detection with confidence scoring
        - Order clustering analysis for institutional activity
        - Advanced market microstructure metrics
        - Hidden liquidity and volume pattern recognition

    Example:
        >>> # V3: Create orderbook with EventBus
        >>> event_bus = EventBus()
        >>> orderbook = OrderBook("MNQ", event_bus, project_x_client)
        >>> await orderbook.initialize(realtime_client)
        >>>
        >>> # V3: Register event handlers
        >>> @event_bus.on(EventType.MARKET_DEPTH_UPDATE)
        >>> async def handle_depth(data):
        ...     print(f"Depth: {data['bids'][0]['price']} @ {data['bids'][0]['size']}")
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
        >>> # Volume profiling
        >>> profile = await orderbook.get_volume_profile()
        >>> support_resistance = await orderbook.get_support_resistance_levels()
        >>>
        >>> # Cleanup when done
        >>> await orderbook.cleanup()
    """

    def __init__(
        self,
        instrument: str,
        event_bus: Any,
        project_x: "ProjectXBase | None" = None,
        timezone_str: str = DEFAULT_TIMEZONE,
        config: "OrderbookConfig | None" = None,
    ):
        """
        Initialize the orderbook.

        Args:
            instrument: Trading instrument symbol
            event_bus: EventBus instance for unified event handling. Required for all
                event emissions including market depth updates and trade ticks.
            project_x: Optional ProjectX client for tick size lookup
            timezone_str: Timezone for timestamps (default: America/Chicago)
            config: Optional configuration for orderbook behavior
        """
        super().__init__(instrument, event_bus, project_x, timezone_str, config)

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
            >>> # V3: Initialize with EventBus and realtime client
            >>> event_bus = EventBus()
            >>> orderbook = OrderBook("MNQ", event_bus, client)
            >>> # V3: Create realtime client with factory
            >>> realtime_client = await create_realtime_client(
            ...     jwt_token=client.jwt_token, account_id=str(client.account_id)
            ... )
            >>> success = await orderbook.initialize(
            ...     realtime_client=realtime_client,
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
    async def get_market_imbalance(self, levels: int = 10) -> LiquidityAnalysisResponse:
        """
        Calculate order flow imbalance between bid and ask sides.

        Delegates to MarketAnalytics.get_market_imbalance().
        See MarketAnalytics.get_market_imbalance() for complete documentation.
        """
        return await self.analytics.get_market_imbalance(levels)

    async def get_orderbook_depth(self, price_range: float) -> MarketImpactResponse:
        """
        Analyze orderbook depth within a price range.

        Delegates to MarketAnalytics.get_orderbook_depth().
        See MarketAnalytics.get_orderbook_depth() for complete documentation.
        """
        return await self.analytics.get_orderbook_depth(price_range)

    async def get_cumulative_delta(
        self, time_window_minutes: int = 60
    ) -> dict[str, Any]:
        """
        Get cumulative delta (buy volume - sell volume) over time window.

        Delegates to MarketAnalytics.get_cumulative_delta().
        See MarketAnalytics.get_cumulative_delta() for complete documentation.
        """
        return await self.analytics.get_cumulative_delta(time_window_minutes)

    async def get_trade_flow_summary(self) -> dict[str, Any]:
        """
        Get comprehensive trade flow statistics.

        Delegates to MarketAnalytics.get_trade_flow_summary().
        See MarketAnalytics.get_trade_flow_summary() for complete documentation.
        """
        return await self.analytics.get_trade_flow_summary()

    async def get_liquidity_levels(
        self, min_volume: int = 100, levels: int = 20
    ) -> dict[str, Any]:
        """
        Identify significant liquidity levels in the orderbook.

        Delegates to MarketAnalytics.get_liquidity_levels().
        See MarketAnalytics.get_liquidity_levels() for complete documentation.
        """
        return await self.analytics.get_liquidity_levels(min_volume, levels)

    async def get_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive orderbook statistics.

        Delegates to MarketAnalytics.get_statistics().
        See MarketAnalytics.get_statistics() for complete documentation.
        """
        return await self.analytics.get_statistics()

    # Delegate detection methods
    async def detect_iceberg_orders(
        self,
        min_refreshes: int | None = None,
        volume_threshold: int | None = None,
        time_window_minutes: int | None = None,
    ) -> dict[str, Any]:
        """
        Detect potential iceberg orders based on price level refresh patterns.

        Delegates to OrderDetection.detect_iceberg_orders().
        See OrderDetection.detect_iceberg_orders() for complete documentation.
        """
        return await self.detection.detect_iceberg_orders(
            min_refreshes, volume_threshold, time_window_minutes
        )

    async def detect_order_clusters(
        self, min_cluster_size: int = 3, price_tolerance: float = 0.1
    ) -> list[dict[str, Any]]:
        """
        Detect clusters of orders at similar price levels.

        Delegates to OrderDetection.detect_order_clusters().
        See OrderDetection.detect_order_clusters() for complete documentation.
        """
        return await self.detection.detect_order_clusters(
            min_cluster_size, price_tolerance
        )

    async def get_advanced_market_metrics(self) -> OrderbookAnalysisResponse:
        """
        Calculate advanced market microstructure metrics.

        Delegates to OrderDetection.get_advanced_market_metrics().
        See OrderDetection.get_advanced_market_metrics() for complete documentation.
        """
        return await self.detection.get_advanced_market_metrics()

    # Delegate profile methods
    async def get_volume_profile(
        self, time_window_minutes: int = 60, price_bins: int = 20
    ) -> dict[str, Any]:
        """
        Calculate volume profile showing volume distribution by price.

        Delegates to VolumeProfile.get_volume_profile().
        See VolumeProfile.get_volume_profile() for complete documentation.
        """
        return await self.profile.get_volume_profile(time_window_minutes, price_bins)

    async def get_support_resistance_levels(
        self,
        lookback_minutes: int = 120,
        min_touches: int = 3,
        price_tolerance: float = 0.1,
    ) -> dict[str, Any]:
        """
        Identify support and resistance levels based on price history.

        Delegates to VolumeProfile.get_support_resistance_levels().
        See VolumeProfile.get_support_resistance_levels() for complete documentation.
        """
        return await self.profile.get_support_resistance_levels(
            lookback_minutes, min_touches, price_tolerance
        )

    async def get_spread_analysis(
        self, window_minutes: int = 30
    ) -> LiquidityAnalysisResponse:
        """
        Analyze bid-ask spread patterns over time.

        Delegates to VolumeProfile.get_spread_analysis().
        See VolumeProfile.get_spread_analysis() for complete documentation.
        """
        return await self.profile.get_spread_analysis(window_minutes)

    # Delegate memory methods
    async def get_memory_stats(self) -> OrderbookStats:
        """
        Get comprehensive memory usage statistics.

        Delegates to MemoryManager.get_memory_stats().
        See MemoryManager.get_memory_stats() for complete documentation.
        """
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
    event_bus: Any,
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
        >>> # V3: Create an orderbook with EventBus
        >>> event_bus = EventBus()
        >>> orderbook = create_orderbook(
        ...     instrument="MNQ",  # V3: Using actual contract symbols
        ...     event_bus=event_bus,
        ...     project_x=client,
        ...     timezone_str="America/Chicago",  # V3: Using CME timezone
        ... )
        >>>
        >>> # V3: Initialize with factory-created realtime client
        >>> realtime_client = await create_realtime_client(
        ...     jwt_token=client.jwt_token, account_id=str(client.account_id)
        ... )
        >>> await orderbook.initialize(realtime_client=realtime_client)
        >>>
        >>> # Start using the orderbook
        >>> snapshot = await orderbook.get_orderbook_snapshot()
    """
    # Note: realtime_client is passed to initialize() separately to allow
    # for async initialization
    _ = realtime_client  # Mark as intentionally unused
    return OrderBook(instrument, event_bus, project_x, timezone_str)
