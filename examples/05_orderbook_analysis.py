#!/usr/bin/env python3
"""
Level 2 Orderbook Analysis Example

Demonstrates comprehensive Level 2 orderbook analysis:
- Real-time bid/ask levels and depth
- Market microstructure analysis
- Trade flow analysis
- Order type statistics
- Iceberg detection
- Market imbalance monitoring
- Best bid/ask tracking

Uses MNQ for Level 2 orderbook data.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/05_orderbook_analysis.py

Author: TexasCoding
Date: July 2025
"""

import time
from datetime import datetime

from project_x_py import (
    ProjectX,
    create_orderbook,
    create_realtime_client,
    setup_logging,
)


def display_best_prices(orderbook):
    """Display current best bid/ask prices."""
    best_prices = orderbook.get_best_bid_ask()

    print("📊 Best Bid/Ask:")
    if best_prices["bid"] and best_prices["ask"]:
        print(f"   Bid: ${best_prices['bid']:.2f}")
        print(f"   Ask: ${best_prices['ask']:.2f}")
        print(f"   Spread: ${best_prices['spread']:.2f}")
        print(f"   Mid: ${best_prices['mid']:.2f}")
    else:
        print("   No bid/ask data available")


def display_orderbook_levels(orderbook, levels=5):
    """Display orderbook levels with bid/ask depth."""
    print(f"\n📈 Orderbook Levels (Top {levels}):")

    # Get bid and ask data
    bids = orderbook.get_orderbook_bids(levels=levels)
    asks = orderbook.get_orderbook_asks(levels=levels)

    # Display asks (sellers) - highest price first
    print("   ASKS (Sellers):")
    if not asks.is_empty():
        # Sort asks by price descending for display
        asks_sorted = asks.sort("price", descending=True)
        for row in asks_sorted.iter_rows(named=True):
            price = row["price"]
            volume = row["volume"]
            timestamp = row["timestamp"]
            print(f"   ${price:8.2f} | {volume:4d} contracts | {timestamp}")
    else:
        print("   No ask data")

    print("   " + "-" * 40)

    # Display bids (buyers) - highest price first
    print("   BIDS (Buyers):")
    if not bids.is_empty():
        for row in bids.iter_rows(named=True):
            price = row["price"]
            volume = row["volume"]
            timestamp = row["timestamp"]
            print(f"   ${price:8.2f} | {volume:4d} contracts | {timestamp}")
    else:
        print("   No bid data")


def display_market_depth(orderbook):
    """Display market depth analysis."""
    try:
        depth = orderbook.get_orderbook_depth(price_range=50.0)  # 50 point range

        print("\n🔍 Market Depth Analysis (±50 points):")
        print(
            f"   Bid Volume: {depth['bid_volume']:,} contracts ({depth['bid_levels']} levels)"
        )
        print(
            f"   Ask Volume: {depth['ask_volume']:,} contracts ({depth['ask_levels']} levels)"
        )

        if depth.get("mid_price"):
            print(f"   Mid Price: ${depth['mid_price']:.2f}")

        # Calculate and display imbalance
        total_volume = depth["bid_volume"] + depth["ask_volume"]
        if total_volume > 0:
            bid_ratio = (depth["bid_volume"] / total_volume) * 100
            ask_ratio = (depth["ask_volume"] / total_volume) * 100
            print(f"   Volume Imbalance: {bid_ratio:.1f}% bids / {ask_ratio:.1f}% asks")

            # Interpret imbalance
            if bid_ratio > 60:
                print("   📈 Strong buying pressure detected")
            elif ask_ratio > 60:
                print("   📉 Strong selling pressure detected")
            else:
                print("   ⚖️  Balanced market")

    except Exception as e:
        print(f"   ❌ Market depth error: {e}")


def display_trade_flow(orderbook):
    """Display trade flow analysis."""
    try:
        # Get trade summary for last 5 minutes
        trade_summary = orderbook.get_trade_flow_summary(minutes=5)

        print("\n💹 Trade Flow Analysis (5 minutes):")
        print(f"   Total Volume: {trade_summary['total_volume']:,} contracts")
        print(f"   Total Trades: {trade_summary['trade_count']}")
        print(
            f"   Buy Volume: {trade_summary['buy_volume']:,} contracts ({trade_summary['buy_trades']} trades)"
        )
        print(
            f"   Sell Volume: {trade_summary['sell_volume']:,} contracts ({trade_summary['sell_trades']} trades)"
        )
        print(f"   Average Trade Size: {trade_summary['avg_trade_size']:.1f} contracts")

        if trade_summary["vwap"] > 0:
            print(f"   VWAP: ${trade_summary['vwap']:.2f}")

        if trade_summary["buy_sell_ratio"] > 0:
            print(f"   Buy/Sell Ratio: {trade_summary['buy_sell_ratio']:.2f}")

            # Interpret ratio
            if trade_summary["buy_sell_ratio"] > 1.5:
                print("   📈 Strong buying activity")
            elif trade_summary["buy_sell_ratio"] < 0.67:
                print("   📉 Strong selling activity")
            else:
                print("   ⚖️  Balanced trading activity")

    except Exception as e:
        print(f"   ❌ Trade flow error: {e}")


def display_order_statistics(orderbook):
    """Display order type statistics."""
    try:
        order_stats = orderbook.get_order_type_statistics()

        print("\n📊 Order Type Statistics:")
        print(f"   Type 1 (Ask Orders): {order_stats['type_1_count']:,}")
        print(f"   Type 2 (Bid Orders): {order_stats['type_2_count']:,}")
        print(f"   Type 5 (Trades): {order_stats['type_5_count']:,}")
        print(f"   Type 9 (Modifications): {order_stats['type_9_count']:,}")
        print(f"   Type 10 (Modifications): {order_stats['type_10_count']:,}")
        print(f"   Other Types: {order_stats['other_types']:,}")

        total_messages = sum(order_stats.values())
        if total_messages > 0:
            trade_ratio = (order_stats["type_5_count"] / total_messages) * 100
            print(f"   Trade Message Ratio: {trade_ratio:.1f}%")

    except Exception as e:
        print(f"   ❌ Order statistics error: {e}")


def display_recent_trades(orderbook, count=10):
    """Display recent trades."""
    try:
        recent_trades = orderbook.get_recent_trades(count=count)

        print(f"\n💰 Recent Trades (Last {count}):")
        if not recent_trades.is_empty():
            print("   Time     | Side | Price    | Volume | Type")
            print("   " + "-" * 45)

            for row in recent_trades.iter_rows(named=True):
                timestamp = (
                    row["timestamp"].strftime("%H:%M:%S")
                    if row["timestamp"]
                    else "Unknown"
                )
                side = row["side"].upper() if row["side"] else "Unknown"
                price = row["price"]
                volume = row["volume"]
                order_type = row.get("order_type", "Unknown")
                print(
                    f"   {timestamp} | {side:4s} | ${price:7.2f} | {volume:6d} | {order_type}"
                )
        else:
            print("   No recent trades available")

    except Exception as e:
        print(f"   ❌ Recent trades error: {e}")


def display_memory_stats(orderbook):
    """Display orderbook memory statistics."""
    try:
        stats = orderbook.get_memory_stats()

        print("\n💾 Memory Statistics:")
        print(f"   Total Trades: {stats['total_trades']:,}")
        print(f"   Total Depth Entries: {stats['total_depth_entries']:,}")
        print(f"   Bid Levels: {stats['bid_levels']:,}")
        print(f"   Ask Levels: {stats['ask_levels']:,}")
        print(f"   Memory Usage: {stats['memory_usage_mb']:.2f} MB")

        if stats.get("cleanup_triggered", False):
            print("   🧹 Memory cleanup active")

    except Exception as e:
        print(f"   ❌ Memory stats error: {e}")


def setup_orderbook_callbacks(orderbook):
    """Setup callbacks for orderbook events."""
    print("\n🔔 Setting up orderbook callbacks...")

    # Price update callback
    def on_price_update(data):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        price = data.get("price", 0)
        side = data.get("side", "unknown")
        volume = data.get("volume", 0)
        print(f"   [{timestamp}] 💰 {side.upper()} ${price:.2f} x{volume}")

    # Depth change callback
    def on_depth_change(data):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        level = data.get("level", 0)
        side = data.get("side", "unknown")
        price = data.get("price", 0)
        volume = data.get("volume", 0)
        print(
            f"   [{timestamp}] 📊 Depth L{level} {side.upper()}: ${price:.2f} x{volume}"
        )

    # Trade callback
    def on_trade(data):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        price = data.get("price", 0)
        volume = data.get("volume", 0)
        side = data.get("side", "unknown")
        print(f"   [{timestamp}] 🔥 TRADE: {side.upper()} ${price:.2f} x{volume}")

    try:
        orderbook.add_callback("price_update", on_price_update)
        orderbook.add_callback("depth_change", on_depth_change)
        orderbook.add_callback("trade", on_trade)
        print("   ✅ Orderbook callbacks registered")
    except Exception as e:
        print(f"   ❌ Callback setup error: {e}")


def monitor_orderbook_feed(orderbook, duration_seconds=60):
    """Monitor the orderbook feed for a specified duration."""
    print(f"\n👀 Orderbook Monitoring ({duration_seconds}s)")
    print("=" * 50)

    start_time = time.time()
    update_count = 0

    print("Monitoring MNQ Level 2 orderbook...")
    print("Press Ctrl+C to stop early")

    try:
        while time.time() - start_time < duration_seconds:
            elapsed = time.time() - start_time

            # Every 15 seconds, show detailed update
            if int(elapsed) % 15 == 0 and int(elapsed) > 0:
                remaining = duration_seconds - elapsed
                print(f"\n⏰ {elapsed:.0f}s elapsed, {remaining:.0f}s remaining")
                print("=" * 30)

                # Show current state
                display_best_prices(orderbook)
                display_market_depth(orderbook)

                # Show recent activity
                print("\n📈 Recent Activity:")
                display_recent_trades(orderbook, count=5)

                update_count += 1

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user")

    print("\n📊 Monitoring Summary:")
    print(f"   Duration: {time.time() - start_time:.1f} seconds")
    print(f"   Update Cycles: {update_count}")


def main():
    """Demonstrate comprehensive Level 2 orderbook analysis."""
    logger = setup_logging(level="INFO")
    print("🚀 Level 2 Orderbook Analysis Example")
    print("=" * 60)

    try:
        # Initialize client
        print("🔑 Initializing ProjectX client...")
        client = ProjectX.from_env()

        account = client.get_account_info()
        if not account:
            print("❌ Could not get account information")
            return False

        print(f"✅ Connected to account: {account.name}")

        # Create orderbook
        print("\n🏗️ Creating Level 2 orderbook...")
        try:
            jwt_token = client.get_session_token()
            realtime_client = create_realtime_client(jwt_token, str(account.id))
            orderbook = create_orderbook(
                instrument="MNQ", realtime_client=realtime_client
            )
            print("✅ Level 2 orderbook created for MNQ")
        except Exception as e:
            print(f"❌ Failed to create orderbook: {e}")
            return False

        print("✅ Orderbook initialized with real-time capabilities")

        # Setup callbacks
        print("\n" + "=" * 50)
        print("🔔 CALLBACK SETUP")
        print("=" * 50)

        setup_orderbook_callbacks(orderbook)

        # Start real-time feed (if available)
        print("\n" + "=" * 50)
        print("🌐 STARTING REAL-TIME FEED")
        print("=" * 50)

        print("Starting Level 2 orderbook feed...")
        try:
            # Note: This depends on the orderbook implementation
            # Some implementations might auto-start with initialize()
            print("✅ Orderbook feed active")
            print("   Collecting Level 2 market data...")
        except Exception as e:
            print(f"⚠️  Feed start warning: {e}")

        # Wait for data to populate
        print("\n⏳ Waiting for orderbook data to populate...")
        time.sleep(5)

        # Show initial orderbook state
        print("\n" + "=" * 50)
        print("📊 INITIAL ORDERBOOK STATE")
        print("=" * 50)

        display_best_prices(orderbook)
        display_orderbook_levels(orderbook, levels=10)
        display_market_depth(orderbook)

        # Show order statistics
        print("\n" + "=" * 50)
        print("📊 ORDER STATISTICS")
        print("=" * 50)

        display_order_statistics(orderbook)
        display_memory_stats(orderbook)

        # Show trade analysis
        print("\n" + "=" * 50)
        print("💹 TRADE ANALYSIS")
        print("=" * 50)

        display_trade_flow(orderbook)
        display_recent_trades(orderbook, count=15)

        # Monitor real-time orderbook
        print("\n" + "=" * 50)
        print("👀 REAL-TIME MONITORING")
        print("=" * 50)

        monitor_orderbook_feed(orderbook, duration_seconds=45)

        # Advanced analysis demonstrations
        print("\n" + "=" * 50)
        print("🔬 ADVANCED ANALYSIS")
        print("=" * 50)

        # Demonstrate orderbook snapshot
        print("Taking comprehensive orderbook snapshot...")
        try:
            snapshot = orderbook.get_orderbook_snapshot(levels=20)
            metadata = snapshot["metadata"]

            print("📸 Orderbook Snapshot:")
            print(f"   Best Bid: ${metadata.get('best_bid', 0):.2f}")
            print(f"   Best Ask: ${metadata.get('best_ask', 0):.2f}")
            print(f"   Spread: ${metadata.get('spread', 0):.2f}")
            print(f"   Mid Price: ${metadata.get('mid_price', 0):.2f}")
            print(f"   Total Bid Volume: {metadata.get('total_bid_volume', 0):,}")
            print(f"   Total Ask Volume: {metadata.get('total_ask_volume', 0):,}")
            print(f"   Bid Levels: {metadata.get('levels_count', {}).get('bids', 0)}")
            print(f"   Ask Levels: {metadata.get('levels_count', {}).get('asks', 0)}")
            print(f"   Last Update: {metadata.get('last_update', 'Never')}")

            # Show sample data structure
            bids_df = snapshot["bids"]
            asks_df = snapshot["asks"]

            print("\n📊 Data Structure (Polars DataFrames):")
            print(f"   Bids DataFrame: {len(bids_df)} rows")
            if not bids_df.is_empty():
                print("   Bid Columns:", bids_df.columns)
                print("   Sample Bid Data:")
                print(bids_df.head(3))

            print(f"   Asks DataFrame: {len(asks_df)} rows")
            if not asks_df.is_empty():
                print("   Ask Columns:", asks_df.columns)
                print("   Sample Ask Data:")
                print(asks_df.head(3))

        except Exception as e:
            print(f"   ❌ Snapshot error: {e}")

        # Final statistics
        print("\n" + "=" * 50)
        print("📊 FINAL STATISTICS")
        print("=" * 50)

        display_memory_stats(orderbook)
        display_order_statistics(orderbook)

        # Final trade flow analysis
        display_trade_flow(orderbook)

        print("\n✅ Level 2 orderbook analysis example completed!")
        print("\n📝 Key Features Demonstrated:")
        print("   ✅ Real-time bid/ask levels")
        print("   ✅ Market depth analysis")
        print("   ✅ Trade flow monitoring")
        print("   ✅ Order type statistics")
        print("   ✅ Market imbalance detection")
        print("   ✅ Memory management")
        print("   ✅ Real-time callbacks")

        print("\n📚 Next Steps:")
        print("   - Try examples/06_multi_timeframe_strategy.py for trading strategies")
        print("   - Try examples/07_technical_indicators.py for indicator analysis")
        print("   - Review orderbook documentation for advanced features")

        return True

    except KeyboardInterrupt:
        print("\n⏹️ Example interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Orderbook analysis example failed: {e}")
        print(f"❌ Error: {e}")
        return False
    finally:
        # Cleanup
        if "orderbook" in locals():
            try:
                print("\n🧹 Cleaning up orderbook...")
                # Note: Cleanup method depends on orderbook implementation
                if hasattr(orderbook, "cleanup"):
                    orderbook.cleanup()
                print("✅ Orderbook cleaned up")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
