#!/usr/bin/env python
"""
Trading Suite Demo - Simplified SDK Initialization

This example demonstrates the new v3.0.0 TradingSuite class that provides
a single-line initialization for the entire trading environment.

Key improvements over v2:
- Single entry point for all components
- Automatic dependency management
- Built-in connection handling
- Feature flags for optional components
"""

import asyncio
import logging

from project_x_py import TradingSuite

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    """Demonstrate simplified TradingSuite initialization."""

    # Method 1: Simple one-liner with defaults
    print("=== Creating TradingSuite with defaults ===")
    suite = await TradingSuite.create("MNQ")

    # Everything is connected and ready!
    print(f"Connected: {suite.is_connected}")
    if suite.instrument is None:
        raise Exception("Instrument is None")
    print(f"Instrument: {suite.instrument.symbolId}")  # Access instrument info

    # Access components - new multi-instrument way (recommended)
    print("\n=== Component Access (Recommended) ===")
    mnq_context = suite["MNQ"]
    print(f"Data Manager: {mnq_context.data}")
    print(f"Order Manager: {mnq_context.orders}")
    print(f"Position Manager: {mnq_context.positions}")

    # Get some data
    print("\n=== Market Data ===")
    current_price = await mnq_context.data.get_current_price()
    print(f"Current price: {current_price}")

    # Get stats
    print("\n=== Suite Statistics ===")
    stats = await suite.get_stats()
    print(f"Stats: {stats}")

    # Clean disconnect
    await suite.disconnect()

    # Method 2: With custom configuration
    print("\n\n=== Creating TradingSuite with custom config ===")
    suite2 = await TradingSuite.create(
        "MGC",
        timeframes=["1min", "5min", "15min"],
        features=["orderbook"],
        initial_days=10,
    )

    print(f"Connected: {suite2.is_connected}")
    print(f"Has orderbook: {suite2['MGC'].orderbook is not None}")

    # Use as context manager for automatic cleanup
    print("\n\n=== Using as context manager ===")
    async with await TradingSuite.create("ES", timeframes=["1min"]) as suite3:
        print(f"Connected: {suite3.is_connected}")
        # Automatic cleanup on exit

    print("\n✅ TradingSuite demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
