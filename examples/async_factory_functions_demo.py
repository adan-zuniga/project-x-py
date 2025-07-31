"""
Example demonstrating the async factory functions for creating trading components.

This example shows how to use the convenient factory functions to create
async trading components with minimal boilerplate code.
"""

import asyncio
import json
from datetime import datetime

from project_x_py import (
    create_async_client,
    create_async_data_manager,
    create_async_order_manager,
    create_async_orderbook,
    create_async_position_manager,
    create_async_realtime_client,
    create_async_trading_suite,
)


async def simple_component_creation():
    """Demonstrate creating individual async components."""
    print("=" * 60)
    print("SIMPLE COMPONENT CREATION")
    print("=" * 60)

    # Create async client using factory
    async with create_async_client() as client:
        await client.authenticate()
        print(f"✅ Created client: {client.account_info.name}")

        # Get JWT token for real-time
        jwt_token = client.jwt_token
        account_id = client.account_info.id

        # Create async realtime client
        realtime_client = create_async_realtime_client(jwt_token, account_id)
        print("✅ Created realtime client")

        # Create individual managers
        order_manager = create_async_order_manager(client, realtime_client)
        await order_manager.initialize()
        print("✅ Created order manager")

        position_manager = create_async_position_manager(client, realtime_client)
        await position_manager.initialize()
        print("✅ Created position manager")

        # Find an instrument
        instruments = await client.search_instruments("MGC")
        if instruments:
            instrument = instruments[0]

            # Create data manager
            data_manager = create_async_data_manager(
                instrument.symbol, client, realtime_client, timeframes=["1min", "5min"]
            )
            print("✅ Created data manager")

            # Create orderbook
            orderbook = create_async_orderbook(
                instrument.symbol, realtime_client=realtime_client, project_x=client
            )
            await orderbook.initialize(realtime_client)
            print("✅ Created orderbook")

        # Clean up
        await realtime_client.cleanup()


async def complete_suite_creation():
    """Demonstrate creating a complete trading suite with one function."""
    print("\n" + "=" * 60)
    print("COMPLETE TRADING SUITE CREATION")
    print("=" * 60)

    # Create async client
    async with create_async_client() as client:
        await client.authenticate()
        print(f"✅ Authenticated: {client.account_info.name}")

        # Find instrument
        instruments = await client.search_instruments("MGC")
        if not instruments:
            print("❌ No instruments found")
            return

        instrument = instruments[0]

        # Create complete trading suite with one function
        suite = await create_async_trading_suite(
            instrument=instrument.symbol,
            project_x=client,
            jwt_token=client.jwt_token,
            account_id=client.account_info.id,
            timeframes=["5sec", "1min", "5min", "15min"],
        )

        print("\n📦 Trading Suite Components:")
        print(f"  ✅ Realtime Client: {suite['realtime_client'].__class__.__name__}")
        print(f"  ✅ Data Manager: {suite['data_manager'].__class__.__name__}")
        print(f"  ✅ OrderBook: {suite['orderbook'].__class__.__name__}")
        print(f"  ✅ Order Manager: {suite['order_manager'].__class__.__name__}")
        print(f"  ✅ Position Manager: {suite['position_manager'].__class__.__name__}")
        print(f"  ✅ Config: {suite['config'].__class__.__name__}")

        # Connect and initialize
        print("\n🔌 Connecting to real-time services...")
        if await suite["realtime_client"].connect():
            print("✅ Connected")

            # Subscribe to data
            await suite["realtime_client"].subscribe_user_updates()
            await suite["realtime_client"].subscribe_market_data(
                [instrument.activeContract]
            )

            # Initialize data manager
            await suite["data_manager"].initialize(initial_days=1)
            await suite["data_manager"].start_realtime_feed()

            print("\n📊 Suite is ready for trading!")

            # Show some data
            await asyncio.sleep(2)  # Let some data come in

            # Get current data
            for timeframe in ["5sec", "1min", "5min"]:
                data = await suite["data_manager"].get_data(timeframe)
                if data and len(data) > 0:
                    last = data[-1]
                    print(
                        f"\n{timeframe} Latest: C=${last['close']:.2f} V={last['volume']}"
                    )

            # Get orderbook
            snapshot = await suite["orderbook"].get_orderbook_snapshot()
            if snapshot:
                spread = await suite["orderbook"].get_bid_ask_spread()
                print(f"\nOrderBook: Bid=${spread['bid']:.2f} Ask=${spread['ask']:.2f}")

            # Get positions
            positions = await suite["position_manager"].get_all_positions()
            print(f"\nPositions: {len(positions)} open")

            # Clean up
            await suite["data_manager"].stop_realtime_feed()
            await suite["realtime_client"].cleanup()
            print("\n✅ Cleanup completed")


async def main():
    """Run all demonstrations."""
    print("\n🚀 ASYNC FACTORY FUNCTIONS DEMONSTRATION\n")

    # Show simple component creation
    await simple_component_creation()

    # Show complete suite creation
    await complete_suite_creation()

    print("\n🎯 Key Benefits of Factory Functions:")
    print("  1. Less boilerplate code")
    print("  2. Consistent initialization")
    print("  3. Proper dependency injection")
    print("  4. Type hints and documentation")
    print("  5. Easy to use for beginners")

    print("\n📚 Factory Functions Available:")
    print("  - create_async_client() - Create AsyncProjectX client")
    print("  - create_async_realtime_client() - Create real-time WebSocket client")
    print("  - create_async_order_manager() - Create order manager")
    print("  - create_async_position_manager() - Create position manager")
    print("  - create_async_data_manager() - Create OHLCV data manager")
    print("  - create_async_orderbook() - Create market depth orderbook")
    print("  - create_async_trading_suite() - Create complete trading toolkit")


if __name__ == "__main__":
    asyncio.run(main())
