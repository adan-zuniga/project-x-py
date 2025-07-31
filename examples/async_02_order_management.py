#!/usr/bin/env python3
"""
Async Order Management Example with Real Orders

⚠️  WARNING: THIS PLACES REAL ORDERS ON THE MARKET! ⚠️

Demonstrates comprehensive async order management using MNQ micro contracts:
- Concurrent order placement
- Market, limit, stop, and bracket orders
- Real-time order tracking with async updates
- Order modification and cancellation
- Async event handling for order fills

This example uses MNQ (Micro E-mini NASDAQ) to minimize risk during testing.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/async_02_order_management.py

Author: TexasCoding
Date: July 2025
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from project_x_py import (
    AsyncProjectX,
    create_async_order_manager,
    create_async_realtime_client,
    setup_logging,
)


async def wait_for_user_confirmation(message: str) -> bool:
    """Wait for user confirmation before proceeding."""
    print(f"\n⚠️  {message}")
    try:
        # Run input in executor to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: input("Continue? (y/N): ").strip().lower()
        )
        return response == "y"
    except (EOFError, KeyboardInterrupt):
        # Handle EOF when input is piped (default to no for safety)
        print("N (EOF detected - defaulting to No for safety)")
        return False


async def show_order_status(order_manager, order_id: int, description: str):
    """Show detailed order status information."""
    print(f"\n📋 {description} Status:")

    # Check if order is tracked in real-time cache
    order_data = await order_manager.get_tracked_order_status(
        str(order_id), wait_for_cache=True
    )

    if order_data:
        status_map = {1: "Open", 2: "Filled", 3: "Cancelled", 4: "Partially Filled"}
        status = status_map.get(
            order_data.get("status", 0), f"Unknown ({order_data.get('status')})"
        )

        print(f"  Order ID: {order_data.get('orderId', 'Unknown')}")
        print(f"  Status: {status}")
        print(
            f"  Filled: {order_data.get('filledQuantity', 0)}/{order_data.get('quantity', 0)}"
        )
        print(f"  Average Fill Price: ${order_data.get('averageFillPrice', 0):.2f}")
    else:
        print(f"  Order ID: {order_id} (awaiting real-time update)")


async def place_concurrent_orders(order_manager, instrument_id: str):
    """Demonstrate placing multiple orders concurrently."""
    print("\n🚀 Demonstrating Concurrent Order Placement")

    # Get current market price
    instrument = await order_manager.project_x.get_instrument(instrument_id)
    if not instrument:
        print("❌ Could not get instrument data")
        return

    current_price = float(instrument.lastPrice)
    tick_size = float(instrument.tickSize)

    # Define multiple orders
    orders = [
        {
            "type": "limit",
            "side": 0,  # Buy
            "price": current_price - (50 * tick_size),
            "size": 1,
            "description": "Buy Limit 50 ticks below",
        },
        {
            "type": "limit",
            "side": 1,  # Sell
            "price": current_price + (50 * tick_size),
            "size": 1,
            "description": "Sell Limit 50 ticks above",
        },
        {
            "type": "stop",
            "side": 0,  # Buy
            "price": current_price + (25 * tick_size),
            "size": 1,
            "description": "Buy Stop 25 ticks above",
        },
    ]

    print(f"\nPlacing {len(orders)} orders concurrently...")
    print(f"Current price: ${current_price:.2f}")

    # Create tasks for concurrent order placement
    tasks = []
    for order in orders:
        if order["type"] == "limit":
            task = order_manager.place_limit_order(
                instrument_id, order["side"], order["size"], order["price"]
            )
        else:  # stop order
            task = order_manager.place_stop_order(
                instrument_id, order["side"], order["size"], order["price"]
            )
        tasks.append(task)

    # Place all orders concurrently
    start_time = asyncio.get_event_loop().time()
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = asyncio.get_event_loop().time()

    print(f"\n✅ Placed {len(orders)} orders in {end_time - start_time:.2f} seconds")

    # Show results
    order_ids = []
    for i, (response, order) in enumerate(zip(responses, orders)):
        if isinstance(response, Exception):
            print(f"❌ {order['description']}: Failed - {response}")
        elif response and response.success:
            print(f"✅ {order['description']}: Order ID {response.orderId}")
            order_ids.append(response.orderId)
        else:
            print(f"❌ {order['description']}: Failed")

    return order_ids


async def main():
    """Main async function demonstrating order management."""
    logger = setup_logging(level="INFO")
    logger.info("🚀 Starting Async Order Management Example")

    try:
        # Create async client and authenticate
        async with AsyncProjectX.from_env() as client:
            await client.authenticate()
            print(f"✅ Connected as: {client.account_info.name}")

            # Create real-time client for order tracking
            realtime_client = create_async_realtime_client(
                client.session_token, client.account_info.id
            )

            # Create order manager with real-time integration
            order_manager = create_async_order_manager(client, realtime_client)
            await order_manager.initialize()

            # Connect real-time client
            print("\n🔌 Connecting to real-time services...")
            if await realtime_client.connect():
                await realtime_client.subscribe_user_updates()
                print("✅ Real-time order tracking enabled")
            else:
                print("⚠️  Real-time tracking unavailable - continuing without it")

            # Find MNQ instrument
            print("\n🔍 Finding MNQ instrument...")
            instruments = await client.search_instruments("MNQ")
            if not instruments:
                print("❌ MNQ instrument not found")
                return

            mnq = instruments[0]
            contract_id = mnq.activeContract
            print(f"✅ Using: {mnq.symbol} ({contract_id})")
            print(f"   Current Price: ${mnq.lastPrice}")
            print(f"   Tick Size: ${mnq.tickSize}")

            # WARNING: Real order placement
            if not await wait_for_user_confirmation(
                "This will place REAL ORDERS on MNQ. Are you sure?"
            ):
                print("❌ Cancelled by user")
                return

            # 1. Demonstrate concurrent order placement
            order_ids = await place_concurrent_orders(order_manager, contract_id)

            if order_ids:
                # Wait a moment for orders to be processed
                await asyncio.sleep(2)

                # Cancel all orders concurrently
                print(f"\n🛑 Cancelling {len(order_ids)} orders concurrently...")
                cancel_tasks = [
                    order_manager.cancel_order(order_id) for order_id in order_ids
                ]

                start_time = asyncio.get_event_loop().time()
                results = await asyncio.gather(*cancel_tasks, return_exceptions=True)
                end_time = asyncio.get_event_loop().time()

                cancelled = sum(
                    1 for r in results if r and not isinstance(r, Exception)
                )
                print(
                    f"✅ Cancelled {cancelled}/{len(order_ids)} orders in {end_time - start_time:.2f} seconds"
                )

            # 2. Demonstrate bracket order with async monitoring
            print("\n📊 Placing Bracket Order...")
            current_price = float(mnq.lastPrice)
            tick_size = float(mnq.tickSize)

            entry_price = current_price - (20 * tick_size)
            stop_loss = entry_price - (10 * tick_size)
            take_profit = entry_price + (20 * tick_size)

            print(f"  Entry: ${entry_price:.2f}")
            print(f"  Stop Loss: ${stop_loss:.2f}")
            print(f"  Take Profit: ${take_profit:.2f}")

            bracket_response = await order_manager.place_bracket_order(
                contract_id,
                side=0,  # Buy
                size=1,
                entry_price=entry_price,
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
            )

            if bracket_response and bracket_response.success:
                print(f"✅ Bracket order placed: {bracket_response.orderId}")

                # Monitor bracket order status
                await asyncio.sleep(2)
                await show_order_status(
                    order_manager, bracket_response.orderId, "Bracket Order"
                )

                # Cancel bracket order
                if await wait_for_user_confirmation("Cancel bracket order?"):
                    result = await order_manager.cancel_bracket_order(
                        bracket_response.orderId
                    )
                    if result:
                        print("✅ Bracket order cancelled")

            # Show final open orders
            print("\n📋 Final Open Orders Check:")
            open_orders = await order_manager.search_open_orders()
            print(f"  Total open orders: {len(open_orders)}")

            # Clean up
            await realtime_client.cleanup()

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ASYNC ORDER MANAGEMENT EXAMPLE")
    print("=" * 60)
    print("\n⚠️  WARNING: THIS PLACES REAL ORDERS! ⚠️\n")

    asyncio.run(main())

    print("\n✅ Example completed!")
