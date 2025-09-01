"""
RTH vs ETH Session Comparison Example

Demonstrates how to compare trading activity between regular and extended hours.
Shows volume, volatility, and price action differences.
"""
# type: ignore

import asyncio

from project_x_py import TradingSuite
from project_x_py.indicators import ATR, BBANDS
from project_x_py.sessions import (
    SessionAnalytics,
    SessionConfig,
    SessionType,
)


async def session_comparison_demo():
    """Compare RTH and ETH trading sessions."""

    print("=" * 60)
    print("RTH vs ETH SESSION COMPARISON")
    print("=" * 60)

    # Create two suites for each session type
    print("\nCreating TradingSuites for RTH and ETH...")

    # RTH Suite
    rth_suite = await TradingSuite.create(
        "MNQ",
        timeframes=["5min"],
        session_config=SessionConfig(session_type=SessionType.RTH),
        initial_days=10,
    )

    # ETH Suite
    eth_suite = await TradingSuite.create(
        "MNQ",
        timeframes=["5min"],
        session_config=SessionConfig(session_type=SessionType.ETH),
        initial_days=10,
    )

    try:
        # Get data from both sessions
        rth_context = rth_suite["MNQ"]
        eth_context = eth_suite["MNQ"]

        rth_data = await rth_context.data.get_session_data("5min", SessionType.RTH)
        eth_data = await eth_context.data.get_session_data("5min", SessionType.ETH)

        if rth_data is None or eth_data is None:
            print("Unable to get session data")
            return

        print("\nData loaded:")
        print(f"  RTH bars: {len(rth_data):,}")
        print(f"  ETH bars: {len(eth_data):,}")

        # 1. Basic Comparison
        print("\n1. BASIC SESSION METRICS")
        print("-" * 40)

        if not rth_data.is_empty() and not eth_data.is_empty():
            # Volume comparison
            rth_volume = rth_data["volume"].sum()
            eth_volume = eth_data["volume"].sum()

            print("\nVolume:")
            print(f"  RTH Total: {int(rth_volume):,}")
            print(f"  ETH Total: {int(eth_volume):,}")
            if eth_volume > 0:
                volume_ratio = rth_volume / eth_volume
                print(f"  Ratio: RTH has {volume_ratio:.2f}x more volume")

            # Average bar size
            rth_avg_volume = rth_data["volume"].mean()
            eth_avg_volume = eth_data["volume"].mean()

            if rth_avg_volume is not None and eth_avg_volume is not None:
                print("\nAverage Bar Volume:")
                print(f"  RTH: {int(rth_avg_volume):,} per bar")  # type: ignore
                print(f"  ETH: {int(eth_avg_volume):,} per bar")  # type: ignore

            # Price range
            rth_high = rth_data["high"].max()
            rth_low = rth_data["low"].min()
            eth_high = eth_data["high"].max()
            eth_low = eth_data["low"].min()

            if (
                rth_high is not None
                and rth_low is not None
                and eth_high is not None
                and eth_low is not None
            ):
                rth_range = float(rth_high) - float(rth_low)  # type: ignore
                eth_range = float(eth_high) - float(eth_low)  # type: ignore

                print("\nPrice Range:")
                print(
                    f"  RTH: ${rth_range:.2f} (${float(rth_low):.2f} - ${float(rth_high):.2f})"  # type: ignore
                )
                print(
                    f"  ETH: ${eth_range:.2f} (${float(eth_low):.2f} - ${float(eth_high):.2f})"  # type: ignore
                )

        # 2. Volatility Analysis
        print("\n2. VOLATILITY ANALYSIS")
        print("-" * 40)

        # Calculate ATR for both sessions
        rth_with_atr = rth_data.pipe(ATR, period=14)
        eth_with_atr = eth_data.pipe(ATR, period=14)

        if "atr_14" in rth_with_atr.columns and "atr_14" in eth_with_atr.columns:
            rth_atr = rth_with_atr["atr_14"].drop_nulls().mean()
            eth_atr = eth_with_atr["atr_14"].drop_nulls().mean()

            if rth_atr is not None and eth_atr is not None:
                print("\nAverage True Range (ATR):")
                print(f"  RTH: ${float(rth_atr):.2f}")  # type: ignore
                print(f"  ETH: ${float(eth_atr):.2f}")  # type: ignore

                if float(rth_atr) > float(eth_atr):  # type: ignore
                    diff_pct = ((float(rth_atr) / float(eth_atr)) - 1) * 100  # type: ignore
                    print(f"  → RTH is {diff_pct:.1f}% more volatile")
                else:
                    diff_pct = ((float(eth_atr) / float(rth_atr)) - 1) * 100  # type: ignore
                    print(f"  → ETH is {diff_pct:.1f}% more volatile")

        # Standard deviation of returns
        rth_returns = rth_data["close"].pct_change().drop_nulls()
        eth_returns = eth_data["close"].pct_change().drop_nulls()

        rth_std = rth_returns.std()
        eth_std = eth_returns.std()

        if rth_std is not None and eth_std is not None:
            print("\nReturn Volatility (Std Dev):")
            print(f"  RTH: {float(rth_std) * 100:.3f}%")  # type: ignore
            print(f"  ETH: {float(eth_std) * 100:.3f}%")  # type: ignore

        # 3. Bollinger Bands Width
        print("\n3. BOLLINGER BANDS ANALYSIS")
        print("-" * 40)

        rth_with_bb = rth_data.pipe(BBANDS, period=20)
        eth_with_bb = eth_data.pipe(BBANDS, period=20)

        if all(
            col in rth_with_bb.columns for col in ["bb_upper_20", "bb_lower_20"]
        ) and all(col in eth_with_bb.columns for col in ["bb_upper_20", "bb_lower_20"]):
            # Calculate average band width
            rth_bb_width = (
                (rth_with_bb["bb_upper_20"] - rth_with_bb["bb_lower_20"])
                .drop_nulls()
                .mean()
            )

            eth_bb_width = (
                (eth_with_bb["bb_upper_20"] - eth_with_bb["bb_lower_20"])
                .drop_nulls()
                .mean()
            )

            if rth_bb_width is not None and eth_bb_width is not None:
                print("\nAverage Bollinger Band Width:")
                print(f"  RTH: ${float(rth_bb_width):.2f}")  # type: ignore
                print(f"  ETH: ${float(eth_bb_width):.2f}")  # type: ignore

                # Wider bands indicate higher volatility
                if float(rth_bb_width) > float(eth_bb_width):  # type: ignore
                    print("  → RTH shows higher volatility (wider bands)")
                else:
                    print("  → ETH shows higher volatility (wider bands)")

        # 4. Using SessionAnalytics for comprehensive comparison
        print("\n4. COMPREHENSIVE SESSION ANALYTICS")
        print("-" * 40)

        # Get all data for analytics
        all_data = await rth_context.data.get_data("5min")

        if all_data is not None and not all_data.is_empty():
            analytics = SessionAnalytics()

            # Compare sessions
            comparison = await analytics.compare_sessions(all_data, "MNQ")

            if comparison:
                print("\nDetailed Comparison Results:")

                # Volume metrics
                if "rth_vs_eth_volume_ratio" in comparison:
                    print(
                        f"  Volume Ratio: {comparison['rth_vs_eth_volume_ratio']:.2f}x"
                    )

                # Volatility comparison
                if "rth_volatility" in comparison and "eth_volatility" in comparison:
                    rth_vol = comparison["rth_volatility"]
                    eth_vol = comparison["eth_volatility"]
                    print(f"  RTH Volatility: {rth_vol:.3%}")
                    print(f"  ETH Volatility: {eth_vol:.3%}")

                # Price efficiency
                if "rth_efficiency" in comparison and "eth_efficiency" in comparison:
                    print(f"  RTH Efficiency: {comparison['rth_efficiency']:.2f}")
                    print(f"  ETH Efficiency: {comparison['eth_efficiency']:.2f}")

        # 5. Trading Implications
        print("\n5. TRADING IMPLICATIONS")
        print("-" * 40)

        # Based on the analysis
        if rth_data is not None and eth_data is not None:
            rth_vol_total = rth_data["volume"].sum()
            eth_vol_total = eth_data["volume"].sum()

            print("\n📊 Key Insights:")

            # Volume insight
            if rth_vol_total > eth_vol_total * 2:
                print("  • RTH has significantly higher liquidity")
                print("    → Better for large orders and tighter spreads")
            else:
                print("  • ETH volume is relatively strong")
                print("    → Extended hours trading is viable")

            # Volatility insight
            if "atr_14" in rth_with_atr.columns:
                rth_atr_val = rth_with_atr["atr_14"].drop_nulls().mean()
                eth_atr_val = (
                    eth_with_atr["atr_14"].drop_nulls().mean()
                    if "atr_14" in eth_with_atr.columns
                    else None
                )

                if rth_atr_val and eth_atr_val:
                    if float(rth_atr_val) > float(eth_atr_val) * 1.2:  # type: ignore
                        print("\n  • RTH shows higher volatility")
                        print("    → Better for day trading strategies")
                    elif float(eth_atr_val) > float(rth_atr_val) * 1.2:  # type: ignore
                        print("\n  • ETH shows higher volatility")
                        print("    → Watch for overnight gaps and news")
                    else:
                        print("\n  • Similar volatility in both sessions")
                        print("    → Consistent trading conditions")

    finally:
        await rth_suite.disconnect()
        await eth_suite.disconnect()
        print("\n✅ Session comparison completed")


if __name__ == "__main__":
    asyncio.run(session_comparison_demo())
