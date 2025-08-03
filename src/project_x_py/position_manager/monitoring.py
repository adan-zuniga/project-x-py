"""
Position monitoring and alerts functionality for ProjectX position management.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides position monitoring and alert functionality for real-time position
    tracking. Includes automated monitoring loops, configurable alerts, and
    event-driven notifications for position changes and risk thresholds.

Key Features:
    - Real-time position monitoring via WebSocket or polling
    - Configurable position alerts with multiple trigger types
    - Automated monitoring loops with error handling
    - Event-driven alert notifications and callbacks
    - Thread-safe operations with proper lock management
    - Comprehensive monitoring statistics and health tracking

Monitoring Capabilities:
    - Real-time position updates and closure detection
    - Configurable alerts for P&L thresholds, size changes, and risk limits
    - Automated monitoring with configurable refresh intervals
    - Alert triggering and notification management
    - Monitoring health tracking and statistics

Example Usage:
    ```python
    # Add position alerts
    await position_manager.add_position_alert("MGC", max_loss=-500.0)
    await position_manager.add_position_alert("NQ", max_gain=1000.0)

    # Start monitoring
    await position_manager.start_monitoring(refresh_interval=30)


    # Register alert callbacks
    async def on_alert(data):
        print(f"Alert triggered: {data['message']}")


    await position_manager.add_callback("position_alert", on_alert)
    ```

See Also:
    - `position_manager.core.PositionManager`
    - `position_manager.tracking.PositionTrackingMixin`
    - `position_manager.risk.RiskManagementMixin`
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from project_x_py.models import Position

if TYPE_CHECKING:
    from asyncio import Lock

logger = logging.getLogger(__name__)


class PositionMonitoringMixin:
    """Mixin for position monitoring and alerts."""

    # Type hints for mypy - these attributes are provided by the main class
    if TYPE_CHECKING:
        position_lock: Lock
        logger: logging.Logger
        stats: dict[str, Any]
        _realtime_enabled: bool

        # Methods from other mixins/main class
        async def _trigger_callbacks(
            self, event_type: str, data: dict[str, Any]
        ) -> None: ...
        async def refresh_positions(self, account_id: int | None = None) -> bool: ...

    def __init__(self) -> None:
        """Initialize monitoring attributes."""
        # Monitoring and alerts
        self._monitoring_active = False
        self._monitoring_task: asyncio.Task[None] | None = None
        self.position_alerts: dict[str, dict[str, Any]] = {}

    async def add_position_alert(
        self,
        contract_id: str,
        max_loss: float | None = None,
        max_gain: float | None = None,
        pnl_threshold: float | None = None,
    ) -> None:
        """
        Add an alert for a specific position.

        Args:
            contract_id: Contract ID to monitor
            max_loss: Maximum loss threshold (negative value)
            max_gain: Maximum gain threshold (positive value)
            pnl_threshold: Absolute P&L change threshold

        Example:
            >>> # Alert if MGC loses more than $500
            >>> await position_manager.add_position_alert("MGC", max_loss=-500.0)
            >>> # Alert if NQ gains more than $1000
            >>> await position_manager.add_position_alert("NQ", max_gain=1000.0)
        """
        async with self.position_lock:
            self.position_alerts[contract_id] = {
                "max_loss": max_loss,
                "max_gain": max_gain,
                "pnl_threshold": pnl_threshold,
                "created": datetime.now(),
                "triggered": False,
            }

        self.logger.info(f"📢 Position alert added for {contract_id}")

    async def remove_position_alert(self, contract_id: str) -> None:
        """
        Remove position alert for a specific contract.

        Args:
            contract_id: Contract ID to remove alert for

        Example:
            >>> await position_manager.remove_position_alert("MGC")
        """
        async with self.position_lock:
            if contract_id in self.position_alerts:
                del self.position_alerts[contract_id]
                self.logger.info(f"🔕 Position alert removed for {contract_id}")

    async def _check_position_alerts(
        self,
        contract_id: str,
        current_position: Position,
        old_position: Position | None,
    ) -> None:
        """
        Check if position alerts should be triggered and handle alert notifications.

        Evaluates position changes against configured alert thresholds and triggers
        notifications when conditions are met. Called automatically during position
        updates from both real-time feeds and polling.

        Args:
            contract_id (str): Contract ID of the position being checked
            current_position (Position): Current position state after update
            old_position (Position | None): Previous position state before update,
                None if this is a new position

        Alert types:
            - max_loss: Triggers when P&L falls below threshold (requires prices)
            - max_gain: Triggers when P&L exceeds threshold (requires prices)
            - pnl_threshold: Triggers on absolute P&L change (requires prices)
            - size_change: Currently implemented - alerts on position size changes

        Side effects:
            - Sets alert['triggered'] = True when triggered (one-time trigger)
            - Logs warning message for triggered alerts
            - Calls position_alert callbacks with alert details

        Note:
            P&L-based alerts require current market prices to be provided
            separately. Currently only size change detection is implemented.
        """
        alert = self.position_alerts.get(contract_id)
        if not alert or alert["triggered"]:
            return

        # Note: P&L-based alerts require current market prices
        # For now, only check position size changes
        alert_triggered = False
        alert_message = ""

        # Check for position size changes as a basic alert
        if old_position and current_position.size != old_position.size:
            size_change = current_position.size - old_position.size
            alert_triggered = True
            alert_message = (
                f"Position {contract_id} size changed by {size_change} contracts"
            )

        if alert_triggered:
            alert["triggered"] = True
            self.logger.warning(f"🚨 POSITION ALERT: {alert_message}")
            await self._trigger_callbacks(
                "position_alert",
                {
                    "contract_id": contract_id,
                    "message": alert_message,
                    "position": current_position,
                    "alert": alert,
                },
            )

    async def _monitoring_loop(self, refresh_interval: int) -> None:
        """
        Main monitoring loop for polling mode position updates.

        Continuously refreshes position data at specified intervals when real-time
        mode is not available. Handles errors gracefully to maintain monitoring.

        Args:
            refresh_interval (int): Seconds between position refreshes

        Note:
            - Runs until self._monitoring_active becomes False
            - Errors are logged but don't stop the monitoring loop
            - Only used in polling mode (when real-time client not available)
        """
        while self._monitoring_active:
            try:
                await self.refresh_positions()
                await asyncio.sleep(refresh_interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(refresh_interval)

    async def start_monitoring(self, refresh_interval: int = 30) -> None:
        """
        Start automated position monitoring for real-time updates and alerts.

        Enables continuous monitoring of positions with automatic alert checking.
        In real-time mode (with AsyncProjectXRealtimeClient), uses live WebSocket feeds.
        In polling mode, periodically refreshes position data from the API.

        Args:
            refresh_interval: Seconds between position updates in polling mode (default: 30)
                Ignored when real-time client is available

        Example:
            >>> # Start monitoring with real-time updates
            >>> await position_manager.start_monitoring()
            >>> # Start monitoring with custom polling interval
            >>> await position_manager.start_monitoring(refresh_interval=60)
        """
        if self._monitoring_active:
            self.logger.warning("⚠️ Position monitoring already active")
            return

        self._monitoring_active = True
        self.stats["monitoring_started"] = datetime.now()

        if not self._realtime_enabled:
            # Start async monitoring loop
            self._monitoring_task = asyncio.create_task(
                self._monitoring_loop(refresh_interval)
            )
            self.logger.info(
                f"📊 Position monitoring started (polling every {refresh_interval}s)"
            )
        else:
            self.logger.info("📊 Position monitoring started (real-time mode)")

    async def stop_monitoring(self) -> None:
        """
        Stop automated position monitoring and clean up monitoring resources.

        Cancels any active monitoring tasks and stops position update notifications.

        Example:
            >>> await position_manager.stop_monitoring()
        """
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
        self.logger.info("🛑 Position monitoring stopped")
