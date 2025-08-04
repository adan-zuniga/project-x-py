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

Uses MNQ for Level 2 orderbook data with OrderBook.

Updated for v3.0.0: Uses new TradingSuite for simplified initialization.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/05_orderbook_analysis.py

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
    TradingSuite,
    setup_logging,
)
from project_x_py.orderbook import OrderBook


async def display_best_prices(orderbook):
    """Display current best bid/ask prices."""
    best_prices = await orderbook.get_best_bid_ask()
    best_bid = best_prices.get("bid")
    best_ask = best_prices.get("ask")

    print("📊 Best Bid/Ask:", flush=True)
    if best_bid and best_ask:
        spread = best_ask["price"] - best_bid["price"]
        mid_price = (best_bid["price"] + best_ask["price"]) / 2

        print(
            f"   Best Bid: ${best_bid['price']:,.2f} x {best_bid['size']}", flush=True
        )
        print(
            f"   Best Ask: ${best_ask['price']:,.2f} x {best_ask['size']}", flush=True
        )
        print(f"   Spread: ${spread:.2f}", flush=True)
        print(f"   Mid: ${mid_price:,.2f}", flush=True)
    else:
        print("   No bid/ask available", flush=True)


async def display_market_depth(orderbook):
    """Display market depth on both sides."""
    depth = await orderbook.get_market_depth(levels=5)

    print("\n📈 Market Depth (Top 5 Levels):", flush=True)

    # Display bids
    print("\n   BIDS:", flush=True)
    total_bid_size = 0
    if "bids" in depth and depth["bids"]:
        for i, level in enumerate(depth["bids"][:5]):
            total_bid_size += level["size"]
            print(
                f"   Level {i + 1}: ${level['price']:,.2f} x {level['size']:>4} | "
                f"Total: {total_bid_size:>5}",
                flush=True,
            )
    else:
        print("   No bids available", flush=True)

    # Display asks
    print("\n   ASKS:", flush=True)
    total_ask_size = 0
    if "asks" in depth and depth["asks"]:
        for i, level in enumerate(depth["asks"][:5]):
            total_ask_size += level["size"]
            print(
                f"   Level {i + 1}: ${level['price']:,.2f} x {level['size']:>4} | "
                f"Total: {total_ask_size:>5}",
                flush=True,
            )
    else:
        print("   No asks available", flush=True)

    if total_bid_size > 0 and total_ask_size > 0:
        imbalance = (total_bid_size - total_ask_size) / (
            total_bid_size + total_ask_size
        )
        print(f"\n   Imbalance: {imbalance:.2%} ", end="", flush=True)
        if imbalance > 0.1:
            print("(Bid Heavy 🟢)", flush=True)
        elif imbalance < -0.1:
            print("(Ask Heavy 🔴)", flush=True)
        else:
            print("(Balanced ⚖️)", flush=True)


async def display_trade_flow(orderbook):
    """Display recent trade flow analysis."""
    trades = await orderbook.get_recent_trades(limit=10)

    if not trades:
        print("\n📉 No recent trades available", flush=True)
        return

    print(f"\n📉 Recent Trade Flow ({len(trades)} trades):", flush=True)

    buy_volume = sum(t["size"] for t in trades if t.get("side") == "buy")
    sell_volume = sum(t["size"] for t in trades if t.get("side") == "sell")
    total_volume = buy_volume + sell_volume

    if total_volume > 0:
        print(
            f"   Buy Volume: {buy_volume:,} ({buy_volume / total_volume:.1%})",
            flush=True,
        )
        print(
            f"   Sell Volume: {sell_volume:,} ({sell_volume / total_volume:.1%})",
            flush=True,
        )

    # Show last 5 trades
    print("\n   Last 5 Trades:", flush=True)
    for trade in trades[:5]:
        side_emoji = "🟢" if trade.get("side") == "buy" else "🔴"
        timestamp = trade.get("timestamp", "")
        if isinstance(timestamp, datetime):
            timestamp = timestamp.strftime("%H:%M:%S")
        print(
            f"   {side_emoji} ${trade['price']:,.2f} x {trade['size']} @ {timestamp}",
            flush=True,
        )


async def display_market_microstructure(orderbook):
    """Display market microstructure analysis."""
    microstructure = await orderbook.analyze_market_microstructure()

    print("\n🔬 Market Microstructure:", flush=True)
    print(f"   Bid Depth: {microstructure.get('bid_depth', 0)} levels", flush=True)
    print(f"   Ask Depth: {microstructure.get('ask_depth', 0)} levels", flush=True)
    print(f"   Total Bid Size: {microstructure.get('total_bid_size', 0):,}", flush=True)
    print(f"   Total Ask Size: {microstructure.get('total_ask_size', 0):,}", flush=True)

    if microstructure.get("avg_bid_size", 0) > 0:
        print(
            f"   Avg Bid Size: {microstructure.get('avg_bid_size', 0):.1f}", flush=True
        )
    if microstructure.get("avg_ask_size", 0) > 0:
        print(
            f"   Avg Ask Size: {microstructure.get('avg_ask_size', 0):.1f}", flush=True
        )

    # Price levels
    if microstructure.get("price_levels"):
        print(f"   Unique Price Levels: {microstructure['price_levels']}", flush=True)

    # Order clustering
    if microstructure.get("order_clustering"):
        print(
            f"   Order Clustering: {microstructure['order_clustering']:.2f}",
            flush=True,
        )


async def display_iceberg_detection(orderbook):
    """Display potential iceberg orders."""
    icebergs = await orderbook.detect_icebergs()

    print("\n🧊 Iceberg Detection:", flush=True)
    if icebergs:
        for iceberg in icebergs[:3]:  # Show top 3
            side = "BID" if iceberg["side"] == "bid" else "ASK"
            print(
                f"   Potential {side} iceberg at ${iceberg['price']:,.2f}",
                flush=True,
            )
            print(f"     - Visible: {iceberg['visible_size']}", flush=True)
            print(f"     - Refill Count: {iceberg['refill_count']}", flush=True)
            print(f"     - Total Volume: {iceberg['total_volume']}", flush=True)
            print(f"     - Confidence: {iceberg['confidence']:.1%}", flush=True)
    else:
        print("   No iceberg orders detected", flush=True)


async def monitor_orderbook_realtime(orderbook: OrderBook, duration: int = 45):
    """Monitor orderbook in real-time for specified duration."""
    print(f"\n🔄 Real-time Monitoring ({duration} seconds)...", flush=True)
    print("=" * 60, flush=True)

    start_time = time.time()
    update_interval = 5  # seconds

    while time.time() - start_time < duration:
        elapsed = int(time.time() - start_time)
        print(f"\n⏰ Update at {elapsed}s:", flush=True)

        # Show best prices
        await display_best_prices(orderbook)

        # Show depth summary
        depth = await orderbook.get_market_depth(levels=3)
        if depth.get("bids") and depth.get("asks"):
            bid_size = sum(level["size"] for level in depth["bids"][:3])
            ask_size = sum(level["size"] for level in depth["asks"][:3])
            print(f"\n   Top 3 Levels: {bid_size} bids | {ask_size} asks", flush=True)

        # Show recent trade
        trades = await orderbook.get_recent_trades(limit=1)
        if trades:
            trade = trades[0]
            side_emoji = "🟢" if trade.get("side") == "buy" else "🔴"
            print(
                f"   Last Trade: {side_emoji} ${trade['price']:,.2f} x {trade['size']}",
                flush=True,
            )

        await asyncio.sleep(update_interval)

    print("\n✅ Real-time monitoring completed", flush=True)


async def demonstrate_comprehensive_methods(orderbook: OrderBook):
    """Demonstrate all comprehensive orderbook methods after 2 minutes."""
    print("\n⏰ Waiting 2 minutes for data accumulation...", flush=True)
    print(
        "   (This ensures we have enough data for comprehensive analysis)", flush=True
    )

    # Show countdown
    for i in range(4):
        remaining = 120 - (i * 30)
        print(f"   {remaining} seconds remaining...", flush=True)
        await asyncio.sleep(30)

    print("\n🎯 Demonstrating Comprehensive Methods:", flush=True)
    print("=" * 60, flush=True)

    # 1. Volume Profile Analysis
    print("\n📊 Volume Profile Analysis:", flush=True)
    try:
        volume_profile = await orderbook.get_volume_profile(bins=10)
        if volume_profile:
            print("   Price Range | Volume | Percentage", flush=True)
            print("   " + "-" * 40, flush=True)
            for level in volume_profile[:5]:  # Show top 5
                price_range = f"${level['price_min']:.2f}-${level['price_max']:.2f}"
                volume = level["volume"]
                percentage = level.get("percentage", 0)
                print(
                    f"   {price_range:<15} | {volume:>6,} | {percentage:>5.1f}%",
                    flush=True,
                )
        else:
            print("   No volume profile data available", flush=True)
    except Exception as e:
        print(f"   Error: {e}", flush=True)

    # 2. Order Type Statistics
    print("\n📈 Order Type Statistics:", flush=True)
    try:
        order_stats = await orderbook.get_order_type_statistics()
        if order_stats:
            print(
                f"   Market Orders: {order_stats.get('market_orders', 0):,}", flush=True
            )
            print(
                f"   Limit Orders: {order_stats.get('limit_orders', 0):,}", flush=True
            )
            print(f"   Stop Orders: {order_stats.get('stop_orders', 0):,}", flush=True)
            if order_stats.get("avg_order_size"):
                print(
                    f"   Avg Order Size: {order_stats['avg_order_size']:.1f}",
                    flush=True,
                )
        else:
            print("   No order statistics available", flush=True)
    except Exception as e:
        print(f"   Error: {e}", flush=True)

    # 3. Market Impact Analysis
    print("\n💥 Market Impact Analysis:", flush=True)
    try:
        # Simulate a 10-contract order
        impact = await orderbook.estimate_market_impact(size=10, side="buy")
        if impact:
            print(f"   Simulating BUY 10 contracts:", flush=True)
            print(
                f"   Estimated Fill Price: ${impact.get('avg_fill_price', 0):,.2f}",
                flush=True,
            )
            print(
                f"   Price Impact: {impact.get('price_impact_pct', 0):.2%}", flush=True
            )
            print(f"   Spread Cost: ${impact.get('spread_cost', 0):,.2f}", flush=True)
            if impact.get("levels_consumed"):
                print(f"   Levels Consumed: {impact['levels_consumed']}", flush=True)
        else:
            print("   Insufficient depth for impact analysis", flush=True)
    except Exception as e:
        print(f"   Error: {e}", flush=True)

    # 4. Liquidity Analysis
    print("\n💧 Liquidity Analysis:", flush=True)
    try:
        liquidity = await orderbook.analyze_liquidity()
        if liquidity:
            print(
                f"   Bid Liquidity: ${liquidity.get('bid_liquidity', 0):,.0f}",
                flush=True,
            )
            print(
                f"   Ask Liquidity: ${liquidity.get('ask_liquidity', 0):,.0f}",
                flush=True,
            )
            print(f"   Avg Spread: ${liquidity.get('avg_spread', 0):.2f}", flush=True)
            print(
                f"   Liquidity Score: {liquidity.get('liquidity_score', 0):.1f}/10",
                flush=True,
            )
        else:
            print("   No liquidity data available", flush=True)
    except Exception as e:
        print(f"   Error: {e}", flush=True)

    # 5. Spoofing Detection
    print("\n🎭 Spoofing Detection:", flush=True)
    try:
        spoofing = await orderbook.detect_spoofing()
        if spoofing:
            for alert in spoofing[:3]:  # Show top 3
                print(f"   Potential spoofing at ${alert['price']:,.2f}:", flush=True)
                print(f"     - Side: {alert['side'].upper()}", flush=True)
                print(f"     - Pattern: {alert['pattern']}", flush=True)
                print(f"     - Confidence: {alert['confidence']:.1%}", flush=True)
        else:
            print("   No spoofing patterns detected", flush=True)
    except Exception as e:
        print(f"   Error: {e}", flush=True)

    # 6. Get full snapshot
    print("\n📸 Full Orderbook Snapshot:", flush=True)
    try:
        snapshot = await orderbook.get_orderbook_snapshot()
        if snapshot:
            print(f"   Timestamp: {snapshot.get('timestamp', 'N/A')}", flush=True)
            print(f"   Bid Levels: {len(snapshot.get('bids', []))}", flush=True)
            print(f"   Ask Levels: {len(snapshot.get('asks', []))}", flush=True)
            print(f"   Total Trades: {len(orderbook.recent_trades)}", flush=True)
        else:
            print("   No snapshot available", flush=True)
    except Exception as e:
        print(f"   Error: {e}", flush=True)


async def main():
    """Main async orderbook analysis demonstration."""
    logger = setup_logging(level="INFO")
    print("🚀 Async Level 2 Orderbook Analysis Example (v3.0.0)", flush=True)
    print("=" * 60, flush=True)

    # Important note about runtime
    print("\n⚠️  IMPORTANT: This example runs for approximately 3 minutes:", flush=True)
    print("   - 5 seconds: Initial data population", flush=True)
    print("   - 45 seconds: Real-time monitoring", flush=True)
    print("   - 2 minutes: Wait before comprehensive analysis", flush=True)
    print("   - 30 seconds: Comprehensive method demonstrations", flush=True)
    print("\nPress Ctrl+C at any time to stop early.", flush=True)

    # Ask for confirmation
    print("\n❓ Continue with the full demonstration? (y/N): ", end="", flush=True)
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: input().strip().lower()
        )
        if response != "y":
            print("❌ Orderbook analysis cancelled", flush=True)
            return False
    except (EOFError, KeyboardInterrupt):
        print("\n❌ Orderbook analysis cancelled", flush=True)
        return False

    try:
        # Initialize TradingSuite v3 with orderbook feature
        print("\n🔑 Initializing TradingSuite v3 with orderbook...", flush=True)

        suite = await TradingSuite.create(
            "MNQ",
            features=["orderbook"],
            timeframes=["1min", "5min"],
        )

        print("✅ TradingSuite created successfully!", flush=True)

        account = suite.client.account_info
        if account:
            print(f"   Account: {account.name}", flush=True)
            print(f"   Balance: ${account.balance:,.2f}", flush=True)
            print(f"   Account Type: {account.accountType}", flush=True)

        # Get orderbook from suite
        orderbook = suite.orderbook
        if not orderbook:
            print("❌ Orderbook not available in suite", flush=True)
            await suite.disconnect()
            return False

        print("\n✅ Orderbook initialized and connected!", flush=True)
        print("   - Real-time depth updates: Active", flush=True)
        print("   - Quote updates: Active", flush=True)
        print("   - Trade feed: Active", flush=True)

        # Wait for initial data
        print("\n⏳ Waiting 5 seconds for initial data population...", flush=True)
        await asyncio.sleep(5)

        # Show initial state
        print("\n" + "=" * 60, flush=True)
        print("📊 INITIAL ORDERBOOK STATE", flush=True)
        print("=" * 60, flush=True)

        await display_best_prices(orderbook)
        await display_market_depth(orderbook)
        await display_trade_flow(orderbook)
        await display_market_microstructure(orderbook)
        await display_iceberg_detection(orderbook)

        # Real-time monitoring
        print("\n" + "=" * 60, flush=True)
        print("📡 REAL-TIME MONITORING", flush=True)
        print("=" * 60, flush=True)

        await monitor_orderbook_realtime(orderbook, duration=45)

        # Comprehensive analysis (after 2 minutes)
        print("\n" + "=" * 60, flush=True)
        print("🔬 COMPREHENSIVE ANALYSIS", flush=True)
        print("=" * 60, flush=True)

        await demonstrate_comprehensive_methods(orderbook)

        # Final statistics
        print("\n" + "=" * 60, flush=True)
        print("📈 FINAL STATISTICS", flush=True)
        print("=" * 60, flush=True)

        # Memory stats
        memory_stats = orderbook.get_memory_stats()
        print("\n💾 Memory Usage:", flush=True)
        print(f"   Bid Entries: {memory_stats.get('bid_entries', 0):,}", flush=True)
        print(f"   Ask Entries: {memory_stats.get('ask_entries', 0):,}", flush=True)
        print(f"   Trades Stored: {memory_stats.get('trades_stored', 0):,}", flush=True)
        print(
            f"   Memory Cleaned: {memory_stats.get('memory_cleanups', 0)} times",
            flush=True,
        )

        print("\n✅ Orderbook analysis completed successfully!", flush=True)
        print("\n📝 Key Takeaways:", flush=True)
        print("   - Real-time Level 2 depth with async/await", flush=True)
        print("   - Market microstructure insights", flush=True)
        print("   - Iceberg and spoofing detection", flush=True)
        print("   - Trade flow and liquidity analysis", flush=True)
        print("   - Memory-efficient sliding window design", flush=True)

        await suite.disconnect()
        return True

    except KeyboardInterrupt:
        print("\n⏹️ Orderbook analysis interrupted by user", flush=True)
        return False
    except Exception as e:
        logger.error(f"Orderbook analysis failed: {e}", flush=True)
        print(f"\n❌ Error: {e}", flush=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
