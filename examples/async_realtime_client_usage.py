"""
Example demonstrating AsyncProjectXRealtimeClient usage for WebSocket connections.

This example shows how to use the AsyncProjectXRealtimeClient for:
- Connecting to ProjectX Gateway SignalR hubs
- Subscribing to user updates (positions, orders, trades)
- Subscribing to market data (quotes, trades, depth)
- Handling real-time events with async callbacks
"""

import asyncio
import json
from datetime import datetime

from project_x_py import AsyncProjectX
from project_x_py.async_realtime import AsyncProjectXRealtimeClient


# Event handlers
async def on_account_update(data):
    """Handle account balance and status updates."""
    print(f"\n💰 Account Update at {datetime.now()}")
    print(json.dumps(data, indent=2))


async def on_position_update(data):
    """Handle position updates."""
    print(f"\n📊 Position Update at {datetime.now()}")
    print(f"  Contract: {data.get('contractId', 'Unknown')}")
    print(f"  Quantity: {data.get('quantity', 0)}")
    print(f"  Avg Price: {data.get('averagePrice', 0)}")
    print(f"  P&L: ${data.get('unrealizedPnl', 0):.2f}")


async def on_order_update(data):
    """Handle order updates."""
    print(f"\n📋 Order Update at {datetime.now()}")
    print(f"  Order ID: {data.get('orderId', 'Unknown')}")
    print(f"  Status: {data.get('status', 'Unknown')}")
    print(f"  Filled: {data.get('filledQuantity', 0)}/{data.get('quantity', 0)}")


async def on_trade_execution(data):
    """Handle trade executions."""
    print(f"\n💹 Trade Execution at {datetime.now()}")
    print(f"  Order ID: {data.get('orderId', 'Unknown')}")
    print(f"  Price: ${data.get('price', 0):.2f}")
    print(f"  Quantity: {data.get('quantity', 0)}")


async def on_quote_update(data):
    """Handle real-time quote updates."""
    contract_id = data.get("contractId", "Unknown")
    bid = data.get("bidPrice", 0)
    ask = data.get("askPrice", 0)
    spread = ask - bid if bid and ask else 0

    print(
        f"\r💱 {contract_id}: Bid ${bid:.2f} | Ask ${ask:.2f} | Spread ${spread:.2f}",
        end="",
        flush=True,
    )


async def on_market_trade(data):
    """Handle market trade updates."""
    print(f"\n🔄 Market Trade at {datetime.now()}")
    print(f"  Contract: {data.get('contractId', 'Unknown')}")
    print(f"  Price: ${data.get('price', 0):.2f}")
    print(f"  Size: {data.get('size', 0)}")


async def on_market_depth(data):
    """Handle market depth updates."""
    contract_id = data.get("contractId", "Unknown")
    depth_entries = data.get("data", [])

    bids = [e for e in depth_entries if e.get("type") == 2]  # Type 2 = Bid
    asks = [e for e in depth_entries if e.get("type") == 1]  # Type 1 = Ask

    if bids or asks:
        print(f"\n📊 Market Depth Update for {contract_id}")
        print(f"  Bid Levels: {len(bids)}")
        print(f"  Ask Levels: {len(asks)}")


async def main():
    """Main async function demonstrating real-time WebSocket usage."""
    # Create async client
    async with AsyncProjectX.from_env() as client:
        # Authenticate
        await client.authenticate()
        print(f"✅ Authenticated as {client.account_info.name}")

        # Get JWT token and account ID
        jwt_token = client.session_token
        account_id = client.account_info.id

        # Create async realtime client
        realtime_client = AsyncProjectXRealtimeClient(
            jwt_token=jwt_token,
            account_id=account_id,
        )

        # Register event callbacks
        print("\n📡 Registering event callbacks...")
        await realtime_client.add_callback("account_update", on_account_update)
        await realtime_client.add_callback("position_update", on_position_update)
        await realtime_client.add_callback("order_update", on_order_update)
        await realtime_client.add_callback("trade_execution", on_trade_execution)
        await realtime_client.add_callback("quote_update", on_quote_update)
        await realtime_client.add_callback("market_trade", on_market_trade)
        await realtime_client.add_callback("market_depth", on_market_depth)

        # Connect to SignalR hubs
        print("\n🔌 Connecting to ProjectX Gateway...")
        if await realtime_client.connect():
            print("✅ Connected to real-time services")
        else:
            print("❌ Failed to connect")
            return

        # Subscribe to user updates
        print("\n👤 Subscribing to user updates...")
        if await realtime_client.subscribe_user_updates():
            print("✅ Subscribed to account, position, and order updates")
        else:
            print("❌ Failed to subscribe to user updates")

        # Get a contract to subscribe to
        print("\n🔍 Finding available contracts...")
        instruments = await client.search_instruments("MGC")
        if instruments:
            # Get the active contract ID
            active_contract = instruments[0].activeContract
            print(f"✅ Found active contract: {active_contract}")

            # Subscribe to market data
            print(f"\n📊 Subscribing to market data for {active_contract}...")
            if await realtime_client.subscribe_market_data([active_contract]):
                print("✅ Subscribed to quotes, trades, and depth")
            else:
                print("❌ Failed to subscribe to market data")
        else:
            print("❌ No instruments found")

        # Display connection stats
        print("\n📈 Connection Statistics:")
        stats = realtime_client.get_stats()
        print(f"  User Hub Connected: {stats['user_connected']}")
        print(f"  Market Hub Connected: {stats['market_connected']}")
        print(f"  Subscribed Contracts: {stats['subscribed_contracts']}")

        # Run for a while to receive events
        print("\n⏰ Listening for real-time events for 60 seconds...")
        print("   (In production, events would trigger your trading logic)")

        try:
            # Keep the connection alive
            await asyncio.sleep(60)

            # Show final stats
            final_stats = realtime_client.get_stats()
            print("\n📊 Final Statistics:")
            print(f"  Events Received: {final_stats['events_received']}")
            print(f"  Connection Errors: {final_stats['connection_errors']}")

        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user")

        # Unsubscribe and cleanup
        print("\n🧹 Cleaning up...")
        if instruments and active_contract:
            await realtime_client.unsubscribe_market_data([active_contract])

        await realtime_client.cleanup()
        print("✅ Cleanup completed")

        # Example of JWT token refresh (in production)
        print("\n🔑 JWT Token Refresh Example:")
        print("  In production, you would:")
        print("  1. Monitor token expiration")
        print("  2. Get new token from ProjectX API")
        print("  3. Call: await realtime_client.update_jwt_token(new_token)")
        print("  4. Client automatically reconnects and resubscribes")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
