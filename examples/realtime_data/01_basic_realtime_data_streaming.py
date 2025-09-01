#!/usr/bin/env python
"""
Basic real-time data streaming example
"""

import asyncio
from datetime import datetime

from project_x_py import EventType, TradingSuite


async def main():
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

    async def on_tick(event):
        nonlocal tick_count, last_price
        tick_data = event.data

        tick_count += 1
        last_price = tick_data.get("price", 0)

        # Display every 10th tick to avoid spam
        if tick_count % 10 == 0:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Tick #{tick_count}: ${last_price:.2f}")

    async def on_new_bar(event):
        nonlocal bar_count
        bar_data = event.data
        bar_count += 1

        timestamp = datetime.now().strftime("%H:%M:%S")
        timeframe = bar_data.get("timeframe", "unknown")

        print(f"[{timestamp}] New {timeframe} bar #{bar_count}:")
        print(
            f"  OHLC: ${bar_data['open']:.2f} / ${bar_data['high']:.2f} / ${bar_data['low']:.2f} / ${bar_data['close']:.2f}"
        )
        print(f"  Volume: {bar_data.get('volume', 0)}")
        print(f"  Timestamp: {bar_data.get('timestamp')}")

    async def on_connection_status(event):
        status = event.data.get("status", "unknown")
        print(f"Connection Status: {status}")

    # Register event handlers
    await suite.on(EventType.QUOTE_UPDATE, on_tick)
    await suite.on(EventType.NEW_BAR, on_new_bar)
    await suite.on(EventType.CONNECTED, on_connection_status)

    print("Listening for real-time data... Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(10)

            # Display periodic status
            current_price = await mnq_context.data.get_current_price()
            connection_health = await suite.get_session_statistics()

            print(
                f"Status - Price: ${current_price:.2f} | Ticks: {tick_count} | Bars: {bar_count} | Health: {connection_health}"
            )

    except KeyboardInterrupt:
        print("\nShutting down real-time stream...")


if __name__ == "__main__":
    asyncio.run(main())
