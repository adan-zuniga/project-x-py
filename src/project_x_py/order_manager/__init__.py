"""
Order Manager Module for ProjectX Trading Platform.

This module provides comprehensive order management functionality including:
- Order placement (market, limit, stop, trailing stop)
- Order modification and cancellation
- Bracket order strategies
- Position-based order management
- Real-time order tracking and monitoring
"""

from project_x_py.order_manager.core import OrderManager
from project_x_py.order_manager.types import OrderStats

__all__ = ["OrderManager", "OrderStats"]
