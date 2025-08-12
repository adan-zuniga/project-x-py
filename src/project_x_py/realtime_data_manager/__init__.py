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
    - Thread-safe operations with asyncio locks
    - Comprehensive health monitoring and statistics

Real-time Capabilities:
    - Live tick processing from WebSocket feeds
    - Automatic OHLCV bar creation for multiple timeframes
    - Real-time price updates and volume tracking
    - Event callbacks for new bars and tick updates
    - Memory management with automatic data cleanup
    - Performance monitoring and statistics

Note:
    While this module provides direct access to the `RealtimeDataManager`, for most
    trading applications, it is recommended to use the `TradingSuite`. The suite
    automatically creates, configures, and manages the data manager, providing
    simplified access to its data and events via `suite.data` and `suite.on()`.
    The example below shows the lower-level manual setup.

Example Usage:
    ```python
    # V3: Uses factory functions and EventBus integration
    from project_x_py import ProjectX, EventBus
    from project_x_py.realtime import create_realtime_client
    from project_x_py.realtime_data_manager import RealtimeDataManager

    async with ProjectX.from_env() as client:
        await client.authenticate()

        # V3: Create real-time client with factory
        realtime_client = await create_realtime_client(
            jwt_token=client.jwt_token, account_id=str(client.account_id)
        )

        # V3: Initialize with EventBus for unified events
        event_bus = EventBus()

        # Create data manager for multiple timeframes
        data_manager = RealtimeDataManager(
            instrument="MNQ",  # V3: Using actual contract symbols
            project_x=client,
            realtime_client=realtime_client,
            timeframes=["1min", "5min", "15min", "1hr"],
            timezone="America/Chicago",
            event_bus=event_bus,  # V3: EventBus integration
        )

        # Initialize with historical data
        if await data_manager.initialize(initial_days=5):
            # Start real-time feed
            if await data_manager.start_realtime_feed():
                # V3: Register callbacks for new bars with actual field names
                async def on_new_bar(data):
                    bar = data["data"]
                    print(f"New {data['timeframe']} bar:")
                    print(f"  Open: {bar['open']}, High: {bar['high']}")
                    print(f"  Low: {bar['low']}, Close: {bar['close']}")
                    print(f"  Volume: {bar['volume']}")

                await data_manager.add_callback("new_bar", on_new_bar)

                # V3: Access real-time data with proper methods
                current_price = await data_manager.get_current_price()
                data_5m = await data_manager.get_data("5min", bars=100)

                # V3: Get memory stats for monitoring
                stats = await data_manager.get_memory_stats()
                print(f"Memory usage: {stats}")

                # Process data...
                await asyncio.sleep(60)

                await data_manager.cleanup()
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
"""

from project_x_py.realtime_data_manager.core import RealtimeDataManager

__all__ = ["RealtimeDataManager"]
