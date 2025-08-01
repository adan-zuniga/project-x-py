"""
Example demonstrating AsyncOrderManager usage for order operations.

This example shows how to use the AsyncOrderManager for placing orders,
managing brackets, and handling order modifications with async/await.
"""

import asyncio

from project_x_py import AsyncOrderManager, AsyncProjectX


async def main():
    """Main async function demonstrating order management."""
    # Create async client
    async with AsyncProjectX.from_env() as client:
        # Authenticate
        await client.authenticate()
        print(f"✅ Authenticated as {client.account_info.name}")

        # Create order manager
        order_manager = AsyncOrderManager(client)

        # 1. Place a market order
        print("\n📈 Placing market order...")
        market_order = await order_manager.place_market_order(
            "MGC",  # Micro Gold
            side=0,  # Buy
            size=1,
        )
        if market_order:
            print(f"✅ Market order placed: ID {market_order.orderId}")

        # 2. Place a limit order
        print("\n📊 Placing limit order...")
        limit_order = await order_manager.place_limit_order(
            "MNQ",  # Micro NASDAQ
            side=0,  # Buy
            size=1,
            price=18000.0,  # Will be auto-aligned to tick size
        )
        if limit_order:
            print(f"✅ Limit order placed: ID {limit_order.orderId}")

        # 3. Place a bracket order (entry + stop loss + take profit)
        print("\n🎯 Placing bracket order...")
        bracket = await order_manager.place_bracket_order(
            "MES",  # Micro S&P
            side=0,  # Buy
            size=1,
            entry_type=2,  # Limit entry
            entry_price=5700.0,
            stop_loss_offset=10.0,  # 10 points below entry
            take_profit_offset=20.0,  # 20 points above entry
        )
        if bracket and bracket.success:
            print("✅ Bracket order placed:")
            print(f"   Entry: {bracket.entry_order_id}")
            print(f"   Stop Loss: {bracket.stop_order_id}")
            print(f"   Take Profit: {bracket.target_order_id}")

        # 4. Search for open orders
        print("\n🔍 Searching for open orders...")
        open_orders = await order_manager.search_open_orders()
        print(f"Found {len(open_orders)} open orders:")
        for order in open_orders:
            side_str = "BUY" if order.side == 0 else "SELL"
            print(f"   {order.id}: {side_str} {order.size} {order.contractId}")

        # 5. Modify an order (if we have any open orders)
        if open_orders and open_orders[0].limitPrice:
            print(f"\n✏️ Modifying order {open_orders[0].id}...")
            new_price = float(open_orders[0].limitPrice) + 1.0
            success = await order_manager.modify_order(
                open_orders[0].id, new_price=new_price
            )
            if success:
                print(f"✅ Order modified to new price: {new_price}")

        # 6. Cancel an order (if we have open orders)
        if len(open_orders) > 1:
            print(f"\n❌ Cancelling order {open_orders[1].id}...")
            success = await order_manager.cancel_order(open_orders[1].id)
            if success:
                print("✅ Order cancelled")

        # 7. Display statistics
        stats = order_manager.get_stats()
        print("\n📊 Order Manager Statistics:")
        print(f"   Orders placed: {stats['orders_placed']}")
        print(f"   Orders cancelled: {stats['orders_cancelled']}")
        print(f"   Orders modified: {stats['orders_modified']}")
        print(f"   Bracket orders: {stats['bracket_orders_placed']}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
