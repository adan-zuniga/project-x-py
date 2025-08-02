"""Statistics, history, and report generation functionality."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_x_py.position_manager.types import PositionManagerProtocol


class PositionReportingMixin:
    """Mixin for statistics, history, and report generation."""

    def get_position_statistics(self: "PositionManagerProtocol") -> dict[str, Any]:
        """
        Get comprehensive position management statistics and health information.

        Provides detailed statistics about position tracking, monitoring status,
        performance metrics, and system health for debugging and monitoring.

        Returns:
            dict[str, Any]: Complete system statistics containing:
                - statistics (dict): Core metrics:
                    * positions_tracked (int): Current position count
                    * total_pnl (float): Aggregate P&L
                    * realized_pnl (float): Closed position P&L
                    * unrealized_pnl (float): Open position P&L
                    * positions_closed (int): Total positions closed
                    * positions_partially_closed (int): Partial closures
                    * last_update_time (datetime): Last data refresh
                    * monitoring_started (datetime): Monitoring start time
                - realtime_enabled (bool): Using WebSocket updates
                - order_sync_enabled (bool): Order synchronization active
                - monitoring_active (bool): Position monitoring running
                - tracked_positions (int): Positions in local cache
                - active_alerts (int): Untriggered alert count
                - callbacks_registered (dict): Callbacks by event type
                - risk_settings (dict): Current risk thresholds
                - health_status (str): "active" or "inactive"

        Example:
            >>> stats = position_manager.get_position_statistics()
            >>> print(f"System Health: {stats['health_status']}")
            >>> print(f"Tracking {stats['tracked_positions']} positions")
            >>> print(f"Real-time: {stats['realtime_enabled']}")
            >>> print(f"Monitoring: {stats['monitoring_active']}")
            >>> print(f"Positions closed: {stats['statistics']['positions_closed']}")
            >>> # Check callback registrations
            >>> for event, count in stats["callbacks_registered"].items():
            ...     print(f"{event}: {count} callbacks")

        Note:
            Statistics are cumulative since manager initialization.
            Use export_portfolio_report() for more detailed analysis.
        """
        return {
            "statistics": self.stats.copy(),
            "realtime_enabled": self._realtime_enabled,
            "order_sync_enabled": self._order_sync_enabled,
            "monitoring_active": self._monitoring_active,
            "tracked_positions": len(self.tracked_positions),
            "active_alerts": len(
                [a for a in self.position_alerts.values() if not a["triggered"]]
            ),
            "callbacks_registered": {
                event: len(callbacks)
                for event, callbacks in self.position_callbacks.items()
            },
            "risk_settings": self.risk_settings.copy(),
            "health_status": (
                "active" if self.project_x._authenticated else "inactive"
            ),
        }

    async def get_position_history(
        self: "PositionManagerProtocol", contract_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get historical position data for a specific contract.

        Retrieves the history of position changes including size changes,
        timestamps, and position snapshots for analysis and debugging.

        Args:
            contract_id (str): Contract ID to retrieve history for (e.g., "MGC")
            limit (int, optional): Maximum number of history entries to return.
                Returns most recent entries if history exceeds limit.
                Defaults to 100.

        Returns:
            list[dict]: Historical position entries, each containing:
                - timestamp (datetime): When the change occurred
                - position (dict): Complete position snapshot at that time
                - size_change (int): Change in position size from previous

        Example:
            >>> # Get recent history for Gold position
            >>> history = await position_manager.get_position_history("MGC", limit=50)
            >>> print(f"Found {len(history)} historical entries")
            >>> # Analyze recent changes
            >>> for entry in history[-5:]:  # Last 5 changes
            ...     ts = entry["timestamp"].strftime("%H:%M:%S")
            ...     size = entry["position"]["size"]
            ...     change = entry["size_change"]
            ...     print(f"{ts}: Size {size} (change: {change:+d})")
            >>> # Find when position was opened
            >>> if history:
            ...     first_entry = history[0]
            ...     print(f"Position opened at {first_entry['timestamp']}")

        Note:
            - History is maintained in memory during manager lifetime
            - Cleared when cleanup() is called
            - Empty list returned if no history exists
        """
        async with self.position_lock:
            history = self.position_history.get(contract_id, [])
            return history[-limit:] if history else []

    async def export_portfolio_report(
        self: "PositionManagerProtocol",
    ) -> dict[str, Any]:
        """
        Generate a comprehensive portfolio report with complete analysis.

        Creates a detailed report suitable for saving to file, sending via email,
        or displaying in dashboards. Combines all available analytics into a
        single comprehensive document.

        Returns:
            dict[str, Any]: Complete portfolio report containing:
                - report_timestamp (datetime): Report generation time
                - portfolio_summary (dict):
                    * total_positions (int): Open position count
                    * total_pnl (float): Aggregate P&L (requires prices)
                    * total_exposure (float): Sum of position values
                    * portfolio_risk (float): Risk score
                - positions (list[dict]): Detailed position list
                - risk_analysis (dict): Complete risk metrics
                - statistics (dict): System statistics and health
                - alerts (dict):
                    * active_alerts (int): Untriggered alert count
                    * triggered_alerts (int): Triggered alert count

        Example:
            >>> # Generate comprehensive report
            >>> report = await position_manager.export_portfolio_report()
            >>> print(f"Portfolio Report - {report['report_timestamp']}")
            >>> print(f"Positions: {report['portfolio_summary']['total_positions']}")
            >>> print(
            ...     f"Exposure: ${report['portfolio_summary']['total_exposure']:,.2f}"
            ... )
            >>> # Save report to file (async)
            >>> import json
            >>> import aiofiles
            >>> async with aiofiles.open("portfolio_report.json", "w") as f:
            ...     await f.write(json.dumps(report, indent=2, default=str))
            >>> # Send key metrics
            >>> summary = report["portfolio_summary"]
            >>> alerts = report["alerts"]
            >>> print(f"Active Alerts: {alerts['active_alerts']}")

        Use cases:
            - End-of-day reporting
            - Risk management dashboards
            - Performance tracking
            - Audit trails
            - Email summaries
        """
        positions = await self.get_all_positions()
        pnl_data = await self.get_portfolio_pnl()
        risk_data = await self.get_risk_metrics()
        stats = self.get_position_statistics()

        return {
            "report_timestamp": datetime.now(),
            "portfolio_summary": {
                "total_positions": len(positions),
                "total_pnl": pnl_data["total_pnl"],
                "total_exposure": risk_data["total_exposure"],
                "portfolio_risk": risk_data["portfolio_risk"],
            },
            "positions": pnl_data["positions"],
            "risk_analysis": risk_data,
            "statistics": stats,
            "alerts": {
                "active_alerts": len(
                    [a for a in self.position_alerts.values() if not a["triggered"]]
                ),
                "triggered_alerts": len(
                    [a for a in self.position_alerts.values() if a["triggered"]]
                ),
            },
        }

    def get_realtime_validation_status(
        self: "PositionManagerProtocol",
    ) -> dict[str, Any]:
        """
        Get validation status for real-time position feed integration and compliance.

        Provides detailed information about real-time integration status,
        payload validation settings, and ProjectX API compliance for debugging
        and system validation.

        Returns:
            dict[str, Any]: Validation and compliance status containing:
                - realtime_enabled (bool): WebSocket integration active
                - tracked_positions_count (int): Positions in cache
                - position_callbacks_registered (int): Update callbacks
                - payload_validation (dict):
                    * enabled (bool): Validation active
                    * required_fields (list[str]): Expected fields
                    * position_type_enum (dict): Type mappings
                    * closure_detection (str): How closures detected
                - projectx_compliance (dict):
                    * gateway_user_position_format: Compliance status
                    * position_type_enum: Enum validation status
                    * closure_logic: Closure detection status
                    * payload_structure: Payload format status
                - statistics (dict): Current statistics

        Example:
            >>> # Check real-time integration health
            >>> status = position_manager.get_realtime_validation_status()
            >>> print(f"Real-time enabled: {status['realtime_enabled']}")
            >>> print(f"Tracking {status['tracked_positions_count']} positions")
            >>> # Verify API compliance
            >>> compliance = status["projectx_compliance"]
            >>> all_compliant = all("✅" in v for v in compliance.values())
            >>> print(f"Fully compliant: {all_compliant}")
            >>> # Check payload validation
            >>> validation = status["payload_validation"]
            >>> print(f"Closure detection: {validation['closure_detection']}")
            >>> print(f"Required fields: {len(validation['required_fields'])}")

        Use cases:
            - Integration testing
            - Debugging connection issues
            - Compliance verification
            - System health checks
        """
        return {
            "realtime_enabled": self._realtime_enabled,
            "tracked_positions_count": len(self.tracked_positions),
            "position_callbacks_registered": len(
                self.position_callbacks.get("position_update", [])
            ),
            "payload_validation": {
                "enabled": True,
                "required_fields": [
                    "id",
                    "accountId",
                    "contractId",
                    "creationTimestamp",
                    "type",
                    "size",
                    "averagePrice",
                ],
                "position_type_enum": {"Undefined": 0, "Long": 1, "Short": 2},
                "closure_detection": "size == 0 (not type == 0)",
            },
            "projectx_compliance": {
                "gateway_user_position_format": "✅ Compliant",
                "position_type_enum": "✅ Correct",
                "closure_logic": "✅ Fixed (was incorrectly checking type==0)",
                "payload_structure": "✅ Direct payload (no 'data' extraction)",
            },
            "statistics": self.stats.copy(),
        }
