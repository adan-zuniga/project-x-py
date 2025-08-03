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

Example Usage:
    ```python
    from project_x_py import ProjectX
    from project_x_py.realtime import ProjectXRealtimeClient

    async with ProjectX.from_env() as client:
        await client.authenticate()

        # Create real-time client
        realtime_client = ProjectXRealtimeClient(
            jwt_token=client.session_token, account_id=client.account_info.id
        )

        # Register callbacks for event handling
        async def on_position_update(data):
            print(f"Position update: {data}")

        async def on_quote_update(data):
            contract = data["contract_id"]
            quote = data["data"]
            print(f"{contract}: {quote['bid']} x {quote['ask']}")

        await realtime_client.add_callback("position_update", on_position_update)
        await realtime_client.add_callback("quote_update", on_quote_update)

        # Connect and subscribe
        if await realtime_client.connect():
            await realtime_client.subscribe_user_updates()
            await realtime_client.subscribe_market_data(["MGC", "NQ"])

            # Process events...
            await asyncio.sleep(60)

            await realtime_client.cleanup()
    ```

See Also:
    - `realtime.core.ProjectXRealtimeClient`
    - `realtime.connection_management.ConnectionManagementMixin`
    - `realtime.event_handling.EventHandlingMixin`
    - `realtime.subscriptions.SubscriptionsMixin`
"""

from project_x_py.realtime.core import ProjectXRealtimeClient

__all__ = ["ProjectXRealtimeClient"]
