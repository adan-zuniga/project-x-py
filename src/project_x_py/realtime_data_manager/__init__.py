"""
Real-time data manager module for OHLCV data processing.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides the RealtimeDataManager class for managing real-time market data
    across multiple timeframes. Implements efficient OHLCV (Open, High, Low, Close, Volume)
    data processing with WebSocket integration, automatic bar creation, and memory management.

Key Features:
    - Multi-timeframe OHLCV data management with real-time updates
    - WebSocket integration for zero-latency tick processing
    - Automatic bar creation and maintenance across all timeframes
    - Memory-efficient sliding window storage with automatic cleanup
    - Event-driven callback system for new bars and data updates
    - Timezone-aware timestamp handling (default: CME Central Time)
    - DST (Daylight Saving Time) transition handling (NEW)
    - Thread-safe operations with asyncio locks
    - Comprehensive health monitoring and statistics
    - DataFrame optimization with lazy evaluation (NEW)

Real-time Capabilities:
    - Live tick processing from WebSocket feeds
    - Automatic OHLCV bar creation for multiple timeframes
    - Real-time price updates and volume tracking
    - Event callbacks for new bars and tick updates
    - Memory management with automatic data cleanup
    - Performance monitoring and statistics
    - Lazy DataFrame operations for 30% memory reduction
    - Query optimization for 40% performance improvement
    - DST transition handling with automatic bar alignment

Note:
    While this module provides direct access to the `RealtimeDataManager`, for most
    trading applications, it is recommended to use the `TradingSuite`. The suite
    automatically creates, configures, and manages the data manager, providing
    simplified access to its data and events via `suite.data` and `suite.on()`.
    The example below shows the lower-level manual setup.

Example Usage:
    ```python
    # V3.1: TradingSuite manages data manager automatically
    import asyncio
    from project_x_py import TradingSuite, EventType

    # V3.1: TradingSuite creates and manages all components
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min", "15min", "1hr"],
        initial_days=5,
    )

    # V3.1: Data manager is automatically initialized and connected
    # Access it via suite.data
    print(f"Data manager ready for {suite.instrument}")


    # V3.1: Register callbacks via suite's event bus
    async def on_new_bar(event):
        bar = event.data["data"]
        timeframe = event.data["timeframe"]
        print(f"New {timeframe} bar:")
        print(f"  Open: {bar['open']}, High: {bar['high']}")
        print(f"  Low: {bar['low']}, Close: {bar['close']}")
        print(f"  Volume: {bar['volume']}")


    await suite.on(EventType.NEW_BAR, on_new_bar)

    # V3.1: Access real-time data via suite.data
    current_price = await suite.data.get_current_price()
    data_5m = await suite.data.get_data("5min", bars=100)

    # V3.1: Monitor memory stats
    stats = suite.data.get_memory_stats()
    print(f"Memory usage: {stats}")

    # Process data...
    await asyncio.sleep(60)

    # V3.1: Cleanup is automatic with context manager
    await suite.disconnect()

    # V3.1: Low-level direct usage (advanced users only)
    # from project_x_py import ProjectX
    # from project_x_py.realtime_data_manager import RealtimeDataManager
    #
    # async with ProjectX.from_env() as client:
    #     await client.authenticate()
    #     # Create components manually
    #     data_manager = RealtimeDataManager(
    #         instrument="MNQ",
    #         project_x=client,
    #         realtime_client=realtime_client,
    #         timeframes=["1min", "5min"],
    #         event_bus=event_bus,
    #     )
    ```

Supported Timeframes:
    - Second-based: "1sec", "5sec", "10sec", "15sec", "30sec"
    - Minute-based: "1min", "5min", "15min", "30min"
    - Hour-based: "1hr", "4hr"
    - Day-based: "1day"
    - Week-based: "1week"
    - Month-based: "1month"

See Also:
    - `realtime_data_manager.core.RealtimeDataManager`
    - `realtime_data_manager.callbacks.CallbackMixin`
    - `realtime_data_manager.data_access.DataAccessMixin`
    - `realtime_data_manager.data_processing.DataProcessingMixin`
    - `realtime_data_manager.memory_management.MemoryManagementMixin`
    - `realtime_data_manager.validation.ValidationMixin`
    - `realtime_data_manager.dataframe_optimization.LazyDataFrameMixin`
"""

from project_x_py.realtime_data_manager.core import RealtimeDataManager
from project_x_py.realtime_data_manager.dataframe_optimization import (
    LazyDataFrameMixin,
    LazyQueryCache,
    QueryOptimizer,
)
from project_x_py.realtime_data_manager.dst_handling import DSTHandlingMixin

__all__ = [
    "RealtimeDataManager",
    "LazyDataFrameMixin",
    "QueryOptimizer",
    "LazyQueryCache",
    "DSTHandlingMixin",
]
