#!/usr/bin/env python3
"""
Advanced Orderbook Methods Example

Demonstrates ALL advanced orderbook analysis methods including:
- Market microstructure analysis
- Iceberg order detection with proper thresholds
- Order clustering detection
- Volume profile analysis
- Support/resistance level identification
- Liquidity analysis with correct parameters
- Spread analysis over time
- Order flow imbalance
- Market impact estimation
- Comprehensive statistics

This example shows how to properly use each method with appropriate
parameters for meaningful results.

Author: TexasCoding
Date: 2025-08-08
"""

import asyncio
import sys

from project_x_py import TradingSuite, setup_logging
from project_x_py.orderbook import OrderBook


async def demonstrate_market_microstructure(orderbook: OrderBook):
    """Demonstrate market microstructure analysis."""
    print("\n" + "=" * 60)
    print("🔬 MARKET MICROSTRUCTURE ANALYSIS")
    print("=" * 60)

    # Get advanced market metrics
    metrics = await orderbook.get_advanced_market_metrics()

    if metrics:
        # Book pressure analysis
        if "book_pressure" in metrics:
            bp = metrics["book_pressure"]
            print("\n📊 Book Pressure:")
            print(f"   Bid Pressure: {bp.get('bid_pressure', 0):.2f}")
            print(f"   Ask Pressure: {bp.get('ask_pressure', 0):.2f}")
            print(f"   Pressure Ratio: {bp.get('pressure_ratio', 0):.2%}")
            if bp.get("pressure_ratio", 0) > 0.1:
                print("   Signal: Buying pressure dominant 🟢")
            elif bp.get("pressure_ratio", 0) < -0.1:
                print("   Signal: Selling pressure dominant 🔴")
            else:
                print("   Signal: Balanced ⚖️")

        # Trade intensity
        if "trade_intensity" in metrics:
            ti = metrics["trade_intensity"]
            print("\n⚡ Trade Intensity:")
            print(f"   Trades/Minute: {ti.get('trades_per_minute', 0):.1f}")
            print(f"   Volume/Minute: {ti.get('volume_per_minute', 0):,.0f}")
            print(f"   Avg Trade Size: {ti.get('avg_trade_size', 0):.1f}")

        # Price concentration
        if "price_concentration" in metrics:
            pc = metrics["price_concentration"]
            print("\n🎯 Price Concentration:")
            print(f"   Bid Concentration: {pc.get('bid_concentration', 0):.3f}")
            print(f"   Ask Concentration: {pc.get('ask_concentration', 0):.3f}")
    else:
        print("   No microstructure data available")


async def demonstrate_iceberg_detection(orderbook: OrderBook):
    """Demonstrate iceberg order detection with proper parameters."""
    print("\n" + "=" * 60)
    print("🧊 ICEBERG ORDER DETECTION")
    print("=" * 60)

    # Use lower thresholds for better detection
    icebergs = await orderbook.detect_iceberg_orders(
        min_refreshes=2,  # Lower threshold
        volume_threshold=10,  # Lower volume requirement
        time_window_minutes=5,  # Shorter window
    )

    if icebergs and "iceberg_levels" in icebergs:
        levels = icebergs["iceberg_levels"]
        if levels:
            print(f"\n✅ Detected {len(levels)} potential iceberg orders:")
            for i, iceberg in enumerate(levels[:5], 1):
                side = iceberg["side"].upper()
                print(f"\n   {i}. {side} Iceberg at ${iceberg['price']:,.2f}")
                print(f"      Average Volume: {iceberg.get('avg_volume', 0):.1f}")
                print(f"      Refresh Count: {iceberg.get('refresh_count', 0)}")
                print(f"      Replenishments: {iceberg.get('replenishment_count', 0)}")
                print(
                    f"      Hidden Size Est: {iceberg.get('estimated_hidden_size', 0):,.0f}"
                )
                print(f"      Confidence: {iceberg.get('confidence', 0):.1%}")
        else:
            print("\n   No iceberg orders detected")
            print("   Note: Icebergs require specific refresh patterns to detect")

    print("\n💡 Detection Parameters Used:")
    params = icebergs.get("detection_parameters", {})
    print(f"   Min Refreshes: {params.get('min_refreshes', 'N/A')}")
    print(f"   Volume Threshold: {params.get('volume_threshold', 'N/A')}")
    print(f"   Time Window: {icebergs.get('analysis_window_minutes', 'N/A')} minutes")


async def demonstrate_order_clustering(orderbook: OrderBook):
    """Demonstrate order clustering detection."""
    print("\n" + "=" * 60)
    print("🎯 ORDER CLUSTERING ANALYSIS")
    print("=" * 60)

    clusters = await orderbook.detect_order_clusters(
        min_cluster_size=3, price_tolerance=0.25
    )

    if clusters:
        print(f"\n✅ Found {len(clusters)} order clusters:")
        for i, cluster in enumerate(clusters[:5], 1):
            side = cluster.get("side", "unknown").upper()
            print(f"\n   {i}. {side} Cluster at ${cluster['center_price']:,.2f}")
            print(f"      Price Range: ${cluster.get('price_range', 0):.2f}")
            print(f"      Order Count: {cluster.get('cluster_size', 0)}")
            print(f"      Total Volume: {cluster.get('total_volume', 0):,}")
            print(f"      Avg Order Size: {cluster.get('avg_order_size', 0):.1f}")

            significance = cluster.get("significance", "")
            if significance:
                print(f"      Significance: {significance}")
    else:
        print("\n   No significant order clusters detected")


async def demonstrate_volume_profile(orderbook: OrderBook):
    """Demonstrate volume profile analysis."""
    print("\n" + "=" * 60)
    print("📊 VOLUME PROFILE ANALYSIS")
    print("=" * 60)

    profile = await orderbook.get_volume_profile(time_window_minutes=30, price_bins=10)

    if profile and profile.get("poc"):
        print("\n✅ Volume Profile (30-minute window):")
        print(f"   Point of Control (POC): ${profile['poc']:,.2f}")
        print(f"   Value Area High: ${profile.get('value_area_high', 0):,.2f}")
        print(f"   Value Area Low: ${profile.get('value_area_low', 0):,.2f}")
        print(f"   Total Volume: {profile.get('total_volume', 0):,}")

        # Show top volume levels
        if "price_bins" in profile and "volumes" in profile:
            bins = profile["price_bins"]
            vols = profile["volumes"]
            if bins and vols:
                print("\n   Top Volume Levels:")
                sorted_levels = sorted(
                    zip(bins, vols, strict=False), key=lambda x: x[1], reverse=True
                )
                for price, vol in sorted_levels[:3]:
                    if vol > 0:
                        pct = (
                            (vol / profile["total_volume"] * 100)
                            if profile["total_volume"] > 0
                            else 0
                        )
                        print(f"   ${price:,.2f}: {vol:,} ({pct:.1f}%)")
    else:
        print("\n   Insufficient trade data for volume profile")
        print("   Note: Volume profile requires trade history")


async def demonstrate_support_resistance(orderbook: OrderBook):
    """Demonstrate support and resistance level detection."""
    print("\n" + "=" * 60)
    print("📈 SUPPORT & RESISTANCE LEVELS")
    print("=" * 60)

    levels = await orderbook.get_support_resistance_levels(
        lookback_minutes=60, min_touches=2, price_tolerance=0.25
    )

    if levels:
        current_price = (await orderbook.get_best_bid_ask()).get("mid", 0)

        # Support levels
        supports = levels.get("support_levels", [])
        if supports:
            print(f"\n📉 Support Levels (below ${current_price:,.2f}):")
            for i, level in enumerate(supports[:3], 1):
                print(f"   S{i}: ${level['price']:,.2f}")
                print(f"       Touches: {level.get('touches', 0)}")
                print(f"       Strength: {level.get('strength', 0):.1%}")
                print(f"       Volume: {level.get('volume_at_level', 0):,}")

        # Resistance levels
        resistances = levels.get("resistance_levels", [])
        if resistances:
            print(f"\n📈 Resistance Levels (above ${current_price:,.2f}):")
            for i, level in enumerate(resistances[:3], 1):
                print(f"   R{i}: ${level['price']:,.2f}")
                print(f"       Touches: {level.get('touches', 0)}")
                print(f"       Strength: {level.get('strength', 0):.1%}")
                print(f"       Volume: {level.get('volume_at_level', 0):,}")

        # Key statistics
        stats = levels.get("statistics", {})
        if stats:
            print("\n📊 Level Statistics:")
            print(f"   Strongest Support: ${stats.get('strongest_support', 0):,.2f}")
            print(
                f"   Strongest Resistance: ${stats.get('strongest_resistance', 0):,.2f}"
            )
            print(f"   Price Range Analyzed: ${stats.get('price_range', 0):.2f}")
    else:
        print("\n   No significant support/resistance levels detected")


async def demonstrate_liquidity_analysis(orderbook: OrderBook):
    """Demonstrate liquidity analysis with proper parameters."""
    print("\n" + "=" * 60)
    print("💧 LIQUIDITY ANALYSIS")
    print("=" * 60)

    # Get current orderbook state first
    bids = await orderbook.get_orderbook_bids(levels=20)
    asks = await orderbook.get_orderbook_asks(levels=20)

    # Show raw liquidity
    if not bids.is_empty() and not asks.is_empty():
        bid_liquidity = bids["volume"].sum()
        ask_liquidity = asks["volume"].sum()

        print("\n📊 Current Liquidity (20 levels):")
        print(f"   Bid Liquidity: {bid_liquidity:,} contracts")
        print(f"   Ask Liquidity: {ask_liquidity:,} contracts")
        print(f"   Total Liquidity: {bid_liquidity + ask_liquidity:,} contracts")

        # Find significant levels (volume > average)
        bid_mean = bids["volume"].mean() if not bids.is_empty() else None
        ask_mean = asks["volume"].mean() if not asks.is_empty() else None

        avg_bid_vol = (
            float(bid_mean)
            if bid_mean is not None and isinstance(bid_mean, int | float)
            else 0.0
        )
        avg_ask_vol = (
            float(ask_mean)
            if ask_mean is not None and isinstance(ask_mean, int | float)
            else 0.0
        )

        print("\n🎯 Significant Levels (above average):")
        print(f"   Average Bid Size: {avg_bid_vol:.1f}")
        print(f"   Average Ask Size: {avg_ask_vol:.1f}")

        # Show large bid levels
        large_bids = bids.filter(bids["volume"] > avg_bid_vol * 1.5)
        if not large_bids.is_empty():
            print("\n   Large Bid Levels:")
            for row in large_bids.head(3).to_dicts():
                print(f"   ${row['price']:,.2f}: {row['volume']} contracts")

        # Show large ask levels
        large_asks = asks.filter(asks["volume"] > avg_ask_vol * 1.5)
        if not large_asks.is_empty():
            print("\n   Large Ask Levels:")
            for row in large_asks.head(3).to_dicts():
                print(f"   ${row['price']:,.2f}: {row['volume']} contracts")

    # Use get_liquidity_levels with appropriate threshold
    liquidity = await orderbook.get_liquidity_levels(
        min_volume=int(avg_bid_vol) if avg_bid_vol > 0 else 5, levels=20
    )

    if liquidity:
        sig_bids = liquidity.get("bid_levels", [])
        sig_asks = liquidity.get("ask_levels", [])

        if sig_bids or sig_asks:
            print("\n💎 Premium Liquidity Levels:")
            print(f"   Significant Bid Levels: {len(sig_bids)}")
            print(f"   Significant Ask Levels: {len(sig_asks)}")


async def demonstrate_spread_analysis(orderbook: OrderBook):
    """Demonstrate spread analysis over time."""
    print("\n" + "=" * 60)
    print("📏 SPREAD ANALYSIS")
    print("=" * 60)

    spread_analysis = await orderbook.get_spread_analysis(window_minutes=15)

    if spread_analysis:
        print("\n✅ Spread Analysis (15-minute window):")
        print(f"   Current Spread: ${spread_analysis.get('current_spread', 0):.2f}")
        print(f"   Average Spread: ${spread_analysis.get('avg_spread', 0):.2f}")
        print(f"   Min Spread: ${spread_analysis.get('min_spread', 0):.2f}")
        print(f"   Max Spread: ${spread_analysis.get('max_spread', 0):.2f}")
        print(
            f"   Spread Volatility: {spread_analysis.get('spread_volatility', 0):.3f}"
        )

        # Spread distribution
        if "spread_distribution" in spread_analysis:
            dist = spread_analysis["spread_distribution"]
            if isinstance(dist, dict) and dist:
                print("\n   Spread Distribution:")
                for spread_val, pct in dist.items():  # type: ignore[misc]
                    print(f"   ${spread_val}: {pct:.1f}%")
    else:
        print("\n   Insufficient data for spread analysis")


async def demonstrate_cumulative_delta(orderbook):
    """Demonstrate order flow imbalance analysis."""
    print("\n" + "=" * 60)
    print("⚖️ CUMULATIVE DELTA ANALYSIS")
    print("=" * 60)

    # Use get_cumulative_delta with correct parameter name
    delta = await orderbook.get_cumulative_delta(time_window_minutes=10)

    if delta:
        print("\n✅ Delta Analysis (10-minute window):")
        print(f"   Buy Volume: {delta.get('buy_volume', 0):,}")
        print(f"   Sell Volume: {delta.get('sell_volume', 0):,}")
        print(f"   Cumulative Delta: {delta.get('cumulative_delta', 0):+,}")

        # Calculate imbalance ratio
        total_vol = delta.get("buy_volume", 0) + delta.get("sell_volume", 0)
        if total_vol > 0:
            imbalance_ratio = (
                delta.get("buy_volume", 0) - delta.get("sell_volume", 0)
            ) / total_vol
            print(f"   Imbalance Ratio: {imbalance_ratio:+.2%}")

            # Flow direction
            if imbalance_ratio > 0.2:
                print("   Flow Direction: Strong Buying 🟢🟢")
            elif imbalance_ratio > 0.1:
                print("   Flow Direction: Buying 🟢")
            elif imbalance_ratio < -0.2:
                print("   Flow Direction: Strong Selling 🔴🔴")
            elif imbalance_ratio < -0.1:
                print("   Flow Direction: Selling 🔴")
            else:
                print("   Flow Direction: Balanced ⚖️")

        # Delta trend
        if "delta_trend" in delta:
            print(f"\n   Delta Trend: {delta['delta_trend']}")
    else:
        print("\n   Insufficient trade data for delta analysis")


async def demonstrate_market_depth_impact(orderbook: OrderBook):
    """Demonstrate market impact estimation."""
    print("\n" + "=" * 60)
    print("💥 MARKET DEPTH & IMPACT ANALYSIS")
    print("=" * 60)

    # Use get_orderbook_depth for market impact analysis
    price_ranges = [10.0, 25.0, 50.0, 100.0]

    for price_range in price_ranges:
        print(f"\n📦 Market Depth within {price_range:.0f} tick range:")

        # Get market depth analysis
        depth_analysis = await orderbook.get_orderbook_depth(price_range=price_range)

        if depth_analysis:
            print(f"   Total Bid Volume: {depth_analysis.get('total_bid_volume', 0):,}")
            print(f"   Total Ask Volume: {depth_analysis.get('total_ask_volume', 0):,}")
            print(
                f"   Estimated Fill Price: ${depth_analysis.get('estimated_fill_price', 0):,.2f}"
            )
            print(f"   Price Impact: {depth_analysis.get('price_impact_pct', 0):.2%}")
            print(f"   Levels Consumed: {depth_analysis.get('levels_consumed', 0)}")
            print(
                f"   Market Depth Score: {depth_analysis.get('market_depth_score', 0):.2f}"
            )
        else:
            print("   Insufficient depth data")


async def demonstrate_comprehensive_stats(orderbook: OrderBook):
    """Demonstrate comprehensive orderbook statistics."""
    print("\n" + "=" * 60)
    print("📈 COMPREHENSIVE STATISTICS")
    print("=" * 60)

    stats = await orderbook.get_statistics()

    if stats:
        print("\n✅ Orderbook Statistics:")

        # Depth stats
        print("\n📊 Depth Statistics:")
        print(f"   Bid Levels: {stats.get('bid_depth', 0)}")
        print(f"   Ask Levels: {stats.get('ask_depth', 0)}")
        print(f"   Total Bid Volume: {stats.get('total_bid_size', 0):,}")
        print(f"   Total Ask Volume: {stats.get('total_ask_size', 0):,}")

        # Trade stats
        print("\n📉 Trade Statistics:")
        print(f"   Total Trades: {stats.get('total_trades', 0):,}")
        print(f"   Buy Trades: {stats.get('buy_trades', 0):,}")
        print(f"   Sell Trades: {stats.get('sell_trades', 0):,}")
        print(f"   Avg Trade Size: {stats.get('avg_trade_size', 0):.1f}")

        # Price stats
        print("\n💰 Price Statistics:")
        print(f"   VWAP: ${stats.get('vwap', 0):,.2f}")
        print(f"   Current Mid: ${stats.get('mid_price', 0):,.2f}")
        print(f"   Session High: ${stats.get('session_high', 0):,.2f}")
        print(f"   Session Low: ${stats.get('session_low', 0):,.2f}")

        # Performance
        memory = await orderbook.get_memory_stats()
        print("\n⚡ Performance:")
        print(f"   Updates Processed: {stats.get('level2_update_count', 0):,}")
        print(f"   Memory Cleanups: {memory.get('memory_cleanups', 0)}")
        print(f"   Total Volume: {memory.get('total_volume', 0):,}")


async def main():
    """Main demonstration of advanced orderbook methods."""
    logger = setup_logging(level="INFO")

    print("🚀 Advanced Orderbook Methods Demonstration")
    print("=" * 60)
    print("\nThis example demonstrates ALL advanced orderbook analysis methods")
    print("with proper parameters for meaningful results.\n")

    try:
        # Initialize trading suite with orderbook
        print("🔑 Initializing TradingSuite with orderbook...")
        suite = await TradingSuite.create(
            "MNQ", features=["orderbook"], timeframes=["1min", "5min"], initial_days=1
        )

        print("✅ Suite initialized successfully!")
        if suite.client.account_info:
            print(f"   Account: {suite.client.account_info.name}")
        if suite["MNQ"].orderbook:
            print(f"   Tracking: {suite["MNQ"].orderbook.instrument}")

        # Wait for initial data
        print("\n⏳ Collecting market data for 10 seconds...")
        await asyncio.sleep(10)

        orderbook: OrderBook | None = suite["MNQ"].orderbook
        if not orderbook:
            raise ValueError("Orderbook not found")

        # Run all demonstrations
        await demonstrate_market_microstructure(orderbook)
        await demonstrate_iceberg_detection(orderbook)
        await demonstrate_order_clustering(orderbook)
        await demonstrate_volume_profile(orderbook)
        await demonstrate_support_resistance(orderbook)
        await demonstrate_liquidity_analysis(orderbook)
        await demonstrate_spread_analysis(orderbook)
        await demonstrate_cumulative_delta(orderbook)
        await demonstrate_market_depth_impact(orderbook)
        await demonstrate_comprehensive_stats(orderbook)

        # Final summary
        print("\n" + "=" * 60)
        print("✅ DEMONSTRATION COMPLETE")
        print("=" * 60)
        print("\n📝 Key Takeaways:")
        print("   • Use appropriate thresholds for each method")
        print("   • Some patterns (icebergs) require specific market conditions")
        print("   • Liquidity analysis needs proper volume thresholds")
        print("   • Volume profile requires sufficient trade history")
        print("   • Combine multiple methods for comprehensive analysis")

        await suite.disconnect()
        return True

    except KeyboardInterrupt:
        print("\n⏹️ Demonstration interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
