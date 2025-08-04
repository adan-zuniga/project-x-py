#!/usr/bin/env python3
"""
Async Real-time Data Streaming Example

Demonstrates comprehensive async real-time market data features:
- Multi-timeframe OHLCV data streaming with async/await
- Real-time price updates and async callbacks
- Historical data initialization with concurrent loading
- Async data management and memory optimization
- WebSocket connection handling with asyncio
- Synchronized multi-timeframe analysis

Uses MNQ for real-time market data streaming with async processing.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/04_realtime_data.py

Author: TexasCoding
Date: July 2025
"""

import asyncio
from collections.abc import Coroutine
from datetime import datetime
from typing import TYPE_CHECKING, Any

import polars as pl

from project_x_py import (
    TradingSuite,
    setup_logging,
)

if TYPE_CHECKING:
    from project_x_py.realtime_data_manager import RealtimeDataManager


async def display_current_prices(data_manager: "RealtimeDataManager"):
    """Display current prices across all timeframes asynchronously."""
    print("\n📊 Current Prices:")

    current_price = await data_manager.get_current_price()
    if current_price:
        print(f"   Current Price: ${current_price:.2f}")
    else:
        print("   Current Price: Not available")

    # Get multi-timeframe data asynchronously - get 1 bar from each timeframe
    timeframes = ["15sec", "1min", "5min", "15min", "1hr"]
    mtf_tasks: list[Coroutine[Any, Any, pl.DataFrame | None]] = []

    for tf in timeframes:
        mtf_tasks.append(data_manager.get_data(tf, bars=1))

    # Get data from all timeframes concurrently
    mtf_results = await asyncio.gather(*mtf_tasks, return_exceptions=True)

    for i, timeframe in enumerate(timeframes):
        data = mtf_results[i]
        if isinstance(data, Exception):
            print(f"   {timeframe:>6}: Error - {data}")
        elif data is not None:
            if not isinstance(data, pl.DataFrame):
                print(f"   {timeframe:>6}: Invalid data type - {type(data)}")
                continue

            if data.is_empty():
                print(f"   {timeframe:>6}: No data")
                continue

            latest_bar = data.tail(1)
            for row in latest_bar.iter_rows(named=True):
                timestamp = row["timestamp"]
                close = row["close"]
                volume = row["volume"]
                print(
                    f"   {timeframe:>6}: ${close:8.2f} @ {timestamp} (Vol: {volume:,})"
                )
        else:
            print(f"   {timeframe:>6}: No data")


async def display_memory_stats(data_manager):
    """Display memory usage statistics asynchronously."""
    try:
        # get_memory_stats is synchronous in async data manager
        stats = data_manager.get_memory_stats()
        print("\n💾 Memory Statistics:")
        print(f"   Total Bars: {stats.get('total_bars', 0):,}")
        print(f"   Ticks Processed: {stats.get('ticks_processed', 0):,}")
        print(f"   Bars Cleaned: {stats.get('bars_cleaned', 0):,}")
        print(f"   Tick Buffer Size: {stats.get('tick_buffer_size', 0):,}")

        # Show per-timeframe breakdown
        breakdown = stats.get("timeframe_breakdown", {})
        if breakdown:
            print("   Timeframe Breakdown:")
            for tf, count in breakdown.items():
                print(f"     {tf}: {count:,} bars")

    except Exception as e:
        print(f"   ❌ Memory stats error: {e}")


async def display_system_statistics(data_manager):
    """Display comprehensive system and validation statistics asynchronously."""
    try:
        # Use validation status instead of get_statistics (which doesn't exist)
        stats = data_manager.get_realtime_validation_status()
        print("\n📈 System Status:")
        print(f"   Instrument: {getattr(data_manager, 'instrument', 'Unknown')}")
        print(f"   Contract ID: {getattr(data_manager, 'contract_id', 'Unknown')}")
        print(f"   Real-time Enabled: {stats.get('realtime_enabled', False)}")
        print(f"   Connection Valid: {stats.get('connection_valid', False)}")
        print(f"   Data Valid: {stats.get('data_valid', False)}")

        # Show data status per timeframe
        print("   Timeframe Status:")
        for tf in ["15sec", "1min", "5min", "15min", "1hr"]:
            try:
                data = await data_manager.get_data(tf)
                if (
                    data is not None
                    and hasattr(data, "is_empty")
                    and not data.is_empty()
                ):
                    print(f"     {tf}: {len(data):,} bars available")
                else:
                    print(f"     {tf}: No data")
            except Exception as e:
                print(f"     {tf}: Error - {e}")

    except Exception as e:
        print(f"   ❌ System stats error: {e}")


async def demonstrate_historical_analysis(data_manager):
    """Demonstrate historical data analysis asynchronously."""
    print("\n📈 Historical Data Analysis:")

    try:
        # Get data for different timeframes concurrently
        data_tasks = []
        timeframes = ["1min", "5min", "15min"]

        for tf in timeframes:
            data_tasks.append(data_manager.get_data(tf, bars=100))

        # Wait for all data concurrently
        data_results = await asyncio.gather(*data_tasks)

        for i, tf in enumerate(timeframes):
            data = data_results[i]
            if data is not None and not data.is_empty():
                # Calculate basic statistics
                avg_price = data["close"].mean()
                price_range = data["close"].max() - data["close"].min()
                total_volume = data["volume"].sum()

                print(f"   {tf} Analysis (last 100 bars):")
                print(f"     Average Price: ${avg_price:.2f}")
                print(f"     Price Range: ${price_range:.2f}")
                print(f"     Total Volume: {total_volume:,}")
            else:
                print(f"   {tf}: No data available for analysis")

    except Exception as e:
        print(f"   ❌ Analysis error: {e}")


async def new_bar_callback(data):
    """Handle new bar creation asynchronously."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    timeframe = data["timeframe"]
    bar = data["data"]
    print(
        f"📊 [{timestamp}] New {timeframe} Bar: ${bar['close']:.2f} (Vol: {bar['volume']:,})"
    )


async def main():
    """Main async real-time data streaming demonstration."""

    # Setup logging
    logger = setup_logging(level="INFO")
    logger.info("🚀 Starting Async Real-time Data Streaming Example")

    print("=" * 60)
    print("ASYNC REAL-TIME DATA STREAMING EXAMPLE")
    print("=" * 60)

    try:
        # Create async client from environment
        print("\n🔑 Creating ProjectX client from environment...")
        async with ProjectX.from_env() as client:
            print("✅ Async client created successfully!")

            # Authenticate
            print("\n🔐 Authenticating...")
            await client.authenticate()
            print("✅ Authentication successful!")

            if client.account_info is None:
                print("❌ No account information available")
                return False

            print(f"   Account: {client.account_info.name}")
            print(f"   Account ID: {client.account_info.id}")

            # Create and initialize trading suite with all components
            print("\n🏗️ Creating and initializing trading suite...")

            # Define timeframes for multi-timeframe analysis
            timeframes = ["15sec", "1min", "5min", "15min", "1hr"]

            try:
                # Use create_initialized_trading_suite which handles all initialization
                suite = await create_initialized_trading_suite(
                    instrument="MNQ",
                    project_x=client,
                    timeframes=timeframes,
                    enable_orderbook=False,  # Don't need orderbook for this example
                    initial_days=5,
                )

                print("✅ Trading suite created and initialized!")
                print("   Instrument: MNQ")
                print(f"   Timeframes: {', '.join(timeframes)}")

                # Extract components from the suite
                data_manager = suite["data_manager"]
                realtime_client = suite["realtime_client"]

                print("\n✅ All components connected and subscribed:")
                print("   - Real-time client connected")
                print("   - Market data subscribed")
                print("   - Historical data loaded")
                print("   - Real-time feed started")
            except Exception as e:
                print(f"❌ Failed to create trading suite: {e}")
                print(
                    "Info: This may happen if MNQ is not available in your environment"
                )
                print("✅ Basic async client functionality verified!")
                return True

            # Show initial data state
            print("\n" + "=" * 50)
            print("📊 INITIAL DATA STATE")
            print("=" * 50)

            await display_current_prices(data_manager)
            await display_memory_stats(data_manager)
            await demonstrate_historical_analysis(data_manager)

            # OPTIONAL: Register callbacks for custom event handling
            # The RealtimeDataManager already processes data internally to build OHLCV bars.
            # These callbacks are only needed if you want to react to specific events.
            print("\n🔔 Registering optional callbacks for demonstration...")
            try:
                # Note: "data_update" callback is not actually triggered by the current implementation
                # Only "new_bar" events are currently supported for external callbacks
                await data_manager.add_callback("new_bar", new_bar_callback)
                print("✅ Optional callbacks registered!")
            except Exception as e:
                print(f"⚠️ Callback registration error: {e}")

            # Note: Real-time feed is already started by create_initialized_trading_suite
            # The data manager is already receiving and processing quotes to build OHLCV bars

            print("\n" + "=" * 60)
            print("📡 REAL-TIME DATA STREAMING ACTIVE")
            print("=" * 60)
            print("🔔 Listening for price updates...")
            print("📊 Watching for bar completions...")
            print("⏱️ Updates will appear below...")
            print("\nPress Ctrl+C to stop streaming")
            print("=" * 60)

            # Create concurrent monitoring tasks
            async def monitor_prices():
                """Monitor and display prices periodically."""
                while True:
                    await asyncio.sleep(10)  # Update every 10 seconds
                    await display_current_prices(data_manager)

            async def monitor_statistics():
                """Monitor and display statistics periodically."""
                while True:
                    await asyncio.sleep(30)  # Update every 30 seconds
                    await display_system_statistics(data_manager)

            async def monitor_memory():
                """Monitor and display memory usage periodically."""
                while True:
                    await asyncio.sleep(60)  # Update every minute
                    await display_memory_stats(data_manager)

            # Run monitoring tasks concurrently
            try:
                await asyncio.gather(
                    monitor_prices(),
                    monitor_statistics(),
                    monitor_memory(),
                    return_exceptions=True,
                )
            except KeyboardInterrupt:
                print("\n🛑 Stopping real-time data stream...")
            except asyncio.CancelledError:
                print("\n🛑 Real-time data stream cancelled...")
            except Exception as e:
                print(f"\n❌ Error in monitoring: {e}")

            # Cleanup
            print("\n🧹 Cleaning up connections...")
            try:
                await data_manager.stop_realtime_feed()
                await realtime_client.disconnect()
                print("✅ Cleanup completed!")
            except Exception as e:
                print(f"⚠️ Cleanup warning: {e}")

            # Display final summary
            print("\n📊 Final Data Summary:")
            await display_current_prices(data_manager)
            await display_system_statistics(data_manager)
            await display_memory_stats(data_manager)

    except Exception as e:
        logger.error(f"❌ Error in real-time data streaming: {e}")
        raise

    print("\n✅ Async Real-time Data Streaming Example completed!")
    return True


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
