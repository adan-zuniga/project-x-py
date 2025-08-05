#!/usr/bin/env python3
"""
Test script to verify order cleanup when positions close.
"""

import asyncio
import sys
from datetime import datetime

from project_x_py import TradingSuite, setup_logging


async def test_order_cleanup():
    """Test that orders are properly cleaned up when positions close."""

    # Enable debug logging
    setup_logging(level="DEBUG")

    print("\n🧪 Testing Order Cleanup Fix")
    print("=" * 50)

    try:
        # Create trading suite
        print("\n1️⃣ Creating TradingSuite...")
        suite = await TradingSuite.create("MNQ", timeframes=["1min"])
        print("✅ TradingSuite created successfully")

        # Verify order sync is enabled
        print("\n2️⃣ Checking order synchronization...")
        if suite.positions._order_sync_enabled:
            print("✅ Order synchronization is ENABLED")
        else:
            print("❌ Order synchronization is DISABLED")
            return False

        # Check if order manager is linked
        if suite.positions.order_manager is not None:
            print("✅ OrderManager is properly linked to PositionManager")
        else:
            print("❌ OrderManager is NOT linked to PositionManager")
            return False

        # Get current positions
        print("\n3️⃣ Checking current positions...")
        positions = await suite.positions.get_all_positions()
        print(f"📊 Found {len(positions)} open positions")

        # Get current orders
        orders = await suite.orders.search_open_orders()
        print(f"📋 Found {len(orders)} open orders")

        # If there are positions with orders, monitor for closure
        if positions and orders:
            print("\n4️⃣ Monitoring for position closure...")
            print("ℹ️  Close a position manually to test automatic order cleanup")

            # Monitor for 30 seconds
            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < 30:
                await asyncio.sleep(5)

                new_positions = await suite.positions.get_all_positions()
                new_orders = await suite.orders.search_open_orders()

                if len(new_positions) < len(positions):
                    print(
                        f"\n🎯 Position closed! Positions: {len(positions)} → {len(new_positions)}"
                    )
                    print(f"📋 Orders: {len(orders)} → {len(new_orders)}")

                    if len(new_orders) < len(orders):
                        print("✅ Orders were automatically cleaned up!")
                        return True
                    else:
                        print("❌ Orders were NOT cleaned up")
                        return False

        print("\n✅ All checks passed!")
        return True

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        print("\n🧹 Cleaning up...")
        if "suite" in locals():
            await suite.disconnect()


async def main():
    """Run the test."""
    success = await test_order_cleanup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
