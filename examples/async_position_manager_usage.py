"""
Example demonstrating AsyncPositionManager usage for position operations.

This example shows how to use the AsyncPositionManager for tracking positions,
calculating P&L, managing risk, and handling position monitoring with async/await.
"""

import asyncio

from project_x_py import AsyncPositionManager, AsyncProjectX


async def main():
    """Main async function demonstrating position management."""
    # Create async client
    async with AsyncProjectX.from_env() as client:
        # Authenticate
        await client.authenticate()
        print(f"✅ Authenticated as {client.account_info.name}")

        # Create position manager
        position_manager = AsyncPositionManager(client)
        await position_manager.initialize()

        # 1. Get all positions
        print("\n📊 Current Positions:")
        positions = await position_manager.get_all_positions()
        for pos in positions:
            direction = "LONG" if pos.type == 1 else "SHORT"
            print(
                f"  {pos.contractId}: {direction} {pos.size} @ ${pos.averagePrice:.2f}"
            )

        # 2. Get specific position
        mgc_position = await position_manager.get_position("MGC")
        if mgc_position:
            print(f"\n🎯 MGC Position: {mgc_position.size} contracts")

        # 3. Calculate P&L with current prices (example prices)
        if positions:
            print("\n💰 P&L Calculations:")
            # In real usage, get current prices from market data
            current_prices = {
                "MGC": 2050.0,
                "MNQ": 18100.0,
                "MES": 5710.0,
            }

            portfolio_pnl = await position_manager.calculate_portfolio_pnl(
                current_prices
            )
            print(f"  Total P&L: ${portfolio_pnl['total_pnl']:.2f}")
            print(f"  Positions with prices: {portfolio_pnl['positions_with_prices']}")

            # Show breakdown
            for pos_data in portfolio_pnl["position_breakdown"]:
                if pos_data["current_price"]:
                    print(
                        f"  {pos_data['contract_id']}: ${pos_data['unrealized_pnl']:.2f}"
                    )

        # 4. Risk metrics
        print("\n⚠️ Risk Analysis:")
        risk = await position_manager.get_risk_metrics()
        print(f"  Total exposure: ${risk['total_exposure']:.2f}")
        print(f"  Position count: {risk['position_count']}")
        print(f"  Diversification score: {risk['diversification_score']:.2f}")

        if risk["risk_warnings"]:
            print("  Warnings:")
            for warning in risk["risk_warnings"]:
                print(f"    - {warning}")

        # 5. Position sizing calculator
        print("\n📏 Position Sizing Example:")
        sizing = await position_manager.calculate_position_size(
            "MGC",
            risk_amount=100.0,  # Risk $100
            entry_price=2045.0,
            stop_price=2040.0,  # 5 point stop
        )
        print(f"  Suggested size: {sizing['suggested_size']} contracts")
        print(f"  Risk per contract: ${sizing['risk_per_contract']:.2f}")
        print(f"  Risk percentage: {sizing['risk_percentage']:.2f}%")

        # 6. Add position alerts
        print("\n🔔 Setting up position alerts...")
        await position_manager.add_position_alert("MGC", max_loss=-500.0)
        await position_manager.add_position_alert("MNQ", max_gain=1000.0)
        print("  Alerts configured for MGC and MNQ")

        # 7. Start monitoring (for demo, just start and stop)
        print("\n👁️ Starting position monitoring...")
        await position_manager.start_monitoring(refresh_interval=30)
        print("  Monitoring active (polling every 30s)")

        # 8. Export portfolio report
        report = await position_manager.export_portfolio_report()
        print("\n📋 Portfolio Report:")
        print(f"  Generated at: {report['report_timestamp']}")
        print(f"  Total positions: {report['portfolio_summary']['total_positions']}")
        print(f"  Total exposure: ${report['portfolio_summary']['total_exposure']:.2f}")

        # 9. Position statistics
        stats = position_manager.get_position_statistics()
        print("\n📊 Position Manager Statistics:")
        print(f"  Positions tracked: {stats['tracked_positions']}")
        print(f"  Real-time enabled: {stats['realtime_enabled']}")
        print(f"  Monitoring active: {stats['monitoring_active']}")
        print(f"  Active alerts: {stats['active_alerts']}")

        # Stop monitoring
        await position_manager.stop_monitoring()
        print("\n🛑 Monitoring stopped")

        # 10. Demo position operations (commented out to avoid actual trades)
        print("\n💡 Position Operations (examples - not executed):")
        print("  # Close entire position:")
        print('  await position_manager.close_position_direct("MGC")')
        print("  # Partial close:")
        print('  await position_manager.partially_close_position("MGC", 3)')
        print("  # Close all positions:")
        print("  await position_manager.close_all_positions()")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
