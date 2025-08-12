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

Note:
    While this module provides direct access to the `PositionManager`, for most
    trading applications, it is recommended to use the `TradingSuite`. The suite
    automatically creates, configures, and manages the position manager, providing
    simplified access to its functionality via `suite.positions`.
    The example below shows the lower-level manual setup.

Example Usage:
    ```python
    # V3: Comprehensive position management with EventBus integration
    import asyncio
    from project_x_py import (
        ProjectX,
        create_realtime_client,
        create_position_manager,
        EventBus,
    )


    async def main():
        async with ProjectX.from_env() as client:
            await client.authenticate()

            # V3: Create dependencies
            event_bus = EventBus()
            realtime_client = await create_realtime_client(
                client.get_session_token(), str(client.get_account_info().id)
            )

            # V3: Create position manager with dependency injection
            pm = create_position_manager(client, realtime_client, event_bus)
            await pm.initialize(realtime_client)

            # V3: Get current positions with detailed info
            positions = await pm.get_all_positions()
            for pos in positions:
                print(f"Contract: {pos.contractId}")
                print(f"  Size: {pos.netPos}")
                print(f"  Avg Price: ${pos.buyAvgPrice:.2f}")
                print(f"  Unrealized P&L: ${pos.unrealizedPnl:.2f}")

            # V3: Calculate portfolio P&L with current market prices
            market_prices = {"MGC": 2050.0, "MNQ": 18500.0}
            pnl = await pm.calculate_portfolio_pnl(market_prices)
            print(f"Total P&L: ${pnl['total_pnl']:.2f}")
            print(f"Unrealized: ${pnl['unrealized_pnl']:.2f}")
            print(f"Realized: ${pnl['realized_pnl']:.2f}")

            # V3: Risk analysis with comprehensive metrics
            risk = await pm.get_risk_metrics()
            print(f"Portfolio Risk: {risk['portfolio_risk']:.2%}")
            print(f"Max Drawdown: ${risk['max_drawdown']:.2f}")
            print(f"VaR (95%): ${risk['var_95']:.2f}")

            # V3: Position sizing with risk management
            sizing = await pm.calculate_position_size(
                "MGC", risk_amount=500.0, entry_price=2050.0, stop_price=2040.0
            )
            print(f"Suggested size: {sizing['suggested_size']} contracts")
            print(f"Position risk: ${sizing['position_risk']:.2f}")

            # V3: Set up position monitoring with alerts
            await pm.add_position_alert("MGC", max_loss=-500.0, min_profit=1000.0)
            await pm.start_monitoring(interval_seconds=5)


    asyncio.run(main())
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
