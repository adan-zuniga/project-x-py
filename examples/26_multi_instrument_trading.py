#!/usr/bin/env python3
"""
Multi-Instrument TradingSuite Example

This example demonstrates the new multi-instrument capabilities of TradingSuite v3.5.0+.
The TradingSuite now acts as a dictionary-like container, allowing you to manage
multiple instruments simultaneously with clean, intuitive access patterns.

Key Features Demonstrated:
- Creating a suite with multiple instruments in parallel
- Dictionary-like access to instrument contexts
- Backward compatibility with deprecation warnings
- Container protocol methods (iteration, keys, values, items)
- Multi-instrument data access and management

Requirements:
- Set PROJECT_X_API_KEY and PROJECT_X_USERNAME environment variables
"""

import asyncio
import logging
from typing import Any

from project_x_py import TradingSuite

# Configure logging to see the parallel creation and operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_multi_instrument_creation():
    """Demonstrate creating a TradingSuite with multiple instruments."""
    print("=" * 60)
    print("Multi-Instrument TradingSuite Creation")
    print("=" * 60)

    # Create a suite with multiple instruments - they are created in parallel
    instruments = ["MNQ", "MES", "MCL"]  # NASDAQ, S&P, Crude Oil
    print(f"Creating TradingSuite for instruments: {instruments}")

    suite = await TradingSuite.create(
        instruments=instruments,
        timeframes=["1min", "5min"],
        initial_days=1,  # Load minimal historical data for demo
    )

    print(f"✅ Successfully created suite with {len(suite)} instruments")
    return suite


async def demonstrate_dictionary_access(suite: TradingSuite):
    """Demonstrate dictionary-like access to instrument contexts."""
    print("\n" + "=" * 60)
    print("Dictionary-like Access Patterns")
    print("=" * 60)

    # Access specific instruments
    print("📊 Accessing individual instruments:")
    mnq_context = suite["MNQ"]
    print(f"  MNQ context: {mnq_context.symbol}")
    print(f"  MNQ instrument ID: {mnq_context.instrument_info.id}")

    mes_context = suite["MES"]
    print(f"  MES context: {mes_context.symbol}")
    print(f"  MES instrument ID: {mes_context.instrument_info.id}")

    # Check if instruments exist
    print("\n🔍 Checking instrument availability:")
    print(f"  'MNQ' in suite: {'MNQ' in suite}")
    print(f"  'ES' in suite: {'ES' in suite}")

    # Get data from specific instruments
    print("\n📈 Getting data from specific instruments:")
    try:
        mnq_price = await mnq_context.data.get_current_price()
        print(f"  MNQ current price: ${mnq_price}")
    except Exception as e:
        print(f"  MNQ price unavailable: {e}")

    try:
        mes_price = await mes_context.data.get_current_price()
        print(f"  MES current price: ${mes_price}")
    except Exception as e:
        print(f"  MES price unavailable: {e}")


async def demonstrate_container_protocol(suite: TradingSuite):
    """Demonstrate container protocol methods."""
    print("\n" + "=" * 60)
    print("Container Protocol Methods")
    print("=" * 60)

    # Length and iteration
    print(f"📊 Suite contains {len(suite)} instruments")

    # Iterate over symbols
    print("\n🔄 Iterating over symbols:")
    for symbol in suite:
        print(f"  - {symbol}")

    # Keys, values, items
    print(f"\n🗝️  Available symbols: {list(suite.keys())}")

    print("\n📋 Instrument details:")
    for symbol, context in suite.items():
        print(f"  {symbol}: {context.instrument_info.id}")


async def demonstrate_backward_compatibility(suite: TradingSuite):
    """Demonstrate backward compatibility with single-instrument access."""
    print("\n" + "=" * 60)
    print("Backward Compatibility (Single Instrument)")
    print("=" * 60)

    # Create a single instrument suite to test backward compatibility
    print("🔄 Creating single-instrument suite for backward compatibility test...")
    single_suite = await TradingSuite.create("MNQ", timeframes=["5min"])

    print(f"✅ Single suite created with {len(single_suite)} instrument")

    # Demonstrate new API
    print("\n✨ New API (recommended):")
    mnq_context = single_suite["MNQ"]
    print(f"  suite['MNQ'].symbol: {mnq_context.symbol}")

    # Demonstrate old API with deprecation warnings
    print("\n⚠️  Old API (deprecated, shows warnings):")
    try:
        # This will show deprecation warnings
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            old_data = single_suite.data  # This triggers deprecation warning
            print("  suite.data access works but shows warning")
            if w:
                print(f"  Warning: {w[0].message}")
    except Exception as e:
        print(f"  Error accessing old API: {e}")

    await single_suite.disconnect()


async def demonstrate_multi_instrument_operations(suite: TradingSuite):
    """Demonstrate operations across multiple instruments."""
    print("\n" + "=" * 60)
    print("Multi-Instrument Operations")
    print("=" * 60)

    # Get data from all instruments
    print("📊 Getting 5min data from all instruments:")
    for symbol in suite:
        try:
            context = suite[symbol]
            bars = await context.data.get_data("5min", bars=5)
            if bars is not None:
                print(f"  {symbol}: {len(bars)} bars available")
            else:
                print(f"  {symbol}: No data available")
        except Exception as e:
            print(f"  {symbol}: Error getting data - {e}")

    # Get position information (if any)
    print("\n💼 Checking positions across instruments:")
    for symbol in suite:
        try:
            context = suite[symbol]
            positions = await context.positions.get_all_positions()
            print(f"  {symbol}: {len(positions)} positions")
        except Exception as e:
            print(f"  {symbol}: Error getting positions - {e}")


async def main():
    """Main demonstration function."""
    print("🚀 Multi-Instrument TradingSuite Demo")
    print("This example demonstrates the new multi-instrument capabilities\n")

    try:
        # Create multi-instrument suite
        suite = await demonstrate_multi_instrument_creation()

        # Demonstrate various access patterns
        await demonstrate_dictionary_access(suite)
        await demonstrate_container_protocol(suite)
        await demonstrate_multi_instrument_operations(suite)
        await demonstrate_backward_compatibility(suite)

        print("\n" + "=" * 60)
        print("✅ Demo completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.exception("Demo error details:")

    finally:
        # Clean up
        if 'suite' in locals():
            print("\n🧹 Cleaning up...")
            await suite.disconnect()
            print("✅ Cleanup complete")


if __name__ == "__main__":
    """
    Run the multi-instrument demo.

    Make sure to set your environment variables:
    export PROJECT_X_API_KEY="your_api_key"  # pragma: allowlist secret
    export PROJECT_X_USERNAME="your_username"
    """
    asyncio.run(main())
