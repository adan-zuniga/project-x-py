#!/usr/bin/env python3
"""
Example: Simplified Data Access with v3.0.0

This example demonstrates the new convenience methods for accessing market data
in the ProjectX SDK v3.0.2. These methods provide a cleaner, more intuitive API
for common data access patterns.

Key improvements:
- get_latest_bars() - Get recent bars without verbose parameters
- get_latest_price() - Clear method name for current price
- get_ohlc() - Get OHLC values as a simple dictionary
- get_price_range() - Calculate price statistics easily
- get_volume_stats() - Quick volume analysis
- is_data_ready() - Check if enough data is loaded
- get_bars_since() - Get data since a specific time

Author: SDK v3.0.2 Examples
"""

import asyncio
from datetime import datetime, timedelta

from project_x_py import TradingSuite


async def demonstrate_simplified_access() -> None:
    """Show the new simplified data access methods."""

    # Create trading suite with 3 timeframes
    async with await TradingSuite.create(
        "MNQ", timeframes=["1min", "5min", "15min"], initial_days=2
    ) as suite:
        print("=== Simplified Data Access Demo ===\n")

        # 1. Check if data is ready
        if await suite["MNQ"].data.is_data_ready(min_bars=50):
            print("✅ Sufficient data loaded for all timeframes")
        else:
            print("⏳ Waiting for more data...")
            await asyncio.sleep(5)

        # 2. Get latest price - much cleaner than get_current_price()
        price = await suite["MNQ"].data.get_latest_price()
        if price is not None:
            print(f"\n📊 Current Price: ${price:,.2f}")

        # 3. Get OHLC as a simple dictionary
        ohlc = await suite["MNQ"].data.get_ohlc("5min")
        if ohlc:
            print("\n📈 Latest 5min Bar:")
            print(f"   Open:   ${ohlc['open']:,.2f}")
            print(f"   High:   ${ohlc['high']:,.2f}")
            print(f"   Low:    ${ohlc['low']:,.2f}")
            print(f"   Close:  ${ohlc['close']:,.2f}")
            print(f"   Volume: {ohlc['volume']:,.0f}")

        # 4. Get latest few bars - cleaner syntax
        recent_bars = await suite["MNQ"].data.get_latest_bars(count=5, timeframe="1min")
        if recent_bars is not None:
            print("\n📊 Last 5 1-minute bars:")
            for i in range(len(recent_bars)):
                bar = recent_bars.row(i, named=True)
                print(
                    f"   {bar['timestamp']}: ${bar['close']:,.2f} (vol: {bar['volume']:,.0f})"
                )

        # 5. Get price range statistics
        range_stats = await suite["MNQ"].data.get_price_range(bars=20, timeframe="5min")
        if range_stats:
            print("\n📊 20-bar Price Range (5min):")
            print(f"   High:  ${range_stats['high']:,.2f}")
            print(f"   Low:   ${range_stats['low']:,.2f}")
            print(f"   Range: ${range_stats['range']:,.2f}")
            print(f"   Avg Range per Bar: ${range_stats['avg_range']:,.2f}")

        # 6. Get volume statistics
        vol_stats = await suite["MNQ"].data.get_volume_stats(bars=20, timeframe="5min")
        if vol_stats:
            print("\n📊 20-bar Volume Stats (5min):")
            print(f"   Current Volume: {vol_stats['current']:,.0f}")
            print(f"   Average Volume: {vol_stats['average']:,.0f}")
            print(f"   Relative Volume: {vol_stats['relative']:.1%}")

            if vol_stats["relative"] > 1.5:
                print("   ⚡ HIGH VOLUME ALERT!")

        # 7. Get bars since a specific time
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_activity = await suite["MNQ"].data.get_bars_since(one_hour_ago, "1min")
        if recent_activity is not None:
            print(f"\n📊 Bars in last hour: {len(recent_activity)}")

            # Calculate price movement
            if len(recent_activity) > 0:
                first_price = float(recent_activity["open"][0])
                last_price = float(recent_activity["close"][-1])
                change = last_price - first_price
                change_pct = (change / first_price) * 100

                print(f"   Price Change: ${change:+,.2f} ({change_pct:+.2f}%)")

        # 8. Multi-timeframe quick access
        print("\n📊 Multi-Timeframe Summary:")
        for tf in ["1min", "5min", "15min"]:
            bars = await suite["MNQ"].data.get_latest_bars(count=1, timeframe=tf)
            if bars is not None and not bars.is_empty():
                close = float(bars["close"][0])
                volume = float(bars["volume"][0])
                print(f"   {tf}: ${close:,.2f} (vol: {volume:,.0f})")


async def demonstrate_trading_usage() -> None:
    """Show how simplified access improves trading logic."""

    async with await TradingSuite.create("MNQ") as suite:
        print("\n=== Trading Logic with Simplified Access ===\n")

        # Wait for enough data
        while not await suite["MNQ"].data.is_data_ready(min_bars=50):
            print("Waiting for data...")
            await asyncio.sleep(1)

        # Simple trading logic using new methods
        price = await suite["MNQ"].data.get_latest_price()
        range_stats = await suite["MNQ"].data.get_price_range(bars=20)
        vol_stats = await suite["MNQ"].data.get_volume_stats(bars=20)

        if price is not None and range_stats and vol_stats:
            # Example strategy logic
            print(f"Current Price: ${price:,.2f}")
            print(f"20-bar Range: ${range_stats['range']:,.2f}")
            print(f"Volume Ratio: {vol_stats['relative']:.1%}")

            # Simple breakout detection
            if price > range_stats["high"]:
                print("🚀 Price breaking above 20-bar high!")
                if vol_stats["relative"] > 1.2:
                    print("   ✅ With above-average volume - Strong signal!")
                else:
                    print("   ⚠️ But volume is weak - Be cautious")

            elif price < range_stats["low"]:
                print("📉 Price breaking below 20-bar low!")
                if vol_stats["relative"] > 1.2:
                    print("   ✅ With above-average volume - Strong signal!")
                else:
                    print("   ⚠️ But volume is weak - Be cautious")

            else:
                range_position = (price - range_stats["low"]) / range_stats["range"]
                print(f"Price is {range_position:.1%} within the 20-bar range")


async def main() -> None:
    """Run all demonstrations."""
    try:
        # Show simplified data access
        await demonstrate_simplified_access()

        # Show trading usage
        await demonstrate_trading_usage()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("ProjectX SDK v3.0.2 - Simplified Data Access")
    print("=" * 50)
    asyncio.run(main())
