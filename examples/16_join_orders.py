#!/usr/bin/env python3
"""
Example demonstrating JoinBid and JoinAsk order types with v3.0.0 TradingSuite.

JoinBid and JoinAsk orders are passive liquidity-providing orders that automatically
place limit orders at the current best bid or ask price. They're useful for:
- Market making strategies
- Providing liquidity
- Minimizing market impact
- Getting favorable queue position

Updated for v3.0.0: Uses new TradingSuite for simplified initialization.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from project_x_py import TradingSuite


async def main():
    """Demonstrate JoinBid and JoinAsk order placement."""
    # Initialize trading suite with simplified API (v3.0.0)
    suite = await TradingSuite.create("MNQ")

    try:
        # Contract to trade
        contract = "MNQ"

        print(f"=== JoinBid and JoinAsk Order Example for {contract} ===\n")

        # Get current market data to show context
        bars = await suite.client.get_bars(contract, days=1)
        if bars is not None and not bars.is_empty():
            latest = bars.tail(1)
            print(f"Current market context:")
            print(f"  Last price: ${latest['close'][0]:,.2f}")
            print(f"  High: ${latest['high'][0]:,.2f}")
            print(f"  Low: ${latest['low'][0]:,.2f}\n")

        try:
            # Example 1: Place a JoinBid order
            print("1. Placing JoinBid order (buy at best bid)...")
            join_bid_response = await suite.orders.place_join_bid_order(
                contract_id=contract, size=1
            )

            if join_bid_response.success:
                print(f"✅ JoinBid order placed successfully!")
                print(f"   Order ID: {join_bid_response.orderId}")
                print(f"   This order will buy at the current best bid price\n")
            else:
                print(f"❌ JoinBid order failed: {join_bid_response.message}\n")

            # Wait a moment
            await asyncio.sleep(2)

            # Example 2: Place a JoinAsk order
            print("2. Placing JoinAsk order (sell at best ask)...")
            join_ask_response = await suite.orders.place_join_ask_order(
                contract_id=contract, size=1
            )

            if join_ask_response.success:
                print(f"✅ JoinAsk order placed successfully!")
                print(f"   Order ID: {join_ask_response.orderId}")
                print(f"   This order will sell at the current best ask price\n")
            else:
                print(f"❌ JoinAsk order failed: {join_ask_response.message}\n")

            # Show order status
            print("3. Checking order status...")
            active_orders = await suite.orders.get_active_orders()

            print(f"\nActive orders: {len(active_orders)}")
            for order in active_orders:
                if order.id in [join_bid_response.orderId, join_ask_response.orderId]:
                    order_type = "JoinBid" if order.side == 0 else "JoinAsk"
                    side = "Buy" if order.side == 0 else "Sell"
                    print(
                        f"  - {order_type} Order {order.id}: {side} {order.size} @ ${order.price:,.2f}"
                    )

            # Cancel orders to clean up
            print("\n4. Cancelling orders...")
            if join_bid_response.success:
                cancel_result = await suite.orders.cancel_order(
                    join_bid_response.orderId
                )
                if cancel_result.success:
                    print(f"✅ JoinBid order {join_bid_response.orderId} cancelled")

            if join_ask_response.success:
                cancel_result = await suite.orders.cancel_order(
                    join_ask_response.orderId
                )
                if cancel_result.success:
                    print(f"✅ JoinAsk order {join_ask_response.orderId} cancelled")

        except Exception as e:
            print(f"❌ Error: {e}")

        print("\n=== JoinBid/JoinAsk Example Complete ===")
        print("\nKey Points:")
        print("- JoinBid places a limit buy order at the current best bid")
        print("- JoinAsk places a limit sell order at the current best ask")
        print("- These are passive orders that provide liquidity")
        print("- The actual fill price depends on market conditions")
        print("- Useful for market making and minimizing market impact")

    finally:
        # Clean disconnect
        await suite.disconnect()


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("PROJECT_X_API_KEY") or not os.getenv("PROJECT_X_USERNAME"):
        print(
            "❌ Error: Please set PROJECT_X_API_KEY and PROJECT_X_USERNAME environment variables"
        )
        print("Example:")
        print('  export PROJECT_X_API_KEY="your-api-key"')
        print('  export PROJECT_X_USERNAME="your-username"')
        sys.exit(1)

    asyncio.run(main())
