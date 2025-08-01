#!/usr/bin/env python3
"""
Async Level 2 Orderbook Analysis Example

Demonstrates comprehensive Level 2 orderbook analysis using async/await:
- Real-time bid/ask levels and depth
- Market microstructure analysis
- Trade flow analysis
- Order type statistics
- Iceberg detection
- Market imbalance monitoring
- Best bid/ask tracking

Uses MNQ for Level 2 orderbook data with AsyncOrderBook.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/async_05_orderbook_analysis.py

Note: This example includes several wait periods:
    - 5 seconds for initial data population
    - 45 seconds for real-time monitoring
    - 2 minutes before comprehensive method demonstration
    Total runtime is approximately 3 minutes.

Author: TexasCoding
Date: July 2025
"""

import asyncio
import sys
import time
from datetime import datetime

from project_x_py import (
    AsyncProjectX,
    create_async_orderbook,
    create_async_realtime_client,
    setup_logging,
)


async def display_best_prices(orderbook):
    """Display current best bid/ask prices."""
    best_bid, best_ask = await orderbook.get_best_bid_ask()

    print("📊 Best Bid/Ask:", flush=True)
    if best_bid and best_ask:
        spread = best_ask - best_bid
        mid = (best_bid + best_ask) / 2
        print(f"   Bid: ${best_bid:.2f}", flush=True)
        print(f"   Ask: ${best_ask:.2f}", flush=True)
        print(f"   Spread: ${spread:.2f}", flush=True)
        print(f"   Mid: ${mid:.2f}", flush=True)
    else:
        print("   No bid/ask data available", flush=True)


async def display_orderbook_levels(orderbook, levels=5):
    """Display orderbook levels with bid/ask depth."""
    print(f"\n📈 Orderbook Levels (Top {levels}):", flush=True)

    # Get bid and ask data
    bids = await orderbook.get_orderbook_bids(levels=levels)
    asks = await orderbook.get_orderbook_asks(levels=levels)

    # Display asks (sellers) - highest price first
    print("   ASKS (Sellers):", flush=True)
    if asks:
        # Sort asks by price descending for display
        asks_sorted = sorted(asks, key=lambda x: x["price"], reverse=True)
        for ask in asks_sorted:
            price = ask["price"]
            volume = ask["volume"]
            timestamp = ask["timestamp"]
            print(f"   ${price:8.2f} | {volume:4d} contracts | {timestamp}", flush=True)
    else:
        print("   No ask data", flush=True)

    print("   " + "-" * 40)

    # Display bids (buyers) - highest price first
    print("   BIDS (Buyers):", flush=True)
    if bids:
        for bid in bids:
            price = bid["price"]
            volume = bid["volume"]
            timestamp = bid["timestamp"]
            print(f"   ${price:8.2f} | {volume:4d} contracts | {timestamp}", flush=True)
    else:
        print("   No bid data", flush=True)


async def display_orderbook_snapshot(orderbook):
    """Display comprehensive orderbook snapshot."""
    try:
        snapshot = await orderbook.get_orderbook_snapshot(levels=20)

        print("\n📸 Orderbook Snapshot:", flush=True)
        print(f"   Instrument: {snapshot['instrument']}", flush=True)
        print(
            f"   Best Bid: ${snapshot['best_bid']:.2f}"
            if snapshot["best_bid"]
            else "   Best Bid: None"
        )
        print(
            f"   Best Ask: ${snapshot['best_ask']:.2f}"
            if snapshot["best_ask"]
            else "   Best Ask: None"
        )
        print(
            f"   Spread: ${snapshot['spread']:.2f}"
            if snapshot["spread"]
            else "   Spread: None"
        )
        print(
            f"   Mid Price: ${snapshot['mid_price']:.2f}"
            if snapshot["mid_price"]
            else "   Mid Price: None"
        )
        print(f"   Update Count: {snapshot['update_count']:,}", flush=True)
        print(f"   Last Update: {snapshot['last_update']}", flush=True)

        # Show data structure
        print("\n📊 Data Structure:", flush=True)
        print(f"   Bids: {len(snapshot['bids'])} levels", flush=True)
        print(f"   Asks: {len(snapshot['asks'])} levels", flush=True)

    except Exception as e:
        print(f"   ❌ Snapshot error: {e}", flush=True)


async def display_memory_stats(orderbook):
    """Display orderbook memory statistics."""
    try:
        stats = orderbook.get_memory_stats()

        print("\n💾 Memory Statistics:", flush=True)
        print(f"   Bid Levels: {stats['total_bid_levels']:,}", flush=True)
        print(f"   Ask Levels: {stats['total_ask_levels']:,}", flush=True)
        print(f"   Recent Trades: {stats['total_trades']:,}", flush=True)
        print(f"   Price History Levels: {stats['price_history_levels']:,}", flush=True)
        print(f"   Update Count: {stats['update_count']:,}", flush=True)
        print(
            f"   Total Trades Processed: {stats.get('total_trades', 0):,}", flush=True
        )
        print(
            f"   Last Cleanup: {datetime.fromtimestamp(stats.get('last_cleanup', 0)).strftime('%H:%M:%S')}"
        )

    except Exception as e:
        print(f"   ❌ Memory stats error: {e}", flush=True)


async def display_iceberg_detection(orderbook):
    """Display potential iceberg orders."""
    try:
        icebergs = await orderbook.detect_iceberg_orders(
            min_refreshes=5, volume_threshold=50, time_window_minutes=10
        )

        print("\n🧊 Iceberg Order Detection:", flush=True)
        print(
            f"   Analysis Window: {icebergs['analysis_window_minutes']} minutes",
            flush=True,
        )

        iceberg_levels = icebergs.get("iceberg_levels", [])
        if iceberg_levels:
            print(f"   Potential Icebergs Found: {len(iceberg_levels)}", flush=True)
            print("   Top Confidence Levels:", flush=True)
            for level in iceberg_levels[:5]:  # Top 5
                print(f"   Price: ${level['price']:.2f} ({level['side']})", flush=True)
                print(
                    f"      Avg Volume: {level['avg_volume']:.0f} contracts", flush=True
                )
                print(f"      Refresh Count: {level['refresh_count']}", flush=True)
                print(f"      Confidence: {level['confidence']:.2%}", flush=True)
                print(
                    f"      Last Seen: {level['last_seen'].strftime('%H:%M:%S')}",
                    flush=True,
                )
        else:
            print("   No potential iceberg orders detected", flush=True)

    except Exception as e:
        print(f"   ❌ Iceberg detection error: {e}", flush=True)


async def setup_orderbook_callbacks(orderbook):
    """Setup callbacks for orderbook events."""
    print("\n🔔 Setting up orderbook callbacks...", flush=True)

    # Market depth callback
    async def on_market_depth(data):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        update_count = data.get("update_count", 0)
        if update_count % 100 == 0:  # Log every 100th update
            print(f"   [{timestamp}] 📊 Depth Update #{update_count}", flush=True)

    try:
        await orderbook.add_callback("market_depth_processed", on_market_depth)
        print("   ✅ Orderbook callbacks registered", flush=True)
    except Exception as e:
        print(f"   ❌ Callback setup error: {e}", flush=True)


async def monitor_orderbook_feed(orderbook, duration_seconds=60):
    """Monitor the orderbook feed for a specified duration."""
    print(f"\n👀 Orderbook Monitoring ({duration_seconds}s)", flush=True)
    print("=" * 50)

    start_time = time.time()
    update_count = 0

    print("Monitoring MNQ Level 2 orderbook...", flush=True)
    print("Press Ctrl+C to stop early", flush=True)

    try:
        while time.time() - start_time < duration_seconds:
            elapsed = time.time() - start_time

            # Every 15 seconds, show detailed update
            if int(elapsed) % 15 == 0 and int(elapsed) > 0:
                remaining = duration_seconds - elapsed
                print(
                    f"\n⏰ {elapsed:.0f}s elapsed, {remaining:.0f}s remaining",
                    flush=True,
                )
                print("=" * 30)

                # Show current state
                await display_best_prices(orderbook)

                # Show memory stats
                stats = orderbook.get_memory_stats()
                print(
                    f"\n📊 Stats: {stats['update_count']} updates, {stats['total_trades']} trades"
                )

                update_count += 1

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user", flush=True)

    print("\n📊 Monitoring Summary:", flush=True)
    print(f"   Duration: {time.time() - start_time:.1f} seconds", flush=True)
    print(f"   Update Cycles: {update_count}", flush=True)


async def demonstrate_all_orderbook_methods(orderbook):
    """Comprehensive demonstration of all AsyncOrderBook methods."""
    print("\n🔍 Testing all available AsyncOrderBook methods...", flush=True)
    print(
        "📝 Note: Some methods may show zero values without live market data connection"
    )

    # 1. Basic OrderBook Data
    print("\n📈 BASIC ORDERBOOK DATA", flush=True)
    print("-" * 40)

    print("1. get_orderbook_snapshot():", flush=True)
    await display_orderbook_snapshot(orderbook)

    print("\n2. get_best_bid_ask():", flush=True)
    best_bid, best_ask = await orderbook.get_best_bid_ask()
    print(
        f"   Best Bid: ${best_bid:.2f}" if best_bid else "   Best Bid: None", flush=True
    )
    print(
        f"   Best Ask: ${best_ask:.2f}" if best_ask else "   Best Ask: None", flush=True
    )

    print("\n3. get_bid_ask_spread():", flush=True)
    spread = await orderbook.get_bid_ask_spread()
    print(f"   Spread: ${spread:.2f}" if spread else "   Spread: None", flush=True)

    # 2. Orderbook Levels
    print("\n📊 ORDERBOOK LEVELS", flush=True)
    print("-" * 40)

    print("4. get_orderbook_bids():", flush=True)
    bids = await orderbook.get_orderbook_bids(levels=5)
    print(f"   Top 5 bid levels: {len(bids)} levels", flush=True)
    if bids:
        top_bid = bids[0]
        print(f"   Best bid: ${top_bid['price']:.2f} x{top_bid['volume']}", flush=True)

    print("\n5. get_orderbook_asks():", flush=True)
    asks = await orderbook.get_orderbook_asks(levels=5)
    print(f"   Top 5 ask levels: {len(asks)} levels", flush=True)
    if asks:
        top_ask = asks[0]
        print(f"   Best ask: ${top_ask['price']:.2f} x{top_ask['volume']}", flush=True)

    # 3. Advanced Detection
    print("\n🔍 ADVANCED DETECTION", flush=True)
    print("-" * 40)

    print("6. detect_iceberg_orders():", flush=True)
    await display_iceberg_detection(orderbook)

    # 4. Memory and Performance
    print("\n💾 MEMORY AND PERFORMANCE", flush=True)
    print("-" * 40)

    print("7. get_memory_stats():", flush=True)
    stats = orderbook.get_memory_stats()
    for key, value in stats.items():
        if isinstance(value, int | float):
            print(
                f"   {key}: {value:,}"
                if isinstance(value, int)
                else f"   {key}: {value:.2f}"
            )
        else:
            print(f"   {key}: {value}", flush=True)

    # 5. Data Management
    print("\n🧹 DATA MANAGEMENT", flush=True)
    print("-" * 40)

    print("8. clear_orderbook():", flush=True)
    # Don't actually clear during demo
    print("   Method available for clearing all orderbook data", flush=True)
    print("   Would reset: bids, asks, trades, and history", flush=True)

    print(
        "\n✅ Comprehensive AsyncOrderBook method demonstration completed!", flush=True
    )
    print("📊 Total methods demonstrated: 8 core async methods", flush=True)


async def main():
    """Demonstrate comprehensive async Level 2 orderbook analysis."""
    logger = setup_logging(level="DEBUG" if "--debug" in sys.argv else "INFO")
    print("🚀 Async Level 2 Orderbook Analysis Example", flush=True)
    print("=" * 60, flush=True)

    # Initialize variables for cleanup
    orderbook = None
    realtime_client = None

    try:
        # Initialize async client
        print("🔑 Initializing AsyncProjectX client...", flush=True)
        async with AsyncProjectX.from_env() as client:
            # Ensure authenticated
            await client.authenticate()

            # Get account info
            if not client.account_info:
                print("❌ Could not get account information", flush=True)
                return False

            account = client.account_info
            print(f"✅ Connected to account: {account.name}", flush=True)

            # Create async orderbook
            print("\n🏗️ Creating async Level 2 orderbook...", flush=True)
            try:
                jwt_token = client.session_token
                realtime_client = create_async_realtime_client(
                    jwt_token, str(account.id)
                )

                # Connect the realtime client
                print("   Connecting to real-time WebSocket feeds...", flush=True)
                if await realtime_client.connect():
                    print("   ✅ Real-time client connected successfully", flush=True)
                else:
                    print(
                        "   ⚠️ Real-time client connection failed - continuing with limited functionality"
                    )

                orderbook = create_async_orderbook(
                    instrument="MNQ", realtime_client=realtime_client, project_x=client
                )

                # Initialize the orderbook with real-time capabilities
                await orderbook.initialize(realtime_client)
                print("✅ Async Level 2 orderbook created for MNQ", flush=True)

                # Get contract ID and subscribe to market data
                print("   Getting contract ID for MNQ...", flush=True)
                instrument_obj = await client.get_instrument("MNQ")
                if instrument_obj:
                    contract_id = instrument_obj.id
                    print(f"   Contract ID: {contract_id}", flush=True)

                    # Subscribe to market data for this contract
                    print("   Subscribing to market data...", flush=True)
                    success = await realtime_client.subscribe_market_data([contract_id])
                    if success:
                        print("   ✅ Market data subscription successful", flush=True)
                    else:
                        print(
                            "   ⚠️ Market data subscription may have failed (might already be subscribed)"
                        )
                else:
                    print("   ❌ Failed to get contract ID for MNQ", flush=True)
                    return False
            except Exception as e:
                print(f"❌ Failed to create orderbook: {e}", flush=True)
                return False

            print(
                "✅ Async orderbook initialized with real-time capabilities", flush=True
            )

            # Setup callbacks
            print("\n" + "=" * 50)
            print("🔔 CALLBACK SETUP", flush=True)
            print("=" * 50)

            await setup_orderbook_callbacks(orderbook)

            # Wait for data to populate
            print("\n⏳ Waiting for orderbook data to populate...", flush=True)
            await asyncio.sleep(5)

            # Show initial orderbook state
            print("\n" + "=" * 50)
            print("📊 INITIAL ORDERBOOK STATE", flush=True)
            print("=" * 50)

            await display_best_prices(orderbook)
            await display_orderbook_levels(orderbook, levels=10)

            # Show memory statistics
            print("\n" + "=" * 50)
            print("📊 MEMORY STATISTICS", flush=True)
            print("=" * 50)

            await display_memory_stats(orderbook)

            # Monitor real-time orderbook
            print("\n" + "=" * 50)
            print("👀 REAL-TIME MONITORING", flush=True)
            print("=" * 50)

            await monitor_orderbook_feed(orderbook, duration_seconds=45)

            # Advanced analysis demonstrations
            print("\n" + "=" * 50)
            print("🔬 ADVANCED ANALYSIS", flush=True)
            print("=" * 50)

            # Demonstrate orderbook snapshot
            print("Taking comprehensive orderbook snapshot...", flush=True)
            await display_orderbook_snapshot(orderbook)

            # Check for iceberg orders
            await display_iceberg_detection(orderbook)

            # Comprehensive OrderBook Methods Demonstration
            print("\n" + "=" * 60)
            print("🧪 COMPREHENSIVE ASYNC ORDERBOOK METHODS DEMONSTRATION", flush=True)
            print("=" * 60)

            print(
                "Waiting 2 minutes to make sure orderbook is full for testing!!",
                flush=True,
            )
            await asyncio.sleep(120)
            await demonstrate_all_orderbook_methods(orderbook)

            # Final statistics
            print("\n" + "=" * 50)
            print("📊 FINAL STATISTICS", flush=True)
            print("=" * 50)

            await display_memory_stats(orderbook)

            print(
                "\n✅ Async Level 2 orderbook analysis example completed!", flush=True
            )
            print("\n📝 Key Features Demonstrated:", flush=True)
            print("   ✅ Async/await patterns throughout", flush=True)
            print("   ✅ Real-time bid/ask levels", flush=True)
            print("   ✅ Orderbook snapshot functionality", flush=True)
            print("   ✅ Memory management and statistics", flush=True)
            print("   ✅ Iceberg order detection", flush=True)
            print("   ✅ Real-time async callbacks", flush=True)
            print("   ✅ Thread-safe async operations", flush=True)

            print("\n📚 Next Steps:", flush=True)
            print("   - Try other async examples for trading strategies", flush=True)
            print(
                "   - Review AsyncOrderBook documentation for advanced features",
                flush=True,
            )
            print("   - Integrate with AsyncOrderManager for trading", flush=True)

            return True

    except KeyboardInterrupt:
        print("\n⏹️ Example interrupted by user", flush=True)
        return False
    except Exception as e:
        logger.error(f"❌ Async orderbook analysis example failed: {e}")
        print(f"❌ Error: {e}", flush=True)
        return False
    finally:
        # Cleanup
        if orderbook is not None:
            try:
                print("\n🧹 Cleaning up async orderbook...", flush=True)
                await orderbook.cleanup()
                print("✅ Async orderbook cleaned up", flush=True)
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}", flush=True)

        if realtime_client is not None:
            try:
                print("🧹 Disconnecting async real-time client...", flush=True)
                await realtime_client.disconnect()
                print("✅ Async real-time client disconnected", flush=True)
            except Exception as e:
                print(f"⚠️  Disconnect warning: {e}", flush=True)


if __name__ == "__main__":
    print("Starting async orderbook example...", flush=True)
    success = asyncio.run(main())
    exit(0 if success else 1)
