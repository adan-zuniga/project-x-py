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

Updated for v3.0.0: Uses new TradingSuite for simplified initialization.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/03_position_management.py

Author: TexasCoding
Date: July 2025
"""

import asyncio
from typing import TYPE_CHECKING

from project_x_py import (
    TradingSuite,
    setup_logging,
)

if TYPE_CHECKING:
    from project_x_py.position_manager import PositionManager


async def get_current_market_price(
    suite: TradingSuite,
    symbol: str = "MNQ",
) -> float | None:
    """Get current market price with async fallback for closed markets."""
    # Try to get real-time price first if available
    try:
        current_price = await suite[symbol].data.get_current_price()
        if current_price:
            return float(current_price)
    except Exception as e:
        print(f"   ⚠️  Real-time price not available: {e}")

    # Try different data configurations concurrently
    configs = [(1, 1), (1, 5), (2, 15), (5, 15), (7, 60)]

    async def try_get_data(days: int, interval: int) -> float | None:
        try:
            market_data = await suite.client.get_bars(
                symbol, days=days, interval=interval
            )
            if market_data is not None and not market_data.is_empty():
                return float(market_data.select("close").tail(1).item())
        except Exception:
            pass
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


async def display_positions(
    position_manager: "PositionManager", suite: TradingSuite | None = None
) -> None:
    """Display current positions with detailed information."""
    print("\n📊 Current Positions:")
    print("-" * 80)

    positions = await position_manager.get_all_positions()

    if not positions:
        print("No open positions")
        return

    # Display each position with real P&L calculation
    for position in positions:
        print(f"\n{position.contractId}:")
        print(f"  Quantity: {position.size}")
        print(f"  Average Price: ${position.averagePrice:.2f}")

        # Calculate position value
        position_value = position.averagePrice * position.size
        print(f"  Position Value: ${position_value:,.2f}")

        # Calculate real P&L if we have market data
        unrealized_pnl = 0.0
        if suite:
            try:
                # Get current market price
                current_price = await suite[position.symbol].data.get_current_price()
                if current_price and suite[position.symbol].instrument_info:
                    # Use the instrument already loaded in suite
                    instrument_info = suite[position.symbol].instrument_info
                    point_value = instrument_info.tickValue / instrument_info.tickSize

                    # Calculate P&L using position manager's method
                    pnl_data = await position_manager.calculate_position_pnl(
                        position, float(current_price), point_value=point_value
                    )
                    unrealized_pnl = pnl_data["unrealized_pnl"]
            except Exception:
                # If we can't get real-time price, try portfolio P&L
                try:
                    portfolio_pnl = await position_manager.get_portfolio_pnl()
                    unrealized_pnl = portfolio_pnl.get("unrealized_pnl", 0) / len(
                        positions
                    )
                except Exception:
                    pass

        print(f"  Unrealized P&L: ${unrealized_pnl:,.2f}")


async def display_risk_metrics(position_manager: "PositionManager") -> None:
    """Display risk metrics and alerts asynchronously."""
    print("\n⚠️  Risk Metrics:")
    print("-" * 80)

    try:
        # Get risk metrics if available
        try:
            if hasattr(position_manager, "get_risk_metrics"):
                risk_check = await position_manager.get_risk_metrics()
                # Check if we're within daily loss limits and position limits
                within_daily_loss = (
                    risk_check["daily_loss"] <= risk_check["daily_loss_limit"]
                )
                within_position_limit = (
                    risk_check["position_count"] <= risk_check["position_limit"]
                )
                within_risk_limits = (
                    risk_check["current_risk"] <= risk_check["max_risk"]
                )

                if within_daily_loss and within_position_limit and within_risk_limits:
                    print("✅ All positions within risk limits")
                else:
                    violations = []
                    if not within_daily_loss:
                        violations.append(
                            f"Daily loss: ${risk_check['daily_loss']:.2f} / ${risk_check['daily_loss_limit']:.2f}"
                        )
                    if not within_position_limit:
                        violations.append(
                            f"Position count: {risk_check['position_count']} / {risk_check['position_limit']}"
                        )
                    if not within_risk_limits:
                        violations.append(
                            f"Current risk: ${risk_check['current_risk']:.2f} / ${risk_check['max_risk']:.2f}"
                        )
                    if violations:
                        print(f"⚠️  Risk limit violations: {', '.join(violations)}")
                    else:
                        print("✅ All positions within risk limits")
            else:
                print("Risk limits check not available")

            if hasattr(position_manager, "get_risk_metrics"):
                risk_summary = await position_manager.get_risk_metrics()
                print("\nRisk Summary:")
                print(f"  Current Risk: ${risk_summary.get('current_risk', 0):,.2f}")
                print(f"  Max Risk Allowed: ${risk_summary.get('max_risk', 0):,.2f}")
                print(
                    f"  Max Drawdown: {risk_summary.get('max_drawdown', 0) * 100:.1f}%"
                )
                print(f"  Win Rate: {risk_summary.get('win_rate', 0) * 100:.1f}%")
                print(f"  Profit Factor: {risk_summary.get('profit_factor', 0):.2f}")
            else:
                print("Risk summary not available")

        except AttributeError:
            print("Risk metrics not available in current implementation")

    except Exception as e:
        print(f"Error calculating risk metrics: {e}")


async def monitor_positions(
    position_manager: "PositionManager",
    suite: TradingSuite | None = None,
    duration: int = 30,
) -> None:
    """Monitor positions for a specified duration with async updates."""
    print(f"\n👁️  Monitoring positions for {duration} seconds...")
    print("=" * 80)

    start_time = asyncio.get_event_loop().time()
    check_interval = 5  # seconds

    try:
        while asyncio.get_event_loop().time() - start_time < duration:
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            print(f"\n⏰ Check at {elapsed}s:")

            # Run checks
            try:
                positions = await position_manager.get_all_positions()

                if positions:
                    print(f"  Active positions: {len(positions)}")

                    # Get P&L with current market prices
                    total_pnl = 0.0
                    try:
                        # Try to calculate real P&L with current prices
                        if suite and positions:
                            current_price = await suite["MNQ"].data.get_current_price()
                            if current_price and suite["MNQ"].instrument_info:
                                # Use the instrument already loaded in suite
                                instrument_info = suite["MNQ"].instrument_info
                                point_value = (
                                    instrument_info.tickValue / instrument_info.tickSize
                                )

                                for position in positions:
                                    pnl_data = (
                                        await position_manager.calculate_position_pnl(
                                            position,
                                            float(current_price),
                                            point_value=point_value,
                                        )
                                    )
                                    total_pnl += pnl_data["unrealized_pnl"]
                        else:
                            # Fallback to portfolio P&L
                            pnl = await position_manager.get_portfolio_pnl()
                            total_pnl = pnl.get("total_pnl", 0)
                    except Exception:
                        pass

                    print(f"  Total P&L: ${total_pnl:,.2f}")

                    # Get summary if available
                    if hasattr(position_manager, "get_portfolio_pnl"):
                        try:
                            summary = await position_manager.get_portfolio_pnl()
                            print(
                                f"  Win rate: {summary.get('win_rate', 0):.1%} ({summary.get('winning_trades', 0)}/{summary.get('total_trades', 0)})"
                            )
                        except Exception:
                            pass
                else:
                    print("  No active positions")

            except Exception as e:
                print(f"  Error during monitoring: {e}")

            # Sleep until next check
            await asyncio.sleep(check_interval)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n⚠️  Monitoring interrupted by user")
        raise  # Re-raise to trigger cleanup in main


async def main() -> bool:
    """Main async position management demonstration."""
    logger = setup_logging(level="INFO")
    print("🚀 Async Position Management Example (v3.0.0)")
    print("=" * 80)

    suite = None
    cleanup_positions = False

    try:
        # Initialize TradingSuite v3
        print("\n🔑 Initializing TradingSuite v3...")
        suite = await TradingSuite.create(
            "MNQ",
            timeframes=["1min", "5min"],
            features=["risk_manager"],
        )

        print(
            f"✅ Connected to: {suite.client.account_info.name if suite.client.account_info else 'Unknown'}"
        )

        # Check for existing positions
        print("\n📊 Checking existing positions...")
        existing_positions = await suite["MNQ"].positions.get_all_positions()

        if existing_positions:
            print(f"Found {len(existing_positions)} existing positions")
            await display_positions(suite["MNQ"].positions, suite)
        else:
            print("No existing positions found")

            # Optionally place a test order to create a position
            print(
                "\n📝 Would you like to place a test order to demonstrate position tracking?"
            )
            print("   (This will place a REAL order on the market)")

            # Get instrument info and current price for order placement
            instrument_info = await suite.client.get_instrument("MNQ")
            contract_id = instrument_info.id
            current_price = await get_current_market_price(suite)

            if current_price:
                print(f"\n   Current MNQ price: ${current_price:.2f}")
                print(f"   Contract ID: {contract_id}")
                print("   Test order: BUY 1 MNQ at market")

                # Wait for user confirmation
                try:
                    loop = asyncio.get_event_loop()
                    try:
                        response = await loop.run_in_executor(
                            None,
                            lambda: input("\n   Place test order? (y/N): ")
                            .strip()
                            .lower(),
                        )
                    except (KeyboardInterrupt, asyncio.CancelledError):
                        print("\n\n⚠️  Script interrupted by user")
                        return False

                    if response == "y":
                        print("\n   Placing market order...")
                        order_response = await suite["MNQ"].orders.place_market_order(
                            contract_id=contract_id,
                            side=0,
                            size=1,  # Buy
                        )

                        if order_response and order_response.success:
                            print(
                                f"   ✅ Order placed! Order ID: {order_response.orderId}"
                            )
                            print("   Waiting for fill...")
                            await asyncio.sleep(3)

                            # Refresh positions
                            existing_positions = await suite[
                                "MNQ"
                            ].positions.get_all_positions()
                            if existing_positions:
                                print("   ✅ Position created!")
                        else:
                            print("   ❌ Order failed")
                except (EOFError, KeyboardInterrupt):
                    print("\n   ⚠️  Skipping test order")

        # Display comprehensive position information
        if await suite["MNQ"].positions.get_all_positions():
            print("\n" + "=" * 80)
            print("📈 POSITION MANAGEMENT DEMONSTRATION")
            print("=" * 80)

            # 1. Display current positions
            await display_positions(suite["MNQ"].positions, suite)

            # 2. Show risk metrics
            await display_risk_metrics(suite["MNQ"].positions)

            # 3. Portfolio statistics
            print("\n📊 Portfolio Statistics:")
            print("-" * 80)
            try:
                if hasattr(suite["MNQ"].positions, "get_portfolio_pnl"):
                    stats = await suite["MNQ"].positions.get_portfolio_pnl()
                    print(f"  Total Trades: {stats.get('total_trades', 0)}")
                    print(f"  Winning Trades: {stats.get('winning_trades', 0)}")
                    print(f"  Average Win: ${stats.get('average_win', 0):,.2f}")
                    print(f"  Average Loss: ${stats.get('average_loss', 0):,.2f}")
                    print(f"  Profit Factor: {stats.get('profit_factor', 0):.2f}")
                    print(f"  Sharpe Ratio: {stats.get('sharpe_ratio', 0):.2f}")
                else:
                    print("  Portfolio statistics not available")
            except Exception as e:
                print(f"  Error getting statistics: {e}")

            # 4. Performance analytics
            print("\n📈 Performance Analytics:")
            print("-" * 80)
            try:
                if hasattr(suite["MNQ"].positions, "get_portfolio_pnl"):
                    analytics = await suite["MNQ"].positions.get_portfolio_pnl()
                    print(f"  Total P&L: ${analytics.get('total_pnl', 0):,.2f}")
                    print(f"  Max Drawdown: ${analytics.get('max_drawdown', 0):,.2f}")
                    print(
                        f"  Recovery Factor: {analytics.get('recovery_factor', 0):.2f}"
                    )
                    print(
                        f"  Average Hold Time: {analytics.get('avg_hold_time', 'N/A')}"
                    )
                else:
                    print("  Performance analytics not available")
            except Exception as e:
                print(f"  Error getting analytics: {e}")

            # 5. Monitor positions for changes
            print("\n" + "=" * 80)
            print("📡 REAL-TIME POSITION MONITORING")
            print("=" * 80)

            # Monitor for 30 seconds
            await monitor_positions(suite["MNQ"].positions, suite, duration=30)

            # 6. Offer to close positions
            if await suite["MNQ"].positions.get_all_positions():
                print("\n" + "=" * 80)
                print("🔧 POSITION MANAGEMENT")
                print("=" * 80)
                print("\nWould you like to close all positions?")
                print("(This will place market orders to flatten positions)")

                try:
                    loop = asyncio.get_event_loop()
                    try:
                        response = await loop.run_in_executor(
                            None,
                            lambda: input("\nClose all positions? (y/N): ")
                            .strip()
                            .lower(),
                        )
                    except (KeyboardInterrupt, asyncio.CancelledError):
                        print("\n\n⚠️  Script interrupted by user")
                        return False

                    if response == "y":
                        print("\n🔄 Closing all positions...")
                        positions = await suite["MNQ"].positions.get_all_positions()

                        for position in positions:
                            try:
                                result = await suite["MNQ"].orders.close_position(
                                    position.contractId, method="market"
                                )
                                if result and result.success:
                                    print(
                                        f"  ✅ Closed {position.contractId}: Order #{result.orderId}"
                                    )
                                else:
                                    print(f"  ❌ Failed to close {position.contractId}")
                            except Exception as e:
                                print(f"  ❌ Error closing {position.contractId}: {e}")

                        # Final position check
                        await asyncio.sleep(3)
                        final_positions = await suite[
                            "MNQ"
                        ].positions.get_all_positions()
                        if not final_positions:
                            print("\n✅ All positions closed successfully!")
                        else:
                            print(f"\n⚠️  {len(final_positions)} positions still open")
                except (EOFError, KeyboardInterrupt):
                    print("\n⚠️  Keeping positions open")

        # Display final summary
        print("\n" + "=" * 80)
        print("📊 SESSION SUMMARY")
        print("=" * 80)

        try:
            if hasattr(suite["MNQ"].positions, "get_portfolio_pnl"):
                session_summary = await suite["MNQ"].positions.get_portfolio_pnl()
                print(f"  Session Duration: {session_summary.get('duration', 'N/A')}")
                print(
                    f"  Positions Opened: {session_summary.get('positions_opened', 0)}"
                )
                print(
                    f"  Positions Closed: {session_summary.get('positions_closed', 0)}"
                )
                print(f"  Session P&L: ${session_summary.get('session_pnl', 0):,.2f}")
            else:
                print("  Session summary not available")
        except Exception as e:
            print(f"  Session summary error: {e}")

        print("\n✅ Position management example completed!")
        print("\n📝 Key Features Demonstrated:")
        print("  - Real-time position tracking with TradingSuite v3")
        print("  - Concurrent P&L and risk calculations")
        print("  - Portfolio analytics and statistics")
        print("  - Real-time position monitoring")
        print("  - Position lifecycle management")

        await suite.disconnect()
        return True

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n⏹️ Example interrupted by user")

        # Ask user if they want to close positions
        if suite:
            try:
                positions = await suite["MNQ"].positions.get_all_positions()
                if positions:
                    print(f"\n⚠️  You have {len(positions)} open position(s).")
                    print("Would you like to close them before exiting?")
                    try:
                        # Use a simple default rather than waiting for input on interrupt
                        print("Auto-closing positions for safety...")
                        cleanup_positions = True
                    except Exception:
                        cleanup_positions = True
            except Exception:
                pass

        return False
    except Exception as e:
        logger.error(f"Position management example failed: {e}")
        print(f"\n❌ Error: {e}")
        cleanup_positions = True
        return False
    finally:
        # Ensure cleanup happens regardless of how we exit
        if suite:
            try:
                # Check if we need to close positions
                if cleanup_positions:
                    print("\n🧹 Performing cleanup...")
                    positions = await suite["MNQ"].positions.get_all_positions()
                    if positions:
                        print(f"  Closing {len(positions)} open position(s)...")
                        for position in positions:
                            try:
                                result = await suite["MNQ"].orders.close_position(
                                    position.contractId, method="market"
                                )
                                if result and result.success:
                                    print(f"  ✅ Closed {position.contractId}")
                                else:
                                    print(f"  ⚠️  Could not close {position.contractId}")
                            except Exception as e:
                                print(f"  ❌ Error closing {position.contractId}: {e}")

                        # Wait for orders to process
                        await asyncio.sleep(2)

                        # Final check
                        final_positions = await suite[
                            "MNQ"
                        ].positions.get_all_positions()
                        if final_positions:
                            print(f"  ⚠️  {len(final_positions)} position(s) still open")
                        else:
                            print("  ✅ All positions closed")
                    else:
                        print("  No positions to close")

                # Always disconnect the suite
                print("  Disconnecting TradingSuite...")
                await suite.disconnect()
                print("  ✅ Disconnected")
            except Exception as e:
                print(f"  ❌ Cleanup error: {e}")


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
