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

from project_x_py import (
    ProjectX,
    create_data_manager,
    create_order_manager,
    create_position_manager,
    create_realtime_client,
    setup_logging,
)
from project_x_py.async_realtime_data_manager import AsyncRealtimeDataManager


async def get_current_market_price(
    client: ProjectX,
    symbol="MNQ",
    realtime_data_manager: AsyncRealtimeDataManager | None = None,
):
    """Get current market price with async fallback for closed markets."""
    # Try to get real-time price first if available
    if realtime_data_manager:
        try:
            current_price = await realtime_data_manager.get_current_price()
            if current_price:
                return float(current_price)
        except Exception as e:
            print(f"   ⚠️  Real-time price not available: {e}")

    # Try different data configurations concurrently
    configs = [(1, 1), (1, 5), (2, 15), (5, 15), (7, 60)]

    async def try_get_data(days, interval):
        try:
            market_data = await client.get_bars(symbol, days=days, interval=interval)
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
            print(f"    Using historical price: ${price:.2f}")
            return price

    # DON'T use a fallback - return None if no data available
    print("   ❌ No market data available")
    return None


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
        async with ProjectX.from_env() as client:
            await client.authenticate()
            if client.account_info:
                print(f"✅ Connected as: {client.account_info.name}")
            else:
                print("❌ Could not get account information")
                return

            # Create real-time client for live updates
            realtime_client = create_realtime_client(
                client.session_token, str(client.account_info.id)
            )

            # Create position manager with real-time integration
            position_manager = create_position_manager(client, realtime_client)

            # Connect real-time client first
            print("\n🔌 Connecting to real-time services...")
            if await realtime_client.connect():
                await realtime_client.subscribe_user_updates()

                # Initialize position manager with connected realtime client
                await position_manager.initialize(realtime_client=realtime_client)
                print("✅ Real-time position tracking enabled")

                # Create real-time data manager for MNQ
                realtime_data_manager = None
                try:
                    realtime_data_manager = create_data_manager(
                        "MNQ",
                        client,
                        realtime_client,
                        timeframes=["15sec", "1min", "5min"],
                    )
                    await realtime_data_manager.initialize()
                    # Start the real-time feed
                    if await realtime_data_manager.start_realtime_feed():
                        print("✅ Real-time market data enabled for MNQ")
                    else:
                        print("⚠️  Real-time market data feed failed to start")
                except Exception as e:
                    print(f"⚠️  Real-time market data setup failed: {e}")
            else:
                # Fall back to polling mode
                await position_manager.initialize()
                print("⚠️  Using polling mode (real-time connection failed)")
                realtime_data_manager = None

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
            market_price = await get_current_market_price(
                client, "MNQ", realtime_data_manager
            )
            if market_price is None:
                market_price = 23400.00  # Use fallback only for sizing calculations
                print(f"   ⚠️  Using fallback price for sizing: ${market_price:.2f}")

            # Get account info
            account_info = client.account_info
            if not account_info:
                print("❌ Could not get account information")
                return
            account_balance = float(account_info.balance)

            print(f"  Account Balance: ${account_balance:,.2f}")
            print(f"  Market Price (MNQ): ${market_price:.2f}")

            # Calculate position sizes for different risk amounts
            # For MNQ micro contracts, use smaller risk amounts
            risk_amounts = [25, 50, 100, 200]  # Risk $25, $50, $100, $200
            stop_distance = 10.0  # $10 stop distance (40 ticks for MNQ)

            print(f"  Stop Distance: ${stop_distance:.2f}")
            print()

            for risk_amount in risk_amounts:
                sizing = await position_manager.calculate_position_size(
                    contract_id="MNQ",  # Use base symbol
                    risk_amount=risk_amount,
                    entry_price=market_price,
                    stop_price=market_price - stop_distance,
                    account_balance=account_balance,
                )

                if "error" in sizing:
                    print(f"  Risk ${risk_amount:.0f}: ❌ {sizing['error']}")
                else:
                    suggested_size = sizing["suggested_size"]
                    total_risk = sizing["total_risk"]
                    risk_percentage = sizing["risk_percentage"]
                    risk_per_contract = sizing["risk_per_contract"]

                    print(f"  Risk ${risk_amount:.0f}:")
                    print(f"    Position Size: {suggested_size} contracts")
                    print(f"    Risk per Contract: ${risk_per_contract:.2f}")
                    print(f"    Total Risk: ${total_risk:.2f}")
                    print(f"    Risk %: {risk_percentage:.1f}%")

                    # Show warnings if any
                    warnings = sizing.get("risk_warnings", [])
                    if warnings:
                        for warning in warnings:
                            print(f"    ⚠️  {warning}")

            # Create order manager for placing test position
            print("\n🏗️ Creating order manager for test position...")
            order_manager = create_order_manager(client, realtime_client)
            await order_manager.initialize(realtime_client=realtime_client)

            # Ask user if they want to place a test position
            print("\n⚠️  DEMONSTRATION: Place a test position?")
            print("   This will place a REAL market order for 1 MNQ contract")
            print("   The position will be closed at the end of the demo")

            # Get user confirmation
            try:
                response = input("\nPlace test position? (y/N): ").strip().lower()
                place_test_position = response == "y"
            except (EOFError, KeyboardInterrupt):
                # Handle non-interactive mode
                print("N (non-interactive mode)")
                place_test_position = False

            if place_test_position:
                print("\n📈 Placing test market order...")

                # Get MNQ contract info
                mnq = await client.get_instrument("MNQ")
                if not mnq:
                    print("❌ Could not find MNQ instrument")
                else:
                    # Get tick value for P&L calculations
                    tick_size = float(mnq.tickSize)  # $0.25 for MNQ
                    tick_value = float(mnq.tickValue)  # $0.50 for MNQ
                    point_value = tick_value / tick_size  # $2 per point

                    print(
                        f"   Using {mnq.name}: Tick size ${tick_size}, Tick value ${tick_value}, Point value ${point_value}"
                    )

                    # Place a small market buy order (1 contract)
                    order_response = await order_manager.place_market_order(
                        contract_id=mnq.id,
                        side=0,  # Buy
                        size=1,  # Just 1 contract for safety
                    )

                    if order_response and order_response.success:
                        print(
                            f"✅ Test position order placed: {order_response.orderId}"
                        )
                        print("   Waiting for order to fill and position to appear...")

                        # Wait for position to appear
                        wait_time = 0
                        max_wait = 10  # Maximum 10 seconds
                        position_found = False

                        while wait_time < max_wait and not position_found:
                            await asyncio.sleep(2)
                            wait_time += 2

                            # Refresh positions
                            await position_manager.refresh_positions()
                            positions = await position_manager.get_all_positions()

                            if positions:
                                position_found = True
                                print("\n✅ Position established!")

                                # Display the new position
                                for pos in positions:
                                    direction = "LONG" if pos.type == 1 else "SHORT"
                                    print("\n📊 New Position:")
                                    print(f"   Contract: {pos.contractId}")
                                    print(f"   Direction: {direction}")
                                    print(f"   Size: {pos.size} contracts")
                                    print(f"   Average Price: ${pos.averagePrice:.2f}")

                                    # Get fresh market price for accurate P&L
                                    try:
                                        # Get current price from market data
                                        current_market_price = (
                                            await get_current_market_price(
                                                client, "MNQ", realtime_data_manager
                                            )
                                        )

                                        if current_market_price is None:
                                            # Use entry price if no market data
                                            current_market_price = pos.averagePrice
                                            print(
                                                "   ⚠️  No market data - using entry price"
                                            )

                                        # Use position manager's P&L calculation with point value
                                        pnl_info = await position_manager.calculate_position_pnl(
                                            pos,
                                            current_market_price,
                                            point_value=point_value,
                                        )

                                        print(
                                            f"   Current Price: ${current_market_price:.2f}"
                                        )
                                        print(
                                            f"   Unrealized P&L: ${pnl_info['unrealized_pnl']:.2f}"
                                        )
                                        print(
                                            f"   Points: {pnl_info['price_change']:.2f}"
                                        )
                                    except Exception:
                                        print("   P&L calculation pending...")

                                # Monitor the position for 20 seconds
                                print("\n👀 Monitoring position for 20 seconds...")

                                for i in range(4):  # 4 updates, 5 seconds apart
                                    await asyncio.sleep(5)

                                    # Refresh and show update
                                    await position_manager.refresh_positions()
                                    positions = (
                                        await position_manager.get_all_positions()
                                    )

                                    if positions:
                                        print(f"\n📊 Position Update {i + 1}/4:")
                                        for pos in positions:
                                            try:
                                                # Get fresh market price
                                                current_market_price = (
                                                    await get_current_market_price(
                                                        client,
                                                        "MNQ",
                                                        realtime_data_manager,
                                                    )
                                                )

                                                if current_market_price is None:
                                                    # Use entry price if no market data
                                                    current_market_price = (
                                                        pos.averagePrice
                                                    )
                                                    print(
                                                        "   ⚠️  No market data - P&L will be $0"
                                                    )

                                                # Use position manager's P&L calculation with point value
                                                pnl_info = await position_manager.calculate_position_pnl(
                                                    pos,
                                                    current_market_price,
                                                    point_value=point_value,
                                                )

                                                print(
                                                    f"   Current Price: ${current_market_price:.2f}"
                                                )
                                                print(
                                                    f"   P&L: ${pnl_info['unrealized_pnl']:.2f}"
                                                )
                                                print(
                                                    f"   Points: {pnl_info['price_change']:.2f}"
                                                )
                                            except Exception:
                                                print("   P&L: Calculating...")

                        if not position_found:
                            print(
                                "⚠️  Position not found after waiting. Order may still be pending."
                            )
                    else:
                        error_msg = (
                            order_response.errorMessage
                            if order_response
                            else "Unknown error"
                        )
                        print(f"❌ Failed to place test order: {error_msg}")

            # Check for any positions that need cleanup
            positions = await position_manager.get_all_positions()

            if positions:
                print("\n🧹 Cleaning up positions...")

                for position in positions:
                    # Close the position
                    side = 1 if position.type == 1 else 0  # Opposite side to close
                    close_response = await order_manager.place_market_order(
                        contract_id=position.contractId,
                        side=side,
                        size=position.size,
                    )

                    if close_response and close_response.success:
                        print(
                            f"✅ Close order placed for {position.contractId}: {close_response.orderId}"
                        )
                    else:
                        print(f"❌ Failed to close {position.contractId}")

                # Wait for positions to close
                await asyncio.sleep(3)

                # Final check
                positions = await position_manager.get_all_positions()
                if not positions:
                    print("✅ All positions closed successfully")
                else:
                    print(f"⚠️  {len(positions)} positions still open")

            # Demonstrate portfolio P&L calculation
            print("\n💰 Portfolio P&L Summary:")
            portfolio_pnl = await position_manager.get_portfolio_pnl()
            print(f"  Position Count: {portfolio_pnl['position_count']}")
            print(
                f"  Total Unrealized P&L: ${portfolio_pnl.get('total_unrealized_pnl', 0):.2f}"
            )
            print(
                f"  Total Realized P&L: ${portfolio_pnl.get('total_realized_pnl', 0):.2f}"
            )
            print(f"  Net P&L: ${portfolio_pnl.get('net_pnl', 0):.2f}")

            # Display position statistics
            print("\n📊 Position Statistics:")
            stats = position_manager.get_position_statistics()
            print(f"  Tracked Positions: {stats['tracked_positions']}")
            print(
                f"  P&L Calculations: {stats['statistics'].get('pnl_calculations', 0)}"
            )
            print(
                f"  Position Updates: {stats['statistics'].get('position_updates', 0)}"
            )
            print(f"  Refresh Count: {stats['statistics'].get('refresh_count', 0)}")

            if stats["realtime_enabled"]:
                print("  Real-time Updates: ✅ Enabled")
            else:
                print("  Real-time Updates: ❌ Disabled")

            print("\n✅ Position management example completed!")
            print("\n📝 Next Steps:")
            print(
                "   - Try examples/async_04_combined_trading.py for full trading workflow"
            )
            print("   - Review position manager documentation for advanced features")
            print("   - Implement your own risk management strategies")

            # Clean up
            if realtime_data_manager:
                await realtime_data_manager.cleanup()
            await realtime_client.cleanup()

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ASYNC POSITION MANAGEMENT EXAMPLE")
    print("=" * 60 + "\n")

    asyncio.run(main())

    print("\n✅ Example completed!")
