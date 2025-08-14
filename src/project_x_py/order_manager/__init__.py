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
    # V3.1: Order management with TradingSuite
    import asyncio
    from project_x_py import TradingSuite


    async def main():
        # Create suite with all managers integrated
        suite = await TradingSuite.create("MNQ")

        # V3.1: Place a market order using integrated order manager
        response = await suite.orders.place_market_order(
            contract_id=suite.instrument_id,
            side=0,  # Buy
            size=1,  # 1 contract
        )
        print(f"Market order placed: {response.orderId}")

        # V3.1: Place a bracket order with automatic risk management
        # Get current price for realistic entry
        current_price = await suite.data.get_current_price()

        bracket = await suite.orders.place_bracket_order(
            contract_id=suite.instrument_id,
            side=0,  # Buy
            size=1,
            entry_price=current_price - 10.0,  # Limit entry below market
            stop_loss_price=current_price - 25.0,  # Stop loss $25 below entry
            take_profit_price=current_price + 25.0,  # Take profit $25 above entry
        )
        print(f"Bracket order IDs:")
        print(f"  Entry: {bracket.entry_order_id}")
        print(f"  Stop: {bracket.stop_order_id}")
        print(f"  Target: {bracket.target_order_id}")

        # V3.1: Add stop loss to existing position
        await suite.orders.add_stop_loss_to_position(
            suite.instrument_id, stop_price=current_price - 20.0
        )

        # V3.1: Check order statistics
        stats = await suite.orders.get_order_statistics()
        print(f"Orders placed: {stats['orders_placed']}")
        print(f"Fill rate: {stats['fill_rate']:.1%}")

        await suite.disconnect()


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
