"""
Async order management for ProjectX trading.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    This package provides the async OrderManager system for ProjectX, offering robust,
    extensible order placement, modification, cancellation, tracking, and advanced
    bracket/position management. Integrates with both API and real-time clients for
    seamless trading workflows.

Key Features:
    - Unified async order placement (market, limit, stop, trailing, bracket)
    - Modification/cancellation with tick-size alignment
    - Position-based order and risk management
    - Real-time tracking, event-driven callbacks, and statistics
    - Modular design for strategy and bot development
    - Thread-safe operations with async locks
    - Automatic price alignment to instrument tick sizes
    - Comprehensive order lifecycle management

Order Types Supported:
    - Market Orders: Immediate execution at current market price
    - Limit Orders: Execution at specified price or better
    - Stop Orders: Market orders triggered at stop price
    - Trailing Stop Orders: Dynamic stops that follow price movement
    - Bracket Orders: Entry + stop loss + take profit combinations

Real-time Capabilities:
    - WebSocket-based order status tracking
    - Immediate fill/cancellation detection
    - Event-driven callbacks for custom logic
    - Local caching to reduce API calls

Example Usage:
    ```python
    # V3: Async order management with event bus integration
    import asyncio
    from project_x_py import (
        ProjectX,
        create_realtime_client,
        create_order_manager,
        EventBus,
    )


    async def main():
        async with ProjectX.from_env() as client:
            await client.authenticate()

            # V3: Create event bus and realtime client
            event_bus = EventBus()
            realtime_client = await create_realtime_client(
                client.get_session_token(), str(client.get_account_info().id)
            )

            # V3: Create order manager with dependencies
            om = create_order_manager(client, realtime_client, event_bus)
            await om.initialize(realtime_client)

            # V3: Place a market order
            response = await om.place_market_order(
                "MNQ",
                side=0,
                size=1,  # Buy 1 contract
            )
            print(f"Market order placed: {response.orderId}")

            # V3: Place a bracket order with automatic risk management
            bracket = await om.place_bracket_order(
                contract_id="MGC",
                side=0,  # Buy
                size=1,
                entry_price=2050.0,
                stop_loss_price=2040.0,
                take_profit_price=2070.0,
            )
            print(f"Bracket order IDs:")
            print(f"  Entry: {bracket.entry_order_id}")
            print(f"  Stop: {bracket.stop_order_id}")
            print(f"  Target: {bracket.target_order_id}")

            # V3: Add stop loss to existing position
            await om.add_stop_loss_to_position("MGC", stop_price=2040.0)

            # V3: Check order statistics
            stats = await om.get_order_statistics()
            print(f"Orders placed: {stats['orders_placed']}")
            print(f"Fill rate: {stats['fill_rate']:.1%}")


    asyncio.run(main())
    ```

See Also:
    - `order_manager.core.OrderManager`
    - `order_manager.bracket_orders`
    - `order_manager.order_types`
    - `order_manager.position_orders`
    - `order_manager.tracking`
    - `order_manager.utils`
"""

from project_x_py.order_manager.core import OrderManager

__all__ = ["OrderManager"]
