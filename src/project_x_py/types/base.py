"""
Core type definitions used across the ProjectX SDK.

This module contains fundamental types that are used throughout the SDK,
including enums, type aliases, and basic data structures.
"""

from collections.abc import Callable, Coroutine
from typing import Any

# Type aliases for callbacks
AsyncCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
SyncCallback = Callable[[dict[str, Any]], None]
CallbackType = AsyncCallback | SyncCallback

# Common constants
DEFAULT_TIMEZONE = "America/Chicago"
TICK_SIZE_PRECISION = 8  # Decimal places for tick size rounding

# Common type aliases
ContractId = str
AccountId = str
OrderId = str
PositionId = str

__all__ = [
    "DEFAULT_TIMEZONE",
    "TICK_SIZE_PRECISION",
    "AccountId",
    "AsyncCallback",
    "CallbackType",
    "ContractId",
    "OrderId",
    "PositionId",
    "SyncCallback",
]
