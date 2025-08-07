#!/usr/bin/env python3
"""
V3 Basic Client Connection - Simplified with TradingSuite

This example shows the dramatic simplification in v3.0.0 using the new
TradingSuite class. Compare with 01_basic_client_connection.py to see
the improvement.

Key improvements:
- Single-line initialization
- Automatic authentication and connection
- All components ready to use immediately
- Built-in error handling and recovery

Usage:
    Run with: uv run examples/01_basic_client_connection_v3.py

Author: TexasCoding
Date: August 2025
"""

import asyncio

from project_x_py import TradingSuite, setup_logging


async def main() -> bool:
    """Demonstrate v3 simplified client connection."""
    logger = setup_logging(level="INFO")
    logger.info("🚀 Starting V3 Basic Client Connection Example")

    try:
        # V3: One line replaces all the setup!
        print("🔑 Creating TradingSuite (v3 simplified API)...")
        suite = await TradingSuite.create("MNQ")

        print("✅ TradingSuite created and connected!")

        # Everything is already authenticated and ready
        print("\n📊 Account Information:")
        account = suite.client.account_info
        if account:
            print(f"   Account ID: {account.id}")
            print(f"   Account Name: {account.name}")
            print(f"   Balance: ${account.balance:,.2f}")
            print(f"   Trading Enabled: {account.canTrade}")
        else:
            print("   ❌ No account information available")
            return False

        # All components are ready to use
        print("\n🛠️ Available Components:")
        print(f"   Data Manager: {suite.data}")
        print(f"   Order Manager: {suite.orders}")
        print(f"   Position Manager: {suite.positions}")
        print(f"   Real-time Client: {suite.realtime}")

        # Get some market data
        print("\n📈 Getting Market Data...")
        current_price = await suite.data.get_current_price()
        print(f"   Current MNQ price: {current_price}")

        # Check positions
        positions = await suite.positions.get_all_positions()
        print(f"   Open positions: {len(positions)}")

        # Show suite statistics
        print("\n📊 Suite Statistics:")
        stats = suite.get_stats()
        print(f"   Connected: {stats['connected']}")
        print(f"   Instrument: {stats['instrument']}")
        print(f"   Features: {stats['features']}")

        # Clean disconnect
        await suite.disconnect()
        print("\n✅ Clean disconnect completed")

        # Alternative: Use as context manager for automatic cleanup
        print("\n🔄 Demonstrating context manager usage...")
        async with await TradingSuite.create(
            "MGC", timeframes=["1min", "5min"]
        ) as suite2:
            print(f"   Connected to {suite2.instrument}")
            print(f"   Timeframes: {suite2.config.timeframes}")
            # Automatic cleanup on exit

        print("✅ Context manager cleanup completed")

        return True

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("V3 BASIC CLIENT CONNECTION EXAMPLE")
    print("Simplified API with TradingSuite")
    print("=" * 60 + "\n")

    success = asyncio.run(main())

    if success:
        print("\n✅ V3 Example completed successfully!")
        print("\n🎯 Key V3 Benefits Demonstrated:")
        print("   - Single-line initialization")
        print("   - Automatic authentication and connection")
        print("   - All components wired and ready")
        print("   - Built-in cleanup with context manager")
        print("   - Simplified error handling")
    else:
        print("\n❌ Example failed!")
