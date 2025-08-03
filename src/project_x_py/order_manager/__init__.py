"""
Async order management for ProjectX trading.

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

Example Usage:
    ```python
    from project_x_py import ProjectX
    from project_x_py.order_manager import OrderManager

    async with ProjectX.from_env() as client:
        om = OrderManager(client)
        await om.place_market_order("MNQ", 0, 1)  # Buy 1 contract at market
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
from project_x_py.types import OrderStats

__all__ = ["OrderManager", "OrderStats"]
