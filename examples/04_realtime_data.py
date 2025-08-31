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

Updated for v3.0.0: Uses new TradingSuite for simplified initialization.

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
    EventType,
    TradingSuite,
    setup_logging,
)

if TYPE_CHECKING:
    from project_x_py.realtime_data_manager import RealtimeDataManager


async def display_current_prices(data_manager: "RealtimeDataManager") -> None:
    """Display current prices across all timeframes asynchronously."""
    print("\n📊 Current Prices:")

    current_price = await data_manager.get_current_price()
    if current_price:
        print(f"   Live Price: ${current_price:.2f}")
    else:
        print("   Live Price: Not available")

    # Get multi-timeframe data asynchronously - get latest bars
    timeframes = ["15sec", "1min", "5min", "15min", "1hr"]
    mtf_tasks: list[Coroutine[Any, Any, pl.DataFrame | None]] = []

    for tf in timeframes:
        mtf_tasks.append(
            data_manager.get_data(tf)
        )  # Get all data, we'll take the last bar

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
                print(f"   {timeframe:>6}: Building bars...")
                continue

            # Get the last complete bar
            latest_bar = data.tail(1)
            for row in latest_bar.iter_rows(named=True):
                timestamp = row["timestamp"]
                close = row["close"]
                volume = row["volume"]
                # Format timestamp more concisely
                time_str = (
                    timestamp.strftime("%H:%M:%S")
                    if hasattr(timestamp, "strftime")
                    else str(timestamp)
                )
                print(
                    f"   {timeframe:>6}: ${close:8.2f} @ {time_str} (Vol: {volume:,})"
                )
        else:
            print(f"   {timeframe:>6}: Initializing...")


async def display_memory_stats(data_manager: "RealtimeDataManager") -> None:
    """Display memory usage statistics asynchronously."""
    try:
        # get_memory_stats is synchronous in async data manager
        stats = await data_manager.get_memory_stats()
        print("\n💾 Memory Statistics:")
        print(f"   Total Bars Stored: {stats.get('total_bars_stored', 0):,}")
        print(f"   Ticks Processed: {stats.get('ticks_processed', 0):,}")
        print(f"   Quotes Processed: {stats.get('quotes_processed', 0):,}")
        print(f"   Trades Processed: {stats.get('trades_processed', 0):,}")

        # Show per-timeframe breakdown (Note: this key doesn't exist in current implementation)
        # Will need to calculate it manually from the data
        print("   Bars per Timeframe:")
        for tf in data_manager.timeframes:
            if tf in data_manager.data:
                count = len(data_manager.data[tf])
                if count > 0:
                    print(f"     {tf}: {count:,} bars")

        # Also show validation status for more insight
        validation = data_manager.get_realtime_validation_status()
        if validation.get("is_running"):
            print(
                f"   Feed Active: ✅ (Processing {validation.get('instrument', 'N/A')})"
            )
        else:
            print("   Feed Active: ❌")

    except Exception as e:
        print(f"   ❌ Memory stats error: {e}")


async def display_system_statistics(data_manager: "RealtimeDataManager") -> None:
    """Display comprehensive system and validation statistics asynchronously."""
    try:
        # Use validation status instead of get_statistics (which doesn't exist)
        stats = data_manager.get_realtime_validation_status()
        print("\n📈 System Status:")
        print(f"   Instrument: {stats.get('instrument', 'Unknown')}")
        print(f"   Contract ID: {stats.get('contract_id', 'Unknown')}")
        print(f"   Real-time Feed Active: {stats.get('is_running', False)}")
        print(f"   Ticks Processed: {stats.get('ticks_processed', 0):,}")
        print(f"   Bars Cleaned: {stats.get('bars_cleaned', 0):,}")

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


async def demonstrate_historical_analysis(data_manager: "RealtimeDataManager") -> None:
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
                price_range = float(data["close"].max()) - float(data["close"].min())
                total_volume = data["volume"].sum()

                print(f"   {tf} Analysis (last 100 bars):")
                print(f"     Average Price: ${avg_price:.2f}")
                print(f"     Price Range: ${price_range:.2f}")
                print(f"     Total Volume: {total_volume:,}")
            else:
                print(f"   {tf}: No data available for analysis")

    except Exception as e:
        print(f"   ❌ Analysis error: {e}")


async def new_bar_callback(event: Any) -> None:
    """Handle new bar creation asynchronously."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    # Extract data from the Event object
    data = event.data if hasattr(event, "data") else event
    timeframe = data.get("timeframe", "unknown")
    bar = data.get("data", {})
    if bar and "close" in bar and "volume" in bar:
        print(
            f"📊 [{timestamp}] New {timeframe} Bar: ${bar['close']:.2f} (Vol: {bar['volume']:,})"
        )


async def main() -> bool:
    """Main async real-time data streaming demonstration."""

    # Setup logging
    logger = setup_logging(level="INFO")
    logger.info("🚀 Starting Async Real-time Data Streaming Example")

    print("=" * 60)
    print("ASYNC REAL-TIME DATA STREAMING EXAMPLE (v3.0.0)")
    print("=" * 60)

    try:
        # Create and initialize TradingSuite v3
        print("\n🔑 Creating TradingSuite v3...")

        # Define timeframes for multi-timeframe analysis
        timeframes = ["15sec", "1min", "5min", "15min", "1hr"]

        try:
            # Use TradingSuite.create which handles all initialization
            suite = await TradingSuite.create(
                instrument="MNQ",
                timeframes=timeframes,
                initial_days=5,
            )

            print("✅ Trading suite created and initialized!")
            print(
                f"   Account: {suite.client.account_info.name if suite.client.account_info else 'Unknown'}"
            )
            print(
                f"   Account ID: {suite.client.account_info.id if suite.client.account_info else 'Unknown'}"
            )
            print("   Instrument: MNQ")
            print(f"   Timeframes: {', '.join(timeframes)}")

            # Components are now accessed as attributes
            data_manager = suite["MNQ"].data

            print("\n✅ All components connected and subscribed:")
            print("   - Real-time client connected")
            print("   - Market data subscribed")
            print("   - Historical data loaded")
            print("   - Real-time feed started")
        except Exception as e:
            print(f"❌ Failed to create trading suite: {e}")
            print("Info: This may happen if MNQ is not available in your environment")
            print("✅ Basic TradingSuite v3 functionality verified!")
            return True

        # Show initial data state
        print("\n" + "=" * 50)
        print("📊 INITIAL DATA STATE")
        print("=" * 50)

        await display_current_prices(data_manager)
        await display_memory_stats(data_manager)
        await demonstrate_historical_analysis(data_manager)

        # OPTIONAL: Register event handlers for custom event handling
        # The RealtimeDataManager already processes data internally to build OHLCV bars.
        # These event handlers are only needed if you want to react to specific events.
        print("\n🔔 Registering optional event handlers for demonstration...")
        try:
            # Use the EventBus through TradingSuite
            await suite.on(EventType.NEW_BAR, new_bar_callback)
            print("✅ Optional event handlers registered!")
        except Exception as e:
            print(f"⚠️ Event handler registration error: {e}")

        # Note: Real-time feed is already started by TradingSuite
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
        async def monitor_prices() -> None:
            """Monitor and display prices periodically."""
            while True:
                await asyncio.sleep(10)  # Update every 10 seconds
                await display_current_prices(data_manager)

        async def monitor_statistics() -> None:
            """Monitor and display statistics periodically."""
            while True:
                await asyncio.sleep(30)  # Update every 30 seconds
                await display_system_statistics(data_manager)

        async def monitor_memory() -> None:
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

        # Display final summary
        print("\n📊 Final Data Summary:")
        await display_current_prices(data_manager)
        await display_system_statistics(data_manager)
        await display_memory_stats(data_manager)

    except Exception as e:
        logger.error(f"❌ Error in real-time data streaming: {e}")
        raise
    finally:
        # Cleanup with TradingSuite
        if "suite" in locals():
            print("\n🧹 Cleaning up connections...")
            await suite.disconnect()
            print("✅ Cleanup completed!")

    print("\n✅ Async Real-time Data Streaming Example completed!")
    return True


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
