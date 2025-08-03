"""
Position Manager Module for ProjectX Trading Platform.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides comprehensive position management functionality for ProjectX trading operations,
    including real-time tracking, P&L calculations, risk management, and direct position
    operations. Integrates with both API and real-time clients for seamless position
    lifecycle management.

Key Features:
    - Real-time position tracking and monitoring via WebSocket
    - P&L calculations and portfolio analytics with market prices
    - Risk metrics and position sizing with configurable thresholds
    - Position monitoring and alerts with customizable triggers
    - Direct position operations (close, partial close, bulk operations)
    - Statistics, history, and comprehensive report generation
    - Thread-safe operations with async/await patterns
    - Event-driven callbacks for custom position monitoring

Position Management Capabilities:
    - Real-time position updates and closure detection
    - Portfolio-level P&L analysis with current market prices
    - Risk assessment and position sizing calculations
    - Automated position monitoring with configurable alerts
    - Direct position operations through ProjectX API
    - Comprehensive reporting and historical analysis

Example Usage:
    ```python
    from project_x_py import ProjectX
    from project_x_py.position_manager import PositionManager

    async with ProjectX.from_env() as client:
        await client.authenticate()
        pm = PositionManager(client)

        # Initialize with real-time tracking
        await pm.initialize(realtime_client=client.realtime_client)

        # Get current positions
        positions = await pm.get_all_positions()
        for pos in positions:
            print(f"{pos.contractId}: {pos.size} @ ${pos.averagePrice}")

        # Calculate P&L with current prices
        prices = {"MGC": 2050.0, "NQ": 15500.0}
        pnl = await pm.calculate_portfolio_pnl(prices)
        print(f"Total P&L: ${pnl['total_pnl']:.2f}")

        # Risk analysis
        risk = await pm.get_risk_metrics()
        print(f"Portfolio risk: {risk['portfolio_risk']:.2%}")

        # Position sizing
        sizing = await pm.calculate_position_size(
            "MGC", risk_amount=500.0, entry_price=2050.0, stop_price=2040.0
        )
        print(f"Suggested size: {sizing['suggested_size']} contracts")
    ```

See Also:
    - `position_manager.core.PositionManager`
    - `position_manager.analytics.PositionAnalyticsMixin`
    - `position_manager.risk.RiskManagementMixin`
    - `position_manager.monitoring.PositionMonitoringMixin`
    - `position_manager.operations.PositionOperationsMixin`
    - `position_manager.reporting.PositionReportingMixin`
    - `position_manager.tracking.PositionTrackingMixin`
"""

from project_x_py.position_manager.core import PositionManager

__all__ = ["PositionManager"]
