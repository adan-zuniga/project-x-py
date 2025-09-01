"""
Basic Session Filtering Example

Demonstrates how to filter market data by trading session (RTH/ETH).
This is the simplest way to work with session-specific data.
"""

import asyncio
from datetime import datetime, timezone

import polars as pl

from project_x_py import TradingSuite
from project_x_py.sessions import SessionConfig, SessionFilterMixin, SessionType


async def basic_session_filtering():
    """Basic example of filtering data by trading session."""

    print("=" * 60)
    print("BASIC SESSION FILTERING EXAMPLE")
    print("=" * 60)

    # Create suite with default configuration
    suite = await TradingSuite.create(
        "MNQ", timeframes=["1min", "5min"], initial_days=5
    )

    try:
        # Get the data manager
        mnq_context = suite["MNQ"]

        # Method 1: Using data manager's built-in session methods
        print("\n1. Using Data Manager Session Methods:")
        print("-" * 40)

        # Get RTH-only data
        rth_data = await mnq_context.data.get_session_data("5min", SessionType.RTH)
        if rth_data is not None and not rth_data.is_empty():
            print(f"RTH bars (9:30 AM - 4:00 PM ET): {len(rth_data):,}")
            print(f"  First bar: {rth_data['timestamp'][0]}")
            print(f"  Last bar:  {rth_data['timestamp'][-1]}")

        # Get ETH-only data
        eth_data = await mnq_context.data.get_session_data("5min", SessionType.ETH)
        if eth_data is not None and not eth_data.is_empty():
            print(f"ETH bars (overnight): {len(eth_data):,}")
            print(f"  First bar: {eth_data['timestamp'][0]}")
            print(f"  Last bar:  {eth_data['timestamp'][-1]}")

        # Method 2: Using SessionFilterMixin for manual filtering
        print("\n2. Using SessionFilterMixin:")
        print("-" * 40)

        # Get all data
        all_data = await mnq_context.data.get_data("5min")

        if all_data is not None and not all_data.is_empty():
            # Create filter
            session_filter = SessionFilterMixin()

            # Filter to RTH
            rth_filtered = await session_filter.filter_by_session(
                all_data, SessionType.RTH, "MNQ"
            )
            print(f"RTH filtered bars: {len(rth_filtered):,}")

            # Filter to ETH
            eth_filtered = await session_filter.filter_by_session(
                all_data, SessionType.ETH, "MNQ"
            )
            print(f"ETH filtered bars: {len(eth_filtered):,}")

            # Show ALL (unfiltered data)
            print(f"ALL (unfiltered) bars: {len(all_data):,}")

        # Method 3: Check current market status
        print("\n3. Current Market Status:")
        print("-" * 40)

        config = SessionConfig(session_type=SessionType.RTH)
        current_time = datetime.now(timezone.utc)

        # Check if market is open
        is_open = config.is_market_open(current_time, "MNQ")
        print(f"RTH Market is: {'OPEN' if is_open else 'CLOSED'}")

        # Get current session
        current_session = config.get_current_session(current_time, "MNQ")
        print(f"Current session: {current_session}")

        # Get session times for the product
        session_times = config.get_session_times("MNQ")
        print("\nMNQ Session Times (ET):")
        print(f"  RTH: {session_times.rth_start} - {session_times.rth_end}")
        print(f"  ETH: {session_times.eth_start} - {session_times.eth_end}")

    finally:
        await suite.disconnect()
        print("\n✅ Session filtering example completed")


if __name__ == "__main__":
    asyncio.run(basic_session_filtering())
