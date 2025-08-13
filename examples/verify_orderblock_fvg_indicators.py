#!/usr/bin/env python
"""
Verification script for Order Block and Fair Value Gap indicators.

This script loads historical market data and applies both the Order Block
and FVG indicators to verify they are detecting patterns correctly.
It displays the full dataframes to show all detected patterns.

Author: ProjectX SDK
Date: 2025-01-12
"""

import asyncio
import os
import sys
from datetime import datetime

import polars as pl

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_x_py import ProjectX
from project_x_py.indicators import FVG, ORDERBLOCK


def display_dataframe_info(df: pl.DataFrame, title: str) -> None:
    """Display comprehensive information about a dataframe."""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}")
    print(f"Shape: {df.shape} (rows: {df.height}, columns: {df.width})")
    print(f"Columns: {df.columns}")
    print(f"Data types: {df.dtypes}")
    print()


def display_order_blocks(df: pl.DataFrame) -> None:
    """Display detected Order Blocks with details."""
    # Filter for rows where order blocks are detected
    ob_columns = [col for col in df.columns if col.startswith("ob_")]

    if not ob_columns:
        print("No Order Block columns found in dataframe!")
        return

    # Check for bullish order blocks
    if "ob_bullish" in df.columns:
        bullish_obs = df.filter(pl.col("ob_bullish") == True)
        if bullish_obs.height > 0:
            print(f"\n📈 BULLISH ORDER BLOCKS DETECTED: {bullish_obs.height}")
            print("-" * 60)
            # Limit display to first 10 for readability
            for row in bullish_obs.head(10).iter_rows(named=True):
                print(f"  Time: {row['timestamp']}")
                if "ob_top" in row and "ob_bottom" in row:
                    print(
                        f"  Order Block Zone: ${row['ob_bottom']:.2f} - ${row['ob_top']:.2f}"
                    )
                print(f"  Bar Range: ${row['low']:.2f} - ${row['high']:.2f}")
                print(f"  Volume: {row['volume']:,}")
                if "ob_strength" in row:
                    print(f"  Strength: {row['ob_strength']:.4f}")
                print()
            if bullish_obs.height > 10:
                print(f"  ... and {bullish_obs.height - 10} more")

    # Check for bearish order blocks
    if "ob_bearish" in df.columns:
        bearish_obs = df.filter(pl.col("ob_bearish") == True)
        if bearish_obs.height > 0:
            print(f"\n📉 BEARISH ORDER BLOCKS DETECTED: {bearish_obs.height}")
            print("-" * 60)
            # Limit display to first 10 for readability
            for row in bearish_obs.head(10).iter_rows(named=True):
                print(f"  Time: {row['timestamp']}")
                if "ob_top" in row and "ob_bottom" in row:
                    print(
                        f"  Order Block Zone: ${row['ob_bottom']:.2f} - ${row['ob_top']:.2f}"
                    )
                print(f"  Bar Range: ${row['low']:.2f} - ${row['high']:.2f}")
                print(f"  Volume: {row['volume']:,}")
                if "ob_strength" in row:
                    print(f"  Strength: {row['ob_strength']:.4f}")
                print()
            if bearish_obs.height > 10:
                print(f"  ... and {bearish_obs.height - 10} more")


def display_fair_value_gaps(df: pl.DataFrame) -> None:
    """Display detected Fair Value Gaps with details."""
    # Filter for rows where FVGs are detected
    fvg_columns = [col for col in df.columns if col.startswith("fvg_")]

    if not fvg_columns:
        print("No FVG columns found in dataframe!")
        return

    # Check for bullish FVGs
    if "fvg_bullish_start" in df.columns:
        bullish_fvgs = df.filter(pl.col("fvg_bullish_start").is_not_null())
        if bullish_fvgs.height > 0:
            print(f"\n⬆️ BULLISH FAIR VALUE GAPS DETECTED: {bullish_fvgs.height}")
            print("-" * 60)
            for row in bullish_fvgs.iter_rows(named=True):
                print(f"  Time: {row['timestamp']}")
                print(f"  Gap Start: ${row['fvg_bullish_start']:.2f}")
                print(f"  Gap End: ${row['fvg_bullish_end']:.2f}")
                gap_size = row["fvg_bullish_end"] - row["fvg_bullish_start"]
                print(f"  Gap Size: ${gap_size:.2f}")
                print(f"  Current Price: ${row['close']:.2f}")
                print()

    # Check for bearish FVGs
    if "fvg_bearish_start" in df.columns:
        bearish_fvgs = df.filter(pl.col("fvg_bearish_start").is_not_null())
        if bearish_fvgs.height > 0:
            print(f"\n⬇️ BEARISH FAIR VALUE GAPS DETECTED: {bearish_fvgs.height}")
            print("-" * 60)
            for row in bearish_fvgs.iter_rows(named=True):
                print(f"  Time: {row['timestamp']}")
                print(f"  Gap Start: ${row['fvg_bearish_start']:.2f}")
                print(f"  Gap End: ${row['fvg_bearish_end']:.2f}")
                gap_size = row["fvg_bearish_start"] - row["fvg_bearish_end"]
                print(f"  Gap Size: ${gap_size:.2f}")
                print(f"  Current Price: ${row['close']:.2f}")
                print()


def display_sample_data(df: pl.DataFrame, n: int = 10) -> None:
    """Display sample rows from the dataframe."""
    print(f"\n📊 SAMPLE DATA (last {n} rows):")
    print("-" * 60)

    # Select relevant columns for display
    display_cols = ["timestamp", "open", "high", "low", "close", "volume"]

    # Add indicator columns if they exist
    for col in df.columns:
        if col.startswith("ob_") or col.startswith("fvg_"):
            display_cols.append(col)

    # Filter to existing columns
    display_cols = [col for col in display_cols if col in df.columns]

    # Show the data
    sample = df.select(display_cols).tail(n)
    print(sample)


async def main():
    """Main function to verify Order Block and FVG indicators."""
    print("🔍 Order Block and Fair Value Gap Indicator Verification")
    print("=" * 80)

    try:
        # Create ProjectX client
        async with ProjectX.from_env() as client:
            await client.authenticate()
            print(f"✅ Connected to account: {client.account_info.name}")

            # Get historical data with enough bars for pattern detection
            print("\n📥 Loading historical data...")
            instrument = "MNQ"  # Using E-mini NASDAQ futures

            # Get 10 days of 1-minute bars for more samples
            bars_df = await client.get_bars(
                instrument,
                days=25,
                interval=15,  # 1-minute bars
                unit=2,  # 2 = minutes
            )

            if bars_df is None or bars_df.is_empty():
                print("❌ No data retrieved!")
                return

            print(f"✅ Loaded {bars_df.height} bars of {instrument} data")

            # Display basic dataframe info
            display_dataframe_info(bars_df, "Original Data")

            # Apply Order Block indicator
            print("\n" + "=" * 80)
            print("APPLYING ORDER BLOCK INDICATOR")
            print("=" * 80)

            ob_df = bars_df.pipe(ORDERBLOCK, lookback_periods=20)

            # Display Order Block results
            display_dataframe_info(ob_df, "Data with Order Blocks")
            display_order_blocks(ob_df)

            # Apply Fair Value Gap indicator
            print("\n" + "=" * 80)
            print("APPLYING FAIR VALUE GAP INDICATOR")
            print("=" * 80)

            fvg_df = bars_df.pipe(FVG)

            # Display FVG results
            display_dataframe_info(fvg_df, "Data with Fair Value Gaps")
            display_fair_value_gaps(fvg_df)

            # Apply both indicators together
            print("\n" + "=" * 80)
            print("APPLYING BOTH INDICATORS")
            print("=" * 80)

            combined_df = bars_df.pipe(ORDERBLOCK, lookback_periods=20).pipe(FVG)

            # Display combined results
            display_dataframe_info(combined_df, "Data with Both Indicators")

            # Show sample of the full dataframe
            display_sample_data(combined_df, n=20)

            # Summary statistics
            print("\n" + "=" * 80)
            print("SUMMARY STATISTICS")
            print("=" * 80)

            if "ob_bullish" in combined_df.columns:
                bullish_ob_count = combined_df.filter(
                    pl.col("ob_bullish").is_not_null()
                ).height
                print(f"📈 Total Bullish Order Blocks: {bullish_ob_count}")

            if "ob_bearish" in combined_df.columns:
                bearish_ob_count = combined_df.filter(
                    pl.col("ob_bearish").is_not_null()
                ).height
                print(f"📉 Total Bearish Order Blocks: {bearish_ob_count}")

            if "fvg_bullish_start" in combined_df.columns:
                bullish_fvg_count = combined_df.filter(
                    pl.col("fvg_bullish_start").is_not_null()
                ).height
                print(f"⬆️  Total Bullish FVGs: {bullish_fvg_count}")

            if "fvg_bearish_start" in combined_df.columns:
                bearish_fvg_count = combined_df.filter(
                    pl.col("fvg_bearish_start").is_not_null()
                ).height
                print(f"⬇️  Total Bearish FVGs: {bearish_fvg_count}")

            # Export to CSV for further analysis if needed
            output_file = f"orderblock_fvg_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            combined_df.write_csv(output_file)
            print(f"\n💾 Full data exported to: {output_file}")

            print("\n✅ Verification complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
