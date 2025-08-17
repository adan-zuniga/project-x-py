"""
Statistics tracking mixin for consistent error and memory tracking.

Author: SDK v3.1.14
Date: 2025-01-17
"""

import sys
import time
import traceback
from collections import deque
from datetime import datetime
from typing import Any, Optional


class StatsTrackingMixin:
    """
    Mixin for tracking errors, memory usage, and activity across managers.

    Provides consistent error tracking, memory usage monitoring, and activity
    timestamps for all manager components in TradingSuite.
    """

    def _init_stats_tracking(self, max_errors: int = 100) -> None:
        """
        Initialize statistics tracking attributes.

        Args:
            max_errors: Maximum number of errors to retain in history
        """
        self._error_count = 0
        self._error_history: deque[dict[str, Any]] = deque(maxlen=max_errors)
        self._last_activity: Optional[datetime] = None
        self._start_time = time.time()

    def _track_error(
        self,
        error: Exception,
        context: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Track an error occurrence.

        Args:
            error: The exception that occurred
            context: Optional context about where/why the error occurred
            details: Optional additional details about the error
        """
        self._error_count += 1
        self._error_history.append(
            {
                "timestamp": datetime.now(),
                "error_type": type(error).__name__,
                "message": str(error),
                "context": context,
                "details": details,
                "traceback": traceback.format_exc()
                if hasattr(error, "__traceback__")
                else None,
            }
        )

    def _update_activity(self) -> None:
        """Update the last activity timestamp."""
        self._last_activity = datetime.now()

    def get_memory_usage_mb(self) -> float:
        """
        Get estimated memory usage of this component in MB.

        Returns:
            Estimated memory usage in megabytes
        """
        # Get size of key attributes
        size = 0

        # Check common attributes
        attrs_to_check = [
            "_orders",
            "_positions",
            "_trades",
            "_data",
            "_order_history",
            "_position_history",
            "_managed_tasks",
            "_persistent_tasks",
            "stats",
            "_error_history",
        ]

        for attr_name in attrs_to_check:
            if hasattr(self, attr_name):
                attr = getattr(self, attr_name)
                size += sys.getsizeof(attr)

                # For collections, also count items
                if isinstance(attr, (list, dict, set, deque)):
                    try:
                        for item in attr.values() if isinstance(attr, dict) else attr:
                            size += sys.getsizeof(item)
                    except:
                        pass  # Skip if iteration fails

        # Convert to MB
        return size / (1024 * 1024)

    def get_error_stats(self) -> dict[str, Any]:
        """
        Get error statistics.

        Returns:
            Dictionary with error statistics
        """
        recent_errors = list(self._error_history)[-10:]  # Last 10 errors

        # Count errors by type
        error_types: dict[str, int] = {}
        for error in self._error_history:
            error_type = error["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total_errors": self._error_count,
            "recent_errors": recent_errors,
            "error_types": error_types,
            "last_error": recent_errors[-1] if recent_errors else None,
        }

    def get_activity_stats(self) -> dict[str, Any]:
        """
        Get activity statistics.

        Returns:
            Dictionary with activity statistics
        """
        uptime = time.time() - self._start_time

        return {
            "uptime_seconds": uptime,
            "last_activity": self._last_activity,
            "is_active": self._last_activity is not None
            and (datetime.now() - self._last_activity).total_seconds() < 60,
        }
