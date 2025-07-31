#!/usr/bin/env python3
"""
Async Position Management and Tracking Example

Demonstrates comprehensive async position management and risk monitoring:
- Real-time position tracking with async updates
- Concurrent portfolio P&L calculations
- Async risk metrics and alerts
- Position monitoring with async callbacks
- Portfolio reporting with live updates

Uses MNQ micro contracts for testing safety.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/async_03_position_management.py

Author: TexasCoding
Date: July 2025
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from project_x_py import (
    AsyncProjectX,
    create_async_order_manager,
    create_async_position_manager,
    create_async_realtime_client,
    setup_logging,
)


async def get_current_market_price(client: AsyncProjectX, symbol="MNQ"):
    """Get current market price with async fallback for closed markets."""
    # Try different data configurations concurrently
    configs = [(1, 1), (1, 5), (2, 15), (5, 15), (7, 60)]

    async def try_get_data(days, interval):
        try:
            market_data = await client.get_data(symbol, days=days, interval=interval)
            if market_data is not None and not market_data.is_empty():
                return float(market_data.select("close").tail(1).item())
        except Exception:
            return None

    # Try all configurations concurrently
    tasks = [try_get_data(days, interval) for days, interval in configs]
    results = await asyncio.gather(*tasks)

    # Return first valid result
    for price in results:
        if price is not None:
            return price

    # Fallback price if no data available
    return 23400.00  # Reasonable MNQ price


async def display_positions(position_manager):
    """Display current positions with detailed information."""
    print("\n📊 Current Positions:")
    print("-" * 80)

    positions = await position_manager.get_all_positions()

    if not positions:
        print("No open positions")
        return

    # Get portfolio P&L concurrently with position display
    pnl_task = asyncio.create_task(position_manager.get_portfolio_pnl())

    # Display each position
    for symbol, position in positions.items():
        print(f"\n{symbol}:")
        print(f"  Quantity: {position.quantity}")
        print(f"  Average Price: ${position.averagePrice:.2f}")
        print(f"  Position Value: ${position.positionValue:.2f}")
        print(f"  Unrealized P&L: ${position.unrealizedPnl:.2f}")

        # Show percentage change
        if position.averagePrice > 0:
            pnl_pct = (
                position.unrealizedPnl / (position.quantity * position.averagePrice)
            ) * 100
            print(f"  P&L %: {pnl_pct:+.2f}%")

    # Show portfolio totals
    portfolio_pnl = await pnl_task
    print("\n" + "=" * 40)
    print(f"Portfolio Total P&L: ${portfolio_pnl:.2f}")
    print("=" * 40)


async def monitor_positions_realtime(position_manager, duration_seconds=30):
    """Monitor positions with real-time updates."""
    print(f"\n🔄 Monitoring positions for {duration_seconds} seconds...")

    # Track position changes
    position_updates = []

    async def on_position_update(data):
        """Handle real-time position updates."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        position_updates.append((timestamp, data))

        # Display update
        symbol = data.get("contractId", "Unknown")
        qty = data.get("quantity", 0)
        pnl = data.get("unrealizedPnl", 0)

        print(f"\n[{timestamp}] Position Update:")
        print(f"  Symbol: {symbol}")
        print(f"  Quantity: {qty}")
        print(f"  Unrealized P&L: ${pnl:.2f}")

    # Register callback if realtime client available
    if (
        hasattr(position_manager, "realtime_client")
        and position_manager.realtime_client
    ):
        await position_manager.realtime_client.add_callback(
            "position_update", on_position_update
        )

    # Monitor for specified duration
    start_time = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start_time < duration_seconds:
        # Display portfolio metrics every 10 seconds
        await asyncio.sleep(10)

        # Get metrics concurrently
        metrics_task = position_manager.get_risk_metrics()
        pnl_task = position_manager.get_portfolio_pnl()

        metrics, pnl = await asyncio.gather(metrics_task, pnl_task)

        print(f"\n📈 Portfolio Update at {datetime.now().strftime('%H:%M:%S')}:")
        print(f"  Total P&L: ${pnl:.2f}")
        print(f"  Max Drawdown: ${metrics.get('max_drawdown', 0):.2f}")
        print(f"  Position Count: {metrics.get('position_count', 0)}")

    print(f"\n✅ Monitoring complete. Received {len(position_updates)} updates.")

    # Remove callback
    if (
        hasattr(position_manager, "realtime_client")
        and position_manager.realtime_client
    ):
        await position_manager.realtime_client.remove_callback(
            "position_update", on_position_update
        )


async def main():
    """Main async function demonstrating position management."""
    logger = setup_logging(level="INFO")
    logger.info("🚀 Starting Async Position Management Example")

    try:
        # Create async client
        async with AsyncProjectX.from_env() as client:
            await client.authenticate()
            print(f"✅ Connected as: {client.account_info.name}")

            # Create real-time client for live updates
            realtime_client = create_async_realtime_client(
                client.session_token, client.account_info.id
            )

            # Create position manager with real-time integration
            position_manager = create_async_position_manager(client, realtime_client)
            await position_manager.initialize()

            # Connect real-time client
            print("\n🔌 Connecting to real-time services...")
            if await realtime_client.connect():
                await realtime_client.subscribe_user_updates()
                print("✅ Real-time position tracking enabled")
            else:
                print("⚠️  Real-time tracking unavailable")

            # Display current positions
            await display_positions(position_manager)

            # Get and display risk metrics
            print("\n📊 Risk Metrics:")
            risk_metrics = await position_manager.get_risk_metrics()

            print(f"  Position Count: {risk_metrics.get('position_count', 0)}")
            print(f"  Total Exposure: ${risk_metrics.get('total_exposure', 0):,.2f}")
            print(
                f"  Max Position Size: ${risk_metrics.get('max_position_size', 0):,.2f}"
            )
            print(f"  Max Drawdown: ${risk_metrics.get('max_drawdown', 0):,.2f}")

            # Calculate optimal position sizing
            print("\n💡 Position Sizing Recommendations:")

            # Get market price for calculation
            market_price = await get_current_market_price(client, "MNQ")

            # Calculate position sizes for different risk levels
            risk_levels = [0.01, 0.02, 0.05]  # 1%, 2%, 5% risk
            account_balance = float(client.account_info.balance)

            print(f"  Account Balance: ${account_balance:,.2f}")
            print(f"  Market Price (MNQ): ${market_price:.2f}")

            for risk_pct in risk_levels:
                position_size = await position_manager.calculate_position_size(
                    account_balance=account_balance,
                    risk_percentage=risk_pct,
                    entry_price=market_price,
                    stop_loss_price=market_price * 0.99,  # 1% stop loss
                )

                print(f"  {risk_pct * 100:.0f}% Risk: {position_size} contracts")

            # Check for any positions that need alerts
            positions = await position_manager.get_all_positions()

            if positions:
                print("\n⚠️  Setting up position alerts...")

                # Add alerts for each position
                alert_tasks = []
                for symbol, position in positions.items():
                    # Alert if position loses more than 2%
                    max_loss = position.averagePrice * position.quantity * 0.02
                    task = position_manager.add_position_alert(
                        symbol, max_loss=-max_loss, alert_name=f"{symbol}_2pct_loss"
                    )
                    alert_tasks.append(task)

                await asyncio.gather(*alert_tasks)
                print(f"✅ Added alerts for {len(positions)} positions")

                # Monitor positions for 30 seconds
                await monitor_positions_realtime(position_manager, duration_seconds=30)

            # Display position history
            print("\n📜 Recent Position History:")
            history = await position_manager.get_position_history(days=7)

            if history:
                for i, pos in enumerate(history[:5]):  # Show last 5
                    print(f"\n{i + 1}. {pos.get('contractId', 'Unknown')}:")
                    print(f"   Opened: {pos.get('openedAt', 'Unknown')}")
                    print(f"   Closed: {pos.get('closedAt', 'Unknown')}")
                    print(f"   P&L: ${pos.get('realizedPnl', 0):.2f}")
            else:
                print("  No position history available")

            # Clean up
            await realtime_client.cleanup()

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ASYNC POSITION MANAGEMENT EXAMPLE")
    print("=" * 60 + "\n")

    asyncio.run(main())

    print("\n✅ Example completed!")
