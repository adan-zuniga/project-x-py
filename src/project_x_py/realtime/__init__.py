"""
Real-time client module for ProjectX Gateway API WebSocket connections.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides the ProjectXRealtimeClient class for managing real-time connections
    to ProjectX SignalR hubs. Enables WebSocket-based streaming of market data,
    position updates, order events, and account information with full async/await
    support and automatic reconnection capabilities.

Key Features:
    - Dual-hub SignalR connections (User Hub + Market Hub)
    - Async/await support for all operations
    - Automatic reconnection with exponential backoff
    - JWT token authentication and refresh handling
    - Event-driven callback system for custom processing
    - Thread-safe operations with proper error handling
    - Connection health monitoring and statistics

Real-time Capabilities:
    - User Hub: Account, position, order, and trade events
    - Market Hub: Quote, trade, and market depth data
    - Event forwarding to registered managers
    - Subscription management for specific contracts
    - Connection health monitoring and statistics

Note:
    While this module provides direct access to the real-time client, for most
    trading applications, it is recommended to use the `TradingSuite`. The suite
    manages the real-time client, data processing, and event handling automatically,
    offering a simpler and more robust development experience.

Example Usage:
    The example below demonstrates the low-level usage of the `ProjectXRealtimeClient`.

    ```python
    # V3: Real-time WebSocket client with async callbacks
    import asyncio
    from project_x_py import ProjectX, create_realtime_client


    async def main():
        async with ProjectX.from_env() as client:
            await client.authenticate()

            # V3: Create real-time client with factory function
            realtime_client = await create_realtime_client(
                jwt_token=client.get_session_token(),
                account_id=str(client.get_account_info().id),
            )

            # V3: Register async callbacks for event handling
            async def on_position_update(data):
                print(f"Position update: {data}")
                # V3: Position data includes actual fields
                if "netPos" in data:
                    print(f"  Net Position: {data['netPos']}")
                    print(f"  Unrealized P&L: ${data.get('unrealizedPnl', 0):.2f}")

            async def on_quote_update(data):
                # V3: Handle ProjectX quote format
                if isinstance(data, dict) and "contractId" in data:
                    contract = data["contractId"]
                    bid = data.get("bid", 0)
                    ask = data.get("ask", 0)
                    print(f"{contract}: {bid} x {ask}")

            # V3: Add callbacks for various event types
            await realtime_client.add_callback("position_update", on_position_update)
            await realtime_client.add_callback("quote_update", on_quote_update)

            # V3: Connect and subscribe to data streams
            if await realtime_client.connect():
                print(f"User Hub connected: {realtime_client.user_connected}")
                print(f"Market Hub connected: {realtime_client.market_connected}")

                # V3: Subscribe to user events (positions, orders, trades)
                await realtime_client.subscribe_user_updates()

                # V3: Subscribe to market data for specific contracts
                await realtime_client.subscribe_market_data(["MGC", "MNQ"])

                # V3: Process events for 60 seconds
                await asyncio.sleep(60)

                # V3: Clean up connections
                await realtime_client.disconnect()


    asyncio.run(main())
    ```

See Also:
    - `realtime.core.ProjectXRealtimeClient`
    - `realtime.connection_management.ConnectionManagementMixin`
    - `realtime.event_handling.EventHandlingMixin`
    - `realtime.subscriptions.SubscriptionsMixin`
"""

from project_x_py.realtime.core import ProjectXRealtimeClient

__all__ = ["ProjectXRealtimeClient"]
