#!/usr/bin/env python3
"""
Order and Position Tracking Demo

This demo script demonstrates the automatic order cleanup functionality when positions are closed.
It creates a bracket order and monitors positions and orders in real-time, showing how the system
automatically cancels remaining orders when a position is closed (either by stop loss, take profit,
or manual closure from the broker).

Features demonstrated:
- Real-time position and order tracking
- Automatic order cleanup when positions close
- Interactive monitoring with clear status updates
- Proper cleanup on exit (cancels open orders and closes positions)

Usage:
    python examples/08_order_and_position_tracking.py

Manual Testing:
    - Let the script create a bracket order
    - From your broker platform, manually close the position or cancel orders
    - Observe how the system automatically handles cleanup
    - Or let the stop loss/take profit trigger naturally

Controls:
    - Ctrl+C to exit (will cleanup all open positions and orders)
"""

import signal
import sys
import time
from datetime import datetime

from project_x_py import ProjectX, create_trading_suite
from project_x_py.order_manager import OrderManager
from project_x_py.position_manager import PositionManager
from project_x_py.realtime_data_manager import ProjectXRealtimeDataManager


class OrderPositionDemo:
    """Demo class for order and position tracking with automatic cleanup."""

    def __init__(self):
        self.client: ProjectX | None = None
        self.data_manager: ProjectXRealtimeDataManager | None = None
        self.order_manager: OrderManager | None = None
        self.position_manager: PositionManager | None = None
        self.running = False
        self.demo_orders = []  # Track orders created by this demo

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, _frame):
        """Handle shutdown signals gracefully."""
        print(f"\n\n🛑 Received signal {signum}. Initiating cleanup...")
        self.running = False
        self.cleanup_all_positions_and_orders()
        sys.exit(0)

    def initialize(self) -> bool:
        """Initialize the trading suite and components."""
        print("🚀 Order and Position Tracking Demo")
        print("=" * 50)
        print("This demo shows automatic order cleanup when positions close.")
        print("You can manually close positions from your broker to test it.\n")

        # Initialize client
        try:
            self.client = ProjectX.from_env()
            if not self.client:
                print("Client not initialized")
            account = self.client.get_account_info()
            if not account:
                print("❌ Could not get account information")
                return False
            print(f"✅ Connected to account: {account.name}")
        except Exception as e:
            print(f"❌ Failed to connect to ProjectX: {e}")
            return False

        # Create trading suite
        try:
            print("\n🔧 Setting up trading suite...")
            jwt_token = self.client.get_session_token()
            trading_suite = create_trading_suite(
                instrument="MNQ",
                project_x=self.client,
                jwt_token=jwt_token,
                account_id=str(account.id),
                timeframes=["5min"],  # Minimal timeframes for demo
            )

            self.data_manager = trading_suite["data_manager"]
            self.order_manager = trading_suite["order_manager"]
            self.position_manager = trading_suite["position_manager"]

            if (
                not self.data_manager
                or not self.order_manager
                or not self.position_manager
            ):
                print("❌ Failed to create trading suite")
                return False

            print("✅ Trading suite created with automatic order cleanup enabled")

        except Exception as e:
            print(f"❌ Failed to create trading suite: {e}")
            return False

        # Initialize data feed
        try:
            print("\n📊 Initializing market data...")
            if not self.data_manager.initialize(initial_days=1):
                print("❌ Failed to load historical data")
                return False
            print("✅ Historical data loaded")

            if not self.data_manager.start_realtime_feed():
                print("❌ Failed to start realtime feed")
                return False
            print("✅ Real-time feed started")

            print("⏳ Waiting for feed to stabilize...")
            time.sleep(3)

        except Exception as e:
            print(f"❌ Failed to initialize data feed: {e}")
            return False

        return True

    def create_demo_bracket_order(self) -> bool:
        """Create a bracket order for demonstration."""
        try:
            if not self.client:
                print("❌ Client not initialized")
                return False

            instrument = self.client.get_instrument("MNQ")
            if not instrument:
                print("❌ MNQ instrument not found")
                return False

            if not self.data_manager:
                print("❌ Data manager not initialized")
                return False

            current_price = self.data_manager.get_current_price()
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

            # Place bracket order
            if not self.order_manager:
                print("❌ Order manager not initialized")
                return False

            account_info = self.client.get_account_info()
            if not account_info:
                print("❌ Could not get account information")
                return False

            bracket_response = self.order_manager.place_bracket_order(
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

    def display_status(self):
        """Display current positions and orders status."""
        try:
            if (
                not self.position_manager
                or not self.order_manager
                or not self.data_manager
            ):
                print("❌ Components not initialized")
                return

            positions = self.position_manager.get_all_positions()
            orders = self.order_manager.search_open_orders()
            current_price = self.data_manager.get_current_price()

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

    def run_monitoring_loop(self):
        """Main monitoring loop."""
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
            while self.running:
                self.display_status()
                if not self.position_manager or not self.order_manager:
                    print("❌ Components not initialized")
                    break

                # Check if everything is closed (position was closed and orders cleaned up)
                positions = self.position_manager.get_all_positions()
                orders = self.order_manager.search_open_orders()
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
                    time.sleep(10)  # Give user time to read
                    break

                time.sleep(5)  # Update every 5 seconds

        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Error in monitoring loop: {e}")

    def cleanup_all_positions_and_orders(self):
        """Clean up all open positions and orders before exit."""
        if not self.order_manager or not self.position_manager:
            return

        try:
            print("\n🧹 Cleaning up all positions and orders...")

            # Cancel all open orders
            orders = self.order_manager.search_open_orders()
            if orders:
                print(f"📋 Cancelling {len(orders)} open orders...")
                for order in orders:
                    try:
                        if self.order_manager.cancel_order(order.id):
                            print(f"   ✅ Cancelled order {order.id}")
                        else:
                            print(f"   ⚠️ Failed to cancel order {order.id}")
                    except Exception as e:
                        print(f"   ❌ Error cancelling order {order.id}: {e}")

            # Close all open positions
            positions = self.position_manager.get_all_positions()
            if positions:
                print(f"🏦 Closing {len(positions)} open positions...")
                for position in positions:
                    try:
                        result = self.position_manager.close_position_direct(
                            position.contractId
                        )
                        if result.get("success", False):
                            print(f"   ✅ Closed position {position.contractId}")
                        else:
                            error_msg = result.get("errorMessage", "Unknown error")
                            print(
                                f"   ⚠️ Failed to close position {position.contractId}: {error_msg}"
                            )
                    except Exception as e:
                        print(
                            f"   ❌ Error closing position {position.contractId}: {e}"
                        )

            print("✅ Cleanup completed")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

    def run(self):
        """Main demo execution."""
        self.setup_signal_handlers()

        # Initialize everything
        if not self.initialize():
            print("❌ Initialization failed")
            return False

        # Create demo bracket order
        if not self.create_demo_bracket_order():
            print("❌ Failed to create demo order")
            self.cleanup_all_positions_and_orders()
            return False

        # Run monitoring loop
        self.run_monitoring_loop()

        # Final cleanup
        self.cleanup_all_positions_and_orders()

        print("\n👋 Demo completed. Thank you!")
        return True


def main():
    """Main entry point."""
    demo = OrderPositionDemo()
    success = demo.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
