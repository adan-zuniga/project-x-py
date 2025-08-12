import asyncio
import signal

from project_x_py import TradingSuite
from project_x_py.event_bus import EventType


async def main():
    suite = await TradingSuite.create(
        instrument="MNQ",
        timeframes=["15sec"],
    )

    await suite.connect()

    # Set up signal handler for clean exit
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        print("\n\nReceived interrupt signal. Shutting down gracefully...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Use a queue to handle events outside the callback
    event_queue = asyncio.Queue()

    # Define the event handler as an async function
    async def on_new_bar(event):
        """Handle new bar events - just queue them"""
        await event_queue.put(event)

    # Register the event handler
    await suite.on(EventType.NEW_BAR, on_new_bar)

    print("Monitoring MNQ 15-second bars. Press CTRL+C to exit.")
    print("Event handler registered and waiting for new bars...\n")

    try:
        # Process events from the queue
        while not shutdown_event.is_set():
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(event_queue.get(), timeout=1.0)

                # Process the event outside the handler
                current_price = await suite.data.get_current_price()
                last_bars = await suite.data.get_data(timeframe="15sec", bars=5)

                print(f"\nCurrent price: {current_price}")
                print("=" * 80)

                if last_bars is not None and not last_bars.is_empty():
                    print("Last 5 bars (oldest to newest):")
                    print("-" * 80)

                    # Get the last 5 bars and iterate through them
                    for row in last_bars.tail(5).iter_rows(named=True):
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

            except asyncio.TimeoutError:
                # Timeout is expected, just check shutdown_event again
                pass
    finally:
        print("Disconnecting from real-time feeds...")
        await suite.disconnect()
        print("Clean shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
