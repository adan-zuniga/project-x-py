#!/usr/bin/env python
"""
Debug script for Order Block indicator to check output values.

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
from project_x_py.indicators import ORDERBLOCK


async def main():
    """Main function to debug Order Block indicator."""
    print("🔍 Order Block Indicator Debug")
    print("=" * 80)

    try:
        async with ProjectX.from_env() as client:
            await client.authenticate()
            print(f"✅ Connected to account: {client.account_info.name}")

            # Get a small sample of data
            print("\n📥 Loading sample data...")
            bars_df = await client.get_bars(
                "MNQ",
                days=1,
                interval=5,  # 5-minute bars for cleaner data
                unit=2,  # 2 = minutes
            )

            if bars_df is None or bars_df.is_empty():
                print("❌ No data retrieved!")
                return

            print(f"✅ Loaded {bars_df.height} bars")

            # Apply Order Block indicator
            print("\n" + "=" * 80)
            print("APPLYING ORDER BLOCK INDICATOR")
            print("=" * 80)

            ob_df = bars_df.pipe(ORDERBLOCK, lookback_periods=10)

            # Check the column types
            print("\n📊 Column Information:")
            for col in ob_df.columns:
                if col.startswith("ob_"):
                    dtype = ob_df[col].dtype
                    print(f"  {col}: {dtype}")

            # Show some actual values
            print("\n📊 Sample Data with Order Block columns:")
            display_cols = ["timestamp", "high", "low", "close", "volume"]
            ob_cols = [col for col in ob_df.columns if col.startswith("ob_")]
            display_cols.extend(ob_cols)

            # Show first few rows with order blocks
            ob_detected = ob_df.filter(pl.col("ob_bullish") | pl.col("ob_bearish"))
            if ob_detected.height > 0:
                print(f"\nFound {ob_detected.height} bars with order blocks")
                print("\nFirst 5 bars with order blocks:")
                sample = ob_detected.select(display_cols).head(5)
                print(sample)

                # Show detailed view of order block values
                print("\n📊 Detailed Order Block Values:")
                for idx, row in enumerate(ob_detected.head(10).iter_rows(named=True)):
                    print(f"\nBar {idx + 1}:")
                    print(f"  Time: {row['timestamp']}")
                    print(
                        f"  Price: H=${row['high']:.2f}, L=${row['low']:.2f}, C=${row['close']:.2f}"
                    )
                    print(
                        f"  ob_bullish: {row['ob_bullish']} (type: {type(row['ob_bullish'])})"
                    )
                    print(
                        f"  ob_bearish: {row['ob_bearish']} (type: {type(row['ob_bearish'])})"
                    )
                    print(f"  ob_top: {row.get('ob_top', 'N/A')}")
                    print(f"  ob_bottom: {row.get('ob_bottom', 'N/A')}")
                    print(f"  ob_volume: {row.get('ob_volume', 'N/A')}")
                    print(f"  ob_strength: {row.get('ob_strength', 'N/A')}")
            else:
                print("\nNo order blocks detected in the data")

            # Check unique values
            print("\n📊 Unique values in ob_bullish column:")
            unique_bullish = ob_df["ob_bullish"].unique()
            print(f"  Values: {unique_bullish.to_list()}")

            print("\n📊 Unique values in ob_bearish column:")
            unique_bearish = ob_df["ob_bearish"].unique()
            print(f"  Values: {unique_bearish.to_list()}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
