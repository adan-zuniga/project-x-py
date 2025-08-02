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
    ProjectX,
    create_orderbook,
    create_realtime_client,
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
    if not asks.is_empty():
        # Convert to list of dicts for display
        asks_list = asks.to_dicts()
        # Sort asks by price descending for display
        asks_sorted = sorted(asks_list, key=lambda x: x["price"], reverse=True)
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
    if not bids.is_empty():
        # Convert to list of dicts for display
        bids_list = bids.to_dicts()
        for bid in bids_list:
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
        stats = await orderbook.get_memory_stats()

        print("\n💾 Memory Statistics:", flush=True)
        print(f"   Bid Levels: {stats['orderbook_bids_count']:,}", flush=True)
        print(f"   Ask Levels: {stats['orderbook_asks_count']:,}", flush=True)
        print(f"   Recent Trades: {stats['recent_trades_count']:,}", flush=True)
        print(
            f"   Total Trades Processed: {stats['total_trades_processed']:,}",
            flush=True,
        )
        print(f"   Trades Cleaned: {stats['trades_cleaned']:,}", flush=True)
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
                    f"      Last Update: {level.get('last_update', datetime.now()).strftime('%H:%M:%S') if 'last_update' in level else 'N/A'}",
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
                stats = await orderbook.get_memory_stats()
                print(
                    f"\n📊 Stats: {stats['total_trades_processed']} trades processed, {stats['recent_trades_count']} in memory"
                )

                update_count += 1

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user", flush=True)

    print("\n📊 Monitoring Summary:", flush=True)
    print(f"   Duration: {time.time() - start_time:.1f} seconds", flush=True)
    print(f"   Update Cycles: {update_count}", flush=True)


async def demonstrate_all_orderbook_methods(orderbook: OrderBook):
    """Comprehensive demonstration of all OrderBook methods."""
    print("\n🔍 Testing all available OrderBook methods...", flush=True)
    print(
        "📝 Note: Some methods may show zero values without live market data connection"
    )

    # 1. Basic OrderBook Data
    print("\n📈 BASIC ORDERBOOK DATA", flush=True)
    print("-" * 40)

    print("1. get_orderbook_snapshot():", flush=True)
    await display_orderbook_snapshot(orderbook)

    print("\n2. get_best_bid_ask():", flush=True)
    best_prices = await orderbook.get_best_bid_ask()
    best_bid = best_prices.get("bid")
    best_ask = best_prices.get("ask")
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
    print(f"   Top 5 bid levels: {bids.height} levels", flush=True)
    if not bids.is_empty():
        top_bid = bids.row(0, named=True)
        print(f"   Best bid: ${top_bid['price']:.2f} x{top_bid['volume']}", flush=True)

    print("\n5. get_orderbook_asks():", flush=True)
    asks = await orderbook.get_orderbook_asks(levels=5)
    print(f"   Top 5 ask levels: {asks.height} levels", flush=True)
    if not asks.is_empty():
        top_ask = asks.row(0, named=True)
        print(f"   Best ask: ${top_ask['price']:.2f} x{top_ask['volume']}", flush=True)

    print("\n6. get_orderbook_depth():", flush=True)
    depth = await orderbook.get_orderbook_depth(price_range=10.0)
    bid_depth = depth.get("bid_depth", {})
    ask_depth = depth.get("ask_depth", {})
    print(f"   Price range: ±${depth.get('price_range', 0):.2f}", flush=True)
    print(
        f"   Bid side: {bid_depth.get('levels', 0)} levels, {bid_depth.get('total_volume', 0):,} contracts",
        flush=True,
    )
    print(
        f"   Ask side: {ask_depth.get('levels', 0)} levels, {ask_depth.get('total_volume', 0):,} contracts",
        flush=True,
    )

    # 3. Liquidity Analysis Methods
    print("\n📈 LIQUIDITY ANALYSIS METHODS", flush=True)
    print("-" * 40)

    print("7. get_liquidity_levels():", flush=True)
    try:
        liquidity = await orderbook.get_liquidity_levels(min_volume=10, levels=20)
        significant_bids = liquidity.get("significant_bid_levels", [])
        significant_asks = liquidity.get("significant_ask_levels", [])
        print(f"   Significant bid levels: {len(significant_bids)} levels", flush=True)
        print(f"   Significant ask levels: {len(significant_asks)} levels", flush=True)
        print(
            f"   Total bid liquidity: {liquidity.get('total_bid_liquidity', 0):,} contracts",
            flush=True,
        )
        print(
            f"   Total ask liquidity: {liquidity.get('total_ask_liquidity', 0):,} contracts",
            flush=True,
        )
        print(
            f"   Liquidity imbalance: {liquidity.get('liquidity_imbalance', 0):.3f}",
            flush=True,
        )
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    print("\n8. get_market_imbalance():", flush=True)
    try:
        imbalance = await orderbook.get_market_imbalance(levels=10)
        imbalance_ratio = imbalance.get("imbalance_ratio", 0)
        bid_volume = imbalance.get("bid_volume", 0)
        ask_volume = imbalance.get("ask_volume", 0)
        analysis = imbalance.get("analysis", "neutral")
        print(f"   Imbalance ratio: {imbalance_ratio:.3f}", flush=True)
        print(f"   Bid volume (top 10): {bid_volume:,} contracts", flush=True)
        print(f"   Ask volume (top 10): {ask_volume:,} contracts", flush=True)
        print(f"   Analysis: {analysis}", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    # 4. Advanced Detection Methods
    print("\n🔍 ADVANCED DETECTION METHODS", flush=True)
    print("-" * 40)

    print("9. detect_order_clusters():", flush=True)
    try:
        clusters = await orderbook.detect_order_clusters(min_cluster_size=2)
        bid_clusters = [c for c in clusters if c["side"] == "bid"]
        ask_clusters = [c for c in clusters if c["side"] == "ask"]
        print(f"   Bid clusters found: {len(bid_clusters)}", flush=True)
        print(f"   Ask clusters found: {len(ask_clusters)}", flush=True)
        print(f"   Total clusters: {len(clusters)}", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    print("\n10. detect_iceberg_orders():", flush=True)
    await display_iceberg_detection(orderbook)

    # 5. Volume Analysis Methods
    print("\n📊 VOLUME ANALYSIS METHODS", flush=True)
    print("-" * 40)
    print(
        "📝 These methods analyze trade volume data (requires recent_trades data)",
        flush=True,
    )
    print("", flush=True)

    print("11. get_volume_profile():", flush=True)
    try:
        vol_profile = await orderbook.get_volume_profile()
        if "error" in vol_profile:
            print(f"   ❌ Error: {vol_profile['error']}", flush=True)
        else:
            poc_price = vol_profile.get("poc", 0)
            total_volume = vol_profile.get("total_volume", 0)
            price_bins = vol_profile.get("price_bins", [])
            print(
                f"   Point of Control (POC): ${poc_price:.2f}"
                if poc_price
                else "   Point of Control (POC): N/A",
                flush=True,
            )
            print(f"   Price bins: {len(price_bins)}", flush=True)
            print(f"   Total volume analyzed: {total_volume:,}", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    print("\n12. get_cumulative_delta():", flush=True)
    try:
        cum_delta = await orderbook.get_cumulative_delta(time_window_minutes=15)
        delta_value = cum_delta.get("cumulative_delta", 0)
        buy_vol = cum_delta.get("buy_volume", 0)
        sell_vol = cum_delta.get("sell_volume", 0)
        neutral_vol = cum_delta.get("neutral_volume", 0)
        trade_count = cum_delta.get("trade_count", 0)
        print(f"   Cumulative delta: {delta_value:,}", flush=True)
        print(f"   Buy volume: {buy_vol:,} contracts", flush=True)
        print(f"   Sell volume: {sell_vol:,} contracts", flush=True)
        print(f"   Neutral volume: {neutral_vol:,} contracts", flush=True)
        print(f"   Trades analyzed: {trade_count}", flush=True)
        # Determine trend
        if delta_value > 1000:
            trend = "strong bullish"
        elif delta_value > 0:
            trend = "bullish"
        elif delta_value < -1000:
            trend = "strong bearish"
        elif delta_value < 0:
            trend = "bearish"
        else:
            trend = "neutral"
        print(f"   Delta trend: {trend}", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    print("\n13. get_trade_flow_summary():", flush=True)
    try:
        trade_flow = await orderbook.get_trade_flow_summary()
        total_trades = trade_flow.get("total_trades", 0)
        aggressive_buy = trade_flow.get("aggressive_buy_volume", 0)
        aggressive_sell = trade_flow.get("aggressive_sell_volume", 0)
        avg_trade_size = trade_flow.get("avg_trade_size", 0)
        vwap = trade_flow.get("vwap", None)
        print(f"   Trades analyzed: {total_trades}", flush=True)
        print(f"   Aggressive buy volume: {aggressive_buy:,} contracts", flush=True)
        print(f"   Aggressive sell volume: {aggressive_sell:,} contracts", flush=True)
        print(f"   Average trade size: {avg_trade_size:.1f}", flush=True)
        if vwap:
            print(f"   VWAP: ${vwap:.2f}", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    # 6. Support/Resistance Methods
    print("\n📈 SUPPORT/RESISTANCE METHODS", flush=True)
    print("-" * 40)

    print("14. get_support_resistance_levels():", flush=True)
    try:
        sr_levels = await orderbook.get_support_resistance_levels()
        support_levels = sr_levels.get("support_levels", [])
        resistance_levels = sr_levels.get("resistance_levels", [])
        print(f"   Support levels found: {len(support_levels)}", flush=True)
        print(f"   Resistance levels found: {len(resistance_levels)}", flush=True)
        if support_levels:
            first_support = support_levels[0]
            if isinstance(first_support, dict):
                price = first_support.get("price", 0)
                print(f"   Strongest support: ${price:.2f}", flush=True)
            else:
                print(f"   Strongest support: ${first_support:.2f}", flush=True)
        if resistance_levels:
            first_resistance = resistance_levels[0]
            if isinstance(first_resistance, dict):
                price = first_resistance.get("price", 0)
                print(f"   Strongest resistance: ${price:.2f}", flush=True)
            else:
                print(f"   Strongest resistance: ${first_resistance:.2f}", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    # 7. Spread Analysis
    print("\n📊 SPREAD ANALYSIS", flush=True)
    print("-" * 40)

    print("15. get_spread_analysis():", flush=True)
    try:
        spread_analysis = await orderbook.get_spread_analysis()
        current_spread = spread_analysis.get("current_spread", 0)
        avg_spread = spread_analysis.get("average_spread", 0)
        min_spread = spread_analysis.get("min_spread", 0)
        max_spread = spread_analysis.get("max_spread", 0)
        print(f"   Current spread: ${current_spread:.2f}", flush=True)
        print(f"   Average spread: ${avg_spread:.2f}", flush=True)
        print(f"   Min spread: ${min_spread:.2f}", flush=True)
        print(f"   Max spread: ${max_spread:.2f}", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    # 8. Statistical Analysis Methods
    print("\n📊 STATISTICAL ANALYSIS METHODS", flush=True)
    print("-" * 40)

    print("16. get_statistics():", flush=True)
    try:
        stats = await orderbook.get_statistics()
        print(f"   Instrument: {stats.get('instrument', 'N/A')}", flush=True)
        print(f"   Level 2 updates: {stats.get('update_count', 0)}", flush=True)
        print(f"   Total trades: {stats.get('total_trades', 0)}", flush=True)
        print(f"   Bid levels: {stats.get('bid_levels', 0)}", flush=True)
        print(f"   Ask levels: {stats.get('ask_levels', 0)}", flush=True)
        if "spread_stats" in stats:
            spread_stats = stats["spread_stats"]
            print(
                f"   Average spread: ${spread_stats.get('average', 0):.2f}", flush=True
            )
            print(
                f"   Current spread: ${spread_stats.get('current', 0):.2f}", flush=True
            )
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    print("\n17. get_order_type_statistics():", flush=True)
    try:
        order_stats = await orderbook.get_order_type_statistics()
        print(f"   Type 1 (Ask): {order_stats.get('type_1_count', 0)}", flush=True)
        print(f"   Type 2 (Bid): {order_stats.get('type_2_count', 0)}", flush=True)
        print(f"   Type 5 (Trade): {order_stats.get('type_5_count', 0)}", flush=True)
        print(f"   Type 6 (Reset): {order_stats.get('type_6_count', 0)}", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    # 9. Memory and Performance
    print("\n💾 MEMORY AND PERFORMANCE", flush=True)
    print("-" * 40)

    print("18. get_memory_stats():", flush=True)
    try:
        stats = await orderbook.get_memory_stats()
        for key, value in stats.items():
            if isinstance(value, int | float):
                print(
                    f"   {key}: {value:,}"
                    if isinstance(value, int)
                    else f"   {key}: {value:.2f}",
                    flush=True,
                )
            else:
                print(f"   {key}: {value}", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    # 10. Data Management
    print("\n🧹 DATA MANAGEMENT", flush=True)
    print("-" * 40)

    print("19. get_recent_trades():", flush=True)
    try:
        recent_trades = await orderbook.get_recent_trades(count=5)
        print(f"   Recent trades: {len(recent_trades)} trades", flush=True)
        for i, trade in enumerate(recent_trades[:3], 1):
            price = trade.get("price", 0)
            volume = trade.get("volume", 0)
            side = trade.get("side", "unknown")
            print(f"   Trade {i}: ${price:.2f} x{volume} ({side})", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    print("\n20. get_price_level_history():", flush=True)
    try:
        # Get current best bid for testing
        best_prices = await orderbook.get_best_bid_ask()
        best_bid = best_prices.get("bid")
        if best_bid:
            # Access price_level_history attribute directly
            async with orderbook.orderbook_lock:
                history = orderbook.price_level_history.get((best_bid, "bid"), [])
            print(
                f"   History for bid ${best_bid:.2f}: {len(history)} updates",
                flush=True,
            )
            if history:
                # Show last few updates
                for update in history[-3:]:
                    print(
                        f"      Volume: {update.get('volume', 0)}, "
                        f"Time: {update.get('timestamp', 'N/A')}",
                        flush=True,
                    )
        else:
            print("   No bid prices available for history test", flush=True)
    except Exception as e:
        print(f"   ❌ Error: {e}", flush=True)

    print("\n21. clear_orderbook() & clear_recent_trades():", flush=True)
    # Don't actually clear during demo
    print("   Methods available for clearing orderbook data", flush=True)
    print("   clear_orderbook(): Resets bids, asks, trades, and history", flush=True)
    print("   clear_recent_trades(): Clears only the trade history", flush=True)

    print(
        "\n✅ Comprehensive AsyncOrderBook method demonstration completed!", flush=True
    )
    print("📊 Total methods demonstrated: 21 async methods", flush=True)
    print(
        "🎯 Feature coverage: Basic data, liquidity analysis, volume profiling,",
        flush=True,
    )
    print(
        "   market microstructure, statistical analysis, and memory management",
        flush=True,
    )


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
        print("🔑 Initializing ProjectX client...", flush=True)
        async with ProjectX.from_env() as client:
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
                realtime_client = create_realtime_client(jwt_token, str(account.id))

                # Connect the realtime client
                print("   Connecting to real-time WebSocket feeds...", flush=True)
                if await realtime_client.connect():
                    print("   ✅ Real-time client connected successfully", flush=True)
                else:
                    print(
                        "   ⚠️ Real-time client connection failed - continuing with limited functionality"
                    )

                # Get contract ID first
                print("   Getting contract ID for MNQ...", flush=True)
                instrument_obj = await client.get_instrument("MNQ")
                if not instrument_obj:
                    print("   ❌ Failed to get contract ID for MNQ", flush=True)
                    return False

                contract_id = instrument_obj.id
                print(f"   Contract ID: {contract_id}", flush=True)

                # Note: We use the full contract ID for proper matching
                orderbook = create_orderbook(
                    instrument=contract_id,
                    realtime_client=realtime_client,
                    project_x=client,
                )

                # Initialize the orderbook with real-time capabilities
                await orderbook.initialize(realtime_client)
                print("✅ Async Level 2 orderbook created for MNQ", flush=True)

                # Subscribe to market data for this contract
                print("   Subscribing to market data...", flush=True)
                success = await realtime_client.subscribe_market_data([contract_id])
                if success:
                    print("   ✅ Market data subscription successful", flush=True)
                else:
                    print(
                        "   ⚠️ Market data subscription may have failed (might already be subscribed)"
                    )
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
                "Waiting 45 seconds to make sure orderbook is full for testing!!",
                flush=True,
            )
            await asyncio.sleep(45)
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
            print("   ✅ Real-time bid/ask levels and depth analysis", flush=True)
            print("   ✅ Liquidity levels and market imbalance detection", flush=True)
            print("   ✅ Order clusters and iceberg order detection", flush=True)
            print("   ✅ Cumulative delta and volume profile analysis", flush=True)
            print("   ✅ Trade flow and market microstructure analysis", flush=True)
            print("   ✅ Support/resistance level identification", flush=True)
            print("   ✅ Spread analysis and statistics", flush=True)
            print("   ✅ Memory management and performance monitoring", flush=True)
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
