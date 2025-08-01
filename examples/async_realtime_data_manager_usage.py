"""
Example demonstrating AsyncRealtimeDataManager usage for real-time OHLCV data.

This example shows how to use the AsyncRealtimeDataManager for managing
multi-timeframe OHLCV data with real-time updates via WebSocket.
"""

import asyncio
from datetime import datetime

from project_x_py import AsyncProjectX, AsyncRealtimeDataManager
from project_x_py.async_realtime import AsyncProjectXRealtimeClient


async def on_new_bar(data):
    """Callback for new bar events."""
    timeframe = data.get("timeframe")
    print(f"🕐 New {timeframe} bar created at {datetime.now()}")


async def on_data_update(data):
    """Callback for data update events."""
    tick = data.get("tick", {})
    price = tick.get("price", 0)
    print(f"📊 Price update: ${price:.2f}")


async def main():
    """Main async function demonstrating real-time data management."""
    # Create async client
    async with AsyncProjectX.from_env() as client:
        # Authenticate
        await client.authenticate()
        print(f"✅ Authenticated as {client.account_info.name}")

        # Get JWT token for real-time connection
        jwt_token = client.session_token
        account_id = client.account_info.id

        # Create async realtime client (placeholder for now)
        realtime_client = AsyncProjectXRealtimeClient(jwt_token, account_id)

        # Create data manager for multiple timeframes
        data_manager = AsyncRealtimeDataManager(
            instrument="MGC",
            project_x=client,
            realtime_client=realtime_client,
            timeframes=["5sec", "1min", "5min", "15min"],
        )

        # 1. Initialize with historical data
        print("\n📚 Loading historical data...")
        if await data_manager.initialize(initial_days=5):
            print("✅ Historical data loaded successfully")

            # Show loaded data stats
            stats = data_manager.get_memory_stats()
            print("\nData loaded per timeframe:")
            for tf, count in stats["timeframe_bar_counts"].items():
                print(f"  {tf}: {count} bars")
        else:
            print("❌ Failed to load historical data")
            return

        # 2. Get current OHLCV data
        print("\n📈 Current OHLCV Data:")
        for timeframe in ["1min", "5min"]:
            data = await data_manager.get_data(timeframe, bars=5)
            if data is not None and not data.is_empty():
                latest = data.tail(1)
                print(
                    f"  {timeframe}: O={latest['open'][0]:.2f}, "
                    f"H={latest['high'][0]:.2f}, L={latest['low'][0]:.2f}, "
                    f"C={latest['close'][0]:.2f}, V={latest['volume'][0]}"
                )

        # 3. Get current price
        current_price = await data_manager.get_current_price()
        if current_price:
            print(f"\n💰 Current price: ${current_price:.2f}")

        # 4. Register callbacks for real-time events
        print("\n🔔 Registering event callbacks...")
        await data_manager.add_callback("new_bar", on_new_bar)
        await data_manager.add_callback("data_update", on_data_update)
        print("  Callbacks registered for new bars and price updates")

        # 5. Start real-time feed
        print("\n🚀 Starting real-time data feed...")
        if await data_manager.start_realtime_feed():
            print("✅ Real-time feed active")
        else:
            print("❌ Failed to start real-time feed")
            return

        # 6. Simulate real-time updates (for demo)
        print("\n📡 Simulating real-time data...")
        print("(In production, these would come from WebSocket)")

        # Simulate quote update
        await data_manager._on_quote_update(
            {
                "contractId": data_manager.contract_id,
                "bidPrice": 2045.50,
                "askPrice": 2046.00,
            }
        )

        # Simulate trade update
        await data_manager._on_trade_update(
            {"contractId": data_manager.contract_id, "price": 2045.75, "size": 5}
        )

        # 7. Get multi-timeframe data
        print("\n🔄 Multi-timeframe analysis:")
        mtf_data = await data_manager.get_mtf_data()
        for tf, df in mtf_data.items():
            if not df.is_empty():
                latest = df.tail(1)
                print(f"  {tf}: Close=${latest['close'][0]:.2f}")

        # 8. Show memory statistics
        print("\n💾 Memory Statistics:")
        mem_stats = data_manager.get_memory_stats()
        print(f"  Total bars: {mem_stats['total_bars']}")
        print(f"  Ticks processed: {mem_stats['ticks_processed']}")
        print(f"  Bars cleaned: {mem_stats['bars_cleaned']}")

        # 9. Validation status
        print("\n✅ Validation Status:")
        status = data_manager.get_realtime_validation_status()
        print(f"  Feed running: {status['is_running']}")
        print(f"  Contract ID: {status['contract_id']}")
        print(f"  Compliance: {status['projectx_compliance']}")

        # 10. Stop real-time feed
        print("\n🛑 Stopping real-time feed...")
        await data_manager.stop_realtime_feed()
        print("  Feed stopped")

        # Example of using data for strategy
        print("\n💡 Strategy Example:")
        print("  # Get data for analysis")
        print("  data_5min = await manager.get_data('5min', bars=100)")
        print("  # Calculate indicators")
        print("  data_5min = data_5min.pipe(SMA, period=20)")
        print("  data_5min = data_5min.pipe(RSI, period=14)")
        print("  # Make trading decisions based on real-time data")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
