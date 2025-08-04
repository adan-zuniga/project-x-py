"""
Example demonstrating the new v3.0.0 TradingSuite for simplified SDK usage.

This example shows how the new TradingSuite replaces all the old factory
functions with a single, intuitive API.

BREAKING CHANGE: This example has been updated for v3.0.0.
The old factory functions are obsolete and will be removed.
"""

import asyncio

from project_x_py import TradingSuite, setup_logging


async def simple_trading_suite():
    """Demonstrate the simplest way to create a trading suite."""
    print("=" * 60)
    print("SIMPLE TRADING SUITE CREATION (v3.0.0)")
    print("=" * 60)

    # One line replaces all the old factory functions!
    suite = await TradingSuite.create("MNQ")

    print("✅ TradingSuite created with single line!")
    print(f"   Account: {suite.client.account_info.name}")
    print(f"   Instrument: {suite.instrument}")
    print(f"   Connected: {suite.is_connected}")

    # All components are ready to use
    print("\n📦 Available Components:")
    print(f"   - Client: {suite.client}")
    print(f"   - Data Manager: {suite.data}")
    print(f"   - Order Manager: {suite.orders}")
    print(f"   - Position Manager: {suite.positions}")
    print(f"   - Real-time Client: {suite.realtime}")

    # Get some data
    current_price = await suite.data.get_current_price()
    print(f"\n💰 Current {suite.instrument} price: ${current_price:,.2f}")

    # Clean disconnect
    await suite.disconnect()
    print("✅ Disconnected cleanly")


async def trading_suite_with_options():
    """Demonstrate creating a trading suite with custom options."""
    print("\n" + "=" * 60)
    print("TRADING SUITE WITH CUSTOM OPTIONS")
    print("=" * 60)

    # Create with specific timeframes and features
    suite = await TradingSuite.create(
        "MGC",
        timeframes=["1min", "5min", "15min", "1hr"],
        features=["orderbook"],
        initial_days=10,
    )

    print("✅ TradingSuite created with custom options!")
    print(f"   Instrument: {suite.instrument}")
    print(f"   Timeframes: {suite.config.timeframes}")
    print(f"   Features: {[f.value for f in suite.config.features]}")
    print(f"   Has OrderBook: {suite.orderbook is not None}")

    # Show suite statistics
    stats = suite.get_stats()
    print("\n📊 Suite Statistics:")
    print(f"   Connected: {stats['connected']}")
    print(f"   Real-time events: {stats['realtime']['events_received']}")
    if "orderbook" in stats:
        print(
            f"   OrderBook depth: {stats['orderbook']['bid_depth']} bids, {stats['orderbook']['ask_depth']} asks"
        )

    await suite.disconnect()


async def trading_suite_context_manager():
    """Demonstrate using TradingSuite as a context manager."""
    print("\n" + "=" * 60)
    print("TRADING SUITE AS CONTEXT MANAGER")
    print("=" * 60)

    # Automatic cleanup with context manager
    async with await TradingSuite.create("ES", timeframes=["5min", "15min"]) as suite:
        print("✅ TradingSuite created and entered context")
        print(f"   Trading: {suite.instrument}")

        # Place an order
        positions = await suite.positions.get_all_positions()
        print(f"   Current positions: {len(positions)}")

        # Get market data
        bars = await suite.client.get_bars(suite.instrument, days=1)
        if bars is not None and not bars.is_empty():
            latest = bars.tail(1)
            print(f"   Latest close: ${latest['close'][0]:,.2f}")

    print("✅ Context exited - automatic cleanup completed")


async def old_vs_new_comparison():
    """Show the dramatic simplification from old factory functions to TradingSuite."""
    print("\n" + "=" * 60)
    print("OLD vs NEW COMPARISON")
    print("=" * 60)

    print("❌ OLD WAY (v2.x) - Complex with many factory functions:")
    print("""
    # Required 50+ lines of code:
    async with ProjectX.from_env() as client:
        await client.authenticate()
        
        realtime_client = create_realtime_client(
            jwt_token=client.session_token,
            account_id=str(client.account_info.id)
        )
        
        data_manager = create_data_manager(
            instrument="MNQ",
            project_x=client,
            realtime_client=realtime_client,
            timeframes=["1min", "5min"]
        )
        
        order_manager = create_order_manager(client, realtime_client)
        position_manager = create_position_manager(client, realtime_client, order_manager)
        
        await realtime_client.connect()
        await realtime_client.subscribe_user_updates()
        await position_manager.initialize(realtime_client, order_manager)
        await data_manager.initialize()
        
        instrument_info = await client.get_instrument("MNQ")
        await realtime_client.subscribe_market_data([instrument_info.id])
        await data_manager.start_realtime_feed()
        
        # ... finally ready to trade ...
    """)

    print("\n✅ NEW WAY (v3.0) - Simple and intuitive:")
    print("""
    # Just 1 line!
    suite = await TradingSuite.create("MNQ")
    # Everything is ready to use!
    """)

    print("\n🎯 Benefits:")
    print("   - 98% less code")
    print("   - No manual wiring")
    print("   - No initialization steps")
    print("   - Automatic resource management")
    print("   - Type-safe with full IDE support")


async def main():
    """Run all demonstrations."""
    logger = setup_logging(level="INFO")
    logger.info("Starting TradingSuite v3.0.0 Demo")

    print("\n" + "🚀 " * 20)
    print("TRADINGSUITE v3.0.0 DEMONSTRATION")
    print("Replacing all factory functions with one simple API")
    print("🚀 " * 20 + "\n")

    try:
        # Run demonstrations
        await simple_trading_suite()
        await trading_suite_with_options()
        await trading_suite_context_manager()
        await old_vs_new_comparison()

        print("\n" + "=" * 60)
        print("✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print("=" * 60)

        print("\n📚 Summary:")
        print("   - TradingSuite.create() replaces ALL factory functions")
        print("   - Single line initialization")
        print("   - Automatic connection and subscription management")
        print("   - Built-in cleanup with context managers")
        print("   - Feature flags for optional components")
        print("\n🎉 Welcome to v3.0.0!")

    except Exception as e:
        logger.error(f"Error in demo: {e}")
        raise


if __name__ == "__main__":
    print("\n📋 Requirements:")
    print("   - Set PROJECT_X_API_KEY environment variable")
    print("   - Set PROJECT_X_USERNAME environment variable")
    print("   - Have valid ProjectX account credentials")
    print("\nRun with: ./test.sh examples/factory_functions_demo.py\n")

    asyncio.run(main())
