#!/usr/bin/env python3
"""
Example: Order Lifecycle Tracking with OrderTracker v3.0.0

This example demonstrates the new OrderTracker functionality that provides
comprehensive order lifecycle management with automatic state tracking and
async waiting capabilities.

Key features shown:
- OrderTracker context manager for automatic cleanup
- Async waiting for order fills and status changes
- Order modification and cancellation helpers
- Order chain builder for complex orders
- Common order templates

Author: SDK v3.0.0 Examples
"""

import asyncio
from datetime import datetime

from project_x_py import EventType, OrderLifecycleError, TradingSuite, get_template


async def demonstrate_order_tracker():
    """Show basic OrderTracker functionality."""

    async with await TradingSuite.create("MNQ") as suite:
        print("=== OrderTracker Demo ===\n")

        # Get current price
        price = await suite.data.get_latest_price()
        if not price:
            print("No price data available")
            return

        print(f"Current price: ${price:,.2f}\n")

        # 1. Basic order tracking with automatic fill detection
        print("1. Basic Order Tracking:")
        async with suite.track_order() as tracker:
            # Place a limit order below market
            order = await suite.orders.place_limit_order(
                contract_id=suite.instrument,
                side=0,  # BUY
                size=1,
                price=price - 50,  # 50 points below market
            )

            if not order.success:
                print(f"Order failed: {order.errorMessage}")
                return

            # Track the order
            tracker.track(order)
            print(f"Placed BUY limit order at ${price - 50:,.2f}")
            print(f"Order ID: {order.orderId}")

            # Wait for fill or timeout
            try:
                print("Waiting for fill (10s timeout)...")
                filled_order = await tracker.wait_for_fill(timeout=10)
                print(f"✅ Order filled at ${filled_order.filledPrice:,.2f}!")

            except TimeoutError:
                print("⏱️ Order not filled in 10 seconds")

                # Try to improve the price
                print("Modifying order price...")
                success = await tracker.modify_or_cancel(new_price=price - 25)

                if success:
                    print(f"✅ Order modified to ${price - 25:,.2f}")
                else:
                    print("❌ Order cancelled")

            except OrderLifecycleError as e:
                print(f"❌ Order error: {e}")

        print("\n" + "-" * 50 + "\n")

        # 2. Wait for specific status
        print("2. Waiting for Specific Status:")
        async with suite.track_order() as tracker:
            # Place a marketable limit order
            order = await suite.orders.place_limit_order(
                contract_id=suite.instrument,
                side=1,  # SELL
                size=1,
                price=price + 10,  # Slightly above market for quick fill
            )

            if order.success:
                tracker.track(order)
                print(f"Placed SELL limit order at ${price + 10:,.2f}")

                try:
                    # Wait for any terminal status
                    print("Waiting for order completion...")
                    completed = await tracker.wait_for_status(2, timeout=5)  # FILLED
                    print(f"✅ Order reached FILLED status")

                except TimeoutError:
                    print("⏱️ Order still pending")

                    # Check current status
                    current = await tracker.get_current_status()
                    if current:
                        print(f"Current status: {current.status_str}")


async def demonstrate_order_chain():
    """Show OrderChainBuilder functionality."""

    async with await TradingSuite.create("MNQ") as suite:
        print("\n=== Order Chain Builder Demo ===\n")

        # 1. Market order with bracket
        print("1. Market Order with Stops and Targets:")

        order_chain = (
            suite.order_chain()
            .market_order(size=1, side=0)  # BUY
            .with_stop_loss(offset=20)  # 20 points stop
            .with_take_profit(offset=40)  # 40 points target
        )

        print("Executing bracket order...")
        result = await order_chain.execute()

        if result.success:
            print(f"✅ Bracket order placed successfully:")
            print(f"   Entry: Market order (ID: {result.entry_order_id})")
            print(
                f"   Stop: ${result.stop_loss_price:,.2f} (ID: {result.stop_order_id})"
            )
            print(
                f"   Target: ${result.take_profit_price:,.2f} (ID: {result.target_order_id})"
            )
        else:
            print(f"❌ Bracket order failed: {result.error_message}")

        print("\n" + "-" * 50 + "\n")

        # 2. Limit order with dynamic stops
        print("2. Limit Order with Price-Based Stops:")

        current_price = await suite.data.get_latest_price()
        if current_price:
            order_chain = (
                suite.order_chain()
                .limit_order(size=1, price=current_price - 10, side=0)
                .with_stop_loss(price=current_price - 30)
                .with_take_profit(price=current_price + 20)
            )

            print(f"Building order:")
            print(f"   Entry: Limit BUY at ${current_price - 10:,.2f}")
            print(f"   Stop: ${current_price - 30:,.2f}")
            print(f"   Target: ${current_price + 20:,.2f}")

            result = await order_chain.execute()
            print(f"Result: {'✅ Success' if result.success else '❌ Failed'}")


async def demonstrate_order_templates():
    """Show pre-configured order templates."""

    async with await TradingSuite.create("MNQ") as suite:
        print("\n=== Order Templates Demo ===\n")

        # 1. Risk/Reward Template
        print("1. Risk/Reward Template (2:1):")

        template = get_template("standard_rr")

        try:
            # Risk $100 with 2:1 risk/reward
            result = await template.create_order(
                suite,
                side=0,  # BUY
                risk_amount=100,
            )

            if result.success:
                print(f"✅ 2:1 R/R order placed:")
                print(f"   Entry: ${result.entry_price:,.2f}")
                print(f"   Stop: ${result.stop_loss_price:,.2f}")
                print(f"   Target: ${result.take_profit_price:,.2f}")

                # Calculate actual R/R
                risk = abs(result.entry_price - result.stop_loss_price)
                reward = abs(result.take_profit_price - result.entry_price)
                print(f"   Actual R/R: {reward / risk:.2f}:1")
            else:
                print(f"❌ Order failed: {result.error_message}")

        except Exception as e:
            print(f"❌ Template error: {e}")

        print("\n" + "-" * 50 + "\n")

        # 2. ATR-based Template
        print("2. ATR-Based Stop Template:")

        # Make sure we have enough data for ATR
        await asyncio.sleep(2)

        atr_template = get_template("standard_atr")

        try:
            result = await atr_template.create_order(
                suite,
                side=1,  # SELL
                size=1,
            )

            if result.success:
                print(f"✅ ATR-based order placed:")
                print(f"   Stop distance based on 2x ATR")
                print(f"   Target distance based on 3x ATR")
                print(f"   Entry: ${result.entry_price:,.2f}")
                print(f"   Stop: ${result.stop_loss_price:,.2f}")
                print(f"   Target: ${result.take_profit_price:,.2f}")
            else:
                print(f"❌ Order failed: {result.error_message}")

        except Exception as e:
            print(f"❌ Template error: {e}")

        print("\n" + "-" * 50 + "\n")

        # 3. Scalping Template
        print("3. Scalping Template:")

        scalp_template = get_template("normal_scalp")

        try:
            result = await scalp_template.create_order(
                suite,
                side=0,  # BUY
                size=2,
                check_spread=False,  # Skip spread check for demo
            )

            if result.success:
                print(f"✅ Scalp order placed:")
                print(f"   4 tick stop, 8 tick target")
                print(f"   Entry: Market order")
                print(f"   Stop: ${result.stop_loss_price:,.2f}")
                print(f"   Target: ${result.take_profit_price:,.2f}")
            else:
                print(f"❌ Order failed: {result.error_message}")

        except Exception as e:
            print(f"❌ Template error: {e}")


async def demonstrate_advanced_tracking():
    """Show advanced order tracking scenarios."""

    async with await TradingSuite.create("MNQ") as suite:
        print("\n=== Advanced Order Tracking ===\n")

        # Track multiple orders
        print("1. Tracking Multiple Orders:")

        trackers = []
        order_ids = []

        current_price = await suite.data.get_latest_price()
        if not current_price:
            return

        # Place multiple orders
        for i in range(3):
            tracker = suite.track_order()

            order = await suite.orders.place_limit_order(
                contract_id=suite.instrument,
                side=0,  # BUY
                size=1,
                price=current_price - (10 * (i + 1)),  # Staggered prices
            )

            if order.success:
                await tracker.__aenter__()  # Enter context manually
                tracker.track(order)
                trackers.append(tracker)
                order_ids.append(order.orderId)
                print(f"Order {i + 1}: BUY at ${current_price - (10 * (i + 1)):,.2f}")

        print(f"\nTracking {len(trackers)} orders...")

        # Wait for any to fill
        print("Waiting for first fill...")

        fill_tasks = [tracker.wait_for_fill(timeout=5) for tracker in trackers]

        try:
            # Wait for first fill
            done, pending = await asyncio.wait(
                fill_tasks, return_when=asyncio.FIRST_COMPLETED
            )

            if done:
                filled = done.pop()
                try:
                    result = await filled
                    print(f"✅ First order filled: {result.id}")
                except Exception as e:
                    print(f"No fills: {e}")

            # Cancel remaining
            for task in pending:
                task.cancel()

        except asyncio.TimeoutError:
            print("⏱️ No orders filled")

        finally:
            # Cleanup trackers
            for tracker in trackers:
                await tracker.__aexit__(None, None, None)

        print("\n" + "-" * 50 + "\n")

        # 2. Complex order with event monitoring
        print("2. Order with Event Monitoring:")

        # Register for order events
        events_received = []

        async def on_order_event(event):
            events_received.append(event)
            print(
                f"📨 Event: {event.event_type.name} - Order {event.data.get('order_id')}"
            )

        await suite.on(EventType.ORDER_PLACED, on_order_event)
        await suite.on(EventType.ORDER_FILLED, on_order_event)
        await suite.on(EventType.ORDER_CANCELLED, on_order_event)

        # Place and track order
        async with suite.track_order() as tracker:
            order = await suite.orders.place_limit_order(
                contract_id=suite.instrument,
                side=1,  # SELL
                size=1,
                price=current_price + 100,  # Far from market
            )

            if order.success:
                tracker.track(order)
                print(f"Placed order at ${current_price + 100:,.2f}")

                # Give events time to arrive
                await asyncio.sleep(1)

                # Cancel the order
                print("Cancelling order...")
                await suite.orders.cancel_order(order.orderId)

                # Wait a bit for cancel event
                await asyncio.sleep(1)

        print(f"\nReceived {len(events_received)} events")

        # Cleanup event handlers
        await suite.off(EventType.ORDER_PLACED, on_order_event)
        await suite.off(EventType.ORDER_FILLED, on_order_event)
        await suite.off(EventType.ORDER_CANCELLED, on_order_event)


async def main():
    """Run all demonstrations."""
    try:
        # Basic order tracking
        await demonstrate_order_tracker()

        # Order chain builder
        await demonstrate_order_chain()

        # Order templates
        await demonstrate_order_templates()

        # Advanced scenarios
        await demonstrate_advanced_tracking()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("ProjectX SDK v3.0.0 - Order Lifecycle Tracking")
    print("=" * 50)
    asyncio.run(main())
