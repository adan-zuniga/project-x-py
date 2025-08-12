#!/usr/bin/env python
"""
Debug script for Fair Value Gap indicator.

This script creates synthetic data with known FVG patterns and tests the indicator.
It also analyzes real data to understand why FVGs aren't being detected.

Author: ProjectX SDK
Date: 2025-01-12
"""

import asyncio
import os
import sys

import polars as pl

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_x_py import ProjectX
from project_x_py.indicators import FVG


def create_synthetic_fvg_data() -> pl.DataFrame:
    """Create synthetic OHLCV data with known Fair Value Gaps."""
    from datetime import datetime, timedelta

    base_time = datetime.now()

    # Create data with intentional FVG patterns
    data = {
        "timestamp": [base_time + timedelta(minutes=i * 15) for i in range(10)],
        "open": [100.0, 102.0, 105.0, 108.0, 104.0, 106.0, 103.0, 105.0, 107.0, 106.0],
        "high": [101.0, 103.0, 106.0, 110.0, 105.0, 107.0, 104.0, 106.0, 108.0, 107.0],
        "low": [99.0, 101.0, 104.0, 107.0, 103.0, 105.0, 102.0, 104.0, 106.0, 105.0],
        "close": [100.5, 102.5, 105.5, 108.5, 104.5, 106.5, 103.5, 105.5, 107.5, 106.5],
        "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900],
    }

    # Add a clear bullish FVG at index 5-7
    # Bar 5: high = 102
    # Bar 6: low = 105, high = 108  (low > prev high)
    # Bar 7: low = 110  (low > bar 6 high AND bar 6 low > bar 5 high)
    data["high"][5] = 102.0  # Bar 5 high
    data["low"][5] = 100.0  # Bar 5 low

    data["high"][6] = 108.0  # Bar 6 high
    data["low"][6] = 105.0  # Bar 6 low (> bar 5 high)

    data["high"][7] = 115.0  # Bar 7 high
    data["low"][7] = 110.0  # Bar 7 low (> bar 6 high)

    # This should create a bullish FVG at bar 7
    # Because: bar7.low (110) > bar6.high (108) AND bar6.low (105) > bar5.high (102)

    return pl.DataFrame(data)


def analyze_real_data_for_gaps(df: pl.DataFrame) -> None:
    """Analyze real data to understand why FVGs aren't being detected."""
    print("\n" + "=" * 80)
    print("ANALYZING DATA FOR POTENTIAL GAPS")
    print("=" * 80)

    # Add shifted columns for analysis
    analysis_df = df.with_columns(
        [
            pl.col("high").shift(1).alias("prev_high"),
            pl.col("low").shift(1).alias("prev_low"),
            pl.col("high").shift(2).alias("prev2_high"),
            pl.col("low").shift(2).alias("prev2_low"),
        ]
    )

    # Check bullish FVG conditions
    analysis_df = analysis_df.with_columns(
        [
            # First condition: current low > prev high
            (pl.col("low") > pl.col("prev_high")).alias("bullish_cond1"),
            # Second condition: prev low > prev2 high
            (pl.col("prev_low") > pl.col("prev2_high")).alias("bullish_cond2"),
            # Both conditions
            (
                (pl.col("low") > pl.col("prev_high"))
                & (pl.col("prev_low") > pl.col("prev2_high"))
            ).alias("bullish_fvg"),
        ]
    )

    # Check bearish FVG conditions
    analysis_df = analysis_df.with_columns(
        [
            # First condition: current high < prev low
            (pl.col("high") < pl.col("prev_low")).alias("bearish_cond1"),
            # Second condition: prev high < prev2 low
            (pl.col("prev_high") < pl.col("prev2_low")).alias("bearish_cond2"),
            # Both conditions
            (
                (pl.col("high") < pl.col("prev_low"))
                & (pl.col("prev_high") < pl.col("prev2_low"))
            ).alias("bearish_fvg"),
        ]
    )

    # Count how often each condition is met
    bullish_cond1_count = analysis_df.filter(pl.col("bullish_cond1")).height
    bullish_cond2_count = analysis_df.filter(pl.col("bullish_cond2")).height
    bullish_both_count = analysis_df.filter(pl.col("bullish_fvg")).height

    bearish_cond1_count = analysis_df.filter(pl.col("bearish_cond1")).height
    bearish_cond2_count = analysis_df.filter(pl.col("bearish_cond2")).height
    bearish_both_count = analysis_df.filter(pl.col("bearish_fvg")).height

    print(f"\n📊 BULLISH FVG CONDITIONS:")
    print(
        f"  Condition 1 (low > prev_high): {bullish_cond1_count}/{df.height} bars ({bullish_cond1_count / df.height * 100:.1f}%)"
    )
    print(
        f"  Condition 2 (prev_low > prev2_high): {bullish_cond2_count}/{df.height} bars ({bullish_cond2_count / df.height * 100:.1f}%)"
    )
    print(f"  Both conditions met: {bullish_both_count} bars")

    print(f"\n📊 BEARISH FVG CONDITIONS:")
    print(
        f"  Condition 1 (high < prev_low): {bearish_cond1_count}/{df.height} bars ({bearish_cond1_count / df.height * 100:.1f}%)"
    )
    print(
        f"  Condition 2 (prev_high < prev2_low): {bearish_cond2_count}/{df.height} bars ({bearish_cond2_count / df.height * 100:.1f}%)"
    )
    print(f"  Both conditions met: {bearish_both_count} bars")

    # Show examples where condition 1 is met but not condition 2
    if bullish_cond1_count > 0 and bullish_both_count == 0:
        print("\n⚠️ Examples where bullish condition 1 is met but not condition 2:")
        examples = analysis_df.filter(pl.col("bullish_cond1")).head(3)
        for row in examples.iter_rows(named=True):
            print(f"  Time: {row['timestamp']}")
            print(f"    Current: L={row['low']:.2f}, H={row['high']:.2f}")
            print(f"    Prev: L={row['prev_low']:.2f}, H={row['prev_high']:.2f}")
            print(f"    Prev2: L={row['prev2_low']:.2f}, H={row['prev2_high']:.2f}")
            print(
                f"    Cond1: {row['low']:.2f} > {row['prev_high']:.2f} = {row['bullish_cond1']}"
            )
            print(
                f"    Cond2: {row['prev_low']:.2f} > {row['prev2_high']:.2f} = {row['bullish_cond2']}"
            )

    # Look for simpler gap patterns (just current low > prev high or current high < prev low)
    simple_bullish_gaps = analysis_df.filter(pl.col("low") > pl.col("prev_high")).height
    simple_bearish_gaps = analysis_df.filter(pl.col("high") < pl.col("prev_low")).height

    print(f"\n💡 SIMPLER GAP PATTERNS:")
    print(f"  Simple bullish gaps (low > prev_high): {simple_bullish_gaps} bars")
    print(f"  Simple bearish gaps (high < prev_low): {simple_bearish_gaps} bars")

    if simple_bullish_gaps > 0:
        print("\n  Examples of simple bullish gaps:")
        examples = analysis_df.filter(pl.col("low") > pl.col("prev_high")).head(5)
        for row in examples.iter_rows(named=True):
            gap_size = row["low"] - row["prev_high"]
            print(
                f"    {row['timestamp']}: Gap of ${gap_size:.2f} (Low ${row['low']:.2f} > Prev High ${row['prev_high']:.2f})"
            )


async def main():
    """Main function to debug FVG indicator."""
    print("🔍 Fair Value Gap Indicator Debug")
    print("=" * 80)

    # Test with synthetic data first
    print("\n1️⃣ TESTING WITH SYNTHETIC DATA")
    print("-" * 40)

    synthetic_df = create_synthetic_fvg_data()
    print(f"Created synthetic data with {synthetic_df.height} bars")
    print("\nSynthetic data:")
    print(synthetic_df.select(["timestamp", "open", "high", "low", "close"]))

    # Apply FVG indicator to synthetic data
    synthetic_with_fvg = synthetic_df.pipe(FVG, min_gap_size=0.0)

    # Check for detected FVGs
    bullish_fvgs = synthetic_with_fvg.filter(pl.col("fvg_bullish"))
    bearish_fvgs = synthetic_with_fvg.filter(pl.col("fvg_bearish"))

    print(f"\n✅ Detected {bullish_fvgs.height} bullish FVGs in synthetic data")
    print(f"✅ Detected {bearish_fvgs.height} bearish FVGs in synthetic data")

    if bullish_fvgs.height > 0:
        print("\nBullish FVGs found:")
        for row in bullish_fvgs.iter_rows(named=True):
            print(f"  Time: {row['timestamp']}")
            print(f"  Gap Top: ${row.get('fvg_gap_top', 'N/A')}")
            print(f"  Gap Bottom: ${row.get('fvg_gap_bottom', 'N/A')}")
            print(f"  Gap Size: ${row.get('fvg_gap_size', 'N/A')}")

    # Now test with real data
    print("\n2️⃣ TESTING WITH REAL MARKET DATA")
    print("-" * 40)

    try:
        async with ProjectX.from_env() as client:
            await client.authenticate()
            print(f"✅ Connected to account: {client.account_info.name}")

            # Get historical data - try 1-minute bars for more samples
            print("\n📥 Loading 1-minute bar data...")
            bars_df = await client.get_bars(
                "MNQ",
                days=10,
                interval=1,  # 1-minute bars
                unit=2,  # 2 = minutes
            )

            if bars_df is None or bars_df.is_empty():
                print("❌ No data retrieved!")
                return

            print(f"✅ Loaded {bars_df.height} bars")

            # Analyze why FVGs aren't being detected
            analyze_real_data_for_gaps(bars_df)

            # Apply FVG indicator with very low threshold
            print("\n3️⃣ APPLYING FVG INDICATOR TO REAL DATA")
            print("-" * 40)

            fvg_df = bars_df.pipe(FVG, min_gap_size=0.0)

            # Check results
            bullish_count = fvg_df.filter(pl.col("fvg_bullish")).height
            bearish_count = fvg_df.filter(pl.col("fvg_bearish")).height

            print(f"\n📈 Bullish FVGs detected: {bullish_count}")
            print(f"📉 Bearish FVGs detected: {bearish_count}")

            if bullish_count == 0 and bearish_count == 0:
                print("\n⚠️ No FVGs detected! The conditions may be too strict.")
                print("The current FVG definition requires:")
                print("  - Three consecutive bars with very specific gap patterns")
                print(
                    "  - These patterns are extremely rare in normal market conditions"
                )
                print("\n💡 Suggestion: Consider using simpler gap detection logic")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
