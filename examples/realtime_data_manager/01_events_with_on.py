import asyncio
import signal

from project_x_py import TradingSuite
from project_x_py.event_bus import EventType


async def main():
    print("Creating TradingSuite...")
    # Note: Use "MNQ" for Micro E-mini Nasdaq-100 futures
    # "NQ" resolves to E-mini Nasdaq (ENQ) which may have different data characteristics
    suite = await TradingSuite.create(
        instrument="NQ",  # Works best with MNQ for consistent real-time updates
        timeframes=["1min"],
    )
    print("TradingSuite created!")

    # No need to call connect() - it's already connected via auto_connect=True
    print("Suite is already connected!")

    # Set up signal handler for clean exit
    shutdown_event = asyncio.Event()

    def signal_handler(_signum, _frame):
        print("\n\nReceived interrupt signal. Shutting down gracefully...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Define the event handler as an async function
    async def on_new_bar(event):
        """Handle new bar events"""
        print(f"New bar event received: {event}")
        print("About to call get_current_price...")
        try:
            current_price = await suite.data.get_current_price()
            print(f"Got current price: {current_price}")
        except Exception as e:
            print(f"Error getting current price: {e}")
            return

        print("About to call get_data...")
        try:
            last_bars = await suite.data.get_data(timeframe="15sec", bars=5)
            print("Got data")
        except Exception as e:
            print(f"Error getting data: {e}")
            return
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

    # Register the event handler
    print("About to register event handler...")
    await suite.on(EventType.NEW_BAR, on_new_bar)
    print("Event handler registered!")

    print("Monitoring MNQ 15-second bars. Press CTRL+C to exit.")
    print("Event handler registered and waiting for new bars...\n")

    try:
        # Keep the program running
        while not shutdown_event.is_set():
            await asyncio.sleep(1)
    finally:
        print("Disconnecting from real-time feeds...")
        await suite.disconnect()
        print("Clean shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
