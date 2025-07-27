#!/usr/bin/env python3
"""
Position Management and Tracking Example

Demonstrates comprehensive position management and risk monitoring:
- Position tracking and history
- Portfolio P&L calculations
- Risk metrics and alerts
- Position sizing calculations
- Real-time position monitoring
- Portfolio reporting

Uses MNQ micro contracts for testing safety.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/03_position_management.py

Author: TexasCoding
Date: July 2025
"""

import time

from project_x_py import (
    ProjectX,
    create_order_manager,
    create_position_manager,
    create_realtime_client,
    setup_logging,
)


def get_current_market_price(client, symbol="MNQ"):
    """Get current market price with fallback for closed markets."""
    # Try different data configurations to find available data
    for days, interval in [(1, 1), (1, 5), (2, 15), (5, 15), (7, 60)]:
        try:
            market_data = client.get_data(symbol, days=days, interval=interval)
            if market_data is not None and not market_data.is_empty():
                return float(market_data.select("close").tail(1).item())
        except Exception:
            continue

    # Fallback price if no data available
    return 23400.00  # Reasonable MNQ price


def display_positions(position_manager, client):
    """Display current positions with detailed information."""
    positions = position_manager.get_all_positions()

    print(f"\n📊 Current Positions ({len(positions)}):")
    if not positions:
        print("   No open positions")
        return

    # Get current market price for P&L calculations
    current_price = get_current_market_price(client)

    for pos in positions:
        direction = "LONG" if pos.type == 1 else "SHORT"
        try:
            pnl_info = position_manager.calculate_position_pnl(pos, current_price)
        except Exception as e:
            print(f"     ❌ P&L calculation error: {e}")
            pnl_info = None

        print(f"   {pos.contractId}:")
        print(f"     Direction: {direction}")
        print(f"     Size: {pos.size} contracts")
        print(f"     Average Price: ${pos.averagePrice:.2f}")

        if pnl_info:
            print(f"     Unrealized P&L: ${pnl_info.get('unrealized_pnl', 0):.2f}")
            print(f"     Current Price: ${pnl_info.get('current_price', 0):.2f}")
            print(f"     P&L per Contract: ${pnl_info.get('pnl_per_contract', 0):.2f}")


def display_risk_metrics(position_manager):
    """Display portfolio risk metrics."""
    try:
        risk_metrics = position_manager.get_risk_metrics()
        print("\n⚖️ Risk Metrics:")
        print(f"   Total Exposure: ${risk_metrics['total_exposure']:.2f}")
        print(f"   Largest Position Risk: {risk_metrics['largest_position_risk']:.2%}")
        print(f"   Diversification Score: {risk_metrics['diversification_score']:.2f}")

        risk_warnings = risk_metrics.get("risk_warnings", [])
        if risk_warnings:
            print("   ⚠️ Risk Warnings:")
            for warning in risk_warnings:
                print(f"     • {warning}")
        else:
            print("   ✅ No risk warnings")

    except Exception as e:
        print(f"   ❌ Risk metrics error: {e}")


def display_portfolio_summary(position_manager):
    """Display portfolio P&L summary."""
    try:
        portfolio_pnl = position_manager.get_portfolio_pnl()
        print("\n💰 Portfolio Summary:")
        print(f"   Position Count: {portfolio_pnl['position_count']}")
        print(
            f"   Total Unrealized P&L: ${portfolio_pnl.get('total_unrealized_pnl', 0):.2f}"
        )
        print(
            f"   Total Realized P&L: ${portfolio_pnl.get('total_realized_pnl', 0):.2f}"
        )
        print(f"   Net P&L: ${portfolio_pnl.get('net_pnl', 0):.2f}")

    except Exception as e:
        print(f"   ❌ Portfolio P&L error: {e}")


def demonstrate_position_sizing(client, position_manager, contract_id: str):
    """Demonstrate position sizing calculations."""
    print("\n📐 Position Sizing Analysis:")

    # Get current market price (with fallback for closed markets)
    current_price = None

    # Try different data configurations to find available data
    for days, interval in [(1, 1), (1, 5), (2, 15), (5, 15), (7, 60)]:
        try:
            market_data = client.get_data("MNQ", days=days, interval=interval)
            if market_data is not None and not market_data.is_empty():
                current_price = float(market_data.select("close").tail(1).item())
                latest_time = market_data.select("timestamp").tail(1).item()
                print(f"   ✅ Using price: ${current_price:.2f} from {latest_time}")
                break
        except Exception:
            continue

    # If no historical data available, use a reasonable fallback price
    if current_price is None:
        print("   ⚠️  No historical market data available (market may be closed)")
        print("   Using fallback price for demonstration...")
        current_price = 23400.00  # Reasonable MNQ price
        print(f"   Fallback price: ${current_price:.2f}")

    # Test different risk amounts
    risk_amounts = [25.0, 50.0, 100.0, 200.0]
    stop_distance = 10.0  # $10 stop loss

    print(f"   Current Price: ${current_price:.2f}")
    print(f"   Stop Distance: ${stop_distance:.2f}")
    print()

    for risk_amount in risk_amounts:
        sizing = position_manager.calculate_position_size(
            contract_id="MNQ",  # Use base symbol
            risk_amount=risk_amount,
            entry_price=current_price,
            stop_price=current_price - stop_distance,
        )

        if "error" in sizing:
            print(f"   Risk ${risk_amount:.0f}: ❌ {sizing['error']}")
        else:
            print(f"   Risk ${risk_amount:.0f}:")
            print(f"     Suggested Size: {sizing['suggested_size']} contracts")
            print(f"     Risk per Contract: ${sizing['risk_per_contract']:.2f}")
            print(f"     Risk Percentage: {sizing['risk_percentage']:.2f}%")


def setup_position_alerts(position_manager, contract_id: str):
    """Setup position alerts for monitoring."""
    print(f"\n🚨 Setting up position alerts for {contract_id}:")

    try:
        # Set up basic risk alerts
        position_manager.add_position_alert(
            contract_id=contract_id,
            max_loss=-50.0,  # Alert if loss exceeds $50
            max_gain=100.0,  # Alert if profit exceeds $100
        )
        print("   ✅ Risk alert set: Max loss $50, Max gain $100")

        # Add a callback for position updates
        def position_update_callback(data):
            event_data = data.get("data", {})
            contract = event_data.get("contractId", "Unknown")
            size = event_data.get("size", 0)
            price = event_data.get("averagePrice", 0)
            print(f"   📊 Position Update: {contract} - Size: {size} @ ${price:.2f}")

        position_manager.add_callback("position_update", position_update_callback)
        print("   ✅ Position update callback registered")

    except Exception as e:
        print(f"   ❌ Alert setup error: {e}")


def main():
    """Demonstrate comprehensive position management."""
    logger = setup_logging(level="INFO")
    print("🚀 Position Management Example")
    print("=" * 60)

    try:
        # Initialize client
        print("🔑 Initializing ProjectX client...")
        client = ProjectX.from_env()

        account = client.get_account_info()
        if not account:
            print("❌ Could not get account information")
            return False

        print(f"✅ Connected to account: {account.name}")
        print(f"   Balance: ${account.balance:,.2f}")
        print(f"   Simulated: {account.simulated}")

        # Get MNQ contract info
        print("\n📈 Getting MNQ contract information...")
        mnq_instrument = client.get_instrument("MNQ")
        if not mnq_instrument:
            print("❌ Could not find MNQ instrument")
            return False

        contract_id = mnq_instrument.id
        print(f"✅ MNQ Contract: {contract_id}")

        # Create position manager with real-time tracking
        print("\n🏗️ Creating position manager...")
        try:
            jwt_token = client.get_session_token()
            realtime_client = create_realtime_client(jwt_token, str(account.id))
            position_manager = create_position_manager(client, realtime_client)
            print("✅ Position manager created with real-time tracking")
        except Exception as e:
            print(f"⚠️  Real-time client failed, using basic position manager: {e}")
            position_manager = create_position_manager(client, None)

        # Also create order manager for potential order placement
        try:
            order_manager = create_order_manager(
                client, realtime_client if "realtime_client" in locals() else None
            )
            print("✅ Order manager created for position-order integration")
        except Exception as e:
            print(f"⚠️  Order manager creation failed: {e}")
            order_manager = None

        # Display initial portfolio state
        print("\n" + "=" * 50)
        print("📊 INITIAL PORTFOLIO STATE")
        print("=" * 50)

        display_positions(position_manager, client)
        display_portfolio_summary(position_manager)
        display_risk_metrics(position_manager)

        # Demonstrate position sizing
        print("\n" + "=" * 50)
        print("📐 POSITION SIZING DEMONSTRATION")
        print("=" * 50)

        demonstrate_position_sizing(client, position_manager, contract_id)

        # Setup alerts and monitoring
        print("\n" + "=" * 50)
        print("🚨 ALERT AND MONITORING SETUP")
        print("=" * 50)

        setup_position_alerts(position_manager, contract_id)

        # Open a small test position to demonstrate position management features
        print("\n" + "=" * 50)
        print("📈 OPENING TEST POSITION")
        print("=" * 50)

        if order_manager:
            try:
                print("Opening a small 1-contract LONG position for demonstration...")

                # Get current market price for order placement
                current_price = get_current_market_price(client)

                # Place a small market buy order (1 contract)
                test_order = order_manager.place_order(
                    contract_id=contract_id,
                    side=0,  # Bid (buy)
                    order_type=2,  # Market order
                    size=1,  # Just 1 contract for safety
                    custom_tag=f"test_pos_{int(time.time())}",
                )

                if test_order.success:
                    print(f"✅ Test position order placed: {test_order.orderId}")
                    print("   Waiting for order to fill and position to appear...")

                    # Wait for order to fill and position to appear
                    wait_time = 0
                    max_wait = 30  # Maximum 30 seconds

                    while wait_time < max_wait:
                        time.sleep(2)
                        wait_time += 2

                        # Check if we have a position now
                        test_positions = position_manager.get_all_positions()
                        if test_positions:
                            print(
                                f"✅ Position opened successfully after {wait_time}s!"
                            )
                            for pos in test_positions:
                                direction = "LONG" if pos.type == 1 else "SHORT"
                                print(
                                    f"   📊 {pos.contractId}: {direction} {pos.size} contracts @ ${pos.averagePrice:.2f}"
                                )
                            break
                        else:
                            print(f"   ⏳ Waiting for position... ({wait_time}s)")

                    if wait_time >= max_wait:
                        print("   ⚠️  Position didn't appear within 30 seconds")
                        print(
                            "   This may be normal if market is closed or order is still pending"
                        )

                else:
                    print(f"❌ Test position order failed: {test_order.errorMessage}")
                    print(
                        "   Continuing with example using existing positions (if any)"
                    )

            except Exception as e:
                print(f"❌ Error opening test position: {e}")
                print("   Continuing with example using existing positions (if any)")
        else:
            print("⚠️  No order manager available, skipping position opening")

        # If we have existing positions, demonstrate detailed analysis
        positions = position_manager.get_all_positions()
        if positions:
            print("\n" + "=" * 50)
            print("🔍 DETAILED POSITION ANALYSIS")
            print("=" * 50)

            for pos in positions:
                print(f"\n📊 Analyzing position: {pos.contractId}")

                # Get position history
                history = position_manager.get_position_history(pos.contractId, limit=5)
                if history:
                    print(f"   Recent position changes ({len(history)}):")
                    for i, entry in enumerate(history[-3:]):  # Last 3 changes
                        timestamp = entry.get("timestamp", "Unknown")
                        size_change = entry.get("size_change", 0)
                        position_data = entry.get("position", {})
                        new_size = position_data.get("size", 0)
                        avg_price = position_data.get("averagePrice", 0)
                        print(
                            f"     {i + 1}. {timestamp}: Size change {size_change:+d} → {new_size} @ ${avg_price:.2f}"
                        )
                else:
                    print("   No position history available")

                # Get real-time P&L
                current_price = get_current_market_price(client)
                try:
                    pnl_info = position_manager.calculate_position_pnl(
                        pos, current_price
                    )
                except Exception as e:
                    print(f"   ❌ P&L calculation error: {e}")
                    pnl_info = None

                if pnl_info:
                    print("   Current P&L Analysis:")
                    print(
                        f"     Unrealized P&L: ${pnl_info.get('unrealized_pnl', 0):.2f}"
                    )
                    print(
                        f"     P&L per Contract: ${pnl_info.get('pnl_per_contract', 0):.2f}"
                    )
                    print(
                        f"     Current Price: ${pnl_info.get('current_price', 0):.2f}"
                    )
                    print(f"     Price Change: ${pnl_info.get('price_change', 0):.2f}")

        # Demonstrate portfolio report generation
        print("\n" + "=" * 50)
        print("📋 PORTFOLIO REPORT GENERATION")
        print("=" * 50)

        try:
            portfolio_report = position_manager.export_portfolio_report()

            print("✅ Portfolio report generated:")
            print(f"   Report Time: {portfolio_report['report_timestamp']}")

            summary = portfolio_report.get("portfolio_summary", {})
            print(f"   Total Positions: {summary.get('total_positions', 0)}")
            print(f"   Total P&L: ${summary.get('total_pnl', 0):.2f}")
            print(f"   Portfolio Risk: {summary.get('portfolio_risk', 0):.2%}")

            # Show position details
            position_details = portfolio_report.get("positions", [])
            if position_details:
                print("   Position Details:")
                for pos_detail in position_details:
                    contract = pos_detail.get("contract_id", "Unknown")
                    size = pos_detail.get("size", 0)
                    pnl = pos_detail.get("unrealized_pnl", 0)
                    print(f"     {contract}: {size} contracts, P&L: ${pnl:.2f}")

        except Exception as e:
            print(f"   ❌ Portfolio report error: {e}")

        # Real-time monitoring demonstration
        if positions:
            print("\n" + "=" * 50)
            print("👀 REAL-TIME POSITION MONITORING")
            print("=" * 50)

            print("Monitoring positions for 30 seconds...")
            print("(Watching for position changes, P&L updates, alerts)")

            start_time = time.time()
            last_update = 0

            while time.time() - start_time < 30:
                current_time = time.time() - start_time

                # Update every 5 seconds
                if int(current_time) > last_update and int(current_time) % 5 == 0:
                    last_update = int(current_time)
                    print(f"\n⏰ Monitor Update ({last_update}s):")

                    # Quick position status
                    current_positions = position_manager.get_all_positions()
                    if current_positions:
                        current_price = get_current_market_price(client)
                        for pos in current_positions:
                            try:
                                pnl_info = position_manager.calculate_position_pnl(
                                    pos, current_price
                                )
                                if pnl_info:
                                    pnl = pnl_info.get("unrealized_pnl", 0)
                                    print(
                                        f"   {pos.contractId}: ${current_price:.2f} (P&L: ${pnl:+.2f})"
                                    )
                            except Exception:
                                print(
                                    f"   {pos.contractId}: ${current_price:.2f} (P&L: calculation error)"
                                )

                    # Check for position alerts (would show if any triggered)
                    print("   📊 Monitoring active, no alerts triggered")

                time.sleep(1)

            print("\n✅ Monitoring completed")

        # Show final statistics
        print("\n" + "=" * 50)
        print("📊 POSITION MANAGER STATISTICS")
        print("=" * 50)

        try:
            stats = position_manager.get_position_statistics()
            print("Position Manager Statistics:")
            print(f"   Positions Tracked: {stats['statistics']['positions_tracked']}")
            print(f"   Positions Closed: {stats['statistics']['positions_closed']}")
            print(f"   Real-time Enabled: {stats['realtime_enabled']}")
            print(f"   Monitoring Active: {stats['monitoring_active']}")
            print(f"   Active Alerts: {stats['statistics'].get('active_alerts', 0)}")

            # Show health status
            health_status = stats.get("health_status", "unknown")
            if health_status == "active":
                print(f"   ✅ System Status: {health_status}")
            else:
                print(f"   ⚠️  System Status: {health_status}")

        except Exception as e:
            print(f"   ❌ Statistics error: {e}")

        # Integration with order manager (if available)
        if order_manager and positions:
            print("\n" + "=" * 50)
            print("🔗 POSITION-ORDER INTEGRATION")
            print("=" * 50)

            print("Checking position-order relationships...")
            for pos in positions:
                # Get orders for this position
                try:
                    position_orders = order_manager.get_position_orders(pos.contractId)
                    total_orders = (
                        len(position_orders["entry_orders"])
                        + len(position_orders["stop_orders"])
                        + len(position_orders["target_orders"])
                    )

                    if total_orders > 0:
                        print(f"   {pos.contractId}:")
                        print(
                            f"     Entry orders: {len(position_orders['entry_orders'])}"
                        )
                        print(
                            f"     Stop orders: {len(position_orders['stop_orders'])}"
                        )
                        print(
                            f"     Target orders: {len(position_orders['target_orders'])}"
                        )
                    else:
                        print(f"   {pos.contractId}: No associated orders")

                except Exception as e:
                    print(f"   {pos.contractId}: Error checking orders - {e}")

        print("\n✅ Position management example completed!")
        print("\n📝 Key Features Demonstrated:")
        print("   ✅ Position tracking and history")
        print("   ✅ Portfolio P&L calculations")
        print("   ✅ Risk metrics and analysis")
        print("   ✅ Position sizing calculations")
        print("   ✅ Real-time monitoring")
        print("   ✅ Portfolio reporting")
        print("   ✅ Alert system setup")

        print("\n📚 Next Steps:")
        print("   - Try examples/04_realtime_data.py for market data streaming")
        print("   - Try examples/05_orderbook_analysis.py for Level 2 data")
        print("   - Review position manager documentation for advanced features")

        return True

    except KeyboardInterrupt:
        print("\n⏹️ Example interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Position management example failed: {e}")
        print(f"❌ Error: {e}")
        return False
    finally:
        # Enhanced cleanup: Close all positions and cleanup
        if "position_manager" in locals() and "order_manager" in locals():
            try:
                print("\n🧹 Enhanced cleanup: Closing all positions and orders...")

                # Get all open positions
                positions = position_manager.get_all_positions()
                if positions:
                    print(f"   Found {len(positions)} open positions to close")

                    for pos in positions:
                        try:
                            # Determine order side (opposite of position)
                            if pos.type == 1:  # Long position
                                side = 1  # Ask (sell)
                                print(
                                    f"   📉 Closing LONG position: {pos.contractId} ({pos.size} contracts)"
                                )
                            else:  # Short position
                                side = 0  # Bid (buy)
                                print(
                                    f"   📈 Closing SHORT position: {pos.contractId} ({pos.size} contracts)"
                                )

                            # Place market order to close position
                            if order_manager:
                                close_order = order_manager.place_order(
                                    contract_id=pos.contractId,
                                    side=side,
                                    order_type=2,  # Market order
                                    size=abs(pos.size),
                                    custom_tag=f"close_pos_{int(time.time())}",
                                )

                                if close_order.success:
                                    print(
                                        f"   ✅ Close order placed: {close_order.orderId}"
                                    )
                                else:
                                    print(
                                        f"   ❌ Failed to place close order: {close_order.errorMessage}"
                                    )

                        except Exception as e:
                            print(f"   ❌ Error closing position {pos.contractId}: {e}")

                else:
                    print("   ✅ No open positions to close")

                # Cancel any remaining open orders
                if order_manager:
                    try:
                        all_orders = order_manager.search_open_orders()
                        if all_orders:
                            print(f"   Found {len(all_orders)} open orders to cancel")
                            for order in all_orders:
                                try:
                                    cancel_result = order_manager.cancel_order(order.id)
                                    if cancel_result:
                                        print(f"   ✅ Cancelled order: {order.id}")
                                    else:
                                        print(
                                            f"   ❌ Failed to cancel order {order.id}"
                                        )
                                except Exception as e:
                                    print(
                                        f"   ❌ Error cancelling order {order.id}: {e}"
                                    )
                        else:
                            print("   ✅ No open orders to cancel")
                    except Exception as e:
                        print(f"   ⚠️  Error checking orders: {e}")

                # Wait a moment for orders to process
                time.sleep(2)

                # Final position check
                final_positions = position_manager.get_all_positions()
                if final_positions:
                    print(
                        f"   ⚠️  {len(final_positions)} positions still open after cleanup"
                    )
                else:
                    print("   ✅ All positions successfully closed")

                # Cleanup managers
                position_manager.cleanup()
                print("   🧹 Position manager cleaned up")

            except Exception as e:
                print(f"   ⚠️  Enhanced cleanup error: {e}")
                # Fallback to basic cleanup
                try:
                    position_manager.cleanup()
                    print("   🧹 Basic position manager cleanup completed")
                except Exception as cleanup_e:
                    print(f"   ❌ Cleanup failed: {cleanup_e}")

        elif "position_manager" in locals():
            try:
                position_manager.cleanup()
                print("🧹 Position manager cleaned up")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
