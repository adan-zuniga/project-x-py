import asyncio
import signal

from project_x_py import TradingSuite
from project_x_py.event_bus import EventType


async def on_new_bar(suite: TradingSuite):
    current_price = await suite["MNQ"].data.get_current_price()
    last_bars = await suite["MNQ"].data.get_data(timeframe="15sec", bars=5)
    print(f"\nCurrent price: {current_price}")
    print("=" * 80)

    if last_bars is not None and not last_bars.is_empty():
        print("Last 6 bars (oldest to newest):")
        print("-" * 80)

        # Get the last 5 bars and iterate through them
        for row in last_bars.tail(6).iter_rows(named=True):
            timestamp = row["timestamp"]
            open_price = row["open"]
            high = row["high"]
            low = row["low"]
            close = row["close"]
            volume = row["volume"]

            print(
                f"Time: {timestamp} | O: ${open_price:,.2f} | H: ${high:,.2f} | L: ${low:,.2f} | C: ${close:,.2f} | Vol: {volume:,}"
            )
    else:
        print("No bar data available yet")


async def main():
    suite = await TradingSuite.create(
        instrument="MNQ",
        timeframes=["15sec"],
    )

    # Set up signal handler for clean exit
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        print("\n\nReceived interrupt signal. Shutting down gracefully...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Monitoring MNQ 15-second bars. Press CTRL+C to exit.\n")

    try:
        while not shutdown_event.is_set():
            try:
                # Wait for new bar with timeout to check shutdown event
                new_bar = await asyncio.wait_for(
                    suite.wait_for(EventType.NEW_BAR), timeout=1.0
                )
                if new_bar:
                    await on_new_bar(suite)
            except TimeoutError:
                # Timeout is expected, just check shutdown_event again
                pass
    finally:
        print("Disconnecting from real-time feeds...")
        await suite.disconnect()
        print("Clean shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
