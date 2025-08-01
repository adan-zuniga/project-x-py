#!/usr/bin/env python3
"""
Async Order and Position Tracking Demo

This demo script demonstrates the automatic order cleanup functionality when positions are closed,
using proper async components (AsyncOrderManager, AsyncPositionManager, AsyncRealtimeDataManager).

It creates a bracket order and monitors positions and orders in real-time, showing how the system
automatically cancels remaining orders when a position is closed (either by stop loss, take profit,
or manual closure from the broker).

Features demonstrated:
- Proper async components for all operations
- Automatic order cleanup when positions close
- Non-blocking real-time monitoring with clear status updates
- Proper async cleanup on exit (cancels open orders and closes positions)
- Concurrent operations for improved performance

Usage:
    python examples/async_08_order_and_position_tracking.py

Manual Testing:
    - Let the script create a bracket order
    - From your broker platform, manually close the position or cancel orders
    - Observe how the system automatically handles cleanup
    - Or let the stop loss/take profit trigger naturally

Controls:
    - Ctrl+C to exit (will cleanup all open positions and orders)
"""

import asyncio
import signal
from contextlib import suppress
from datetime import datetime

from project_x_py import ProjectX, create_trading_suite


class AsyncOrderPositionDemo:
    """Async demo class for order and position tracking with automatic cleanup."""

    def __init__(self):
        self.client = None
        self.suite = None
        self.running = False
        self.demo_orders = []  # Track orders created by this demo
        self.shutdown_event = asyncio.Event()

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum, _frame):
            print(f"\n\n🛑 Received signal {signum}. Initiating cleanup...")
            self.running = False
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def create_demo_bracket_order(self) -> bool:
        """Create a bracket order for demonstration asynchronously."""
        try:
            if self.client is None:
                print("❌ No client found")
                return False

            instrument = await self.client.get_instrument("MNQ")
            if not instrument:
                print("❌ MNQ instrument not found")
                return False

            if self.suite is None:
                print("❌ No suite found")
                return False

            current_price = await self.suite["data_manager"].get_current_price()
            if not current_price:
                print("❌ Could not get current price")
                return False

            print("\n📋 Creating Bracket Order:")
            print("   Instrument: MNQ")
            print(f"   Current Price: ${current_price:.2f}")

            # Create bracket with reasonable stop/target distances
            tick_size = instrument.tickSize
            stop_distance = tick_size * 10  # 10 ticks risk
            target_distance = tick_size * 15  # 15 ticks profit (1.5:1 R/R)

            stop_price = current_price - stop_distance
            take_price = current_price + target_distance

            print("   Entry: Market order (Buy)")
            print(f"   Stop Loss: ${stop_price:.2f} (-${stop_distance:.2f})")
            print(f"   Take Profit: ${take_price:.2f} (+${target_distance:.2f})")
            print(f"   Risk/Reward: 1:{target_distance / stop_distance:.1f}")

            # Place bracket order using async order manager
            account_info = self.client.account_info
            if not account_info:
                print("❌ Could not get account information")
                return False

            bracket_response = await self.suite["order_manager"].place_bracket_order(
                contract_id=instrument.id,
                side=0,  # Buy
                size=1,
                entry_price=current_price,
                stop_loss_price=stop_price,
                take_profit_price=take_price,
                entry_type="market",
                account_id=account_info.id,
            )

            if bracket_response and bracket_response.success:
                print("✅ Bracket order created successfully!")
                print(f"   Entry Order ID: {bracket_response.entry_order_id}")
                print(f"   Stop Order ID: {bracket_response.stop_order_id}")
                print(f"   Target Order ID: {bracket_response.target_order_id}")

                # Track these orders for cleanup
                self.demo_orders.extend(
                    [
                        bracket_response.entry_order_id,
                        bracket_response.stop_order_id,
                        bracket_response.target_order_id,
                    ]
                )
                return True
            else:
                error_msg = (
                    bracket_response.error_message
                    if bracket_response
                    else "Unknown error"
                )
                print(f"❌ Failed to create bracket order: {error_msg}")
                return False

        except Exception as e:
            print(f"❌ Error creating bracket order: {e}")
            return False

    async def display_status(self):
        """Display current positions and orders status asynchronously."""
        try:
            if self.suite is None:
                print("❌ No suite found")
                return

            # Fetch data concurrently using async methods
            positions_task = self.suite["position_manager"].get_all_positions()
            orders_task = self.suite["order_manager"].search_open_orders()
            price_task = self.suite["data_manager"].get_current_price()

            positions, orders, current_price = await asyncio.gather(
                positions_task, orders_task, price_task
            )

            print(f"\n📊 Status Update - {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 40)
            print(
                f"💰 Current MNQ Price: ${current_price:.2f}"
                if current_price
                else "💰 Price: Unavailable"
            )
            print(f"📈 Open Positions: {len(positions)}")
            print(f"📋 Open Orders: {len(orders)}")

            # Show position details
            if positions:
                print("\n🏦 Position Details:")
                for pos in positions:
                    direction = (
                        "LONG"
                        if pos.type == 1
                        else "SHORT"
                        if pos.type == 2
                        else "UNKNOWN"
                    )
                    pnl_info = ""
                    if current_price:
                        if pos.type == 1:  # Long
                            unrealized_pnl = (
                                current_price - pos.averagePrice
                            ) * pos.size
                        elif pos.type == 2:  # Short
                            unrealized_pnl = (
                                pos.averagePrice - current_price
                            ) * pos.size
                        else:
                            unrealized_pnl = 0
                        pnl_info = f" | P&L: ${unrealized_pnl:+.2f}"

                    print(
                        f"   • {direction} {pos.size} @ ${pos.averagePrice:.2f}{pnl_info}"
                    )

            # Show order details
            if orders:
                print("\n📝 Order Details:")
                for order in orders:
                    order_type = "UNKNOWN"
                    if hasattr(order, "type"):
                        order_type = order.type
                    side = "BUY" if order.side == 0 else "SELL"

                    # Handle None prices gracefully
                    price_str = "Pending"
                    if hasattr(order, "filledPrice") and order.filledPrice is not None:
                        price_str = f"${order.filledPrice:.2f}"

                    print(
                        f"   • {order_type} {side} {order.size} @ {price_str} (ID: {order.id})"
                    )

            if not positions and not orders:
                print("   📝 No open positions or orders")

        except Exception as e:
            print(f"❌ Error displaying status: {e}")

    async def run_monitoring_loop(self):
        """Main async monitoring loop."""
        print("\n🔍 Starting Real-Time Monitoring")
        print("=" * 40)
        print("📌 Instructions:")
        print("   • Watch for automatic order cleanup when position closes")
        print("   • You can manually close positions from your broker")
        print("   • Orders will be automatically cancelled when position closes")
        print("   • Press Ctrl+C to exit and cleanup everything")
        print()

        self.running = True
        last_status_count = (0, 0)  # (positions, orders)

        try:
            while self.running and not self.shutdown_event.is_set():
                await self.display_status()

                if self.suite is None:
                    print("❌ No suite found")
                    break

                # Check if everything is closed (position was closed and orders cleaned up)
                positions = await self.suite["position_manager"].get_all_positions()
                orders = await self.suite["order_manager"].search_open_orders()
                current_count = (len(positions), len(orders))

                # Detect when positions/orders change
                if current_count != last_status_count:
                    if last_status_count[0] > 0 and len(positions) == 0:
                        print(
                            "\n🎯 POSITION CLOSED! Automatic order cleanup should have triggered."
                        )
                    if (
                        last_status_count[1] > len(orders)
                        and len(orders) < last_status_count[1]
                    ):
                        print(
                            f"📋 {last_status_count[1] - len(orders)} orders automatically cancelled."
                        )
                    last_status_count = current_count

                # If everything is closed, show completion message
                if len(positions) == 0 and len(orders) == 0 and any(last_status_count):
                    print("\n✅ DEMO COMPLETE!")
                    print(
                        "   All positions closed and orders cleaned up automatically."
                    )
                    print(
                        "   The automatic cleanup functionality is working correctly."
                    )
                    print("\n   Press Ctrl+C to exit, or wait for a new setup...")
                    await asyncio.sleep(10)  # Give user time to read
                    break

                # Use wait_for to make the sleep interruptible
                try:
                    await asyncio.wait_for(self.shutdown_event.wait(), timeout=5.0)
                    break  # Shutdown event was set
                except TimeoutError:
                    pass  # Continue monitoring

        except asyncio.CancelledError:
            print("\n🛑 Monitoring cancelled")
            raise
        except Exception as e:
            print(f"❌ Error in monitoring loop: {e}")

    async def cleanup_all_positions_and_orders(self):
        """Clean up all open positions and orders asynchronously before exit."""
        try:
            print("\n🧹 Cleaning up all positions and orders...")

            if self.suite is None:
                print("❌ No suite found")
                return

            # Cancel all open orders
            orders = await self.suite["order_manager"].search_open_orders()
            if orders:
                print(f"📋 Cancelling {len(orders)} open orders...")
                cancel_tasks = []
                for order in orders:
                    cancel_tasks.append(
                        self.suite["order_manager"].cancel_order(order.id)
                    )

                # Wait for all cancellations to complete
                results = await asyncio.gather(*cancel_tasks, return_exceptions=True)
                for order, result in zip(orders, results, strict=False):
                    if isinstance(result, Exception):
                        print(f"   ❌ Error cancelling order {order.id}: {result}")
                    elif result:
                        print(f"   ✅ Cancelled order {order.id}")
                    else:
                        print(f"   ⚠️ Failed to cancel order {order.id}")

            # Close all open positions
            positions = await self.suite["position_manager"].get_all_positions()
            if positions:
                print(f"🏦 Closing {len(positions)} open positions...")
                close_tasks = []
                for position in positions:
                    close_tasks.append(
                        self.suite["position_manager"].close_position_direct(
                            position.contractId
                        )
                    )

                # Wait for all positions to close
                results = await asyncio.gather(*close_tasks, return_exceptions=True)
                for position, result in zip(positions, results, strict=False):
                    if isinstance(result, Exception):
                        print(
                            f"   ❌ Error closing position {position.contractId}: {result}"
                        )
                    elif isinstance(result, dict):
                        if result.get("success", False):
                            print(f"   ✅ Closed position {position.contractId}")
                        else:
                            error_msg = result.get("errorMessage", "Unknown error")
                            print(
                                f"   ⚠️ Failed to close position {position.contractId}: {error_msg}"
                            )
                    else:
                        print(
                            f"   ⚠️ Unexpected result closing position {position.contractId}"
                        )

            print("✅ Cleanup completed")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

    async def run(self, client: ProjectX):
        """Main async demo execution."""
        self.setup_signal_handlers()
        self.client = client

        print("🚀 Async Order and Position Tracking Demo")
        print("=" * 50)
        print("This demo shows automatic order cleanup when positions close.")
        print("You can manually close positions from your broker to test it.\n")

        # Authenticate and get account info
        try:
            await self.client.authenticate()
            account = self.client.account_info
            if not account:
                print("❌ Could not get account information")
                return False
            print(f"✅ Connected to account: {account.name}")
        except Exception as e:
            print(f"❌ Failed to authenticate: {e}")
            return False

        # Create async trading suite
        try:
            print("\n🔧 Setting up async trading suite...")
            jwt_token = self.client.session_token
            self.suite = await create_trading_suite(
                instrument="MNQ",
                project_x=self.client,
                jwt_token=jwt_token,
                account_id=str(account.id),
                timeframes=["5min"],  # Minimal timeframes for demo
            )

            print("✅ Async trading suite created with automatic order cleanup enabled")

        except Exception as e:
            print(f"❌ Failed to create async trading suite: {e}")
            return False

        # Connect real-time client and initialize data feed
        try:
            print("\n📊 Initializing market data...")
            # Connect WebSocket
            await self.suite["realtime_client"].connect()
            print("✅ WebSocket connected")

            # Initialize data manager
            if not await self.suite["data_manager"].initialize(initial_days=1):
                print("❌ Failed to load historical data")
                return False
            print("✅ Historical data loaded")

            # Start real-time feed
            if not await self.suite["data_manager"].start_realtime_feed():
                print("❌ Failed to start realtime feed")
                return False
            print("✅ Real-time feed started")

            print("⏳ Waiting for feed to stabilize...")
            await asyncio.sleep(3)

        except Exception as e:
            print(f"❌ Failed to initialize data feed: {e}")
            return False

        # Create demo bracket order
        if not await self.create_demo_bracket_order():
            print("❌ Failed to create demo order")
            await self.cleanup_all_positions_and_orders()
            return False

        # Run monitoring loop
        with suppress(asyncio.CancelledError):
            await self.run_monitoring_loop()

        # Final cleanup
        await self.cleanup_all_positions_and_orders()

        # Disconnect WebSocket
        if self.suite and self.suite["realtime_client"]:
            await self.suite["realtime_client"].disconnect()

        print("\n👋 Demo completed. Thank you!")
        return True


async def main():
    """Main async entry point."""
    demo = AsyncOrderPositionDemo()
    try:
        async with ProjectX.from_env() as client:
            success = await demo.run(client)
            return 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
