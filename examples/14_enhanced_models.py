#!/usr/bin/env python3
"""
Example: Enhanced Models with Strategy-Friendly Properties

This example demonstrates the new properties added to Order and Position models
in v3.0.0 that make strategy development much cleaner and more intuitive.

Key improvements:
- Position: is_long, is_short, direction, symbol, signed_size, unrealized_pnl()
- Order: is_open, is_filled, is_buy, is_sell, side_str, type_str, status_str, filled_percent

Author: SDK v3.0.2 Examples
"""

import asyncio
from datetime import datetime

from project_x_py import TradingSuite


async def demonstrate_position_properties():
    """Show the new Position model properties."""

    async with await TradingSuite.create("MNQ") as suite:
        print("=== Enhanced Position Properties ===\n")

        # Get positions
        positions = await suite["MNQ"].positions.get_all_positions()

        if not positions:
            print("No open positions. Creating a demo position for illustration...")
            # For demo purposes, show what properties would look like
            from project_x_py.models import Position

            demo_position = Position(
                id=12345,
                accountId=1001,
                contractId="CON.F.US.MNQ.H25",
                creationTimestamp=datetime.now().isoformat(),
                type=1,  # LONG
                size=2,
                averagePrice=16500.0,
            )
            positions = [demo_position]

        for pos in positions:
            print(f"Position ID: {pos.id}")

            # OLD WAY (verbose)
            print("\n❌ OLD WAY (verbose):")
            print(f"  Direction: {'LONG' if pos.type == 1 else 'SHORT'}")
            print(
                f"  Symbol: {pos.contractId.split('.')[3] if '.' in pos.contractId else pos.contractId}"
            )
            print(f"  Size: {-pos.size if pos.type == 2 else pos.size}")

            # NEW WAY (clean properties)
            print("\n✅ NEW WAY (clean properties):")
            print(f"  Direction: {pos.direction}")
            print(f"  Symbol: {pos.symbol}")
            print(f"  Signed Size: {pos.signed_size}")
            print(f"  Total Cost: ${pos.total_cost:,.2f}")

            # Boolean checks
            print("\n  Position Checks:")
            print(f"    Is Long? {pos.is_long}")
            print(f"    Is Short? {pos.is_short}")

            # P&L calculation
            current_price = await suite["MNQ"].data.get_latest_price()
            if current_price:
                pnl = pos.unrealized_pnl(
                    current_price, tick_value=5.0
                )  # MNQ tick value
                print(f"\n  Unrealized P&L: ${pnl:,.2f}")

                # Strategy logic is much cleaner
                if pos.is_long and pnl > 100:
                    print("  💰 Long position is profitable!")
                elif pos.is_short and pnl > 100:
                    print("  💰 Short position is profitable!")

            print("-" * 50)


async def demonstrate_order_properties():
    """Show the new Order model properties."""

    async with await TradingSuite.create("MNQ") as suite:
        print("\n\n=== Enhanced Order Properties ===\n")

        # Search for open orders
        orders = await suite["MNQ"].orders.search_open_orders()

        if not orders:
            print("No open orders. Creating demo orders for illustration...")
            from project_x_py.models import Order

            # Create demo orders
            orders = [
                Order(
                    id=98765,
                    accountId=1001,
                    contractId="CON.F.US.MNQ.H25",
                    creationTimestamp=datetime.now().isoformat(),
                    updateTimestamp=None,
                    status=1,  # OPEN
                    type=1,  # LIMIT
                    side=0,  # BUY
                    size=5,
                    fillVolume=2,
                    limitPrice=16450.0,
                ),
                Order(
                    id=98766,
                    accountId=1001,
                    contractId="CON.F.US.MNQ.H25",
                    creationTimestamp=datetime.now().isoformat(),
                    updateTimestamp=None,
                    status=2,  # FILLED
                    type=4,  # STOP
                    side=1,  # SELL
                    size=3,
                    fillVolume=3,
                    stopPrice=16400.0,
                ),
            ]

        for order in orders:
            print(f"Order ID: {order.id}")

            # OLD WAY (verbose with magic numbers)
            print("\n❌ OLD WAY (verbose):")
            print(f"  Side: {'BUY' if order.side == 0 else 'SELL'}")
            print(
                f"  Type: {['UNKNOWN', 'LIMIT', 'MARKET', 'STOP_LIMIT', 'STOP'][order.type] if order.type < 5 else 'OTHER'}"
            )
            print(
                f"  Status: {['NONE', 'OPEN', 'FILLED', 'CANCELLED'][order.status] if order.status < 4 else 'OTHER'}"
            )
            print(f"  Working?: {order.status == 1 or order.status == 6}")

            # NEW WAY (clean properties)
            print("\n✅ NEW WAY (clean properties):")
            print(f"  Side: {order.side_str}")
            print(f"  Type: {order.type_str}")
            print(f"  Status: {order.status_str}")
            print(f"  Symbol: {order.symbol}")

            # Boolean checks make logic cleaner
            print("\n  Order State:")
            print(f"    Is Open? {order.is_open}")
            print(f"    Is Filled? {order.is_filled}")
            print(f"    Is Working? {order.is_working}")
            print(f"    Is Terminal? {order.is_terminal}")

            # Fill information
            if order.fillVolume:
                print("\n  Fill Progress:")
                print(
                    f"    Filled: {order.fillVolume}/{order.size} ({order.filled_percent:.1f}%)"
                )
                print(f"    Remaining: {order.remaining_size}")

            # Clean strategy logic
            if order.is_working and order.is_buy:
                print("\n  📊 Active buy order waiting for fill")
            elif order.is_filled:
                print("\n  ✅ Order completely filled")

            print("-" * 50)


async def demonstrate_strategy_usage():
    """Show how enhanced models improve strategy code."""

    async with await TradingSuite.create("MNQ") as suite:
        print("\n\n=== Strategy Code Improvements ===\n")

        # Position management is cleaner
        positions = await suite["MNQ"].positions.get_all_positions()

        print("BEFORE (verbose):")
        print("```python")
        print("for pos in positions:")
        print("    if pos.type == 1:  # Magic number!")
        print("        direction = 'LONG'")
        print("        signed_size = pos.size")
        print("    else:")
        print("        direction = 'SHORT'")
        print("        signed_size = -pos.size")
        print("```")

        print("\nAFTER (clean):")
        print("```python")
        print("for pos in positions:")
        print("    print(f'{pos.direction} {pos.signed_size} {pos.symbol}')")
        print("    if pos.is_long and pos.unrealized_pnl(price) > 100:")
        print("        # Take profit logic")
        print("```")

        # Order filtering is simpler
        print("\n\nOrder Filtering:")
        print("\nBEFORE:")
        print("```python")
        print("working_buys = [o for o in orders if o.status == 1 and o.side == 0]")
        print("```")

        print("\nAFTER:")
        print("```python")
        print("working_buys = [o for o in orders if o.is_working and o.is_buy]")
        print("```")

        # Real example
        if positions:
            print("\n\nReal Position Summary:")
            for pos in positions:
                current_price = await suite["MNQ"].data.get_latest_price()
                if current_price:
                    pnl = pos.unrealized_pnl(current_price, tick_value=5.0)

                    # Clean, readable output
                    print(
                        f"{pos.direction} {pos.size} {pos.symbol} @ ${pos.averagePrice:,.2f}"
                    )
                    print(f"  Current: ${current_price:,.2f}")
                    print(f"  P&L: ${pnl:+,.2f}")

                    # Strategy decisions are clearer
                    if pos.is_long:
                        if pnl > 200:
                            print("  ➡️ Consider taking profit")
                        elif pnl < -100:
                            print("  ⚠️ Consider stop loss")
                    elif pos.is_short:
                        if pnl > 200:
                            print("  ➡️ Consider covering short")
                        elif pnl < -100:
                            print("  ⚠️ Consider stop loss")


async def main():
    """Run all demonstrations."""
    try:
        # Show position enhancements
        await demonstrate_position_properties()

        # Show order enhancements
        await demonstrate_order_properties()

        # Show strategy improvements
        await demonstrate_strategy_usage()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("ProjectX SDK v3.0.2 - Enhanced Models Demo")
    print("=" * 50)
    asyncio.run(main())
