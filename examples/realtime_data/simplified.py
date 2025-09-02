"""
Basic real-time data streaming example.

This example demonstrates:
- Connecting to real-time data feeds
- Handling tick (quote) updates
- Processing new bar events
- Monitoring connection health
- Displaying streaming statistics
"""

import asyncio
from datetime import datetime

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event


async def main():
    """Main function to run real-time data streaming."""
    # Create suite with real-time capabilities
    suite = await TradingSuite.create(
        ["MNQ"],
        timeframes=["1min"],
        initial_days=1,  # Minimal historical data
    )
    mnq_context = suite["MNQ"]

    print(f"Real-time streaming started for {mnq_context.symbol}")
    print(f"Connected: {suite.is_connected}")

    # Track statistics
    tick_count = 0
    bar_count = 0
    last_price = None

    async def on_new_bar(event: Event):
        """Handle new bar events."""
        nonlocal bar_count
        bar_count += 1
        print("MNQ ohlcv")
        timestamp = datetime.now().strftime("%H:%M:%S")

        # The event.data contains timeframe and nested data
        event_data = event.data
        timeframe = event_data.get("timeframe", "unknown")

        # Get the bar data directly from the event
        bar_data = event_data.get("data", {})

        if bar_data:
            print(f"This {timeframe} data is from the new bar event.")
            # Data from the event is from the new bar that was just started
            # So all the values are the opening values
            # Use instrument context to get the previous bar's values

            # Access the bar data fields directly
            open_price = bar_data.get("open", 1)
            high_price = bar_data.get("high", 1)
            low_price = bar_data.get("low", 0)
            close_price = bar_data.get("close", 0)
            volume = bar_data.get("volume", 0)
            bar_timestamp = bar_data.get("timestamp", "")

            print(f"New {timeframe} bar:")
            print(f"BAR TIMESTAMP: {bar_timestamp}")
            print(f"OPEN PRICE: {open_price}")
            print(f"HIGH PRICE: {high_price}")
            print(f"LOW PRICE: {low_price}")
            print(f"CLOSE PRICE: {close_price}")
            print(f"VOLUME: {volume}")
            print("\n")

        realtime_data = await mnq_context.data.get_data(timeframe)
        if realtime_data is not None:
            # Data from the instrument context is the true OHLCV values
            # [-1] is the current bar
            # [-2] is the previous bar
            print(f"This {timeframe} data is from MNQ context.")
            print(f"BAR TIMESTAMP: {realtime_data['timestamp'][-2]}")
            print(f"OPEN PRICE: {realtime_data['open'][-2]}")
            print(f"HIGH PRICE: {realtime_data['high'][-2]}")
            print(f"LOW PRICE: {realtime_data['low'][-2]}")
            print(f"CLOSE PRICE: {realtime_data['close'][-2]}")
            print(f"VOLUME: {realtime_data['volume'][-2]}")
            print("\n")

    async def on_connection_status(event: Event):
        """Handle connection status changes."""
        status = event.data.get("connected", False)
        print(f"Connection Status Changed: {status}")
        if status:
            print("✅ Real-time feed connected")
        else:
            print("❌ Real-time feed disconnected")

    # Register event handlers

    await mnq_context.on(EventType.NEW_BAR, on_new_bar)
    await mnq_context.on(EventType.CONNECTED, on_connection_status)
    await mnq_context.on(EventType.DISCONNECTED, on_connection_status)

    print("Listening for real-time data... Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("\nShutting down real-time stream...")
    finally:
        # Ensure proper cleanup
        await suite.disconnect()
        print("Disconnected from real-time feeds")


asyncio.run(main())
