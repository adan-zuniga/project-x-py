"""
Example demonstrating integrated async trading suite with shared ProjectXRealtimeClient.

This example shows how multiple async managers can share a single real-time WebSocket
connection, ensuring efficient resource usage and coordinated event handling.
"""

import asyncio
from datetime import datetime

from project_x_py import (
    OrderBook,
    OrderManager,
    PositionManager,
    ProjectX,
    ProjectXRealtimeClient,
    RealtimeDataManager,
)


# Shared event handler to show all events
async def log_event(event_type: str, data: dict):
    """Log all events to show integration working."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[{timestamp}] 📡 {event_type}:")
    if isinstance(data, dict):
        for key, value in data.items():
            if key != "data":  # Skip nested data for brevity
                print(f"  {key}: {value}")
    else:
        print(f"  {data}")


async def main():
    """Main async function demonstrating integrated trading suite."""
    # Create async client
    async with ProjectX.from_env() as client:
        # Authenticate
        await client.authenticate()
        if client.account_info is None:
            print("❌ No account info found")
            return
        print(f"✅ Authenticated as {client.account_info.name}")

        # Get JWT token and account ID
        jwt_token = client.session_token
        account_id = str(client.account_info.id)

        # Create single async realtime client (shared across all managers)
        realtime_client = ProjectXRealtimeClient(
            jwt_token=jwt_token,
            account_id=account_id,
        )

        # Register general event logging
        await realtime_client.add_callback(
            "account_update", lambda d: log_event("Account Update", d)
        )
        await realtime_client.add_callback(
            "connection_status", lambda d: log_event("Connection Status", d)
        )

        # Connect to real-time services
        print("\n🔌 Connecting to ProjectX Gateway...")
        if await realtime_client.connect():
            print("✅ Connected to real-time services")
        else:
            print("❌ Failed to connect")
            return

        # Get an instrument for testing
        print("\n🔍 Finding active instruments...")
        instruments = await client.search_instruments("MGC")
        if not instruments:
            print("❌ No instruments found")
            return

        instrument = instruments[0]
        active_contract = instrument.activeContract
        print(f"✅ Using instrument: {instrument.symbolId} ({active_contract})")

        # Create managers with shared realtime client
        print("\n🏗️ Creating async managers with shared realtime client...")

        # 1. Position Manager
        position_manager = PositionManager(client)
        await position_manager.initialize(realtime_client=realtime_client)
        print("  ✅ Position Manager initialized")

        # 2. Order Manager
        order_manager = OrderManager(client)
        await order_manager.initialize(realtime_client=realtime_client)
        print("  ✅ Order Manager initialized")

        # 3. Realtime Data Manager
        data_manager = RealtimeDataManager(
            instrument=instrument.id,
            project_x=client,
            realtime_client=realtime_client,
            timeframes=["5sec", "1min", "5min"],
        )
        await data_manager.initialize(initial_days=1)
        print("  ✅ Realtime Data Manager initialized")

        # 4. OrderBook
        orderbook = OrderBook(
            instrument=instrument.id,
            project_x=client,
        )
        await orderbook.initialize(realtime_client=realtime_client)
        print("  ✅ OrderBook initialized")

        # Subscribe to real-time data
        print("\n📊 Subscribing to real-time updates...")
        await realtime_client.subscribe_user_updates()
        await realtime_client.subscribe_market_data([instrument.id])
        await data_manager.start_realtime_feed()
        print("✅ Subscribed to all real-time feeds")

        # Display current state
        print("\n📈 Current Trading State:")

        # Positions
        positions = await position_manager.get_all_positions()
        print(f"\n  Positions: {len(positions)} open")
        for pos in positions:
            print(f"    {pos.contractId}: {pos.size} @ ${pos.averagePrice:.2f}")

        # Orders
        orders = await order_manager.search_open_orders()
        print(f"\n  Orders: {len(orders)} open")
        for order in orders[:3]:  # Show first 3
            print(
                f"    {order.contractId}: {order.side} {order.size} @ ${order.filledPrice:.2f}"
            )

        # Market Data
        for timeframe in ["5sec", "1min", "5min"]:
            data = await data_manager.get_data(timeframe)
            if data is not None and len(data) > 0:
                last_bar = data[-1]
                print(
                    f"\n  {timeframe} OHLCV: O=${last_bar['open']:.2f} H=${last_bar['high']:.2f} L=${last_bar['low']:.2f} C=${last_bar['close']:.2f} V={last_bar['volume']}"
                )

        # OrderBook
        snapshot = await orderbook.get_orderbook_snapshot()
        if snapshot:
            spread = await orderbook.get_bid_ask_spread()
            if spread and isinstance(spread, dict):
                print(
                    f"\n  OrderBook: Bid=${spread.get('bid', 0):.2f} Ask=${spread.get('ask', 0):.2f} Spread=${spread.get('spread', 0):.2f}"
                )
            print(
                f"    Bid Levels: {len(snapshot.get('bids', []))}, Ask Levels: {len(snapshot.get('asks', []))}"
            )

        # Run for a while to show integration
        print("\n⏰ Monitoring real-time events for 30 seconds...")
        print("   All managers are sharing the same WebSocket connection")
        print("   Events flow: WebSocket → Realtime Client → Managers → Your Logic")

        # Track some stats
        start_time = asyncio.get_event_loop().time()
        initial_stats = realtime_client.get_stats()

        try:
            await asyncio.sleep(30)
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user")

        # Show final statistics
        end_time = asyncio.get_event_loop().time()
        final_stats = realtime_client.get_stats()

        print(f"\n📊 Integration Statistics ({end_time - start_time:.1f} seconds):")
        print(
            f"  Events Received: {final_stats['events_received'] - initial_stats['events_received']}"
        )
        print(
            f"  Connection Errors: {final_stats['connection_errors'] - initial_stats['connection_errors']}"
        )
        print("  Managers Sharing Connection: 4 (Position, Order, Data, OrderBook)")

        # Clean up
        print("\n🧹 Cleaning up...")
        await data_manager.stop_realtime_feed()
        await realtime_client.cleanup()
        print("✅ Cleanup completed")

        print("\n🎯 Key Integration Points Demonstrated:")
        print("  1. Single ProjectXRealtimeClient shared by all managers")
        print("  2. Each manager registers its own async callbacks")
        print("  3. Events flow efficiently through one WebSocket connection")
        print("  4. No duplicate subscriptions or connections")
        print("  5. Coordinated cleanup across all components")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
