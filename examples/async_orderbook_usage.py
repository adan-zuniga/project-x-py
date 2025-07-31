"""
Example demonstrating AsyncOrderBook usage for market depth analysis.

This example shows how to use the AsyncOrderBook for:
- Real-time Level 2 market depth processing
- Trade flow analysis
- Iceberg order detection
- Market microstructure analytics
"""

import asyncio
from datetime import datetime

from project_x_py import AsyncOrderBook, AsyncProjectX
from project_x_py.async_realtime import AsyncProjectXRealtimeClient


async def on_depth_update(data):
    """Callback for market depth updates."""
    print(f"📊 Market depth updated - Update #{data['update_count']}")


async def main():
    """Main async function demonstrating orderbook analysis."""
    # Create async client
    async with AsyncProjectX.from_env() as client:
        # Authenticate
        await client.authenticate()
        print(f"✅ Authenticated as {client.account_info.name}")

        # Get JWT token for real-time connection
        jwt_token = client.session_token
        account_id = client.account_info.id

        # Create async realtime client (placeholder for now)
        realtime_client = AsyncProjectXRealtimeClient(jwt_token, account_id)

        # Create async orderbook
        orderbook = AsyncOrderBook(
            instrument="MGC",
            client=client,
        )

        # Initialize with real-time capabilities
        if await orderbook.initialize(realtime_client):
            print("✅ AsyncOrderBook initialized with real-time data")
        else:
            print("❌ Failed to initialize orderbook")
            return

        # Register callback for depth updates
        await orderbook.add_callback("market_depth_processed", on_depth_update)

        # Simulate some market depth data for demonstration
        print("\n📈 Simulating Market Depth Updates...")

        # Simulate initial orderbook state
        depth_data = {
            "contract_id": "MGC-H25",
            "data": [
                # Bids
                {"price": 2044.0, "volume": 25, "type": 2},
                {"price": 2044.5, "volume": 50, "type": 2},
                {"price": 2045.0, "volume": 100, "type": 2},
                {"price": 2045.5, "volume": 75, "type": 2},
                {"price": 2046.0, "volume": 30, "type": 2},
                # Asks
                {"price": 2046.5, "volume": 35, "type": 1},
                {"price": 2047.0, "volume": 80, "type": 1},
                {"price": 2047.5, "volume": 110, "type": 1},
                {"price": 2048.0, "volume": 60, "type": 1},
                {"price": 2048.5, "volume": 40, "type": 1},
            ],
        }
        await orderbook.process_market_depth(depth_data)

        # Get orderbook snapshot
        print("\n📸 Orderbook Snapshot:")
        snapshot = await orderbook.get_orderbook_snapshot(levels=5)
        print(f"  Best Bid: ${snapshot['best_bid']:.2f}")
        print(f"  Best Ask: ${snapshot['best_ask']:.2f}")
        print(f"  Spread: ${snapshot['spread']:.2f}")
        print(f"  Mid Price: ${snapshot['mid_price']:.2f}")

        print("\n  Top 5 Bids:")
        for bid in snapshot["bids"]:
            print(f"    ${bid['price']:.2f} x {bid['volume']}")

        print("\n  Top 5 Asks:")
        for ask in snapshot["asks"]:
            print(f"    ${ask['price']:.2f} x {ask['volume']}")

        # Simulate some trades
        print("\n💹 Simulating Trade Execution...")
        trade_data = {
            "contract_id": "MGC-H25",
            "data": [
                {"price": 2046.2, "volume": 15, "type": 5},  # Trade
                {"price": 2046.3, "volume": 10, "type": 5},  # Trade
                {"price": 2046.1, "volume": 20, "type": 5},  # Trade
            ],
        }
        await orderbook.process_market_depth(trade_data)
        print("  3 trades executed")

        # Simulate iceberg order behavior
        print("\n🧊 Simulating Iceberg Order Behavior...")
        # Simulate consistent volume refreshes at same price level
        for i in range(10):
            refresh_data = {
                "contract_id": "MGC-H25",
                "data": [
                    {
                        "price": 2045.0,
                        "volume": 95 + (i % 10),
                        "type": 2,
                    },  # Bid refresh
                ],
            }
            await orderbook.process_market_depth(refresh_data)
            # Track the refresh in history (normally done internally)
            orderbook.price_level_history[(2045.0, "bid")].append(
                {"volume": 95 + (i % 10), "timestamp": datetime.now(orderbook.timezone)}
            )

        # Detect iceberg orders
        print("\n🔍 Detecting Iceberg Orders...")
        icebergs = await orderbook.detect_iceberg_orders(
            min_refreshes=5, volume_threshold=50, time_window_minutes=30
        )

        if icebergs["iceberg_levels"]:
            print(
                f"  Found {len(icebergs['iceberg_levels'])} potential iceberg orders:"
            )
            for iceberg in icebergs["iceberg_levels"]:
                print(f"    Price: ${iceberg['price']:.2f} ({iceberg['side']})")
                print(f"    Avg Volume: {iceberg['avg_volume']:.0f}")
                print(f"    Refresh Count: {iceberg['refresh_count']}")
                print(f"    Confidence: {iceberg['confidence']:.1%}")
                print()
        else:
            print("  No iceberg orders detected")

        # Get memory statistics
        print("\n💾 Memory Statistics:")
        stats = orderbook.get_memory_stats()
        print(f"  Bid Levels: {stats['total_bid_levels']}")
        print(f"  Ask Levels: {stats['total_ask_levels']}")
        print(f"  Total Trades: {stats['total_trades']}")
        print(f"  Update Count: {stats['update_count']}")

        # Example of real-time integration
        print("\n🔄 Real-time Integration:")
        print("  In production, the orderbook would automatically receive:")
        print("  - Market depth updates via WebSocket")
        print("  - Trade executions in real-time")
        print("  - Quote updates for best bid/ask")
        print("  - All processed asynchronously with callbacks")

        # Advanced analytics example
        print("\n📊 Advanced Analytics Available:")
        print("  - Market imbalance detection")
        print("  - Support/resistance level identification")
        print("  - Liquidity distribution analysis")
        print("  - Market maker detection")
        print("  - Volume profile analysis")
        print("  - Trade flow toxicity metrics")

        # Clean up
        await orderbook.cleanup()
        print("\n✅ AsyncOrderBook cleanup completed")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
