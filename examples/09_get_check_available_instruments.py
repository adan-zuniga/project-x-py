#!/usr/bin/env python3
"""
Interactive Instrument Search Demo for ProjectX

This version demonstrates:
- Using ProjectX client with async context manager
- Async instrument search with await client.search_instruments()
- Async best match selection with await client.get_instrument()
- Non-blocking user input handling
- Background performance stats monitoring
- Proper authentication flow

Key differences from sync version:
- Uses ProjectX instead of ProjectX
- All API calls use await (search_instruments, get_instrument)
- Context manager (with)
- Can run background tasks while accepting user input
"""

import asyncio
import sys
from contextlib import suppress

from project_x_py import ProjectX
from project_x_py.client.base import ProjectXBase
from project_x_py.exceptions import ProjectXError
from project_x_py.models import Instrument


def display_instrument(instrument: Instrument, prefix: str = "") -> None:
    """Display instrument details in a formatted way"""
    print(f"{prefix}┌─ Contract Details ─────────────────────────────")
    print(f"{prefix}│ ID:           {instrument.id}")
    print(f"{prefix}│ Name:         {instrument.name}")
    print(f"{prefix}│ Symbol ID:    {instrument.symbolId}")
    print(f"{prefix}│ Description:  {instrument.description}")
    print(f"{prefix}│ Active:       {'✓ Yes' if instrument.activeContract else '✗ No'}")
    print(f"{prefix}│ Tick Size:    {instrument.tickSize}")
    print(f"{prefix}│ Tick Value:   ${instrument.tickValue}")
    print(f"{prefix}└" + "─" * 47)


async def search_and_display(client: ProjectXBase, symbol: str) -> None:
    """Search for instruments and display results asynchronously"""
    print(f"\n{'=' * 60}")
    print(f"Searching for: '{symbol}'")
    print(f"{'=' * 60}")

    try:
        # Search for all matching instruments
        print(f"\n1. All contracts matching '{symbol}':")
        print("-" * 50)

        instruments = await client.search_instruments(symbol)

        if not instruments:
            print(f"   No instruments found for '{symbol}'")
            return

        print(f"   Found {len(instruments)} contract(s):\n")

        for i, instrument in enumerate(instruments, 1):
            active_marker = "★" if instrument.activeContract else " "
            print(
                f"   {active_marker} [{i}] {instrument.name} - {instrument.description}"
            )

        # Get the best matching instrument
        print(f"\n2. Best match using get_instrument('{symbol}'):")
        print("-" * 50)

        best_instrument = await client.get_instrument(symbol)
        if best_instrument:
            print(f"   Selected: {best_instrument.name}")
            display_instrument(best_instrument, "   ")
        else:
            print(f"   No best match found for '{symbol}'")

    except ProjectXError as e:
        print(f"   Error: {e}")
    except Exception as e:
        print(f"   Unexpected error: {e}")


def show_common_symbols():
    """Display common symbol examples"""
    print("\nCommon symbols to try:")
    print("┌─────────┬──────────────────────────────────────────┐")
    print("│ Symbol  │ Description                              │")
    print("├─────────┼──────────────────────────────────────────┤")
    print("│ ES      │ E-mini S&P 500                           │")
    print("│ NQ      │ E-mini NASDAQ-100                        │")
    print("│ YM      │ E-mini Dow Jones                         │")
    print("│ RTY     │ E-mini Russell 2000                      │")
    print("│ CL      │ Crude Oil                                │")
    print("│ GC      │ Gold                                     │")
    print("│ SI      │ Silver                                   │")
    print("│ ZB      │ 30-Year Treasury Bond                    │")
    print("│ ZN      │ 10-Year Treasury Note                    │")
    print("│ ZC      │ Corn                                     │")
    print("│ ZS      │ Soybeans                                 │")
    print("│ ZW      │ Wheat                                    │")
    print("│ 6E      │ Euro FX                                  │")
    print("│ 6J      │ Japanese Yen                             │")
    print("│ MES     │ Micro E-mini S&P 500                     │")
    print("│ MNQ     │ Micro E-mini NASDAQ-100                  │")
    print("│ MGC     │ Micro Gold                               │")
    print("└─────────┴──────────────────────────────────────────┘")


async def get_user_input(prompt: str) -> str:
    """Get user input"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)


async def run_interactive_search(client: ProjectXBase) -> None:
    """Run the interactive search loop."""
    show_common_symbols()

    print("\nHow the search works:")
    print("- search_instruments(): Returns ALL matching contracts")
    print("- get_instrument(): Returns the BEST match (active contract preferred)")
    print(
        "- Contract names include month/year codes (e.g., NQU5 = NQ + September 2025)"
    )

    while True:
        print("\n" + "─" * 60)
        symbol = await get_user_input("Enter a symbol to search (or 'quit' to exit): ")
        symbol = symbol.strip()

        if symbol.lower() in ["quit", "exit", "q"]:
            print("\nGoodbye!")
            break

        if symbol.lower() == "help":
            show_common_symbols()
            continue

        if not symbol:
            print("Please enter a valid symbol.")
            continue

        await search_and_display(client, symbol.upper())


async def main() -> None:
    """Main entry point."""
    print("╔═══════════════════════════════════════════════════════╗")
    print("║   Async ProjectX Instrument Search Interactive Demo   ║")
    print("╚═══════════════════════════════════════════════════════╝")

    try:
        print("\nConnecting to ProjectX...")
        async with ProjectX.from_env() as client:
            await client.authenticate()
            if client is None:
                print("❌ No client found")
                return
            if client.account_info is None:
                print("❌ No account info found")
                return
            print("✓ Connected successfully!")
            print(f"✓ Using account: {client.account_info.name}")

            # Show client performance stats periodically
            async def show_stats() -> None:
                while True:
                    await asyncio.sleep(60)  # Every minute
                    stats = await client.get_health_status()
                    # Using defined PerformanceStatsResponse keys
                    if stats["api_calls"] > 0:
                        print(
                            f"\n[Stats] API calls: {stats['api_calls']}, "
                            f"Cache hits: {stats['cache_hits']} "
                            f"({(stats['cache_hits'] / max(stats['api_calls'], 1)):.1%} hit rate)"
                        )

            # Run stats display in background
            stats_task = asyncio.create_task(show_stats())

            try:
                await run_interactive_search(client)
            finally:
                stats_task.cancel()
                with suppress(asyncio.CancelledError):
                    await stats_task

    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print("\nMake sure you have set the following environment variables:")
        print("  - PROJECT_X_API_KEY")
        print("  - PROJECT_X_USERNAME")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
