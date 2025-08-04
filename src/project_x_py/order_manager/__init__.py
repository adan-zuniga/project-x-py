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
    from project_x_py import ProjectX
    from project_x_py.order_manager import OrderManager

    async with ProjectX.from_env() as client:
        om = OrderManager(client)

        # Place a market order
        response = await om.place_market_order("MNQ", 0, 1)  # Buy 1 contract

        # Place a bracket order with stop loss and take profit
        bracket = await om.place_bracket_order(
            contract_id="MGC",
            side=0,
            size=1,
            entry_price=2050.0,
            stop_loss_price=2040.0,
            take_profit_price=2070.0,
        )

        # Add stop loss to existing position
        await om.add_stop_loss("MGC", stop_price=2040.0)
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
