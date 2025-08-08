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
        print(f"=== JoinBid and JoinAsk Order Example for {suite.symbol} ===")
        print(f"Using contract: {suite.instrument_id}")
        if suite.instrument:
            print(
                f"Tick size: ${suite.instrument.tickSize}, Tick value: ${suite.instrument.tickValue}"
            )
        print()

        # Get current market data to show context
        bars = await suite.client.get_bars(suite.symbol, days=1)
        if bars is not None and not bars.is_empty():
            latest = bars.tail(1)
            print("Current market context:")
            print(f"  Last price: ${latest['close'][0]:,.2f}")
            print(f"  High: ${latest['high'][0]:,.2f}")
            print(f"  Low: ${latest['low'][0]:,.2f}\n")

        try:
            # Example 1: Place a JoinBid order
            print("1. Placing JoinBid order (buy at best bid)...")

            # Note: JoinBid/JoinAsk orders may not be supported in all environments
            # or may require specific market conditions (active bid/ask quotes)
            try:
                join_bid_response = await suite.orders.place_join_bid_order(
                    contract_id=suite.instrument_id, size=1
                )

                if join_bid_response.success:
                    print("✅ JoinBid order placed successfully!")
                    print(f"   Order ID: {join_bid_response.orderId}")
                    print("   This order will buy at the current best bid price\n")
                else:
                    error_msg = join_bid_response.errorMessage or "Unknown error"
                    print(f"❌ JoinBid order failed: {error_msg}")
                    print(f"   Error code: {join_bid_response.errorCode}\n")
            except Exception as e:
                print(f"❌ JoinBid order error: {e}")
                print(
                    "   Note: JoinBid/JoinAsk orders may not be available in simulation mode\n"
                )
                join_bid_response = None

            # Wait a moment
            await asyncio.sleep(2)

            # Example 2: Place a JoinAsk order
            print("2. Placing JoinAsk order (sell at best ask)...")
            try:
                join_ask_response = await suite.orders.place_join_ask_order(
                    contract_id=suite.instrument_id, size=1
                )

                if join_ask_response.success:
                    print("✅ JoinAsk order placed successfully!")
                    print(f"   Order ID: {join_ask_response.orderId}")
                    print("   This order will sell at the current best ask price\n")
                else:
                    error_msg = join_ask_response.errorMessage or "Unknown error"
                    print(f"❌ JoinAsk order failed: {error_msg}")
                    print(f"   Error code: {join_ask_response.errorCode}\n")
            except Exception as e:
                print(f"❌ JoinAsk order error: {e}")
                print(
                    "   Note: JoinBid/JoinAsk orders may not be available in simulation mode\n"
                )
                join_ask_response = None

            # Show order status
            print("3. Checking order status...")
            active_orders = await suite.orders.search_open_orders()

            print(f"\nActive orders: {len(active_orders)}")
            order_ids = []
            if (
                join_bid_response
                and hasattr(join_bid_response, "orderId")
                and join_bid_response.success
            ):
                order_ids.append(join_bid_response.orderId)
            if (
                join_ask_response
                and hasattr(join_ask_response, "orderId")
                and join_ask_response.success
            ):
                order_ids.append(join_ask_response.orderId)

            for order in active_orders:
                if order.id in order_ids:
                    order_type = "JoinBid" if order.side == 0 else "JoinAsk"
                    side = "Buy" if order.side == 0 else "Sell"
                    price_str = (
                        f"${order.limitPrice:,.2f}" if order.limitPrice else "Market"
                    )
                    print(
                        f"  - {order_type} Order {order.id}: {side} {order.size} @ {price_str}"
                    )

            # Cancel orders to clean up
            if order_ids:
                print("\n4. Cancelling orders...")
                if join_bid_response and join_bid_response.success:
                    cancel_result = await suite.orders.cancel_order(
                        join_bid_response.orderId
                    )
                    if cancel_result:
                        print(f"✅ JoinBid order {join_bid_response.orderId} cancelled")

                if join_ask_response and join_ask_response.success:
                    cancel_result = await suite.orders.cancel_order(
                        join_ask_response.orderId
                    )
                    if cancel_result:
                        print(f"✅ JoinAsk order {join_ask_response.orderId} cancelled")

        except Exception as e:
            print(f"❌ Error: {e}")

        print("\n=== Alternative: Using Limit Orders ===")
        print("If JoinBid/JoinAsk orders are not available, you can achieve")
        print("similar results using limit orders with current market prices:")
        print("\nExample code:")
        print("```python")
        print("# Get current orderbook or last trade price")
        print("current_price = await suite.data.get_current_price()")
        print("# Place limit orders slightly below/above market")
        print("buy_order = await suite.orders.place_limit_order(")
        print("    contract_id='MNQ',")
        print("    side=0,  # Buy")
        print("    size=1,")
        print("    limit_price=current_price - 0.25  # One tick below")
        print(")")
        print("```")

        print("\n=== JoinBid/JoinAsk Example Complete ===")
        print("\nKey Points:")
        print("- JoinBid places a limit buy order at the current best bid")
        print("- JoinAsk places a limit sell order at the current best ask")
        print("- These are passive orders that provide liquidity")
        print("- The actual fill price depends on market conditions")
        print("- Useful for market making and minimizing market impact")
        print("- May not be available in all trading environments")

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
