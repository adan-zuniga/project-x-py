#!/usr/bin/env python3
"""
Comparison of factory function approaches.

This example demonstrates the difference between the old manual setup
and the new auto-initialization features.
"""

import asyncio

from project_x_py import (
    ProjectX,
    create_initialized_trading_suite,
    create_trading_suite,
)
from project_x_py.models import Instrument


async def old_approach():
    """The old way - lots of boilerplate."""
    print("\n=== OLD APPROACH (Manual Setup) ===")
    print("Creating trading suite...")

    async with ProjectX.from_env() as client:
        await client.authenticate()

        # Create suite without auto-initialization
        suite = await create_trading_suite(
            instrument="MNQ",
            project_x=client,
            timeframes=["5min", "15min"],
            auto_connect=False,  # Manual mode
            auto_subscribe=False,  # Manual mode
        )

        print("✓ Suite created (but not connected)")
        print("\nNow we need to manually:")
        print("1. Connect realtime client")
        print("2. Subscribe to user updates")
        print("3. Initialize data manager")
        print("4. Search for instruments")
        print("5. Subscribe to market data")
        print("6. Start realtime feed")
        print("7. Initialize orderbook\n")

        # Manual connection steps
        print("Connecting realtime client...")
        await suite["realtime_client"].connect()

        print("Subscribing to user updates...")
        await suite["realtime_client"].subscribe_user_updates()

        print("Initializing data manager...")
        await suite["data_manager"].initialize(initial_days=5)

        print("Searching for instruments...")
        instruments = await client.search_instruments("MNQ")
        if not instruments:
            raise ValueError("Instrument not found")

        print("Subscribing to market data...")
        await suite["realtime_client"].subscribe_market_data([instruments[0].id])

        print("Starting realtime feed...")
        await suite["data_manager"].start_realtime_feed()

        if suite.get("orderbook"):
            print("Initializing orderbook...")
            await suite["orderbook"].initialize(
                realtime_client=suite["realtime_client"]
            )

        # In manual mode, we have the instruments from our search
        print(f"Instrument: {instruments[0].name}")
        print(f"Contract: {instruments[0].activeContract}")

        print("\n✓ Finally ready to trade!")
        print("Lines of setup code: ~15-20")

        # Cleanup
        await suite["data_manager"].stop_realtime_feed()
        await suite["realtime_client"].cleanup()


async def new_approach_flexible():
    """The new way - with flexibility."""
    print("\n=== NEW APPROACH (Flexible) ===")
    print("Creating trading suite with auto options...")

    async with ProjectX.from_env() as client:
        await client.authenticate()

        # Create suite with selective auto-initialization
        suite = await create_trading_suite(
            instrument="MNQ",
            project_x=client,
            timeframes=["5min", "15min"],
            auto_connect=True,  # Auto-connect
            auto_subscribe=True,  # Auto-subscribe
            initial_days=5,  # Historical data to load
        )

        instrument: Instrument = suite["instrument_info"]
        print(f"Instrument: {instrument.symbolId}")
        print(f"Contract: {instrument.activeContract}")

        print("\n✓ Everything is ready!")
        print("- Realtime client connected ✓")
        print("- User updates subscribed ✓")
        print("- Historical data loaded ✓")
        print("- Market data subscribed ✓")
        print("- Realtime feeds started ✓")
        print("- Orderbook initialized ✓")
        print("\nLines of setup code: 1")


async def new_approach_simple():
    """The simplest way - fully automated."""
    print("\n=== SIMPLEST APPROACH (Fully Automated) ===")
    print("Creating fully initialized trading suite...")

    async with ProjectX.from_env() as client:
        await client.authenticate()

        # One line does everything!
        suite = await create_initialized_trading_suite(
            instrument="MNQ",
            project_x=client,
            timeframes=["5min", "15min"],
        )

        instrument: Instrument = suite["instrument_info"]

        print("\n✓ Ready to trade immediately!")
        print(f"Instrument: {instrument.symbolId}")
        print(f"Contract: {instrument.activeContract}")
        print("\nLines of setup code: 1")
        print("\nThis is perfect for:")
        print("- Trading strategies")
        print("- Quick prototyping")
        print("- Research and backtesting")
        print("- Any use case where you want everything ready")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("FACTORY FUNCTION COMPARISON")
    print("=" * 60)

    # Show old approach
    await old_approach()

    # Show new flexible approach
    await new_approach_flexible()

    # Show simplest approach
    await new_approach_simple()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\nThe new factory functions reduce boilerplate by 95%!")
    print("\nChoose your approach:")
    print("1. create_trading_suite(..., auto_connect=False, auto_subscribe=False)")
    print("   → Full manual control (like before)")
    print("\n2. create_trading_suite(..., auto_connect=True, auto_subscribe=True)")
    print("   → Automatic initialization with options")
    print("\n3. create_initialized_trading_suite(...)")
    print("   → Everything ready in one line!")


if __name__ == "__main__":
    asyncio.run(main())
