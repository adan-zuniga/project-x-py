#!/usr/bin/env python3
"""
Example: Simplified Multi-Timeframe Strategy with v3.0.0

This example shows how the new convenience methods dramatically simplify
multi-timeframe strategy implementation by removing verbose data checks
and providing cleaner access patterns.

Compare this with 06_multi_timeframe_strategy.py to see the improvements!

Author: SDK v3.0.2 Examples
"""

import asyncio

from project_x_py import TradingSuite
from project_x_py.indicators import RSI, SMA


class SimplifiedMTFStrategy:
    """Multi-timeframe strategy using simplified data access."""

    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.data = suite["MNQ"].data  # Direct access to data manager
        self.position_size: int = 0
        self.last_signal_time: float | None = None

    async def analyze_market(self) -> dict | None:
        """Analyze market across multiple timeframes."""
        # Much cleaner than checking data is None and len(data) < X

        # 1. Long-term trend (4hr) - using get_data_or_none
        data_4hr = await self.data.get_data_or_none("4hr", min_bars=50)
        if data_4hr is None:
            return None  # Not enough data yet

        # Calculate long-term trend
        data_4hr = data_4hr.pipe(SMA, period=50)
        longterm = {
            "trend": "bullish"
            if data_4hr["close"][-1] > data_4hr["sma_50"][-1]
            else "bearish",
            "strength": abs(data_4hr["close"][-1] - data_4hr["sma_50"][-1])
            / data_4hr["sma_50"][-1],
        }

        # 2. Medium-term momentum (1hr) - simplified access
        data_1hr = await self.data.get_data_or_none("1hr", min_bars=20)
        if data_1hr is None:
            return None

        data_1hr = data_1hr.pipe(RSI, period=14)
        medium = {
            "momentum": "strong" if data_1hr["rsi_14"][-1] > 50 else "weak",
            "rsi": float(data_1hr["rsi_14"][-1]),
        }

        # 3. Short-term entry (15min) - no verbose checks needed
        data_15min = await self.data.get_data_or_none("15min", min_bars=20)
        if data_15min is None:
            return None

        # Quick SMA cross calculation
        data_15min = data_15min.pipe(SMA, period=10).pipe(SMA, period=20)
        fast_sma = float(data_15min["sma_10"][-1])
        slow_sma = float(data_15min["sma_20"][-1])

        # 4. Get current price using new convenience method
        current_price = await self.data.get_latest_price()
        if current_price is None:
            return None

        # 5. Get recent price action stats
        price_stats = await self.data.get_price_range(bars=20, timeframe="15min")
        if price_stats is None:
            return None

        volume_stats = await self.data.get_volume_stats(bars=20, timeframe="15min")

        return {
            "longterm": longterm,
            "medium": medium,
            "entry": {
                "signal": "buy" if fast_sma > slow_sma else "sell",
                "strength": abs(fast_sma - slow_sma) / slow_sma,
            },
            "current_price": current_price,
            "price_position": (current_price - price_stats["low"])
            / price_stats["range"]
            if price_stats
            else 0.5,
            "volume_strength": volume_stats["relative"] if volume_stats else 1.0,
        }

    async def check_entry_conditions(self) -> dict | None:
        """Check if all conditions align for entry."""
        analysis = await self.analyze_market()
        if not analysis:
            return None

        # All timeframes must align
        if (
            analysis["longterm"]["trend"] == "bullish"
            and analysis["medium"]["momentum"] == "strong"
            and analysis["entry"]["signal"] == "buy"
            and analysis["medium"]["rsi"] < 70
        ):  # Not overbought
            # Additional filters using new methods
            if (
                analysis["volume_strength"] > 1.2 and analysis["price_position"] < 0.7
            ):  # Above average volume
                return {
                    "action": "BUY",
                    "confidence": min(
                        analysis["longterm"]["strength"],
                        analysis["entry"]["strength"],
                        analysis["volume_strength"] - 1.0,
                    ),
                }

        elif (
            analysis["longterm"]["trend"] == "bearish"
            and analysis["medium"]["momentum"] == "weak"
            and analysis["entry"]["signal"] == "sell"
            and analysis["medium"]["rsi"] > 30
            and analysis["volume_strength"] > 1.2
            and analysis["price_position"] > 0.3
        ):  # Not oversold
            return {
                "action": "SELL",
                "confidence": min(
                    analysis["longterm"]["strength"],
                    analysis["entry"]["strength"],
                    analysis["volume_strength"] - 1.0,
                ),
            }

        return None


async def run_simplified_mtf_strategy() -> None:
    """Run the simplified multi-timeframe strategy."""

    # Create suite with multiple timeframes
    async with await TradingSuite.create(
        "MNQ", timeframes=["15min", "1hr", "4hr"], initial_days=13
    ) as suite:
        strategy = SimplifiedMTFStrategy(suite)

        print("=== Simplified Multi-Timeframe Strategy ===")
        print("Waiting for sufficient data...\n")

        # Wait for data using the new is_data_ready method
        while not await suite["MNQ"].data.is_data_ready(min_bars=50, timeframe="4hr"):
            await asyncio.sleep(1)

        print("✅ Data ready, starting analysis...\n")

        # Monitor for signals
        signal_count = 0
        while signal_count < 3:  # Demo: stop after 3 signals
            # Check entry conditions
            signal = await strategy.check_entry_conditions()

            if signal and signal["confidence"] > 0.05:
                # Get current market snapshot using new methods
                price = await suite["MNQ"].data.get_latest_price()
                ohlc = await suite["MNQ"].data.get_ohlc("15min")

                print(f"\n🎯 SIGNAL: {signal['action']}")
                if price is not None:
                    print(f"   Price: ${price:,.2f}")
                print(f"   Confidence: {signal['confidence']:.1%}")
                if ohlc is not None:
                    print(
                        f"   15min Bar: O:{ohlc['open']:,.2f} H:{ohlc['high']:,.2f} "
                        f"L:{ohlc['low']:,.2f} C:{ohlc['close']:,.2f}"
                    )

                # Show multi-timeframe alignment
                print("\n   Timeframe Alignment:")
                analysis = await strategy.analyze_market()
                if analysis is None:
                    print("❌ Analysis is None")
                    return

                print(
                    f"   - 4hr: {analysis['longterm']['trend'].upper()} "
                    f"(strength: {analysis['longterm']['strength']:.1%})"
                )
                print(
                    f"   - 1hr: RSI {analysis['medium']['rsi']:.1f} "
                    f"({analysis['medium']['momentum']})"
                )
                print(f"   - 15min: {analysis['entry']['signal'].upper()} signal")
                print(f"   - Volume: {analysis['volume_strength']:.1%} of average")

                signal_count += 1

                # Wait before next signal
                await asyncio.sleep(30)

            else:
                # Show current status using simplified methods
                stats = await suite["MNQ"].data.get_price_range(bars=10, timeframe="15min")
                if stats:
                    print(
                        f"\r⏳ Monitoring... Price range: ${stats['range']:,.2f} "
                        f"(High: ${stats['high']:,.2f}, Low: ${stats['low']:,.2f})",
                        end="",
                        flush=True,
                    )

                await asyncio.sleep(5)

        print("\n\n✅ Strategy demonstration complete!")


async def compare_verbose_vs_simplified() -> None:
    """Show the difference between verbose and simplified patterns."""

    async with await TradingSuite.create("MNQ") as suite:
        print("\n=== Verbose vs Simplified Patterns ===\n")

        # VERBOSE PATTERN (old way)
        print("❌ VERBOSE PATTERN:")
        print("```python")
        print("data = await manager.get_data('5min')")
        print("if data is None or len(data) < 50:")
        print("    return None")
        print("# ... process data")
        print("```")

        # SIMPLIFIED PATTERN (new way)
        print("\n✅ SIMPLIFIED PATTERN:")
        print("```python")
        print("data = await manager.get_data_or_none('5min', min_bars=50)")
        print("if data is None:")
        print("    return None")
        print("# ... process data")
        print("```")

        # More examples
        print("\n❌ VERBOSE: Getting current price")
        print("```python")
        print("data = await manager.get_data('1min', bars=1)")
        print("if data is not None and not data.is_empty():")
        print("    price = float(data['close'][-1])")
        print("```")

        print("\n✅ SIMPLIFIED: Getting current price")
        print("```python")
        print("price = await manager.get_latest_price()")
        print("```")

        # Actual demonstration
        print("\n\nActual Results:")

        # Old verbose way
        import time

        start = time.time()
        data = await suite["MNQ"].data.get_data("5min")
        if data is not None and len(data) >= 20:
            last_close = float(data["close"][-1])
            print(
                f"Verbose method: ${last_close:,.2f} (took {time.time() - start:.3f}s)"
            )

        # New simplified way
        start = time.time()
        price = await suite["MNQ"].data.get_latest_price()
        if price is not None:
            print(f"Simplified method: ${price:,.2f} (took {time.time() - start:.3f}s)")


async def main() -> None:
    """Run all demonstrations."""
    try:
        # Run simplified multi-timeframe strategy
        await run_simplified_mtf_strategy()

        # Show comparison
        await compare_verbose_vs_simplified()

    except KeyboardInterrupt:
        print("\n\nStrategy interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("ProjectX SDK v3.0.2 - Simplified Multi-Timeframe Strategy")
    print("=" * 60)
    asyncio.run(main())
