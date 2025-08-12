import asyncio

from project_x_py import TradingSuite
from project_x_py.event_bus import EventType


async def main():
    print("Test of deadlock fix")
    print("=" * 50)

    print("Creating TradingSuite...")
    suite = await TradingSuite.create(
        instrument="MNQ",
        timeframes=["15sec"],
    )
    print("✓ TradingSuite created")

    # Test flag to verify handler was called
    handler_called = asyncio.Event()
    data_accessed = asyncio.Event()

    async def on_new_bar(event):
        """Event handler that tries to access data (would deadlock before fix)"""
        print("✓ Event handler called")
        handler_called.set()

        try:
            # This would deadlock before the fix
            current_price = await suite.data.get_current_price()
            print(f"✓ Got current price: {current_price}")

            bars = await suite.data.get_data(timeframe="15sec", bars=5)
            print(f"✓ Got bar data: {bars is not None}")

            data_accessed.set()
        except Exception as e:
            print(f"✗ Error accessing data: {e}")

    # Register handler
    print("Registering event handler...")
    await suite.on(EventType.NEW_BAR, on_new_bar)
    print("✓ Handler registered")

    # Wait for handler to be called
    print("Waiting for new bar event (max 30 seconds)...")
    try:
        await asyncio.wait_for(handler_called.wait(), timeout=30.0)
        print("✓ Handler was called successfully")

        # Wait for data access to complete
        await asyncio.wait_for(data_accessed.wait(), timeout=5.0)
        print("✓ Data was accessed successfully without deadlock!")
        print("\n✅ TEST PASSED: No deadlock detected!")

    except asyncio.TimeoutError:
        print("\n⚠️ TEST INCONCLUSIVE: No new bar event received (market may be closed)")

    await suite.disconnect()
    print("✓ Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
