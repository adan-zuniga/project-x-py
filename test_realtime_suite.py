#!/usr/bin/env python3
"""Quick test of the real-time connection using create_initialized_trading_suite."""

import asyncio

from project_x_py import ProjectX, create_initialized_trading_suite, setup_logging


async def main():
    """Test real-time connection with trading suite."""
    setup_logging(level="INFO")

    try:
        async with ProjectX.from_env() as client:
            await client.authenticate()
            print(f"✅ Authenticated: {client.account_info.name}")

            # Create trading suite with automatic initialization
            print("\n🏗️ Creating trading suite...")
            suite = await create_initialized_trading_suite(
                instrument="MNQ",
                project_x=client,
                timeframes=["1min", "5min"],
                enable_orderbook=False,
                initial_days=1,
            )

            print("✅ Trading suite created!")
            print(f"   Components: {list(suite.keys())}")

            # Test if we can get data
            data_manager = suite["data_manager"]
            current_price = await data_manager.get_current_price()

            if current_price:
                print(f"\n✅ Real-time connection working!")
                print(f"   Current MNQ price: ${current_price:.2f}")
            else:
                print("\n⚠️ No current price available (market may be closed)")

            # Wait a bit to see if we get any real-time updates
            print("\n⏱️ Waiting 5 seconds for real-time updates...")
            await asyncio.sleep(5)

            print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
