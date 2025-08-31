#!/usr/bin/env python3
"""
Async Order Management Example with Real Orders

⚠️  WARNING: THIS PLACES REAL ORDERS ON THE MARKET! ⚠️

Demonstrates comprehensive async order management using MNQ micro contracts:
- Market orders
- Limit orders
- Stop orders
- Bracket orders (entry + stop loss + take profit)
- Order tracking and status monitoring
- Order modification and cancellation
- Concurrent order operations

This example uses MNQ (Micro E-mini NASDAQ) to minimize risk during testing.

Updated for v3.0.0: Uses new TradingSuite for simplified initialization.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/02_order_management.py

Author: TexasCoding
Date: July 2025
"""

import asyncio
from decimal import Decimal
from typing import Any

from project_x_py import (
    TradingSuite,
    setup_logging,
)
from project_x_py.models import Order, OrderPlaceResponse


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


async def show_order_status(
    order_manager: Any, order_id: int, description: str
) -> None:
    """Show detailed order status information."""
    print(f"\n📋 {description} Status:")

    # Check if order is tracked in real-time cache (with built-in wait)
    order_data = await order_manager.get_tracked_order_status(
        str(order_id), wait_for_cache=True
    )

    if order_data:
        status_map = {1: "Open", 2: "Filled", 3: "Cancelled", 4: "Partially Filled"}
        status = status_map.get(
            order_data.get("status", 0), f"Unknown ({order_data.get('status')})"
        )

        print(f"   Order ID: {order_id}")
        print(f"   Status: {status} (from real-time cache)")
        print(f"   Side: {'BUY' if order_data.get('side') == 0 else 'SELL'}")
        print(f"   Size: {order_data.get('size', 0)}")
        print(f"   Fill Volume: {order_data.get('fillVolume', 0)}")

        if order_data.get("limitPrice"):
            print(f"   Limit Price: ${order_data['limitPrice']:.2f}")
        if order_data.get("stopPrice"):
            print(f"   Stop Price: ${order_data['stopPrice']:.2f}")
        if order_data.get("filledPrice"):
            print(f"   Filled Price: ${order_data['filledPrice']:.2f}")
    else:
        # Fall back to API check for status
        print(f"   Order {order_id} not in real-time cache, checking API...")
        api_order: Order | None = await order_manager.get_order_by_id(order_id)
        if not isinstance(api_order, Order):
            print(f"   Order {order_id} not found in API either")
            return

        status_map = {1: "Open", 2: "Filled", 3: "Cancelled", 4: "Partially Filled"}
        status = status_map.get(api_order.status, f"Unknown ({api_order.status})")
        print(f"   Status: {status} (from API)")
        print(f"   Side: {'BUY' if api_order.side == 0 else 'SELL'}")
        print(f"   Size: {api_order.size}")
        print(f"   Fill Volume: {api_order.fillVolume}")

    # Check if filled
    is_filled = await order_manager.is_order_filled(order_id)
    print(f"   Filled: {'Yes' if is_filled else 'No'}")


async def main() -> bool:
    """Demonstrate comprehensive async order management with real orders."""
    logger = setup_logging(level="INFO")
    print("🚀 Async Order Management Example with REAL ORDERS (v3.0.0)")
    print("=" * 60)

    # Safety warning
    print("⚠️  WARNING: This script places REAL ORDERS on the market!")
    print("   - Uses MNQ micro contracts to minimize risk")
    print("   - Only use in simulated/demo accounts")
    print("   - Monitor positions closely")
    print("   - Orders will be cancelled at the end")

    if not await wait_for_user_confirmation("This will place REAL ORDERS. Proceed?"):
        print("❌ Order management example cancelled for safety")
        return False

    try:
        # Initialize trading suite with TradingSuite v3
        print("\n🔑 Initializing TradingSuite v3...")
        suite = await TradingSuite.create("MNQ")

        account = suite.client.account_info
        if not account:
            print("❌ No account information available")
            await suite.disconnect()
            return False

        print(f"✅ Connected to account: {account.name}")
        print(f"   Balance: ${account.balance:,.2f}")
        print(f"   Simulated: {account.simulated}")

        if not account.canTrade:
            print("❌ Trading not enabled on this account")
            await suite.disconnect()
            return False

        # Get MNQ contract information
        print("\n📈 Getting MNQ contract information...")
        mnq_instrument = await suite.client.get_instrument("MNQ")
        if not mnq_instrument:
            print("❌ Could not find MNQ instrument")
            await suite.disconnect()
            return False

        contract_id = mnq_instrument.id
        tick_size = Decimal(str(mnq_instrument.tickSize))

        print(f"✅ MNQ Contract: {mnq_instrument.name}")
        print(f"   Contract ID: {contract_id}")
        print(f"   Tick Size: ${tick_size}")
        print(f"   Tick Value: ${mnq_instrument.tickValue}")

        # Get current market price (with fallback for closed markets)
        print("\n📊 Getting current market data...")
        current_price = None

        # Try different data configurations to find available data
        for days, interval in [(1, 1), (1, 5), (2, 15), (5, 15), (7, 60)]:
            try:
                market_data = await suite.client.get_bars(
                    "MNQ", days=days, interval=interval
                )
                if market_data is not None and not market_data.is_empty():
                    current_price = Decimal(
                        str(market_data.select("close").tail(1).item())
                    )
                    latest_time = market_data.select("timestamp").tail(1).item()
                    print(f"✅ Retrieved MNQ price: ${current_price:.2f}")
                    print(f"   Data from: {latest_time} ({days}d {interval}min bars)")
                    break
            except Exception:
                continue

        # If no historical data available, use a reasonable fallback price
        if current_price is None:
            print("⚠️  No historical market data available (market may be closed)")
            print("   Using fallback price for demonstration...")
            # Use a typical MNQ price range (around $20,000-$25,000)
            current_price = Decimal("23400.00")  # Reasonable MNQ price
            print(f"   Fallback price: ${current_price:.2f}")
            print("   Note: In live trading, ensure you have current market data!")

        # TradingSuite v3 includes order manager with real-time tracking
        print("\n🏗️ Using TradingSuite order manager...")
        order_manager = suite["MNQ"].orders
        print("✅ Order manager ready with real-time tracking")

        # Track orders placed in this demo for cleanup
        demo_orders: list[int] = []

        try:
            # Example 1: Limit Order (less likely to fill immediately)
            print("\n" + "=" * 50)
            print("📝 EXAMPLE 1: LIMIT ORDER")
            print("=" * 50)

            limit_price = current_price - Decimal("10.0")  # $10 below market
            print("Placing limit BUY order:")
            print("   Size: 1 contract")
            print(
                f"   Limit Price: ${limit_price:.2f} (${current_price - limit_price:.2f} below market)"
            )

            if await wait_for_user_confirmation("Place limit order?"):
                limit_response: OrderPlaceResponse = (
                    await order_manager.place_limit_order(  # type: ignore[misc]
                        contract_id=contract_id,
                        side=0,  # Buy
                        size=1,
                        limit_price=float(limit_price),
                    )
                )

                if limit_response and limit_response.success:
                    order_id = limit_response.orderId
                    demo_orders.append(order_id)
                    print(f"✅ Limit order placed! Order ID: {order_id}")

                    # Wait and check status
                    await asyncio.sleep(2)
                    await show_order_status(order_manager, order_id, "Limit Order")
                else:
                    error_msg = (
                        limit_response.errorMessage
                        if limit_response
                        else "Unknown error"
                    )
                    print(f"❌ Limit order failed: {error_msg}")

            # Example 2: Stop Order (triggered if price rises)
            print("\n" + "=" * 50)
            print("📝 EXAMPLE 2: STOP ORDER")
            print("=" * 50)

            stop_price = current_price + Decimal("15.0")  # $15 above market
            print("Placing stop BUY order:")
            print("   Size: 1 contract")
            print(
                f"   Stop Price: ${stop_price:.2f} (${stop_price - current_price:.2f} above market)"
            )
            print("   (Will trigger if price reaches this level)")

            if await wait_for_user_confirmation("Place stop order?"):
                stop_response = await order_manager.place_stop_order(
                    contract_id=contract_id,
                    side=0,  # Buy
                    size=1,
                    stop_price=float(stop_price),
                )

                if stop_response and stop_response.success:
                    order_id = stop_response.orderId
                    demo_orders.append(order_id)
                    print(f"✅ Stop order placed! Order ID: {order_id}")

                    await asyncio.sleep(2)
                    await show_order_status(order_manager, order_id, "Stop Order")
                else:
                    error_msg = (
                        stop_response.errorMessage if stop_response else "Unknown error"
                    )
                    print(f"❌ Stop order failed: {error_msg}")

            # Example 3: Bracket Order (Entry + Stop Loss + Take Profit)
            print("\n" + "=" * 50)
            print("📝 EXAMPLE 3: BRACKET ORDER")
            print("=" * 50)

            try:
                market_data = await suite.client.get_bars(
                    "MNQ", days=days, interval=interval
                )
                if market_data is not None and not market_data.is_empty():
                    current_price = Decimal(
                        str(market_data.select("close").tail(1).item())
                    )
                    latest_time = market_data.select("timestamp").tail(1).item()
                    print(f"✅ Retrieved MNQ price: ${current_price:.2f}")
                    print(f"   Data from: {latest_time} ({days}d {interval}min bars)")
            except Exception:
                print("❌ Failed to get market data")
                return False

            entry_price = current_price - Decimal("1.00")  # Entry $5 below market
            stop_loss = entry_price - Decimal("10.0")  # $10 risk
            take_profit = entry_price + Decimal("20.0")  # $20 profit target (2:1 R/R)

            print("Placing bracket order:")
            print("   Size: 1 contract")
            print(f"   Entry: ${entry_price:.2f} (limit order)")
            print(
                f"   Stop Loss: ${stop_loss:.2f} (${entry_price - stop_loss:.2f} risk)"
            )
            print(
                f"   Take Profit: ${take_profit:.2f} (${take_profit - entry_price:.2f} profit)"
            )
            print("   Risk/Reward: 1:2 ratio")

            if await wait_for_user_confirmation("Place bracket order?"):
                try:
                    bracket_response = await order_manager.place_bracket_order(
                        contract_id=contract_id,
                        side=0,  # Buy
                        size=1,
                        entry_price=float(entry_price),
                        stop_loss_price=float(stop_loss),
                        take_profit_price=float(take_profit),
                        entry_type="limit",
                    )
                except Exception as e:
                    print(f"❌ Bracket order failed with exception: {e}")
                    bracket_response = None

                if bracket_response and bracket_response.success:
                    print("✅ Bracket order placed successfully!")

                    if bracket_response.entry_order_id:
                        demo_orders.append(bracket_response.entry_order_id)
                        print(f"   Entry Order ID: {bracket_response.entry_order_id}")
                    if bracket_response.stop_order_id:
                        demo_orders.append(bracket_response.stop_order_id)
                        print(f"   Stop Order ID: {bracket_response.stop_order_id}")
                    if bracket_response.target_order_id:
                        demo_orders.append(bracket_response.target_order_id)
                        print(f"   Target Order ID: {bracket_response.target_order_id}")

                    # Show status of all bracket orders
                    await asyncio.sleep(2)
                    if bracket_response.entry_order_id:
                        await show_order_status(
                            order_manager,
                            bracket_response.entry_order_id,
                            "Entry Order",
                        )
                else:
                    error_msg = (
                        bracket_response.error_message
                        if bracket_response
                        else "Unknown error"
                    )
                    print(f"❌ Bracket order failed: {error_msg}")

            # Example 4: Order Modification
            if demo_orders:
                print("\n" + "=" * 50)
                print("📝 EXAMPLE 4: ORDER MODIFICATION")
                print("=" * 50)

                first_order = demo_orders[0]
                print(f"Attempting to modify Order #{first_order}")

                # Get order details to determine type
                order_data = await order_manager.get_tracked_order_status(
                    str(first_order), wait_for_cache=True
                )

                if not order_data:
                    # Fallback to API
                    api_order = await order_manager.get_order_by_id(first_order)
                    if api_order and hasattr(api_order, "type"):
                        # Order types: 1=Limit, 2=Market, 4=Stop
                        is_stop_order = api_order.type == 4
                    else:
                        is_stop_order = False
                else:
                    # Check if it has a stop price (indicating stop order)
                    is_stop_order = bool(order_data.get("stopPrice"))

                await show_order_status(
                    order_manager, first_order, "Before Modification"
                )

                # Modify based on order type
                if is_stop_order:
                    # For stop orders, modify the stop price
                    new_stop_price = current_price + Decimal("10.0")  # Move stop closer
                    print(
                        f"\nModifying stop order to new stop price: ${new_stop_price:.2f}"
                    )

                    if await wait_for_user_confirmation("Modify order?"):
                        modify_success = await order_manager.modify_order(
                            order_id=first_order, stop_price=float(new_stop_price)
                        )
                else:
                    # For limit orders, modify the limit price
                    new_limit_price = current_price - Decimal("5.0")  # Closer to market
                    print(
                        f"\nModifying limit order to new limit price: ${new_limit_price:.2f}"
                    )

                    if await wait_for_user_confirmation("Modify order?"):
                        modify_success = await order_manager.modify_order(
                            order_id=first_order, limit_price=float(new_limit_price)
                        )

                if "modify_success" in locals() and modify_success:
                    print(f"✅ Order {first_order} modified successfully")
                    await asyncio.sleep(2)
                    await show_order_status(
                        order_manager, first_order, "After Modification"
                    )
                elif "modify_success" in locals():
                    print(f"❌ Failed to modify order {first_order}")

            # Monitor orders for a short time
            if demo_orders:
                print("\n" + "=" * 50)
                print("👀 MONITORING ORDERS")
                print("=" * 50)

                print("Monitoring orders for 30 seconds...")
                print("(Looking for fills, status changes, etc.)")

                for i in range(6):  # 30 seconds, check every 5 seconds
                    print(f"\n⏰ Check {i + 1}/6...")

                    # Check for filled orders and positions
                    filled_orders = []
                    for order_id in demo_orders:
                        if await order_manager.is_order_filled(order_id):
                            filled_orders.append(order_id)

                    if filled_orders:
                        print(f"🎯 Orders filled: {filled_orders}")
                        for filled_id in filled_orders:
                            await show_order_status(
                                order_manager,
                                filled_id,
                                f"Filled Order {filled_id}",
                            )
                    else:
                        print("📋 No orders filled yet")

                    # Check current positions (to detect fills that weren't caught)
                    current_positions = await suite["MNQ"].positions.get_all_positions()
                    if current_positions:
                        print(f"📊 Open positions: {len(current_positions)}")
                        for pos in current_positions:
                            side = "LONG" if pos.type == 1 else "SHORT"
                            print(
                                f"   {pos.contractId}: {side} {pos.size} @ ${pos.averagePrice:.2f}"
                            )

                    # Show current open orders
                    open_orders = await order_manager.search_open_orders(
                        contract_id=contract_id
                    )
                    print(f"📊 Open orders: {len(open_orders)}")
                    if open_orders:
                        for order in open_orders:
                            side = "BUY" if order.side == 0 else "SELL"
                            order_type = {1: "LIMIT", 2: "MARKET", 4: "STOP"}.get(
                                order.type, f"TYPE_{order.type}"
                            )
                            status = {1: "OPEN", 2: "FILLED", 3: "CANCELLED"}.get(
                                order.status, f"STATUS_{order.status}"
                            )
                            price = ""
                            if hasattr(order, "limitPrice") and order.limitPrice:
                                price = f" @ ${order.limitPrice:.2f}"
                            elif hasattr(order, "stopPrice") and order.stopPrice:
                                price = f" @ ${order.stopPrice:.2f}"
                            print(
                                f"   Order #{order.id}: {side} {order.size} {order_type}{price} - {status}"
                            )

                    if i < 5:  # Don't sleep on last iteration
                        await asyncio.sleep(5)

            # Show final order statistics
            print("\n" + "=" * 50)
            print("📊 ORDER STATISTICS")
            print("=" * 50)

            stats = await order_manager.get_order_statistics_async()
            print("Order Manager Statistics:")
            print(f"   Orders Placed: {stats.get('orders_placed', 0)}")
            print(f"   Orders Cancelled: {stats.get('orders_cancelled', 0)}")
            print(f"   Orders Modified: {stats.get('orders_modified', 0)}")
            print(f"   Bracket Orders: {stats.get('bracket_orders', 0)}")
            print(f"   Fill Rate: {stats.get('fill_rate', 0):.1%}")
            print(f"   Market Orders: {stats.get('market_orders', 0)}")
            print(f"   Limit Orders: {stats.get('limit_orders', 0)}")
            print(f"   Stop Orders: {stats.get('stop_orders', 0)}")

        finally:
            # Enhanced cleanup: Cancel ALL orders and close ALL positions
            print("\n" + "=" * 50)
            print("🧹 ENHANCED CLEANUP - ORDERS & POSITIONS")
            print("=" * 50)

            try:
                # First, get ALL open orders (not just demo orders)
                all_orders = await order_manager.search_open_orders()
                print(f"Found {len(all_orders)} total open orders")

                # Cancel all orders
                cancelled_count = 0
                for order in all_orders:
                    try:
                        if await order_manager.cancel_order(order.id):
                            print(f"✅ Cancelled order #{order.id}")
                            cancelled_count += 1
                        else:
                            # Order might already be cancelled or filled
                            print(f"⚠️  Could not cancel order #{order.id} (may be filled or already cancelled)")
                    except Exception as e:
                        # Log but don't fail on individual order cancellation errors
                        if "already cancelled" in str(e).lower() or "none" in str(e).lower():
                            print(f"ℹ️  Order #{order.id} was already cancelled or doesn't exist")
                        else:
                            print(f"⚠️  Error cancelling order #{order.id}: {e}")

                # Check for positions and close them
                positions = await suite["MNQ"].positions.get_all_positions()
                print(f"Found {len(positions)} open positions")

                closed_count = 0
                for position in positions:
                    try:
                        side_text = "LONG" if position.type == 1 else "SHORT"
                        print(
                            f"Closing {side_text} position: {position.contractId} ({position.size} contracts)"
                        )

                        response = await order_manager.close_position(
                            position.contractId, method="market"
                        )

                        if response and response.success:
                            print(
                                f"✅ Closed position {position.contractId} (Order #{response.orderId})"
                            )
                            closed_count += 1
                        else:
                            print(f"❌ Failed to close position {position.contractId}")
                    except Exception as e:
                        print(f"❌ Error closing position {position.contractId}: {e}")

                print("\n📊 Cleanup completed:")
                print(f"   Orders cancelled: {cancelled_count}")
                print(f"   Positions closed: {closed_count}")

            except Exception as e:
                print(f"❌ Cleanup error: {e}")
                print("⚠️  Manual cleanup may be required")

        # Final status check
        print("\n" + "=" * 50)
        print("📈 FINAL STATUS")
        print("=" * 50)

        open_orders = await order_manager.search_open_orders(contract_id=contract_id)
        print(f"Remaining open orders: {len(open_orders)}")

        if open_orders:
            print("⚠️  Warning: Some orders may still be open")
            for order in open_orders:
                side = "BUY" if order.side == 0 else "SELL"
                price = (
                    getattr(order, "limitPrice", None)
                    or getattr(order, "stopPrice", None)
                    or "Market"
                )
                print(f"   Order #{order.id}: {side} {order.size} @ {price}")

        print("\n✅ Async order management example completed!")
        print("\n📝 Next Steps:")
        print("   - Check your trading platform for any filled positions")
        print("   - Try examples/03_position_management.py for position tracking")
        print("   - Review order manager documentation for advanced features")

        await suite.disconnect()
        return True

    except KeyboardInterrupt:
        print("\n⏹️ Example interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Async order management example failed: {e}")
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Example interrupted by user")
        exit(0)
