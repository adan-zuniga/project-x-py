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

Author: SDK v3.0.2 Examples
"""

import asyncio
from typing import Any

from project_x_py import (
    EventType,
    OrderLifecycleError,
    OrderTracker,
    TradingSuite,
    get_template,
)


async def demonstrate_order_tracker() -> None:
    """Show basic OrderTracker functionality."""

    async with await TradingSuite.create("MNQ") as suite:
        print("=== OrderTracker Demo ===\n")

        # Get current price
        price = await suite["MNQ"].data.get_current_price()
        if price is None:
            print("No price data available")
            return

        print(f"Current price: ${price:,.2f}")
        print(f"Using contract: {suite['MNQ'].instrument_info.id}\n")

        # 1. Basic order tracking with automatic fill detection
        print("1. Basic Order Tracking:")
        tracker_instance: OrderTracker = suite.track_order()
        async with tracker_instance as tracker:
            # Place a limit order below market
            assert suite["MNQ"].instrument_info.id is not None
            order = await suite["MNQ"].orders.place_limit_order(
                contract_id=suite["MNQ"].instrument_info.id,
                side=0,  # BUY
                size=1,
                limit_price=price - 50,  # 50 points below market
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
        tracker2_instance: OrderTracker = suite.track_order()
        async with tracker2_instance as tracker2:
            # Place a marketable limit order
            assert suite["MNQ"].instrument_info.id is not None
            order = await suite["MNQ"].orders.place_limit_order(
                contract_id=suite["MNQ"].instrument_info.id,
                side=1,  # SELL
                size=1,
                limit_price=price + 10,  # Slightly above market for quick fill
            )

            if order.success:
                tracker2.track(order)
                print(f"Placed SELL limit order at ${price + 10:,.2f}")

                try:
                    # Wait for any terminal status
                    print("Waiting for order completion...")
                    _completed = await tracker2.wait_for_status(2, timeout=5)  # FILLED
                    print("✅ Order reached FILLED status")

                except TimeoutError:
                    print("⏱️ Order still pending")

                    # Check current status
                    current = await tracker2.get_current_status()
                    if current:
                        print(f"Current status: {current.status_str}")


async def demonstrate_order_chain() -> None:
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
            print("✅ Bracket order placed successfully:")
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

        current_price = await suite["MNQ"].data.get_current_price()
        if current_price is not None:
            order_chain = (
                suite.order_chain()
                .limit_order(size=1, price=current_price - 10, side=0)
                .with_stop_loss(price=current_price - 30)
                .with_take_profit(price=current_price + 20)
            )

            print("Building order:")
            print(f"   Entry: Limit BUY at ${current_price - 10:,.2f}")
            print(f"   Stop: ${current_price - 30:,.2f}")
            print(f"   Target: ${current_price + 20:,.2f}")

            result = await order_chain.execute()
            print(f"Result: {'✅ Success' if result.success else '❌ Failed'}")


async def demonstrate_order_templates() -> None:
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
                print("✅ 2:1 R/R order placed:")
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
                print("✅ ATR-based order placed:")
                print("   Stop distance based on 2x ATR")
                print("   Target distance based on 3x ATR")
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
                print("✅ Scalp order placed:")
                print("   4 tick stop, 8 tick target")
                print("   Entry: Market order")
                print(f"   Stop: ${result.stop_loss_price:,.2f}")
                print(f"   Target: ${result.take_profit_price:,.2f}")
            else:
                print(f"❌ Order failed: {result.error_message}")

        except Exception as e:
            print(f"❌ Template error: {e}")


async def demonstrate_advanced_tracking() -> None:
    """Show advanced order tracking scenarios."""

    async with await TradingSuite.create("MNQ") as suite:
        print("\n=== Advanced Order Tracking ===\n")

        # Track multiple orders
        print("1. Tracking Multiple Orders:")

        trackers: list[Any] = []
        order_ids: list[int] = []

        current_price = await suite["MNQ"].data.get_current_price()
        if current_price is None:
            return

        # Place multiple orders
        for i in range(3):
            tracker = suite.track_order()

            assert suite["MNQ"].instrument_info.id is not None
            order = await suite["MNQ"].orders.place_limit_order(
                contract_id=suite["MNQ"].instrument_info.id,
                side=0,  # BUY
                size=1,
                limit_price=current_price - (10 * (i + 1)),  # Staggered prices
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

        # Create tasks instead of coroutines
        fill_tasks = [
            asyncio.create_task(tracker.wait_for_fill(timeout=5))
            for tracker in trackers
        ]

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

        except TimeoutError:
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

        async def on_order_event(event: Any) -> None:
            events_received.append(event)
            print(
                f"📨 Event: {event.event_type.name} - Order {event.data.get('order_id')}"
            )

        await suite.on(EventType.ORDER_PLACED, on_order_event)
        await suite.on(EventType.ORDER_FILLED, on_order_event)
        await suite.on(EventType.ORDER_CANCELLED, on_order_event)

        # Place and track order
        event_tracker_instance: OrderTracker = suite.track_order()
        async with event_tracker_instance as event_tracker:
            assert suite["MNQ"].instrument_info.id is not None
            order = await suite["MNQ"].orders.place_limit_order(
                contract_id=suite["MNQ"].instrument_info.id,
                side=1,  # SELL
                size=1,
                limit_price=current_price + 100,  # Far from market
            )

            if order.success:
                event_tracker.track(order)
                print(f"Placed order at ${current_price + 100:,.2f}")

                # Give events time to arrive
                await asyncio.sleep(1)

                # Cancel the order
                print("Cancelling order...")
                await suite["MNQ"].orders.cancel_order(order.orderId)

                # Wait a bit for cancel event
                await asyncio.sleep(1)

        print(f"\nReceived {len(events_received)} events")

        # Cleanup event handlers
        await suite.off(EventType.ORDER_PLACED, on_order_event)
        await suite.off(EventType.ORDER_FILLED, on_order_event)
        await suite.off(EventType.ORDER_CANCELLED, on_order_event)


async def cleanup_demo_orders_and_positions() -> None:
    """Clean up any open orders and positions created during the demo."""
    print("\n" + "=" * 50)
    print("=== Demo Cleanup ===")
    print("=" * 50 + "\n")

    async with await TradingSuite.create("MNQ") as suite:
        print("Cleaning up demo orders and positions...\n")

        # 1. Cancel all open orders
        print("1. Checking for open orders...")
        open_orders = await suite["MNQ"].orders.search_open_orders()

        if open_orders:
            print(f"   Found {len(open_orders)} open orders to cancel:")
            for order in open_orders:
                try:
                    success = await suite["MNQ"].orders.cancel_order(order.id)
                    if success:
                        # Get order type and side names safely
                        order_type = (
                            "LIMIT"
                            if order.type == 1
                            else "MARKET"
                            if order.type == 2
                            else "STOP"
                            if order.type == 4
                            else str(order.type)
                        )
                        side = (
                            "BUY"
                            if order.side == 0
                            else "SELL"
                            if order.side == 1
                            else str(order.side)
                        )
                        print(f"   ✅ Cancelled order {order.id} ({order_type} {side})")
                    else:
                        print(f"   ⚠️ Failed to cancel order {order.id}")
                except Exception as e:
                    print(f"   ⚠️ Error cancelling order {order.id}: {e}")
        else:
            print("   No open orders found")

        print()

        # 2. Close all open positions
        print("2. Checking for open positions...")
        positions = await suite["MNQ"].positions.get_all_positions()

        if positions:
            print(f"   Found {len(positions)} open positions to close:")
            for position in positions:
                if position.size != 0:
                    try:
                        # Place a market order to close the position
                        # Position type: 1=LONG, 2=SHORT
                        side = (
                            1 if position.type == 1 else 0
                        )  # SELL if long, BUY if short
                        size = position.size  # size is always positive

                        result = await suite["MNQ"].orders.place_market_order(
                            contract_id=position.contractId, side=side, size=size
                        )

                        if result.success:
                            position_type = (
                                "LONG"
                                if position.type == 1
                                else "SHORT"
                                if position.type == 2
                                else "UNKNOWN"
                            )
                            print(
                                f"   ✅ Closed {position_type} position in {position.contractId} (Size: {position.size})"
                            )
                        else:
                            print(
                                f"   ⚠️ Failed to close position in {position.contractId}: {result.errorMessage}"
                            )
                    except Exception as e:
                        print(
                            f"   ⚠️ Error closing position in {position.contractId}: {e}"
                        )
        else:
            print("   No open positions found")

        print("\n✅ Demo cleanup complete!")


async def main() -> None:
    """Run all demonstrations."""
    _suite = None
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
    finally:
        # Always run cleanup, even if demo fails
        try:
            await cleanup_demo_orders_and_positions()
        except Exception as cleanup_error:
            print(f"\n⚠️ Cleanup error: {cleanup_error}")


if __name__ == "__main__":
    print("ProjectX SDK v3.0.2 - Order Lifecycle Tracking")
    print("=" * 50)
    asyncio.run(main())
