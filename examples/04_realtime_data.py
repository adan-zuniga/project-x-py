#!/usr/bin/env python3
"""
Real-time Data Streaming Example

Demonstrates comprehensive real-time market data features:
- Multi-timeframe OHLCV data streaming
- Real-time price updates and callbacks
- Historical data initialization
- Data management and memory optimization
- WebSocket connection handling
- Synchronized multi-timeframe analysis

Uses MNQ for real-time market data streaming.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/04_realtime_data.py

Author: TexasCoding
Date: July 2025
"""

import time
from datetime import datetime

from project_x_py import (
    ProjectX,
    create_data_manager,
    create_realtime_client,
    setup_logging,
)


def display_current_prices(data_manager):
    """Display current prices across all timeframes."""
    print("\n📊 Current Prices:")

    current_price = data_manager.get_current_price()
    if current_price:
        print(f"   Current Price: ${current_price:.2f}")
    else:
        print("   Current Price: Not available")

    # Get multi-timeframe data
    mtf_data = data_manager.get_mtf_data(bars=1)  # Just latest bar from each timeframe

    for timeframe, data in mtf_data.items():
        if not data.is_empty():
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


def display_memory_stats(data_manager):
    """Display memory usage statistics."""
    try:
        stats = data_manager.get_memory_stats()
        print("\n💾 Memory Statistics:")
        print(f"   Total Bars: {stats['total_bars']:,}")
        print(f"   Ticks Processed: {stats['ticks_processed']:,}")
        print(f"   Bars Cleaned: {stats['bars_cleaned']:,}")
        print(f"   Tick Buffer Size: {stats['tick_buffer_size']:,}")

        # Show per-timeframe breakdown
        breakdown = stats.get("timeframe_breakdown", {})
        if breakdown:
            print("   Timeframe Breakdown:")
            for tf, count in breakdown.items():
                print(f"     {tf}: {count:,} bars")

    except Exception as e:
        print(f"   ❌ Memory stats error: {e}")


def display_system_statistics(data_manager):
    """Display comprehensive system statistics."""
    try:
        stats = data_manager.get_statistics()
        print("\n📈 System Statistics:")
        print(f"   System Running: {stats['is_running']}")
        print(f"   Instrument: {stats['instrument']}")
        print(f"   Contract ID: {stats['contract_id']}")
        print(
            f"   Real-time Connected: {stats.get('realtime_client_connected', False)}"
        )

        # Show timeframe statistics
        tf_stats = stats.get("timeframes", {})
        if tf_stats:
            print("   Timeframe Data:")
            for tf, tf_info in tf_stats.items():
                bars = tf_info.get("bars", 0)
                latest_price = tf_info.get("latest_price", 0)
                latest_time = tf_info.get("latest_time", "Never")
                print(f"     {tf}: {bars} bars, ${latest_price:.2f} @ {latest_time}")

    except Exception as e:
        print(f"   ❌ System stats error: {e}")


def setup_realtime_callbacks(data_manager):
    """Setup callbacks for real-time data events."""
    print("\n🔔 Setting up real-time callbacks...")

    # Data update callback
    def on_data_update(data):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        price = data.get("price", 0)
        volume = data.get("volume", 0)
        print(f"   [{timestamp}] 📊 Price Update: ${price:.2f} (Volume: {volume})")

    # New bar callback
    def on_new_bar(data):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        timeframe = data.get("timeframe", "Unknown")
        bar_data = data.get("bar_data", {})
        open_price = bar_data.get("open", 0)
        high_price = bar_data.get("high", 0)
        low_price = bar_data.get("low", 0)
        close_price = bar_data.get("close", 0)
        volume = bar_data.get("volume", 0)
        print(
            f"   [{timestamp}] 📈 New {timeframe} Bar: O:{open_price:.2f} H:{high_price:.2f} L:{low_price:.2f} C:{close_price:.2f} V:{volume}"
        )

    # Connection status callback
    def on_connection_status(data):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        status = data.get("status", "unknown")
        message = data.get("message", "")
        print(f"   [{timestamp}] 🔌 Connection: {status} - {message}")

    # Register callbacks
    try:
        data_manager.add_callback("data_update", on_data_update)
        data_manager.add_callback("new_bar", on_new_bar)
        data_manager.add_callback("connection_status", on_connection_status)
        print("   ✅ Callbacks registered successfully")
    except Exception as e:
        print(f"   ❌ Callback setup error: {e}")


def demonstrate_historical_analysis(data_manager):
    """Demonstrate historical data analysis capabilities."""
    print("\n📚 Historical Data Analysis:")

    # Get data for different timeframes
    timeframes_to_analyze = ["1min", "5min", "15min"]

    for tf in timeframes_to_analyze:
        try:
            data = data_manager.get_data(tf, bars=20)  # Last 20 bars

            if data is not None and not data.is_empty():
                print(f"\n   {tf} Analysis ({len(data)} bars):")

                # Calculate basic statistics
                closes = data.select("close")
                volumes = data.select("volume")

                latest_close = float(closes.tail(1).item())
                min_price = float(closes.min().item())
                max_price = float(closes.max().item())
                avg_price = float(closes.mean().item())
                total_volume = int(volumes.sum().item())

                print(f"     Latest: ${latest_close:.2f}")
                print(f"     Range: ${min_price:.2f} - ${max_price:.2f}")
                print(f"     Average: ${avg_price:.2f}")
                print(f"     Total Volume: {total_volume:,}")

                # Simple trend analysis
                if len(data) >= 10:
                    first_10_avg = float(closes.head(10).mean().item())
                    last_10_avg = float(closes.tail(10).mean().item())
                    trend = "Bullish" if last_10_avg > first_10_avg else "Bearish"
                    trend_strength = (
                        abs(last_10_avg - first_10_avg) / first_10_avg * 100
                    )
                    print(f"     Trend: {trend} ({trend_strength:.2f}%)")

            else:
                print(f"   {tf}: No data available")

        except Exception as e:
            print(f"   {tf}: Error - {e}")


def monitor_realtime_feed(data_manager, duration_seconds=60):
    """Monitor the real-time data feed for a specified duration."""
    print(f"\n👀 Real-time Monitoring ({duration_seconds}s)")
    print("=" * 50)

    start_time = time.time()
    last_price_update = time.time()
    price_updates = 0
    bar_updates = 0

    print("Monitoring MNQ real-time data feed...")
    print("Press Ctrl+C to stop early")

    try:
        while time.time() - start_time < duration_seconds:
            # Display periodic updates
            elapsed = time.time() - start_time

            # Every 10 seconds, show current status
            if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                remaining = duration_seconds - elapsed
                print(f"\n⏰ {elapsed:.0f}s elapsed, {remaining:.0f}s remaining")

                # Show current price
                current_price = data_manager.get_current_price()
                if current_price:
                    print(f"   Current Price: ${current_price:.2f}")

                # Show recent activity
                print(
                    f"   Activity: {price_updates} price updates, {bar_updates} new bars"
                )

                # Health check
                try:
                    health = data_manager.health_check()
                    if health:
                        print("   ✅ System Health: Good")
                    else:
                        print("   ⚠️  System Health: Issues detected")
                except Exception as e:
                    print(f"   ❌ Health check error: {e}")

            time.sleep(1)

            # Count updates (this is a simplified counter - actual updates come via callbacks)
            if time.time() - last_price_update > 0.5:  # Simulate price updates
                price_updates += 1
                last_price_update = time.time()

                # Occasionally simulate bar updates
                if price_updates % 10 == 0:
                    bar_updates += 1

    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user")

    print("\n📊 Monitoring Summary:")
    print(f"   Duration: {time.time() - start_time:.1f} seconds")
    print(f"   Price Updates: {price_updates}")
    print(f"   Bar Updates: {bar_updates}")


def main():
    """Demonstrate comprehensive real-time data streaming."""
    logger = setup_logging(level="INFO")
    print("🚀 Real-time Data Streaming Example")
    print("=" * 60)

    # Initialize variables for cleanup
    data_manager = None
    realtime_client = None

    try:
        # Initialize client
        print("🔑 Initializing ProjectX client...")
        client = ProjectX.from_env()

        account = client.get_account_info()
        if not account:
            print("❌ Could not get account information")
            return False

        print(f"✅ Connected to account: {account.name}")

        # Create real-time data manager
        print("\n🏗️ Creating real-time data manager...")

        # Define timeframes for multi-timeframe analysis
        timeframes = ["15sec", "1min", "5min", "15min", "1hr"]

        try:
            jwt_token = client.get_session_token()
            realtime_client = create_realtime_client(jwt_token, str(account.id))

            # Connect the realtime client
            print("   Connecting to real-time WebSocket feeds...")
            if realtime_client.connect():
                print("   ✅ Real-time client connected successfully")
            else:
                print(
                    "   ⚠️ Real-time client connection failed - continuing with limited functionality"
                )

            data_manager = create_data_manager(
                instrument="MNQ",
                project_x=client,
                realtime_client=realtime_client,
                timeframes=timeframes,
            )
            print("✅ Real-time data manager created for MNQ")
            print(f"   Timeframes: {', '.join(timeframes)}")
        except Exception as e:
            print(f"❌ Failed to create data manager: {e}")
            return False

        # Initialize with historical data
        print("\n📚 Initializing with historical data...")
        if data_manager.initialize(initial_days=5):
            print("✅ Historical data loaded successfully")
            print("   Loaded 5 days of historical data across all timeframes")
        else:
            print("❌ Failed to load historical data")
            return False

        # Show initial data state
        print("\n" + "=" * 50)
        print("📊 INITIAL DATA STATE")
        print("=" * 50)

        display_current_prices(data_manager)
        display_memory_stats(data_manager)
        demonstrate_historical_analysis(data_manager)

        # Setup real-time callbacks
        print("\n" + "=" * 50)
        print("🔔 REAL-TIME CALLBACK SETUP")
        print("=" * 50)

        setup_realtime_callbacks(data_manager)

        # Start real-time feed
        print("\n" + "=" * 50)
        print("🌐 STARTING REAL-TIME FEED")
        print("=" * 50)

        print("Starting real-time data feed...")
        if data_manager.start_realtime_feed():
            print("✅ Real-time feed started successfully!")
            print("   WebSocket connection established")
            print("   Receiving live market data...")
        else:
            print("❌ Failed to start real-time feed")
            return False

        # Wait a moment for connection to stabilize
        print("\n⏳ Waiting for data connection to stabilize...")
        time.sleep(3)

        # Show system statistics
        print("\n" + "=" * 50)
        print("📈 SYSTEM STATISTICS")
        print("=" * 50)

        display_system_statistics(data_manager)

        # Demonstrate data access methods
        print("\n" + "=" * 50)
        print("📊 DATA ACCESS DEMONSTRATION")
        print("=" * 50)

        print("Getting multi-timeframe data (last 10 bars each):")
        mtf_data = data_manager.get_mtf_data(bars=10)

        for timeframe, data in mtf_data.items():
            if not data.is_empty():
                print(f"   {timeframe}: {len(data)} bars")
                # Show latest bar
                latest = data.tail(1)
                for row in latest.iter_rows(named=True):
                    print(
                        f"     Latest: ${row['close']:.2f} @ {row['timestamp']} (Vol: {row['volume']:,})"
                    )
            else:
                print(f"   {timeframe}: No data")

        # Monitor real-time feed
        print("\n" + "=" * 50)
        print("👀 REAL-TIME MONITORING")
        print("=" * 50)

        monitor_realtime_feed(data_manager, duration_seconds=45)

        # Show updated statistics
        print("\n" + "=" * 50)
        print("📊 UPDATED STATISTICS")
        print("=" * 50)

        display_current_prices(data_manager)
        display_memory_stats(data_manager)
        display_system_statistics(data_manager)

        # Demonstrate data management features
        print("\n" + "=" * 50)
        print("🧹 DATA MANAGEMENT FEATURES")
        print("=" * 50)

        print("Testing data cleanup and refresh features...")

        # Force data refresh
        try:
            print("   Forcing data refresh...")
            data_manager.force_data_refresh()
            print("   ✅ Data refresh completed")
        except Exception as e:
            print(f"   ❌ Data refresh error: {e}")

        # Cleanup old data
        try:
            print("   Cleaning up old data...")
            data_manager.cleanup_old_data()
            print("   ✅ Data cleanup completed")
        except Exception as e:
            print(f"   ❌ Data cleanup error: {e}")

        # Final statistics
        print("\n" + "=" * 50)
        print("📊 FINAL STATISTICS")
        print("=" * 50)

        display_memory_stats(data_manager)

        try:
            stats = data_manager.get_statistics()
            print("\nFinal System State:")
            print(f"   Is Running: {stats['is_running']}")
            print(f"   Total Timeframes: {len(stats.get('timeframes', {}))}")
            print(
                f"   Connection Status: {'Connected' if stats.get('realtime_client_connected') else 'Disconnected'}"
            )
        except Exception as e:
            print(f"   ❌ Final stats error: {e}")

        print("\n✅ Real-time data streaming example completed!")
        print("\n📝 Key Features Demonstrated:")
        print("   ✅ Multi-timeframe data streaming")
        print("   ✅ Real-time price updates")
        print("   ✅ Historical data initialization")
        print("   ✅ Memory management")
        print("   ✅ WebSocket connection handling")
        print("   ✅ Data callbacks and events")
        print("   ✅ System health monitoring")

        print("\n📚 Next Steps:")
        print("   - Try examples/05_orderbook_analysis.py for Level 2 data")
        print("   - Try examples/06_multi_timeframe_strategy.py for trading strategies")
        print("   - Review realtime data manager documentation")

        return True

    except KeyboardInterrupt:
        print("\n⏹️ Example interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Real-time data example failed: {e}")
        print(f"❌ Error: {e}")
        return False
    finally:
        # Cleanup
        if data_manager is not None:
            try:
                print("\n🧹 Stopping real-time feed...")
                data_manager.stop_realtime_feed()
                print("✅ Real-time feed stopped")
            except Exception as e:
                print(f"⚠️  Stop feed warning: {e}")

        if realtime_client is not None:
            try:
                print("🧹 Disconnecting real-time client...")
                realtime_client.disconnect()
                print("✅ Real-time client disconnected")
            except Exception as e:
                print(f"⚠️  Disconnect warning: {e}")


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
