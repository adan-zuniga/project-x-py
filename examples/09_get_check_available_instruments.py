#!/usr/bin/env python3
"""
Interactive Instrument Search Demo for ProjectX

This demo showcases the instrument search functionality, including:
- Searching for all contracts matching a symbol
- Getting the best matching contract using smart selection
- Understanding the contract naming patterns
"""

import sys

from project_x_py import ProjectX
from project_x_py.exceptions import ProjectXError


def display_instrument(instrument, prefix=""):
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


def search_and_display(client, symbol):
    """Search for instruments and display results"""
    print(f"\n{'=' * 60}")
    print(f"Searching for: '{symbol}'")
    print(f"{'=' * 60}")

    try:
        # Search for all matching instruments
        print(f"\n1. All contracts matching '{symbol}':")
        print("-" * 50)

        instruments = client.search_instruments(symbol)

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

        best_instrument = client.get_instrument(symbol)
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


def main():
    print("╔═══════════════════════════════════════════════════════╗")
    print("║     ProjectX Instrument Search Interactive Demo       ║")
    print("╚═══════════════════════════════════════════════════════╝")

    try:
        print("\nConnecting to ProjectX...")
        client = ProjectX.from_env()
        print("✓ Connected successfully!")

    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print("\nMake sure you have set the following environment variables:")
        print("  - PROJECT_X_API_KEY")
        print("  - PROJECT_X_USERNAME")
        sys.exit(1)

    show_common_symbols()

    print("\nHow the search works:")
    print("- search_instruments(): Returns ALL matching contracts")
    print("- get_instrument(): Returns the BEST match (active contract preferred)")
    print(
        "- Contract names include month/year codes (e.g., NQU5 = NQ + September 2025)"
    )

    while True:
        print("\n" + "─" * 60)
        symbol = input("Enter a symbol to search (or 'quit' to exit): ").strip()

        if symbol.lower() in ["quit", "exit", "q"]:
            print("\nGoodbye!")
            break

        if symbol.lower() == "help":
            show_common_symbols()
            continue

        if not symbol:
            print("Please enter a valid symbol.")
            continue

        search_and_display(client, symbol.upper())


if __name__ == "__main__":
    main()
