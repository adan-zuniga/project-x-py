#!/usr/bin/env python
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
        timeframes=["15sec", "1min"],
        initial_days=1,  # Minimal historical data
    )
    mnq_context = suite["MNQ"]

    print(f"Real-time streaming started for {mnq_context.symbol}")
    print(f"Connected: {suite.is_connected}")

    # Track statistics
    tick_count = 0
    bar_count = 0
    last_price = None

    async def on_tick(event: Event):
        """Handle tick updates."""
        nonlocal tick_count, last_price
        tick_data = event.data

        tick_count += 1
        last_price = tick_data.get("last") or last_price

        # Display every 10th tick to avoid spam
        if tick_count % 10 == 0:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Tick #{tick_count}: ${last_price:.2f}")

    async def on_new_bar(event: Event):
        """Handle new bar events."""
        nonlocal bar_count
        bar_count += 1

        timestamp = datetime.now().strftime("%H:%M:%S")

        # The event.data contains timeframe and nested data
        event_data = event.data
        timeframe = event_data.get("timeframe", "unknown")

        # Get the bar data directly from the event
        bar_data = event_data.get("data", {})

        if bar_data:
            print(f"[{timestamp}] New {timeframe} bar #{bar_count}:")

            # Access the bar data fields directly
            open_price = bar_data.get("open", 0)
            high_price = bar_data.get("high", 0)
            low_price = bar_data.get("low", 0)
            close_price = bar_data.get("close", 0)
            volume = bar_data.get("volume", 0)
            bar_timestamp = bar_data.get("timestamp", "")

            print(
                f"  OHLC: ${open_price:.2f} / ${high_price:.2f} / "
                f"${low_price:.2f} / ${close_price:.2f}"
            )
            print(f"  Volume: {volume}")
            print(f"  Timestamp: {bar_timestamp}")

    async def on_connection_status(event: Event):
        """Handle connection status changes."""
        status = event.data.get("connected", False)
        print(f"Connection Status Changed: {status}")
        if status:
            print("✅ Real-time feed connected")
        else:
            print("❌ Real-time feed disconnected")

    # Register event handlers
    await mnq_context.on(EventType.QUOTE_UPDATE, on_tick)
    await mnq_context.on(EventType.NEW_BAR, on_new_bar)
    await mnq_context.on(EventType.CONNECTED, on_connection_status)
    await mnq_context.on(EventType.DISCONNECTED, on_connection_status)

    print("Listening for real-time data... Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(10)

            # Display periodic status
            current_price = await mnq_context.data.get_current_price()
            connection_health = await mnq_context.data.get_health_score()

            print(
                f"Status - Price: ${current_price:.2f} | "
                f"Ticks: {tick_count} | Bars: {bar_count} | "
                f"Health: {connection_health}"
            )

    except KeyboardInterrupt:
        print("\nShutting down real-time stream...")
    finally:
        # Ensure proper cleanup
        await suite.disconnect()
        print("Disconnected from real-time feeds")


if __name__ == "__main__":
    asyncio.run(main())
