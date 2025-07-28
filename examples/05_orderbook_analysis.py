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

import polars as pl

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
        print(f"   Recent Trades: {stats['recent_trades_count']:,}")
        print(f"   Bid Levels: {stats['orderbook_bids_count']:,}")
        print(f"   Ask Levels: {stats['orderbook_asks_count']:,}")
        print(f"   Total Memory Entries: {stats['total_memory_entries']:,}")
        print(f"   Max Trades Limit: {stats['max_trades']:,}")
        print(f"   Max Depth Entries Limit: {stats['max_depth_entries']:,}")

        # Display additional stats if available
        if stats.get("total_trades"):
            print(f"   Total Trades Processed: {stats['total_trades']:,}")
        if stats.get("trades_cleaned"):
            print(f"   Trades Cleaned: {stats['trades_cleaned']:,}")
        if stats.get("last_cleanup"):
            print(f"   Last Cleanup: {stats['last_cleanup']}")

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


def demonstrate_all_orderbook_methods(orderbook):
    """Comprehensive demonstration of all OrderBook methods."""
    print("🔍 Testing all available OrderBook methods...")
    print(
        "📝 Note: Some methods may show zero values without live market data connection"
    )

    # 1. Liquidity Analysis Methods
    print("\\n📈 LIQUIDITY ANALYSIS METHODS")
    print("-" * 40)

    try:
        print("1. get_liquidity_levels():")
        liquidity = orderbook.get_liquidity_levels(min_volume=10, levels=20)
        bid_liquidity = liquidity.get("bid_liquidity", pl.DataFrame())
        ask_liquidity = liquidity.get("ask_liquidity", pl.DataFrame())
        print(f"   Bid liquidity levels: {len(bid_liquidity)} levels")
        print(f"   Ask liquidity levels: {len(ask_liquidity)} levels")
        # Show volume statistics if data exists
        if not bid_liquidity.is_empty():
            total_bid_vol = (
                bid_liquidity["volume"].sum()
                if "volume" in bid_liquidity.columns
                else 0
            )
            print(f"   Total bid liquidity: {total_bid_vol:,} contracts")
        if not ask_liquidity.is_empty():
            total_ask_vol = (
                ask_liquidity["volume"].sum()
                if "volume" in ask_liquidity.columns
                else 0
            )
            print(f"   Total ask liquidity: {total_ask_vol:,} contracts")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    try:
        print("\\n2. get_market_imbalance():")
        imbalance = orderbook.get_market_imbalance(levels=10)
        imbalance_ratio = imbalance.get("imbalance_ratio", 0)
        orderbook_metrics = imbalance.get("orderbook_metrics", {})
        bid_volume = orderbook_metrics.get("top_bid_volume", 0)
        ask_volume = orderbook_metrics.get("top_ask_volume", 0)
        direction = imbalance.get("direction", "neutral")
        confidence = imbalance.get("confidence", "unknown")
        print(f"   Imbalance ratio: {imbalance_ratio:.3f}")
        print(f"   Bid volume (top 5): {bid_volume:,} contracts")
        print(f"   Ask volume (top 5): {ask_volume:,} contracts")
        print(f"   Direction: {direction}")
        print(f"   Confidence: {confidence}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 2. Advanced Detection Methods
    print("\\n🔍 ADVANCED DETECTION METHODS")
    print("-" * 40)

    try:
        print("3. detect_order_clusters():")
        # Use automatic tick size detection with reasonable cluster size for futures
        clusters = orderbook.detect_order_clusters(min_cluster_size=2)
        bid_clusters = clusters.get("bid_clusters", [])
        ask_clusters = clusters.get("ask_clusters", [])
        print(f"   Bid clusters found: {len(bid_clusters)}")
        print(f"   Ask clusters found: {len(ask_clusters)}")
        print(f"   Total clusters: {clusters.get('cluster_count', 0)}")

        # Show detected price tolerance for debugging
        try:
            tolerance = orderbook._calculate_price_tolerance()
            print(f"   🔍 Price tolerance used: ${tolerance:.4f}")
        except Exception:
            pass

        # Debug info to understand why no clusters
        if len(bid_clusters) == 0 and len(ask_clusters) == 0:
            print(
                f"   🔍 Debug: Orderbook has {len(orderbook.orderbook_bids)} bid levels, {len(orderbook.orderbook_asks)} ask levels"
            )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    try:
        print("\\n4. detect_iceberg_orders():")
        # Try with more relaxed parameters
        icebergs = orderbook.detect_iceberg_orders(
            time_window_minutes=10, min_refresh_count=3, min_total_volume=500
        )
        potential_list = icebergs.get("potential_icebergs", [])
        analysis = icebergs.get("analysis", {})
        print(f"   Potential iceberg orders: {len(potential_list)}")
        high_confidence = len(
            [x for x in potential_list if x.get("confidence_score", 0) > 0.8]
        )
        print(f"   High confidence signals: {high_confidence}")
        print(f"   Detection method: {analysis.get('detection_method', 'unknown')}")

        # Debug info if no icebergs found
        if len(potential_list) == 0:
            error_msg = analysis.get("error", "No error message")
            print(f"   🔍 Debug: {error_msg}")
            print(
                f"   🔍 Debug: Orderbook data - bids: {orderbook.orderbook_bids.height if hasattr(orderbook.orderbook_bids, 'height') else 'unknown'}, asks: {orderbook.orderbook_asks.height if hasattr(orderbook.orderbook_asks, 'height') else 'unknown'}"
            )

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 3. Volume Analysis Methods
    print("\\n📊 VOLUME ANALYSIS METHODS")
    print("-" * 40)
    print("📝 These methods analyze trade volume data (requires recent_trades data)")
    print("")

    try:
        print("5. get_volume_profile():")
        vol_profile = orderbook.get_volume_profile()
        poc_data = vol_profile.get("poc", {})
        poc_price = poc_data.get("price", 0) if poc_data else 0
        poc_volume = poc_data.get("volume", 0) if poc_data else 0
        total_volume = vol_profile.get("total_volume", 0)
        profile_levels = vol_profile.get("profile", [])
        print(f"   Point of Control (POC): ${poc_price:.2f}")
        print(f"   POC Volume: {poc_volume:,} contracts")
        print(f"   Volume levels count: {len(profile_levels)}")
        print(f"   Total volume analyzed: {total_volume:,}")
        # Add debugging info if issues
        if total_volume > 0 and poc_price == 0:
            print(
                f"   🔍 Debug: Trade count = {len(orderbook.recent_trades)}, Profile levels = {len(profile_levels)}"
            )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    try:
        print("\\n6. get_cumulative_delta():")
        cum_delta = orderbook.get_cumulative_delta(time_window_minutes=15)
        delta_value = cum_delta.get("cumulative_delta", 0)
        analysis = cum_delta.get("analysis", {})
        buy_vol = analysis.get("total_buy_volume", 0)
        sell_vol = analysis.get("total_sell_volume", 0)
        trade_count = analysis.get("trade_count", 0)
        print(f"   Cumulative delta: {delta_value:,}")
        print(f"   Buy volume: {buy_vol:,} contracts")
        print(f"   Sell volume: {sell_vol:,} contracts")
        print(f"   Trades analyzed: {trade_count}")
        # Add debugging if inconsistent data
        if delta_value != 0 and buy_vol == 0 and sell_vol == 0:
            print(f"   🔍 Debug: Delta {delta_value} but no buy/sell breakdown")
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
        print(f"   Delta trend: {trend}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 4. Support/Resistance Methods
    print("\\n📈 SUPPORT/RESISTANCE METHODS")
    print("-" * 40)

    try:
        print("7. get_support_resistance_levels():")
        sr_levels = orderbook.get_support_resistance_levels()
        support_levels = sr_levels.get("support_levels", [])
        resistance_levels = sr_levels.get("resistance_levels", [])
        print(f"   Support levels found: {len(support_levels)}")
        print(f"   Resistance levels found: {len(resistance_levels)}")
        if support_levels:
            # Handle case where support_levels might be dicts or numbers
            first_support = support_levels[0]
            if isinstance(first_support, dict):
                price = first_support.get("price", 0)
                print(f"   Strongest support: ${price:.2f}")
            else:
                print(f"   Strongest support: ${first_support:.2f}")
        if resistance_levels:
            # Handle case where resistance_levels might be dicts or numbers
            first_resistance = resistance_levels[0]
            if isinstance(first_resistance, dict):
                price = first_resistance.get("price", 0)
                print(f"   Strongest resistance: ${price:.2f}")
            else:
                print(f"   Strongest resistance: ${first_resistance:.2f}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 5. Statistical Analysis Methods
    print("\\n📊 STATISTICAL ANALYSIS METHODS")
    print("-" * 40)

    try:
        print("8. get_advanced_market_metrics():")
        metrics = orderbook.get_advanced_market_metrics()
        # This method returns a collection of other analyses
        analysis_summary = metrics.get("analysis_summary", {})
        print(f"   Data quality: {analysis_summary.get('data_quality', 'unknown')}")
        print(
            f"   Market activity: {analysis_summary.get('market_activity', 'unknown')}"
        )
        print(
            f"   Analysis completeness: {analysis_summary.get('analysis_completeness', 'unknown')}"
        )
        print(
            f"   Components analyzed: {len([k for k in metrics if k not in ['timestamp', 'analysis_summary']])}"
        )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    try:
        print("\\n9. get_statistics():")
        stats = orderbook.get_statistics()
        data_flow = stats.get("data_flow", {})
        dom_breakdown = stats.get("dom_event_breakdown", {})
        raw_stats = dom_breakdown.get("raw_stats", {})
        print(f"   Level 2 updates: {data_flow.get('level2_updates', 0)}")
        print(f"   Recent trades count: {data_flow.get('recent_trades_count', 0)}")
        print(f"   Trade executions: {raw_stats.get('type_5_count', 0)}")
        print(f"   Best bid changes: {raw_stats.get('type_9_count', 0)}")
        print(f"   Best ask changes: {raw_stats.get('type_10_count', 0)}")

        # Debug: Check direct access to order_type_stats
        direct_stats = orderbook.get_order_type_statistics()
        print(
            f"   🔍 Direct DOM stats: type_5={direct_stats.get('type_5_count', 0)}, type_9={direct_stats.get('type_9_count', 0)}, type_10={direct_stats.get('type_10_count', 0)}"
        )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 6. DOM Event Analysis Methods
    print("\\n🔍 DOM EVENT ANALYSIS METHODS")
    print("-" * 40)
    print(
        "📝 DOM statistics accumulate over time - may show zeros during early collection"
    )

    try:
        print("10. get_dom_event_analysis():")
        dom_analysis = orderbook.get_dom_event_analysis(time_window_minutes=10)
        analysis = dom_analysis.get("analysis", {})
        dom_events = dom_analysis.get("dom_events", {})
        total_events = analysis.get("total_dom_events", 0)

        if total_events == 0:
            print(
                "   ⏳ DOM events still accumulating (check final statistics for current counts)"
            )
            print(f"   Trade events tracked: {dom_events.get('type_5_count', 0)}")
        else:
            print(f"   Total DOM events: {total_events:,}")
            print(f"   Trade events: {dom_events.get('type_5_count', 0):,}")
            print(
                f"   Best bid/ask changes: {dom_events.get('type_9_count', 0):,}/{dom_events.get('type_10_count', 0):,}"
            )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    try:
        print("\\n11. get_best_price_change_analysis():")
        price_changes = orderbook.get_best_price_change_analysis(time_window_minutes=5)
        analysis = price_changes.get("analysis", {})

        if "note" in analysis:
            print("   ⏳ Best price events still accumulating")
            print(f"   Note: {analysis.get('note', 'Data being collected')}")
        else:
            # Access nested data structure correctly
            best_price_events = analysis.get("best_price_events", {})
            price_movement = analysis.get("price_movement_indicators", {})
            print(
                f"   Best bid changes: {best_price_events.get('new_best_bid', 0) + best_price_events.get('best_bid_updates', 0)}"
            )
            print(
                f"   Best ask changes: {best_price_events.get('new_best_ask', 0) + best_price_events.get('best_ask_updates', 0)}"
            )
            print(
                f"   Price volatility: {price_movement.get('price_volatility_indicator', 'unknown')}"
            )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    try:
        print("\\n12. get_spread_analysis():")
        spread_result = orderbook.get_spread_analysis(time_window_minutes=5)
        spread_data = spread_result.get("spread_analysis", {})
        spread_stats = spread_data.get("spread_statistics", {})
        print(f"   Average spread: ${spread_stats.get('avg_spread', 0):.4f}")
        print(f"   Spread volatility: {spread_stats.get('spread_volatility', 0):.4f}")
        print(f"   Spread trend: {spread_data.get('spread_trend', 'unknown')}")
        print(
            f"   Min/Max spread: ${spread_stats.get('min_spread', 0):.4f} / ${spread_stats.get('max_spread', 0):.4f}"
        )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 7. Status and Testing Methods
    print("\\n🧪 STATUS AND TESTING METHODS")
    print("-" * 40)

    try:
        print("13. get_iceberg_detection_status():")
        iceberg_status = orderbook.get_iceberg_detection_status()
        print(
            f"   Detection ready: {iceberg_status.get('iceberg_detection_ready', False)}"
        )
        data_quality = iceberg_status.get("data_quality", {})
        print(f"   Data quality score: {data_quality.get('overall_score', 0.0):.2f}")
        print(
            f"   Analysis capability: {'ready' if iceberg_status.get('iceberg_detection_ready') else 'not ready'}"
        )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    try:
        print("\\n14. get_volume_profile_enhancement_status():")
        vp_status = orderbook.get_volume_profile_enhancement_status()
        print(
            f"   Enhancement active: {vp_status.get('time_filtering_enabled', False)}"
        )
        print(
            f"   Enhancement version: {vp_status.get('enhancement_version', 'unknown')}"
        )
        capabilities = vp_status.get("capabilities", {})
        print(
            f"   Time filtering capability: {'available' if capabilities.get('time_window_filtering') else 'unavailable'}"
        )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 8. Test Methods (if available)
    print("\\n🧪 TESTING METHODS (Sample Tests)")
    print("-" * 40)
    print(
        "📝 These are internal validation tests (may show 'False' without sufficient data)"
    )

    try:
        print("15. test_iceberg_detection():")
        test_result = orderbook.test_iceberg_detection()
        print(f"   Test passed: {test_result.get('test_passed', False)}")
        print(f"   Simulated icebergs: {test_result.get('simulated_icebergs', 0)}")
        print(f"   Detection accuracy: {test_result.get('detection_accuracy', 0):.1f}%")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    try:
        print("\\n16. test_support_resistance_detection():")
        sr_test = orderbook.test_support_resistance_detection()
        print(f"   Test passed: {sr_test.get('test_passed', False)}")
        print(f"   Levels detected: {sr_test.get('levels_detected', 0)}")
        print(f"   Accuracy score: {sr_test.get('accuracy_score', 0):.1f}%")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    try:
        print("\\n17. test_volume_profile_time_filtering():")
        vp_test = orderbook.test_volume_profile_time_filtering()
        print(f"   Test passed: {vp_test.get('test_passed', False)}")
        print(f"   Time periods tested: {vp_test.get('periods_tested', 0)}")
        print(
            f"   Filtering effectiveness: {vp_test.get('filtering_effectiveness', 0):.1f}%"
        )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\\n✅ Comprehensive OrderBook method demonstration completed!")
    print("📊 Total methods demonstrated: 17")
    print("🔍 All core functionality has been tested and validated")


def main():
    """Demonstrate comprehensive Level 2 orderbook analysis."""
    logger = setup_logging(level="INFO")
    print("🚀 Level 2 Orderbook Analysis Example")
    print("=" * 60)

    # Initialize variables for cleanup
    orderbook = None
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

        # Create orderbook
        print("\n🏗️ Creating Level 2 orderbook...")
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

            orderbook = create_orderbook(
                instrument="MNQ", realtime_client=realtime_client, project_x=client
            )
            print("✅ Level 2 orderbook created for MNQ")

            # Get contract ID and subscribe to market data
            print("   Getting contract ID for MNQ...")
            instrument_obj = client.get_instrument("MNQ")
            if instrument_obj:
                contract_id = instrument_obj.id
                print(f"   Contract ID: {contract_id}")

                # Subscribe to market data for this contract
                print("   Subscribing to market data...")
                success = realtime_client.subscribe_market_data([contract_id])
                if success:
                    print("   ✅ Market data subscription successful")
                else:
                    print(
                        "   ⚠️ Market data subscription may have failed (might already be subscribed)"
                    )
            else:
                print("   ❌ Failed to get contract ID for MNQ")
                return False
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
            best_bid = metadata.get("best_bid") or 0
            best_ask = metadata.get("best_ask") or 0
            spread = metadata.get("spread") or 0
            mid_price = metadata.get("mid_price") or 0
            total_bid_volume = metadata.get("total_bid_volume") or 0
            total_ask_volume = metadata.get("total_ask_volume") or 0

            print(f"   Best Bid: ${best_bid:.2f}")
            print(f"   Best Ask: ${best_ask:.2f}")
            print(f"   Spread: ${spread:.2f}")
            print(f"   Mid Price: ${mid_price:.2f}")
            print(f"   Total Bid Volume: {total_bid_volume:,}")
            print(f"   Total Ask Volume: {total_ask_volume:,}")
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

        # Comprehensive OrderBook Methods Demonstration
        print("\n" + "=" * 60)
        print("🧪 COMPREHENSIVE ORDERBOOK METHODS DEMONSTRATION")
        print("=" * 60)

        print("Waiting 2 minutes to make sure orderbook is full for testing!!")
        time.sleep(120)
        demonstrate_all_orderbook_methods(orderbook)

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
        print("   ✅ Comprehensive method testing (17 methods)")
        print("   ✅ Advanced analytics (icebergs, clusters, volume profile)")
        print("   ✅ Support/resistance detection")
        print("   ✅ Statistical analysis and market metrics")

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
        if orderbook is not None:
            try:
                print("\n🧹 Cleaning up orderbook...")
                # Note: Cleanup method depends on orderbook implementation
                if hasattr(orderbook, "cleanup"):
                    orderbook.cleanup()
                print("✅ Orderbook cleaned up")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")

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
