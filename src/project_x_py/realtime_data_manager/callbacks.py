"""
Callback management and event handling for real-time data updates.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides callback management and event handling functionality for real-time data updates.
    Implements an event-driven system that allows registering callbacks for specific data events,
    enabling reactive trading systems that respond to real-time market events.

Key Features:
    - Event-driven callback system for real-time data processing
    - Support for both async and sync callbacks
    - Multiple callbacks per event type
    - Error isolation to prevent callback failures
    - Thread-safe callback registration and management
    - Comprehensive event data structures

Event Types:
    - "new_bar": Triggered when a new OHLCV bar is created in any timeframe
    - "data_update": Triggered on every tick update with price and volume information

Callback Capabilities:
    - Registration and removal of callbacks for specific events
    - Support for both synchronous and asynchronous callback functions
    - Error handling and isolation to prevent callback failures
    - Event data structures with comprehensive market information
    - Thread-safe operations with proper error handling

Example Usage:
    ```python
    # Register an async callback for new bar events
    async def on_new_bar(data):
        tf = data["timeframe"]
        bar = data["data"]
        print(
            f"New {tf} bar: O={bar['open']}, H={bar['high']}, L={bar['low']}, C={bar['close']}"
        )

        # Implement trading logic based on the new bar
        if tf == "5min" and bar["close"] > bar["open"]:
            # Bullish bar detected
            print(f"Bullish 5min bar detected at {data['bar_time']}")

            # Trigger trading logic (implement your strategy here)
            # await strategy.on_bullish_bar(data)


    # Register the callback
    await data_manager.add_callback("new_bar", on_new_bar)


    # You can also use regular (non-async) functions
    def on_data_update(data):
        # This is called on every tick - keep it lightweight!
        print(f"Price update: {data['price']}")


    await data_manager.add_callback("data_update", on_data_update)
    ```

Event Data Structures:
    "new_bar" event data contains:
        {
            "timeframe": "5min",                  # The timeframe of the bar
            "bar_time": datetime(2023,5,1,10,0),  # Bar timestamp (timezone-aware)
            "data": {                             # Complete bar data
                "timestamp": datetime(...),       # Bar timestamp
                "open": 1950.5,                   # Opening price
                "high": 1955.2,                   # High price
                "low": 1950.0,                    # Low price
                "close": 1954.8,                  # Closing price
                "volume": 128                     # Bar volume
            }
        }

    "data_update" event data contains:
        {
            "timestamp": datetime(2023,5,1,10,0,15),  # Tick timestamp
            "price": 1954.75,                         # Current price
            "volume": 1                               # Tick volume
        }

See Also:
    - `realtime_data_manager.core.RealtimeDataManager`
    - `realtime_data_manager.data_access.DataAccessMixin`
    - `realtime_data_manager.data_processing.DataProcessingMixin`
    - `realtime_data_manager.memory_management.MemoryManagementMixin`
    - `realtime_data_manager.validation.ValidationMixin`
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_x_py.types import RealtimeDataManagerProtocol

logger = logging.getLogger(__name__)


class CallbackMixin:
    """Mixin for managing callbacks and event handling."""

    async def add_callback(
        self: "RealtimeDataManagerProtocol",
        event_type: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None],
    ) -> None:
        """
        Register a callback for specific data events.

        This method allows you to register callback functions that will be triggered when
        specific events occur in the data manager. Callbacks can be either synchronous functions
        or asynchronous coroutines. This event-driven approach enables building reactive
        trading systems that respond to real-time market events.

        Args:
            event_type: Type of event to listen for. Supported event types:
                - "new_bar": Triggered when a new OHLCV bar is created in any timeframe.
                  The callback receives data with timeframe, bar_time, and complete bar data.
                - "data_update": Triggered on every tick update.
                  The callback receives timestamp, price, and volume information.

            callback: Function or coroutine to call when the event occurs.
                Both synchronous functions and async coroutines are supported.
                The function should accept a single dictionary parameter with event data.

        Event Data Structures:
            "new_bar" event data contains:
                {
                    "timeframe": "5min",                  # The timeframe of the bar
                    "bar_time": datetime(2023,5,1,10,0),  # Bar timestamp (timezone-aware)
                    "data": {                             # Complete bar data
                        "timestamp": datetime(...),       # Bar timestamp
                        "open": 1950.5,                   # Opening price
                        "high": 1955.2,                   # High price
                        "low": 1950.0,                    # Low price
                        "close": 1954.8,                  # Closing price
                        "volume": 128                     # Bar volume
                    }
                }

            "data_update" event data contains:
                {
                    "timestamp": datetime(2023,5,1,10,0,15),  # Tick timestamp
                    "price": 1954.75,                         # Current price
                    "volume": 1                               # Tick volume
                }

        Example:
            ```python
            # Register an async callback for new bar events
            async def on_new_bar(data):
                tf = data["timeframe"]
                bar = data["data"]
                print(
                    f"New {tf} bar: O={bar['open']}, H={bar['high']}, L={bar['low']}, C={bar['close']}"
                )

                # Implement trading logic based on the new bar
                if tf == "5min" and bar["close"] > bar["open"]:
                    # Bullish bar detected
                    print(f"Bullish 5min bar detected at {data['bar_time']}")

                    # Trigger trading logic (implement your strategy here)
                    # await strategy.on_bullish_bar(data)


            # Register the callback
            await data_manager.add_callback("new_bar", on_new_bar)


            # You can also use regular (non-async) functions
            def on_data_update(data):
                # This is called on every tick - keep it lightweight!
                print(f"Price update: {data['price']}")


            await data_manager.add_callback("data_update", on_data_update)
            ```

        Note:
            - Multiple callbacks can be registered for the same event type
            - Callbacks are executed sequentially for each event
            - For high-frequency events like "data_update", keep callbacks lightweight
              to avoid processing bottlenecks
            - Exceptions in callbacks are caught and logged, preventing them from
              affecting the data manager's operation
        """
        self.callbacks[event_type].append(callback)

    async def _trigger_callbacks(
        self: "RealtimeDataManagerProtocol", event_type: str, data: dict[str, Any]
    ) -> None:
        """
        Trigger all callbacks for a specific event type.

        Args:
            event_type: Type of event to trigger
            data: Data to pass to callbacks
        """
        for callback in self.callbacks.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {e}")
